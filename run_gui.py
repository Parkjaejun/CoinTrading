# run_improved_gui.py
"""
실제 OKX 데이터 연동 GUI 실행 스크립트
- 자동 의존성 설치
- 설정 검증
- GUI 실행
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

def validate_config():
    """설정 검증"""
    try:
        from config import API_KEY, API_SECRET, PASSPHRASE
        
        errors = []
        
        if not API_KEY or API_KEY == "your_api_key_here":
            errors.append("API_KEY가 설정되지 않았습니다")
        
        if not API_SECRET or API_SECRET == "your_api_secret_here":
            errors.append("API_SECRET이 설정되지 않았습니다")
        
        if not PASSPHRASE or PASSPHRASE == "your_passphrase_here":
            errors.append("PASSPHRASE가 설정되지 않았습니다")
        
        if errors:
            print("❌ 설정 오류:")
            for error in errors:
                print(f"  - {error}")
            print("\n📝 config.py 파일을 수정하여 올바른 API 정보를 입력하세요.")
            return False
        
        print("✅ API 설정 검증 완료")
        return True
        
    except ImportError as e:
        print(f"❌ config.py 파일을 찾을 수 없습니다: {e}")
        return False

def test_api_connection():
    """API 연결 테스트"""
    try:
        print("🧪 API 연결 테스트 중...")
        
        from okx.account_manager import AccountManager
        
        account = AccountManager()
        balances = account.get_account_balance()
        
        if balances:
            print("✅ API 연결 테스트 성공")
            
            # USDT 잔고 표시
            if 'USDT' in balances:
                usdt_balance = balances['USDT']['total']
                print(f"💰 USDT 잔고: ${usdt_balance:,.2f}")
            
            return True
        else:
            print("❌ API 연결 테스트 실패 - 응답 없음")
            return False
            
    except Exception as e:
        print(f"❌ API 연결 테스트 실패: {e}")
        print("📋 해결 방법:")
        print("  1. config.py의 API 키 확인")
        print("  2. OKX API 권한 설정 확인") 
        print("  3. IP 화이트리스트 설정 확인")
        return False

def create_improved_gui_files():
    """개선된 GUI 파일들 생성"""
    project_root = Path(__file__).parent
    
    # 개선된 메인 윈도우를 기존 파일로 저장
    improved_gui_path = project_root / 'gui' / 'main_window.py'
    improved_ws_path = project_root / 'okx' / 'websocket_handler.py'
    
    print("📝 개선된 GUI 파일 확인 중...")
    
    if not improved_gui_path.exists():
        print("⚠️ gui/main_window_improved.py 파일이 없습니다.")
        print("위에서 제공한 코드를 해당 경로에 저장하세요.")
        return False
    
    if not improved_ws_path.exists():
        print("⚠️ okx/websocket_handler_improved.py 파일이 없습니다.")
        print("위에서 제공한 코드를 해당 경로에 저장하세요.")
        return False
    
    print("✅ 개선된 GUI 파일들 확인 완료")
    return True

def run_improved_gui():
    """개선된 GUI 실행"""
    try:
        print("🚀 실제 OKX 데이터 연동 GUI 시작...")
        
        # 개선된 GUI 모듈 임포트 및 실행
        from gui.main_window_improved import main as improved_gui_main
        
        improved_gui_main()
        
    except ImportError as e:
        print(f"❌ GUI 모듈 임포트 실패: {e}")
        print("📋 해결 방법:")
        print("  1. gui/main_window_improved.py 파일이 올바른 위치에 있는지 확인")
        print("  2. 모든 필수 라이브러리가 설치되었는지 확인")
        return False
    except Exception as e:
        print(f"❌ GUI 실행 오류: {e}")
        return False
    
    return True

def print_startup_info():
    """시작 정보 출력"""
    print("=" * 80)
    print("🚀 OKX 자동매매 시스템 v2.0 - 실제 데이터 연동 GUI")
    print("=" * 80)
    print("📊 특징:")
    print("  ✅ 실제 OKX 시장 데이터 실시간 수신")
    print("  ✅ 실제 계좌 잔고 및 포지션 정보 표시")
    print("  ✅ WebSocket을 통한 실시간 업데이트")
    print("  ✅ 과거 데이터 로딩 및 차트 표시")
    print("  ✅ 다크 테마 UI")
    print()
    print("⚠️  주의사항:")
    print("  • config.py에 올바른 OKX API 키가 설정되어 있어야 합니다")
    print("  • 실제 거래소 데이터를 사용하므로 안정적인 인터넷 연결이 필요합니다")
    print("  • Paper Trading 모드가 아닌 경우 실제 자금이 사용될 수 있습니다")
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
    
    # 3. 설정 검증
    if not validate_config():
        input("Enter 키를 눌러 종료하세요...")
        return False
    
    # 4. API 연결 테스트
    api_test_choice = input("API 연결 테스트를 수행하시겠습니까? (y/n): ").lower().strip()
    if api_test_choice == 'y':
        if not test_api_connection():
            continue_choice = input("API 테스트에 실패했습니다. 계속 진행하시겠습니까? (y/n): ").lower().strip()
            if continue_choice != 'y':
                return False
    
    # 5. GUI 파일 확인
    if not create_improved_gui_files():
        print("\n📋 다음 단계:")
        print("1. 위에서 제공한 'main_window_improved.py' 코드를 gui/ 폴더에 저장")
        print("2. 위에서 제공한 'websocket_handler_improved.py' 코드를 okx/ 폴더에 저장")
        print("3. 다시 이 스크립트를 실행")
        input("Enter 키를 눌러 종료하세요...")
        return False
    
    # 6. GUI 실행
    print("\n🎨 GUI 실행 준비 완료!")
    
    run_choice = input("지금 GUI를 실행하시겠습니까? (y/n): ").lower().strip()
    if run_choice == 'y':
        return run_improved_gui()
    else:
        print("GUI 실행을 취소했습니다.")
        print("나중에 실행하려면: python run_improved_gui.py")
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