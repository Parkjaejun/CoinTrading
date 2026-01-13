# gui/main_window_real_trade_update.py
"""
기존 main_window.py에 실제 거래 테스트 기능을 추가하는 코드
이 파일의 내용을 기존 main_window.py에 통합하세요
"""

"""
=======================================================================
                     통합 가이드
=======================================================================

1. 먼저 새 파일들을 프로젝트에 추가:
   - okx/real_order_manager.py
   - gui/real_trade_test_widget.py

2. main_window.py 상단에 import 추가:
-----------------------------------------------------------------------
"""

# === 추가할 import 문 ===
# from okx.real_order_manager import RealOrderManager
# from gui.real_trade_test_widget import RealTradeTestWidget

"""
-----------------------------------------------------------------------
3. MainWindow.__init__ 에서 order_manager 초기화 추가:
-----------------------------------------------------------------------
"""

def initialize_real_order_manager(self):
    """실제 주문 관리자 초기화"""
    from config import API_KEY, API_SECRET, PASSPHRASE
    from okx.real_order_manager import RealOrderManager
    
    try:
        self.real_order_manager = RealOrderManager(API_KEY, API_SECRET, PASSPHRASE)
        print("✅ 실제 주문 관리자 초기화 완료")
        return True
    except Exception as e:
        print(f"❌ 실제 주문 관리자 초기화 실패: {e}")
        self.real_order_manager = None
        return False

"""
-----------------------------------------------------------------------
4. create_test_trade_tab 메서드를 교체 (기존 메서드 대체):
-----------------------------------------------------------------------
"""

def create_real_trade_tab(self):
    """실제 거래 테스트 탭 생성 (시뮬레이션 없음)"""
    from gui.real_trade_test_widget import RealTradeTestWidget
    
    tab = QWidget()
    layout = QVBoxLayout(tab)
    
    # 실제 거래 테스트 위젯 생성
    self.real_trade_widget = RealTradeTestWidget()
    
    # 주문 관리자 설정
    if hasattr(self, 'real_order_manager') and self.real_order_manager:
        self.real_trade_widget.set_order_manager(self.real_order_manager)
    
    layout.addWidget(self.real_trade_widget)
    
    return tab

"""
-----------------------------------------------------------------------
5. create_tabs 메서드에서 탭 추가 (기존 테스트 탭 교체):
-----------------------------------------------------------------------
"""

def create_tabs_with_real_trade(self):
    """탭 위젯 생성 (실제 거래 테스트 포함)"""
    self.tab_widget = QTabWidget()
    
    # 기존 탭들...
    # self.tab_widget.addTab(self.create_dashboard_tab(), "📊 대시보드")
    # self.tab_widget.addTab(self.create_position_tab(), "💼 포지션")
    # self.tab_widget.addTab(self.create_settings_tab(), "⚙️ 설정")
    # self.tab_widget.addTab(self.create_monitoring_tab(), "🎯 모니터링")
    
    # 실제 거래 테스트 탭 (시뮬레이션 대신)
    self.tab_widget.addTab(self.create_real_trade_tab(), "💰 실제 거래 테스트")
    
    # self.tab_widget.addTab(self.create_debug_tab(), "🔧 디버깅")

"""
=======================================================================
                     전체 예제 코드
=======================================================================
"""

# 완전한 MainWindow 클래스 예제 (참고용)

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QPushButton, QFrame, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime


