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

    def test_docs_explain_theme_switching_and_reset(self):
        setup = Path("docs/setup.md").read_text("utf-8")
        readme = Path("README.md").read_text("utf-8")
        for phrase in ("19 种主题", "黑白橙", "自动保存", "strava-photobook.theme"):
            self.assertIn(phrase, setup + readme)

    def test_docs_explain_nightly_github_actions_setup(self):
        text = Path("README.md").read_text("utf-8") + Path("docs/setup.md").read_text("utf-8")
        for phrase in (
            "每天 21:00", "nightly-photobook.yml", "STRAVA_CLIENT_ID",
            "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN", "SECRETS_ADMIN_TOKEN",
            "workflow_dispatch",
        ):
            self.assertIn(phrase, text)


class BrandRenameTests(unittest.TestCase):
    def test_readme_uses_new_brand(self):
        text = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("我的骑行数据", text)


if __name__ == "__main__":
    unittest.main()
