"""Intervals.icu API 只读客户端（Basic auth，不走 OAuth）。

认证：HTTP Basic，用户名固定字符串 "API_KEY"，密码为个人 API Key。
只读；仅暴露仪表盘所需端点。除 requests 外无第三方依赖。
"""
from __future__ import annotations

import base64
from typing import Any

import requests

API_BASE = "https://intervals.icu/api/v1"


class IntervalsError(RuntimeError):
    pass


class IntervalsClient:
    def __init__(self, api_key: str, athlete_id: str = "0", pause: float = 0.5) -> None:
        self.api_key = str(api_key)
        self.athlete_id = str(athlete_id or "0")
        self.pause = pause

    @property
    def ready(self) -> bool:
        return bool(self.api_key)

    def _auth_header(self) -> str:
        raw = f"API_KEY:{self.api_key}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = requests.get(
            f"{API_BASE}{path}",
            headers={"Authorization": self._auth_header()},
            params=params or {},
            timeout=30,
        )
        if resp.status_code == 429:
            raise IntervalsError("rate limited (429): slow down requests")
        if resp.status_code != 200:
            raise IntervalsError(f"GET {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    # ---- endpoints (只读) ----
    def athlete(self) -> dict[str, Any]:
        return self._get(f"/athlete/{self.athlete_id}")

    def activities(self, oldest: str, newest: str) -> list[dict]:
        """区间内活动（含训练负荷/功率心率摘要）。日期格式 YYYY-MM-DD。"""
        return self._get(
            f"/athlete/{self.athlete_id}/activities",
            params={"oldest": oldest, "newest": newest},
        )

    def gear(self) -> list[dict]:
        return self._get(f"/athlete/{self.athlete_id}/gear")

    def power_curve(self) -> dict[str, Any]:
        # `type` is required by the current Intervals.icu OpenAPI contract.
        # This project is a cycling dashboard, so only request Ride curves.
        return self._get(
            f"/athlete/{self.athlete_id}/power-curves.json",
            params={"type": "Ride"},
        )
