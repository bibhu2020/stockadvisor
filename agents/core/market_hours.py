"""Market hours check for US equities (NYSE/NASDAQ).

Reads FORCE_RUN env var. If 'true', always returns open.
Otherwise, checks America/New_York timezone for:
  - Weekdays (Mon–Fri)
  - Not a NYSE holiday (New Year's, MLK, Presidents', Good Friday,
    Memorial Day, Juneteenth, Independence Day, Labor Day,
    Thanksgiving, Christmas)
  - 9:30 AM–4:00 PM Eastern
"""
import os
import sys
from datetime import date, datetime, timedelta

import pytz


def _easter(year: int) -> date:
    """Return Easter Sunday for the given year (Anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(114 + h + l - 7 * m, 31)
    return date(year, month, day + 1)


def _observed(d: date) -> date:
    """Return the NYSE observed date for a holiday on a weekend."""
    if d.weekday() == 5:   # Saturday → Friday
        return d - timedelta(days=1)
    if d.weekday() == 6:   # Sunday → Monday
        return d + timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the nth occurrence of weekday (0=Mon…6=Sun) in year/month."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Return the last occurrence of weekday (0=Mon…6=Sun) in year/month."""
    last = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _nyse_holidays(year: int) -> set:
    """Return the set of NYSE closure dates for the given year."""
    holidays = set()

    # New Year's Day
    holidays.add(_observed(date(year, 1, 1)))
    # Martin Luther King Jr. Day — 3rd Monday in January
    holidays.add(_nth_weekday(year, 1, 0, 3))
    # Presidents' Day — 3rd Monday in February
    holidays.add(_nth_weekday(year, 2, 0, 3))
    # Good Friday — Friday before Easter Sunday
    holidays.add(_easter(year) - timedelta(days=2))
    # Memorial Day — last Monday in May
    holidays.add(_last_weekday(year, 5, 0))
    # Juneteenth — June 19 (observed), effective 2022
    if year >= 2022:
        holidays.add(_observed(date(year, 6, 19)))
    # Independence Day — July 4 (observed)
    holidays.add(_observed(date(year, 7, 4)))
    # Labor Day — 1st Monday in September
    holidays.add(_nth_weekday(year, 9, 0, 1))
    # Thanksgiving — 4th Thursday in November
    holidays.add(_nth_weekday(year, 11, 3, 4))
    # Christmas Day — December 25 (observed)
    holidays.add(_observed(date(year, 12, 25)))

    return holidays


def is_trading_day() -> bool:
    """Return True if today is a NYSE trading day (weekday and not a holiday).

    Never bypassed by FORCE_RUN — weekend/holiday checks are always enforced.
    """
    eastern = pytz.timezone("America/New_York")
    now_et = datetime.now(eastern)
    if now_et.weekday() >= 5:
        return False
    today = now_et.date()
    return today not in _nyse_holidays(today.year)


def is_open() -> bool:
    """Return True if the market is currently open for trading.

    FORCE_RUN=true bypasses the 9:30–4:00 ET time window (e.g. for pre-market
    agents) but never bypasses the weekend/holiday check.
    """
    if not is_trading_day():
        return False

    if os.getenv("FORCE_RUN", "false").lower() == "true":
        return True

    eastern = pytz.timezone("America/New_York")
    now_et = datetime.now(eastern)
    open_time  = now_et.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_time = now_et.replace(hour=16, minute=0,  second=0, microsecond=0)
    return open_time <= now_et <= close_time


def check_or_exit(agent_name: str) -> None:
    """Exit with code 0 (success/no-op) if market is closed or today is a non-trading day."""
    if not is_open():
        eastern = pytz.timezone("America/New_York")
        now_et = datetime.now(eastern)
        print(
            f"[market_hours] Market is closed at {now_et.strftime('%Y-%m-%d %H:%M %Z')}. "
            f"{agent_name} will not run. "
            f"(FORCE_RUN=true bypasses the time window but not weekends/holidays.)"
        )
        sys.exit(0)
