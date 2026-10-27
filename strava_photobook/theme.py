"""画册样式：介绍页布局补充 + Distance Manifesto 固定主题。

`FEATURE_CSS` 追加到运行时的 book-style.css（介绍页布局、满屏/留边照片、轨迹图形）。
`THEME_CSS` 写成独立的 theme.css 并最后加载，统一暗色书页、暖白文字与锈橙视觉。
"""
from __future__ import annotations

# Layout additions the runtime doesn't ship (feature pages, bleed photos, route).
FEATURE_CSS = """
/* strava-photobook feature-page additions */
/* text flows in a left column; the route glyph owns the bottom-right corner,
   so the two never share an x-band and cannot overlap regardless of length. */
.art-page .feature{position:absolute;left:10%;right:34%;top:11%;bottom:9%;overflow:hidden;display:flex;flex-direction:column}
.art-page .feat-month{margin:0 0 3cqw}
.art-page .feat-title{margin:0 0 3.5cqw}
.art-page .feat-stats{margin:0 0 2cqw}
.art-page .feat-tags{margin:0 0 4cqw}
.art-page .feat-desc{margin:0 0 4cqw}
.art-page .feat-title,.art-page .feat-desc,.art-page .photo-note{display:-webkit-box;-webkit-box-orient:vertical;overflow:hidden}
.art-page .feat-title{-webkit-line-clamp:3}
.art-page .feat-desc{-webkit-line-clamp:5}
.art-page .pr-list{list-style:none;padding:0;margin:0;padding-top:3cqw}
.art-page .pr-list li{display:flex;justify-content:space-between;gap:2cqw}
.art-page .pr-list li::before{align-self:center}
/* portrait photos are full-screen; landscape photos use a separate copy band */
.art-page.bleed{background:#0A0807}
.art-page .portrait-full{position:absolute;inset:0;margin:0;overflow:hidden;background:#0A0807}
.art-page .portrait-full img{width:100%;height:100%;object-fit:cover;object-position:center}
.art-page .landscape-split{position:absolute;inset:0;margin:0;overflow:hidden;background:var(--theme-paper)}
.art-page .landscape-split img{position:absolute;left:0;top:0;width:100%;height:66%;object-fit:contain;object-position:center;background:#0A0807}
.art-page .landscape-split .bleed-cap{position:absolute;left:0;right:0;bottom:0;height:34%;box-sizing:border-box;overflow:hidden;margin:0;padding:5cqw 7%;color:var(--theme-accent-ink);background:var(--theme-primary);display:flex;flex-direction:column;justify-content:center;gap:1.2cqw}
.art-page .bleed-cap strong{font:700 4.2cqw/1.05 var(--book-sans);letter-spacing:-.01em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.art-page .bleed-cap>span{font:600 1.9cqw/1.35 var(--book-sans);letter-spacing:.08em;text-transform:uppercase}
.art-page .bleed-cap .photo-note{-webkit-line-clamp:2;text-transform:none;letter-spacing:.02em;font-weight:500}
.art-page .feat-route{position:absolute;right:8%;bottom:11%;width:25%;opacity:1}
.art-page .feat-route .route{width:100%;height:auto;display:block}
/* companions row: athlete avatar + "+N" badge */
.art-page .companions{display:flex;align-items:center;gap:2.5cqw;margin:0 0 4cqw}
.art-page .companions .avatars{display:flex}
.art-page .companions .avatar{width:7cqw;height:7cqw;border-radius:50%;object-fit:cover;display:flex;align-items:center;justify-content:center;flex:none}
.art-page .companions .avatar + .avatar{margin-left:-2.2cqw}
/* --- portrait / single-page (phones) --- */
/* The leaf shows alone, so give text more width for readability while keeping
   the same non-overlap invariant: text's right edge (70%) stays left of the
   route column's left edge (71%). Slightly larger type for small screens. */
.book[data-layout="portrait"] .art-page .feature{left:9%;right:30%;top:9%;bottom:8%}
.book[data-layout="portrait"] .art-page .feat-route{right:5%;bottom:8%;width:24%}
"""

