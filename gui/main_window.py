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

try:
    from config import (
        API_KEY, API_SECRET, PASSPHRASE, TRADING_CONFIG, 
        LONG_STRATEGY_CONFIG, SHORT_STRATEGY_CONFIG, NOTIFICATION_CONFIG
    )
    from okx.account_manager import AccountManager
    from okx.websocket_handler import WebSocketHandler
    from okx.connection_manager import connection_manager
    from utils.logger import log_system, log_error
    from utils.data_loader import historical_loader
except ImportError as e:
    print(f"모듈 임포트 오류: {e}")

class RealDataThread(QThread):
    """실제 OKX 데이터 수신 스레드"""
    
    # 시그널 정의
    price_updated = pyqtSignal(str, float, dict)  # symbol, price, full_data
    account_updated = pyqtSignal(dict)  # 계좌 정보
    position_updated = pyqtSignal(list)  # 포지션 정보
    connection_status_changed = pyqtSignal(bool)  # 연결 상태
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.should_stop = False
        
        # OKX 연결 관리
        self.account_manager = None
        self.ws_handler = None
        
        # 데이터 저장
        self.latest_prices = {}
        self.price_history = {}
        
    def run(self):
        """메인 실행 루프"""
        self.is_running = True
        print("🔗 실제 OKX 데이터 연결 시작")
        
        try:
            # API 연결 테스트
            self.account_manager = AccountManager()
            
            # 계좌 정보 조회 테스트
            balances = self.account_manager.get_account_balance()
            if balances:
                self.connection_status_changed.emit(True)
                self.account_updated.emit(balances)
                print("✅ OKX API 연결 성공")
            else:
                self.error_occurred.emit("API 연결 실패")
                return
            
            # WebSocket 연결 (실제 데이터)
            self.ws_handler = RealWebSocketHandler()
            self.ws_handler.price_updated.connect(self.on_price_update)
            
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            self.ws_handler.start_real_websocket(symbols)
            
            # 주기적 계좌 정보 업데이트
            last_account_update = 0
            last_position_update = 0
            
            while self.is_running and not self.should_stop:
                try:
                    current_time = time.time()
                    
                    # 30초마다 계좌 정보 업데이트
                    if current_time - last_account_update >= 30:
                        self.update_account_info()
                        last_account_update = current_time
                    
                    # 10초마다 포지션 정보 업데이트
                    if current_time - last_position_update >= 10:
                        self.update_position_info()
                        last_position_update = current_time
                    
                    # 1초 대기
                    time.sleep(1)
                    
                except Exception as e:
                    self.error_occurred.emit(f"데이터 수신 오류: {str(e)}")
                    time.sleep(5)
                    
        except Exception as e:
            self.error_occurred.emit(f"초기화 오류: {str(e)}")
    
    def on_price_update(self, symbol: str, price_data: dict):
        """실시간 가격 업데이트"""
        try:
            price = float(price_data.get('last', 0))
            
            if price > 0:
                self.latest_prices[symbol] = price
                
                # 가격 히스토리 저장
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                
                self.price_history[symbol].append({
                    'timestamp': time.time(),
                    'price': price,
                    'volume': float(price_data.get('vol24h', 0))
                })
                
                # 최근 500개만 유지
                if len(self.price_history[symbol]) > 500:
                    self.price_history[symbol] = self.price_history[symbol][-500:]
                
                # GUI에 시그널 전송
                self.price_updated.emit(symbol, price, price_data)
        
        except Exception as e:
            print(f"가격 업데이트 오류: {e}")
    
    def update_account_info(self):
        """계좌 정보 업데이트"""
        try:
            if self.account_manager:
                balances = self.account_manager.get_account_balance()
                if balances:
                    self.account_updated.emit(balances)
        except Exception as e:
            print(f"계좌 정보 업데이트 오류: {e}")
    
    def update_position_info(self):
        """포지션 정보 업데이트"""
        try:
            if self.account_manager:
                positions = self.account_manager.get_positions()
                self.position_updated.emit(positions)
        except Exception as e:
            print(f"포지션 정보 업데이트 오류: {e}")
    
    def get_historical_data(self, symbol: str, days: int = 1):
        """과거 데이터 조회"""
        try:
            df = historical_loader.get_historical_candles(symbol, "1m", limit=days*1440)
            if df is not None:
                return df.to_dict('records')
            return []
        except Exception as e:
            print(f"과거 데이터 조회 오류: {e}")
            return []
    
    def stop(self):
        """데이터 수신 중지"""
        self.should_stop = True
        self.is_running = False
        
        if self.ws_handler:
            self.ws_handler.stop_websocket()

