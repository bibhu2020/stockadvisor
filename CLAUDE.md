# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

StockAdvisor is an autonomous AI paper-trading system. Three Python agents run on a schedule via GitHub Actions, write results to a shared PostgreSQL database (Neon.tech in production, SQLite locally), and a NestJS + Vue 3 web app lets users view reports, portfolio performance, and control agents.

## Development commands

### Full-stack dev (runs API + UI concurrently)
```bash
npm run dev          # API on :3000, UI on :5173
```

### Individual workspaces
```bash
npm run dev:api      # NestJS watch mode
npm run dev:ui       # Vite dev server
npm run build        # build both workspaces
```

### API (NestJS) — run from repo root
```bash
npm run lint --workspace=api
npm run test --workspace=api               # jest
npm run test --workspace=api -- --testPathPattern=auth   # single spec file
npm run test:e2e --workspace=api
```

### UI (Vue 3) — run from repo root
```bash
npm run lint --workspace=ui                # oxlint + eslint
```

**Important**: `@nestjs/cli` and `vite` live in `api/node_modules/` and `ui/node_modules/` respectively, not the root. The root `npm run` scripts handle this; never try to call `nest` or `vite` directly from the root shell.

### Python agents
```bash
pip install -e .                           # install agents package + deps

# Run individual agents manually (bypasses market hours check)
FORCE_RUN=true python -m agents.market_analyst.run_market_analyst manual
FORCE_RUN=true python -m agents.paper_trader.run_paper_trader manual
FORCE_RUN=true python -m agents.retrospective.run_retrospective --triggered-by manual

# DB init/seed
python -c "from agents.core.db import init_db; init_db()"
# or:
npm run init-db
```

### Environment variables (`.env` at repo root)
```
ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
DATABASE_URL          # postgresql://... for Neon; omit to use SQLite
JWT_SECRET
API_PORT              # default 3000; HuggingFace sets this to 7860
VITE_API_URL          # /api in prod, http://localhost:3000/api in dev
GITHUB_TOKEN          # PAT with actions=write for workflow dispatch + repo write for artifacts
GITHUB_REPO           # bibhu2020/stockadvisor
ARTIFACTS_PATH        # https://github.com/<owner>/<media-repo>/<path> for PDF storage
```

## Architecture

### Runtime layers

```
GitHub Actions (cron) → Python Agents → PostgreSQL (Neon) ← NestJS API ← Vue 3 UI
```

The NestJS API serves the compiled Vue SPA at `/` and all API routes under `/api`. In production both run from a single Docker container on HuggingFace Spaces (port 7860).

### Python agents (`agents/`)

Each agent pipeline is a sequential chain of sub-agents. Every run is tracked via an `agent_runs` DB row whose `log` column is appended live so NestJS can stream it to the UI via SSE polling.

**`agents/core/`** — shared infrastructure:
- `base_agent.py` — `BaseAgent` class with LLM fallback chain: Anthropic (`claude-sonnet-4-6`) → OpenAI (`gpt-4o`) → Gemini (`gemini-2.0-flash`). Each provider uses tool-use loops (up to 10 rounds). Anthropic uses its native SDK; GPT-4o and Gemini share the OpenAI-compatible `_run_openai()` path.
- `orchestrator.py` — `AgentOrchestrator` context manager: creates `agent_runs` row on `__enter__`, flushes each log line to DB immediately, marks run completed/failed on `__exit__`.
- `db.py` — SQLAlchemy models + `SessionLocal` factory. Auto-detects `DATABASE_URL` for Postgres vs SQLite fallback. TypeORM (in `api/`) uses the same schema via separate entity files.
- `data_fetcher.py` — all market data: yfinance (primary) → Stooq CSV → Google Finance scrape for price; Yahoo/Google News RSS for sentiment; Finviz + Yahoo trending + Reddit RSS for candidates.
- `day_cache.py` — JSON file cache at `data/cache/YYYY-MM-DD.json`. Expensive fetches (fundamentals, technicals, sentiment) are cached per calendar day so re-runs within a day are fast and deterministic.
- `github_storage.py` — stores PDF artifacts to a GitHub repo via the Contents API (parsed from `ARTIFACTS_PATH` env var).
- `market_hours.py` — checks NYSE hours (America/New_York). Set `FORCE_RUN=true` to bypass.

