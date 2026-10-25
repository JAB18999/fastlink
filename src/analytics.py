from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


DEFAULT_STRATEGY_PARAMS = {
    "fast_window": 12,
    "slow_window": 26,
    "rsi_buy": 55,
    "rsi_sell": 45,
    "rsi_add": 60,
    "rsi_reduce": 50,
}


def classify_market_state(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {"state": "待补充数据", "score": 0.0}

    latest = df.iloc[-1]
    close = float(latest["close"])
    ema_short = float(latest.get("ema_12", close))
    ema_long = float(latest.get("ema_26", close))
    macd_hist = float(latest.get("macd_hist", 0.0))
    rsi = float(latest.get("rsi", 50.0))
    boll_lower = float(latest.get("boll_lower", close))
    boll_upper = float(latest.get("boll_upper", close))

    if close > ema_short > ema_long and macd_hist > 0 and rsi > 55:
        state = "强势多头"
        score = 3.0
    elif close > ema_short > ema_long and macd_hist > 0 and rsi >= 50:
        state = "弱势多头"
        score = 2.0
    elif close < ema_short < ema_long and macd_hist < 0 and rsi < 45:
        state = "强势空头"
        score = -3.0
    elif close < ema_short < ema_long and macd_hist < 0 and rsi <= 50:
        state = "弱势空头"
        score = -2.0
    elif boll_lower <= close <= boll_upper:
        state = "箱体震荡"
        score = 0.0
    else:
        state = "中性/待确认"
        score = 0.0

    return {
        "state": state,
        "score": score,
        "close": close,
        "ema_short": ema_short,
        "ema_long": ema_long,
        "rsi": rsi,
        "macd_hist": macd_hist,
    }


def _signal_for_row(row: pd.Series, prev_row: Optional[pd.Series], params: Dict[str, Any]) -> Dict[str, str]:
    close = float(row.get("close", 0))
    ema_short = float(row.get("ema_12", close))
    ema_long = float(row.get("ema_26", close))
    rsi = float(row.get("rsi", 50.0))
    macd_hist = float(row.get("macd_hist", 0.0))
    dmi_plus = float(row.get("dmi_plus", 0.0))
    dmi_minus = float(row.get("dmi_minus", 0.0))

    rsi_buy = float(params.get("rsi_buy", 55))
    rsi_sell = float(params.get("rsi_sell", 45))
    rsi_add = float(params.get("rsi_add", 60))
    rsi_reduce = float(params.get("rsi_reduce", 50))

    bullish = close > ema_short > ema_long and macd_hist > 0 and rsi >= rsi_buy
    bearish = close < ema_short < ema_long and macd_hist < 0 and rsi <= rsi_sell

    if bullish and dmi_plus >= dmi_minus:
        return {"signal_type": "long_open", "signal_reason": "趋势向上 + MACD>0 + RSI>阈值 + DMI强度>空头"}
    if close > ema_short and macd_hist > 0 and rsi >= rsi_add:
        return {"signal_type": "long_add", "signal_reason": "强势延续，适合加仓"}
    if prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("long") and close < ema_short and rsi < rsi_reduce:
        return {"signal_type": "long_reduce", "signal_reason": "多头减仓，防止回撤扩大"}
    if prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("long") and close < ema_short and macd_hist < 0 and rsi <= rsi_sell:
        return {"signal_type": "long_close", "signal_reason": "多头趋势反转，执行平仓"}
    if bearish and dmi_minus >= dmi_plus:
        return {"signal_type": "short_open", "signal_reason": "趋势向下 + MACD<0 + RSI<阈值 + DMI强度>多头"}
    if close < ema_short and macd_hist < 0 and rsi <= (100 - rsi_add):
        return {"signal_type": "short_add", "signal_reason": "空头延续，适合加仓"}
    if prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("short") and close > ema_short and rsi > (100 - rsi_reduce):
        return {"signal_type": "short_reduce", "signal_reason": "空头减仓，等待趋势企稳"}
    if prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("short") and close > ema_short and macd_hist > 0 and rsi >= rsi_buy:
        return {"signal_type": "short_close", "signal_reason": "空头趋势反转，执行平仓"}
    return {"signal_type": "none", "signal_reason": ""}


def generate_signal_history(df: pd.DataFrame, strategy_name: str = "trend_following", params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    if df.empty:
        return df

    params = {**DEFAULT_STRATEGY_PARAMS, **(params or {})}
    result = df.copy()
    result["signal_type"] = "none"
    result["signal_reason"] = ""

    for idx in range(len(result)):
        row = result.iloc[idx]
        prev_row = result.iloc[idx - 1] if idx > 0 else None
        signal = _signal_for_row(row, prev_row, params)
        result.at[idx, "signal_type"] = signal["signal_type"]
        result.at[idx, "signal_reason"] = signal["signal_reason"]

    return result


def _summarize_returns(series: pd.Series) -> Dict[str, Any]:
    values = pd.to_numeric(series, errors="coerce").dropna().tolist()
    count = len(values)
    if count == 0:
        return {"count": 0, "win_rate": 0.0, "avg_return": 0.0}

    wins = sum(1 for value in values if value > 0)
    avg_return = float(sum(values) / count)
    return {
        "count": count,
        "win_rate": float(wins / count),
        "avg_return": avg_return,
    }


def evaluate_signal_performance(df: pd.DataFrame, lookahead: int = 10) -> Dict[str, Dict[str, Any]]:
    if df.empty:
        return {"long_open": {"count": 0, "win_rate": 0.0, "avg_return": 0.0}, "short_open": {"count": 0, "win_rate": 0.0, "avg_return": 0.0}}

    result = generate_signal_history(df)
    if result.empty:
        return {"long_open": {"count": 0, "win_rate": 0.0, "avg_return": 0.0}, "short_open": {"count": 0, "win_rate": 0.0, "avg_return": 0.0}}

    closes = pd.to_numeric(result["close"], errors="coerce")
    future_returns = closes.shift(-int(lookahead)) / closes - 1.0
    metrics: Dict[str, Dict[str, Any]] = {}

    for signal_name in ("long_open", "short_open"):
        signal_mask = result["signal_type"] == signal_name
        if signal_mask.any():
            signal_returns = future_returns[signal_mask].dropna()
            metrics[signal_name] = _summarize_returns(signal_returns)
        else:
            metrics[signal_name] = {"count": 0, "win_rate": 0.0, "avg_return": 0.0}

    return metrics


def get_latest_signal(df: pd.DataFrame, strategy_name: str = "trend_following", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = generate_signal_history(df, strategy_name=strategy_name, params=params)
    if result.empty:
        return {"signal_type": "none", "signal_reason": "无数据"}

    latest = result.iloc[-1]
    state = classify_market_state(result)
    return {
        "signal_type": latest.get("signal_type", "none"),
        "signal_reason": latest.get("signal_reason", ""),
        "timestamp": latest.get("timestamp"),
        "close": float(latest.get("close", 0.0)),
        "state": state.get("state", "中性"),
    }


__all__ = [
    "DEFAULT_STRATEGY_PARAMS",
    "classify_market_state",
    "generate_signal_history",
    "evaluate_signal_performance",
    "get_latest_signal",
]
