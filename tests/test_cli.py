import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from strava_photobook import cli
from strava_photobook.github.publisher import PublishResult


class CLITests(unittest.TestCase):
    def test_fetch_accepts_a_year_scope(self):
        with tempfile.TemporaryDirectory() as root, patch(
            "strava_photobook.source.fetch_activities", return_value=[]
        ) as fetch:
            cli.main(["--root", root, "fetch", "--year", "2026"])
            self.assertEqual(fetch.call_args.kwargs["year"], "2026")

    def test_github_auth_falls_back_to_gh_cli(self):
        completed = type("Completed", (), {"stdout": "oauth-token\n", "returncode": 1})()
        with tempfile.TemporaryDirectory() as root, patch.dict("os.environ", {}, clear=True), patch(
            "strava_photobook.cli.shutil.which", return_value="/usr/bin/gh"
        ), patch("strava_photobook.cli.subprocess.run", return_value=completed) as run:
            cli.main(["--root", root, "github-auth"])
            env = Path(root, ".env").read_text("utf-8")
        self.assertIn("GITHUB_TOKEN=oauth-token", env)
        self.assertEqual(run.call_count, 3)

    def test_publish_routes_year_and_repo(self):
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            book = root / "books" / "2026"
            book.mkdir(parents=True)
            (book / "index.html").write_text('<html data-strava-photobook="1">', encoding="utf-8")
            with patch.dict("os.environ", {"GH_TOKEN": "token"}, clear=True), patch(
                "strava_photobook.github.publisher.Publisher.publish",
                return_value=PublishResult("https://github.com/alice/custom", "https://alice.github.io/custom/", "abc"),
            ) as publish:
                cli.main(["--root", raw_root, "publish", "2026", "--repo", "custom"])
            self.assertEqual(publish.call_args.args[0], book.resolve())
            self.assertEqual(publish.call_args.args[1], "custom")

    def test_sync_intervals_invokes_source_with_year(self):
        with tempfile.TemporaryDirectory() as root, patch(
            "strava_photobook.intervals.source.sync_intervals",
            return_value={"activities": [1, 2], "gear": []},
        ) as sync:
            cli.main(["--root", root, "sync-intervals", "--year", "2026"])
            self.assertEqual(sync.call_args.kwargs["year"], "2026")

    def test_build_dashboard_writes_json_for_year(self):
        with tempfile.TemporaryDirectory() as root, patch(
            "strava_photobook.source.load_activities",
            return_value=[],
        ), patch(
            "strava_photobook.dashboard.build_dashboard_data",
            return_value={"year": "2026", "metrics": {"kpis": {}}, "routes": []},
        ) as build, patch(
            "strava_photobook.dashboard.write_dashboard_json",
        ) as write:
            cli.main(["--root", root, "build-dashboard", "2026"])
            self.assertEqual(build.call_args.kwargs["year"], "2026")
            self.assertTrue(write.called)


if __name__ == "__main__":
    unittest.main()
