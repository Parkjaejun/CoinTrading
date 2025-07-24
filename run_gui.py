"""
OKX 자동매매 시스템 GUI 실행 스크립트
- 잔액 조회 버그 수정
- main.py와 동일한 방식으로 계좌 정보 처리
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
    """API 연결 테스트 - 수정된 버전"""
    try:
        from okx.account_manager import AccountManager
        
        print("🔗 API 연결 테스트 중...")
        account = AccountManager()
        
        # main.py와 동일한 방식으로 잔액 조회
        balance_data = account.get_account_balance()
        
        if balance_data and isinstance(balance_data, dict):
            # OKX API 응답 구조 확인
            if 'details' in balance_data:
                # details 배열에서 USDT 찾기
                usdt_balance = 0.0
                total_currencies = 0
                
                for detail in balance_data.get('details', []):
                    ccy = detail.get('ccy')
                    available_bal = detail.get('availBal', '0')
                    cash_bal = detail.get('cashBal', '0')
                    
                    # 빈 문자열 처리
                    if available_bal == '' or available_bal is None:
                        available_bal = '0'
                    if cash_bal == '' or cash_bal is None:
                        cash_bal = '0'
                    
                    available = float(available_bal)
                    total = float(cash_bal)
                    
                    if ccy == 'USDT':
                        usdt_balance = available
                    
                    if total > 0.001:  # 0.001 이상인 통화만 카운트
                        total_currencies += 1
                        print(f"  💰 {ccy}: 총 {total:.6f} | 사용가능 {available:.6f}")
                
                # 총 자산 정보
                total_eq = balance_data.get('totalEq', '0')
                if total_eq == '' or total_eq is None:
                    total_eq = '0'
                total_equity = float(total_eq)
                
                print(f"✅ API 연결 성공 - USDT: ${usdt_balance:.2f}")
                print(f"💰 총 자산: ${total_equity:.2f} ({total_currencies}개 통화)")
                return True
                
            else:
                # 다른 형태의 잔액 데이터 처리 (백업)
                usdt_info = balance_data.get('USDT', {})
                if isinstance(usdt_info, dict):
                    usdt_balance = usdt_info.get('available', 0)
                    print(f"✅ API 연결 성공 - USDT: ${usdt_balance:.2f}")
                    return True
                else:
                    print("❌ 예상하지 못한 잔액 데이터 구조")
                    print(f"디버그: balance_data 키들 = {list(balance_data.keys())}")
                    # 그래도 연결은 성공한 것으로 간주
                    return True
        else:
            print("❌ API 연결 실패 - 잔액 데이터 없음")
            print(f"디버그: balance_data = {balance_data}")
            return False
            
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        print(f"디버그: 오류 타입 = {type(e)}")
        import traceback
        print(f"상세 오류:\n{traceback.format_exc()}")
        return False

def run_gui():
    """GUI 실행"""
    try:
        print("🎨 GUI 실행 중...")
        
        # 모듈 로드 확인
        try:
            import config
            print("✅ config 모듈 로드 성공")
        except Exception as e:
            print(f"❌ config 모듈 로드 실패: {e}")
            return False
        
        try:
            from okx.account_manager import AccountManager
            print("✅ account_manager 모듈 로드 성공")
        except Exception as e:
            print(f"❌ account_manager 모듈 로드 실패: {e}")
            return False
        
        try:
            from utils.websocket_handler import WebSocketHandler
            print("✅ websocket_handler 모듈 로드 성공")
        except Exception as e:
            print("⚠️ websocket_handler 모듈 로드 실패 (GUI는 실행 가능)")
            print(f"   오류: {e}")
        
        try:
            from utils.logger import log_system
            print("✅ logger 모듈 로드 성공")
        except Exception as e:
            print("⚠️ logger 모듈 로드 실패 (GUI는 실행 가능)")
            print(f"   오류: {e}")
        
        # 실제 거래 시스템 가용성 확인
        trading_available = True
        try:
            from main import TradingSystem
            print(f"🎯 실제 거래 시스템 가용성: {trading_available}")
        except Exception as e:
            trading_available = False
            print(f"⚠️ 실제 거래 시스템 불가 (GUI 모드만 가능): {e}")
        
        # 계정 관리자 재초기화 (GUI용)
        print("🔗 실제 OKX API 연결 시작")
        account_manager = AccountManager()
        print("✅ 계정 관리자 초기화 완료")
        
        # GUI 메인 실행
        from gui.main_window import main as gui_main
        return gui_main()
        
    except ImportError as e:
        print(f"❌ GUI 모듈 임포트 실패: {e}")
        print("gui/main_window.py 파일을 확인하세요")
        return False
    except Exception as e:
        print(f"❌ GUI 실행 오류: {e}")
        import traceback
        print(f"상세 오류:\n{traceback.format_exc()}")
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
                    print("❌ 설치 실패. 수동으로 설치해주세요.")
                    return False
            else:
                print("❌ 필수 라이브러리 설치를 취소했습니다.")
                return False
    
    # 시스템 검증
    if not args.skip_checks:
        print("🔍 시스템 검증 중...")
        if not validate_system():
            return False
    
    # API 연결 테스트
    print("🔗 API 연결 테스트 중...")
    if not test_api():
        print("❌ API 연결 실패. config.py를 확인해주세요.")
        return False
    
    # 실행 모드 선택
    if args.console:
        success = run_console()
    else:
        success = run_gui()
    
    if not success:
        print("\n❌ 실행 실패")
        input("Enter를 눌러 종료...")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        input("Enter를 눌러 종료...")
        sys.exit(1)