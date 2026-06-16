"""
Day-level JSON cache for market data.

All expensive fetches (trending tickers, fundamentals, technicals, sentiment,
volatility) are written to  data/cache/YYYY-MM-DD.json  on first use and
reloaded on every subsequent run within the same calendar day.  This makes
back-to-back agent runs produce identical candidate lists and scores, so the
Synthesizer (now at temperature=0) always generates the same picks.
"""
import json
import os
from datetime import date
from pathlib import Path

_CACHE_DIR = Path(__file__).parents[2] / "data" / "cache"


def _path(day: str | None = None) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{day or date.today().isoformat()}.json"


def _load(day: str | None = None) -> dict:
    p = _path(day)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def _save(data: dict, day: str | None = None) -> None:
    _path(day).write_text(json.dumps(data, default=str))


# ── Public helpers ─────────────────────────────────────────────────────────────

def get(key: str, day: str | None = None):
    """Return cached value for key, or None if not cached today."""
    return _load(day).get(key)


def put(key: str, value, day: str | None = None) -> None:
    """Write value under key into today's cache file."""
    data = _load(day)
    data[key] = value
    _save(data, day)


def cached(key: str, fn, log=None, day: str | None = None):
    """
    Return cached[key] if present; otherwise call fn(), cache and return result.
    Logs a cache-hit/miss message when log is provided.
    """
    hit = get(key, day)
    if hit is not None:
        if log:
            log(f"[cache] HIT  {key} ({len(hit) if hasattr(hit, '__len__') else ''})")
        return hit
    if log:
        log(f"[cache] MISS {key} — fetching fresh data")
    result = fn()
    put(key, result, day)
    return result
