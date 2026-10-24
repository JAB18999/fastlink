from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_equity_curve(equity_curve: Iterable[Dict[str, Any]], output_path: str = "reports/equity_curve.png") -> str:
    rows = list(equity_curve)
    if not rows:
        return output_path

    timestamps = [row["timestamp"] for row in rows]
    equity = [float(row["equity"]) for row in rows]

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(timestamps, equity, color="#4ecdc4", linewidth=2)
    ax.set_title("Equity Curve")
    ax.set_xlabel("Time")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return str(out)


def plot_signal_overlay(df, output_path: str = "reports/signal_overlay.png") -> str:
    if df.empty:
        return output_path

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(df["timestamp"], df["close"], color="#4ecdc4", linewidth=1.5, label="Close")

    long_mask = df["signal_type"].str.startswith("long")
    short_mask = df["signal_type"].str.startswith("short")

    if long_mask.any():
        ax.scatter(df.loc[long_mask, "timestamp"], df.loc[long_mask, "close"], color="green", marker="^", s=30, label="Long")
    if short_mask.any():
        ax.scatter(df.loc[short_mask, "timestamp"], df.loc[short_mask, "close"], color="red", marker="v", s=30, label="Short")

    ax.set_title("Price with Signal Events")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return str(out)
