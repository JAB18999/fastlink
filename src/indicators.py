from __future__ import annotations

import os
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd
import requests

from src.config import DEFAULT_LIMIT, OKX_BASE_URL, RAW_DATA_DIR


class OkxCandlesClient:
    def __init__(self, base_url: str = OKX_BASE_URL):
        self.base_url = base_url

    def fetch_klines(self, inst_id: str, bar: str, limit: int = DEFAULT_LIMIT) -> pd.DataFrame:
        params = {
            "instId": inst_id,
            "bar": bar,
            "limit": limit,
        }
        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "0":
            raise ValueError(f"OKX API error: {payload}")

        raw_data = payload.get("data", [])
        if not raw_data:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        records = []
        for item in raw_data:
            if len(item) < 6:
                continue
            ts, open_price, high, low, close, volume, *_ = item
            records.append(
                {
                    "timestamp": pd.to_datetime(int(ts), unit="ms"),
                    "open": float(open_price),
                    "high": float(high),
                    "low": float(low),
                    "close": float(close),
                    "volume": float(volume),
                }
            )

        df = pd.DataFrame(records)
        if df.empty:
            return df
        return df.sort_values("timestamp").reset_index(drop=True)

    def ensure_data_dir(self):
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def save_klines(self, inst_id: str, bar: str, df: pd.DataFrame):
        self.ensure_data_dir()
        file_path = RAW_DATA_DIR / f"{inst_id}_{bar}.csv"
        df.to_csv(file_path, index=False)
        return file_path

    def load_klines(self, inst_id: str, bar: str) -> pd.DataFrame:
        file_path = RAW_DATA_DIR / f"{inst_id}_{bar}.csv"
        if not file_path.exists():
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        return pd.read_csv(file_path, parse_dates=["timestamp"])


def fetch_all_timeframes(symbol: str, timeframes: Iterable[str], limit: int = DEFAULT_LIMIT) -> Dict[str, pd.DataFrame]:
    client = OkxCandlesClient()
    result: Dict[str, pd.DataFrame] = {}
    for timeframe in timeframes:
        df = client.fetch_klines(symbol, timeframe, limit=limit)
        result[timeframe] = df
        client.save_klines(symbol, timeframe, df)
    return result


def load_all_timeframes(symbol: str, timeframes: Iterable[str]) -> Dict[str, pd.DataFrame]:
    client = OkxCandlesClient()
    result: Dict[str, pd.DataFrame] = {}
    for timeframe in timeframes:
        result[timeframe] = client.load_klines(symbol, timeframe)
    return result


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _bollinger(series: pd.Series, window: int = 20, k: float = 2.0):
    middle = series.rolling(window=window, min_periods=1).mean()
    std = series.rolling(window=window, min_periods=1).std(ddof=0)
    upper = middle + std * k
    lower = middle - std * k
    return middle, upper, lower


def _dmi(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    up_move = high.diff()
    down_move = low.diff().mul(-1)

    plus_move = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_move = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    atr = (high - low).rolling(window=period, min_periods=1).mean()
    plus_di = (100 * plus_move.rolling(window=period, min_periods=1).sum() / atr.replace(0, np.nan)).fillna(0.0)
    minus_di = (100 * minus_move.rolling(window=period, min_periods=1).sum() / atr.replace(0, np.nan)).fillna(0.0)
    adx = (plus_di - minus_di).abs().rolling(window=period, min_periods=1).mean().fillna(0.0)
    return plus_di.fillna(0.0), minus_di.fillna(0.0), adx.fillna(0.0)


def enrich_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """Add the technical indicator columns expected by the strategy and analytics modules."""
    if df.empty:
        return df.copy()

    result = df.copy()
    close = pd.to_numeric(result["close"], errors="coerce").fillna(method="ffill").fillna(0.0)
    high = pd.to_numeric(result["high"], errors="coerce").fillna(method="ffill").fillna(0.0)
    low = pd.to_numeric(result["low"], errors="coerce").fillna(method="ffill").fillna(0.0)

    if "volume" in result.columns:
        volume = pd.to_numeric(result["volume"], errors="coerce").fillna(0.0)
    else:
        volume = pd.Series(0.0, index=result.index)

    result["ema_12"] = close.ewm(span=12, adjust=False).mean()
    result["ema_26"] = close.ewm(span=26, adjust=False).mean()
    result["rsi"] = _rsi(close, period=14)

    macd_line, macd_signal, macd_hist = _macd(close)
    result["macd_line"] = macd_line
    result["macd_signal"] = macd_signal
    result["macd_hist"] = macd_hist

    boll_middle, boll_upper, boll_lower = _bollinger(close)
    result["boll_middle"] = boll_middle
    result["boll_upper"] = boll_upper
    result["boll_lower"] = boll_lower

    dmi_plus, dmi_minus, adx = _dmi(high, low, close)
    result["dmi_plus"] = dmi_plus
    result["dmi_minus"] = dmi_minus
    result["adx"] = adx

    result["volume"] = volume
    return result


__all__ = [
    "OkxCandlesClient",
    "fetch_all_timeframes",
    "load_all_timeframes",
    "enrich_market_data",
]
