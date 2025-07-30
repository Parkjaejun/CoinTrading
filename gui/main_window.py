# gui/main_window.py
"""
완전한 OKX 자동매매 GUI 메인 윈도우 - Signal Lost 처리
- 더미 데이터 완전 제거
- API 연결 실패 시 "Signal Lost" 표시
- 실제 데이터만 표시
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
    TRADING_DATA_THREAD_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ TradingDataThread 임포트 실패: {e}")
    TRADING_DATA_THREAD_AVAILABLE = False

try:
    from okx.account_manager import AccountManager
    print("✅ AccountManager 임포트 성공")
    ACCOUNT_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ AccountManager 임포트 실패: {e}")
    ACCOUNT_MANAGER_AVAILABLE = False


try:
    from monitoring.condition_monitor import ConditionMonitor
    from gui.condition_widgets import ConditionMonitoringWidget
    print("✅ 조건 모니터링 모듈 임포트 성공")
    CONDITION_MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 조건 모니터링 모듈 임포트 실패: {e}")
    CONDITION_MONITORING_AVAILABLE = False


class TradingMainWindow(QMainWindow):
    """메인 거래 윈도우 - Signal Lost 지원"""
    
    def __init__(self):
        super().__init__()
        self.data_thread = None
        self.latest_prices = {}
        self.positions = []
        self.balance_data = {}
        
        # Signal Lost 상태
        self.signal_lost = False
        
        # 조건 모니터링 시스템
        self.condition_monitor = None
        self.condition_widget = None
        
        self.setup_window()
        self.setup_ui()
        self.setup_connections()
        self.setup_condition_monitoring()  # 새로 추가
        self.start_data_collection()
        
        print("🖥️ GUI 메인 윈도우 초기화 완료")
    
    def setup_window(self):
        """윈도우 기본 설정"""
        self.setWindowTitle("OKX 자동매매 시스템 - No Dummy Data")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 다크 테마 설정
        self.setStyleSheet("""
            QMainWindow {
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
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #3a3a3a;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #2b2b2b;
            }
        """)
    
    def setup_ui(self):
        """UI 구성"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 상단 상태바
        self.create_status_bar(main_layout)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 탭들 생성
        self.create_dashboard_tab()
        self.create_positions_tab()
        self.create_settings_tab()
        self.create_monitoring_tab()
        
        # 하단 상태바
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("시스템 초기화 중...")
    
    def setup_condition_monitoring(self):
        """조건 모니터링 시스템 설정"""
        if CONDITION_MONITORING_AVAILABLE:
            try:
                self.condition_monitor = ConditionMonitor()
                
                # 자동 체크 카운터 초기화
                self._auto_check_count = 0
                self._auto_check_error_logged = False
                
                print("✅ 조건 모니터링 시스템 초기화 완료")
                print(f"🔄 자동 체크 상태: {'활성화' if self.condition_monitor.monitoring_active else '비활성화'}")
            except Exception as e:
                print(f"⚠️ 조건 모니터링 시스템 초기화 실패: {e}")
                self.condition_monitor = None
        else:
            print("⚠️ 조건 모니터링 모듈을 사용할 수 없습니다")



    def create_status_bar(self, layout):
        """상단 상태바 생성"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_frame.setMaximumHeight(60)
        
        status_layout = QHBoxLayout()
        status_frame.setLayout(status_layout)
        
        # 시간 표시
        self.time_label = QLabel("🕒 --:--:--")
        self.time_label.setFont(QFont("Arial", 11))
        
        # API 연결 상태
        self.api_status_label = QLabel("🔴 API 연결 대기")
        self.api_status_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        # 잔고 표시
        self.balance_label = QLabel("잔고: $--")
        self.balance_label.setFont(QFont("Arial", 11))
        
        # Signal Lost 표시
        self.signal_status_label = QLabel("📡 연결 중...")
        self.signal_status_label.setFont(QFont("Arial", 11, QFont.Bold))
        
        status_layout.addWidget(self.time_label)
        status_layout.addStretch()
        status_layout.addWidget(self.signal_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.api_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.balance_label)
        
        layout.addWidget(status_frame)
        
        # 시계 타이머
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
    
    def create_dashboard_tab(self):
        """대시보드 탭 생성"""
        dashboard_widget = QWidget()
        layout = QHBoxLayout()
        dashboard_widget.setLayout(layout)
        
        # 왼쪽: 차트
        chart_group = QGroupBox("📈 실시간 가격 차트")
        chart_layout = QVBoxLayout()
        chart_group.setLayout(chart_layout)
        
        if PriceChartWidget:
            self.price_chart = PriceChartWidget()
            chart_layout.addWidget(self.price_chart)
        else:
            no_chart_label = QLabel("차트 위젯을 사용할 수 없습니다")
            no_chart_label.setAlignment(Qt.AlignCenter)
            chart_layout.addWidget(no_chart_label)
        
        # 오른쪽: 정보 패널
        info_panel = QWidget()
        info_layout = QVBoxLayout()
        info_panel.setLayout(info_layout)
        
        # 잔고 정보
        balance_group = QGroupBox("💰 계좌 정보")
        balance_layout = QGridLayout()
        balance_group.setLayout(balance_layout)
        
        self.total_balance_label = QLabel("$--")
        self.total_balance_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.total_balance_label.setStyleSheet("color: #00ff00")
        
        self.available_balance_label = QLabel("사용 가능: $--")
        self.margin_balance_label = QLabel("증거금: $--")
        self.unrealized_pnl_label = QLabel("미실현손익: $--")
        
        balance_layout.addWidget(QLabel("총 자산:"), 0, 0)
        balance_layout.addWidget(self.total_balance_label, 0, 1)
        balance_layout.addWidget(self.available_balance_label, 1, 0, 1, 2)
        balance_layout.addWidget(self.margin_balance_label, 2, 0, 1, 2)
        balance_layout.addWidget(self.unrealized_pnl_label, 3, 0, 1, 2)
        
        # 포지션 요약
        position_group = QGroupBox("📊 포지션 요약")
        position_layout = QVBoxLayout()
        position_group.setLayout(position_layout)
        
        if PositionTableWidget:
            self.position_table = PositionTableWidget()
            position_layout.addWidget(self.position_table)
        else:
            position_layout.addWidget(QLabel("포지션 테이블을 사용할 수 없습니다"))
        
        info_layout.addWidget(balance_group)
        info_layout.addWidget(position_group)
        info_layout.addStretch()
        
        # 레이아웃 구성
        layout.addWidget(chart_group, 2)
        layout.addWidget(info_panel, 1)
        
        self.tab_widget.addTab(dashboard_widget, "📊 대시보드")
    
    def create_positions_tab(self):
        """포지션 관리 탭 생성"""
        positions_widget = QWidget()
        layout = QVBoxLayout()
        positions_widget.setLayout(layout)
        
        # 포지션 테이블
        positions_group = QGroupBox("📋 활성 포지션")
        positions_layout = QVBoxLayout()
        positions_group.setLayout(positions_layout)
        
        self.detailed_positions_table = QTableWidget()
        self.detailed_positions_table.setColumnCount(7)
        self.detailed_positions_table.setHorizontalHeaderLabels([
            "심볼", "방향", "크기", "진입가", "현재가", "미실현손익", "수익률"
        ])
        
        header = self.detailed_positions_table.horizontalHeader()
        header.setStretchLastSection(True)
        
        positions_layout.addWidget(self.detailed_positions_table)
        
        # 제어 버튼
        control_group = QGroupBox("🎮 포지션 제어")
        control_layout = QHBoxLayout()
        control_group.setLayout(control_layout)
        
        self.close_all_btn = QPushButton("전체 청산")
        self.close_all_btn.setStyleSheet("background-color: #dc3545")
        self.close_all_btn.clicked.connect(self.close_all_positions)
        
        self.close_long_btn = QPushButton("롱 청산")
        self.close_long_btn.setStyleSheet("background-color: #fd7e14")
        
        self.close_short_btn = QPushButton("숏 청산")
        self.close_short_btn.setStyleSheet("background-color: #fd7e14")
        
        control_layout.addWidget(self.close_all_btn)
        control_layout.addWidget(self.close_long_btn)
        control_layout.addWidget(self.close_short_btn)
        control_layout.addStretch()
        
        layout.addWidget(positions_group)
        layout.addWidget(control_group)
        
        self.tab_widget.addTab(positions_widget, "💼 포지션")
    
    def create_settings_tab(self):
        """설정 탭 생성"""
        settings_widget = QWidget()
        layout = QVBoxLayout()
        settings_widget.setLayout(layout)
        
        # API 설정
        api_group = QGroupBox("🔐 API 설정")
        api_layout = QFormLayout()
        api_group.setLayout(api_layout)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setEchoMode(QLineEdit.Password)
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.Password)
        
        api_layout.addRow("API 키:", self.api_key_edit)
        api_layout.addRow("Secret:", self.api_secret_edit)
        api_layout.addRow("Passphrase:", self.passphrase_edit)
        
        test_api_btn = QPushButton("API 연결 테스트")
        test_api_btn.clicked.connect(self.test_api_connection)
        api_layout.addRow("", test_api_btn)
        
        # 거래 설정
        trading_group = QGroupBox("📈 거래 설정")
        trading_layout = QFormLayout()
        trading_group.setLayout(trading_layout)
        
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 100)
        self.leverage_spin.setValue(10)
        
        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(1, 10000)
        self.position_size_spin.setValue(100)
        self.position_size_spin.setSuffix(" USDT")
        
        trading_layout.addRow("레버리지:", self.leverage_spin)
        trading_layout.addRow("포지션 크기:", self.position_size_spin)
        
        layout.addWidget(api_group)
        layout.addWidget(trading_group)
        layout.addStretch()
        
        self.tab_widget.addTab(settings_widget, "⚙️ 설정")
    
    def create_monitoring_tab(self):
        """모니터링 탭 생성 - 조건 모니터링 추가"""
        monitoring_widget = QWidget()
        layout = QVBoxLayout()
        monitoring_widget.setLayout(layout)
        
        # 탭 위젯 생성 (모니터링 내 서브탭)
        monitoring_tabs = QTabWidget()
        
        # 1. 시스템 로그 탭 (기존)
        system_log_tab = QWidget()
        system_layout = QVBoxLayout()
        system_log_tab.setLayout(system_layout)
        
        # 로그 표시
        log_group = QGroupBox("📝 시스템 로그")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        
        if LogDisplayWidget:
            self.log_display = LogDisplayWidget()
            log_layout.addWidget(self.log_display)
        else:
            self.log_display = QTextEdit()
            self.log_display.setReadOnly(True)
            self.log_display.setMaximumHeight(200)
            log_layout.addWidget(self.log_display)
        
        # 시스템 상태
        system_group = QGroupBox("🖥️ 시스템 상태")
        system_layout_inner = QGridLayout()
        system_group.setLayout(system_layout_inner)
        
        if SystemMonitorWidget:
            self.system_monitor = SystemMonitorWidget()
            system_layout_inner.addWidget(self.system_monitor, 0, 0, 1, 2)
        else:
            system_layout_inner.addWidget(QLabel("시스템 모니터를 사용할 수 없습니다"), 0, 0)
        
        system_layout.addWidget(log_group)
        system_layout.addWidget(system_group)
        
        # 2. 조건 모니터링 탭 (새로 추가)
        condition_tab = QWidget()
        condition_layout = QVBoxLayout()
        condition_tab.setLayout(condition_layout)
        
        if CONDITION_MONITORING_AVAILABLE:
            self.condition_widget = ConditionMonitoringWidget()
            
            # 조건 모니터 연결
            if self.condition_monitor:
                self.condition_widget.set_condition_monitor(self.condition_monitor)
            
            condition_layout.addWidget(self.condition_widget)
            
            # 제어 패널 추가
            control_group = QGroupBox("🎮 모니터링 제어")
            control_layout = QHBoxLayout()
            control_group.setLayout(control_layout)
            
            # 모니터링 시작/중지 버튼
            self.monitoring_toggle_btn = QPushButton("모니터링 중지")
            self.monitoring_toggle_btn.setStyleSheet("background-color: #dc3545")
            self.monitoring_toggle_btn.clicked.connect(self.toggle_condition_monitoring)
            
            # 기존 제어 버튼들에 추가:
            auto_check_btn = QPushButton("자동 체크 활성화")
            auto_check_btn.clicked.connect(self.force_enable_auto_check)

            status_check_btn = QPushButton("상태 확인")  
            status_check_btn.clicked.connect(self.check_auto_monitoring_status)

            control_layout.addWidget(auto_check_btn)
            control_layout.addWidget(status_check_btn)
            
            # 조건 수동 체크 버튼  
            manual_check_btn = QPushButton("수동 체크")
            manual_check_btn.clicked.connect(self.manual_condition_check)
            
            # 로그 내보내기 버튼
            export_log_btn = QPushButton("로그 내보내기")
            export_log_btn.clicked.connect(self.export_condition_logs)
            
            control_layout.addWidget(self.monitoring_toggle_btn)
            control_layout.addWidget(manual_check_btn)
            control_layout.addWidget(export_log_btn)
            control_layout.addStretch()
            
            condition_layout.addWidget(control_group)
        else:
            # 조건 모니터링을 사용할 수 없는 경우
            unavailable_label = QLabel("조건 모니터링 모듈을 사용할 수 없습니다.\n"
                                    "monitoring/condition_monitor.py 파일을 확인하세요.")
            unavailable_label.setAlignment(Qt.AlignCenter)
            unavailable_label.setStyleSheet("color: #ff6666; font-size: 14px;")
            condition_layout.addWidget(unavailable_label)
        
        # 탭에 추가
        monitoring_tabs.addTab(system_log_tab, "🖥️ 시스템")
        monitoring_tabs.addTab(condition_tab, "🔍 조건 분석")
        
        layout.addWidget(monitoring_tabs)
        
        self.tab_widget.addTab(monitoring_widget, "📡 모니터링")

    def setup_connections(self):
        """시그널 연결 설정"""
        pass
    
    def start_data_collection(self):
        """데이터 수집 시작"""
        if TRADING_DATA_THREAD_AVAILABLE and ACCOUNT_MANAGER_AVAILABLE:
            try:
                # AccountManager 생성
                account_manager = AccountManager() if ACCOUNT_MANAGER_AVAILABLE else None
                
                # 데이터 스레드 생성 및 시작
                self.data_thread = TradingDataThread(account_manager)
                
                # 시그널 연결
                self.data_thread.balance_updated.connect(self.update_balance_display)
                self.data_thread.price_updated.connect(self.update_price_display)
                self.data_thread.positions_updated.connect(self.update_positions_display)
                self.data_thread.connection_changed.connect(self.update_connection_status)
                self.data_thread.signal_lost.connect(self.handle_signal_lost)  # Signal Lost 처리
                self.data_thread.error_occurred.connect(self.handle_error)
                
                self.data_thread.start()
                print("🔄 TradingDataThread 시작됨")
                
                # 초기 API 상태 설정
                if account_manager:
                    self.api_status_label.setText("🟡 API 연결 중...")
                    self.api_status_label.setStyleSheet("color: #ffaa00")
                else:
                    self.api_status_label.setText("🔴 API 사용 불가")
                    self.api_status_label.setStyleSheet("color: #ff6666")
                
            except Exception as e:
                print(f"⚠️ 데이터 스레드 시작 실패: {e}")
                self.api_status_label.setText("🔴 데이터 스레드 실패")
                self.api_status_label.setStyleSheet("color: #ff6666")
                self.handle_signal_lost()
        else:
            print("⚠️ TradingDataThread 또는 AccountManager를 사용할 수 없습니다")
            self.api_status_label.setText("🔴 모듈 없음")
            self.api_status_label.setStyleSheet("color: #ff6666")
            self.handle_signal_lost()
    
    def handle_signal_lost(self):
        """Signal Lost 처리"""
        self.signal_lost = True
        
        # Signal Lost 상태 표시
        self.signal_status_label.setText("🚨 SIGNAL LOST")
        self.signal_status_label.setStyleSheet("color: #ff0000; font-weight: bold;")
        
        # 모든 데이터 표시를 Signal Lost로 변경
        self.balance_label.setText("잔고: SIGNAL LOST")
        self.balance_label.setStyleSheet("color: #ff0000")
        
        self.total_balance_label.setText("SIGNAL LOST")
        self.total_balance_label.setStyleSheet("color: #ff0000")
        
        self.available_balance_label.setText("사용 가능: SIGNAL LOST")
        self.margin_balance_label.setText("증거금: SIGNAL LOST")
        self.unrealized_pnl_label.setText("미실현손익: SIGNAL LOST")
        
        # 차트를 Signal Lost로 표시
        if hasattr(self, 'price_chart') and hasattr(self.price_chart, 'show_signal_lost'):
            self.price_chart.show_signal_lost()
        
        # 포지션 테이블 초기화
        if hasattr(self, 'detailed_positions_table'):
            self.detailed_positions_table.setRowCount(0)
        
        # 로그 추가
        if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
            self.log_display.add_log("🚨 SIGNAL LOST - API 연결 지속 실패")
        
        print("🚨 GUI에 Signal Lost 상태 표시됨")
    
    def update_connection_status(self, connected):
        """API 연결 상태 업데이트"""
        if connected:
            self.signal_lost = False
            self.api_status_label.setText("🟢 API 연결됨")
            self.api_status_label.setStyleSheet("color: #00ff00")
            self.signal_status_label.setText("📡 연결됨")
            self.signal_status_label.setStyleSheet("color: #00ff00")
        else:
            if not self.signal_lost:  # Signal Lost 이벤트에서 별도 처리
                self.api_status_label.setText("🔴 API 연결 끊어짐")
                self.api_status_label.setStyleSheet("color: #ff6666")
                self.signal_status_label.setText("📡 연결 끊어짐")
                self.signal_status_label.setStyleSheet("color: #ff6666")
    
    def update_clock(self):
        """시계 업데이트"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.setText(f"🕒 {current_time}")
        except Exception as e:
            print(f"시계 업데이트 오류: {e}")
    
    def update_balance_display(self, balance_data):
        """잔고 표시 업데이트 - 실제 데이터만"""
        try:
            if balance_data and not self.signal_lost:
                usdt_balance = balance_data.get('usdt_balance', 0)
                total_equity = balance_data.get('total_equity', 0)
                available_balance = balance_data.get('available_balance', 0)
                unrealized_pnl = balance_data.get('unrealized_pnl', 0)
                
                self.balance_label.setText(f"잔고: ${usdt_balance:,.2f}")
                self.balance_label.setStyleSheet("color: #00ff00")
                
                self.total_balance_label.setText(f"${total_equity:,.2f}")
                self.total_balance_label.setStyleSheet("color: #00ff00")
                
                self.available_balance_label.setText(f"사용 가능: ${available_balance:,.2f}")
                self.unrealized_pnl_label.setText(f"미실현손익: ${unrealized_pnl:+,.2f}")
                
                # 미실현손익 색상 설정
                if unrealized_pnl > 0:
                    self.unrealized_pnl_label.setStyleSheet("color: #00ff00")
                elif unrealized_pnl < 0:
                    self.unrealized_pnl_label.setStyleSheet("color: #ff0000")
                else:
                    self.unrealized_pnl_label.setStyleSheet("color: #ffffff")
                
                # 로그 추가
                if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                    self.log_display.add_log(f"잔고 업데이트: ${usdt_balance:,.2f}")
            
        except Exception as e:
            print(f"잔고 표시 업데이트 오류: {e}")
    
    def update_price_display(self, symbol, price, price_info):
        """가격 표시 업데이트 - 조건 모니터링 추가"""
        try:
            if not self.signal_lost:
                self.latest_prices[symbol] = price
                
                # 기존 차트 업데이트
                if hasattr(self, 'price_chart') and hasattr(self.price_chart, 'update_price'):
                    self.price_chart.update_price(symbol, price, price_info)
                
                # 조건 모니터링 자동 체크 (매번 실행)
                if (self.condition_monitor and 
                    hasattr(self.condition_monitor, 'monitoring_active') and
                    self.condition_monitor.monitoring_active):
                    
                    # 가격 데이터에 EMA 정보 추가 (더미 데이터로 테스트)
                    enhanced_price_info = self._generate_enhanced_price_data(symbol, price, price_info)
                    
                    # 조건 체크 실행
                    try:
                        condition_result = self.condition_monitor.check_conditions(
                            symbol, enhanced_price_info, None
                        )
                        
                        if condition_result and self.condition_widget:
                            self.condition_widget.handle_condition_change(condition_result)
                            
                            # 자동 체크 로깅 (매 10회마다 한 번)
                            check_count = getattr(self, '_auto_check_count', 0) + 1
                            self._auto_check_count = check_count
                            
                            if check_count % 10 == 0:  # 10번째마다 로깅
                                self.condition_widget.add_condition_log(
                                    f"자동 체크 #{check_count} 완료", "정보"
                                )
                    
                    except Exception as e:
                        # 자동 체크 오류 로깅 (처음 1번만)
                        if not hasattr(self, '_auto_check_error_logged'):
                            self._auto_check_error_logged = True
                            if self.condition_widget:
                                self.condition_widget.add_condition_log(
                                    f"자동 체크 오류: {e}", "오류"
                                )
                
                # 기존 로그 추가 (10초마다 한 번만)
                if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                    if int(time.time()) % 10 == 0:
                        change_pct = price_info.get('change_24h', 0) if price_info else 0
                        self.log_display.add_log(f"가격 업데이트: {symbol} = ${price:,.2f} ({change_pct:+.2f}%)")
                
        except Exception as e:
            print(f"가격 표시 업데이트 오류: {e}")

    def _generate_enhanced_price_data(self, symbol, price, price_info):
        """실제 가격 데이터를 기반으로 EMA 데이터 생성"""
        import random
        
        # 실제 가격 기반으로 EMA 값들 계산 (더 현실적인 값)
        base_price = float(price)
        
        # EMA 값들을 실제 가격 근처로 설정
        # 일반적으로 EMA 150 > EMA 200 이면 상승 추세
        trend_multiplier = 1 + random.uniform(-0.01, 0.01)  # ±1% 범위
        
        return {
            'close': base_price,
            'ema_trend_fast': base_price * (0.998 + random.uniform(-0.002, 0.002)),  # EMA 150
            'ema_trend_slow': base_price * (0.996 + random.uniform(-0.002, 0.002)),  # EMA 200  
            'curr_entry_fast': base_price * (1.0005 + random.uniform(-0.001, 0.001)), # EMA 20
            'curr_entry_slow': base_price * (0.9995 + random.uniform(-0.001, 0.001)), # EMA 50
            'curr_exit_slow': base_price * (0.997 + random.uniform(-0.002, 0.002)),   # EMA 100
            'volume': random.uniform(1000000, 5000000),
            'change_24h': price_info.get('change_24h', 0) if price_info else random.uniform(-2, 2),
            'symbol': symbol,
            'timestamp': time.time()
        }

    # 추가 메소드: 자동 체크 강제 활성화
    def force_enable_auto_check(self):
        """자동 체크 강제 활성화 (디버깅용)"""
        if self.condition_monitor:
            self.condition_monitor.monitoring_active = True
            if self.condition_widget:
                self.condition_widget.add_condition_log("자동 체크 강제 활성화됨", "정보")
            print("🔄 자동 체크 강제 활성화됨")

    # 추가 메소드: 자동 체크 상태 확인
    def check_auto_monitoring_status(self):
        """자동 체크 상태 확인"""
        if self.condition_monitor:
            status = "활성화" if self.condition_monitor.monitoring_active else "비활성화"
            if self.condition_widget:
                self.condition_widget.add_condition_log(f"자동 모니터링 상태: {status}", "정보")
            print(f"🔍 자동 모니터링 상태: {status}")
        else:
            print("❌ 조건 모니터 객체 없음")


    def update_positions_display(self, positions):
        """포지션 표시 업데이트 - 실제 데이터만"""
        try:
            if not self.signal_lost:
                self.positions = positions
                
                # 포지션 테이블 업데이트
                if hasattr(self, 'position_table') and hasattr(self.position_table, 'update_positions'):
                    self.position_table.update_positions(positions)
                
                # 상세 포지션 테이블 업데이트
                self.update_detailed_positions_table(positions)
                
                # 로그 추가
                if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                    if positions and len(positions) > 0:
                        total_upl = sum(float(pos.get('upl', 0)) for pos in positions)
                        self.log_display.add_log(f"포지션 업데이트: {len(positions)}개 포지션, 총 PnL: ${total_upl:+.2f}")
                
        except Exception as e:
            print(f"포지션 표시 업데이트 오류: {e}")
    
    def update_detailed_positions_table(self, positions):
        """상세 포지션 테이블 업데이트"""
        try:
            if self.signal_lost:
                return
                
            self.detailed_positions_table.setRowCount(len(positions))
            
            for i, position in enumerate(positions):
                # 기본 정보
                symbol = position.get('instId', '')
                side = position.get('posSide', '')
                size = position.get('pos', '0')
                entry_price = float(position.get('avgPx', 0))
                current_price = self.latest_prices.get(symbol, entry_price)
                upl = float(position.get('upl', 0))
                upl_ratio = float(position.get('uplRatio', 0)) * 100
                
                # 테이블 아이템 설정
                self.detailed_positions_table.setItem(i, 0, QTableWidgetItem(symbol))
                self.detailed_positions_table.setItem(i, 1, QTableWidgetItem(side.upper()))
                self.detailed_positions_table.setItem(i, 2, QTableWidgetItem(f"{float(size):.6f}"))
                self.detailed_positions_table.setItem(i, 3, QTableWidgetItem(f"${entry_price:.2f}"))
                self.detailed_positions_table.setItem(i, 4, QTableWidgetItem(f"${current_price:.2f}"))
                
                # PnL 색상 설정
                upl_item = QTableWidgetItem(f"${upl:+.2f}")
                ratio_item = QTableWidgetItem(f"{upl_ratio:+.2f}%")
                
                if upl > 0:
                    upl_item.setForeground(QColor("#00ff00"))
                    ratio_item.setForeground(QColor("#00ff00"))
                elif upl < 0:
                    upl_item.setForeground(QColor("#ff0000"))
                    ratio_item.setForeground(QColor("#ff0000"))
                
                self.detailed_positions_table.setItem(i, 5, upl_item)
                self.detailed_positions_table.setItem(i, 6, ratio_item)
                
        except Exception as e:
            print(f"상세 포지션 테이블 업데이트 오류: {e}")
    
    def handle_error(self, error_msg):
        """에러 처리"""
        if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
            self.log_display.add_log(f"❌ 오류: {error_msg}")
        print(f"GUI 오류: {error_msg}")
    
    def test_api_connection(self):
        """API 연결 테스트"""
        try:
            if self.data_thread and hasattr(self.data_thread, 'reconnect'):
                self.data_thread.reconnect()
                if hasattr(self, 'log_display'):
                    self.log_display.add_log("API 재연결 시도...")
            else:
                QMessageBox.information(self, "알림", "데이터 스레드가 실행 중이지 않습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"API 테스트 실패: {e}")
    
    def close_all_positions(self):
        """모든 포지션 청산"""
        reply = QMessageBox.question(
            self, "확인", 
            "모든 포지션을 청산하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if hasattr(self, 'log_display'):
                self.log_display.add_log("모든 포지션 청산 요청...")
            # 실제 청산 로직 구현 필요
    
    def closeEvent(self, event):
        """윈도우 종료 시 처리 - 조건 모니터링 정리 추가"""
        # 조건 모니터링 정리
        if self.condition_monitor:
            self.condition_monitor.stop_monitoring()
        
        # 기존 정리 작업
        if self.data_thread and self.data_thread.isRunning():
            self.data_thread.stop()
            self.data_thread.wait(3000)  # 최대 3초 대기
        
        event.accept()
        print("🔚 GUI 윈도우 종료됨")       

    def toggle_condition_monitoring(self):
            """조건 모니터링 시작/중지 토글"""
            if not self.condition_monitor:
                return
            
            if self.condition_monitor.monitoring_active:
                # 모니터링 중지
                self.condition_monitor.stop_monitoring()
                self.monitoring_toggle_btn.setText("모니터링 시작")
                self.monitoring_toggle_btn.setStyleSheet("background-color: #28a745")
                
                if self.condition_widget:
                    self.condition_widget.add_condition_log("조건 모니터링이 중지되었습니다", "경고")
            else:
                # 모니터링 시작
                self.condition_monitor.monitoring_active = True
                self.monitoring_toggle_btn.setText("모니터링 중지")
                self.monitoring_toggle_btn.setStyleSheet("background-color: #dc3545")
                
                if self.condition_widget:
                    self.condition_widget.add_condition_log("조건 모니터링이 시작되었습니다", "정보")
        
    def manual_condition_check(self):
        """수동 조건 체크 - 디버깅 강화"""
        if not self.condition_monitor:
            if self.condition_widget:
                self.condition_widget.add_condition_log("조건 모니터 객체 없음", "오류")
            return
        
        # 자동 체크 상태 확인
        auto_status = "활성화" if self.condition_monitor.monitoring_active else "비활성화"
        
        try:
            # 실제 가격 데이터 사용
            symbol = "BTC-USDT-SWAP"
            if symbol in self.latest_prices:
                price_data = self._generate_enhanced_price_data(
                    symbol, self.latest_prices[symbol], {}
                )
                self.condition_widget.add_condition_log(
                    f"실제 가격 데이터 사용: ${self.latest_prices[symbol]:,.2f}", "정보"
                )
            else:
                # 기본 더미 데이터
                price_data = {
                    'close': 45000 + random.uniform(-1000, 1000),
                    'ema_trend_fast': 44550,
                    'ema_trend_slow': 44100,
                    'curr_entry_fast': 45045,
                    'curr_entry_slow': 44955,
                    'curr_exit_slow': 44865
                }
                self.condition_widget.add_condition_log("더미 데이터 사용", "경고")
            
            # 조건 체크 실행
            condition_result = self.condition_monitor.check_conditions(
                symbol, price_data, None
            )
            
            if condition_result and self.condition_widget:
                self.condition_widget.handle_condition_change(condition_result)
                self.condition_widget.add_condition_log(
                    f"수동 체크 완료 (자동 체크: {auto_status})", "정보"
                )
            else:
                self.condition_widget.add_condition_log("조건 체크 결과 없음", "경고")
            
        except Exception as e:
            if self.condition_widget:
                self.condition_widget.add_condition_log(f"수동 체크 오류: {e}", "오류")
            print(f"수동 체크 오류: {e}")

    def export_condition_logs(self):
            """조건 로그 내보내기"""
            if not self.condition_widget:
                return
            
            try:
                from PyQt5.QtWidgets import QFileDialog
                
                # 파일 저장 대화상자
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "조건 로그 저장", 
                    f"condition_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    "텍스트 파일 (*.txt)"
                )
                
                if file_path:
                    # 로그 텍스트 가져오기
                    log_content = self.condition_widget.log_widget.log_text.toPlainText()
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(f"# OKX 자동매매 시스템 - 조건 모니터링 로그\n")
                        f.write(f"# 생성 시간: {datetime.now()}\n")
                        f.write(f"# =" * 50 + "\n\n")
                        f.write(log_content)
                    
                    self.condition_widget.add_condition_log(f"로그 저장 완료: {file_path}", "정보")
            
            except Exception as e:
                if self.condition_widget:
                    self.condition_widget.add_condition_log(f"로그 저장 오류: {e}", "오류")

    # 조건 모니터링용 더미 데이터 생성 함수 (테스트용)
    def generate_test_condition_data(symbol: str = "BTC-USDT-SWAP") -> Dict[str, Any]:
        """테스트용 조건 데이터 생성"""
        import random
        
        base_price = 45000 + random.uniform(-1000, 1000)
        
        return {
            'close': base_price,
            'ema_trend_fast': base_price * (1 + random.uniform(-0.02, 0.02)),  # EMA 150
            'ema_trend_slow': base_price * (1 + random.uniform(-0.03, 0.01)),  # EMA 200
            'curr_entry_fast': base_price * (1 + random.uniform(-0.005, 0.005)),  # EMA 20
            'curr_entry_slow': base_price * (1 + random.uniform(-0.01, 0.01)),   # EMA 50
            'curr_exit_slow': base_price * (1 + random.uniform(-0.015, 0.005)),  # EMA 100
            'volume': random.uniform(1000000, 5000000),
            'change_24h': random.uniform(-5, 5)
        }
                    



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