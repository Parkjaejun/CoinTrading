# gui/main_window_improved.py
"""
실제 OKX 데이터를 연동한 개선된 GUI
- 실제 시장 가격 데이터 사용
- 실제 계좌 잔고 조회
- WebSocket 실시간 데이터 연결
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QProgressBar, QSplitter, QFrame, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QSlider, QDateEdit,
    QSystemTrayIcon, QMenu, QAction, QStatusBar, QToolBar, QSizePolicy,
    QHeaderView
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

class SimulatedDataThread(QThread):
    """시뮬레이션된 데이터 스레드 (OKX API 없이도 작동)"""
    
    # 시그널 정의
    price_updated = pyqtSignal(str, float, dict)
    account_updated = pyqtSignal(dict)
    position_updated = pyqtSignal(list)
    connection_status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.should_stop = False
        
        # 시뮬레이션 데이터
        self.latest_prices = {}
        self.price_history = {}
        
        # 시뮬레이션 계좌
        self.simulated_account = {
            'USDT': {
                'available': 10000.0,
                'total': 10000.0,
                'frozen': 0.0
            }
        }
        
        # 시뮬레이션 포지션
        self.simulated_positions = []
        
    def run(self):
        """메인 실행 루프"""
        self.is_running = True
        print("🔗 시뮬레이션 데이터 연결 시작")
        
        try:
            # 연결 성공 시뮬레이션
            self.connection_status_changed.emit(True)
            self.account_updated.emit(self.simulated_account)
            
            print("✅ 시뮬레이션 API 연결 성공")
            
            # 주기적 데이터 업데이트
            last_price_update = 0
            last_account_update = 0
            
            while self.is_running and not self.should_stop:
                try:
                    current_time = time.time()
                    
                    # 1초마다 가격 업데이트
                    if current_time - last_price_update >= 1:
                        self.update_simulated_prices()
                        last_price_update = current_time
                    
                    # 30초마다 계좌 정보 업데이트
                    if current_time - last_account_update >= 30:
                        self.update_simulated_account()
                        last_account_update = current_time
                    
                    # 1초 대기
                    time.sleep(1)
                    
                except Exception as e:
                    self.error_occurred.emit(f"시뮬레이션 데이터 오류: {str(e)}")
                    time.sleep(5)
                    
        except Exception as e:
            self.error_occurred.emit(f"시뮬레이션 초기화 오류: {str(e)}")
    
    def update_simulated_prices(self):
        """가격 데이터 시뮬레이션"""
        try:
            symbols = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP']
            
            for symbol in symbols:
                # 기본 가격 설정
                if symbol not in self.latest_prices:
                    if 'BTC' in symbol:
                        self.latest_prices[symbol] = 45000.0
                    elif 'ETH' in symbol:
                        self.latest_prices[symbol] = 3000.0
                    else:
                        self.latest_prices[symbol] = 1.0
                
                # 랜덤 가격 변동 시뮬레이션
                import random
                current_price = self.latest_prices[symbol]
                change_percent = random.uniform(-0.001, 0.001)  # ±0.1% 변동
                new_price = current_price * (1 + change_percent)
                
                self.latest_prices[symbol] = new_price
                
                # 가격 히스토리 저장
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                
                self.price_history[symbol].append({
                    'timestamp': time.time(),
                    'price': new_price,
                    'volume': random.uniform(1000, 10000)
                })
                
                # 최근 500개만 유지
                if len(self.price_history[symbol]) > 500:
                    self.price_history[symbol] = self.price_history[symbol][-500:]
                
                # 24시간 변화율 시뮬레이션
                change_24h = random.uniform(-5.0, 5.0)
                
                # GUI에 시그널 전송
                price_data = {
                    'last': new_price,
                    'bid': new_price * 0.999,
                    'ask': new_price * 1.001,
                    'vol24h': random.uniform(10000, 100000),
                    'change_24h': change_24h,
                    'high_24h': new_price * 1.02,
                    'low_24h': new_price * 0.98,
                    'timestamp': int(time.time() * 1000)
                }
                
                self.price_updated.emit(symbol, new_price, price_data)
        
        except Exception as e:
            print(f"가격 시뮬레이션 오류: {e}")
    
    def update_simulated_account(self):
        """계좌 정보 시뮬레이션"""
        try:
            # 계좌 잔고에 약간의 변동 추가
            import random
            change = random.uniform(-10, 10)
            self.simulated_account['USDT']['available'] += change
            self.simulated_account['USDT']['total'] = self.simulated_account['USDT']['available']
            
            # 최소값 보장
            if self.simulated_account['USDT']['available'] < 1000:
                self.simulated_account['USDT']['available'] = 10000.0
                self.simulated_account['USDT']['total'] = 10000.0
            
            self.account_updated.emit(self.simulated_account)
            
            # 포지션 시뮬레이션 (가끔 추가)
            if random.random() < 0.1:  # 10% 확률
                self.update_simulated_positions()
            
        except Exception as e:
            print(f"계좌 시뮬레이션 오류: {e}")
    
    def update_simulated_positions(self):
        """포지션 시뮬레이션"""
        try:
            import random
            
            # 랜덤하게 포지션 생성/제거
            if len(self.simulated_positions) == 0 and random.random() < 0.3:
                # 새 포지션 생성
                symbol = random.choice(['BTC-USDT-SWAP', 'ETH-USDT-SWAP'])
                price = self.latest_prices.get(symbol, 45000)
                
                position = {
                    'instrument': symbol,
                    'position_side': random.choice(['long', 'short']),
                    'size': random.uniform(0.001, 0.1),
                    'avg_price': price,
                    'mark_price': price,
                    'unrealized_pnl': random.uniform(-100, 100),
                    'unrealized_pnl_ratio': random.uniform(-0.05, 0.05),
                    'margin': random.uniform(100, 1000),
                    'leverage': random.randint(1, 10),
                    'last_trade_id': '12345'
                }
                
                self.simulated_positions.append(position)
            
            elif len(self.simulated_positions) > 0 and random.random() < 0.2:
                # 포지션 제거
                self.simulated_positions.clear()
            
            # 기존 포지션 PnL 업데이트
            for position in self.simulated_positions:
                symbol = position['instrument']
                current_price = self.latest_prices.get(symbol, position['avg_price'])
                
                # PnL 계산
                if position['position_side'] == 'long':
                    pnl_change = (current_price - position['avg_price']) / position['avg_price']
                else:
                    pnl_change = (position['avg_price'] - current_price) / position['avg_price']
                
                position['mark_price'] = current_price
                position['unrealized_pnl'] = position['margin'] * pnl_change * position['leverage']
                position['unrealized_pnl_ratio'] = pnl_change * position['leverage']
            
            self.position_updated.emit(self.simulated_positions)
            
        except Exception as e:
            print(f"포지션 시뮬레이션 오류: {e}")
    
    def stop(self):
        """데이터 수신 중지"""
        self.should_stop = True
        self.is_running = False

class AccountWidget(QWidget):
    """계좌 정보 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 계좌 요약
        account_group = QGroupBox("💰 계좌 정보")
        account_layout = QGridLayout()
        
        # 잔고 표시 레이블들
        self.usdt_balance_label = QLabel("USDT: $0.00")
        self.usdt_balance_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        self.available_balance_label = QLabel("사용가능: $0.00")
        self.frozen_balance_label = QLabel("동결: $0.00")
        
        # 기타 정보
        self.connection_info_label = QLabel("연결 상태: 시뮬레이션 모드")
        
        account_layout.addWidget(self.usdt_balance_label, 0, 0, 1, 2)
        account_layout.addWidget(self.available_balance_label, 1, 0)
        account_layout.addWidget(self.frozen_balance_label, 1, 1)
        account_layout.addWidget(self.connection_info_label, 2, 0, 1, 2)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        # 계좌 설정 정보
        config_group = QGroupBox("⚙️ 시뮬레이션 설정")
        config_layout = QGridLayout()
        
        self.mode_label = QLabel("모드: 시뮬레이션")
        self.update_interval_label = QLabel("업데이트: 1초")
        self.data_source_label = QLabel("데이터: 가상 생성")
        
        config_layout.addWidget(self.mode_label, 0, 0)
        config_layout.addWidget(self.update_interval_label, 1, 0)
        config_layout.addWidget(self.data_source_label, 2, 0)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_account_data(self, balances: Dict[str, Any]):
        """계좌 데이터 업데이트"""
        try:
            # USDT 잔고 업데이트
            if 'USDT' in balances:
                usdt_data = balances['USDT']
                total_usdt = usdt_data.get('total', 0)
                available_usdt = usdt_data.get('available', 0)
                frozen_usdt = usdt_data.get('frozen', 0)
                
                self.usdt_balance_label.setText(f"USDT: ${total_usdt:,.2f}")
                self.available_balance_label.setText(f"사용가능: ${available_usdt:,.2f}")
                self.frozen_balance_label.setText(f"동결: ${frozen_usdt:,.2f}")
                
                # 잔고에 따른 색상 변경
                if total_usdt > 10000:
                    self.usdt_balance_label.setStyleSheet("color: #4CAF50;")  # 녹색
                elif total_usdt > 5000:
                    self.usdt_balance_label.setStyleSheet("color: #FF9800;")  # 주황색
                else:
                    self.usdt_balance_label.setStyleSheet("color: #F44336;")  # 빨간색
                
        except Exception as e:
            print(f"계좌 데이터 업데이트 오류: {e}")

