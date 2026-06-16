"""PerformanceCalculatorAgent — computes P&L vs SPY for a given month."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.data_fetcher import get_spy_monthly_return
from agents.core.db import PortfolioSnapshot, Transaction
from sqlalchemy import select, extract
from sqlalchemy.orm import Session


def run(session: Session, year: int, month: int, log) -> dict:
    # All closed trades in the month
    txs = session.execute(
        select(Transaction).where(
            Transaction.action == "SELL",
            Transaction.realized_pnl != None,
            extract("year",  Transaction.executed_at) == year,
            extract("month", Transaction.executed_at) == month,
        )
    ).scalars().all()

    total_pnl = sum(t.realized_pnl or 0 for t in txs)
    wins   = [t for t in txs if (t.realized_pnl or 0) > 0]
    losses = [t for t in txs if (t.realized_pnl or 0) <= 0]
    win_rate = round(len(wins) / len(txs) * 100, 1) if txs else 0.0

    # Starting portfolio value (first snapshot of month)
    first_snap = session.execute(
        select(PortfolioSnapshot).where(
            extract("year",  PortfolioSnapshot.snapshot_at) == year,
            extract("month", PortfolioSnapshot.snapshot_at) == month,
        ).order_by(PortfolioSnapshot.snapshot_at)
    ).scalar_one_or_none()
    initial_value = first_snap.total_value if first_snap else 5000.0

    spy_return = get_spy_monthly_return(year, month)
    spy_pnl = round(initial_value * (spy_return / 100), 2) if spy_return else None

    log(f"Performance: P&L=${total_pnl:.2f}, Win Rate={win_rate}%, SPY={spy_return}%")

    return {
        "year": year,
        "month": month,
        "total_trades": len(txs),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": win_rate,
        "total_pnl": round(total_pnl, 2),
        "initial_value": initial_value,
        "spy_return_pct": spy_return,
        "spy_equivalent_pnl": spy_pnl,
        "underperformed_spy": spy_return is not None and total_pnl < (spy_pnl or 0),
        "transactions": [
            {
                "symbol": t.symbol,
                "action": t.action,
                "price": t.price,
                "quantity": t.quantity,
                "amount": t.amount,
                "realized_pnl": t.realized_pnl,
                "executed_at": str(t.executed_at),
                "reason": t.reason,
            }
            for t in txs
        ],
    }
