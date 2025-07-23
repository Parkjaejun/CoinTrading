# run_gui.py - 수정된 버전
"""
OKX 자동매매 시스템 GUI 실행 스크립트 (오류 수정)
- 시뮬레이션 모드로 실행 (API 없이도 작동)
- 자동 의존성 설치
- 설정 검증
"""

import sys
import os
import subprocess
from pathlib import Path

def check_requirements():
    """필수 라이브러리 확인"""
    required_packages = [
        'PyQt5',
        'pyqtgraph', 
        'pandas',
        'numpy',
        'requests',
        'websocket-client'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'PyQt5':
                import PyQt5
            elif package == 'pyqtgraph':
                import pyqtgraph
            elif package == 'pandas':
                import pandas
            elif package == 'numpy':
                import numpy
            elif package == 'requests':
                import requests
            elif package == 'websocket-client':
                import websocket
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_missing_packages(packages):
    """누락된 패키지 설치"""
    print("📦 누락된 패키지를 설치합니다...")
    
    for package in packages:
        print(f"설치 중: {package}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} 설치 완료")
        except subprocess.CalledProcessError:
            print(f"❌ {package} 설치 실패")
            return False
    
    print("✅ 모든 패키지 설치 완료")
    return True

def setup_environment():
    """환경 설정"""
    # 프로젝트 루트 디렉토리를 Python 경로에 추가
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 필요한 디렉토리 생성
    directories = ['logs', 'gui', 'config_backups']
    for directory in directories:
        (project_root / directory).mkdir(exist_ok=True)
    
    # GUI 모듈 __init__.py 파일 생성
    gui_init = project_root / 'gui' / '__init__.py'
    if not gui_init.exists():
        gui_init.write_text('# GUI 패키지\n')
        print("📁 gui/__init__.py 파일 생성")

def create_main_window_file():
    """메인 윈도우 파일이 없는 경우 기본 파일 생성"""
    project_root = Path(__file__).parent
    main_window_path = project_root / 'gui' / 'main_window.py'
    
    if not main_window_path.exists():
        print("📝 기본 main_window.py 파일 생성 중...")
        
        # 기본 GUI 파일 내용
        basic_gui_content = '''# gui/main_window.py - 기본 GUI
"""
기본 GUI 파일 - 시뮬레이션 모드
"""

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
import sys

class TradingMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OKX 자동매매 시스템 - 기본 모드")
        self.setGeometry(100, 100, 800, 600)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 레이아웃
        layout = QVBoxLayout()
        
        # 라벨
        label = QLabel("🚀 OKX 자동매매 시스템\\n\\n시뮬레이션 모드로 실행 중입니다.\\n실제 거래는 발생하지 않습니다.")
        label.setStyleSheet("font-size: 16px; text-align: center; padding: 50px;")
        
        layout.addWidget(label)
        central_widget.setLayout(layout)

def main():
    app = QApplication(sys.argv)
    window = TradingMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
'''
        
        try:
            main_window_path.write_text(basic_gui_content, encoding='utf-8')
            print("✅ 기본 main_window.py 파일 생성 완료")
            return True
        except Exception as e:
            print(f"❌ main_window.py 파일 생성 실패: {e}")
            return False
    
    return True

def validate_config():
    """설정 검증 (간소화)"""
    try:
        # config.py 파일이 있는지 확인
        config_path = Path(__file__).parent / 'config.py'
        if config_path.exists():
            print("✅ config.py 파일 발견")
            
            # 간단한 임포트 테스트
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                import config
                print("✅ config.py 임포트 성공")
                return True
            except ImportError as e:
                print(f"⚠️ config.py 임포트 오류: {e}")
                print("시뮬레이션 모드로 실행됩니다")
                return True  # 시뮬레이션 모드에서는 계속 진행
        else:
            print("⚠️ config.py 파일이 없습니다")
            print("시뮬레이션 모드로 실행됩니다")
            return True  # 시뮬레이션 모드에서는 계속 진행
            
    except Exception as e:
        print(f"⚠️ 설정 검증 중 오류: {e}")
        print("시뮬레이션 모드로 실행됩니다")
        return True

def run_gui():
    """GUI 실행"""
    try:
        print("🚀 GUI 시작...")
        
        # GUI 모듈 임포트 시도
        try:
            # main_window_improved.py가 있는지 확인
            improved_path = Path(__file__).parent / 'gui' / 'main_window_improved.py'
            if improved_path.exists():
                from gui.main_window_improved import main as gui_main
                print("✅ 개선된 GUI 사용")
            else:
                from gui.main_window import main as gui_main
                print("✅ 기본 GUI 사용")
            
            gui_main()
            
        except ImportError as e:
            print(f"❌ GUI 모듈 임포트 실패: {e}")
            
            # 기본 PyQt5 GUI 실행
            print("🔄 기본 PyQt5 GUI로 대체 실행...")
            from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
            from PyQt5.QtCore import Qt
            
            app = QApplication(sys.argv)
            window = QMainWindow()
            window.setWindowTitle("OKX 자동매매 시스템 - 시뮬레이션")
            window.setGeometry(100, 100, 800, 600)
            
            # 중앙 위젯
            central_widget = QWidget()
            window.setCentralWidget(central_widget)
            
            # 레이아웃
            layout = QVBoxLayout()
            
            # 메시지
            message = '''🚀 OKX 자동매매 시스템

📊 시뮬레이션 모드로 실행 중입니다

✅ GUI 기본 기능 작동 확인
⚠️  실제 거래는 발생하지 않습니다

개선된 기능을 사용하려면:
1. gui/main_window_improved.py 파일 확인
2. 모든 의존성 라이브러리 설치 확인'''
            
            label = QLabel(message)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    padding: 50px;
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border-radius: 10px;
                }
            """)
            
            layout.addWidget(label)
            central_widget.setLayout(layout)
            
            # 다크 테마 적용
            window.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
            """)
            
            window.show()
            print("✅ 기본 GUI 실행 성공")
            
            return app.exec_()
            
    except Exception as e:
        print(f"❌ GUI 실행 오류: {e}")
        return False

