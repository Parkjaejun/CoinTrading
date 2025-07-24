# gui/main_window.py - 실제 OKX 데이터 연동 GUI (완전 수정)
"""
실제 OKX API 연동 GUI - 모든 오류 해결
- 존재하는 모듈만 사용 (account_manager)
- position_manager 완전 제거
- 실제 시간 차트 X축
- 강화된 오류 처리
"""

import sys
import os
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QMessageBox
)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor

try:
    import pyqtgraph as pg
    from pyqtgraph import DateAxisItem
    pg.setConfigOption('background', 'k')
    pg.setConfigOption('foreground', 'w')
    PG_AVAILABLE = True
except ImportError:
    pg = None
    PG_AVAILABLE = False
    print("⚠️ pyqtgraph를 설치하세요: pip install pyqtgraph")

# 프로젝트 모듈 임포트 - 존재하는 모듈만
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 개별 모듈 임포트로 오류 격리
try:
    from config import API_KEY, API_SECRET, PASSPHRASE
    print("✅ config 모듈 로드 성공")
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"❌ config 모듈 로드 실패: {e}")
    CONFIG_AVAILABLE = False

try:
    from okx.account_manager import AccountManager  # 실제 존재하는 모듈
    print("✅ account_manager 모듈 로드 성공")
    ACCOUNT_AVAILABLE = True
except ImportError as e:
    print(f"❌ account_manager 모듈 로드 실패: {e}")
    ACCOUNT_AVAILABLE = False

try:
    from okx.websocket_handler import WebSocketHandler
    print("✅ websocket_handler 모듈 로드 성공")
    WEBSOCKET_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ websocket_handler 모듈 로드 실패: {e}")
    WEBSOCKET_AVAILABLE = False

try:
    from utils.logger import log_system, log_error, log_info
    print("✅ logger 모듈 로드 성공")
    LOGGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ logger 모듈 로드 실패: {e}")
    LOGGER_AVAILABLE = False
    # 기본 로그 함수 정의
    def log_system(msg): print(f"[SYSTEM] {msg}")
    def log_error(msg, e=None): print(f"[ERROR] {msg}: {e}" if e else f"[ERROR] {msg}")
    def log_info(msg): print(f"[INFO] {msg}")

# 시스템 가용성 확인
REAL_TRADING_AVAILABLE = CONFIG_AVAILABLE and ACCOUNT_AVAILABLE
print(f"🎯 실제 거래 시스템 가용성: {REAL_TRADING_AVAILABLE}")

