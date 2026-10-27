from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_dashboard import ValidationError, validate_dashboard


def write_site(root: Path) -> Path:
    site = root / "site"
    (site / "data").mkdir(parents=True)
    (site / "photobook").mkdir()
    (site / "index.html").write_text(
        '<html data-strava-photobook="1" data-cycling-dashboard="1">'
        '<iframe src="photobook/index.html"></iframe></html>',
        encoding="utf-8",
    )
    (site / "dashboard.css").write_text("body{}", encoding="utf-8")
    (site / "dashboard.js").write_text("void 0;", encoding="utf-8")
    (site / "photobook" / "index.html").write_text(
        '<html data-strava-photobook="1"></html>', encoding="utf-8"
    )
    for name, payload in {
        "metrics": {"kpis": {}, "intervals_available": False},
        "routes": [],
        "activities": [],
    }.items():
        (site / "data" / f"{name}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
    return site


class DashboardValidationTests(unittest.TestCase):
    def test_accepts_complete_public_site(self):
        with tempfile.TemporaryDirectory() as raw:
            counts = validate_dashboard(write_site(Path(raw)))
        self.assertEqual(counts["activities"], 0)

    def test_rejects_missing_asset_and_unresolved_placeholder(self):
        with tempfile.TemporaryDirectory() as raw:
            site = write_site(Path(raw))
            (site / "dashboard.js").unlink()
            index = site / "index.html"
            index.write_text(index.read_text("utf-8") + "__YEAR__", encoding="utf-8")
            with self.assertRaises(ValidationError) as caught:
                validate_dashboard(site)
        self.assertIn("missing asset: dashboard.js", str(caught.exception))
        self.assertIn("unresolved placeholders: __YEAR__", str(caught.exception))

    def test_rejects_sensitive_keys_in_any_public_json(self):
        with tempfile.TemporaryDirectory() as raw:
            site = write_site(Path(raw))
            (site / "data" / "metrics.json").write_text(
                json.dumps({"nested": {"api_key": "must-not-ship"}}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValidationError, "sensitive key"):
                validate_dashboard(site)

    def test_rejects_development_artifacts(self):
        with tempfile.TemporaryDirectory() as raw:
            site = write_site(Path(raw))
            (site / ".DS_Store").write_bytes(b"metadata")
            (site / "dashboard.test.mjs").write_text("test", encoding="utf-8")
            (site / "photobook" / "dashboard").mkdir()
            with self.assertRaises(ValidationError) as caught:
                validate_dashboard(site)
        message = str(caught.exception)
        self.assertIn(".DS_Store", message)
        self.assertIn("dashboard.test.mjs", message)
        self.assertIn("photobook/dashboard", message)


if __name__ == "__main__":
    unittest.main()
