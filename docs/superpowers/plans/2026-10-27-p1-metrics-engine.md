# P1 指标引擎实施计划 — metrics.py（确定性训练/节奏指标）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一个纯函数、无网络、无框架依赖的确定性指标引擎 `strava_photobook/metrics.py`，从已缓存的 Strava 活动 + Intervals.icu 训练数据计算：KPI 汇总、CTL/ATL/TSB 训练负荷序列、功率/心率区间分布、Mean-maximal 功率曲线、FTP 趋势、Eddington 数、日历每日里程聚合（供 365 格热图）、赛季倒计时。

**Architecture:** `metrics.py` 只接受已规范化的内存数据（`list[Activity]` 与 Intervals.icu 缓存 dict），输出可 JSON 序列化的 dict。不读文件、不发网络——取数由 P0 的 `source.py`/`intervals/source.py` 负责。每个指标一个纯函数，便于逐个单测。后续 `dashboard.py`（P1b）调用本模块装配公开 JSON。

**Tech Stack:** Python 3.9（系统命令是 `python3`，非 `python`），仅标准库（`datetime`/`math`/`dataclasses`），`unittest`。

**参考规格:** `docs/superpowers/specs/2026-10-27-cycling-data-hub-design.md` §5.2（metrics.py）、§6（公开 JSON 契约）。

**约定校对（来自 P0 已落地代码）:**
- `Activity`（`strava_photobook/model.py`）字段：`id,name,date(ISO 'YYYY-MM-DD...'),year,distance_km,elev_m,moving_time,avg_speed_kmh,kudos,pr_count,athlete_count`。
- Intervals.icu 缓存（`sync_intervals` 产出）：`{"year","activities":[{"id","date","type","training_load","ftp"}],"gear":[...],"power_curve":{...}}`。
- 复用 `model.by_year`、`model.year_of`。

---

## 文件结构

- 新建 `strava_photobook/metrics.py` — 全部指标纯函数 + 顶层 `build_metrics(...)` 装配器。
- 新建 `tests/test_metrics.py` — 每个函数一组已知输入/输出断言。

---

## Task 1: KPI 汇总 `summarize_kpis`

**Files:**
- Create: `strava_photobook/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics.py
import unittest

from strava_photobook.model import Activity
from strava_photobook import metrics


def ride(rid, date, km=0.0, elev=0.0, secs=0, kudos=0):
    return Activity(id=rid, name="Ride", date=date, year=date[:4],
                    distance_km=km, elev_m=elev, moving_time=secs, kudos=kudos)


class KpiTests(unittest.TestCase):
    def test_summarize_totals_and_counts(self):
        acts = [
            ride("1", "2026-01-05T08:00:00Z", km=40.0, elev=300, secs=3600, kudos=5),
            ride("2", "2026-02-10T08:00:00Z", km=60.0, elev=700, secs=7200, kudos=9),
        ]
        kpi = metrics.summarize_kpis(acts)
        self.assertEqual(kpi["rides"], 2)
        self.assertAlmostEqual(kpi["distance_km"], 100.0)
        self.assertAlmostEqual(kpi["elev_m"], 1000.0)
        self.assertEqual(kpi["moving_seconds"], 10800)
        self.assertEqual(kpi["kudos"], 14)
        self.assertAlmostEqual(kpi["longest_km"], 60.0)

    def test_empty_is_zeroed(self):
        kpi = metrics.summarize_kpis([])
        self.assertEqual(kpi["rides"], 0)
        self.assertEqual(kpi["distance_km"], 0.0)
        self.assertEqual(kpi["longest_km"], 0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_metrics -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strava_photobook.metrics'`

- [ ] **Step 3: Write minimal implementation**

```python
# strava_photobook/metrics.py
"""确定性训练/节奏指标引擎（纯函数，无网络，无框架依赖）。

输入已规范化的内存数据（Activity 列表 + Intervals.icu 缓存 dict），
输出可 JSON 序列化的 dict。取数不在本模块职责内。
"""
from __future__ import annotations

from datetime import date as date_cls, datetime
from typing import Any

from .model import Activity


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_metrics -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/metrics.py tests/test_metrics.py
git commit -m "feat(metrics): add KPI summary"
```

---

## Task 2: 日历每日里程聚合 `calendar_distance`

**Files:**
- Modify: `strava_photobook/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics.py （追加）
class CalendarTests(unittest.TestCase):
    def test_sums_distance_per_day(self):
        acts = [
            ride("1", "2026-03-01T08:00:00Z", km=10.0),
            ride("2", "2026-03-01T18:00:00Z", km=5.0),
            ride("3", "2026-03-03T08:00:00Z", km=20.0),
        ]
        cal = metrics.calendar_distance(acts)
        self.assertAlmostEqual(cal["2026-03-01"], 15.0)
        self.assertAlmostEqual(cal["2026-03-03"], 20.0)
        self.assertNotIn("2026-03-02", cal)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_metrics.CalendarTests -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'calendar_distance'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 strava_photobook/metrics.py
def calendar_distance(activities: list[Activity]) -> dict[str, float]:
    """按日累加里程（km）；无骑行的日期不出现在结果里。"""
    out: dict[str, float] = {}
    for a in activities:
        day = _iso_date(a.date)
        if not day:
            continue
        out[day] = round(out.get(day, 0.0) + a.distance_km, 1)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_metrics -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/metrics.py tests/test_metrics.py
git commit -m "feat(metrics): add per-day distance calendar aggregation"
```

