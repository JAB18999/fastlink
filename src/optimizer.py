from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from src.config import DEFAULT_FEE_RATE, DEFAULT_INITIAL_CAPITAL
from src.strategy import generate_signal_history


DEFAULT_BACKTEST_PARAMS = {
    "fast_window": 12,
    "slow_window": 26,
    "rsi_buy": 55,
    "rsi_sell": 45,
    "rsi_add": 60,
    "rsi_reduce": 50,
}


def run_backtest(
    df: pd.DataFrame,
    strategy_name: str = "trend_following",
    params: Optional[Dict[str, Any]] = None,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    fee_rate: float = DEFAULT_FEE_RATE,
) -> Dict[str, Any]:
    if df.empty:
        return {"total_return": 0.0, "net_profit": 0.0, "trades": 0, "win_rate": 0.0, "max_drawdown": 0.0, "equity_curve": []}

    params = {**DEFAULT_BACKTEST_PARAMS, **(params or {})}
    market = generate_signal_history(df.copy(), strategy_name=strategy_name, params=params)

    cash = float(initial_capital)
    position_units = 0.0
    position_side = 0
    entry_price = 0.0
    trades: List[Dict[str, Any]] = []
    equity_curve: List[Dict[str, Any]] = []
    history_pnls: List[float] = []
    max_drawdown = 0.0
    peak_equity = float(initial_capital)

    for idx, row in market.iterrows():
        close = float(row["close"])
        signal = str(row.get("signal_type", "none"))

        current_position_value = position_units * close
        equity = cash + current_position_value
        if equity > peak_equity:
            peak_equity = equity
        drawdown = (peak_equity - equity) / peak_equity if peak_equity else 0.0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        if signal == "long_open" and position_side <= 0:
            if position_side < 0:
                pnl = position_units * (close - entry_price)
                cash += pnl
                trades.append({"type": "cover", "timestamp": row["timestamp"], "pnl": float(pnl)})
            position_units = 1.0
            position_side = 1
            entry_price = close
            trades.append({"type": "long_open", "timestamp": row["timestamp"], "price": float(close)})

        elif signal == "long_add" and position_side == 1:
            add_units = 0.5
            position_units += add_units
            trades.append({"type": "long_add", "timestamp": row["timestamp"], "units": add_units, "price": float(close)})

        elif signal == "long_reduce" and position_side == 1:
            reduce_units = min(position_units * 0.5, position_units)
            if reduce_units > 0:
                pnl = reduce_units * (close - entry_price)
                cash += pnl
                position_units -= reduce_units
                trades.append({"type": "long_reduce", "timestamp": row["timestamp"], "units": float(reduce_units), "pnl": float(pnl)})

        elif signal == "long_close" and position_side == 1:
            pnl = position_units * (close - entry_price)
            cash += pnl
            position_units = 0.0
            position_side = 0
            entry_price = 0.0
            trades.append({"type": "long_close", "timestamp": row["timestamp"], "pnl": float(pnl)})

        elif signal == "short_open" and position_side >= 0:
            if position_side > 0:
                pnl = position_units * (close - entry_price)
                cash += pnl
                trades.append({"type": "close_long", "timestamp": row["timestamp"], "pnl": float(pnl)})
            position_units = -1.0
            position_side = -1
            entry_price = close
            trades.append({"type": "short_open", "timestamp": row["timestamp"], "price": float(close)})

        elif signal == "short_add" and position_side == -1:
            add_units = 0.5
            position_units -= add_units
            trades.append({"type": "short_add", "timestamp": row["timestamp"], "units": add_units, "price": float(close)})

        elif signal == "short_reduce" and position_side == -1:
            reduce_units = min(abs(position_units) * 0.5, abs(position_units))
            if reduce_units > 0:
                pnl = reduce_units * (entry_price - close)
                cash += pnl
                position_units += reduce_units
                trades.append({"type": "short_reduce", "timestamp": row["timestamp"], "units": float(reduce_units), "pnl": float(pnl)})

        elif signal == "short_close" and position_side == -1:
            pnl = position_units * (close - entry_price)
            cash += pnl
            position_units = 0.0
            position_side = 0
            entry_price = 0.0
            trades.append({"type": "short_close", "timestamp": row["timestamp"], "pnl": float(pnl)})

        equity = cash + position_units * close
        history_pnls.append(equity - initial_capital)
        equity_curve.append({"timestamp": row["timestamp"], "equity": float(equity)})

    final_equity = cash + position_units * market.iloc[-1]["close"]
    total_return = (final_equity - initial_capital) / initial_capital
    realized_trades = [trade for trade in trades if "pnl" in trade]
    win_count = sum(1 for trade in realized_trades if trade["pnl"] > 0)
    win_rate = win_count / len(realized_trades) if realized_trades else 0.0

    return {
        "strategy_name": strategy_name,
        "params": params,
        "initial_capital": float(initial_capital),
        "final_equity": float(final_equity),
        "total_return": float(total_return),
        "net_profit": float(final_equity - initial_capital),
        "trades": len(realized_trades),
        "win_rate": float(win_rate),
        "max_drawdown": float(max_drawdown),
        "equity_curve": equity_curve,
        "trade_log": trades,
    }
