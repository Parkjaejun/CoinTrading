"""
enhanced_main_window.py - 잔액 문제를 해결한 완전한 GUI 메인 윈도우
기존 gui/main_window.py를 백업하고 이 파일로 교체하거나 참고하세요.
"""

import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTextEdit, QGroupBox,
    QGridLayout, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QProgressBar, QStatusBar, QMenuBar,
    QAction, QMessageBox, QSystemTrayIcon, QMenu, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# 프로젝트 모듈들
try:
    from okx.account_manager import AccountManager
    from gui.balance_manager import GUIBalanceManager
    from utils.logger import log_system, log_error
    from utils.websocket_handler import WebSocketHandler
except ImportError as e:
    print(f"⚠️ 모듈 임포트 경고: {e}")
    print("일부 기능이 제한될 수 있습니다.")

class EnhancedDataThread(QThread):
    """향상된 데이터 처리 스레드 - 잔액 문제 해결"""
    
    # 시그널 정의
    account_updated = pyqtSignal(dict)
    price_updated = pyqtSignal(str, float, dict)
    connection_status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.account_manager = None
        self.websocket_handler = None
        self.account_data = {}
        self.running = False
        self.update_interval = 5  # 5초마다 업데이트
        
    def run(self):
        """메인 실행 루프"""
        try:
            self.running = True
            print("🚀 Enhanced 데이터 스레드 시작")
            
            # API 연결 설정
            if not self._setup_connections():
                self.connection_status_changed.emit(False)
                return
            
            self.connection_status_changed.emit(True)
            
            # 초기 데이터 로드
            self._load_initial_data()
            
            # 메인 루프
            while self.running:
                try:
                    self._update_account_data()
                    self.msleep(self.update_interval * 1000)  # 밀리초 단위
                    
                except Exception as e:
                    print(f"⚠️ 데이터 업데이트 루프 오류: {e}")
                    self.error_occurred.emit(f"데이터 업데이트 오류: {str(e)}")
                    self.msleep(10000)  # 오류 시 10초 대기
                    
        except Exception as e:
            print(f"❌ 데이터 스레드 치명적 오류: {e}")
            traceback.print_exc()
            self.error_occurred.emit(f"데이터 스레드 오류: {str(e)}")
            self.connection_status_changed.emit(False)
        
        finally:
            self._cleanup()
    
    def _setup_connections(self) -> bool:
        """연결 설정"""
        try:
            # AccountManager 초기화
            print("🔗 AccountManager 초기화...")
            self.account_manager = AccountManager()
            
            # 연결 테스트
            test_data = self.account_manager.get_account_balance()
            if not test_data:
                print("❌ API 연결 테스트 실패")
                return False
            
            print("✅ API 연결 테스트 성공")
            
            # WebSocket 핸들러 초기화 (옵션)
            try:
                self.websocket_handler = WebSocketHandler(['BTC-USDT-SWAP'], ['tickers'])
                if hasattr(self.websocket_handler, 'price_updated'):
                    self.websocket_handler.price_updated.connect(self._on_price_update)
                print("✅ WebSocket 핸들러 초기화 완료")
            except Exception as e:
                print(f"⚠️ WebSocket 초기화 실패 (계속 진행): {e}")
                self.websocket_handler = None
            
            return True
            
        except Exception as e:
            print(f"❌ 연결 설정 실패: {e}")
            traceback.print_exc()
            return False
    
    def _load_initial_data(self):
        """초기 데이터 로드"""
        try:
            print("📊 초기 데이터 로드 중...")
            self._update_account_data()
            print("✅ 초기 데이터 로드 완료")
        except Exception as e:
            print(f"⚠️ 초기 데이터 로드 실패: {e}")
    
    def _update_account_data(self):
        """계정 정보 업데이트 - Enhanced 버전"""
        try:
            if not self.account_manager:
                return
            
            # OKX API에서 원본 데이터 조회
            raw_balance_data = self.account_manager.get_account_balance()
            
            if raw_balance_data:
                # GUIBalanceManager를 사용해서 안전하게 파싱
                parsed_balances = GUIBalanceManager.parse_okx_balance(raw_balance_data)
                
                # 데이터 검증
                if self._validate_balance_data(parsed_balances):
                    self.account_data = parsed_balances
                    self.account_updated.emit(parsed_balances)
                    
                    # 간단한 로그 (너무 자주 나오지 않도록)
                    if not hasattr(self, '_last_balance_log'):
                        self._last_balance_log = 0
                    
                    current_time = time.time()
                    if current_time - self._last_balance_log >= 30:  # 30초에 한 번
                        usdt_balance = GUIBalanceManager.get_usdt_balance(parsed_balances)
                        total_equity = GUIBalanceManager.get_total_equity(parsed_balances)
                        print(f"💰 계정 업데이트: USDT ${usdt_balance:.2f}, 총 자산 ${total_equity:.2f}")
                        self._last_balance_log = current_time
                else:
                    print("⚠️ 잔액 데이터 검증 실패")
                    self._emit_empty_account_data()
            else:
                print("⚠️ 원본 잔액 데이터 없음")
                self._emit_empty_account_data()
                
        except Exception as e:
            print(f"❌ 계정 정보 업데이트 오류: {e}")
            self.error_occurred.emit(f"계정 정보 오류: {str(e)}")
            self._emit_empty_account_data()
    
    def _validate_balance_data(self, data: Dict[str, Any]) -> bool:
        """잔액 데이터 검증"""
        try:
            if not isinstance(data, dict):
                return False
            
            # 최소한 USDT 키가 있어야 함
            if 'USDT' not in data:
                return False
            
            # USDT 데이터 구조 확인
            usdt_data = data['USDT']
            if not isinstance(usdt_data, dict):
                return False
            
            required_keys = ['total', 'available', 'frozen']
            for key in required_keys:
                if key not in usdt_data:
                    return False
                
                # 숫자 타입 확인
                value = usdt_data[key]
                if not isinstance(value, (int, float)):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _emit_empty_account_data(self):
        """빈 계정 데이터 전송"""
        empty_data = GUIBalanceManager._get_empty_balance()
        self.account_updated.emit(empty_data)
    
    def _on_price_update(self, symbol: str, price: float, price_info: Dict):
        """가격 업데이트 콜백"""
        try:
            self.price_updated.emit(symbol, price, price_info)
        except Exception as e:
            print(f"⚠️ 가격 업데이트 처리 오류: {e}")
    
    def _cleanup(self):
        """정리 작업"""
        try:
            print("🧹 데이터 스레드 정리 중...")
            
            if self.websocket_handler:
                try:
                    self.websocket_handler.stop()
                except:
                    pass
            
            self.running = False
            print("✅ 데이터 스레드 정리 완료")
            
        except Exception as e:
            print(f"⚠️ 정리 작업 오류: {e}")
    
    def stop(self):
        """스레드 중지"""
        self.running = False

