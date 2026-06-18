"""SentimentAnalystAgent — fetch all news first, then one batch LLM call for all tickers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent
from agents.core.data_fetcher import fetch_all_news
from agents.core import day_cache

SYSTEM_PROMPT = """You are a senior financial news analyst at a hedge fund.
You receive recent headlines for multiple stocks simultaneously and extract structured
investment intelligence for each. Focus on concrete, verifiable information.

Return ONLY valid JSON (no markdown, no preamble):
{
  "analyses": [
    {
      "symbol": "TICKER",
      "sentiment_score": <float -1.0 to 1.0>,
      "sentiment_label": "very_positive|positive|neutral|negative|very_negative",
      "sentiment_summary": "<2 sentences on the overall news tone and what is driving it>",
      "notable_news": "<single most impactful headline verbatim>",
      "catalysts": [
        "<concrete catalyst with numbers, e.g. 'Q1 EPS $1.10 beat $1.07 estimate'>",
        "<catalyst 2 if present>"
      ],
      "analyst_actions": [
        "<e.g. 'JPMorgan raised PT to $460 (Buy) from $395 post-earnings'>",
        "<additional action if present>"
      ],
      "risks_from_news": "<1-2 sentences on specific downside risks visible in the headlines>"
    }
  ]
}

Rules:
- Analyse EVERY ticker in the input, even if headlines are sparse
- catalysts: ONLY concrete verifiable events with specific numbers. Empty list [] if none found
- analyst_actions: specific firm names and price targets only. Empty list [] if none found
- If no headlines for a ticker: return neutral sentiment, empty lists, empty strings
- Return ONLY valid JSON."""


def get_prompt(strategy_params: dict) -> str:
    return strategy_params.get("prompts", {}).get("sentiment_analyst") or SYSTEM_PROMPT


def run(candidates: list[str], fundamentals: list[dict], log,
        strategy_params: dict | None = None) -> list[dict]:
    """Fetch news for all candidates, then one batch LLM call for all sentiment analysis."""
    fund_map = {f["symbol"]: f for f in fundamentals}
    agent    = BaseAgent(role="SentimentAnalyst", system_prompt=get_prompt(strategy_params or {}), tools=[])

    # ── Step 1: collect news for all tickers (HTTP only, no LLM) ──────────────
    news_map:   dict[str, list] = {}
    needs_llm:  list[dict]      = []
    results:    list[dict]      = []

    for sym in candidates:
        sent_key = f"sentiment_{sym}"
        cached   = day_cache.get(sent_key)
        if cached:
            log(f"[cache] HIT  {sent_key} — {cached.get('sentiment_label', '?')}")
            results.append(cached)
            continue

        news_key = f"news_{sym}"
        news     = day_cache.get(news_key)
        if news is not None:
            log(f"[cache] HIT  {news_key} ({len(news)} headlines)")
        else:
            company = fund_map.get(sym, {}).get("company", sym)
            log(f"SentimentAnalyst: fetching news for {sym}...")
            news = fetch_all_news(sym, company)
            day_cache.put(news_key, news)

        news_map[sym] = news
        needs_llm.append({"symbol": sym})

    # ── Step 2: one batch LLM call for all non-cached tickers ─────────────────
    if needs_llm:
        payload = [
            {
                "symbol":    d["symbol"],
                "company":   fund_map.get(d["symbol"], {}).get("company", d["symbol"]),
                "headlines": [
                    f"- {n['title']} ({n.get('source', '')})"
                    for n in news_map.get(d["symbol"], [])[:15]
                ],
            }
            for d in needs_llm
        ]
        syms = [d["symbol"] for d in needs_llm]
        log(f"SentimentAnalyst: batch LLM analysis for {syms}...")

        try:
            result   = agent.run(
                f"Analyse news sentiment for all {len(payload)} stocks in the context.",
                context={"stocks": payload},
            )
            analyses = {a["symbol"]: a for a in result.get("analyses", [])}
        except Exception as exc:
            log(f"SentimentAnalyst: batch LLM call failed ({exc})")
            analyses = {}

        for d in needs_llm:
            sym   = d["symbol"]
            a     = analyses.get(sym, {})
            entry = {
                "symbol":           sym,
                "sentiment_score":  a.get("sentiment_score", 0.0),
                "sentiment_label":  a.get("sentiment_label", "neutral"),
                "sentiment_summary": a.get("sentiment_summary", ""),
                "notable_news":     a.get("notable_news", ""),
                "catalysts":        a.get("catalysts", []),
                "analyst_actions":  a.get("analyst_actions", []),
                "risks_from_news":  a.get("risks_from_news", ""),
            }
            log(f"  {sym} sentiment={entry['sentiment_label']} ({entry['sentiment_score']:.2f})")
            day_cache.put(f"sentiment_{sym}", entry)
            results.append(entry)

    return results
