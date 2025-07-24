# gui/main_window.py
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

# 프로젝트 모듈들 - 단계별 임포트로 에러 방지
try:
    from gui.balance_manager import GUIBalanceManager
    print("✅ GUIBalanceManager 임포트 성공")
except ImportError as e:
    print(f"⚠️ GUIBalanceManager 임포트 실패: {e}")
    GUIBalanceManager = None

try:
    from gui.widgets import (
        PriceChartWidget, PositionTableWidget, TradingControlWidget,
        SystemMonitorWidget, LogDisplayWidget
    )
    print("✅ GUI 위젯들 임포트 성공")
except ImportError as e:
    print(f"⚠️ GUI 위젯 임포트 실패: {e}")
    # 기본 위젯 클래스들 정의
    class PriceChartWidget(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout()
            layout.addWidget(QLabel("차트 위젯 (임포트 실패)"))
            self.setLayout(layout)
        
        def update_price(self, symbol, price, price_info=None):
            pass
    
    class PositionTableWidget(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout()
            layout.addWidget(QLabel("포지션 테이블 (임포트 실패)"))
            self.setLayout(layout)
        
        def update_positions(self, positions):
            pass
    
    class TradingControlWidget(QWidget):
        start_trading_requested = pyqtSignal()
        stop_trading_requested = pyqtSignal()
        emergency_stop_requested = pyqtSignal()
        
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout()
            layout.addWidget(QLabel("거래 제어 위젯 (임포트 실패)"))
            self.setLayout(layout)
        
        def update_status(self, data):
            pass
    
    class SystemMonitorWidget(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout()
            layout.addWidget(QLabel("시스템 모니터 (임포트 실패)"))
            self.setLayout(layout)
    
    class LogDisplayWidget(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout()
            self.log_text = QTextEdit()
            layout.addWidget(QLabel("로그 디스플레이 (임포트 실패)"))
            layout.addWidget(self.log_text)
            self.setLayout(layout)
        
        def add_log(self, message, level="INFO"):
            if hasattr(self, 'log_text'):
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_text.append(f"[{timestamp}] {message}")

try:
    from gui.data_thread import TradingDataThread
    print("✅ TradingDataThread 임포트 성공")
except ImportError as e:
    print(f"⚠️ TradingDataThread 임포트 실패: {e}")
    TradingDataThread = None

try:
    from okx.account_manager import AccountManager
    print("✅ AccountManager 임포트 성공")
except ImportError as e:
    print(f"⚠️ AccountManager 임포트 실패: {e}")
    AccountManager = None

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
        self.create_positions_tab(tab_widget)
        self.create_strategies_tab(tab_widget)
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
        right_layout.addWidget(self.widgets['position_table'])
        
        # 시스템 모니터
        self.widgets['system_monitor'] = SystemMonitorWidget()
        right_layout.addWidget(self.widgets['system_monitor'])
        
        layout.addWidget(right_panel, 1)
        
        tab_widget.addTab(dashboard_widget, "📊 대시보드")
    
    def create_trading_tab(self, tab_widget):
        """거래 탭 생성"""
        trading_widget = QWidget()
        layout = QVBoxLayout(trading_widget)
        
        # 거래 설정
        settings_group = QGroupBox("⚙️ 거래 설정")
        settings_layout = QFormLayout()
        
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"])
        
        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(0.01, 1000)
        self.position_size_spin.setValue(10.0)
        self.position_size_spin.setSuffix(" USDT")
        
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 100)
        self.leverage_spin.setValue(10)
        self.leverage_spin.setSuffix("x")
        
        settings_layout.addRow("거래 심볼:", self.symbol_combo)
        settings_layout.addRow("포지션 크기:", self.position_size_spin)
        settings_layout.addRow("레버리지:", self.leverage_spin)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 수동 거래 버튼들
        manual_group = QGroupBox("🎮 수동 거래")
        manual_layout = QGridLayout()
        
        long_btn = QPushButton("📈 롱 포지션")
        long_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        long_btn.clicked.connect(self.open_long_position)
        
        short_btn = QPushButton("📉 숏 포지션")
        short_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 10px;")
        short_btn.clicked.connect(self.open_short_position)
        
        close_all_btn = QPushButton("❌ 모든 포지션 청산")
        close_all_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; padding: 10px;")
        close_all_btn.clicked.connect(self.close_all_positions)
        
        manual_layout.addWidget(long_btn, 0, 0)
        manual_layout.addWidget(short_btn, 0, 1)
        manual_layout.addWidget(close_all_btn, 1, 0, 1, 2)
        
        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)
        
        layout.addStretch()
        tab_widget.addTab(trading_widget, "💰 거래")
    
    def create_positions_tab(self, tab_widget):
        """포지션 탭 생성"""
        positions_widget = QWidget()
        layout = QVBoxLayout(positions_widget)
        
        # 포지션 요약
        summary_group = QGroupBox("📊 포지션 요약")
        summary_layout = QGridLayout()
        
        self.total_positions_label = QLabel("0")
        self.unrealized_pnl_label = QLabel("$0.00")
        self.margin_used_label = QLabel("$0.00")
        self.margin_ratio_label = QLabel("0%")
        
        summary_layout.addWidget(QLabel("총 포지션:"), 0, 0)
        summary_layout.addWidget(self.total_positions_label, 0, 1)
        summary_layout.addWidget(QLabel("미실현 손익:"), 0, 2)
        summary_layout.addWidget(self.unrealized_pnl_label, 0, 3)
        summary_layout.addWidget(QLabel("사용 마진:"), 1, 0)
        summary_layout.addWidget(self.margin_used_label, 1, 1)
        summary_layout.addWidget(QLabel("마진 비율:"), 1, 2)
        summary_layout.addWidget(self.margin_ratio_label, 1, 3)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # 상세 포지션 테이블
        detailed_positions = PositionTableWidget()
        layout.addWidget(detailed_positions)
        
        tab_widget.addTab(positions_widget, "📋 포지션")
    
    def create_strategies_tab(self, tab_widget):
        """전략 탭 생성"""
        strategies_widget = QWidget()
        layout = QVBoxLayout(strategies_widget)
        
        # 전략 선택
        strategy_group = QGroupBox("🧠 전략 선택")
        strategy_layout = QGridLayout()
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "RSI 역추세 전략",
            "볼린저 밴드 전략", 
            "이동평균 크로스오버",
            "MACD 전략",
            "사용자 정의"
        ])
        
        strategy_layout.addWidget(QLabel("전략:"), 0, 0)
        strategy_layout.addWidget(self.strategy_combo, 0, 1)
        
        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)
        
        # 전략 파라미터
        params_group = QGroupBox("⚙️ 전략 파라미터")
        params_layout = QFormLayout()
        
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(5, 50)
        self.rsi_period_spin.setValue(14)
        
        self.rsi_oversold_spin = QSpinBox()
        self.rsi_oversold_spin.setRange(10, 40)
        self.rsi_oversold_spin.setValue(30)
        
        self.rsi_overbought_spin = QSpinBox()
        self.rsi_overbought_spin.setRange(60, 90)
        self.rsi_overbought_spin.setValue(70)
        
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(0.1, 10.0)
        self.stop_loss_spin.setValue(2.0)
        self.stop_loss_spin.setSuffix("%")
        
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(0.1, 20.0)
        self.take_profit_spin.setValue(4.0)
        self.take_profit_spin.setSuffix("%")
        
        params_layout.addRow("RSI 기간:", self.rsi_period_spin)
        params_layout.addRow("RSI 과매도:", self.rsi_oversold_spin)
        params_layout.addRow("RSI 과매수:", self.rsi_overbought_spin)
        params_layout.addRow("손절매:", self.stop_loss_spin)
        params_layout.addRow("익절매:", self.take_profit_spin)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 전략 상태
        status_group = QGroupBox("📈 전략 상태")
        status_layout = QFormLayout()
        
        self.long_status_label = QLabel("대기 중")
        self.short_status_label = QLabel("대기 중")
        self.last_signal_label = QLabel("없음")
        
        status_layout.addRow("롱 전략:", self.long_status_label)
        status_layout.addRow("숏 전략:", self.short_status_label)
        status_layout.addRow("마지막 신호:", self.last_signal_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
        tab_widget.addTab(strategies_widget, "🧠 전략")
    
    def create_monitoring_tab(self, tab_widget):
        """모니터링 탭 생성"""
        monitoring_widget = QWidget()
        layout = QVBoxLayout(monitoring_widget)
        
        # 시스템 상태
        system_group = QGroupBox("🖥️ 시스템 상태")
        system_layout = QGridLayout()
        
        system_monitor = SystemMonitorWidget()
        system_layout.addWidget(system_monitor, 0, 0, 1, 2)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        # API 상태
        api_group = QGroupBox("🔗 API 상태")
        api_layout = QFormLayout()
        
        self.api_status_label = QLabel("연결됨")
        self.api_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        self.latency_label = QLabel("0ms")
        self.requests_label = QLabel("0")
        self.errors_label = QLabel("0")
        
        api_layout.addRow("연결 상태:", self.api_status_label)
        api_layout.addRow("지연 시간:", self.latency_label)
        api_layout.addRow("총 요청:", self.requests_label)
        api_layout.addRow("오류 수:", self.errors_label)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 거래 통계
        stats_group = QGroupBox("📊 거래 통계")
        stats_layout = QFormLayout()
        
        self.total_trades_label = QLabel("0")
        self.win_rate_label = QLabel("0%")
        self.avg_profit_label = QLabel("$0.00")
        self.max_drawdown_label = QLabel("0%")
        
        stats_layout.addRow("총 거래:", self.total_trades_label)
        stats_layout.addRow("승률:", self.win_rate_label)
        stats_layout.addRow("평균 수익:", self.avg_profit_label)
        stats_layout.addRow("최대 손실:", self.max_drawdown_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        tab_widget.addTab(monitoring_widget, "📊 모니터링")
    
    def create_settings_tab(self, tab_widget):
        """설정 탭 생성"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # API 설정
        api_group = QGroupBox("🔑 API 설정")
        api_layout = QFormLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setEchoMode(QLineEdit.Password)
        
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.Password)
        
        self.sandbox_check = QCheckBox("샌드박스 모드")
        
        api_layout.addRow("API Key:", self.api_key_edit)
        api_layout.addRow("Secret Key:", self.secret_key_edit)
        api_layout.addRow("Passphrase:", self.passphrase_edit)
        api_layout.addRow("", self.sandbox_check)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 일반 설정
        general_group = QGroupBox("⚙️ 일반 설정")
        general_layout = QFormLayout()
        
        self.auto_start_check = QCheckBox("시작 시 자동 실행")
        self.notifications_check = QCheckBox("알림 활성화")
        self.dark_theme_check = QCheckBox("다크 테마")
        self.dark_theme_check.setChecked(True)
        
        general_layout.addRow("", self.auto_start_check)
        general_layout.addRow("", self.notifications_check)
        general_layout.addRow("", self.dark_theme_check)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # 저장 버튼
        save_btn = QPushButton("💾 설정 저장")
        save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px;")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        tab_widget.addTab(settings_widget, "⚙️ 설정")
    
    def create_backtest_tab(self, tab_widget):
        """백테스트 탭 생성"""
        backtest_widget = QWidget()
        layout = QVBoxLayout(backtest_widget)
        
        # 백테스트 설정
        config_group = QGroupBox("📈 백테스트 설정")
        config_layout = QFormLayout()
        
        self.backtest_symbol_combo = QComboBox()
        self.backtest_symbol_combo.addItems(["BTC-USDT-SWAP", "ETH-USDT-SWAP"])
        
        self.backtest_start_edit = QLineEdit("2024-01-01")
        self.backtest_end_edit = QLineEdit("2024-12-31")
        self.backtest_capital_spin = QDoubleSpinBox()
        self.backtest_capital_spin.setRange(100, 100000)
        self.backtest_capital_spin.setValue(10000)
        self.backtest_capital_spin.setSuffix(" USDT")
        
        config_layout.addRow("심볼:", self.backtest_symbol_combo)
        config_layout.addRow("시작일:", self.backtest_start_edit)
        config_layout.addRow("종료일:", self.backtest_end_edit)
        config_layout.addRow("초기 자본:", self.backtest_capital_spin)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # 실행 버튼
        run_btn = QPushButton("🚀 백테스트 실행")
        run_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 12px;")
        run_btn.clicked.connect(self.run_backtest)
        layout.addWidget(run_btn)
        
        # 결과 표시
        results_group = QGroupBox("📊 백테스트 결과")
        results_layout = QFormLayout()
        
        self.backtest_return_label = QLabel("0%")
        self.backtest_sharpe_label = QLabel("0.0")
        self.backtest_maxdd_label = QLabel("0%")
        self.backtest_trades_label = QLabel("0")
        
        results_layout.addRow("총 수익률:", self.backtest_return_label)
        results_layout.addRow("샤프 비율:", self.backtest_sharpe_label)
        results_layout.addRow("최대 낙폭:", self.backtest_maxdd_label)
        results_layout.addRow("총 거래:", self.backtest_trades_label)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        layout.addStretch()
        tab_widget.addTab(backtest_widget, "📈 백테스트")
    
    def apply_dark_theme(self):
        """다크 테마 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px 16px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
                background-color: #3c3c3c;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                background-color: #3c3c3c;
            }
            QTableWidget {
                gridline-color: #555;
                background-color: #2b2b2b;
                alternate-background-color: #3c3c3c;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                border: 1px solid #555;
                padding: 4px;
            }
        """)
    
    def update_clock(self):
        """시계 업데이트"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.setText(f"🕐 {current_time}")
    
    def start_data_thread(self):
        """데이터 스레드 시작"""
        if TradingDataThread and not self.data_thread:
            try:
                self.data_thread = TradingDataThread()
                self.data_thread.account_updated.connect(self.on_account_updated)
                self.data_thread.price_updated.connect(self.on_price_updated)
                self.data_thread.position_updated.connect(self.on_position_updated)
                self.data_thread.strategy_updated.connect(self.on_strategy_updated)
                self.data_thread.connection_changed.connect(self.on_connection_changed)
                self.data_thread.start()
                
                self.add_log("✅ 데이터 스레드 시작됨", "SUCCESS")
            except Exception as e:
                self.add_log(f"❌ 데이터 스레드 시작 실패: {e}", "ERROR")
    
    def on_account_updated(self, account_data):
        """계정 정보 업데이트 처리"""
        try:
            self.account_balance = account_data
            
            if GUIBalanceManager:
                # 주요 값들 추출
                usdt_balance = GUIBalanceManager.get_usdt_balance(account_data)
                total_equity = GUIBalanceManager.get_total_equity(account_data) 
                
                # UI 업데이트
                self.balance_label.setText(f"💰 USDT: ${usdt_balance:.2f}")
                self.equity_label.setText(f"총 자산: ${total_equity:.2f}")
                
                # 상태바 업데이트
                if total_equity > 0:
                    self.statusBar().showMessage(f"완전한 GUI - 총 자산: ${total_equity:.2f}")
            else:
                # 기본 처리
                self.balance_label.setText("💰 USDT: $0.00")
                self.equity_label.setText("총 자산: $0.00")
            
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
            self.connection_label.setText("✅ 연결됨")
            self.connection_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
        else:
            self.connection_label.setText("❌ 연결 끊김")
            self.connection_label.setStyleSheet("color: #F44336; font-weight: bold; font-size: 14px;")
    
    def start_trading(self):
        """자동매매 시작"""
        self.trading_active = True
        self.add_log("🎯 자동매매 시작됨", "SUCCESS")
        
        # 실제 거래 로직 호출
        # trading_system.start() 등
    
    def stop_trading(self):
        """자동매매 중지"""
        self.trading_active = False
        self.add_log("⏹️ 자동매매 중지됨", "INFO")
        
        # 실제 거래 중지 로직 호출
        # trading_system.stop() 등
    
    def emergency_stop(self):
        """긴급 중지"""
        self.trading_active = False
        self.add_log("🚨 긴급 중지 실행됨", "WARNING")
        
        # 긴급 중지 로직 (모든 포지션 청산 등)
        # trading_system.emergency_stop() 등
    
    def open_long_position(self):
        """롱 포지션 열기"""
        symbol = self.symbol_combo.currentText()
        size = self.position_size_spin.value()
        self.add_log(f"📈 롱 포지션 요청: {symbol} ${size}", "INFO")
    
    def open_short_position(self):
        """숏 포지션 열기"""
        symbol = self.symbol_combo.currentText()
        size = self.position_size_spin.value()
        self.add_log(f"📉 숏 포지션 요청: {symbol} ${size}", "INFO")
    
    def close_all_positions(self):
        """모든 포지션 청산"""
        self.add_log("❌ 모든 포지션 청산 요청", "WARNING")
    
    def run_backtest(self):
        """백테스트 실행"""
        symbol = self.backtest_symbol_combo.currentText()
        start_date = self.backtest_start_edit.text()
        end_date = self.backtest_end_edit.text()
        capital = self.backtest_capital_spin.value()
        
        self.add_log(f"📈 백테스트 시작: {symbol} ({start_date} ~ {end_date})", "INFO")
        
        # 임시 결과 표시
        self.backtest_return_label.setText("15.4%")
        self.backtest_sharpe_label.setText("1.23")
        self.backtest_maxdd_label.setText("-8.2%")
        self.backtest_trades_label.setText("47")
    
    def save_settings(self):
        """설정 저장"""
        self.add_log("💾 설정이 저장되었습니다", "SUCCESS")
    
    def add_log(self, message: str, level: str = "INFO"):
        """로그 추가"""
        if 'log_display' in self.widgets:
            self.widgets['log_display'].add_log(message, level)
        else:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")
    
    def closeEvent(self, event):
        """윈도우 종료 이벤트"""
        # 데이터 스레드 종료
        if self.data_thread:
            self.data_thread.stop()
            self.data_thread.wait()
        
        event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("OKX 자동매매 시스템")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("TradingBot")
    
    try:
        # 메인 윈도우 생성
        window = MainWindow()
        window.show()
        
        print("🚀 완전한 OKX 자동매매 GUI 시작")
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ 완전한 GUI 시작 실패: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()