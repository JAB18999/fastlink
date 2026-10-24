from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


DEFAULT_STRATEGY_PARAMS = {
    "fast_window": 12,
    "slow_window": 26,
    "rsi_buy": 55,
    "rsi_sell": 45,
    "rsi_add": 60,
    "rsi_reduce": 50,
    "boll_band": 2.0,
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


def aggregate_multi_timeframe_signals(frames: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    if not frames:
        return {"signal_type": "none", "signal_reason": "无数据"}

    results = []
    for timeframe, df in frames.items():
        if df.empty:
            continue
        result = classify_market_state(df)
        signal = get_latest_signal(df)
        results.append(
            {
                "timeframe": timeframe,
                "market_state": result["state"],
                "signal": signal["signal_type"],
                "score": result["score"],
            }
        )

    bullish_count = sum(1 for item in results if item["market_state"] in {"强势多头", "弱势多头"})
    bearish_count = sum(1 for item in results if item["market_state"] in {"强势空头", "弱势空头"})

    if bullish_count > bearish_count:
        signal_type = "long_bias"
        reason = "多周期趋势偏多，适合观察多头机会"
    elif bearish_count > bullish_count:
        signal_type = "short_bias"
        reason = "多周期趋势偏空，适合观察空头机会"
    else:
        signal_type = "range_bias"
        reason = "多周期趋势偏震荡，适合区间交易"

    return {"signal_type": signal_type, "signal_reason": reason, "details": results}


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
    "aggregate_multi_timeframe_signals",
    "get_latest_signal",
]
