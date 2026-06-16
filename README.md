# StockAdvisor — AI-Powered Paper Trading System

An autonomous multi-agent stock advisor that studies markets daily, paper-trades based on AI analysis, and self-improves its strategy monthly by comparing performance to SPY.

## Quick Start

### 1. Setup Environment

```bash
cp .env.example .env
# Edit .env and fill in your OPENAI_API_KEY and a JWT_SECRET
```

### 2. Initialize Database

```bash
bash scripts/init_db.sh
```

### 3. Start All Services (3 terminals)

```bash
# Terminal 1 — NestJS API
bash scripts/start_api.sh

# Terminal 2 — Vue UI
bash scripts/start_ui.sh

# Terminal 3 — Agent Scheduler (runs agents on schedule)
bash scripts/start_scheduler.sh
```

The UI opens at **http://localhost:5173**

### 4. First Login

Register at http://localhost:5173/login — the **first account** is automatically made admin.
Subsequent accounts require admin approval.

---

## Architecture

```
stockadvisor/
├── agents/          # Python AI agents (GPT-4o powered)
├── api/             # NestJS REST API
├── ui/              # Vue 3 frontend
├── artifacts/       # Generated PDF reports
├── data/            # SQLite database
└── scripts/         # Shell scripts to start services
```

## Agent Schedules

| Agent | Schedule | Purpose |
|---|---|---|
| Market Analyst | 9:30 AM CST, Mon–Fri | Finds top 5 picks with entry/exit/stop-loss |
| Paper Trader | 10 AM, 12 PM, 2:45 PM CST, Mon–Fri | Executes virtual trades |
| Retrospective | Last Sunday of month, 11 PM CST | Reviews P&L vs SPY, evolves strategy |

## Manual Triggers

```bash
bash scripts/run_market_analyst.sh
bash scripts/run_paper_trader.sh
bash scripts/run_retrospective.sh --force   # --force skips the "last Sunday" check
```

Or use the **Admin Panel → Manual Triggers** tab in the UI.

## Data Sources (Free, No API Key)

- **yfinance** — price history, fundamentals, earnings dates, VIX
- **Yahoo Finance RSS** — stock news for sentiment analysis
- **Google News RSS** — broader market news
- **Finviz** — trending stocks and top gainers
- **Reddit** (RSS) — retail sentiment from r/stocks, r/investing

## Strategy Evolution

The system starts with a seed strategy (v1). Each month, the Retrospective Analyst:
1. Calculates realized P&L vs SPY
2. If underperforming: GPT-4o rewrites the strategy text AND adjusts parameters
3. New strategy version is saved to DB; old versions preserved for history

View strategy history at **http://localhost:5173/strategies**

## Configuration (Admin Panel)

| Setting | Default | Description |
|---|---|---|
| buying_power | $5,000 | Starting capital |
| stop_loss_pct | 15% | Auto-exit if position drops this much |
| profit_target_pct | 10% | Auto-exit if position gains this much |
| max_positions | 5 | Maximum concurrent open positions |
| confidence_threshold | 70 | Minimum analyst confidence % to enter |
