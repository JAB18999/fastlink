from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.backtest import run_backtest
from src.config import OPTIMIZATION_DIR


DEFAULT_STRATEGY_SEARCH_SPACE = {
    "trend_following": {
        "fast_window": [8, 10, 12, 14],
        "slow_window": [20, 24, 26, 30],
        "rsi_buy": [50, 55, 60],
        "rsi_sell": [40, 45, 50],
        "rsi_add": [55, 60, 65],
        "rsi_reduce": [45, 50, 55],
    }
}


def _generate_param_grid(search_space: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    keys = list(search_space.keys())
    values = [search_space[key] for key in keys]
    grid: List[Dict[str, Any]] = []
    for combo in itertools.product(*values):
        grid.append(dict(zip(keys, combo)))
    return grid


def optimize_strategies(df, strategy_names: Optional[Iterable[str]] = None, save_path: Optional[str] = None) -> List[Dict[str, Any]]:
    strategy_names = list(strategy_names) if strategy_names else list(DEFAULT_STRATEGY_SEARCH_SPACE.keys())
    results: List[Dict[str, Any]] = []

    for strategy_name in strategy_names:
        search_space = DEFAULT_STRATEGY_SEARCH_SPACE.get(strategy_name, {})
        for params in _generate_param_grid(search_space):
            result = run_backtest(df, strategy_name=strategy_name, params=params)
            if result["trades"] == 0:
                continue
            item = {
                "strategy_name": strategy_name,
                "params": params,
                "total_return": result["total_return"],
                "net_profit": result["net_profit"],
                "win_rate": result["win_rate"],
                "trades": result["trades"],
                "max_drawdown": result["max_drawdown"],
            }
            results.append(item)

    results.sort(key=lambda x: (x["total_return"], x["win_rate"]), reverse=True)
    top_results = results[:10]

    if save_path is None:
        save_path = str(Path(OPTIMIZATION_DIR) / "best_params.json")
    out_path = Path(save_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(top_results, ensure_ascii=False, indent=2), encoding="utf-8")
    return top_results
