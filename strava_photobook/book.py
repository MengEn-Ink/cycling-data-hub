"""从 Activity 数据 + 照片源编排单年画册。

页面渲染函数都是纯字符串构造；`build_year` 负责把运行时拷贝、照片下载、
高光筛选与页面排序串起来，再写出 index.html 和 theme.css。
"""
from __future__ import annotations

import html
import math
import shutil
from pathlib import Path

from .config import Config
from .editorial import CoverSelection, YearReview, build_year_review, select_cover
from .model import (
    FEATURE_PHOTO_QUOTA,
    GALLERY_PHOTO_QUOTA,
    MAX_CANDIDATE_RIDES,
    Activity,
    Highlight,
    by_year,
    plan_photo_quotas,
    select_editorial_highlights,
    target_photo_count,
)
from .route import route_heatmap_svg, route_svg
from .theme import FEATURE_CSS, THEME_CSS

PAGE_W, PAGE_H = 512, 640
THEME_OPTIONS = [
    ("editorial", "黑白橙（默认）", "#0A0A0A", "#FF5A36"),
    ("klein-neon", "克莱因蓝 + 荧光绿", "#022A99", "#B7F800"),
    ("lapis-magenta", "青金石 + 洋红", "#01008A", "#FF0086"),
    ("deep-green-lava", "深灰绿 + 熔岩", "#003D37", "#EB4743"),
    ("navy-hermes", "藏蓝色 + 爱马仕橙", "#000035", "#FC8416"),
    ("mars-rose", "马尔斯绿 + 玫瑰粉", "#01847F", "#F9D2E4"),
    ("sea-lemon", "海蓝 + 柠檬黄", "#0084D6", "#FFFF00"),
    ("klein-pine", "克莱因蓝 + 松花黄", "#022A99", "#FFE76F"),
    ("navy-crimson", "藏蓝色 + 绯红", "#000035", "#E41726"),
    ("marine-sage", "海军蓝 + 鼠尾草绿", "#29436E", "#A1CD6A"),
    ("smoke-rice", "烟雾蓝 + 稻香黄", "#2F4058", "#D89F3E"),
    ("burgundy-stone", "绛红 + 石绿", "#950F16", "#56C4C3"),
    ("china-red-white", "中国红 + 鱼肚白", "#D7000F", "#F1F2E5"),
    ("vandyke-khaki", "凡戴克棕 + 浅卡其", "#492D22", "#D8C7B5"),
    ("deepblue-mist", "深灰蓝 + 雾蓝", "#28517F", "#C7E1FA"),
    ("royal-mint", "宝蓝色 + 薄荷绿", "#012696", "#A4E2C6"),
    ("dai-lotus", "黛蓝 + 藕粉", "#425066", "#E4C6D0"),
    ("indigo-chixiang", "靛蓝 + 赤香", "#0C567D", "#EDB79C"),
    ("hidden-green-spring", "幽绿 + 春辰", "#56765E", "#CBDA99"),
]


def _esc(t: str) -> str:
    return html.escape(t or "", quote=True)


