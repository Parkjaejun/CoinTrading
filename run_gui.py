#!/usr/bin/env python3
# run_gui.py
"""
OKX 자동매매 시스템 GUI 실행
"""
# 맨 처음에 quiet_logger import (포지션 조회 로그 숨김)
try:
    import quiet_logger
except ImportError:
    pass  # quiet_logger가 없으면 무시

import sys
import os
import traceback
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("=" * 70)
print("  OKX 자동매매 시스템 GUI")
print("=" * 70)

def check_dependencies():
    """필수 의존성 확인"""
    print("[1/4] 의존성 확인 중...")
    
    # PyQt5 확인
    try:
        from PyQt5.QtWidgets import QApplication
        print("  - PyQt5: OK")
    except ImportError:
        print("  - PyQt5: 없음! pip install PyQt5")
        return False

    # 선택적 라이브러리
    try:
        import pyqtgraph
        print("  - pyqtgraph: OK")
    except ImportError:
        print("  - pyqtgraph: 없음 (차트 제한)")

    return True

def load_modules():
    """모듈 로딩"""
    print("[2/4] 모듈 로딩 중...")
    
    modules_ok = True
    
    try:
        import config
        print("  - config: OK")
    except ImportError as e:
        print(f"  - config: 실패 ({e})")
        modules_ok = False

    try:
        from okx.account_manager import AccountManager
        print("  - AccountManager: OK")
    except ImportError as e:
        print(f"  - AccountManager: 실패 ({e})")
        modules_ok = False

    try:
        from gui.main_window import TradingMainWindow
        print("  - TradingMainWindow: OK")
    except ImportError as e:
        print(f"  - TradingMainWindow: 실패 ({e})")
        modules_ok = False

    return modules_ok

def test_api():
    """API 연결 테스트"""
    print("[3/4] API 연결 테스트...")
    
    try:
        from okx.account_manager import AccountManager
        account = AccountManager()
        balance = account.get_account_balance()
        
        if balance and 'data' in balance:
            usdt = 0
            for detail in balance['data'][0].get('details', []):
                if detail.get('ccy') == 'USDT':
                    usdt = float(detail.get('availBal', 0))
                    break
            print(f"  - API 연결: OK (USDT: ${usdt:.2f})")
            return True
        else:
            print("  - API 연결: OK (잔고 없음)")
            return True
    except Exception as e:
        print(f"  - API 연결: 실패 ({e})")
        return False

def main():
    """메인 함수"""
    # 의존성 확인
    if not check_dependencies():
        return 1
    
    # 모듈 로딩
    if not load_modules():
        print("필수 모듈 로딩 실패!")
        return 1
    
    # API 테스트
    test_api()
    
    print("[4/4] GUI 시작...")
    print("=" * 70)
    
    # GUI 실행
    try:
        from PyQt5.QtWidgets import QApplication
        from gui.main_window import TradingMainWindow
        
        app = QApplication(sys.argv)
        app.setApplicationName("OKX 자동매매")
        
        window = TradingMainWindow()
        window.show()
        
        print("GUI 시작 완료! 자동매매 탭에서 시작 버튼을 누르세요.")
        print("=" * 70)
        print("")  # 빈 줄
        
        return app.exec_()
        
    except Exception as e:
        print(f"GUI 시작 실패: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n종료됨")
        sys.exit(0)