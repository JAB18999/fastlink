from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from src.config import DEFAULT_FEE_RATE, DEFAULT_INITIAL_CAPITAL
from src.strategy import generate_signal_history
from src.strategy_combo import generate_combined_signal_history


DEFAULT_BACKTEST_PARAMS = {
    "fast_window": 12,
    "slow_window": 26,
    "rsi_buy": 55,
    "rsi_sell": 45,
    "rsi_add": 60,
    "rsi_reduce": 50,
}


def calculate_drawdown(equity_curve: List[float]) -> Dict[str, Any]:
    if not equity_curve:
        return {"max_drawdown": 0.0, "drawdown_series": []}

    peak = equity_curve[0]
    drawdown_series = []
    max_drawdown = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak else 0.0
        drawdown_series.append(dd)
        if dd > max_drawdown:
            max_drawdown = dd

    return {"max_drawdown": float(max_drawdown), "drawdown_series": drawdown_series}


def run_backtest(
    df: pd.DataFrame,
    strategy_name: str = "trend_following",
    params: Optional[Dict[str, Any]] = None,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    fee_rate: float = DEFAULT_FEE_RATE,
    strategy_mode: str = "standard",
) -> Dict[str, Any]:
    if df.empty:
        return {"total_return": 0.0, "net_profit": 0.0, "trades": 0, "win_rate": 0.0, "max_drawdown": 0.0, "equity_curve": [], "drawdown_series": []}

    params = {**DEFAULT_BACKTEST_PARAMS, **(params or {})}
    if strategy_mode == "combo":
        market = generate_combined_signal_history(df.copy(), params=params)
    else:
        market = generate_signal_history(df.copy(), strategy_name=strategy_name, params=params)

    cash = float(initial_capital)
    position_units = 0.0
    position_side = 0
    entry_price = 0.0
    trades: List[Dict[str, Any]] = []
    equity_curve: List[Dict[str, Any]] = []
    realized_trades: List[Dict[str, Any]] = []
    equity_values: List[float] = []

    for idx, row in market.iterrows():
        close = float(row["close"])
        signal = str(row.get("signal_type", "none"))

        if signal == "long_open" and position_side <= 0:
            if position_side < 0:
                pnl = position_units * (close - entry_price)
                cash += pnl
                realized_trades.append({"pnl": float(pnl), "type": "cover"})
            position_units = 1.0
            position_side = 1
            entry_price = close
            trades.append({"type": "long_open", "timestamp": row["timestamp"], "price": float(close)})

        elif signal == "long_add" and position_side == 1:
            position_units += 0.5
            trades.append({"type": "long_add", "timestamp": row["timestamp"], "units": 0.5, "price": float(close)})

        elif signal == "long_reduce" and position_side == 1:
            reduce_units = min(position_units * 0.5, position_units)
            if reduce_units > 0:
                pnl = reduce_units * (close - entry_price)
                cash += pnl
                position_units -= reduce_units
                realized_trades.append({"pnl": float(pnl), "type": "long_reduce"})
                trades.append({"type": "long_reduce", "timestamp": row["timestamp"], "units": float(reduce_units), "pnl": float(pnl)})

        elif signal == "long_close" and position_side == 1:
            pnl = position_units * (close - entry_price)
            cash += pnl
            position_units = 0.0
            position_side = 0
            entry_price = 0.0
            realized_trades.append({"pnl": float(pnl), "type": "long_close"})
            trades.append({"type": "long_close", "timestamp": row["timestamp"], "pnl": float(pnl)})

        elif signal == "short_open" and position_side >= 0:
            if position_side > 0:
                pnl = position_units * (close - entry_price)
                cash += pnl
                realized_trades.append({"pnl": float(pnl), "type": "close_long"})
            position_units = -1.0
            position_side = -1
            entry_price = close
            trades.append({"type": "short_open", "timestamp": row["timestamp"], "price": float(close)})

        elif signal == "short_add" and position_side == -1:
            position_units -= 0.5
            trades.append({"type": "short_add", "timestamp": row["timestamp"], "units": 0.5, "price": float(close)})

        elif signal == "short_reduce" and position_side == -1:
            reduce_units = min(abs(position_units) * 0.5, abs(position_units))
            if reduce_units > 0:
                pnl = reduce_units * (entry_price - close)
                cash += pnl
                position_units += reduce_units
                realized_trades.append({"pnl": float(pnl), "type": "short_reduce"})
                trades.append({"type": "short_reduce", "timestamp": row["timestamp"], "units": float(reduce_units), "pnl": float(pnl)})

        elif signal == "short_close" and position_side == -1:
            pnl = position_units * (close - entry_price)
            cash += pnl
            position_units = 0.0
            position_side = 0
            entry_price = 0.0
            realized_trades.append({"pnl": float(pnl), "type": "short_close"})
            trades.append({"type": "short_close", "timestamp": row["timestamp"], "pnl": float(pnl)})

        equity = cash + position_units * close
        equity_values.append(float(equity))
        equity_curve.append({"timestamp": row["timestamp"], "equity": float(equity)})

    final_equity = cash + position_units * market.iloc[-1]["close"]
    total_return = (final_equity - initial_capital) / initial_capital
    win_pnls = [trade.get("pnl", 0.0) for trade in realized_trades]
    wins = sum(1 for pnl in win_pnls if pnl > 0)
    win_rate = wins / len(win_pnls) if win_pnls else 0.0

    drawdown = calculate_drawdown(equity_values)

    return {
        "strategy_name": strategy_name,
        "params": params,
        "initial_capital": float(initial_capital),
        "final_equity": float(final_equity),
        "total_return": float(total_return),
        "net_profit": float(final_equity - initial_capital),
        "trades": len(realized_trades),
        "win_rate": float(win_rate),
        "max_drawdown": float(drawdown["max_drawdown"]),
        "equity_curve": equity_curve,
        "drawdown_series": drawdown["drawdown_series"],
        "trade_log": trades,
    }
