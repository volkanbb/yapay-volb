"""Runs scheduled reminders and commands stored in SQLite (survives restarts while VOLB is closed)."""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from ..memory.database import Database
from .timeparse import next_occurrence

log = logging.getLogger(__name__)
GRACE = dt.timedelta(minutes=15)   # a one-off job missed by more than this (VOLB was closed) is not run late


class Scheduler:
    def __init__(self, db: Database, fire: Callable[[dict[str, Any]], Awaitable[str]],
                 on_change: Callable[[], None] | None = None, interval: float = 5.0) -> None:
        self.db = db
        self.fire = fire
        self.on_change = on_change or (lambda: None)
        self.interval = interval
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._run())

    async def _run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:  # noqa: BLE001
                log.exception("scheduler tick failed")
            await asyncio.sleep(self.interval)

    async def tick(self, now: dt.datetime | None = None) -> int:
        now = now or dt.datetime.now()
        fired = 0
        for job in self.db.due_schedules(now.timestamp()):
            run_at = dt.datetime.fromtimestamp(job["run_at"])
            late = now - run_at > GRACE
            nxt = next_occurrence(run_at, job["repeat"], now)
            if nxt:
                self.db.update_schedule(job["id"], run_at=nxt.timestamp())
            else:
                self.db.update_schedule(job["id"], enabled=0)
            if late:
                self.db.update_schedule(job["id"], last_result=f"Kaçırıldı ({run_at:%d.%m %H:%M}, VOLB kapalıydı)")
                self.on_change()
                continue
            self.db.update_schedule(job["id"], last_run=now.timestamp(), last_result="Çalışıyor…")
            self.on_change()
            log.info("schedule #%s firing: %s %s", job["id"], job["kind"], job["payload"])
            try:
                result = await self.fire(job)
            except Exception as exc:  # noqa: BLE001
                log.exception("scheduled job failed")
                result = f"Hata: {exc}"
            self.db.update_schedule(job["id"], last_result=(result or "Tamamlandı")[:300])
            self.on_change()
            fired += 1
        return fired
