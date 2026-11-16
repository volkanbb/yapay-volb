"""Optional ChromaDB semantic memory. Degrades to a no-op when chromadb is not installed."""
from __future__ import annotations

import logging

from ..core.config import DATA_DIR

log = logging.getLogger(__name__)


class SemanticMemory:
    def __init__(self, enabled: bool) -> None:
        self._col = None
        if not enabled:
            return
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))
            self._col = client.get_or_create_collection("volb_memories")
        except Exception as exc:  # noqa: BLE001
            log.warning("Semantic memory unavailable: %s", exc)

    @property
    def available(self) -> bool:
        return self._col is not None

    def upsert(self, mem_id: int, text: str) -> None:
        if self._col is not None:
            self._col.upsert(ids=[str(mem_id)], documents=[text])

    def delete(self, mem_id: int) -> None:
        if self._col is not None:
            self._col.delete(ids=[str(mem_id)])

    def search(self, query: str, n: int = 4) -> list[str]:
        if self._col is None or self._col.count() == 0:
            return []
        res = self._col.query(query_texts=[query], n_results=min(n, self._col.count()))
        return res.get("documents", [[]])[0]
