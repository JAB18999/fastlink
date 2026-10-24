from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.config import LOGS_DIR


def append_trade_log(trade: Dict[str, Any], log_path: str = str(LOGS_DIR / "trades.jsonl")) -> str:
    out = Path(log_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(trade, ensure_ascii=False) + "\n")
    return str(out)


def read_trade_log(log_path: str = str(LOGS_DIR / "trades.jsonl")) -> List[Dict[str, Any]]:
    out = Path(log_path)
    if not out.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with out.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def summarize_trade_log(log_path: str = str(LOGS_DIR / "trades.jsonl")) -> Dict[str, Any]:
    rows = read_trade_log(log_path)
    if not rows:
        return {"trades": 0, "wins": 0, "losses": 0, "net_profit": 0.0}

    pnl_values = [float(item.get("pnl", 0.0)) for item in rows if "pnl" in item]
    wins = sum(1 for value in pnl_values if value > 0)
    losses = sum(1 for value in pnl_values if value < 0)
    net_profit = sum(pnl_values)

    return {
        "trades": len(rows),
        "wins": wins,
        "losses": losses,
        "net_profit": net_profit,
    }
