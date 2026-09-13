"""Text-to-speech with on-disk caching.

Same (text, rate) pair is re-used across renders and across lines
within a video (e.g. the mascot catchphrase, or a refrain repeated
across verses) instead of re-hitting the TTS API every time.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from gtts import gTTS

CACHE_DIR = Path(__file__).resolve().parents[2] / "output" / ".tts_cache"


def synth(text: str, *, rate: str = "natural", lang: str = "es") -> Path:
    """Return a path to an mp3 of `text` spoken in `lang`.

    rate: "slow" (beginner tier) or "natural" (intermediate/advanced).
    """
    slow = rate == "slow"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{lang}|{slow}|{text}".encode("utf-8")).hexdigest()
    out_path = CACHE_DIR / f"{key}.mp3"
    if not out_path.exists():
        gTTS(text=text, lang=lang, slow=slow).save(str(out_path))
    return out_path
