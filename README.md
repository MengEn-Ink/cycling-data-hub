# 我的骑行数据 · Cycling Data Hub 🚲

把 **Strava** 骑行记录与可选的 **Intervals.icu** 训练数据汇总成一个响应式年度仪表盘，
并把可翻页照片画册直接嵌入页面。电脑与手机共享同一套 Distance Manifesto 暗色视觉。

> 🚲 **在线仪表盘（2026）**：<https://mengen-ink.github.io/strava-photobook-2026/>
> 源码仓库：<https://github.com/MengEn-Ink/strava-photobook-2026>

响应式与阅读友好：窄屏（≤700px）自动折为单页并加宽文字栏、放大触控按钮（≥46px）、
适配刘海/底部安全区；正文用容器相对单位（cqw），无论页面大小字号都等比、清晰。

站点在构建时从数据源取数，浏览器只读取无密钥的公开 JSON：

- **单页仪表盘**：最近七天、年度柱状节奏、GitHub 式骑行日历、路线轨迹热图、纪录、目标、完整活动日志与详情。
- **训练证据**：配置 Intervals.icu 后显示 CTL / ATL / TSB、FTP、功率曲线与装备里程；缺失时明确降级，不生成假数据。
- **翻页画册**：在仪表盘中直接打开，也可访问 `photobook/`；电脑端双页、手机端单页。

- **高光摄影海报封面**：自动从入册照片中选择年度代表横图，结合主题色、年份与核心数据；没有合适照片时自动退回年度路线海报。
- **年度总结跨页**：用年度总里程、月份节奏、累计爬升、Kudos、PR 与最长单骑讲述这一年的骑行变化。
- **年度活动热力图**：聚合当年 GPS 轨迹，重复路段自然加深，并使用统一的 Distance Manifesto 锈橙色阶。
- **高光介绍页**：按「收藏最高 / 赛段 PR / 同行人数」挑选的代表骑行，含标题、描述、数据、
  当天刷出的赛段 PR，以及由 GPS 轨迹（polyline）解码而成的**矢量路线图**。
- **照片画廊**：从 Strava 下载骑行照片。竖图满屏且零文字遮挡；横图完整显示，标题、日期、里程、爬升和照片说明放在独立信息区。

画册只支持**唯一主题 Distance Manifesto**：深黑阅读环境、暗色书页、暖白文字与锈橙强调色统一覆盖海报封面、年度总结、
路线热力图和控制区。页面不提供主题选择器，避免仪表盘与画册出现两套视觉语言。

