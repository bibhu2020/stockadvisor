"""FundamentalAnalystAgent — scores each candidate on fundamentals."""
import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.data_fetcher import get_fundamentals, get_web_enrichment
from agents.core import day_cache

# Trigger web search only when yfinance has neither analyst targets nor earnings data
# (yfinance now provides rich data; web search is a last resort for obscure/new stocks)
def _needs_web_enrichment(info: dict) -> bool:
    has_target   = info.get("analyst_target") is not None
    has_earnings = len(info.get("recent_earnings_history", [])) > 0
    return not has_target and not has_earnings


def _score(info: dict) -> float:
    """0-100 fundamental score with analyst consensus and earnings beat bonuses."""
    score = 50.0

    pe = info.get("pe_ratio")
    if pe and 0 < pe < 20:
        score += 10
    elif pe and pe > 60:
        score -= 10

    eps_growth = info.get("eps_growth")
    if eps_growth is not None:
        if eps_growth > 0.2:
            score += 15
        elif eps_growth > 0:
            score += 7
        else:
            score -= 10

    rev_growth = info.get("revenue_growth")
    if rev_growth is not None:
        if rev_growth > 0.15:
            score += 10
        elif rev_growth > 0:
            score += 5
        else:
            score -= 5

    roe = info.get("roe")
    if roe and roe > 0.15:
        score += 10

    de = info.get("debt_to_equity")
    if de is not None:
        if de < 0.5:
            score += 5
        elif de > 2.0:
            score -= 10

    # Bonus: positive EPS surprise
    surprise = info.get("eps_surprise_pct")
    if surprise is not None:
        if surprise > 5:
            score += 12
        elif surprise > 0:
            score += 5
        else:
            score -= 8

    # Bonus: analyst consensus bullish
    rating = (info.get("analyst_rating") or "").lower()
    if "buy" in rating:
        score += 8
    elif "hold" in rating:
        score += 0
    elif "sell" in rating:
        score -= 8

    # Bonus: recent analyst actions with buy ratings
    recent_actions = info.get("recent_analyst_actions", [])
    buys_in_recent = sum(
        1 for a in recent_actions[:5]
        if "buy" in (a.get("to_grade") or "").lower()
    )
    if buys_in_recent >= 2:
        score += 8
    elif buys_in_recent == 1:
        score += 4

    a_upg = info.get("analyst_upgrades")
    if a_upg and a_upg >= 5:
        score += 5

    # Market cap: prefer large/mid cap for liquidity and analyst coverage
    market_cap = info.get("market_cap")
    if market_cap:
        if market_cap >= 10_000_000_000:   # Large/mega cap ≥ $10B
            score += 5
        elif market_cap >= 2_000_000_000:  # Mid cap $2B–$10B
            score += 2
        elif market_cap < 300_000_000:     # Micro cap < $300M — too illiquid
            score -= 10
        else:                               # Small cap $300M–$2B
            score -= 3

    # YTD momentum
    ytd = info.get("ytd_return_pct")
    if ytd is not None:
        if ytd > 30:
            score += 8
        elif ytd > 15:
            score += 5
        elif ytd > 0:
            score += 2
        elif ytd < -30:
            score -= 10
        elif ytd < -15:
            score -= 5

    # Distance from 52-week high: near high = strong momentum
    pct_from_high = info.get("pct_from_52w_high")
    if pct_from_high is not None:
        if pct_from_high >= -5:    # Within 5% of 52w high — breakout zone
            score += 5
        elif pct_from_high >= -15: # Within 15% — strong uptrend
            score += 3
        elif pct_from_high < -40:  # >40% below high — significant downtrend
            score -= 5

    return max(0.0, min(100.0, score))


def run(candidates: list[str], log) -> list[dict]:
    """Return fundamentals + score for each candidate."""
    results = []
    for sym in candidates:
        key = f"fundamentals_{sym}"
        cached = day_cache.get(key)
        if cached:
            log(f"[cache] HIT  {key}")
            results.append(cached)
            continue

        log(f"FundamentalAnalyst: fetching {sym}...")
        info = get_fundamentals(sym)

        # If yfinance has no analyst target AND no earnings history, enrich via web search
        if _needs_web_enrichment(info):
            web_key = f"web_enrichment_{sym}"
            web = day_cache.get(web_key)
            if web:
                log(f"[cache] HIT  {web_key}")
            else:
                company = info.get("company", sym)
                log(f"FundamentalAnalyst: {sym} — no yfinance analyst/earnings data, running web search...")
                web = get_web_enrichment(sym, company)
                day_cache.put(web_key, web)
            info["web_snippets"] = web.get("web_snippets", [])
        else:
            info["web_snippets"] = []

        # Skip tickers with no price — delisted or data unavailable from all sources
        if not info.get("current_price"):
            has_error = "error" in info
            reason = f"yfinance error: {info['error']}" if has_error else "no price from yfinance / Stooq / Google Finance"
            log(f"FundamentalAnalyst: {sym} — skipping ({reason})")
            time.sleep(0.5)
            continue

        # Compute 52-week proximity metrics
        price    = info.get("current_price")
        high_52w = info.get("fifty_two_week_high")
        low_52w  = info.get("fifty_two_week_low")
        if price and high_52w and high_52w > 0:
            info["pct_from_52w_high"] = round((price - high_52w) / high_52w * 100, 1)
        if price and low_52w and low_52w > 0:
            info["pct_from_52w_low"] = round((price - low_52w) / low_52w * 100, 1)

        info["fundamental_score"] = round(_score(info), 1)

        mc = info.get("market_cap")
        mc_str = f"${mc/1e9:.1f}B" if mc and mc >= 1e9 else (f"${mc/1e6:.0f}M" if mc else "N/A")
        ytd_str = f"{info['ytd_return_pct']:+.1f}% YTD" if info.get("ytd_return_pct") is not None else "YTD N/A"
        h_str   = f"{info['pct_from_52w_high']:+.1f}% from 52w high" if info.get("pct_from_52w_high") is not None else ""
        log(f"FundamentalAnalyst: {sym} — ${info['current_price']} | {mc_str} | {ytd_str} | {h_str} | score {info['fundamental_score']}")
        day_cache.put(key, info)
        results.append(info)
        time.sleep(0.5)

    results.sort(key=lambda x: -x["fundamental_score"])
    log(f"FundamentalAnalyst: top {len(results)} valid candidates by score: {[r['symbol'] for r in results[:10]]}")
    return results
