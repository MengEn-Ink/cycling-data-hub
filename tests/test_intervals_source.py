import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from strava_photobook.config import Config
from strava_photobook.intervals import source


class SyncIntervalsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _cfg(self):
        env = {"INTERVALS_API_KEY": "k", "INTERVALS_ATHLETE_ID": "0"}
        with mock.patch.dict("os.environ", env, clear=False):
            return Config.load(root=self.root)

    def test_writes_normalized_cache(self):
        cfg = self._cfg()
        fake = mock.Mock()
        fake.ready = True
        fake.activities.return_value = [
            {"id": "i1", "start_date_local": "2026-05-01T07:00:00",
             "icu_training_load": 65, "icu_ftp": 250, "type": "Ride"},
        ]
        fake.gear.return_value = [{"id": "b1", "name": "Road", "distance": 1000000}]
        fake.power_curve.return_value = {"list": [{"secs": 5, "watts": 900}]}
        out = source.sync_intervals(cfg, client=fake, year="2026")
        self.assertEqual(out["activities"][0]["training_load"], 65)
        self.assertEqual(out["gear"][0]["distance_km"], 1000.0)
        cache = cfg.intervals_dir / "2026.json"
        self.assertTrue(cache.is_file())
        saved = json.loads(cache.read_text(encoding="utf-8"))
        self.assertEqual(saved["activities"][0]["id"], "i1")

    def test_not_ready_raises(self):
        cfg = self._cfg()
        fake = mock.Mock()
        fake.ready = False
        with self.assertRaises(SystemExit):
            source.sync_intervals(cfg, client=fake, year="2026")
