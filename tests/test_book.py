import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from strava_photobook import book
from strava_photobook.book import (
    _activity_photo_page, _cover, _document, _feature_page, _frame_pages, _heatmap_page,
    _year_declaration_page, _year_rhythm_page,
)
from strava_photobook.config import Config, GitHubConfig, StravaCreds
from strava_photobook.editorial import CoverSelection, build_year_review
from strava_photobook.model import Activity, Highlight, Photo

BLEED_PAGE = re.compile(
    r'class="book-page art-page bleed (?:recto|verso)" data-activity-id="([^"]+)"'
)
PHOTO_TARGET = re.compile(r'data-photo-target="(\d+)"')
POLYLINE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"


class DynamicBuildTests(unittest.TestCase):
    def _build(self, n=30, per=10, **cfg_overrides):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        runtime = root / "runtime"
        runtime.mkdir()
        cfg = Config(
            root, root / "data", root / "books", runtime,
            StravaCreds(), GitHubConfig(), **cfg_overrides,
        )
        activities = [
            Activity(
                id=str(1000 + i), name=f"Ride {i}",
                date=f"2026-{((i % 12) + 1):02d}-{(i % 27) + 1:02d}T08:00:00Z",
                year="2026", kudos=i, distance_km=20 + i, elev_m=100 + i,
                moving_time=3600, photo_count=per, polyline=POLYLINE,
                description="story" if i % 3 == 0 else "",
            )
            for i in range(n)
        ]

        def fake_hydrate(act, photos_dir, limit, with_detail=True):
            want = min(limit, act.photo_count)
            while len(act.photos) < want:
                k = len(act.photos)
                act.photos.append(Photo(f"assets/photos/{act.id}-{k:02d}.jpg", landscape=(k % 2 == 1)))

        out = book.build_year(cfg, "2026", activities, fake_hydrate)
        return (out / "index.html").read_text(encoding="utf-8")

    def test_rich_year_grows_up_to_cap_without_flooding_one_ride(self):
        html = self._build(n=30, per=10)  # 300 uploads -> 60% capped at 120

        per_activity = Counter(BLEED_PAGE.findall(html))
        self.assertEqual(sum(per_activity.values()), 120)
        self.assertEqual(PHOTO_TARGET.search(html).group(1), "120")
        self.assertTrue(all(count <= 6 for count in per_activity.values()))
        self.assertGreaterEqual(len(per_activity), 20)  # spread across many rides

    def test_explicit_override_pins_the_count(self):
        html = self._build(photos_per_book=10)

        self.assertEqual(len(BLEED_PAGE.findall(html)), 10)
        self.assertEqual(PHOTO_TARGET.search(html).group(1), "10")

    def test_sparse_year_is_not_inflated_to_the_floor(self):
        html = self._build(n=2, per=3)  # only 6 uploads exist

        self.assertEqual(len(BLEED_PAGE.findall(html)), 6)
        self.assertEqual(PHOTO_TARGET.search(html).group(1), "6")


