import unittest
from pathlib import Path


class NightlyWorkflowTests(unittest.TestCase):
    def test_nightly_workflow_has_safe_refresh_and_publish_contract(self):
        text = Path(".github/workflows/nightly-photobook.yml").read_text(encoding="utf-8")
        for token in (
            "cron: '0 13 * * *'",
            "workflow_dispatch:",
            "contents: write",
            "cancel-in-progress: true",
            "STRAVA_CLIENT_ID",
            "STRAVA_CLIENT_SECRET",
            "STRAVA_REFRESH_TOKEN",
            "SECRETS_ADMIN_TOKEN",
            "INTERVALS_API_KEY",
            "INTERVALS_ATHLETE_ID",
            "Retry Strava fetch after rate limit",
            'fetch --year "$BOOK_YEAR"',
            'sync-intervals --year "$BOOK_YEAR"',
            "continue-on-error: true",
            "900 - $(date +%s) % 900 + 60",
            "if: always()",
            "tools/validate_release.py",
            "tools/validate_dashboard.py",
            "--require-heatmap",
            "tools/photo_layout_gate.py",
            'build-dashboard "$BOOK_YEAR"',
            'books/$BOOK_YEAR/photobook/index.html',
            'books/$BOOK_YEAR/html-contract.test.mjs',
            'previous_dir/photobook',
            "FETCH_OK=false",
            "env.FETCH_OK == 'true'",
            "continue-on-error: true",
            "refs/heads/gh-pages",
        ):
            self.assertIn(token, text)
        self.assertIn("env.INTERVALS_API_KEY != ''", text)
        self.assertLess(text.index('build "$BOOK_YEAR"'), text.index('build-dashboard "$BOOK_YEAR"'))
        self.assertLess(text.index('books/$BOOK_YEAR/html-contract.test.mjs'), text.index('build-dashboard "$BOOK_YEAR"'))
        self.assertLess(text.index("tools/validate_dashboard.py"), text.index("refs/heads/gh-pages"))
        self.assertLess(text.index("tools/validate_release.py"), text.index("refs/heads/gh-pages"))
        self.assertLess(text.index("BOOK_YEAR="), text.index("Fetch current Strava activities"))
        self.assertGreaterEqual(text.count("env.FETCH_OK == 'true'"), 4)


if __name__ == "__main__":
    unittest.main()
