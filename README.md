---
title: StockAdvisor
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# StockAdvisor — AI-Powered Paper Trading System

An autonomous multi-agent stock advisor that studies markets daily, paper-trades based on AI analysis, and self-improves its strategy monthly by comparing performance to SPY.

**Live demo:** [mishrabp-stockadvisor.hf.space](https://mishrabp-stockadvisor.hf.space)

## Architecture

```
stockadvisor/
├── agents/          # Python AI agents (Claude Sonnet 4.6 → GPT-4o → Gemini)
├── api/             # NestJS REST API (TypeScript + TypeORM + PostgreSQL)
├── ui/              # Vue 3 frontend
├── artifacts/       # Generated PDF reports (stored in GitHub bibhu2020/media)
└── .github/
    └── workflows/   # Agent schedules + HF deployment
```

## AI Model Chain

Agents try providers in order, falling back on missing key or error:
1. **Claude Sonnet 4.6** (Anthropic) — primary
2. **GPT-4o** (OpenAI) — fallback
3. **Gemini** (Google) — second fallback

## Agent Schedules (GitHub Actions)

| Agent | Schedule (CST) | Workflow |
|---|---|---|
| Market Analyst | 9:30 AM, Mon–Fri | `market_analyst.yml` |
| Paper Trader | 10 AM · 12 PM · 2:45 PM, Mon–Fri | `paper_trader.yml` |
| Retrospective | Last Sunday of month, 11 PM | `retrospective.yml` |

Market Analyst and Paper Trader skip runs when the US market is closed (weekends, holidays). Admins can force-trigger any agent from the Admin Panel regardless of market hours.

## Deployment

### HuggingFace Space (auto-deploy)

Every push to `main` triggers `deploy-hf.yml`, which force-pushes the repo to the HF Space git remote. HF rebuilds the Docker image automatically.

The Dockerfile is a multi-stage build:
1. Builds the Vue UI (`VITE_API_URL=/api`)
2. Builds the NestJS API
3. Runs the API on port 7860, serving the Vue build as static files

### GitHub Secrets required

| Secret | Used by |
|---|---|
| `ANTHROPIC_API_KEY` | Agent workflows |
| `OPENAI_API_KEY` | Agent workflows |
| `GEMINI_API_KEY` | Agent workflows |
| `DATABASE_URL` | Agent workflows |
| `GH_TOKEN` | Artifact uploads + workflow dispatch |
| `ARTIFACTS_PATH` | Agent workflows |
| `HF_TOKEN` | `deploy-hf.yml` |

### HuggingFace Space Secrets required

| Secret | Purpose |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL |
| `JWT_SECRET` | API token signing |
| `GITHUB_TOKEN` | Workflow dispatch from Admin UI |
| `GITHUB_REPO` | `bibhu2020/stockadvisor` |
| `ARTIFACTS_PATH` | PDF redirect URLs |

## Local Development

```bash
cp .env.example .env
# Fill in DATABASE_URL, JWT_SECRET, and at least one AI key

# Terminal 1 — NestJS API (http://localhost:3000)
bash scripts/start_api.sh

# Terminal 2 — Vue UI (http://localhost:5173)
bash scripts/start_ui.sh
```

First account registered is automatically made admin. Subsequent accounts require admin approval.

## Data Sources (free, no additional API key)

- **yfinance** — price history, fundamentals, earnings dates, VIX
- **Yahoo Finance RSS** — stock news for sentiment analysis
- **Google News RSS** — broader market news
- **Finviz** — trending stocks and top gainers

## Configuration (Admin Panel → Settings)

| Setting | Default | Description |
|---|---|---|
| `buying_power` | $5,000 | Starting capital |
| `stop_loss_pct` | 15% | Auto-exit if position drops this much |
| `profit_target_pct` | 10% | Auto-exit if position gains this much |
| `max_positions` | 5 | Maximum concurrent open positions |
| `confidence_threshold` | 70 | Minimum analyst confidence % to buy |
