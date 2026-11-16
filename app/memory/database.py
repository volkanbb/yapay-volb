"""SQLite persistence: conversations, preferences, memories, tasks, research, settings, action log."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from ..core.config import DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL, content TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'genel',
    created_at REAL NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, state TEXT NOT NULL,
    steps TEXT NOT NULL DEFAULT '[]', result TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL, report TEXT NOT NULL, sources TEXT NOT NULL DEFAULT '[]', created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at REAL NOT NULL, provider TEXT NOT NULL, purpose TEXT NOT NULL,
    model TEXT NOT NULL, input INTEGER NOT NULL, output INTEGER NOT NULL, cache_read INTEGER NOT NULL,
    cache_write INTEGER NOT NULL, cost_usd REAL NOT NULL, duration_ms INTEGER NOT NULL, is_error INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS usage_log_time ON usage_log(created_at);
CREATE TABLE IF NOT EXISTS rate_limits (
    limit_type TEXT PRIMARY KEY, info TEXT NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
    run_at REAL NOT NULL, repeat TEXT NOT NULL DEFAULT '', enabled INTEGER NOT NULL DEFAULT 1,
    last_run REAL, last_result TEXT, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL, params TEXT NOT NULL, ok INTEGER NOT NULL, message TEXT, created_at REAL NOT NULL
);
"""


