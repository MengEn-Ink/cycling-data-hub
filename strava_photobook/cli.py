"""strava-photobook 命令行入口。

  python -m strava_photobook auth    一键浏览器 OAuth，把 STRAVA_REFRESH_TOKEN 写入 .env
  python -m strava_photobook fetch   拉取全部活动概要到 data/activities.json
  python -m strava_photobook build   生成某一年的翻页画册
  python -m strava_photobook years   列出缓存中的年份及活动/照片数

全部由 Config 驱动（环境变量 / .env）；无硬编码路径。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from .book import build_year
from .config import Config
from .model import by_year


def _cmd_auth(cfg: Config, args) -> None:
    from .strava.oauth import authorize

    cid = cfg.strava.client_id or input("STRAVA_CLIENT_ID: ").strip()
    secret = cfg.strava.client_secret or input("STRAVA_CLIENT_SECRET: ").strip()
    if not (cid and secret):
        raise SystemExit("需要 client_id 和 client_secret（在 https://www.strava.com/settings/api 创建应用）")
    token = authorize(cid, secret)
    refresh = token["refresh_token"]
    _update_env(cfg.root / ".env", {
        "STRAVA_CLIENT_ID": cid,
        "STRAVA_CLIENT_SECRET": secret,
        "STRAVA_REFRESH_TOKEN": refresh,
    })
    print(f"授权成功，refresh_token 已写入 {cfg.root / '.env'}")


def _update_env(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text("utf-8").splitlines() if path.is_file() else []
    keys = set(values)
    out = []
    for line in lines:
        k = line.split("=", 1)[0].strip() if "=" in line else ""
        if k in keys:
            out.append(f"{k}={values.pop(k)}")
        else:
            out.append(line)
    for k, v in values.items():
        out.append(f"{k}={v}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _cmd_fetch(cfg: Config, args) -> None:
    from . import source

    recs = source.fetch_activities(cfg, year=args.year)
    print(f"已缓存 {len(recs)} 条活动 -> {cfg.summaries_path}")


def _cmd_sync_intervals(cfg: Config, args) -> None:
    from .intervals import source as intervals_source

    result = intervals_source.sync_intervals(cfg, year=args.year)
    print(f"已缓存 {len(result['activities'])} 条 Intervals.icu 活动 -> "
          f"{cfg.intervals_dir / (args.year + '.json')}")


def _cmd_years(cfg: Config, args) -> None:
    from . import source

    acts = source.load_activities(cfg)
    for y, group in sorted(by_year(acts).items()):
        photos = sum(a.photo_count for a in group)
        print(f"  {y}: {len(group):4d} 次骑行, {photos:4d} 张照片")


def _cmd_build(cfg: Config, args) -> None:
    from . import source

    acts = source.load_activities(cfg)
    client = source.make_client(cfg)

    def hydrate(a, photos_dir, remaining, with_detail=True):
        source.hydrate_activity(
            cfg, client, a, photos_dir, remaining, with_detail=with_detail
        )

    def avatar_fetcher(photos_dir):
        return source.fetch_athlete_avatar(client, photos_dir)

    build_year(cfg, args.year, acts, hydrate, avatar_fetcher)


def _cmd_github_auth(cfg: Config, args) -> None:
    from .github.oauth import authorize_device

    if cfg.github.client_id:
        token = authorize_device(cfg.github.client_id)
    elif shutil.which("gh"):
        status = subprocess.run(
            ["gh", "auth", "status", "--hostname", "github.com"], capture_output=True, text=True
        )
        if status.returncode != 0:
            print("未配置 GITHUB_CLIENT_ID，使用本机 GitHub CLI 完成浏览器授权。")
            subprocess.run(
                ["gh", "auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web", "--scopes", "repo"],
                check=True,
            )
        token = subprocess.run(
            ["gh", "auth", "token", "--hostname", "github.com"], check=True, capture_output=True, text=True
        ).stdout.strip()
    else:
        raise SystemExit("请设置 GITHUB_CLIENT_ID，或安装 GitHub CLI 后重试")
    if not token:
        raise SystemExit("GitHub 授权未返回 token")
    _update_env(cfg.root / ".env", {"GITHUB_TOKEN": token})
    print(f"GitHub 授权成功，token 已安全写入 {cfg.root / '.env'}")


def _cmd_publish(cfg: Config, args) -> None:
    from .github.client import GitHubClient
    from .github.publisher import Publisher

    if not cfg.github.token:
        raise SystemExit("尚未获得 GitHub 授权，请先运行 github-auth，或设置 GH_TOKEN")
    book_dir = cfg.book_dir(args.year)
    repo_name = args.repo or f"strava-photobook-{args.year}"
    result = Publisher(
        GitHubClient(cfg.github.token, cfg.github.api_url),
        upload_limit_bytes=cfg.github.upload_limit_bytes,
    ).publish(book_dir, repo_name)
    print(f"GitHub 仓库：{result.repo_url}")
    print(f"Pages 页面：{result.pages_url}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="strava-photobook", description=__doc__)
    ap.add_argument("--root", help="项目根目录（默认取当前目录或 PHOTOBOOK_ROOT）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("auth", help="浏览器 OAuth 授权，获取 refresh token")
    fetch = sub.add_parser("fetch", help="缓存活动概要")
    fetch.add_argument("--year", help="只同步指定年份，适合每日自动更新")
    si = sub.add_parser("sync-intervals", help="同步 Intervals.icu 训练数据")
    si.add_argument("--year", required=True, help="同步指定年份")
    sub.add_parser("years", help="列出缓存中的年份")
    sub.add_parser("github-auth", help="通过 GitHub Device Flow 授权")
    b = sub.add_parser("build", help="生成某一年的翻页画册")
    b.add_argument("year")
    p = sub.add_parser("publish", help="发布某一年的画册到 GitHub Pages")
    p.add_argument("year")
    p.add_argument("--repo", help="GitHub 仓库名（默认 strava-photobook-<year>）")

    args = ap.parse_args(argv)
    cfg = Config.load(args.root)
    {
        "auth": _cmd_auth, "fetch": _cmd_fetch, "years": _cmd_years, "build": _cmd_build,
        "github-auth": _cmd_github_auth, "publish": _cmd_publish,
        "sync-intervals": _cmd_sync_intervals,
    }[args.cmd](cfg, args)


if __name__ == "__main__":
    main()
