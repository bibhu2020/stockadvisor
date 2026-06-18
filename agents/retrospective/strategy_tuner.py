"""StrategyTunerAgent — evolves strategy parameters AND analyst prompts based on performance."""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.base_agent import BaseAgent
from agents.core.db import Strategy, SessionLocal

# Import default prompts as the authoritative fallback baselines
from agents.market_analyst.fundamental_analyst import SYSTEM_PROMPT as DEFAULT_FUNDAMENTAL_PROMPT
from agents.market_analyst.technical_analyst   import SYSTEM_PROMPT as DEFAULT_TECHNICAL_PROMPT
from agents.market_analyst.sentiment_analyst   import SYSTEM_PROMPT as DEFAULT_SENTIMENT_PROMPT
from agents.market_analyst.synthesizer         import SYSTEM_PROMPT as DEFAULT_SYNTHESIZER_PROMPT
from agents.paper_trader.trade_decision        import SYSTEM_PROMPT as DEFAULT_TRADE_DECISION_PROMPT

DEFAULT_PROMPTS = {
    "fundamental_analyst": DEFAULT_FUNDAMENTAL_PROMPT,
    "technical_analyst":   DEFAULT_TECHNICAL_PROMPT,
    "sentiment_analyst":   DEFAULT_SENTIMENT_PROMPT,
    "synthesizer":         DEFAULT_SYNTHESIZER_PROMPT,
    "trade_decision":      DEFAULT_TRADE_DECISION_PROMPT,
}

# Safety limits for prompt tuning
_MIN_TRADES_FOR_PROMPT_TUNING = 3   # need at least this many closed trades
_MAX_PROMPT_LENGTH             = 4000  # chars — reject any prompt longer than this
_MAX_GROWTH_RATIO              = 1.6   # reject if new prompt > 60% longer than current

SYSTEM_PROMPT = """You are a senior quantitative strategist and AI systems engineer at a top
hedge fund. A trading strategy underperformed SPY. You must evolve BOTH the numeric trading
parameters AND the prompt instructions that guide how the AI picks and buys stocks.

The "prompts" block contains the current instructions given to each AI agent:
  - fundamental_analyst: how to assess company financials
  - technical_analyst:   how to read chart setups
  - sentiment_analyst:   how to interpret news and social signals
  - synthesizer:         how to select and rank final picks
  - trade_decision:      how the paper trader decides which analyst picks to BUY and at what
                         quantity — including entry timing, confidence filters, and position sizing

PROMPT TUNING RULES (read carefully):
1. Make TARGETED, SURGICAL edits — do not rewrite prompts from scratch
2. Identify WHICH agent's prompt contributed to the failures in the pattern analysis
3. Add specific rules that address the observed failures (e.g. "Penalise stocks with RSI > 75
   unless MACD crossed bullish in the same week", or "Skip buys if price deviation > 1%")
4. If a prompt is working well, return null — no change
5. Keep additions concise; do not make any prompt more than 50% longer than it currently is
6. Preserve the existing JSON output schema instructions in each prompt — do not alter the
   expected output format, only the analysis/decision guidance

NUMERIC PARAMETER RULES:
- stop_loss_pct:            5–20 float
- profit_target_pct:        5–30 float
- max_positions:            3–8 int
- confidence_threshold:     60–90 int
- position_size_pct:        10–40 float
- avoid_earnings_within_days: 0–14 int

Return ONLY valid JSON (no markdown, no preamble):
{
  "name": "<Strategy name with version hint>",
  "description": "<3-5 sentences of high-level strategy intent>",
  "parameters": {
    "stop_loss_pct": <float>,
    "profit_target_pct": <float>,
    "max_positions": <int>,
    "confidence_threshold": <int>,
    "position_size_pct": <float>,
    "preferred_sectors": ["sector1"],
    "avoid_earnings_within_days": <int>,
    "entry_timing_rules": "<string>",
    "prompts": {
      "fundamental_analyst": "<updated prompt text, or null to keep current>",
      "technical_analyst":   "<updated prompt text, or null to keep current>",
      "sentiment_analyst":   "<updated prompt text, or null to keep current>",
      "synthesizer":         "<updated prompt text, or null to keep current>",
      "trade_decision":      "<updated prompt text, or null to keep current>"
    }
  },
  "rationale": "<2-3 sentences on numeric parameter changes>",
  "prompt_changes_summary": {
    "fundamental_analyst": "<what changed and why, or null if unchanged>",
    "technical_analyst":   "<what changed and why, or null if unchanged>",
    "sentiment_analyst":   "<what changed and why, or null if unchanged>",
    "synthesizer":         "<what changed and why, or null if unchanged>",
    "trade_decision":      "<what changed and why, or null if unchanged>"
  }
}"""


def _current_prompts(current_params: dict) -> dict:
    """Return active prompts: strategy override if set, else default."""
    stored = current_params.get("prompts", {})
    return {
        agent: stored.get(agent) or DEFAULT_PROMPTS[agent]
        for agent in DEFAULT_PROMPTS
    }


