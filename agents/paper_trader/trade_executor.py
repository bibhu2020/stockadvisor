"""TradeExecutorAgent — records all trades in the DB (pure Python, no GPT)."""
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.core.db import (
    Notification, Position, PortfolioSnapshot, Setting, Transaction,
    get_setting
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _update_buying_power(session: Session, delta: float):
    s = session.get(Setting, "buying_power")
    s.value = str(round(float(s.value) + delta, 2))


def execute_sells(session: Session, sell_orders: list[dict],
                  strategy_id: int, run_id: int, log) -> float:
    """Execute all SELL orders. Returns total amount recovered."""
    recovered = 0.0
    for order in sell_orders:
        pos = session.get(Position, order["position_id"])
        if not pos or pos.status != "open":
            continue

        price = order["current_price"]
        qty   = order["quantity"]
        amount = round(price * qty, 2)
        pnl = round(amount - pos.cost_basis, 2)
        recovered += amount

        pos.status = "closed"
        pos.closed_at = datetime.utcnow()
        pos.close_reason = order["close_reason"]

        tx = Transaction(
            symbol=pos.symbol,
            action="SELL",
            price=price,
            quantity=qty,
            amount=amount,
            position_id=pos.id,
            strategy_id=strategy_id,
            agent_run_id=run_id,
            reason=f"Auto-exit: {order['close_reason']} ({order['pct_change']:+.1f}%)",
            realized_pnl=pnl,
        )
        session.add(tx)
        _update_buying_power(session, amount)

        close_reason = order["close_reason"]
        if close_reason == "stop_loss":
            notif_type  = "stop_loss"
            notif_title = f"Stop Loss: {pos.symbol}"
        elif close_reason == "profit_target":
            notif_type  = "profit_booked"
            notif_title = f"Profit Booked: {pos.symbol}"
        else:
            notif_type  = "position_closed"
            notif_title = f"Position Closed ({close_reason}): {pos.symbol}"
        session.add(Notification(
            user_id=None,
            type=notif_type,
            title=notif_title,
            message=f"{pos.symbol} exited via {close_reason} at ${price:.2f} "
                    f"| P&L: ${pnl:+.2f} ({order['pct_change']:+.1f}%)",
        ))
        log(f"SELL {pos.symbol}: {qty} shares @ ${price:.2f} | P&L ${pnl:+.2f}")

    session.flush()
    return recovered


def execute_buys(session: Session, buy_orders: list[dict], last_report,
                 strategy_id: int, run_id: int, buying_power: float, log) -> float:
    """Execute all BUY orders. Returns total amount spent.

    Hard cap: total capital deployed (existing open positions + new buys) can
    never exceed the buying_power available at the start of this execution.
    """
    # Total cost basis already locked in open positions
    open_cost = session.execute(
        select(func.sum(Position.cost_basis)).where(Position.status == "open")
    ).scalar() or 0.0

    # Total capital = cash on hand + what's already deployed
    total_capital = round(buying_power + open_cost, 2)
    log(f"Capital check: total=${total_capital:.2f} "
        f"deployed=${open_cost:.2f} available=${buying_power:.2f}")

    spent = 0.0
    for order in buy_orders:
        sym    = order["symbol"]
        price  = order["price"]
        qty    = order.get("quantity", 1)
        if not qty or qty <= 0:
            log(f"  {sym}: quantity={qty} — skipping zero-quantity order")
            continue
        amount = round(price * qty, 2)

        # Hard cap: existing deployed + already spent this run + this order ≤ total capital
        if open_cost + spent + amount > total_capital:
            log(f"  {sym}: would exceed capital cap "
                f"(deployed=${open_cost + spent:.2f} + ${amount:.2f} > cap=${total_capital:.2f}) — skip")
            continue

        # Live buying-power check: re-read from session identity map which reflects
        # _update_buying_power mutations from earlier buys in this same run
        live_bp = float(get_setting(session, "buying_power", "0"))
        if amount > live_bp:
            log(f"  {sym}: insufficient buying power "
                f"(${live_bp:.2f} available, ${amount:.2f} needed) — skip")
            continue

        # Find analyst pick for stop/exit targets
        picks = last_report.get_picks() if last_report else []
        pick = next((p for p in picks if p["symbol"] == sym), {})

        stop_loss   = pick.get("stop_loss", round(price * 0.85, 2))
        exit_target = pick.get("exit_price", round(price * 1.10, 2))

        pos = Position(
            symbol=sym,
            strategy_id=strategy_id,
            analyst_report_id=last_report.id if last_report else None,
            entry_price=price,
            quantity=qty,
            cost_basis=amount,
            stop_loss_price=stop_loss,
            exit_target_price=exit_target,
        )
        session.add(pos)
        session.flush()

        tx = Transaction(
            symbol=sym,
            action="BUY",
            price=price,
            quantity=qty,
            amount=amount,
            position_id=pos.id,
            strategy_id=strategy_id,
            agent_run_id=run_id,
            reason=order.get("reason", ""),
        )
        session.add(tx)
        _update_buying_power(session, -amount)
        spent += amount

        session.add(Notification(
            user_id=None,
            type="trade_executed",
            title=f"BUY: {sym}",
            message=f"Bought {qty} shares of {sym} @ ${price:.2f} | Total: ${amount:.2f}",
        ))
        log(f"BUY {sym}: {qty} shares @ ${price:.2f} | Cost ${amount:.2f}")

    session.flush()
    return spent


def snapshot_portfolio(session: Session, run_id: int, log):
    """Take a portfolio value snapshot."""
    from agents.core.data_fetcher import get_current_price
    buying_power = float(get_setting(session, "buying_power", "5000"))

    open_positions = session.execute(
        select(Position).where(Position.status == "open")
    ).scalars().all()

    pos_value = 0.0
    for pos in open_positions:
        price = get_current_price(pos.symbol) or pos.entry_price
        pos_value += price * pos.quantity

    total = round(buying_power + pos_value, 2)
    snap = PortfolioSnapshot(
        buying_power=buying_power,
        open_positions_value=round(pos_value, 2),
        total_value=total,
        agent_run_id=run_id,
    )
    session.add(snap)
    log(f"Portfolio snapshot: power=${buying_power:.2f} positions=${pos_value:.2f} total=${total:.2f}")
