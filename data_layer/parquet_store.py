"""
Parquet 기반 통계 스냅샷 저장소.

역할:
- SQLite의 weekly_checks 데이터를 Parquet로 스냅샷 저장
- Polars로 빠르게 읽어 통계 계산
- SQLite는 실시간 체크 상태 관리, Parquet는 통계 전용

사용 흐름:
    store = ParquetStore()
    store.snapshot()           # SQLite → Parquet 동기화
    df = store.load()          # Polars DataFrame 반환
    totals = store.weekly_totals()  # 주차별 수익 집계
"""

import os
import polars as pl

from data_layer.database import get_connection
from config import PARQUET_FILE


class ParquetStore:
    """weekly_checks 데이터를 Parquet로 스냅샷하고 Polars로 집계."""

    def __init__(self, path: str = PARQUET_FILE):
        self.path = path

    # ------------------------------------------------------------------
    # 스냅샷 (SQLite → Parquet)
    # ------------------------------------------------------------------

    def snapshot(self) -> None:
        """SQLite의 weekly_checks 전체를 Parquet로 저장."""
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM weekly_checks").fetchall()

        if not rows:
            return

        df = pl.DataFrame([dict(r) for r in rows]).with_columns(
            pl.col("checked").cast(pl.Boolean)
        )
        df.write_parquet(self.path)

    # ------------------------------------------------------------------
    # 읽기
    # ------------------------------------------------------------------

    def load(self) -> pl.DataFrame:
        """Parquet 파일을 Polars DataFrame으로 반환. 없으면 빈 DataFrame."""
        if not os.path.exists(self.path):
            self.snapshot()

        if not os.path.exists(self.path):
            return pl.DataFrame()

        return pl.read_parquet(self.path)

    # ------------------------------------------------------------------
    # 집계
    # ------------------------------------------------------------------

    def weekly_totals(self) -> list[dict]:
        """
        주차별 총 수익 반환.

        Returns:
            [{"week_key": "2025-37", "total": 426415000}, ...]
        """
        df = self.load()
        if df.is_empty():
            return []

        result = (
            df.filter(pl.col("checked"))
              .group_by("week_key")
              .agg(pl.col("boss_value").sum().alias("total"))
              .sort("week_key")
        )
        return result.to_dicts()

    def character_totals(self, week_key: str) -> list[dict]:
        """
        특정 주차의 캐릭터별 수익 반환.

        Returns:
            [{"character": "쿠루리우타", "total": 123000000}, ...]
        """
        df = self.load()
        if df.is_empty():
            return []

        result = (
            df.filter(pl.col("checked") & (pl.col("week_key") == week_key))
              .group_by("character")
              .agg(pl.col("boss_value").sum().alias("total"))
              .sort("total", descending=True)
        )
        return result.to_dicts()

    def boss_contribution(self, week_key: str) -> list[dict]:
        """
        특정 주차에서 보스별 총 수익 기여도 반환.
        (여러 캐릭터가 같은 보스를 깼을 때 합산)
        """
        df = self.load()
        if df.is_empty():
            return []

        result = (
            df.filter(pl.col("checked") & (pl.col("week_key") == week_key))
              .group_by("boss_name")
              .agg(pl.col("boss_value").sum().alias("total"))
              .sort("total", descending=True)
        )
        return result.to_dicts()

    def accumulated_total(self) -> int:
        """전체 누적 수익 합계."""
        df = self.load()
        if df.is_empty():
            return 0

        return (
            df.filter(pl.col("checked"))
              .select(pl.col("boss_value").sum())
              .item()
        )
    def boss_contribution_all(self) -> list[dict]:
        """전체 누적 기간의 보스별 수익 기여도 반환."""
        df = self.load()
        if df.is_empty():
            return []
        result = (
            df.filter(pl.col("checked"))
              .group_by("boss_name")
              .agg(pl.col("boss_value").sum().alias("total"))
              .sort("total", descending=True)
        )
        return result.to_dicts()