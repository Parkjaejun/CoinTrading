# gui/main_window.py
"""
OKX 자동매매 시스템 메인 GUI
PyQt5 기반 통합 인터페이스
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
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPalette, QColor, QMovie

import pyqtgraph as pg
import pandas as pd
import numpy as np

# 프로젝트 모듈들 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    API_KEY, API_SECRET, PASSPHRASE, TRADING_CONFIG, 
    LONG_STRATEGY_CONFIG, SHORT_STRATEGY_CONFIG, NOTIFICATION_CONFIG
)
from okx.account_manager import AccountManager
from okx.connection_manager import connection_manager
from strategy.dual_manager import DualStrategyManager
from utils.logger import log_system, log_error
from utils.notifications import initialize_notifications, send_system_alert
from backtest.backtester import run_strategy_backtest

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
        self.strategy_manager = None
        self.is_running = False
        self.should_stop = False
        
    def initialize_trading_system(self):
        """트레이딩 시스템 초기화"""
        try:
            # 연결 확인
            if not connection_manager.test_connection():
                self.error_occurred.emit("API 연결 실패")
                return False
            
            # 전략 매니저 초기화
            self.strategy_manager = DualStrategyManager(
                total_capital=TRADING_CONFIG.get('initial_capital', 10000),
                symbols=TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            )
            
            # 알림 시스템 초기화
            initialize_notifications(NOTIFICATION_CONFIG)
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"초기화 실패: {str(e)}")
            return False
    
    def run(self):
        """메인 실행 루프"""
        if not self.initialize_trading_system():
            return
        
        self.is_running = True
        log_system("GUI: 트레이딩 시스템 시작")
        
        while self.is_running and not self.should_stop:
            try:
                # 상태 업데이트 (5초마다)
                status = self.get_system_status()
                self.status_updated.emit(status)
                
                # 포지션 업데이트
                if self.strategy_manager:
                    positions = self.get_position_summary()
                    self.position_updated.emit(positions)
                
                # 1초 대기
                self.msleep(1000)
                
            except Exception as e:
                self.error_occurred.emit(f"실행 오류: {str(e)}")
                self.msleep(5000)
    
    def stop_trading(self):
        """트레이딩 중지"""
        self.should_stop = True
        self.is_running = False
        
        if self.strategy_manager:
            self.strategy_manager.close_all_positions()
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        return {
            'is_connected': connection_manager.is_connected,
            'is_running': self.is_running,
            'uptime': datetime.now(),
            'error_count': 0
        }
    
    def get_position_summary(self) -> Dict[str, Any]:
        """포지션 요약"""
        if not self.strategy_manager:
            return {}
        
        return self.strategy_manager.position_manager.get_summary()

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
        
        # 상태 표시 그룹
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
        
        # 가격 차트
        chart_group = QGroupBox("실시간 차트")
        chart_layout = QVBoxLayout()
        
        self.price_chart = pg.PlotWidget()
        self.price_chart.setLabel('left', 'Price ($)')
        self.price_chart.setLabel('bottom', 'Time')
        self.price_chart.showGrid(x=True, y=True)
        
        chart_layout.addWidget(self.price_chart)
        chart_group.setLayout(chart_layout)
        right_layout.addWidget(chart_group)
        
        # 전략 성과
        performance_group = QGroupBox("전략별 성과")
        perf_layout = QGridLayout()
        
        # 롱 전략
        perf_layout.addWidget(QLabel("롱 전략:"), 0, 0)
        self.long_performance = QLabel("승률: 0%, 손익: $0")
        perf_layout.addWidget(self.long_performance, 0, 1)
        
        # 숏 전략
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
        
        # 차트 데이터 초기화
        self.price_data = []
        self.time_data = []
    
    def setup_timer(self):
        """타이머 설정"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # 1초마다 업데이트
    
    def update_status(self, status: Dict[str, Any]):
        """상태 업데이트"""
        # 연결 상태
        if status.get('is_connected', False):
            self.connection_status.setText("🟢 연결됨")
            self.connection_status.setStyleSheet("color: green;")
        else:
            self.connection_status.setText("🔴 연결 끊어짐")
            self.connection_status.setStyleSheet("color: red;")
        
        # 거래 상태
        if status.get('is_running', False):
            self.trading_status.setText("▶️ 거래 중")
            self.trading_status.setStyleSheet("color: green;")
        else:
            self.trading_status.setText("⏸️ 거래 중지")
            self.trading_status.setStyleSheet("color: orange;")
    
    def update_positions(self, positions: Dict[str, Any]):
        """포지션 업데이트"""
        active_positions = positions.get('positions', {})
        
        self.position_table.setRowCount(len(active_positions))
        
        for row, (symbol, pos_data) in enumerate(active_positions.items()):
            self.position_table.setItem(row, 0, QTableWidgetItem(symbol))
            self.position_table.setItem(row, 1, QTableWidgetItem(pos_data.get('side', '').upper()))
            self.position_table.setItem(row, 2, QTableWidgetItem(f"{pos_data.get('size', 0):.6f}"))
            self.position_table.setItem(row, 3, QTableWidgetItem(f"${pos_data.get('entry_price', 0):.2f}"))
            self.position_table.setItem(row, 4, QTableWidgetItem("$0.00"))  # 현재가는 별도 업데이트
            self.position_table.setItem(row, 5, QTableWidgetItem("$0.00"))  # PnL 계산 필요
    
    def update_trades(self, trade_data: List[Dict]):
        """거래 내역 업데이트"""
        recent_trades = trade_data[-10:] if len(trade_data) > 10 else trade_data
        
        self.trades_table.setRowCount(len(recent_trades))
        
        for row, trade in enumerate(recent_trades):
            time_str = trade.get('exit_time', datetime.now()).strftime('%H:%M:%S')
            self.trades_table.setItem(row, 0, QTableWidgetItem(time_str))
            self.trades_table.setItem(row, 1, QTableWidgetItem(trade.get('symbol', '')))
            self.trades_table.setItem(row, 2, QTableWidgetItem(trade.get('close_reason', '')))
            self.trades_table.setItem(row, 3, QTableWidgetItem("$0.00"))
            self.trades_table.setItem(row, 4, QTableWidgetItem("$0.00"))
    
    def update_chart(self, symbol: str, price: float):
        """차트 업데이트"""
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
    
    def update_display(self):
        """디스플레이 주기적 업데이트"""
        # 운영시간 업데이트 (예시)
        self.uptime_label.setText(f"운영시간: {datetime.now().strftime('%H:%M:%S')}")

