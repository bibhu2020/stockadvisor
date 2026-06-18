"""TechnicalAnalystAgent — indicators + rule-based score + one batch LLM call for all tickers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
import ta
from agents.core.base_agent import BaseAgent
from agents.core.data_fetcher import get_price_history
from agents.core import day_cache

SYSTEM_PROMPT = """You are a senior technical analyst at a quantitative hedge fund.
You receive computed technical indicators for multiple stocks simultaneously and provide
chart-reading assessments for each — focusing on how signals interact, not just individual
readings. Look for confluence, divergence, and what the setup implies for the next 30 days.

OBJECTIVE: Identify stocks showing RELATIVE STRENGTH versus the broad market. A stock that
merely tracks SPY provides no alpha. Prioritise setups where the stock is outperforming or
building momentum independent of SPY moves.

BULLISH SIGNALS (score up):
- Price above SMA50 AND SMA200 (trend intact); SMA50 > SMA200 (golden cross)
- RSI in the 50-70 range with upward slope — momentum without being overbought
- MACD bullish crossover (MACD line crossing above signal line)
- Price breaking above prior resistance on above-average volume (conviction breakout)
- Stock holding or making new highs while broader market pulls back (relative strength)

BEARISH SIGNALS (score down):
- Price below SMA200 — stock is in a structural downtrend
- Death cross (SMA50 < SMA200) with no recovery catalyst
- RSI < 40 or RSI divergence (price making new highs, RSI falling)
- High-volume rejection at resistance; low-volume rallies (no conviction)
- Stock declining more than SPY on down days (relative weakness, negative beta-adjusted return)

Return ONLY valid JSON (no markdown, no preamble):
{
  "analyses": [
    {
      "symbol": "TICKER",
      "summary": "<2-3 sentences — describe the overall chart setup, cite actual RSI/MACD/SMA values, explain what the confluence implies>",
      "setup": "bullish|bearish|neutral|mixed",
      "key_signals": ["<specific signal with values, e.g. 'MACD bullish crossover at +0.42 with RSI resetting from 78 to 58'>", "<signal 2>"],
      "support_level": <nearest support price as float, or null>,
      "resistance_level": <nearest resistance price as float, or null>,
      "score_adjustment": <integer -20 to +20>
    }
  ]
}

Analyse EVERY ticker in the input. score_adjustment:
  +20 very strong bullish confluence with clear relative strength vs SPY
  +10 setup is better than the rule-based score implies
   0  score is fair
  -10 bearish signals the formula missed (e.g. RSI divergence, fading volume on rally)
  -20 serious technical breakdown (death cross + RSI collapsing + high downside volume)

