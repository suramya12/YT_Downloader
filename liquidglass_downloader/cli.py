from __future__ import annotations
import argparse
from .core.config import CONFIG
from .core.downloader import DownloadManager
from .core.db import DB_INSTANCE as DB
from .core.models import Status

def main(argv=None):
    p = argparse.ArgumentParser(description="LiquidGlass Downloader (CLI)")
    p.add_argument("urls", nargs="+", help="One or more video/playlist URLs")
    p.add_argument("-o", "--output", help="Download directory (overrides config)")
    p.add_argument("-f", "--format", default=None, help="yt-dlp format string")
    p.add_argument("-c", "--concurrency", type=int, default=None, help="Concurrent downloads")
    args = p.parse_args(argv)

    if args.output:
        s = CONFIG.settings
        s.download_dir = args.output
        CONFIG.save(s)
    if args.concurrency:
        CONFIG.settings.concurrent_downloads = max(1, args.concurrency)
        CONFIG.save(CONFIG.settings)

    dm = DownloadManager()
    item_ids = [dm.queue(u, args.format) for u in args.urls]
    for item_id in item_ids:
        dm.start(item_id)

    try:
        while True:
            rows = [DB.get(i) for i in item_ids]
            if all(r and r.status in (Status.COMPLETED, Status.ERROR, Status.CANCELED) for r in rows):
                break
    except KeyboardInterrupt:
        for item_id in item_ids:
            dm.cancel(item_id)

if __name__ == "__main__":
    main()
