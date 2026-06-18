"""Entry point for the Market Analyst agent pipeline."""
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[2] / ".env")

sys.path.insert(0, str(Path(__file__).parents[2]))

from agents.core.market_hours import check_or_exit
check_or_exit("Market Analyst")

from agents.core.db import (
    AnalystReport, Notification, Position, SessionLocal, User,
    get_active_strategy, get_setting, init_db
)
from agents.core.orchestrator import AgentOrchestrator
from agents.core.pdf_generator import build_analyst_report
from agents.market_analyst import (
    fundamental_analyst,
    sentiment_analyst,
    synthesizer,
    technical_analyst,
    trend_spotter,
    volatility_analyst,
)
from sqlalchemy import delete, select, update

_ANALYST_REPORT_RETENTION_DAYS = 30


def _purge_old_analyst_reports(session, log) -> None:
    """Delete analyst_report rows older than retention window, nulling Position FKs first."""
    cutoff = datetime.utcnow() - timedelta(days=_ANALYST_REPORT_RETENTION_DAYS)

    old_ids = session.execute(
        select(AnalystReport.id).where(AnalystReport.created_at < cutoff)
    ).scalars().all()

    if not old_ids:
        log(f"Report cleanup: no reports older than {_ANALYST_REPORT_RETENTION_DAYS} days.")
        return

    session.execute(
        update(Position)
        .where(Position.analyst_report_id.in_(old_ids))
        .values(analyst_report_id=None)
    )
    session.execute(delete(AnalystReport).where(AnalystReport.id.in_(old_ids)))
    log(f"Report cleanup: deleted {len(old_ids)} analyst report(s) older than {_ANALYST_REPORT_RETENTION_DAYS} days.")


def main(triggered_by: str = "scheduler"):
    init_db()

    with AgentOrchestrator("market_analyst", triggered_by) as orch:
        session = orch.get_session()

        # Load active strategy first — prompts and params flow to every agent
        strategy = get_active_strategy(session)
        if not strategy:
            orch.log("No active strategy found — using defaults.")
            strategy_params = {}
            strategy_dict   = {"description": "Balanced momentum", "parameters": "{}"}
        else:
            strategy_params = strategy.get_parameters()
            strategy_dict   = {
                "description": strategy.description,
                "parameters":  strategy.parameters,
            }
            prompt_count = len(strategy_params.get("prompts", {}))
            orch.log(f"Strategy v{strategy.version} loaded ({prompt_count} custom prompts active).")

        # 1. Trend Spotter
        candidates = trend_spotter.run(orch.log)
        if not candidates:
            orch.log("No candidates found — aborting.")
            return

        # 2. Fundamental Analysis
        fundamentals = fundamental_analyst.run(candidates, orch.log, strategy_params)

        # 3. Technical Analysis
        technicals = technical_analyst.run(candidates, orch.log, strategy_params)

        # 4. Sentiment Analysis (top 15 by combined score)
        fund_map = {f["symbol"]: f.get("fundamental_score", 0) for f in fundamentals}
        tech_map = {t["symbol"]: t.get("technical_score", 0) for t in technicals}
        top15 = sorted(
            candidates,
            key=lambda s: fund_map.get(s, 0) + tech_map.get(s, 0),
            reverse=True
        )[:15]
        sentiments = sentiment_analyst.run(top15, fundamentals, orch.log, strategy_params)

        # 5. Volatility
        vol_data = volatility_analyst.run(candidates, orch.log)

        # 6. Synthesize
        synthesis = synthesizer.run(
            fundamentals, technicals, sentiments, vol_data, strategy_dict, orch.log
        )

        picks = synthesis.get("picks", [])
        market_summary = synthesis.get("market_summary", "")
        vix = vol_data.get("vix")
        today = str(date.today())

        # 7. Save report to DB
        report = AnalystReport(
            report_date=today,
            agent_run_id=orch.run_id,
            market_summary=market_summary,
            vix_level=vix,
        )
        report.set_picks(picks)
        session.add(report)
        session.flush()  # get report.id

        # 8. Generate PDF
        try:
            pdf_path = build_analyst_report(today, picks, market_summary, vix)
            report.pdf_path = pdf_path
            orch.log(f"PDF saved: {pdf_path}")
        except Exception as e:
            orch.log(f"PDF generation failed: {e}")

        session.commit()
        orch.log(f"Report #{report.id} saved with {len(picks)} picks.")

        # 9. Create in-app notifications for all users
        users = session.execute(select(User)).scalars().all()
        for user in users:
            session.add(Notification(
                user_id=user.id,
                type="report_ready",
                title=f"Market Analyst Report — {today}",
                message=f"Daily report ready with {len(picks)} picks. VIX: {vix}.",
            ))
        session.commit()
        orch.log("Notifications sent to all users.")

        # Housekeeping — purge analyst reports older than 30 days
        orch.log("--- Housekeeping ---")
        _purge_old_analyst_reports(session, orch.log)
        session.commit()


if __name__ == "__main__":
    triggered_by = sys.argv[1] if len(sys.argv) > 1 else "manual"
    main(triggered_by)