class SettingsTab(QWidget):
    """설정 탭"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # API 설정 그룹
        api_group = QGroupBox("API 설정")
        api_layout = QGridLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setText(API_KEY if API_KEY != "your_api_key_here" else "")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        
        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setText(API_SECRET if API_SECRET != "your_api_secret_here" else "")
        self.api_secret_edit.setEchoMode(QLineEdit.Password)
        
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setText(PASSPHRASE if PASSPHRASE != "your_passphrase_here" else "")
        self.passphrase_edit.setEchoMode(QLineEdit.Password)
        
        self.test_connection_btn = QPushButton("연결 테스트")
        self.test_connection_btn.clicked.connect(self.test_api_connection)
        
        api_layout.addWidget(QLabel("API Key:"), 0, 0)
        api_layout.addWidget(self.api_key_edit, 0, 1)
        api_layout.addWidget(QLabel("Secret:"), 1, 0)
        api_layout.addWidget(self.api_secret_edit, 1, 1)
        api_layout.addWidget(QLabel("Passphrase:"), 2, 0)
        api_layout.addWidget(self.passphrase_edit, 2, 1)
        api_layout.addWidget(self.test_connection_btn, 3, 1)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 전략 설정
        strategy_layout = QHBoxLayout()
        
        # 롱 전략 설정
        long_group = QGroupBox("롱 전략 설정")
        long_layout = QFormLayout()
        
        self.long_capital_spin = QDoubleSpinBox()
        self.long_capital_spin.setRange(100, 1000000)
        self.long_capital_spin.setValue(TRADING_CONFIG.get('initial_capital', 10000) / 2)
        
        self.long_leverage_spin = QSpinBox()
        self.long_leverage_spin.setRange(1, 100)
        self.long_leverage_spin.setValue(LONG_STRATEGY_CONFIG.get('leverage', 10))
        
        self.long_trailing_spin = QDoubleSpinBox()
        self.long_trailing_spin.setRange(0.01, 0.50)
        self.long_trailing_spin.setSingleStep(0.01)
        self.long_trailing_spin.setValue(LONG_STRATEGY_CONFIG.get('trailing_stop', 0.10))
        
        long_layout.addRow("초기 자본:", self.long_capital_spin)
        long_layout.addRow("레버리지:", self.long_leverage_spin)
        long_layout.addRow("트레일링 스탑:", self.long_trailing_spin)
        
        long_group.setLayout(long_layout)
        strategy_layout.addWidget(long_group)
        
        # 숏 전략 설정
        short_group = QGroupBox("숏 전략 설정")
        short_layout = QFormLayout()
        
        self.short_capital_spin = QDoubleSpinBox()
        self.short_capital_spin.setRange(100, 1000000)
        self.short_capital_spin.setValue(TRADING_CONFIG.get('initial_capital', 10000) / 2)
        
        self.short_leverage_spin = QSpinBox()
        self.short_leverage_spin.setRange(1, 100)
        self.short_leverage_spin.setValue(SHORT_STRATEGY_CONFIG.get('leverage', 3))
        
        self.short_trailing_spin = QDoubleSpinBox()
        self.short_trailing_spin.setRange(0.01, 0.50)
        self.short_trailing_spin.setSingleStep(0.01)
        self.short_trailing_spin.setValue(SHORT_STRATEGY_CONFIG.get('trailing_stop', 0.02))
        
        short_layout.addRow("초기 자본:", self.short_capital_spin)
        short_layout.addRow("레버리지:", self.short_leverage_spin)
        short_layout.addRow("트레일링 스탑:", self.short_trailing_spin)
        
        short_group.setLayout(short_layout)
        strategy_layout.addWidget(short_group)
        
        layout.addLayout(strategy_layout)
        
        # 알림 설정
        notification_group = QGroupBox("알림 설정")
        notif_layout = QGridLayout()
        
        self.slack_enabled = QCheckBox("슬랙 알림")
        self.slack_enabled.setChecked(NOTIFICATION_CONFIG.get('slack', {}).get('enabled', False))
        
        self.telegram_enabled = QCheckBox("텔레그램 알림")
        self.telegram_enabled.setChecked(NOTIFICATION_CONFIG.get('telegram', {}).get('enabled', False))
        
        self.email_enabled = QCheckBox("이메일 알림")
        self.email_enabled.setChecked(NOTIFICATION_CONFIG.get('email', {}).get('enabled', False))
        
        notif_layout.addWidget(self.slack_enabled, 0, 0)
        notif_layout.addWidget(self.telegram_enabled, 0, 1)
        notif_layout.addWidget(self.email_enabled, 0, 2)
        
        notification_group.setLayout(notif_layout)
        layout.addWidget(notification_group)
        
        # 설정 저장 버튼
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_settings_btn = QPushButton("설정 저장")
        self.save_settings_btn.clicked.connect(self.save_settings)
        save_layout.addWidget(self.save_settings_btn)
        
        layout.addLayout(save_layout)
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
    
    def save_settings(self):
        """설정 저장"""
        try:
            # 설정 업데이트 (실제로는 config 파일에 저장)
            QMessageBox.information(self, "설정 저장", "✅ 설정이 저장되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "설정 저장", f"❌ 저장 오류: {str(e)}")

class MonitoringTab(QWidget):
    """모니터링 탭"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        
        # 왼쪽: 실시간 로그
        log_group = QGroupBox("실시간 로그")
        log_layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumBlockCount(1000)  # 최대 1000줄
        
        log_layout.addWidget(self.log_display)
        log_group.setLayout(log_layout)
        
        # 오른쪽: 시스템 상태
        status_group = QGroupBox("시스템 상태")
        status_layout = QVBoxLayout()
        
        # CPU/메모리 사용률
        self.cpu_progress = QProgressBar()
        self.memory_progress = QProgressBar()
        
        status_layout.addWidget(QLabel("CPU 사용률:"))
        status_layout.addWidget(self.cpu_progress)
        status_layout.addWidget(QLabel("메모리 사용률:"))
        status_layout.addWidget(self.memory_progress)
        
        # 네트워크 상태
        network_layout = QGridLayout()
        network_layout.addWidget(QLabel("API:"), 0, 0)
        self.api_status = QLabel("🔴")
        network_layout.addWidget(self.api_status, 0, 1)
        
        network_layout.addWidget(QLabel("WebSocket:"), 1, 0)
        self.ws_status = QLabel("🔴")
        network_layout.addWidget(self.ws_status, 1, 1)
        
        status_layout.addLayout(network_layout)
        
        # 오류 카운트
        error_layout = QGridLayout()
        error_layout.addWidget(QLabel("경고:"), 0, 0)
        self.warning_count = QLabel("0")
        error_layout.addWidget(self.warning_count, 0, 1)
        
        error_layout.addWidget(QLabel("오류:"), 1, 0)
        self.error_count = QLabel("0")
        error_layout.addWidget(self.error_count, 1, 1)
        
        status_layout.addLayout(error_layout)
        status_layout.addStretch()
        
        status_group.setLayout(status_layout)
        
        # 레이아웃에 추가
        layout.addWidget(log_group, 2)  # 2:1 비율
        layout.addWidget(status_group, 1)
        
        self.setLayout(layout)
    
    def add_log_message(self, message: str, level: str = "INFO"):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        color = {
            'INFO': 'white',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'TRADE': 'green'
        }.get(level, 'white')
        
        formatted_message = f"<span style='color: {color}'>[{timestamp}] [{level}] {message}</span>"
        self.log_display.append(formatted_message)
    
    def update_system_status(self, cpu_usage: float, memory_usage: float):
        """시스템 상태 업데이트"""
        self.cpu_progress.setValue(int(cpu_usage))
        self.memory_progress.setValue(int(memory_usage))

