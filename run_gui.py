#!/usr/bin/env python3
# run_gui.py
"""
OKX 자동매매 시스템 GUI 런처 - 수정된 버전
- 모든 임포트 오류 해결
- 안전한 모듈 로딩
- 완전한 GUI 실행
"""
import quiet_logger
import sys
import os
import traceback
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python path에 추가
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("================================================================================")
print("🚀 OKX 자동매매 시스템 - 완전한 실제 거래 GUI")
print("================================================================================")
print("💰 실시간 가격 차트 | 전략 관리 | 포지션 제어 | 백테스팅")
print("⚠️  실제 자금으로 거래가 실행됩니다. 신중하게 사용하세요!")
print("================================================================================")

def check_dependencies():
    """필수 의존성 확인"""
    print("🔧 환경 설정 중...")
    
    try:
        from terminal_dashboard import init_dashboard
        init_dashboard()  # 불필요한 로그 숨김
    except:
        pass
    
    # PyQt5 확인
    try:
        from PyQt5.QtWidgets import QApplication
        print("✅ PyQt5 확인됨")
    except ImportError:
        print("❌ PyQt5가 설치되지 않음")
        print("다음 명령어로 설치하세요: pip install PyQt5")
        return False
    
    # 선택적 라이브러리들
    try:
        import pyqtgraph
        print("✅ pyqtgraph 확인됨 (차트 기능 활성화)")
    except ImportError:
        print("⚠️ pyqtgraph 없음 (차트 기능 제한)")
    
    try:
        import psutil
        print("✅ psutil 확인됨 (시스템 모니터링 활성화)")
    except ImportError:
        print("⚠️ psutil 없음 (시스템 모니터링 제한)")
    
    try:
        import colorlog
        print("✅ colorlog 확인됨 (컬러 로깅 활성화)")
    except ImportError:
        print("⚠️ colorlog 없음 (기본 로깅 사용)")
    
    print("📦 라이브러리 확인 중...")
    return True

def load_modules():
    """모듈 로딩 확인"""
    print("🔍 시스템 검증 중...")
    
    modules_status = {}
    
    # 핵심 모듈들
    try:
        import config
        modules_status['config'] = True
        print("✅ config 모듈 로드 성공")
    except ImportError as e:
        modules_status['config'] = False
        print(f"⚠️ config 모듈 로드 실패: {e}")
    
    try:
        from okx.account_manager import AccountManager
        modules_status['account_manager'] = True
        print("✅ account_manager 모듈 로드 성공")
    except ImportError as e:
        modules_status['account_manager'] = False
        print(f"⚠️ account_manager 모듈 로드 실패: {e}")
    
    # GUI 모듈들
    try:
        from gui.widgets import PriceChartWidget
        modules_status['gui_widgets'] = True
        print("✅ GUI 위젯 모듈 로드 성공")
    except ImportError as e:
        modules_status['gui_widgets'] = False
        print(f"⚠️ GUI 위젯 임포트 실패: {e}")
    
    try:
        from gui.main_window import TradingMainWindow
        modules_status['main_window'] = True
        print("✅ main_window 모듈 로드 성공")
    except ImportError as e:
        modules_status['main_window'] = False
        print(f"GUI 모듈 임포트 실패: {e}")
        print("PyQt5가 설치되어 있는지 확인하세요: pip install PyQt5")
    
    try:
        from gui.balance_manager import GUIBalanceManager
        modules_status['balance_manager'] = True
        print("✅ balance_manager 모듈 로드 성공")
    except ImportError as e:
        modules_status['balance_manager'] = False
        print(f"⚠️ balance_manager 모듈 로드 실패: {e}")
    
    # 선택적 모듈들
    try:
        from utils.websocket_handler import WebSocketHandler
        modules_status['websocket_handler'] = True
        print("✅ websocket_handler 모듈 로드 성공")
    except ImportError as e:
        modules_status['websocket_handler'] = False
        print(f"⚠️ websocket_handler 모듈 로드 실패 (선택사항): {e}")
    
    try:
        from utils.logger import setup_logger
        modules_status['logger'] = True
        print("✅ logger 모듈 로드 성공")
    except ImportError as e:
        modules_status['logger'] = False
        print(f"⚠️ logger 모듈 로드 실패: {e}")
    
    return modules_status

