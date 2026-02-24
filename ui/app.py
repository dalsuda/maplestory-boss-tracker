"""
BossTrackerApp — 앱의 진입 위젯.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSystemTrayIcon, QMenu, QApplication, QTabWidget
from PySide6.QtGui import QIcon, QAction

from config import WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_X, WINDOW_Y
from data_layer import DataManager, current_week_key, ParquetStore
from data_layer.database import init_db
from ui.checklist_tab import ChecklistTab
from ui.stats_tab import WeeklyStatsTab, BossStatsTab, CharStatsTab
from ui.styles import APP_DARK_THEME, TAB_STYLE


class BossTrackerApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("주간 보스 체크리스트")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.move(WINDOW_X, WINDOW_Y)
        self.setStyleSheet(APP_DARK_THEME)

        init_db()

        self._dm = DataManager()
        self._dm.ensure_current_week()
        self._week_key = current_week_key()
        self._store = ParquetStore()  # 통계 탭 3개가 공유

        self._setup_tray()
        self._setup_tabs()
        self._checklist_tab.switch_week(self._week_key)

    def _setup_tabs(self) -> None:
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(TAB_STYLE)

        self._checklist_tab = ChecklistTab(dm=self._dm, week_key=self._week_key)
        self._weekly_stats_tab = WeeklyStatsTab(store=self._store)
        self._boss_stats_tab = BossStatsTab(store=self._store)
        self._char_stats_tab = CharStatsTab(store=self._store)

        self._tabs.addTab(self._checklist_tab,    "📋 주간 체크리스트")
        self._tabs.addTab(self._weekly_stats_tab,  "📊 누적 수익")
        self._tabs.addTab(self._boss_stats_tab,    "🥧 보스별 기여도")
        self._tabs.addTab(self._char_stats_tab,    "📈 캐릭터별 통계")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._checklist_tab.data_changed.connect(self._checklist_tab.refresh_stats_summary)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)

    def _on_tab_changed(self, index: int) -> None:
        """탭 진입 시 해당 탭만 Parquet 스냅샷 + 갱신."""
        if index == 1:
            self._store.snapshot()
            self._weekly_stats_tab.refresh()
        elif index == 2:
            self._store.snapshot()
            self._boss_stats_tab.refresh()
        elif index == 3:
            self._store.snapshot()
            self._char_stats_tab.refresh()

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(QIcon("icon.png"))
        self._tray.setToolTip("주간 보스 체크리스트")
        menu = QMenu()
        menu.addAction(QAction("열기", self, triggered=self.show_window))
        menu.addAction(QAction("종료", self, triggered=QApplication.instance().quit))
        self._tray.setContextMenu(menu)
        self._tray.show()

    def show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
        self._tray.showMessage(
            "주간 보스 체크리스트",
            "프로그램이 트레이로 최소화되었습니다.",
            QSystemTrayIcon.Information,
            3000,
        )
