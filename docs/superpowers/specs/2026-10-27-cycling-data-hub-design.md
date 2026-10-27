# 我的骑行数据 — 集成骑行仪表盘设计

- 日期：2026-10-27
- 状态：已批准（用户授权"后面都按推荐执行，直接上线 Pages 完成功能"）
- 站点品牌名：**我的骑行数据**
- 远端仓库：https://github.com/MengEn-Ink/cycling-data-hub
- Live URL：https://mengen-ink.github.io/cycling-data-hub/

## 1. 背景与目标

现有项目是"Strava 年度翻页画册 + GitHub Pages 夜间发布"的纯静态站点。本轮在其基础上：

1. 站点改名为"我的骑行数据"。
2. 引入 Intervals.icu 作为训练数据源（Strava 仍是画册与轨迹主源）。
3. 借鉴 `doniwirawan/Ascent-Strava-Dashboard` 等开源项目的功能集与单页 UX，把**大部分功能集成到一个页面**。
4. 增加围绕"提升 FTP"的 AI 教练训练计划草案；草案经人工确认后写入 Intervals.icu 日历。
5. 全部内容**公开**发布到 Pages；**直接上线完成功能**。

赛季目标：赛季开始 **2027-04-01**，从今天 2026-10-27 起约 22 周训练周期，目标提升 FTP。

## 2. 范围

**本轮包含：**
- 站点改名（品牌文案、首页标题、README）。
- Intervals.icu 只读连接器（Basic auth）。
- 确定性训练指标引擎（CTL/ATL/TSB、功率/心率区间、功率曲线、FTP 趋势、Eddington、日历聚合）。
- 单页集成仪表盘（锚点导航，8 个区块，画册作为其中一节嵌入）。
- 交互式地图（Leaflet + 公开瓦片，复用缓存 polyline）。
- AI 教练 FTP 周期计划草案 + 公开草案页。
- 独立审批工作流（人工 `workflow_dispatch` → 校验 → 写 Intervals.icu 日历）。
- 夜间工作流整合（同步 + 重算指标 + 重生成草案，只读）。
- 直接上线 Pages 并验收。

**本轮不包含（YAGNI）：**
- 浏览器端 OAuth / localStorage 数据模型（保留构建时取数 + 公开 JSON）。
- Story 分享卡生成器（用户已明确去掉）。
- Serverless 中转、多用户、远程数据库。

## 3. 架构

三层，单页仪表盘；构建时取数 → 公开 JSON → 浏览器渲染。

### 数据层（`strava_photobook/`）
| 模块 | 状态 | 职责 |
|---|---|---|
| `source.py` · `strava/` | 复用 | Strava 取数：活动/照片/头像/polyline（画册主源） |
| `intervals/client.py` | 新增 | Intervals.icu 只读连接器（Basic auth，非 OAuth） |
| `metrics.py` | 新增 | 确定性指标引擎 |
| `coach.py` | 新增 | AI 教练：读指标 → 生成 FTP 周期计划草案 |
| `model.py` · `editorial.py` | 复用 | Activity 模型 / 高光筛选，补训练字段 |
| `dashboard.py` | 新增 | 总装配入口：各区块数据 → 公开 JSON + 渲染单页外壳 |

### 呈现层
| 模块 | 状态 | 职责 |
|---|---|---|
| `book.py` · `theme.py` · `route.py` | 复用 | 翻页画册 + 主题 + 轨迹 SVG，降为单页中的一节 |
| `runtime/dashboard/` | 新增 | 单页外壳：锚点导航 + Leaflet 地图 + 图表 |
| `runtime/flipbook.js` 等 | 复用 | StPageFlip、点击导航、主题目录（画册区块内沿用） |

### 编排层
| 模块 | 状态 | 职责 |
|---|---|---|
| `cli.py` | 复用 | 新增子命令：`sync-intervals` / `build-dashboard` / `coach-draft` |
| `github/publisher.py` | 复用 | 原子发布到 gh-pages（整页 + 公开 JSON） |
| `.github/workflows/approve-plan.yml` | 新增 | 独立审批工作流：人工 dispatch → 校验 → 写 Intervals.icu 日历 |
| `.github/workflows/nightly-photobook.yml` | 复用 | 夜间扩展：同步 + 重算指标 + 重生成草案（只读） |

## 4. 单页区块栈（顶部锚点导航，向下滚动）

1. **年度英雄区 + KPI 卡** — 总里程/爬升/时长/骑行数/新路线 + 赛季倒计时（复用缓存）
2. **交互式地图 + 足迹** — Leaflet + 公开瓦片，点选活动看真实轨迹（Strava 轨迹）
3. **节奏图表** — 周/月柱状 + 日历热图(365格) + 距离-爬升气泡图 + Eddington 数（复用缓存）
4. **训练分析** — CTL/ATL/TSB 负荷曲线 + 功率/心率区间 + 功率曲线 + FTP 趋势（Intervals.icu）
5. **翻页画册（嵌入区块）** — 保留 StPageFlip 年度视觉叙事（复用）
6. **活动明细 + 装备** — 可排序活动表 + 每车累计里程/保养提示（混合）
7. **AI 教练草案** — 到 2027-04 的 FTP 周期计划草案；确认后才写日历（AI）

## 5. 组件详细

### 5.1 `intervals/client.py`
- 认证：Basic auth，`Authorization: Basic base64("API_KEY:" + <key>)`。
- Base URL：`https://intervals.icu/api/v1/`。
- 端点：`athlete/0`（档案/区间/FTP）、`athlete/0/activities`（含训练负荷/功率心率）、`athlete/0/gear`、`athlete/0/power-curves.json`、`athlete/0/pace-curves.json`。
- 只读；输出规范化为内部 dataclass；带缓存到 `data/intervals/`。
- 配置：`INTERVALS_API_KEY`、`INTERVALS_ATHLETE_ID`（默认 `0`=当前账号）。

