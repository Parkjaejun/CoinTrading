# gui/main_window.py
"""
OKX 자동매매 시스템 - 메인 윈도우

구조:
- 상단 바: 잔고, BTC 가격, 연결 상태
- 탭: 대시보드, 자동매매, 알고리즘 검증

수정사항 (2024-02-12):
- update_balance_display(): USDT 실제 잔고 정확히 표시 (수정됨)
- update_price_display(): 차트 실시간 업데이트 개선 (수정됨)
- 초기 데이터 자동 로드 기능 추가 (신규)
"""

import sys
import time
from datetime import datetime
from typing import Dict, Optional, Any

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QFrame, QGroupBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QStatusBar, QSplitter, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor

# 컴포넌트 import
try:
    from gui.dashboard_chart_widget import DashboardChartWidget
    DASHBOARD_CHART_AVAILABLE = True
    print("✅ DashboardChartWidget 로드 성공")
except ImportError as e:
    DASHBOARD_CHART_AVAILABLE = False
    print(f"⚠️ DashboardChartWidget 로드 실패: {e}")

try:
    from gui.auto_trading_widget import AutoTradingWidget
    AUTO_TRADING_AVAILABLE = True
    print("✅ AutoTradingWidget 로드 성공")
except ImportError as e:
    AUTO_TRADING_AVAILABLE = False
    print(f"⚠️ AutoTradingWidget 로드 실패: {e}")

try:
    from okx.historical_data_loader import HistoricalDataLoader
    DATA_LOADER_AVAILABLE = True
    print("✅ HistoricalDataLoader 로드 성공")
except ImportError as e:
    DATA_LOADER_AVAILABLE = False
    print(f"⚠️ HistoricalDataLoader 로드 실패: {e}")

try:
    from gui.data_thread import TradingDataThread
    DATA_THREAD_AVAILABLE = True
except ImportError:
    DATA_THREAD_AVAILABLE = False
    print("⚠️ TradingDataThread 사용 불가")

try:
    from okx.account_manager import AccountManager
    ACCOUNT_MANAGER_AVAILABLE = True
except ImportError:
    ACCOUNT_MANAGER_AVAILABLE = False
    print("⚠️ AccountManager 사용 불가")

# 백테스트 위젯 import
try:
    import os
    backtest_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backtest_project')
    if backtest_path not in sys.path:
        sys.path.insert(0, backtest_path)
    from main import create_backtest_tab
    BACKTEST_AVAILABLE = True
    print("✅ 백테스트 위젯 로드 성공")
except ImportError as e:
    BACKTEST_AVAILABLE = False
    print(f"⚠️ 백테스트 위젯 로드 실패: {e}")


# 다크 테마
DARK_THEME = """
    QMainWindow {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    QWidget {
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
        padding: 10px 20px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        font-size: 13px;
    }
    QTabBar::tab:selected {
        background-color: #0078d4;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #3a3a3a;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }
    QTableWidget {
        background-color: #2b2b2b;
        gridline-color: #3a3a3a;
        border: none;
    }
    QHeaderView::section {
        background-color: #3a3a3a;
        padding: 5px;
        border: 1px solid #2b2b2b;
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
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
        background-color: #2b2b2b;
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        padding: 5px;
        color: #ffffff;
    }
"""


