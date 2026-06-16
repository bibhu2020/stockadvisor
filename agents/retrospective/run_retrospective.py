"""Entry point for the Retrospective Analyst agent."""
import os
import sys
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[2] / ".env")

sys.path.insert(0, str(Path(__file__).parents[2]))

from agents.core.db import Notification, SessionLocal, User, get_active_strategy, init_db
from agents.core.orchestrator import AgentOrchestrator
from agents.core.pdf_generator import build_retrospective_report
from agents.retrospective import pattern_analyzer, performance_calculator, strategy_tuner
from sqlalchemy import select


def is_last_sunday_of_month() -> bool:
    today = date.today()
    if today.weekday() != 6:  # 6 = Sunday
        return False
    # Is next Sunday in a different month?
    next_sunday = today.day + 7
    _, days_in_month = monthrange(today.year, today.month)
    return next_sunday > days_in_month


def get_previous_month(today: date) -> tuple[int, int]:
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def main(triggered_by: str = "scheduler", force: bool = False):
    if not force and not is_last_sunday_of_month():
        print(f"Today ({date.today()}) is not the last Sunday of the month — skipping.")
        return

    init_db()
    today = date.today()
    year, month = get_previous_month(today)

    with AgentOrchestrator("retrospective", triggered_by) as orch:
        session = orch.get_session()
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
        if current_strategy:
            new_strategy = strategy_tuner.run(current_strategy, performance, patterns, session, orch.log)
            session.commit()

        # 4. Generate PDF
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
            orch.log(f"PDF saved: {pdf_path}")
        except Exception as e:
            orch.log(f"PDF generation failed: {e}")

        # 5. Notify all users
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
    main(args.triggered_by, args.force)
