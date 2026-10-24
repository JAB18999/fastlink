from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


def score_market_situation(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0

    latest = df.iloc[-1]
    close = float(latest.get("close", 0.0))
    ema_short = float(latest.get("ema_12", close))
    ema_long = float(latest.get("ema_26", close))
    rsi = float(latest.get("rsi", 50.0))
    macd_hist = float(latest.get("macd_hist", 0.0))
    atr = float(latest.get("atr", 0.0))
    boll_mid = float(latest.get("boll_mid", close))
    boll_upper = float(latest.get("boll_upper", close))
    boll_lower = float(latest.get("boll_lower", close))

    score = 0.0
    if close > ema_short > ema_long:
        score += 1.0
    if close < ema_short < ema_long:
        score -= 1.0
    if macd_hist > 0:
        score += 0.5
    if macd_hist < 0:
        score -= 0.5
    if rsi > 55:
        score += 0.5
    if rsi < 45:
        score -= 0.5
    if close > boll_mid:
        score += 0.3
    if close < boll_mid:
        score -= 0.3
    if atr > 0:
        score += 0.1
    return score


def generate_combined_signal_history(df: pd.DataFrame, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    if df.empty:
        return df

    params = params or {}
    result = df.copy()
    result["signal_type"] = "none"
    result["signal_reason"] = ""

    for idx in range(len(result)):
        row = result.iloc[idx]
        prev_row = result.iloc[idx - 1] if idx > 0 else None

        close = float(row.get("close", 0.0))
        ema_fast = float(row.get("ema_12", close))
        ema_slow = float(row.get("ema_26", close))
        macd_hist = float(row.get("macd_hist", 0.0))
        rsi = float(row.get("rsi", 50.0))
        atr = float(row.get("atr", 0.0))
        boll_mid = float(row.get("boll_mid", close))
        dmi_plus = float(row.get("dmi_plus", 0.0))
        dmi_minus = float(row.get("dmi_minus", 0.0))

        bullish = (
            close > ema_fast > ema_slow
            and macd_hist > 0
            and rsi > params.get("rsi_long", 55)
            and close > boll_mid
        )
        bearish = (
            close < ema_fast < ema_slow
            and macd_hist < 0
            and rsi < params.get("rsi_short", 45)
            and close < boll_mid
        )

        if bullish and dmi_plus >= dmi_minus:
            result.at[idx, "signal_type"] = "combo_long_open"
            result.at[idx, "signal_reason"] = "EMA趋势 + MACD + RSI + BOLL + DMI 共振，形成多头开仓信号"
        elif bearish and dmi_minus >= dmi_plus:
            result.at[idx, "signal_type"] = "combo_short_open"
            result.at[idx, "signal_reason"] = "EMA趋势 + MACD + RSI + BOLL + DMI 共振，形成空头开仓信号"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("combo_long") and close > ema_fast and macd_hist > 0 and rsi > 60:
            result.at[idx, "signal_type"] = "combo_long_add"
            result.at[idx, "signal_reason"] = "多头强度继续增强，执行加仓"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("combo_short") and close < ema_fast and macd_hist < 0 and rsi < 40:
            result.at[idx, "signal_type"] = "combo_short_add"
            result.at[idx, "signal_reason"] = "空头强度继续增强，执行加仓"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("combo_long") and close < ema_fast and rsi < 50:
            result.at[idx, "signal_type"] = "combo_long_reduce"
            result.at[idx, "signal_reason"] = "多头回落，适度减仓"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("combo_short") and close > ema_fast and rsi > 50:
            result.at[idx, "signal_type"] = "combo_short_reduce"
            result.at[idx, "signal_reason"] = "空头回落，适度减仓"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("combo_long") and close < ema_fast and macd_hist < 0:
            result.at[idx, "signal_type"] = "combo_long_close"
            result.at[idx, "signal_reason"] = "多头趋势失效，执行平仓"
        elif prev_row is not None and str(prev_row.get("signal_type", "none")).startswith("combo_short") and close > ema_fast and macd_hist > 0:
            result.at[idx, "signal_type"] = "combo_short_close"
            result.at[idx, "signal_reason"] = "空头趋势失效，执行平仓"

    return result


def aggregate_timeframe_bias(frames: Dict[str, pd.DataFrame], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not frames:
        return {"signal_type": "none", "signal_reason": "无数据"}

    results = []
    for timeframe, df in frames.items():
        if df.empty:
            continue
        combo = generate_combined_signal_history(df, params=params)
        latest = combo.iloc[-1]
        score = score_market_situation(combo)
        results.append(
            {
                "timeframe": timeframe,
                "state_score": score,
                "signal_type": latest.get("signal_type", "none"),
                "signal_reason": latest.get("signal_reason", ""),
            }
        )

    bullish = sum(1 for item in results if item["state_score"] > 0)
    bearish = sum(1 for item in results if item["state_score"] < 0)

    if bullish > bearish:
        return {"signal_type": "combo_long_bias", "signal_reason": "多周期组合策略偏多，适合偏多观察", "details": results}
    if bearish > bullish:
        return {"signal_type": "combo_short_bias", "signal_reason": "多周期组合策略偏空，适合偏空观察", "details": results}
    return {"signal_type": "combo_range_bias", "signal_reason": "多周期组合策略偏震荡，适合区间策略", "details": results}
