---
name: photobook-release
description: Commit changes, push main, and redeploy through a GitHub Actions workflow_dispatch pipeline, then verify the live site. Use for 提交并推送、部署、重新部署、触发 Actions、发布画册、上线画册. Not for local-only edits.
---

# Release via GitHub Actions (generic, copyable)

把改动提交、推送到主干，手动触发 GitHub Actions 重新构建/发布，最后核对线上结果。
流程与具体项目解耦：**只有下面「项目配置」需要按仓库改**，步骤与脚本可直接复制到其它仓库。

## 项目配置（复制到别的仓库时只改这里）

| 变量 | 本仓库默认值 | 说明 / 自动探测 |
| --- | --- | --- |
| 主干分支 `REF` | `main` | `deploy.sh -r` 可覆盖 |
| Workflow `WORKFLOW` | `Nightly photobook refresh` | 仓库只有一个 active workflow 时脚本自动探测，多个则用 `-w` 指定 |
| 线上地址 `LIVE_URL` | `https://mengen-ink.github.io/strava-photobook-2026/` | `verify_live.py` 顶部 `LIVE_URL_DEFAULT`；留空可从 `origin` 推导 `owner.github.io/repo` |
| 本地自检命令 | 见下「发布前自检」 | 换成目标项目的 test/lint/gate 命令 |
| 成功判据 | 见下「核对」 | 换成目标项目的产物校验（脚本 `verify_live.py` 顶部 CONFIG 块可改选择器） |

关键事实：很多此类仓库的 workflow 只在 `schedule` + `workflow_dispatch` 触发，
**push 本身不会部署**，必须手动 dispatch；是否如此以 `.github/workflows/*.yml` 的 `on:` 为准。

## 脚本（机械步骤已固化，优先使用）

- `scripts/deploy.sh`：fetch 预检 → 可选 push → dispatch → 轮询到结束。**默认安全**：
  不带开关时只做预检与 workflow 探测，不 push、不触发。
  ```bash
  bash scripts/deploy.sh -w "Nightly photobook refresh"           # 安全预检（无副作用）
  bash scripts/deploy.sh -w "Nightly photobook refresh" --go      # push + 触发 + 轮询
  # 可选：-r <ref>  分支；--push 只推送；--dispatch 只触发
  ```
  远端领先会直接拒绝；触发后校验 run 的 `event=workflow_dispatch` 且 `headSha==HEAD`；
  轮询上限约 25 分钟（兼容限流窗口重试），非 success 退出码非零并打印失败日志。
- `scripts/verify_live.py`：抓线上页面做唯一性/目标核对；复制到新项目时只改顶部 CONFIG。
  ```bash
  python3 scripts/verify_live.py [URL] [--ignore-target]
  ```

脚本调用方式与裸命令无关：确认两个脚本都带可执行位（`chmod +x scripts/*.sh scripts/*.py`）。

## 发布前自检

```bash
python3 -m unittest discover
node --test runtime/*.test.mjs
node --test books/2026/*.test.mjs
python3 -m tools.layout_gate
python3 tools/photo_layout_gate.py books/2026/index.html
```

注意 `books/2026/` 是旧发布物时，`validate_release.py` 可能因新门禁（如封面重复）报错，
属预期；CI 用新代码重新 build 后即通过，不要据此回退代码。

## 手工流程（脚本不可用时的等价步骤）

1. `git status --short` 盘点；按语义把功能与文档拆独立 commit，只精确 `git add <文件>`，
   禁止 `git add -A`，避免混入临时/产物文件。
2. Conventional Commits（`feat/fix/docs/chore(scope): ...`），现在时祈使句；不 amend、不 force push。
3. 推送前预检：`git fetch origin` 后
   `git rev-list --left-right --count HEAD...origin/main`（左=本地领先，右=远端领先）；
   右值>0 先 rebase/merge 并确认关键改动仍在。
4. `git push origin main`，确认计数变 `0  0`，记录 `git rev-parse HEAD`。
5. 触发：`gh workflow run "$WORKFLOW" --ref main`；`sleep 12` 后用
   `gh run list --workflow="$WORKFLOW" --limit 1 ...` 核对 event 与 sha。
6. `gh run view <RUN_ID> --json status,conclusion --jq '"\(.status) \(.conclusion)"'` 轮询到
   `completed success`；失败用 `gh run view <RUN_ID> --log-failed`，走**新 commit** 修复。
7. 核对流水线关键步骤与日志（见下）。
8. 核对线上（Pages 可能有数十秒延迟，必要时轮询）。

## 核对（本仓库判据，复制后替换）

- `Fetch / Build / Test and validate / Publish` 四步均 `success`。
- 日志：`built ... photos=<唯一数>/<目标> uploads=<当年上传数>`，唯一数达成目标；
  `release valid: photos=.. target=.. baseline=..`，动态画册按本次 target 的 90% 判定，
  且不出现 `cover photo repeated` / `duplicate photo in body`。
- `verify_live.py` 输出 `cover_in_body=False`、`body_unique==body 数`、`total_unique==target`、`PASS`。
  `athlete` 头像在多张高光页复用属豁免。

## 复制到其它仓库的清单

1. 拷贝整个 skill 目录；按需改 `name`（目录名与 frontmatter 必须一致）与触发词。
2. 改本文件「项目配置」表与「发布前自检/核对」命令。
3. 改 `verify_live.py` 顶部 CONFIG（或换成项目自己的验收脚本）；`deploy.sh` 通常无需改动。
4. 确认 `gh` 已登录、workflow 启用了 `workflow_dispatch`、分支名与 `-r` 一致。

## 安全边界

- 仅在用户明确要求部署时 dispatch；不要为“跑测试/看效果”而发布。
- 不打印 secrets，不改 git config，不 force push，不跳过 hook；远端领先时先同步不强推。
- 汇报：commit 链接、Run 链接、关键日志行、线上核对结果。