> 翻页运行时改编自 MIT 许可的
> [create-photo-flipbook-ui](https://github.com/HaichaoLihc/create-photo-flipbook-ui)。

## 快速开始

第一次使用建议直接照着 [从零配置与发布指南](docs/setup.md) 操作。

环境要求：Python 3.9+；Node.js 仅用于可选的运行时契约测试。

```bash
pip install -r requirements.txt

# 1. 一次性授权（会打开浏览器）。需要一个 Strava API 应用，见下方「准备 Strava 应用」。
python -m strava_photobook auth

# 2. 缓存全部活动指标（每约 200 条活动一次请求）。
python -m strava_photobook fetch

# 3. 查看有哪些年份。
python -m strava_photobook years

# 4. 生成某一年，照片直接从 Strava 下载。
python -m strava_photobook build 2026

# 5. 把仪表盘提升为站点根页，画册移入 photobook/，并生成公开 JSON。
python -m strava_photobook build-dashboard 2026

# 6. 本地预览。
cd books/2026 && python -m http.server 4173 --bind 127.0.0.1

# 7. 一次性 GitHub 授权，然后发布并等待 Pages 真正可访问。
python3 -m strava_photobook github-auth
python3 -m strava_photobook publish 2026
```

## 命令

| 命令 | 作用 |
|---|---|
| `python -m strava_photobook auth` | 一键浏览器 OAuth 授权，把 refresh token 写入 `.env`。 |
| `python -m strava_photobook fetch` | 拉取全部活动概要到 `data/activities.json`。 |
| `python -m strava_photobook sync-intervals --year <年份>` | 可选：同步规范化的训练、装备与功率数据。 |
| `strava_photobook years` | 列出年份及每年的骑行数、照片数。 |
| `strava_photobook build <年份>` | 生成 `books/<年份>/`。 |
| `strava_photobook build-dashboard <年份>` | 生成公开 JSON，把仪表盘设为根页并将画册移入 `photobook/`。 |
| `python3 -m strava_photobook github-auth` | 浏览器授权 GitHub，token 安全写入 `.env`。 |
| `python3 -m strava_photobook publish <年份>` | 建仓、上传、启用 Pages，并等待公网页面可打开。 |

## 发布到 GitHub Pages

最省事的方式是安装 GitHub CLI，然后运行 `github-auth` 和 `publish`。`github-auth` 会调用 GitHub
官方浏览器授权。也可创建 GitHub OAuth App、启用 Device Flow，并配置公开的 `GITHUB_CLIENT_ID`，
此时工具使用内置 Device Flow，不依赖 `gh`。自动化环境可直接注入 `GH_TOKEN`。

默认创建公开仓库 `strava-photobook-<年份>`，只把生成后的静态站点写到 `gh-pages` 分支；
`.env`、Strava token、`data/` 和项目源码不会被上传。可以用 `--repo NAME` 自定义仓库名。
发布根页是仪表盘，翻页画册位于 `photobook/`，公开数据位于 `data/metrics.json`、
`data/activities.json` 与 `data/routes.json`。同名仓库必须带有本工具标记，否则命令会拒绝覆盖。

## 准备 Strava 应用

1. 打开 <https://www.strava.com/settings/api>，用 Strava 账号登录。
2. 创建应用：名称随意（如 `strava-photobook`），**Authorization Callback Domain 必须填 `localhost`**。
3. 记下 **Client ID** 和 **Client Secret**。
4. 运行 `python -m strava_photobook auth`：未配置时会提示粘贴 client id/secret，浏览器授权后
   refresh token 自动写入 `.env`（权限 600）。

申请的权限（只读）：`read`、`activity:read_all`、`profile:read_all`——足以读取你的活动
（含私密）、PR 与照片。

## 工作原理

```
Strava API ───────────────┐
  ├── /athlete/activities        概要：收藏、PR、同行人、轨迹   ──► data/activities.json
  ├── /activities/{id}           赛段 PR + 描述        （仅高光骑行）
  └── /activities/{id}/photos    原图照片 URL          （入册骑行）
Intervals.icu（可选）─────┤ 训练负荷 / FTP / 功率 / 装备（规范化缓存）
                          ▼
                    构建静态站点
                          ├── books/<年份>/index.html             仪表盘
                          ├── books/<年份>/data/*.json            公开数据
                          └── books/<年份>/photobook/index.html   翻页画册
```

概要请求很省（每约 200 条一次），全量历史几秒缓存完；较贵的逐条请求（PR 赛段、照片下载）
只对真正入册的骑行发起，稳妥落在 Strava 限流内（200 次 / 15 分钟）。

## 项目结构

```
strava-photobook/
├── strava_photobook/
│   ├── cli.py / __main__.py   # 命令行入口
│   ├── config.py              # 环境变量 / .env，无硬编码路径
│   ├── model.py               # Activity 模型 + 高光筛选
│   ├── route.py               # GPS 轨迹解码为内联 SVG
│   ├── theme.py               # 介绍页布局 + 黑白主题
│   ├── book.py                # 编排单年画册
│   ├── source.py              # 从 Strava API 取数据与照片
│   ├── dashboard.py           # 公开 JSON 与生产站点装配
│   ├── metrics.py             # KPI / Eddington / CTL / ATL / TSB 等纯函数
│   ├── intervals/             # Intervals.icu 只读同步与安全规范化
│   └── strava/                # 自带 OAuth 客户端 + 本地授权服务
├── tools/                     # 画册布局、发布完整性与 Dashboard 安全门禁
├── runtime/                   # 翻页运行时 + Distance Manifesto Dashboard
├── books/                     # 产出，一年一个静态站点（已 gitignore）
└── data/                      # API 缓存 + token（已 gitignore）
```

## 配置

密钥放 `.env`（从 `.env.example` 复制）；其余调优项用环境变量覆盖，均有默认值：

| 环境变量 | 作用 | 默认 |
|---|---|---|
| `STRAVA_CLIENT_ID` / `_SECRET` / `_REFRESH_TOKEN` | Strava 凭证 | — |
| `PHOTOBOOK_ROOT` | 项目根目录 | 当前目录 |
| `PHOTOBOOK_DATA_DIR` / `PHOTOBOOK_BOOKS_DIR` / `PHOTOBOOK_RUNTIME_DIR` | 数据/产出/运行时目录 | `data` / `books` / `runtime` |
| `PHOTOBOOK_PHOTOS_PER_BOOK` | 可选逃生舱；设置后强制固定入册照片数，不设则按当年上传量动态决定 | 未设置（动态） |
| `PHOTOBOOK_PHOTO_RATIO` | 动态模式：选取当年上传照片的比例 | `0.60` |
| `PHOTOBOOK_PHOTO_FLOOR` | 动态模式：入册照片数下限 | `40` |
| `PHOTOBOOK_PHOTO_CAP` | 动态模式：入册照片数上限 | `120` |
| `PHOTOBOOK_MAX_PHOTOS_PER_RIDE` | 单次活动最多入册张数，避免一次活动刷屏 | `6` |
| `PHOTOBOOK_FEATURE_RIDES` | 高光介绍页数量 | `6` |
| `PHOTOBOOK_MAX_PHOTO_EDGE` | 照片最长边（像素） | `1600` |
| `GITHUB_CLIENT_ID` | 可选；启用 Device Flow 的 GitHub OAuth App Client ID | — |
| `GITHUB_TOKEN` | `github-auth` 保存的 GitHub token | — |
| `GH_TOKEN` | 自动化 token，优先于 `GITHUB_TOKEN` | — |
| `INTERVALS_API_KEY` | 可选；Intervals.icu 只读 API Key | — |
| `INTERVALS_ATHLETE_ID` | 可选；Intervals.icu athlete ID | `0` |

### 入册照片数（动态）

默认不固定张数，而是跟随当年 Strava 上传量增长：

```
目标张数 = min(上传总数, clamp(round(上传总数 × PHOTOBOOK_PHOTO_RATIO), PHOTOBOOK_PHOTO_FLOOR, PHOTOBOOK_PHOTO_CAP))
```

即默认取当年上传照片的 **60%**，并夹在 **40～120 张**之间（上传不足 40 张时全部入册，不凑数）。
分配上，高光活动起步 4 张、其余活动 2 张，再按活动精彩度（点赞、PR、同行、距离/爬升、图文完整度）
把剩余名额逐张补足，单次活动最多 `PHOTOBOOK_MAX_PHOTOS_PER_RIDE`（默认 6）张，避免一次活动刷屏。
需要回到固定数量时，设置 `PHOTOBOOK_PHOTOS_PER_BOOK` 即可强制覆盖（逃生舱）。

### 固定主题

画册固定使用唯一主题 Distance Manifesto：深黑环境承载翻页舞台，暗色书页配暖白文字，锈橙用于路线、焦点和当前月份。
主题不接受查询参数覆盖，也不写入浏览器偏好；从仪表盘打开或直接访问画册都保持同一套视觉。

## 门禁检测

三类校验，改样式或生成后跑一遍：

```bash
# 1) 布局门禁（静态、秒级）：断言高光页「文字左栏 / 轨迹右下角」分栏不重叠、
#    轨迹颜色足够浅、关键文字类都有样式。改 theme.py 后必跑。
python -m tools.layout_gate

# 2) 运行时契约（生成后）：校验仪表盘和翻页书结构、响应式排版、资源就位。
node --test runtime/dashboard/*.test.mjs
node --test books/<年份>/photobook/html-contract.test.mjs

# 3) 发布门禁：校验根页、嵌套画册、三份公开 JSON、占位符与敏感字段。
python tools/validate_dashboard.py books/<年份>
```

布局门禁把「文字栏右边界不得越过轨迹栏左边界」这条几何不变量固化下来——只要成立，
文字再长也不会和轨迹图案堆积遮挡。需要逐页像素级核对时，可本地起服务后在浏览器对每个
高光页测元素矩形碰撞（`?page=N`）。

## 每晚自动更新

`.github/workflows/nightly-photobook.yml` 每天北京时间 **21:00** 自动运行，也可在 Actions
页面通过 `workflow_dispatch` 手动触发。GitHub 的 cron 使用 UTC，因此配置为 `0 13 * * *`。
同一时刻只保留一个运行：后触发的会取消仍在进行的旧运行（`concurrency: cancel-in-progress`）。

每次运行按以下步骤执行：

1. **选年份**：按 `Asia/Shanghai` 时区取当前年份，只构建当年画册。
2. **恢复线上基线**：把 `gh-pages` 分支检出到临时 worktree，并将现有照片拷入本地
   `data/photo-cache`——既作为照片下载缓存，也作为发布前的回归对比基线。
3. **拉取当年活动**：执行 `fetch --year <年份>`。若撞上 Strava 限流（每 15 分钟一个固定
   配额窗口），会等待到下一个窗口后自动重试一次。
4. **同步训练数据（可选）**：配置 Intervals Secrets 后执行只读同步；缺失或失败时保留明确降级状态。
5. **构建站点**：先执行 `build <年份>` 生成画册，再执行 `build-dashboard <年份>` 生成根仪表盘与公开 JSON。
6. **发布前校验**：依次运行 Python 单测、运行时与画册的 Node 契约测试、布局门禁、照片
   布局门禁，以及对照线上基线的 `validate_release`（校验画册标记、封面 / 年度总结 / 热力图、
   无空白衬页与内部页码、资源齐全、照片数无显著回落），以及根站点 `validate_dashboard` 安全门禁。
7. **原子发布**：全部通过后，用临时 worktree 清空 `gh-pages` 旧内容并拷入新站点；没有变化
   则不产生提交，有变化才提交 `Publish nightly Strava photobook` 并推送，Pages 随之更新。

首次启用时，在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 创建：

- `STRAVA_CLIENT_ID`：Strava 应用 Client ID
- `STRAVA_CLIENT_SECRET`：Strava 应用 Client Secret
- `STRAVA_REFRESH_TOKEN`：执行本地 `auth` 后 `.env` 中的刷新令牌
- `SECRETS_ADMIN_TOKEN`：能管理本仓库 Actions Secrets 并推送分支的 GitHub token
- `INTERVALS_API_KEY` / `INTERVALS_ATHLETE_ID`：可选；不配置时训练区块诚实降级，仍会发布

动态画册以本次构建声明的目标张数为准：实际入册达到目标的 **90%** 即发布（容忍个别图片下载失败），
目标本身随上传量增删，不再与线上旧版本比张数；未声明动态目标的旧画册仍沿用发布基线的 **5% 容差**
（如 40→39 仍发布，40→37 才拦截）。校验不通过时旧页面保持不变。Strava 刷新令牌每次轮换后
都会立即回写到 `STRAVA_REFRESH_TOKEN`（限流重试成功后也会再回写一次），避免长期运行后
令牌过期。需要暂停时，在 Actions 中禁用 **Nightly photobook refresh** 工作流即可。

## 隐私

取数与构建在本机或 GitHub Actions 内完成，API 凭证只来自 `.env` / Actions Secrets，绝不写入成品。
发布是公开行为：生成后的照片、活动标题、日期、路线与汇总指标会出现在 Pages；发布前请确认接受公开范围。
源码仓库仍忽略 `.env`、原始 `data/` 与本地 `books/`。

## 许可

MIT，见 [LICENSE](LICENSE)。内置的翻页运行时组件 StPageFlip 保留其自身许可（见 `runtime/vendor/`）。

## 商标声明

本项目为非官方的第三方工具，与 Strava, Inc. 无任何隶属、赞助或背书关系。
「Strava」是 Strava, Inc. 的注册商标，此处仅用于说明本工具处理的数据来源。
