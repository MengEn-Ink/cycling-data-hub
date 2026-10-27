# 产品事实核验 · 我的骑行数据

> 核验日期：2026-10-27

## 项目与数据

- 本项目是静态 GitHub Pages 站点，构建时读取 Strava 与 Intervals.icu 数据并发布公开 JSON；浏览器端不保存 OAuth 密钥。依据：仓库内 `docs/superpowers/specs/2026-10-27-cycling-data-hub-design.md`。
- 2026 年本地 Strava 缓存包含 111 次骑行、7,984.5 km、64,299 m 爬升、884,549 秒移动时间、4,503 个 kudos；Eddington 数为 63。依据：本地 `data/activities.json` 经 `strava_photobook.metrics.build_metrics` 计算。
- 2027 赛季开始日为 2027-04-01；以 2026-10-27 计还剩 156 天 / 22 周。依据：已批准项目规格与 `metrics.season_countdown`。
- 当前仓库没有可用的 Intervals.icu 年度缓存，因此训练负荷、FTP 趋势与 AI 教练区在方向稿中必须显示真实的「尚未同步 / 尚未生成」状态，不伪造曲线。

## 外部参考

- [Ascent-Strava-Dashboard](https://github.com/doniwirawan/Ascent-Strava-Dashboard) 是静态单页应用，README 展示了概览、趋势、热图、日历、Eddington 与活动详情等区块。它使用浏览器侧 OAuth/缓存；本项目只借信息架构，不复制其数据架构或 Story 分享功能。
- [GitHub 官方文档](https://docs.github.com/en/account-and-profile/how-tos/setting-up-and-managing-your-github-profile/managing-contribution-settings-on-your-profile/viewing-contributions-on-your-profile) 将 contributions calendar 定义为过去一年贡献的可视化，并以每日方格支持查看具体日期或时间范围。本项目只借用“7 行星期 × 连续周列”的年度网格结构；颜色仍表示骑行里程或爬升，不使用 GitHub 贡献语义或品牌配色。
- [Strava API Brand Guidelines](https://developers.strava.com/guidelines/) 提供橙色、白色和黑色的官方 API 标识，并要求避免暗示产品由 Strava 开发或赞助。
- [Intervals.icu](https://www.intervals.icu/) 官方页面将 fitness / fatigue / form、eFTP、power curve、活动时间线与训练日历列为核心能力。本项目将这些训练视图放在 Strava 年度叙事之后，并明确标注数据来源。

## 设计边界

- 站点品牌是「我的骑行数据」，不是 Strava 或 Intervals.icu 的官方产品。
- Strava 只作为数据来源署名；主视觉品牌仍属于用户自己的年度骑行档案。
- Ascent 的 Story card generator 明确不在本项目范围内。
