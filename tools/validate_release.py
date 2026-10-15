"""Fail closed when a generated photobook is incomplete or regresses."""
from __future__ import annotations

import argparse
import math
import re
from collections import Counter
from pathlib import Path


class ValidationError(RuntimeError):
    pass


# 旧的固定 40 张画册：照片数仅在跌破发布基线的一个小相对容差时才算回归。
PHOTO_REGRESSION_TOLERANCE = 0.05
# 动态画册（HTML 声明 data-photo-target）：实际入册至少要达成目标的 90%，
# 容忍个别照片下载失败；目标本身随 Strava 上传量增删，故不再与线上基线比较。
PHOTO_TARGET_FULFILLMENT = 0.90

_ARTICLE_RE = re.compile(r"<article\b([^>]*)>(.*?)</article>", re.S | re.I)
_IMG_SRC_RE = re.compile(r'<img\b[^>]*\bsrc="(assets/photos/[^"]+)"', re.I)


def _photo_placements(html: str) -> tuple[str | None, list[str]]:
    """Return the cover photo src and the ordered body (bleed page) photo srcs.

    The athlete avatar is reused on several feature pages and is not a ride
    photo, so it is excluded from uniqueness checks.
    """
    cover_src: str | None = None
    body_srcs: list[str] = []
    for attrs, inner in _ARTICLE_RE.findall(html):
        srcs = [s for s in _IMG_SRC_RE.findall(inner) if "athlete" not in s]
        if 'data-cover-mode="photo"' in attrs:
            if srcs:
                cover_src = srcs[0]
        elif "art-page bleed" in attrs:
            body_srcs.extend(srcs)
    return cover_src, body_srcs


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
    # 每张骑行照片在整本书里只允许出现一次：正文照片页之间不得重复，封面海报
    # 也不得再在正文出现（封面本身占用一个名额，而不是复用一张正文照片）。
    cover_src, body_srcs = _photo_placements(html)
    for src in sorted(s for s, n in Counter(body_srcs).items() if n > 1):
        errors.append(f"duplicate photo in body: {src}")
    if cover_src and cover_src in body_srcs:
        errors.append(f"cover photo repeated in body: {cover_src}")
    target_match = re.search(r'data-photo-target="(\d+)"', html)
    photo_target = int(target_match.group(1)) if target_match else 0
    baseline_photos = 0
    if baseline and (Path(baseline) / "index.html").is_file():
        _, old_images = _inspect(Path(baseline))
        baseline_photos = len({
            source for source in old_images
            if source.startswith("assets/photos/") and "athlete" not in source
        })
    if photo_target:
        # Dynamic book: must mostly fulfill the target it was built for, not
        # the previous release — uploads legitimately grow or shrink year round.
        needed = math.ceil(photo_target * PHOTO_TARGET_FULFILLMENT)
        if photos < needed:
            errors.append(f"photo count below target: {photos} < {needed}")
    elif baseline_photos:
        # Legacy fixed-size book (no data-photo-target): keep baseline guard.
        floor_photos = min(baseline_photos, 40)
        allowed_photos = floor_photos - int(floor_photos * PHOTO_REGRESSION_TOLERANCE)
        if photos < allowed_photos:
            errors.append(f"photo count regressed: {photos} < {allowed_photos}")
    if errors:
        raise ValidationError("; ".join(errors))
    return {"photos": photos, "baseline_photos": baseline_photos, "photo_target": photo_target}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("book", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--require-heatmap", action="store_true")
    args = parser.parse_args()
    result = validate_release(args.book, args.baseline, require_heatmap=args.require_heatmap)
    print(
        f"release valid: photos={result['photos']} target={result['photo_target']} "
        f"baseline={result['baseline_photos']}"
    )


if __name__ == "__main__":
    main()
