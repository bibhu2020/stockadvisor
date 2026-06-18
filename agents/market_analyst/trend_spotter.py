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
    # Options / derivatives slang
    "ATM", "ITM", "OTM", "DTE", "OPEX", "IV", "LEAPS",
    # Macro / Fed terms
    "FOMC", "PCE", "PMI", "ISM", "CPI", "RRP", "JOLTS",
    # Media / network names
    "CNBC", "MSNB",
    # Crypto (not stocks)
    "BTC", "ETH", "NFT", "DOGE", "SHIB",
    # Corporate / legal jargon
    "SPAC", "YTD", "ROI", "NAV", "AUM", "NDA", "MOU", "LOI",
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
    """Basic sanity check: 2-5 uppercase letters only."""
    return sym.isalpha() and 2 <= len(sym) <= 5 and sym.isupper()


def run(log) -> list[str]:
    """Return tickers buzzing across multiple sources, capped at MAX_CANDIDATES."""
    cached = day_cache.get(CACHE_KEY)
    if cached:
        log(f"[cache] HIT  trend_spotter_candidates ({len(cached)}) — reusing today's tickers")
        return cached

    log("TrendSpotter: fetching Yahoo Finance trending...")
    yahoo   = set(get_yahoo_trending())
    log(f"  Yahoo trending ({len(yahoo)}): {sorted(yahoo)}")

    log("TrendSpotter: fetching Yahoo Finance gainers/most-active...")
    gainers = set(get_yahoo_gainers())
    log(f"  Yahoo gainers ({len(gainers)}): {sorted(gainers)}")

    log("TrendSpotter: fetching Reddit hot tickers...")
    reddit  = set(get_reddit_hot_tickers())
    log(f"  Reddit mentions ({len(reddit)}): {sorted(reddit)}")

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

    # Tier 1: seen in 2+ sources — highest signal quality
    multi = [s for s in ranked if len(sources[s]) >= 2]

    # Tier 2: curated single-source from Yahoo (Trending or Gainers) — reliable
    yahoo_single = [
        s for s in ranked
        if len(sources[s]) == 1 and not sources[s].issubset({"Reddit"})
    ]

    # Tier 3: Reddit-only — noisy, last resort
    reddit_only = [
        s for s in ranked
        if len(sources[s]) == 1 and sources[s] == {"Reddit"}
    ]

    log(
        f"TrendSpotter: scored {len(ranked)} tickers — "
        f"{len(multi)} multi-source, {len(yahoo_single)} Yahoo-only, "
        f"{len(reddit_only)} Reddit-only"
    )

    # Build candidates strictly by tier: multi → Yahoo-curated → Reddit (last resort)
    candidates: list[str] = []
    for pool in [multi, yahoo_single, reddit_only]:
        need = MAX_CANDIDATES - len(candidates)
        if need <= 0:
            break
        candidates.extend(pool[:need])

    def _src_label(sym: str) -> str:
        return "+".join(sorted(sources.get(sym, {"?"})))

    detail = [f"{s}({_src_label(s)})" for s in candidates]
    log(f"TrendSpotter: selected {len(candidates)}: {detail}")

    if len(candidates) < MIN_CANDIDATES:
        log(
            f"TrendSpotter: WARNING — only {len(candidates)} candidates found "
            f"(min {MIN_CANDIDATES}). Sources may be returning limited data today."
        )

    day_cache.put(CACHE_KEY, candidates)
    return candidates
