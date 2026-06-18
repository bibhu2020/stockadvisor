"""TechnicalAnalystAgent — RSI, MACD, Bollinger, MA cross, volume surge + LLM interpretation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
import ta
from agents.core.base_agent import BaseAgent
from agents.core.data_fetcher import get_price_history
from agents.core import day_cache

SYSTEM_PROMPT = """You are a senior technical analyst at a quantitative hedge fund.
You receive computed technical indicators for a stock and provide a concise chart-reading
assessment that captures the full setup — not just individual signals, but how they interact.

Return ONLY valid JSON (no markdown, no preamble):
{
  "summary": "<2-3 sentences — describe the overall chart setup, cite actual RSI/MACD/SMA values, explain what the confluence of signals suggests>",
  "setup": "bullish|bearish|neutral|mixed",
  "key_signals": ["<specific signal with values, e.g. 'MACD bullish crossover at +0.42 while RSI reset from 78 to 58'>", "<signal 2>"],
  "support_level": <nearest support price as float, or null>,
  "resistance_level": <nearest resistance price as float, or null>,
  "score_adjustment": <integer -20 to +20>
}

score_adjustment rules:
  +20: very strong confluence of bullish signals the formula undervalued
  +10: setup is better than the rule-based score implies
    0: score is fair
  -10: bearish confluence the formula missed (e.g. RSI divergence, volume declining on rally)
  -20: serious technical breakdown (death cross + RSI collapsing + volume on downside)

