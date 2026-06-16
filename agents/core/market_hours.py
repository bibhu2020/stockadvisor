"""Market hours check for US equities (NYSE/NASDAQ).

Reads FORCE_RUN env var. If 'true', always returns open.
Otherwise, checks America/New_York timezone for weekdays and 9:30 AM–4:00 PM.
Does not check US market holidays — the GitHub Actions cron schedule handles
most cases; rare holiday runs exit cleanly without side effects.
"""
import os
import sys
from datetime import datetime

import pytz


def is_open() -> bool:
    if os.getenv("FORCE_RUN", "false").lower() == "true":
        return True

    eastern = pytz.timezone("America/New_York")
    now_et = datetime.now(eastern)

    if now_et.weekday() >= 5:
        return False

    open_time  = now_et.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_time = now_et.replace(hour=16, minute=0,  second=0, microsecond=0)
    return open_time <= now_et <= close_time


def check_or_exit(agent_name: str) -> None:
    """Exit with code 0 (success/no-op) if market is closed."""
    if not is_open():
        eastern = pytz.timezone("America/New_York")
        now_et = datetime.now(eastern)
        print(
            f"[market_hours] Market is closed at {now_et.strftime('%Y-%m-%d %H:%M %Z')}. "
            f"{agent_name} will not run. Set FORCE_RUN=true to override."
        )
        sys.exit(0)
