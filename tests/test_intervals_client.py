import base64
import unittest
from unittest import mock

from strava_photobook.intervals.client import IntervalsClient, IntervalsError


class AuthHeaderTests(unittest.TestCase):
    def test_basic_auth_header_uses_api_key_prefix(self):
        client = IntervalsClient(api_key="SECRET", athlete_id="0")
        expected = "Basic " + base64.b64encode(b"API_KEY:SECRET").decode("ascii")
        self.assertEqual(client._auth_header(), expected)

    def test_ready_requires_api_key(self):
        self.assertFalse(IntervalsClient(api_key="", athlete_id="0").ready)
        self.assertTrue(IntervalsClient(api_key="k", athlete_id="0").ready)


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = IntervalsClient(api_key="k", athlete_id="42")

    def test_athlete_hits_athlete_path(self):
        with mock.patch.object(self.client, "_get", return_value={"id": 42}) as g:
            self.assertEqual(self.client.athlete(), {"id": 42})
            g.assert_called_once_with("/athlete/42")

    def test_activities_passes_oldest_param(self):
        with mock.patch.object(self.client, "_get", return_value=[{"id": "a"}]) as g:
            out = self.client.activities(oldest="2026-01-01", newest="2026-12-31")
            self.assertEqual(out, [{"id": "a"}])
            g.assert_called_once_with(
                "/athlete/42/activities",
                params={"oldest": "2026-01-01", "newest": "2026-12-31"},
            )

    def test_gear_and_power_curve_paths(self):
        with mock.patch.object(self.client, "_get", return_value=[]) as g:
            self.client.gear()
            g.assert_called_with("/athlete/42/gear")
        with mock.patch.object(self.client, "_get", return_value={}) as g:
            self.client.power_curve()
            g.assert_called_with(
                "/athlete/42/power-curves.json",
                params={"type": "Ride"},
            )

    def test_429_raises_intervals_error(self):
        resp = mock.Mock(status_code=429, text="too many")
        with mock.patch("strava_photobook.intervals.client.requests.get", return_value=resp):
            with self.assertRaises(IntervalsError):
                self.client._get("/athlete/42")