class EnhancedMainWindow(QMainWindow):
    """향상된 메인 윈도우 - 잔액 문제 해결"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 OKX 자동매매 시스템 - Enhanced GUI")
        self.setGeometry(100, 100, 1200, 800)
        
        # 데이터 관련
        self.data_thread = None
        self.account_balance = {}
        self.latest_prices = {}
        
        # UI 구성 요소들
        self.connection_label = None
        self.balance_label = None
        self.usdt_label = None
        self.btc_label = None
        self.log_display = None
        self.account_details = None
        
        # 타이머들
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)  # 1초마다
        
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
        self.create_monitoring_tab(tab_widget)
        self.create_account_tab(tab_widget)
        
        # 상태바
        self.statusBar().showMessage("Enhanced GUI 시작됨")
    
    def create_status_header(self, parent_layout):
        """상태 헤더 생성"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        
        # 연결 상태
        self.connection_label = QLabel("🔄 연결 중...")
        self.connection_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.connection_label)
        
        # 현재 시간
        self.clock_label = QLabel()
        header_layout.addWidget(self.clock_label)
        
        header_layout.addStretch()
        
        # 잔액 정보
        self.balance_label = QLabel("💰 USDT: $0.00")
        self.balance_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #00ff00;")
        header_layout.addWidget(self.balance_label)
        
        parent_layout.addWidget(header_widget)
    
    def create_dashboard_tab(self, tab_widget):
        """대시보드 탭 생성"""
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)
        
        # 상단 정보 패널
        info_panel = QWidget()
        info_layout = QGridLayout(info_panel)
        
        # 잔액 정보
        balance_group = QGroupBox("💰 계정 잔액")
        balance_layout = QFormLayout(balance_group)
        
        self.usdt_label = QLabel("$0.000000")
        self.usdt_label.setStyleSheet("font-size: 18px; color: #00ff00; font-weight: bold;")
        balance_layout.addRow("USDT:", self.usdt_label)
        
        self.btc_label = QLabel("0.00000000 BTC")
        balance_layout.addRow("BTC:", self.btc_label)
        
        self.total_equity_label = QLabel("$0.00")
        self.total_equity_label.setStyleSheet("font-size: 16px; color: #ffff00; font-weight: bold;")
        balance_layout.addRow("총 자산:", self.total_equity_label)
        
        info_layout.addWidget(balance_group, 0, 0)
        
        # 시스템 상태
        system_group = QGroupBox("⚙️ 시스템 상태")
        system_layout = QFormLayout(system_group)
        
        self.uptime_label = QLabel("00:00:00")
        system_layout.addRow("가동 시간:", self.uptime_label)
        
        self.status_label = QLabel("시작 중...")
        system_layout.addRow("상태:", self.status_label)
        
        info_layout.addWidget(system_group, 0, 1)
        
        layout.addWidget(info_panel)
        
        # 로그 디스플레이
        log_group = QGroupBox("📋 실시간 로그")
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setMaximumHeight(200)
        self.log_display.setReadOnly(True)
        log_layout.addWidget(self.log_display)
        
        layout.addWidget(log_group)
        
        tab_widget.addTab(dashboard_widget, "📊 대시보드")
    
    def create_monitoring_tab(self, tab_widget):
        """모니터링 탭 생성"""
        monitoring_widget = QWidget()
        layout = QVBoxLayout(monitoring_widget)
        
        # 계정 상세 정보
        account_group = QGroupBox("💼 계정 상세 정보")
        account_layout = QVBoxLayout(account_group)
        
        self.account_details = QTextEdit()
        self.account_details.setReadOnly(True)
        self.account_details.setMaximumHeight(300)
        account_layout.addWidget(self.account_details)
        
        layout.addWidget(account_group)
        
        # 새로고침 버튼
        refresh_btn = QPushButton("🔄 계정 정보 새로고침")
        refresh_btn.clicked.connect(self.refresh_account_data)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        tab_widget.addTab(monitoring_widget, "📡 모니터링")
    
    def create_account_tab(self, tab_widget):
        """계정 관리 탭 생성"""
        account_widget = QWidget()
        layout = QVBoxLayout(account_widget)
        
        # 테스트 버튼들
        test_group = QGroupBox("🧪 테스트 기능")
        test_layout = QHBoxLayout(test_group)
        
        balance_test_btn = QPushButton("잔액 조회 테스트")
        balance_test_btn.clicked.connect(self.test_balance_query)
        test_layout.addWidget(balance_test_btn)
        
        api_test_btn = QPushButton("API 연결 테스트")
        api_test_btn.clicked.connect(self.test_api_connection)
        test_layout.addWidget(api_test_btn)
        
        layout.addWidget(test_group)
        
        layout.addStretch()
        
        tab_widget.addTab(account_widget, "⚙️ 계정 관리")
    
    def apply_dark_theme(self):
        """다크 테마 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #404040;
                border: 1px solid #666666;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2b2b2b;
                border-bottom: 1px solid #2b2b2b;
            }
        """)
    
    def start_data_thread(self):
        """데이터 스레드 시작"""
        try:
            if self.data_thread and self.data_thread.isRunning():
                self.data_thread.stop()
                self.data_thread.wait(3000)
            
            self.data_thread = EnhancedDataThread()
            
            # 시그널 연결
            self.data_thread.account_updated.connect(self.on_account_updated)
            self.data_thread.price_updated.connect(self.on_price_updated)
            self.data_thread.connection_status_changed.connect(self.on_connection_changed)
            self.data_thread.error_occurred.connect(self.on_error_occurred)
            
            self.data_thread.start()
            self.add_log("🚀 Enhanced 데이터 스레드 시작됨")
            
        except Exception as e:
            print(f"❌ 데이터 스레드 시작 실패: {e}")
            self.add_log(f"❌ 데이터 스레드 오류: {e}")
    
    def on_account_updated(self, account_data):
        """계정 정보 업데이트 처리"""
        try:
            self.account_balance = account_data
            
            # 주요 값들 추출
            usdt_balance = GUIBalanceManager.get_usdt_balance(account_data)
            total_equity = GUIBalanceManager.get_total_equity(account_data)
            
            # BTC 잔액
            btc_info = account_data.get('BTC', {})
            btc_balance = btc_info.get('available', 0.0) if isinstance(btc_info, dict) else 0.0
            
            # UI 업데이트
            self.balance_label.setText(f"💰 USDT: ${usdt_balance:.2f}")
            self.usdt_label.setText(f"${usdt_balance:.6f}")
            self.btc_label.setText(f"{btc_balance:.8f} BTC")
            self.total_equity_label.setText(f"${total_equity:.2f}")
            
            # 상세 정보 업데이트
            if self.account_details:
                summary_text = GUIBalanceManager.format_balance_summary(account_data)
                self.account_details.setPlainText(summary_text)
            
            # 상태바 업데이트
            if total_equity > 0:
                self.statusBar().showMessage(f"Enhanced GUI - 총 자산: ${total_equity:.2f}")
            
            # 시스템 상태 업데이트
            self.status_label.setText("정상 운영")
            
        except Exception as e:
            print(f"⚠️ 계정 정보 UI 업데이트 오류: {e}")
            self.add_log(f"⚠️ UI 업데이트 오류: {e}")
    
    def on_price_updated(self, symbol, price, price_info):
        """가격 업데이트 처리"""
        self.latest_prices[symbol] = price
        
        # 간헐적으로만 로그 출력
        if not hasattr(self, '_last_price_log'):
            self._last_price_log = 0
        
        if time.time() - self._last_price_log >= 10:  # 10초에 한 번
            self.add_log(f"📈 {symbol}: ${price:,.2f}")
            self._last_price_log = time.time()
    
    def on_connection_changed(self, is_connected):
        """연결 상태 변경 처리"""
        if is_connected:
            self.connection_label.setText("✅ API 연결됨")
            self.connection_label.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 14px;")
            self.add_log("✅ Enhanced API 연결 성공")
        else:
            self.connection_label.setText("❌ API 연결 실패")
            self.connection_label.setStyleSheet("color: #ff0000; font-weight: bold; font-size: 14px;")
            self.add_log("❌ Enhanced API 연결 실패")
    
    def on_error_occurred(self, error_message):
        """오류 발생 처리"""
        self.add_log(f"⚠️ 오류: {error_message}")
    
    def update_clock(self):
        """시계 업데이트"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.setText(f"🕐 {current_time}")
    
    def add_log(self, message):
        """로그 추가"""
        if self.log_display:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            self.log_display.append(formatted_message)
            
            # 최대 라인 수 제한
            if self.log_display.document().lineCount() > 100:
                cursor = self.log_display.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.select(cursor.LineUnderCursor)
                cursor.removeSelectedText()
    
    def refresh_account_data(self):
        """계정 데이터 새로고침"""
        try:
            if self.data_thread and self.data_thread.isRunning():
                self.data_thread._update_account_data()
                self.add_log("🔄 계정 정보 수동 새로고침")
            else:
                self.add_log("⚠️ 데이터 스레드가 실행 중이 아닙니다")
        except Exception as e:
            self.add_log(f"❌ 새로고침 실패: {e}")
    
    def test_balance_query(self):
        """잔액 조회 테스트"""
        try:
            self.add_log("🧪 잔액 조회 테스트 시작...")
            
            # 직접 AccountManager로 테스트
            from okx.account_manager import AccountManager
            account = AccountManager()
            
            raw_data = account.get_account_balance()
            if raw_data:
                parsed_data = GUIBalanceManager.parse_okx_balance(raw_data)
                usdt_balance = GUIBalanceManager.get_usdt_balance(parsed_data)
                total_equity = GUIBalanceManager.get_total_equity(parsed_data)
                
                self.add_log(f"✅ 테스트 성공: USDT ${usdt_balance:.6f}, 총 자산 ${total_equity:.2f}")
                
                # 상세 정보
                currency_count = len([k for k in parsed_data.keys() if not k.startswith('_')])
                self.add_log(f"📊 활성 통화: {currency_count}개")
                
            else:
                self.add_log("❌ 테스트 실패: 잔액 데이터 없음")
                
        except Exception as e:
            self.add_log(f"❌ 테스트 오류: {e}")
    
    def test_api_connection(self):
        """API 연결 테스트"""
        try:
            self.add_log("🧪 API 연결 테스트 시작...")
            
            from okx.account_manager import AccountManager
            account = AccountManager()
            
            # 간단한 API 호출
            import requests
            response = requests.get("https://www.okx.com/api/v5/public/time", timeout=10)
            
            if response.status_code == 200:
                self.add_log("✅ OKX 서버 연결 성공")
                
                # 계정 API 테스트
                balance_data = account.get_account_balance()
                if balance_data:
                    self.add_log("✅ 계정 API 호출 성공")
                else:
                    self.add_log("⚠️ 계정 API 호출 실패")
            else:
                self.add_log(f"❌ 서버 연결 실패: HTTP {response.status_code}")
                
        except Exception as e:
            self.add_log(f"❌ 연결 테스트 오류: {e}")
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        try:
            self.add_log("🛑 Enhanced GUI 종료 중...")
            
            # 데이터 스레드 정리
            if self.data_thread and self.data_thread.isRunning():
                self.data_thread.stop()
                self.data_thread.wait(5000)  # 5초 대기
            
            event.accept()
            
        except Exception as e:
            print(f"⚠️ 종료 처리 오류: {e}")
            event.accept()

def main():
    """Enhanced GUI 메인 함수"""
    try:
        print("🚀 Enhanced OKX 자동매매 GUI 시작")
        
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        
        # 메인 윈도우 생성
        window = EnhancedMainWindow()
        window.show()
        
        print("✅ Enhanced GUI 실행 중...")
        
        # 이벤트 루프 시작
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Enhanced GUI 시작 실패: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
