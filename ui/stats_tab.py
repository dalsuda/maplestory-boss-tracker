"""
통계 탭 모음
- WeeklyStatsTab  : 주차별 수익 막대 + 전체 누적 수익 (기존)
- BossStatsTab    : 보스별 기여도 파이 (주간 / 누적)
- CharStatsTab    : 캐릭터별 수익 꺾은선(크게) + 달성률(작게)
"""

import polars as pl

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QComboBox, QScrollArea, QGroupBox, QPushButton,
    QFileDialog, QMessageBox, QTabBar,
)
from PySide6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    QLineSeries, QPieSeries, QSplineSeries,
)
from PySide6.QtGui import QPainter, QCursor, QColor, QFont, QPen
from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import QToolTip

from data_layer import ParquetStore
from data_layer.database import get_connection
from utils import format_currency_ko


CHART_COLORS = [
    "#5865F2", "#23A559", "#FEE75C", "#ED4245",
    "#EB459E", "#57F287", "#FF6B6B", "#4FC3F7",
    "#AB47BC", "#FF8A65", "#26C6DA", "#D4E157",
    "#78909C",
]
class DonutChartView(QChartView):
    """도넛 차트 가운데에 호버 텍스트를 표시하는 커스텀 뷰."""

    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)
        self._center_text = ""

    def set_center_text(self, text: str) -> None:
        self._center_text = text
        self.update()  # repaint 트리거

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._center_text:
            return

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)

        # 차트 플롯 영역 중앙
        rect = self.chart().plotArea()
        font = QFont("Noto Sans KR", 15)
        painter.setFont(font)
        painter.setPen(QColor("#F2F3F5"))
        painter.drawText(
            QRectF(rect.x(), rect.y(), rect.width(), rect.height()),
            Qt.AlignCenter,
            self._center_text
        )
        painter.end()

# ===========================================================================
# 공통 헬퍼 믹스인
# ===========================================================================

class ChartMixin:
    def _make_chart(self, title: str = "") -> QChart:
        chart = QChart()
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setBackgroundBrush(QColor("#2B2D31"))
        chart.setTitleBrush(QColor("#F2F3F5"))
        chart.setTitleFont(QFont("Noto Sans KR", 10, QFont.Bold))
        chart.setFont(QFont("Noto Sans KR", 8))
        chart.legend().setVisible(False)
        return chart

    def _make_chart_view(self, chart: QChart, min_height: int = 280) -> QChartView:
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setBackgroundBrush(QColor("#2B2D31"))
        view.setMinimumHeight(min_height)
        return view

    def _style_axis(self, axis) -> None:
        axis.setLabelsColor(QColor("#B5BAC1"))
        axis.setGridLineColor(QColor("#383A40"))
        axis.setLinePen(QColor("#43444B"))

    def _make_group(self, title: str, chart_view: QChartView) -> QGroupBox:
        group = QGroupBox(title)
        group.setStyleSheet(
            "QGroupBox { border:1px solid #43444B; border-radius:8px; margin-top:15px; padding:10px; font-weight:bold; }"
            "QGroupBox::title { subcontrol-origin:margin; left:15px; color:#B5BAC1; }"
        )
        layout = QVBoxLayout(group)
        layout.addWidget(chart_view)
        return group

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)


# ===========================================================================
# 탭 1 : 주차별 수익 + 누적 수익
# ===========================================================================

