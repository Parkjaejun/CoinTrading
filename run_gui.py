# run_gui.py - Real Trading 전용 버전
"""
OKX 자동매매 시스템 GUI 실행 스크립트 (Real Trading 전용)
- main.py의 실제 거래 시스템과 완전 통합
- 실제 API 연결, 실제 자본, 실제 거래
- 가상 거래 기능 완전 제거
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path
from datetime import datetime

def print_startup_banner():
    """시작 배너 출력"""
    print("=" * 80)
    print("🚀 OKX 자동매매 시스템 - Real Trading GUI v4.0")
    print("=" * 80)
    print("💰 실제 거래 특징:")
    print("  ✅ 실제 OKX API 연결")
    print("  ✅ 실제 USDT 잔액 사용")
    print("  ✅ 실제 BTC 가격 데이터")
    print("  ✅ 실제 주문 실행")
    print("  ✅ 실제 포지션 관리")
    print()
    print("🎯 지원 모드:")
    print("  📊 GUI 모드: 실시간 차트와 거래 대시보드")
    print("  📋 콘솔 모드: 터미널에서 거래 실행")
    print()
    print("⚠️  중요 주의사항:")
    print("  • 실제 자금으로 거래가 실행됩니다")
    print("  • API 키와 충분한 USDT 잔액이 필요합니다")
    print("  • 손실 위험이 있으니 신중하게 사용하세요")
    print("=" * 80)

def check_trading_requirements():
    """실제 거래에 필요한 라이브러리 확인"""
    # 실제 거래 시스템 라이브러리
    required_packages = [
        'PyQt5',           # GUI
        'pyqtgraph',       # 차트
        'requests',        # API 호출
        'websocket-client', # 실시간 데이터
        'pandas',          # 데이터 처리
        'numpy',           # 수치 계산
    ]
    
    # 선택적 라이브러리
    optional_packages = [
        'psutil',          # 시스템 모니터링
    ]
    
    missing_packages = []
    
    # 필수 패키지 확인
    for package in required_packages:
        try:
            if package == 'PyQt5':
                import PyQt5
            elif package == 'pyqtgraph':
                import pyqtgraph
            elif package == 'requests':
                import requests
            elif package == 'websocket-client':
                import websocket
            elif package == 'pandas':
                import pandas
            elif package == 'numpy':
                import numpy
        except ImportError:
            missing_packages.append(package)
    
    # 선택적 패키지 확인 (오류 무시)
    optional_missing = []
    for package in optional_packages:
        try:
            if package == 'psutil':
                import psutil
        except ImportError:
            optional_missing.append(package)
    
    return missing_packages, optional_missing

def install_packages_with_retry(packages):
    """패키지 설치 (재시도 포함)"""
    if not packages:
        return True
    
    print(f"📦 {len(packages)}개 필수 패키지 설치 중...")
    
    # 1차: 일괄 설치 시도
    try:
        cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade'] + packages
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ 모든 패키지 설치 완료")
            return True
        else:
            print(f"⚠️ 일괄 설치 실패: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print("⏰ 설치 시간 초과")
    except Exception as e:
        print(f"❌ 설치 오류: {e}")
    
    # 2차: 개별 설치
    print("🔄 개별 패키지 설치 시도...")
    success_count = 0
    
    for package in packages:
        print(f"  설치 중: {package}")
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '--upgrade', package],
                capture_output=True, 
                text=True, 
                timeout=180,
                check=True
            )
            print(f"  ✅ {package} 완료")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"  ❌ {package} 실패: {e.stderr[:100] if e.stderr else 'Unknown error'}")
        except subprocess.TimeoutExpired:
            print(f"  ⏰ {package} 시간 초과")
        except Exception as e:
            print(f"  ❌ {package} 오류: {e}")
        
        time.sleep(1)  # 설치 간 잠시 대기
    
    success_rate = success_count / len(packages)
    print(f"📊 설치 성공률: {success_rate*100:.1f}% ({success_count}/{len(packages)})")
    
    return success_rate >= 0.8  # 80% 이상 성공시 통과

def setup_trading_environment():
    """실제 거래 환경 설정"""
    project_root = Path(__file__).parent
    
    # Python 경로 설정
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 실제 거래에 필요한 디렉토리 생성
    directories = [
        'logs',           # 거래 로그
        'gui',            # GUI 파일들
        'okx',            # OKX API 모듈
        'strategy',       # 거래 전략
        'utils',          # 유틸리티
        'config_backups', # 설정 백업
        'data'            # 데이터 파일
    ]
    
    created_dirs = []
    for directory in directories:
        dir_path = project_root / directory
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            created_dirs.append(directory)
    
    # 필수 __init__.py 파일 생성
    init_files = [
        'gui/__init__.py',
        'okx/__init__.py',
        'strategy/__init__.py',
        'utils/__init__.py'
    ]
    
    for init_file in init_files:
        init_path = project_root / init_file
        if not init_path.exists():
            init_path.write_text('# Package initialization for real trading\n')
    
    if created_dirs:
        print(f"📁 생성된 디렉토리: {', '.join(created_dirs)}")
    
    print("✅ 실제 거래 환경 설정 완료")

def validate_trading_system():
    """실제 거래 시스템 검증"""
    project_root = Path(__file__).parent
    
    # 핵심 파일 확인
    required_files = [
        'main.py',                    # 메인 거래 시스템
        'config.py',                  # 설정 파일
        'okx/account.py',             # 계좌 관리
        'okx/websocket_handler.py',   # 실시간 데이터
        'strategy/dual_manager.py',   # 듀얼 전략
        'utils/logger.py',            # 로거
    ]
    
    missing_files = []
    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 필수 파일 누락: {len(missing_files)}개")
        for file in missing_files:
            print(f"  - {file}")
        return False
    
    # 설정 파일 검증
    try:
        sys.path.insert(0, str(project_root))
        import config
        
        # API 키 확인
        required_vars = ['API_KEY', 'API_SECRET', 'PASSPHRASE']
        missing_vars = []
        
        for var in required_vars:
            if not hasattr(config, var) or not getattr(config, var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ config.py에 다음 변수가 누락됨: {', '.join(missing_vars)}")
            print("OKX API 키를 올바르게 설정해주세요.")
            return False
        
        print("✅ 설정 파일 검증 완료")
        return True
        
    except ImportError as e:
        print(f"❌ config.py 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 설정 검증 오류: {e}")
        return False

def test_api_connection():
    """API 연결 테스트"""
    try:
        print("🔗 OKX API 연결 테스트 중...")
        
        # main.py의 TradingSystem 활용
        from main import TradingSystem
        
        trading_system = TradingSystem()
        
        # 간단한 API 테스트 (계좌 조회)
        from okx.account import AccountManager
        account = AccountManager()
        
        balances = account.get_account_balance()
        if balances:
            print("✅ API 연결 성공")
            
            # USDT 잔액 확인
            usdt_balance = balances.get('USDT', {}).get('available', 0)
            print(f"💰 사용 가능한 USDT: ${usdt_balance:.2f}")
            
            if usdt_balance < 10:
                print("⚠️ USDT 잔액이 부족합니다. 거래 전 충분한 잔액을 확보하세요.")
            
            return True
        else:
            print("❌ API 연결 실패 - 계좌 정보를 가져올 수 없습니다")
            return False
            
    except ImportError as e:
        print(f"❌ 거래 시스템 모듈 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ API 연결 테스트 실패: {e}")
        return False

def create_trading_gui_fallback():
    """실제 거래용 GUI fallback 생성"""
    project_root = Path(__file__).parent
    gui_path = project_root / 'gui' / 'main_window.py'
    
    if gui_path.exists():
        return  # 이미 존재하면 생성하지 않음
    
    trading_gui_content = '''# gui/main_window.py - Real Trading GUI
"""
실제 거래용 GUI - main.py의 TradingSystem과 연동
"""

import sys
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QTabWidget, QGroupBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime

# main.py의 거래 시스템 임포트
try:
    from main import TradingSystem
    from okx.account import AccountManager
    from strategy.dual_manager import DualStrategyManager
    TRADING_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 거래 시스템 임포트 실패: {e}")
    TRADING_SYSTEM_AVAILABLE = False

class TradingThread(QThread):
    """실제 거래 백그라운드 스레드"""
    
    # 시그널 정의
    account_updated = pyqtSignal(dict)
    position_updated = pyqtSignal(list)
    trade_executed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.trading_system = None
        self.is_running = False
        
    def run(self):
        """거래 시스템 실행"""
        if not TRADING_SYSTEM_AVAILABLE:
            self.error_occurred.emit("거래 시스템 모듈을 찾을 수 없습니다")
            return
        
        try:
            self.is_running = True
            self.status_changed.emit("🔧 거래 시스템 초기화 중...")
            
            # TradingSystem 인스턴스 생성
            self.trading_system = TradingSystem()
            
            # 시스템 초기화
            if not self.trading_system.initialize_system():
                self.error_occurred.emit("거래 시스템 초기화 실패")
                return
            
            self.status_changed.emit("🚀 실제 거래 시작")
            
            # 거래 시작
            self.trading_system.start_trading()
            
        except Exception as e:
            self.error_occurred.emit(f"거래 시스템 오류: {str(e)}")
        finally:
            self.is_running = False
            self.status_changed.emit("⏹️ 거래 중지됨")
    
    def stop_trading(self):
        """거래 중지"""
        if self.trading_system and self.is_running:
            try:
                self.trading_system.stop_trading()
                self.is_running = False
                self.status_changed.emit("🛑 거래 시스템 종료")
            except Exception as e:
                self.error_occurred.emit(f"거래 종료 오류: {str(e)}")

class RealTradingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OKX 자동매매 시스템 - Real Trading")
        self.setGeometry(100, 100, 1400, 900)
        
        # 거래 스레드
        self.trading_thread = None
        
        # 데이터
        self.account_balance = {}
        self.active_positions = []
        
        self.setup_ui()
        self.setup_timers()
        self.apply_dark_theme()
        
        # 시작시 계좌 정보 로드
        self.load_account_info()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        
        # 상단 상태바
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("🔴 거래 중지됨")
        self.balance_label = QLabel("💰 잔고: 로딩 중...")
        self.time_label = QLabel()
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.balance_label)
        status_layout.addStretch()
        status_layout.addWidget(self.time_label)
        
        main_layout.addLayout(status_layout)
        
        # 탭 위젯
        tab_widget = QTabWidget()
        
        # 대시보드 탭
        dashboard_tab = self.create_dashboard_tab()
        tab_widget.addTab(dashboard_tab, "📊 대시보드")
        
        # 포지션 탭
        position_tab = self.create_position_tab()
        tab_widget.addTab(position_tab, "💼 포지션")
        
        # 로그 탭
        log_tab = self.create_log_tab()
        tab_widget.addTab(log_tab, "📝 로그")
        
        main_layout.addWidget(tab_widget)
        
        # 하단 컨트롤
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 거래 시작")
        self.stop_btn = QPushButton("⏹️ 거래 중지")
        self.refresh_btn = QPushButton("🔄 새로고침")
        self.emergency_btn = QPushButton("🚨 긴급 정지")
        
        self.start_btn.clicked.connect(self.start_trading)
        self.stop_btn.clicked.connect(self.stop_trading)
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.emergency_btn.clicked.connect(self.emergency_stop)
        
        # 초기 상태
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.refresh_btn)
        control_layout.addWidget(self.emergency_btn)
        control_layout.addStretch()
        
        main_layout.addLayout(control_layout)
        
        central_widget.setLayout(main_layout)
    
    def create_dashboard_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 계좌 정보
        account_group = QGroupBox("💰 계좌 정보")
        account_layout = QGridLayout()
        
        self.usdt_label = QLabel("USDT: 로딩 중...")
        self.btc_label = QLabel("BTC: 로딩 중...")
        self.total_label = QLabel("총 자산: 로딩 중...")
        
        account_layout.addWidget(QLabel("사용 가능:"), 0, 0)
        account_layout.addWidget(self.usdt_label, 0, 1)
        account_layout.addWidget(QLabel("BTC 보유:"), 1, 0)
        account_layout.addWidget(self.btc_label, 1, 1)
        account_layout.addWidget(QLabel("총 자산:"), 2, 0)
        account_layout.addWidget(self.total_label, 2, 1)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        # 거래 통계
        stats_group = QGroupBox("📊 거래 통계")
        stats_layout = QGridLayout()
        
        self.trades_label = QLabel("총 거래: 0회")
        self.profit_label = QLabel("총 수익: $0.00")
        self.win_rate_label = QLabel("승률: 0%")
        
        stats_layout.addWidget(QLabel("거래 횟수:"), 0, 0)
        stats_layout.addWidget(self.trades_label, 0, 1)
        stats_layout.addWidget(QLabel("총 수익:"), 1, 0)
        stats_layout.addWidget(self.profit_label, 1, 1)
        stats_layout.addWidget(QLabel("승률:"), 2, 0)
        stats_layout.addWidget(self.win_rate_label, 2, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_position_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 활성 포지션 테이블
        position_group = QGroupBox("📈 활성 포지션")
        position_layout = QVBoxLayout()
        
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(7)
        self.position_table.setHorizontalHeaderLabels([
            "심볼", "방향", "크기", "진입가", "현재가", "PnL", "수익률"
        ])
        
        position_layout.addWidget(self.position_table)
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(400)
        
        layout.addWidget(QLabel("거래 시스템 로그:"))
        layout.addWidget(self.log_display)
        
        widget.setLayout(layout)
        return widget
    
    def setup_timers(self):
        # 시간 업데이트
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
        
        # 데이터 업데이트 (거래 중일 때만)
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_trading_data)
        self.data_timer.start(5000)  # 5초마다
    
    def update_time(self):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.setText(f"⏰ {current_time}")
    
    def load_account_info(self):
        """계좌 정보 로드"""
        if not TRADING_SYSTEM_AVAILABLE:
            self.add_log("❌ 거래 시스템을 사용할 수 없습니다")
            return
        
        try:
            account = AccountManager()
            balances = account.get_account_balance()
            
            if balances:
                self.account_balance = balances
                
                usdt_balance = balances.get('USDT', {}).get('available', 0)
                btc_balance = balances.get('BTC', {}).get('available', 0)
                
                self.balance_label.setText(f"💰 USDT: ${usdt_balance:.2f}")
                self.usdt_label.setText(f"${usdt_balance:.6f}")
                self.btc_label.setText(f"{btc_balance:.8f} BTC")
                
                # 총 자산 계산 (간단한 USDT 기준)
                total_value = usdt_balance  # 실제로는 BTC 가격 계산 필요
                self.total_label.setText(f"${total_value:.2f}")
                
                self.add_log(f"✅ 계좌 정보 업데이트: USDT ${usdt_balance:.2f}")
            else:
                self.add_log("❌ 계좌 정보를 가져올 수 없습니다")
                
        except Exception as e:
            self.add_log(f"❌ 계좌 정보 로드 오류: {str(e)}")
    
    def start_trading(self):
        """거래 시작"""
        if not TRADING_SYSTEM_AVAILABLE:
            QMessageBox.warning(self, "오류", "거래 시스템 모듈을 찾을 수 없습니다.\\nmain.py 파일이 있는지 확인해주세요.")
            return
        
        # 확인 메시지
        reply = QMessageBox.question(
            self, 
            "거래 시작 확인", 
            "실제 자금으로 거래를 시작하시겠습니까?\\n\\n⚠️ 손실 위험이 있습니다.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 거래 스레드 시작
        if self.trading_thread and self.trading_thread.isRunning():
            self.add_log("⚠️ 이미 거래가 실행 중입니다")
            return
        
        self.trading_thread = TradingThread()
        self.trading_thread.status_changed.connect(self.on_status_changed)
        self.trading_thread.error_occurred.connect(self.on_error_occurred)
        self.trading_thread.start()
        
        # UI 상태 업데이트
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.add_log("🚀 거래 시스템 시작 중...")
    
    def stop_trading(self):
        """거래 중지"""
        if self.trading_thread and self.trading_thread.isRunning():
            self.trading_thread.stop_trading()
            self.trading_thread.wait(5000)  # 5초 대기
        
        # UI 상태 업데이트
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.add_log("⏹️ 거래 시스템 중지")
    
    def emergency_stop(self):
        """긴급 정지"""
        reply = QMessageBox.critical(
            self,
            "긴급 정지",
            "모든 거래를 즉시 중단하시겠습니까?\\n\\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.stop_trading()
            self.add_log("🚨 긴급 정지 실행됨")
    
    def refresh_data(self):
        """데이터 새로고침"""
        self.load_account_info()
        self.add_log("🔄 데이터 새로고침 완료")
    
    def update_trading_data(self):
        """거래 데이터 업데이트 (거래 중일 때만)"""
        if self.trading_thread and self.trading_thread.isRunning():
            self.load_account_info()
    
    def on_status_changed(self, status):
        """상태 변경 처리"""
        self.status_label.setText(status)
        self.add_log(status)
    
    def on_error_occurred(self, error_msg):
        """오류 발생 처리"""
        self.add_log(f"❌ {error_msg}")
        
        # UI 상태 복원
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def add_log(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        self.log_display.append(log_message)
        print(log_message)
    
    def apply_dark_theme(self):
        """다크 테마 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox {
                border: 2px solid #444444;
                border-radius: 8px;
                margin-top: 1ex;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
            QTextEdit, QTableWidget {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px;
            }
            QLabel {
                color: #ffffff;
                padding: 2px;
            }
            QTabWidget::pane {
                border: 1px solid #444444;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 10px 20px;
                border: 1px solid #444444;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QTableWidget {
                gridline-color: #444444;
                alternate-background-color: #323232;
                selection-background-color: #4CAF50;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #444444;
                font-weight: bold;
            }
        """)
    
    def closeEvent(self, event):
        """창 종료 이벤트"""
        if self.trading_thread and self.trading_thread.isRunning():
            reply = QMessageBox.question(
                self, 
                "종료 확인", 
                "거래가 실행 중입니다. 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.stop_trading()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    """메인 GUI 함수"""
    app = QApplication(sys.argv)
    app.setApplicationName("OKX 자동매매 시스템 - Real Trading")
    app.setStyle('Fusion')
    
    # 시스템 가용성 확인
    if not TRADING_SYSTEM_AVAILABLE:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "시스템 오류",
            "거래 시스템 모듈을 찾을 수 없습니다.\\n\\n"
            "다음 파일들이 있는지 확인해주세요:\\n"
            "- main.py\\n"
            "- okx/account.py\\n"
            "- strategy/dual_manager.py"
        )
        return False
    
    window = RealTradingWindow()
    window.show()
    
    print("🚀 Real Trading GUI 시작")
    print("💰 실제 자금으로 거래가 실행됩니다")
    print("⚠️ 신중하게 사용하세요")
    
    return app.exec_() == 0

if __name__ == "__main__":
    main()
'''
    
    try:
        gui_path.write_text(trading_gui_content, encoding='utf-8')
        print("📝 Real Trading GUI 생성 완료")
    except Exception as e:
        print(f"❌ GUI 생성 실패: {e}")

def run_console_trading(args):
    """콘솔 모드 실제 거래 실행"""
    print("📋 콘솔 모드 실제 거래 시작")
    
    try:
        # main.py의 TradingSystem 직접 실행
        from main import TradingSystem
        
        print("🔧 거래 시스템 초기화 중...")
        trading_system = TradingSystem()
        
        if not trading_system.initialize_system():
            print("❌ 거래 시스템 초기화 실패")
            return False
        
        print("🚀 실제 거래 시작")
        trading_system.start_trading()
        
        return True
        
    except ImportError as e:
        print(f"❌ 거래 시스템 모듈 임포트 실패: {e}")
        print("main.py 파일이 있는지 확인하세요.")
        return False
        
    except Exception as e:
        print(f"❌ 콘솔 거래 시스템 오류: {e}")
        return False

def run_gui_trading(args):
    """GUI 모드 실제 거래 실행"""
    print("🎨 GUI 모드 실제 거래 시작")
    
    try:
        # 1차: 기존 GUI 시도
        try:
            from gui.main_window import main as gui_main
            print("✅ 기존 Real Trading GUI 실행")
            return gui_main()
            
        except ImportError:
            print("⚠️ 기존 GUI 모듈 없음, Fallback GUI 생성...")
            
        # 2차: Fallback GUI 사용
        from PyQt5.QtWidgets import QApplication
        from gui.main_window import RealTradingWindow
        
        app = QApplication(sys.argv)
        app.setApplicationName("OKX 자동매매 시스템 - Real Trading")
        app.setStyle('Fusion')
        
        window = RealTradingWindow()
        window.show()
        
        print("✅ Real Trading GUI 실행")
        return app.exec_() == 0
        
    except ImportError as e:
        print(f"❌ GUI 라이브러리 오류: {e}")
        print("PyQt5가 설치되지 않았습니다. 콘솔 모드를 사용하세요:")
        print(f"python {sys.argv[0]} --console")
        return False
        
    except Exception as e:
        print(f"❌ GUI 실행 오류: {e}")
        return False

def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description='OKX 자동매매 시스템 - Real Trading 전용',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python run_gui.py                    # GUI 모드 (기본값)
  python run_gui.py --console          # 콘솔 모드
  python run_gui.py --test-api         # API 연결 테스트만
        """
    )
    
    parser.add_argument(
        '--console', 
        action='store_true', 
        help='콘솔 모드로 실행 (GUI 없음)'
    )
    
    parser.add_argument(
        '--test-api', 
        action='store_true',
        help='API 연결 테스트만 실행'
    )
    
    parser.add_argument(
        '--skip-deps', 
        action='store_true',
        help='의존성 검사 건너뛰기'
    )
    
    parser.add_argument(
        '--no-install', 
        action='store_true',
        help='누락된 패키지 자동 설치 안함'
    )
    
    return parser.parse_args()

