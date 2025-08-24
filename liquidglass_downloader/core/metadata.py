from __future__ import annotations
from yt_dlp import YoutubeDL
import requests, os
from .config import CONFIG
from .db import DB_INSTANCE as DB
from .logging_util import get_logger

log = get_logger("metadata")

def fetch_and_store(item_id: int, url: str) -> None:
    try:
        with YoutubeDL({"quiet": True, "skip_download": True, "noplaylist": False}) as ydl:
            info = ydl.extract_info(url, download=False)
        title = info.get("title")
        thumb = info.get("thumbnail")
        duration = info.get("duration")
        uploader = info.get("uploader")
        thumb_path = None
        if thumb:
            try:
                fn = os.path.join(CONFIG.thumb_dir, f"{item_id}.jpg")
                r = requests.get(thumb, timeout=15)
                if r.ok:
                    with open(fn, "wb") as f:
                        f.write(r.content)
                    thumb_path = fn
            except Exception as e:
                log.warning("thumbnail fetch failed: %s", e)
        DB.update(item_id, title=title, duration=duration, uploader=uploader, thumb_path=thumb_path)
    except Exception as e:
        log.warning("metadata fetch failed: %s", e)
