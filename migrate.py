"""
boss_data.json → boss_data.db (SQLite) 마이그레이션 스크립트

실행 방법:
    python migrate.py

기존 boss_data.json은 건드리지 않고,
boss_data.db 파일을 새로 생성합니다.
"""

import json
import sqlite3
import os
from datetime import date, timedelta


JSON_FILE = "boss_data.json"
DB_FILE = "boss_data.db"


# ------------------------------------------------------------------
# 주차 계산 (현재 주차)
# ------------------------------------------------------------------

def current_week_key() -> str:
    today = date.today()
    offset = (today.weekday() - 3) % 7
    thursday = today - timedelta(days=offset)
    year, week, _ = thursday.isocalendar()
    return f"{year}-{week}"


# ------------------------------------------------------------------
# DB 초기화
# ------------------------------------------------------------------

def create_tables(conn: sqlite3.Connection) -> None:
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

        CREATE TABLE IF NOT EXISTS boss_price_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            boss_name       TEXT,
            value           INTEGER,
            applied_from    TEXT,
            note            TEXT
        );

        CREATE TABLE IF NOT EXISTS weekly_checks (
            week_key    TEXT,
            character   TEXT,
            boss_name   TEXT,
            boss_value  INTEGER,
            checked     INTEGER DEFAULT 0,
            PRIMARY KEY (week_key, character, boss_name)
        );
    """)
    conn.commit()


# ------------------------------------------------------------------
# 마이그레이션
# ------------------------------------------------------------------

def migrate(json_path: str, db_path: str) -> None:
    if not os.path.exists(json_path):
        print(f"❌ {json_path} 파일을 찾을 수 없습니다.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(db_path)
    create_tables(conn)

    today_week = current_week_key()
    migrated = {"characters": 0, "boss_list": 0, "weekly_checks": 0}

    # --- 1. boss_list ---
    for boss in data.get("boss_list", []):
        conn.execute(
            "INSERT OR REPLACE INTO boss_list (name, value) VALUES (?, ?)",
            (boss["text"], boss["value"])
        )
        # 시세 이력 초기 기록 (마이그레이션 시점)
        conn.execute(
            "INSERT INTO boss_price_history (boss_name, value, applied_from, note) VALUES (?, ?, ?, ?)",
            (boss["text"], boss["value"], today_week, "JSON 마이그레이션 초기값")
        )
        migrated["boss_list"] += 1

    # --- 2. characters ---
    for name, info in data.get("characters", {}).items():
        conn.execute(
            """INSERT OR REPLACE INTO characters (name, ocid, level, job, power, image_url)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                name,
                info.get("ocid"),
                info.get("level"),
                info.get("job"),
                info.get("power"),
                info.get("character_image"),
            )
        )
        migrated["characters"] += 1

    # --- 3. weekly_checks ---
    for week_key, chars in data.get("weeks", {}).items():
        for char_name, char_data in chars.items():
            bosses = char_data.get("bosses", []) if isinstance(char_data, dict) else char_data
            for boss in bosses:
                if not isinstance(boss, dict):
                    continue
                conn.execute(
                    """INSERT OR REPLACE INTO weekly_checks
                       (week_key, character, boss_name, boss_value, checked)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        week_key,
                        char_name,
                        boss.get("text", ""),
                        boss.get("value", 0),
                        1 if boss.get("checked") else 0,
                    )
                )
                migrated["weekly_checks"] += 1

    conn.commit()
    conn.close()

    print(f"✅ 마이그레이션 완료 → {db_path}")
    print(f"   캐릭터: {migrated['characters']}개")
    print(f"   보스:   {migrated['boss_list']}개")
    print(f"   체크내역: {migrated['weekly_checks']}개")


if __name__ == "__main__":
    migrate(JSON_FILE, DB_FILE)