def _fmt_time(seconds: int) -> str:
    h, rem = divmod(int(seconds or 0), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _short(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


# ---- page renderers -------------------------------------------------------

def _cover(year: str, review: YearReview, selection: CoverSelection | None, route: str) -> str:
    metrics = (f'<div class="cover-index"><span>{review.rides} RIDES</span>'
               f'<span>{review.distance_km:,.0f} KM</span>'
               f'<span>{review.active_months} ACTIVE MONTHS</span></div>')
    if selection:
        title = _esc(_short(selection.activity.name, 42))
        return (f'<article class="book-page art-page cloth recto poster-cover" data-density="hard" '
                f'data-cover-mode="photo" data-layout="subject-safe" data-overlay="forbid" '
                f'data-image-zone="0,0,100,64" data-copy-zone="0,64,100,36" aria-label="Front cover">'
                f'<div class="cover-photo"><img src="{selection.photo.web_path}" alt="" '
                f'style="object-position:{selection.object_position}"></div>'
                f'<div class="cover-copy"><div class="cover-year">{year}</div>'
                f'<p class="cover-kicker">YEAR IN MOTION</p><h2 class="cover-story">{title}</h2>'
                f'{metrics}</div></article>')
    return (f'<article class="book-page art-page cloth recto poster-cover" data-density="hard" '
            f'data-cover-mode="route" aria-label="Front cover"><div class="cover-route">{route}</div>'
            f'<div class="cover-year">{year}</div><p class="cover-kicker">ROUTE ARCHIVE</p>'
            f'<h2 class="cover-story">年度骑行纪年</h2>{metrics}</article>')


def _back(year: str) -> str:
    return (f'<article class="book-page art-page cloth recto" data-density="hard" '
            f'aria-label="Back cover"><span class="back-mark">Strava Photobook · {year}</span></article>')


def _blank(label: str, cls: str = "endpaper") -> str:
    return f'<article class="book-page art-page {cls} verso" aria-label="{label}"></article>'


def _title_page(year: str, stats: dict) -> str:
    return (f'<article class="book-page art-page paper recto" aria-label="Title">'
            f'<div class="title-block"><h2>{year} 骑行纪年</h2>'
            f'<p>{stats["rides"]} 次骑行 · {stats["km"]:,.0f} km · '
            f'累计爬升 {stats["elev"]:,.0f} m</p></div></article>')


def _stats_page(stats: dict) -> str:
    lines = "".join(f"<p><b>{v}</b> {k}</p>" for k, v in stats["lines"])
    return (f'<article class="book-page art-page paper verso" aria-label="Year in numbers">'
            f'<div class="colophon year-stats"><p>年度数字</p>{lines}</div></article>')


def _year_declaration_page(year: str, review: YearReview) -> str:
    return (
        f'<article class="book-page art-page review-page year-declaration recto" '
        f'data-year-review="declaration" aria-label="{year} 年度宣言">'
        f'<p class="review-eyebrow">{year} / YOUR YEAR IN MOTION</p>'
        f'<h2 class="review-distance">{review.distance_km:,.0f}</h2><p class="review-unit">KILOMETRES RIDDEN</p>'
        '<p class="review-statement">这一年，你用两个车轮<br>重新画了一遍城市与山野。</p>'
        '<div class="review-core">'
        f'<span><b>{review.rides}</b>次骑行</span><span><b>{review.moving_hours}h</b>移动时间</span>'
        f'<span><b>{review.elevation_m:,.0f}m</b>累计爬升</span></div></article>'
    )


def _year_rhythm_page(review: YearReview, route: str) -> str:
    peak = max(review.peak_month.distance_km, 1)
    bars = "".join(
        f'<span class="month-bar{" is-peak" if month.month == review.peak_month.month else ""}" '
        f'style="--month-height:{max(4, month.distance_km / peak * 100):.1f}%">'
        f'<i></i><b>{month.month}</b></span>' for month in review.months
    )
    return (
        '<article class="book-page art-page review-page year-rhythm verso" '
        'data-year-review="rhythm" aria-label="年度节奏与纪录">'
        f'<div class="rhythm-route">{route}</div><p class="review-eyebrow">THE RHYTHM OF YOUR YEAR</p>'
        '<h2 class="rhythm-title">越骑越远<br>也越骑越高</h2>'
        f'<div class="month-bars">{bars}</div><div class="rhythm-facts">'
        f'<span><b>{review.peak_month.distance_km:,.0f} km</b>最活跃月份 · {review.peak_month.month}月</span>'
        f'<span><b>{review.longest_ride.distance_km:,.0f} km</b>最长单骑<small>{_esc(_short(review.longest_ride.name, 30))}</small></span>'
        f'<span><b>{review.kudos:,}</b>收到 Kudos</span><span><b>{review.pr_count:,}</b>赛段 PR</span>'
        '</div></article>'
    )


def _heatmap_page(year: str, activities: list[Activity]) -> str:
    routed = [activity for activity in activities if activity.polyline]
    graphic = route_heatmap_svg([activity.polyline for activity in routed])
    if not graphic:
        return ""
    months = len({activity.month_label for activity in routed if activity.month_label})
    distance = sum(activity.distance_km for activity in routed)
    return (
        f'<article class="book-page art-page paper verso annual-heatmap" '
        f'data-annual-heatmap="1" aria-label="{_esc(year)} 年度活动轨迹热力图">'
        '<div class="heatmap-heading"><span>ANNUAL ROUTES</span><h2>年度轨迹</h2></div>'
        f'<div class="heatmap-canvas">{graphic}</div>'
        '<p class="heatmap-note">轨迹已按主要活动区域聚合</p>'
        '<div class="heatmap-summary">'
        f'<span><b>{len(routed)}</b> 次活动</span>'
        f'<span><b>{int(distance + 0.5):,}</b> km</span>'
        f'<span><b>{months}</b> 个活跃月份</span></div></article>'
    )


def _activity_photo_page(side: str, highlight: Highlight, ph, folio: str) -> str:
    a = highlight.activity
    original = f'<span class="photo-note">{_esc(_short(ph.caption, 90))}</span>' if ph.caption else ""
    cap = (f'<figcaption class="bleed-cap"><strong>{_esc(_short(a.name, 64))}</strong>'
           f'<span>{_esc(a.date_label)} · {a.distance_km:.0f} km · 爬升 {a.elev_m:.0f} m</span>'
           f'{original}</figcaption>')
    month = int(a.month_label.removesuffix("月")) if a.month_label else 0
    if ph.landscape:
        figure = (f'<figure class="landscape-split" data-layout="landscape-split" '
                  f'data-image-zone="0,0,100,66" data-copy-zone="0,66,100,34">'
                  f'<img src="{ph.web_path}" alt="{_esc(ph.caption) or "ride photo"}" '
                  f'loading="lazy" decoding="async">{cap}</figure>')
    else:
        figure = (f'<figure class="portrait-full" data-layout="portrait-full" '
                  f'data-overlay="forbid"><img src="{ph.web_path}" loading="lazy" decoding="async" '
                  f'alt="{_esc(ph.caption) or _esc(_short(a.name, 40))}"></figure>')
    return (f'<article class="book-page art-page bleed {side}" data-activity-id="{_esc(a.id)}" '
            f'data-month="{month}" '
            f'aria-label="{_esc(_short(a.name, 40))} photo">'
            f'{figure}'
            f'</article>')


def _companions(avatar: str | None, athlete_count: int) -> str:
    """Companion row: the athlete's own avatar + a "+N" badge for co-riders.

    Strava doesn't expose co-riders' identities, so companions are shown as a
    count, not real faces — only the athlete's own avatar is a real photo.
    """
    if athlete_count <= 1:
        return ""
    others = athlete_count - 1
    me = (f'<img class="avatar" src="{avatar}" alt="rider">' if avatar
          else '<span class="avatar avatar-fallback">你</span>')
    badge = f'<span class="avatar avatar-more">+{others}</span>'
    return (f'<div class="companions"><div class="avatars">{me}{badge}</div>'
            f'<span class="companions-label">与 {others} 位车友同行</span></div>')


def _feature_page(side: str, highlight: Highlight, avatar: str | None = None) -> str:
    a = highlight.activity
    month = int(a.month_label.removesuffix("月")) if a.month_label else 0
    tags = []
    if a.kudos:
        tags.append(f"♥ {a.kudos}")
    if a.pr_count:
        tags.append(f"{a.pr_count} PR")
    tags_html = f'<p class="feat-tags">{" · ".join(tags)}</p>' if tags else ""
    top = sorted([p for p in a.prs if p.get("pr_rank") == 1],
                 key=lambda p: p.get("elapsed_time") or 0)[:4]
    pr_html = ""
    if top:
        items = "".join(f"<li>{_esc(_short(p['name'], 32))} — {_fmt_time(p['elapsed_time'])}</li>" for p in top)
        pr_html = f'<ul class="pr-list">{items}</ul>'
    desc = f'<p class="feat-desc">{_esc(_short(a.description, 180))}</p>' if a.description else ""
    companions = _companions(avatar, a.athlete_count)
    route = route_svg(a.polyline, stroke="#0a0a0a", stroke_width=2.6)
    route_html = f'<div class="feat-route">{route}</div>' if route else ""
    return (f'<article class="book-page art-page paper {side}" data-activity-id="{_esc(a.id)}" '
            f'data-month="{month}" aria-label="{_esc(a.name)[:40]}">'
            f'<div class="feature"><p class="feat-month">{a.date_label}</p>'
            f'<p class="feat-reason">{_esc(highlight.reason)}</p>'
            f'<h3 class="feat-title">{_esc(_short(a.name, 72))}</h3>'
            f'<p class="feat-stats">{a.distance_km:.0f} km · 爬升 {a.elev_m:.0f} m · '
            f'均速 {a.avg_speed_kmh:.1f} km/h · {_fmt_time(a.moving_time)}</p>'
            f'{tags_html}{desc}{companions}{pr_html}</div>{route_html}</article>')


def _colophon(year: str) -> str:
    return (f'<article class="book-page art-page paper recto" aria-label="Colophon">'
            f'<div class="colophon"><p>Strava Photobook · {year}</p>'
            f'<p>由 Strava 骑行数据与照片自动编排。</p>'
            f'<p class="small-print">数据来源：Strava 官方 API。'
            f'照片为原图缩放，未改动源文件。</p></div></article>')


def _theme_picker() -> str:
    options = []
    for index, (theme_id, name, primary, accent) in enumerate(THEME_OPTIONS):
        pressed = "true" if index == 0 else "false"
        options.append(
            f'<button class="theme-option" type="button" data-theme-id="{theme_id}" '
            f'aria-pressed="{pressed}" style="--swatch-primary:{primary};--swatch-accent:{accent}">'
            f'<span class="theme-swatch" aria-hidden="true"></span><span>{name}</span>'
            f'<span class="theme-check" aria-hidden="true">✓</span></button>'
        )
    return (
        '<div class="theme-picker">'
        '<button id="theme-toggle" class="theme-toggle" type="button" aria-expanded="false" '
        'aria-controls="theme-popover"><span class="current-swatch" aria-hidden="true"></span>'
        '<span>主题</span></button>'
        '<div id="theme-popover" class="theme-popover" role="dialog" aria-label="选择画册主题" hidden>'
        '<div class="theme-popover-head"><strong>画册主题</strong><span>19 种</span></div>'
        '<div class="theme-options">' + "".join(options) + '</div></div></div>'
    )


def _theme_restore_script() -> str:
    themes = ",".join(f'"{item[0]}":["{item[2]}","{item[3]}"]' for item in THEME_OPTIONS)
    return ("<script>(function(){try{var k='strava-photobook.theme',v=localStorage.getItem(k),"
            f"t={{ {themes} }};if(t[v]){{var r=document.documentElement,c=t[v];r.dataset.theme=v;"
            "r.style.setProperty('--theme-primary',c[0]);r.style.setProperty('--theme-accent',c[1]);"
            "}}}catch(e){}})();</script>")


def _month_timeline(body: str) -> str:
    months = sorted({int(value) for value in __import__("re").findall(r'data-month="(\d+)"', body)})
    buttons = "".join(
        f'<button class="month-jump" type="button" data-month="{month}" '
        f'aria-label="跳到 {month} 月" aria-controls="book"><span>{month}</span><b>月</b></button>'
        for month in months
    )
    return f'<nav id="month-timeline" class="month-timeline" aria-label="按月份浏览">{buttons}</nav>'


def _document(year: str, body: str, *, photo_target: int = 0) -> str:
    target_attr = f' data-photo-target="{photo_target}"' if photo_target else ""
    return f"""<!doctype html>
<html lang="zh-CN" data-strava-photobook="1"{target_attr}>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Strava Photobook {year}</title>
  {_theme_restore_script()}
  <link rel="stylesheet" href="styles.css">
  <link rel="stylesheet" href="theme.css">
</head>
<body>
<main class="room">
  <section class="stage" aria-label="Interactive photo book">
    <div class="book-rig">
      <div class="book-theme-overlay" data-no-page-click>{_theme_picker()}</div>
      <div id="book" class="book" data-page-width="{PAGE_W}" data-page-height="{PAGE_H}">
        {body}
      </div>
    </div>
  </section>
  <footer class="controls" aria-label="Book controls">
    <button id="previous" type="button" aria-label="Previous page">←</button>
    <div class="control-center">{_month_timeline(body)}
      <div class="status" aria-live="polite"><span id="page-status">Cover</span><small>点击左右、拖动或方向键翻页</small></div>
    </div>
    <button id="next" type="button" aria-label="Next page">→</button>
  </footer>
</main>
<script src="vendor/page-flip.browser.js"></script>
<script type="module" src="theme-catalog.js"></script>
<script type="module" src="month-timeline.js"></script>
<script type="module" src="flipbook.js"></script>
</body>
</html>
"""


def _copy_runtime(cfg: Config, out: Path) -> Path:
    """Copy the shared runtime into the book dir; return the photos dir."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for item in cfg.runtime_dir.iterdir():
        if item.name == "index.html":
            continue
        dst = out / item.name
        if item.is_dir():
            shutil.copytree(item, dst)
        else:
            shutil.copy2(item, dst)
    # append feature layout to the copied book-style.css (theme.css handles look)
    bs = out / "style" / "book-style.css"
    if bs.is_file() and "strava-photobook feature-page additions" not in bs.read_text("utf-8"):
        bs.write_text(bs.read_text("utf-8") + FEATURE_CSS, encoding="utf-8")
    (out / "theme.css").write_text(THEME_CSS, encoding="utf-8")
    photos = out / "assets" / "photos"
    photos.mkdir(parents=True, exist_ok=True)
    return photos


def _stats(acts: list[Activity]) -> dict:
    total_km = sum(a.distance_km for a in acts)
    total_elev = sum(a.elev_m for a in acts)
    total_time = sum(a.moving_time for a in acts)
    total_kudos = sum(a.kudos for a in acts)
    total_pr = sum(a.pr_count for a in acts)
    longest = max(acts, key=lambda a: a.distance_km)
    return {
        "rides": len(acts), "km": total_km, "elev": total_elev,
        "lines": [
            ("次骑行", f"{len(acts)}"),
            ("公里", f"{total_km:,.0f}"),
            ("米累计爬升", f"{total_elev:,.0f}"),
            ("小时在车上", f"{total_time/3600:,.0f}"),
            ("次收藏（kudos）", f"{total_kudos:,}"),
            ("个赛段 PR", f"{total_pr:,}"),
            (f"km 最长单骑（{_esc(longest.name)}）", f"{longest.distance_km:.0f}"),
        ],
    }


def _chronological_activity_blocks(
    featured: list[Highlight], gallery: list[Highlight]
) -> list[tuple[Highlight, bool]]:
    """Merge selected activities into one date-ordered, de-duplicated timeline."""
    blocks: dict[str, tuple[Highlight, bool]] = {}
    for highlight in gallery:
        blocks.setdefault(highlight.activity.id, (highlight, False))
    for highlight in featured:
        blocks[highlight.activity.id] = (highlight, True)
    return sorted(
        blocks.values(),
        key=lambda item: (item[0].activity.date, item[0].activity.id),
    )


def _frame_pages(
    year: str, stats: dict, activity_pages: list[str], activities: list[Activity] | None = None,
    selection: CoverSelection | None = None,
) -> list[str]:
    """Wrap meaningful content with covers without inserting blank leaves."""
    year_activities = activities or []
    if year_activities:
        review = build_year_review(year_activities)
    else:
        placeholder = Activity(id="review", name="Ride", date=f"{year}-01-01T00:00:00Z", year=year,
                               distance_km=stats.get("km", 0), elev_m=stats.get("elev", 0))
        review = build_year_review([placeholder])
    route = route_heatmap_svg([activity.polyline for activity in year_activities if activity.polyline])
    pages = [
        _cover(year, review, selection, route),
        _year_declaration_page(year, review),
        _year_rhythm_page(review, route),
    ]
    heatmap = _heatmap_page(year, year_activities)
    if heatmap:
        pages.append(heatmap)
    pages.extend([*activity_pages, _colophon(year), _back(year)])
    return pages


def build_year(cfg: Config, year: str, activities: list[Activity], hydrate,
               avatar_fetcher=None) -> Path:
    """Build the book for `year`. `hydrate(act, photos_dir, remaining)` fills photos+PRs.

    `avatar_fetcher(photos_dir) -> web_path | None` downloads the athlete's own
    photo (companions can't be resolved from the API, so group rides show the
    athlete + an "+N" badge).
    """
    ya = by_year(activities).get(year, [])
    if not ya:
        raise SystemExit(f"没有 {year} 的活动数据")
    out = cfg.book_dir(year)
    photos_dir = _copy_runtime(cfg, out)
    avatar = avatar_fetcher(photos_dir) if avatar_fetcher else None
    stats = _stats(ya)

    # 动态目标：跟随当年上传照片数增长，受下限/上限护栏约束；显式固定值优先。
    total_photos = sum(a.photo_count for a in ya)
    target = cfg.photos_per_book or target_photo_count(
        total_photos, ratio=cfg.photo_ratio, floor=cfg.photo_floor, cap=cfg.photo_cap
    )

    # 候选活动要足以承载目标张数，同时封顶以尊重 Strava 限流预算。
    reserve = cfg.feature_rides * cfg.max_photos_per_ride
    needed = cfg.feature_rides + max(0, math.ceil((target - reserve) / GALLERY_PHOTO_QUOTA))
    candidate_limit = min(MAX_CANDIDATE_RIDES, max(24, needed))
    candidates = sorted(
        ya, key=lambda a: (a.photo_count > 0, a.kudos, a.pr_count), reverse=True
    )[:candidate_limit]

    # 第一轮：拉详情（让描述/同行/PR 进入评分），照片先取画廊基础配额。
    for a in candidates:
        hydrate(a, photos_dir, min(GALLERY_PHOTO_QUOTA, a.photo_count))
    highlights = select_editorial_highlights(candidates, cfg.feature_rides)
    featured_ids = {highlight.activity.id for highlight in highlights}
    gallery = select_editorial_highlights(
        [x for x in candidates if x.id not in featured_ids], len(candidates)
    )
    ordered = [highlight.activity for highlight in highlights] + [
        highlight.activity for highlight in gallery
        if highlight.activity.id not in featured_ids
    ]
    # 高光加权分配：feature 起步更多，剩余名额再按精彩度逐张补足。
    quotas = plan_photo_quotas(
        ordered, featured_ids, target,
        feature_quota=FEATURE_PHOTO_QUOTA, gallery_quota=GALLERY_PHOTO_QUOTA,
        per_ride_cap=cfg.max_photos_per_ride,
    )
    # 第二轮：仅对需要超出基础配额的活动增量补片，不重复拉详情。
    for a in ordered:
        want = quotas.get(a.id, 0)
        if want > len(a.photos):
            hydrate(a, photos_dir, want, False)

    # 海报封面复用候选池里得分最高的一张。封面固定占用一个名额：正文只取
    # target-1 张且跳过封面那张，保证整本书 unique 照片数恰为 target，也不会
    # 因为封面活动在时间序上靠后（正文提前截断）而让封面变成"第 target+1 张"。
    cover = select_cover(candidates)
    cover_src = cover.photo.web_path if cover else None
    body_target = target - (1 if cover_src else 0)

    activity_pages: list[str] = []

    side = ["recto", "verso"]
    used = 0
    for highlight, is_featured in _chronological_activity_blocks(highlights, gallery):
        a = highlight.activity
        if is_featured:
            activity_pages.append(_feature_page(side[len(activity_pages) % 2], highlight, avatar))
        for ph in a.photos[: quotas.get(a.id, 0)]:
            if ph.web_path == cover_src:
                continue
            if used >= body_target:
                break
            activity_pages.append(_activity_photo_page(side[len(activity_pages) % 2], highlight, ph, str(used + 1)))
            used += 1
        if used >= body_target:
            break

    # 计划产出（已扣除活动自身照片数与候选池上限），作为发布门禁的达成目标。
    planned_target = min(target, sum(quotas.values()))
    # 封面占一个名额：全书唯一照片 = 正文照片页 + 封面海报（路线封面时无封面照片）。
    unique_photos = used + (1 if cover_src else 0)
    pages = _frame_pages(year, stats, activity_pages, ya, cover)
    (out / "index.html").write_text(
        _document(year, "\n        ".join(pages), photo_target=planned_target),
        encoding="utf-8",
    )
    print(
        f"built {out}  pages={len(pages)} photos={unique_photos}/{planned_target} "
        f"uploads={total_photos}"
    )
    return out
