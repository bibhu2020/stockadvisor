"""PositionMonitorAgent — checks open positions for exit triggers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from datetime import datetime, timezone
from agents.core.data_fetcher import get_current_price
from agents.core.db import Position, SessionLocal
from sqlalchemy import select


def run(session, stop_loss_pct: float, profit_target_pct: float, max_hold_days: float, log) -> list[dict]:
    """Return list of sell orders for positions that hit exit conditions."""
    open_positions = session.execute(
        select(Position).where(Position.status == "open")
    ).scalars().all()

    sell_orders = []
    for pos in open_positions:
        current = get_current_price(pos.symbol)
        if current is None:
            log(f"  {pos.symbol}: could not fetch price — skipping")
            continue

        opened_at = pos.opened_at
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        days_held = (datetime.now(timezone.utc) - opened_at).days

        log(f"  {pos.symbol}: entry={pos.entry_price:.2f} current={current:.2f} "
            f"stop={pos.stop_loss_price:.2f} target={pos.exit_target_price:.2f} "
            f"held={days_held}d")

        reason = None
        pct_change = (current - pos.entry_price) / pos.entry_price * 100
        # Stop loss: analyst stop OR strategy pct, whichever triggers first
        if current <= pos.stop_loss_price or pct_change <= -stop_loss_pct:
            reason = "stop_loss"
        # Profit target: analyst exit OR strategy pct, whichever triggers first
        elif current >= pos.exit_target_price or pct_change >= profit_target_pct:
            reason = "profit_target"
        # Max hold period
        elif days_held >= max_hold_days:
            reason = "max_hold_days"

        if reason:
            sell_orders.append({
                "position_id": pos.id,
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "current_price": current,
                "close_reason": reason,
                "pct_change": round(pct_change, 2),
            })
            log(f"  {pos.symbol}: EXIT triggered → {reason} ({pct_change:+.1f}%)")

    return sell_orders
