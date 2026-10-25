from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Dict, List

from src.config import LOGS_DIR


def append_trade_log(trade: Dict[str, Any], log_path: str = str(LOGS_DIR / "trades.jsonl")) -> str:
    out = Path(log_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(trade, ensure_ascii=False) + "\n")
    return str(out)


def read_trade_log(log_path: str = str(LOGS_DIR / "trades.jsonl")) -> List[Dict[str, Any]]:
    out = Path(log_path)
    if not out.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with out.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def summarize_trade_log(log_path: str = str(LOGS_DIR / "trades.jsonl")) -> Dict[str, Any]:
    rows = read_trade_log(log_path)
    if not rows:
        return {"trades": 0, "wins": 0, "losses": 0, "net_profit": 0.0}

    pnl_values = [float(item.get("pnl", 0.0)) for item in rows if "pnl" in item]
    wins = sum(1 for value in pnl_values if value > 0)
    losses = sum(1 for value in pnl_values if value < 0)
    net_profit = sum(pnl_values)

    return {
        "trades": len(rows),
        "wins": wins,
        "losses": losses,
        "net_profit": net_profit,
    }


def generate_dashboard_html(summary: Dict[str, Any], best_results: Any, dashboard_path: str) -> str:
    """Generate a lightweight HTML dashboard summary.

    The application calls this helper when the --dashboard flag is enabled. The
    function exists to satisfy the import in src/main.py and writes a simple HTML
    page that can be opened in a browser.
    """
    out = Path(dashboard_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    market_state = summary.get("market_state", "未知")
    signal_type = summary.get("signal_type", "none")
    total_return = float(summary.get("total_return", 0.0))
    max_drawdown = float(summary.get("max_drawdown", 0.0))
    signals = summary.get("signals", [])

    if isinstance(best_results, dict):
        best_rows = [best_results]
    elif isinstance(best_results, list):
        best_rows = best_results
    else:
        best_rows = []

    signal_rows_html = "\n".join(
        (
            "<tr>"
            f"<td>{escape(str(item.get('timeframe', '')))}</td>"
            f"<td>{escape(str(item.get('market_state', '')))}</td>"
            f"<td>{escape(str(item.get('signal_type', '')))}</td>"
            f"<td>{escape(str(item.get('signal_reason', '')))}</td>"
            "</tr>"
        )
        for item in signals
    )

    opt_rows_html = "\n".join(
        (
            "<tr>"
            f"<td>{escape(str(item.get('strategy_name', item.get('name', ''))))}</td>"
            f"<td>{escape(str(item.get('objective', item.get('score', ''))))}</td>"
            "</tr>"
        )
        for item in best_rows
    )

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Market Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    h1 {{ margin-bottom: 8px; }}
    .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 24px 0; }}
    .card {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; min-width: 180px; background: #f9fafb; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef2ff; }}
  </style>
</head>
<body>
  <h1>Market Dashboard</h1>
  <div class=\"cards\">
    <div class=\"card\"><strong>Market State</strong><br>{escape(str(market_state))}</div>
    <div class=\"card\"><strong>Signal Type</strong><br>{escape(str(signal_type))}</div>
    <div class=\"card\"><strong>Total Return</strong><br>{total_return:.2f}</div>
    <div class=\"card\"><strong>Max Drawdown</strong><br>{max_drawdown:.2f}</div>
  </div>

  <h2>Signals</h2>
  <table>
    <thead>
      <tr>
        <th>Timeframe</th>
        <th>Market State</th>
        <th>Signal Type</th>
        <th>Signal Reason</th>
      </tr>
    </thead>
    <tbody>
      {signal_rows_html or '<tr><td colspan="4">No signals available.</td></tr>'}
    </tbody>
  </table>

  <h2>Best Results</h2>
  <table>
    <thead>
      <tr>
        <th>Strategy</th>
        <th>Objective</th>
      </tr>
    </thead>
    <tbody>
      {opt_rows_html or '<tr><td colspan="2">No optimization results available.</td></tr>'}
    </tbody>
  </table>
</body>
</html>
"""

    out.write_text(html, encoding="utf-8")
    return str(out)
