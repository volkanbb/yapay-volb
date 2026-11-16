import logging
from logging.handlers import RotatingFileHandler

from .config import LOG_DIR


def setup_logging(level: int = logging.INFO) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        return
    fh = RotatingFileHandler(LOG_DIR / "volb.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(fh)
    root.addHandler(sh)
    for noisy in ("httpx", "faster_whisper", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
