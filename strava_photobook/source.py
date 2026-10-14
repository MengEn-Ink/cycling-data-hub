"""API 数据源：完全从 Strava 构建活动列表与照片。

`fetch_activities` 一次性拉取全部概要（很省）并缓存到 data/activities.json。
`hydrate_activity` 再针对入册的骑行下载原图、并通过活动详情接口取赛段 PR——
只对真正进画册的骑行发起，以尊重限流。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image, ImageOps

from .config import Config
from .model import Activity, Photo, clean_description, year_of
from .strava.client import StravaClient

# summary fields we keep in the cache
_KEEP = (
    "id", "name", "start_date_local", "type", "sport_type", "distance",
    "moving_time", "total_elevation_gain", "average_speed", "kudos_count",
    "comment_count", "athlete_count", "pr_count", "achievement_count",
    "total_photo_count", "photo_count",
)


def _client(cfg: Config) -> StravaClient:
    s = cfg.strava
    if not s.ready:
        raise SystemExit("Strava 未配置：请先 `python -m strava_photobook auth` 或填好 .env")
    return StravaClient(s.client_id, s.client_secret, s.refresh_token, cfg.token_cache)


def fetch_activities(
    cfg: Config, year: str | None = None, *, client: StravaClient | None = None
) -> list[dict]:
    """Pull every activity summary and cache it. Returns the raw records."""
    from datetime import datetime, timezone

    cfg.ensure_dirs()
    client = client or _client(cfg)
    bounds = {}
    if year:
        start = datetime(int(year), 1, 1, tzinfo=timezone.utc)
        end = datetime(int(year) + 1, 1, 1, tzinfo=timezone.utc)
        bounds = {"after": int(start.timestamp()), "before": int(end.timestamp())}
    out: list[dict] = []
    for a in client.iter_activities(pause=cfg.request_pause, **bounds):
        rec = {k: a.get(k) for k in _KEEP}
        rec["summary_polyline"] = (a.get("map") or {}).get("summary_polyline") or ""
        out.append(rec)
    if year and cfg.summaries_path.is_file():
        previous = json.loads(cfg.summaries_path.read_text(encoding="utf-8"))
        out = [record for record in previous if not str(record.get("start_date_local") or "").startswith(year)] + out
    cfg.summaries_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def load_activities(cfg: Config) -> list[Activity]:
    """Read cached summaries into Activity objects (no network)."""
    path = cfg.summaries_path
    if not path.is_file():
        raise SystemExit(f"没有活动缓存 {path}，请先运行 `python -m strava_photobook fetch`")
    data = json.loads(path.read_text(encoding="utf-8"))
    acts: list[Activity] = []
    for s in data:
        date = s.get("start_date_local") or ""
        acts.append(
            Activity(
                id=str(s["id"]),
                name=(s.get("name") or "").strip(),
                date=date,
                year=year_of(date),
                kudos=int(s.get("kudos_count") or 0),
                pr_count=int(s.get("pr_count") or 0),
                athlete_count=int(s.get("athlete_count") or 1),
                distance_km=round((s.get("distance") or 0) / 1000, 1),
                elev_m=round(s.get("total_elevation_gain") or 0),
                avg_speed_kmh=round((s.get("average_speed") or 0) * 3.6, 1),
                moving_time=int(s.get("moving_time") or 0),
                polyline=s.get("summary_polyline") or "",
                photo_count=int(s.get("total_photo_count") or 0),
                meta=s,
            )
        )
    return acts


def _save_photo(raw: bytes, dest: Path, max_edge: int) -> bool | None:
    """Return True=landscape, False=portrait, None=failed."""
    try:
        from io import BytesIO

        with Image.open(BytesIO(raw)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            landscape = im.width >= im.height * 1.15
            im.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            dest.parent.mkdir(parents=True, exist_ok=True)
            im.save(dest, quality=88, subsampling=0)
            return landscape
    except Exception:  # noqa: BLE001
        return None


def _cached_photos(cfg: Config, act: Activity, photos_dir: Path, limit: int,
                   *, have: set[str] | None = None) -> list[Photo]:
    """Copy cached photos until the activity reaches `limit`, skipping `have`."""
    have = have or set()
    base = len(have)  # photos already attached before this top-up call
    cached: list[Photo] = []
    for source in sorted((cfg.data_dir / "photo-cache").glob(f"{act.id}-*.jpg")):
        if base + len(cached) >= limit:
            break
        if source.name in have:
            continue
        dest = photos_dir / source.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        try:
            with Image.open(source) as image:
                landscape = image.width >= image.height * 1.15
        except Exception:  # noqa: BLE001
            continue
        photo = Photo(f"assets/photos/{source.name}", landscape=landscape)
        cached.append(photo)
        have.add(source.name)
    return cached


def hydrate_activity(cfg: Config, client: StravaClient, act: Activity,
                     photos_dir: Path, max_photos: int, *, with_detail: bool = True) -> None:
    """Download an activity's photos, pull PR segments and refresh companions.

    The summary list often reports athlete_count=1 even for group rides; the
    real value (and the full description) live in the activity detail, so we
    fetch detail for rides that have PRs or photos and correct it in place.

    Idempotent / re-entrant: callers can hydrate a base quota first and later
    raise `max_photos`. Photos already attached (by index name) are never
    downloaded or appended twice. Pass with_detail=False on those top-up calls
    to avoid a redundant activity-detail request.
    """
    act.description = clean_description(act.meta.get("description") or "")
    if with_detail and (act.pr_count > 0 or act.photo_count > 0):
        try:
            detail = client.activity_detail(act.id)
            act.description = act.description or clean_description(
                detail.get("description") or ""
            )
            # summary athlete_count is unreliable; trust the detail value
            ac = detail.get("athlete_count")
            if isinstance(ac, int) and ac > act.athlete_count:
                act.athlete_count = ac
            act.prs = [
                {"name": e.get("name"), "elapsed_time": e.get("elapsed_time"),
                 "pr_rank": e.get("pr_rank")}
                for e in (detail.get("segment_efforts") or [])
                if e.get("pr_rank")
            ]
        except Exception:  # noqa: BLE001
            pass
    # photos — re-entrant: skip indexes already attached, fill up to max_photos
    if act.photo_count > 0 and max_photos > 0:
        have = {Path(p.web_path).name for p in act.photos}
        try:
            objs = client.activity_photos(act.id, size=cfg.max_photo_edge)
        except Exception:  # noqa: BLE001
            objs = []
        import requests

        for i, obj in enumerate(objs[:max_photos]):
            if len(act.photos) >= max_photos:
                break
            name = f"{act.id}-{i:02d}.jpg"
            if name in have:
                continue
            urls = obj.get("urls") or {}
            url = urls.get(str(cfg.max_photo_edge)) or (list(urls.values())[0] if urls else None)
            if not url:
                continue
            try:
                resp = requests.get(url, timeout=30)
                if resp.status_code != 200:
                    continue
            except requests.RequestException:
                continue
            landscape = _save_photo(resp.content, photos_dir / name, cfg.max_photo_edge)
            if landscape is None:
                continue
            act.photos.append(
                Photo(
                    web_path=f"assets/photos/{name}",
                    caption=(obj.get("caption") or "").strip(),
                    landscape=landscape,
                )
            )
            have.add(name)
            cache = cfg.data_dir / "photo-cache" / name
            cache.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(photos_dir / name, cache)
        if len(act.photos) < max_photos:
            act.photos.extend(
                _cached_photos(cfg, act, photos_dir, max_photos, have=have)
            )


def make_client(cfg: Config) -> StravaClient:
    return _client(cfg)


def fetch_athlete_avatar(client: StravaClient, dest_dir: Path) -> str | None:
    """下载本人头像到画册；返回相对 web 路径，失败则 None。

    Strava 只公开授权运动员本人的头像（profile / profile_medium）；同行人身份
    不对外暴露，故同行只能以人数徽章表示。
    """
    try:
        me = client.athlete()
    except Exception:  # noqa: BLE001
        return None
    url = me.get("profile") or me.get("profile_medium") or ""
    if not url or url.endswith("/avatar/athlete/large.png"):
        return None  # 默认占位头像，视作没有
    dest = dest_dir / "athlete.jpg"
    if not client.download(url, dest):
        return None
    return "assets/photos/athlete.jpg"
