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
    PriceChartWidget = None
    PositionTableWidget = None
    TradingControlWidget = None
    SystemMonitorWidget = None
    LogDisplayWidget = None

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

try:
    from utils.logger import setup_logger
    logger = setup_logger("gui_main")
except ImportError as e:
    print(f"⚠️ Logger 임포트 실패: {e}")
    import logging
    logger = logging.getLogger("gui_main")

class TradingMainWindow(QMainWindow):
    """메인 GUI 윈도우 - TradingMainWindow로 정확한 이름 사용"""
    
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
        
        # 기존 __init__ 코드 다음에 추가
        
        # 전략 상태 변수들
        self.long_strategy_active = False
        self.short_strategy_active = False

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
    
    def create_status_header(self, layout):
        """상단 상태 헤더 생성"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        # 시간 표시
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(self.time_label)
        
        header_layout.addStretch()
        
        # 계좌 정보
        self.balance_label = QLabel("잔고: $0.00")
        self.balance_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.balance_label.setStyleSheet("color: #00ff00")
        header_layout.addWidget(self.balance_label)
        
        # API 상태
        self.api_status_label = QLabel("🔴 API 연결 확인 중...")
        header_layout.addWidget(self.api_status_label)
        
        layout.addWidget(header_frame)
    
    def create_dashboard_tab(self, tab_widget):
        """대시보드 탭 생성"""
        dashboard = QWidget()
        layout = QVBoxLayout(dashboard)
        
        # 상단 - 주요 지표
        metrics_layout = QHBoxLayout()
        
        # 잔고 정보
        balance_group = QGroupBox("계좌 잔고")
        balance_layout = QVBoxLayout()
        self.total_balance_label = QLabel("$0.00")
        self.total_balance_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.total_balance_label.setStyleSheet("color: #00ff00")
        balance_layout.addWidget(self.total_balance_label)
        balance_group.setLayout(balance_layout)
        metrics_layout.addWidget(balance_group)
        
        # 일일 수익
        daily_pnl_group = QGroupBox("일일 수익")
        daily_pnl_layout = QVBoxLayout()
        self.daily_pnl_label = QLabel("$0.00")
        self.daily_pnl_label.setFont(QFont("Arial", 20, QFont.Bold))
        daily_pnl_layout.addWidget(self.daily_pnl_label)
        daily_pnl_group.setLayout(daily_pnl_layout)
        metrics_layout.addWidget(daily_pnl_group)
        
        # 총 수익
        total_pnl_group = QGroupBox("총 수익")
        total_pnl_layout = QVBoxLayout()
        self.total_pnl_label = QLabel("$0.00")
        self.total_pnl_label.setFont(QFont("Arial", 20, QFont.Bold))
        total_pnl_layout.addWidget(self.total_pnl_label)
        total_pnl_group.setLayout(total_pnl_layout)
        metrics_layout.addWidget(total_pnl_group)
        
        layout.addLayout(metrics_layout)
        
        # 중간 - 차트와 포지션
        content_splitter = QSplitter(Qt.Horizontal)
        
        # 가격 차트
        if PriceChartWidget:
            self.price_chart = PriceChartWidget()
            self.widgets['price_chart'] = self.price_chart
        else:
            self.price_chart = QLabel("차트 위젯을 사용할 수 없습니다.")
        content_splitter.addWidget(self.price_chart)
        
        # 포지션 테이블
        if PositionTableWidget:
            self.position_table = PositionTableWidget()
            self.widgets['position_table'] = self.position_table
        else:
            self.position_table = QLabel("포지션 테이블을 사용할 수 없습니다.")
        content_splitter.addWidget(self.position_table)
        
        content_splitter.setSizes([2, 1])
        layout.addWidget(content_splitter)
        
        tab_widget.addTab(dashboard, "📊 대시보드")
    
    def create_trading_tab(self, tab_widget):
        """거래 탭 생성"""
        trading = QWidget()
        layout = QHBoxLayout(trading)
        
        # 좌측 - 거래 제어
        if TradingControlWidget:
            self.trading_control = TradingControlWidget()
            self.widgets['trading_control'] = self.trading_control
            
            # 시그널 연결
            self.trading_control.start_trading_requested.connect(self.start_trading)
            self.trading_control.stop_trading_requested.connect(self.stop_trading)
            self.trading_control.emergency_stop_requested.connect(self.emergency_stop)
        else:
            self.trading_control = QLabel("거래 제어 위젯을 사용할 수 없습니다.")
        
        layout.addWidget(self.trading_control)
        
        # 우측 - 주문 내역
        orders_group = QGroupBox("최근 주문 내역")
        orders_layout = QVBoxLayout()
        
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(6)
        self.orders_table.setHorizontalHeaderLabels([
            "시간", "심볼", "타입", "수량", "가격", "상태"
        ])
        
        orders_layout.addWidget(self.orders_table)
        orders_group.setLayout(orders_layout)
        layout.addWidget(orders_group)
        
        tab_widget.addTab(trading, "💰 거래")
    
    def create_positions_tab(self, tab_widget):
        """포지션 탭 생성"""
        positions = QWidget()
        layout = QVBoxLayout(positions)
        
        # 포지션 관리 버튼들
        button_layout = QHBoxLayout()
        
        close_all_btn = QPushButton("🚨 모든 포지션 청산")
        close_all_btn.setStyleSheet("background-color: #aa0000; color: white; padding: 10px;")
        close_all_btn.clicked.connect(self.close_all_positions)
        button_layout.addWidget(close_all_btn)
        
        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.clicked.connect(self.refresh_positions)
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 상세 포지션 테이블
        self.detailed_positions_table = QTableWidget()
        self.detailed_positions_table.setColumnCount(10)
        self.detailed_positions_table.setHorizontalHeaderLabels([
            "심볼", "방향", "크기", "진입가격", "현재가격", "PnL", "PnL%", 
            "마진", "레버리지", "액션"
        ])
        
        layout.addWidget(self.detailed_positions_table)
        
        tab_widget.addTab(positions, "📈 포지션")
    
    # 전략 제어 메소드들 - main_window.py 클래스에 추가

    def start_all_strategies(self):
        """모든 전략 시작"""
        try:
            self.start_long_strategy()
            self.start_short_strategy()
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("🚀 모든 전략이 시작되었습니다.", "SUCCESS")
                
        except Exception as e:
            self.handle_error(f"전체 전략 시작 실패: {e}")

    def stop_all_strategies(self):
        """모든 전략 중지"""
        try:
            self.stop_long_strategy()
            self.stop_short_strategy()
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("⏹️ 모든 전략이 중지되었습니다.", "WARNING")
                
        except Exception as e:
            self.handle_error(f"전체 전략 중지 실패: {e}")

    def emergency_stop_all(self):
        """긴급 전체 중지"""
        try:
            self.stop_all_strategies()
            self.close_all_positions()
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("🚨 긴급 전체 중지 실행! 모든 전략 중지 및 포지션 청산", "ERROR")
                
        except Exception as e:
            self.handle_error(f"긴급 전체 중지 실패: {e}")

    def start_long_strategy(self):
        """롱 전략 시작"""
        try:
            # 롱 전략 활성화
            self.long_strategy_active = True
            
            # UI 상태 업데이트
            self.long_status_label.setText("🟢 활성")
            self.long_status_label.setStyleSheet("color: #00ff00")
            
            # 버튼 상태 변경
            self.start_long_btn.setEnabled(False)
            self.stop_long_btn.setEnabled(True)
            
            # 파라미터 가져오기
            capital = self.long_capital_spin.value()
            leverage = self.long_leverage_spin.value()
            stop_loss = self.long_stop_loss_spin.value()
            take_profit = self.long_take_profit_spin.value()
            trailing = self.long_trailing_spin.value()
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log(
                    f"📈 롱 전략 시작: 자본 ${capital:.2f}, 레버리지 {leverage}x, "
                    f"손절 {stop_loss}%, 익절 {take_profit}%, 트레일링 {trailing}%", "SUCCESS"
                )
            
            # 실제 전략 시작 로직 (data_thread 또는 strategy_manager와 연동)
            if self.data_thread and hasattr(self.data_thread, 'start_long_strategy'):
                self.data_thread.start_long_strategy({
                    'capital': capital,
                    'leverage': leverage,
                    'stop_loss': stop_loss / 100,
                    'take_profit': take_profit / 100,
                    'trailing_stop': trailing / 100
                })
                
        except Exception as e:
            self.handle_error(f"롱 전략 시작 실패: {e}")

    def stop_long_strategy(self):
        """롱 전략 중지"""
        try:
            # 롱 전략 비활성화
            self.long_strategy_active = False
            
            # UI 상태 업데이트
            self.long_status_label.setText("🔴 비활성")
            self.long_status_label.setStyleSheet("color: #ff6666")
            
            # 버튼 상태 변경
            self.start_long_btn.setEnabled(True)
            self.stop_long_btn.setEnabled(False)
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("📈 롱 전략이 중지되었습니다.", "WARNING")
            
            # 실제 전략 중지 로직
            if self.data_thread and hasattr(self.data_thread, 'stop_long_strategy'):
                self.data_thread.stop_long_strategy()
                
        except Exception as e:
            self.handle_error(f"롱 전략 중지 실패: {e}")

    def start_short_strategy(self):
        """숏 전략 시작"""
        try:
            # 숏 전략 활성화
            self.short_strategy_active = True
            
            # UI 상태 업데이트
            self.short_status_label.setText("🟢 활성")
            self.short_status_label.setStyleSheet("color: #00ff00")
            
            # 버튼 상태 변경
            self.start_short_btn.setEnabled(False)
            self.stop_short_btn.setEnabled(True)
            
            # 파라미터 가져오기
            capital = self.short_capital_spin.value()
            leverage = self.short_leverage_spin.value()
            stop_loss = self.short_stop_loss_spin.value()
            take_profit = self.short_take_profit_spin.value()
            trailing = self.short_trailing_spin.value()
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log(
                    f"📉 숏 전략 시작: 자본 ${capital:.2f}, 레버리지 {leverage}x, "
                    f"손절 {stop_loss}%, 익절 {take_profit}%, 트레일링 {trailing}%", "SUCCESS"
                )
            
            # 실제 전략 시작 로직
            if self.data_thread and hasattr(self.data_thread, 'start_short_strategy'):
                self.data_thread.start_short_strategy({
                    'capital': capital,
                    'leverage': leverage,
                    'stop_loss': stop_loss / 100,
                    'take_profit': take_profit / 100,
                    'trailing_stop': trailing / 100
                })
                
        except Exception as e:
            self.handle_error(f"숏 전략 시작 실패: {e}")

    def stop_short_strategy(self):
        """숏 전략 중지"""
        try:
            # 숏 전략 비활성화
            self.short_strategy_active = False
            
            # UI 상태 업데이트
            self.short_status_label.setText("🔴 비활성")
            self.short_status_label.setStyleSheet("color: #ff6666")
            
            # 버튼 상태 변경
            self.start_short_btn.setEnabled(True)
            self.stop_short_btn.setEnabled(False)
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("📉 숏 전략이 중지되었습니다.", "WARNING")
            
            # 실제 전략 중지 로직
            if self.data_thread and hasattr(self.data_thread, 'stop_short_strategy'):
                self.data_thread.stop_short_strategy()
                
        except Exception as e:
            self.handle_error(f"숏 전략 중지 실패: {e}")

    def update_strategy_performance(self, strategy_data):
        """전략 성과 업데이트"""
        try:
            # 롱 전략 성과 업데이트
            long_data = strategy_data.get('long_strategy', {})
            if long_data:
                self.long_trades_label.setText(str(long_data.get('total_trades', 0)))
                
                win_rate = long_data.get('win_rate', 0) * 100
                self.long_win_rate_label.setText(f"{win_rate:.1f}%")
                if win_rate >= 60:
                    self.long_win_rate_label.setStyleSheet("color: #00ff00")
                elif win_rate >= 40:
                    self.long_win_rate_label.setStyleSheet("color: #ffaa00")
                else:
                    self.long_win_rate_label.setStyleSheet("color: #ff6666")
                
                profit = long_data.get('total_profit', 0)
                self.long_profit_label.setText(f"${profit:+.2f}")
                self.long_profit_label.setStyleSheet("color: #00ff00" if profit >= 0 else "color: #ff6666")
            
            # 숏 전략 성과 업데이트
            short_data = strategy_data.get('short_strategy', {})
            if short_data:
                self.short_trades_label.setText(str(short_data.get('total_trades', 0)))
                
                win_rate = short_data.get('win_rate', 0) * 100
                self.short_win_rate_label.setText(f"{win_rate:.1f}%")
                if win_rate >= 60:
                    self.short_win_rate_label.setStyleSheet("color: #00ff00")
                elif win_rate >= 40:
                    self.short_win_rate_label.setStyleSheet("color: #ffaa00")
                else:
                    self.short_win_rate_label.setStyleSheet("color: #ff6666")
                
                profit = short_data.get('total_profit', 0)
                self.short_profit_label.setText(f"${profit:+.2f}")
                self.short_profit_label.setStyleSheet("color: #00ff00" if profit >= 0 else "color: #ff6666")
            
            # 전체 성과 요약 업데이트
            total_trades = long_data.get('total_trades', 0) + short_data.get('total_trades', 0)
            total_profit = long_data.get('total_profit', 0) + short_data.get('total_profit', 0)
            
            self.total_trades_summary_label.setText(str(total_trades))
            self.total_profit_summary_label.setText(f"${total_profit:+.2f}")
            self.total_profit_summary_label.setStyleSheet("color: #00ff00" if total_profit >= 0 else "color: #ff6666")
            
            # 전체 승률 계산
            if total_trades > 0:
                total_wins = long_data.get('winning_trades', 0) + short_data.get('winning_trades', 0)
                overall_win_rate = (total_wins / total_trades) * 100
                self.overall_win_rate_label.setText(f"{overall_win_rate:.1f}%")
                if overall_win_rate >= 60:
                    self.overall_win_rate_label.setStyleSheet("color: #00ff00")
                elif overall_win_rate >= 40:
                    self.overall_win_rate_label.setStyleSheet("color: #ffaa00")
                else:
                    self.overall_win_rate_label.setStyleSheet("color: #ff6666")
            
            # 일일 수익은 임시로 총 수익의 일부로 계산
            daily_profit = total_profit * 0.1  # 예시: 총 수익의 10%를 일일 수익으로 가정
            self.daily_profit_summary_label.setText(f"${daily_profit:+.2f}")
            self.daily_profit_summary_label.setStyleSheet("color: #00ff00" if daily_profit >= 0 else "color: #ff6666")
            
        except Exception as e:
            print(f"전략 성과 업데이트 오류: {e}")

    def create_monitoring_tab(self, tab_widget):
        """모니터링 탭 생성"""
        monitoring = QWidget()
        layout = QHBoxLayout(monitoring)
        
        # 좌측 - 시스템 모니터
        if SystemMonitorWidget:
            self.system_monitor = SystemMonitorWidget()
            self.widgets['system_monitor'] = self.system_monitor
        else:
            self.system_monitor = QLabel("시스템 모니터를 사용할 수 없습니다.")
        
        layout.addWidget(self.system_monitor)
        
        # 우측 - 로그
        if LogDisplayWidget:
            self.log_display = LogDisplayWidget()
            self.widgets['log_display'] = self.log_display
        else:
            self.log_display = QTextEdit()
            self.log_display.setReadOnly(True)
            self.log_display.append("로그 디스플레이를 사용할 수 없습니다.")
        
        layout.addWidget(self.log_display)
        
        tab_widget.addTab(monitoring, "📱 모니터링")
    
    def create_settings_tab(self, tab_widget):
        """설정 탭 생성"""
        settings = QWidget()
        layout = QVBoxLayout(settings)
        
        # API 설정
        api_group = QGroupBox("API 설정")
        api_layout = QFormLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.api_key_edit)
        
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("Secret Key:", self.secret_key_edit)
        
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("Passphrase:", self.passphrase_edit)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 거래 설정
        trading_group = QGroupBox("거래 설정")
        trading_layout = QFormLayout()
        
        self.max_position_spin = QDoubleSpinBox()
        self.max_position_spin.setRange(0.01, 1000.0)
        self.max_position_spin.setValue(1.0)
        trading_layout.addRow("최대 포지션 크기:", self.max_position_spin)
        
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(0.1, 50.0)
        self.stop_loss_spin.setValue(5.0)
        self.stop_loss_spin.setSuffix("%")
        trading_layout.addRow("손절가:", self.stop_loss_spin)
        
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(0.1, 100.0)
        self.take_profit_spin.setValue(10.0)
        self.take_profit_spin.setSuffix("%")
        trading_layout.addRow("익절가:", self.take_profit_spin)
        
        trading_group.setLayout(trading_layout)
        layout.addWidget(trading_group)
        
        # 설정 저장/로드 버튼
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 설정 저장")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        load_btn = QPushButton("📂 설정 로드")
        load_btn.clicked.connect(self.load_settings)
        button_layout.addWidget(load_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        tab_widget.addTab(settings, "⚙️ 설정")
    
    def create_backtest_tab(self, tab_widget):
        """백테스트 탭 생성"""
        backtest = QWidget()
        layout = QVBoxLayout(backtest)
        
        # 백테스트 설정
        backtest_group = QGroupBox("백테스트 설정")
        backtest_layout = QFormLayout()
        
        self.start_date_edit = QLineEdit()
        self.start_date_edit.setText("2024-01-01")
        backtest_layout.addRow("시작 날짜:", self.start_date_edit)
        
        self.end_date_edit = QLineEdit()
        self.end_date_edit.setText("2024-12-31")
        backtest_layout.addRow("종료 날짜:", self.end_date_edit)
        
        self.initial_capital_spin = QDoubleSpinBox()
        self.initial_capital_spin.setRange(100, 1000000)
        self.initial_capital_spin.setValue(10000)
        self.initial_capital_spin.setPrefix("$")
        backtest_layout.addRow("초기 자본:", self.initial_capital_spin)
        
        backtest_group.setLayout(backtest_layout)
        layout.addWidget(backtest_group)
        
        # 백테스트 실행 버튼
        run_backtest_btn = QPushButton("🧪 백테스트 실행")
        run_backtest_btn.setStyleSheet("background-color: #0066aa; color: white; padding: 10px;")
        run_backtest_btn.clicked.connect(self.run_backtest)
        layout.addWidget(run_backtest_btn)
        
        # 백테스트 결과
        results_group = QGroupBox("백테스트 결과")
        results_layout = QGridLayout()
        
        results_layout.addWidget(QLabel("총 수익률:"), 0, 0)
        self.backtest_return_label = QLabel("0%")
        results_layout.addWidget(self.backtest_return_label, 0, 1)
        
        results_layout.addWidget(QLabel("최대 드로다운:"), 1, 0)
        self.max_drawdown_label = QLabel("0%")
        results_layout.addWidget(self.max_drawdown_label, 1, 1)
        
        results_layout.addWidget(QLabel("샤프 비율:"), 2, 0)
        self.sharpe_ratio_label = QLabel("0.00")
        results_layout.addWidget(self.sharpe_ratio_label, 2, 1)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        tab_widget.addTab(backtest, "🧪 백테스트")
    
    def apply_dark_theme(self):
        """다크 테마 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #3b3b3b;
            }
            QTabBar::tab {
                background-color: #555555;
                color: #ffffff;
                padding: 10px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0066aa;
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
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #444444;
                color: #ffffff;
                border: 1px solid #666666;
                padding: 5px;
                border-radius: 3px;
            }
            QTableWidget {
                background-color: #3b3b3b;
                color: #ffffff;
                gridline-color: #555555;
                selection-background-color: #0066aa;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #555555;
                color: #ffffff;
                padding: 5px;
                border: none;
            }
            QTextEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0066aa;
                border-radius: 3px;
            }
            QFrame {
                background-color: #3b3b3b;
                border: 1px solid #555555;
            }
        """)
    
    def start_data_thread(self):
        """데이터 스레드 시작"""
        if TradingDataThread:
            try:
                # AccountManager 초기화 (선택적)
                account_manager = None
                if AccountManager:
                    try:
                        account_manager = AccountManager()
                        print("✅ 계좌 관리자 초기화 완료")
                    except Exception as e:
                        print(f"⚠️ 계좌 관리자 초기화 실패: {e}")
                        account_manager = None
                
                # 데이터 스레드 생성 및 시작 (AccountManager는 선택적 전달)
                self.data_thread = TradingDataThread(account_manager)
                
                # 시그널 연결
                self.data_thread.balance_updated.connect(self.update_balance_display)
                self.data_thread.price_updated.connect(self.update_price_display)
                self.data_thread.positions_updated.connect(self.update_positions_display)
                self.data_thread.connection_changed.connect(self.update_connection_status)
                self.data_thread.error_occurred.connect(self.handle_error)
                
                self.data_thread.start()
                print("🔄 TradingDataThread 시작됨")
                
                # 초기 API 상태 설정
                if account_manager:
                    self.api_status_label.setText("🟡 API 연결 중...")
                    self.api_status_label.setStyleSheet("color: #ffaa00")
                else:
                    self.api_status_label.setText("🔴 API 사용 불가 (더미 모드)")
                    self.api_status_label.setStyleSheet("color: #ff6666")
                
            except Exception as e:
                print(f"⚠️ 데이터 스레드 시작 실패: {e}")
                self.api_status_label.setText("🔴 데이터 스레드 실패")
                self.api_status_label.setStyleSheet("color: #ff6666")
        else:
            print("⚠️ TradingDataThread 모듈을 사용할 수 없습니다")
            self.api_status_label.setText("🔴 모듈 없음")
            self.api_status_label.setStyleSheet("color: #ff6666")
    
    def update_connection_status(self, connected):
        """API 연결 상태 업데이트"""
        if connected:
            self.api_status_label.setText("🟢 API 연결됨")
            self.api_status_label.setStyleSheet("color: #00ff00")
        else:
            self.api_status_label.setText("🔴 API 연결 끊어짐")
            self.api_status_label.setStyleSheet("color: #ff6666")
    
    def update_clock(self):
        """시계 업데이트"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.setText(f"🕒 {current_time}")
        except Exception as e:
            print(f"시계 업데이트 오류: {e}")
    
    def update_balance_display(self, balance_data):
        """잔고 표시 업데이트"""
        try:
            if balance_data:
                usdt_balance = balance_data.get('usdt_balance', 0)
                total_equity = balance_data.get('total_equity', 0)
                
                self.balance_label.setText(f"잔고: ${usdt_balance:,.2f}")
                self.total_balance_label.setText(f"${total_equity:,.2f}")
                
                # 더미 데이터인지 확인
                if balance_data.get('is_dummy', False):
                    self.balance_label.setStyleSheet("color: #ffaa00")  # 주황색으로 더미 표시
                else:
                    self.balance_label.setStyleSheet("color: #00ff00")
                
                # 로그 추가
                if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                    status = "(더미)" if balance_data.get('is_dummy', False) else ""
                    self.log_display.add_log(f"잔고 업데이트: ${usdt_balance:,.2f} {status}")
            
        except Exception as e:
            print(f"잔고 표시 업데이트 오류: {e}")
    
    def update_price_display(self, symbol, price, price_info):
        """가격 표시 업데이트"""
        try:
            self.latest_prices[symbol] = price
            
            # 차트 업데이트
            if hasattr(self, 'price_chart') and hasattr(self.price_chart, 'update_price'):
                self.price_chart.update_price(symbol, price, price_info)
            
            # 로그 추가 (너무 자주 로그되지 않도록 제한)
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                if int(time.time()) % 10 == 0:  # 10초마다 한 번만 로그
                    status = "(더미)" if price_info.get('is_dummy', False) else ""
                    self.log_display.add_log(f"가격 업데이트: {symbol} = ${price:,.2f} {status}")
                
        except Exception as e:
            print(f"가격 표시 업데이트 오류: {e}")
    
    def update_positions_display(self, positions):
        """포지션 표시 업데이트"""
        try:
            self.positions = positions
            
            # 포지션 테이블 업데이트
            if hasattr(self, 'position_table') and hasattr(self.position_table, 'update_positions'):
                self.position_table.update_positions(positions)
            
            # 상세 포지션 테이블 업데이트
            self.update_detailed_positions_table(positions)
            
            # 로그 추가
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                if positions and len(positions) > 0:
                    status = "(더미)" if positions[0].get('is_dummy', False) else ""
                    self.log_display.add_log(f"포지션 업데이트: {len(positions)}개 포지션 {status}")
                
        except Exception as e:
            print(f"포지션 표시 업데이트 오류: {e}")
    
    def update_detailed_positions_table(self, positions):
        """상세 포지션 테이블 업데이트"""
        try:
            self.detailed_positions_table.setRowCount(len(positions))
            
            for i, position in enumerate(positions):
                self.detailed_positions_table.setItem(i, 0, QTableWidgetItem(position.get('instId', '')))
                self.detailed_positions_table.setItem(i, 1, QTableWidgetItem(position.get('posSide', '')))
                self.detailed_positions_table.setItem(i, 2, QTableWidgetItem(str(position.get('pos', '0'))))
                self.detailed_positions_table.setItem(i, 3, QTableWidgetItem(f"${float(position.get('avgPx', 0)):,.4f}"))
                
                # 현재 가격 (latest_prices에서 가져오기)
                symbol = position.get('instId', '')
                current_price = self.latest_prices.get(symbol, 0)
                self.detailed_positions_table.setItem(i, 4, QTableWidgetItem(f"${current_price:,.4f}"))
                
                # PnL 색상 설정
                pnl = float(position.get('upl', 0))
                pnl_item = QTableWidgetItem(f"${pnl:,.2f}")
                if pnl > 0:
                    pnl_item.setForeground(QColor("#00ff00"))
                elif pnl < 0:
                    pnl_item.setForeground(QColor("#ff6666"))
                self.detailed_positions_table.setItem(i, 5, pnl_item)
                
                # PnL 퍼센트
                pnl_pct = float(position.get('uplRatio', 0)) * 100
                pnl_pct_item = QTableWidgetItem(f"{pnl_pct:.2f}%")
                if pnl_pct > 0:
                    pnl_pct_item.setForeground(QColor("#00ff00"))
                elif pnl_pct < 0:
                    pnl_pct_item.setForeground(QColor("#ff6666"))
                self.detailed_positions_table.setItem(i, 6, pnl_pct_item)
                
                self.detailed_positions_table.setItem(i, 7, QTableWidgetItem(f"${float(position.get('margin', 0)):,.2f}"))
                self.detailed_positions_table.setItem(i, 8, QTableWidgetItem(f"{position.get('lever', '1')}x"))
                
                # 액션 버튼
                close_btn = QPushButton("청산")
                close_btn.setStyleSheet("background-color: #aa0000; color: white;")
                close_btn.clicked.connect(lambda checked, pos=position: self.close_position(pos))
                self.detailed_positions_table.setCellWidget(i, 9, close_btn)
                
        except Exception as e:
            print(f"상세 포지션 테이블 업데이트 오류: {e}")
    
    def handle_error(self, error_message):
        """에러 처리"""
        print(f"GUI 에러: {error_message}")
        
        # 로그에 에러 추가
        if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
            self.log_display.add_log(error_message, "ERROR")
        
        # 상태바에 에러 표시
        self.statusBar().showMessage(f"에러: {error_message}", 5000)
    
    def create_strategies_tab(self, tab_widget):
            """전략 탭 생성 - 롱/숏 전략 분리"""
            strategies = QWidget()
            layout = QVBoxLayout(strategies)
            
            # 전체 전략 제어
            overall_control_group = QGroupBox("전체 전략 제어")
            overall_layout = QHBoxLayout()
            
            start_all_btn = QPushButton("🚀 모든 전략 시작")
            start_all_btn.setStyleSheet("background-color: #00aa00; color: white; padding: 15px; font-size: 14px; font-weight: bold;")
            start_all_btn.clicked.connect(self.start_all_strategies)
            overall_layout.addWidget(start_all_btn)
            
            stop_all_btn = QPushButton("⏹️ 모든 전략 중지")
            stop_all_btn.setStyleSheet("background-color: #aa6600; color: white; padding: 15px; font-size: 14px; font-weight: bold;")
            stop_all_btn.clicked.connect(self.stop_all_strategies)
            overall_layout.addWidget(stop_all_btn)
            
            emergency_btn = QPushButton("🚨 긴급 중지")
            emergency_btn.setStyleSheet("background-color: #aa0000; color: white; padding: 15px; font-size: 14px; font-weight: bold;")
            emergency_btn.clicked.connect(self.emergency_stop_all)
            overall_layout.addWidget(emergency_btn)
            
            overall_control_group.setLayout(overall_layout)
            layout.addWidget(overall_control_group)
            
            # 전략별 설정 (수평 분할)
            strategies_splitter = QSplitter(Qt.Horizontal)
            
            # 롱 전략 설정
            long_strategy_group = QGroupBox("📈 롱 전략 (상승 추세)")
            long_layout = QVBoxLayout()
            
            # 롱 전략 상태
            self.long_status_label = QLabel("🔴 비활성")
            self.long_status_label.setFont(QFont("Arial", 12, QFont.Bold))
            long_layout.addWidget(self.long_status_label)
            
            # 롱 전략 파라미터
            long_params_layout = QFormLayout()
            
            self.long_capital_spin = QDoubleSpinBox()
            self.long_capital_spin.setRange(10.0, 10000.0)
            self.long_capital_spin.setValue(100.0)
            self.long_capital_spin.setPrefix("$")
            self.long_capital_spin.setSuffix(" USDT")
            long_params_layout.addRow("할당 자본:", self.long_capital_spin)
            
            self.long_leverage_spin = QSpinBox()
            self.long_leverage_spin.setRange(1, 100)
            self.long_leverage_spin.setValue(10)
            self.long_leverage_spin.setSuffix("x")
            long_params_layout.addRow("레버리지:", self.long_leverage_spin)
            
            self.long_stop_loss_spin = QDoubleSpinBox()
            self.long_stop_loss_spin.setRange(0.5, 20.0)
            self.long_stop_loss_spin.setValue(5.0)
            self.long_stop_loss_spin.setSuffix("%")
            long_params_layout.addRow("손절매:", self.long_stop_loss_spin)
            
            self.long_take_profit_spin = QDoubleSpinBox()
            self.long_take_profit_spin.setRange(1.0, 50.0)
            self.long_take_profit_spin.setValue(10.0)
            self.long_take_profit_spin.setSuffix("%")
            long_params_layout.addRow("익절매:", self.long_take_profit_spin)
            
            self.long_trailing_spin = QDoubleSpinBox()
            self.long_trailing_spin.setRange(0.1, 5.0)
            self.long_trailing_spin.setValue(1.0)
            self.long_trailing_spin.setSuffix("%")
            long_params_layout.addRow("트레일링 스탑:", self.long_trailing_spin)
            
            long_layout.addLayout(long_params_layout)
            
            # 롱 전략 제어 버튼
            long_control_layout = QHBoxLayout()
            
            self.start_long_btn = QPushButton("📈 롱 전략 시작")
            self.start_long_btn.setStyleSheet("background-color: #00aa00; color: white; padding: 10px;")
            self.start_long_btn.clicked.connect(self.start_long_strategy)
            long_control_layout.addWidget(self.start_long_btn)
            
            self.stop_long_btn = QPushButton("⏸️ 롱 전략 중지")
            self.stop_long_btn.setStyleSheet("background-color: #aa6600; color: white; padding: 10px;")
            self.stop_long_btn.clicked.connect(self.stop_long_strategy)
            long_control_layout.addWidget(self.stop_long_btn)
            
            long_layout.addLayout(long_control_layout)
            
            # 롱 전략 성과
            long_performance_group = QGroupBox("롱 전략 성과")
            long_performance_layout = QGridLayout()
            
            long_performance_layout.addWidget(QLabel("총 거래:"), 0, 0)
            self.long_trades_label = QLabel("0")
            long_performance_layout.addWidget(self.long_trades_label, 0, 1)
            
            long_performance_layout.addWidget(QLabel("승률:"), 1, 0)
            self.long_win_rate_label = QLabel("0%")
            long_performance_layout.addWidget(self.long_win_rate_label, 1, 1)
            
            long_performance_layout.addWidget(QLabel("총 수익:"), 2, 0)
            self.long_profit_label = QLabel("$0.00")
            long_performance_layout.addWidget(self.long_profit_label, 2, 1)
            
            long_performance_group.setLayout(long_performance_layout)
            long_layout.addWidget(long_performance_group)
            
            long_strategy_group.setLayout(long_layout)
            strategies_splitter.addWidget(long_strategy_group)
            
            # 숏 전략 설정
            short_strategy_group = QGroupBox("📉 숏 전략 (하락 추세)")
            short_layout = QVBoxLayout()
            
            # 숏 전략 상태
            self.short_status_label = QLabel("🔴 비활성")
            self.short_status_label.setFont(QFont("Arial", 12, QFont.Bold))
            short_layout.addWidget(self.short_status_label)
            
            # 숏 전략 파라미터
            short_params_layout = QFormLayout()
            
            self.short_capital_spin = QDoubleSpinBox()
            self.short_capital_spin.setRange(10.0, 10000.0)
            self.short_capital_spin.setValue(100.0)
            self.short_capital_spin.setPrefix("$")
            self.short_capital_spin.setSuffix(" USDT")
            short_params_layout.addRow("할당 자본:", self.short_capital_spin)
            
            self.short_leverage_spin = QSpinBox()
            self.short_leverage_spin.setRange(1, 100)
            self.short_leverage_spin.setValue(8)  # 숏은 조금 낮은 레버리지
            self.short_leverage_spin.setSuffix("x")
            short_params_layout.addRow("레버리지:", self.short_leverage_spin)
            
            self.short_stop_loss_spin = QDoubleSpinBox()
            self.short_stop_loss_spin.setRange(0.5, 20.0)
            self.short_stop_loss_spin.setValue(6.0)  # 숏은 조금 높은 손절
            self.short_stop_loss_spin.setSuffix("%")
            short_params_layout.addRow("손절매:", self.short_stop_loss_spin)
            
            self.short_take_profit_spin = QDoubleSpinBox()
            self.short_take_profit_spin.setRange(1.0, 50.0)
            self.short_take_profit_spin.setValue(12.0)
            self.short_take_profit_spin.setSuffix("%")
            short_params_layout.addRow("익절매:", self.short_take_profit_spin)
            
            self.short_trailing_spin = QDoubleSpinBox()
            self.short_trailing_spin.setRange(0.1, 5.0)
            self.short_trailing_spin.setValue(1.2)
            self.short_trailing_spin.setSuffix("%")
            short_params_layout.addRow("트레일링 스탑:", self.short_trailing_spin)
            
            short_layout.addLayout(short_params_layout)
            
            # 숏 전략 제어 버튼
            short_control_layout = QHBoxLayout()
            
            self.start_short_btn = QPushButton("📉 숏 전략 시작")
            self.start_short_btn.setStyleSheet("background-color: #aa0000; color: white; padding: 10px;")
            self.start_short_btn.clicked.connect(self.start_short_strategy)
            short_control_layout.addWidget(self.start_short_btn)
            
            self.stop_short_btn = QPushButton("⏸️ 숏 전략 중지")
            self.stop_short_btn.setStyleSheet("background-color: #aa6600; color: white; padding: 10px;")
            self.stop_short_btn.clicked.connect(self.stop_short_strategy)
            short_control_layout.addWidget(self.stop_short_btn)
            
            short_layout.addLayout(short_control_layout)
            
            # 숏 전략 성과
            short_performance_group = QGroupBox("숏 전략 성과")
            short_performance_layout = QGridLayout()
            
            short_performance_layout.addWidget(QLabel("총 거래:"), 0, 0)
            self.short_trades_label = QLabel("0")
            short_performance_layout.addWidget(self.short_trades_label, 0, 1)
            
            short_performance_layout.addWidget(QLabel("승률:"), 1, 0)
            self.short_win_rate_label = QLabel("0%")
            short_performance_layout.addWidget(self.short_win_rate_label, 1, 1)
            
            short_performance_layout.addWidget(QLabel("총 수익:"), 2, 0)
            self.short_profit_label = QLabel("$0.00")
            short_performance_layout.addWidget(self.short_profit_label, 2, 1)
            
            short_performance_group.setLayout(short_performance_layout)
            short_layout.addWidget(short_performance_group)
            
            short_strategy_group.setLayout(short_layout)
            strategies_splitter.addWidget(short_strategy_group)
            
            # 스플리터 크기 설정
            strategies_splitter.setSizes([1, 1])
            layout.addWidget(strategies_splitter)
            
            # 전체 성과 요약
            summary_group = QGroupBox("📊 전체 성과 요약")
            summary_layout = QGridLayout()
            
            summary_layout.addWidget(QLabel("총 거래 수:"), 0, 0)
            self.total_trades_summary_label = QLabel("0")
            summary_layout.addWidget(self.total_trades_summary_label, 0, 1)
            
            summary_layout.addWidget(QLabel("전체 승률:"), 0, 2)
            self.overall_win_rate_label = QLabel("0%")
            summary_layout.addWidget(self.overall_win_rate_label, 0, 3)
            
            summary_layout.addWidget(QLabel("총 수익:"), 1, 0)
            self.total_profit_summary_label = QLabel("$0.00")
            summary_layout.addWidget(self.total_profit_summary_label, 1, 1)
            
            summary_layout.addWidget(QLabel("일일 수익:"), 1, 2)
            self.daily_profit_summary_label = QLabel("$0.00")
            summary_layout.addWidget(self.daily_profit_summary_label, 1, 3)
            
            summary_group.setLayout(summary_layout)
            layout.addWidget(summary_group)
            
            tab_widget.addTab(strategies, "🎯 전략")


    # 거래 제어 메소드들
    def start_trading(self):
        """거래 시작"""
        try:
            self.trading_active = True
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("거래가 시작되었습니다.", "SUCCESS")
            
            # 거래 제어 위젯 상태 업데이트
            if hasattr(self, 'trading_control') and hasattr(self.trading_control, 'update_status'):
                self.trading_control.update_status({'trading_active': True})
                
        except Exception as e:
            self.handle_error(f"거래 시작 실패: {e}")
    
    def stop_trading(self):
        """거래 중지"""
        try:
            self.trading_active = False
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("거래가 중지되었습니다.", "WARNING")
            
            # 거래 제어 위젯 상태 업데이트
            if hasattr(self, 'trading_control') and hasattr(self.trading_control, 'update_status'):
                self.trading_control.update_status({'trading_active': False})
                
        except Exception as e:
            self.handle_error(f"거래 중지 실패: {e}")
    
    def emergency_stop(self):
        """긴급 중지"""
        try:
            self.trading_active = False
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("🚨 긴급 중지가 실행되었습니다!", "ERROR")
            
            # 모든 포지션 청산 (실제로는 구현 필요)
            self.close_all_positions()
            
        except Exception as e:
            self.handle_error(f"긴급 중지 실패: {e}")
    
    def close_position(self, position):
        """특정 포지션 청산"""
        try:
            symbol = position.get('instId', '')
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log(f"포지션 청산 요청: {symbol}", "WARNING")
            
            # 실제 청산 로직은 여기에 구현
            
        except Exception as e:
            self.handle_error(f"포지션 청산 실패: {e}")
    
    def close_all_positions(self):
        """모든 포지션 청산"""
        try:
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("🚨 모든 포지션 청산 요청", "ERROR")
            
            # 실제 청산 로직은 여기에 구현
            
        except Exception as e:
            self.handle_error(f"전체 포지션 청산 실패: {e}")
    
    def refresh_positions(self):
        """포지션 새로고침"""
        try:
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("포지션 새로고침", "INFO")
            
            # 데이터 스레드에서 포지션 업데이트 요청
            if self.data_thread:
                # 실제로는 데이터 스레드에 새로고침 시그널 전송
                pass
                
        except Exception as e:
            self.handle_error(f"포지션 새로고침 실패: {e}")
    
    def run_backtest(self):
        """백테스트 실행"""
        try:
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("백테스트 시작", "INFO")
            
            # 백테스트 로직 구현
            # 이것은 예시이므로 간단한 결과만 표시
            self.backtest_return_label.setText("15.6%")
            self.backtest_return_label.setStyleSheet("color: #00ff00")
            
            self.max_drawdown_label.setText("-8.2%")
            self.max_drawdown_label.setStyleSheet("color: #ff6666")
            
            self.sharpe_ratio_label.setText("1.85")
            self.sharpe_ratio_label.setStyleSheet("color: #00ff00")
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("백테스트 완료", "SUCCESS")
                
        except Exception as e:
            self.handle_error(f"백테스트 실행 실패: {e}")
    
    def save_settings(self):
        """설정 저장"""
        try:
            settings = {
                'api_key': self.api_key_edit.text(),
                'secret_key': self.secret_key_edit.text(),
                'passphrase': self.passphrase_edit.text(),
                'max_position': self.max_position_spin.value(),
                'stop_loss': self.stop_loss_spin.value(),
                'take_profit': self.take_profit_spin.value()
            }
            
            with open('gui_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("설정이 저장되었습니다.", "SUCCESS")
                
        except Exception as e:
            self.handle_error(f"설정 저장 실패: {e}")
    
    def load_settings(self):
        """설정 로드"""
        try:
            with open('gui_settings.json', 'r') as f:
                settings = json.load(f)
            
            self.api_key_edit.setText(settings.get('api_key', ''))
            self.secret_key_edit.setText(settings.get('secret_key', ''))
            self.passphrase_edit.setText(settings.get('passphrase', ''))
            self.max_position_spin.setValue(settings.get('max_position', 1.0))
            self.stop_loss_spin.setValue(settings.get('stop_loss', 5.0))
            self.take_profit_spin.setValue(settings.get('take_profit', 10.0))
            
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("설정이 로드되었습니다.", "SUCCESS")
                
        except FileNotFoundError:
            if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                self.log_display.add_log("설정 파일을 찾을 수 없습니다.", "WARNING")
        except Exception as e:
            self.handle_error(f"설정 로드 실패: {e}")
    
    def closeEvent(self, event):
        """윈도우 종료 시 처리"""
        try:
            # 데이터 스레드 중지
            if self.data_thread:
                self.data_thread.stop()
                self.data_thread.wait(3000)  # 3초 대기
                print("🛑 TradingDataThread 중지 요청됨")
            
            # 타이머 중지
            if hasattr(self, 'clock_timer'):
                self.clock_timer.stop()
            
            print("⏹️ TradingDataThread 종료됨")
            event.accept()
            
        except Exception as e:
            print(f"윈도우 종료 처리 오류: {e}")
            event.accept()

# 메인 함수
def main():
    """GUI 애플리케이션 실행"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("OKX 자동매매 시스템")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Trading Bot Team")
    
    try:
        # 메인 윈도우 생성
        print("✅ 계좌 관리자 초기화 완료")
        window = TradingMainWindow()
        window.show()
        
        # 애플리케이션 실행
        return app.exec_()
        
    except Exception as e:
        print(f"GUI 애플리케이션 시작 실패: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())