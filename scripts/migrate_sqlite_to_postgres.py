#!/usr/bin/env python3
"""
Migrate all data from SQLite → PostgreSQL (Neon.tech).

Usage:  python3 scripts/migrate_sqlite_to_postgres.py
Reads:  data/stockadvisor.db  (SQLite source)
Writes: DATABASE_URL env var   (PostgreSQL target)
"""
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parents[1]
env_path = ROOT / ".env"
for line in env_path.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SQLITE_PATH  = os.environ.get("DB_PATH", str(ROOT / "data" / "stockadvisor.db"))

if not DATABASE_URL or not DATABASE_URL.startswith("postgresql"):
    print("ERROR: DATABASE_URL not set or not a PostgreSQL URL")
    sys.exit(1)

import psycopg2
from psycopg2.extras import execute_values

# ── Connect ───────────────────────────────────────────────────────────────────
print(f"Source : {SQLITE_PATH}")
print(f"Target : {DATABASE_URL[:60]}...")

sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

# Strip channel_binding from URL if psycopg2 doesn't support it
pg_url = DATABASE_URL.replace("&channel_binding=require", "").replace("?channel_binding=require&", "?")
pg_conn = psycopg2.connect(pg_url)
pg_conn.autocommit = False
cur = pg_conn.cursor()

print("\nConnections established.\n")

# ── Create schema in PostgreSQL ───────────────────────────────────────────────
print("Creating schema...")
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT DEFAULT 'pending',
    approved_at   TIMESTAMP,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strategies (
    id                  SERIAL PRIMARY KEY,
    version             INTEGER NOT NULL,
    name                TEXT NOT NULL,
    description         TEXT NOT NULL,
    parameters          TEXT NOT NULL,
    is_active           BOOLEAN DEFAULT FALSE,
    performance_vs_spy  FLOAT,
    source              TEXT DEFAULT 'initial',
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id           SERIAL PRIMARY KEY,
    agent_type   TEXT NOT NULL,
    status       TEXT DEFAULT 'pending',
    started_at   TIMESTAMP,
    finished_at  TIMESTAMP,
    log          TEXT DEFAULT '',
    error        TEXT,
    triggered_by TEXT DEFAULT 'scheduler'
);