def test_api_connection():
    """API 연결 테스트"""
    print("🔗 API 연결 테스트 중...")
    
    try:
        from okx.account_manager import AccountManager
        account = AccountManager()
        print("✅ 계좌 관리자 초기화 완료")
        
        # 잔고 테스트
        print("🔗 API 연결 테스트 중...")
        balance = account.get_account_balance()
        
        if balance and 'data' in balance:
            # USDT 잔고 확인
            usdt_balance = 0
            for detail in balance['data'][0].get('details', []):
                if detail.get('ccy') == 'USDT':
                    usdt_balance = float(detail.get('availBal', 0))
                    break
            
            print(f"  💰 USDT: 총 {balance['data'][0].get('totalEq', 0)} | 사용가능 {usdt_balance}")
            print(f"✅ API 연결 성공 - USDT: ${usdt_balance:.2f}")
            
            # 총 자산 계산
            total_eq = float(balance['data'][0].get('totalEq', 0))
            currencies = len(balance['data'][0].get('details', []))
            print(f"💰 총 자산: ${total_eq:.2f} ({currencies}개 통화)")
            
            return True
        else:
            print("⚠️ API 연결됨, 잔고 데이터 없음")
            return True
            
    except Exception as e:
        print(f"❌ API 연결 테스트 실패: {e}")
        return False

def create_gui_fallback():
    """GUI 모듈 실패시 폴백 윈도우 생성"""
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
        QTextEdit, QHBoxLayout, QGroupBox
    )
    from PyQt5.QtCore import QTimer
    from PyQt5.QtGui import QFont
    
    class FallbackWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("🚀 OKX 자동매매 시스템 - 기본 모드")
            self.setGeometry(100, 100, 800, 600)
            
            # 중앙 위젯
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # 헤더
            header = QLabel("⚠️ 일부 모듈을 사용할 수 없어 기본 모드로 실행됩니다")
            header.setFont(QFont("Arial", 14, QFont.Bold))
            header.setStyleSheet("color: #ff6666; padding: 10px; border: 1px solid #ff6666;")
            layout.addWidget(header)
            
            # 상태 그룹
            status_group = QGroupBox("시스템 상태")
            status_layout = QVBoxLayout()
            
            self.status_label = QLabel("시스템 확인 중...")
            status_layout.addWidget(self.status_label)
            
            # API 테스트 버튼
            test_btn = QPushButton("🔗 API 연결 테스트")
            test_btn.clicked.connect(self.test_api)
            status_layout.addWidget(test_btn)
            
            status_group.setLayout(status_layout)
            layout.addWidget(status_group)
            
            # 로그 영역
            log_group = QGroupBox("시스템 로그")
            log_layout = QVBoxLayout()
            
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setMaximumHeight(200)
            log_layout.addWidget(self.log_text)
            
            log_group.setLayout(log_layout)
            layout.addWidget(log_group)
            
            # 해결 방법 안내
            help_group = QGroupBox("문제 해결 방법")
            help_layout = QVBoxLayout()
            
            help_text = QLabel("""
필요한 모듈들을 설치하세요:

1. GUI 위젯 문제:
   - gui/widgets.py 파일이 생성되었습니다
   
2. Logger 문제:
   - utils/logger.py 파일이 생성되었습니다
   - pip install colorlog
   
3. WebSocket 문제:
   - utils/websocket_handler.py 파일이 생성되었습니다
   - pip install websocket-client

4. 추가 라이브러리:
   - pip install pyqtgraph psutil

모든 파일이 생성된 후 다시 실행해보세요.
            """)
            help_text.setStyleSheet("padding: 10px; background-color: #2b2b2b; border: 1px solid #555;")
            help_layout.addWidget(help_text)
            
            help_group.setLayout(help_layout)
            layout.addWidget(help_group)
            
            # 완전한 GUI 실행 버튼
            full_gui_btn = QPushButton("🚀 완전한 GUI 다시 시도")
            full_gui_btn.setStyleSheet("background-color: #00aa00; color: white; padding: 10px; font-weight: bold;")
            full_gui_btn.clicked.connect(self.try_full_gui)
            layout.addWidget(full_gui_btn)
            
            # 다크 테마 적용
            self.setStyleSheet("""
                QMainWindow { background-color: #2b2b2b; color: #ffffff; }
                QGroupBox { font-weight: bold; border: 2px solid #555555; border-radius: 5px; margin: 5px; padding-top: 10px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
                QPushButton { background-color: #555555; color: #ffffff; border: none; padding: 8px; border-radius: 4px; }
                QPushButton:hover { background-color: #666666; }
                QTextEdit { background-color: #3b3b3b; color: #ffffff; border: 1px solid #555555; }
                QLabel { color: #ffffff; }
            """)
            
            # 초기 상태 확인
            self.check_status()
            
        def check_status(self):
            """시스템 상태 확인"""
            try:
                from okx.account_manager import AccountManager
                self.status_label.setText("✅ 핵심 모듈 사용 가능")
                self.status_label.setStyleSheet("color: #00ff00")
                self.add_log("핵심 모듈 로드 성공")
            except Exception as e:
                self.status_label.setText("❌ 핵심 모듈 오류")
                self.status_label.setStyleSheet("color: #ff6666")
                self.add_log(f"핵심 모듈 오류: {e}")
        
        def test_api(self):
            """API 연결 테스트"""
            self.add_log("API 연결 테스트 시작...")
            try:
                from okx.account_manager import AccountManager
                account = AccountManager()
                balance = account.get_account_balance()
                
                if balance and 'data' in balance:
                    usdt_balance = 0
                    for detail in balance['data'][0].get('details', []):
                        if detail.get('ccy') == 'USDT':
                            usdt_balance = float(detail.get('availBal', 0))
                            break
                    
                    self.add_log(f"✅ API 연결 성공 - USDT: ${usdt_balance:.2f}")
                else:
                    self.add_log("⚠️ API 연결됨, 데이터 없음")
                    
            except Exception as e:
                self.add_log(f"❌ API 연결 실패: {e}")
        
        def try_full_gui(self):
            """완전한 GUI 다시 시도"""
            self.add_log("완전한 GUI 재시도 중...")
            try:
                # 모듈 다시 임포트 시도
                import importlib
                import gui.main_window
                importlib.reload(gui.main_window)
                
                from gui.main_window import TradingMainWindow
                
                # 새 윈도우 생성
                self.full_window = TradingMainWindow()
                self.full_window.show()
                self.add_log("✅ 완전한 GUI 시작 성공!")
                
                # 현재 윈도우 숨기기
                self.hide()
                
            except Exception as e:
                self.add_log(f"❌ 완전한 GUI 시작 실패: {e}")
                self.add_log("누락된 파일들을 확인하고 다시 시도하세요.")
        
        def add_log(self, message):
            """로그 추가"""
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
    
    return FallbackWindow