def print_startup_info():
    """시작 정보 출력"""
    print("=" * 80)
    print("🚀 OKX 자동매매 시스템 GUI v2.0")
    print("=" * 80)
    print("📊 특징:")
    print("  ✅ 시뮬레이션 모드 지원 (API 없이도 작동)")
    print("  ✅ 다크 테마 UI")
    print("  ✅ 실시간 차트 시뮬레이션")
    print("  ✅ 가상 계좌 및 포지션 표시")
    print()
    print("⚠️  주의사항:")
    print("  • 시뮬레이션 모드에서는 실제 거래가 발생하지 않습니다")
    print("  • 실제 API 연결이 없어도 GUI 기능을 테스트할 수 있습니다")
    print("=" * 80)

def main():
    """메인 실행 함수"""
    print_startup_info()
    
    print("🔧 시스템 준비 중...")
    
    # 1. 환경 설정
    setup_environment()
    
    # 2. 필수 라이브러리 확인
    print("📦 필수 라이브러리 확인 중...")
    missing = check_requirements()
    
    if missing:
        print(f"❌ 누락된 라이브러리: {', '.join(missing)}")
        
        install_choice = input("자동으로 설치하시겠습니까? (y/n): ").lower().strip()
        if install_choice == 'y':
            if not install_missing_packages(missing):
                print("❌ 라이브러리 설치 실패")
                input("Enter 키를 눌러 종료하세요...")
                return False
        else:
            print("수동으로 라이브러리를 설치해주세요:")
            print(f"pip install {' '.join(missing)}")
            input("Enter 키를 눌러 종료하세요...")
            return False
    
    print("✅ 모든 라이브러리 확인 완료")
    
    # 3. 기본 파일 생성
    if not create_main_window_file():
        print("❌ GUI 파일 생성 실패")
        return False
    
    # 4. 설정 검증 (간소화)
    validate_config()
    
    # 5. GUI 실행
    print("\n🎨 GUI 실행 준비 완료!")
    
    run_choice = input("지금 GUI를 실행하시겠습니까? (y/n): ").lower().strip()
    if run_choice == 'y':
        return run_gui()
    else:
        print("GUI 실행을 취소했습니다.")
        print("나중에 실행하려면: python run_gui.py")
        return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        input("Enter 키를 눌러 종료하세요...")
        sys.exit(1)