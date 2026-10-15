---
name: photobook-release
description: Commit photobook changes, push main, and redeploy through the nightly GitHub Actions workflow, then verify the live site. Use for 提交并推送、部署、重新部署、触发 Actions、发布画册、上线画册. Not for local-only edits.
---

# Photobook release

把本仓库（MengEn-Ink/strava-photobook-2026）的改动提交、推送到 `main`，手动触发
GitHub Actions 重新构建并发布 gh-pages，最后核对线上结果。这是本仓库固定的发布链路，
**push 本身不会触发部署**（workflow 只在 `schedule` 与 `workflow_dispatch` 触发）。

## 环境事实（不要重新摸索）

- macOS；解释器是 `python3`（不存在 `python`）；Node v24；`gh` 已登录 MengEn-Ink。
- 主干分支 `main`；线上地址 https://mengen-ink.github.io/strava-photobook-2026/
- workflow 名 `Nightly photobook refresh`（文件 `.github/workflows/nightly-photobook.yml`）：
  拉 Strava → build → 全量测试与三道门禁 → 原子发布 gh-pages。
- 拉取失败时 workflow 内置限流重试，会 sleep 到下一个 15 分钟配额窗口（约 16 分钟），
  轮询要有耐心；正常情况一次成功，约 60–90 秒跑完。
- 每晚 21:00（北京）定时跑；手动部署仅用于需要立刻上线的场景。

## 发布前本地自检（强烈建议）

```bash
python3 -m unittest discover
node --test runtime/*.test.mjs
node --test books/2026/*.test.mjs
python3 -m tools.layout_gate
python3 tools/photo_layout_gate.py books/2026/index.html
```

注意 `books/2026/` 是已发布旧产物时，`validate_release.py` 可能因新门禁报封面重复等，
这属预期；CI 用新代码重新 build 后即通过，不要据此回退代码。

## 执行步骤

1. **盘点变更**：`git status --short`。按用户偏好把功能与文档（README/.env.example）
   拆成独立 commit；只精确 `git add <文件>`，禁止 `git add -A`，避免混入临时/产物文件。
2. **提交**：Conventional Commits（如 `feat(photos): ...`、`fix(photos): ...`、`docs: ...`），
   现在时祈使句；不 amend、不 force push。
3. **推送前预检**：
   ```bash
   git fetch origin
   git rev-list --left-right --count HEAD...origin/main   # 左=本地领先 右=远端领先
   ```
   远端领先（右值>0）时先处理同步：stash 无关改动 → rebase → 确认关键改动仍在，再继续。
4. **推送**：`git push origin main`，推送后确认计数为 `0  0`，并记下
   `git rev-parse HEAD`（用于核对 Actions 跑的就是该提交）。
5. **触发部署**：
   ```bash
   gh workflow run "Nightly photobook refresh" --ref main
   sleep 12
   gh run list --workflow="Nightly photobook refresh" --limit 1 \
     --json databaseId,status,event,headSha \
     --jq '.[] | "run=\(.databaseId) status=\(.status) event=\(.event) sha=\(.headSha)"'
   ```
   必须确认 `event=workflow_dispatch` 且 `sha` 等于刚推送的 commit；不一致则不要继续观察错 run。
6. **轮询到结束**（可能进入限流重试，最长约 20 分钟）：
   ```bash
   gh run view <RUN_ID> --json status,conclusion --jq '"\(.status) \(.conclusion)"'
   ```
   期望 `completed success`；失败则 `gh run view <RUN_ID> --log-failed` 定位并修复，
   走新 commit，不在失败提交上 amend。
7. **核对流水线结果**：
   ```bash
   gh run view <RUN_ID> --json jobs \
     --jq '.jobs[].steps[] | select(.name|test("Build|Test|Publish|Fetch current")) | "\(.conclusion)\t\(.name)"'
   gh run view <RUN_ID> --log | grep -E "built /home/runner.*books/[0-9]{4} |release valid:"
   ```
   关键判据：
   - Fetch / Build / Test and validate / Publish 四个步骤均 `success`；
   - `built ... photos=<唯一数>/<目标> uploads=<当年上传数>`，唯一数达成目标；
   - `release valid: photos=.. target=.. baseline=..`，动态画册按本次 target 判定（90% 达成率），
     且封面/正文唯一性门禁通过（不出现 `cover photo repeated` 或 `duplicate photo in body`）。
8. **核对线上**（Pages 可能有数十秒延迟，必要时轮询）：
   ```bash
   python3 .trae/skills/photobook-release/scripts/verify_live.py
   ```
   期望 `cover_in_body=False`、`body_unique == body 数`、`total_unique == target`。
   `athlete.jpg` 在多张高光页复用是本人头像，属豁免，不算重复。

## 安全边界

- 仅在用户明确要求部署时触发 workflow；不要为“跑个测试/看看效果”而发布。
- 不打印 secrets，不修改 git config，不 force push，不跳过 hook。
- 部署后汇报：commit 链接、Run 链接、build/release 日志关键行、线上唯一性核对结果。
