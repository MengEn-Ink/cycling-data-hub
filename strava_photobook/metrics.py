"""确定性训练/节奏指标引擎（纯函数，无网络，无框架依赖）。

输入已规范化的内存数据（Activity 列表 + Intervals.icu 缓存 dict），
输出可 JSON 序列化的 dict。取数不在本模块职责内——由 source.py /
intervals/source.py 负责。每个指标一个纯函数，便于逐个单测。
"""
from __future__ import annotations

from datetime import date as date_cls, datetime
from typing import Any

from .model import Activity

CTL_DAYS = 42
ATL_DAYS = 7


def _iso_date(raw: str) -> str:
    """Return the 'YYYY-MM-DD' prefix of an ISO datetime string."""
    return (raw or "")[:10]


def summarize_kpis(activities: list[Activity]) -> dict[str, Any]:
    if not activities:
        return {"rides": 0, "distance_km": 0.0, "elev_m": 0.0,
                "moving_seconds": 0, "kudos": 0, "longest_km": 0.0}
    return {
        "rides": len(activities),
        "distance_km": round(sum(a.distance_km for a in activities), 1),
        "elev_m": round(sum(a.elev_m for a in activities), 0),
        "moving_seconds": sum(a.moving_time for a in activities),
        "kudos": sum(a.kudos for a in activities),
        "longest_km": round(max(a.distance_km for a in activities), 1),
    }


def calendar_distance(activities: list[Activity]) -> dict[str, float]:
    """按日累加里程（km）；无骑行的日期不出现在结果里。"""
    out: dict[str, float] = {}
    for a in activities:
        day = _iso_date(a.date)
        if not day:
            continue
        out[day] = round(out.get(day, 0.0) + a.distance_km, 1)
    return out


def eddington_number(activities: list[Activity]) -> int:
    """Eddington 数 E：存在 E 天，每天骑行里程 >= E km。按日合计里程。"""
    per_day = calendar_distance(activities)
    distances = sorted(per_day.values(), reverse=True)
    e = 0
    for i, dist in enumerate(distances, start=1):
        if dist >= i:
            e = i
        else:
            break
    return e


def training_load_series(load_records: list[dict]) -> list[dict]:
    """从 [{"date","training_load"}] 计算每日 CTL/ATL/TSB。

    CTL = 42 天指数加权，ATL = 7 天指数加权；按日递推：
      value_today = value_yesterday + (load_today - value_yesterday) / N
    TSB_today = CTL_yesterday - ATL_yesterday（今晨状态）。
    同日多条负荷先求和；缺失的日期按 load=0 的天推进。
    """
    if not load_records:
        return []
    by_day: dict[str, float] = {}
    for r in load_records:
        day = _iso_date(str(r.get("date") or ""))
        if not day:
            continue
        by_day[day] = by_day.get(day, 0.0) + float(r.get("training_load") or 0)
    if not by_day:
        return []
    days_sorted = sorted(by_day)
    start = datetime.strptime(days_sorted[0], "%Y-%m-%d").date()
    end = datetime.strptime(days_sorted[-1], "%Y-%m-%d").date()

    ctl = atl = 0.0
    out: list[dict] = []
    cursor = start
    while cursor <= end:
        key = cursor.isoformat()
        load = by_day.get(key, 0.0)
        tsb = round(ctl - atl, 1)  # 用昨日 CTL/ATL
        ctl = ctl + (load - ctl) / CTL_DAYS
        atl = atl + (load - atl) / ATL_DAYS
        out.append({"date": key, "load": round(load, 1),
                    "ctl": round(ctl, 1), "atl": round(atl, 1), "tsb": tsb})
        cursor = date_cls.fromordinal(cursor.toordinal() + 1)
    return out


def ftp_trend(records: list[dict]) -> list[dict]:
    """从带 ftp 的活动记录提取 FTP 时间序列；同日取最后一次非空值。"""
    per_day: dict[str, int] = {}
    for r in records:
        ftp = r.get("ftp")
        if ftp in (None, 0, ""):
            continue
        day = _iso_date(str(r.get("date") or ""))
        if not day:
            continue
        per_day[day] = int(ftp)
    return [{"date": d, "ftp": per_day[d]} for d in sorted(per_day)]


def season_countdown(today: date_cls, season_start: date_cls) -> dict[str, Any]:
    """到赛季开始的倒计时。season_start 当天或之后视为已开始。"""
    delta = (season_start - today).days
    if delta <= 0:
        return {"days": 0, "weeks": 0, "started": True,
                "season_start": season_start.isoformat()}
    return {"days": delta, "weeks": delta // 7, "started": False,
            "season_start": season_start.isoformat()}


def build_metrics(activities: list[Activity], intervals: dict | None, *,
                  today: date_cls, season_start: date_cls) -> dict[str, Any]:
    """装配单页仪表盘所需的全部指标为一个可 JSON 序列化的 dict。

    intervals 为 None（断源降级）时，训练相关块返回空列表，其余照常。
    """
    iv_acts = (intervals or {}).get("activities") or []
    return {
        "kpis": summarize_kpis(activities),
        "calendar": calendar_distance(activities),
        "eddington": eddington_number(activities),
        "training_load": training_load_series(iv_acts) if iv_acts else [],
        "ftp_trend": ftp_trend(iv_acts) if iv_acts else [],
        "gear": (intervals or {}).get("gear") or [],
        "power_curve": (intervals or {}).get("power_curve") or {"list": []},
        "season": season_countdown(today, season_start),
        "intervals_available": bool(iv_acts),
    }
