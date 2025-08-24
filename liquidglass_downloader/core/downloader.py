from __future__ import annotations
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
import os
import time

from yt_dlp import YoutubeDL
from .config import CONFIG
from .db import DB_INSTANCE as DB
from .models import Status
from .logging_util import get_logger
from . import metadata

log = get_logger("downloader")


class _TaskControl:
    def __init__(self) -> None:
        self.cancel = threading.Event()
        self.pause = threading.Event()


class DownloadManager:
    def __init__(self) -> None:
        self.exec = ThreadPoolExecutor(max_workers=CONFIG.settings.concurrent_downloads)
        self.controls: Dict[int, _TaskControl] = {}
        self.lock = threading.Lock()

    def set_concurrency(self, n: int) -> None:
        if n < 1:
            n = 1
        if n == CONFIG.settings.concurrent_downloads:
            return
        CONFIG.settings.concurrent_downloads = n
        CONFIG.save(CONFIG.settings)
        old = self.exec
        self.exec = ThreadPoolExecutor(max_workers=n)
        old.shutdown(wait=False, cancel_futures=True)

    def queue(self, url: str, fmt: str | None = None) -> int:
        item_id = DB.add_queue_item(url, fmt or CONFIG.settings.format)
        self.exec.submit(metadata.fetch_and_store, item_id, url)
        log.info("Queued %s -> id %s", url, item_id)
        return item_id

    def start(self, item_id: int) -> None:
        with self.lock:
            ctl = self.controls.get(item_id) or _TaskControl()
            self.controls[item_id] = ctl
        self.exec.submit(self._run, item_id, ctl)

    def start_all(self) -> None:
        for r in DB.list():
            if r.status in (Status.QUEUED, Status.PAUSED, Status.ERROR):
                self.start(r.id)

    def pause(self, item_id: int) -> None:
        ctl = self.controls.get(item_id)
        if ctl:
            ctl.pause.set()

    def pause_all(self) -> None:
        for r in DB.list():
            self.pause(r.id)

    def cancel(self, item_id: int) -> None:
        ctl = self.controls.get(item_id)
        if ctl:
            ctl.cancel.set()

    def cancel_all(self) -> None:
        for r in DB.list():
            self.cancel(r.id)

    def resume(self, item_id: int) -> None:
        DB.update(item_id, status=Status.QUEUED.value, errmsg=None)
        self.start(item_id)

    def _progress_hook(self, item_id: int, ctl: _TaskControl):
        last: dict[str, float] = {"time": 0.0, "downloaded": -1}

        def hook(d: dict) -> None:
            if ctl.cancel.is_set():
                raise Exception("Canceled by user")
            if ctl.pause.is_set():
                raise Exception("Paused by user")
            status = d.get("status")
            if status == "downloading":
                now = time.time()
                downloaded = d.get("downloaded_bytes") or 0
                if downloaded != last["downloaded"] and now - last["time"] > 0.5:
                    DB.update(
                        item_id,
                        status=Status.DOWNLOADING.value,
                        downloaded_bytes=downloaded,
                        total_bytes=d.get("total_bytes")
                        or d.get("total_bytes_estimate"),
                        speed=d.get("speed"),
                        eta=d.get("eta"),
                        title=d.get("info_dict", {}).get("title"),
                    )
                    last["time"] = now
                    last["downloaded"] = downloaded
            elif status == "finished":
                DB.update(
                    item_id, status=Status.COMPLETED.value, filepath=d.get("filename")
                )

        return hook

    def _build_ydl_opts(
        self, item_id: int, ctl: _TaskControl, fmt: str, postprocessors: list[dict]
    ) -> Dict[str, Any]:
        outtmpl = os.path.join(
            CONFIG.settings.download_dir, "%(title)s [%(id)s].%(ext)s"
        )
        opts: Dict[str, Any] = {
            "outtmpl": outtmpl,
            "format": "bestaudio/best" if CONFIG.settings.audio_only else fmt,
            "merge_output_format": "mp3" if CONFIG.settings.audio_only else "mp4",
            "continuedl": True,
            "ignoreerrors": True,
            "noprogress": True,
            "retries": 3,
            "fragment_retries": 3,
            "skip_unavailable_fragments": True,
            "progress_hooks": [self._progress_hook(item_id, ctl)],
            "nopart": False,
            "http_headers": {
                "User-Agent": CONFIG.settings.user_agent,
                "Referer": "https://www.youtube.com/",
            },
            "extractor_args": {
                "youtube": {"player_client": [CONFIG.settings.player_client]}
            },
        }
        if CONFIG.settings.cookies_file:
            opts["cookiefile"] = CONFIG.settings.cookies_file
        if postprocessors:
            opts["postprocessors"] = postprocessors
        return opts

    def _run(self, item_id: int, ctl: _TaskControl) -> None:
        row = DB.get(item_id)
        if not row:
            return
        fmt = row.format or CONFIG.settings.format
        postprocessors: list[dict[str, Any]] = []
        if CONFIG.settings.embed_thumbnail:
            postprocessors.append({"key": "EmbedThumbnail"})
        if CONFIG.settings.embed_subtitles:
            postprocessors.append({"key": "FFmpegEmbedSubtitle"})
        ydl_opts = self._build_ydl_opts(item_id, ctl, fmt, postprocessors)
        try:
            DB.update(item_id, status=Status.QUEUED.value)
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([row.url])
            DB.update(item_id, status=Status.COMPLETED.value)
            log.info("Completed id=%s", item_id)
        except Exception as e:
            msg = str(e)
            log.warning("Task id=%s interrupted: %s", item_id, msg)
            if "Paused by user" in msg:
                DB.update(item_id, status=Status.PAUSED.value, errmsg=None)
            elif "Canceled by user" in msg:
                DB.update(item_id, status=Status.CANCELED.value, errmsg=None)
            else:
                DB.update(item_id, status=Status.ERROR.value, errmsg=msg)
