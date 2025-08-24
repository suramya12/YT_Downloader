from __future__ import annotations
import sqlite3, time
from pathlib import Path
from typing import List, Optional, Any
from .models import QueueItem, Status
from .config import CONFIG

# Only declare the table; don't create indexes until after migration.
SCHEMA = '''
CREATE TABLE IF NOT EXISTS downloads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  title TEXT,
  status TEXT NOT NULL,
  filepath TEXT,
  added_at REAL,
  updated_at REAL,
  total_bytes INTEGER,
  downloaded_bytes INTEGER,
  speed REAL,
  eta INTEGER,
  errmsg TEXT,
  format TEXT,
  position INTEGER DEFAULT 0,
  thumb_path TEXT,
  uploader TEXT,
  duration INTEGER
);
'''

def _column_exists(con: sqlite3.Connection, table: str, col: str) -> bool:
    cur = con.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())

class DB:
    def __init__(self, db_path: Path) -> None:
        self.path = db_path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as con:
            # 1) Ensure table exists (no indexes yet)
            con.executescript(SCHEMA)

            # 2) Add missing columns for legacy DBs
            migrations = {
                "position": "INTEGER DEFAULT 0",
                "thumb_path": "TEXT",
                "uploader": "TEXT",
                "duration": "INTEGER",
            }
            for col, decl in migrations.items():
                if not _column_exists(con, "downloads", col):
                    con.execute(f"ALTER TABLE downloads ADD COLUMN {col} {decl}")

            # 3) Create indexes AFTER columns exist
            con.execute("CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_downloads_position ON downloads(position)")

            # 4) Seed position for rows lacking it
            con.execute("UPDATE downloads SET position = id WHERE position IS NULL OR position = 0")

    def add_queue_item(self, url: str, fmt: str) -> int:
        now = time.time()
        with self._connect() as con:
            # compute next position
            (mx,) = con.execute("SELECT COALESCE(MAX(position), 0) FROM downloads").fetchone()
            pos = int(mx) + 1
            cur = con.execute(
                "INSERT INTO downloads (url, status, added_at, updated_at, format, position) VALUES (?, ?, ?, ?, ?, ?)",
                (url, "queued", now, now, fmt, pos),
            )
            return cur.lastrowid

    def update(self, item_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = time.time()
        keys = ", ".join([f"{k}=?" for k in fields.keys()])
        values = list(fields.values()) + [item_id]
        with self._connect() as con:
            con.execute(f"UPDATE downloads SET {keys} WHERE id=?", values)

    def get(self, item_id: int) -> Optional[QueueItem]:
        with self._connect() as con:
            row = con.execute("SELECT * FROM downloads WHERE id=?", (item_id,)).fetchone()
            return QueueItem(**dict(row)) if row else None

    def list(self, status: Optional[str] = None) -> list[QueueItem]:
        with self._connect() as con:
            if status:
                rows = con.execute("SELECT * FROM downloads WHERE status=? ORDER BY position ASC", (status,)).fetchall()
            else:
                rows = con.execute("SELECT * FROM downloads ORDER BY position ASC").fetchall()
            return [QueueItem(**dict(r)) for r in rows]

    def search(self, term: str) -> list[QueueItem]:
        like = f"%{term}%"
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM downloads WHERE url LIKE ? OR title LIKE ? OR filepath LIKE ? ORDER BY position ASC",
                (like, like, like),
            ).fetchall()
            return [QueueItem(**dict(r)) for r in rows]

    def delete(self, item_id: int) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM downloads WHERE id=?", (item_id,))

    def move_up(self, item_id: int) -> None:
        with self._connect() as con:
            row = con.execute("SELECT id, position FROM downloads WHERE id=?", (item_id,)).fetchone()
            if not row: return
            pos = row["position"]
            above = con.execute("SELECT id, position FROM downloads WHERE position < ? ORDER BY position DESC LIMIT 1", (pos,)).fetchone()
            if not above: return
            con.execute("UPDATE downloads SET position=? WHERE id=?", (above["position"], item_id))
            con.execute("UPDATE downloads SET position=? WHERE id=?", (pos, above["id"]))

    def move_down(self, item_id: int) -> None:
        with self._connect() as con:
            row = con.execute("SELECT id, position FROM downloads WHERE id=?", (item_id,)).fetchone()
            if not row: return
            pos = row["position"]
            below = con.execute("SELECT id, position FROM downloads WHERE position > ? ORDER BY position ASC LIMIT 1", (pos,)).fetchone()
            if not below: return
            con.execute("UPDATE downloads SET position=? WHERE id=?", (below["position"], item_id))
            con.execute("UPDATE downloads SET position=? WHERE id=?", (pos, below["id"]))

    def clear_history(self) -> None:
        """Remove completed, error and canceled items."""
        with self._connect() as con:
            con.execute(
                "DELETE FROM downloads WHERE status IN (?, ?, ?)",
                (
                    Status.COMPLETED.value,
                    Status.ERROR.value,
                    Status.CANCELED.value,
                ),
            )

DB_INSTANCE = DB(CONFIG.db_file)
