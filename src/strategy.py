from __future__ import annotations

import pandas as pd


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def calculate_sma(series: pd.Series, window: int) -> pd.Series:
    values = safe_numeric(series)
    return values.rolling(window=window, min_periods=window).mean()


def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    values = safe_numeric(series)
    return values.ewm(span=span, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    values = safe_numeric(series)
    delta = values.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calculate_bollinger(df: pd.DataFrame, window: int = 20, k: float = 2.0) -> pd.DataFrame:
    close = safe_numeric(df["close"])
    mid = close.rolling(window=window, min_periods=window).mean()
    std = close.rolling(window=window, min_periods=window).std(ddof=0)
    upper = mid + k * std
    lower = mid - k * std
    df["boll_mid"] = mid
    df["boll_upper"] = upper
    df["boll_lower"] = lower
    df["boll_width"] = upper - lower
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr"] = tr.rolling(window=period, min_periods=period).mean()
    return df


def calculate_dmi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    high = safe_numeric(df["high"])
    low = safe_numeric(df["low"])
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    up_move = (high - prev_high).clip(lower=0)
    down_move = (prev_low - low).clip(lower=0)

    plus_dm = up_move.where(up_move > down_move, 0)
    minus_dm = down_move.where(down_move > up_move, 0)

    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_low).abs(),
            (low - prev_high).abs(),
        ],
        axis=1,
    ).max(axis=1)

    plus_di = (
        100 * plus_dm.rolling(window=period, min_periods=period).sum()
        / tr.rolling(window=period, min_periods=period).sum()
    ).fillna(0)
    minus_di = (
        100 * minus_dm.rolling(window=period, min_periods=period).sum()
        / tr.rolling(window=period, min_periods=period).sum()
    ).fillna(0)
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)).fillna(0)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()

    df["dmi_plus"] = plus_di
    df["dmi_minus"] = minus_di
    df["adx"] = adx
    return df


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    close = safe_numeric(df["close"])
    ema_fast = calculate_ema(close, fast)
    ema_slow = calculate_ema(close, slow)
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal

    df["ema_12"] = ema_fast
    df["ema_26"] = ema_slow
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["macd_hist"] = macd_hist
    return df


def enrich_market_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["close"] = safe_numeric(df["close"])
    df["high"] = safe_numeric(df["high"])
    df["low"] = safe_numeric(df["low"])
    df["open"] = safe_numeric(df["open"])
    df["volume"] = safe_numeric(df["volume"])

    df["sma_5"] = calculate_sma(df["close"], 5)
    df["sma_10"] = calculate_sma(df["close"], 10)
    df["sma_20"] = calculate_sma(df["close"], 20)
    df["ema_12"] = calculate_ema(df["close"], 12)
    df["ema_26"] = calculate_ema(df["close"], 26)

    df = calculate_macd(df, fast=12, slow=26, signal=9)
    df["rsi_14"] = calculate_rsi(df["close"], 14)
    df = calculate_bollinger(df)
    df = calculate_atr(df)
    df = calculate_dmi(df)
    df["rsi"] = df["rsi_14"]
    return df
