import unittest
from pathlib import Path
from unittest import mock

from strava_photobook.config import Config


class IntervalsConfigTests(unittest.TestCase):
    def test_intervals_creds_from_env(self):
        env = {"INTERVALS_API_KEY": "abc", "INTERVALS_ATHLETE_ID": "7"}
        with mock.patch.dict("os.environ", env, clear=False):
            cfg = Config.load(root=Path.cwd())
        self.assertEqual(cfg.intervals.api_key, "abc")
        self.assertEqual(cfg.intervals.athlete_id, "7")
        self.assertTrue(cfg.intervals.ready)

    def test_intervals_defaults_athlete_zero_and_not_ready(self):
        env = {"INTERVALS_API_KEY": "", "INTERVALS_ATHLETE_ID": ""}
        with mock.patch.dict("os.environ", env, clear=False):
            cfg = Config.load(root=Path.cwd())
        self.assertEqual(cfg.intervals.athlete_id, "0")
        self.assertFalse(cfg.intervals.ready)

    def test_intervals_dir_under_data(self):
        cfg = Config.load(root=Path.cwd())
        self.assertEqual(cfg.intervals_dir, cfg.data_dir / "intervals")
