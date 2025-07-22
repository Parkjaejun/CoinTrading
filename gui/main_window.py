# gui/main_window.py
"""
OKX 자동매매 시스템 메인 GUI (수정된 버전)
PyQt5 호환성 문제 해결
"""

import sys
import os
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QProgressBar, QSplitter, QFrame, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QSlider, QDateEdit,
    QSystemTrayIcon, QMenu, QAction, QStatusBar, QToolBar, QSizePolicy
)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt, QDateTime, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPalette, QColor

try:
    import pyqtgraph as pg
except ImportError:
    print("pyqtgraph를 설치하세요: pip install pyqtgraph")
    pg = None

# 프로젝트 모듈들 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import (
        API_KEY, API_SECRET, PASSPHRASE, TRADING_CONFIG, 
        LONG_STRATEGY_CONFIG, SHORT_STRATEGY_CONFIG, NOTIFICATION_CONFIG
    )
    from okx.account_manager import AccountManager
    from utils.logger import log_system, log_error
except ImportError as e:
    print(f"모듈 임포트 오류: {e}")
    # 기본값 설정
    API_KEY = "your_api_key_here"
    TRADING_CONFIG = {"initial_capital": 10000, "symbols": ["BTC-USDT-SWAP"]}
    LONG_STRATEGY_CONFIG = {"leverage": 10}
    SHORT_STRATEGY_CONFIG = {"leverage": 3}
    NOTIFICATION_CONFIG = {}

class TradingSystemThread(QThread):
    """백그라운드 트레이딩 시스템 스레드"""
    
    # 시그널 정의
    status_updated = pyqtSignal(dict)
    position_updated = pyqtSignal(dict)
    trade_executed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    price_updated = pyqtSignal(str, float)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.should_stop = False
        
    def run(self):
        """메인 실행 루프"""
        self.is_running = True
        print("GUI: 트레이딩 시스템 시작")
        
        while self.is_running and not self.should_stop:
            try:
                # 가짜 상태 업데이트 (실제 구현시 실제 데이터로 교체)
                status = {
                    'is_connected': True,
                    'is_running': self.is_running,
                    'uptime': datetime.now(),
                    'error_count': 0
                }
                self.status_updated.emit(status)
                
                # 가짜 가격 업데이트
                import random
                fake_price = 45000 + random.uniform(-1000, 1000)
                self.price_updated.emit("BTC-USDT-SWAP", fake_price)
                
                # 1초 대기
                time.sleep(1)
                
            except Exception as e:
                self.error_occurred.emit(f"실행 오류: {str(e)}")
                time.sleep(5)
    
    def stop_trading(self):
        """트레이딩 중지"""
        self.should_stop = True
        self.is_running = False

