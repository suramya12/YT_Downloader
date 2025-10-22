"""
Configuration management using Pydantic for validation and type safety.

This module handles application settings persistence and provides:
- Cross-platform configuration directories using platformdirs
- Type-safe settings with Pydantic validation
- Automatic settings migration and defaults
- JSON-based configuration storage
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from platformdirs import user_config_dir, user_data_dir
from pathlib import Path
import json

APP_NAME = "LiquidGlassDownloader"
APP_AUTHOR = "LiquidGlass"


class Settings(BaseModel):
    """
    Application settings with validation and type safety.

    All settings are persisted to a JSON configuration file and loaded
    on application startup. Pydantic ensures type safety and validation.
    """
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

    # Auto-update settings (new in v2.3.0)
    auto_update_enabled: bool = True  # Enable automatic updates on startup
    auto_update_ytdlp_only: bool = True  # Only auto-update critical packages (yt-dlp)
    check_updates_on_startup: bool = True  # Check for available updates
    notify_updates_available: bool = True  # Show notification when updates are available


class Config:
    """
    Configuration manager with cross-platform directory support.

    Automatically creates necessary directories for:
    - Configuration files (settings.json)
    - Data files (downloads.sqlite3)
    - Thumbnails cache
    - Log files
    """

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
        """
        Load settings from configuration file.

        If the file doesn't exist or is corrupted, creates a new
        settings file with default values.

        Returns:
            Loaded or default Settings object
        """
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
        """
        Save settings to configuration file.

        Args:
            settings: Settings object to persist

        Side Effects:
            - Writes settings to JSON file with pretty-printing
            - Updates self.settings with the new settings
        """
        self.config_file.write_text(
            settings.model_dump_json(indent=2), encoding="utf-8"
        )
        self.settings = settings


CONFIG = Config()
