"""Market data fetchers: yfinance, RSS news, Finviz trending."""
import time
import random
import re
from datetime import datetime, date, timedelta

import feedparser
import requests
import yfinance as yf
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _sleep():
    time.sleep(random.uniform(1.0, 2.0))


# ── Price & Fundamentals ──────────────────────────────────────────────────────

def get_current_price(symbol: str) -> float | None:
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.fast_info
        price = getattr(data, "last_price", None)
        if price and price > 0:
            return round(float(price), 4)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 4)
    except Exception:
        pass
    return None


def get_price_history(symbol: str, period: str = "3mo") -> list[dict]:
    """Return OHLCV list [{date, open, high, low, close, volume}]."""
    try:
        hist = yf.Ticker(symbol).history(period=period)
        records = []
        for idx, row in hist.iterrows():
            records.append({
                "date": str(idx.date()),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })
        return records
    except Exception:
        return []


def get_fundamentals(symbol: str) -> dict:
    """Return rich fundamental + analyst data for a symbol."""
    try:
        t = yf.Ticker(symbol)
        info = t.info

        # ── Earnings date ─────────────────────────────────────────────────────
        earnings_date = None
        earnings_days_away = None
        try:
            cal = t.calendar
            if cal is not None and not cal.empty:
                ed = cal.loc["Earnings Date"].iloc[0] if "Earnings Date" in cal.index else None
                if ed is not None:
                    ed_date = ed.date() if hasattr(ed, "date") else None
                    if ed_date:
                        earnings_date = str(ed_date)
                        earnings_days_away = (ed_date - date.today()).days
        except Exception:
            pass

        # ── Recent EPS history (actuals vs estimates) ─────────────────────────
        eps_actual = None
        eps_estimate = None
        eps_surprise_pct = None
        recent_earnings_history = []     # list of up to 4 quarters
        next_earnings_date = None        # from earnings_dates (future row)
        try:
            ed_df = t.earnings_dates
            if ed_df is not None and not ed_df.empty:
                now_tz = datetime.now(ed_df.index.tz)
                past   = ed_df[ed_df.index <= now_tz].sort_index(ascending=False)
                future = ed_df[ed_df.index  > now_tz].sort_index(ascending=True)
                # Most recent reported EPS
                if not past.empty:
                    row = past.iloc[0]
                    eps_actual   = row.get("Reported EPS")
                    eps_estimate = row.get("EPS Estimate")
                    if eps_actual is not None and not (eps_actual != eps_actual):  # nan check
                        eps_actual = float(eps_actual)
                        eps_estimate = float(eps_estimate) if eps_estimate and eps_estimate == eps_estimate else None
                        if eps_estimate and eps_estimate != 0:
                            eps_surprise_pct = round((eps_actual - eps_estimate) / abs(eps_estimate) * 100, 1)
                    else:
                        eps_actual = None
                # Up to 4 quarters of history
                for i, (idx, row) in enumerate(past.head(4).iterrows()):
                    act = row.get("Reported EPS")
                    est = row.get("EPS Estimate")
                    surp = row.get("Surprise(%)")
                    if act and act == act:   # not nan
                        recent_earnings_history.append({
                            "date": str(idx.date()),
                            "eps_actual": round(float(act), 2),
                            "eps_estimate": round(float(est), 2) if est and est == est else None,
                            "surprise_pct": round(float(surp), 1) if surp and surp == surp else None,
                        })
                # Next earnings date from future rows
                if not future.empty and earnings_date is None:
                    next_dt = future.index[0]
                    next_earnings_date = str(next_dt.date())
                    if earnings_date is None:
                        earnings_date = next_earnings_date
                        if earnings_days_away is None:
                            earnings_days_away = (next_dt.date() - date.today()).days
        except Exception:
            pass

        # ── Analyst upgrades / downgrades (most recent 5) ────────────────────
        recent_analyst_actions = []
        analyst_upgrades = None
        try:
            ud = t.upgrades_downgrades
            if ud is not None and not ud.empty:
                # Most recent 5 actions
                for idx, row in ud.head(5).iterrows():
                    action_date = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
                    pt_cur  = row.get("currentPriceTarget")
                    pt_prev = row.get("priorPriceTarget")
                    recent_analyst_actions.append({
                        "date": action_date,
                        "firm": row.get("Firm", ""),
                        "to_grade": row.get("ToGrade", ""),
                        "from_grade": row.get("FromGrade", ""),
                        "action": row.get("Action", ""),
                        "price_target": float(pt_cur) if pt_cur and pt_cur == pt_cur else None,
                        "prior_target": float(pt_prev) if pt_prev and pt_prev == pt_prev else None,
                    })
        except Exception:
            pass

        # Analyst upgrade count from recommendations summary
        try:
            rec = t.recommendations
            if rec is not None and not rec.empty and "period" in rec.columns:
                cur = rec[rec["period"] == "0m"]
                if cur.empty:
                    cur = rec.head(1)
                if not cur.empty:
                    row = cur.iloc[0]
                    analyst_upgrades = int(row.get("strongBuy", 0) + row.get("buy", 0))
        except Exception:
            pass

        # ── YTD return ───────────────────────────────────────────────────────
        ytd_return_pct = None
        try:
            start_of_year = date(date.today().year, 1, 1)
            hist_ytd = t.history(start=str(start_of_year))
            if not hist_ytd.empty and len(hist_ytd) >= 2:
                ytd_start = float(hist_ytd["Close"].iloc[0])
                ytd_end   = float(hist_ytd["Close"].iloc[-1])
                if ytd_start > 0:
                    ytd_return_pct = round((ytd_end - ytd_start) / ytd_start * 100, 1)
        except Exception:
            pass

        # ── Analyst consensus ─────────────────────────────────────────────────
        analyst_target      = info.get("targetMeanPrice")
        analyst_high_target = info.get("targetHighPrice")
        analyst_low_target  = info.get("targetLowPrice")
        analyst_rating      = info.get("recommendationKey", "")   # 'buy', 'hold', 'strong_buy'
        analyst_count       = info.get("numberOfAnalystOpinions")

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not current_price:
            current_price = get_current_price(symbol)

        return {
            "symbol": symbol,
            "current_price": round(float(current_price), 4) if current_price else None,
            "company": info.get("longName", symbol),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "price_to_book": info.get("priceToBook"),
            "eps": info.get("trailingEps"),
            "eps_growth": info.get("earningsQuarterlyGrowth"),
            "eps_actual": float(eps_actual) if eps_actual is not None else None,
            "eps_estimate": float(eps_estimate) if eps_estimate is not None else None,
            "eps_surprise_pct": eps_surprise_pct,
            "revenue_growth": info.get("revenueGrowth"),
            "gross_margin": info.get("grossMargins"),
            "operating_margin": info.get("operatingMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "free_cash_flow": info.get("freeCashflow"),
            "roe": info.get("returnOnEquity"),
            "profit_margin": info.get("profitMargins"),
            "beta": info.get("beta"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
            "earnings_date": earnings_date,
            "earnings_days_away": earnings_days_away,
            "recent_earnings_history": recent_earnings_history,
            "ytd_return_pct": ytd_return_pct,
            "analyst_target": analyst_target,
            "analyst_high_target": analyst_high_target,
            "analyst_low_target": analyst_low_target,
            "analyst_rating": analyst_rating,
            "analyst_count": analyst_count,
            "analyst_upgrades": analyst_upgrades,
            "recent_analyst_actions": recent_analyst_actions,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def get_vix() -> float | None:
    """Fetch current VIX level."""
    try:
        hist = yf.Ticker("^VIX").history(period="2d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        pass
    return None


def is_market_open() -> bool:
    """Check if US market is currently open."""
    try:
        info = yf.Ticker("SPY").fast_info
        state = getattr(info, "market_state", None)
        return state == "REGULAR"
    except Exception:
        return False


def get_spy_monthly_return(year: int, month: int) -> float | None:
    """Calculate SPY return for a given month."""
    try:
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        hist = yf.Ticker("^SPY").history(start=start, end=end)
        if len(hist) < 2:
            return None
        first = float(hist["Close"].iloc[0])
        last = float(hist["Close"].iloc[-1])
        return round((last - first) / first * 100, 2)
    except Exception:
        return None


# ── Trending Stocks ───────────────────────────────────────────────────────────

def get_yahoo_trending() -> list[str]:
    """Scrape Yahoo Finance trending tickers."""
    try:
        url = "https://finance.yahoo.com/trending-tickers/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        tickers = []
        for a in soup.select("a[data-testid='quoteLink'], a[href*='/quote/']"):
            href = a.get("href", "")
            m = re.search(r"/quote/([A-Z]{1,5})(?:/|$|\?)", href)
            if m:
                tickers.append(m.group(1))
        return list(dict.fromkeys(tickers))[:30]
    except Exception:
        return []


def scrape_finviz_trending() -> list[str]:
    """Scrape Finviz most active / top gainers."""
    tickers = []
    for url in [
        "https://finviz.com/screener.ashx?v=110&s=ta_topgainers",
        "https://finviz.com/screener.ashx?v=110&o=-volume",
    ]:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.select("a.screener-link-primary"):
                text = a.get_text(strip=True)
                if text.isupper() and 1 <= len(text) <= 5:
                    tickers.append(text)
            _sleep()
        except Exception:
            pass
    return list(dict.fromkeys(tickers))[:20]


def get_reddit_hot_tickers() -> list[str]:
    """Extract ticker mentions from Reddit finance subs via RSS."""
    subreddits = ["stocks", "investing", "StockMarket"]
    tickers: dict[str, int] = {}
    ticker_re = re.compile(r"\b([A-Z]{1,5})\b")
    # Common false positives to ignore
    ignore = {"I", "A", "AI", "IT", "BE", "GO", "AT", "US", "IS", "AS", "OR",
               "FOR", "THE", "AND", "ETF", "IPO", "SEC", "CEO", "CFO", "CTO"}
    for sub in subreddits:
        try:
            feed = feedparser.parse(f"https://www.reddit.com/r/{sub}/hot.rss")
            for entry in feed.entries[:25]:
                text = entry.get("title", "") + " " + entry.get("summary", "")
                for match in ticker_re.findall(text):
                    if match not in ignore and len(match) >= 2:
                        tickers[match] = tickers.get(match, 0) + 1
            _sleep()
        except Exception:
            pass
    return [t for t, _ in sorted(tickers.items(), key=lambda x: -x[1])][:20]


# ── News & Sentiment ──────────────────────────────────────────────────────────

def fetch_yahoo_news(symbol: str, max_items: int = 10) -> list[dict]:
    """Fetch recent news headlines from Yahoo Finance RSS."""
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:max_items]:
            items.append({
                "title": e.get("title", ""),
                "summary": e.get("summary", "")[:300],
                "published": e.get("published", ""),
                "source": "yahoo",
            })
        return items
    except Exception:
        return []


def fetch_google_news(symbol: str, company: str = "", max_items: int = 10) -> list[dict]:
    """Fetch recent news from Google News RSS."""
    query = f"{symbol} {company} stock".strip()
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:max_items]:
            items.append({
                "title": e.get("title", ""),
                "summary": e.get("summary", "")[:300],
                "published": e.get("published", ""),
                "source": "google",
            })
        return items
    except Exception:
        return []


def fetch_all_news(symbol: str, company: str = "") -> list[dict]:
    yahoo = fetch_yahoo_news(symbol)
    _sleep()
    google = fetch_google_news(symbol, company)
    return yahoo + google


# ── Web Search (Yahoo Finance API → DuckDuckGo HTML fallback) ─────────────────

def _yahoo_finance_news_search(query: str, max_results: int) -> list[dict]:
    """Yahoo Finance's own search API — returns news article titles (no snippets)."""
    try:
        url = (
            "https://query1.finance.yahoo.com/v1/finance/search"
            f"?q={requests.utils.quote(query)}&quotesCount=0&newsCount={max_results}"
        )
        resp = requests.get(url, headers=HEADERS, timeout=12)
        data = resp.json()
        results = []
        for n in data.get("news", [])[:max_results]:
            title = n.get("title", "")
            if title:
                results.append({"title": title, "snippet": n.get("summary", ""), "url": n.get("link", "")})
        return results
    except Exception:
        return []


def _duckduckgo_search(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo HTML search — returns rich title + snippet pairs."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        for item in soup.select(".result")[:max_results]:
            title_el  = item.select_one(".result__title")
            snip_el   = item.select_one(".result__snippet")
            url_el    = item.select_one("a.result__url")
            title   = title_el.get_text(" ", strip=True) if title_el else ""
            snippet = snip_el.get_text(" ", strip=True)  if snip_el  else ""
            href    = url_el.get("href", "")             if url_el   else ""
            if title or snippet:
                results.append({"title": title, "snippet": snippet, "url": href})
        return results
    except Exception:
        return []


def yahoo_web_search(query: str, max_results: int = 6) -> list[dict]:
    """
    Search the web for financial data and return [{title, snippet, url}].

    Strategy:
    1. Yahoo Finance news API  — fast, finance-focused (but often returns generic news)
    2. DuckDuckGo HTML search  — richer snippets with specific numbers; used when Yahoo
       results don't contain keywords from the query

    Never raises — returns [] on complete failure.
    """
    # Extract key terms from query to judge relevance (symbol, year, finance words)
    query_terms = set(re.findall(r"\b[A-Z]{2,5}\b|\b\d{4}\b|\bearnings\b|\bEPS\b|\banalyst\b|\btarget\b", query))

    yf_results = _yahoo_finance_news_search(query, max_results)
    relevant = [
        r for r in yf_results
        if any(t.lower() in (r["title"] + r["snippet"]).lower() for t in query_terms if len(t) >= 3)
    ]
    if len(relevant) >= 3:
        return relevant[:max_results]

    # Yahoo Finance results weren't relevant — use DuckDuckGo for richer data
    return _duckduckgo_search(query, max_results)


def get_web_enrichment(symbol: str, company: str) -> dict:
    """
    Run targeted web searches for data that yfinance often misses:
    earnings beats vs estimates, analyst upgrades with price targets, corporate actions.
    Results are passed as raw text snippets into the synthesizer context.
    """
    year = date.today().year
    queries = [
        f"{symbol} {company} earnings EPS beat estimate analyst price target {year}",
        f"{symbol} stock analyst upgrade downgrade price target {year}",
        f"{symbol} stock split buyback dividend corporate action {year}",
    ]
    all_snippets = []
    for q in queries:
        hits = yahoo_web_search(q, max_results=4)
        for r in hits:
            parts = [r["title"], r["snippet"]]
            text = " — ".join(p for p in parts if p).strip(" —")
            if len(text) > 30:
                all_snippets.append(text)
        time.sleep(random.uniform(1.0, 1.8))

    # Deduplicate on first 60 chars
    seen, unique = set(), []
    for s in all_snippets:
        key = re.sub(r"\s+", " ", s[:60]).lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return {
        "web_snippets": unique[:18],
        "web_queries": queries,
    }