class DashboardTab(QWidget):
    """대시보드 탭"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 상단 상태 패널
        status_layout = QHBoxLayout()
        
        self.connection_status = QLabel("🔴 연결 끊어짐")
        self.trading_status = QLabel("⏸️ 거래 중지")
        self.uptime_label = QLabel("운영시간: 00:00:00")
        self.total_pnl_label = QLabel("총 손익: $0.00")
        
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.trading_status)
        status_layout.addWidget(self.uptime_label)
        status_layout.addWidget(self.total_pnl_label)
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
        
        # 메인 컨텐츠 영역
        splitter = QSplitter()
        
        # 왼쪽 패널
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 포지션 현황
        position_group = QGroupBox("포지션 현황")
        position_layout = QVBoxLayout()
        
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(6)
        self.position_table.setHorizontalHeaderLabels([
            "심볼", "방향", "크기", "진입가", "현재가", "PnL"
        ])
        self.position_table.setMaximumHeight(200)
        
        position_layout.addWidget(self.position_table)
        position_group.setLayout(position_layout)
        left_layout.addWidget(position_group)
        
        # 최근 거래 내역
        trades_group = QGroupBox("최근 거래")
        trades_layout = QVBoxLayout()
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(5)
        self.trades_table.setHorizontalHeaderLabels([
            "시간", "심볼", "동작", "가격", "PnL"
        ])
        self.trades_table.setMaximumHeight(200)
        
        trades_layout.addWidget(self.trades_table)
        trades_group.setLayout(trades_layout)
        left_layout.addWidget(trades_group)
        
        # 오른쪽 패널 - 차트
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 가격 차트 (pyqtgraph 사용 가능한 경우에만)
        if pg is not None:
            chart_group = QGroupBox("실시간 차트")
            chart_layout = QVBoxLayout()
            
            self.price_chart = pg.PlotWidget()
            self.price_chart.setLabel('left', 'Price ($)')
            self.price_chart.setLabel('bottom', 'Time')
            self.price_chart.showGrid(x=True, y=True)
            
            chart_layout.addWidget(self.price_chart)
            chart_group.setLayout(chart_layout)
            right_layout.addWidget(chart_group)
            
            # 차트 데이터 초기화
            self.price_data = []
            self.time_data = []
        else:
            # pyqtgraph가 없는 경우 간단한 텍스트로 대체
            chart_group = QGroupBox("가격 정보")
            chart_layout = QVBoxLayout()
            self.price_label = QLabel("BTC-USDT-SWAP: $0.00")
            self.price_label.setStyleSheet("font-size: 24px; font-weight: bold;")
            chart_layout.addWidget(self.price_label)
            chart_group.setLayout(chart_layout)
            right_layout.addWidget(chart_group)
        
        # 전략 성과
        performance_group = QGroupBox("전략별 성과")
        perf_layout = QGridLayout()
        
        perf_layout.addWidget(QLabel("롱 전략:"), 0, 0)
        self.long_performance = QLabel("승률: 0%, 손익: $0")
        perf_layout.addWidget(self.long_performance, 0, 1)
        
        perf_layout.addWidget(QLabel("숏 전략:"), 1, 0)
        self.short_performance = QLabel("승률: 0%, 손익: $0")
        perf_layout.addWidget(self.short_performance, 1, 1)
        
        performance_group.setLayout(perf_layout)
        right_layout.addWidget(performance_group)
        
        # 스플리터에 패널 추가
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def setup_timer(self):
        """타이머 설정"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # 1초마다 업데이트
    
    def update_status(self, status: Dict[str, Any]):
        """상태 업데이트"""
        if status.get('is_connected', False):
            self.connection_status.setText("🟢 연결됨")
            self.connection_status.setStyleSheet("color: green;")
        else:
            self.connection_status.setText("🔴 연결 끊어짐")
            self.connection_status.setStyleSheet("color: red;")
        
        if status.get('is_running', False):
            self.trading_status.setText("▶️ 거래 중")
            self.trading_status.setStyleSheet("color: green;")
        else:
            self.trading_status.setText("⏸️ 거래 중지")
            self.trading_status.setStyleSheet("color: orange;")
    
    def update_positions(self, positions: Dict[str, Any]):
        """포지션 업데이트"""
        # 간단한 구현
        pass
    
    def update_chart(self, symbol: str, price: float):
        """차트 업데이트"""
        if pg is not None and hasattr(self, 'price_chart'):
            current_time = time.time()
            
            self.time_data.append(current_time)
            self.price_data.append(price)
            
            # 최근 100개 데이터만 유지
            if len(self.price_data) > 100:
                self.time_data = self.time_data[-100:]
                self.price_data = self.price_data[-100:]
            
            # 차트 업데이트
            if len(self.price_data) > 1:
                self.price_chart.clear()
                self.price_chart.plot(
                    self.time_data, self.price_data,
                    pen=pg.mkPen(color='#00ff00', width=2)
                )
        else:
            # pyqtgraph가 없는 경우 텍스트로 표시
            if hasattr(self, 'price_label'):
                self.price_label.setText(f"{symbol}: ${price:,.2f}")
    
    def update_display(self):
        """디스플레이 주기적 업데이트"""
        self.uptime_label.setText(f"운영시간: {datetime.now().strftime('%H:%M:%S')}")

