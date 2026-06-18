"""SQLAlchemy models and database session factory.

Supports both SQLite (dev/local) and PostgreSQL (production via DATABASE_URL).
Priority: DATABASE_URL env var → default SQLite path (data/stockadvisor.db).
"""
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, create_engine, event
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

# Load .env from project root
_ROOT = Path(__file__).parents[2]
load_dotenv(_ROOT / ".env")

_DATABASE_URL = os.getenv("DATABASE_URL", "")

if _DATABASE_URL.startswith("postgresql"):
    # Strip channel_binding — not supported by psycopg2
    _DATABASE_URL = (
        _DATABASE_URL
        .replace("&channel_binding=require", "")
        .replace("?channel_binding=require&", "?")
    )
    ENGINE = create_engine(
        _DATABASE_URL,
        connect_args={"sslmode": "require"},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
else:
    DB_PATH = str(_ROOT / "data" / "stockadvisor.db")
    ENGINE = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(ENGINE, "connect")
    def _set_wal(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="pending")  # admin | guest | pending
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    notifications = relationship("Notification", back_populates="user")


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)


class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    parameters = Column(Text, nullable=False)  # JSON string
    is_active = Column(Boolean, default=False)
    performance_vs_spy = Column(Float, nullable=True)
    source = Column(String, default="initial")  # initial | retrospective
    created_at = Column(DateTime, default=datetime.utcnow)

    def get_parameters(self) -> dict:
        return json.loads(self.parameters)

    def set_parameters(self, params: dict):
        self.parameters = json.dumps(params)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(Integer, primary_key=True)
    agent_type = Column(String, nullable=False)  # market_analyst | paper_trader | retrospective
    status = Column(String, default="pending")   # pending | running | completed | failed
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    log = Column(Text, default="")
    error = Column(Text, nullable=True)
    triggered_by = Column(String, default="scheduler")  # scheduler | manual


class AnalystReport(Base):
    __tablename__ = "analyst_reports"
    id = Column(Integer, primary_key=True)
    report_date = Column(String, nullable=False)  # YYYY-MM-DD
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=True)
    picks = Column(Text, nullable=False)          # JSON list of picks
    market_summary = Column(Text, nullable=True)
    vix_level = Column(Float, nullable=True)
    pdf_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def get_picks(self) -> list:
        return json.loads(self.picks)

    def set_picks(self, picks: list):
        self.picks = json.dumps(picks)


class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    analyst_report_id = Column(Integer, ForeignKey("analyst_reports.id"), nullable=True)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    cost_basis = Column(Float, nullable=False)
    stop_loss_price = Column(Float, nullable=False)
    exit_target_price = Column(Float, nullable=False)
    status = Column(String, default="open")   # open | closed
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    close_reason = Column(String, nullable=True)  # stop_loss | profit_target | expired | manual
    transactions = relationship("Transaction", back_populates="position")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False)   # BUY | SELL | HOLD
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=True)
    reason = Column(Text, nullable=True)
    realized_pnl = Column(Float, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)
    position = relationship("Position", back_populates="transactions")


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    id = Column(Integer, primary_key=True)
    snapshot_at = Column(DateTime, default=datetime.utcnow)
    buying_power = Column(Float, nullable=False)
    open_positions_value = Column(Float, default=0.0)
    total_value = Column(Float, nullable=False)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = all users
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="notifications")


def init_db():
    """Create all tables and seed initial data."""
    if not _DATABASE_URL.startswith("postgresql"):
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(ENGINE)

    with SessionLocal() as session:
        _seed_settings(session)
        _seed_strategy(session)
        _backfill_strategy_prompts(session)
        session.commit()


def _seed_settings(session: Session):
    defaults = {
        "buying_power": "5000",
        "stop_loss_pct": "15",
        "profit_target_pct": "10",
        "max_positions": "5",
        "confidence_threshold": "70",
    }
    for key, value in defaults.items():
        if not session.get(Setting, key):
            session.add(Setting(key=key, value=value))


def _default_prompts() -> dict:
    from agents.market_analyst.fundamental_analyst import SYSTEM_PROMPT as FP
    from agents.market_analyst.technical_analyst   import SYSTEM_PROMPT as TP
    from agents.market_analyst.sentiment_analyst   import SYSTEM_PROMPT as SP
    from agents.market_analyst.synthesizer         import SYSTEM_PROMPT as SYP
    from agents.paper_trader.trade_decision        import SYSTEM_PROMPT as TDP
    return {
        "fundamental_analyst": FP,
        "technical_analyst":   TP,
        "sentiment_analyst":   SP,
        "synthesizer":         SYP,
        "trade_decision":      TDP,
    }


def _seed_strategy(session: Session):
    from sqlalchemy import select
    existing = session.execute(select(Strategy)).first()
    if existing:
        return
    seed_params = {
        "stop_loss_pct": 15,
        "profit_target_pct": 10,
        "max_positions": 5,
        "confidence_threshold": 70,
        "position_size_pct": 20,
        "preferred_sectors": [],
        "avoid_earnings_within_days": 5,
        "entry_timing_rules": "Buy at open or within 1% of analyst entry price. Prefer morning entries before 11 AM.",
        "prompts": _default_prompts(),
    }
    strategy = Strategy(
        version=1,
        name="SPY Outperformance v1",
        description=(
            "Initial strategy targeting returns above the S&P 500 benchmark (~1% per month). "
            "Selects stocks with idiosyncratic, company-specific catalysts — earnings beats, "
            "analyst upgrades, product launches — that can move independently of broad market "
            "direction. Requires RSI 50-70 with SMA50 above SMA200 (trend intact), revenue "
            "growth > 15% YoY, and minimum 70% analyst confidence. Max 5 concurrent positions "
            "at 20% of buying power each. Avoids earnings within 5 days to limit binary risk. "
            "The retrospective agent automatically evolves this strategy when returns lag SPY."
        ),
        parameters=json.dumps(seed_params),
        is_active=True,
        source="initial",
    )
    session.add(strategy)


def _backfill_strategy_prompts(session: Session):
    """Ensure every strategy has all 5 agent prompts stored.

    - 'initial' strategies: always sync to current defaults (prompts are code-defined,
      not hand-tuned, so it's safe to refresh them when the code changes).
    - 'retrospective' strategies: only ADD missing keys; never overwrite tuned prompts.
    """
    from sqlalchemy import select
    defaults = _default_prompts()
    strategies = session.execute(select(Strategy)).scalars().all()
    updated = 0
    for s in strategies:
        params = s.get_parameters()
        prompts = params.get("prompts") or {}
        changed = False
        for key, default_text in defaults.items():
            if s.source == "initial":
                # Always keep initial strategies in sync with current code defaults
                if prompts.get(key) != default_text:
                    prompts[key] = default_text
                    changed = True
            else:
                # Retrospective strategies: only fill in completely missing keys
                if not prompts.get(key):
                    prompts[key] = default_text
                    changed = True
        if changed:
            params["prompts"] = prompts
            s.set_parameters(params)
            updated += 1
    if updated:
        print(f"[db] Synced prompts on {updated} strategy row(s).")


def get_setting(session: Session, key: str, default=None):
    s = session.get(Setting, key)
    return s.value if s else default


def get_active_strategy(session: Session) -> Strategy | None:
    from sqlalchemy import select
    return session.execute(
        select(Strategy).where(Strategy.is_active == True)
    ).scalar_one_or_none()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
