# P1b 数据装配实施计划 — dashboard.py（公开 JSON 契约）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `strava_photobook/dashboard.py`，把 P1 的 `build_metrics` 结果与路线数据装配成浏览器可读的**公开 JSON**（`metrics.json`、`routes.json`），并新增 `build-dashboard` CLI 子命令把这些 JSON 写入画册产出目录，随画册一起发布。本计划只负责**数据装配**，不含单页 HTML 外壳（留待 P1c 在 mockup 确认后实现）。

**Architecture:** `dashboard.py` 读取已缓存的 Strava 活动（`source.load_activities`）与 Intervals.icu 缓存（`cfg.intervals_dir/<year>.json`，可缺失），调用 `metrics.build_metrics` 与一个新的轻量 `routes_payload`（复用已有 polyline），输出 dict 并写 JSON 到 `cfg.book_dir(year)/data/`。密钥/原始响应绝不进入输出。Intervals 缓存缺失时按降级处理（`intervals=None`）。

**Tech Stack:** Python 3.9（命令是 `python3`），标准库 `json`/`datetime`，`unittest`。

**参考规格:** `docs/superpowers/specs/2026-10-27-cycling-data-hub-design.md` §5.4（dashboard.py）、§6（公开 JSON 契约）、§7（Intervals 断源降级）。

**约定校对（已落地代码）:**
- `metrics.build_metrics(activities, intervals, *, today, season_start)`（P1，f5166a5）。
- `Activity.polyline`、`model.by_year`（已有）。
- `cfg.intervals_dir`、`cfg.book_dir(year)`、`source.load_activities(cfg)`（P0/已有）。
- 赛季默认 `date(2027, 4, 1)`（规格 §1）。

---

## 文件结构

- 新建 `strava_photobook/dashboard.py` — `routes_payload`、`build_dashboard_data`、`write_dashboard_json`。
- 修改 `strava_photobook/cli.py` — 新增 `build-dashboard <year>` 子命令。
- 新建 `tests/test_dashboard.py`。
- 扩展 `tests/test_cli.py`。

---

## Task 1: 路线数据 `routes_payload`

**Files:**
- Create: `strava_photobook/dashboard.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dashboard.py
import unittest
from datetime import date

from strava_photobook.model import Activity
from strava_photobook import dashboard


def ride(rid, date_str, km=0.0, poly=""):
    return Activity(id=rid, name="Ride", date=date_str, year=date_str[:4],
                    distance_km=km, polyline=poly)


class RoutesPayloadTests(unittest.TestCase):
    def test_includes_only_activities_with_polyline(self):
        acts = [
            ride("1", "2026-01-01T08:00:00Z", km=10.0, poly="abc"),
            ride("2", "2026-01-02T08:00:00Z", km=20.0, poly=""),
        ]
        routes = dashboard.routes_payload(acts)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]["id"], "1")
        self.assertEqual(routes[0]["polyline"], "abc")
        self.assertAlmostEqual(routes[0]["distance_km"], 10.0)
        self.assertEqual(routes[0]["date"], "2026-01-01")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_dashboard -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strava_photobook.dashboard'`

- [ ] **Step 3: Write minimal implementation**

```python
# strava_photobook/dashboard.py
"""单页仪表盘数据装配：把指标 + 路线写成公开 JSON（无密钥、无原始响应）。"""
from __future__ import annotations

import json
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from .config import Config
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_dashboard -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/dashboard.py tests/test_dashboard.py
git commit -m "feat(dashboard): add routes payload for map rendering"
```

---

## Task 2: 装配 `build_dashboard_data`（含 Intervals 缺失降级）

**Files:**
- Modify: `strava_photobook/dashboard.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dashboard.py （追加）
import tempfile
from pathlib import Path


class BuildDashboardDataTests(unittest.TestCase):
    def test_degrades_when_intervals_cache_missing(self):
        acts = [ride("1", "2026-06-01T08:00:00Z", km=50.0, poly="xy")]
        with tempfile.TemporaryDirectory() as tmp:
            data = dashboard.build_dashboard_data(
                acts, intervals_path=Path(tmp) / "missing.json",
                year="2026", today=date(2026, 10, 27),
                season_start=date(2027, 4, 1),
            )
        self.assertEqual(data["metrics"]["kpis"]["rides"], 1)
        self.assertFalse(data["metrics"]["intervals_available"])
        self.assertEqual(len(data["routes"]), 1)
        self.assertEqual(data["year"], "2026")

    def test_loads_intervals_cache_when_present(self):
        acts = [ride("1", "2026-06-01T08:00:00Z", km=50.0, poly="xy")]
        with tempfile.TemporaryDirectory() as tmp:
            ivp = Path(tmp) / "2026.json"
            ivp.write_text('{"activities":[{"date":"2026-06-01T08:00:00",'
                           '"training_load":80,"ftp":250}]}', encoding="utf-8")
            data = dashboard.build_dashboard_data(
                acts, intervals_path=ivp, year="2026",
                today=date(2026, 10, 27), season_start=date(2027, 4, 1),
            )
        self.assertTrue(data["metrics"]["intervals_available"])
        self.assertEqual(data["metrics"]["ftp_trend"], [{"date": "2026-06-01", "ftp": 250}])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_dashboard.BuildDashboardDataTests -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'build_dashboard_data'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 strava_photobook/dashboard.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_dashboard -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/dashboard.py tests/test_dashboard.py
git commit -m "feat(dashboard): assemble public metrics+routes with Intervals degradation"
```