class RealDataThread(QThread):
    """실제 OKX API 데이터 수신 스레드"""
    
    price_updated = pyqtSignal(str, float, dict)
    account_updated = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.should_stop = False
        self.account_manager = None
        self.websocket_handler = None
        self.latest_prices = {}
        self.account_data = {}
        
    def run(self):
        """메인 실행 루프"""
        if not REAL_TRADING_AVAILABLE:
            self.error_occurred.emit("필수 모듈(config.py, account_manager.py)을 찾을 수 없습니다")
            return
            
        self.is_running = True
        print("🔗 실제 OKX API 연결 시작")
        
        try:
            # 계정 관리자 초기화
            self.account_manager = AccountManager()
            print("✅ 계정 관리자 초기화 완료")
            
            # WebSocket 핸들러 (선택적)
            if WEBSOCKET_AVAILABLE:
                try:
                    self.websocket_handler = WebSocketHandler()
                    self.websocket_handler.set_callbacks(
                        price_callback=self._on_price_update,
                        connection_callback=self._on_connection_update
                    )
                    print("✅ WebSocket 핸들러 초기화 완료")
                    
                    # WebSocket 연결 시작
                    symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
                    self.websocket_handler.start_websocket(symbols)
                except Exception as e:
                    print(f"⚠️ WebSocket 초기화 실패: {e}")
                    self.websocket_handler = None
            
            # 초기 데이터 로드
            self._load_initial_data()
            
            # 연결 성공 신호
            self.connection_status_changed.emit(True)
            
            # 주기적 업데이트 루프
            last_account_update = 0
            price_simulation_counter = 0
            
            while self.is_running and not self.should_stop:
                try:
                    current_time = time.time()
                    
                    # 10초마다 계정 정보 업데이트
                    if current_time - last_account_update >= 10:
                        self._update_account_data()
                        last_account_update = current_time
                    
                    # WebSocket이 없으면 가격 시뮬레이션
                    if not self.websocket_handler:
                        price_simulation_counter += 1
                        if price_simulation_counter >= 3:  # 3초마다
                            self._simulate_price_data()
                            price_simulation_counter = 0
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"데이터 업데이트 오류: {e}")
                    self.error_occurred.emit(f"데이터 업데이트 오류: {str(e)}")
                    time.sleep(5)
                    
        except Exception as e:
            print(f"실제 API 연결 실패: {e}")
            self.error_occurred.emit(f"API 연결 실패: {str(e)}")
            self.connection_status_changed.emit(False)
        
        finally:
            self._cleanup()
    
    def _load_initial_data(self):
        """초기 데이터 로드"""
        try:
            self._update_account_data()
            print("✅ 초기 데이터 로드 완료")
        except Exception as e:
            print(f"초기 데이터 로드 실패: {e}")
    
    def _update_account_data(self):
        """계정 정보 업데이트 - 강화된 오류 처리"""
        try:
            if not self.account_manager:
                return
            
            print("🔄 계정 정보 업데이트 시도...")
            balances = self.account_manager.get_account_balance()
            
            if balances and isinstance(balances, dict):
                self.account_data = balances
                self.account_updated.emit(balances)
                
                usdt_balance = balances.get('USDT', {}).get('available', 0)
                print(f"💰 계정 정보 업데이트 성공: USDT ${usdt_balance:.2f}")
            else:
                print("⚠️ 계정 정보를 가져올 수 없습니다 - 기본값 사용")
                # 기본 데이터 제공
                default_data = {
                    'USDT': {'available': 0, 'total': 0, 'frozen': 0},
                    'BTC': {'available': 0, 'total': 0, 'frozen': 0}
                }
                self.account_updated.emit(default_data)
            
        except Exception as e:
            print(f"계정 정보 업데이트 오류: {e}")
            self.error_occurred.emit(f"계정 정보 오류: {str(e)}")
            # 오류 시에도 기본 데이터 제공
            default_data = {
                'USDT': {'available': 0, 'total': 0, 'frozen': 0},
                'BTC': {'available': 0, 'total': 0, 'frozen': 0}
            }
            self.account_updated.emit(default_data)
    
    def _simulate_price_data(self):
        """가격 데이터 시뮬레이션 (WebSocket 없을 때)"""
        try:
            import random
            
            # BTC 가격 시뮬레이션
            current_time = time.time()
            base_price = 45000
            variation = random.uniform(-1000, 1000)
            simulated_price = base_price + variation
            
            price_info = {
                'open_24h': base_price,
                'high_24h': simulated_price + 500,
                'low_24h': simulated_price - 500,
                'change_24h': variation / base_price,
                'timestamp': int(current_time * 1000)
            }
            
            self.price_updated.emit("BTC-USDT-SWAP", simulated_price, price_info)
            
        except Exception as e:
            print(f"가격 시뮬레이션 오류: {e}")
    
    def _on_price_update(self, *args):
        """WebSocket 가격 데이터 콜백 - 유연한 매개변수"""
        try:
            # args의 개수에 따라 처리 방식 결정
            if len(args) == 1:
                # 단일 price_data 객체
                price_data = args[0]
            elif len(args) >= 3:
                # (symbol, price, price_info) 형태
                symbol, price, price_info = args[0], args[1], args[2]
                price_data = {
                    'instId': symbol,
                    'last': str(price),
                    'ts': str(price_info.get('timestamp', int(time.time() * 1000)))
                }
            else:
                print(f"⚠️ 예상치 못한 콜백 매개변수 개수: {len(args)}")
                return
            
            # price_data 객체에서 정보 추출
            if isinstance(price_data, dict) and 'instId' in price_data:
                symbol = price_data['instId']
                price = float(price_data.get('last', 0))
                
                if price > 0:  # 유효한 가격인 경우만 처리
                    self.latest_prices[symbol] = price
                    
                    price_info = {
                        'open_24h': float(price_data.get('open24h', price)),
                        'high_24h': float(price_data.get('high24h', price)),
                        'low_24h': float(price_data.get('low24h', price)),
                        'change_24h': float(price_data.get('chg', 0)),
                        'timestamp': int(price_data.get('ts', time.time() * 1000))
                    }
                    
                    self.price_updated.emit(symbol, price, price_info)
                    
        except Exception as e:
            print(f"가격 데이터 처리 오류: {e}")
            print(f"매개변수: {args}")  # 디버깅용
    
    def _on_connection_update(self, *args):
        """연결 상태 콜백 - 유연한 매개변수"""
        try:
            # args에서 boolean 값 찾기
            is_connected = False
            
            for arg in args:
                if isinstance(arg, bool):
                    is_connected = arg
                    break
            
            self.connection_status_changed.emit(is_connected)
            
        except Exception as e:
            print(f"연결 상태 처리 오류: {e}")
            print(f"매개변수: {args}")  # 디버깅용
    
    def _cleanup(self):
        """정리 작업"""
        try:
            if self.websocket_handler:
                self.websocket_handler.stop_websocket()
            print("🛑 실제 API 연결 정리 완료")
        except Exception as e:
            print(f"정리 작업 오류: {e}")
    
    def stop(self):
        """데이터 수신 중지"""
        self.should_stop = True
        self.is_running = False

