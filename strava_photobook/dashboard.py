"""单页仪表盘数据装配：把指标 + 路线写成公开 JSON（无密钥、无原始响应）。"""
from __future__ import annotations

import json
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
        if not a.polyline:
            continue
        out.append({
            "id": a.id,
            "name": a.name,
            "date": (a.date or "")[:10],
            "distance_km": a.distance_km,
            "polyline": a.polyline,
        })
    return out


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
    }


def write_dashboard_json(data: dict, out_dir: Path) -> Path:
    """把 metrics/routes 分文件写到 out_dir/data/。返回 data 目录。"""
    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "metrics.json").write_text(
        json.dumps(data["metrics"], ensure_ascii=False, indent=1), encoding="utf-8")
    (data_dir / "routes.json").write_text(
        json.dumps(data["routes"], ensure_ascii=False, indent=1), encoding="utf-8")
    return data_dir
