from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from src.config import REPORTS_DIR


def build_report(markdown: str, report_path: str) -> str:
    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    return str(out)


def generate_markdown_report(symbol: str, market_data: Dict[str, dict], strategy_summary: Dict[str, object], signal_summary: Dict[str, object], performance: Dict[str, dict]) -> str:
    lines: List[str] = []
    lines.append(f"# {symbol} 永续合约量化策略分析报告")
    lines.append("")
    lines.append("## 1. 当前市场状态")
    lines.append("")
    for timeframe, meta in market_data.items():
        lines.append(f"- {timeframe}: {meta['state']} | close={meta['close']:.4f} | rsi={meta['rsi']:.2f} | macd_hist={meta['macd_hist']:.4f}")
    lines.append("")
    lines.append("## 2. 当前有效策略信号")
    lines.append("")
    lines.append(f"- 触发信号: {signal_summary.get('signal_type', 'none')}")
    lines.append(f"- 信号依据: {signal_summary.get('signal_reason', '未触发有效信号')}")
    lines.append(f"- 市场状态: {strategy_summary.get('market_state', '中性')}")
    lines.append("")
    lines.append("## 3. 历史胜率与样本数量")
    lines.append("")
    for signal_name, stats in performance.items():
        lines.append(f"- {signal_name}: 样本数={stats.get('count', 0)} | 胜率={stats.get('win_rate', 0.0):.2%} | 平均收益={stats.get('avg_return', 0.0):.2%}")
    lines.append("")
    lines.append("## 4. 策略表现对比")
    lines.append("")
    for item in strategy_summary.get("comparison", []):
        long = item["long_open"]
        short = item["short_open"]
        lines.append(
            f"- {item['timeframe']}: 市场状态={item['market_state']} | 多头开仓胜率={long.get('win_rate', 0.0):.2%} | 空头开仓胜率={short.get('win_rate', 0.0):.2%}"
        )
    lines.append("")
    lines.append("## 5. 结论")
    lines.append("")
    lines.append("- 依据多周期趋势与技术指标，当前盘面仍需要结合具体周期的强弱状态进行动态管理。")
    lines.append("- 本框架可持续积累历史信号样本，用于后续策略稳定性评估和参数优化。")
    lines.append("")
    return "\n".join(lines)


def write_report(symbol: str, market_data: Dict[str, dict], strategy_summary: Dict[str, object], signal_summary: Dict[str, object], performance: Dict[str, dict], report_path: str = str(REPORTS_DIR / "analysis_report.md")) -> str:
    markdown = generate_markdown_report(symbol, market_data, strategy_summary, signal_summary, performance)
    return build_report(markdown, report_path)