class MainWindowWithRealTrade(QMainWindow):
    """실제 거래 테스트가 통합된 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        # 실제 주문 관리자 초기화
        self.real_order_manager = None
        self._init_order_manager()
        
        # UI 초기화
        self.init_ui()
        
    def _init_order_manager(self):
        """주문 관리자 초기화"""
        try:
            from config import API_KEY, API_SECRET, PASSPHRASE
            from okx.real_order_manager import RealOrderManager
            
            self.real_order_manager = RealOrderManager(API_KEY, API_SECRET, PASSPHRASE)
            print("✅ 실제 주문 관리자 초기화 완료")
        except ImportError as e:
            print(f"⚠️ 모듈 import 실패: {e}")
        except Exception as e:
            print(f"❌ 주문 관리자 초기화 실패: {e}")
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("OKX 자동매매 시스템 - 실제 거래")
        self.setGeometry(100, 100, 1600, 1000)
        self.setMinimumSize(1200, 800)
        
        # 다크 테마 적용
        self.setStyleSheet(DARK_THEME)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 상단 상태바
        self._create_status_bar(main_layout)
        
        # 탭 위젯
        self._create_tabs(main_layout)
    
    def _create_status_bar(self, layout):
        """상단 상태바"""
        status_frame = QFrame()
        status_frame.setMaximumHeight(60)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-bottom: 1px solid #3a3a3a;
            }
        """)
        
        status_layout = QHBoxLayout(status_frame)
        
        # 시스템 상태
        self.system_status = QLabel("🟢 실제 거래 모드")
        self.system_status.setFont(QFont('Arial', 11, QFont.Bold))
        self.system_status.setStyleSheet("color: #00ff88;")
        status_layout.addWidget(self.system_status)
        
        status_layout.addStretch()
        
        # 시간
        self.time_label = QLabel(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        status_layout.addWidget(self.time_label)
        
        # 시간 업데이트 타이머
        timer = QTimer(self)
        timer.timeout.connect(self._update_time)
        timer.start(1000)
        
        layout.addWidget(status_frame)
    
    def _update_time(self):
        """시간 업데이트"""
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def _create_tabs(self, layout):
        """탭 위젯 생성"""
        self.tab_widget = QTabWidget()
        
        # 실제 거래 테스트 탭
        self.tab_widget.addTab(self._create_real_trade_tab(), "💰 실제 거래 테스트")
        
        # 추가 탭들 (필요시)
        self.tab_widget.addTab(self._create_info_tab(), "ℹ️ 정보")
        
        layout.addWidget(self.tab_widget)
    
    def _create_real_trade_tab(self):
        """실제 거래 테스트 탭"""
        try:
            from gui.real_trade_test_widget import RealTradeTestWidget
            
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            # 위젯 생성 및 주문 관리자 연결
            self.real_trade_widget = RealTradeTestWidget()
            
            if self.real_order_manager:
                self.real_trade_widget.set_order_manager(self.real_order_manager)
            
            layout.addWidget(self.real_trade_widget)
            
            return tab
            
        except ImportError as e:
            # 폴백: 간단한 안내 탭
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            error_label = QLabel(f"⚠️ 위젯 로드 실패: {e}\n\n"
                                 f"gui/real_trade_test_widget.py 파일이 필요합니다.")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: #ff8800; font-size: 14px;")
            layout.addWidget(error_label)
            
            return tab
    
    def _create_info_tab(self):
        """정보 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        info_text = """
        <h2>OKX 실제 거래 테스트 시스템</h2>
        
        <h3>⚠️ 주의사항</h3>
        <ul>
            <li>이 시스템은 <b>실제 자금</b>을 사용합니다</li>
            <li>테스트 전 반드시 잔고를 확인하세요</li>
            <li>소액으로 시작하는 것을 권장합니다</li>
            <li>시뮬레이션 모드가 아닙니다</li>
        </ul>
        
        <h3>📋 사용 방법</h3>
        <ol>
            <li>거래 상품 선택 (BTC/ETH)</li>
            <li>주문 금액 설정 (최소 5 USDT)</li>
            <li>레버리지 설정 (권장: 1x)</li>
            <li>'실제 자금 사용에 동의' 체크</li>
            <li>'실제 구매 테스트' 버튼 클릭</li>
        </ol>
        
        <h3>📊 최소 주문 요건</h3>
        <ul>
            <li>BTC-USDT-SWAP: 약 $5 이상</li>
            <li>ETH-USDT-SWAP: 약 $5 이상</li>
        </ul>
        """
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.RichText)
        info_label.setStyleSheet("font-size: 12px; padding: 20px;")
        layout.addWidget(info_label)
        layout.addStretch()
        
        return tab


# 다크 테마 스타일시트
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
    QPushButton:disabled {
        background-color: #3a3a3a;
        color: #666666;
    }
    QComboBox {
        background-color: #3a3a3a;
        color: #ffffff;
        border: 1px solid #555;
        padding: 5px;
        border-radius: 4px;
    }
    QSpinBox, QDoubleSpinBox {
        background-color: #3a3a3a;
        color: #ffffff;
        border: 1px solid #555;
        padding: 5px;
        border-radius: 4px;
    }
    QTextEdit {
        background-color: #1e1e1e;
        color: #d4d4d4;
        border: 1px solid #3a3a3a;
        border-radius: 4px;
    }
    QGroupBox {
        border: 1px solid #3a3a3a;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
    }
    QGroupBox::title {
        color: #ffffff;
        subcontrol-origin: margin;
        left: 10px;
    }
    QTableWidget {
        background-color: #2b2b2b;
        color: #ffffff;
        gridline-color: #3a3a3a;
        border: 1px solid #3a3a3a;
    }
    QHeaderView::section {
        background-color: #3a3a3a;
        color: #ffffff;
        padding: 5px;
        border: none;
    }
    QProgressBar {
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        text-align: center;
        background-color: #2b2b2b;
    }
    QProgressBar::chunk {
        background-color: #0078d4;
    }
    QCheckBox {
        color: #ffffff;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }
"""


# 실행 예제
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    window = MainWindowWithRealTrade()
    window.show()
    sys.exit(app.exec_())