class Database:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else DATA_DIR / "volb.db"
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def _exec(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, args)
            self._conn.commit()
            return cur

    def _rows(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, args).fetchall()]

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # conversations ---------------------------------------------------------
    def add_message(self, role: str, content: str) -> int:
        return self._exec("INSERT INTO conversations(role, content, created_at) VALUES (?,?,?)",
                          (role, content, time.time())).lastrowid or 0

    def recent_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._rows("SELECT * FROM conversations ORDER BY id DESC LIMIT ?", (limit,))
        return list(reversed(rows))

    def clear_conversations(self) -> None:
        self._exec("DELETE FROM conversations")

    # preferences -----------------------------------------------------------
    def set_preference(self, key: str, value: str) -> None:
        self._exec("INSERT INTO preferences(key, value, updated_at) VALUES (?,?,?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                   (key, value, time.time()))

    def preferences(self) -> dict[str, str]:
        return {r["key"]: r["value"] for r in self._rows("SELECT key, value FROM preferences")}

    # memories --------------------------------------------------------------
    def add_memory(self, content: str, category: str = "genel") -> int:
        now = time.time()
        return self._exec("INSERT INTO memories(content, category, created_at, updated_at) VALUES (?,?,?,?)",
                          (content, category, now, now)).lastrowid or 0

    def update_memory(self, mem_id: int, content: str) -> None:
        self._exec("UPDATE memories SET content=?, updated_at=? WHERE id=?", (content, time.time(), mem_id))

    def delete_memory(self, mem_id: int) -> None:
        self._exec("DELETE FROM memories WHERE id=?", (mem_id,))

    def list_memories(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM memories ORDER BY updated_at DESC")

    # tasks -----------------------------------------------------------------
    def save_task(self, task: dict[str, Any]) -> None:
        now = time.time()
        self._exec(
            "INSERT INTO tasks(id, title, state, steps, result, created_at, updated_at) VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET title=excluded.title, state=excluded.state, steps=excluded.steps, "
            "result=excluded.result, updated_at=excluded.updated_at",
            (task["id"], task["title"], task["state"], json.dumps(task.get("steps", []), ensure_ascii=False),
             task.get("result"), task.get("created_at", now), now))

    def list_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._rows("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,))
        for r in rows:
            r["steps"] = json.loads(r["steps"])
        return rows

    # research --------------------------------------------------------------
    def save_research(self, topic: str, report: str, sources: list[dict[str, Any]]) -> int:
        return self._exec("INSERT INTO research(topic, report, sources, created_at) VALUES (?,?,?,?)",
                          (topic, report, json.dumps(sources, ensure_ascii=False), time.time())).lastrowid or 0

    def list_research(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._rows("SELECT * FROM research ORDER BY id DESC LIMIT ?", (limit,))
        for r in rows:
            r["sources"] = json.loads(r["sources"])
        return rows

    def delete_research(self, rid: int) -> None:
        self._exec("DELETE FROM research WHERE id=?", (rid,))

    # settings --------------------------------------------------------------
    def load_settings(self) -> dict[str, Any]:
        return {r["key"]: json.loads(r["value"]) for r in self._rows("SELECT key, value FROM settings")}

    def save_setting(self, key: str, value: Any) -> None:
        self._exec("INSERT INTO settings(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                   (key, json.dumps(value)))

    # action log ------------------------------------------------------------
    def log_action(self, action: str, params: dict[str, Any], ok: bool, message: str) -> None:
        self._exec("INSERT INTO action_log(action, params, ok, message, created_at) VALUES (?,?,?,?,?)",
                   (action, json.dumps(params, ensure_ascii=False), int(ok), message, time.time()))

    def recent_actions(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM action_log ORDER BY id DESC LIMIT ?", (limit,))

    # schedules -------------------------------------------------------------
    def add_schedule(self, title: str, kind: str, payload: str, run_at: float, repeat: str = "") -> int:
        return self._exec("INSERT INTO schedules(title, kind, payload, run_at, repeat, enabled, created_at) "
                          "VALUES (?,?,?,?,?,1,?)", (title, kind, payload, run_at, repeat, time.time())).lastrowid or 0

    def list_schedules(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM schedules ORDER BY enabled DESC, run_at ASC")

    def due_schedules(self, now: float) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM schedules WHERE enabled = 1 AND run_at <= ? ORDER BY run_at", (now,))

    def update_schedule(self, sid: int, **fields: Any) -> None:
        allowed = {"title", "run_at", "repeat", "enabled", "last_run", "last_result", "payload"}
        cols = [k for k in fields if k in allowed]
        if cols:
            self._exec(f"UPDATE schedules SET {', '.join(c + '=?' for c in cols)} WHERE id=?",  # noqa: S608
                       (*[fields[c] for c in cols], sid))

    def delete_schedule(self, sid: int) -> None:
        self._exec("DELETE FROM schedules WHERE id=?", (sid,))

    # AI usage --------------------------------------------------------------
    def log_usage(self, rec: dict[str, Any]) -> None:
        now = rec.get("created_at", time.time())
        models = rec.get("models") or {"?": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0,
                                              "cost": rec.get("cost_usd", 0.0)}}
        for i, (model, m) in enumerate(models.items()):
            self._exec(
                "INSERT INTO usage_log(created_at, provider, purpose, model, input, output, cache_read, cache_write, "
                "cost_usd, duration_ms, is_error) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (now, rec.get("provider", ""), rec.get("purpose", ""), model, m.get("input", 0), m.get("output", 0),
                 m.get("cache_read", 0), m.get("cache_write", 0), m.get("cost", 0.0),
                 rec.get("duration_ms", 0) if i == 0 else 0, int(bool(rec.get("is_error")))))

    def save_rate_limit(self, info: dict[str, Any]) -> None:
        kind = str(info.get("rateLimitType") or "unknown")
        self._exec("INSERT INTO rate_limits(limit_type, info, updated_at) VALUES (?,?,?) "
                   "ON CONFLICT(limit_type) DO UPDATE SET info=excluded.info, updated_at=excluded.updated_at",
                   (kind, json.dumps(info), time.time()))

    def rate_limits(self) -> list[dict[str, Any]]:
        out = []
        for r in self._rows("SELECT * FROM rate_limits ORDER BY limit_type"):
            info = json.loads(r["info"])
            info["updated_at"] = r["updated_at"]
            out.append(info)
        return out

    def usage_summary(self, now: float | None = None) -> dict[str, Any]:
        import datetime as _dt
        now = now or time.time()
        midnight = _dt.datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        tot = ("COUNT(DISTINCT created_at) AS calls, "
               "COALESCE(SUM(input),0) AS input, COALESCE(SUM(output),0) AS output, "
               "COALESCE(SUM(cache_read),0) AS cache_read, COALESCE(SUM(cache_write),0) AS cache_write, "
               "COALESCE(SUM(cost_usd),0) AS cost")

        def window(since: float) -> dict[str, Any]:
            row = self._rows(f"SELECT {tot} FROM usage_log WHERE created_at >= ?", (since,))[0]  # noqa: S608
            row["total"] = row["input"] + row["output"] + row["cache_read"] + row["cache_write"]
            return row

        week = now - 7 * 86400
        by_purpose = self._rows(f"SELECT purpose, {tot} FROM usage_log WHERE created_at >= ? GROUP BY purpose "  # noqa: S608
                                "ORDER BY cost DESC", (week,))
        by_model = self._rows(f"SELECT model, {tot} FROM usage_log WHERE created_at >= ? GROUP BY model "  # noqa: S608
                              "ORDER BY cost DESC", (week,))
        for r in by_purpose + by_model:
            r["total"] = r["input"] + r["output"] + r["cache_read"] + r["cache_write"]
        daily = []
        for d in range(6, -1, -1):
            start = midnight - d * 86400
            w = self._rows("SELECT COALESCE(SUM(input+output+cache_read+cache_write),0) AS t, "
                           "COALESCE(SUM(output),0) AS o FROM usage_log WHERE created_at >= ? AND created_at < ?",
                           (start, start + 86400))[0]
            daily.append({"day": _dt.datetime.fromtimestamp(start).strftime("%d.%m"), "total": w["t"], "output": w["o"]})
        recent = self._rows("SELECT created_at, purpose, model, input, output, cache_read, cache_write, cost_usd "
                            "FROM usage_log ORDER BY id DESC LIMIT 12")
        return {"today": window(midnight), "last5h": window(now - 5 * 3600), "week": window(week),
                "all": window(0), "byPurpose": by_purpose, "byModel": by_model, "daily": daily, "recent": recent}

    # export / wipe ---------------------------------------------------------
    def export_all(self, path: Path) -> Path:
        data = {
            "exported_at": time.time(),
            "conversations": self._rows("SELECT * FROM conversations ORDER BY id"),
            "preferences": self.preferences(),
            "memories": self.list_memories(),
            "tasks": self.list_tasks(10_000),
            "research": self.list_research(10_000),
            "settings": self.load_settings(),
            "action_log": self._rows("SELECT * FROM action_log ORDER BY id"),
            "usage_log": self._rows("SELECT * FROM usage_log ORDER BY id"),
            "schedules": self.list_schedules(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def wipe_personal_data(self) -> None:
        for table in ("conversations", "preferences", "memories", "tasks", "research", "action_log", "usage_log",
                      "schedules"):
            self._exec(f"DELETE FROM {table}")  # noqa: S608 - fixed table names