### 5.2 `metrics.py`（确定性，无网络）
- **CTL/ATL/TSB**：按日 Training Load 指数加权（CTL 42 天、ATL 7 天），TSB = 昨日 CTL − 昨日 ATL。
- **区间分布**：功率/心率按区间边界聚合时长。
- **功率曲线**：Mean-maximal 功率（5s→60min）取各活动最佳。
- **FTP 趋势**：取 Intervals.icu 的 eFTP/设置 FTP 时间序列。
- **Eddington 数**：当年按日里程计算。
- **日历聚合**：每日里程/有无骑行，供 365 格热图。
- 全部函数纯输入输出，便于单测。

### 5.3 `coach.py`
- 输入：当前 FTP、CTL/ATL/TSB、区间分布、赛季日期（2027-04-01）。
- 产出：22 周 FTP 周期计划草案（基础/建设/专项/减量四期），每周训练要点。
- 输出含：`draft_id`（内容哈希前 12 位）、生成时间、依据摘要、风险提示、每个计划项的建议日期/时长/目标区间。
- 页面与 JSON 明确标注"AI 生成"，与原始指标区分。
- AI provider 可配置；密钥只在 Actions Secrets。

### 5.4 `dashboard.py`
- 调用 source/intervals/metrics/coach 装配各区块数据。
- 写公开 JSON 到 `books/<year>/data/`（随画册一起发布）：`metrics.json`、`routes.json`、`coach-draft.json`、复用 `activities.json`。
- 渲染 `runtime/dashboard/` 外壳为站点根 `index.html`，画册区块内联/嵌入。

## 6. 公开 JSON 契约（发布到 gh-pages，浏览器读取）
- `data/metrics.json`：KPI、CTL/ATL/TSB 序列、区间、功率曲线、FTP 趋势、Eddington、日历聚合。
- `data/routes.json`：活动 polyline + 边界（供 Leaflet）。
- `data/coach-draft.json`：当前草案（draft_id、周计划、依据、风险、"AI 生成"标记）。
- 均不含任何令牌/密钥/原始接口响应。

## 7. 异常处理 · 优雅降级（任一数据源故障不阻断上线）
- **Intervals.icu 不可用**：跳过训练区块（4、6 的装备部分），页面标"训练数据暂不可用"，画册/Strava 区块照常发布。
- **Strava 限流**：沿用现有 15 分钟配额窗口重试；仍失败则保留上次公开数据。
- **AI 不可用**：跳过新草案，保留上一版草案与 draft ID，页面标"草案未更新"。
- **审批哈希不匹配**：拒绝写入并报错退出；同 draft ID 已写入则幂等跳过，不重复建事件。

## 8. 安全与隐私边界
- Strava / Intervals.icu / AI 密钥只存在 GitHub Actions Secrets，绝不进入浏览器或公开产物。
- 新增 Secrets：`INTERVALS_API_KEY`、`INTERVALS_ATHLETE_ID`、AI provider 密钥。
- 写日历仅由人工触发的 `approve-plan.yml` 完成；夜间任务只读。
- 公开页面包含健康指标、AI 分析、训练计划（用户选择"都公开"）；但不含任何凭证。
- **数据诚实性**：页面区分"原始指标 / 确定性规则 / AI 生成"，不把模型结论伪装成生理测量。

## 9. 测试策略（三层）
- **宿主机单测（unittest）**：metrics 用已知输入验证 CTL/ATL/TSB/Eddington/区间；intervals client 用 mock 响应；coach 草案结构 + draft_id 哈希稳定性；审批哈希校验。
- **前端契约（node --test）**：单页外壳 DOM 契约、地图/图表数据绑定、画册区块沿用现有 flipbook 测试。
- **发布门禁**：扩展 `tools/validate_release.py` 校验新区块与公开 JSON 结构；保留 heatmap/照片/结构校验与 5% 照片数容差。

## 10. 分阶段实施（最终形态为一页；分阶段构建、每阶段可增量上线）
- **P0 基础**：改名 + `intervals/client.py` + 配置/CLI（`sync-intervals`）。
- **P1 数据+外壳**：`metrics.py` + `runtime/dashboard/` 单页外壳 + 区块 1/3（KPI、节奏图表、日历热图、Eddington）。
- **P2 地图+画册**：区块 2（Leaflet 地图/足迹）+ 区块 5（画册嵌入）+ 区块 6（活动明细/装备）。
- **P3 训练+教练+审批**：区块 4（CTL/ATL/TSB/区间/功率曲线）+ 区块 7（`coach.py` 草案页）+ `approve-plan.yml`。
- **P4 夜间整合+上线**：扩展 `nightly-photobook.yml`，直接上线 Pages 并验收。

## 11. 验收标准
- 本地 `build-dashboard` 生成单页，第 4 节的 7 个锚点区块齐全。
- 全量 `python -m unittest` + `node --test` + 发布门禁通过。
- 发布到 gh-pages，Live URL（https://mengen-ink.github.io/cycling-data-hub/）返回 HTTP 200 且包含既有 Strava photobook marker 与新仪表盘区块标识。
- Intervals.icu 降级路径验证：断源时页面仍成功发布，训练区块显示占位。
- 审批工作流：草案哈希校验通过后成功在 Intervals.icu 建立带 draft ID 的日历事件；重复触发幂等。
