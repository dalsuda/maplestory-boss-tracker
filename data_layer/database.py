"""
SQLite 연결 및 테이블 초기화 담당.
앱 시작 시 한 번만 호출하면 됩니다.
"""

import sqlite3
from config import DB_FILE


def get_connection() -> sqlite3.Connection:
    """DB 연결 반환. Row를 dict처럼 접근 가능하게 설정."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # row["컬럼명"] 형태로 접근 가능
    conn.execute("PRAGMA journal_mode=WAL")  # 동시 읽기 성능 향상
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """테이블이 없으면 생성. 앱 시작 시 한 번 호출."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS characters (
                name        TEXT PRIMARY KEY,
                ocid        TEXT,
                level       INTEGER,
                job         TEXT,
                power       INTEGER,
                image_url   TEXT
            );

            CREATE TABLE IF NOT EXISTS boss_list (
                name        TEXT PRIMARY KEY,
                value       INTEGER
            );

            -- 보스 시세 변경 이력
            CREATE TABLE IF NOT EXISTS boss_price_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                boss_name       TEXT NOT NULL,
                value           INTEGER NOT NULL,
                applied_from    TEXT NOT NULL,   -- 적용 시작 주차 ex) "2025-10"
                note            TEXT             -- ex) "1분기 패치 반영"
            );

            -- 주차별 체크 상태 (체크 당시 시세 스냅샷)
            CREATE TABLE IF NOT EXISTS weekly_checks (
                week_key    TEXT NOT NULL,
                character   TEXT NOT NULL,
                boss_name   TEXT NOT NULL,
                boss_value  INTEGER NOT NULL,    -- 체크 당시 시세 고정
                checked     INTEGER DEFAULT 0,
                PRIMARY KEY (week_key, character, boss_name)
            );
        """)
