from __future__ import annotations

from typing import Dict, List

import pandas as pd


def compute_signal_win_rate(df: pd.DataFrame, signal_name: str, lookahead: int = 12) -> Dict[str, float]:
    if df.empty:
        return {"count": 0, "win_rate": 0.0, "avg_return": 0.0}

    mask = df["signal_type"] == signal_name
    if not mask.any():
        return {"count": 0, "win_rate": 0.0, "avg_return": 0.0}

    future_returns = (df["close"].shift(-lookahead) / df["close"] - 1).where(mask).dropna()
    if future_returns.empty:
        return {"count": 0, "win_rate": 0.0, "avg_return": 0.0}

    wins = (future_returns > 0).mean()
    avg = future_returns.mean()
    return {
        "count": int(len(future_returns)),
        "win_rate": float(wins),
        "avg_return": float(avg),
    }


def evaluate_signal_performance(df: pd.DataFrame, lookahead: int = 12) -> Dict[str, Dict[str, float]]:
    if df.empty:
        return {}

    signal_names = [
        "long_open",
        "long_add",
        "long_reduce",
        "long_close",
        "short_open",
        "short_add",
        "short_reduce",
        "short_close",
    ]
    summary: Dict[str, Dict[str, float]] = {}
    for name in signal_names:
        summary[name] = compute_signal_win_rate(df, name, lookahead=lookahead)
    return summary


def summarize_strategy_comparison(frames: Dict[str, pd.DataFrame], lookahead: int = 12) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for timeframe, df in frames.items():
        if df.empty:
            continue
        market_state = df.iloc[-1].get("state", "中性") if "state" in df.columns else "中性"
        signal_summary = evaluate_signal_performance(df, lookahead=lookahead)
        rows.append({
            "timeframe": timeframe,
            "market_state": market_state,
            "long_open": signal_summary.get("long_open", {"count": 0, "win_rate": 0.0, "avg_return": 0.0}),
            "short_open": signal_summary.get("short_open", {"count": 0, "win_rate": 0.0, "avg_return": 0.0}),
        })
    return rows


__all__ = [
    "compute_signal_win_rate",
    "evaluate_signal_performance",
    "summarize_strategy_comparison",
]
