from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_signal_overlay(df: pd.DataFrame, output_path: str) -> str:
    """Render a price chart with signal markers and save it to disk."""
    if df.empty:
        raise ValueError("df is empty")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    chart = df.copy()
    if "close" not in chart.columns:
        raise ValueError("DataFrame must contain a 'close' column")

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(chart.index, chart["close"], label="close", linewidth=1.5, color="#1f77b4")

    if "signal_type" in chart.columns:
        for idx, row in chart.iterrows():
            signal = str(row.get("signal_type", "")).strip()
            if signal in {"", "none"}:
                continue
            marker = "^" if signal.endswith(("long", "_long", "long_open", "long_add")) else "v"
            color = "green" if signal.endswith(("long", "_long", "long_open", "long_add")) else "red"
            ax.scatter(idx, row["close"], marker=marker, s=40, color=color, alpha=0.85, zorder=3)

    ax.set_title("Signal Overlay")
    ax.set_xlabel("Index")
    ax.set_ylabel("Close")
    ax.grid(True, alpha=0.2)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return str(out)


def plot_equity_curve(equity_curve: Any, output_path: str) -> str:
    """Render an equity curve and save it to disk."""
    if hasattr(equity_curve, "to_list"):
        values = equity_curve.to_list()
    elif isinstance(equity_curve, dict):
        values = list(equity_curve.values())
    elif isinstance(equity_curve, (list, tuple)):
        values = list(equity_curve)
    else:
        raise TypeError(f"Unsupported equity_curve type: {type(equity_curve)!r}")

    if not values:
        raise ValueError("equity_curve is empty")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = list(range(len(values)))
    ax.plot(x, values, color="#2ca02c", linewidth=1.8)
    ax.set_title("Equity Curve")
    ax.set_xlabel("Trade / Step")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return str(out)


__all__ = ["plot_signal_overlay", "plot_equity_curve"]
