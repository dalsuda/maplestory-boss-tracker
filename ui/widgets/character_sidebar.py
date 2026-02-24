"""
캐릭터 사이드바 위젯 — 아이콘 리스트로 캐릭터를 선택.
"""

import os

from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QSize

from config import IMAGE_DIR, SIDEBAR_WIDTH, SIDEBAR_ICON_SIZE
from ui.styles import SIDEBAR_STYLE


# 사이드바 전용 이미지 크롭 파라미터
_SIDEBAR_CROP_RATIO = 0.3
_SIDEBAR_Y_OFFSET = 0.05
_SIDEBAR_X_OFFSET = 15


class CharacterSidebar(QListWidget):
    """아이콘 기반 캐릭터 선택 사이드바."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setIconSize(QSize(SIDEBAR_ICON_SIZE, SIDEBAR_ICON_SIZE))
        self.setSpacing(12)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(SIDEBAR_STYLE)

    # ------------------------------------------------------------------

    def refresh(self, character_names: list[str]) -> None:
        """캐릭터 이름 목록으로 사이드바 아이콘을 재구성."""
        self.blockSignals(True)
        self.clear()

        for name in character_names:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, name)
            item.setToolTip(name)
            item.setIcon(self._build_icon(name))
            self.addItem(item)

        self.blockSignals(False)

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------

    def _build_icon(self, char_name: str) -> QIcon:
        img_path = os.path.join(IMAGE_DIR, f"{char_name}.png")

        if not os.path.exists(img_path):
            fallback = QPixmap(SIDEBAR_ICON_SIZE, SIDEBAR_ICON_SIZE)
            fallback.fill(Qt.transparent)
            return QIcon(fallback)

        pixmap = QPixmap(img_path)
        w, h = pixmap.width(), pixmap.height()

        crop_side = int(min(w, h) * _SIDEBAR_CROP_RATIO)
        x = (w - crop_side) // 2 + _SIDEBAR_X_OFFSET
        y = int((h - crop_side) // 2 + h * _SIDEBAR_Y_OFFSET)

        pixmap = pixmap.copy(x, y, crop_side, crop_side)
        pixmap = pixmap.scaled(
            SIDEBAR_ICON_SIZE, SIDEBAR_ICON_SIZE,
            Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation,
        )
        return QIcon(pixmap)
