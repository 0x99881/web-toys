from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "system_config.json"
DATA_FILE_PATTERNS = ["BM2记录_*.xlsx", "BM2璁板綍_*.xlsx"]

DEFAULT_MEMBERS = [
    "zj", "bb", "hd", "hp", "xys", "ryl", "gpp", "gsh", "gj", "dcl", "ys", "gmj",
    "zt", "gyg", "dtjdx", "dtjpj", "dtjgege", "jshxh", "qhy", "zad", "whj", "hmj",
]
DEFAULT_QUICK_SCORES = [18, 17, 12, 3, 2, 0]

ENABLED = "启用"
DISABLED = "停用"
WINDOW_SIZE = 15

SCORE_SHEET = "每日积分记录"
WEAR_SHEET = "每日磨损记录"
INCOME_SHEET = "每日收入记录"
META_SHEET = "_积分列日期"
LEGACY_WEAR_SHEET = "旧磨损记录"

SCORE_SHEET_ALIASES = [SCORE_SHEET, "姣忔棩绉垎璁板綍"]
WEAR_SHEET_ALIASES = [WEAR_SHEET, "姣忔棩纾ㄦ崯璁板綍"]
INCOME_SHEET_ALIASES = [INCOME_SHEET]
META_SHEET_ALIASES = [META_SHEET, "_绉垎鍒楁棩鏈?"]

TOTAL_HEADER = "总积分"
NAME_HEADER = "姓名"
WEAR_TOTAL_HEADER = "累计磨损"
WEAR_NAME_HEADER = "姓名"
WEAR_META_SHEET = "_磨损列日期"
WEAR_META_SHEET_ALIASES = [WEAR_META_SHEET]
WEAR_META_HEADERS = ["日期", "磨损列"]
INCOME_NAME_HEADER = "姓名"
INCOME_META_SHEET = "_收入列日期"
INCOME_META_SHEET_ALIASES = [INCOME_META_SHEET]
INCOME_META_HEADERS = ["日期", "收入列"]
META_HEADERS = ["日期", "积分列"]

ENABLED_ALIASES = {"启用", "鍚敤"}
DISABLED_ALIASES = {"停用", "鍋滅敤"}
