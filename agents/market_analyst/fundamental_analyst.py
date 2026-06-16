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

        # Skip tickers with no price — delisted, invalid, or yfinance outage
        if not info.get("current_price"):
            has_error = "error" in info
            reason = f"yfinance error: {info['error']}" if has_error else "no price returned by yfinance"
            log(f"FundamentalAnalyst: {sym} — skipping ({reason})")
            time.sleep(0.5)
            continue

        info["fundamental_score"] = round(_score(info), 1)
        day_cache.put(key, info)
        results.append(info)
        time.sleep(0.5)

    results.sort(key=lambda x: -x["fundamental_score"])
    log(f"FundamentalAnalyst: top {len(results)} valid candidates by score: {[r['symbol'] for r in results[:10]]}")
    return results
