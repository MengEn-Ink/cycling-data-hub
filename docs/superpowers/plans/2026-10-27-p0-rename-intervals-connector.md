# P0 基础阶段实施计划 — 改名 + Intervals.icu 连接器

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把站点品牌改名为"我的骑行数据"，并新增一个只读的 Intervals.icu 连接器（Basic auth）+ 配置项 + `sync-intervals` CLI 子命令，作为后续训练数据分析的地基。

**Architecture:** 沿用现有三层结构。新增 `strava_photobook/intervals/` 子包（镜像现有 `strava/` 客户端模式），由 `config.py` 注入凭证，由 `cli.py` 暴露 `sync-intervals` 子命令把规范化后的训练数据缓存到 `data/intervals/`。改名只触及文案常量，不改数据流。密钥只来自环境变量/.env，绝不进入产物。

**Tech Stack:** Python 3.12，`requests`（已有依赖），`unittest`（现有测试框架，`python -m unittest` 运行）。

**参考规格:** `docs/superpowers/specs/2026-10-27-cycling-data-hub-design.md`（§5.1 连接器、§8 安全边界）。

---

## 文件结构

- 新建 `strava_photobook/intervals/__init__.py` — 子包导出。
- 新建 `strava_photobook/intervals/client.py` — `IntervalsClient`：Basic auth、`_get`、`athlete`/`activities`/`gear`/`power_curve`。
- 新建 `strava_photobook/intervals/source.py` — `sync_intervals(cfg)`：拉取→规范化→写缓存。
- 修改 `strava_photobook/config.py` — 新增 `IntervalsCreds` 与 `Config.intervals`、`intervals_dir`。
- 修改 `strava_photobook/cli.py` — 新增 `sync-intervals` 子命令。
- 修改 `README.md` 与站点文案常量 — 改名"我的骑行数据"。
- 新建 `tests/test_intervals_client.py`、`tests/test_intervals_source.py`、扩展 `tests/test_cli.py`、`tests/test_config.py`（若无则新建）。

---

## Task 1: Intervals.icu 客户端骨架（Basic auth）

**Files:**
- Create: `strava_photobook/intervals/__init__.py`
- Create: `strava_photobook/intervals/client.py`
- Test: `tests/test_intervals_client.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_intervals_client.py
import base64
import unittest
from unittest import mock

from strava_photobook.intervals.client import IntervalsClient, IntervalsError


class AuthHeaderTests(unittest.TestCase):
    def test_basic_auth_header_uses_api_key_prefix(self):
        client = IntervalsClient(api_key="SECRET", athlete_id="0")
        expected = "Basic " + base64.b64encode(b"API_KEY:SECRET").decode("ascii")
        self.assertEqual(client._auth_header(), expected)

    def test_ready_requires_api_key(self):
        self.assertFalse(IntervalsClient(api_key="", athlete_id="0").ready)
        self.assertTrue(IntervalsClient(api_key="k", athlete_id="0").ready)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_intervals_client -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strava_photobook.intervals'`

- [ ] **Step 3: Write minimal implementation**

```python
# strava_photobook/intervals/__init__.py
"""Intervals.icu 只读连接器子包。"""
from .client import IntervalsClient, IntervalsError

__all__ = ["IntervalsClient", "IntervalsError"]
```

```python
# strava_photobook/intervals/client.py
"""Intervals.icu API 只读客户端（Basic auth，不走 OAuth）。

认证：HTTP Basic，用户名固定字符串 "API_KEY"，密码为个人 API Key。
只读；仅暴露仪表盘所需端点。除 requests 外无第三方依赖。
"""
from __future__ import annotations

import base64
import time
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_intervals_client -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/intervals/__init__.py strava_photobook/intervals/client.py tests/test_intervals_client.py
git commit -m "feat(intervals): add Intervals.icu client skeleton with basic auth"
```

---

## Task 2: 客户端端点方法

