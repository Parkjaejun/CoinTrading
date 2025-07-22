# simulation_gui/sim_main_window.py
"""
실시간 라이브 시뮬레이션 전용 GUI
가상 거래 시뮬레이션을 위한 특화된 인터페이스
"""

import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QSplitter, QProgressBar, QSlider,
    QSpinBox, QDoubleSpinBox, QTextEdit, QMessageBox, QStatusBar
)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor

try:
    import pyqtgraph as pg
    pg.setConfigOption('background', '#2b2b2b')
    pg.setConfigOption('foreground', 'w')
except ImportError:
    pg = None

# 프로젝트 모듈들 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.simulation_main import LiveSimulationSystem
from simulation.virtual_order_manager import virtual_order_manager

class SimulationThread(QThread):
    """시뮬레이션 백그라운드 스레드"""
    
    # 시그널 정의
    portfolio_updated = pyqtSignal(dict)
    price_updated = pyqtSignal(str, float)
    trade_executed = pyqtSignal(dict)
    status_updated = pyqtSignal(dict)
    
    def __init__(self, initial_balance: float = 10000.0):
        super().__init__()
        self.simulation_system = LiveSimulationSystem(initial_balance)
        self.is_running = False
        
    def run(self):
        """시뮬레이션 실행"""
        self.is_running = True
        
        # 시뮬레이션 시스템 초기화
        if not self.simulation_system.initialize_system():
            self.status_updated.emit({'error': '시뮬레이션 초기화 실패'})
            return
        
        # WebSocket 시작
        try:
            symbols = ['BTC-USDT-SWAP']  # 기본 심볼
            self.simulation_system.ws_handler.start_ws(symbols)
            self.simulation_system.is_running = True
            self.simulation_system.start_time = datetime.now()
            
            # 상태 업데이트 루프
            while self.is_running:
                try:
                    # 포트폴리오 업데이트
                    portfolio = virtual_order_manager.get_portfolio_summary()
                    self.portfolio_updated.emit(portfolio)
                    
                    # 현재 가격 업데이트
                    for symbol, price in virtual_order_manager.current_prices.items():
                        self.price_updated.emit(symbol, price)
                    
                    # 상태 정보 업데이트
                    status = {
                        'is_running': True,
                        'uptime': datetime.now() - self.simulation_system.start_time,
                        'signals_processed': self.simulation_system.signals_processed
                    }
                    self.status_updated.emit(status)
                    
                    # 1초 대기
                    self.msleep(1000)
                    
                except Exception as e:
                    print(f"시뮬레이션 스레드 오류: {e}")
                    self.msleep(5000)
                    
        except Exception as e:
            self.status_updated.emit({'error': f'시뮬레이션 오류: {str(e)}'})
    
    def stop_simulation(self):
        """시뮬레이션 중지"""
        self.is_running = False
        if hasattr(self, 'simulation_system'):
            self.simulation_system.stop_simulation()