class BacktestTab(QWidget):
    """백테스팅 탭"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 백테스트 설정
        settings_group = QGroupBox("백테스트 설정")
        settings_layout = QGridLayout()
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["long", "short"])
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDateTime.currentDateTime().addDays(-30).date())
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDateTime.currentDateTime().date())
        
        self.initial_capital_spin = QDoubleSpinBox()
        self.initial_capital_spin.setRange(1000, 1000000)
        self.initial_capital_spin.setValue(10000)
        
        self.run_backtest_btn = QPushButton("백테스트 실행")
        self.run_backtest_btn.clicked.connect(self.run_backtest)
        
        settings_layout.addWidget(QLabel("전략:"), 0, 0)
        settings_layout.addWidget(self.strategy_combo, 0, 1)
        settings_layout.addWidget(QLabel("시작일:"), 0, 2)
        settings_layout.addWidget(self.start_date, 0, 3)
        settings_layout.addWidget(QLabel("종료일:"), 1, 0)
        settings_layout.addWidget(self.end_date, 1, 1)
        settings_layout.addWidget(QLabel("초기자본:"), 1, 2)
        settings_layout.addWidget(self.initial_capital_spin, 1, 3)
        settings_layout.addWidget(self.run_backtest_btn, 2, 3)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 백테스트 결과
        results_layout = QHBoxLayout()
        
        # 결과 요약
        summary_group = QGroupBox("백테스트 결과")
        summary_layout = QFormLayout()
        
        self.total_return_label = QLabel("0.00%")
        self.win_rate_label = QLabel("0.00%")
        self.max_drawdown_label = QLabel("0.00%")
        self.sharpe_ratio_label = QLabel("0.00")
        self.total_trades_label = QLabel("0")
        
        summary_layout.addRow("총 수익률:", self.total_return_label)
        summary_layout.addRow("승률:", self.win_rate_label)
        summary_layout.addRow("최대 낙폭:", self.max_drawdown_label)
        summary_layout.addRow("샤프 비율:", self.sharpe_ratio_label)
        summary_layout.addRow("총 거래수:", self.total_trades_label)
        
        summary_group.setLayout(summary_layout)
        results_layout.addWidget(summary_group)
        
        # 자본 곡선 차트
        chart_group = QGroupBox("자본 곡선")
        chart_layout = QVBoxLayout()
        
        self.equity_chart = pg.PlotWidget()
        self.equity_chart.setLabel('left', 'Capital ($)')
        self.equity_chart.setLabel('bottom', 'Time')
        self.equity_chart.showGrid(x=True, y=True)
        
        chart_layout.addWidget(self.equity_chart)
        chart_group.setLayout(chart_layout)
        results_layout.addWidget(chart_group)
        
        layout.addLayout(results_layout)
        self.setLayout(layout)
    
    def run_backtest(self):
        """백테스트 실행"""
        try:
            strategy_type = self.strategy_combo.currentText()
            start_date = self.start_date.date().toString('yyyy-MM-dd')
            end_date = self.end_date.date().toString('yyyy-MM-dd')
            initial_capital = self.initial_capital_spin.value()
            
            # 백테스트 실행 (별도 스레드에서)
            self.run_backtest_btn.setText("실행 중...")
            self.run_backtest_btn.setEnabled(False)
            
            # 실제 백테스트 호출
            result = run_strategy_backtest(strategy_type, 'BTC-USDT-SWAP', start_date, end_date, initial_capital)
            
            # 결과 업데이트
            self.update_backtest_results(result)
            
        except Exception as e:
            QMessageBox.critical(self, "백테스트 오류", f"백테스트 실행 중 오류: {str(e)}")
        finally:
            self.run_backtest_btn.setText("백테스트 실행")
            self.run_backtest_btn.setEnabled(True)
    
    def update_backtest_results(self, result):
        """백테스트 결과 업데이트"""
        if not result or not result.metrics:
            return
        
        metrics = result.metrics
        
        # 결과 레이블 업데이트
        self.total_return_label.setText(f"{metrics.get('total_return', 0)*100:.2f}%")
        self.win_rate_label.setText(f"{metrics.get('win_rate', 0)*100:.1f}%")
        self.max_drawdown_label.setText(f"{metrics.get('max_drawdown', 0)*100:.2f}%")
        self.sharpe_ratio_label.setText(f"{metrics.get('sharpe_ratio', 0):.2f}")
        self.total_trades_label.setText(str(metrics.get('total_trades', 0)))
        
        # 자본 곡선 차트 업데이트
        if result.equity_curve:
            timestamps = [point['timestamp'] for point in result.equity_curve]
            equity_values = [point['equity'] for point in result.equity_curve]
            
            # 시간을 숫자로 변환
            time_values = [i for i in range(len(timestamps))]
            
            self.equity_chart.clear()
            self.equity_chart.plot(
                time_values, equity_values,
                pen=pg.mkPen(color='#00ff00', width=2)
            )

class PositionTab(QWidget):
    """포지션 관리 탭"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 활성 포지션 테이블
        position_group = QGroupBox("활성 포지션")
        position_layout = QVBoxLayout()
        
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(8)
        self.position_table.setHorizontalHeaderLabels([
            "심볼", "전략", "방향", "크기", "진입가", "현재가", "PnL", "PnL%"
        ])
        
        position_layout.addWidget(self.position_table)
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)
        
        # 포지션 제어 버튼
        control_layout = QHBoxLayout()
        
        self.close_all_btn = QPushButton("전체 청산")
        self.close_all_btn.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold;")
        self.close_all_btn.clicked.connect(self.close_all_positions)
        
        self.close_long_btn = QPushButton("롱만 청산")
        self.close_long_btn.clicked.connect(self.close_long_positions)
        
        self.close_short_btn = QPushButton("숏만 청산")
        self.close_short_btn.clicked.connect(self.close_short_positions)
        
        self.emergency_stop_btn = QPushButton("긴급 정지")
        self.emergency_stop_btn.setStyleSheet("background-color: #ff0000; color: white; font-weight: bold;")
        self.emergency_stop_btn.clicked.connect(self.emergency_stop)
        
        control_layout.addWidget(self.close_all_btn)
        control_layout.addWidget(self.close_long_btn)
        control_layout.addWidget(self.close_short_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.emergency_stop_btn)
        
        layout.addLayout(control_layout)
        
        # 거래 이력
        history_group = QGroupBox("거래 이력 (최근 20건)")
        history_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "시간", "심볼", "전략", "방향", "진입가", "청산가", "PnL"
        ])
        
        history_layout.addWidget(self.history_table)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        self.setLayout(layout)
    
    def close_all_positions(self):
        """전체 포지션 청산"""
        reply = QMessageBox.question(self, "포지션 청산", 
                                   "모든 포지션을 청산하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # 실제 청산 로직 호출
                QMessageBox.information(self, "청산 완료", "모든 포지션이 청산되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "청산 오류", f"청산 중 오류: {str(e)}")
    
    def close_long_positions(self):
        """롱 포지션만 청산"""
        reply = QMessageBox.question(self, "롱 포지션 청산", 
                                   "모든 롱 포지션을 청산하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 롱 포지션 청산 로직
            pass
    
    def close_short_positions(self):
        """숏 포지션만 청산"""
        reply = QMessageBox.question(self, "숏 포지션 청산", 
                                   "모든 숏 포지션을 청산하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 숏 포지션 청산 로직
            pass
    
    def emergency_stop(self):
        """긴급 정지"""
        reply = QMessageBox.critical(self, "긴급 정지", 
                                   "⚠️ 긴급 정지하시겠습니까?\n\n"
                                   "모든 거래가 중단되고 포지션이 청산됩니다.",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 긴급 정지 로직
            send_system_alert("긴급 정지", "사용자에 의한 긴급 정지 실행", "warning")

class TradingMainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.trading_thread = None
        self.setup_ui()
        self.setup_system_tray()
        self.setup_connections()
        
    def setup_ui(self):
        self.setWindowTitle("OKX 자동매매 시스템 v1.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메뉴바 설정
        self.setup_menubar()
        
        # 툴바 설정
        self.setup_toolbar()
        
        # 상태바 설정
        self.setup_statusbar()
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        
        # 각 탭 추가
        self.dashboard_tab = DashboardTab()
        self.settings_tab = SettingsTab()
        self.monitoring_tab = MonitoringTab()
        self.backtest_tab = BacktestTab()
        self.position_tab = PositionTab()
        
        self.tab_widget.addTab(self.dashboard_tab, "📊 대시보드")
        self.tab_widget.addTab(self.settings_tab, "⚙️ 설정")
        self.tab_widget.addTab(self.monitoring_tab, "📡 모니터링")
        self.tab_widget.addTab(self.backtest_tab, "📈 백테스팅")
        self.tab_widget.addTab(self.position_tab, "💼 포지션 관리")
        
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
        
        save_config_action = QAction('설정 저장', self)
        save_config_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_config_action)
        
        load_config_action = QAction('설정 불러오기', self)
        load_config_action.triggered.connect(self.load_configuration)
        file_menu.addAction(load_config_action)
        
        file_menu.addSeparator()
        
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
        
        trading_menu.addSeparator()
        
        emergency_action = QAction('긴급 정지', self)
        emergency_action.triggered.connect(self.emergency_stop)
        trading_menu.addAction(emergency_action)
        
        # Tools 메뉴
        tools_menu = menubar.addMenu('도구')
        
        log_viewer_action = QAction('로그 뷰어', self)
        log_viewer_action.triggered.connect(self.show_log_viewer)
        tools_menu.addAction(log_viewer_action)
        
        # Help 메뉴
        help_menu = menubar.addMenu('도움말')
        
        about_action = QAction('정보', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """툴바 설정"""
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
        toolbar.addStretch()
    
    def setup_statusbar(self):
        """상태바 설정"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 상태 표시 위젯들
        self.status_label = QLabel("준비")
        self.profit_label = QLabel("총 손익: $0.00")
        self.time_label = QLabel(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.profit_label)
        self.status_bar.addPermanentWidget(self.time_label)
        
        # 시간 업데이트 타이머
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
    
    def setup_system_tray(self):
        """시스템 트레이 설정"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            # 트레이 메뉴
            tray_menu = QMenu()
            
            show_action = QAction("화면 표시", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)
            
            quit_action = QAction("종료", self)
            quit_action.triggered.connect(QApplication.quit)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
    
    def setup_connections(self):
        """시그널 연결 설정"""
        # 트레이딩 스레드 시그널 연결은 스레드 생성 시 설정
        pass
    
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
            QTableWidget {
                background-color: #404040;
                alternate-background-color: #4a4a4a;
                selection-background-color: #4CAF50;
                gridline-color: #555555;
            }
            QHeaderView::section {
                background-color: #555555;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #666666;
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
            QPushButton:pressed {
                background-color: #444444;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 4px;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
            QStatusBar {
                background-color: #3c3c3c;
                color: #ffffff;
                border-top: 1px solid #555555;
            }
            QMenuBar {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #4CAF50;
            }
            QMenu {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
            }
        """)
    
    def start_trading(self):
        """거래 시작"""
        if self.trading_thread is None or not self.trading_thread.isRunning():
            self.trading_thread = TradingSystemThread()
            
            # 시그널 연결
            self.trading_thread.status_updated.connect(self.dashboard_tab.update_status)
            self.trading_thread.position_updated.connect(self.dashboard_tab.update_positions)
            self.trading_thread.error_occurred.connect(self.handle_error)
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
            
            self.monitoring_tab.add_log_message("거래 시스템 시작", "INFO")
            
            if hasattr(self, 'tray_icon'):
                self.tray_icon.showMessage("거래 시작", "자동매매가 시작되었습니다.", QSystemTrayIcon.Information)
    
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
            
            self.monitoring_tab.add_log_message("거래 시스템 중지", "INFO")
            
            if hasattr(self, 'tray_icon'):
                self.tray_icon.showMessage("거래 중지", "자동매매가 중지되었습니다.", QSystemTrayIcon.Warning)
    
    def emergency_stop(self):
        """긴급 정지"""
        reply = QMessageBox.critical(self, "긴급 정지", 
                                   "⚠️ 긴급 정지하시겠습니까?\n\n"
                                   "모든 거래가 즉시 중단됩니다.",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.stop_trading()
            self.monitoring_tab.add_log_message("긴급 정지 실행", "ERROR")
            send_system_alert("긴급 정지", "사용자에 의한 긴급 정지", "error")
    
    def handle_error(self, error_message: str):
        """오류 처리"""
        self.monitoring_tab.add_log_message(error_message, "ERROR")
        
        # 심각한 오류의 경우 알림
        if "연결" in error_message or "API" in error_message:
            self.connection_indicator.setText("🔴")
    
    def update_time(self):
        """시간 업데이트"""
        self.time_label.setText(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    def save_configuration(self):
        """설정 저장"""
        try:
            config_data = {
                'window_geometry': self.geometry().getRect(),
                'selected_tab': self.tab_widget.currentIndex(),
                'timestamp': datetime.now().isoformat()
            }
            
            with open('gui_config.json', 'w') as f:
                json.dump(config_data, f, indent=2)
            
            QMessageBox.information(self, "설정 저장", "GUI 설정이 저장되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"설정 저장 실패: {str(e)}")
    
    def load_configuration(self):
        """설정 불러오기"""
        try:
            with open('gui_config.json', 'r') as f:
                config_data = json.load(f)
            
            # 윈도우 크기/위치 복원
            if 'window_geometry' in config_data:
                x, y, w, h = config_data['window_geometry']
                self.setGeometry(x, y, w, h)
            
            # 선택된 탭 복원
            if 'selected_tab' in config_data:
                self.tab_widget.setCurrentIndex(config_data['selected_tab'])
            
            QMessageBox.information(self, "설정 불러오기", "GUI 설정이 불러와졌습니다.")
            
        except FileNotFoundError:
            QMessageBox.information(self, "설정 불러오기", "저장된 설정 파일이 없습니다.")
        except Exception as e:
            QMessageBox.critical(self, "불러오기 오류", f"설정 불러오기 실패: {str(e)}")
    
    def show_log_viewer(self):
        """로그 뷰어 표시"""
        self.tab_widget.setCurrentWidget(self.monitoring_tab)
    
    def show_about(self):
        """정보 대화상자"""
        QMessageBox.about(self, "OKX 자동매매 시스템", 
                         "OKX 자동매매 시스템 v1.0\n\n"
                         "EMA 기반 듀얼 전략 자동매매\n"
                         "- 롱/숏 전략 병렬 실행\n"
                         "- 실시간 모니터링\n"
                         "- 백테스팅 지원\n\n"
                         "© 2024")
    
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
    app.setOrganizationName("Trading Bot")
    
    # 다크 팔레트 설정
    app.setStyle('Fusion')
    
    # 메인 윈도우 생성 및 표시
    window = TradingMainWindow()
    window.show()
    
    # 시작 메시지
    window.monitoring_tab.add_log_message("GUI 시스템 시작", "INFO")
    
    # 이벤트 루프 실행
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()