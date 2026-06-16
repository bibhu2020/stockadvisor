"""PatternAnalyzerAgent — finds win/lose patterns via Claude → GPT-4o → Gemini fallback."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent

SYSTEM_PROMPT = """You are a quantitative trading analyst reviewing a month of paper trades.
Analyze the transaction data to identify patterns:
- What characteristics do winning trades share?
- What caused the losing trades?
- Were there timing issues (entered too early/late)?
- Did market conditions (VIX, sector trends) affect outcomes?
- Any sector biases that helped or hurt?

Return ONLY valid JSON:
{
  "winning_patterns": ["pattern 1", "pattern 2"],
  "losing_patterns": ["pattern 1", "pattern 2"],
  "key_insight": "Most important single insight from this month",
  "strategy_weaknesses": ["weakness 1", "weakness 2"],
  "strategy_strengths": ["strength 1"],
  "analysis_text": "3-5 paragraph detailed narrative analysis"
}"""


def run(performance: dict, log) -> dict:
    if performance["total_trades"] == 0:
        log("PatternAnalyzer: no trades this month — skipping.")
        return {
            "winning_patterns": [],
            "losing_patterns": [],
            "key_insight": "No trades executed this month.",
            "strategy_weaknesses": ["No data available"],
            "strategy_strengths": [],
            "analysis_text": "No trades were executed in this period.",
        }

    agent = BaseAgent(role="PatternAnalyzer", system_prompt=SYSTEM_PROMPT)
    log("PatternAnalyzer: analyzing trade patterns...")
    result = agent.run(
        "Analyze the monthly trading performance and find patterns.",
        context=performance,
    )
    log(f"PatternAnalyzer: key insight: {result.get('key_insight','')}")
    return result
