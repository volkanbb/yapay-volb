"""Download local voice models.

    python scripts/download_models.py                  # Turkish Piper voice (default)
    python scripts/download_models.py --piper en_US-ryan-medium
    python scripts/download_models.py --whisper small  # pre-fetch the Faster-Whisper model

Piper voices come from the official rhasspy/piper-voices repository on Hugging Face.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def piper_url(voice: str, suffix: str) -> str:
    lang_region, name, quality = voice.split("-", 2)
    lang = lang_region.split("_")[0]
    return f"{PIPER_BASE}/{lang}/{lang_region}/{name}/{quality}/{voice}{suffix}"


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"✓ zaten var: {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"↓ {url}")
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:  # noqa: S310 - fixed https host
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        while chunk := r.read(1 << 16):
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / 1e6:5.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    print()
    tmp.rename(dest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--piper", default="tr_TR-dfki-medium", help="Piper voice name ('' to skip)")
    ap.add_argument("--whisper", default="", help="Faster-Whisper model size to pre-download")
    args = ap.parse_args()
    if args.piper:
        out = ROOT / "models" / "piper"
        for suffix in (".onnx", ".onnx.json"):
            download(piper_url(args.piper, suffix), out / f"{args.piper}{suffix}")
    if args.whisper:
        from faster_whisper import download_model
        print("↓ whisper", args.whisper, "→", download_model(args.whisper))
    return 0


if __name__ == "__main__":
    sys.exit(main())
