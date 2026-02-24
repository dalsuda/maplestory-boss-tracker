"""
앱 진입점.
"""

import sys
import os
import PySide6

# Qt 플랫폼 플러그인 경로 지정
plugin_path = os.path.join(os.path.dirname(PySide6.__file__), "Qt", "plugins", "platforms")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont

from ui.app import BossTrackerApp


def main() -> None:
    app = QApplication(sys.argv)

    # 한글 폰트 등록
    font_id = QFontDatabase.addApplicationFont("fonts/NotoSansKR-Regular.ttf")
    if font_id != -1:
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(family))

    # QSS 파일이 있으면 적용 (없어도 동작)
    try:
        with open("style.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    win = BossTrackerApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
