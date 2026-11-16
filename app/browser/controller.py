"""Playwright Chromium controller: navigation, tabs, extraction, screenshots, search."""
from __future__ import annotations

import asyncio
import datetime as dt
import html
import json
import logging
import os
import re
import urllib.request
from dataclasses import dataclass
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from ..core.config import DATA_DIR

log = logging.getLogger(__name__)

INSTALL_HINT = "Playwright Chromium eksik: .venv/bin/playwright install chromium"

EXTRACT_JS = r"""
() => {
  const pick = document.querySelector('article') || document.querySelector('main') || document.body;
  if (!pick) return '';
  const clone = pick.cloneNode(true);
  clone.querySelectorAll('script,style,noscript,nav,footer,header,aside,form,iframe,svg,button').forEach(e => e.remove());
  return clone.innerText || '';
}
"""


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""


def _clean_ddg_url(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    u = urlparse(href)
    if "duckduckgo.com" in u.netloc and u.path.startswith("/l/"):
        q = parse_qs(u.query).get("uddg")
        if q:
            return unquote(q[0])
    return href


def normalize_text(text: str, limit: int = 12_000) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()[:limit]


class BrowserController:
    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self._pw = None
        self._browser = None
        self._context = None
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._context is not None

    async def start(self) -> None:
        async with self._lock:
            if self._context:
                return
            from playwright.async_api import async_playwright

            self._pw = await async_playwright().start()
            try:
                self._browser = await self._pw.chromium.launch(headless=self.headless)
            except Exception as exc:
                await self._pw.stop()
                self._pw = None
                raise RuntimeError(f"{INSTALL_HINT}\n{exc}") from exc
            self._context = await self._browser.new_context(
                locale="tr-TR", viewport={"width": 1280, "height": 860},
                user_agent=None, java_script_enabled=True, accept_downloads=False)

    async def stop(self) -> None:
        async with self._lock:
            for obj in (self._context, self._browser):
                try:
                    if obj:
                        await obj.close()
                except Exception:  # noqa: BLE001
                    pass
            if self._pw:
                await self._pw.stop()
            self._pw = self._browser = self._context = None

    async def new_tab(self, url: str | None = None):
        await self.start()
        page = await self._context.new_page()
        if url:
            await self.goto(page, url)
        return page

    async def goto(self, page, url: str, timeout: float = 25_000) -> None:
        if not urlparse(url).scheme:
            url = "https://" + url
        if urlparse(url).scheme not in ("http", "https"):
            raise ValueError("Sadece http/https.")
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

    def tabs(self) -> list[dict]:
        if not self._context:
            return []
        return [{"index": i, "url": p.url} for i, p in enumerate(self._context.pages)]

    async def tab_titles(self) -> list[dict]:
        out = []
        if self._context:
            for i, p in enumerate(self._context.pages):
                try:
                    title = await p.title()
                except Exception:  # noqa: BLE001
                    title = ""
                out.append({"index": i, "url": p.url, "title": title})
        return out

    async def close_tab(self, index: int) -> None:
        if self._context and 0 <= index < len(self._context.pages):
            await self._context.pages[index].close()

    async def extract_text(self, page) -> str:
        try:
            return normalize_text(await page.evaluate(EXTRACT_JS))
        except Exception as exc:  # noqa: BLE001
            log.warning("extract failed: %s", exc)
            return ""

    async def screenshot(self, page, full_page: bool = False) -> str:
        out = DATA_DIR / "screenshots"
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"web_{dt.datetime.now():%Y%m%d_%H%M%S}.png"
        await page.screenshot(path=str(path), full_page=full_page)
        return str(path)

    async def search(self, query: str, limit: int = 8, engine: str = "duckduckgo") -> list[SearchResult]:
        page = await self.new_tab()
        try:
            if engine == "bing":
                await self.goto(page, f"https://www.bing.com/search?q={quote_plus(query)}&setlang=tr")
                raw = await page.evaluate("""() => Array.from(document.querySelectorAll('li.b_algo')).map(li => ({
                    title: li.querySelector('h2')?.innerText || '', url: li.querySelector('h2 a')?.href || '',
                    snippet: li.querySelector('p')?.innerText || ''}))""")
            else:
                await self.goto(page, f"https://html.duckduckgo.com/html/?q={quote_plus(query)}&kl=tr-tr")
                raw = await page.evaluate("""() => Array.from(document.querySelectorAll('.result')).map(r => ({
                    title: r.querySelector('a.result__a')?.innerText || '',
                    url: r.querySelector('a.result__a')?.getAttribute('href') || '',
                    snippet: r.querySelector('.result__snippet')?.innerText || ''}))""")
        finally:
            await page.close()
        results: list[SearchResult] = []
        seen: set[str] = set()
        for r in raw:
            url = _clean_ddg_url(r.get("url", ""))
            host = urlparse(url).netloc
            if not url.startswith("http") or "duckduckgo.com" in host or "bing.com" in host or url in seen:
                continue
            seen.add(url)
            results.append(SearchResult(r.get("title", "").strip(), url, r.get("snippet", "").strip()))
            if len(results) >= limit:
                break
        if not results and engine != "bing":
            return await self.search(query, limit, "bing")
        if not results:
            log.info("web search returned nothing (headless=%s) — using API fallbacks", self.headless)
            results = await api_search(query, limit)
        return results


USER_AGENT = "YapayVolb/0.1 (personal desktop research assistant)"


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 - fixed https hosts / user-configured SearXNG
        return json.load(r)


async def api_search(query: str, limit: int = 8) -> list[SearchResult]:
    """Official/self-hosted search APIs: SearXNG (VOLB_SEARXNG_URL) and Wikipedia (tr + en)."""
    results: list[SearchResult] = []
    searx = os.environ.get("VOLB_SEARXNG_URL", "").rstrip("/")
    if searx:
        try:
            data = await asyncio.to_thread(_get_json, f"{searx}/search?q={quote_plus(query)}&format=json")
            results += [SearchResult(r.get("title", ""), r["url"], r.get("content", ""))
                        for r in data.get("results", []) if r.get("url", "").startswith("http")]
        except Exception as exc:  # noqa: BLE001
            log.warning("SearXNG failed: %s", exc)
    for lang in ("tr", "en"):
        if len(results) >= limit:
            break
        try:
            data = await asyncio.to_thread(
                _get_json, f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&format=json"
                           f"&srlimit={limit}&srsearch={quote_plus(query)}")
            for r in data.get("query", {}).get("search", []):
                title = r["title"]
                snippet = html.unescape(re.sub(r"<[^>]+>", "", r.get("snippet", "")))
                results.append(SearchResult(f"{title} — Wikipedia ({lang})",
                                            f"https://{lang}.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}",
                                            snippet))
        except Exception as exc:  # noqa: BLE001
            log.warning("Wikipedia search failed: %s", exc)
    return results[:limit]
