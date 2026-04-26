"""Runtime logging helpers for production diagnostics."""

from __future__ import annotations

import os
import resource
import time


def now_ms() -> int:
    return int(time.perf_counter() * 1000)


def elapsed_ms(start_ms: int) -> int:
    return now_ms() - start_ms


def _read_status_value(name: str) -> str:
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as status_file:
            for line in status_file:
                if line.startswith(f"{name}:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        return "unknown"
    return "unknown"


def memory_snapshot() -> str:
    max_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return (
        f"pid={os.getpid()} "
        f"rss={_read_status_value('VmRSS')} "
        f"hwm={_read_status_value('VmHWM')} "
        f"maxrss_kb={max_rss_kb}"
    )


def text_preview(text: str, limit: int = 240) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."
