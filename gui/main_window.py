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
        
        self.setup_window()
        self.setup_ui()
        self.setup_connections()
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
        """모니터링 탭 생성"""
        monitoring_widget = QWidget()
        layout = QVBoxLayout()
        monitoring_widget.setLayout(layout)
        
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
            self.log_display.setMaximumHeight(300)
            log_layout.addWidget(self.log_display)
        
        # 시스템 상태
        system_group = QGroupBox("🖥️ 시스템 상태")
        system_layout = QGridLayout()
        system_group.setLayout(system_layout)
        
        if SystemMonitorWidget:
            self.system_monitor = SystemMonitorWidget()
            system_layout.addWidget(self.system_monitor, 0, 0, 1, 2)
        else:
            system_layout.addWidget(QLabel("시스템 모니터를 사용할 수 없습니다"), 0, 0)
        
        layout.addWidget(log_group)
        layout.addWidget(system_group)
        
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
        """가격 표시 업데이트 - 실제 데이터만"""
        try:
            if not self.signal_lost:
                self.latest_prices[symbol] = price
                
                # 차트 업데이트
                if hasattr(self, 'price_chart') and hasattr(self.price_chart, 'update_price'):
                    self.price_chart.update_price(symbol, price, price_info)
                
                # 로그 추가 (10초마다 한 번만)
                if hasattr(self, 'log_display') and hasattr(self.log_display, 'add_log'):
                    if int(time.time()) % 10 == 0:
                        change_pct = price_info.get('change_24h', 0)
                        self.log_display.add_log(f"가격 업데이트: {symbol} = ${price:,.2f} ({change_pct:+.2f}%)")
                
        except Exception as e:
            print(f"가격 표시 업데이트 오류: {e}")
    
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
        """윈도우 종료 시 처리"""
        if self.data_thread and self.data_thread.isRunning():
            self.data_thread.stop()
            self.data_thread.wait(3000)  # 최대 3초 대기
        
        event.accept()
        print("🔚 GUI 윈도우 종료됨")
            

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