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
    format: str = "bv*+ba/best"
    audio_only: bool = False
    embed_subtitles: bool = False
    embed_thumbnail: bool = True
    theme: str = "Dark"
    clipboard_watch: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    cookies_file: str | None = None
    player_client: str = "web"


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