def main():
    """메인 실행 함수"""
    # 시작 배너 출력
    print_startup_banner()
    
    # 명령행 인수 파싱
    args = parse_arguments()
    
    print(f"🎯 실행 모드: {'콘솔' if args.console else 'GUI'}")
    print("=" * 50)
    
    # 1. 환경 설정
    print("🔧 실제 거래 환경 설정 중...")
    setup_trading_environment()
    
    # 2. 의존성 검사 (건너뛰기 옵션 확인)
    if not args.skip_deps:
        print("📦 의존성 검사 중...")
        missing_packages, optional_missing = check_trading_requirements()
        
        if missing_packages:
            print(f"❌ 필수 패키지 누락: {', '.join(missing_packages)}")
            
            if args.no_install:
                print("자동 설치가 비활성화되어 있습니다.")
                print("수동으로 설치하세요:")
                print(f"pip install {' '.join(missing_packages)}")
                return False
            
            install_choice = input("자동으로 설치하시겠습니까? (y/n): ").lower().strip()
            if install_choice == 'y':
                if not install_packages_with_retry(missing_packages):
                    print("❌ 패키지 설치 실패")
                    return False
            else:
                print("패키지 설치를 취소했습니다.")
                return False
        
        if optional_missing:
            print(f"📋 선택적 패키지 누락: {', '.join(optional_missing)}")
            print("이 패키지들은 필수는 아니며, 성능 향상을 위한 것입니다.")
        
        print("✅ 의존성 검사 완료")
    else:
        print("⏭️ 의존성 검사 건너뛰기")
    
    # 3. 거래 시스템 검증
    print("🎯 실제 거래 시스템 검증 중...")
    if not validate_trading_system():
        print("❌ 거래 시스템 검증 실패")
        print("\n필요한 파일들:")
        print("- main.py (메인 거래 시스템)")
        print("- config.py (API 키 설정)")
        print("- okx/ 디렉토리 (OKX API 모듈들)")
        print("- strategy/ 디렉토리 (거래 전략)")
        return False
    
    # 4. API 연결 테스트
    if args.test_api:
        print("🔗 API 연결 테스트 모드")
        return test_api_connection()
    
    # 5. GUI fallback 준비
    if not args.console:
        print("🎨 GUI 파일 준비 중...")
        create_trading_gui_fallback()
    
    # 6. API 연결 확인
    print("🔗 OKX API 연결 확인 중...")
    if not test_api_connection():
        print("❌ API 연결 실패")
        print("\n해결 방법:")
        print("1. config.py에서 API 키 확인")
        print("2. OKX에서 API 권한 확인")
        print("3. 인터넷 연결 확인")
        
        continue_choice = input("그래도 계속하시겠습니까? (y/n): ").lower().strip()
        if continue_choice != 'y':
            return False
    
    print("✅ 시스템 준비 완료!")
    print("=" * 50)
    
    # 7. 실행 모드에 따른 분기
    if args.console:
        return run_console_trading(args)
    else:
        return run_gui_trading(args)