# Distance Manifesto: dark room and pages, warm-white copy, rust-orange focus.
THEME_CSS = """
/* ===== Strava Photobook · Distance Manifesto ===== */
:root{
  color-scheme:dark;
  --theme-primary:#0A0807;--theme-accent:#F05523;--theme-accent-ink:#F4E8D8;
  --theme-paper:#15100D;--paper:#15100D;--ink:#F4E8D8;--cloth:#0A0807;
  --theme-page-alt:#211711;--theme-muted:#AA998C;--theme-line:#58463A;
  --book-serif:"Bodoni 72","Songti SC","STSong",serif;
  --book-sans:"Avenir Next","PingFang SC","Hiragino Sans GB",Arial,sans-serif;
}
html[data-theme="distance-manifesto"],
html[data-theme="distance-manifesto"] body,
html[data-theme="distance-manifesto"] .room{background:#0A0807;color:#F4E8D8}
html[data-theme="distance-manifesto"] .art-page{background:#15100D!important;color:#F4E8D8}
html[data-theme="distance-manifesto"] .art-page.endpaper{background:#211711!important}
html[data-theme="distance-manifesto"] .art-page.cloth{background:#0A0807!important;color:#F4E8D8}
html[data-theme="distance-manifesto"] .art-page.year-declaration{background:#0A0807!important;color:#F4E8D8}
.book{filter:drop-shadow(0 18px 38px rgb(0 0 0 / 52%))}
.book-header h1{font:600 18px/1.2 var(--book-sans);letter-spacing:.14em;text-transform:uppercase}
.book-header a,.book-header span{font:500 10px/1.4 var(--book-sans);letter-spacing:.18em;text-transform:uppercase;color:var(--theme-muted)}
.controls>button{border:1px solid var(--theme-line);border-radius:0;background:#17110E;color:#F4E8D8}
.controls>button:hover:not(:disabled){border-color:var(--theme-accent);background:var(--theme-page-alt);color:#F4E8D8}
.month-timeline::before{background:var(--theme-line)}
.month-jump{color:var(--theme-muted)}
.month-jump::before{border-color:var(--theme-primary);background:var(--theme-line)}
.month-jump[aria-current="true"]{color:#F4E8D8}
.month-jump[aria-current="true"]::before{background:var(--theme-accent)}
.status span{font:600 10px/1.4 var(--book-sans);letter-spacing:.22em;text-transform:uppercase;color:#F4E8D8}
.status small{font:500 9px/1.4 var(--book-sans);letter-spacing:.12em;text-transform:uppercase;color:var(--theme-muted)}
.art-page .cover-title{font:700 20cqw/.9 var(--book-sans);letter-spacing:-.02em;text-shadow:none;color:#F4E8D8}
.art-page .cover-subtitle{font:600 2.4cqw/1.4 var(--book-sans);letter-spacing:.28em;text-transform:uppercase;color:var(--theme-muted)}
.art-page .back-mark{font:600 2.6cqw/1.4 var(--book-sans);letter-spacing:.24em;text-transform:uppercase;color:#F4E8D8}
.art-page .title-block{top:22%}
.art-page .title-block h2{margin:0 0 5cqw;color:#F4E8D8;font:700 8.5cqw/1.16 var(--book-sans);letter-spacing:-.015em;text-transform:none}
.art-page .title-block p{color:var(--theme-muted);font:500 2.6cqw/1.5 var(--book-sans);letter-spacing:.04em}
.art-page .colophon{font:500 2.6cqw/1.55 var(--book-sans)}
.art-page .colophon p{margin:0 0 4cqw}
.art-page .colophon p b{font-weight:700;font-size:1.5em}
.art-page .year-stats{top:15%;max-height:76%;overflow:hidden}
.art-page .year-stats p{margin:0 0 2.6cqw}
.art-page .year-stats p:first-child{margin-bottom:4cqw}
.art-page .colophon .small-print{font:500 1.8cqw/1.6 var(--book-sans);color:var(--theme-muted)}
.art-page .feat-month{font:600 2.2cqw/1 var(--book-sans);letter-spacing:.28em;color:var(--theme-accent);text-transform:uppercase}
.art-page .feat-reason{align-self:flex-start;margin:0 0 3cqw;padding:.8cqw 1.4cqw;background:var(--theme-accent);color:#0A0807;font:700 1.6cqw/1 var(--book-sans);letter-spacing:.12em;text-transform:uppercase}
.art-page .feat-title{color:#F4E8D8;font:700 7.2cqw/1.16 var(--book-sans);letter-spacing:-.015em;text-transform:none}
.art-page .feat-stats{font:500 2.5cqw/1.5 var(--book-sans);letter-spacing:.02em;color:#F4E8D8}
.art-page .feat-tags{font:600 2.6cqw/1.4 var(--book-sans);letter-spacing:.06em;color:var(--theme-muted);text-transform:uppercase}
.art-page .feat-desc{font:500 2.6cqw/1.48 var(--book-sans);color:var(--theme-muted)}
.art-page .companions .avatar{border:.4cqw solid #15100D;box-shadow:0 0 0 .4cqw var(--theme-line)}
.art-page .companions .avatar-fallback,.art-page .companions .avatar-more{background:var(--theme-page-alt);color:#F4E8D8;font:600 2.4cqw/1 var(--book-sans);letter-spacing:.02em}
.art-page .companions-label{font:600 2.4cqw/1.3 var(--book-sans);letter-spacing:.06em;color:var(--theme-muted);text-transform:uppercase}
.art-page .pr-list{border-top:1px solid var(--theme-line)}
.art-page .pr-list li{font:500 2.3cqw/1.7 var(--book-sans);color:#F4E8D8}
.art-page .pr-list li::before{content:"PR";font:600 1.6cqw var(--book-sans);letter-spacing:.1em;color:var(--theme-accent)}
.art-page .feat-route .route path{stroke:#AA998C}
.art-page .feat-route .route circle{fill:var(--theme-accent)}
.art-page .bleed-cap{font:600 2.2cqw/1.35 var(--book-sans);letter-spacing:.14em;text-transform:uppercase}
.art-page .landscape-split .bleed-cap{border-top:.5cqw solid #F05523;background:#0A0807;color:#F4E8D8}
.art-page .bleed-cap strong{line-height:1.18;letter-spacing:-.01em;text-transform:none}
.art-page .bleed-cap>span{color:var(--theme-muted)}
.art-page.annual-heatmap{overflow:hidden;background:#15100D!important}
.art-page .heatmap-heading{position:absolute;left:9%;right:9%;top:8%;z-index:2}
.art-page .heatmap-heading span{font:700 1.7cqw/1 var(--book-sans);letter-spacing:.28em;color:var(--theme-accent)}
.art-page .heatmap-heading h2{margin:1.4cqw 0 0;color:#F4E8D8;font:700 6.4cqw/1.16 var(--book-sans);letter-spacing:-.015em}
.art-page .heatmap-canvas{position:absolute;left:7%;right:7%;top:23%;bottom:20%;overflow:hidden}
.art-page .route-heatmap{display:block;width:100%;height:100%;filter:drop-shadow(0 0 1.8cqw color-mix(in srgb,var(--theme-accent) 42%,transparent))}
.art-page .heat-route{fill:none;stroke-linecap:round;stroke-linejoin:round}
.art-page .heat-route.base{stroke:#F4E8D8;stroke-width:1.8;opacity:.14}
.art-page .heat-route.hot{stroke:var(--theme-accent);stroke-width:.62;opacity:.7;mix-blend-mode:screen}
.art-page .heatmap-note{position:absolute;left:9%;bottom:17%;margin:0;font:500 1.35cqw/1 var(--book-sans);letter-spacing:.12em;color:var(--theme-muted);text-transform:uppercase}
.art-page .heatmap-summary{position:absolute;left:9%;right:9%;bottom:7%;display:grid;grid-template-columns:repeat(3,1fr);gap:2cqw;border-top:1px solid var(--theme-line);padding-top:3cqw;overflow:hidden}
.art-page .heatmap-summary span{font:600 1.65cqw/1.3 var(--book-sans);letter-spacing:.06em;color:var(--theme-muted);white-space:nowrap}
.art-page .heatmap-summary b{display:block;margin-bottom:.7cqw;font:700 3.2cqw/1 var(--book-sans);letter-spacing:-.02em}
.art-page.poster-cover{overflow:hidden;background:var(--theme-primary)!important;color:var(--theme-accent-ink)}
.art-page .cover-photo{position:absolute;left:0;right:0;top:0;height:64%;overflow:hidden}
.art-page .cover-photo img{width:100%;height:100%;object-fit:cover}
.art-page .cover-copy{position:absolute;left:0;right:0;bottom:0;height:36%;overflow:hidden;background:var(--theme-primary);color:var(--theme-accent-ink)}
.art-page .cover-year{position:absolute;left:6%;top:8%;font:900 9.5cqw/.85 var(--book-sans);letter-spacing:-.06em;color:var(--theme-accent)}
.art-page .cover-kicker{position:absolute;left:7%;top:37%;margin:0;font:800 1.6cqw/1 var(--book-sans);letter-spacing:.2em;color:var(--theme-accent);text-transform:uppercase}
.art-page .cover-story{position:absolute;left:7%;right:7%;top:48%;margin:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;font:800 4.1cqw/1.05 var(--book-sans);color:var(--theme-accent-ink)}
.art-page .cover-index{position:absolute;left:7%;right:7%;bottom:9%;display:flex;justify-content:space-between;border-top:1px solid color-mix(in srgb,var(--theme-accent) 65%,transparent);padding-top:2cqw;font:700 1.45cqw/1 var(--book-sans);letter-spacing:.08em;color:var(--theme-accent)}
.art-page .cover-route{position:absolute;inset:14% 10% 28%;opacity:.58}
.art-page .cover-route .route-heatmap{width:100%;height:100%}
.art-page.review-page{overflow:hidden}
.art-page.year-declaration{background:var(--theme-primary)!important;color:var(--theme-accent-ink)}
.art-page .review-eyebrow{position:absolute;left:8%;right:8%;top:7%;margin:0;font:800 1.55cqw/1 var(--book-sans);letter-spacing:.23em;color:var(--theme-accent)}
.art-page .review-distance{position:absolute;left:8%;top:18%;margin:0;font:900 16cqw/.8 var(--book-sans);letter-spacing:-.08em}
.art-page .review-unit{position:absolute;left:8%;top:34%;margin:0;font:800 2.3cqw/1 var(--book-sans);letter-spacing:.16em}
.art-page .review-statement{position:absolute;left:8%;right:10%;top:48%;margin:0;font:800 4.6cqw/1.12 var(--book-sans)}
.art-page .review-core{position:absolute;left:8%;right:8%;bottom:8%;display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid color-mix(in srgb,var(--theme-accent-ink) 35%,transparent);padding-top:3cqw}
.art-page .review-core span{font:600 1.5cqw/1.4 var(--book-sans)}
.art-page .review-core b{display:block;font-size:3.7cqw}
.art-page.year-rhythm{background:#15100D!important;color:#F4E8D8}
.art-page .rhythm-title{position:absolute;left:8%;right:8%;top:10%;margin:0;color:#F4E8D8;font:900 6.6cqw/1.16 var(--book-sans);letter-spacing:-.015em}
.art-page .rhythm-route{position:absolute;right:-4%;top:2%;width:45%;height:40%;opacity:.16}
.art-page .rhythm-route .route-heatmap{width:100%;height:100%}
.art-page .month-bars{position:absolute;left:8%;right:8%;top:28%;height:28%;display:flex;align-items:end;gap:1.2cqw;border-bottom:1px solid var(--theme-line);overflow:hidden}
.art-page .month-bar{display:flex;flex:1;height:100%;align-items:end;justify-content:center;position:relative}
.art-page .month-bar i{display:block;width:100%;height:var(--month-height);background:#58463A}
.art-page .month-bar.is-peak i{background:var(--theme-accent)}
.art-page .month-bar b{position:absolute;bottom:1cqw;font:700 1.4cqw/1 var(--book-sans);color:#F4E8D8;text-shadow:0 1px 2px #0A0807}
.art-page .month-bar.is-peak b{color:#0A0807;text-shadow:none}
.art-page .rhythm-facts{position:absolute;left:8%;right:8%;bottom:7%;display:grid;grid-template-columns:1fr 1fr;gap:3cqw 4cqw}
.art-page .rhythm-facts span{min-width:0;border-top:.5cqw solid #F05523;padding-top:1.5cqw;font:600 1.6cqw/1.3 var(--book-sans)}
.art-page .rhythm-facts b{display:block;font:900 4cqw/1 var(--book-sans);white-space:nowrap}
.art-page .rhythm-facts small{display:block;overflow:hidden;margin-top:.7cqw;color:var(--theme-muted);white-space:nowrap;text-overflow:ellipsis}
.art-page .review-statement{line-height:1.16;letter-spacing:-.015em;text-transform:none}
.art-page .cover-year{letter-spacing:-.04em}
.art-page .cover-story{letter-spacing:-.01em;text-transform:none}
"""
