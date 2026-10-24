from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
REPORTS_DIR = ROOT_DIR / "reports"

TIMEFRAMES = ["5m", "15m", "30m", "1H", "2H"]
DEFAULT_SYMBOL = os.getenv("FASTLINK_SYMBOL", "BTC-USDT-SWAP")
DEFAULT_LIMIT = int(os.getenv("FASTLINK_LIMIT", "200"))
DEFAULT_LOOKAHEAD = int(os.getenv("FASTLINK_LOOKAHEAD", "12"))

OKX_BASE_URL = "https://www.okx.com/api/v5/market/candles"
OKX_SYMBOLS = [
    "BTC-USDT-SWAP",
    "ETH-USDT-SWAP",
    "SOL-USDT-SWAP",
]