class TradingMainWindow(QMainWindow):
    """실제 거래용 메인 윈도우 - 오류 수정"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OKX 자동매매 시스템 - 실제 거래 모드 v4.2")
        self.setGeometry(100, 100, 1400, 900)
        
        # 실제 데이터 스레드
        self.data_thread = None
        
        # 데이터 저장
        self.account_balance = {}
        self.latest_prices = {}
        self.price_history = {}
        
        # UI 요소들
        self.time_label = None
        self.connection_label = None
        self.balance_label = None
        self.usdt_label = None
        self.btc_label = None
        self.log_display = None
        self.price_chart = None
        
        self.setup_ui()
        self.setup_timers()
        self.start_real_data_connection()
        self.apply_dark_theme()
    
    def setup_ui(self):
        """UI 설정"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 상단 정보 바
        info_bar = self.create_info_bar()
        main_layout.addWidget(info_bar)
        
        # 탭 위젯
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # 탭들 추가
        tab_widget.addTab(self.create_dashboard_tab(), "📊 대시보드")
        tab_widget.addTab(self.create_account_tab(), "💰 계정")
        tab_widget.addTab(self.create_log_tab(), "📋 로그")
        
        # 상태바
        if REAL_TRADING_AVAILABLE:
            self.statusBar().showMessage("실제 거래 모드 - API 연결 중...")
        else:
            self.statusBar().showMessage("실제 거래 모드 - 필수 모듈 누락")
    
    def create_info_bar(self):
        """상단 정보 바 생성"""
        info_widget = QWidget()
        info_layout = QHBoxLayout()
        info_widget.setLayout(info_layout)
        
        self.time_label = QLabel("⏰ 시간 업데이트 중...")
        self.time_label.setFont(QFont("Arial", 12))
        info_layout.addWidget(self.time_label)
        
        info_layout.addStretch()
        
        self.connection_label = QLabel("🔗 연결 확인 중...")
        self.connection_label.setFont(QFont("Arial", 12))
        info_layout.addWidget(self.connection_label)
        
        self.balance_label = QLabel("💰 잔고 로딩 중...")
        self.balance_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_layout.addWidget(self.balance_label)
        
        return info_widget
    
    def create_dashboard_tab(self):
        """대시보드 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 시스템 상태 그룹
        status_group = QGroupBox("🔧 시스템 상태")
        status_layout = QGridLayout()
        status_group.setLayout(status_layout)
        
        # 모듈 상태 표시
        config_status = "✅ 사용가능" if CONFIG_AVAILABLE else "❌ 누락"
        account_status = "✅ 사용가능" if ACCOUNT_AVAILABLE else "❌ 누락"
        websocket_status = "✅ 사용가능" if WEBSOCKET_AVAILABLE else "⚠️ 누락 (시뮬레이션 모드)"
        
        status_layout.addWidget(QLabel("Config 모듈:"), 0, 0)
        status_layout.addWidget(QLabel(config_status), 0, 1)
        status_layout.addWidget(QLabel("Account 모듈:"), 1, 0)
        status_layout.addWidget(QLabel(account_status), 1, 1)
        status_layout.addWidget(QLabel("WebSocket 모듈:"), 2, 0)
        status_layout.addWidget(QLabel(websocket_status), 2, 1)
        
        layout.addWidget(status_group)
        
        # 계정 정보 그룹
        account_group = QGroupBox("💰 실시간 계정 정보")
        account_layout = QGridLayout()
        account_group.setLayout(account_layout)
        
        self.usdt_label = QLabel("USDT: 로딩 중...")
        self.btc_label = QLabel("BTC: 로딩 중...")
        
        account_layout.addWidget(QLabel("💵 USDT:"), 0, 0)
        account_layout.addWidget(self.usdt_label, 0, 1)
        account_layout.addWidget(QLabel("₿ BTC:"), 1, 0)  
        account_layout.addWidget(self.btc_label, 1, 1)
        
        layout.addWidget(account_group)
        
        # 실시간 차트
        if PG_AVAILABLE:
            chart_group = QGroupBox("📈 BTC 가격 차트")
            chart_layout = QVBoxLayout()
            chart_group.setLayout(chart_layout)
            
            try:
                # 시간축을 실제 시간으로 표시
                time_axis = DateAxisItem(orientation='bottom')
                self.price_chart = pg.PlotWidget(axisItems={'bottom': time_axis})
                self.price_chart.setLabel('left', 'Price (USDT)')
                self.price_chart.setLabel('bottom', 'Time')
                self.price_chart.showGrid(x=True, y=True)
                chart_layout.addWidget(self.price_chart)
                
                # 차트 설명
                chart_info = QLabel("• 실시간 WebSocket 데이터 또는 시뮬레이션 데이터")
                chart_info.setStyleSheet("color: #888888; font-size: 10px;")
                chart_layout.addWidget(chart_info)
                
            except Exception as e:
                print(f"차트 생성 오류: {e}")
                # 차트 생성 실패 시 기본 차트
                self.price_chart = pg.PlotWidget()
                self.price_chart.setLabel('left', 'Price (USDT)')
                self.price_chart.setLabel('bottom', 'Time')
                chart_layout.addWidget(self.price_chart)
            
            layout.addWidget(chart_group)
        else:
            # pyqtgraph가 없는 경우
            chart_group = QGroupBox("📈 BTC 가격 차트")
            chart_layout = QVBoxLayout()
            chart_group.setLayout(chart_layout)
            
            no_chart_label = QLabel("차트를 표시하려면 pyqtgraph를 설치하세요:\npip install pyqtgraph")
            no_chart_label.setAlignment(Qt.AlignCenter)
            no_chart_label.setStyleSheet("color: #888888; padding: 50px;")
            chart_layout.addWidget(no_chart_label)
            
            layout.addWidget(chart_group)
        
        return widget
    
    def create_account_tab(self):
        """계정 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        account_group = QGroupBox("💰 계정 상세 정보")
        account_layout = QGridLayout()
        account_group.setLayout(account_layout)
        
        self.account_details = QTextEdit()
        self.account_details.setReadOnly(True)
        self.account_details.setPlainText("계정 정보 로딩 중...")
        account_layout.addWidget(self.account_details, 0, 0, 1, 2)
        
        refresh_btn = QPushButton("🔄 계정 정보 새로고침")
        refresh_btn.clicked.connect(self.refresh_account_data)
        account_layout.addWidget(refresh_btn, 1, 0, 1, 2)
        
        layout.addWidget(account_group)
        
        return widget
    
    def create_log_tab(self):
        """로그 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 로그 제어 버튼
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ 로그 지우기")
        clear_btn.clicked.connect(self.clear_logs)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 로그 표시
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_display)
        
        return widget
    
    def setup_timers(self):
        """타이머 설정"""
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # 1초마다
    
    def start_real_data_connection(self):
        """실제 데이터 연결 시작"""
        if not REAL_TRADING_AVAILABLE:
            self.add_log("❌ 실제 거래 시스템을 사용할 수 없습니다")
            self.add_log("• config.py 또는 account_manager.py를 확인하세요")
            self.connection_label.setText("❌ 필수 모듈 누락")
            self.connection_label.setStyleSheet("color: red; font-weight: bold;")
            return
        
        self.add_log("🔗 실제 OKX API 연결 시작...")
        
        self.data_thread = RealDataThread()
        self.data_thread.price_updated.connect(self.on_price_updated)
        self.data_thread.account_updated.connect(self.on_account_updated)
        self.data_thread.connection_status_changed.connect(self.on_connection_changed)
        self.data_thread.error_occurred.connect(self.on_error_occurred)
        
        self.data_thread.start()
    
    def on_price_updated(self, symbol, price, price_info):
        """가격 업데이트 처리"""
        self.latest_prices[symbol] = price
        self.update_price_chart(symbol, price, price_info.get('timestamp', time.time() * 1000))
        
        # 로그는 5초에 한 번만
        if not hasattr(self, '_last_price_log'):
            self._last_price_log = 0
        
        if time.time() - self._last_price_log >= 5:
            self.add_log(f"📈 {symbol}: ${price:,.2f}")
            self._last_price_log = time.time()
    
    def on_account_updated(self, account_data):
        """계정 정보 업데이트 처리"""
        self.account_balance = account_data
        
        try:
            usdt_balance = account_data.get('USDT', {}).get('available', 0)
            btc_balance = account_data.get('BTC', {}).get('available', 0)
            
            self.balance_label.setText(f"💰 USDT: ${usdt_balance:.2f}")
            self.usdt_label.setText(f"${usdt_balance:.6f}")
            self.btc_label.setText(f"{btc_balance:.8f} BTC")
            
            # 계정 상세 정보 업데이트
            if hasattr(self, 'account_details'):
                details_text = "실시간 계정 정보:\n\n"
                for currency, info in account_data.items():
                    if isinstance(info, dict):
                        details_text += f"{currency}:\n"
                        details_text += f"  사용가능: {info.get('available', 0):.6f}\n"
                        details_text += f"  총 잔고: {info.get('total', 0):.6f}\n"
                        details_text += f"  동결: {info.get('frozen', 0):.6f}\n\n"
                
                self.account_details.setPlainText(details_text)
            
            self.add_log(f"💰 계정 정보 업데이트: USDT ${usdt_balance:.2f}")
            
        except Exception as e:
            self.add_log(f"⚠️ 계정 정보 처리 오류: {e}")
    
    def on_connection_changed(self, is_connected):
        """연결 상태 변경 처리"""
        if is_connected:
            self.connection_label.setText("✅ API 연결됨")
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")
            self.statusBar().showMessage("실제 거래 모드 - API 연결 성공")
            self.add_log("✅ OKX API 연결 성공")
        else:
            self.connection_label.setText("❌ API 연결 실패")
            self.connection_label.setStyleSheet("color: red; font-weight: bold;")
            self.statusBar().showMessage("실제 거래 모드 - API 연결 실패")
            self.add_log("❌ OKX API 연결 실패")
    
    def on_error_occurred(self, error_message):
        """오류 발생 처리"""
        self.add_log(f"❌ 오류: {error_message}")
    
    def update_price_chart(self, symbol, price, timestamp):
        """가격 차트 업데이트 - 실제 시간 X축"""
        if not PG_AVAILABLE or not self.price_chart or symbol != "BTC-USDT-SWAP":
            return
        
        try:
            # 타임스탬프를 초 단위로 변환
            timestamp_seconds = timestamp / 1000 if timestamp > 1000000000000 else timestamp
            
            if symbol not in self.price_history:
                self.price_history[symbol] = {'times': [], 'prices': []}
            
            history = self.price_history[symbol]
            history['times'].append(timestamp_seconds)
            history['prices'].append(price)
            
            # 최대 50개 데이터포인트 유지 (성능 고려)
            if len(history['times']) > 50:
                history['times'] = history['times'][-50:]
                history['prices'] = history['prices'][-50:]
            
            # 차트 업데이트
            if len(history['times']) > 1:
                self.price_chart.clear()
                self.price_chart.plot(
                    history['times'], 
                    history['prices'], 
                    pen=pg.mkPen(color='y', width=2),
                    symbol='o', 
                    symbolSize=4,
                    symbolBrush='y'
                )
                
                # 현재 가격과 시간 표시
                current_time_str = datetime.fromtimestamp(timestamp_seconds).strftime('%H:%M:%S')
                data_source = "WebSocket" if WEBSOCKET_AVAILABLE else "시뮬레이션"
                self.price_chart.setTitle(
                    f"BTC-USDT-SWAP: ${price:,.2f} ({current_time_str}) - {data_source}"
                )
        
        except Exception as e:
            print(f"차트 업데이트 오류: {e}")
    
    def update_time(self):
        """시간 업데이트"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.setText(f"⏰ {current_time}")
    
    def refresh_account_data(self):
        """계정 정보 수동 새로고침"""
        if self.data_thread and self.data_thread.account_manager:
            try:
                self.add_log("🔄 계정 정보 새로고침 중...")
                self.data_thread._update_account_data()
            except Exception as e:
                self.add_log(f"❌ 계정 정보 새로고침 실패: {e}")
        else:
            self.add_log("❌ 계정 관리자를 사용할 수 없습니다")
    
    def clear_logs(self):
        """로그 지우기"""
        if self.log_display:
            self.log_display.clear()
            self.add_log("🗑️ 로그가 지워졌습니다")
    
    def add_log(self, message):
        """로그 추가 - 개선된 버전"""
        if self.log_display:
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_message = f"[{timestamp}] {message}"
            self.log_display.append(log_message)
            
            # 스크롤을 맨 아래로
            scrollbar = self.log_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
            # 로그 라인 수 제한 (500줄로 축소 - 성능 고려)
            if self.log_display.document().lineCount() > 500:
                cursor = self.log_display.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.movePosition(cursor.Down, cursor.KeepAnchor, 50)
                cursor.removeSelectedText()
    
    def apply_dark_theme(self):
        """다크 테마 적용"""
        dark_style = """
        QMainWindow { 
            background-color: #2b2b2b; 
            color: #ffffff; 
        }
        QWidget { 
            background-color: #2b2b2b; 
            color: #ffffff; 
        }
        QGroupBox { 
            border: 2px solid #555555; 
            border-radius: 5px; 
            margin-top: 1ex; 
            font-weight: bold; 
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #ffffff;
        }
        QTabWidget::pane { 
            border: 1px solid #555555; 
            background-color: #2b2b2b; 
        }
        QTabBar::tab { 
            background-color: #404040; 
            border: 1px solid #555555; 
            padding: 8px; 
            margin-right: 2px;
            color: #ffffff;
        }
        QTabBar::tab:selected { 
            background-color: #606060; 
        }
        QPushButton { 
            background-color: #404040; 
            border: 1px solid #555555; 
            padding: 8px; 
            border-radius: 3px; 
            color: #ffffff;
        }
        QPushButton:hover { 
            background-color: #505050; 
        }
        QPushButton:pressed { 
            background-color: #606060; 
        }
        QTextEdit { 
            background-color: #353535; 
            border: 1px solid #555555; 
            color: #ffffff;
        }
        QLabel { 
            color: #ffffff; 
        }
        QStatusBar { 
            background-color: #404040; 
            color: #ffffff; 
        }
        """
        self.setStyleSheet(dark_style)
    
    def closeEvent(self, event):
        """윈도우 종료 이벤트"""
        reply = QMessageBox.question(
            self,
            "종료 확인",
            "⚠️ 실제 거래 시스템을 종료하시겠습니까?\n\n"
            "• 실시간 데이터 수신이 중지됩니다\n"
            "• 활성 거래는 영향받지 않습니다\n\n"
            "종료하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 데이터 스레드 정리
            if self.data_thread:
                self.add_log("🛑 데이터 스레드 중지 중...")
                self.data_thread.stop()
                self.data_thread.wait(3000)  # 3초 대기
            
            self.add_log("👋 GUI 종료")
            event.accept()
        else:
            event.ignore()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    app.setApplicationName("OKX 자동매매 시스템")
    app.setApplicationVersion("4.2")
    app.setApplicationDisplayName("OKX Trading Bot")
    
    # 애플리케이션 아이콘 설정 시도
    try:
        app.setWindowIcon(QIcon())  # 기본 아이콘
    except:
        pass
    
    # 메인 윈도우 생성
    window = TradingMainWindow()
    window.show()
    
    # 시작 로그
    window.add_log("🚀 OKX 실제 거래 GUI 시작")
    
    if REAL_TRADING_AVAILABLE:
        window.add_log("⚠️ 실제 자금으로 거래가 실행됩니다")
        window.add_log("💡 API 연결 상태를 확인하세요")
        
        if WEBSOCKET_AVAILABLE:
            window.add_log("📡 WebSocket 실시간 데이터 활성화")
        else:
            window.add_log("⚠️ WebSocket 없음 - 가격 시뮬레이션 모드")
    else:
        window.add_log("⚠️ 필수 모듈 누락 - 제한된 기능으로 실행")
        window.add_log("• config.py와 okx/account_manager.py를 확인하세요")
    
    # 모듈 상태 로그
    window.add_log(f"🔧 Config: {'✅' if CONFIG_AVAILABLE else '❌'}")
    window.add_log(f"🔧 Account: {'✅' if ACCOUNT_AVAILABLE else '❌'}")  
    window.add_log(f"🔧 WebSocket: {'✅' if WEBSOCKET_AVAILABLE else '⚠️'}")
    window.add_log(f"🔧 Logger: {'✅' if LOGGER_AVAILABLE else '⚠️'}")
    window.add_log(f"🔧 PyQtGraph: {'✅' if PG_AVAILABLE else '⚠️'}")
    
    try:
        # 이벤트 루프 시작
        return app.exec_()
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단됨")
        window.close()
        return 0

if __name__ == "__main__":
    sys.exit(main())