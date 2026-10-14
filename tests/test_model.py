import unittest

from strava_photobook.model import (
    Activity,
    plan_photo_quotas,
    select_editorial_highlights,
    target_photo_count,
)


def ride(identifier, name, month, **values):
    return Activity(id=identifier, name=name, date=f"2026-{month:02d}-01T08:00:00Z", year="2026", **values)


class TargetPhotoCountTests(unittest.TestCase):
    def test_small_year_uses_every_upload_without_forcing_the_floor(self):
        self.assertEqual(target_photo_count(0), 0)
        self.assertEqual(target_photo_count(20), 20)

    def test_typical_year_keeps_the_old_baseline(self):
        self.assertEqual(target_photo_count(40), 40)   # 24 wanted, floor holds at 40
        self.assertEqual(target_photo_count(66), 40)
        self.assertEqual(target_photo_count(67), 40)

    def test_rich_year_grows_at_sixty_percent_until_cap(self):
        self.assertEqual(target_photo_count(100), 60)
        self.assertEqual(target_photo_count(200), 120)
        self.assertEqual(target_photo_count(500), 120)  # capped

    def test_guard_rails_are_overridable(self):
        self.assertEqual(target_photo_count(100, ratio=0.5, floor=10, cap=40), 40)


class PhotoQuotaPlanningTests(unittest.TestCase):
    def test_features_get_more_and_leftovers_follow_priority(self):
        feature = ride("f", "Feature", 1, photo_count=10)
        gallery_a = ride("g1", "Gallery A", 2, photo_count=10)
        gallery_b = ride("g2", "Gallery B", 3, photo_count=10)
        ordered = [feature, gallery_a, gallery_b]

        quota = plan_photo_quotas(ordered, {"f"}, target=10)

        # base is 4/2/2 = 8; two leftover slots raise the feature first, then g1
        self.assertEqual(quota, {"f": 5, "g1": 3, "g2": 2})

    def test_per_ride_cap_keeps_one_photo_heavy_activity_from_filling_the_book(self):
        big = ride("big", "Album", 1, photo_count=100)
        quota = plan_photo_quotas([big], {"big"}, target=120)
        self.assertEqual(quota, {"big": 6})

    def test_quotas_never_exceed_actual_uploads(self):
        small = ride("s", "One Shot", 1, photo_count=1)
        quota = plan_photo_quotas([small], set(), target=10)
        self.assertEqual(quota, {"s": 1})

    def test_spreads_quota_across_many_rides(self):
        rides = [ride(str(i), f"Ride {i}", (i % 12) + 1, photo_count=10) for i in range(10)]
        quota = plan_photo_quotas(rides, {"0"}, target=40)
        self.assertEqual(sum(quota.values()), 40)
        self.assertTrue(all(value <= 6 for value in quota.values()))
        self.assertGreaterEqual(quota["0"], quota["9"])  # featured ride not starved


class EditorialSelectionTests(unittest.TestCase):
    def test_photo_story_outranks_bare_kudos_when_signals_are_close(self):
        bare = ride("1", "Morning Ride", 1, kudos=60)
        story = ride("2", "Mountain Story", 2, kudos=52, photo_count=5, description="A memorable mountain day", pr_count=3)
        selected = select_editorial_highlights([bare, story], limit=1)
        self.assertEqual(selected[0].activity.id, "2")
        self.assertEqual(selected[0].reason, "年度最多点赞")

    def test_selection_spreads_months_and_repeated_titles(self):
        rides = [
            ride("1", "黑分解 Ride", 4, kudos=70, photo_count=3),
            ride("2", "黑分解Ride", 4, kudos=69, photo_count=3),
            ride("3", "雨战百里画廊", 8, kudos=60, photo_count=4, description="雨中骑完百里"),
        ]
        selected = select_editorial_highlights(rides, limit=2)
        self.assertEqual([x.activity.id for x in selected], ["3", "1"])

    def test_reason_can_explain_pr_highlight(self):
        selected = select_editorial_highlights([ride("1", "Race", 9, pr_count=12, photo_count=1)], limit=1)
        self.assertIn("PR", selected[0].reason)


if __name__ == "__main__":
    unittest.main()
