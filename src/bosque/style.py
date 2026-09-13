"""Loads config/style.yaml once. Both schema validation (tier rules)
and visuals rendering (palette/fonts) read through this so the YAML
file stays the single source of truth.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

STYLE_PATH = Path(__file__).resolve().parents[2] / "config" / "style.yaml"


@lru_cache(maxsize=1)
def load_style() -> dict:
    with open(STYLE_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)