**Files:**
- Modify: `strava_photobook/intervals/client.py`
- Test: `tests/test_intervals_client.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_intervals_client.py  （追加到文件末尾）
class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = IntervalsClient(api_key="k", athlete_id="42")

    def _patch_get(self, payload):
        return mock.patch.object(self.client, "_get", return_value=payload)

    def test_athlete_hits_athlete_path(self):
        with mock.patch.object(self.client, "_get", return_value={"id": 42}) as g:
            self.assertEqual(self.client.athlete(), {"id": 42})
            g.assert_called_once_with("/athlete/42")

    def test_activities_passes_oldest_param(self):
        with mock.patch.object(self.client, "_get", return_value=[{"id": "a"}]) as g:
            out = self.client.activities(oldest="2026-01-01", newest="2026-12-31")
            self.assertEqual(out, [{"id": "a"}])
            g.assert_called_once_with(
                "/athlete/42/activities",
                params={"oldest": "2026-01-01", "newest": "2026-12-31"},
            )

    def test_gear_and_power_curve_paths(self):
        with mock.patch.object(self.client, "_get", return_value=[]) as g:
            self.client.gear()
            g.assert_called_with("/athlete/42/gear")
        with mock.patch.object(self.client, "_get", return_value={}) as g:
            self.client.power_curve()
            g.assert_called_with("/athlete/42/power-curves.json")

    def test_429_raises_intervals_error(self):
        resp = mock.Mock(status_code=429, text="too many")
        with mock.patch("strava_photobook.intervals.client.requests.get", return_value=resp):
            with self.assertRaises(IntervalsError):
                self.client._get("/athlete/42")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_intervals_client.EndpointTests -v`
Expected: FAIL — `AttributeError: 'IntervalsClient' object has no attribute 'athlete'`

- [ ] **Step 3: Write minimal implementation**

在 `strava_photobook/intervals/client.py` 的 `_get` 方法之后、类内追加：

```python
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
        return self._get(f"/athlete/{self.athlete_id}/power-curves.json")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_intervals_client -v`
Expected: PASS（全部用例）

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/intervals/client.py tests/test_intervals_client.py
git commit -m "feat(intervals): add read-only athlete/activities/gear/power-curve endpoints"
```

---

## Task 3: 配置注入 Intervals 凭证

**Files:**
- Modify: `strava_photobook/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import unittest
from pathlib import Path
from unittest import mock

from strava_photobook.config import Config


class IntervalsConfigTests(unittest.TestCase):
    def test_intervals_creds_from_env(self):
        env = {"INTERVALS_API_KEY": "abc", "INTERVALS_ATHLETE_ID": "7"}
        with mock.patch.dict("os.environ", env, clear=False):
            cfg = Config.load(root=Path.cwd())
        self.assertEqual(cfg.intervals.api_key, "abc")
        self.assertEqual(cfg.intervals.athlete_id, "7")
        self.assertTrue(cfg.intervals.ready)

    def test_intervals_defaults_athlete_zero_and_not_ready(self):
        env = {"INTERVALS_API_KEY": "", "INTERVALS_ATHLETE_ID": ""}
        with mock.patch.dict("os.environ", env, clear=False):
            cfg = Config.load(root=Path.cwd())
        self.assertEqual(cfg.intervals.athlete_id, "0")
        self.assertFalse(cfg.intervals.ready)

    def test_intervals_dir_under_data(self):
        cfg = Config.load(root=Path.cwd())
        self.assertEqual(cfg.intervals_dir, cfg.data_dir / "intervals")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_config -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'intervals'`

- [ ] **Step 3: Write minimal implementation**

在 `strava_photobook/config.py` 中，`GitHubConfig` 之后新增 dataclass：

```python
@dataclass
class IntervalsCreds:
    api_key: str = ""
    athlete_id: str = "0"

    @property
    def ready(self) -> bool:
        return bool(self.api_key)
```

在 `Config` dataclass 字段里，`github: GitHubConfig` 之后新增一行：

```python
    intervals: IntervalsCreds = field(default_factory=IntervalsCreds)
