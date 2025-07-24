# run_gui.py - 깔끔한 OKX 실제 거래 GUI 실행 스크립트
"""
OKX 자동매매 시스템 GUI 실행 스크립트
- 실제 거래 시스템과 연동
- 간단하고 안정적인 실행
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def print_banner():
    """시작 배너"""
    print("=" * 80)
    print("🚀 OKX 자동매매 시스템 - 실제 거래 GUI")
    print("=" * 80)
    print("💰 실제 OKX API 연결 | 실제 USDT 잔액 | 실시간 BTC 가격")
    print("⚠️  실제 자금으로 거래가 실행됩니다. 신중하게 사용하세요!")
    print("=" * 80)

def check_requirements():
    """필수 라이브러리 확인"""
    required = ['PyQt5', 'pyqtgraph', 'requests', 'websocket-client']
    missing = []
    
    for pkg in required:
        try:
            if pkg == 'PyQt5':
                import PyQt5
            elif pkg == 'pyqtgraph':
                import pyqtgraph
            elif pkg == 'requests':
                import requests
            elif pkg == 'websocket-client':
                import websocket
        except ImportError:
            missing.append(pkg)
    
    return missing

def install_packages(packages):
    """패키지 설치"""
    for pkg in packages:
        print(f"📦 설치 중: {pkg}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
            print(f"✅ {pkg} 설치 완료")
        except subprocess.CalledProcessError:
            print(f"❌ {pkg} 설치 실패")
            return False
    return True

def setup_environment():
    """환경 설정"""
    project_root = Path(__file__).parent
    
    # Python 경로 추가
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 필요한 디렉토리 생성
    dirs = {'gui', 'logs'}
    for dir_name in dirs:
        (project_root / dir_name).mkdir(exist_ok=True)
    
    # gui/__init__.py 생성
    init_file = project_root / 'gui' / '__init__.py'
    if not init_file.exists():
        init_file.write_text('# GUI package\n')

def validate_system():
    """시스템 검증"""
    project_root = Path(__file__).parent
    
    # 필수 파일 확인
    required_files = [
        'config.py',
        'okx/account_manager.py',
        'gui/main_window.py'
    ]
    
    missing = []
    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing.append(file_path)
    
    if missing:
        print(f"❌ 필수 파일 누락: {', '.join(missing)}")
        return False
    
    # API 키 확인
    try:
        import config
        if not all([config.API_KEY, config.API_SECRET, config.PASSPHRASE]):
            print("❌ config.py에 API 키가 설정되지 않았습니다")
            return False
    except Exception as e:
        print(f"❌ config.py 오류: {e}")
        return False
    
    print("✅ 시스템 검증 완료")
    return True

def test_api():
    """API 연결 테스트"""
    try:
        from okx.account_manager import AccountManager
        
        print("🔗 API 연결 테스트 중...")
        account = AccountManager()
        balances = account.get_account_balance()
        
        if balances:
            usdt = balances.get('USDT', {}).get('available', 0)
            print(f"✅ API 연결 성공 - USDT: ${usdt:.2f}")
            return True
        else:
            print("❌ API 연결 실패")
            return False
            
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        return False

def run_gui():
    """GUI 실행"""
    try:
        print("🎨 GUI 실행 중...")
        
        from gui.main_window import main as gui_main
        return gui_main()
        
    except ImportError as e:
        print(f"❌ GUI 모듈 임포트 실패: {e}")
        print("gui/main_window.py 파일을 확인하세요")
        return False
    except Exception as e:
        print(f"❌ GUI 실행 오류: {e}")
        return False

def run_console():
    """콘솔 모드 실행"""
    try:
        print("📋 콘솔 모드 실행...")
        
        from main import TradingSystem
        
        trading_system = TradingSystem()
        if trading_system.initialize_system():
            trading_system.start_trading()
            return True
        else:
            print("❌ 거래 시스템 초기화 실패")
            return False
            
    except Exception as e:
        print(f"❌ 콘솔 모드 실행 오류: {e}")
        return False

def main():
    """메인 함수"""
    print_banner()
    
    # 명령행 인수
    parser = argparse.ArgumentParser()
    parser.add_argument('--console', action='store_true', help='콘솔 모드')
    parser.add_argument('--skip-checks', action='store_true', help='검증 건너뛰기')
    args = parser.parse_args()
    
    # 환경 설정
    print("🔧 환경 설정 중...")
    setup_environment()
    
    # 라이브러리 확인
    if not args.console:
        print("📦 라이브러리 확인 중...")
        missing = check_requirements()
        
        if missing:
            print(f"❌ 누락된 라이브러리: {', '.join(missing)}")
            
            if input("자동 설치하시겠습니까? (y/n): ").lower() == 'y':
                if not install_packages(missing):
                    print("❌ 설치 실패. 수동으로 설치하세요:")
                    print(f"pip install {' '.join(missing)}")
                    return False
            else:
                print("콘솔 모드: python run_gui.py --console")
                return False
    
    # 시스템 검증
    if not args.skip_checks:
        print("🔍 시스템 검증 중...")
        if not validate_system():
            print("⚠️ 검증 실패했지만 계속 진행합니다...")
        
        # API 테스트
        if not test_api():
            print("⚠️ API 테스트 실패했지만 GUI는 실행합니다...")
    
    # 실행 모드 선택
    if args.console:
        return run_console()
    else:
        return run_gui()

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n❌ 실행 실패")
            input("Enter를 눌러 종료...")
    except KeyboardInterrupt:
        print("\n🛑 사용자 중단")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        input("Enter를 눌러 종료...")