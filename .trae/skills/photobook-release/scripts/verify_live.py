#!/usr/bin/env python3
"""Fetch the live photobook and assert ride photos are unique.

Checks the published GitHub Pages site: the poster cover photo must not
reappear on a body photo page, body photos must be pairwise unique, and the
total unique photo count should match the declared data-photo-target. The
athlete avatar (athlete.jpg) is reused on feature pages by design and ignored.

Usage:
    python3 verify_live.py [URL]
Exit code 0 = pass, 1 = duplicate/target mismatch, 2 = fetch/parse problem.
"""
from __future__ import annotations

import re
import sys
import urllib.request

DEFAULT_URL = "https://mengen-ink.github.io/strava-photobook-2026/"
ARTICLE_RE = re.compile(r"<article\b([^>]*)>(.*?)</article>", re.S | re.I)
IMG_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"', re.I)
TARGET_RE = re.compile(r'data-photo-target="(\d+)"')


def analyze(html: str) -> dict:
    target = int(m.group(1)) if (m := TARGET_RE.search(html)) else None
    cover = None
    body: list[str] = []
    for attrs, inner in ARTICLE_RE.findall(html):
        srcs = [
            s for s in IMG_RE.findall(inner)
            if s.startswith("assets/photos/") and "athlete" not in s
        ]
        if 'data-cover-mode="photo"' in attrs and srcs and cover is None:
            cover = srcs[0]
        elif "art-page bleed" in attrs:
            body.extend(srcs)
    return {
        "target": target,
        "cover": cover,
        "body": body,
        "body_dups": sorted({s for s in body if body.count(s) > 1}),
        "cover_in_body": cover in body if cover else False,
        "total_unique": len(set(body) | ({cover} if cover else set())),
    }


def main(url: str = DEFAULT_URL) -> int:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            html = resp.read().decode("utf-8", "replace")
    except Exception as exc:  # network / decode problem
        print(f"FETCH-FAIL {url}: {exc}")
        return 2
    if 'data-strava-photobook="1"' not in html:
        print("PARSE-FAIL: live page is not a photobook document")
        return 2

    r = analyze(html)
    print(f"target={r['target']} cover={r['cover']}")
    print(
        f"body={len(r['body'])} body_unique={len(set(r['body']))} "
        f"cover_in_body={r['cover_in_body']} total_unique={r['total_unique']}"
    )
    ok = not r["body_dups"] and not r["cover_in_body"]
    if r["body_dups"]:
        print("DUPLICATE-IN-BODY:", ", ".join(r["body_dups"]))
    if r["target"] is not None and r["total_unique"] != r["target"]:
        print(f"TARGET-MISMATCH: unique {r['total_unique']} != target {r['target']}")
        ok = False
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL))