class PortfolioWidget(QWidget):
    """포트폴리오 현황 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 포트폴리오 요약
        summary_group = QGroupBox("💰 포트폴리오 요약")
        summary_layout = QGridLayout()
        
        self.total_value_label = QLabel("$10,000.00")
        self.total_value_label.setFont(QFont("Arial", 18, QFont.Bold))
        
        self.return_label = QLabel("+0.00%")
        self.return_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        self.balance_label = QLabel("현금: $10,000.00")
        self.unrealized_pnl_label = QLabel("미실현: $0.00")
        self.fees_label = QLabel("수수료: $0.00")
        
        summary_layout.addWidget(QLabel("총 자산:"), 0, 0)
        summary_layout.addWidget(self.total_value_label, 0, 1)
        summary_layout.addWidget(QLabel("수익률:"), 1, 0)
        summary_layout.addWidget(self.return_label, 1, 1)
        summary_layout.addWidget(self.balance_label, 2, 0, 1, 2)
        summary_layout.addWidget(self.unrealized_pnl_label, 3, 0, 1, 2)
        summary_layout.addWidget(self.fees_label, 4, 0, 1, 2)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # 활성 포지션
        positions_group = QGroupBox("📊 활성 포지션")
        positions_layout = QVBoxLayout()
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(6)
        self.positions_table.setHorizontalHeaderLabels([
            "심볼", "방향", "크기", "진입가", "현재가", "PnL"
        ])
        self.positions_table.setMaximumHeight(200)
        
        positions_layout.addWidget(self.positions_table)
        positions_group.setLayout(positions_layout)
        layout.addWidget(positions_group)
        
        # 거래 통계
        stats_group = QGroupBox("📈 거래 통계")
        stats_layout = QGridLayout()
        
        self.total_trades_label = QLabel("0회")
        self.win_rate_label = QLabel("0%")
        self.profit_factor_label = QLabel("0.00")
        
        stats_layout.addWidget(QLabel("총 거래:"), 0, 0)
        stats_layout.addWidget(self.total_trades_label, 0, 1)
        stats_layout.addWidget(QLabel("승률:"), 1, 0)
        stats_layout.addWidget(self.win_rate_label, 1, 1)
        stats_layout.addWidget(QLabel("수익 팩터:"), 2, 0)
        stats_layout.addWidget(self.profit_factor_label, 2, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        self.setLayout(layout)
    
    def update_portfolio(self, portfolio: Dict[str, Any]):
        """포트폴리오 업데이트"""
        # 총 자산
        total_value = portfolio.get('total_value', 0)
        self.total_value_label.setText(f"${total_value:,.2f}")
        
        # 수익률
        total_return = portfolio.get('total_return', 0)
        self.return_label.setText(f"{total_return:+.2f}%")
        
        # 색상 설정
        if total_return > 0:
            self.return_label.setStyleSheet("color: #4CAF50;")  # 녹색
        elif total_return < 0:
            self.return_label.setStyleSheet("color: #F44336;")  # 빨간색
        else:
            self.return_label.setStyleSheet("color: #FFFFFF;")  # 흰색
        
        # 기타 정보
        self.balance_label.setText(f"현금: ${portfolio.get('current_balance', 0):,.2f}")
        
        unrealized_pnl = portfolio.get('unrealized_pnl', 0)
        unrealized_color = "#4CAF50" if unrealized_pnl >= 0 else "#F44336"
        self.unrealized_pnl_label.setText(f"미실현: ${unrealized_pnl:+,.2f}")
        self.unrealized_pnl_label.setStyleSheet(f"color: {unrealized_color};")
        
        self.fees_label.setText(f"수수료: ${portfolio.get('total_fees', 0):,.2f}")
        
        # 포지션 테이블 업데이트
        self.update_positions_table(portfolio.get('positions', {}))
    
    def update_positions_table(self, positions: Dict):
        """포지션 테이블 업데이트"""
        self.positions_table.setRowCount(len(positions))
        
        for row, (symbol, position) in enumerate(positions.items()):
            self.positions_table.setItem(row, 0, QTableWidgetItem(symbol))
            self.positions_table.setItem(row, 1, QTableWidgetItem(position.side.upper()))
            self.positions_table.setItem(row, 2, QTableWidgetItem(f"{position.size:.6f}"))
            self.positions_table.setItem(row, 3, QTableWidgetItem(f"${position.entry_price:.2f}"))
            self.positions_table.setItem(row, 4, QTableWidgetItem(f"${position.current_price:.2f}"))
            
            # PnL 색상 설정
            pnl = position.unrealized_pnl
            pnl_item = QTableWidgetItem(f"${pnl:+.2f}")
            if pnl > 0:
                pnl_item.setForeground(QColor("#4CAF50"))
            elif pnl < 0:
                pnl_item.setForeground(QColor("#F44336"))
            self.positions_table.setItem(row, 5, pnl_item)
    
    def update_trade_stats(self, trade_stats: Dict[str, Any]):
        """거래 통계 업데이트"""
        self.total_trades_label.setText(f"{trade_stats.get('total_trades', 0)}회")
        self.win_rate_label.setText(f"{trade_stats.get('win_rate', 0):.1f}%")
        self.profit_factor_label.setText(f"{trade_stats.get('profit_factor', 0):.2f}")

class PriceChartWidget(QWidget):
    """가격 차트 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.price_data = []
        self.time_data = []
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 차트 헤더
        header_layout = QHBoxLayout()
        self.symbol_label = QLabel("BTC-USDT-SWAP")
        self.symbol_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.price_label = QLabel("$0.00")
        self.price_label.setFont(QFont("Arial", 12))
        
        header_layout.addWidget(self.symbol_label)
        header_layout.addStretch()
        header_layout.addWidget(self.price_label)
        
        layout.addLayout(header_layout)
        
        # 차트 (pyqtgraph 사용 가능한 경우)
        if pg is not None:
            self.chart = pg.PlotWidget()
            self.chart.setLabel('left', 'Price ($)')
            self.chart.setLabel('bottom', 'Time')
            self.chart.showGrid(x=True, y=True)
            self.chart.setMinimumHeight(300)
            
            # 가격 라인
            self.price_line = self.chart.plot(pen=pg.mkPen(color='#00ff00', width=2))
            
            layout.addWidget(self.chart)
        else:
            # pyqtgraph가 없는 경우 간단한 텍스트
            no_chart_label = QLabel("차트를 보려면 pyqtgraph를 설치하세요:\npip install pyqtgraph")
            no_chart_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_chart_label)
        
        self.setLayout(layout)
    
    def update_price(self, symbol: str, price: float):
        """가격 업데이트"""
        self.symbol_label.setText(symbol)
        self.price_label.setText(f"${price:,.2f}")
        
        # 차트 데이터 업데이트
        if pg is not None and hasattr(self, 'chart'):
            current_time = time.time()
            
            self.time_data.append(current_time)
            self.price_data.append(price)
            
            # 최근 100개 데이터만 유지
            if len(self.price_data) > 100:
                self.time_data = self.time_data[-100:]
                self.price_data = self.price_data[-100:]
            
            # 차트 업데이트
            if len(self.price_data) > 1:
                self.price_line.setData(self.time_data, self.price_data)

