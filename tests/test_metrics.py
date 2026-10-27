import unittest
from datetime import date, timedelta

from strava_photobook.model import Activity
from strava_photobook import metrics


def ride(rid, date, km=0.0, elev=0.0, secs=0, kudos=0):
    return Activity(id=rid, name="Ride", date=date, year=date[:4],
                    distance_km=km, elev_m=elev, moving_time=secs, kudos=kudos)


class KpiTests(unittest.TestCase):
    def test_summarize_totals_and_counts(self):
        acts = [
            ride("1", "2026-01-05T08:00:00Z", km=40.0, elev=300, secs=3600, kudos=5),
            ride("2", "2026-02-10T08:00:00Z", km=60.0, elev=700, secs=7200, kudos=9),
        ]
        kpi = metrics.summarize_kpis(acts)
        self.assertEqual(kpi["rides"], 2)
        self.assertAlmostEqual(kpi["distance_km"], 100.0)
        self.assertAlmostEqual(kpi["elev_m"], 1000.0)
        self.assertEqual(kpi["moving_seconds"], 10800)
        self.assertEqual(kpi["kudos"], 14)
        self.assertAlmostEqual(kpi["longest_km"], 60.0)

    def test_empty_is_zeroed(self):
        kpi = metrics.summarize_kpis([])
        self.assertEqual(kpi["rides"], 0)
        self.assertEqual(kpi["distance_km"], 0.0)
        self.assertEqual(kpi["longest_km"], 0.0)


class CalendarTests(unittest.TestCase):
    def test_sums_distance_per_day(self):
        acts = [
            ride("1", "2026-03-01T08:00:00Z", km=10.0),
            ride("2", "2026-03-01T18:00:00Z", km=5.0),
            ride("3", "2026-03-03T08:00:00Z", km=20.0),
        ]
        cal = metrics.calendar_distance(acts)
        self.assertAlmostEqual(cal["2026-03-01"], 15.0)
        self.assertAlmostEqual(cal["2026-03-03"], 20.0)
        self.assertNotIn("2026-03-02", cal)


class EddingtonTests(unittest.TestCase):
    def test_eddington_counts_days_meeting_threshold(self):
        acts = []
        for i, km in enumerate([100.0, 80.0, 60.0, 40.0, 20.0], start=1):
            acts.append(ride(str(i), f"2026-04-0{i}T08:00:00Z", km=km))
        self.assertEqual(metrics.eddington_number(acts), 5)

    def test_eddington_simple_case(self):
        acts = [ride(str(i), f"2026-05-0{i}T08:00:00Z", km=km)
                for i, km in enumerate([3.0, 3.0, 3.0], start=1)]
        self.assertEqual(metrics.eddington_number(acts), 3)

    def test_eddington_empty(self):
        self.assertEqual(metrics.eddington_number([]), 0)


class TrainingLoadTests(unittest.TestCase):
    def test_constant_load_converges_upward(self):
        base = date(2026, 1, 1)
        loads = [{"date": (base + timedelta(days=d)).isoformat(),
                  "training_load": 100} for d in range(60)]
        series = metrics.training_load_series(loads)
        self.assertEqual(len(series), 60)
        self.assertLess(series[0]["ctl"], series[-1]["ctl"])
        self.assertLess(series[-1]["ctl"], 101)
        self.assertIn("tsb", series[0])

    def test_empty_returns_empty(self):
        self.assertEqual(metrics.training_load_series([]), [])


class FtpTrendTests(unittest.TestCase):
    def test_keeps_last_ftp_per_day_sorted(self):
        recs = [
            {"date": "2026-01-10T00:00:00", "ftp": 240},
            {"date": "2026-03-01T00:00:00", "ftp": 250},
            {"date": "2026-03-01T12:00:00", "ftp": 255},
            {"date": "2026-02-01T00:00:00", "ftp": None},
        ]
        trend = metrics.ftp_trend(recs)
        self.assertEqual(trend, [
            {"date": "2026-01-10", "ftp": 240},
            {"date": "2026-03-01", "ftp": 255},
        ])


class SeasonCountdownTests(unittest.TestCase):
    def test_weeks_and_days_until_season(self):
        cd = metrics.season_countdown(today=date(2026, 10, 27),
                                      season_start=date(2027, 4, 1))
        self.assertEqual(cd["days"], 156)
        self.assertEqual(cd["weeks"], 22)
        self.assertFalse(cd["started"])

    def test_after_season_marks_started(self):
        cd = metrics.season_countdown(today=date(2027, 4, 2),
                                      season_start=date(2027, 4, 1))
        self.assertTrue(cd["started"])
        self.assertEqual(cd["days"], 0)


class BuildMetricsTests(unittest.TestCase):
    def test_assembles_all_blocks_with_degraded_intervals(self):
        acts = [ride("1", "2026-06-01T08:00:00Z", km=50.0, elev=400, secs=5400, kudos=3)]
        out = metrics.build_metrics(acts, intervals=None,
                                    today=date(2026, 10, 27),
                                    season_start=date(2027, 4, 1))
        self.assertEqual(out["kpis"]["rides"], 1)
        self.assertIn("2026-06-01", out["calendar"])
        self.assertEqual(out["training_load"], [])
        self.assertEqual(out["ftp_trend"], [])
        self.assertFalse(out["intervals_available"])
        self.assertEqual(out["season"]["weeks"], 22)

    def test_includes_training_when_intervals_present(self):
        acts = [ride("1", "2026-06-01T08:00:00Z", km=50.0)]
        intervals = {
            "activities": [
                {"date": "2026-06-01T08:00:00", "training_load": 80, "ftp": 250}
            ],
            "gear": [{"id": "bike", "name": "Road", "distance_km": 1200}],
            "power_curve": {"list": [{"secs": 5, "watts": 900}]},
        }
        out = metrics.build_metrics(acts, intervals=intervals,
                                    today=date(2026, 10, 27),
                                    season_start=date(2027, 4, 1))
        self.assertTrue(out["intervals_available"])
        self.assertEqual(len(out["training_load"]), 1)
        self.assertEqual(out["ftp_trend"], [{"date": "2026-06-01", "ftp": 250}])
        self.assertEqual(out["gear"][0]["name"], "Road")
        self.assertEqual(out["power_curve"]["list"][0]["watts"], 900)


if __name__ == "__main__":
    unittest.main()
