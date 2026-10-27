import json as _json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from strava_photobook.model import Activity
from strava_photobook import dashboard


def ride(rid, date_str, km=0.0, poly=""):
    return Activity(id=rid, name="Ride", date=date_str, year=date_str[:4],
                    distance_km=km, polyline=poly)


class RoutesPayloadTests(unittest.TestCase):
    def test_includes_only_activities_with_polyline(self):
        acts = [
            ride("1", "2026-01-01T08:00:00Z", km=10.0, poly="abc"),
            ride("2", "2026-01-02T08:00:00Z", km=20.0, poly=""),
        ]
        routes = dashboard.routes_payload(acts)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]["id"], "1")
        self.assertEqual(routes[0]["polyline"], "abc")
        self.assertAlmostEqual(routes[0]["distance_km"], 10.0)
        self.assertEqual(routes[0]["date"], "2026-01-01")

    def test_excludes_virtual_routes_from_geographic_heatmap(self):
        virtual = ride("v1", "2026-01-03T08:00:00Z", km=30.0, poly="virtual")
        virtual.meta = {"sport_type": "VirtualRide"}
        self.assertEqual(dashboard.routes_payload([virtual]), [])


class ActivitiesPayloadTests(unittest.TestCase):
    def test_exposes_dashboard_fields_without_raw_api_response(self):
        activity = ride("1", "2026-06-01T08:00:00Z", km=50.0, poly="xy")
        activity.elev_m = 700
        activity.avg_speed_kmh = 28.4
        activity.moving_time = 6400
        activity.kudos = 12
        activity.pr_count = 3
        activity.athlete_count = 4
        activity.photo_count = 2
        activity.meta = {"sport_type": "Ride", "achievement_count": 5, "secret": "drop-me"}
        payload = dashboard.activities_payload([activity])
        self.assertEqual(payload[0]["moving_seconds"], 6400)
        self.assertEqual(payload[0]["sport_type"], "Ride")
        self.assertEqual(payload[0]["achievements"], 5)
        self.assertNotIn("meta", payload[0])
        self.assertNotIn("secret", payload[0])


class BuildDashboardDataTests(unittest.TestCase):
    def test_degrades_when_intervals_cache_missing(self):
        acts = [ride("1", "2026-06-01T08:00:00Z", km=50.0, poly="xy")]
        with tempfile.TemporaryDirectory() as tmp:
            data = dashboard.build_dashboard_data(
                acts, intervals_path=Path(tmp) / "missing.json",
                year="2026", today=date(2026, 10, 27),
                season_start=date(2027, 4, 1),
            )
        self.assertEqual(data["metrics"]["kpis"]["rides"], 1)
        self.assertFalse(data["metrics"]["intervals_available"])
        self.assertEqual(len(data["routes"]), 1)
        self.assertEqual(len(data["activities"]), 1)
        self.assertEqual(data["year"], "2026")

    def test_loads_intervals_cache_when_present(self):
        acts = [ride("1", "2026-06-01T08:00:00Z", km=50.0, poly="xy")]
        with tempfile.TemporaryDirectory() as tmp:
            ivp = Path(tmp) / "2026.json"
            ivp.write_text('{"activities":[{"date":"2026-06-01T08:00:00",'
                           '"training_load":80,"ftp":250}]}', encoding="utf-8")
            data = dashboard.build_dashboard_data(
                acts, intervals_path=ivp, year="2026",
                today=date(2026, 10, 27), season_start=date(2027, 4, 1),
            )
        self.assertTrue(data["metrics"]["intervals_available"])
        self.assertEqual(data["metrics"]["ftp_trend"], [{"date": "2026-06-01", "ftp": 250}])


class WriteJsonTests(unittest.TestCase):
    def test_writes_split_json_files(self):
        data = {
            "year": "2026",
            "metrics": {"kpis": {"rides": 1}},
            "routes": [{"id": "1", "polyline": "xy"}],
            "activities": [{"id": "1", "name": "Ride"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            dashboard.write_dashboard_json(data, out)
            metrics = _json.loads((out / "data" / "metrics.json").read_text("utf-8"))
            routes = _json.loads((out / "data" / "routes.json").read_text("utf-8"))
            activities = _json.loads((out / "data" / "activities.json").read_text("utf-8"))
        self.assertEqual(metrics["kpis"]["rides"], 1)
        self.assertEqual(routes[0]["polyline"], "xy")
        self.assertEqual(activities[0]["id"], "1")


class BuildDashboardSiteTests(unittest.TestCase):
    def test_promotes_dashboard_to_root_and_nests_existing_book(self):
        data = {
            "year": "2026",
            "metrics": {"kpis": {"rides": 1}},
            "routes": [],
            "activities": [{"id": "1", "name": "Ride"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "books" / "2026"
            photos = out / "assets" / "photos"
            photos.mkdir(parents=True)
            (photos / "one.jpg").write_bytes(b"one")
            (photos / "two.jpg").write_bytes(b"two")
            (out / "index.html").write_text(
                '<html data-strava-photobook="1" data-theme="distance-manifesto">book</html>',
                encoding="utf-8",
            )
            (out / "styles.css").write_text("book", encoding="utf-8")
            (out / "html-contract.test.mjs").write_text("test", encoding="utf-8")
            (out / ".DS_Store").write_bytes(b"metadata")
            (out / "dashboard").mkdir()
            (out / "dashboard" / "stale.js").write_text("stale", encoding="utf-8")
            template = root / "runtime" / "dashboard"
            (template / "assets" / "strava").mkdir(parents=True)
            (template / "index.html").write_text(
                '<html data-strava-photobook="1" data-cycling-dashboard="1">'
                '__YEAR__ __HERO_PHOTO__ __ALBUM_PHOTO__ __PHOTOBOOK_URL__</html>',
                encoding="utf-8",
            )
            (template / "dashboard.css").write_text("dashboard", encoding="utf-8")
            (template / "dashboard.js").write_text("dashboard", encoding="utf-8")
            (template / "dashboard.test.mjs").write_text("test", encoding="utf-8")
            (template / "assets" / "strava" / "strava-white.svg").write_text(
                "<svg/>", encoding="utf-8"
            )

            result = dashboard.build_dashboard_site(data, out, template)

            index = (out / "index.html").read_text("utf-8")
            self.assertEqual(result, out / "index.html")
            self.assertIn("2026", index)
            self.assertIn("photobook/assets/photos/one.jpg", index)
            self.assertIn("photobook/index.html", index)
            self.assertTrue((out / "photobook" / "index.html").is_file())
            self.assertTrue((out / "dashboard.css").is_file())
            self.assertTrue((out / "data" / "activities.json").is_file())
            self.assertFalse((out / ".DS_Store").exists())
            self.assertFalse((out / "dashboard").exists())
            self.assertFalse((out / "dashboard.test.mjs").exists())
            self.assertFalse((out / "photobook" / "html-contract.test.mjs").exists())
            self.assertFalse((out / "photobook" / "dashboard").exists())


if __name__ == "__main__":
    unittest.main()
