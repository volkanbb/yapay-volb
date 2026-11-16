"""Local Ollama provider (free, offline). Uses only the standard library."""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import AsyncIterator

from .base import AIProvider, ChatChunk, ProviderStatus


class OllamaProvider(AIProvider):
    name = "ollama"
    display_name = "Ollama (yerel)"

    def __init__(self, model: str = "llama3.1", host: str = "http://127.0.0.1:11434") -> None:
        self.model = model
        self.host = host.rstrip("/")
        self._history: list[dict] = []
        self._cancel = False

    async def status(self) -> ProviderStatus:
        def _probe() -> list[str]:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=2) as r:
                return [m["name"] for m in json.load(r).get("models", [])]
        try:
            models = await asyncio.to_thread(_probe)
        except (urllib.error.URLError, OSError, ValueError):
            return ProviderStatus(self.name, False, False, "Ollama çalışmıyor.",
                                  install_hint="sudo pacman -S ollama && systemctl --user start ollama")
        ok = any(m.split(":")[0] == self.model.split(":")[0] for m in models)
        return ProviderStatus(self.name, True, ok,
                              "Hazır" if ok else f"Model yok: ollama pull {self.model}", extra={"models": models})

    def reset_conversation(self) -> None:
        self._history.clear()

    async def stream(self, prompt: str, system: str | None = None) -> AsyncIterator[ChatChunk]:
        messages = ([{"role": "system", "content": system}] if system else []) + self._history + [
            {"role": "user", "content": prompt}]
        body = json.dumps({"model": self.model, "messages": messages, "stream": True}).encode()
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        self._cancel = False

        def _worker() -> None:
            try:
                req = urllib.request.Request(f"{self.host}/api/chat", data=body,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=300) as r:
                    for line in r:
                        if self._cancel:
                            break
                        data = json.loads(line)
                        text = data.get("message", {}).get("content", "")
                        if text:
                            loop.call_soon_threadsafe(queue.put_nowait, ChatChunk("text", text))
                        if data.get("done"):
                            break
                loop.call_soon_threadsafe(queue.put_nowait, ChatChunk("done"))
            except Exception as exc:  # noqa: BLE001
                loop.call_soon_threadsafe(queue.put_nowait, ChatChunk("error", f"Ollama hatası: {exc}"))

        loop.run_in_executor(None, _worker)
        full: list[str] = []
        while True:
            chunk: ChatChunk = await queue.get()
            if chunk.kind == "text":
                full.append(chunk.text)
            yield chunk
            if chunk.kind != "text":
                break
        self._history += [{"role": "user", "content": prompt}, {"role": "assistant", "content": "".join(full)}]
        self._history = self._history[-20:]

    async def cancel(self) -> None:
        self._cancel = True
