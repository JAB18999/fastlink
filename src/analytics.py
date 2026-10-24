from __future__ import annotations

from typing import Dict, List

import pandas as pd


def classify_market_state(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {"state": "待补充数据", "score": 0.0}

    latest = df.iloc[-1]
    close = float(latest["close"])
    ema_short = float(latest.get("ema_12", close))
    ema_long = float(latest.get("ema_26", close))
    macd_hist = float(latest.get("macd_hist", 0.0))
    rsi = float(latest.get("rsi", 50.0))
    boll_mid = float(latest.get("boll_mid", close))
    boll_upper = float(latest.get("boll_upper", close))
    boll_lower = float(latest.get("boll_lower", close))

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

    return {"state": state, "score": score, "close": close, "ema_short": ema_short, "ema_long": ema_long, "rsi": rsi, "macd_hist": macd_hist}


def generate_signal_history(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    result["signal_type"] = "none"
    result["signal_reason"] = ""

    for idx in range(len(result)):
        row = result.iloc[idx]
        prev_row = result.iloc[idx - 1] if idx > 0 else None

        close = float(row["close"])
        ema_short = float(row.get("ema_12", close))
        ema_long = float(row.get("ema_26", close))
        rsi = float(row.get("rsi", 50.0))
        macd_hist = float(row.get("macd_hist", 0.0))
        dmi_plus = float(row.get("dmi_plus", 0.0))
        dmi_minus = float(row.get("dmi_minus", 0.0))

        bullish = close > ema_short > ema_long and macd_hist > 0 and rsi > 55
        bearish = close < ema_short < ema_long and macd_hist < 0 and rsi < 45

        if bullish and dmi_plus >= dmi_minus:
            result.at[idx, "signal_type"] = "long_open"
            result.at[idx, "signal_reason"] = "趋势向上 + MACD>0 + RSI>55 + DMI强度>空头"
        elif close > ema_short and macd_hist > 0 and rsi > 60:
            result.at[idx, "signal_type"] = "long_add"
            result.at[idx, "signal_reason"] = "强势延续，适合加仓"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("long") and close < ema_short and rsi < 50:
            result.at[idx, "signal_type"] = "long_reduce"
            result.at[idx, "signal_reason"] = "多头减仓，防止趋势回撤"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("long") and close < ema_short and macd_hist < 0 and rsi < 45:
            result.at[idx, "signal_type"] = "long_close"
            result.at[idx, "signal_reason"] = "多头趋势反转，执行平仓"
        elif bearish and dmi_minus >= dmi_plus:
            result.at[idx, "signal_type"] = "short_open"
            result.at[idx, "signal_reason"] = "趋势向下 + MACD<0 + RSI<45 + DMI强度>多头"
        elif close < ema_short and macd_hist < 0 and rsi < 40:
            result.at[idx, "signal_type"] = "short_add"
            result.at[idx, "signal_reason"] = "空头延续，适合加仓"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("short") and close > ema_short and rsi > 50:
            result.at[idx, "signal_type"] = "short_reduce"
            result.at[idx, "signal_reason"] = "空头减仓，等待趋势企稳"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("short") and close > ema_short and macd_hist > 0 and rsi > 55:
            result.at[idx, "signal_type"] = "short_close"
            result.at[idx, "signal_reason"] = "空头趋势反转，执行平仓"

    return result


def get_latest_signal(df: pd.DataFrame) -> Dict[str, object]:
    result = generate_signal_history(df)
    if result.empty:
        return {"signal_type": "none", "signal_reason": "无数据"}

    latest = result.iloc[-1]
    return {
        "signal_type": latest.get("signal_type", "none"),
        "signal_reason": latest.get("signal_reason", ""),
        "timestamp": latest.get("timestamp"),
        "close": latest.get("close"),
        "state": classify_market_state(result).get("state", "中性"),
    }