class WeeklyStatsTab(QWidget, ChartMixin):

    def __init__(self, store: ParquetStore, parent=None):
        super().__init__(parent)
        self._store = store
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(15, 10, 15, 10)
        self._main_layout.setSpacing(10)

        # 상단 누적 수익 + 내보내기
        top = QHBoxLayout()
        self._lbl_accumulated = QLabel("전체 누적 수익: -")
        self._lbl_accumulated.setStyleSheet("font-size:18px; font-weight:bold; color:#23A559;")
        top.addWidget(self._lbl_accumulated)
        top.addStretch()

        btn_export = QPushButton("📥 Parquet 내보내기")
        btn_export.clicked.connect(self._export_parquet)
        btn_export.setStyleSheet(
            "QPushButton { background-color:#4E5058; padding:6px 12px; border-radius:4px; font-weight:bold; }"
            "QPushButton:hover { background-color:#6D6F78; }"
        )
        top.addWidget(btn_export)
        self._main_layout.addLayout(top)

        self._chart_area = QVBoxLayout()
        self._main_layout.addLayout(self._chart_area)

    def refresh(self) -> None:
        self._clear_layout(self._chart_area)

        accumulated = self._store.accumulated_total()
        self._lbl_accumulated.setText(f"전체 누적 수익: {format_currency_ko(accumulated)}")

        week_summaries = self._store.weekly_totals()
        if week_summaries:
            self._chart_area.addWidget(
                self._make_group("📊 주차별 수익 추이", self._build_weekly_bar_chart(week_summaries))
            )

    def _build_weekly_bar_chart(self, week_summaries: list[dict]) -> QChartView:
        labels = [f"{i}주\n({r['week_key']})" for i, r in enumerate(week_summaries, 1)]
        values_eok = [r["total"] / 100_000_000 for r in week_summaries]

        bar_set = QBarSet("총 수익")
        bar_set.setColor(QColor("#5865F2"))
        bar_set.append(values_eok)
        bar_set.hovered.connect(
            lambda status, idx: QToolTip.showText(
                QCursor.pos(),
                f"{week_summaries[idx]['week_key']}\n{format_currency_ko(week_summaries[idx]['total'])}"
            ) if status else QToolTip.hideText()
        )

        series = QBarSeries()
        series.append(bar_set)

        chart = self._make_chart("주차별 수익 (억)")
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        self._style_axis(axis_x)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.1f")
        axis_y.setTickCount(5)
        self._style_axis(axis_y)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        return self._make_chart_view(chart, min_height=400)

    def _export_parquet(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Parquet 파일 저장", "boss_stats_export.parquet",
            "Parquet Files (*.parquet)"
        )
        if not path:
            return
        try:
            self._store.snapshot()
            import shutil
            from config import PARQUET_FILE
            shutil.copy(PARQUET_FILE, path)
            QMessageBox.information(self, "완료", f"저장 완료:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"내보내기 실패:\n{e}")


# ===========================================================================
# 탭 2 : 보스별 기여도 파이 (주간 / 누적)
# ===========================================================================

class BossStatsTab(QWidget, ChartMixin):


    def __init__(self, store: ParquetStore, parent=None):
        super().__init__(parent)
        self._store = store

        root = QVBoxLayout(self)
        root.setContentsMargins(15, 10, 15, 10)
        root.setSpacing(10)

        # 주차 선택
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("주차 선택:"))
        self._week_combo = QComboBox()
        self._week_combo.setFixedWidth(130)
        self._week_combo.setStyleSheet(
            "QComboBox { background-color:#1E1F22; border:1px solid #383A40; padding:4px 8px; border-radius:4px; }"
        )
        self._week_combo.currentTextChanged.connect(self._on_week_changed)
        ctrl.addWidget(self._week_combo)
        ctrl.addStretch()
        root.addLayout(ctrl)

        # 파이 차트 2개 나란히
        self._charts_row = QHBoxLayout()
        root.addLayout(self._charts_row)

    def refresh(self) -> None:
        weeks = [r["week_key"] for r in self._store.weekly_totals()]
        if not weeks:
            return

        self._week_combo.blockSignals(True)
        self._week_combo.clear()
        self._week_combo.addItems(sorted(weeks))
        self._week_combo.setCurrentIndex(self._week_combo.count() - 1)
        self._week_combo.blockSignals(False)

        self._render(self._week_combo.currentText())

    def _on_week_changed(self, week_key: str) -> None:
        self._render(week_key)

    def _render(self, week_key: str) -> None:
        self._clear_layout(self._charts_row)
        if not week_key:
            return

        left = self._make_group(f"🥧 {week_key} 주간 보스별 기여도",
                                self._build_pie(week_key, accumulated=False))
        right = self._make_group("🥧 전체 누적 보스별 기여도",
                                 self._build_pie(week_key=None, accumulated=True))

        self._charts_row.addWidget(left, stretch=1)   # ← stretch=1 추가
        self._charts_row.addWidget(right, stretch=1)  # ← stretch=1 추가

    def _build_pie(self, week_key: str | None, accumulated: bool) -> QChartView:
        if accumulated:
            data = self._store.boss_contribution_all()
        else:
            data = self._store.boss_contribution(week_key)

        total_sum = sum(b["total"] for b in data)

        series = QPieSeries()
        series.setHoleSize(0.45)  # 가운데 공간 넉넉하게

        chart = self._make_chart()
        chart.setFont(QFont("Noto Sans KR", 8))

        view = DonutChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setBackgroundBrush(QColor("#2B2D31"))
        view.setMinimumHeight(380)

        for i, b in enumerate(data):
            sl = series.append(b["boss_name"], b["total"])
            sl.setColor(QColor(CHART_COLORS[i % len(CHART_COLORS)]))
            sl.setLabel(f"{b['boss_name']}\n{format_currency_ko(b['total'])}")
            sl.setLabelVisible(True)
            sl.setLabelFont(QFont("Noto Sans KR", 8))
            pct = b["total"] / total_sum * 100 if total_sum else 0

            sl.hovered.connect(
                lambda state, s=sl, name=b["boss_name"], val=b["total"], p=pct: (
                    s.setExploded(state),
                    s.setLabelVisible(not state),  # 호버 시 외부 라벨 숨기고 가운데로
                    view.set_center_text(
                        f"{name}\n{format_currency_ko(val)}\n{p:.1f}%" if state else ""
                    )
                )
            )

        chart.addSeries(series)
        chart.legend().setVisible(False)

        return view


# ===========================================================================
# 탭 3 : 캐릭터별 수익 꺾은선(크게) + 달성률(작게)
# ===========================================================================

