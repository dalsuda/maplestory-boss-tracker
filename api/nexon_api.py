"""
Nexon Open API 연동 모듈
- 캐릭터 OCID 조회
- 캐릭터 기본 정보 / 스탯 조회
- 캐릭터 이미지 다운로드 및 캐싱
- 비동기 API 호출 QThread
"""

import os
import urllib.parse

import requests
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from config import API_KEY, NEXON_API_BASE, IMAGE_DIR


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _get(endpoint: str, params: dict | None = None) -> dict | None:
    """공통 GET 요청. 실패 시 None 반환."""
    url = f"{NEXON_API_BASE}/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        resp = requests.get(url, headers={"x-nxopen-api-key": API_KEY}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[API] {endpoint} 호출 실패: {e}")
        return None


# ---------------------------------------------------------------------------
# 공개 API 함수
# ---------------------------------------------------------------------------

def get_character_ocid(character_name: str) -> str | None:
    """캐릭터 이름으로 OCID 조회."""
    data = _get("id", {"character_name": character_name})
    return data.get("ocid") if data else None


def get_character_info(ocid: str) -> dict | None:
    """OCID로 캐릭터 기본 정보 조회."""
    return _get("character/basic", {"ocid": ocid})


def get_character_stat(ocid: str) -> dict | None:
    """OCID로 캐릭터 스탯 조회."""
    return _get("character/stat", {"ocid": ocid})


def extract_combat_power(stat_info: dict) -> int | None:
    """스탯 정보에서 전투력 값 추출."""
    for stat in stat_info.get("final_stat", []):
        if stat.get("stat_name") == "전투력":
            return stat.get("stat_value")
    return None


# ---------------------------------------------------------------------------
# 이미지 처리
# ---------------------------------------------------------------------------

def load_character_pixmap(
    url: str,
    char_name: str,
    target_size: int,
    crop_ratio: float = 0.3,
    y_offset_ratio: float = 0.05,
    x_offset: int = 0,
) -> QPixmap | None:
    """
    캐릭터 이미지를 URL에서 내려받거나 캐시에서 불러온 뒤
    지정된 크기로 크롭·스케일한 QPixmap 반환.
    """
    file_path = os.path.join(IMAGE_DIR, f"{char_name}.png")

    try:
        if os.path.exists(file_path):
            pixmap = QPixmap(file_path)
        else:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            pixmap = QPixmap()
            pixmap.loadFromData(resp.content)
            pixmap.save(file_path, "PNG")

        w, h = pixmap.width(), pixmap.height()
        crop_side = int(min(w, h) * crop_ratio)
        x = (w - crop_side) // 2 + x_offset
        y = int((h - crop_side) // 2 + h * y_offset_ratio)

        pixmap = pixmap.copy(x, y, crop_side, crop_side)
        return pixmap.scaled(target_size, target_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    except Exception as e:
        print(f"[Image] {char_name} 이미지 로드 실패: {e}")
        return None


# ---------------------------------------------------------------------------
# 비동기 API 호출 스레드
# ---------------------------------------------------------------------------

class CharacterFetchThread(QThread):
    """캐릭터 기본 정보를 백그라운드에서 조회."""

    finished = Signal(dict)   # 성공: 캐릭터 info dict 전달
    failed = Signal(str)      # 실패: 에러 메시지 전달

    def __init__(self, character_name: str):
        super().__init__()
        self.character_name = character_name

    def run(self) -> None:
        ocid = get_character_ocid(self.character_name)
        if not ocid:
            self.failed.emit("OCID를 불러오지 못했습니다.")
            return

        info = get_character_info(ocid)
        if not info:
            self.failed.emit("캐릭터 정보를 불러오지 못했습니다.")
            return

        self.finished.emit(info)