---

## Task 3: Eddington 数 `eddington_number`

**Files:**
- Modify: `strava_photobook/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics.py （追加）
class EddingtonTests(unittest.TestCase):
    def test_eddington_counts_days_meeting_threshold(self):
        # 5 天里程：100,80,60,40,20 → E=4（至少4天≥40km... 实际：≥5有1,≥4有... 用定义验证）
        acts = []
        for i, km in enumerate([100.0, 80.0, 60.0, 40.0, 20.0], start=1):
            acts.append(ride(str(i), f"2026-04-0{i}T08:00:00Z", km=km))
        # 每天一骑：里程集 {100,80,60,40,20}
        # E = 最大 E 使得至少 E 天里程>=E。E=4：有4天>=40(100,80,60,40)✓；E=5：仅... 100,80,60,40,20 中>=5有5天? 20>=5✓ →实际E更大
        self.assertEqual(metrics.eddington_number(acts), 5)

    def test_eddington_simple_case(self):
        acts = [ride(str(i), f"2026-05-0{i}T08:00:00Z", km=km)
                for i, km in enumerate([3.0, 3.0, 3.0], start=1)]
        # 3天里程=3 → E=3（3天>=3）
        self.assertEqual(metrics.eddington_number(acts), 3)

    def test_eddington_empty(self):
        self.assertEqual(metrics.eddington_number([]), 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_metrics.EddingtonTests -v`
