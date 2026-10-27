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
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            dashboard.write_dashboard_json(data, out)
            metrics = _json.loads((out / "data" / "metrics.json").read_text("utf-8"))
            routes = _json.loads((out / "data" / "routes.json").read_text("utf-8"))
        self.assertEqual(metrics["kpis"]["rides"], 1)
        self.assertEqual(routes[0]["polyline"], "xy")


if __name__ == "__main__":
    unittest.main()
