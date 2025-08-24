from __future__ import annotations
from pydantic import BaseModel, Field
from platformdirs import user_config_dir, user_data_dir
from pathlib import Path
import json

APP_NAME = "LiquidGlassDownloader"
APP_AUTHOR = "LiquidGlass"


class Settings(BaseModel):
    download_dir: str = Field(default_factory=lambda: str(Path.home() / "Downloads"))
    concurrent_downloads: int = 3
    format: str = (
        "bestvideo[ext=mp4][height>=2160][fps>=60]+"
        "bestaudio[ext=m4a][abr>=160]/bestvideo[ext=mp4][height>=2160]+"
        "bestaudio[ext=m4a][abr>=128]/bestvideo[ext=mp4][height>=1440][fps>=60]+"
        "bestaudio[ext=m4a][abr>=128]/bestvideo[ext=mp4][height>=1440]+"
        "bestaudio[ext=m4a][abr>=128]/bestvideo[ext=mp4][height>=1080][fps>=60]+"
        "bestaudio[ext=m4a][abr>=128]/bestvideo[ext=mp4][height>=1080]+"
        "bestaudio[ext=m4a][abr>=128]/best[ext=mp4]/best"
    )
    preferred_quality: str = "1080p"  # New setting for preferred quality
    preferred_fps: int = 60  # New setting for preferred FPS
    audio_quality: str = "best"  # New setting for audio quality
    audio_only: bool = False
    embed_subtitles: bool = True  # Changed default to True
    embed_thumbnail: bool = True
    auto_subtitles: bool = True  # New setting for automatic subtitle download
    theme: str = "Dark"
    clipboard_watch: bool = True
    user_agent: str = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"  # iOS User-Agent
    )
    cookies_file: str | None = None
    player_client: str = "web"  # Using web client for better compatibility
    browser_for_cookies: str = "chrome"  # Options: chrome, firefox, edge, opera, safari, chromium
    use_cookies_from_browser: bool = True  # Enable browser cookies by default


class Config:
    def __init__(self) -> None:
        self.config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
        self.data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
        self.thumb_dir = self.data_dir / "thumbs"
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "settings.json"
        self.db_file = self.data_dir / "downloads.sqlite3"
        self.log_dir = self.data_dir / "logs"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.settings = self._load()

    def _load(self) -> Settings:
        if self.config_file.exists():
            try:
                return Settings(
                    **json.loads(self.config_file.read_text(encoding="utf-8"))
                )
            except Exception:
                pass
        s = Settings()
        self.save(s)
        return s

    def save(self, settings: Settings) -> None:
        self.config_file.write_text(
            settings.model_dump_json(indent=2), encoding="utf-8"
        )
        self.settings = settings


CONFIG = Config()
