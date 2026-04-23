from __future__ import annotations

import re


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_token(value: str) -> str:
    cleaned = clean_text(value).lower()
    return cleaned
