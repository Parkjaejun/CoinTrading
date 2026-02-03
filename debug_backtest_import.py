# debug_backtest_import.py
"""
backtest_project import 문제 디버깅
D:\Project\CoinTrading\ 에서 실행
"""

import sys
import os

print("=" * 60)
print("백테스트 모듈 Import 디버깅")
print("=" * 60)

# 현재 디렉토리
print(f"\n1. 현재 디렉토리: {os.getcwd()}")

# backtest_project 폴더 확인
backtest_path = os.path.join(os.getcwd(), 'backtest_project')
print(f"\n2. backtest_project 경로: {backtest_path}")
print(f"   존재 여부: {os.path.exists(backtest_path)}")

if os.path.exists(backtest_path):
    print(f"\n3. backtest_project 내용:")
    for item in os.listdir(backtest_path):
        item_path = os.path.join(backtest_path, item)
        if os.path.isdir(item_path):
            print(f"   📁 {item}/")
        else:
            print(f"   📄 {item}")
    
    # main.py 확인
    main_py = os.path.join(backtest_path, 'main.py')
    print(f"\n4. main.py 존재: {os.path.exists(main_py)}")
    
    # backtest 폴더 확인
    backtest_module = os.path.join(backtest_path, 'backtest')
    print(f"   backtest/ 폴더 존재: {os.path.exists(backtest_module)}")
    
    # gui 폴더 확인
    gui_module = os.path.join(backtest_path, 'gui')
    print(f"   gui/ 폴더 존재: {os.path.exists(gui_module)}")

# sys.path에 추가
print(f"\n5. sys.path에 추가 시도...")
if backtest_path not in sys.path:
    sys.path.insert(0, backtest_path)
    print(f"   ✅ 추가됨: {backtest_path}")

print(f"\n6. 현재 sys.path (처음 5개):")
for i, p in enumerate(sys.path[:5]):
    print(f"   [{i}] {p}")

# import 시도
print(f"\n7. Import 테스트:")

try:
    print("   - backtest 모듈 import 시도...")
    from backtest import BacktestEngine, Params
    print("   ✅ backtest 모듈 import 성공!")
except ImportError as e:
    print(f"   ❌ backtest 모듈 import 실패: {e}")

try:
    print("   - gui 모듈 import 시도...")
    from gui.backtest_widget import BacktestWidget
    print("   ✅ gui.backtest_widget import 성공!")
except ImportError as e:
    print(f"   ❌ gui.backtest_widget import 실패: {e}")

try:
    print("   - main.create_backtest_tab import 시도...")
    from main import create_backtest_tab
    print("   ✅ create_backtest_tab import 성공!")
except ImportError as e:
    print(f"   ❌ create_backtest_tab import 실패: {e}")
    
    # 상세 오류 확인
    import traceback
    print("\n   상세 오류:")
    traceback.print_exc()

print("\n" + "=" * 60)
print("디버깅 완료")
print("=" * 60)
