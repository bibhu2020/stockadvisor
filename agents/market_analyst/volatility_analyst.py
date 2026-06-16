"""VolatilityAnalystAgent — VIX, beta, sector volatility."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.data_fetcher import get_vix, get_price_history
from agents.core import day_cache
import numpy as np
import pandas as pd


def _calc_beta(symbol: str, period: str = "3mo") -> float | None:
    """Beta relative to SPY."""
    try:
        stock_bars = get_price_history(symbol, period)
        spy_bars   = get_price_history("SPY", period)
        if len(stock_bars) < 20 or len(spy_bars) < 20:
            return None
        stock_ret = pd.Series([b["close"] for b in stock_bars]).pct_change().dropna()
        spy_ret   = pd.Series([b["close"] for b in spy_bars]).pct_change().dropna()
        min_len = min(len(stock_ret), len(spy_ret))
        if min_len < 10:
            return None
        cov = np.cov(stock_ret[-min_len:], spy_ret[-min_len:])
        beta = cov[0][1] / cov[1][1]
        return round(float(beta), 2)
    except Exception:
        return None


def run(candidates: list[str], log) -> dict:
    """Return market risk assessment and per-symbol beta."""
    cached = day_cache.get("volatility")
    if cached:
        log(f"[cache] HIT  volatility — VIX={cached.get('vix')}, risk={cached.get('market_risk')}")
        # add any new candidates that weren't cached yet
        missing = [s for s in candidates if s not in cached.get("betas", {})]
        if not missing:
            return cached
        log(f"VolatilityAnalyst: computing betas for new candidates {missing}")
        for sym in missing:
            cached["betas"][sym] = _calc_beta(sym)
            log(f"  {sym} beta: {cached['betas'][sym]}")
        day_cache.put("volatility", cached)
        return cached

    vix = get_vix()
    log(f"VolatilityAnalyst: VIX = {vix}")

    if vix is None:
        market_risk = "unknown"
    elif vix < 15:
        market_risk = "low"
    elif vix < 25:
        market_risk = "medium"
    else:
        market_risk = "high"

    betas = {}
    for sym in candidates[:15]:  # limit to 15 to save time
        b = _calc_beta(sym)
        betas[sym] = b
        log(f"  {sym} beta: {b}")

    result = {
        "vix": vix,
        "market_risk": market_risk,
        "betas": betas,
    }
    day_cache.put("volatility", result)
    return result