def _safe_prompt(new_text, current_text: str, agent_name: str, log) -> str:
    """Accept new prompt only if it passes safety checks; otherwise keep current."""
    if not new_text or not isinstance(new_text, str):
        return current_text

    stripped = new_text.strip()
    if not stripped:
        return current_text

    if len(stripped) > _MAX_PROMPT_LENGTH:
        log(f"  [safety] {agent_name} prompt rejected — too long ({len(stripped)} chars > {_MAX_PROMPT_LENGTH})")
        return current_text

    growth = len(stripped) / max(len(current_text), 1)
    if growth > _MAX_GROWTH_RATIO:
        log(f"  [safety] {agent_name} prompt rejected — grew {growth:.1f}x (limit {_MAX_GROWTH_RATIO}x)")
        return current_text

    return stripped


def run(current_strategy: Strategy, performance: dict, patterns: dict,
        session, log) -> Strategy | None:
    """Evolve strategy params and analyst prompts. Returns new Strategy or None."""
    if not performance.get("underperformed_spy"):
        log("StrategyTuner: performance meets or beats SPY — no strategy change.")
        return None

    current_params  = current_strategy.get_parameters()
    active_prompts  = _current_prompts(current_params)
    total_trades    = performance.get("total_trades", 0)
    tune_prompts    = total_trades >= _MIN_TRADES_FOR_PROMPT_TUNING

    if not tune_prompts:
        log(f"StrategyTuner: only {total_trades} trade(s) — prompt tuning requires "
            f">= {_MIN_TRADES_FOR_PROMPT_TUNING}. Tuning numeric params only.")

    context = {
        "current_strategy": {
            "name":        current_strategy.name,
            "version":     current_strategy.version,
            "description": current_strategy.description,
            "parameters":  {k: v for k, v in current_params.items() if k != "prompts"},
        },
        "prompts": active_prompts if tune_prompts else "(skipped — insufficient trade data)",
        "performance": performance,
        "patterns":    patterns,
        "tune_prompts": tune_prompts,
    }

    agent = BaseAgent(role="StrategyTuner", system_prompt=SYSTEM_PROMPT)
    log("StrategyTuner: evolving strategy and analyst prompts...")
    underperformance = (
        (performance.get("spy_equivalent_pnl") or 0) - performance.get("total_pnl", 0)
    )
    result = agent.run(
        f"The strategy underperformed SPY by ${underperformance:.2f}. "
        f"Total trades: {total_trades}. Prompt tuning enabled: {tune_prompts}. "
        "Evolve both numeric parameters and analyst prompts to improve profitability.",
        context=context,
    )

    if "error" in result or "name" not in result:
        log(f"StrategyTuner: invalid LLM response — {result}")
        return None

    # ── Validate numeric parameters ──────────────────────────────────────────
    raw_params = result.get("parameters", {})
    safe_params: dict = {
        "stop_loss_pct":             max(5.0,  min(20.0, float(raw_params.get("stop_loss_pct",             current_params.get("stop_loss_pct", 15))))),
        "profit_target_pct":         max(5.0,  min(30.0, float(raw_params.get("profit_target_pct",         current_params.get("profit_target_pct", 10))))),
        "max_positions":             max(3,    min(8,    int(raw_params.get("max_positions",               current_params.get("max_positions", 5))))),
        "confidence_threshold":      max(60,   min(90,   int(raw_params.get("confidence_threshold",        current_params.get("confidence_threshold", 70))))),
        "position_size_pct":         max(10.0, min(40.0, float(raw_params.get("position_size_pct",         current_params.get("position_size_pct", 20))))),
        "preferred_sectors":         raw_params.get("preferred_sectors", []),
        "avoid_earnings_within_days":max(0,    min(14,   int(raw_params.get("avoid_earnings_within_days",  current_params.get("avoid_earnings_within_days", 5))))),
        "entry_timing_rules":        raw_params.get("entry_timing_rules", current_params.get("entry_timing_rules", "")),
    }

    # ── Validate and apply prompt updates ────────────────────────────────────
    proposed_prompts = raw_params.get("prompts", {})
    prompt_changes   = result.get("prompt_changes_summary", {})
    final_prompts    = {}

    for agent_name, current_text in active_prompts.items():
        proposed = proposed_prompts.get(agent_name)
        if proposed and tune_prompts:
            final_prompts[agent_name] = _safe_prompt(proposed, current_text, agent_name, log)
            change_note = prompt_changes.get(agent_name)
            if final_prompts[agent_name] != current_text and change_note:
                log(f"  [prompt] {agent_name}: {change_note}")
            elif final_prompts[agent_name] == current_text:
                log(f"  [prompt] {agent_name}: kept unchanged (failed safety check)")
        else:
            final_prompts[agent_name] = current_text
            if not tune_prompts:
                log(f"  [prompt] {agent_name}: kept unchanged (insufficient data)")
            else:
                log(f"  [prompt] {agent_name}: no change proposed")

    safe_params["prompts"] = final_prompts

    # ── Deactivate old strategy ───────────────────────────────────────────────
    current_strategy.is_active = False
    current_strategy.performance_vs_spy = round(
        performance.get("total_pnl", 0) - (performance.get("spy_equivalent_pnl") or 0), 2
    )

    # ── Create new strategy ───────────────────────────────────────────────────
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

    log(f"StrategyTuner: new strategy v{new_strategy.version} — {new_strategy.name}")
    log(f"  Rationale: {result.get('rationale', '')}")
    prompt_updates = sum(1 for a in final_prompts if final_prompts[a] != active_prompts[a])
    log(f"  Prompts updated: {prompt_updates}/4 agents")
    return new_strategy