class SimulationControlWidget(QWidget):
    """시뮬레이션 제어 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 제어 버튼
        control_group = QGroupBox("🎮 시뮬레이션 제어")
        control_layout = QGridLayout()
        
        self.start_btn = QPushButton("▶️ 시작")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        
        self.stop_btn = QPushButton("⏹️ 중지")
        self.stop_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 10px;")
        self.stop_btn.setEnabled(False)
        
        self.reset_btn = QPushButton("🔄 리셋")
        self.reset_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 10px;")
        
        control_layout.addWidget(self.start_btn, 0, 0)
        control_layout.addWidget(self.stop_btn, 0, 1)
        control_layout.addWidget(self.reset_btn, 1, 0, 1, 2)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 시뮬레이션 설정
        settings_group = QGroupBox("⚙️ 설정")
        settings_layout = QGridLayout()
        
        self.balance_spin = QDoubleSpinBox()
        self.balance_spin.setRange(1000, 1000000)
        self.balance_spin.setValue(10000)
        self.balance_spin.setPrefix("$")
        
        settings_layout.addWidget(QLabel("초기 자본:"), 0, 0)
        settings_layout.addWidget(self.balance_spin, 0, 1)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 상태 정보
        status_group = QGroupBox("📊 상태")
        status_layout = QGridLayout()
        
        self.status_label = QLabel("준비")
        self.uptime_label = QLabel("운영시간: 00:00:00")
        self.signals_label = QLabel("처리된 신호: 0개")
        
        status_layout.addWidget(QLabel("상태:"), 0, 0)
        status_layout.addWidget(self.status_label, 0, 1)
        status_layout.addWidget(self.uptime_label, 1, 0, 1, 2)
        status_layout.addWidget(self.signals_label, 2, 0, 1, 2)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_status(self, status: Dict[str, Any]):
        """상태 업데이트"""
        if 'error' in status:
            self.status_label.setText(f"오류: {status['error']}")
            self.status_label.setStyleSheet("color: #F44336;")
            return
        
        if status.get('is_running', False):
            self.status_label.setText("🟢 실행 중")
            self.status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.status_label.setText("🔴 중지됨")
            self.status_label.setStyleSheet("color: #F44336;")
        
        # 운영 시간
        uptime = status.get('uptime')
        if uptime:
            self.uptime_label.setText(f"운영시간: {str(uptime).split('.')[0]}")
        
        # 처리된 신호
        signals = status.get('signals_processed', 0)
        self.signals_label.setText(f"처리된 신호: {signals}개")

class TradingLogWidget(QWidget):
    """거래 로그 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 거래 로그
        log_group = QGroupBox("📝 거래 로그")
        log_layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumBlockCount(500)  # 최대 500줄
        self.log_display.setMaximumHeight(200)
        
        log_layout.addWidget(self.log_display)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # 최근 거래
        trades_group = QGroupBox("💼 최근 거래")
        trades_layout = QVBoxLayout()
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(6)
        self.trades_table.setHorizontalHeaderLabels([
            "시간", "심볼", "방향", "가격", "PnL", "사유"
        ])
        self.trades_table.setMaximumHeight(150)
        
        trades_layout.addWidget(self.trades_table)
        trades_group.setLayout(trades_layout)
        layout.addWidget(trades_group)
        
        self.setLayout(layout)
    
    def add_log_message(self, message: str, level: str = "INFO"):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        color = {
            'INFO': 'white',
            'TRADE': '#4CAF50',
            'ERROR': '#F44336',
            'WARNING': '#FF9800'
        }.get(level, 'white')
        
        formatted_message = f"<span style='color: {color}'>[{timestamp}] [{level}] {message}</span>"
        self.log_display.append(formatted_message)
    
    def update_trades(self, trade_history: list):
        """거래 내역 업데이트"""
        recent_trades = trade_history[-10:] if len(trade_history) > 10 else trade_history
        
        self.trades_table.setRowCount(len(recent_trades))
        
        for row, trade in enumerate(recent_trades):
            time_str = trade.get('exit_time', datetime.now()).strftime('%H:%M:%S')
            self.trades_table.setItem(row, 0, QTableWidgetItem(time_str))
            self.trades_table.setItem(row, 1, QTableWidgetItem(trade.get('symbol', '')))
            self.trades_table.setItem(row, 2, QTableWidgetItem(trade.get('side', '').upper()))
            self.trades_table.setItem(row, 3, QTableWidgetItem(f"${trade.get('exit_price', 0):.2f}"))
            
            # PnL 색상 설정
            pnl = trade.get('pnl', 0)
            pnl_item = QTableWidgetItem(f"${pnl:+.2f}")
            if pnl > 0:
                pnl_item.setForeground(QColor("#4CAF50"))
            elif pnl < 0:
                pnl_item.setForeground(QColor("#F44336"))
            self.trades_table.setItem(row, 4, pnl_item)
            
            self.trades_table.setItem(row, 5, QTableWidgetItem(trade.get('close_reason', '')))