**Market Analyst pipeline** (`agents/market_analyst/`):
1. `trend_spotter.py` — collects up to `MAX_CANDIDATES=20` tickers from Yahoo trending, Finviz, Reddit RSS; filters with `NOISE` set and `_valid_ticker()`.
2. `fundamental_analyst.py` — yfinance fundamentals; skips tickers with no price across all 3 sources.
3. `technical_analyst.py` — RSI, MACD, Bollinger, MA crossovers via `ta` library.
4. `sentiment_analyst.py` — LLM scores headlines from Yahoo + Google News RSS.
5. `volatility_analyst.py` — VIX, beta, sector volatility.
6. `synthesizer.py` — LLM call combining all sub-agent outputs + active strategy → top picks JSON.

**Paper Trader** (`agents/paper_trader/`): `position_monitor.py` checks stop-loss/profit-target/expiry → `trade_decision.py` (LLM) decides new buys → `trade_executor.py` writes positions/transactions/snapshots.

**Retrospective** (`agents/retrospective/`): `performance_calculator.py` → `pattern_analyzer.py` (LLM) → `strategy_tuner.py` (LLM, only if P&L < SPY) → `report_generator.py`. Strategy tuner inserts a new `strategies` row and sets it active.

### NestJS API (`api/src/`)

All routes are prefixed `/api`. Entities live in `api/src/common/entities/`; each module follows the standard NestJS pattern (module / controller / service). TypeORM uses `synchronize: false` — schema changes must be done via migrations or by running `init_db()` from the Python side first.

- **Auth**: JWT access + refresh tokens, bcrypt passwords. Role enum: `admin | guest | pending`. Users self-register (role=pending), admin approves via PATCH.
- **`agent-runs`**: `GET /agent-runs/:id/stream` polls DB every 500 ms and sends new log bytes as SSE. `POST /agent-runs/trigger/:type` dispatches a GitHub Actions workflow via the GitHub REST API (requires `GITHUB_TOKEN` with `actions=write`).
- **Database**: `app.module.ts` detects Postgres vs SQLite the same way `db.py` does; strips `channel_binding` from Neon connection strings (psycopg2 doesn't support it).

### Vue 3 UI (`ui/src/`)

- `ui/src/api/index.ts` — single axios instance; `VITE_API_URL` sets base URL; attaches JWT from `localStorage`; 401 on non-auth routes redirects to `/login`.
- `ui/src/stores/auth.ts` — Pinia store; `router/index.ts` calls `auth.fetchMe()` on every navigation and guards `meta.admin` routes.
- Views: Dashboard, Transactions, Reports, Strategies, Admin (agent runs + user management + settings + manual triggers), Profile.

### Deployment (HuggingFace Spaces)

Docker is a 4-stage build: `deps` (npm ci with native build tools) → `ui-builder` (Vite) → `api-builder` (nest build) → production image. Each stage explicitly copies workspace-level `node_modules` from `deps` because npm workspaces don't hoist `@nestjs/cli` or `vite` to the root.

SPA routing is handled by Express middleware registered in `main.ts` **before** `app.listen()` (which internally calls `app.init()`). It serves `ui/dist/index.html` for any request that doesn't start with `/api`. `ServeStaticModule` is intentionally absent — it is incompatible with Express 5 / path-to-regexp v8.

Push to `main` triggers `deploy-hf.yml` which force-pushes to the HuggingFace git remote. A `keepalive.yml` workflow pings the Space every 35 minutes to prevent it from sleeping.

### GitHub Actions secrets required (for agents to work)
`DATABASE_URL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GH_TOKEN` (PAT with `actions=write` + repo write), `ARTIFACTS_PATH`, `HF_TOKEN` (for deploy).
