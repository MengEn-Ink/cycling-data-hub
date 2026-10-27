"""配置：凭证与路径，无硬编码位置。

优先级（从高到低）：
  1. 环境变量
  2. 项目根目录的 .env 文件（KEY=VALUE，不提交）
  3. 内置默认值（相对项目根目录）

密钥（STRAVA_CLIENT_ID/_SECRET/_REFRESH_TOKEN）只来自环境变量或 .env。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .model import MAX_PHOTOS_PER_RIDE, PHOTO_CAP, PHOTO_FLOOR, PHOTO_RATIO


def _load_dotenv(path: Path) -> None:
    """读取极简 .env（KEY=VALUE），不覆盖已存在的真实环境变量。"""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


@dataclass
class StravaCreds:
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)


@dataclass(repr=False)
class GitHubConfig:
    client_id: str = ""
    token: str = ""
    api_url: str = "https://api.github.com"
    upload_limit_bytes: int = 50 * 1024 * 1024

    def __repr__(self) -> str:
        return (
            "GitHubConfig(client_id=%r, token=%s, api_url=%r, upload_limit_bytes=%r)"
            % (self.client_id, "<set>" if self.token else "<empty>", self.api_url, self.upload_limit_bytes)
        )


@dataclass
class IntervalsCreds:
    api_key: str = ""
    athlete_id: str = "0"

    @property
    def ready(self) -> bool:
        return bool(self.api_key)


@dataclass
class Config:
    root: Path
    data_dir: Path
    books_dir: Path
    runtime_dir: Path
    strava: StravaCreds
    github: GitHubConfig
    intervals: IntervalsCreds = field(default_factory=IntervalsCreds)
    # 调优项（可用环境变量覆盖）
    max_photo_edge: int = 1600
    # None = 照片数按当年上传量动态决定（见 model.target_photo_count）；
    # 显式设置 PHOTOBOOK_PHOTOS_PER_BOOK 时作为强制固定值（逃生舱）。
    photos_per_book: int | None = None
    feature_rides: int = 6
    request_pause: float = 1.0
    # 动态照片数护栏（仅在 photos_per_book 为 None 时生效）
    photo_ratio: float = 0.60
    photo_floor: int = 40
    photo_cap: int = 120
    max_photos_per_ride: int = 6

    @classmethod
    def load(cls, root: str | Path | None = None) -> "Config":
        root = Path(root or os.getenv("PHOTOBOOK_ROOT") or Path.cwd()).resolve()
        _load_dotenv(root / ".env")

        def _path(env: str, default: str) -> Path:
            p = Path(os.getenv(env) or default)
            return p if p.is_absolute() else (root / p)

        def _int(env: str, default: int) -> int:
            try:
                return int(os.getenv(env, default))
            except ValueError:
                return default

        def _float(env: str, default: float) -> float:
            try:
                return float(os.getenv(env, default))
            except ValueError:
                return default

        fixed_raw = os.getenv("PHOTOBOOK_PHOTOS_PER_BOOK", "").strip()
        try:
            photos_per_book = int(fixed_raw) if fixed_raw and int(fixed_raw) > 0 else None
        except ValueError:
            photos_per_book = None

        return cls(
            root=root,
            data_dir=_path("PHOTOBOOK_DATA_DIR", "data"),
            books_dir=_path("PHOTOBOOK_BOOKS_DIR", "books"),
            runtime_dir=_path("PHOTOBOOK_RUNTIME_DIR", "runtime"),
            strava=StravaCreds(
                client_id=os.getenv("STRAVA_CLIENT_ID", ""),
                client_secret=os.getenv("STRAVA_CLIENT_SECRET", ""),
                refresh_token=os.getenv("STRAVA_REFRESH_TOKEN", ""),
            ),
            github=GitHubConfig(
                client_id=os.getenv("GITHUB_CLIENT_ID", ""),
                token=os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN", ""),
                api_url=os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/"),
                upload_limit_bytes=_int("GITHUB_UPLOAD_LIMIT_BYTES", 50 * 1024 * 1024),
            ),
            intervals=IntervalsCreds(
                api_key=os.getenv("INTERVALS_API_KEY", ""),
                athlete_id=os.getenv("INTERVALS_ATHLETE_ID", "").strip() or "0",
            ),
            max_photo_edge=_int("PHOTOBOOK_MAX_PHOTO_EDGE", 1600),
            photos_per_book=photos_per_book,
            feature_rides=_int("PHOTOBOOK_FEATURE_RIDES", 6),
            photo_ratio=_float("PHOTOBOOK_PHOTO_RATIO", PHOTO_RATIO),
            photo_floor=_int("PHOTOBOOK_PHOTO_FLOOR", PHOTO_FLOOR),
            photo_cap=_int("PHOTOBOOK_PHOTO_CAP", PHOTO_CAP),
            max_photos_per_ride=_int("PHOTOBOOK_MAX_PHOTOS_PER_RIDE", MAX_PHOTOS_PER_RIDE),
        )

    @property
    def token_cache(self) -> Path:
        return self.data_dir / ".strava_token.json"

    @property
    def summaries_path(self) -> Path:
        return self.data_dir / "activities.json"

    @property
    def intervals_dir(self) -> Path:
        return self.data_dir / "intervals"

    def book_dir(self, year: str) -> Path:
        return self.books_dir / year

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.books_dir.mkdir(parents=True, exist_ok=True)
