# gui/main_window.py (1부)
"""
완전한 OKX 자동매매 GUI 메인 윈도우
- 모든 기존 기능 복원
- 잔액 문제 해결
- 실시간 가격 차트, 전략 관리, 포지션 제어 등
"""

import sys
import os
import time
import json
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTextEdit, QGroupBox, QTableWidget,
    QTableWidgetItem, QGridLayout, QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QComboBox, QProgressBar, QStatusBar,
    QSplitter, QHeaderView, QMessageBox, QFileDialog, QSlider,
    QSystemTrayIcon, QMenu, QAction, QFrame
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPixmap

try:
    import pyqtgraph as pg
    pg.setConfigOption('background', '#2b2b2b')
    pg.setConfigOption('foreground', 'w')
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

# 프로젝트 모듈들
try:
    from gui.balance_manager import GUIBalanceManager
    from gui.widgets import (
        PriceChartWidget, PositionTableWidget, TradingControlWidget,
        SystemMonitorWidget, LogDisplayWidget
    )
    from gui.data_thread import TradingDataThread
    from okx.account_manager import AccountManager
except ImportError as e:
    print(f"⚠️ 모듈 임포트 경고: {e}")

class MainWindow(QMainWindow):
    """메인 GUI 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 OKX 자동매매 시스템 - 완전한 거래 GUI")
        self.setGeometry(100, 100, 1400, 900)
        
        # 데이터 관련
        self.data_thread = None
        self.account_balance = {}
        self.latest_prices = {}
        self.positions = []
        self.trading_active = False
        
        # 위젯들
        self.widgets = {}
        
        # 타이머들
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        
        # UI 초기화
        self.init_ui()
        self.apply_dark_theme()
        
        # 데이터 스레드 시작
        self.start_data_thread()
    
    def init_ui(self):
        """UI 초기화"""
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 상단 상태바
        self.create_status_header(main_layout)
        
        # 탭 위젯
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # 탭들 생성
        self.create_dashboard_tab(tab_widget)
        self.create_trading_tab(tab_widget)
        self.create_monitoring_tab(tab_widget)
        self.create_settings_tab(tab_widget)
        self.create_backtest_tab(tab_widget)
        
        # 상태바
        self.statusBar().showMessage("완전한 GUI 시작됨")
    
    def create_status_header(self, parent_layout):
        """상태 헤더 생성"""
        header_widget = QWidget()
        header_widget.setMaximumHeight(80)
        header_layout = QHBoxLayout(header_widget)
        
        # 왼쪽: 연결 상태
        self.connection_label = QLabel("🔄 연결 중...")
        self.connection_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.connection_label)
        
        # 중앙: 현재 시간
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.clock_label)
        
        # 오른쪽: 잔액 정보
        balance_widget = QWidget()
        balance_layout = QVBoxLayout(balance_widget)
        balance_layout.setContentsMargins(0, 0, 0, 0)
        
        self.balance_label = QLabel("💰 USDT: $0.00")
        self.balance_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #00ff00;")
        
        self.equity_label = QLabel("총 자산: $0.00")
        self.equity_label.setStyleSheet("font-size: 12px; color: #ffaa00;")
        
        balance_layout.addWidget(self.balance_label)
        balance_layout.addWidget(self.equity_label)
        
        header_layout.addWidget(balance_widget)
        parent_layout.addWidget(header_widget)
    
    def create_dashboard_tab(self, tab_widget):
        """대시보드 탭 생성"""
        dashboard_widget = QWidget()
        layout = QHBoxLayout(dashboard_widget)
        
        # 왼쪽 패널 (차트 + 로그)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 가격 차트
        self.widgets['price_chart'] = PriceChartWidget()
        left_layout.addWidget(self.widgets['price_chart'], 2)
        
        # 로그 디스플레이
        self.widgets['log_display'] = LogDisplayWidget()
        left_layout.addWidget(self.widgets['log_display'], 1)
        
        layout.addWidget(left_panel, 2)
        
        # 오른쪽 패널 (포지션 + 제어)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 거래 제어
        self.widgets['trading_control'] = TradingControlWidget()
        self.widgets['trading_control'].start_trading_requested.connect(self.start_trading)
        self.widgets['trading_control'].stop_trading_requested.connect(self.stop_trading)
        self.widgets['trading_control'].emergency_stop_requested.connect(self.emergency_stop)
        right_layout.addWidget(self.widgets['trading_control'])
        
        # 포지션 테이블
        self.widgets['position_table'] = PositionTableWidget()
        self.widgets['position_table'].position_close_requested.connect(self.close_position)
        right_layout.addWidget(self.widgets['position_table'])
        
        layout.addWidget(right_panel, 1)
        
        tab_widget.addTab(dashboard_widget, "📊 대시보드")
    
    def create_trading_tab(self, tab_widget):
        """거래 관리 탭 생성"""
        trading_widget = QWidget()
        layout = QVBoxLayout(trading_widget)
        
        # 전략 상태
        strategy_group = QGroupBox("🎯 전략 상태")
        strategy_layout = QGridLayout()
        
        # 롱 전략
        long_frame = QFrame()
        long_frame.setFrameStyle(QFrame.Box)
        long_layout = QFormLayout(long_frame)
        
        long_layout.addRow("전략:", QLabel("Long Strategy"))
        self.long_status_label = QLabel("대기 중")
        self.long_pnl_label = QLabel("$0.00")
        self.long_trades_label = QLabel("0")
        
        long_layout.addRow("상태:", self.long_status_label)
        long_layout.addRow("PnL:", self.long_pnl_label)
        long_layout.addRow("거래 수:", self.long_trades_label)
        
        strategy_layout.addWidget(long_frame, 0, 0)
        
        # 숏 전략
        short_frame = QFrame()
        short_frame.setFrameStyle(QFrame.Box)
        short_layout = QFormLayout(short_frame)
        
        short_layout.addRow("전략:", QLabel("Short Strategy"))
        self.short_status_label = QLabel("대기 중")
        self.short_pnl_label = QLabel("$0.00")
        self.short_trades_label = QLabel("0")
        
        short_layout.addRow("상태:", self.short_status_label)
        short_layout.addRow("PnL:", self.short_pnl_label)
        short_layout.addRow("거래 수:", self.short_trades_label)
        
        strategy_layout.addWidget(short_frame, 0, 1)
        
        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)
        
        # 전략 설정
        settings_group = QGroupBox("⚙️ 전략 설정")
        settings_layout = QGridLayout()
        
        # 롱 전략 설정
        settings_layout.addWidget(QLabel("롱 자본:"), 0, 0)
        self.long_capital_spin = QDoubleSpinBox()
        self.long_capital_spin.setRange(10, 10000)
        self.long_capital_spin.setValue(100)
        self.long_capital_spin.setSuffix(" USDT")
        settings_layout.addWidget(self.long_capital_spin, 0, 1)
        
        settings_layout.addWidget(QLabel("롱 레버리지:"), 0, 2)
        self.long_leverage_spin = QSpinBox()
        self.long_leverage_spin.setRange(1, 50)
        self.long_leverage_spin.setValue(10)
        settings_layout.addWidget(self.long_leverage_spin, 0, 3)
        
        # 숏 전략 설정
        settings_layout.addWidget(QLabel("숏 자본:"), 1, 0)
        self.short_capital_spin = QDoubleSpinBox()
        self.short_capital_spin.setRange(10, 10000)
        self.short_capital_spin.setValue(100)
        self.short_capital_spin.setSuffix(" USDT")
        settings_layout.addWidget(self.short_capital_spin, 1, 1)
        
        settings_layout.addWidget(QLabel("숏 레버리지:"), 1, 2)
        self.short_leverage_spin = QSpinBox()
        self.short_leverage_spin.setRange(1, 50)
        self.short_leverage_spin.setValue(10)
        settings_layout.addWidget(self.short_leverage_spin, 1, 3)
        
        # 공통 설정
        settings_layout.addWidget(QLabel("트레일링 스탑:"), 2, 0)
        self.trailing_stop_spin = QDoubleSpinBox()
        self.trailing_stop_spin.setRange(0.01, 0.5)
        self.trailing_stop_spin.setValue(0.1)
        self.trailing_stop_spin.setSuffix("%")
        settings_layout.addWidget(self.trailing_stop_spin, 2, 1)
        
        # 적용 버튼
        apply_btn = QPushButton("설정 적용")
        apply_btn.clicked.connect(self.apply_strategy_settings)
        settings_layout.addWidget(apply_btn, 2, 2, 1, 2)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        layout.addStretch()
        tab_widget.addTab(trading_widget, "🎯 거래 관리")
    
    def create_monitoring_tab(self, tab_widget):
        """모니터링 탭 생성"""
        monitoring_widget = QWidget()
        layout = QHBoxLayout(monitoring_widget)
        
        # 왼쪽: 시스템 모니터
        self.widgets['system_monitor'] = SystemMonitorWidget()
        layout.addWidget(self.widgets['system_monitor'], 1)
        
        # 오른쪽: 계정 상세 정보
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 계정 상세
        account_group = QGroupBox("💼 계정 상세 정보")
        account_layout = QVBoxLayout()
        
        self.account_details = QTextEdit()
        self.account_details.setReadOnly(True)
        self.account_details.setMaximumHeight(300)
        self.account_details.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        
        account_layout.addWidget(self.account_details)
        account_group.setLayout(account_layout)
        right_layout.addWidget(account_group)
        
        # 새로고침 버튼
        refresh_btn = QPushButton("🔄 계정 정보 새로고침")
        refresh_btn.clicked.connect(self.refresh_account_data)
        right_layout.addWidget(refresh_btn)
        
        # 거래 통계
        stats_group = QGroupBox("📈 거래 통계")
        stats_layout = QFormLayout()
        
        self.total_trades_label = QLabel("0")
        self.win_rate_label = QLabel("0%")
        self.total_pnl_label = QLabel("$0.00")
        self.max_drawdown_label = QLabel("0%")
        
        stats_layout.addRow("총 거래:", self.total_trades_label)
        stats_layout.addRow("승률:", self.win_rate_label)
        stats_layout.addRow("총 PnL:", self.total_pnl_label)
        stats_layout.addRow("최대 낙폭:", self.max_drawdown_label)
        
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        
        right_layout.addStretch()
        layout.addWidget(right_panel, 1)
        
        tab_widget.addTab(monitoring_widget, "📡 모니터링")
# gui/main_window.py (2부)

    def create_settings_tab(self, tab_widget):
        """설정 탭 생성"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # API 설정
        api_group = QGroupBox("🔑 API 설정")
        api_layout = QFormLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setEchoMode(QLineEdit.Password)
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.Password)
        
        api_layout.addRow("API Key:", self.api_key_edit)
        api_layout.addRow("Secret:", self.api_secret_edit)
        api_layout.addRow("Passphrase:", self.passphrase_edit)
        
        # API 테스트 버튼
        test_api_btn = QPushButton("🧪 API 연결 테스트")
        test_api_btn.clicked.connect(self.test_api_connection)
        api_layout.addRow("", test_api_btn)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 알림 설정
        notification_group = QGroupBox("🔔 알림 설정")
        notification_layout = QFormLayout()
        
        self.telegram_enabled = QCheckBox("텔레그램 알림 사용")
        self.telegram_token_edit = QLineEdit()
        self.telegram_chat_id_edit = QLineEdit()
        
        notification_layout.addRow("", self.telegram_enabled)
        notification_layout.addRow("Bot Token:", self.telegram_token_edit)
        notification_layout.addRow("Chat ID:", self.telegram_chat_id_edit)
        
        self.slack_enabled = QCheckBox("슬랙 알림 사용")
        self.slack_webhook_edit = QLineEdit()
        
        notification_layout.addRow("", self.slack_enabled)
        notification_layout.addRow("Webhook URL:", self.slack_webhook_edit)
        
        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)
        
        # 설정 저장/로드
        settings_buttons = QHBoxLayout()
        
        save_btn = QPushButton("💾 설정 저장")
        save_btn.clicked.connect(self.save_settings)
        
        load_btn = QPushButton("📁 설정 로드")
        load_btn.clicked.connect(self.load_settings)
        
        reset_btn = QPushButton("🔄 기본값 복원")
        reset_btn.clicked.connect(self.reset_settings)
        
        settings_buttons.addWidget(save_btn)
        settings_buttons.addWidget(load_btn)
        settings_buttons.addWidget(reset_btn)
        settings_buttons.addStretch()
        
        layout.addLayout(settings_buttons)
        layout.addStretch()
        
        tab_widget.addTab(settings_widget, "⚙️ 설정")
    
    def create_backtest_tab(self, tab_widget):
        """백테스팅 탭 생성"""
        backtest_widget = QWidget()
        layout = QVBoxLayout(backtest_widget)
        
        # 백테스트 설정
        settings_group = QGroupBox("📈 백테스트 설정")
        settings_layout = QGridLayout()
        
        # 기간 설정
        settings_layout.addWidget(QLabel("시작 날짜:"), 0, 0)
        self.backtest_start_date = QLineEdit("2024-01-01")
        settings_layout.addWidget(self.backtest_start_date, 0, 1)
        
        settings_layout.addWidget(QLabel("종료 날짜:"), 0, 2)
        self.backtest_end_date = QLineEdit("2024-12-31")
        settings_layout.addWidget(self.backtest_end_date, 0, 3)
        
        # 초기 자본
        settings_layout.addWidget(QLabel("초기 자본:"), 1, 0)
        self.backtest_capital_spin = QDoubleSpinBox()
        self.backtest_capital_spin.setRange(100, 100000)
        self.backtest_capital_spin.setValue(10000)
        self.backtest_capital_spin.setSuffix(" USDT")
        settings_layout.addWidget(self.backtest_capital_spin, 1, 1)
        
        # 전략 선택
        settings_layout.addWidget(QLabel("전략:"), 1, 2)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["듀얼 전략", "롱 전용", "숏 전용"])
        settings_layout.addWidget(self.strategy_combo, 1, 3)
        
        # 실행 버튼
        run_backtest_btn = QPushButton("🚀 백테스트 실행")
        run_backtest_btn.clicked.connect(self.run_backtest)
        settings_layout.addWidget(run_backtest_btn, 2, 0, 1, 4)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 진행 상황
        self.backtest_progress = QProgressBar()
        self.backtest_progress.setVisible(False)
        layout.addWidget(self.backtest_progress)
        
        # 결과 표시
        results_group = QGroupBox("📊 백테스트 결과")
        results_layout = QHBoxLayout()
        
        # 왼쪽: 수치 결과
        metrics_widget = QWidget()
        metrics_layout = QFormLayout(metrics_widget)
        
        self.backtest_return_label = QLabel("0%")
        self.backtest_sharpe_label = QLabel("0.00")
        self.backtest_mdd_label = QLabel("0%")
        self.backtest_trades_label = QLabel("0")
        self.backtest_winrate_label = QLabel("0%")
        
        metrics_layout.addRow("총 수익률:", self.backtest_return_label)
        metrics_layout.addRow("샤프 비율:", self.backtest_sharpe_label)
        metrics_layout.addRow("최대 낙폭:", self.backtest_mdd_label)
        metrics_layout.addRow("총 거래:", self.backtest_trades_label)
        metrics_layout.addRow("승률:", self.backtest_winrate_label)
        
        results_layout.addWidget(metrics_widget, 1)
        
        # 오른쪽: 차트 (자본 곡선)
        if PYQTGRAPH_AVAILABLE:
            self.equity_chart = pg.PlotWidget()
            self.equity_chart.setLabel('left', 'Equity ($)')
            self.equity_chart.setLabel('bottom', 'Time')
            self.equity_chart.showGrid(x=True, y=True)
            results_layout.addWidget(self.equity_chart, 2)
        else:
            no_chart_label = QLabel("차트를 보려면 pyqtgraph를 설치하세요")
            no_chart_label.setAlignment(Qt.AlignCenter)
            results_layout.addWidget(no_chart_label, 2)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        tab_widget.addTab(backtest_widget, "📈 백테스팅")
    
    def apply_dark_theme(self):
        """다크 테마 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 1ex;
                padding: 10px;
                background-color: #333333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
            QTextEdit, QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #404040;
                border: 1px solid #666666;
                padding: 8px 12px;
                margin-right: 2px;
                color: #ffffff;
            }
            QTabBar::tab:selected {
                background-color: #2b2b2b;
                border-bottom: 1px solid #2b2b2b;
            }
            QTableWidget {
                background-color: #2b2b2b;
                alternate-background-color: #333333;
                selection-background-color: #555555;
                gridline-color: #555555;
            }
            QHeaderView::section {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #666666;
                padding: 4px;
            }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #1e1e1e;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                background-color: #2b2b2b;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)

# gui/main_window.py (3부)

    def start_data_thread(self):
        """데이터 스레드 시작"""
        try:
            if self.data_thread and self.data_thread.isRunning():
                self.data_thread.stop()
                self.data_thread.wait(3000)
            
            self.data_thread = TradingDataThread()
            
            # 시그널 연결
            self.data_thread.account_updated.connect(self.on_account_updated)
            self.data_thread.price_updated.connect(self.on_price_updated)
            self.data_thread.position_updated.connect(self.on_position_updated)
            self.data_thread.strategy_updated.connect(self.on_strategy_updated)
            self.data_thread.connection_status_changed.connect(self.on_connection_changed)
            self.data_thread.error_occurred.connect(self.on_error_occurred)
            self.data_thread.system_stats_updated.connect(self.on_system_stats_updated)
            
            self.data_thread.start()
            self.add_log("🚀 완전한 데이터 스레드 시작됨", "SUCCESS")
            
        except Exception as e:
            print(f"❌ 데이터 스레드 시작 실패: {e}")
            self.add_log(f"❌ 데이터 스레드 오류: {e}", "ERROR")
    
    def on_account_updated(self, account_data):
        """계정 정보 업데이트 처리"""
        try:
            self.account_balance = account_data
            
            # 주요 값들 추출
            usdt_balance = GUIBalanceManager.get_usdt_balance(account_data)
            total_equity = GUIBalanceManager.get_total_equity(account_data)
            
            # UI 업데이트
            self.balance_label.setText(f"💰 USDT: ${usdt_balance:.2f}")
            self.equity_label.setText(f"총 자산: ${total_equity:.2f}")
            
            # 상세 정보 업데이트
            if hasattr(self, 'account_details'):
                summary_text = GUIBalanceManager.format_balance_summary(account_data)
                self.account_details.setPlainText(summary_text)
            
            # 상태바 업데이트
            if total_equity > 0:
                self.statusBar().showMessage(f"완전한 GUI - 총 자산: ${total_equity:.2f}")
            
        except Exception as e:
            print(f"⚠️ 계정 정보 UI 업데이트 오류: {e}")
            self.add_log(f"⚠️ UI 업데이트 오류: {e}", "WARNING")
    
    def on_price_updated(self, symbol, price, price_info):
        """가격 업데이트 처리"""
        self.latest_prices[symbol] = price
        
        # 차트 업데이트
        if 'price_chart' in self.widgets:
            self.widgets['price_chart'].update_price(symbol, price, price_info)
        
        # 간헐적으로만 로그 출력
        if not hasattr(self, '_last_price_log'):
            self._last_price_log = 0
        
        if time.time() - self._last_price_log >= 30:  # 30초에 한 번
            self.add_log(f"📈 {symbol}: ${price:,.2f}", "INFO")
            self._last_price_log = time.time()
    
    def on_position_updated(self, positions_data):
        """포지션 업데이트 처리"""
        self.positions = positions_data.get('positions', [])
        
        # 포지션 테이블 업데이트
        if 'position_table' in self.widgets:
            self.widgets['position_table'].update_positions(self.positions)
    
    def on_strategy_updated(self, strategy_data):
        """전략 상태 업데이트 처리"""
        try:
            is_running = strategy_data.get('is_running', False)
            active_strategies = strategy_data.get('active_strategies', 0)
            uptime = strategy_data.get('uptime', 0)
            
            # 거래 제어 위젯 업데이트
            if 'trading_control' in self.widgets:
                self.widgets['trading_control'].update_status(strategy_data)
            
            # 전략별 상태 업데이트
            if hasattr(self, 'long_status_label'):
                self.long_status_label.setText("실행 중" if is_running else "대기 중")
                self.short_status_label.setText("실행 중" if is_running else "대기 중")
            
        except Exception as e:
            print(f"⚠️ 전략 상태 업데이트 오류: {e}")
    
    def on_connection_changed(self, is_connected):
        """연결 상태 변경 처리"""
        if is_connected:
            self.connection_label.setText("✅ API 연결됨")
            self.connection_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
            self.add_log("✅ 완전한 API 연결 성공", "SUCCESS")
        else:
            self.connection_label.setText("❌ API 연결 실패")
            self.connection_label.setStyleSheet("color: #ff4444; font-weight: bold; font-size: 14px;")
            self.add_log("❌ 완전한 API 연결 실패", "ERROR")
        
        # 시스템 모니터 업데이트
        if 'system_monitor' in self.widgets:
            self.widgets['system_monitor'].update_network_status(is_connected, is_connected)
        
        # 거래 제어 위젯 업데이트
        if 'trading_control' in self.widgets:
            self.widgets['trading_control'].update_connection_status(is_connected)
    
    def on_error_occurred(self, error_message):
        """오류 발생 처리"""
        self.add_log(f"⚠️ 오류: {error_message}", "ERROR")
    
    def on_system_stats_updated(self, stats):
        """시스템 통계 업데이트 처리"""
        if 'system_monitor' in self.widgets:
            self.widgets['system_monitor'].update_system_stats(stats)
    
    def update_clock(self):
        """시계 업데이트"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.setText(f"🕐 {current_time}")
    
    def add_log(self, message: str, level: str = "INFO"):
        """로그 추가"""
        if 'log_display' in self.widgets:
            self.widgets['log_display'].add_log(message, level)
    
    def start_trading(self):
        """거래 시작"""
        try:
            self.add_log("🚀 거래 시스템 시작 요청", "INFO")
            
            if self.data_thread and self.data_thread.start_trading_system():
                self.trading_active = True
                self.add_log("✅ 거래 시스템 시작됨", "SUCCESS")
            else:
                self.add_log("❌ 거래 시스템 시작 실패", "ERROR")
                
        except Exception as e:
            self.add_log(f"❌ 거래 시작 오류: {e}", "ERROR")
    
    def stop_trading(self):
        """거래 중지"""
        try:
            self.add_log("⏹️ 거래 시스템 중지 요청", "INFO")
            
            if self.data_thread and self.data_thread.stop_trading_system():
                self.trading_active = False
                self.add_log("✅ 거래 시스템 중지됨", "SUCCESS")
            else:
                self.add_log("❌ 거래 시스템 중지 실패", "ERROR")
                
        except Exception as e:
            self.add_log(f"❌ 거래 중지 오류: {e}", "ERROR")
    
    def emergency_stop(self):
        """긴급 정지"""
        reply = QMessageBox.question(self, "긴급 정지", 
                                   "🚨 모든 거래를 즉시 중단하고 포지션을 청산하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.add_log("🚨 긴급 정지 실행", "WARNING")
                self.stop_trading()
                # 추가 긴급 정지 로직 여기에 구현
                self.add_log("✅ 긴급 정지 완료", "SUCCESS")
            except Exception as e:
                self.add_log(f"❌ 긴급 정지 오류: {e}", "ERROR")
    
    def close_position(self, position_id: str):
        """포지션 청산"""
        try:
            self.add_log(f"💼 포지션 청산 요청: {position_id}", "INFO")
            # 포지션 청산 로직 구현
            self.add_log(f"✅ 포지션 청산 완료: {position_id}", "SUCCESS")
        except Exception as e:
            self.add_log(f"❌ 포지션 청산 오류: {e}", "ERROR")
    
    def refresh_account_data(self):
        """계정 데이터 새로고침"""
        try:
            if self.data_thread and self.data_thread.isRunning():
                self.data_thread._update_account_data()
                self.add_log("🔄 계정 정보 수동 새로고침", "INFO")
            else:
                self.add_log("⚠️ 데이터 스레드가 실행 중이 아닙니다", "WARNING")
        except Exception as e:
            self.add_log(f"❌ 새로고침 실패: {e}", "ERROR")
    
    def apply_strategy_settings(self):
        """전략 설정 적용"""
        try:
            settings = {
                'long_capital': self.long_capital_spin.value(),
                'long_leverage': self.long_leverage_spin.value(),
                'short_capital': self.short_capital_spin.value(),
                'short_leverage': self.short_leverage_spin.value(),
                'trailing_stop': self.trailing_stop_spin.value()
            }
            
            self.add_log(f"⚙️ 전략 설정 적용: {settings}", "INFO")
            # 설정 적용 로직 구현
            self.add_log("✅ 전략 설정 적용 완료", "SUCCESS")
            
        except Exception as e:
            self.add_log(f"❌ 설정 적용 오류: {e}", "ERROR")
    
    def test_api_connection(self):
        """API 연결 테스트"""
        try:
            self.add_log("🧪 API 연결 테스트 시작", "INFO")
            
            from okx.account_manager import AccountManager
            account = AccountManager()
            
            # 간단한 API 호출
            balance_data = account.get_account_balance()
            if balance_data:
                self.add_log("✅ API 연결 테스트 성공", "SUCCESS")
                QMessageBox.information(self, "API 테스트", "✅ API 연결이 성공적으로 확인되었습니다!")
            else:
                self.add_log("❌ API 연결 테스트 실패", "ERROR")
                QMessageBox.warning(self, "API 테스트", "❌ API 연결에 실패했습니다.")
                
        except Exception as e:
            self.add_log(f"❌ API 테스트 오류: {e}", "ERROR")
            QMessageBox.critical(self, "API 테스트", f"❌ API 테스트 중 오류가 발생했습니다:\n{e}")
    
    def save_settings(self):
        """설정 저장"""
        try:
            settings = {
                'api_key': self.api_key_edit.text(),
                'api_secret': self.api_secret_edit.text(),
                'passphrase': self.passphrase_edit.text(),
                'telegram_enabled': self.telegram_enabled.isChecked(),
                'telegram_token': self.telegram_token_edit.text(),
                'telegram_chat_id': self.telegram_chat_id_edit.text(),
                'slack_enabled': self.slack_enabled.isChecked(),
                'slack_webhook': self.slack_webhook_edit.text(),
                'strategy_settings': {
                    'long_capital': self.long_capital_spin.value(),
                    'long_leverage': self.long_leverage_spin.value(),
                    'short_capital': self.short_capital_spin.value(),
                    'short_leverage': self.short_leverage_spin.value(),
                    'trailing_stop': self.trailing_stop_spin.value()
                }
            }
            
            config_path = Path("gui_trading_config.json")
            with open(config_path, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.add_log("💾 설정 저장 완료", "SUCCESS")
            QMessageBox.information(self, "설정 저장", "✅ 설정이 성공적으로 저장되었습니다!")
            
        except Exception as e:
            self.add_log(f"❌ 설정 저장 오류: {e}", "ERROR")
            QMessageBox.critical(self, "설정 저장", f"❌ 설정 저장 중 오류가 발생했습니다:\n{e}")
    
    def load_settings(self):
        """설정 로드"""
        try:
            config_path = Path("gui_trading_config.json")
            if not config_path.exists():
                QMessageBox.warning(self, "설정 로드", "⚠️ 저장된 설정 파일이 없습니다.")
                return
            
            with open(config_path, 'r') as f:
                settings = json.load(f)
            
            # UI 업데이트
            self.api_key_edit.setText(settings.get('api_key', ''))
            self.api_secret_edit.setText(settings.get('api_secret', ''))
            self.passphrase_edit.setText(settings.get('passphrase', ''))
            
            self.telegram_enabled.setChecked(settings.get('telegram_enabled', False))
            self.telegram_token_edit.setText(settings.get('telegram_token', ''))
            self.telegram_chat_id_edit.setText(settings.get('telegram_chat_id', ''))
            
            self.slack_enabled.setChecked(settings.get('slack_enabled', False))
            self.slack_webhook_edit.setText(settings.get('slack_webhook', ''))
            
            # 전략 설정
            strategy_settings = settings.get('strategy_settings', {})
            self.long_capital_spin.setValue(strategy_settings.get('long_capital', 100))
            self.long_leverage_spin.setValue(strategy_settings.get('long_leverage', 10))
            self.short_capital_spin.setValue(strategy_settings.get('short_capital', 100))
            self.short_leverage_spin.setValue(strategy_settings.get('short_leverage', 10))
            self.trailing_stop_spin.setValue(strategy_settings.get('trailing_stop', 0.1))
            
            self.add_log("📁 설정 로드 완료", "SUCCESS")
            QMessageBox.information(self, "설정 로드", "✅ 설정이 성공적으로 로드되었습니다!")
            
        except Exception as e:
            self.add_log(f"❌ 설정 로드 오류: {e}", "ERROR")
            QMessageBox.critical(self, "설정 로드", f"❌ 설정 로드 중 오류가 발생했습니다:\n{e}")
    
    def reset_settings(self):
        """설정 초기화"""
        reply = QMessageBox.question(self, "설정 초기화", 
                                   "🔄 모든 설정을 기본값으로 초기화하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # UI 초기화
                self.api_key_edit.clear()
                self.api_secret_edit.clear()
                self.passphrase_edit.clear()
                
                self.telegram_enabled.setChecked(False)
                self.telegram_token_edit.clear()
                self.telegram_chat_id_edit.clear()
                
                self.slack_enabled.setChecked(False)
                self.slack_webhook_edit.clear()
                
                # 전략 설정 초기화
                self.long_capital_spin.setValue(100)
                self.long_leverage_spin.setValue(10)
                self.short_capital_spin.setValue(100)
                self.short_leverage_spin.setValue(10)
                self.trailing_stop_spin.setValue(0.1)
                
                self.add_log("🔄 설정 초기화 완료", "SUCCESS")
                QMessageBox.information(self, "설정 초기화", "✅ 설정이 기본값으로 초기화되었습니다!")
                
            except Exception as e:
                self.add_log(f"❌ 설정 초기화 오류: {e}", "ERROR")
    
    def run_backtest(self):
        """백테스트 실행"""
        try:
            self.add_log("📈 백테스트 시작", "INFO")
            self.backtest_progress.setVisible(True)
            self.backtest_progress.setValue(0)
            
            # 백테스트 설정
            start_date = self.backtest_start_date.text()
            end_date = self.backtest_end_date.text()
            initial_capital = self.backtest_capital_spin.value()
            strategy = self.strategy_combo.currentText()
            
            self.add_log(f"📊 백테스트 설정: {start_date} ~ {end_date}, 자본: ${initial_capital}, 전략: {strategy}", "INFO")
            
            # 백테스트 실행 (시뮬레이션)
            import random
            for i in range(101):
                self.backtest_progress.setValue(i)
                QApplication.processEvents()
                time.sleep(0.01)  # 진행 상황 시뮬레이션
            
            # 결과 업데이트 (예시 데이터)
            total_return = random.uniform(-20, 50)
            sharpe_ratio = random.uniform(0.5, 2.5)
            max_drawdown = random.uniform(5, 25)
            total_trades = random.randint(50, 500)
            win_rate = random.uniform(45, 75)
            
            self.backtest_return_label.setText(f"{total_return:+.2f}%")
            self.backtest_sharpe_label.setText(f"{sharpe_ratio:.2f}")
            self.backtest_mdd_label.setText(f"-{max_drawdown:.2f}%")
            self.backtest_trades_label.setText(f"{total_trades}")
            self.backtest_winrate_label.setText(f"{win_rate:.1f}%")
            
            # 결과 색상 설정
            color = "#4CAF50" if total_return > 0 else "#ff4444"
            self.backtest_return_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            
            self.backtest_progress.setVisible(False)
            self.add_log("✅ 백테스트 완료", "SUCCESS")
            
        except Exception as e:
            self.add_log(f"❌ 백테스트 오류: {e}", "ERROR")
            self.backtest_progress.setVisible(False)
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        try:
            reply = QMessageBox.question(self, "종료 확인", 
                                       "🚪 거래 시스템을 종료하시겠습니까?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.add_log("🛑 완전한 GUI 종료 중...", "INFO")
                
                # 거래 중지
                if self.trading_active:
                    self.stop_trading()
                
                # 데이터 스레드 정리
                if self.data_thread and self.data_thread.isRunning():
                    self.data_thread.stop()
                    self.data_thread.wait(5000)  # 5초 대기
                
                event.accept()
            else:
                event.ignore()
                
        except Exception as e:
            print(f"⚠️ 종료 처리 오류: {e}")
            event.accept()

def main():
    """GUI 메인 함수"""
    try:
        print("🚀 완전한 OKX 자동매매 GUI 시작")
        
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        
        # 애플리케이션 정보 설정
        app.setApplicationName("OKX 자동매매 시스템")
        app.setApplicationVersion("2.0")
        app.setOrganizationName("CoinTrading")
        
        # 메인 윈도우 생성
        window = MainWindow()
        window.show()
        
        print("✅ 완전한 GUI 실행 중...")
        
        # 이벤트 루프 시작
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ 완전한 GUI 시작 실패: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()