class RealWebSocketHandler(QThread):
    """실제 WebSocket 연결 처리"""
    
    price_updated = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self.ws_handler = None
    
    def start_real_websocket(self, symbols):
        """실제 WebSocket 시작"""
        try:
            from okx.websocket_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler()
            
            # 실제 WebSocket 연결
            public_thread, private_thread = self.ws_handler.start_ws(symbols)
            
            # 가격 업데이트 콜백 등록
            self.ws_handler.on_price_callback = self.on_price_data
            
            print("✅ 실제 WebSocket 연결 완료")
            
        except Exception as e:
            print(f"WebSocket 연결 오류: {e}")
    
    def on_price_data(self, symbol: str, data: dict):
        """실시간 가격 데이터 콜백"""
        self.price_updated.emit(symbol, data)
    
    def stop_websocket(self):
        """WebSocket 중지"""
        if self.ws_handler:
            self.ws_handler.stop_ws()

class RealAccountWidget(QWidget):
    """실제 계좌 정보 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 계좌 요약
        account_group = QGroupBox("💰 실제 계좌 정보")
        account_layout = QGridLayout()
        
        # 잔고 표시 레이블들
        self.usdt_balance_label = QLabel("USDT: $0.00")
        self.usdt_balance_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        self.available_balance_label = QLabel("사용가능: $0.00")
        self.frozen_balance_label = QLabel("동결: $0.00")
        
        # 다른 자산 표시
        self.other_assets_label = QLabel("기타 자산: 없음")
        
        account_layout.addWidget(self.usdt_balance_label, 0, 0, 1, 2)
        account_layout.addWidget(self.available_balance_label, 1, 0)
        account_layout.addWidget(self.frozen_balance_label, 1, 1)
        account_layout.addWidget(self.other_assets_label, 2, 0, 1, 2)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        # 계좌 설정 정보
        config_group = QGroupBox("⚙️ 계좌 설정")
        config_layout = QGridLayout()
        
        self.account_level_label = QLabel("계좌 레벨: -")
        self.position_mode_label = QLabel("포지션 모드: -")
        self.margin_mode_label = QLabel("마진 모드: -")
        
        config_layout.addWidget(self.account_level_label, 0, 0)
        config_layout.addWidget(self.position_mode_label, 1, 0)
        config_layout.addWidget(self.margin_mode_label, 2, 0)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # 수수료 정보
        fee_group = QGroupBox("💸 수수료 정보")
        fee_layout = QGridLayout()
        
        self.maker_fee_label = QLabel("Maker: 0.000%")
        self.taker_fee_label = QLabel("Taker: 0.000%")
        
        fee_layout.addWidget(self.maker_fee_label, 0, 0)
        fee_layout.addWidget(self.taker_fee_label, 0, 1)
        
        fee_group.setLayout(fee_layout)
        layout.addWidget(fee_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_account_data(self, balances: Dict[str, Any]):
        """실제 계좌 데이터 업데이트"""
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
                if total_usdt > 1000:
                    self.usdt_balance_label.setStyleSheet("color: #4CAF50;")  # 녹색
                elif total_usdt > 100:
                    self.usdt_balance_label.setStyleSheet("color: #FF9800;")  # 주황색
                else:
                    self.usdt_balance_label.setStyleSheet("color: #F44336;")  # 빨간색
            
            # 기타 자산 표시
            other_assets = []
            for currency, data in balances.items():
                if currency != 'USDT' and data.get('total', 0) > 0:
                    other_assets.append(f"{currency}: {data['total']:.6f}")
            
            if other_assets:
                self.other_assets_label.setText("기타 자산: " + ", ".join(other_assets[:3]))
            else:
                self.other_assets_label.setText("기타 자산: 없음")
                
        except Exception as e:
            print(f"계좌 데이터 업데이트 오류: {e}")
    
    def update_account_config(self, config: Dict[str, Any]):
        """계좌 설정 정보 업데이트"""
        try:
            self.account_level_label.setText(f"계좌 레벨: {config.get('account_level', 'Unknown')}")
            self.position_mode_label.setText(f"포지션 모드: {config.get('position_mode', 'Unknown')}")
            self.margin_mode_label.setText(f"마진 모드: {config.get('margin_mode', 'Unknown')}")
        except Exception as e:
            print(f"계좌 설정 업데이트 오류: {e}")
    
    def update_fee_info(self, fees: Dict[str, float]):
        """수수료 정보 업데이트"""
        try:
            maker_fee = fees.get('maker_fee', 0) * 100
            taker_fee = fees.get('taker_fee', 0) * 100
            
            self.maker_fee_label.setText(f"Maker: {maker_fee:.3f}%")
            self.taker_fee_label.setText(f"Taker: {taker_fee:.3f}%")
        except Exception as e:
            print(f"수수료 정보 업데이트 오류: {e}")

class RealPositionWidget(QWidget):
    """실제 포지션 정보 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 포지션 테이블
        position_group = QGroupBox("📊 실제 포지션")
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
        """실제 포지션 데이터 업데이트"""
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

