"""TechnicalAnalystAgent — RSI, MACD, Bollinger, MA cross, volume surge."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
import ta
from agents.core.data_fetcher import get_price_history
from agents.core import day_cache


def _calculate_technicals(symbol: str) -> dict:
    bars = get_price_history(symbol, period="6mo")
    if len(bars) < 30:
        return {"symbol": symbol, "error": "insufficient data", "technical_score": 0}

    df = pd.DataFrame(bars)
    df["close"] = df["close"].astype(float)
    df["high"]  = df["high"].astype(float)
    df["low"]   = df["low"].astype(float)
    df["volume"]= df["volume"].astype(float)

    # Indicators via `ta` library
    df["rsi"]    = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd_obj     = ta.trend.MACD(df["close"])
    df["macd"]   = macd_obj.macd()
    df["macd_sig"]= macd_obj.macd_signal()
    bb           = ta.volatility.BollingerBands(df["close"], window=20)
    df["bb_upper"]= bb.bollinger_hband()
    df["bb_lower"]= bb.bollinger_lband()
    df["bb_mid"]  = bb.bollinger_mavg()
    df["sma50"]   = ta.trend.SMAIndicator(df["close"], window=50).sma_indicator()
    df["sma200"]  = ta.trend.SMAIndicator(df["close"], window=200).sma_indicator()
    df["vol_avg"] = df["volume"].rolling(20).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = float(last["close"])
    rsi   = float(last["rsi"]) if not pd.isna(last["rsi"]) else 50.0

    signals = []
    score = 50.0

    # RSI signal
    if 40 <= rsi <= 65:
        score += 10
        signals.append(f"RSI healthy at {rsi:.1f}")
    elif rsi < 30:
        score += 5
        signals.append(f"RSI oversold at {rsi:.1f} — potential bounce")
    elif rsi > 75:
        score -= 10
        signals.append(f"RSI overbought at {rsi:.1f}")

    # MACD bullish crossover
    if not pd.isna(last["macd"]) and not pd.isna(last["macd_sig"]):
        macd_bullish = float(last["macd"]) > float(last["macd_sig"]) and float(prev["macd"]) <= float(prev["macd_sig"])
        if macd_bullish:
            score += 15
            signals.append("MACD bullish crossover")
        elif float(last["macd"]) > float(last["macd_sig"]):
            score += 7
            signals.append("MACD above signal (bullish)")

    # Price vs Bollinger
    if not pd.isna(last["bb_lower"]) and close > float(last["bb_mid"]):
        score += 5
        signals.append("Price above Bollinger midband")

    # 50/200 MA golden cross
    if not pd.isna(last["sma50"]) and not pd.isna(last["sma200"]):
        if float(last["sma50"]) > float(last["sma200"]):
            score += 8
            signals.append("Golden cross: SMA50 > SMA200")
        else:
            score -= 5
            signals.append("Death cross: SMA50 < SMA200")

    # Volume surge
    if not pd.isna(last["vol_avg"]) and float(last["volume"]) > float(last["vol_avg"]) * 1.5:
        score += 7
        signals.append("Volume surge (1.5x avg)")

    # 52-week high/low proximity
    high_52w = float(df["high"].max())
    low_52w  = float(df["low"].min())
    pct_from_high = round((close - high_52w) / high_52w * 100, 1) if high_52w > 0 else None
    pct_from_low  = round((close - low_52w)  / low_52w  * 100, 1) if low_52w  > 0 else None

    # Date of 52-week high (bars list has a "date" column)
    try:
        high_pos = int(df["high"].idxmax())
        high_date = bars[high_pos]["date"] if 0 <= high_pos < len(bars) else None
    except Exception:
        high_date = None

    return {
        "symbol": symbol,
        "current_price": round(close, 4),
        "rsi": round(rsi, 2),
        "macd": round(float(last["macd"]), 4) if not pd.isna(last["macd"]) else None,
        "sma50": round(float(last["sma50"]), 2) if not pd.isna(last["sma50"]) else None,
        "sma200": round(float(last["sma200"]), 2) if not pd.isna(last["sma200"]) else None,
        "bb_upper": round(float(last["bb_upper"]), 2) if not pd.isna(last["bb_upper"]) else None,
        "bb_lower": round(float(last["bb_lower"]), 2) if not pd.isna(last["bb_lower"]) else None,
        "high_52w": round(high_52w, 2),
        "low_52w": round(low_52w, 2),
        "high_52w_date": high_date,
        "pct_from_52w_high": pct_from_high,
        "pct_from_52w_low": pct_from_low,
        "signals": signals,
        "technical_score": round(max(0.0, min(100.0, score)), 1),
    }


def run(candidates: list[str], log) -> list[dict]:
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
        day_cache.put(key, data)
        results.append(data)

    results.sort(key=lambda x: -x.get("technical_score", 0))
    log(f"TechnicalAnalyst: top 5: {[r['symbol'] for r in results[:5]]}")
    return results
