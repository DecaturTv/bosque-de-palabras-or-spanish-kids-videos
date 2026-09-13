"""Procedurally synthesized placeholder sound effects and music beds.

No recorded audio assets exist yet (assets/audio/sfx, .../music_beds
are empty). These sine-wave stand-ins let the pipeline produce a
real, fully-scored video today; swap in real recordings later by
pointing pipeline.py at files in assets/audio/ instead of these
functions — nothing else in the pipeline needs to change.
"""
from __future__ import annotations

import numpy as np
from moviepy import AudioArrayClip

SAMPLE_RATE = 44100

# Beginner = single tone, advanced = full triad — mirrors the
# "music bed complexity scales with tier" rule in config/style.yaml.
TIER_CHORD_FREQS = {
    "beginner": [220.00],
    "intermediate": [220.00, 277.18],
    "advanced": [220.00, 277.18, 329.63],
}


def _sine(freq: float, duration: float, amplitude: float = 0.2) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    wave = amplitude * np.sin(2 * np.pi * freq * t)
    fade_n = int(min(0.02, duration / 4) * SAMPLE_RATE)
    if fade_n > 0:
        wave[:fade_n] *= np.linspace(0, 1, fade_n)
        wave[-fade_n:] *= np.linspace(1, 0, fade_n)
    return wave


def _to_clip(mono: np.ndarray) -> AudioArrayClip:
    stereo = np.column_stack([mono, mono])
    return AudioArrayClip(stereo, fps=SAMPLE_RATE)


def chime(duration: float = 0.35) -> AudioArrayClip:
    """New-vocab pop-in cue."""
    wave = _sine(880, duration, 0.2) + _sine(1320, duration, 0.1)
    return _to_clip(wave)


def starburst(duration: float = 0.5) -> AudioArrayClip:
    """Correct-answer reward cue."""
    wave = (
        _sine(660, duration, 0.15)
        + _sine(990, duration, 0.15)
        + _sine(1320, duration, 0.1)
    )
    return _to_clip(wave)


def silence(duration: float) -> AudioArrayClip:
    n = max(1, int(SAMPLE_RATE * duration))
    return AudioArrayClip(np.zeros((n, 2)), fps=SAMPLE_RATE)


def music_bed(tier: str, duration: float, amplitude: float = 0.03) -> AudioArrayClip:
    freqs = TIER_CHORD_FREQS.get(tier, [220.00])
    wave = sum(_sine(f, duration, amplitude) for f in freqs)
    return _to_clip(wave)