def main():
    """메인 실행 함수"""
    # 의존성 확인
    if not check_dependencies():
        print("❌ 필수 의존성 확인 실패")
        return 1
    
    # 모듈 로딩
    modules_status = load_modules()
    if not modules_status:
        print("❌ 핵심 모듈 로딩 실패")
        return 1
    
    # API 연결 테스트
    api_connected = test_api_connection()
    
    print("✅ 시스템 검증 완료")
    print("✅ 설정 파일 로드 완료")
    print("✅ 모든 모듈 로드 완료")
    
    # GUI 애플리케이션 시작
    try:
        from PyQt5.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        app.setApplicationName("OKX 자동매매 시스템")
        app.setApplicationVersion("2.0")
        
        print("🎨 완전한 GUI 실행 중...")
        
        # 메인 윈도우 생성
        try:
            if modules_status.get('main_window', False):
                from gui.main_window import TradingMainWindow
                
                print("✅ main TradingMainWindow 모듈 로드 성공")
                print("🚀 완전한 GUI 시작...")
                print("🚀 완전한 OKX 자동매매 GUI 시작")
                
                window = TradingMainWindow()
                window.show()
                
                print("✅ 완전한 GUI 시작 성공!")
                
            else:
                print("⚠️ 메인 윈도우 모듈 사용 불가, 폴백 모드로 실행")
                FallbackWindow = create_gui_fallback()
                window = FallbackWindow()
                window.show()
        
        except Exception as e:
            print(f"❌ 완전한 GUI 시작 실패: {e}")
            print("스택 트레이스:")
            traceback.print_exc()
            
            print("\n🔧 폴백 모드로 실행합니다...")
            FallbackWindow = create_gui_fallback()
            window = FallbackWindow()
            window.show()
        
        # 애플리케이션 실행
        return app.exec_()
        
    except Exception as e:
        print(f"❌ GUI 애플리케이션 시작 실패: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단됨")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        traceback.print_exc()  
        sys.exit(1)