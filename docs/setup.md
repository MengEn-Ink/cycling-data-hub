# 从零生成并发布骑行数据仪表盘

这份指南面向第一次使用命令行的用户。完成后，你会得到一个根页仪表盘、内嵌翻页画册和一个任何人都能打开的 GitHub Pages 链接。

- 项目仓库：<https://github.com/MengEn-Ink/cycling-data-hub>
- 在线仪表盘：<https://mengen-ink.github.io/cycling-data-hub/>

## 1. 准备环境

需要 Python 3.9 或更高版本。运行 `python3 --version` 检查，再进入项目目录执行 `python3 -m pip install -r requirements.txt`。预期命令正常结束，没有红色错误。

## 2. 创建 Strava API 应用

1. 登录 https://www.strava.com/settings/api 。
2. 创建一个 Strava API 应用，名称可填 Cycling Data Hub。
3. `Authorization Callback Domain` 填 `localhost`。
4. 记下 Client ID 和 Client Secret。它们只保存在本机 `.env`。

## 3. 授权并获取活动

依次运行 `python3 -m strava_photobook auth`、`python3 -m strava_photobook fetch`、`python3 -m strava_photobook years`。浏览器会要求确认 Strava 只读权限。预期 fetch 显示缓存条数，years 列出可生成的年份。

## 4. 生成并预览

先运行 `python3 -m strava_photobook build 2026`，再运行 `python3 -m strava_photobook build-dashboard 2026`。后者会把 Distance Manifesto 仪表盘设为根页，把画册移入 `books/2026/photobook/`，并生成三份不含密钥的公开 JSON。然后进入 `books/2026` 执行 `python3 -m http.server 4173 --bind 127.0.0.1`，打开 http://127.0.0.1:4173 。预期首先看到年度仪表盘；滚动到「翻页画册」可在弹层里直接打开，点击、拖动或方向键翻页。按 Ctrl+C 停止预览。

封面只使用已经下载到画册内的照片，不会额外请求 API。若当年没有合格照片，生成器会自动使用年度路线海报，不会留下空图片框。竖版照片满屏显示且不叠加可见文案；横版照片完整放在独立图片区，活动标题、日期、里程、爬升和照片说明放在图片外的信息区。点击画册左半区域向前翻页，点击右半区域向后翻页；拖动、方向键和月份时间轴仍然可用。

画册只支持唯一主题 Distance Manifesto：深黑环境、暗色书页、暖白文字与锈橙强调色和仪表盘保持一致。页面不显示主题选择器，也不读取或保存浏览器主题偏好；从任何入口打开都是同一套视觉。

封面后的首个跨页包含年度活动热力图。它直接使用 Strava GPS 轨迹，不需要地图服务或额外密钥；重复经过的路线会更深，并使用 Distance Manifesto 的锈橙色阶。异地活动不会把主要骑行区域压缩成角落，页面会优先展示最密集的活动区域。

## 5. 授权 GitHub

运行 `python3 -m strava_photobook github-auth`。若已安装 GitHub CLI，终端会显示一次性验证码并打开浏览器。若没有，可创建 GitHub OAuth App、启用 Device Flow，并在 `.env` 设置 `GITHUB_CLIENT_ID`。预期终端显示授权成功并保存 `GITHUB_TOKEN`；不要复制或提交 token。

## 6. 公开发布

运行 `python3 -m strava_photobook publish 2026 --repo cycling-data-hub`。它会复用或创建公开仓库 `cycling-data-hub`、上传根仪表盘、公开 JSON 和 `photobook/` 到 gh-pages 分支、开启 Pages，并等待公网 HTML 可访问。预期输出包含仓库地址和 Pages 地址。

公开页面包含照片、活动标题、日期、路线与统计。执行前请确认允许公开。以后重新生成后运行同一条 publish 命令即可更新。

## 7. 配置每天 21:00 自动更新

代码仓库包含 `.github/workflows/nightly-photobook.yml`。它在每天北京时间 21:00
（UTC 13:00）运行，也可从 GitHub 仓库 **Actions → Nightly photobook refresh →
Run workflow** 手动触发（对应 `workflow_dispatch`）。

打开仓库 **Settings → Secrets and variables → Actions → New repository secret**，依次添加：

1. `STRAVA_CLIENT_ID`：复制本地 `.env` 的同名值。
2. `STRAVA_CLIENT_SECRET`：复制本地 `.env` 的同名值。
3. `STRAVA_REFRESH_TOKEN`：复制本地 `.env` 的同名值；工作流之后会自动维护轮换值。
4. `SECRETS_ADMIN_TOKEN`：GitHub token，需要能管理本仓库 Actions Secrets 和推送分支。

可选增强：再添加 `INTERVALS_API_KEY` 与 `INTERVALS_ATHLETE_ID`。本项目的夜间同步流程只调用 GET 接口来获取训练负荷、FTP、功率曲线与装备里程；API Key 仍应像密码一样保管。未配置或同步失败时，训练区块显示明确的不可用状态，不阻塞 Strava 仪表盘和画册发布。

配置后先手动运行一次。在运行日志中看到 `release valid`、提交 `gh-pages` 成功，并能
打开 Pages 地址即完成。失败时旧网站不会被覆盖：先打开失败步骤查看日志；凭证错误时重新
执行本地 `python3 -m strava_photobook auth`，再更新上述 Strava Secrets。暂停自动更新时，
进入该工作流右上角菜单选择 **Disable workflow**。

## 常见问题

- 没有活动缓存：先运行 fetch。
- 没有该年份：运行 years 查看年份。
- GitHub 验证码过期：重跑 github-auth，只使用最新验证码。
- 拒绝覆盖同名仓库：用 `--repo 新名字` 发布。
- Pages 未完成：稍后重跑 publish，流程会安全复用已有仓库。
- LibreSSL 警告：建议使用 Homebrew Python 3.11+；警告本身不代表生成失败。

## 隐私与文件位置

- `.env` 保存凭据，已被 Git 忽略。
- `data/` 保存原始活动缓存，已被 Git 忽略。
- `books/` 保存生成站点，已被 Git 忽略；publish 会公开指定年份的仪表盘、JSON、路线和照片成品。
