"""
앱 전체 스타일시트 상수 모음.
직접 문자열로 관리해 QSS 파일 없이도 동작하도록 구성.
"""

APP_DARK_THEME = """
    QWidget { background-color: #313338; color: #F2F3F5; }
    QGroupBox {
        border: 1px solid #43444B; border-radius: 8px;
        margin-top: 15px; padding: 15px; font-weight: bold;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #B5BAC1; }
    QPushButton {
        background-color: #4E5058; color: #F2F3F5;
        border-radius: 4px; padding: 6px 12px; font-weight: bold;
    }
    QPushButton:hover { background-color: #6D6F78; }
    QLineEdit, QSpinBox {
        background-color: #1E1F22; border: 1px solid #383A40;
        border-radius: 4px; padding: 6px; color: white;
    }
    QLabel { color: #F2F3F5; font-weight: bold; }
    QScrollArea { border: none; background-color: transparent; }
    QScrollArea > QWidget > QWidget { background-color: transparent; }
"""

TAB_STYLE = """
    QTabWidget::pane { border-top: 2px solid #1E1F22; }
    QTabBar::tab {
        background-color: #2B2D31; color: #B5BAC1;
        padding: 10px 20px; font-weight: bold; font-size: 14px;
        border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
    }
    QTabBar::tab:selected { background-color: #313338; color: #F2F3F5; }
    QTabBar::tab:hover:!selected { background-color: #383A40; color: #DBDEE1; }
"""

SIDEBAR_STYLE = """
    QListWidget {
        background-color: #1E1F22; border: none; padding-top: 10px; outline: none;
    }
    QListWidget::item {
        background-color: #313338; border-radius: 12px;
        margin-left: 3px; margin-right: 3px;
        height: 55px; width: 55px; border: 2px solid transparent;
    }
    QListWidget::item:selected {
        background-color: transparent; border: 2px solid #80848E;
        border-radius: 12px; color: white;
    }
    QListWidget::item:hover:!selected {
        background-color: #383A40; border-radius: 12px;
    }
"""

COMBO_STYLE = """
    QComboBox {
        background-color: #1E1F22; border: 1px solid #383A40;
        padding: 4px 8px; border-radius: 4px;
    }
"""

CHECKLIST_BTN_STYLE = """
    QPushButton {
        background-color: #2B2D31; color: #B5BAC1;
        border: 1px solid #1E1F22; border-radius: 8px;
        padding: 10px 16px; font-size: 14px;
    }
    QPushButton:hover { background-color: #383A40; color: #F2F3F5; }
    QPushButton:checked { background-color: #23A559; color: white; border: none; }
"""

WEEK_TOTAL_LABEL_STYLE = """
    color: #23A559;
    background-color: #1E1F22;
    border: 1px solid #383A40;
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 8px;
"""

CHAR_TOTAL_LABEL_STYLE = """
    font-size: 16px;
    color: #5865F2;
    font-weight: bold;
    margin-top: 10px;
"""

CHAR_STAT_LABEL_STYLE = """
    font-size: 14px;
    font-weight: bold;
    color: #DBDEE1;
    margin-left: 10px;
    margin-bottom: 4px;
"""
