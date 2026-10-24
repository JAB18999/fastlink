from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List

from src.analytics import evaluate_signal_performance, summarize_strategy_comparison
from src.config import DEFAULT_LIMIT, DEFAULT_LOOKAHEAD, DEFAULT_SYMBOL, REPORTS_DIR, TIMEFRAMES
from src.data_manager import fetch_all_timeframes, load_all_timeframes
from src.indicators import enrich_market_data
from src.reporter import write_report
from src.strategy import classify_market_state, generate_signal_history, get_latest_signal


def load_or_fetch_market_data(symbol: str, timeframes: Iterable[str], limit: int) -> Dict[str, dict]:
    frames = load_all_timeframes(symbol, list(timeframes))
    missing = {tf: df for tf, df in frames.items() if df.empty}
    if missing:
        fetched = fetch_all_timeframes(symbol, list(missing.keys()), limit=limit)
        frames.update(fetched)
    return frames


def analyze_symbol(symbol: str, timeframes: Iterable[str], limit: int = DEFAULT_LIMIT, lookahead: int = DEFAULT_LOOKAHEAD) -> Dict[str, object]:
    frames = load_or_fetch_market_data(symbol, timeframes, limit)
    enriched: Dict[str, dict] = {}
    comparison: List[dict] = []

    for timeframe, df in frames.items():
        if df.empty:
            continue
        chart = enrich_market_data(df)
        signal_history = generate_signal_history(chart)
        signal_history["state"] = signal_history.apply(lambda row: classify_market_state(signal_history.iloc[: row.name + 1]).get("state"), axis=1)
        signal_history["signal_type"] = signal_history["signal_type"].fillna("none")
        enriched[timeframe] = signal_history

        comparison.append(
            {
                "timeframe": timeframe,
                "market_state": classify_market_state(signal_history).get("state", "中性"),
                "long_open": evaluate_signal_performance(signal_history, lookahead=lookahead).get("long_open", {"count": 0, "win_rate": 0.0, "avg_return": 0.0}),
                "short_open": evaluate_signal_performance(signal_history, lookahead=lookahead).get("short_open", {"count": 0, "win_rate": 0.0, "avg_return": 0.0}),
            }
        )

    market_data = {}
    for timeframe, chart in enriched.items():
        latest = chart.iloc[-1]
        state_info = classify_market_state(chart)
        market_data[timeframe] = {
            "state": state_info.get("state", "中性"),
            "close": float(latest.get("close", 0.0)),
            "rsi": float(latest.get("rsi", 50.0)),
            "macd_hist": float(latest.get("macd_hist", 0.0)),
        }

    signal_summary = get_latest_signal(enriched[timeframes[0]]) if enriched else {"signal_type": "none", "signal_reason": "无数据"}
    performance = evaluate_signal_performance(enriched[timeframes[0]], lookahead=lookahead) if enriched else {}

    strategy_summary = {
        "market_state": signal_summary.get("state", "中性"),
        "comparison": comparison,
    }

    report_path = str(REPORTS_DIR / f"{symbol.replace('/', '_')}_analysis.md")
    write_report(symbol, market_data, strategy_summary, signal_summary, performance, report_path)

    return {
        "symbol": symbol,
        "timeframes": list(timeframes),
        "market_data": market_data,
        "signal_summary": signal_summary,
        "strategy_summary": strategy_summary,
        "performance": performance,
        "report_path": report_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SOL 永续合约量化策略分析系统")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help="交易对，例如 BTC-USDT-SWAP")
    parser.add_argument("--timeframes", nargs="*", default=TIMEFRAMES, help="分析周期，例如 5m 15m 1H")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="下载的 K 线数量")
    parser.add_argument("--lookahead", type=int, default=DEFAULT_LOOKAHEAD, help="回看收益窗口（K 线数量）")
    args = parser.parse_args()

    result = analyze_symbol(args.symbol, args.timeframes, limit=args.limit, lookahead=args.lookahead)
    print(json.dumps({
        "symbol": result["symbol"],
        "market_data": result["market_data"],
        "signal_summary": result["signal_summary"],
        "strategy_summary": result["strategy_summary"],
        "performance": result["performance"],
        "report_path": result["report_path"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
