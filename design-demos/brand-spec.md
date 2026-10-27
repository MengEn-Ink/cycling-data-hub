# 我的骑行数据 · Brand Spec

> 采集日期：2026-10-27
> 资产来源：项目本地画册、Strava 官方 About 页面、Strava API Brand Guidelines、Intervals.icu 官方产品页
> 资产完整度：完整（本项目自有品牌暂无独立 logo，使用纯文字品牌名；具名数据源使用官方资产）

## 核心资产

### 站点品牌

- 品牌名：「我的骑行数据」
- 标志策略：不临时创造图标，使用文字标志；后续如用户提供自有 logo 再替换。

### Strava Logo

- 主版本：`assets/strava/strava-orange.svg`
- 深底反色版：`assets/strava/strava-white.svg`
- 来源：Strava 官方 `strava.com/about` 页面所引用的 CDN 资产。
- 使用场景：页尾「数据来自 Strava」署名，不作为站点主品牌。
- 禁用：不拉伸、不描边、不改色、不暗示本项目由 Strava 开发或赞助。

### 用户照片

- 动态特写：`../books/2026/photobook/assets/photos/18166002364-00.jpg`（1067×1600）
  - 评分：9/10；真实本地内容、人物和车辆清晰、动势强、可独立承担 hero 叙事。
- 集团爬坡：`../books/2026/photobook/assets/photos/19563904174-00.jpg`（1600×1200）
  - 评分：9.5/10；真实本地内容、分辨率足够、横向队列天然适合数据叙事、场景完整。
- 使用场景：方向 1 以动态特写为主角；方向 3 以集团爬坡为章节转场；方向 2 让照片退居画册区。

### 数字产品 UI 参考

- Ascent：`refs/ascent-overview.png`、`refs/ascent-trends.png`
- Intervals.icu：`refs/intervals-fitness.png`、`refs/intervals-timeline.png`
- 只借信息结构与图表层级，不把参考中的示例数据或品牌视觉搬进页面。

## 辅助资产

### 色板

- Strava Orange：`#F05523`，来自 Strava 官方橙色 wordmark。
- Night Ink：`#070707`，主深底；取自现有画册默认近黑并压到纯暗场。
- Road White：`#F2F0EA`，文字与路面标线的暖白。
- Bike Lime：`#8EF236`，只供方向 1 小面积使用；取自动态照片中的车架荧光绿。
- Training Cyan：`#35D9B0`，方向 2 的训练状态色；与 Strava 橙色拉开色相，避免数据源混淆。
- Archive Sand：`#D8C7B5`，方向 3 的图录纸色；来自现有主题目录 `vandyke-khaki`。

### 字型

- 方向 1 Display：`DIN Alternate`；Body：`Avenir Next` + `PingFang SC`。
- 方向 2 Display / Body：`Avenir Next` + `PingFang SC`；Data：`Menlo`。
- 方向 3 Display 数字：`Bodoni 72`；中文：`PingFang SC`；注释：`Songti SC`。
- 均禁用合成斜体与合成粗体；数据数字使用 tabular nums。

### 签名细节

- 方向 1：照片中的道路黄线延伸为全页节奏线。
- 方向 2：每个模块都带真实的数据来源状态，不用装饰性标签。
- 方向 3：里程数字、轨迹线与画册照片形成一条纵向「年度图谱」。

### 禁区

- 不做通用的黑底 + 一排圆角 KPI 卡片作为三套共同首屏。
- 不把 Strava 橙色扩成整个站点的唯一品牌识别。
- 不把 Intervals.icu 示例图里的紫色曲线当成本项目真实训练数据。
- 不出现 Story 分享功能。

### 气质关键词

- 自我记录
- 骑行速度
- 训练诚实
- 山路尺度
- 年度档案
