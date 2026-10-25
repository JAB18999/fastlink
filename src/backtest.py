from __future__ import annotations

import html
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
        "combo_long_open",
        "combo_short_open",
        "combo_long_add",
        "combo_short_add",
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


def run_backtest(
    df: pd.DataFrame,
    *,
    initial_capital: float = 10000.0,
    fee_rate: float = 0.0003,
    strategy_name: str = "default",
    lookahead: int = 12,
) -> Dict[str, object]:
    """Simple backtest stub used by the report generator.

    This function is intentionally lightweight: it validates the dataframe,
    computes a basic PnL based on signal_type, and returns summary metrics.
    """
    if df.empty:
        return {
            "strategy_name": strategy_name,
            "initial_capital": float(initial_capital),
            "final_value": float(initial_capital),
            "total_return": 0.0,
            "net_profit": 0.0,
            "win_rate": 0.0,
            "trades": 0,
            "max_drawdown": 0.0,
            "summary": {"num_trades": 0},
        }

    if "close" not in df.columns:
        raise ValueError("DataFrame must include a 'close' column for backtesting")

    close = pd.to_numeric(df["close"], errors="coerce")
    signal_series = df["signal_type"] if "signal_type" in df.columns else pd.Series(["" for _ in range(len(df))], index=df.index)

    cash = float(initial_capital)
    position = 0
    entry_price = 0.0
    trades = 0
    wins = 0
    equity_curve: List[float] = []
    max_equity = float(initial_capital)
    min_equity = float(initial_capital)

    for idx, row in df.iterrows():
        signal = str(signal_series.loc[idx]).strip().lower()
        price = float(close.loc[idx])
        if pd.isna(price):
            continue

        if signal in {"long_open", "buy", "long_add"} and position == 0:
            position = 1
            entry_price = price
        elif signal in {"long_close", "sell", "short_open"} and position == 1:
            pnl_ratio = (price - entry_price) / entry_price if entry_price else 0.0
            cash = cash * (1.0 + pnl_ratio - fee_rate)
            trades += 1
            if pnl_ratio > 0:
                wins += 1
            position = 0
            entry_price = 0.0

        equity_curve.append(cash)
        max_equity = max(max_equity, cash)
        min_equity = min(min_equity, cash)

    final_value = cash
    total_return = (final_value / initial_capital) - 1.0 if initial_capital else 0.0
    net_profit = final_value - initial_capital
    win_rate = (wins / trades) if trades else 0.0
    max_drawdown = (max_equity - min_equity) / max_equity if max_equity else 0.0

    return {
        "strategy_name": strategy_name,
        "initial_capital": float(initial_capital),
        "final_value": float(final_value),
        "total_return": float(total_return),
        "net_profit": float(net_profit),
        "win_rate": float(win_rate),
        "trades": int(trades),
        "max_drawdown": float(max_drawdown),
        "summary": {
            "num_trades": int(trades),
            "lookahead": int(lookahead),
            "fee_rate": float(fee_rate),
        },
    }


def generate_html_report(symbol: str, market_data: Dict[str, dict], strategy_summary: Dict[str, object], signal_summary: Dict[str, object], performance: Dict[str, dict], backtest: Dict[str, object] = None) -> str:
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


def write_html_report(symbol: str, market_data: Dict[str, dict], strategy_summary: Dict[str, object], signal_summary: Dict[str, object], performance: Dict[str, dict], backtest: Dict[str, object], report_path: str) -> str:
    html_text = generate_html_report(symbol, market_data, strategy_summary, signal_summary, performance, backtest)
    with open(report_path, "w", encoding="utf-8") as fp:
        fp.write(html_text)
    return report_path