Return ONLY valid JSON."""


def _calculate_technicals(symbol: str) -> dict:
    bars = get_price_history(symbol, period="6mo")
    if len(bars) < 30:
        return {"symbol": symbol, "error": "insufficient data", "technical_score": 0}

    df = pd.DataFrame(bars)
    df["close"]  = df["close"].astype(float)
    df["high"]   = df["high"].astype(float)
    df["low"]    = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)

    df["rsi"]      = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd_obj       = ta.trend.MACD(df["close"])
    df["macd"]     = macd_obj.macd()
    df["macd_sig"] = macd_obj.macd_signal()
    bb             = ta.volatility.BollingerBands(df["close"], window=20)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_mid"]   = bb.bollinger_mavg()
    df["sma50"]    = ta.trend.SMAIndicator(df["close"], window=50).sma_indicator()
    df["sma200"]   = ta.trend.SMAIndicator(df["close"], window=200).sma_indicator()
    df["vol_avg"]  = df["volume"].rolling(20).mean()

    last  = df.iloc[-1]
    prev  = df.iloc[-2]
    close = float(last["close"])
    rsi   = float(last["rsi"]) if not pd.isna(last["rsi"]) else 50.0

    signals = []
    score   = 50.0

    if 40 <= rsi <= 65:
        score += 10; signals.append(f"RSI healthy at {rsi:.1f}")
    elif rsi < 30:
        score += 5;  signals.append(f"RSI oversold at {rsi:.1f} — potential bounce")
    elif rsi > 75:
        score -= 10; signals.append(f"RSI overbought at {rsi:.1f}")

    if not pd.isna(last["macd"]) and not pd.isna(last["macd_sig"]):
        mv, ms = float(last["macd"]), float(last["macd_sig"])
        pv, ps = float(prev["macd"]), float(prev["macd_sig"])
        if mv > ms and pv <= ps:
            score += 15; signals.append(f"MACD bullish crossover ({mv:.3f} > {ms:.3f})")
        elif mv > ms:
            score += 7;  signals.append(f"MACD above signal — bullish ({mv:.3f} vs {ms:.3f})")

    if not pd.isna(last["bb_lower"]) and close > float(last["bb_mid"]):
        score += 5; signals.append(f"Price above BB midband ({float(last['bb_mid']):.2f})")

    sma50  = float(last["sma50"])  if not pd.isna(last["sma50"])  else None
    sma200 = float(last["sma200"]) if not pd.isna(last["sma200"]) else None
    if sma50 and sma200:
        if sma50 > sma200:
            score += 8; signals.append(f"Golden cross: SMA50 ({sma50:.2f}) > SMA200 ({sma200:.2f})")
        else:
            score -= 5; signals.append(f"Death cross: SMA50 ({sma50:.2f}) < SMA200 ({sma200:.2f})")

    if not pd.isna(last["vol_avg"]) and float(last["volume"]) > float(last["vol_avg"]) * 1.5:
        score += 7; signals.append("Volume surge (1.5x avg)")

    high_52w = float(df["high"].max())
    low_52w  = float(df["low"].min())
    pct_from_high = round((close - high_52w) / high_52w * 100, 1) if high_52w > 0 else None
    pct_from_low  = round((close - low_52w)  / low_52w  * 100, 1) if low_52w  > 0 else None

    try:
        high_pos  = int(df["high"].idxmax())
        high_date = bars[high_pos]["date"] if 0 <= high_pos < len(bars) else None
    except Exception:
        high_date = None

    return {
        "symbol":           symbol,
        "current_price":    round(close, 4),
        "rsi":              round(rsi, 2),
        "macd":             round(float(last["macd"]), 4)    if not pd.isna(last["macd"])     else None,
        "macd_signal":      round(float(last["macd_sig"]), 4) if not pd.isna(last["macd_sig"]) else None,
        "sma50":            round(sma50, 2)  if sma50  else None,
        "sma200":           round(sma200, 2) if sma200 else None,
        "bb_upper":         round(float(last["bb_upper"]), 2) if not pd.isna(last["bb_upper"]) else None,
        "bb_lower":         round(float(last["bb_lower"]), 2) if not pd.isna(last["bb_lower"]) else None,
        "bb_mid":           round(float(last["bb_mid"]),   2) if not pd.isna(last["bb_mid"])   else None,
        "high_52w":         round(high_52w, 2),
        "low_52w":          round(low_52w, 2),
        "high_52w_date":    high_date,
        "pct_from_52w_high": pct_from_high,
        "pct_from_52w_low":  pct_from_low,
        "signals":          signals,
        "technical_score":  round(max(0.0, min(100.0, score)), 1),
    }


def _batch_llm_analysis(agent: BaseAgent, items: list[dict], log) -> None:
    """One LLM call for all items. Enriches dicts in-place and updates cache."""
    payload = [
        {
            "symbol":            d["symbol"],
            "current_price":     d.get("current_price"),
            "rsi":               d.get("rsi"),
            "macd":              d.get("macd"),
            "macd_signal":       d.get("macd_signal"),
            "sma50":             d.get("sma50"),
            "sma200":            d.get("sma200"),
            "bb_upper":          d.get("bb_upper"),
            "bb_lower":          d.get("bb_lower"),
            "bb_mid":            d.get("bb_mid"),
            "high_52w":          d.get("high_52w"),
            "low_52w":           d.get("low_52w"),
            "pct_from_52w_high": d.get("pct_from_52w_high"),
            "pct_from_52w_low":  d.get("pct_from_52w_low"),
            "signals":           d.get("signals", []),
            "rule_based_score":  d.get("technical_score"),
        }
        for d in items
    ]

    try:
        result = agent.run(
            f"Perform technical analysis for all {len(items)} stocks in the context.",
            context={"stocks": payload},
        )
        analyses = {a["symbol"]: a for a in result.get("analyses", [])}
    except Exception as exc:
        log(f"TechnicalAnalyst: batch LLM call failed ({exc})")
        analyses = {}

    for d in items:
        sym = d["symbol"]
        a   = analyses.get(sym, {})
        d["technical_summary"]   = a.get("summary", "")
        d["technical_setup"]     = a.get("setup", "neutral")
        d["technical_signals"]   = a.get("key_signals", d.get("signals", []))
        d["support_level"]       = a.get("support_level")
        d["resistance_level"]    = a.get("resistance_level")
        adj = int(a.get("score_adjustment", 0))
        if adj:
            d["technical_score"] = round(max(0.0, min(100.0, d["technical_score"] + adj)), 1)
        day_cache.put(f"technicals_{sym}", d)


def get_prompt(strategy_params: dict) -> str:
    return strategy_params.get("prompts", {}).get("technical_analyst") or SYSTEM_PROMPT


def run(candidates: list[str], log, strategy_params: dict | None = None) -> list[dict]:
    agent     = BaseAgent(role="TechnicalAnalyst", system_prompt=get_prompt(strategy_params or {}), tools=[])
    results   = []
    needs_llm = []

    for sym in candidates:
        key    = f"technicals_{sym}"
        cached = day_cache.get(key)
        if cached:
            log(f"[cache] HIT  {key}")
            results.append(cached)
            continue

        log(f"TechnicalAnalyst: analyzing {sym}...")
        try:
            data = _calculate_technicals(sym)
        except Exception as e:
            data = {"symbol": sym, "error": str(e), "technical_score": 0}

        results.append(data)
        if not data.get("error"):
            log(f"  {sym} — RSI={data.get('rsi')} | signals={data.get('signals', [])} | rule score={data['technical_score']}")
            needs_llm.append(data)

    # One batch LLM call for all non-cached tickers
    if needs_llm:
        syms = [d["symbol"] for d in needs_llm]
        log(f"TechnicalAnalyst: batch LLM analysis for {syms}...")
        _batch_llm_analysis(agent, needs_llm, log)
        for d in needs_llm:
            log(f"  {d['symbol']} setup={d.get('technical_setup')} score={d['technical_score']}")

    results.sort(key=lambda x: -x.get("technical_score", 0))
    log(f"TechnicalAnalyst: ranked — {[r['symbol'] for r in results[:10]]}")
    return results
