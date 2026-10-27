import unittest
from pathlib import Path


class BeginnerDocsTests(unittest.TestCase):
    def test_setup_covers_complete_first_run(self):
        text = Path("docs/setup.md").read_text("utf-8")
        for phrase in (
            "Python 3", "Strava API", "Authorization Callback Domain", "github-auth",
            "publish 2026", "预期", "常见问题", "公开",
        ):
            self.assertIn(phrase, text)

    def test_docs_explain_the_fixed_distance_manifesto_theme(self):
        setup = Path("docs/setup.md").read_text("utf-8")
        readme = Path("README.md").read_text("utf-8")
        for phrase in ("唯一主题", "Distance Manifesto", "暗色书页", "暖白", "锈橙"):
            self.assertIn(phrase, setup + readme)
        self.assertNotIn("strava-photobook.theme", setup + readme)

    def test_docs_explain_nightly_github_actions_setup(self):
        text = Path("README.md").read_text("utf-8") + Path("docs/setup.md").read_text("utf-8")
        for phrase in (
            "每天 21:00", "nightly-photobook.yml", "STRAVA_CLIENT_ID",
            "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN", "SECRETS_ADMIN_TOKEN",
            "workflow_dispatch",
        ):
            self.assertIn(phrase, text)

    def test_docs_explain_root_dashboard_and_optional_training_source(self):
        text = Path("README.md").read_text("utf-8") + Path("docs/setup.md").read_text("utf-8")
        for phrase in (
            "build-dashboard 2026", "根页", "photobook/", "data/metrics.json",
            "INTERVALS_API_KEY", "明确降级", "validate_dashboard.py",
        ):
            self.assertIn(phrase, text)


class BrandRenameTests(unittest.TestCase):
    def test_readme_uses_new_brand(self):
        text = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("我的骑行数据", text)

    def test_active_docs_use_cycling_data_hub_repository(self):
        active_docs = (
            Path("README.md"),
            Path("docs/setup.md"),
            Path("docs/superpowers/specs/2026-10-27-cycling-data-hub-design.md"),
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in active_docs)
        self.assertIn("https://github.com/MengEn-Ink/cycling-data-hub", combined)
        self.assertIn("https://mengen-ink.github.io/cycling-data-hub/", combined)
        self.assertNotIn("strava-photobook-2026", combined)


if __name__ == "__main__":
    unittest.main()
