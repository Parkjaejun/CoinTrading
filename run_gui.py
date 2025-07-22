# run_gui.py
"""
OKX 자동매매 시스템 GUI 실행 스크립트
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
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.lower().replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_missing_packages(packages):
    """누락된 패키지 설치"""
    print("누락된 패키지를 설치합니다...")
    
    for package in packages:
        print(f"설치 중: {package}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
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
    
    # 로그 디렉토리 생성
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # GUI 설정 디렉토리 생성
    gui_dir = project_root / 'gui'
    gui_dir.mkdir(exist_ok=True)

def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("🚀 OKX 자동매매 시스템 GUI 시작")
    print("=" * 50)
    
    # 환경 설정
    setup_environment()
    
    # 필수 라이브러리 확인
    print("📦 필수 라이브러리 확인 중...")
    missing = check_requirements()
    
    if missing:
        print(f"❌ 누락된 라이브러리: {', '.join(missing)}")
        
        install_choice = input("자동으로 설치하시겠습니까? (y/n): ").lower()
        if install_choice == 'y':
            if not install_missing_packages(missing):
                print("❌ 라이브러리 설치 실패. 수동으로 설치해주세요:")
                print(f"pip install {' '.join(missing)}")
                return False
        else:
            print("라이브러리를 먼저 설치해주세요:")
            print(f"pip install {' '.join(missing)}")
            return False
    
    print("✅ 모든 라이브러리 확인 완료")
    
    # GUI 시작
    try:
        print("🎨 GUI 애플리케이션 시작...")
        
        # GUI 모듈 임포트 (이 시점에서 임포트)
        from gui.main_window import main as gui_main
        
        # GUI 실행
        gui_main()
        
    except ImportError as e:
        print(f"❌ GUI 모듈 임포트 실패: {e}")
        print("gui/main_window.py 파일이 올바른 위치에 있는지 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ GUI 실행 오류: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("Enter 키를 눌러 종료하세요...")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 사용자에 의해 종료되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        input("Enter 키를 눌러 종료하세요...")
        sys.exit(1)