CREATE TABLE IF NOT EXISTS analyst_reports (
    id             SERIAL PRIMARY KEY,
    report_date    TEXT NOT NULL,
    agent_run_id   INTEGER REFERENCES agent_runs(id),
    picks          TEXT NOT NULL,
    market_summary TEXT,
    vix_level      FLOAT,
    pdf_path       TEXT,
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
    id                 SERIAL PRIMARY KEY,
    symbol             TEXT NOT NULL,
    strategy_id        INTEGER REFERENCES strategies(id),
    analyst_report_id  INTEGER REFERENCES analyst_reports(id),
    entry_price        FLOAT NOT NULL,
    quantity           INTEGER NOT NULL,
    cost_basis         FLOAT NOT NULL,
    stop_loss_price    FLOAT NOT NULL,
    exit_target_price  FLOAT NOT NULL,
    status             TEXT DEFAULT 'open',
    opened_at          TIMESTAMP DEFAULT NOW(),
    closed_at          TIMESTAMP,
    close_reason       TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id           SERIAL PRIMARY KEY,
    symbol       TEXT NOT NULL,
    action       TEXT NOT NULL,
    price        FLOAT NOT NULL,
    quantity     INTEGER NOT NULL,
    amount       FLOAT NOT NULL,
    position_id  INTEGER REFERENCES positions(id),
    strategy_id  INTEGER REFERENCES strategies(id),
    agent_run_id INTEGER REFERENCES agent_runs(id),
    reason       TEXT,
    realized_pnl FLOAT,
    executed_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id                   SERIAL PRIMARY KEY,
    snapshot_at          TIMESTAMP DEFAULT NOW(),
    buying_power         FLOAT NOT NULL,
    open_positions_value FLOAT DEFAULT 0,
    total_value          FLOAT NOT NULL,
    agent_run_id         INTEGER REFERENCES agent_runs(id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id),
    type       TEXT NOT NULL,
    title      TEXT NOT NULL,
    message    TEXT NOT NULL,
    is_read    BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
""")
pg_conn.commit()
print("Schema created.\n")


# ── Helper ────────────────────────────────────────────────────────────────────
def ts(val):
    """Convert SQLite datetime string → Python datetime or None."""
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(val), fmt)
        except ValueError:
            continue
    return None


BOOL_COLS = {"is_active", "is_read"}

def _cast(col: str, val):
    """Convert SQLite value to PostgreSQL-compatible Python value."""
    if col in BOOL_COLS:
        return bool(val) if val is not None else None
    return val


def migrate_table(table: str, rows, columns: list[str], insert_sql: str):
    if not rows:
        print(f"  {table}: 0 rows (skipped)")
        return
    data = [tuple(_cast(c, r[c]) for c in columns) for r in rows]
    execute_values(cur, insert_sql, data)
    print(f"  {table}: {len(data)} rows migrated")


# ── Migrate each table in FK order ────────────────────────────────────────────
print("Migrating data...\n")

# 1. users
rows = sqlite_conn.execute("SELECT * FROM users ORDER BY id").fetchall()
migrate_table("users", rows, ["id","email","name","password_hash","role","approved_at","created_at"],
    "INSERT INTO users (id,email,name,password_hash,role,approved_at,created_at) VALUES %s ON CONFLICT (id) DO NOTHING")

# 2. settings
rows = sqlite_conn.execute("SELECT * FROM settings").fetchall()
if rows:
    data = [(r["key"], r["value"]) for r in rows]
    execute_values(cur, "INSERT INTO settings (key,value) VALUES %s ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", data)
    print(f"  settings: {len(data)} rows migrated")

# 3. strategies
rows = sqlite_conn.execute("SELECT * FROM strategies ORDER BY id").fetchall()
migrate_table("strategies", rows, ["id","version","name","description","parameters","is_active","performance_vs_spy","source","created_at"],
    "INSERT INTO strategies (id,version,name,description,parameters,is_active,performance_vs_spy,source,created_at) VALUES %s ON CONFLICT (id) DO NOTHING")

# 4. agent_runs
rows = sqlite_conn.execute("SELECT * FROM agent_runs ORDER BY id").fetchall()
migrate_table("agent_runs", rows, ["id","agent_type","status","started_at","finished_at","log","error","triggered_by"],
    "INSERT INTO agent_runs (id,agent_type,status,started_at,finished_at,log,error,triggered_by) VALUES %s ON CONFLICT (id) DO NOTHING")

# 5. analyst_reports
rows = sqlite_conn.execute("SELECT * FROM analyst_reports ORDER BY id").fetchall()
migrate_table("analyst_reports", rows, ["id","report_date","agent_run_id","picks","market_summary","vix_level","pdf_path","created_at"],
    "INSERT INTO analyst_reports (id,report_date,agent_run_id,picks,market_summary,vix_level,pdf_path,created_at) VALUES %s ON CONFLICT (id) DO NOTHING")

# 6. positions
rows = sqlite_conn.execute("SELECT * FROM positions ORDER BY id").fetchall()
migrate_table("positions", rows, ["id","symbol","strategy_id","analyst_report_id","entry_price","quantity","cost_basis","stop_loss_price","exit_target_price","status","opened_at","closed_at","close_reason"],
    "INSERT INTO positions (id,symbol,strategy_id,analyst_report_id,entry_price,quantity,cost_basis,stop_loss_price,exit_target_price,status,opened_at,closed_at,close_reason) VALUES %s ON CONFLICT (id) DO NOTHING")

# 7. transactions
rows = sqlite_conn.execute("SELECT * FROM transactions ORDER BY id").fetchall()
migrate_table("transactions", rows, ["id","symbol","action","price","quantity","amount","position_id","strategy_id","agent_run_id","reason","realized_pnl","executed_at"],
    "INSERT INTO transactions (id,symbol,action,price,quantity,amount,position_id,strategy_id,agent_run_id,reason,realized_pnl,executed_at) VALUES %s ON CONFLICT (id) DO NOTHING")

# 8. portfolio_snapshots
rows = sqlite_conn.execute("SELECT * FROM portfolio_snapshots ORDER BY id").fetchall()
migrate_table("portfolio_snapshots", rows, ["id","snapshot_at","buying_power","open_positions_value","total_value","agent_run_id"],
    "INSERT INTO portfolio_snapshots (id,snapshot_at,buying_power,open_positions_value,total_value,agent_run_id) VALUES %s ON CONFLICT (id) DO NOTHING")

# 9. notifications
rows = sqlite_conn.execute("SELECT * FROM notifications ORDER BY id").fetchall()
migrate_table("notifications", rows, ["id","user_id","type","title","message","is_read","created_at"],
    "INSERT INTO notifications (id,user_id,type,title,message,is_read,created_at) VALUES %s ON CONFLICT (id) DO NOTHING")

pg_conn.commit()

# ── Reset sequences so INSERT without explicit ID works ───────────────────────
print("\nResetting PostgreSQL sequences...")
for tbl in ["users","strategies","agent_runs","analyst_reports","positions","transactions","portfolio_snapshots","notifications"]:
    cur.execute(f"SELECT setval(pg_get_serial_sequence('{tbl}','id'), COALESCE(MAX(id),0)+1, false) FROM {tbl}")
    print(f"  {tbl} sequence reset")

pg_conn.commit()
pg_conn.close()
sqlite_conn.close()

print("\nMigration complete.")
