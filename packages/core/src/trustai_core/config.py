from __future__ import annotations

import os
from typing import Literal


def get_llm_mode() -> Literal["fixture", "live"]:
    raw_mode = os.getenv("TRUSTAI_LLM_MODE", "fixture").lower()
    if raw_mode == "mock":
        raw_mode = "fixture"
    if raw_mode not in {"fixture", "live"}:
        raise ValueError("TRUSTAI_LLM_MODE must be 'fixture' or 'live'")
    return raw_mode