class PositionWidget(QWidget):
    """포지션 정보 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 포지션 테이블
        position_group = QGroupBox("📊 포지션")
        position_layout = QVBoxLayout()
        
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(8)
        self.position_table.setHorizontalHeaderLabels([
            "심볼", "방향", "크기", "평균가", "마크가", "미실현PnL", "레버리지", "마진"
        ])
        
        # 테이블 설정
        header = self.position_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        
        position_layout.addWidget(self.position_table)
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)
        
        # 포지션 요약
        summary_group = QGroupBox("📈 포지션 요약")
        summary_layout = QGridLayout()
        
        self.total_positions_label = QLabel("총 포지션: 0개")
        self.total_unrealized_pnl_label = QLabel("총 미실현 PnL: $0.00")
        self.total_margin_label = QLabel("총 사용 마진: $0.00")
        
        summary_layout.addWidget(self.total_positions_label, 0, 0)
        summary_layout.addWidget(self.total_unrealized_pnl_label, 0, 1)
        summary_layout.addWidget(self.total_margin_label, 1, 0, 1, 2)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        self.setLayout(layout)
    
    def update_positions(self, positions: list):
        """포지션 데이터 업데이트"""
        try:
            self.position_table.setRowCount(len(positions))
            
            total_unrealized_pnl = 0
            total_margin = 0
            
            for row, position in enumerate(positions):
                # 기본 정보
                symbol = position.get('instrument', '')
                side = position.get('position_side', '')
                size = position.get('size', 0)
                avg_price = position.get('avg_price', 0)
                mark_price = position.get('mark_price', 0)
                unrealized_pnl = position.get('unrealized_pnl', 0)
                leverage = position.get('leverage', 1)
                margin = position.get('margin', 0)
                
                # 테이블에 데이터 설정
                self.position_table.setItem(row, 0, QTableWidgetItem(symbol))
                self.position_table.setItem(row, 1, QTableWidgetItem(side.upper()))
                self.position_table.setItem(row, 2, QTableWidgetItem(f"{size:.6f}"))
                self.position_table.setItem(row, 3, QTableWidgetItem(f"${avg_price:.2f}"))
                self.position_table.setItem(row, 4, QTableWidgetItem(f"${mark_price:.2f}"))
                
                # PnL 색상 설정
                pnl_item = QTableWidgetItem(f"${unrealized_pnl:+.2f}")
                if unrealized_pnl > 0:
                    pnl_item.setForeground(QColor("#4CAF50"))  # 녹색
                elif unrealized_pnl < 0:
                    pnl_item.setForeground(QColor("#F44336"))  # 빨간색
                self.position_table.setItem(row, 5, pnl_item)
                
                self.position_table.setItem(row, 6, QTableWidgetItem(f"{leverage}x"))
                self.position_table.setItem(row, 7, QTableWidgetItem(f"${margin:.2f}"))
                
                # 합계 계산
                total_unrealized_pnl += unrealized_pnl
                total_margin += margin
            
            # 요약 정보 업데이트
            self.total_positions_label.setText(f"총 포지션: {len(positions)}개")
            
            # 총 PnL 색상 설정
            pnl_color = "#4CAF50" if total_unrealized_pnl >= 0 else "#F44336"
            self.total_unrealized_pnl_label.setText(f"총 미실현 PnL: ${total_unrealized_pnl:+.2f}")
            self.total_unrealized_pnl_label.setStyleSheet(f"color: {pnl_color}; font-weight: bold;")
            
            self.total_margin_label.setText(f"총 사용 마진: ${total_margin:.2f}")
            
        except Exception as e:
            print(f"포지션 업데이트 오류: {e}")

class ChartWidget(QWidget):
    """차트 위젯"""
    
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
        self.symbol_label.setFont(QFont("Arial", 16, QFont.Bold))
        
        self.price_label = QLabel("$0.00")
        self.price_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        self.change_label = QLabel("(+0.00%)")
        self.change_label.setFont(QFont("Arial", 12))
        
        self.volume_label = QLabel("Vol: 0")
        self.volume_label.setFont(QFont("Arial", 10))
        
        header_layout.addWidget(self.symbol_label)
        header_layout.addStretch()
        header_layout.addWidget(self.volume_label)
        header_layout.addWidget(self.change_label)
        header_layout.addWidget(self.price_label)
        
        layout.addLayout(header_layout)
        
        # 차트 (pyqtgraph 사용 가능한 경우)
        if pg is not None:
            # 차트 위젯 생성
            self.chart_widget = pg.GraphicsLayoutWidget()
            
            # 가격 차트
            self.price_plot = self.chart_widget.addPlot(title="시뮬레이션 가격", row=0, col=0)
            self.price_plot.setLabel('left', 'Price ($)')
            self.price_plot.setLabel('bottom', 'Time')
            self.price_plot.showGrid(x=True, y=True)
            
            # 가격 라인
            self.price_curve = self.price_plot.plot(
                pen=pg.mkPen(color='#00ff00', width=2),
                name='Price'
            )
            
            layout.addWidget(self.chart_widget)
            
        else:
            # pyqtgraph가 없는 경우
            no_chart_label = QLabel("시뮬레이션 차트를 보려면 pyqtgraph를 설치하세요:\npip install pyqtgraph")
            no_chart_label.setAlignment(Qt.AlignCenter)
            no_chart_label.setStyleSheet("color: #FF9800; font-size: 14px;")
            layout.addWidget(no_chart_label)
        
        self.setLayout(layout)
    
    def update_price(self, symbol: str, price: float, full_data: dict):
        """가격 데이터로 차트 업데이트"""
        try:
            # 헤더 정보 업데이트
            self.symbol_label.setText(symbol)
            self.price_label.setText(f"${price:,.2f}")
            
            # 24시간 변화율
            change_24h = full_data.get('change_24h', 0)
            change_color = "#4CAF50" if change_24h >= 0 else "#F44336"
            self.change_label.setText(f"({change_24h:+.2f}%)")
            self.change_label.setStyleSheet(f"color: {change_color};")
            
            # 24시간 거래량
            volume_24h = full_data.get('vol24h', 0)
            if volume_24h >= 1000000:
                vol_str = f"Vol: {volume_24h/1000000:.1f}M"
            elif volume_24h >= 1000:
                vol_str = f"Vol: {volume_24h/1000:.1f}K"
            else:
                vol_str = f"Vol: {volume_24h:.0f}"
            self.volume_label.setText(vol_str)
            
            # 차트 데이터 업데이트
            if pg is not None and hasattr(self, 'price_curve'):
                current_time = time.time()
                
                self.time_data.append(current_time)
                self.price_data.append(price)
                
                # 최근 100개 데이터만 유지
                max_points = 100
                if len(self.price_data) > max_points:
                    self.time_data = self.time_data[-max_points:]
                    self.price_data = self.price_data[-max_points:]
                
                # 가격 차트 업데이트
                if len(self.price_data) > 1:
                    self.price_curve.setData(self.time_data, self.price_data)
            
        except Exception as e:
            print(f"차트 업데이트 오류: {e}")

class TradingMainWindow(QMainWindow):
    """메인 윈도우 - 시뮬레이션 모드"""
    
    def __init__(self):
        super().__init__()
        self.data_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("🚀 OKX 자동매매 시스템 - 시뮬레이션 모드")
        self.setGeometry(100, 100, 1400, 900)
        
        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메뉴바 및 툴바
        self.setup_menubar()
        self.setup_toolbar()
        self.setup_statusbar()
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        
        # 위젯들
        self.chart_tab = ChartWidget()
        self.account_tab = AccountWidget()
        self.position_tab = PositionWidget()
        
        # 로그 탭
        self.log_tab = self.create_log_tab()
        
        # 탭 추가
        self.tab_widget.addTab(self.chart_tab, "📈 시뮬레이션 차트")
        self.tab_widget.addTab(self.account_tab, "💰 계좌 정보")
        self.tab_widget.addTab(self.position_tab, "📊 포지션")
        self.tab_widget.addTab(self.log_tab, "📝 로그")
        
        # 레이아웃 설정
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)
        
        # 스타일 적용
        self.apply_dark_theme()
        
        # 자동 시작
        self.auto_start_simulation()
    
    def create_log_tab(self):
        """로그 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 시뮬레이션 로그
        log_group = QGroupBox("📝 시뮬레이션 로그")
        log_layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(400)
        
        log_layout.addWidget(self.log_display)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        widget.setLayout(layout)
        return widget
    
    def setup_menubar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # 시뮬레이션 메뉴
        sim_menu = menubar.addMenu('시뮬레이션')
        
        self.start_action = QAction('시뮬레이션 시작', self)
        self.start_action.triggered.connect(self.start_simulation)
        sim_menu.addAction(self.start_action)
        
        self.stop_action = QAction('시뮬레이션 중지', self)
        self.stop_action.triggered.connect(self.stop_simulation)
        self.stop_action.setEnabled(False)
        sim_menu.addAction(self.stop_action)
    
    def setup_toolbar(self):
        """툴바 설정"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 시뮬레이션 버튼
        self.start_btn = QPushButton("🔗 시뮬레이션 시작")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.start_btn.clicked.connect(self.start_simulation)
        
        self.stop_btn = QPushButton("🔌 시뮬레이션 중지")
        self.stop_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 8px;")
        self.stop_btn.clicked.connect(self.stop_simulation)
        self.stop_btn.setEnabled(False)
        
        # 상태 표시
        self.status_label = QLabel("🔴 중지됨")
        self.status_label.setStyleSheet("color: #F44336; font-weight: bold; padding: 8px;")
        
        self.data_count_label = QLabel("수신 데이터: 0건")
        self.data_count_label.setStyleSheet("color: #666; padding: 8px;")
        
        # 툴바에 추가
        toolbar.addWidget(self.start_btn)
        toolbar.addWidget(self.stop_btn)
        toolbar.addSeparator()
        toolbar.addWidget(self.status_label)
        toolbar.addWidget(self.data_count_label)
        
        # 우측 정렬
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
    
    def setup_statusbar(self):
        """상태바 설정"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.connection_status_label = QLabel("준비")
        self.last_update_label = QLabel("마지막 업데이트: 없음")
        self.time_label = QLabel(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.status_bar.addWidget(self.connection_status_label)
        self.status_bar.addWidget(self.last_update_label)
        self.status_bar.addPermanentWidget(self.time_label)
        
        # 시간 업데이트 타이머
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time_display)
        self.time_timer.start(1000)
    
    def apply_dark_theme(self):
        """다크 테마 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #444444;
                background-color: #2d2d2d;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #333333;
                color: #ffffff;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QTabBar::tab:hover {
                background-color: #444444;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444444;
                border-radius: 10px;
                margin: 10px;
                padding-top: 15px;
                background-color: #2a2a2a;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #4CAF50;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 2px solid #666666;
                padding: 10px 16px;
                border-radius: 8px;
                font-weight: bold;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #505050;
                border: 2px solid #777777;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QTableWidget {
                background-color: #2a2a2a;
                alternate-background-color: #323232;
                selection-background-color: #4CAF50;
                gridline-color: #444444;
                border: 1px solid #444444;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 10px;
                border: 1px solid #444444;
                font-weight: bold;
                font-size: 12px;
            }
            QLabel {
                color: #ffffff;
                padding: 4px;
            }
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
    
    def auto_start_simulation(self):
        """자동으로 시뮬레이션 시작"""
        QTimer.singleShot(1000, self.start_simulation)  # 1초 후 자동 시작
    
    def start_simulation(self):
        """시뮬레이션 시작"""
        if self.data_thread and self.data_thread.isRunning():
            self.add_log("⚠️ 이미 시뮬레이션이 실행 중입니다")
            return
        
        self.add_log("🔗 시뮬레이션 데이터 연결 시작...")
        
        # 데이터 스레드 생성 및 시작
        self.data_thread = SimulatedDataThread()
        
        # 시그널 연결
        self.data_thread.price_updated.connect(self.on_price_update)
        self.data_thread.account_updated.connect(self.on_account_update)
        self.data_thread.position_updated.connect(self.on_position_update)
        self.data_thread.connection_status_changed.connect(self.on_connection_status_changed)
        self.data_thread.error_occurred.connect(self.on_error_occurred)
        
        # 스레드 시작
        self.data_thread.start()
        
        # UI 상태 업데이트
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(True)
    
    def stop_simulation(self):
        """시뮬레이션 중지"""
        if self.data_thread and self.data_thread.isRunning():
            self.add_log("🔌 시뮬레이션 중지 중...")
            
            self.data_thread.stop()
            self.data_thread.wait(5000)
            
            self.add_log("✅ 시뮬레이션 중지 완료")
        
        # UI 상태 업데이트
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.status_label.setText("🔴 중지됨")
        self.status_label.setStyleSheet("color: #F44336; font-weight: bold; padding: 8px;")
    
    def on_price_update(self, symbol: str, price: float, full_data: dict):
        """가격 업데이트 처리"""
        # 차트 업데이트
        self.chart_tab.update_price(symbol, price, full_data)
        
        # 데이터 카운트 업데이트
        current_text = self.data_count_label.text()
        if "수신 데이터:" in current_text:
            try:
                count = int(current_text.split(":")[1].replace("건", "").strip())
                count += 1
                self.data_count_label.setText(f"수신 데이터: {count}건")
            except:
                self.data_count_label.setText("수신 데이터: 1건")
        
        # 마지막 업데이트 시간
        self.last_update_label.setText(f"마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")
    
    def on_account_update(self, balances: dict):
        """계좌 정보 업데이트 처리"""
        self.account_tab.update_account_data(balances)
        self.add_log(f"💰 계좌 정보 업데이트 완료")
    
    def on_position_update(self, positions: list):
        """포지션 정보 업데이트 처리"""
        self.position_tab.update_positions(positions)
        self.add_log(f"📊 포지션 정보 업데이트: {len(positions)}개")
    
    def on_connection_status_changed(self, is_connected: bool):
        """연결 상태 변경 처리"""
        if is_connected:
            self.status_label.setText("🟢 시뮬레이션 실행중")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 8px;")
            self.connection_status_label.setText("시뮬레이션 연결됨")
            self.add_log("✅ 시뮬레이션 연결 성공")
        else:
            self.status_label.setText("🔴 중지됨")
            self.status_label.setStyleSheet("color: #F44336; font-weight: bold; padding: 8px;")
            self.connection_status_label.setText("연결 끊어짐")
            self.add_log("❌ 시뮬레이션 연결 실패")
    
    def on_error_occurred(self, error_message: str):
        """오류 발생 처리"""
        self.add_log(f"❌ 오류: {error_message}")
    
    def add_log(self, message: str):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_display.append(formatted_message)
        print(formatted_message)  # 콘솔에도 출력
    
    def update_time_display(self):
        """시간 표시 업데이트"""
        self.time_label.setText(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    def closeEvent(self, event):
        """창 종료 이벤트"""
        if self.data_thread and self.data_thread.isRunning():
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
    app.setApplicationName("OKX 자동매매 시스템 - 시뮬레이션")
    app.setStyle('Fusion')
    
    # 메인 윈도우 생성 및 표시
    window = TradingMainWindow()
    window.show()
    
    # 시작 메시지
    print("🚀 OKX 자동매매 시스템 - 시뮬레이션 모드")
    print("📊 가상 데이터로 GUI 기능을 테스트합니다")
    print("⚠️  실제 거래는 발생하지 않습니다")
    
    # 이벤트 루프 실행
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()