from __future__ import annotations

from typing import Dict, Iterable

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


__all__ = [
    "OkxCandlesClient",
    "fetch_all_timeframes",
    "load_all_timeframes",
]
