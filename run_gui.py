# run_gui.py
"""
OKX 자동매매 시스템 GUI 실행 스크립트 - 수정된 버전
임포트 오류 수정 및 에러 처리 강화
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def print_banner():
    """시작 배너"""
    print("=" * 80)
    print("🚀 OKX 자동매매 시스템 - 완전한 실제 거래 GUI")
    print("=" * 80)
    print("💰 실시간 가격 차트 | 전략 관리 | 포지션 제어 | 백테스팅")
    print("⚠️  실제 자금으로 거래가 실행됩니다. 신중하게 사용하세요!")
    print("=" * 80)

def check_requirements():
    """필수 라이브러리 확인"""
    required = {
        'PyQt5': 'PyQt5',
        'pyqtgraph': 'pyqtgraph', 
        'requests': 'requests',
        'websocket-client': 'websocket',
        'psutil': 'psutil',
        'numpy': 'numpy',
        'pandas': 'pandas'
    }
    missing = []
    
    for pkg_name, import_name in required.items():
        try:
            if import_name == 'websocket':
                import websocket
            else:
                __import__(import_name)
        except ImportError:
            missing.append(pkg_name)
    
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
    dirs = {'gui', 'logs', 'config_backups'}
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
        'gui/main_window.py',
        'gui/balance_manager.py'
    ]
    
    missing = []
    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing.append(file_path)
    
    if missing:
        print(f"❌ 필수 파일 누락: {', '.join(missing)}")
        print("필요한 파일들을 생성해주세요.")
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
        
        balance_data = account.get_account_balance()
        
        if balance_data and isinstance(balance_data, dict):
            if 'details' in balance_data:
                usdt_balance = 0.0
                total_currencies = 0
                
                for detail in balance_data.get('details', []):
                    ccy = detail.get('ccy')
                    available_bal = detail.get('availBal', '0')
                    cash_bal = detail.get('cashBal', '0')
                    
                    if available_bal == '' or available_bal is None:
                        available_bal = '0'
                    if cash_bal == '' or cash_bal is None:
                        cash_bal = '0'
                    
                    available = float(available_bal)
                    total = float(cash_bal)
                    
                    if ccy == 'USDT':
                        usdt_balance = available
                    
                    if total > 0.001:
                        total_currencies += 1
                        print(f"  💰 {ccy}: 총 {total:.6f} | 사용가능 {available:.6f}")
                
                total_eq = balance_data.get('totalEq', '0')
                if total_eq == '' or total_eq is None:
                    total_eq = '0'
                total_equity = float(total_eq)
                
                print(f"✅ API 연결 성공 - USDT: ${usdt_balance:.2f}")
                print(f"💰 총 자산: ${total_equity:.2f} ({total_currencies}개 통화)")
                return True
            else:
                print("✅ API 연결 성공 (다른 형태의 데이터)")
                return True
        else:
            print("❌ API 연결 실패 - 잔액 데이터 없음")
            return False
            
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        return False

def run_gui():
    """GUI 실행"""
    try:
        print("🎨 완전한 GUI 실행 중...")
        
        # 모듈 로드 확인
        modules_to_check = [
            ('config', 'config'),
            ('account_manager', 'okx.account_manager'),
            ('balance_manager', 'gui.balance_manager'),
        ]
        
        # 선택적 모듈들
        optional_modules = [
            ('websocket_handler', 'utils.websocket_handler'),
            ('logger', 'utils.logger'),
            ('main TradingSystem', 'main')
        ]
        
        for name, module in modules_to_check:
            try:
                __import__(module)
                print(f"✅ {name} 모듈 로드 성공")
            except Exception as e:
                print(f"❌ {name} 모듈 로드 실패: {e}")
                print("필요한 파일이 누락되었습니다.")
                return False
        
        for name, module in optional_modules:
            try:
                __import__(module)
                print(f"✅ {name} 모듈 로드 성공")
            except Exception as e:
                print(f"⚠️ {name} 모듈 로드 실패 (선택사항): {e}")
        
        # GUI 메인 실행
        print("🚀 완전한 GUI 시작...")
        from gui.main_window import main as gui_main
        return gui_main()
        
    except ImportError as e:
        print(f"❌ GUI 모듈 임포트 실패: {e}")
        print("gui/main_window.py 파일을 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ GUI 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수"""
    print_banner()
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-checks', action='store_true', help='검증 건너뛰기')
    args = parser.parse_args()
    
    # 환경 설정
    print("🔧 환경 설정 중...")
    setup_environment()
    
    # 라이브러리 확인
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
    
    # GUI 실행
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
        import traceback
        traceback.print_exc()
        input("Enter를 눌러 종료...")
        sys.exit(1)