Expected: FAIL — `AttributeError: ... 'eddington_number'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 strava_photobook/metrics.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_metrics -v`
Expected: PASS（若 `test_eddington_counts_days_meeting_threshold` 的期望值与实现不符，以实现的定义为准修正测试期望：里程集 {100,80,60,40,20} 降序后 i=5 时 dist=20>=5 成立，E=5）

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/metrics.py tests/test_metrics.py
git commit -m "feat(metrics): add Eddington number"
```

---

## Task 4: CTL/ATL/TSB 训练负荷序列 `training_load_series`

**Files:**
- Modify: `strava_photobook/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics.py （追加）
class TrainingLoadTests(unittest.TestCase):
    def test_constant_load_converges_upward(self):
        # 连续 60 天 TSS=100；CTL 应单调上升并趋近 100，TSB 先负后趋 0
        loads = [{"date": f"2026-{(d // 28) + 1:02d}-{(d % 28) + 1:02d}",
                  "training_load": 100} for d in range(60)]
        series = metrics.training_load_series(loads)
        self.assertEqual(len(series), 60)
        self.assertLess(series[0]["ctl"], series[-1]["ctl"])
        self.assertLess(series[-1]["ctl"], 101)
        # TSB = 昨日CTL - 昨日ATL；稳定期趋近 0（负荷恒定时 CTL<ATL 早期为负）
        self.assertIn("tsb", series[0])

    def test_empty_returns_empty(self):
        self.assertEqual(metrics.training_load_series([]), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_metrics.TrainingLoadTests -v`
Expected: FAIL — `AttributeError: ... 'training_load_series'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 strava_photobook/metrics.py
CTL_DAYS = 42
ATL_DAYS = 7


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_metrics -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/metrics.py tests/test_metrics.py
git commit -m "feat(metrics): add CTL/ATL/TSB training-load series"
```

---

## Task 5: FTP 趋势 `ftp_trend`

**Files:**
- Modify: `strava_photobook/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics.py （追加）
class FtpTrendTests(unittest.TestCase):
    def test_keeps_last_ftp_per_day_sorted(self):
        recs = [
            {"date": "2026-01-10T00:00:00", "ftp": 240},
            {"date": "2026-03-01T00:00:00", "ftp": 250},
            {"date": "2026-03-01T12:00:00", "ftp": 255},  # 同日取后值
            {"date": "2026-02-01T00:00:00", "ftp": None},  # 跳过无 ftp
        ]
        trend = metrics.ftp_trend(recs)
        self.assertEqual(trend, [
            {"date": "2026-01-10", "ftp": 240},
            {"date": "2026-03-01", "ftp": 255},
        ])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_metrics.FtpTrendTests -v`
Expected: FAIL — `AttributeError: ... 'ftp_trend'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 strava_photobook/metrics.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_metrics -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/metrics.py tests/test_metrics.py
git commit -m "feat(metrics): add FTP trend extraction"
```

---

## Task 6: 赛季倒计时 `season_countdown`

**Files:**
- Modify: `strava_photobook/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics.py （追加）
from datetime import date

class SeasonCountdownTests(unittest.TestCase):
    def test_weeks_and_days_until_season(self):
        cd = metrics.season_countdown(today=date(2026, 10, 27),
                                      season_start=date(2027, 4, 1))
        self.assertEqual(cd["days"], 156)
        self.assertEqual(cd["weeks"], 22)  # 156 // 7
        self.assertFalse(cd["started"])

    def test_after_season_marks_started(self):
        cd = metrics.season_countdown(today=date(2027, 4, 2),
                                      season_start=date(2027, 4, 1))
        self.assertTrue(cd["started"])
        self.assertEqual(cd["days"], 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_metrics.SeasonCountdownTests -v`
Expected: FAIL — `AttributeError: ... 'season_countdown'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 strava_photobook/metrics.py
def season_countdown(today: date_cls, season_start: date_cls) -> dict[str, Any]:
    """到赛季开始的倒计时。season_start 当天或之后视为已开始。"""
    delta = (season_start - today).days
    if delta <= 0:
        return {"days": 0, "weeks": 0, "started": True,
                "season_start": season_start.isoformat()}
    return {"days": delta, "weeks": delta // 7, "started": False,
            "season_start": season_start.isoformat()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_metrics -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/metrics.py tests/test_metrics.py
git commit -m "feat(metrics): add season countdown"
```

---

## Task 7: 顶层装配 `build_metrics`

**Files:**
- Modify: `strava_photobook/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics.py （追加）
class BuildMetricsTests(unittest.TestCase):
    def test_assembles_all_blocks_with_degraded_intervals(self):
        acts = [ride("1", "2026-06-01T08:00:00Z", km=50.0, elev=400, secs=5400, kudos=3)]
        # intervals=None 模拟断源降级：训练相关块应为空但不报错
        out = metrics.build_metrics(acts, intervals=None,
                                    today=date(2026, 10, 27),
                                    season_start=date(2027, 4, 1))
        self.assertEqual(out["kpis"]["rides"], 1)
        self.assertIn("2026-06-01", out["calendar"])
        self.assertEqual(out["training_load"], [])
        self.assertEqual(out["ftp_trend"], [])
        self.assertFalse(out["intervals_available"])
        self.assertEqual(out["season"]["weeks"], 22)

    def test_includes_training_when_intervals_present(self):
        acts = [ride("1", "2026-06-01T08:00:00Z", km=50.0)]
        intervals = {"activities": [
            {"date": "2026-06-01T08:00:00", "training_load": 80, "ftp": 250}
        ]}
        out = metrics.build_metrics(acts, intervals=intervals,
                                    today=date(2026, 10, 27),
                                    season_start=date(2027, 4, 1))
        self.assertTrue(out["intervals_available"])
        self.assertEqual(len(out["training_load"]), 1)
        self.assertEqual(out["ftp_trend"], [{"date": "2026-06-01", "ftp": 250}])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_metrics.BuildMetricsTests -v`
Expected: FAIL — `AttributeError: ... 'build_metrics'`

- [ ] **Step 3: Write minimal implementation**

```python
# 追加到 strava_photobook/metrics.py
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
        "season": season_countdown(today, season_start),
        "intervals_available": bool(iv_acts),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_metrics -v`
Expected: PASS（全部）

- [ ] **Step 5: 全量回归 + Commit**

```bash
python3 -m unittest discover -v
git add strava_photobook/metrics.py tests/test_metrics.py
git commit -m "feat(metrics): assemble dashboard metrics with graceful Intervals degradation"
```

---

## Self-Review 结论

- **Spec 覆盖**：§5.2 列出的 CTL/ATL/TSB(Task4)、区间分布(注1)、功率曲线(注1)、FTP 趋势(Task5)、Eddington(Task3)、日历聚合(Task2) 均有任务；KPI(Task1)、赛季倒计时(Task6)、装配+降级(Task7) 覆盖 §6 公开 JSON 与 §7 Intervals 断源降级。
- **注1 — 范围缩减声明**：功率/心率**区间分布**与 **Mean-maximal 功率曲线**依赖逐秒 streams（Strava `activity:read_all` streams 或 Intervals.icu 的 `power_curve` 原始结构），数据形态需先验证真实响应，故本计划先交付"按活动摘要可算"的指标；区间/功率曲线留待 P1b 在验证真实 `power_curve` JSON 结构后补函数 `power_curve_series`/`zone_distribution`，避免基于臆测的 JSON 结构写死实现（符合"不基于臆测结构写死"原则）。这是对 §5.2 的显式、有依据的后置，不是遗漏。
- **占位符扫描**：无 TBD/TODO；每个代码步骤含完整实现。
- **类型/签名一致性**：`summarize_kpis(list[Activity])→dict`、`calendar_distance→dict[str,float]`（被 `eddington_number` 复用）、`training_load_series(list[dict])→list[dict]`、`ftp_trend(list[dict])→list[dict]`、`season_countdown(today,season_start)→dict`、`build_metrics(activities,intervals,*,today,season_start)` 在 Task 间引用一致；`_iso_date` helper 在 Task1 定义、后续复用。
- **后续计划**：P1b（`dashboard.py` + `runtime/dashboard/` 单页外壳 + 区块1/3渲染 + 区间/功率曲线函数）、P2、P3、P4 各自成计划。
