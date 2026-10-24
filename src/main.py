from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _render_metrics_cards(summary: Dict[str, Any]) -> str:
    cards = [
        ("当前状态", summary.get("market_state", "中性")),
        ("当前信号", summary.get("signal_type", "none")),
        ("回测收益", f"{summary.get('total_return', 0.0):.2%}"),
        ("最大回撤", f"{summary.get('max_drawdown', 0.0):.2%}"),
    ]
    return "\n".join(
        f"<div class='card'><h3>{label}</h3><p>{value}</p></div>" for label, value in cards
    )


def _render_signal_table(rows: Iterable[Dict[str, Any]]) -> str:
    html_rows = []
    for row in rows:
        html_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('timeframe', '')))}</td>"
            f"<td>{html.escape(str(row.get('market_state', '')))}</td>"
            f"<td>{html.escape(str(row.get('signal_type', '')))}</td>"
            f"<td>{html.escape(str(row.get('signal_reason', '')))}</td>"
            "</tr>"
        )
    return "".join(html_rows)


def generate_dashboard_html(summary: Dict[str, Any], best_results: Optional[List[Dict[str, Any]]] = None, output_path: str = "reports/dashboard.html") -> str:
    signals = summary.get("signals", [])
    best_results = best_results or []

    best_rows = []
    for result in best_results[:5]:
        best_rows.append(
            "<tr>"
            f"<td>{html.escape(result.get('strategy_name', ''))}</td>"
            f"<td>{html.escape(json.dumps(result.get('params', {}), ensure_ascii=False))}</td>"
            f"<td>{result.get('total_return', 0.0):.2%}</td>"
            f"<td>{result.get('win_rate', 0.0):.2%}</td>"
            "</tr>"
        )

    html_doc = f"""
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8">
      <title>fastlink 策略 dashboard</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; background: #0b1020; color: #e5ecff; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: #151d32; border: 1px solid #273457; border-radius: 12px; padding: 20px; }}
        .card h3 {{ margin: 0 0 8px; font-size: 14px; color: #9bb5ff; }}
        .card p {{ margin: 0; font-size: 24px; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ border: 1px solid #2c3c66; padding: 10px; text-align: left; }}
        th {{ background: #1a2746; }}
        h1, h2 {{ color: #f0f6ff; }}
      </style>
    </head>
    <body>
      <h1>fastlink 策略分析 Dashboard</h1>
      <div class="grid">
        {_render_metrics_cards(summary)}
      </div>

      <h2>多周期信号</h2>
      <table>
        <thead>
          <tr>
            <th>周期</th>
            <th>市场状态</th>
            <th>当前信号</th>
            <th>依据</th>
          </tr>
        </thead>
        <tbody>
          {_render_signal_table(signals)}
        </tbody>
      </table>

      <h2>最优策略参数</h2>
      <table>
        <thead>
          <tr>
            <th>策略</th>
            <th>参数</th>
            <th>收益率</th>
            <th>命中率</th>
          </tr>
        </thead>
        <tbody>
          {''.join(best_rows) if best_rows else '<tr><td colspan="4">暂无优化结果</td></tr>'}
        </tbody>
      </table>
    </body>
    </html>
    """

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    return str(out_path)
