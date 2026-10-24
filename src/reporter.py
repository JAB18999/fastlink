from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import DATA_DIR


DB_PATH = DATA_DIR / "fastlink.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timeframe TEXT,
                market_state TEXT,
                signal_type TEXT,
                signal_reason TEXT,
                report_path TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS strategy_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                strategy_name TEXT,
                params_json TEXT,
                total_return REAL,
                net_profit REAL,
                win_rate REAL,
                max_drawdown REAL,
                trade_count INTEGER,
                created_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_analysis_run(symbol: str, timeframe: str, market_state: str, signal_type: str, signal_reason: str, report_path: str) -> int:
    init_db()
    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO analysis_runs (symbol, timeframe, market_state, signal_type, signal_reason, report_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                timeframe,
                market_state,
                signal_type,
                signal_reason,
                report_path,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def save_strategy_run(symbol: str, strategy_name: str, params: Dict[str, Any], result: Dict[str, Any]) -> int:
    init_db()
    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO strategy_runs (symbol, strategy_name, params_json, total_return, net_profit, win_rate, max_drawdown, trade_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                strategy_name,
                json.dumps(params, ensure_ascii=False),
                float(result.get("total_return", 0.0)),
                float(result.get("net_profit", 0.0)),
                float(result.get("win_rate", 0.0)),
                float(result.get("max_drawdown", 0.0)),
                int(result.get("trades", 0)),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def get_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
    init_db()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM analysis_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_recent_strategy_runs(limit: int = 10) -> List[Dict[str, Any]]:
    init_db()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM strategy_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
