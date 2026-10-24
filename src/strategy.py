from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Iterable, List

from src.analytics import evaluate_signal_performance
from src.backtest import run_backtest
from src.charts import plot_equity_curve, plot_signal_overlay
from src.config import DEFAULT_LIMIT, DEFAULT_LOOKAHEAD, DEFAULT_SYMBOL, LOGS_DIR, OPTIMIZATION_DIR, REPORTS_DIR, TIMEFRAMES
from src.dashboard import generate_dashboard_html
from src.data_manager import fetch_all_timeframes, load_all_timeframes
from src.indicators import enrich_market_data
from src.optimizer import optimize_strategies
from src.reporter import write_html_report
from src.storage import save_analysis_run, save_strategy_run
from src.strategy import classify_market_state, generate_signal_history, get_latest_signal
from src.strategy_combo import aggregate_timeframe_bias, generate_combined_signal_history
from src.trade_logger import append_trade_log, summarize_trade_log


def load_or_fetch_market_data(symbol: str, timeframes: Iterable[str], limit: int) -> Dict[str, Any]:
    frames = load_all_timeframes(symbol, list(timeframes))
    missing = {tf: df for tf, df in frames.items() if df.empty}
    if missing:
        fetched = fetch_all_timeframes(symbol, list(missing.keys()), limit=limit)
        frames.update(fetched)
    return frames