class BookRenderingTests(unittest.TestCase):
    def setUp(self):
        self.activity = Activity(
            id="42", name="A very long ride title " * 20, date="2026-08-16T06:01:05Z", year="2026",
            description="A long description " * 100, kudos=60, pr_count=4,
            distance_km=161.2, elev_m=1952, moving_time=22000,
        )
        self.highlight = Highlight(self.activity, 88.0, "照片与骑行故事完整")

    def test_photo_page_keeps_activity_context(self):
        photo = Photo("assets/photos/42.jpg", "Rain and mountains")
        rendered = _activity_photo_page("recto", self.highlight, photo, "7")
        self.assertIn('data-activity-id="42"', rendered)
        self.assertIn('data-month="8"', rendered)
        self.assertIn("Rain and mountains", rendered)
        self.assertNotIn("照片与骑行故事完整", rendered)
        self.assertNotIn("photo-kicker", rendered)
        self.assertNotIn('class="folio"', rendered)
        self.assertIn('class="portrait-full"', rendered)
        self.assertIn('data-layout="portrait-full"', rendered)
        self.assertIn('data-overlay="forbid"', rendered)
        self.assertNotIn("<figcaption", rendered)
        self.assertIn('loading="lazy"', rendered)
        self.assertIn('decoding="async"', rendered)

    def test_landscape_and_portrait_photos_share_the_same_frame(self):
        portrait = _activity_photo_page("recto", self.highlight, Photo("portrait.jpg"), "1")
        landscape = _activity_photo_page("verso", self.highlight, Photo("landscape.jpg", landscape=True), "2")
        self.assertIn('class="portrait-full"', portrait)
        self.assertIn('data-layout="portrait-full"', portrait)
        self.assertNotIn("<figcaption", portrait)
        self.assertIn('class="landscape-split"', landscape)
        self.assertIn('data-layout="landscape-split"', landscape)
        self.assertIn('data-image-zone="0,0,100,66"', landscape)
        self.assertIn('data-copy-zone="0,66,100,34"', landscape)
        self.assertIn("<figcaption", landscape)

    def test_selected_activity_blocks_are_sorted_by_date(self):
        january = Highlight(
            Activity(id="jan", name="January Ride", date="2026-01-20T08:00:00Z", year="2026"),
            10,
            "影像记录",
        )
        march = Highlight(
            Activity(id="mar", name="March Ride", date="2026-03-01T08:00:00Z", year="2026"),
            99,
            "年度最多点赞",
        )
        december = Highlight(
            Activity(id="dec", name="December Ride", date="2026-12-02T08:00:00Z", year="2026"),
            80,
            "年度 PR 高光",
        )

        timeline = book._chronological_activity_blocks([december, march], [january, march])

        self.assertEqual(
            [(item.activity.id, featured) for item, featured in timeline],
            [("jan", False), ("mar", True), ("dec", True)],
        )

    def test_book_frame_contains_no_blank_endpapers(self):
        pages = _frame_pages("2026", {"rides": 1, "km": 10, "elev": 20, "lines": []}, ["activity"])
        rendered = "".join(pages)
        self.assertEqual(len(pages), 6)
        self.assertNotIn("endpaper", rendered)
        self.assertEqual(rendered.count('data-density="hard"'), 2)

    def test_cover_renders_photo_poster_and_route_fallback(self):
        review = build_year_review([self.activity])
        selection = CoverSelection(Photo("assets/photos/42.jpg", landscape=True), self.activity)

        photo_cover = _cover("2026", review, selection, "<svg></svg>")
        fallback = _cover("2026", review, None, "<svg class=\"route-heatmap\"></svg>")

        self.assertIn('data-cover-mode="photo"', photo_cover)
        self.assertIn('data-layout="subject-safe"', photo_cover)
        self.assertIn('data-overlay="forbid"', photo_cover)
        self.assertIn('data-image-zone="0,0,100,64"', photo_cover)
        self.assertIn('data-copy-zone="0,64,100,36"', photo_cover)
        self.assertIn('src="assets/photos/42.jpg"', photo_cover)
        self.assertIn("161 KM", photo_cover)
        self.assertIn('data-cover-mode="route"', fallback)
        self.assertNotIn("<img", fallback)
        self.assertIn("route-heatmap", fallback)

    def test_annual_review_is_exactly_two_pages_with_real_month_bars(self):
        january = Activity(id="jan", name="January", date="2026-01-02T08:00:00Z", year="2026", distance_km=20)
        august = Activity(id="aug", name="A very long longest ride title " * 10, date="2026-08-02T08:00:00Z", year="2026", distance_km=200)
        review = build_year_review([january, august])

        declaration = _year_declaration_page("2026", review)
        rhythm = _year_rhythm_page(review, "<svg></svg>")

        self.assertIn('data-year-review="declaration"', declaration)
        self.assertIn('data-year-review="rhythm"', rhythm)
        self.assertEqual(rhythm.count('<span class="month-bar'), 2)
        self.assertEqual(rhythm.count("is-peak"), 1)
        self.assertIn("8月", rhythm)
        self.assertIn("…", rhythm)

    def test_heatmap_page_aggregates_routes_and_compact_year_metrics(self):
        demo = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        rides = [
            Activity(id="jan", name="January", date="2026-01-02T08:00:00Z", year="2026", distance_km=12.4, polyline=demo),
            Activity(id="mar", name="March", date="2026-03-02T08:00:00Z", year="2026", distance_km=20.1, polyline=demo),
        ]

        rendered = _heatmap_page("2026", rides)

        self.assertIn('data-annual-heatmap="1"', rendered)
        self.assertIn("年度轨迹", rendered)
        self.assertIn('<b>2</b> 次活动', rendered)
        self.assertIn('<b>33</b> km', rendered)
        self.assertIn('<b>2</b> 个活跃月份', rendered)
        self.assertEqual(rendered.count('class="heat-route hot"'), 2)
        self.assertIn("轨迹已按主要活动区域聚合", rendered)

    def test_heatmap_is_after_title_and_omitted_without_routes(self):
        stats = {"rides": 1, "km": 10, "elev": 20, "lines": []}
        ride = Activity(id="plain", name="No GPS", date="2026-01-02T08:00:00Z", year="2026")
        pages = _frame_pages("2026", stats, ["activity"], [ride])
        self.assertNotIn("annual-heatmap", "".join(pages))

        ride.polyline = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        pages = _frame_pages("2026", stats, ["activity"], [ride])
        self.assertIn('data-year-review="rhythm"', pages[2])
        self.assertIn('data-annual-heatmap="1"', pages[3])

    def test_long_feature_copy_is_bounded_before_render(self):
        rendered = _feature_page("recto", self.highlight)
        self.assertLess(len(rendered), 3000)
        self.assertIn("…", rendered)

    def test_document_renders_accessible_theme_picker_and_scripts(self):
        body = (
            '<article class="book-page" data-month="3"></article>'
            '<article class="book-page" data-month="3"></article>'
            '<article class="book-page" data-month="8"></article>'
        )
        rendered = _document("2026", body)
        self.assertIn('id="theme-toggle"', rendered)
        self.assertIn('aria-expanded="false"', rendered)
        self.assertIn('id="theme-popover"', rendered)
        self.assertEqual(rendered.count('data-theme-id="'), 19)
        self.assertIn('aria-pressed="true"', rendered)
        self.assertIn('strava-photobook.theme', rendered)
        self.assertIn("style.setProperty('--theme-primary'", rendered)
        self.assertLess(rendered.index('theme-catalog.js'), rendered.index('flipbook.js'))
        self.assertEqual(rendered.count('class="month-jump"'), 2)
        self.assertIn('data-month="3" aria-label="跳到 3 月"', rendered)
        self.assertIn('data-month="8" aria-label="跳到 8 月"', rendered)
        self.assertIn('id="month-timeline"', rendered)
        self.assertIn('month-timeline.js', rendered)
        self.assertNotIn('class="book-header"', rendered)
        self.assertIn('class="book-theme-overlay"', rendered)
        self.assertLess(rendered.index('class="book-theme-overlay"'), rendered.index('id="book"'))


if __name__ == "__main__":
    unittest.main()
