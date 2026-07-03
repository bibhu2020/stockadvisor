"""Entry point for the Retrospective Analyst agent."""
import json
import os
import sys
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[2] / ".env")

sys.path.insert(0, str(Path(__file__).parents[2]))

from agents.core.db import (
    Notification, RetrospectiveReport, SessionLocal, Transaction, User,
    get_active_strategy, init_db
)
from agents.core.orchestrator import AgentOrchestrator
from agents.core.pdf_generator import build_retrospective_report
from agents.retrospective import pattern_analyzer, performance_calculator, strategy_tuner
from sqlalchemy import func, select


def is_last_sunday_of_month() -> bool:
    # Use CST/CDT — the cron fires Mon 4AM UTC which is still Sunday in Chicago (both CDT and CST)
    import pytz
    chicago = pytz.timezone("America/Chicago")
    today = datetime.now(chicago).date()
    if today.weekday() != 6:  # 6 = Sunday
        return False
    _, days_in_month = monthrange(today.year, today.month)
    return (today.day + 7) > days_in_month


def get_previous_month(today: date) -> tuple[int, int]:
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def resolve_target_month(session, today: date) -> tuple[int, int]:
    """Pick the month to evaluate.

    Normally that's the previous calendar month (the last fully-completed one).
    But if trading only went live *during* that previous month or later — e.g. the
    bot launched mid-June, so May has zero transactions — the "previous month"
    is empty by construction, not because performance was flat. In that case
    evaluate the current, in-progress month instead, since that's where the
    actual trade history lives.
    """
    year, month = get_previous_month(today)
    first_tx_at = session.execute(select(func.min(Transaction.executed_at))).scalar()
    if first_tx_at and (first_tx_at.year, first_tx_at.month) > (year, month):
        return today.year, today.month
    return year, month


def main(triggered_by: str = "scheduler", force: bool = False):
    if not force and not is_last_sunday_of_month():
        print(f"Today ({date.today()}) is not the last Sunday of the month — skipping.")
        return

    init_db()
    today = date.today()

    with AgentOrchestrator("retrospective", triggered_by) as orch:
        session = orch.get_session()
        year, month = resolve_target_month(session, today)
        orch.log(f"Retrospective for {year}-{month:02d}")

        # 1. Performance calculation
        orch.log("--- Performance Calculator ---")
        performance = performance_calculator.run(session, year, month, orch.log)

        # 2. Pattern analysis
        orch.log("--- Pattern Analyzer ---")
        patterns = pattern_analyzer.run(performance, orch.log)

        # 3. Strategy tuning (if underperformed)
        orch.log("--- Strategy Tuner ---")
        current_strategy = get_active_strategy(session)
        new_strategy = None
        tuning_meta: dict = {}
        if current_strategy:
            new_strategy, tuning_meta = strategy_tuner.run(current_strategy, performance, patterns, session, orch.log)
            session.commit()

        # 4. Save retrospective report
        report = RetrospectiveReport(
            year=year,
            month=month,
            agent_run_id=orch.run_id,
            old_strategy_id=current_strategy.id if current_strategy else None,
            new_strategy_id=new_strategy.id if new_strategy else None,
            total_trades=performance.get("total_trades", 0),
            wins=performance.get("wins", 0),
            losses=performance.get("losses", 0),
            win_rate_pct=performance.get("win_rate_pct", 0.0),
            total_pnl=performance.get("total_pnl", 0.0),
            initial_value=performance.get("initial_value"),
            spy_return_pct=performance.get("spy_return_pct"),
            spy_equivalent_pnl=performance.get("spy_equivalent_pnl"),
            underperformed_spy=bool(performance.get("underperformed_spy")),
            tuning_rationale=tuning_meta.get("rationale"),
            prompts_updated=tuning_meta.get("prompts_updated"),
        )
        report.patterns = json.dumps(patterns)
        session.add(report)
        session.flush()  # get report.id

        # 5. Generate PDF
        orch.log("--- Report Generation ---")
        old_s = {"name": current_strategy.name, "description": current_strategy.description,
                  "parameters": current_strategy.get_parameters()} if current_strategy else None
        new_s = {"name": new_strategy.name, "description": new_strategy.description,
                  "parameters": new_strategy.get_parameters()} if new_strategy else None

        try:
            pdf_path = build_retrospective_report(
                year, month, performance,
                patterns.get("analysis_text", ""),
                old_s, new_s,
                performance.get("transactions", []),
            )
            report.pdf_path = pdf_path
            orch.log(f"PDF saved: {pdf_path}")
        except Exception as e:
            orch.log(f"PDF generation failed: {e}")

        session.commit()
        orch.log(f"Retrospective report #{report.id} saved.")

        # 6. Notify all users
        users = session.execute(select(User)).scalars().all()
        notif_msg = (
            f"Monthly retrospective for {year}-{month:02d} complete. "
            f"P&L: ${performance['total_pnl']:+.2f} vs SPY: {performance.get('spy_return_pct','?')}%."
        )
        if new_strategy:
            notif_msg += f" Strategy updated to v{new_strategy.version}."
        for user in users:
            session.add(Notification(
                user_id=user.id,
                type="retrospective_done",
                title=f"Monthly Retrospective — {year}-{month:02d}",
                message=notif_msg,
            ))
        session.commit()
        orch.log("Notifications sent.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Run regardless of date")
    parser.add_argument("--triggered-by", default="manual")
    args = parser.parse_args()
    # FORCE_RUN env var (set by GitHub Actions workflow_dispatch) overrides --force
    force = args.force or os.getenv("FORCE_RUN", "false").lower() == "true"
    main(args.triggered_by, force)
