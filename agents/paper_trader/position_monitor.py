"""PositionMonitorAgent — checks open positions for exit triggers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from datetime import datetime, timedelta
from agents.core.data_fetcher import get_current_price
from agents.core.db import Position, SessionLocal
from sqlalchemy import select


def run(session, stop_loss_pct: float, profit_target_pct: float, log) -> list[dict]:
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

        log(f"  {pos.symbol}: entry={pos.entry_price:.2f} current={current:.2f} "
            f"stop={pos.stop_loss_price:.2f} target={pos.exit_target_price:.2f}")

        reason = None
        # Stop loss: analyst stop OR 15% rule, whichever triggers first
        pct_change = (current - pos.entry_price) / pos.entry_price * 100
        if current <= pos.stop_loss_price or pct_change <= -stop_loss_pct:
            reason = "stop_loss"
        # Profit target: analyst exit OR 10% rule
        elif current >= pos.exit_target_price or pct_change >= profit_target_pct:
            reason = "profit_target"
        # Month horizon expired
        elif datetime.utcnow() - pos.opened_at > timedelta(days=30):
            reason = "expired"

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
