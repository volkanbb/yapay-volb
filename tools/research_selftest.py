"""Research self-test: python tools/research_selftest.py "konu" """
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai.claude_cli import ClaudeCodeCLIProvider  # noqa: E402
from app.browser.controller import BrowserController  # noqa: E402
from app.browser.research import ResearchService  # noqa: E402


async def main(topic: str) -> None:
    browser = BrowserController(headless="--headless" in sys.argv)
    provider = ClaudeCodeCLIProvider()
    svc = ResearchService(browser, lambda: provider)
    try:
        rep = await svc.research(topic, 3, lambda m, p: print(f"  [{p:4.0%}] {m}"))
    finally:
        await browser.stop()
    print("AI summary:", rep.ai_generated)
    print(rep.to_markdown()[:1500])

asyncio.run(main(next((a for a in sys.argv[1:] if not a.startswith("--")), None) or "PySide6 Qt Quick Shapes CurveRenderer"))
