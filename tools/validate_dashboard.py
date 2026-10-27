"""Fail closed when the generated public dashboard is incomplete or unsafe."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


class ValidationError(RuntimeError):
    pass


REQUIRED_FILES = (
    "index.html",
    "dashboard.css",
    "dashboard.js",
    "data/metrics.json",
    "data/routes.json",
    "data/activities.json",
    "photobook/index.html",
)
SECRET_KEY = re.compile(r"(?:^|_)(?:token|secret|api_?key|refresh_token)(?:$|_)", re.I)
PLACEHOLDER = re.compile(r"__[A-Z][A-Z0-9_]+__")


def _walk_json(value, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{path}.{key}"
            if SECRET_KEY.search(str(key)):
                errors.append(f"sensitive key in public JSON: {key_path}")
            errors.extend(_walk_json(child, key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk_json(child, f"{path}[{index}]"))
    return errors


def validate_dashboard(site: Path) -> dict[str, int]:
    site = Path(site)
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (site / relative).is_file():
            errors.append(f"missing asset: {relative}")

    index = site / "index.html"
    html = index.read_text(encoding="utf-8") if index.is_file() else ""
    for marker in ('data-strava-photobook="1"', 'data-cycling-dashboard="1"'):
        if marker not in html:
            errors.append(f"missing dashboard marker: {marker}")
    placeholders = sorted(set(PLACEHOLDER.findall(html)))
    if placeholders:
        errors.append("unresolved placeholders: " + ", ".join(placeholders))
    if 'src="photobook/index.html"' not in html:
        errors.append("dashboard does not embed photobook/index.html")

    counts: dict[str, int] = {}
    for name in ("metrics", "routes", "activities"):
        path = site / "data" / f"{name}.json"
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"invalid JSON: data/{name}.json ({exc})")
            continue
        errors.extend(f"data/{name}.json: {error}" for error in _walk_json(payload))
        counts[name] = len(payload) if isinstance(payload, list) else len(payload.keys())

    if errors:
        raise ValidationError("; ".join(errors))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    counts = validate_dashboard(args.site)
    print(
        "dashboard valid: "
        f"metrics={counts.get('metrics', 0)} "
        f"routes={counts.get('routes', 0)} "
        f"activities={counts.get('activities', 0)}"
    )


if __name__ == "__main__":
    main()
