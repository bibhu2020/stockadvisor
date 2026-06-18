"""FundamentalAnalystAgent — data fetch + rule-based score + one batch LLM call for all tickers."""
import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent
from agents.core.data_fetcher import get_fundamentals, get_web_enrichment
from agents.core import day_cache

SYSTEM_PROMPT = """You are a senior fundamental equity analyst at a top-tier hedge fund.
You receive financial metrics for multiple stocks simultaneously. Analyse each one and return
a concise, data-driven qualitative assessment — the kind that surfaces insights a scoring
formula cannot: inflecting margins, re-rating catalysts, hidden leverage risks.

OBJECTIVE: Identify stocks with idiosyncratic, company-specific catalysts that can OUTPERFORM
the S&P 500. The SPY benchmark returns ~10-12% annually (~1% per month). Only stocks with a
clear path to exceeding this deserve a buy/strong_buy verdict. Reject index-correlated plays.

FAVOUR (score up):
- Revenue growth > 15% YoY with stable or expanding gross margins
- EPS beat in the most recent quarter; ≥2 consecutive beats is a strong signal
- Positive analyst revisions (upgrades or PT increases) in the past 30 days
- ROE > 15%, debt/equity < 1.5, positive free cash flow
- A concrete upcoming catalyst: product launch, earnings re-rating, buyback, restructuring

PENALISE (score down):
- Revenue growth < 5% with no visible re-rating catalyst — that is a SPY-equivalent at best
- Gross margin compression for 2+ consecutive quarters
- Debt/equity > 2.5 or sustained negative free cash flow with no clear profitability path
- High-beta stocks with no fundamental story — those just amplify SPY risk, not alpha

Return ONLY valid JSON (no markdown, no preamble):
{
  "analyses": [
    {
      "symbol": "TICKER",
      "summary": "<2-3 sentences — interpret what the numbers mean together, cite specific values>",
      "strengths": ["<specific strength with numbers>", "<strength 2>"],
      "risks": ["<specific risk>", "<risk 2 if present>"],
      "verdict": "strong_buy|buy|neutral|sell|avoid",
      "score_adjustment": <integer -20 to +20>
    }
  ]
}

Analyse EVERY ticker in the input. score_adjustment:
  +20 exceptional hidden value — clear path to 20%+ gains independent of market direction
  +10 meaningfully better than the score implies
   0  formula is fair
  -10 concerning factors underweighted (e.g. margin compression, rising debt)
  -20 serious red flags (liquidity crisis, accounting concern, sector collapse)

Return ONLY valid JSON."""


def _needs_web_enrichment(info: dict) -> bool:
    return info.get("analyst_target") is None and len(info.get("recent_earnings_history", [])) == 0


def _score(info: dict) -> float:
    score = 50.0

    pe = info.get("pe_ratio")
    if pe and 0 < pe < 20:   score += 10
    elif pe and pe > 60:      score -= 10

    eps_growth = info.get("eps_growth")
    if eps_growth is not None:
        if eps_growth > 0.2:  score += 15
        elif eps_growth > 0:  score += 7
        else:                 score -= 10

    rev_growth = info.get("revenue_growth")
    if rev_growth is not None:
        if rev_growth > 0.15: score += 10
        elif rev_growth > 0:  score += 5
        else:                 score -= 5

    if (info.get("roe") or 0) > 0.15:  score += 10

    de = info.get("debt_to_equity")
    if de is not None:
        if de < 0.5:   score += 5
        elif de > 2.0: score -= 10

    surprise = info.get("eps_surprise_pct")
    if surprise is not None:
        if surprise > 5:  score += 12
        elif surprise > 0: score += 5
        else:              score -= 8

    rating = (info.get("analyst_rating") or "").lower()
    if "buy" in rating:  score += 8
    elif "sell" in rating: score -= 8

    buys = sum(1 for a in info.get("recent_analyst_actions", [])[:5]
               if "buy" in (a.get("to_grade") or "").lower())
    if buys >= 2:   score += 8
    elif buys == 1: score += 4

    if (info.get("analyst_upgrades") or 0) >= 5: score += 5

    mc = info.get("market_cap")
    if mc:
        if mc >= 10_000_000_000:  score += 5
        elif mc >= 2_000_000_000: score += 2
        elif mc < 300_000_000:    score -= 10
        else:                     score -= 3

    ytd = info.get("ytd_return_pct")
    if ytd is not None:
        if ytd > 30:    score += 8
        elif ytd > 15:  score += 5
        elif ytd > 0:   score += 2
        elif ytd < -30: score -= 10
        elif ytd < -15: score -= 5

    pfh = info.get("pct_from_52w_high")
    if pfh is not None:
        if pfh >= -5:    score += 5
        elif pfh >= -15: score += 3
        elif pfh < -40:  score -= 5

    return max(0.0, min(100.0, score))


