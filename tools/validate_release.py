"""Fail closed when a generated photobook is incomplete or regresses."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


class ValidationError(RuntimeError):
    pass


# Strava 每晚返回的可用照片会随单条活动照片的增减轻微浮动；
# 仅在照片数跌破发布基线的一个小相对容差时，才判定为真正的内容回归。
PHOTO_REGRESSION_TOLERANCE = 0.05


def _inspect(book: Path) -> tuple[str, list[str]]:
    index = book / "index.html"
    if not index.is_file():
        raise ValidationError(f"missing index: {index}")
    html = index.read_text(encoding="utf-8")
    return html, re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', html)


def validate_release(
    book: Path, baseline: Path | None = None, *, require_heatmap: bool = False
) -> dict[str, int]:
    book = Path(book)
    html, images = _inspect(book)
    errors: list[str] = []
    if 'data-strava-photobook="1"' not in html:
        errors.append("missing photobook marker")
    if 'id="month-timeline"' not in html:
        errors.append("missing month timeline")
    if not re.search(r'data-cover-mode="(?:photo|route)"', html):
        errors.append("missing editorial cover")
    if 'data-year-review="declaration"' not in html:
        errors.append("missing annual review declaration")
    if 'data-year-review="rhythm"' not in html:
        errors.append("missing annual review rhythm")
    if require_heatmap and 'data-annual-heatmap="1"' not in html:
        errors.append("missing annual heatmap")
    if "endpaper" in html:
        errors.append("blank endpaper present")
    if 'class="folio"' in html:
        errors.append("internal folio present")
    for source in images:
        if source.startswith(("http://", "https://", "data:")):
            continue
        if not (book / source).is_file():
            errors.append(f"missing asset: {source}")
    photos = len({source for source in images if source.startswith("assets/photos/") and "athlete" not in source})
    baseline_photos = 0
    if baseline and (Path(baseline) / "index.html").is_file():
        _, old_images = _inspect(Path(baseline))
        baseline_photos = len({
            source for source in old_images
            if source.startswith("assets/photos/") and "athlete" not in source
        })
        if baseline_photos:
            floor_photos = min(baseline_photos, 40)
            allowed_photos = floor_photos - int(floor_photos * PHOTO_REGRESSION_TOLERANCE)
            if photos < allowed_photos:
                errors.append(f"photo count regressed: {photos} < {allowed_photos}")
    if errors:
        raise ValidationError("; ".join(errors))
    return {"photos": photos, "baseline_photos": baseline_photos}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("book", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--require-heatmap", action="store_true")
    args = parser.parse_args()
    result = validate_release(args.book, args.baseline, require_heatmap=args.require_heatmap)
    print(f"release valid: photos={result['photos']} baseline={result['baseline_photos']}")


if __name__ == "__main__":
    main()
