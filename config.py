"""
앱 전역 설정 및 상수
"""

import os

# --- 파일 경로 ---
SAVE_FILE = "boss_data.json"       # 레거시 (마이그레이션 후 미사용)
DB_FILE = "boss_data.db"           # SQLite DB
PARQUET_FILE = "stats_snapshot.parquet"  # Polars 통계용 스냅샷
IMAGE_DIR = "character_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# --- Nexon API ---
API_KEY = "add_your_api_key"
NEXON_API_BASE = "https://open.api.nexon.com/maplestory/v1"

# --- 기본 보스 목록 ---
DEFAULT_BOSSES = [
    {"text": "보스1", "value": 1_000_000},
    {"text": "보스2", "value": 3_000_000},
    {"text": "보스3", "value": 500_000},
]

# --- UI 크기 ---
WINDOW_WIDTH = 1050
WINDOW_HEIGHT = 875
WINDOW_X = 300
WINDOW_Y = 200

SIDEBAR_WIDTH = 85
SIDEBAR_ICON_SIZE = 55
