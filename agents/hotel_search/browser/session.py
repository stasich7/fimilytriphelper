from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BrowserSessionConfig:
    headless: bool = True
    timeout_seconds: int = 30
    max_retries: int = 2


def default_session_config() -> BrowserSessionConfig:
    return BrowserSessionConfig()