class CharStatsTab(QWidget, ChartMixin):

    def __init__(self, store: ParquetStore, parent=None):
        super().__init__(parent)
        self._store = store

        root = QVBoxLayout(self)
        root.setContentsMargins(15, 10, 15, 10)
        root.setSpacing(10)

        # 주차 선택 (달성률 기준)
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("달성률 기준 주차:"))
        self._week_combo = QComboBox()
        self._week_combo.setFixedWidth(130)
        self._week_combo.setStyleSheet(
            "QComboBox { background-color:#1E1F22; border:1px solid #383A40; padding:4px 8px; border-radius:4px; }"
        )
        self._week_combo.currentTextChanged.connect(self._render)
        ctrl.addWidget(self._week_combo)
        ctrl.addStretch()
        root.addLayout(ctrl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        scroll_widget = QWidget()
        self._content = QVBoxLayout(scroll_widget)
        self._content.setSpacing(12)
        scroll.setWidget(scroll_widget)
        root.addWidget(scroll)

    def refresh(self) -> None:
        weeks = [r["week_key"] for r in self._store.weekly_totals()]
        if not weeks:
            return

        self._week_combo.blockSignals(True)
        self._week_combo.clear()
        self._week_combo.addItems(sorted(weeks))
        self._week_combo.setCurrentIndex(self._week_combo.count() - 1)
        self._week_combo.blockSignals(False)

        self._render(self._week_combo.currentText())

    def _render(self, week_key: str) -> None:
        self._clear_layout(self._content)
        if not week_key:
            return

        # 꺾은선 (크게)
        line_group = self._make_group("📈 캐릭터별 주차별 수익 추이", self._build_line_chart())
        self._content.addWidget(line_group)

        # 달성률 (작게)
        ach_group = self._make_group(f"✅ {week_key} 캐릭터별 달성률", self._build_achievement_chart(week_key))
        self._content.addWidget(ach_group)

    def _build_line_chart(self) -> QChartView:
        
        week_summaries = self._store.weekly_totals()
        week_keys = [r["week_key"] for r in week_summaries]
        week_labels = [f"{i}주" for i in range(1, len(week_keys) + 1)]

        with get_connection() as conn:
            chars = [r[0] for r in conn.execute(
                "SELECT DISTINCT character FROM weekly_checks ORDER BY character"
            ).fetchall()]

        chart = self._make_chart("캐릭터별 수익 추이 (억)")
        df = self._store.load()

        for i, char in enumerate(chars):
            series = QSplineSeries()
            series.setName(char)
            color = QColor(CHART_COLORS[i % len(CHART_COLORS)])
            pen = series.pen()
            pen.setColor(color)
            pen.setWidth(2)
            series.setPen(pen)

            for j, wk in enumerate(week_keys):
                total = 0
                if not df.is_empty():
                    filtered = df.filter(
                        pl.col("checked") &
                        (pl.col("week_key") == wk) &
                        (pl.col("character") == char)
                    )
                    if not filtered.is_empty():
                        total = filtered.select(pl.col("boss_value").sum()).item()
                series.append(j, total / 100_000_000)

            chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(week_labels)
        self._style_axis(axis_x)
        chart.addAxis(axis_x, Qt.AlignBottom)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.1f")
        axis_y.setTickCount(6)
        # 최대값의 1.5배로 여유 있게
        all_values = [v for s in chart.series() for v in [s.at(i).y() for i in range(s.count())]]
        max_val = max(all_values) if all_values else 1
        axis_y.setRange(0, max_val * 1.5)
        self._style_axis(axis_y)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        for s in chart.series():
            if axis_x not in s.attachedAxes():
                s.attachAxis(axis_x)
            if axis_y not in s.attachedAxes():
                s.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.legend().setLabelColor(QColor("#B5BAC1"))

        return self._make_chart_view(chart, min_height=400)

    def _build_achievement_chart(self, week_key: str) -> QChartView:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT character,
                          SUM(checked) as done,
                          COUNT(*) as total
                   FROM weekly_checks
                   WHERE week_key = ?
                   GROUP BY character
                   ORDER BY CAST(SUM(checked) AS FLOAT) / COUNT(*) DESC""",
                (week_key,)
            ).fetchall()

        if not rows:
            return self._make_chart_view(self._make_chart("데이터 없음"), min_height=200)

        labels = [r["character"] for r in rows]
        rates = [round(r["done"] / r["total"] * 100, 1) if r["total"] > 0 else 0 for r in rows]

        bar_set = QBarSet("달성률")
        bar_set.setColor(QColor("#23A559"))
        bar_set.append(rates)
        bar_set.hovered.connect(
            lambda status, idx: QToolTip.showText(
                QCursor.pos(),
                f"{labels[idx]}  {rates[idx]}%  ({rows[idx]['done']}/{rows[idx]['total']}개)"
            ) if status else QToolTip.hideText()
        )

        series = QBarSeries()
        series.append(bar_set)

        chart = self._make_chart("달성률 (%)")
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        self._style_axis(axis_x)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setRange(0, 100)
        axis_y.setLabelFormat("%.0f%%")
        axis_y.setTickCount(6)
        self._style_axis(axis_y)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        return self._make_chart_view(chart, min_height=220)
