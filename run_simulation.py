# run_simulation.py
"""
OKX 실시간 라이브 시뮬레이션 실행 스크립트
실제 시장 데이터를 받아와서 가상 거래 시뮬레이션
"""

import sys
import os
import argparse
from datetime import datetime

def check_dependencies():
    """의존성 확인"""
    missing_packages = []
    
    try:
        import PyQt5
    except ImportError:
        missing_packages.append("PyQt5")
    
    try:
        import pyqtgraph
    except ImportError:
        missing_packages.append("pyqtgraph")
    
    return missing_packages

def install_packages(packages):
    """패키지 설치"""
    import subprocess
    
    for package in packages:
        print(f"설치 중: {package}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        except subprocess.CalledProcessError:
            print(f"❌ {package} 설치 실패")
            return False
    
    return True

def setup_environment():
    """환경 설정"""
    # 프로젝트 루트를 Python 경로에 추가
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 필요한 디렉토리 생성
    os.makedirs('logs', exist_ok=True)
    os.makedirs('simulation', exist_ok=True)
    os.makedirs('simulation_gui', exist_ok=True)

def run_console_simulation(args):
    """콘솔 모드 시뮬레이션"""
    print("🎮 콘솔 모드 시뮬레이션 시작")
    
    try:
        from simulation.simulation_main import main as console_main
        
        # 명령행 인수 설정
        sys.argv = ['simulation_main.py', '--balance', str(args.balance)]
        
        console_main()
        
    except ImportError as e:
        print(f"❌ 모듈 임포트 실패: {e}")
        print("필요한 파일들이 올바른 위치에 있는지 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ 시뮬레이션 오류: {e}")
        return False
    
    return True

def run_gui_simulation(args):
    """GUI 모드 시뮬레이션"""
    print("🎨 GUI 모드 시뮬레이션 시작")
    
    try:
        from simulation_gui.sim_main_window import main as gui_main
        
        gui_main()
        
    except ImportError as e:
        print(f"❌ GUI 모듈 임포트 실패: {e}")
        print("PyQt5와 관련 모듈이 설치되어 있는지 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ GUI 실행 오류: {e}")
        return False
    
    return True

def main():
    """메인 함수"""
    print("=" * 60)
    print("🎮 OKX 실시간 라이브 트레이딩 시뮬레이션")
    print("=" * 60)
    print("실제 시장 데이터로 가상 거래 시뮬레이션")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description='OKX 실시간 라이브 트레이딩 시뮬레이션')
    parser.add_argument('--balance', type=float, default=10000.0, 
                       help='초기 가상 자본 (기본값: $10,000)')
    parser.add_argument('--console', action='store_true', 
                       help='콘솔 모드로 실행 (GUI 없음)')
    parser.add_argument('--no-gui-deps', action='store_true',
                       help='GUI 의존성 검사 건너뛰기')
    
    args = parser.parse_args()
    
    # 환경 설정
    setup_environment()
    
    # 콘솔 모드 실행
    if args.console:
        print("📋 콘솔 모드 선택")
        return run_console_simulation(args)
    
    # GUI 모드 실행
    print("🎨 GUI 모드 선택")
    
    # GUI 의존성 확인
    if not args.no_gui_deps:
        print("📦 GUI 라이브러리 확인 중...")
        missing = check_dependencies()
        
        if missing:
            print(f"❌ 누락된 라이브러리: {', '.join(missing)}")
            
            install_choice = input("자동으로 설치하시겠습니까? (y/n): ").lower()
            if install_choice == 'y':
                if not install_packages(missing):
                    print("❌ 라이브러리 설치 실패")
                    print("수동으로 설치하세요:")
                    print(f"pip install {' '.join(missing)}")
                    return False
            else:
                print("GUI 없이 콘솔 모드로 실행하려면:")
                print(f"python {sys.argv[0]} --console --balance {args.balance}")
                return False
        
        print("✅ GUI 라이브러리 확인 완료")
    
    return run_gui_simulation(args)

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n❌ 시뮬레이션 실행 실패")
            input("Enter 키를 눌러 종료하세요...")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단되었습니다")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        input("Enter 키를 눌러 종료하세요...")
        sys.exit(1)