def analyze_symbol(
    symbol: str,
    timeframes: Iterable[str],
    limit: int = DEFAULT_LIMIT,
    lookahead: int = DEFAULT_LOOKAHEAD,
    strategy_name: str = "trend_following",
    run_backtest_flag: bool = False,
    optimize_flag: bool = False,
    dashboard_flag: bool = False,
    generate_charts: bool = False,
) -> Dict[str, Any]:
    frames = load_or_fetch_market_data(symbol, timeframes, limit)
    enriched: Dict[str, Any] = {}
    market_data: Dict[str, Any] = {}
    comparisons: List[Dict[str, Any]] = []
    primary_df: Any = None

    for timeframe, df in frames.items():
        if df.empty:
            continue
        chart = enrich_market_data(df)
        if strategy_name == "combo":
            chart = generate_combined_signal_history(chart)
        else:
            chart = generate_signal_history(chart, strategy_name=strategy_name)
        chart["state"] = chart.apply(lambda row: classify_market_state(chart.iloc[: row.name + 1]).get("state", "中性"), axis=1)
        enriched[timeframe] = chart

        if primary_df is None:
            primary_df = chart

        state = classify_market_state(chart)
        market_data[timeframe] = {
            "state": state.get("state", "中性"),
            "close": float(chart.iloc[-1].get("close", 0.0)),
            "rsi": float(chart.iloc[-1].get("rsi", 50.0)),
            "macd_hist": float(chart.iloc[-1].get("macd_hist", 0.0)),
        }

        perf = evaluate_signal_performance(chart, lookahead=lookahead)
        latest_signal = get_latest_signal(chart, strategy_name=strategy_name)
        comparisons.append(
            {
                "timeframe": timeframe,
                "market_state": state.get("state", "中性"),
                "signal_type": latest_signal.get("signal_type", "none"),
                "signal_reason": latest_signal.get("signal_reason", ""),
                "long_open": perf.get("long_open", {"count": 0, "win_rate": 0.0, "avg_return": 0.0}),
                "short_open": perf.get("short_open", {"count": 0, "win_rate": 0.0, "avg_return": 0.0}),
            }
        )

    if primary_df is None:
        raise ValueError(f"No market data available for symbol {symbol}")

    signal_summary = get_latest_signal(primary_df, strategy_name=strategy_name)
    performance = evaluate_signal_performance(primary_df, lookahead=lookahead)
    strategy_summary = {
        "market_state": signal_summary.get("state", "中性"),
        "comparison": comparisons,
    }

    report_md_path = str(REPORTS_DIR / f"{symbol.replace('/', '_')}_analysis.md")
    report_html_path = str(REPORTS_DIR / f"{symbol.replace('/', '_')}_analysis.html")

    analysis_summary: Dict[str, Any] = {
        "symbol": symbol,
        "timeframes": list(timeframes),
        "market_data": market_data,
        "signal_summary": signal_summary,
        "strategy_summary": strategy_summary,
        "performance": performance,
        "report_path": report_md_path,
        "html_report_path": report_html_path,
    }

    if strategy_name == "combo":
        combo_bias = aggregate_timeframe_bias(enriched)
        analysis_summary["combo_bias"] = combo_bias

    if generate_charts and not primary_df.empty:
        signal_chart = plot_signal_overlay(primary_df, str(REPORTS_DIR / f"{symbol.replace('/', '_')}_signal_overlay.png"))
        analysis_summary["signal_chart_path"] = signal_chart

    if run_backtest_flag:
        bt = run_backtest(primary_df, strategy_name=strategy_name, strategy_mode="combo" if strategy_name == "combo" else "standard")
        analysis_summary["backtest"] = bt
        if generate_charts:
            eq_path = plot_equity_curve(bt["equity_curve"], str(REPORTS_DIR / f"{symbol.replace('/', '_')}_equity_curve.png"))
            analysis_summary["equity_curve_path"] = eq_path
        for trade in bt["trade_log"]:
            if "type" in trade and trade["type"].endswith(("open", "add", "reduce", "close")):
                append_trade_log(trade, str(LOGS_DIR / "trades.jsonl"))
        analysis_summary["trade_log_summary"] = summarize_trade_log(str(LOGS_DIR / "trades.jsonl"))
        save_strategy_run(symbol, strategy_name, bt["params"], bt)
        save_analysis_run(symbol, "multi", signal_summary.get("state", "中性"), signal_summary.get("signal_type", "none"), signal_summary.get("signal_reason", ""), report_html_path)

    if optimize_flag:
        best_results = optimize_strategies(primary_df, strategy_names=[strategy_name], save_path=str(OPTIMIZATION_DIR / "best_params.json"))
        analysis_summary["optimization"] = best_results

    if dashboard_flag:
        best_results = analysis_summary.get("optimization", [])
        summary_for_dashboard = {
            "market_state": signal_summary.get("state", "中性"),
            "signal_type": signal_summary.get("signal_type", "none"),
            "total_return": analysis_summary.get("backtest", {}).get("total_return", 0.0),
            "max_drawdown": analysis_summary.get("backtest", {}).get("max_drawdown", 0.0),
            "signals": [
                {
                    "timeframe": timeframe,
                    "market_state": meta["state"],
                    "signal_type": get_latest_signal(enriched[timeframe], strategy_name=strategy_name).get("signal_type", "none"),
                    "signal_reason": get_latest_signal(enriched[timeframe], strategy_name=strategy_name).get("signal_reason", ""),
                }
                for timeframe, meta in market_data.items()
            ],
        }
        dashboard_path = str(REPORTS_DIR / "dashboard.html")
        analysis_summary["dashboard_path"] = generate_dashboard_html(summary_for_dashboard, best_results, dashboard_path)

    write_html_report(symbol, market_data, strategy_summary, signal_summary, performance, analysis_summary.get("backtest"), report_html_path)
    return analysis_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="SOL 永续合约量化策略分析系统")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help="交易对，例如 SOL-USDT-SWAP")
    parser.add_argument("--timeframes", nargs="*", default=TIMEFRAMES, help="分析周期，例如 5m 15m 1H")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="下载 K 线数据数量")
    parser.add_argument("--lookahead", type=int, default=DEFAULT_LOOKAHEAD, help="胜率评估的未来窗口长度")
    parser.add_argument("--strategy", default="trend_following", choices=["trend_following", "combo"], help="策略名称")
    parser.add_argument("--run-backtest", action="store_true", help="执行回测并记录交易日志")
    parser.add_argument("--optimize", action="store_true", help="进行参数优化搜索")
    parser.add_argument("--dashboard", action="store_true", help="生成 dashboard HTML 页面")
    parser.add_argument("--charts", action="store_true", help="生成图表")
    args = parser.parse_args()

    result = analyze_symbol(
        args.symbol,
        args.timeframes,
        limit=args.limit,
        lookahead=args.lookahead,
        strategy_name=args.strategy,
        run_backtest_flag=args.run_backtest,
        optimize_flag=args.optimize,
        dashboard_flag=args.dashboard,
        generate_charts=args.charts,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
