# main.py
"""
백테스트 GUI 메인 실행 파일
- 독립 실행 모드
- 기존 GUI 통합 모드 지원
"""

import sys
import os

# 경로 설정 - backtest_project 폴더를 path에 추가
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt5.QtCore import Qt

from backtest_gui.backtest_widget import BacktestWidget


# 다크 테마 스타일시트
DARK_THEME = """
    QMainWindow {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    QWidget {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    QTabWidget::pane {
        border: 1px solid #3a3a3a;
        background-color: #2b2b2b;
    }
    QTabBar::tab {
        background-color: #3a3a3a;
        color: #ffffff;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background-color: #0078d4;
    }
    QTabBar::tab:hover {
        background-color: #4a4a4a;
    }
    QLabel {
        color: #ffffff;
    }
    QPushButton {
        background-color: #0078d4;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #106ebe;
    }
    QPushButton:disabled {
        background-color: #555555;
        color: #888888;
    }
    QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {
        background-color: #3a3a3a;
        color: white;
        border: 1px solid #555555;
        border-radius: 3px;
        padding: 5px;
    }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {
        border: 1px solid #0078d4;
    }
    QTableWidget {
        background-color: #2b2b2b;
        color: #ffffff;
        gridline-color: #3a3a3a;
        border: none;
    }
    QTableWidget::item:selected {
        background-color: #0078d4;
    }
    QHeaderView::section {
        background-color: #3a3a3a;
        color: #ffffff;
        padding: 5px;
        border: 1px solid #2b2b2b;
    }
    QScrollBar:vertical {
        background-color: #2b2b2b;
        width: 12px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background-color: #555555;
        min-height: 20px;
        border-radius: 6px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #666666;
    }
    QScrollBar:horizontal {
        background-color: #2b2b2b;
        height: 12px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background-color: #555555;
        min-width: 20px;
        border-radius: 6px;
    }
    QGroupBox {
        color: white;
        border: 1px solid #3a3a3a;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
    }
    QProgressBar {
        background-color: #3a3a3a;
        border: none;
        border-radius: 3px;
        text-align: center;
        color: white;
    }
    QProgressBar::chunk {
        background-color: #0078d4;
        border-radius: 3px;
    }
    QCheckBox {
        color: white;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
    }
    QCheckBox::indicator:unchecked {
        border: 1px solid #555555;
        background-color: #3a3a3a;
        border-radius: 3px;
    }
    QCheckBox::indicator:checked {
        border: 1px solid #0078d4;
        background-color: #0078d4;
        border-radius: 3px;
    }
    QSplitter::handle {
        background-color: #3a3a3a;
    }
    QSplitter::handle:hover {
        background-color: #555555;
    }
"""


class BacktestMainWindow(QMainWindow):
    """백테스트 메인 윈도우 (독립 실행용)"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧪 알고리즘 백테스트 시스템")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 700)
        
        # 다크 테마 적용
        self.setStyleSheet(DARK_THEME)
        
        # 메인 위젯
        self.backtest_widget = BacktestWidget()
        self.setCentralWidget(self.backtest_widget)


def create_backtest_tab() -> BacktestWidget:
    """
    기존 GUI에 통합하기 위한 탭 위젯 생성
    
    사용법:
        from backtest_project.main import create_backtest_tab
        
        # MainWindow의 setup_ui()에서:
        backtest_tab = create_backtest_tab()
        self.tab_widget.addTab(backtest_tab, "🧪 알고리즘 검증")
    """
    return BacktestWidget()


def run_standalone():
    """독립 실행"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = BacktestMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_standalone()
