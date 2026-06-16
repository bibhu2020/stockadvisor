"""APScheduler daemon — runs all agent jobs on their defined schedules."""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

scheduler = BlockingScheduler(timezone="America/Chicago")


def run_market_analyst():
    log.info("Scheduler: triggering Market Analyst...")
    from agents.market_analyst.run_market_analyst import main
    try:
        main("scheduler")
    except Exception as e:
        log.error(f"Market Analyst failed: {e}")


def run_paper_trader():
    log.info("Scheduler: triggering Paper Trader...")
    from agents.paper_trader.run_paper_trader import main
    try:
        main("scheduler")
    except Exception as e:
        log.error(f"Paper Trader failed: {e}")


def run_retrospective():
    log.info("Scheduler: triggering Retrospective Analyst...")
    from agents.retrospective.run_retrospective import main
    try:
        main("scheduler")
    except Exception as e:
        log.error(f"Retrospective failed: {e}")


# Market Analyst: Mon–Fri 9:30 AM CST
scheduler.add_job(
    run_market_analyst,
    CronTrigger(day_of_week="mon-fri", hour=9, minute=30, timezone="America/Chicago"),
    id="market_analyst",
    name="Daily Market Analyst",
)

# Paper Trader: Mon–Fri 10:00 AM, 12:00 PM, 2:45 PM CST
for hour, minute in [(10, 0), (12, 0), (14, 45)]:
    scheduler.add_job(
        run_paper_trader,
        CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute, timezone="America/Chicago"),
        id=f"paper_trader_{hour:02d}{minute:02d}",
        name=f"Paper Trader {hour:02d}:{minute:02d}",
    )

# Retrospective: Every Sunday 11:00 PM CST (script checks if last Sunday of month)
scheduler.add_job(
    run_retrospective,
    CronTrigger(day_of_week="sun", hour=23, minute=0, timezone="America/Chicago"),
    id="retrospective",
    name="Monthly Retrospective",
)


def main():
    log.info("StockAdvisor scheduler starting...")
    for job in scheduler.get_jobs():
        log.info(f"  Scheduled: {job.name}")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
