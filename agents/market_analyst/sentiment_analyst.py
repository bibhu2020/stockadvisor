"""SentimentAnalystAgent — scores news sentiment via Claude → GPT-4o → Gemini fallback."""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent, Tool
from agents.core.data_fetcher import fetch_all_news
from agents.core import day_cache

SYSTEM_PROMPT = """You are a senior financial news analyst at a hedge fund. You receive recent
news headlines for a stock and extract structured intelligence for a research note.

Return ONLY valid JSON with these exact fields:
{
  "sentiment_score": <float -1.0 to +1.0>,
  "sentiment_label": "very_positive|positive|neutral|negative|very_negative",
  "key_themes": [<3-5 key themes driving the stock narrative>],
  "notable_news": "<single most impactful headline verbatim>",
  "sentiment_summary": "<2 sentences summarising the overall news tone>",
  "catalysts": [
    "<specific catalyst 1: e.g. 'Q1 EPS beat: $1.10 actual vs $1.07 estimate'>",
    "<specific catalyst 2: e.g. '4-for-1 stock split announced for July 2026'>",
    "<specific catalyst 3 if present>"
  ],
  "analyst_actions": [
    "<e.g. 'JPMorgan raised PT to $460 (Buy) from $395 post-earnings'>",
    "<additional analyst action if present>"
  ],
  "risks_from_news": "<1-2 sentences on specific downside risks visible in the news>"
}

Rules:
- catalysts: ONLY include concrete, verifiable events (earnings beats with specific numbers,
  analyst upgrades with targets, stock splits, buybacks, regulatory wins/losses, product launches).
  Do NOT include vague statements.
- analyst_actions: extract specific firm names and price targets where mentioned.
- If no catalysts or analyst actions are found in the headlines, return empty lists [].
- Return ONLY valid JSON, no markdown, no code fences."""


def run(candidates: list[str], fundamentals: list[dict], log) -> list[dict]:
    """Score news sentiment for each candidate using GPT-4o."""
    fund_map = {f["symbol"]: f for f in fundamentals}
    agent = BaseAgent(
        role="SentimentAnalyst",
        system_prompt=SYSTEM_PROMPT,
        tools=[],
    )

    results = []
    for sym in candidates:
        key = f"sentiment_{sym}"
        cached = day_cache.get(key)
        if cached:
            log(f"[cache] HIT  {key} — {cached.get('sentiment_label','?')}")
            results.append(cached)
            continue

        company = fund_map.get(sym, {}).get("company", sym)
        log(f"SentimentAnalyst: fetching news for {sym}...")
        news = fetch_all_news(sym, company)

        if not news:
            entry = {
                "symbol": sym,
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "key_themes": [],
                "notable_news": "",
                "sentiment_summary": "No news found.",
            }
            day_cache.put(key, entry)
            results.append(entry)
            continue

        headlines = "\n".join(
            f"- {n['title']} ({n.get('source','')})" for n in news[:15]
        )
        msg = f"Stock: {sym} ({company})\n\nHeadlines:\n{headlines}"
        result = agent.run(msg)

        result["symbol"] = sym
        day_cache.put(key, result)
        results.append(result)
        log(f"  {sym} sentiment: {result.get('sentiment_label','?')} ({result.get('sentiment_score',0):.2f})")

    return results
