"""
주간 보스 체크리스트 탭.
SQLite DataManager 기반으로 동작.
"""

from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QGroupBox, QInputDialog, QMessageBox, QDialog,
    QListWidget, QListWidgetItem, QLineEdit, QSpinBox, QSplitter,
    QScrollArea, QSizePolicy,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QTimer, Signal

from data_layer import DataManager, current_week_key
from ui.styles import (
    COMBO_STYLE, CHECKLIST_BTN_STYLE, CHAR_TOTAL_LABEL_STYLE,
    WEEK_TOTAL_LABEL_STYLE, CHAR_STAT_LABEL_STYLE,
)
from ui.widgets.character_sidebar import CharacterSidebar
from api import (
    get_character_ocid, get_character_info, get_character_stat,
    extract_combat_power, load_character_pixmap, CharacterFetchThread,
)
from utils import format_currency_ko, format_power_ko


class ChecklistTab(QWidget):
    data_changed = Signal()

    def __init__(self, dm: DataManager, week_key: str, parent=None):
        super().__init__(parent)
        self._dm = dm
        self._week_key = week_key
        self._current_character = None
        self._current_boss_list = []
        self._fetch_thread = None
        self._pending_checks = []

        self._save_timer = QTimer(singleShot=True)
        self._save_timer.timeout.connect(self._flush_pending_checks)

        self._build_ui()

    def switch_week(self, week_key: str) -> None:
        self._week_key = week_key
        self._refresh_sidebar()
        if self.sidebar.count() > 0:
            self.sidebar.setCurrentRow(0)
            first = self.sidebar.item(0)
            if first:
                self._load_character_checklist(first.data(Qt.UserRole))
        self.refresh_stats_summary()

    def refresh_week_combo(self) -> None:
        weeks = self._dm.get_all_week_keys()
        self.week_combo.blockSignals(True)
        self.week_combo.clear()
        self.week_combo.addItems(sorted(weeks))
        self.week_combo.setCurrentText(self._week_key)
        self.week_combo.blockSignals(False)

    def refresh_stats_summary(self) -> None:
        # 이번 주 전체 캐릭터 목록 가져오기
        week_data = self._dm.get_week_data(self._week_key)
        all_characters = list(week_data.keys())

        # 수익 있는 캐릭터만 반환하는 기존 메서드 결과를 dict로 변환
        char_totals_map = {
            r["character"]: r["total"]
            for r in self._dm.get_character_weekly_totals(self._week_key)
        }

        # 수익 없는 캐릭터도 0으로 포함
        total = sum(char_totals_map.values())

        if not hasattr(self, "_lbl_week_total"):
            self._lbl_week_total = QLabel()
            self._lbl_week_total.setFont(QFont("Noto Sans KR", 16, QFont.Bold))
            self._lbl_week_total.setStyleSheet(WEEK_TOTAL_LABEL_STYLE)
            self._lbl_week_total.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self._stats_layout.insertWidget(0, self._lbl_week_total)

        self._lbl_week_total.setText(f"이번 주 총 수익: {format_currency_ko(total)}")

        for i in reversed(range(self._char_scroll_layout.count())):
            w = self._char_scroll_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        for char in all_characters:
            char_total = char_totals_map.get(char, 0)  # 없으면 0
            lbl = QLabel(f"{char}: {format_currency_ko(char_total)}")
            lbl.setStyleSheet(CHAR_STAT_LABEL_STYLE)
            self._char_scroll_layout.addWidget(lbl)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 10, 10)
        self.sidebar = CharacterSidebar()
        self.sidebar.currentItemChanged.connect(self._on_sidebar_changed)
        layout.addWidget(self.sidebar)
        content = QVBoxLayout()
        layout.addLayout(content)
        self.splitter = QSplitter(Qt.Horizontal)
        content.addWidget(self.splitter)
        self.splitter.addWidget(self._build_left_panel())
        self.splitter.addWidget(self._build_right_panel())
        self.splitter.setSizes([450, 450])

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 5, 5, 5)

        char_row = QHBoxLayout()
        self.char_image_label = QLabel()
        self.char_image_label.setFixedSize(180, 180)
        char_row.addWidget(self.char_image_label, alignment=Qt.AlignTop)

        info_col = QVBoxLayout()
        self.lbl_power = QLabel("전투력: -")
        self.lbl_level = QLabel("레벨: -")
        self.lbl_class = QLabel("직업: -")
        for lbl in (self.lbl_power, self.lbl_level, self.lbl_class):
            info_col.addWidget(lbl)

        btn_refresh = QPushButton("정보 새로고침")
        btn_refresh.clicked.connect(self._refresh_character_info)
        info_col.addWidget(btn_refresh)

        self.char_total_label = QLabel("선택된 캐릭터 수익: 0 메소")
        info_col.addWidget(self.char_total_label)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("캐릭터 추가")
        btn_add.clicked.connect(self._add_character_dialog)
        btn_del = QPushButton("현재 캐릭터 삭제")
        btn_del.clicked.connect(self._delete_character_dialog)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        info_col.addLayout(btn_row)

        char_row.addLayout(info_col)
        layout.addLayout(char_row)

        stats_group = QGroupBox("통계 요약")
        self._stats_layout = QVBoxLayout(stats_group)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self._char_scroll_layout = QVBoxLayout(scroll_widget)
        scroll.setWidget(scroll_widget)
        self._stats_layout.addWidget(scroll)
        layout.addWidget(stats_group)

        return w

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.week_combo = QComboBox()
        self.week_combo.setStyleSheet(COMBO_STYLE)
        self.week_combo.addItems(sorted(self._dm.get_all_week_keys()))
        self.week_combo.setCurrentText(self._week_key)
        self.week_combo.currentTextChanged.connect(self.switch_week)

        week_row = QHBoxLayout()
        week_row.addStretch()
        week_row.addWidget(QLabel("주차 선택:"))
        week_row.addWidget(self.week_combo)
        layout.addLayout(week_row)

        checklist_group = QGroupBox("보스 체크리스트")
        checklist_col = QVBoxLayout(checklist_group)
        self._checklist_buttons_layout = QVBoxLayout()
        checklist_col.addLayout(self._checklist_buttons_layout)

        boss_btn_row = QHBoxLayout()
        btn_add_boss = QPushButton("캐릭터 전용 보스 추가")
        btn_add_boss.clicked.connect(self._add_character_boss_dialog)
        btn_del_boss = QPushButton("캐릭터 전용 보스 삭제")
        btn_del_boss.clicked.connect(self._delete_character_boss_dialog)
        boss_btn_row.addWidget(btn_add_boss)
        boss_btn_row.addWidget(btn_del_boss)
        checklist_col.addLayout(boss_btn_row)
        layout.addWidget(checklist_group)
        layout.addWidget(self._build_global_boss_group())
        return w

    def _build_global_boss_group(self) -> QGroupBox:
        group = QGroupBox("전역 보스 관리")
        group.setCheckable(True)
        group.setChecked(False)
        inner = QVBoxLayout(group)

        self._boss_list_widget = QListWidget()
        inner.addWidget(self._boss_list_widget)

        form_row = QHBoxLayout()
        self._input_boss_name = QLineEdit()
        self._input_boss_name.setPlaceholderText("보스 이름")
        self._input_boss_value = QSpinBox()
        self._input_boss_value.setRange(0, 10 ** 9)
        self._input_boss_value.setSingleStep(10_000)
        form_row.addWidget(self._input_boss_name)
        form_row.addWidget(self._input_boss_value)
        inner.addLayout(form_row)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("보스 추가")
        btn_add.clicked.connect(self._add_global_boss)
        btn_del = QPushButton("선택 보스 삭제")
        btn_del.clicked.connect(self._delete_selected_global_boss)
        btn_update = QPushButton("시세 업데이트")
        btn_update.clicked.connect(self._update_boss_price_dialog)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addWidget(btn_update)
        inner.addLayout(btn_row)

        def _toggle(checked):
            for i in range(inner.count()):
                item = inner.itemAt(i)
                if item and item.widget():
                    item.widget().setVisible(checked)

        _toggle(False)
        group.toggled.connect(_toggle)
        self._refresh_boss_list_widget()
        return group

    def _load_character_checklist(self, char_name: str) -> None:
        self._clear_checklist_buttons()
        self._current_character = char_name

        char_info = self._dm.get_character(char_name)
        week_data = self._dm.get_week_data(self._week_key)

        if char_name not in week_data:
            self._dm.add_character_to_week(self._week_key, char_name)
            week_data = self._dm.get_week_data(self._week_key)

        if char_info:
            self.lbl_power.setText(f"전투력: {format_power_ko(char_info.get('power', 0))}")
            self.lbl_level.setText(f"레벨: {char_info.get('level', '-')}")
            self.lbl_class.setText(f"직업: {char_info.get('job', '-')}")
            if char_info.get("image_url"):
                self._show_character_image(char_info["image_url"], char_name)
        else:
            self._clear_character_info()

        self._current_boss_list = week_data.get(char_name, {}).get("bosses", [])

        for idx, boss in enumerate(self._current_boss_list):
            btn = QPushButton(f"{boss['text']} ({boss['value']:,}메소)")
            btn.setCheckable(True)
            btn.setChecked(boss.get("checked", False))
            btn.setStyleSheet(CHECKLIST_BTN_STYLE)
            btn.clicked.connect(partial(self._on_boss_toggled, idx, btn))
            self._checklist_buttons_layout.addWidget(btn)

        self._update_char_total_label()

    def _on_boss_toggled(self, idx: int, btn: QPushButton) -> None:
        boss = self._current_boss_list[idx]
        boss["checked"] = btn.isChecked()
        # DB에 즉시 저장 (디바운스 제거)
        self._dm.set_boss_checked(self._week_key, self._current_character, boss["text"], boss["checked"])
        self._update_char_total_label()
        self.refresh_stats_summary()  # 즉시 갱신
        self.data_changed.emit()
        
    def _flush_pending_checks(self) -> None:
        for boss_name, checked in self._pending_checks:
            self._dm.set_boss_checked(self._week_key, self._current_character, boss_name, checked)
        self._pending_checks.clear()

    def _update_char_total_label(self) -> None:
        total = sum(b["value"] for b in self._current_boss_list if b.get("checked"))
        self.char_total_label.setText(f"{self._current_character} 수익: {format_currency_ko(total)}")
        self.char_total_label.setStyleSheet(CHAR_TOTAL_LABEL_STYLE)

    def _clear_checklist_buttons(self) -> None:
        while self._checklist_buttons_layout.count():
            item = self._checklist_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_sidebar_changed(self, current, _previous) -> None:
        if current:
            self._load_character_checklist(current.data(Qt.UserRole))
            self.refresh_stats_summary()

    def _refresh_sidebar(self) -> None:
        week_data = self._dm.get_week_data(self._week_key)
        self.sidebar.refresh(list(week_data.keys()))

    def _add_character_dialog(self) -> None:
        text, ok = QInputDialog.getText(self, "캐릭터 추가", "추가할 캐릭터 이름을 입력하세요:")
        if not ok or not text.strip():
            return
        name = text.strip()

        if name in self._dm.get_week_data(self._week_key):
            QMessageBox.warning(self, "중복", "이미 동일한 이름의 캐릭터가 있습니다.")
            return

        self._fetch_thread = CharacterFetchThread(name)
        self._fetch_thread.finished.connect(lambda info: self._on_character_fetch_success(name, info))
        self._fetch_thread.failed.connect(lambda msg: QMessageBox.warning(self, "실패", msg))
        self._fetch_thread.start()

    def _on_character_fetch_success(self, name: str, info: dict) -> None:
        self._dm.upsert_character(
            name=name,
            ocid=info.get("ocid"),
            level=info.get("character_level"),
            job=info.get("character_class"),
            image_url=info.get("character_image"),
        )
        self._dm.add_character_to_week(self._week_key, name)
        self._refresh_sidebar()

        for i in range(self.sidebar.count()):
            if self.sidebar.item(i).data(Qt.UserRole) == name:
                self.sidebar.setCurrentRow(i)
                break

        self.data_changed.emit()
        QMessageBox.information(self, "추가", f"{name} 캐릭터 정보가 등록되었습니다.")

    def _delete_character_dialog(self) -> None:
        name = self._current_character
        if not name:
            return
        ans = QMessageBox.question(
            self, "캐릭터 삭제", f"캐릭터 '{name}'을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return

        self._dm.delete_character(name)
        self._refresh_sidebar()

        if self.sidebar.count() > 0:
            self.sidebar.setCurrentRow(0)
        else:
            self._current_character = None
            self._clear_character_info()
            self._clear_checklist_buttons()
            self.char_total_label.setText("선택된 캐릭터 수익: 0 메소")

        self.data_changed.emit()

    def _add_character_boss_dialog(self) -> None:
        if not self._current_character:
            return
        current_names = {b["text"] for b in self._current_boss_list}
        available = [{"text": b["name"], "value": b["value"]}
                     for b in self._dm.get_boss_list() if b["name"] not in current_names]

        def _do_add(selected):
            for b in selected:
                self._dm.add_boss_to_character(self._week_key, self._current_character, b["text"], b["value"])

        self._show_multi_select_dialog("캐릭터 보스 추가", available, "추가", _do_add)

    def _delete_character_boss_dialog(self) -> None:
        if not self._current_character:
            return

        def _do_delete(selected):
            for b in selected:
                self._dm.remove_boss_from_character(self._week_key, self._current_character, b["text"])

        self._show_multi_select_dialog("캐릭터 보스 삭제", self._current_boss_list, "삭제", _do_delete)

    def _show_multi_select_dialog(self, title, items, confirm_label, on_confirm) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setGeometry(400, 300, 300, 400)
        layout = QVBoxLayout(dlg)

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        for b in sorted(items, key=lambda x: x["value"]):
            item = QListWidgetItem(f"{b['text']} ({format_currency_ko(b['value'])})")
            item.setData(Qt.UserRole, b)
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton(confirm_label)
        btn_cancel = QPushButton("취소")
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        def _on_ok():
            selected = [i.data(Qt.UserRole) for i in list_widget.selectedItems()]
            on_confirm(selected)
            self._load_character_checklist(self._current_character)
            dlg.accept()

        btn_ok.clicked.connect(_on_ok)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec()

    def _refresh_boss_list_widget(self) -> None:
        self._boss_list_widget.clear()
        for b in self._dm.get_boss_list():
            item = QListWidgetItem(f"{b['name']} ({b['value']:,}메소)")
            item.setData(Qt.UserRole, b)
            self._boss_list_widget.addItem(item)

    def _add_global_boss(self) -> None:
        name = self._input_boss_name.text().strip()
        value = int(self._input_boss_value.value())
        if not name:
            return
        if any(b["name"] == name for b in self._dm.get_boss_list()):
            QMessageBox.warning(self, "중복", "이미 있는 보스입니다.")
            return
        self._dm.add_boss(name, value)
        self._refresh_boss_list_widget()
        if self._current_character:
            self._load_character_checklist(self._current_character)

    def _delete_selected_global_boss(self) -> None:
        sel = self._boss_list_widget.currentItem()
        if not sel:
            return
        self._dm.delete_boss(sel.data(Qt.UserRole)["name"])
        self._refresh_boss_list_widget()
        if self._current_character:
            self._load_character_checklist(self._current_character)

    def _update_boss_price_dialog(self) -> None:
        sel = self._boss_list_widget.currentItem()
        if not sel:
            QMessageBox.warning(self, "알림", "시세를 변경할 보스를 먼저 선택하세요.")
            return

        boss = sel.data(Qt.UserRole)
        boss_name = boss["name"]
        current_value = boss["value"]

        new_value, ok = QInputDialog.getInt(
            self, f"{boss_name} 시세 업데이트",
            f"현재 시세: {current_value:,}메소\n새 시세 입력:",
            value=current_value, min=0, max=10**9,
        )
        if not ok or new_value == current_value:
            return

        applied_from, ok = QInputDialog.getText(
            self, "적용 시작 주차",
            "이 주차부터 새 시세가 적용됩니다.\n(이전 주차 내역은 변경되지 않습니다)",
            text=current_week_key(),
        )
        if not ok or not applied_from.strip():
            return

        note, ok = QInputDialog.getText(
            self, "변경 메모", "변경 사유를 입력하세요 (선택):",
            text="분기 패치 반영",
        )

        self._dm.update_boss_price(boss_name, new_value, applied_from.strip(), note if ok else "")
        self._refresh_boss_list_widget()
        QMessageBox.information(
            self, "완료",
            f"{boss_name} 시세가 {new_value:,}메소로 변경되었습니다.\n"
            f"({applied_from} 이후 주차부터 적용)"
        )

    def _refresh_character_info(self) -> None:
        if not self._current_character:
            QMessageBox.warning(self, "경고", "캐릭터를 먼저 선택하세요.")
            return

        name = self._current_character
        char = self._dm.get_character(name) or {}
        ocid = char.get("ocid") or get_character_ocid(name)
        if not ocid:
            QMessageBox.critical(self, "에러", "OCID를 불러올 수 없습니다.")
            return

        basic = get_character_info(ocid)
        stat = get_character_stat(ocid)
        power = extract_combat_power(stat) if stat else None

        self._dm.upsert_character(
            name=name, ocid=ocid,
            level=basic.get("character_level") if basic else None,
            job=basic.get("character_class") if basic else None,
            image_url=basic.get("character_image") if basic else None,
            power=power,
        )
        self._update_character_display(name)

    def _show_character_image(self, url: str, char_name: str) -> None:
        size = min(self.char_image_label.width(), self.char_image_label.height())
        pixmap = load_character_pixmap(url, char_name, target_size=size)
        if pixmap:
            self.char_image_label.setPixmap(pixmap)

    def _update_character_display(self, char_name: str) -> None:
        char = self._dm.get_character(char_name) or {}
        self.lbl_power.setText(f"전투력: {format_power_ko(char.get('power', 0))}")
        self.lbl_level.setText(f"레벨: {char.get('level', '-')}")
        self.lbl_class.setText(f"직업: {char.get('job', '-')}")
        if char.get("image_url"):
            self._show_character_image(char["image_url"], char_name)

    def _clear_character_info(self) -> None:
        self.lbl_power.setText("전투력: -")
        self.lbl_level.setText("레벨: -")
        self.lbl_class.setText("직업: -")
        self.char_image_label.clear()