---

## Task 3: 写公开 JSON `write_dashboard_json`

**Files:**
- Modify: `strava_photobook/dashboard.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dashboard.py （追加）
import json as _json


class WriteJsonTests(unittest.TestCase):
    def test_writes_split_json_files(self):
        acts = [ride("1", "2026-06-01T08:00:00Z", km=50.0, poly="xy")]
        data = {
            "year": "2026",
            "metrics": {"kpis": {"rides": 1}},
            "routes": [{"id": "1", "polyline": "xy"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            dashboard.write_dashboard_json(data, out)
            metrics = _json.loads((out / "data" / "metrics.json").read_text("utf-8"))
            routes = _json.loads((out / "data" / "routes.json").read_text("utf-8"))
        self.assertEqual(metrics["kpis"]["rides"], 1)
        self.assertEqual(routes[0]["polyline"], "xy")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_dashboard.WriteJsonTests -v`
Expected: FAIL — `AttributeError: ... 'write_dashboard_json'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 strava_photobook/dashboard.py
def write_dashboard_json(data: dict, out_dir: Path) -> Path:
    """把 metrics/routes 分文件写到 out_dir/data/。返回 data 目录。"""
    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "metrics.json").write_text(
        json.dumps(data["metrics"], ensure_ascii=False, indent=1), encoding="utf-8")
    (data_dir / "routes.json").write_text(
        json.dumps(data["routes"], ensure_ascii=False, indent=1), encoding="utf-8")
    return data_dir
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_dashboard -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/dashboard.py tests/test_dashboard.py
git commit -m "feat(dashboard): write split public metrics.json and routes.json"
```

---

## Task 4: `build-dashboard` CLI 子命令

**Files:**
- Modify: `strava_photobook/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py （追加到 CLITests 内）
    def test_build_dashboard_writes_json_for_year(self):
        from datetime import date as _date
        with tempfile.TemporaryDirectory() as root, patch(
            "strava_photobook.source.load_activities",
            return_value=[],
        ), patch(
            "strava_photobook.dashboard.build_dashboard_data",
            return_value={"year": "2026", "metrics": {"kpis": {}}, "routes": []},
        ) as build, patch(
            "strava_photobook.dashboard.write_dashboard_json",
        ) as write:
            cli.main(["--root", root, "build-dashboard", "2026"])
            self.assertEqual(build.call_args.kwargs["year"], "2026")
            self.assertTrue(write.called)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_cli.CLITests.test_build_dashboard_writes_json_for_year -v`
Expected: FAIL — argparse `invalid choice: 'build-dashboard'`（SystemExit）

- [ ] **Step 3: Write minimal implementation**

在 `strava_photobook/cli.py` 新增命令函数（放在 `_cmd_build` 附近）：

```python
def _cmd_build_dashboard(cfg: Config, args) -> None:
    from datetime import date
    from . import source
    from . import dashboard

    acts = source.load_activities(cfg)
    data = dashboard.build_dashboard_data(
        acts, intervals_path=cfg.intervals_dir / f"{args.year}.json",
        year=args.year, today=date.today(),
    )
    out = cfg.book_dir(args.year)
    dashboard.write_dashboard_json(data, out)
    print(f"已写仪表盘 JSON -> {out / 'data'}")
```

在 `main()` 子命令区（`b = sub.add_parser("build", ...)` 之后）新增：

```python
    bd = sub.add_parser("build-dashboard", help="生成单页仪表盘的公开 JSON")
    bd.add_argument("year")
```

在调度字典新增：

```python
        "build-dashboard": _cmd_build_dashboard,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_cli -v`
Expected: PASS

- [ ] **Step 5: 全量回归 + Commit**

```bash
python3 -m unittest discover
git add strava_photobook/cli.py tests/test_cli.py
git commit -m "feat(cli): add build-dashboard subcommand"
```

---

## Self-Review 结论

- **Spec 覆盖**：§5.4 dashboard 装配 → Task2；§6 公开 JSON（metrics.json/routes.json）→ Task3；§7 Intervals 断源降级 → Task2（`_load_intervals` 返回 None）；CLI 入口 → Task4。`coach-draft.json` 属 P3，不在本计划。
- **占位符扫描**：无 TBD/TODO；代码步骤均含完整实现。
- **类型/签名一致性**：`routes_payload(list[Activity])→list[dict]`、`build_dashboard_data(activities,*,intervals_path,year,today,season_start)→dict`、`write_dashboard_json(data,out_dir)→Path`、`DEFAULT_SEASON_START=date(2027,4,1)` 在 Task 间与 CLI 引用一致。
- **边界**：单页 HTML 外壳（`runtime/dashboard/` + 图表 + 发布结构变化）不在本计划——需先在可视化窗口确认布局 mockup（符合用户对浅色主题可见性/视觉门禁的重视），作为 P1c。