Return ONLY valid JSON."""


def _calculate_technicals(symbol: str) -> dict:
    bars = get_price_history(symbol, period="6mo")
    if len(bars) < 30:
        return {"symbol": symbol, "error": "insufficient data", "technical_score": 0}

    df = pd.DataFrame(bars)
    df["close"] = df["close"].astype(float)
    df["high"]  = df["high"].astype(float)
    df["low"]   = df["low"].astype(float)
    df["volume"]= df["volume"].astype(float)

    df["rsi"]     = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd_obj      = ta.trend.MACD(df["close"])
    df["macd"]    = macd_obj.macd()
    df["macd_sig"]= macd_obj.macd_signal()
    bb            = ta.volatility.BollingerBands(df["close"], window=20)
    df["bb_upper"]= bb.bollinger_hband()
    df["bb_lower"]= bb.bollinger_lband()
    df["bb_mid"]  = bb.bollinger_mavg()
    df["sma50"]   = ta.trend.SMAIndicator(df["close"], window=50).sma_indicator()
    df["sma200"]  = ta.trend.SMAIndicator(df["close"], window=200).sma_indicator()
    df["vol_avg"] = df["volume"].rolling(20).mean()

    last  = df.iloc[-1]
    prev  = df.iloc[-2]
    close = float(last["close"])
    rsi   = float(last["rsi"]) if not pd.isna(last["rsi"]) else 50.0

    signals = []
    score   = 50.0

    if 40 <= rsi <= 65:
        score += 10
        signals.append(f"RSI healthy at {rsi:.1f}")
    elif rsi < 30:
        score += 5
        signals.append(f"RSI oversold at {rsi:.1f} — potential bounce")
    elif rsi > 75:
        score -= 10
        signals.append(f"RSI overbought at {rsi:.1f}")

    if not pd.isna(last["macd"]) and not pd.isna(last["macd_sig"]):
        macd_val  = float(last["macd"])
        macd_sig  = float(last["macd_sig"])
        macd_prev = float(prev["macd"])
        msig_prev = float(prev["macd_sig"])
        if macd_val > macd_sig and macd_prev <= msig_prev:
            score += 15
            signals.append(f"MACD bullish crossover (MACD {macd_val:.3f} > signal {macd_sig:.3f})")
        elif macd_val > macd_sig:
            score += 7
            signals.append(f"MACD above signal — bullish ({macd_val:.3f} vs {macd_sig:.3f})")

    if not pd.isna(last["bb_lower"]) and close > float(last["bb_mid"]):
        score += 5
        signals.append(f"Price above BB midband ({float(last['bb_mid']):.2f})")

    sma50  = float(last["sma50"])  if not pd.isna(last["sma50"])  else None
    sma200 = float(last["sma200"]) if not pd.isna(last["sma200"]) else None
    if sma50 and sma200:
        if sma50 > sma200:
            score += 8
            signals.append(f"Golden cross: SMA50 ({sma50:.2f}) > SMA200 ({sma200:.2f})")
        else:
            score -= 5
            signals.append(f"Death cross: SMA50 ({sma50:.2f}) < SMA200 ({sma200:.2f})")

    if not pd.isna(last["vol_avg"]) and float(last["volume"]) > float(last["vol_avg"]) * 1.5:
        score += 7
        signals.append("Volume surge (1.5x avg)")

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
        "symbol": symbol,
        "current_price": round(close, 4),
        "rsi": round(rsi, 2),
        "macd": round(float(last["macd"]), 4) if not pd.isna(last["macd"]) else None,
        "macd_signal": round(float(last["macd_sig"]), 4) if not pd.isna(last["macd_sig"]) else None,
        "sma50": round(sma50, 2) if sma50 else None,
        "sma200": round(sma200, 2) if sma200 else None,
        "bb_upper": round(float(last["bb_upper"]), 2) if not pd.isna(last["bb_upper"]) else None,
        "bb_lower": round(float(last["bb_lower"]), 2) if not pd.isna(last["bb_lower"]) else None,
        "bb_mid": round(float(last["bb_mid"]), 2) if not pd.isna(last["bb_mid"]) else None,
        "high_52w": round(high_52w, 2),
        "low_52w": round(low_52w, 2),
        "high_52w_date": high_date,
        "pct_from_52w_high": pct_from_high,
        "pct_from_52w_low": pct_from_low,
        "signals": signals,
        "technical_score": round(max(0.0, min(100.0, score)), 1),
    }


def _llm_analysis(agent: BaseAgent, data: dict, log) -> dict:
    """Call LLM for qualitative technical interpretation. Returns enrichment dict."""
    sym = data.get("symbol", "?")
    payload = {
        "symbol": sym,
        "current_price": data.get("current_price"),
        "rsi": data.get("rsi"),
        "macd": data.get("macd"),
        "macd_signal": data.get("macd_signal"),
        "sma50": data.get("sma50"),
        "sma200": data.get("sma200"),
        "bb_upper": data.get("bb_upper"),
        "bb_lower": data.get("bb_lower"),
        "bb_mid": data.get("bb_mid"),
        "high_52w": data.get("high_52w"),
        "low_52w": data.get("low_52w"),
        "pct_from_52w_high": data.get("pct_from_52w_high"),
        "pct_from_52w_low": data.get("pct_from_52w_low"),
        "signals": data.get("signals", []),
        "rule_based_score": data.get("technical_score"),
    }
    try:
        result = agent.run(
            f"Analyse the technical chart setup for {sym} and return structured JSON.",
            context=payload,
        )
        return {
            "technical_summary":   result.get("summary", ""),
            "technical_setup":     result.get("setup", "neutral"),
            "technical_signals":   result.get("key_signals", []),
            "support_level":       result.get("support_level"),
            "resistance_level":    result.get("resistance_level"),
            "technical_score_adj": int(result.get("score_adjustment", 0)),
        }
    except Exception as exc:
        log(f"  [LLM] technical analysis failed for {sym}: {exc}")
        return {}


def run(candidates: list[str], log) -> list[dict]:
    agent   = BaseAgent(role="TechnicalAnalyst", system_prompt=SYSTEM_PROMPT, tools=[])
    results = []

    for sym in candidates:
        key = f"technicals_{sym}"
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

        if not data.get("error"):
            log(f"TechnicalAnalyst: {sym} — running LLM analysis...")
            llm = _llm_analysis(agent, data, log)
            data.update(llm)

            adj = llm.get("technical_score_adj", 0)
            if adj:
                data["technical_score"] = round(
                    max(0.0, min(100.0, data["technical_score"] + adj)), 1
                )

            setup = data.get("technical_setup", "")
            log(
                f"TechnicalAnalyst: {sym} — RSI={data.get('rsi')} | "
                f"setup={setup} | score={data['technical_score']}"
            )

        day_cache.put(key, data)
        results.append(data)

    results.sort(key=lambda x: -x.get("technical_score", 0))
    log(f"TechnicalAnalyst: top 5 by score: {[r['symbol'] for r in results[:5]]}")
    return results
