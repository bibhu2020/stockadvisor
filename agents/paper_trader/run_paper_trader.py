"""Entry point for the Paper Trader agent pipeline."""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[2] / ".env")

sys.path.insert(0, str(Path(__file__).parents[2]))

from agents.core.market_hours import check_or_exit
check_or_exit("Paper Trader")

from agents.core.db import (
    AgentRun, AnalystReport, PortfolioSnapshot, Position,
    Transaction, init_db, get_setting, get_active_strategy, SessionLocal
)
from agents.core.orchestrator import AgentOrchestrator
from agents.paper_trader import position_monitor, trade_decision, trade_executor
from sqlalchemy import select, desc, update, delete


_AGENT_RUN_RETENTION_DAYS = 7


def _purge_old_agent_runs(session, log) -> None:
    """Delete agent_run rows older than retention window and null their FKs first."""
    cutoff = datetime.utcnow() - timedelta(days=_AGENT_RUN_RETENTION_DAYS)

    old_ids = session.execute(
        select(AgentRun.id).where(AgentRun.started_at < cutoff)
    ).scalars().all()

    if not old_ids:
        log(f"Agent run cleanup: no runs older than {_AGENT_RUN_RETENTION_DAYS} days.")
        return

    # Null FK references in child tables before deleting
    session.execute(
        update(AnalystReport)
        .where(AnalystReport.agent_run_id.in_(old_ids))
        .values(agent_run_id=None)
    )
    session.execute(
        update(Transaction)
        .where(Transaction.agent_run_id.in_(old_ids))
        .values(agent_run_id=None)
    )
    session.execute(
        update(PortfolioSnapshot)
        .where(PortfolioSnapshot.agent_run_id.in_(old_ids))
        .values(agent_run_id=None)
    )

    session.execute(delete(AgentRun).where(AgentRun.id.in_(old_ids)))
    log(f"Agent run cleanup: deleted {len(old_ids)} run(s) older than {_AGENT_RUN_RETENTION_DAYS} days.")


def main(triggered_by: str = "scheduler"):
    init_db()

    with AgentOrchestrator("paper_trader", triggered_by) as orch:
        session = orch.get_session()

        # Load config — all trading params come from the active strategy;
        # buying_power is the only dynamic value kept in settings.
        strategy = get_active_strategy(session)

        if not strategy:
            orch.log("No active strategy — aborting paper trader.")
            return

        strategy_id     = strategy.id
        strategy_params = strategy.get_parameters()
        stop_loss_pct     = float(strategy_params.get("stop_loss_pct", 15))
        profit_target_pct = float(strategy_params.get("profit_target_pct", 5))
        buying_power      = float(get_setting(session, "buying_power", "5000"))
        orch.log(f"Strategy: {strategy.name} (v{strategy.version})")
        orch.log(f"Buying power: ${buying_power:.2f}")

        # Fetch latest analyst report
        last_report = session.execute(
            select(AnalystReport).order_by(desc(AnalystReport.created_at)).limit(1)
        ).scalar_one_or_none()

        if not last_report:
            orch.log("No analyst report found — holding all positions.")
        else:
            orch.log(f"Using analyst report #{last_report.id} from {last_report.report_date}")

        # 1. Monitor & exit open positions
        orch.log("--- Position Monitor ---")
        sell_orders = position_monitor.run(
            session, stop_loss_pct, profit_target_pct, orch.log
        )
        trade_executor.execute_sells(session, sell_orders, strategy_id, orch.run_id, orch.log)
        session.commit()

        # Refresh buying power after sells
        buying_power = float(get_setting(session, "buying_power", "5000"))
        orch.log(f"Buying power after exits: ${buying_power:.2f}")

        # 2. Decide & execute new buys
        if last_report and buying_power > 100:
            orch.log("--- Trade Decision ---")
            open_symbols = [
                p.symbol for p in session.execute(
                    select(Position).where(Position.status == "open")
                ).scalars().all()
            ]
            buy_orders = trade_decision.run(
                last_report, open_symbols, buying_power, strategy_params, orch.log
            )
            trade_executor.execute_buys(
                session, buy_orders, last_report, strategy_id, orch.run_id, buying_power, orch.log
            )
            session.commit()
        else:
            orch.log("Skipping buys — no report or insufficient buying power.")

        # 3. Portfolio snapshot
        orch.log("--- Portfolio Snapshot ---")
        trade_executor.snapshot_portfolio(session, orch.run_id, orch.log)
        session.commit()

        # 4. Housekeeping — purge agent runs older than 7 days
        orch.log("--- Housekeeping ---")
        _purge_old_agent_runs(session, orch.log)
        session.commit()


if __name__ == "__main__":
    triggered_by = sys.argv[1] if len(sys.argv) > 1 else "manual"
    main(triggered_by)
