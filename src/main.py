from __future__ import annotations

import html
from typing import Dict, List


def generate_html_report(symbol: str, market_data: Dict[str, dict], strategy_summary: Dict[str, object], signal_summary: Dict[str, object], performance: Dict[str, dict], backtest: Dict[str, object] | None = None) -> str:
    rows = []
    for timeframe, meta in market_data.items():
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(timeframe))}</td>"
            f"<td>{html.escape(str(meta.get('state', '中性')))}</td>"
            f"<td>{meta.get('close', 0.0):.4f}</td>"
            f"<td>{meta.get('rsi', 50.0):.2f}</td>"
            f"<td>{meta.get('macd_hist', 0.0):.4f}</td>"
            "</tr>"
        )

    perf_rows = []
    for signal_name, stats in performance.items():
        perf_rows.append(
            "<tr>"
            f"<td>{html.escape(signal_name)}</td>"
            f"<td>{stats.get('count', 0)}</td>"
            f"<td>{stats.get('win_rate', 0.0):.2%}</td>"
            f"<td>{stats.get('avg_return', 0.0):.2%}</td>"
            "</tr>"
        )

    bt = backtest or {}
    html = f"""
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8">
      <title>{html.escape(symbol)} 策略研究报告</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; background: #0f172a; color: #e2e8f0; }}
        .card {{ background: #111827; border: 1px solid #334155; border-radius: 12px; padding: 18px; margin-bottom: 16px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #334155; padding: 10px; text-align: left; }}
        th {{ background: #1e293b; }}
        h2 {{ margin-top: 24px; }}
      </style>
    </head>
    <body>
      <h1>{html.escape(symbol)} 永续合约量化策略分析报告</h1>

      <div class="card">
        <h2>1. 当前市场状态</h2>
        <table>
          <thead><tr><th>周期</th><th>状态</th><th>收盘</th><th>RSI</th><th>MACD Hist</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>

      <div class="card">
        <h2>2. 当前有效信号</h2>
        <p>信号类型：{html.escape(str(signal_summary.get('signal_type', 'none')))}</p>
        <p>依据：{html.escape(str(signal_summary.get('signal_reason', '无明确信号')))}</p>
        <p>多周期结论：{html.escape(str(strategy_summary.get('market_state', '中性')))}</p>
      </div>

      <div class="card">
        <h2>3. 历史胜率与样本数量</h2>
        <table>
          <thead><tr><th>信号</th><th>样本数</th><th>胜率</th><th>平均收益</th></tr></thead>
          <tbody>{''.join(perf_rows)}</tbody>
        </table>
      </div>

      <div class="card">
        <h2>4. 回测摘要</h2>
        <p>总收益率：{bt.get('total_return', 0.0):.2%}</p>
        <p>净利润：{bt.get('net_profit', 0.0):.2f}</p>
        <p>最大回撤：{bt.get('max_drawdown', 0.0):.2%}</p>
        <p>交易次数：{bt.get('trades', 0)}</p>
        <p>命中率：{bt.get('win_rate', 0.0):.2%}</p>
      </div>
    </body>
    </html>
    """
    return html


def write_html_report(symbol: str, market_data: Dict[str, dict], strategy_summary: Dict[str, object], signal_summary: Dict[str, object], performance: Dict[str, dict], backtest: Dict[str, object] | None = None, report_path: str = "reports/analysis_report.html") -> str:
    html_text = generate_html_report(symbol, market_data, strategy_summary, signal_summary, performance, backtest)
    with open(report_path, "w", encoding="utf-8") as fp:
        fp.write(html_text)
    return report_path


__all__ = [
    "generate_html_report",
    "write_html_report",
]