class SimulationMainWindow(QMainWindow):
    """시뮬레이션 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.simulation_thread = None
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        self.setWindowTitle("🎮 OKX 실시간 라이브 시뮬레이션")
        self.setGeometry(100, 100, 1400, 900)
        
        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout()
        
        # 왼쪽 패널 (차트 + 로그)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 가격 차트
        self.price_chart = PriceChartWidget()
        left_layout.addWidget(self.price_chart, 2)  # 2/3 크기
        
        # 거래 로그
        self.trading_log = TradingLogWidget()
        left_layout.addWidget(self.trading_log, 1)  # 1/3 크기
        
        # 오른쪽 패널 (제어 + 포트폴리오)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 시뮬레이션 제어
        self.control_widget = SimulationControlWidget()
        right_layout.addWidget(self.control_widget, 1)
        
        # 포트폴리오
        self.portfolio_widget = PortfolioWidget()
        right_layout.addWidget(self.portfolio_widget, 2)
        
        # 스플리터에 패널 추가
        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 400])  # 2:1 비율
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # 상태바
        self.setup_statusbar()
        
        # 스타일 적용
        self.apply_dark_theme()
        
        # 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # 1초마다
    
    def setup_statusbar(self):
        """상태바 설정"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.connection_status = QLabel("🔴 연결 끊어짐")
        self.time_label = QLabel(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.status_bar.addWidget(self.connection_status)
        self.status_bar.addPermanentWidget(self.time_label)
    
    def setup_connections(self):
        """시그널 연결"""
        # 제어 버튼 연결
        self.control_widget.start_btn.clicked.connect(self.start_simulation)
        self.control_widget.stop_btn.clicked.connect(self.stop_simulation)
        self.control_widget.reset_btn.clicked.connect(self.reset_simulation)
    
    def apply_dark_theme(self):
        """다크 테마 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444444;
                border-radius: 8px;
                margin: 8px;
                padding-top: 15px;
                background-color: #2d2d2d;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #333333;
                alternate-background-color: #3a3a3a;
                selection-background-color: #4CAF50;
                gridline-color: #555555;
                border: 1px solid #555555;
            }
            QHeaderView::section {
                background-color: #444444;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #555555;
                font-weight: bold;
            }
            QPushButton {
                background-color: #444444;
                color: #ffffff;
                border: 2px solid #666666;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #555555;
                border: 2px solid #777777;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
            QLabel {
                color: #ffffff;
                padding: 2px;
            }
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QDoubleSpinBox, QSpinBox {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
        """)
    
    def start_simulation(self):
        """시뮬레이션 시작"""
        if self.simulation_thread and self.simulation_thread.isRunning():
            return
        
        initial_balance = self.control_widget.balance_spin.value()
        
        self.simulation_thread = SimulationThread(initial_balance)
        
        # 시그널 연결
        self.simulation_thread.portfolio_updated.connect(self.portfolio_widget.update_portfolio)
        self.simulation_thread.price_updated.connect(self.price_chart.update_price)
        self.simulation_thread.status_updated.connect(self.control_widget.update_status)
        
        # 스레드 시작
        self.simulation_thread.start()
        
        # UI 상태 업데이트
        self.control_widget.start_btn.setEnabled(False)
        self.control_widget.stop_btn.setEnabled(True)
        self.control_widget.balance_spin.setEnabled(False)
        
        self.connection_status.setText("🟢 시뮬레이션 실행 중")
        self.connection_status.setStyleSheet("color: #4CAF50;")
        
        self.trading_log.add_log_message(f"시뮬레이션 시작 - 초기 자본: ${initial_balance:,.2f}", "INFO")
    
    def stop_simulation(self):
        """시뮬레이션 중지"""
        if self.simulation_thread and self.simulation_thread.isRunning():
            self.simulation_thread.stop_simulation()
            self.simulation_thread.wait(5000)  # 5초 대기
        
        # UI 상태 업데이트
        self.control_widget.start_btn.setEnabled(True)
        self.control_widget.stop_btn.setEnabled(False)
        self.control_widget.balance_spin.setEnabled(True)
        
        self.connection_status.setText("🔴 시뮬레이션 중지됨")
        self.connection_status.setStyleSheet("color: #F44336;")
        
        self.trading_log.add_log_message("시뮬레이션 중지", "INFO")
    
    def reset_simulation(self):
        """시뮬레이션 리셋"""
        reply = QMessageBox.question(self, "시뮬레이션 리셋", 
                                   "시뮬레이션을 초기 상태로 리셋하시겠습니까?\n"
                                   "모든 거래 기록이 삭제됩니다.",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 시뮬레이션 중지
            self.stop_simulation()
            
            # 가상 주문 매니저 리셋
            global virtual_order_manager
            initial_balance = self.control_widget.balance_spin.value()
            virtual_order_manager.__init__(initial_balance)
            
            # 포트폴리오 위젯 리셋
            portfolio = virtual_order_manager.get_portfolio_summary()
            self.portfolio_widget.update_portfolio(portfolio)
            
            self.trading_log.add_log_message("시뮬레이션 리셋 완료", "INFO")
    
    def update_display(self):
        """주기적 디스플레이 업데이트"""
        # 시간 업데이트
        self.time_label.setText(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # 거래 통계 업데이트 (시뮬레이션 실행 중일 때만)
        if self.simulation_thread and self.simulation_thread.isRunning():
            trade_stats = virtual_order_manager.get_trade_summary()
            self.portfolio_widget.update_trade_stats(trade_stats)
            
            # 거래 내역 업데이트
            self.trading_log.update_trades(virtual_order_manager.trade_history)
    
    def closeEvent(self, event):
        """창 종료 이벤트"""
        if self.simulation_thread and self.simulation_thread.isRunning():
            reply = QMessageBox.question(self, "종료 확인", 
                                       "시뮬레이션이 실행 중입니다. 종료하시겠습니까?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.stop_simulation()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    app.setApplicationName("OKX 실시간 라이브 시뮬레이션")
    app.setStyle('Fusion')
    
    # 메인 윈도우 생성 및 표시
    window = SimulationMainWindow()
    window.show()
    
    # 이벤트 루프 실행
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()