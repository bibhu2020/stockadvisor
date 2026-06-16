"""TradeDecisionAgent — decides which picks to buy via Claude → GPT-4o → Gemini fallback."""
import json
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent
from agents.core.data_fetcher import get_current_price

SYSTEM_PROMPT = """You are a disciplined algorithmic paper trader. Given a list of analyst picks
and current portfolio state, decide which stocks to BUY now.

Rules you must follow:
1. Never buy if the stock is already in open_positions
2. Never exceed max_positions total open positions
3. Never spend more than position_size_pct * buying_power per trade
4. Only buy picks with confidence_pct >= confidence_threshold
5. Don't buy within avoid_earnings_within_days days of earnings_date
6. Current price must be within 2% of the analyst entry_price (not too far off)
7. Only buy if buying_power > $100 after the purchase

Return ONLY valid JSON:
{
  "buy_orders": [
    {
      "symbol": "AAPL",
      "quantity": 5,
      "price": 185.40,
      "reason": "Within entry range, strong technicals, above confidence threshold"
    }
  ],
  "reasoning": "Brief explanation of overall decisions"
}
If no buys are warranted, return {"buy_orders": [], "reasoning": "..."}"""


def run(last_report, open_symbols: list[str], buying_power: float,
        strategy_params: dict, log) -> list[dict]:
    """Decide BUY orders from analyst picks not yet in portfolio."""
    if not last_report:
        log("TradeDecision: no analyst report available — holding")
        return []

    picks = last_report.get_picks()
    candidates = []
    for pick in picks:
        sym = pick.get("symbol")
        if sym in open_symbols:
            log(f"  {sym}: already in portfolio — skip")
            continue

        current = get_current_price(sym)
        if current is None:
            log(f"  {sym}: price unavailable — skip")
            continue

        entry = pick.get("entry_price", current)
        pct_diff = abs(current - entry) / entry * 100
        pick["current_price"] = current
        pick["price_deviation_pct"] = round(pct_diff, 2)
        candidates.append(pick)

    if not candidates:
        log("TradeDecision: no eligible candidates")
        return []

    params = strategy_params if isinstance(strategy_params, dict) else json.loads(strategy_params)
    context = {
        "buying_power": buying_power,
        "open_symbols": open_symbols,
        "open_position_count": len(open_symbols),
        "max_positions": params.get("max_positions", 5),
        "position_size_pct": params.get("position_size_pct", 20),
        "confidence_threshold": params.get("confidence_threshold", 70),
        "avoid_earnings_within_days": params.get("avoid_earnings_within_days", 5),
        "candidates": candidates,
    }

    agent = BaseAgent(role="TradeDecision", system_prompt=SYSTEM_PROMPT)
    log("TradeDecision: generating trade decisions...")
    result = agent.run("Decide which stocks to buy from the candidates.", context=context)
    buy_orders = result.get("buy_orders", [])
    log(f"TradeDecision: {len(buy_orders)} BUY orders: {[o.get('symbol') for o in buy_orders]}")
    log(f"  Reasoning: {result.get('reasoning','')}")
    return buy_orders
