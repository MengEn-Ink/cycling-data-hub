"""单页仪表盘数据装配：把指标 + 路线写成公开 JSON（无密钥、无原始响应）。"""
from __future__ import annotations

import json
import re
import shutil
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from .metrics import build_metrics
from .model import Activity, by_year

DEFAULT_SEASON_START = date_cls(2027, 4, 1)


def routes_payload(activities: list[Activity]) -> list[dict]:
    """供地图使用的轻量路线列表（仅含有 polyline 的活动）。"""
    out: list[dict] = []
    for a in activities:
        sport_type = a.meta.get("sport_type") or a.meta.get("type") or "Ride"
        if not a.polyline or sport_type != "Ride":
            continue
        out.append({
            "id": a.id,
            "name": a.name,
            "date": (a.date or "")[:10],
            "distance_km": a.distance_km,
            "polyline": a.polyline,
        })
    return out


def activities_payload(activities: list[Activity]) -> list[dict]:
    """公开活动日志所需的最小字段；不透出原始 API 响应。"""
    payload: list[dict] = []
    for a in activities:
        payload.append({
            "id": a.id,
            "name": a.name or "未命名骑行",
            "date": (a.date or "")[:10],
            "sport_type": a.meta.get("sport_type") or a.meta.get("type") or "Ride",
            "distance_km": a.distance_km,
            "elev_m": a.elev_m,
            "moving_seconds": a.moving_time,
            "avg_speed_kmh": a.avg_speed_kmh,
            "kudos": a.kudos,
            "comments": int(a.meta.get("comment_count") or 0),
            "athletes": a.athlete_count,
            "pr_count": a.pr_count,
            "achievements": int(a.meta.get("achievement_count") or 0),
            "photo_count": a.photo_count,
            "polyline": a.polyline,
        })
    return sorted(payload, key=lambda item: (item["date"], item["id"]), reverse=True)


def _load_intervals(intervals_path: Path) -> dict | None:
    """读 Intervals.icu 缓存；缺失或损坏时返回 None（降级）。"""
    if not intervals_path.is_file():
        return None
    try:
        return json.loads(intervals_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def build_dashboard_data(activities: list[Activity], *, intervals_path: Path,
                         year: str, today: date_cls,
                         season_start: date_cls = DEFAULT_SEASON_START) -> dict[str, Any]:
    """装配单页仪表盘的公开数据（metrics + routes），Intervals 缺失即降级。"""
    year_acts = by_year(activities).get(year, [])
    intervals = _load_intervals(intervals_path)
    return {
        "year": year,
        "metrics": build_metrics(year_acts, intervals,
                                 today=today, season_start=season_start),
        "routes": routes_payload(year_acts),
        "activities": activities_payload(year_acts),
    }


def write_dashboard_json(data: dict, out_dir: Path) -> Path:
    """把 metrics/routes 分文件写到 out_dir/data/。返回 data 目录。"""
    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "metrics.json").write_text(
        json.dumps(data["metrics"], ensure_ascii=False, indent=1), encoding="utf-8")
    (data_dir / "routes.json").write_text(
        json.dumps(data["routes"], ensure_ascii=False, indent=1), encoding="utf-8")
    (data_dir / "activities.json").write_text(
        json.dumps(data["activities"], ensure_ascii=False, indent=1), encoding="utf-8")
    return data_dir


def _book_photos(book_dir: Path) -> list[Path]:
    photos = book_dir / "assets" / "photos"
    return sorted(
        path for path in photos.glob("*.jpg")
        if "athlete" not in path.name.lower()
    )


def _cover_photo(book_dir: Path) -> Path | None:
    index = book_dir / "index.html"
    if index.is_file():
        html = index.read_text(encoding="utf-8")
        match = re.search(
            r'data-cover-mode="photo"[\s\S]*?<img[^>]+src="assets/photos/([^"]+)"',
            html,
        )
        if match:
            candidate = book_dir / "assets" / "photos" / match.group(1)
            if candidate.is_file():
                return candidate
    photos = _book_photos(book_dir)
    return photos[0] if photos else None


def build_dashboard_site(data: dict, out_dir: Path, template_dir: Path) -> Path:
    """把已生成画册嵌入 `photobook/`，并把仪表盘提升为发布根页。"""
    out_dir = Path(out_dir)
    template_dir = Path(template_dir)
    source_index = out_dir / "index.html"
    photobook = out_dir / "photobook"

    def excluded(item: Path) -> bool:
        return (
            item.name in {".DS_Store", "dashboard", "__pycache__"}
            or item.name.endswith(".test.mjs")
            or item.name.endswith(".pyc")
        )

    def remove(item: Path) -> None:
        if item.is_dir():
            shutil.rmtree(item)
        elif item.exists():
            item.unlink()

    if not photobook.is_dir():
        if not source_index.is_file() or 'data-theme="distance-manifesto"' not in source_index.read_text("utf-8"):
            raise FileNotFoundError("请先生成 Distance Manifesto 画册，再构建仪表盘")
        staging = out_dir / ".photobook.tmp"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        for item in list(out_dir.iterdir()):
            if item.name in {".DS_Store", ".photobook.tmp", "data", "photobook"}:
                if item.name == ".DS_Store":
                    remove(item)
                continue
            if excluded(item):
                remove(item)
                continue
            shutil.move(str(item), str(staging / item.name))
        staging.replace(photobook)

    for folder in (out_dir, photobook):
        for item in list(folder.iterdir()):
            if excluded(item):
                remove(item)
        for metadata in folder.rglob(".DS_Store"):
            remove(metadata)

    template_index = template_dir / "index.html"
    if not template_index.is_file():
        raise FileNotFoundError(f"缺少仪表盘模板：{template_index}")
    for item in template_dir.iterdir():
        target = out_dir / item.name
        if item.name == "index.html" or excluded(item):
            continue
        if item.is_dir():
            shutil.copytree(
                item,
                target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"),
            )
        else:
            shutil.copy2(item, target)

    photos = _book_photos(photobook)
    cover = _cover_photo(photobook)
    hero = cover or (photos[0] if photos else None)
    album = next((photo for photo in photos if photo != hero), hero)
    def public_photo(path: Path | None) -> str:
        return "photobook/assets/photos/" + path.name if path else ""

    html = template_index.read_text(encoding="utf-8")
    replacements = {
        "__YEAR__": str(data["year"]),
        "__HERO_PHOTO__": public_photo(hero),
        "__ALBUM_PHOTO__": public_photo(album),
        "__PHOTOBOOK_URL__": "photobook/index.html",
    }
    for marker, value in replacements.items():
        html = html.replace(marker, value)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    write_dashboard_json(data, out_dir)
    return out_dir / "index.html"