def run_interactive_mode():
    """대화형 모드 실행"""
    print("\n🔧 대화형 설정 모드")
    print("=" * 30)
    
    # 실행 모드 선택
    print("실행 모드를 선택하세요:")
    print("1. GUI 모드 (추천)")
    print("2. 콘솔 모드")
    print("3. API 테스트만")
    
    while True:
        choice = input("선택 (1-3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("올바른 번호를 입력하세요.")
    
    # 가상 args 객체 생성
    class Args:
        def __init__(self):
            self.console = (choice == '2')
            self.test_api = (choice == '3')
            self.skip_deps = False
            self.no_install = False
    
    return Args()

if __name__ == "__main__":
    try:
        # 인수가 없으면 대화형 모드
        if len(sys.argv) == 1:
            print("💬 대화형 모드로 시작합니다...")
            time.sleep(1)
            
            # 가상 args로 main 함수 실행
            original_argv = sys.argv[:]
            interactive_args = run_interactive_mode()
            
            # args를 시스템 argv로 변환
            sys.argv = ['run_gui.py']
            if interactive_args.console:
                sys.argv.append('--console')
            if interactive_args.test_api:
                sys.argv.append('--test-api')
            
            success = main()
            sys.argv = original_argv  # 복원
        else:
            success = main()
        
        if not success:
            print("\n❌ 프로그램 실행 실패")
            input("Enter 키를 눌러 종료하세요...")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n👋 사용자에 의해 중단되었습니다.")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        print("\n🔍 디버그 정보:")
        import traceback
        traceback.print_exc()
        input("Enter 키를 눌러 종료하세요...")
        sys.exit(1)