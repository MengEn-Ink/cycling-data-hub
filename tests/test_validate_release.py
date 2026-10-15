from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.validate_release import ValidationError, validate_release


def write_book(
    root: Path, photo_count: int, *, extras: str = "", heatmap: bool = True,
    target: int = 0, cover_photo: str | None = None, cover_in_body: bool = True,
) -> Path:
    book = root / "book"
    photos = book / "assets" / "photos"
    photos.mkdir(parents=True)
    cover_name = Path(cover_photo).name if cover_photo else None
    tags = []
    for index in range(photo_count):
        name = f"{index}.jpg"
        (photos / name).write_bytes(b"jpg")
        if cover_name == name and not cover_in_body:
            continue  # cover occupies its own slot; it must not reappear in the body
        tags.append(
            f'<article class="book-page art-page bleed recto" data-activity-id="{index}">'
            f'<img src="assets/photos/{name}"></article>'
        )
    if cover_photo:
        cover_asset = photos / cover_name
        if not cover_asset.exists():
            cover_asset.write_bytes(b"jpg")
        cover_article = (
            '<article class="book-page art-page cloth recto poster-cover" '
            f'data-cover-mode="photo"><img src="{cover_photo}"></article>'
        )
    else:
        cover_article = '<article data-cover-mode="photo"></article>'
    target_attr = f' data-photo-target="{target}"' if target else ""
    (book / "index.html").write_text(
        f'<html data-strava-photobook="1"{target_attr}><nav id="month-timeline"></nav>'
        + cover_article
        + '<article data-year-review="declaration"></article>'
        + '<article data-year-review="rhythm"></article>'
        + ('<article data-annual-heatmap="1"></article>' if heatmap else '')
        + "".join(tags) + extras + "</html>",
        encoding="utf-8",
    )
    return book


class ReleaseValidationTests(unittest.TestCase):
    def test_accepts_complete_book_at_baseline_photo_count(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            baseline = write_book(root / "old", 2)
            candidate = write_book(root / "new", 2)
            result = validate_release(candidate, baseline)
            self.assertEqual(result["photos"], 2)

    def test_rejects_photo_regression(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            baseline = write_book(root / "old", 2)
            candidate = write_book(root / "new", 1)
            with self.assertRaisesRegex(ValidationError, "photo count regressed"):
                validate_release(candidate, baseline)

    def test_accepts_small_photo_count_fluctuation_within_tolerance(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            baseline = write_book(root / "old", 40)
            candidate = write_book(root / "new", 39)
            result = validate_release(candidate, baseline)
            self.assertEqual(result["photos"], 39)

    def test_rejects_photo_drop_beyond_tolerance(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            baseline = write_book(root / "old", 40)
            candidate = write_book(root / "new", 37)
            with self.assertRaisesRegex(ValidationError, r"photo count regressed: 37 < 38"):
                validate_release(candidate, baseline)

    def test_dynamic_book_is_judged_against_its_own_target(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            # Previous fixed release shipped 100; the new dynamic target is 40.
            baseline = write_book(root / "old", 100)
            candidate = write_book(root / "new", 40, target=40)
            result = validate_release(candidate, baseline)
            self.assertEqual(result["photo_target"], 40)
            self.assertEqual(result["photos"], 40)

    def test_dynamic_book_accepts_up_to_ten_percent_shortfall(self):
        with tempfile.TemporaryDirectory() as raw:
            candidate = write_book(Path(raw), 36, target=40)  # ceil(40*0.9) == 36
            self.assertEqual(validate_release(candidate)["photos"], 36)

    def test_dynamic_book_rejects_when_target_is_unmet(self):
        with tempfile.TemporaryDirectory() as raw:
            candidate = write_book(Path(raw), 35, target=40)
            with self.assertRaisesRegex(ValidationError, r"photo count below target: 35 < 36"):
                validate_release(candidate)

    def test_rejects_cover_photo_repeated_in_body(self):
        with tempfile.TemporaryDirectory() as raw:
            # cover uses 0.jpg and the same file is still rendered as a body page
            candidate = write_book(Path(raw), 3, cover_photo="assets/photos/0.jpg")
            with self.assertRaisesRegex(ValidationError, "cover photo repeated in body"):
                validate_release(candidate)

    def test_accepts_cover_photo_excluded_from_body(self):
        with tempfile.TemporaryDirectory() as raw:
            candidate = write_book(
                Path(raw), 3, cover_photo="assets/photos/0.jpg", cover_in_body=False
            )
            result = validate_release(candidate)
            self.assertEqual(result["photos"], 3)  # cover 0.jpg + body 1.jpg/2.jpg, all unique

    def test_rejects_duplicate_photo_within_body_pages(self):
        with tempfile.TemporaryDirectory() as raw:
            repeated = (
                '<article class="book-page art-page bleed recto" data-activity-id="9">'
                '<img src="assets/photos/1.jpg"></article>'
            )
            candidate = write_book(Path(raw), 3, extras=repeated)
            with self.assertRaisesRegex(ValidationError, "duplicate photo in body: assets/photos/1.jpg"):
                validate_release(candidate)

    def test_athlete_avatar_reused_on_feature_pages_is_not_a_duplicate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            avatars = "".join(
                '<article class="book-page art-page paper recto">'
                '<img src="assets/photos/athlete.jpg"></article>'
                for _ in range(3)
            )
            candidate = write_book(root, 2, extras=avatars)
            (candidate / "assets" / "photos" / "athlete.jpg").write_bytes(b"jpg")
            self.assertEqual(validate_release(candidate)["photos"], 2)

    def test_reused_cover_photo_counts_once(self):
        with tempfile.TemporaryDirectory() as raw:
            candidate = write_book(Path(raw), 2, extras='<img src="assets/photos/0.jpg">')
            self.assertEqual(validate_release(candidate)["photos"], 2)

    def test_rejects_blank_folio_and_missing_asset(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate = write_book(
                root, 1, extras='<article class="endpaper"></article><p class="folio"></p><img src="missing.jpg">',
            )
            with self.assertRaises(ValidationError) as caught:
                validate_release(candidate)
            message = str(caught.exception)
            self.assertIn("blank endpaper", message)
            self.assertIn("internal folio", message)
            self.assertIn("missing asset", message)

    def test_rejects_missing_annual_heatmap_when_routes_are_expected(self):
        with tempfile.TemporaryDirectory() as raw:
            candidate = write_book(Path(raw), 1, heatmap=False)
            with self.assertRaisesRegex(ValidationError, "missing annual heatmap"):
                validate_release(candidate, require_heatmap=True)

    def test_rejects_missing_cover_or_annual_review_pages(self):
        with tempfile.TemporaryDirectory() as raw:
            candidate = write_book(Path(raw), 1)
            index = candidate / "index.html"
            html = index.read_text(encoding="utf-8")
            index.write_text(
                html.replace('data-cover-mode="photo"', 'data-old-cover="1"')
                    .replace('data-year-review="rhythm"', 'data-old-review="1"'),
                encoding="utf-8",
            )
            with self.assertRaises(ValidationError) as caught:
                validate_release(candidate)
            self.assertIn("missing editorial cover", str(caught.exception))
            self.assertIn("missing annual review rhythm", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
