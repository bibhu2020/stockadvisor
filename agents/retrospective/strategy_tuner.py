"""StrategyTunerAgent — GPT-4o rewrites strategy when performance lags SPY."""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent
from agents.core.db import Strategy, SessionLocal
from sqlalchemy import select

SYSTEM_PROMPT = """You are a senior quantitative strategist at a top hedge fund. You are
reviewing a trading strategy that underperformed the SPY benchmark and must evolve it.

Based on the performance data, pattern analysis, and the current strategy, create an improved
strategy for the next month.

Return ONLY valid JSON (no markdown):
{
  "name": "Strategy name (include version hint)",
  "description": "Detailed strategy instructions in 3-5 sentences. This text is used directly
    as the system prompt for the AI analyst. Be specific about: what kinds of stocks to prefer,
    what signals to look for, what to avoid, timing preferences.",
  "parameters": {
    "stop_loss_pct": <5-20 float>,
    "profit_target_pct": <5-30 float>,
    "max_positions": <3-8 int>,
    "confidence_threshold": <60-90 int>,
    "position_size_pct": <10-40 float>,
    "preferred_sectors": ["sector1", "sector2"],
    "avoid_earnings_within_days": <0-14 int>,
    "entry_timing_rules": "description of when/how to enter"
  },
  "rationale": "2-3 sentence explanation of what changed and why"
}"""


def run(current_strategy: Strategy, performance: dict, patterns: dict,
        session, log) -> Strategy | None:
    """Create a new evolved strategy. Returns the new Strategy object or None."""
    if not performance.get("underperformed_spy"):
        log("StrategyTuner: performance meets or beats SPY — no strategy change.")
        return None

    current_params = current_strategy.get_parameters()
    context = {
        "current_strategy": {
            "name": current_strategy.name,
            "version": current_strategy.version,
            "description": current_strategy.description,
            "parameters": current_params,
        },
        "performance": performance,
        "patterns": patterns,
    }

    agent = BaseAgent(role="StrategyTuner", system_prompt=SYSTEM_PROMPT)
    log("StrategyTuner: calling GPT-4o to evolve strategy...")
    result = agent.run(
        f"The current strategy underperformed SPY by "
        f"{performance.get('spy_equivalent_pnl', 0) - performance.get('total_pnl', 0):.2f}. "
        "Create an improved strategy for next month.",
        context=context,
    )

    if "error" in result or "name" not in result:
        log(f"StrategyTuner: invalid response — {result}")
        return None

    # Validate parameters
    params = result.get("parameters", {})
    safe_params = {
        "stop_loss_pct": max(5.0, min(20.0, float(params.get("stop_loss_pct", current_params["stop_loss_pct"])))),
        "profit_target_pct": max(5.0, min(30.0, float(params.get("profit_target_pct", current_params["profit_target_pct"])))),
        "max_positions": max(3, min(8, int(params.get("max_positions", current_params["max_positions"])))),
        "confidence_threshold": max(60, min(90, int(params.get("confidence_threshold", current_params["confidence_threshold"])))),
        "position_size_pct": max(10.0, min(40.0, float(params.get("position_size_pct", current_params["position_size_pct"])))),
        "preferred_sectors": params.get("preferred_sectors", []),
        "avoid_earnings_within_days": max(0, min(14, int(params.get("avoid_earnings_within_days", current_params["avoid_earnings_within_days"])))),
        "entry_timing_rules": params.get("entry_timing_rules", ""),
    }

    # Deactivate old strategy
    current_strategy.is_active = False
    current_strategy.performance_vs_spy = round(
        performance.get("total_pnl", 0) - (performance.get("spy_equivalent_pnl") or 0), 2
    )

    # Create new strategy
    new_strategy = Strategy(
        version=current_strategy.version + 1,
        name=result.get("name", f"Strategy v{current_strategy.version + 1}"),
        description=result.get("description", ""),
        parameters=json.dumps(safe_params),
        is_active=True,
        source="retrospective",
    )
    session.add(new_strategy)
    session.flush()

    log(f"StrategyTuner: new strategy v{new_strategy.version} created: {new_strategy.name}")
    log(f"  Rationale: {result.get('rationale','')}")
    return new_strategy