class RealChartWidget(QWidget):
    """실제 데이터를 사용하는 차트 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.price_data = []
        self.time_data = []
        self.volume_data = []
        
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
        
        # 실제 차트 (pyqtgraph)
        if pg is not None:
            # 차트 위젯 생성
            self.chart_widget = pg.GraphicsLayoutWidget()
            
            # 가격 차트
            self.price_plot = self.chart_widget.addPlot(title="실시간 가격", row=0, col=0)
            self.price_plot.setLabel('left', 'Price ($)')
            self.price_plot.setLabel('bottom', 'Time')
            self.price_plot.showGrid(x=True, y=True)
            
            # 가격 라인
            self.price_curve = self.price_plot.plot(
                pen=pg.mkPen(color='#00ff00', width=2),
                name='Price'
            )
            
            # 볼륨 차트 (하단)
            self.volume_plot = self.chart_widget.addPlot(title="거래량", row=1, col=0)
            self.volume_plot.setLabel('left', 'Volume')
            self.volume_plot.setLabel('bottom', 'Time')
            self.volume_plot.setMaximumHeight(150)
            
            # 볼륨 바
            self.volume_bars = pg.BarGraphItem(
                x=[], height=[], width=0.8, 
                brush=pg.mkBrush(color='#4CAF50')
            )
            self.volume_plot.addItem(self.volume_bars)
            
            layout.addWidget(self.chart_widget)
            
        else:
            # pyqtgraph가 없는 경우
            no_chart_label = QLabel("실시간 차트를 보려면 pyqtgraph를 설치하세요:\npip install pyqtgraph")
            no_chart_label.setAlignment(Qt.AlignCenter)
            no_chart_label.setStyleSheet("color: #FF9800; font-size: 14px;")
            layout.addWidget(no_chart_label)
        
        self.setLayout(layout)
    
    def update_real_price(self, symbol: str, price: float, full_data: dict):
        """실제 가격 데이터로 차트 업데이트"""
        try:
            # 헤더 정보 업데이트
            self.symbol_label.setText(symbol)
            self.price_label.setText(f"${price:,.2f}")
            
            # 24시간 변화율 계산
            change_24h = float(full_data.get('change_24h', '0'))
            change_color = "#4CAF50" if change_24h >= 0 else "#F44336"
            self.change_label.setText(f"({change_24h:+.2f}%)")
            self.change_label.setStyleSheet(f"color: {change_color};")
            
            # 24시간 거래량
            volume_24h = float(full_data.get('vol24h', '0'))
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
                self.volume_data.append(volume_24h)
                
                # 최근 200개 데이터만 유지 (더 많은 히스토리)
                max_points = 200
                if len(self.price_data) > max_points:
                    self.time_data = self.time_data[-max_points:]
                    self.price_data = self.price_data[-max_points:]
                    self.volume_data = self.volume_data[-max_points:]
                
                # 가격 차트 업데이트
                if len(self.price_data) > 1:
                    self.price_curve.setData(self.time_data, self.price_data)
                
                # 볼륨 차트 업데이트
                if len(self.volume_data) > 1:
                    bar_width = (self.time_data[-1] - self.time_data[0]) / len(self.time_data) * 0.8
                    self.volume_bars.setOpts(
                        x=self.time_data,
                        height=self.volume_data,
                        width=bar_width
                    )
            
        except Exception as e:
            print(f"차트 업데이트 오류: {e}")
    
    def load_historical_data(self, symbol: str):
        """과거 데이터 로드하여 차트 초기화"""
        try:
            # 과거 1일 데이터 로드
            df = historical_loader.get_historical_candles(symbol, "5m", limit=288)  # 5분봉 1일
            
            if df is not None and len(df) > 0:
                # 데이터 변환
                timestamps = [dt.timestamp() for dt in df['timestamp']]
                prices = df['close'].tolist()
                volumes = df['volume'].tolist()
                
                # 초기 차트 데이터 설정
                self.time_data = timestamps[-100:]  # 최근 100개
                self.price_data = prices[-100:]
                self.volume_data = volumes[-100:]
                
                # 차트 그리기
                if pg is not None and hasattr(self, 'price_curve'):
                    self.price_curve.setData(self.time_data, self.price_data)
                    
                    if hasattr(self, 'volume_bars'):
                        bar_width = (self.time_data[-1] - self.time_data[0]) / len(self.time_data) * 0.8
                        self.volume_bars.setOpts(
                            x=self.time_data,
                            height=self.volume_data,
                            width=bar_width
                        )
                
                print(f"✅ {symbol} 과거 데이터 로드 완료: {len(df)}개 캔들")
                
        except Exception as e:
            print(f"과거 데이터 로드 오류: {e}")

class ImprovedTradingMainWindow(QMainWindow):
    """개선된 메인 윈도우 - 실제 OKX 데이터 연동"""
    
    def __init__(self):
        super().__init__()
        self.real_data_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("🚀 OKX 자동매매 시스템 v2.0 - 실제 데이터 연동")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메뉴바 및 툴바
        self.setup_menubar()
        self.setup_toolbar()
        self.setup_statusbar()
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        
        # 실제 데이터 위젯들
        self.real_chart_tab = RealChartWidget()
        self.real_account_tab = RealAccountWidget()
        self.real_position_tab = RealPositionWidget()
        
        # 기존 탭들 (개선된 버전)
        self.trading_log_tab = self.create_trading_log_tab()
        self.settings_tab = self.create_settings_tab()
        
        # 탭 추가
        self.tab_widget.addTab(self.real_chart_tab, "📈 실시간 차트")
        self.tab_widget.addTab(self.real_account_tab, "💰 계좌 정보")
        self.tab_widget.addTab(self.real_position_tab, "📊 포지션")
        self.tab_widget.addTab(self.trading_log_tab, "📝 거래 로그")
        self.tab_widget.addTab(self.settings_tab, "⚙️ 설정")
        
        # 레이아웃 설정
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)
        
        # 스타일 적용
        self.apply_improved_theme()
        
        # 자동 시작
        self.auto_start_data_connection()
    
    def setup_menubar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # 연결 메뉴
        connection_menu = menubar.addMenu('연결')
        
        self.connect_action = QAction('실제 데이터 연결', self)
        self.connect_action.triggered.connect(self.start_real_data_connection)
        connection_menu.addAction(self.connect_action)
        
        self.disconnect_action = QAction('연결 해제', self)
        self.disconnect_action.triggered.connect(self.stop_real_data_connection)
        self.disconnect_action.setEnabled(False)
        connection_menu.addAction(self.disconnect_action)
        
        connection_menu.addSeparator()
        
        # 계좌 새로고침
        refresh_account_action = QAction('계좌 새로고침', self)
        refresh_account_action.triggered.connect(self.refresh_account_data)
        connection_menu.addAction(refresh_account_action)
        
        # 포지션 새로고침
        refresh_position_action = QAction('포지션 새로고침', self)
        refresh_position_action.triggered.connect(self.refresh_position_data)
        connection_menu.addAction(refresh_position_action)
        
        # 도구 메뉴
        tools_menu = menubar.addMenu('도구')
        
        # API 연결 테스트
        test_api_action = QAction('API 연결 테스트', self)
        test_api_action.triggered.connect(self.test_api_connection)
        tools_menu.addAction(test_api_action)
        
        # 과거 데이터 로드
        load_history_action = QAction('과거 데이터 로드', self)
        load_history_action.triggered.connect(self.load_historical_data)
        tools_menu.addAction(load_history_action)
    
    def setup_toolbar(self):
        """툴바 설정"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 연결 버튼
        self.connect_btn = QPushButton("🔗 실제 데이터 연결")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.connect_btn.clicked.connect(self.start_real_data_connection)
        
        self.disconnect_btn = QPushButton("🔌 연결 해제")
        self.disconnect_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 8px;")
        self.disconnect_btn.clicked.connect(self.stop_real_data_connection)
        self.disconnect_btn.setEnabled(False)
        
        # 새로고침 버튼
        self.refresh_btn = QPushButton("🔄 새로고침")
        self.refresh_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        self.refresh_btn.clicked.connect(self.refresh_all_data)
        
        # 상태 표시
        self.api_status_label = QLabel("🔴 연결 끊어짐")
        self.api_status_label.setStyleSheet("color: #F44336; font-weight: bold; padding: 8px;")
        
        self.data_count_label = QLabel("수신 데이터: 0건")
        self.data_count_label.setStyleSheet("color: #666; padding: 8px;")
        
        # 툴바에 추가
        toolbar.addWidget(self.connect_btn)
        toolbar.addWidget(self.disconnect_btn)
        toolbar.addSeparator()
        toolbar.addWidget(self.refresh_btn)
        toolbar.addSeparator()
        toolbar.addWidget(self.api_status_label)
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
    
    def create_trading_log_tab(self):
        """거래 로그 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 실시간 로그
        log_group = QGroupBox("📝 실시간 로그")
        log_layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(300)
        
        log_layout.addWidget(self.log_display)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # API 호출 로그
        api_group = QGroupBox("🔗 API 호출 로그")
        api_layout = QVBoxLayout()
        
        self.api_log_display = QTextEdit()
        self.api_log_display.setReadOnly(True)
        self.api_log_display.setMaximumHeight(200)
        
        api_layout.addWidget(self.api_log_display)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_settings_tab(self):
        """설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # API 설정 표시
        api_group = QGroupBox("🔑 API 설정 상태")
        api_layout = QGridLayout()
        
        # API 키 상태 (마스킹)
        api_key_status = "설정됨" if API_KEY and API_KEY != "your_api_key_here" else "미설정"
        api_secret_status = "설정됨" if API_SECRET and API_SECRET != "your_api_secret_here" else "미설정"
        passphrase_status = "설정됨" if PASSPHRASE and PASSPHRASE != "your_passphrase_here" else "미설정"
        
        api_layout.addWidget(QLabel("API Key:"), 0, 0)
        api_layout.addWidget(QLabel(api_key_status), 0, 1)
        api_layout.addWidget(QLabel("API Secret:"), 1, 0)
        api_layout.addWidget(QLabel(api_secret_status), 1, 1)
        api_layout.addWidget(QLabel("Passphrase:"), 2, 0)
        api_layout.addWidget(QLabel(passphrase_status), 2, 1)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 데이터 업데이트 설정
        update_group = QGroupBox("⏱️ 업데이트 설정")
        update_layout = QGridLayout()
        
        self.price_update_interval = QSpinBox()
        self.price_update_interval.setRange(1, 60)
        self.price_update_interval.setValue(1)
        self.price_update_interval.setSuffix("초")
        
        self.account_update_interval = QSpinBox()
        self.account_update_interval.setRange(10, 300)
        self.account_update_interval.setValue(30)
        self.account_update_interval.setSuffix("초")
        
        update_layout.addWidget(QLabel("가격 업데이트:"), 0, 0)
        update_layout.addWidget(self.price_update_interval, 0, 1)
        update_layout.addWidget(QLabel("계좌 업데이트:"), 1, 0)
        update_layout.addWidget(self.account_update_interval, 1, 1)
        
        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def apply_improved_theme(self):
        """개선된 다크 테마 적용"""
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
            QSpinBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px;
            }
        """)
    
    def auto_start_data_connection(self):
        """자동으로 데이터 연결 시작"""
        QTimer.singleShot(1000, self.start_real_data_connection)  # 1초 후 자동 연결
    
    def start_real_data_connection(self):
        """실제 데이터 연결 시작"""
        if self.real_data_thread and self.real_data_thread.isRunning():
            self.add_log("⚠️ 이미 데이터 연결이 실행 중입니다")
            return
        
        self.add_log("🔗 실제 OKX 데이터 연결 시작...")
        
        # 데이터 스레드 생성 및 시작
        self.real_data_thread = RealDataThread()
        
        # 시그널 연결
        self.real_data_thread.price_updated.connect(self.on_price_update)
        self.real_data_thread.account_updated.connect(self.on_account_update)
        self.real_data_thread.position_updated.connect(self.on_position_update)
        self.real_data_thread.connection_status_changed.connect(self.on_connection_status_changed)
        self.real_data_thread.error_occurred.connect(self.on_error_occurred)
        
        # 스레드 시작
        self.real_data_thread.start()
        
        # UI 상태 업데이트
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        
        # 과거 데이터 로드
        QTimer.singleShot(3000, self.load_historical_data)  # 3초 후 과거 데이터 로드
    
    def stop_real_data_connection(self):
        """실제 데이터 연결 중지"""
        if self.real_data_thread and self.real_data_thread.isRunning():
            self.add_log("🔌 데이터 연결 중지 중...")
            
            self.real_data_thread.stop()
            self.real_data_thread.wait(5000)
            
            self.add_log("✅ 데이터 연결 중지 완료")
        
        # UI 상태 업데이트
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.api_status_label.setText("🔴 연결 끊어짐")
        self.api_status_label.setStyleSheet("color: #F44336; font-weight: bold; padding: 8px;")
    
    def on_price_update(self, symbol: str, price: float, full_data: dict):
        """가격 업데이트 처리"""
        # 차트 업데이트
        self.real_chart_tab.update_real_price(symbol, price, full_data)
        
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
        self.real_account_tab.update_account_data(balances)
        self.add_log(f"💰 계좌 정보 업데이트 완료")
        
        # 계좌 설정 및 수수료 정보도 업데이트
        if hasattr(self.real_data_thread, 'account_manager') and self.real_data_thread.account_manager:
            try:
                config = self.real_data_thread.account_manager.get_account_config()
                fees = self.real_data_thread.account_manager.get_trading_fee_rate()
                
                self.real_account_tab.update_account_config(config)
                self.real_account_tab.update_fee_info(fees)
            except Exception as e:
                print(f"계좌 설정/수수료 정보 업데이트 오류: {e}")
    
    def on_position_update(self, positions: list):
        """포지션 정보 업데이트 처리"""
        self.real_position_tab.update_positions(positions)
        self.add_log(f"📊 포지션 정보 업데이트: {len(positions)}개")
    
    def on_connection_status_changed(self, is_connected: bool):
        """연결 상태 변경 처리"""
        if is_connected:
            self.api_status_label.setText("🟢 연결됨")
            self.api_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 8px;")
            self.connection_status_label.setText("실제 데이터 연결됨")
            self.add_log("✅ OKX API 연결 성공")
        else:
            self.api_status_label.setText("🔴 연결 끊어짐")
            self.api_status_label.setStyleSheet("color: #F44336; font-weight: bold; padding: 8px;")
            self.connection_status_label.setText("연결 끊어짐")
            self.add_log("❌ OKX API 연결 실패")
    
    def on_error_occurred(self, error_message: str):
        """오류 발생 처리"""
        self.add_log(f"❌ 오류: {error_message}")
        
        # 심각한 오류인 경우 연결 중지
        if "초기화 오류" in error_message or "API 연결 실패" in error_message:
            QTimer.singleShot(1000, self.stop_real_data_connection)
    
    def refresh_all_data(self):
        """모든 데이터 새로고침"""
        self.add_log("🔄 모든 데이터 새로고침 중...")
        
        if self.real_data_thread and self.real_data_thread.isRunning():
            # 강제로 계좌 및 포지션 정보 업데이트
            self.real_data_thread.update_account_info()
            self.real_data_thread.update_position_info()
        else:
            self.add_log("⚠️ 데이터 연결이 활성화되지 않음")
    
    def refresh_account_data(self):
        """계좌 데이터만 새로고침"""
        if self.real_data_thread and self.real_data_thread.isRunning():
            self.real_data_thread.update_account_info()
            self.add_log("💰 계좌 데이터 새로고침 요청")
    
    def refresh_position_data(self):
        """포지션 데이터만 새로고침"""
        if self.real_data_thread and self.real_data_thread.isRunning():
            self.real_data_thread.update_position_info()
            self.add_log("📊 포지션 데이터 새로고침 요청")
    
    def test_api_connection(self):
        """API 연결 테스트"""
        self.add_log("🧪 API 연결 테스트 시작...")
        
        try:
            test_account = AccountManager()
            balances = test_account.get_account_balance()
            
            if balances:
                self.add_log("✅ API 연결 테스트 성공")
                QMessageBox.information(self, "API 테스트", "✅ API 연결이 정상적으로 작동합니다!")
            else:
                self.add_log("❌ API 연결 테스트 실패")
                QMessageBox.warning(self, "API 테스트", "❌ API 연결에 실패했습니다.\nconfig.py의 API 설정을 확인해주세요.")
                
        except Exception as e:
            error_msg = f"API 테스트 오류: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            QMessageBox.critical(self, "API 테스트", f"❌ {error_msg}")
    
    def load_historical_data(self):
        """과거 데이터 로드"""
        self.add_log("📊 과거 데이터 로딩 중...")
        
        symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
        for symbol in symbols:
            self.real_chart_tab.load_historical_data(symbol)
        
        self.add_log("✅ 과거 데이터 로딩 완료")
    
    def add_log(self, message: str):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_display.append(formatted_message)
        
        # API 관련 로그는 별도 표시
        if any(keyword in message for keyword in ['API', '연결', '계좌', '포지션']):
            self.api_log_display.append(formatted_message)
        
        print(formatted_message)  # 콘솔에도 출력
    
    def update_time_display(self):
        """시간 표시 업데이트"""
        self.time_label.setText(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    def closeEvent(self, event):
        """창 종료 이벤트"""
        if self.real_data_thread and self.real_data_thread.isRunning():
            reply = QMessageBox.question(self, "종료 확인", 
                                       "실제 데이터 연결이 활성화되어 있습니다. 종료하시겠습니까?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.stop_real_data_connection()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    app.setApplicationName("OKX 자동매매 시스템 v2.0")
    app.setStyle('Fusion')
    
    # 메인 윈도우 생성 및 표시
    window = ImprovedTradingMainWindow()
    window.show()
    
    # 시작 메시지
    print("🚀 OKX 자동매매 시스템 v2.0 - 실제 데이터 연동")
    print("📊 실제 OKX 시장 데이터 및 계좌 정보를 표시합니다")
    print("⚠️  config.py에 올바른 API 키가 설정되어 있는지 확인하세요")
    
    # 이벤트 루프 실행
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()