class TradingMainWindow(QMainWindow):
    """메인 거래 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        # 데이터 관련
        self.data_thread = None
        self.data_loader = None
        self.account_manager = None
        self.latest_prices = {}
        self.positions = []
        self.balance_data = {}
        
        # 위젯 참조
        self.dashboard_chart = None
        self.auto_trading_widget = None
        
        # 초기화
        self._init_data_loader()
        self.setup_window()
        self.setup_ui()
        self.setup_connections()
        self.start_data_collection()
        
        print("🖥️ GUI 메인 윈도우 초기화 완료")
    
    def _init_data_loader(self):
        """데이터 로더 초기화"""
        if DATA_LOADER_AVAILABLE:
            try:
                self.data_loader = HistoricalDataLoader(self.account_manager)
                print("✅ HistoricalDataLoader 초기화 완료")
            except Exception as e:
                print(f"⚠️ HistoricalDataLoader 초기화 실패: {e}")
                self.data_loader = None
    
    def setup_window(self):
        """윈도우 기본 설정"""
        self.setWindowTitle("OKX 자동매매 시스템 v2")
        self.setGeometry(100, 100, 1600, 1000)
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(DARK_THEME)
    
    def setup_ui(self):
        """UI 구성"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 상단 상태바
        self.create_status_bar(main_layout)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 탭 생성
        self.create_dashboard_tab()
        self.create_auto_trading_tab()
        self.create_backtest_tab()
    
    def create_status_bar(self, layout):
        """상단 상태바"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_frame.setMaximumHeight(60)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 5px;
            }
        """)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(15, 5, 15, 5)
        
        # 잔고 표시
        balance_label = QLabel("💰 잔고:")
        balance_label.setFont(QFont("Arial", 11))
        status_layout.addWidget(balance_label)
        
        self.balance_display = QLabel("$0.00")
        self.balance_display.setFont(QFont("Arial", 14, QFont.Bold))
        self.balance_display.setStyleSheet("color: #00ff88;")
        status_layout.addWidget(self.balance_display)
        
        status_layout.addSpacing(30)
        
        # BTC 가격 표시
        btc_label = QLabel("₿ BTC:")
        btc_label.setFont(QFont("Arial", 11))
        status_layout.addWidget(btc_label)
        
        self.btc_price_display = QLabel("$0.00")
        self.btc_price_display.setFont(QFont("Arial", 14, QFont.Bold))
        self.btc_price_display.setStyleSheet("color: #f39c12;")
        status_layout.addWidget(self.btc_price_display)
        
        status_layout.addStretch()
        
        # 모드 상태
        self.mode_status_label = QLabel("⏸️ 대기 중")
        self.mode_status_label.setFont(QFont("Arial", 11))
        self.mode_status_label.setStyleSheet("color: #888888;")
        status_layout.addWidget(self.mode_status_label)
        
        status_layout.addSpacing(20)
        
        # 연결 상태
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setFont(QFont("Arial", 16))
        self.connection_indicator.setStyleSheet("color: #888888;")
        status_layout.addWidget(self.connection_indicator)
        
        self.connection_label = QLabel("연결 중...")
        self.connection_label.setFont(QFont("Arial", 11))
        status_layout.addWidget(self.connection_label)
        
        layout.addWidget(status_frame)
    
    def create_dashboard_tab(self):
        """대시보드 탭 - 향상된 차트 + 정보 패널"""
        dashboard_widget = QWidget()
        layout = QHBoxLayout(dashboard_widget)
        layout.setSpacing(10)
        
        # 왼쪽: 실시간 차트 (70%)
        chart_group = QGroupBox("📈 BTC 실시간 차트 (30분봉, EMA 포함)")
        chart_layout = QVBoxLayout(chart_group)
        
        if DASHBOARD_CHART_AVAILABLE:
            self.dashboard_chart = DashboardChartWidget()
            chart_layout.addWidget(self.dashboard_chart)
        else:
            placeholder = QLabel("차트 위젯 로드 실패\n\n가격 데이터는 상단에서 확인하세요")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #888888; font-size: 14px;")
            chart_layout.addWidget(placeholder)
        
        # 오른쪽: 정보 패널 (30%)
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        info_layout.setSpacing(10)
        
        # 계좌 정보
        account_group = QGroupBox("💰 계좌 정보")
        account_layout = QGridLayout(account_group)
        account_layout.setSpacing(8)
        
        self.total_asset_label = QLabel("$0.00")
        self.total_asset_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.total_asset_label.setStyleSheet("color: #00ff88;")
        account_layout.addWidget(QLabel("총 자산:"), 0, 0)
        account_layout.addWidget(self.total_asset_label, 0, 1)
        
        self.available_label = QLabel("$0.00")
        account_layout.addWidget(QLabel("사용 가능:"), 1, 0)
        account_layout.addWidget(self.available_label, 1, 1)
        
        self.unrealized_pnl_label = QLabel("$0.00")
        account_layout.addWidget(QLabel("미실현 손익:"), 2, 0)
        account_layout.addWidget(self.unrealized_pnl_label, 2, 1)
        
        info_layout.addWidget(account_group)
        
        # 트렌드 상태
        trend_group = QGroupBox("📊 트렌드 상태")
        trend_layout = QGridLayout(trend_group)
        
        self.trend_status_label = QLabel("분석 중...")
        self.trend_status_label.setFont(QFont("Arial", 12, QFont.Bold))
        trend_layout.addWidget(QLabel("현재 트렌드:"), 0, 0)
        trend_layout.addWidget(self.trend_status_label, 0, 1)
        
        self.trend_strength_label = QLabel("-")
        trend_layout.addWidget(QLabel("강도:"), 1, 0)
        trend_layout.addWidget(self.trend_strength_label, 1, 1)
        
        info_layout.addWidget(trend_group)
        
        # 포지션 요약
        position_group = QGroupBox("📋 포지션 요약")
        position_layout = QVBoxLayout(position_group)
        
        self.position_summary_table = QTableWidget()
        self.position_summary_table.setColumnCount(4)
        self.position_summary_table.setHorizontalHeaderLabels(["심볼", "방향", "수량", "손익"])
        self.position_summary_table.horizontalHeader().setStretchLastSection(True)
        self.position_summary_table.setMaximumHeight(150)
        position_layout.addWidget(self.position_summary_table)
        
        info_layout.addWidget(position_group)
        
        # 상태 그룹
        status_group = QGroupBox("🔗 시스템 상태")
        status_layout_inner = QGridLayout(status_group)
        
        self.api_status_label = QLabel("🟡 확인 중")
        status_layout_inner.addWidget(QLabel("API:"), 0, 0)
        status_layout_inner.addWidget(self.api_status_label, 0, 1)
        
        self.ws_status_label = QLabel("🟡 확인 중")
        status_layout_inner.addWidget(QLabel("WebSocket:"), 1, 0)
        status_layout_inner.addWidget(self.ws_status_label, 1, 1)
        
        info_layout.addWidget(status_group)
        
        # 데이터 로드 버튼
        load_btn = QPushButton("📊 1주일 데이터 로드")
        load_btn.clicked.connect(self.load_historical_data)
        info_layout.addWidget(load_btn)
        
        info_layout.addStretch()
        
        # 레이아웃 비율
        layout.addWidget(chart_group, 7)
        layout.addWidget(info_panel, 3)
        
        self.tab_widget.addTab(dashboard_widget, "📊 대시보드")
    
    def create_auto_trading_tab(self):
        """자동매매 탭"""
        if AUTO_TRADING_AVAILABLE:
            self.auto_trading_widget = AutoTradingWidget(
                parent=self,
                account_manager=self.account_manager,
                data_loader=self.data_loader
            )
            
            # 시그널 연결
            self.auto_trading_widget.trading_started.connect(self._on_trading_started)
            self.auto_trading_widget.trading_stopped.connect(self._on_trading_stopped)
            self.auto_trading_widget.request_historical_data.connect(self._send_data_to_dashboard)
            
            self.tab_widget.addTab(self.auto_trading_widget, "🤖 자동매매")
        else:
            fallback = QWidget()
            layout = QVBoxLayout(fallback)
            label = QLabel("자동매매 위젯 로드 실패\n\nauto_trading_widget.py 파일을 확인하세요")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #888888; font-size: 14px;")
            layout.addWidget(label)
            self.tab_widget.addTab(fallback, "🤖 자동매매")
    
    def create_backtest_tab(self):
        """알고리즘 검증 탭"""
        try:
            if BACKTEST_AVAILABLE:
                backtest_widget = create_backtest_tab()
                self.tab_widget.addTab(backtest_widget, "🧪 알고리즘 검증")
            else:
                fallback = QWidget()
                layout = QVBoxLayout(fallback)
                info_label = QLabel("백테스트 모듈을 찾을 수 없습니다")
                info_label.setStyleSheet("font-size: 14px; color: #f39c12;")
                layout.addWidget(info_label)
                
                instruction = QLabel(
                    "backtest_project 폴더를 프로젝트 루트에 복사하세요:\n"
                    "D:\\Project\\CoinTrading\\backtest_project\\"
                )
                layout.addWidget(instruction)
                layout.addStretch()
                
                self.tab_widget.addTab(fallback, "🧪 알고리즘 검증")
        except Exception as e:
            print(f"❌ 백테스트 탭 생성 실패: {e}")
    
    def setup_connections(self):
        """시그널 연결"""
        pass
    
    def start_data_collection(self):
        """데이터 수집 시작"""
        if DATA_THREAD_AVAILABLE and ACCOUNT_MANAGER_AVAILABLE:
            try:
                self.account_manager = AccountManager()
                self.data_thread = TradingDataThread(self.account_manager)
                
                self.data_thread.price_updated.connect(self.update_price_display)
                self.data_thread.balance_updated.connect(self.update_balance_display)
                self.data_thread.positions_updated.connect(self.update_positions_display)
                self.data_thread.connection_changed.connect(self.update_connection_status)
                
                self.data_thread.start()
                print("✅ 데이터 수집 스레드 시작")
                
                # ★ 신규: 초기 데이터 자동 로드 (2초 후)
                self._auto_load_initial_data()
                
            except Exception as e:
                print(f"⚠️ 데이터 수집 시작 실패: {e}")
                self._start_dummy_data()
        else:
            print("⚠️ 데이터 스레드 사용 불가 - 더미 데이터 사용")
            self._start_dummy_data()
    
    def _start_dummy_data(self):
        """더미 데이터 타이머 시작"""
        self.dummy_timer = QTimer()
        self.dummy_timer.timeout.connect(self._update_dummy_data)
        self.dummy_timer.start(1000)
        
        self.update_connection_status(True)
    
    def _update_dummy_data(self):
        """더미 데이터 업데이트"""
        import random
        
        base_price = getattr(self, '_dummy_price', 97000)
        change = random.uniform(-50, 50)
        base_price += change
        self._dummy_price = base_price
        
        self.update_price_display("BTC-USDT-SWAP", base_price, {'change_24h': random.uniform(-2, 2)})
        self.update_balance_display({
            'total_equity': 10000 + random.uniform(-100, 100),
            'usdt_balance': 10000 + random.uniform(-100, 100),
            'available_balance': 9500 + random.uniform(-100, 100),
            'unrealized_pnl': random.uniform(-50, 50)
        })
    
    # ========================================
    # ★ 신규: 초기 데이터 자동 로드 메서드
    # ========================================
    def _auto_load_initial_data(self):
        """GUI 시작 시 초기 데이터 자동 로드"""
        if not self.data_loader:
            print("⚠️ 데이터 로더 없음 - 초기 데이터 로드 건너뜀")
            return
        
        try:
            print("📊 초기 데이터 자동 로드 예약 (2초 후)...")
            QTimer.singleShot(2000, self._load_initial_data_async)
        except Exception as e:
            print(f"⚠️ 초기 데이터 로드 설정 실패: {e}")
    
    def _load_initial_data_async(self):
        """비동기 초기 데이터 로드"""
        try:
            print("📊 초기 데이터 로드 시작...")
            df = self.data_loader.load_historical_candles_sync(
                symbol="BTC-USDT-SWAP",
                timeframe="30m",
                days=7
            )
            
            if df is not None and len(df) > 0:
                print(f"✅ 초기 데이터 로드 완료: {len(df)}개 캔들")
                
                # 대시보드 차트에 데이터 전달
                if self.dashboard_chart:
                    self.dashboard_chart.set_historical_data(df)
                
                # 트렌드 상태 업데이트
                self._update_trend_status()
                
                self.statusBar().showMessage(f"✅ {len(df)}개 30분봉 데이터 자동 로드됨", 5000)
            else:
                print("⚠️ 초기 데이터 로드 실패 - 실시간 데이터로 시작")
                
        except Exception as e:
            print(f"⚠️ 초기 데이터 로드 오류: {e}")
    
    def load_historical_data(self):
        """1주일 과거 데이터 로드 (버튼 클릭)"""
        if not self.data_loader:
            QMessageBox.warning(self, "오류", "데이터 로더가 초기화되지 않았습니다.")
            return
        
        try:
            self.statusBar().showMessage("📊 과거 데이터 로드 중...")
            
            df = self.data_loader.load_historical_candles_sync(
                symbol="BTC-USDT-SWAP",
                timeframe="30m",
                days=7
            )
            
            if df is not None and len(df) > 0:
                # 대시보드 차트에 데이터 전달
                if self.dashboard_chart:
                    self.dashboard_chart.set_historical_data(df)
                
                # 트렌드 상태 업데이트
                self._update_trend_status()
                
                self.statusBar().showMessage(f"✅ {len(df)}개 캔들 로드 완료", 5000)
                QMessageBox.information(self, "성공", f"{len(df)}개의 30분봉 데이터를 로드했습니다.")
            else:
                self.statusBar().showMessage("❌ 데이터 로드 실패", 5000)
                QMessageBox.warning(self, "오류", "데이터 로드에 실패했습니다.")
                
        except Exception as e:
            self.statusBar().showMessage(f"❌ 오류: {e}", 5000)
            QMessageBox.critical(self, "오류", f"데이터 로드 중 오류 발생:\n{e}")
    
    def _send_data_to_dashboard(self):
        """데이터 로더의 데이터를 대시보드 차트로 전송"""
        if self.data_loader and self.dashboard_chart:
            df = self.data_loader.get_cached_dataframe()
            if df is not None:
                self.dashboard_chart.set_historical_data(df)
                self._update_trend_status()
    
    def _update_trend_status(self):
        """트렌드 상태 업데이트"""
        if not self.data_loader:
            return
        
        data = self.data_loader.get_latest_strategy_data()
        if not data:
            return
        
        ema150 = data.get('ema_150', 0)
        ema200 = data.get('ema_200', 0)
        
        if ema150 and ema200:
            is_uptrend = ema150 > ema200
            strength = ((ema150 - ema200) / ema200 * 100) if ema200 > 0 else 0
            
            if is_uptrend:
                self.trend_status_label.setText("📈 상승장")
                self.trend_status_label.setStyleSheet("color: #28a745;")
            else:
                self.trend_status_label.setText("📉 하락장")
                self.trend_status_label.setStyleSheet("color: #dc3545;")
            
            self.trend_strength_label.setText(f"{strength:+.3f}%")
    
    # ========================================
    # ★ 수정됨: update_price_display - 차트 실시간 업데이트 개선
    # ========================================
    def update_price_display(self, symbol: str, price: float, price_info: dict = None):
        """가격 표시 업데이트 - 차트 실시간 반영 (수정됨)"""
        try:
            self.latest_prices[symbol] = price
            
            if "BTC" in symbol:
                # 상단 BTC 가격 표시
                self.btc_price_display.setText(f"${price:,.2f}")
                
                # 24시간 변화율 표시 (있는 경우)
                if price_info and 'change_24h' in price_info:
                    change = price_info['change_24h']
                    color = "#28a745" if change >= 0 else "#dc3545"
                    self.btc_price_display.setStyleSheet(f"color: {color};")
                
                # ★ 수정됨: 대시보드 차트 실시간 업데이트
                if self.dashboard_chart:
                    timestamp = int(time.time() * 1000)  # 밀리초 단위
                    self.dashboard_chart.update_price_only(price, timestamp)
                
                # 데이터 로더 업데이트
                if self.data_loader:
                    self.data_loader.update_current_price(symbol, price)
                    
                    # 자동매매 위젯이 실행 중이면 전략 데이터 전달
                    if hasattr(self, 'auto_trading_widget') and self.auto_trading_widget:
                        if self.auto_trading_widget.is_running:
                            strategy_data = self.data_loader.get_latest_strategy_data()
                            if strategy_data:
                                strategy_data['close'] = price
                                self.auto_trading_widget.update_from_external(strategy_data)
                
        except Exception as e:
            print(f"⚠️ 가격 표시 업데이트 오류: {e}")
    
    # ========================================
    # ★ 수정됨: update_balance_display - USDT 실제 잔고 표시
    # ========================================
    def update_balance_display(self, balance_data: dict):
        """잔고 표시 업데이트 - USDT 실제 잔고 정확히 표시 (수정됨)"""
        try:
            # data_thread.py에서 emit하는 구조에 맞춤
            # {'total_equity': xxx, 'usdt_balance': xxx, 'available_balance': xxx, 'currencies': {...}}
            
            # 1. 총 자산 (totalEq)
            total_equity = balance_data.get('total_equity', 0)
            if total_equity == 0:
                total_equity = balance_data.get('total', 0)
            
            # 2. USDT 잔고
            usdt_balance = balance_data.get('usdt_balance', 0)
            available_balance = balance_data.get('available_balance', 0)
            
            # currencies에서 USDT 정보 추출 (대안)
            currencies = balance_data.get('currencies', {})
            if usdt_balance == 0 and 'USDT' in currencies:
                usdt_info = currencies['USDT']
                usdt_balance = usdt_info.get('equity', 0)
                available_balance = usdt_info.get('available', 0)
            
            # 3. 미실현 손익
            unrealized_pnl = balance_data.get('unrealized_pnl', 0)
            
            # ========================================
            # UI 업데이트
            # ========================================
            
            # 상단 상태바 - 총 자산 표시
            if hasattr(self, 'balance_display'):
                self.balance_display.setText(f"${total_equity:,.2f}")
            
            # 대시보드 계좌 정보 - 총 자산
            if hasattr(self, 'total_asset_label'):
                self.total_asset_label.setText(f"${total_equity:,.2f}")
            
            # 대시보드 계좌 정보 - 사용 가능 잔고
            if hasattr(self, 'available_label'):
                self.available_label.setText(f"${available_balance:,.2f}")
            
            # 대시보드 계좌 정보 - 미실현 손익
            if hasattr(self, 'unrealized_pnl_label'):
                self.unrealized_pnl_label.setText(f"${unrealized_pnl:+,.2f}")
                if unrealized_pnl >= 0:
                    self.unrealized_pnl_label.setStyleSheet("color: #28a745;")
                else:
                    self.unrealized_pnl_label.setStyleSheet("color: #dc3545;")
            
            # 자동매매 위젯에 잔고 전달
            if hasattr(self, 'auto_trading_widget') and self.auto_trading_widget:
                if hasattr(self.auto_trading_widget, 'update_balance'):
                    self.auto_trading_widget.update_balance(available_balance)
            
            # 내부 저장
            self.balance_data = {
                'total': total_equity,
                'available': available_balance,
                'usdt': usdt_balance,
                'unrealized_pnl': unrealized_pnl
            }
            
        except Exception as e:
            print(f"⚠️ 잔고 표시 업데이트 오류: {e}")
    
    def update_positions_display(self, positions: list):
        """포지션 표시 업데이트"""
        try:
            self.positions = positions
            
            self.position_summary_table.setRowCount(len(positions))
            
            for i, pos in enumerate(positions):
                symbol = pos.get('instId', pos.get('symbol', '-'))
                side = pos.get('posSide', pos.get('side', '-'))
                size = pos.get('pos', pos.get('size', '0'))
                upl = float(pos.get('upl', pos.get('unrealized_pnl', 0)))
                
                self.position_summary_table.setItem(i, 0, QTableWidgetItem(symbol))
                self.position_summary_table.setItem(i, 1, QTableWidgetItem(side))
                self.position_summary_table.setItem(i, 2, QTableWidgetItem(str(size)))
                
                pnl_item = QTableWidgetItem(f"${upl:+,.2f}")
                if upl >= 0:
                    pnl_item.setForeground(QColor('#28a745'))
                else:
                    pnl_item.setForeground(QColor('#dc3545'))
                self.position_summary_table.setItem(i, 3, pnl_item)
                
        except Exception as e:
            print(f"포지션 표시 업데이트 오류: {e}")
    
    def update_connection_status(self, connected: bool):
        """연결 상태 업데이트"""
        if connected:
            self.connection_indicator.setStyleSheet("color: #28a745;")
            self.connection_label.setText("연결됨")
            self.api_status_label.setText("🟢 연결됨")
            self.ws_status_label.setText("🟢 연결됨")
        else:
            self.connection_indicator.setStyleSheet("color: #dc3545;")
            self.connection_label.setText("연결 끊김")
            self.api_status_label.setText("🔴 끊김")
            self.ws_status_label.setText("🔴 끊김")
    
    def _on_trading_started(self):
        """자동매매 시작 시"""
        self.mode_status_label.setText("🟡 가상 모드")
        self.mode_status_label.setStyleSheet("color: #ffc107;")
    
    def _on_trading_stopped(self):
        """자동매매 정지 시"""
        self.mode_status_label.setText("⏸️ 대기 중")
        self.mode_status_label.setStyleSheet("color: #888888;")
    
    def closeEvent(self, event):
        """윈도우 종료 시"""
        # 타이머 정지
        if hasattr(self, 'dummy_timer'):
            self.dummy_timer.stop()
        
        # 데이터 스레드 정지
        if self.data_thread and self.data_thread.isRunning():
            self.data_thread.stop()
            self.data_thread.wait(3000)
        
        event.accept()
        print("🔚 GUI 윈도우 종료됨")


def main():
    """메인 함수"""
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = TradingMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