class SettingsTab(QWidget):
    """설정 탭"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # API 설정
        api_group = QGroupBox("API 설정")
        api_layout = QGridLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setText(API_KEY if API_KEY != "your_api_key_here" else "")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        
        self.test_connection_btn = QPushButton("연결 테스트")
        self.test_connection_btn.clicked.connect(self.test_api_connection)
        
        api_layout.addWidget(QLabel("API Key:"), 0, 0)
        api_layout.addWidget(self.api_key_edit, 0, 1)
        api_layout.addWidget(self.test_connection_btn, 1, 1)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def test_api_connection(self):
        """API 연결 테스트"""
        try:
            account = AccountManager()
            balances = account.get_account_balance()
            
            if balances:
                QMessageBox.information(self, "연결 테스트", "✅ API 연결 성공!")
            else:
                QMessageBox.warning(self, "연결 테스트", "❌ API 연결 실패")
        except Exception as e:
            QMessageBox.critical(self, "연결 테스트", f"❌ 연결 오류: {str(e)}")

class TradingMainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.trading_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("OKX 자동매매 시스템 v1.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메뉴바 설정
        self.setup_menubar()
        
        # 툴바 설정 (수정된 버전)
        self.setup_toolbar()
        
        # 상태바 설정
        self.setup_statusbar()
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        
        # 각 탭 추가
        self.dashboard_tab = DashboardTab()
        self.settings_tab = SettingsTab()
        
        self.tab_widget.addTab(self.dashboard_tab, "📊 대시보드")
        self.tab_widget.addTab(self.settings_tab, "⚙️ 설정")
        
        # 레이아웃 설정
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)
        
        # 스타일 적용
        self.apply_dark_theme()
    
    def setup_menubar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # File 메뉴
        file_menu = menubar.addMenu('파일')
        
        exit_action = QAction('종료', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Trading 메뉴
        trading_menu = menubar.addMenu('거래')
        
        self.start_trading_action = QAction('거래 시작', self)
        self.start_trading_action.triggered.connect(self.start_trading)
        trading_menu.addAction(self.start_trading_action)
        
        self.stop_trading_action = QAction('거래 중지', self)
        self.stop_trading_action.triggered.connect(self.stop_trading)
        self.stop_trading_action.setEnabled(False)
        trading_menu.addAction(self.stop_trading_action)
    
    def setup_toolbar(self):
        """툴바 설정 - QToolBar 호환성 수정"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 거래 시작/중지 버튼
        self.start_btn = QPushButton("▶️ 시작")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.start_btn.clicked.connect(self.start_trading)
        
        self.stop_btn = QPushButton("⏸️ 중지")
        self.stop_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 8px;")
        self.stop_btn.clicked.connect(self.stop_trading)
        self.stop_btn.setEnabled(False)
        
        self.emergency_btn = QPushButton("🚨 긴급정지")
        self.emergency_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 8px;")
        self.emergency_btn.clicked.connect(self.emergency_stop)
        
        # 연결 상태 표시
        self.connection_indicator = QLabel("🔴")
        self.connection_indicator.setToolTip("API 연결 상태")
        
        # 툴바에 위젯 추가
        toolbar.addWidget(self.start_btn)
        toolbar.addWidget(self.stop_btn)
        toolbar.addSeparator()
        toolbar.addWidget(self.emergency_btn)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("연결:"))
        toolbar.addWidget(self.connection_indicator)
        
        # Stretch 대신 빈 위젯 추가로 우측 정렬 효과
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
    
    def setup_statusbar(self):
        """상태바 설정"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel("준비")
        self.time_label = QLabel(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.time_label)
        
        # 시간 업데이트 타이머
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
    
    def apply_dark_theme(self):
        """다크 테마 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #3c3c3c;
            }
            QTabBar::tab {
                background-color: #555555;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin: 5px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #555555;
                color: #ffffff;
                border: 1px solid #666666;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QLineEdit {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
    
    def start_trading(self):
        """거래 시작"""
        if self.trading_thread is None or not self.trading_thread.isRunning():
            self.trading_thread = TradingSystemThread()
            
            # 시그널 연결
            self.trading_thread.status_updated.connect(self.dashboard_tab.update_status)
            self.trading_thread.price_updated.connect(self.dashboard_tab.update_chart)
            
            # 스레드 시작
            self.trading_thread.start()
            
            # UI 상태 업데이트
            self.start_btn.setEnabled(False)
            self.start_trading_action.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.stop_trading_action.setEnabled(True)
            
            self.status_label.setText("거래 중")
            self.connection_indicator.setText("🟢")
    
    def stop_trading(self):
        """거래 중지"""
        if self.trading_thread and self.trading_thread.isRunning():
            self.trading_thread.stop_trading()
            self.trading_thread.wait(5000)  # 5초 대기
            
            # UI 상태 업데이트
            self.start_btn.setEnabled(True)
            self.start_trading_action.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.stop_trading_action.setEnabled(False)
            
            self.status_label.setText("중지됨")
            self.connection_indicator.setText("🔴")
    
    def emergency_stop(self):
        """긴급 정지"""
        reply = QMessageBox.critical(self, "긴급 정지", 
                                   "⚠️ 긴급 정지하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.stop_trading()
    
    def update_time(self):
        """시간 업데이트"""
        self.time_label.setText(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    def closeEvent(self, event):
        """창 종료 이벤트"""
        if self.trading_thread and self.trading_thread.isRunning():
            reply = QMessageBox.question(self, "종료 확인", 
                                       "거래가 진행 중입니다. 종료하시겠습니까?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.stop_trading()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    app.setApplicationName("OKX 자동매매 시스템")
    app.setStyle('Fusion')
    
    # 메인 윈도우 생성 및 표시
    window = TradingMainWindow()
    window.show()
    
    # 이벤트 루프 실행
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()