"""SynthesizerAgent — combines all analysis into top 5 picks via Claude → GPT-4o → Gemini fallback."""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent

SYSTEM_PROMPT = """You are a senior equity analyst and portfolio manager at a top-tier hedge fund.
You write institutional-quality research notes — the kind that move markets. Your analysis is
specific, number-driven, and actionable. Vague prose gets you fired.

You will receive comprehensive research on multiple stocks: fundamentals, technicals, news
catalysts, analyst actions, and market conditions. Select the TOP 5 picks for the next 30 days.

══════════════════════════════════════════════════════════════════
OUTPUT FORMAT — return ONLY valid JSON (no markdown, no code fences):
══════════════════════════════════════════════════════════════════
{
  "picks": [
    {
      "symbol": "CRWD",
      "company": "CrowdStrike Holdings, Inc.",
      "exchange": "NASDAQ",
      "sector": "Technology",
      "current_price": 688.00,
      "entry_price": 690.00,
      "exit_price": 820.00,
      "stop_loss": 620.00,
      "confidence_pct": 65,
      "confidence_label": "Med-High",
      "earnings_date": "~Sept 2026 (outside horizon)",
      "thesis": "CrowdStrike offers a clean post-earnings momentum setup with a near-term structural catalyst: a 4-for-1 stock split effective July 2026. The stock gained ~60% YTD and pulled back 12% from its ATH of $785 on broader market weakness, offering an attractive re-entry point with no binary event risk in the 30-day window.",
      "fundamental_analysis": "Q1 FY2027 EPS was $1.10 vs. $1.07 estimated — a clean beat driving 40 bullish analyst revisions and a strengthened Moderate Buy consensus. ARR is tracking toward $6B. The AI Falcon platform's high switching costs and net revenue retention support continued ARR acceleration. The 4-for-1 split will lower the per-share price to ~$170, broadening the retail investor base — a mechanism that has historically created short-term demand.",
      "technical_analysis": "CRWD pulled back 12% from its June 1 ATH of $785 to ~$688, resetting RSI from overbought levels. Post-earnings base has technical support at $620 (stop). The $820 target represents a re-test of the ATH area consistent with split-catalyst buying. SMA50 remains above SMA200 (golden cross intact). Volume on the pullback was below average, suggesting distribution is limited.",
      "risks": "High valuation (~30x revenue) requires continued ARR acceleration. Competitors SentinelOne and Palo Alto Networks are intensifying platform competition. Any broad tech multiple compression driven by higher yields could disproportionately affect high-multiple growth names. The stock split catalyst, while historically positive, is not guaranteed to drive sustained demand."
    }
  ],
  "market_summary": "2-3 sentence overview of current market conditions, VIX level, and dominant themes."
}

══════════════════════════════════════════════════════════════════
STRICT RULES FOR EACH FIELD:
══════════════════════════════════════════════════════════════════

PRICES:
- current_price: use the live market price from the research data
- entry_price: within 0.5% of current_price (round to nearest dollar or 50 cents)
- exit_price: derive from analyst_target in the data, or fundamental fair value. Must be
  achievable within 30 days. Show the % gain in your thesis.
- stop_loss: entry × (1 − stop_loss_pct/100) OR the nearest significant technical support
  level, whichever is more meaningful. Must align with your technical_analysis text.

CONFIDENCE:
- confidence_pct: 60-95. Base on: quality of catalyst + technical setup + sentiment + risk
- confidence_label: "Medium" (60-69) | "Med-High" (70-79) | "High" (80-89) | "Very High" (90+)

EARNINGS DATE:
- If earnings_days_away is known and ≤ 30: state exact date and flag as risk
- If outside 30-day horizon: write "~Month Year (outside horizon)"
- If unknown: write "Unknown — monitor for announcement"

THESIS (2-4 sentences — the SINGLE most compelling reason to own this stock):
- Lead with the primary catalyst (earnings beat, analyst upgrade, technical setup, corporate action)
- Name specific numbers: EPS actual vs estimate, analyst price target, YTD performance, % from ATH
- Must be actionable: WHY is NOW the right entry point?

FUNDAMENTAL_ANALYSIS (3-5 sentences):
- Cite specific metrics from the data: EPS surprise %, revenue growth %, forward PE, analyst count
- Mention analyst consensus (rating + target) and any recent upgrades/downgrades
- Explain the business model moat and why it matters for the 30-day setup
- If analyst_upgrades or analyst_actions are in the data, reference them explicitly

TECHNICAL_ANALYSIS (3-5 sentences):
- Use the actual RSI, SMA50 vs SMA200 status, MACD signal from the data
- Reference the 52-week high, how far the stock has pulled back, and what that level represents
- Name specific price levels for support and resistance
- Describe volume context (surging/declining on the move)

RISKS (2-4 sentences):
- Be specific: name the actual risks (regulatory, competitive, macro, valuation)
- Include the binary event risk if earnings are within 45 days
- Do NOT use generic platitudes like "all investments carry risk"

WEB SNIPPETS:
- Each stock in the research package may include a "web_snippets" list containing raw
  Yahoo Search results fetched when yfinance had data gaps.
- Mine these snippets for specific data: EPS actuals vs estimates, analyst firm upgrades
  with price targets, stock splits, buybacks, regulatory events, product launches.
- If a snippet says "JPMorgan raised price target to $460" — cite that in analyst_actions.
- If a snippet says "Q1 EPS $1.10 beat $1.07 estimate" — use those exact numbers in your analysis.
- Do NOT hallucinate numbers. Only use numbers that appear in the research data or web_snippets.

ADDITIONAL RULES:
- DO NOT pick any stock with earnings within avoid_earnings_within_days days
  UNLESS confidence_pct ≥ 85 and you explicitly flag the binary risk in the thesis
- If market_risk is "high" (VIX > 25), include at least one defensive ETF pick
- Rank picks by confidence_pct descending
- All four prose sections must feel like they were written by a professional analyst
  who actually read the data — cite specific numbers from the research package
- Never write bullet points. Always write flowing prose paragraphs."""


