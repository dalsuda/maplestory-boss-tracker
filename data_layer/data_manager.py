"""
SQLite 기반 데이터 관리.
기존 JSON DataManager와 동일한 인터페이스를 유지합니다.
"""
# sqlite3.Row를 반환하는 함수에서 타입 힌트용
import sqlite3

from datetime import date, timedelta
from data_layer.database import get_connection


# ---------------------------------------------------------------------------
# 주차 계산
# ---------------------------------------------------------------------------

def current_week_key() -> str:
    """목요일 기준 현재 주차 키 반환. ex) '2025-37'"""
    today = date.today()
    offset = (today.weekday() - 3) % 7
    thursday = today - timedelta(days=offset)
    year, week, _ = thursday.isocalendar()
    return f"{year}-{week}"


# ---------------------------------------------------------------------------
# DataManager
# ---------------------------------------------------------------------------

class DataManager:
    """SQLite 기반 앱 데이터 관리."""

    # ------------------------------------------------------------------
    # 초기화
    # ------------------------------------------------------------------

    def ensure_current_week(self) -> None:
        """현재 주차 데이터가 없으면 직전 주차에서 복사해 초기화."""
        week_key = current_week_key()
        existing_weeks = self.get_all_week_keys()

        if week_key in existing_weeks:
            return

        # 직전 주차 찾기
        past_weeks = sorted(w for w in existing_weeks if w < week_key)
        if not past_weeks:
            return

        last_week = past_weeks[-1]
        prev_checks = self.get_weekly_checks(last_week)
        current_bosses = {b["name"]: b["value"] for b in self.get_boss_list()}

        with get_connection() as conn:
            for row in prev_checks:
                # 현재 boss_list에 있는 보스면 최신 시세로, 없으면 기존 시세 유지
                value = current_bosses.get(row["boss_name"], row["boss_value"])
                conn.execute(
                    """INSERT OR IGNORE INTO weekly_checks
                       (week_key, character, boss_name, boss_value, checked)
                       VALUES (?, ?, ?, ?, 0)""",
                    (week_key, row["character"], row["boss_name"], value)
                )

    # ------------------------------------------------------------------
    # 주차
    # ------------------------------------------------------------------

    def get_all_week_keys(self) -> list[str]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT week_key FROM weekly_checks ORDER BY week_key"
            ).fetchall()
        return [r["week_key"] for r in rows]

    def get_weekly_checks(self, week_key: str) -> list[sqlite3.Row]:
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM weekly_checks WHERE week_key = ?", (week_key,)
            ).fetchall()

    def get_week_data(self, week_key: str) -> dict:
        """
        week_key에 해당하는 데이터를 기존 JSON 구조와 동일하게 반환.
        {char_name: {"bosses": [{text, value, checked}, ...]}}
        """
        rows = self.get_weekly_checks(week_key)
        result: dict[str, dict] = {}
        for row in rows:
            char = row["character"]
            result.setdefault(char, {"bosses": []})
            result[char]["bosses"].append({
                "text": row["boss_name"],
                "value": row["boss_value"],
                "checked": bool(row["checked"]),
            })
        # value 기준 정렬
        for char_data in result.values():
            char_data["bosses"].sort(key=lambda b: b["value"])
        return result

    def set_boss_checked(self, week_key: str, character: str, boss_name: str, checked: bool) -> None:
        with get_connection() as conn:
            conn.execute(
                """UPDATE weekly_checks SET checked = ?
                   WHERE week_key = ? AND character = ? AND boss_name = ?""",
                (1 if checked else 0, week_key, character, boss_name)
            )

    # ------------------------------------------------------------------
    # 캐릭터
    # ------------------------------------------------------------------

    def get_all_characters(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM characters").fetchall()
        return [dict(r) for r in rows]

    def get_character(self, name: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM characters WHERE name = ?", (name,)
            ).fetchone()
        return dict(row) if row else None

    def upsert_character(self, name: str, ocid: str = None, level: int = None,
                         job: str = None, power: int = None, image_url: str = None) -> None:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO characters (name, ocid, level, job, power, image_url)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       ocid      = COALESCE(excluded.ocid, ocid),
                       level     = COALESCE(excluded.level, level),
                       job       = COALESCE(excluded.job, job),
                       power     = COALESCE(excluded.power, power),
                       image_url = COALESCE(excluded.image_url, image_url)""",
                (name, ocid, level, job, power, image_url)
            )

    def delete_character(self, name: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM characters WHERE name = ?", (name,))
            conn.execute("DELETE FROM weekly_checks WHERE character = ?", (name,))

    def add_character_to_week(self, week_key: str, character: str) -> None:
        """캐릭터를 해당 주차에 추가 (전역 보스 목록 기준으로 행 생성)."""
        bosses = self.get_boss_list()
        with get_connection() as conn:
            for boss in bosses:
                conn.execute(
                    """INSERT OR IGNORE INTO weekly_checks
                       (week_key, character, boss_name, boss_value, checked)
                       VALUES (?, ?, ?, ?, 0)""",
                    (week_key, character, boss["name"], boss["value"])
                )

    # ------------------------------------------------------------------
    # 보스
    # ------------------------------------------------------------------

    def get_boss_list(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT name, value FROM boss_list ORDER BY value"
            ).fetchall()
        return [dict(r) for r in rows]

    def add_boss(self, name: str, value: int) -> None:
        week_key = current_week_key()
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO boss_list (name, value) VALUES (?, ?)",
                (name, value)
            )
            conn.execute(
                """INSERT INTO boss_price_history (boss_name, value, applied_from, note)
                   VALUES (?, ?, ?, ?)""",
                (name, value, week_key, "보스 추가")
            )

    def delete_boss(self, name: str) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM boss_list WHERE name = ?", (name,))
            conn.execute(
                "DELETE FROM weekly_checks WHERE boss_name = ?", (name,)
            )

    def add_boss_to_character(self, week_key: str, character: str, boss_name: str, boss_value: int) -> None:
        with get_connection() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO weekly_checks
                   (week_key, character, boss_name, boss_value, checked)
                   VALUES (?, ?, ?, ?, 0)""",
                (week_key, character, boss_name, boss_value)
            )

    def remove_boss_from_character(self, week_key: str, character: str, boss_name: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """DELETE FROM weekly_checks
                   WHERE week_key = ? AND character = ? AND boss_name = ?""",
                (week_key, character, boss_name)
            )

    # ------------------------------------------------------------------
    # 보스 시세 업데이트
    # ------------------------------------------------------------------

    def update_boss_price(self, boss_name: str, new_value: int,
                          applied_from: str, note: str = "") -> None:
        """
        보스 시세를 업데이트하고 이력을 기록.
        applied_from 이후 주차의 weekly_checks는 새 시세로 갱신.
        그 이전 주차는 절대 건드리지 않음 (과거 내역 보호).
        """
        with get_connection() as conn:
            # 1. 현재 시세 업데이트
            conn.execute(
                "UPDATE boss_list SET value = ? WHERE name = ?",
                (new_value, boss_name)
            )
            # 2. 이력 기록
            conn.execute(
                """INSERT INTO boss_price_history (boss_name, value, applied_from, note)
                   VALUES (?, ?, ?, ?)""",
                (boss_name, new_value, applied_from, note)
            )
            # 3. applied_from 이후 주차만 갱신 (과거 보호)
            conn.execute(
                """UPDATE weekly_checks SET boss_value = ?
                   WHERE boss_name = ? AND week_key >= ?""",
                (new_value, boss_name, applied_from)
            )

    def get_boss_price_history(self, boss_name: str) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM boss_price_history
                   WHERE boss_name = ? ORDER BY applied_from DESC""",
                (boss_name,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # 통계용
    # ------------------------------------------------------------------

    def get_weekly_totals(self) -> list[dict]:
        """주차별 총 수익 반환. Polars/Parquet 연동 전 기본 집계."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT week_key, SUM(boss_value) as total
                   FROM weekly_checks
                   WHERE checked = 1
                   GROUP BY week_key
                   ORDER BY week_key"""
            ).fetchall()
        return [dict(r) for r in rows]

    def get_character_weekly_totals(self, week_key: str) -> list[dict]:
        """특정 주차의 캐릭터별 수익 반환."""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT character, SUM(boss_value) as total
                   FROM weekly_checks
                   WHERE week_key = ? AND checked = 1
                   GROUP BY character
                   ORDER BY total DESC""",
                (week_key,)
            ).fetchall()
        return [dict(r) for r in rows]