def _batch_llm_analysis(agent: BaseAgent, items: list[dict], log) -> None:
    """One LLM call for all items. Enriches dicts in-place and updates cache."""
    payload = []
    for d in items:
        cur = d.get("current_price")
        tgt = d.get("analyst_target")
        payload.append({
            "symbol":               d["symbol"],
            "company":              d.get("company"),
            "sector":               d.get("sector"),
            "current_price":        cur,
            "market_cap":           d.get("market_cap"),
            "pe_ratio":             d.get("pe_ratio"),
            "forward_pe":           d.get("forward_pe"),
            "price_to_sales":       d.get("price_to_sales"),
            "eps_growth_yoy":       d.get("eps_growth"),
            "eps_surprise_pct":     d.get("eps_surprise_pct"),
            "revenue_growth":       d.get("revenue_growth"),
            "gross_margin":         d.get("gross_margin"),
            "operating_margin":     d.get("operating_margin"),
            "free_cash_flow":       d.get("free_cash_flow"),
            "roe":                  d.get("roe"),
            "debt_to_equity":       d.get("debt_to_equity"),
            "analyst_rating":       d.get("analyst_rating"),
            "analyst_target":       tgt,
            "analyst_upside_pct":   round((tgt - cur) / cur * 100, 1) if tgt and cur else None,
            "analyst_count":        d.get("analyst_count"),
            "ytd_return_pct":       d.get("ytd_return_pct"),
            "pct_from_52w_high":    d.get("pct_from_52w_high"),
            "earnings_days_away":   d.get("earnings_days_away"),
            "recent_earnings":      d.get("recent_earnings_history", [])[:2],
            "recent_analyst_actions": d.get("recent_analyst_actions", [])[:3],
            "web_snippets":         d.get("web_snippets", [])[:3],
            "rule_based_score":     d.get("fundamental_score"),
        })

    try:
        result = agent.run(
            f"Perform fundamental analysis for all {len(items)} stocks in the context.",
            context={"stocks": payload},
        )
        analyses = {a["symbol"]: a for a in result.get("analyses", [])}
    except Exception as exc:
        log(f"FundamentalAnalyst: batch LLM call failed ({exc})")
        analyses = {}

    for d in items:
        sym = d["symbol"]
        a   = analyses.get(sym, {})
        d["fundamental_summary"]   = a.get("summary", "")
        d["fundamental_strengths"] = a.get("strengths", [])
        d["fundamental_risks"]     = a.get("risks", [])
        d["fundamental_verdict"]   = a.get("verdict", "neutral")
        adj = int(a.get("score_adjustment", 0))
        if adj:
            d["fundamental_score"] = round(max(0.0, min(100.0, d["fundamental_score"] + adj)), 1)
        day_cache.put(f"fundamentals_{sym}", d)


def get_prompt(strategy_params: dict) -> str:
    return strategy_params.get("prompts", {}).get("fundamental_analyst") or SYSTEM_PROMPT


def run(candidates: list[str], log, strategy_params: dict | None = None) -> list[dict]:
    agent     = BaseAgent(role="FundamentalAnalyst", system_prompt=get_prompt(strategy_params or {}), tools=[])
    results   = []
    needs_llm = []

    for sym in candidates:
        key    = f"fundamentals_{sym}"
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
                log(f"FundamentalAnalyst: {sym} — no yfinance data, running web search...")
                web = get_web_enrichment(sym, info.get("company", sym))
                day_cache.put(web_key, web)
            info["web_snippets"] = web.get("web_snippets", [])
        else:
            info["web_snippets"] = []

        if not info.get("current_price"):
            reason = f"yfinance error: {info['error']}" if "error" in info else "no price from any source"
            log(f"FundamentalAnalyst: {sym} — skipping ({reason})")
            time.sleep(0.5)
            continue

        price    = info["current_price"]
        high_52w = info.get("fifty_two_week_high")
        low_52w  = info.get("fifty_two_week_low")
        if high_52w and high_52w > 0:
            info["pct_from_52w_high"] = round((price - high_52w) / high_52w * 100, 1)
        if low_52w and low_52w > 0:
            info["pct_from_52w_low"] = round((price - low_52w) / low_52w * 100, 1)

        info["fundamental_score"] = round(_score(info), 1)

        mc  = info.get("market_cap")
        mc_str  = f"${mc/1e9:.1f}B" if mc and mc >= 1e9 else (f"${mc/1e6:.0f}M" if mc else "N/A")
        ytd_str = f"{info['ytd_return_pct']:+.1f}% YTD" if info.get("ytd_return_pct") is not None else "YTD N/A"
        h_str   = f"{info['pct_from_52w_high']:+.1f}% from 52w high" if info.get("pct_from_52w_high") is not None else ""
        log(f"  {sym} — ${price} | {mc_str} | {ytd_str} | {h_str} | rule score={info['fundamental_score']}")

        results.append(info)
        needs_llm.append(info)
        time.sleep(0.5)

    # One batch LLM call for all non-cached tickers
    if needs_llm:
        syms = [d["symbol"] for d in needs_llm]
        log(f"FundamentalAnalyst: batch LLM analysis for {syms}...")
        _batch_llm_analysis(agent, needs_llm, log)
        for d in needs_llm:
            log(f"  {d['symbol']} verdict={d.get('fundamental_verdict')} score={d['fundamental_score']}")

    results.sort(key=lambda x: -x["fundamental_score"])
    log(f"FundamentalAnalyst: ranked — {[r['symbol'] for r in results]}")
    return results
