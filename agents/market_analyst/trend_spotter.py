"""TrendSpotterAgent — discovers the most talked-about stocks."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.data_fetcher import (
    get_yahoo_trending, get_yahoo_gainers, get_reddit_hot_tickers
)
from agents.core import day_cache

MAX_CANDIDATES = 10
MIN_CANDIDATES = 5

CACHE_KEY = "trend_spotter_candidates"

# Common non-ticker words that appear in financial Reddit/news discussions
NOISE = {
    # Generic ETF/index symbols
    "SPY", "QQQ", "IWM", "DIA", "VIX", "VTI", "VOO", "GLD", "SLV", "TLT", "HYG",
    # Financial jargon mistaken for tickers
    "ETF", "IPO", "CEO", "CFO", "CTO", "GDP", "CPI", "FED", "SEC", "NYSE", "AMEX",
    "NASDAQ", "OTC", "ATH", "ATL", "EPS", "PE", "PEG", "ROE", "FCF", "EBIT",
    # Technical indicator names
    "MACD", "RSI", "SMA", "EMA", "VWAP", "OBV", "ATR", "ADX", "BB",
    # Reddit/WSB slang
    "DD", "YOLO", "FOMO", "HODL", "BTFD", "MOASS", "GME",
    # Common English words / industry terms that slip through
    "NOT", "FOR", "AND", "THE", "ARE", "ALL", "NEW", "NOW", "INC", "LLC",
    "AI", "ML", "EV", "OR", "IT", "IS", "IN", "AT", "TO",
    "HVAC", "MSE", "PAC",
}


def _valid_ticker(sym: str) -> bool:
    """Basic sanity check: 1-5 uppercase letters only."""
    return sym.isalpha() and 1 <= len(sym) <= 5 and sym.isupper()


def run(log) -> list[str]:
    """Return tickers buzzing across multiple sources, capped at MAX_CANDIDATES."""
    cached = day_cache.get(CACHE_KEY)
    if cached:
        log(f"[cache] HIT  trend_spotter_candidates ({len(cached)}) — reusing today's tickers")
        return cached

    log("TrendSpotter: fetching Yahoo Finance trending...")
    yahoo   = set(get_yahoo_trending())
    log(f"  Yahoo ({len(yahoo)}): {sorted(yahoo)}")

    log("TrendSpotter: fetching Yahoo Finance gainers/most-active...")
    gainers = set(get_yahoo_gainers())
    log(f"  Gainers ({len(gainers)}): {sorted(gainers)}")

    log("TrendSpotter: fetching Reddit hot tickers...")
    reddit  = set(get_reddit_hot_tickers())
    log(f"  Reddit ({len(reddit)}): {sorted(reddit)}")

    # Score by source weight; track which sources each ticker appears in
    score:   dict[str, int] = {}
    sources: dict[str, set] = {}

    for sym, src, pts in (
        [(s, "Yahoo",   2) for s in yahoo]   +
        [(s, "Gainers", 3) for s in gainers] +
        [(s, "Reddit",  1) for s in reddit]
    ):
        if sym in NOISE or not _valid_ticker(sym):
            continue
        score[sym] = score.get(sym, 0) + pts
        sources.setdefault(sym, set()).add(src)

    ranked = sorted(score, key=lambda x: (-len(sources[x]), -score[x]))

    # Prefer tickers seen in 2+ sources; fill remainder with best single-source
    multi  = [s for s in ranked if len(sources[s]) >= 2]
    single = [s for s in ranked if len(sources[s]) == 1]

    if len(multi) >= MIN_CANDIDATES:
        candidates = multi[:MAX_CANDIDATES]
    else:
        candidates = multi + single[: max(0, MIN_CANDIDATES - len(multi))]
        candidates = candidates[:MAX_CANDIDATES]

    def _src_label(sym: str) -> str:
        return "+".join(sorted(sources.get(sym, {"?"})))

    detail = [f"{s}({_src_label(s)})" for s in candidates]
    log(
        f"TrendSpotter: {len(multi)} multi-source, {len(single)} single-source. "
        f"Selected {len(candidates)}: {detail}"
    )
    day_cache.put(CACHE_KEY, candidates)
    return candidates
