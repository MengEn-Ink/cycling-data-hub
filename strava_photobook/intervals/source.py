"""Intervals.icu 同步：拉取→规范化→写缓存（只读，不写回平台）。"""
from __future__ import annotations

import json

from ..config import Config
from .client import IntervalsClient


def _make_client(cfg: Config) -> IntervalsClient:
    return IntervalsClient(cfg.intervals.api_key, cfg.intervals.athlete_id)


def _normalize_activity(a: dict) -> dict:
    return {
        "id": str(a.get("id") or ""),
        "date": a.get("start_date_local") or "",
        "type": a.get("type") or "",
        "training_load": a.get("icu_training_load"),
        "ftp": a.get("icu_ftp"),
    }


def _normalize_gear(g: dict) -> dict:
    return {
        "id": str(g.get("id") or ""),
        "name": g.get("name") or "",
        "distance_km": round((g.get("distance") or 0) / 1000, 1),
    }


def _normalize_power_curve(raw) -> dict:
    """提取持续时间/功率点，丢弃活动 ID 等原始响应字段。"""
    best: dict[int, float] = {}

    def add(seconds, watts) -> None:
        try:
            duration = int(float(seconds))
            power = float(watts)
        except (TypeError, ValueError):
            return
        if duration <= 0 or power <= 0:
            return
        best[duration] = max(best.get(duration, 0.0), power)

    def visit(value, depth: int = 0) -> None:
        if depth > 5:
            return
        if isinstance(value, dict):
            seconds = value.get("secs", value.get("seconds", value.get("duration")))
            watts = value.get("watts", value.get("power", value.get("value")))
            if isinstance(seconds, list) and isinstance(watts, list):
                for duration, power in zip(seconds, watts):
                    add(duration, power)
            elif not isinstance(seconds, (list, dict)) and not isinstance(watts, (list, dict)):
                add(seconds, watts)
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                visit(child, depth + 1)

    visit(raw)
    points = [
        {"secs": seconds, "watts": round(watts, 1)}
        for seconds, watts in sorted(best.items())[:2000]
    ]
    return {"list": points}


def sync_intervals(cfg: Config, client: IntervalsClient | None = None,
                   *, year: str) -> dict:
    """拉取某年训练数据并写入 cfg.intervals_dir/<year>.json。返回规范化结果。"""
    client = client or _make_client(cfg)
    if not client.ready:
        raise SystemExit("缺少 INTERVALS_API_KEY，无法同步 Intervals.icu")
    oldest, newest = f"{year}-01-01", f"{year}-12-31"
    activities = [_normalize_activity(a) for a in client.activities(oldest, newest)]
    gear = [_normalize_gear(g) for g in client.gear()]
    power_curve = _normalize_power_curve(client.power_curve())
    result = {"year": year, "activities": activities, "gear": gear,
              "power_curve": power_curve}
    cfg.intervals_dir.mkdir(parents=True, exist_ok=True)
    (cfg.intervals_dir / f"{year}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return result
