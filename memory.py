"""
持久记忆 —— SQLite 存储聊天记录和用户偏好。

两个表:
- messages:   (id, role, content, created_at)
- preferences: (key, value, created_at, updated_at)

每次对话从最近 N 条消息 + 全部偏好构建上下文，
每几轮自动从对话中提取新的用户偏好。
"""

import sqlite3
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "memory.db"

HISTORY_LIMIT = 30  # 每次注入上下文的历史消息条数


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    created_at: float


class MemoryStore:
    """SQLite 记忆存储。"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    # ── 初始化 ──────────────────────────────────────────

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()

    # ── 消息 ────────────────────────────────────────────

    def add_message(self, role: str, content: str):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
                (role, content, time.time()),
            )
            conn.commit()

    def recent_messages(self, limit: int = HISTORY_LIMIT) -> list[Message]:
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM messages ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            Message(role=r[0], content=r[1], created_at=r[2])
            for r in reversed(rows)  # 时间顺序
        ]

    def message_count(self) -> int:
        with sqlite3.connect(str(self.db_path)) as conn:
            return conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

    def clear_messages(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM messages")
            conn.commit()

    # ── 偏好 ────────────────────────────────────────────

    def set_preference(self, key: str, value: str):
        now = time.time()
        with sqlite3.connect(str(self.db_path)) as conn:
            existing = conn.execute(
                "SELECT value FROM preferences WHERE key = ?", (key,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE preferences SET value = ?, updated_at = ? WHERE key = ?",
                    (value, now, key),
                )
            else:
                conn.execute(
                    "INSERT INTO preferences (key, value, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (key, value, now, now),
                )
            conn.commit()

    def all_preferences(self) -> dict[str, str]:
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT key, value FROM preferences ORDER BY updated_at DESC"
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def clear_preferences(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM preferences")
            conn.commit()

    # ── 工具 ────────────────────────────────────────────

    def reset(self):
        """清空所有记忆。"""
        self.clear_messages()
        self.clear_preferences()

    def stats(self) -> dict:
        return {
            "messages": self.message_count(),
            "preferences": len(self.all_preferences()),
        }
