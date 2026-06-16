"""TrendSpotterAgent — discovers the most talked-about stocks."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.data_fetcher import (
    get_yahoo_trending, scrape_finviz_trending, get_reddit_hot_tickers
)
from agents.core import day_cache

MAX_CANDIDATES = 8
MIN_CANDIDATES = 5

CACHE_KEY = "trend_spotter_candidates"


def run(log) -> list[str]:
    """Return tickers buzzing across multiple sources, capped at MAX_CANDIDATES."""
    cached = day_cache.get(CACHE_KEY)
    if cached:
        log(f"[cache] HIT  trend_spotter_candidates ({len(cached)}) — reusing today's tickers")
        return cached

    log("TrendSpotter: fetching Yahoo Finance trending...")
    yahoo  = set(get_yahoo_trending())
    log(f"  Yahoo: {sorted(yahoo)[:10]}")

    log("TrendSpotter: fetching Finviz top gainers...")
    finviz = set(scrape_finviz_trending())
    log(f"  Finviz: {sorted(finviz)[:10]}")

    log("TrendSpotter: fetching Reddit hot tickers...")
    reddit = set(get_reddit_hot_tickers())
    log(f"  Reddit: {sorted(reddit)[:10]}")

    noise = {"ETF", "IPO", "CEO", "GDP", "CPI", "FED", "SPY", "QQQ", "IWM"}

    # Score by source weight; track how many sources each ticker appears in
    score:   dict[str, int] = {}
    sources: dict[str, int] = {}

    for sym, pts in [(s, 2) for s in yahoo] + [(s, 3) for s in finviz] + [(s, 1) for s in reddit]:
        if sym in noise:
            continue
        score[sym]   = score.get(sym, 0) + pts
        sources[sym] = sources.get(sym, 0) + 1

    ranked = sorted(score, key=lambda x: (-sources[x], -score[x]))

    # Prefer tickers seen in 2+ sources; fall back to top single-source if needed
    multi  = [s for s in ranked if sources[s] >= 2]
    single = [s for s in ranked if sources[s] == 1]

    if len(multi) >= MIN_CANDIDATES:
        candidates = multi[:MAX_CANDIDATES]
    else:
        # pad with highest-scored single-source tickers until we reach MIN_CANDIDATES
        candidates = multi + single[: max(0, MIN_CANDIDATES - len(multi))]
        candidates = candidates[:MAX_CANDIDATES]

    log(
        f"TrendSpotter: {len(multi)} multi-source, {len(single)} single-source. "
        f"Selected {len(candidates)}: {candidates}"
    )
    day_cache.put(CACHE_KEY, candidates)
    return candidates