def run(
    fundamentals: list[dict],
    technicals: list[dict],
    sentiments: list[dict],
    volatility: dict,
    strategy: dict,
    log,
) -> dict:
    """Synthesize all research into 5 actionable picks."""
    tech_map = {t["symbol"]: t for t in technicals}
    sent_map = {s["symbol"]: s for s in sentiments}

    research = []
    for f in fundamentals[:20]:
        sym = f["symbol"]
        t   = tech_map.get(sym, {})
        s   = sent_map.get(sym, {})

        # Compute expected gain % from analyst target vs current price
        cur   = t.get("current_price") or f.get("current_price")
        a_tgt = f.get("analyst_target")
        upside_pct = None
        if cur and a_tgt and cur > 0:
            upside_pct = round((a_tgt - cur) / cur * 100, 1)

        research.append({
            "symbol": sym,
            "company": f.get("company", sym),
            "exchange": "NASDAQ/NYSE",
            "sector": f.get("sector", "Unknown"),
            "industry": f.get("industry", "Unknown"),

            # Price context
            "current_price": cur,
            "ytd_return_pct": f.get("ytd_return_pct"),
            "52w_high": t.get("high_52w") or f.get("fifty_two_week_high"),
            "52w_high_date": t.get("high_52w_date"),
            "52w_low": t.get("low_52w") or f.get("fifty_two_week_low"),
            "pct_from_52w_high": t.get("pct_from_52w_high"),
            "pct_from_52w_low": t.get("pct_from_52w_low"),

            # Fundamentals
            "market_cap": f.get("market_cap"),
            "pe_ratio": f.get("pe_ratio"),
            "forward_pe": f.get("forward_pe"),
            "price_to_sales": f.get("price_to_sales"),
            "eps_ttm": f.get("eps"),
            "eps_growth_yoy": f.get("eps_growth"),
            "last_eps_actual": f.get("eps_actual"),
            "last_eps_estimate": f.get("eps_estimate"),
            "eps_surprise_pct": f.get("eps_surprise_pct"),
            "revenue_growth": f.get("revenue_growth"),
            "gross_margin": f.get("gross_margin"),
            "operating_margin": f.get("operating_margin"),
            "free_cash_flow": f.get("free_cash_flow"),
            "roe": f.get("roe"),
            "debt_to_equity": f.get("debt_to_equity"),
            "fundamental_score": f.get("fundamental_score", 0),
            "fundamental_summary": f.get("fundamental_summary", ""),
            "fundamental_strengths": f.get("fundamental_strengths", []),
            "fundamental_risks": f.get("fundamental_risks", []),
            "fundamental_verdict": f.get("fundamental_verdict", ""),

            # Analyst consensus
            "analyst_target_mean": a_tgt,
            "analyst_target_high": f.get("analyst_high_target"),
            "analyst_target_low": f.get("analyst_low_target"),
            "analyst_upside_pct": upside_pct,
            "analyst_rating": f.get("analyst_rating"),
            "analyst_count": f.get("analyst_count"),
            "analyst_buy_count": f.get("analyst_upgrades"),
            "recent_analyst_actions": f.get("recent_analyst_actions", []),

            # Earnings
            "earnings_date": f.get("earnings_date"),
            "earnings_days_away": f.get("earnings_days_away"),
            "recent_earnings_history": f.get("recent_earnings_history", []),

            # Technicals
            "rsi": t.get("rsi"),
            "sma50": t.get("sma50"),
            "sma200": t.get("sma200"),
            "macd": t.get("macd"),
            "bb_upper": t.get("bb_upper"),
            "bb_lower": t.get("bb_lower"),
            "technical_signals": t.get("signals", []),
            "technical_score": t.get("technical_score", 0),
            "technical_summary": t.get("technical_summary", ""),
            "technical_setup": t.get("technical_setup", ""),
            "support_level": t.get("support_level"),
            "resistance_level": t.get("resistance_level"),

            # Sentiment & catalysts
            "sentiment_score": s.get("sentiment_score", 0),
            "sentiment_label": s.get("sentiment_label", "neutral"),
            "sentiment_summary": s.get("sentiment_summary", ""),
            "notable_news": s.get("notable_news", ""),
            "catalysts": s.get("catalysts", []),
            "analyst_actions": s.get("analyst_actions", []),
            "risks_from_news": s.get("risks_from_news", ""),

            # Yahoo Search enrichment (filled when yfinance had gaps)
            "web_snippets": f.get("web_snippets", []),

            # Market risk
            "beta": f.get("beta") or volatility.get("betas", {}).get(sym),
        })

    params = strategy.get("parameters", {})
    if isinstance(params, str):
        params = json.loads(params)

    context = {
        "market_conditions": {
            "vix": volatility.get("vix"),
            "market_risk": volatility.get("market_risk"),
            "date": __import__("datetime").date.today().isoformat(),
        },
        "active_strategy": {
            "description": strategy.get("description", ""),
            "stop_loss_pct": params.get("stop_loss_pct", 15),
            "profit_target_pct": params.get("profit_target_pct", 10),
            "confidence_threshold": params.get("confidence_threshold", 70),
            "avoid_earnings_within_days": params.get("avoid_earnings_within_days", 5),
            "preferred_sectors": params.get("preferred_sectors", []),
        },
        "research": research,
    }

    synth_prompt = params.get("prompts", {}).get("synthesizer") or SYSTEM_PROMPT
    agent = BaseAgent(role="Synthesizer", system_prompt=synth_prompt)
    log("Synthesizer: generating final picks (institutional-quality mode)...")
    result = agent.run(
        "Based on the full research package, select the top 5 picks for the next 30 days. "
        "Write institutional-quality analysis citing specific data points from the research. "
        "Each pick must name actual numbers — EPS beats, YTD %, ATH proximity, analyst targets. "
        "For any stock with web_snippets, mine those for specific EPS beats, analyst upgrades "
        "with price targets, and corporate actions (splits, buybacks) — cite them explicitly.",
        context=context,
    )

    picks = result.get("picks", [])
    log(f"Synthesizer: selected {len(picks)} picks: {[p.get('symbol') for p in picks]}")
    return result
