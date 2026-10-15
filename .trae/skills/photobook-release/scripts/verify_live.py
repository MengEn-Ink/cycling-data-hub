#!/usr/bin/env python3
"""Verify a published GitHub Pages photobook has no repeated ride photos.

Project-specific selectors live in the CONFIG block below — edit those lines
to adapt this script to another site. Everything else is generic.

Asserts:
  * the poster cover photo does not also appear on a body photo page;
  * body photo pages are pairwise unique;
  * total unique photos equals the declared data-photo-target (unless
    --ignore-target is given).
The athlete avatar (filename contains "athlete") is reused on feature pages
by design and ignored.

Usage:
    verify_live.py [URL] [--ignore-target]
With no URL it uses LIVE_URL_DEFAULT, then falls back to the GitHub Pages
address derived from the `origin` remote. Exit 0 = pass, 1 = content failure,
2 = fetch/parse problem.
"""
from __future__ import annotations

import re
import subprocess
import sys
import urllib.request

# ── CONFIG: edit these when copying to another project ──────────────────────
LIVE_URL_DEFAULT = "https://mengen-ink.github.io/strava-photobook-2026/"
DOCUMENT_MARKER = 'data-strava-photobook="1"'
TARGET_ATTR = "data-photo-target"          # declared planned unique photo count
COVER_ARTICLE_HAS = 'data-cover-mode="photo"'
BODY_ARTICLE_HAS = "art-page bleed"
PHOTO_SRC_PREFIX = "assets/photos/"
AVATAR_KEYWORD = "athlete"                 # repeated avatars are exempt
# ────────────────────────────────────────────────────────────────────────────

ARTICLE_RE = re.compile(r"<article\b([^>]*)>(.*?)</article>", re.S | re.I)
IMG_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"', re.I)


def pages_url_from_origin() -> str | None:
    """Derive the project Pages URL (owner.github.io/repo) from origin."""
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    m = re.match(r"(?:git@github.com:|https://github.com/)([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not m:
        return None
    owner, repo = m.groups()
    return f"https://{owner}.github.io/{repo}/"


def is_ride_photo(src: str) -> bool:
    return src.startswith(PHOTO_SRC_PREFIX) and AVATAR_KEYWORD not in src


def analyze(html: str) -> dict:
    m = re.search(rf'{TARGET_ATTR}="(\d+)"', html)
    target = int(m.group(1)) if m else None
    cover = None
    body: list[str] = []
    for attrs, inner in ARTICLE_RE.findall(html):
        srcs = [s for s in IMG_RE.findall(inner) if is_ride_photo(s)]
        if COVER_ARTICLE_HAS in attrs and srcs and cover is None:
            cover = srcs[0]
        elif BODY_ARTICLE_HAS in attrs:
            body.extend(srcs)
    return {
        "target": target,
        "cover": cover,
        "body": body,
        "body_dups": sorted({s for s in body if body.count(s) > 1}),
        "cover_in_body": cover in body if cover else False,
        "total_unique": len(set(body) | ({cover} if cover else set())),
    }


def main(argv: list[str]) -> int:
    ignore_target = "--ignore-target" in argv
    positional = [a for a in argv[1:] if not a.startswith("--")]
    url = positional[0] if positional else (LIVE_URL_DEFAULT or pages_url_from_origin())
    if not url:
        print("no URL given and none derivable from origin")
        return 2
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            html = resp.read().decode("utf-8", "replace")
    except Exception as exc:
        print(f"FETCH-FAIL {url}: {exc}")
        return 2
    if DOCUMENT_MARKER not in html:
        print("PARSE-FAIL: live page is not the expected document")
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
    if r["target"] is not None and not ignore_target and r["total_unique"] != r["target"]:
        print(f"TARGET-MISMATCH: unique {r['total_unique']} != target {r['target']}")
        ok = False
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