```

文件顶部 `from dataclasses import dataclass` 改为 `from dataclasses import dataclass, field`。

在 `Config.load` 的 `return cls(` 里，`github=GitHubConfig(...)` 之后新增：

```python
            intervals=IntervalsCreds(
                api_key=os.getenv("INTERVALS_API_KEY", ""),
                athlete_id=os.getenv("INTERVALS_ATHLETE_ID", "").strip() or "0",
            ),
```

在 `Config` 的 `@property summaries_path` 附近新增：

```python
    @property
    def intervals_dir(self) -> Path:
        return self.data_dir / "intervals"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_config -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/config.py tests/test_config.py
git commit -m "feat(config): inject Intervals.icu credentials and cache dir"
```

---

## Task 4: 同步与规范化 `sync_intervals`

**Files:**
- Create: `strava_photobook/intervals/source.py`
- Test: `tests/test_intervals_source.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_intervals_source.py
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from strava_photobook.config import Config
from strava_photobook.intervals import source


class SyncIntervalsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _cfg(self):
        env = {"INTERVALS_API_KEY": "k", "INTERVALS_ATHLETE_ID": "0"}
        with mock.patch.dict("os.environ", env, clear=False):
            return Config.load(root=self.root)

    def test_writes_normalized_cache(self):
        cfg = self._cfg()
        fake = mock.Mock()
        fake.ready = True
        fake.activities.return_value = [
            {"id": "i1", "start_date_local": "2026-05-01T07:00:00",
             "icu_training_load": 65, "icu_ftp": 250, "type": "Ride"},
        ]
        fake.gear.return_value = [{"id": "b1", "name": "Road", "distance": 1000000}]
        fake.power_curve.return_value = {"list": [{"secs": 5, "watts": 900}]}
        out = source.sync_intervals(cfg, client=fake, year="2026")
        self.assertEqual(out["activities"][0]["training_load"], 65)
        self.assertEqual(out["gear"][0]["distance_km"], 1000.0)
        cache = cfg.intervals_dir / "2026.json"
        self.assertTrue(cache.is_file())
        saved = json.loads(cache.read_text(encoding="utf-8"))
        self.assertEqual(saved["activities"][0]["id"], "i1")

    def test_not_ready_raises(self):
        cfg = self._cfg()
        fake = mock.Mock()
        fake.ready = False
        with self.assertRaises(SystemExit):
            source.sync_intervals(cfg, client=fake, year="2026")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_intervals_source -v`
Expected: FAIL — `ModuleNotFoundError` 或 `AttributeError: module ... has no attribute 'sync_intervals'`

- [ ] **Step 3: Write minimal implementation**

```python
# strava_photobook/intervals/source.py
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


def sync_intervals(cfg: Config, client: IntervalsClient | None = None,
                   *, year: str) -> dict:
    """拉取某年训练数据并写入 cfg.intervals_dir/<year>.json。返回规范化结果。"""
    client = client or _make_client(cfg)
    if not client.ready:
        raise SystemExit("缺少 INTERVALS_API_KEY，无法同步 Intervals.icu")
    oldest, newest = f"{year}-01-01", f"{year}-12-31"
    activities = [_normalize_activity(a) for a in client.activities(oldest, newest)]
    gear = [_normalize_gear(g) for g in client.gear()]
    power_curve = client.power_curve()
    result = {"year": year, "activities": activities, "gear": gear,
              "power_curve": power_curve}
    cfg.intervals_dir.mkdir(parents=True, exist_ok=True)
    (cfg.intervals_dir / f"{year}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_intervals_source -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/intervals/source.py tests/test_intervals_source.py
git commit -m "feat(intervals): sync and normalize activities/gear/power-curve to cache"
```

---

## Task 5: `sync-intervals` CLI 子命令

**Files:**
- Modify: `strava_photobook/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py  （追加）
import unittest
from unittest import mock

from strava_photobook import cli


class SyncIntervalsCommandTests(unittest.TestCase):
    def test_sync_intervals_invokes_source_with_year(self):
        with mock.patch("strava_photobook.intervals.source.sync_intervals") as sync, \
             mock.patch("strava_photobook.config.Config.load") as load:
            load.return_value = mock.Mock()
            sync.return_value = {"activities": [1, 2], "gear": []}
            cli.main(["sync-intervals", "--year", "2026"])
            self.assertEqual(sync.call_args.kwargs["year"], "2026")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_cli.SyncIntervalsCommandTests -v`
Expected: FAIL — argparse 报 `invalid choice: 'sync-intervals'`（SystemExit）

- [ ] **Step 3: Write minimal implementation**

在 `strava_photobook/cli.py` 新增命令函数（放在 `_cmd_fetch` 附近）：

```python
def _cmd_sync_intervals(cfg: Config, args) -> None:
    from .intervals import source as intervals_source

    result = intervals_source.sync_intervals(cfg, year=args.year)
    print(f"已缓存 {len(result['activities'])} 条 Intervals.icu 活动 -> "
          f"{cfg.intervals_dir / (args.year + '.json')}")
```

在 `main()` 的子命令定义区（`fetch = sub.add_parser(...)` 附近）新增：

```python
    si = sub.add_parser("sync-intervals", help="同步 Intervals.icu 训练数据")
    si.add_argument("--year", required=True, help="同步指定年份")
```

在 `main()` 末尾的调度字典里新增一项：

```python
        "sync-intervals": _cmd_sync_intervals,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_cli -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add strava_photobook/cli.py tests/test_cli.py
git commit -m "feat(cli): add sync-intervals subcommand"
```

---

## Task 6: 站点改名"我的骑行数据"

**Files:**
- Modify: `README.md`
- Modify: `strava_photobook/book.py`（标题/品牌文案常量，定位见步骤）
- Test: `tests/test_docs.py`（扩展）

- [ ] **Step 1: Write the failing test**

先定位现有品牌字符串，确认替换点：

```bash
grep -rn "strava-photobook\|Strava 画册\|年度画册\|photobook" README.md strava_photobook/book.py | head
```

然后新增断言：

```python
# tests/test_docs.py  （追加）
import pathlib
import unittest


class BrandRenameTests(unittest.TestCase):
    def test_readme_uses_new_brand(self):
        text = pathlib.Path("README.md").read_text(encoding="utf-8")
        self.assertIn("我的骑行数据", text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_docs.BrandRenameTests -v`
Expected: FAIL — `AssertionError: '我的骑行数据' not found`

- [ ] **Step 3: Write minimal implementation**

在 `README.md` 顶部主标题处加入/替换为"我的骑行数据"品牌名（保留原英文/仓库名说明）。在 `strava_photobook/book.py` 中，把面向读者的站点/封面品牌文案常量改为"我的骑行数据"（通过 Step 1 的 grep 结果定位具体行；仅改展示文案，不改仓库名/路径/数据键）。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_docs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md strava_photobook/book.py tests/test_docs.py
git commit -m "chore: rename site brand to 我的骑行数据"
```

---

## Task 7: 环境样例与全量回归

**Files:**
- Modify: `.env.example`（若不存在则创建）
- Test: 全量

- [ ] **Step 1: 更新 `.env.example`**

追加（不含真实值）：

```bash
INTERVALS_API_KEY=
INTERVALS_ATHLETE_ID=0
```

- [ ] **Step 2: 运行全量 Python 单测**

Run: `python -m unittest discover -v`
Expected: PASS（全部，含新增 intervals/config/cli/docs 用例）

- [ ] **Step 3: 运行前端契约测试确认未破坏**

Run: `node --test runtime/*.test.mjs`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add .env.example
git commit -m "docs: document Intervals.icu env vars in .env.example"
```

---

## Self-Review 结论

- **Spec 覆盖**：§5.1 连接器 → Task 1/2；§8 密钥只来自环境变量 → Task 3 + Task 7；改名 → Task 6；缓存目录 `data/intervals/` → Task 3/4。P0 范围内无遗漏。
- **占位符扫描**：无 TBD/TODO；每个代码步骤均含完整代码；Task 6 的文案定位用 grep 给出确定方法而非留空。
- **类型/签名一致性**：`IntervalsClient(api_key, athlete_id, pause)`、`_auth_header()`、`_get()`、`athlete()/activities(oldest,newest)/gear()/power_curve()`、`sync_intervals(cfg, client=None, *, year)`、`cfg.intervals`/`cfg.intervals_dir` 在各 Task 间引用一致。
- **后续阶段**：P1–P4（指标引擎、单页外壳、地图、训练/教练/审批、夜间整合+上线）将在各自计划中展开；本计划交付后，`sync-intervals` 可独立运行并缓存训练数据。
