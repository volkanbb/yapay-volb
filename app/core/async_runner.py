"""Runs a dedicated asyncio event loop in a background thread.

Qt owns the main thread; all async work (Claude CLI, Playwright, STT/TTS) runs here.
Results travel back to the UI through Qt signals, which are queued across threads.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from collections.abc import Coroutine
from typing import Any

log = logging.getLogger(__name__)


class AsyncRunner:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="volb-asyncio", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.set_exception_handler(self._on_exception)
        self.loop.run_forever()

    @staticmethod
    def _on_exception(loop: asyncio.AbstractEventLoop, ctx: dict[str, Any]) -> None:
        log.error("asyncio error: %s", ctx.get("message"), exc_info=ctx.get("exception"))

    def submit(self, coro: Coroutine[Any, Any, Any]) -> concurrent.futures.Future:
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        fut.add_done_callback(self._log_failure)
        return fut

    @staticmethod
    def _log_failure(fut: concurrent.futures.Future) -> None:
        if fut.cancelled():
            return
        exc = fut.exception()
        if exc and not isinstance(exc, asyncio.CancelledError):
            log.error("Background task failed", exc_info=exc)

    def call_soon(self, fn, *args) -> None:
        self.loop.call_soon_threadsafe(fn, *args)

    def stop(self, timeout: float = 3.0) -> None:
        if not self.loop.is_running():
            return

        async def _shutdown() -> None:
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        try:
            asyncio.run_coroutine_threadsafe(_shutdown(), self.loop).result(timeout)
        except Exception:  # noqa: BLE001
            pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._thread.join(timeout)
