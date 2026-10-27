import unittest
from pathlib import Path

from strava_photobook.theme import FEATURE_CSS, THEME_CSS


class LayoutContractTests(unittest.TestCase):
    def test_text_regions_are_clamped_and_clipped(self):
        css = (FEATURE_CSS + THEME_CSS).replace(" ", "")
        for selector in (".feature{", ".feat-title{", ".feat-desc{", ".bleed-cap{"):
            self.assertIn(selector, css)
        self.assertIn("overflow:hidden", css)
        self.assertIn("-webkit-line-clamp", css)

    def test_photo_orientations_have_distinct_safe_layouts(self):
        css = FEATURE_CSS.replace(" ", "")
        self.assertIn(".art-page.portrait-fullimg{", css)
        self.assertIn("height:100%", css)
        self.assertIn("object-fit:cover", css)
        self.assertIn(".art-page.landscape-splitimg{", css)
        self.assertIn("height:66%", css)
        self.assertIn("object-fit:contain", css)
        self.assertIn("height:34%", css)

    def test_year_statistics_have_a_bounded_compact_layout(self):
        css = (FEATURE_CSS + THEME_CSS).replace(" ", "")
        self.assertIn(".year-stats{", css)
        self.assertIn("max-height:76%", css)
        self.assertIn("overflow:hidden", css)
        self.assertIn(".year-statsp{margin:002.6cqw}", css)

    def test_theme_variables_cover_book_surfaces_without_picker_chrome(self):
        css = (FEATURE_CSS + THEME_CSS).replace(" ", "")
        runtime = Path("runtime/styles.css").read_text(encoding="utf-8").replace(" ", "")
        for variable in ("--theme-primary", "--theme-accent", "--theme-accent-ink", "--theme-paper"):
            self.assertIn(variable, css + runtime)
        self.assertNotIn(".theme-picker{", runtime)
        self.assertNotIn(".theme-toggle{", runtime)
        self.assertNotIn(".theme-popover{", runtime)
        for token in (".month-timeline{", ".month-jump{", "min-width:44px", "overflow-x:auto"):
            self.assertIn(token, runtime)
        for selector in (".cloth{", ".feat-reason{", ".routecircle{"):
            self.assertIn(selector, css)
        self.assertNotIn(".photo-kicker{", css)

    def test_annual_heatmap_stays_in_safe_bounds_and_uses_theme_colors(self):
        css = THEME_CSS.replace(" ", "")
        for selector in (".annual-heatmap{", ".heatmap-canvas{", ".heatmap-summary{"):
            self.assertIn(selector, css)
        self.assertIn("overflow:hidden", css)
        self.assertIn("var(--theme-primary)", css)
        self.assertIn("var(--theme-accent)", css)

    def test_poster_cover_and_year_review_have_safe_theme_aware_layouts(self):
        css = THEME_CSS.replace(" ", "")
        for selector in (
            ".poster-cover{", ".cover-photo{", ".cover-copy{",
            ".year-declaration{", ".year-rhythm{", ".month-bars{", ".rhythm-facts{",
        ):
            self.assertIn(selector, css)
        for token in ("height:64%", "height:36%", "overflow:hidden", "var(--theme-primary)", "var(--theme-accent)"):
            self.assertIn(token, css)

    def test_distance_manifesto_uses_dark_pages_with_readable_content(self):
        css = THEME_CSS.replace(" ", "").lower()
        for token in (
            'html[data-theme="distance-manifesto"]',
            "--theme-primary:#0a0807",
            "--theme-accent:#f05523",
            "--theme-paper:#15100d",
            "--paper:#15100d",
            "--ink:#f4e8d8",
            "background:#0a0807",
            "background:#15100d!important",
            "color:#f4e8d8",
            "border-top:.5cqwsolid#f05523",
            "background:var(--theme-accent);color:#0a0807",
            "mix-blend-mode:screen",
            "line-height:1.16",
            "letter-spacing:-.015em",
        ):
            self.assertIn(token, css)
        self.assertNotIn("background:#d8c7b5!important", css)


if __name__ == "__main__":
    unittest.main()
