"""FundamentalAnalystAgent — scores each candidate on fundamentals."""
import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent
from agents.core.data_fetcher import get_fundamentals, get_web_enrichment
from agents.core import day_cache

SYSTEM_PROMPT = """You are a senior fundamental equity analyst at a top-tier hedge fund.
You receive financial metrics for a stock and provide a concise, data-driven qualitative
assessment that goes beyond what a rule-based scoring formula can capture.

Return ONLY valid JSON (no markdown, no preamble):
{
  "summary": "<2-3 sentences — interpret what the numbers mean together, cite specific values, explain the investment story>",
  "strengths": ["<specific strength with numbers, e.g. '23% YoY EPS growth beating estimate by 8%'>", "<strength 2>"],
  "risks": ["<specific risk, e.g. 'D/E of 2.3 leaves little room if rates stay high'>", "<risk 2 if present>"],
  "verdict": "strong_buy|buy|neutral|sell|avoid",
  "score_adjustment": <integer -20 to +20>
}

score_adjustment rules:
  +20: exceptional hidden value the formula misses (e.g. inflecting margins, re-rating catalyst)
  +10: meaningfully better than the score implies
    0: formula is fair
  -10: concerning factors the formula underweighted (e.g. deteriorating margins despite EPS beat)
  -20: serious red flags (e.g. accounting irregularities, liquidity crisis, sector headwinds)

Return ONLY valid JSON."""


# Trigger web search only when yfinance has neither analyst targets nor earnings data
def _needs_web_enrichment(info: dict) -> bool:
    has_target   = info.get("analyst_target") is not None
    has_earnings = len(info.get("recent_earnings_history", [])) > 0
    return not has_target and not has_earnings


def _score(info: dict) -> float:
    """0-100 rule-based fundamental score."""
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

    surprise = info.get("eps_surprise_pct")
    if surprise is not None:
        if surprise > 5:
            score += 12
        elif surprise > 0:
            score += 5
        else:
            score -= 8

    rating = (info.get("analyst_rating") or "").lower()
    if "buy" in rating:
        score += 8
    elif "sell" in rating:
        score -= 8

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

    market_cap = info.get("market_cap")
    if market_cap:
        if market_cap >= 10_000_000_000:
            score += 5
        elif market_cap >= 2_000_000_000:
            score += 2
        elif market_cap < 300_000_000:
            score -= 10
        else:
            score -= 3

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

    pct_from_high = info.get("pct_from_52w_high")
    if pct_from_high is not None:
        if pct_from_high >= -5:
            score += 5
        elif pct_from_high >= -15:
            score += 3
        elif pct_from_high < -40:
            score -= 5

    return max(0.0, min(100.0, score))


def _llm_analysis(agent: BaseAgent, info: dict, log) -> dict:
    """Call LLM for qualitative fundamental interpretation. Returns enrichment dict."""
    sym = info.get("symbol", "?")
    cur = info.get("current_price")
    tgt = info.get("analyst_target")
    upside = round((tgt - cur) / cur * 100, 1) if tgt and cur else None

    payload = {
        "symbol": sym,
        "company": info.get("company"),
        "sector": info.get("sector"),
        "current_price": cur,
        "market_cap": info.get("market_cap"),
        "pe_ratio": info.get("pe_ratio"),
        "forward_pe": info.get("forward_pe"),
        "price_to_sales": info.get("price_to_sales"),
        "eps_growth_yoy": info.get("eps_growth"),
        "eps_surprise_pct": info.get("eps_surprise_pct"),
        "revenue_growth": info.get("revenue_growth"),
        "gross_margin": info.get("gross_margin"),
        "operating_margin": info.get("operating_margin"),
        "free_cash_flow": info.get("free_cash_flow"),
        "roe": info.get("roe"),
        "debt_to_equity": info.get("debt_to_equity"),
        "analyst_rating": info.get("analyst_rating"),
        "analyst_target": tgt,
        "analyst_upside_pct": upside,
        "analyst_count": info.get("analyst_count"),
        "ytd_return_pct": info.get("ytd_return_pct"),
        "pct_from_52w_high": info.get("pct_from_52w_high"),
        "earnings_days_away": info.get("earnings_days_away"),
        "recent_earnings_history": info.get("recent_earnings_history", [])[:2],
        "recent_analyst_actions": info.get("recent_analyst_actions", [])[:3],
        "web_snippets": info.get("web_snippets", [])[:3],
        "rule_based_score": info.get("fundamental_score"),
    }
    try:
        result = agent.run(
            f"Analyse the fundamental picture for {sym} and return structured JSON.",
            context=payload,
        )
        return {
            "fundamental_summary":   result.get("summary", ""),
            "fundamental_strengths": result.get("strengths", []),
            "fundamental_risks":     result.get("risks", []),
            "fundamental_verdict":   result.get("verdict", "neutral"),
            "fundamental_score_adj": int(result.get("score_adjustment", 0)),
        }
    except Exception as exc:
        log(f"  [LLM] fundamental analysis failed for {sym}: {exc}")
        return {}


def run(candidates: list[str], log) -> list[dict]:
    """Return fundamentals + rule-based score + LLM analysis for each candidate."""
    agent = BaseAgent(role="FundamentalAnalyst", system_prompt=SYSTEM_PROMPT, tools=[])
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

        if not info.get("current_price"):
            has_error = "error" in info
            reason = f"yfinance error: {info['error']}" if has_error else "no price from yfinance / Stooq / Google Finance"
            log(f"FundamentalAnalyst: {sym} — skipping ({reason})")
            time.sleep(0.5)
            continue

        # 52-week proximity metrics
        price    = info.get("current_price")
        high_52w = info.get("fifty_two_week_high")
        low_52w  = info.get("fifty_two_week_low")
        if price and high_52w and high_52w > 0:
            info["pct_from_52w_high"] = round((price - high_52w) / high_52w * 100, 1)
        if price and low_52w and low_52w > 0:
            info["pct_from_52w_low"] = round((price - low_52w) / low_52w * 100, 1)

        # Rule-based score
        info["fundamental_score"] = round(_score(info), 1)

        # LLM qualitative analysis
        log(f"FundamentalAnalyst: {sym} — running LLM analysis...")
        llm = _llm_analysis(agent, info, log)
        info.update(llm)

        # Apply LLM score adjustment (capped 0-100)
        adj = llm.get("fundamental_score_adj", 0)
        if adj:
            info["fundamental_score"] = round(
                max(0.0, min(100.0, info["fundamental_score"] + adj)), 1
            )

        mc = info.get("market_cap")
        mc_str  = f"${mc/1e9:.1f}B" if mc and mc >= 1e9 else (f"${mc/1e6:.0f}M" if mc else "N/A")
        ytd_str = f"{info['ytd_return_pct']:+.1f}% YTD" if info.get("ytd_return_pct") is not None else "YTD N/A"
        h_str   = f"{info['pct_from_52w_high']:+.1f}% from 52w high" if info.get("pct_from_52w_high") is not None else ""
        verdict = info.get("fundamental_verdict", "")
        log(
            f"FundamentalAnalyst: {sym} — ${info['current_price']} | {mc_str} | "
            f"{ytd_str} | {h_str} | verdict={verdict} | score={info['fundamental_score']}"
        )

        day_cache.put(key, info)
        results.append(info)
        time.sleep(0.5)

    results.sort(key=lambda x: -x["fundamental_score"])
    log(f"FundamentalAnalyst: top {len(results)} by score: {[r['symbol'] for r in results[:10]]}")
    return results
