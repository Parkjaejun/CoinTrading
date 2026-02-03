# add_backtest_tab_patch.py
"""
main_window.py에 백테스트 탭을 추가하는 패치

사용법:
1. 이 파일을 D:\Project\CoinTrading\ 에 저장
2. python add_backtest_tab_patch.py 실행
3. GUI 재시작: python run_gui.py
"""

import os
import re
import shutil
from datetime import datetime

def patch_main_window():
    """main_window.py에 백테스트 탭 추가"""
    
    main_window_path = "gui/main_window.py"
    
    if not os.path.exists(main_window_path):
        print(f"❌ 파일을 찾을 수 없습니다: {main_window_path}")
        return False
    
    # 백업 생성
    backup_path = f"gui/main_window.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(main_window_path, backup_path)
    print(f"✅ 백업 생성: {backup_path}")
    
    with open(main_window_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 이미 패치되어 있는지 확인
    if 'create_backtest_tab' in content or 'backtest_project' in content:
        print("⚠️ 이미 백테스트 탭이 추가되어 있습니다.")
        return True
    
    # 1. import 추가 (파일 상단에)
    import_code = '''
# 백테스트 위젯 import
try:
    import sys
    import os
    backtest_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backtest_project')
    if backtest_path not in sys.path:
        sys.path.insert(0, backtest_path)
    from main import create_backtest_tab
    BACKTEST_AVAILABLE = True
    print("✅ 백테스트 위젯 로드 성공")
except ImportError as e:
    BACKTEST_AVAILABLE = False
    print(f"⚠️ 백테스트 위젯 로드 실패: {e}")
'''
    
    # import 추가 위치 찾기 (기존 import 블록 끝)
    import_pattern = r'(from PyQt5\.QtGui import.*?\n)'
    match = re.search(import_pattern, content)
    
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + import_code + content[insert_pos:]
        print("✅ import 구문 추가됨")
    else:
        # 대안: 파일 상단에 추가
        content = import_code + "\n" + content
        print("✅ import 구문 (파일 상단에) 추가됨")
    
    # 2. create_backtest_tab 메서드 추가
    backtest_method = '''
    def create_backtest_tab(self):
        """백테스트/알고리즘 검증 탭 생성"""
        try:
            if BACKTEST_AVAILABLE:
                backtest_widget = create_backtest_tab()
                self.tab_widget.addTab(backtest_widget, "🧪 알고리즘 검증")
                print("✅ 백테스트 탭 추가됨")
            else:
                # 대체 위젯
                from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
                fallback = QWidget()
                layout = QVBoxLayout(fallback)
                
                info_label = QLabel("⚠️ 백테스트 위젯을 로드할 수 없습니다.")
                info_label.setStyleSheet("font-size: 14px; color: #f39c12;")
                layout.addWidget(info_label)
                
                instruction = QLabel(
                    "backtest_project 폴더를 프로젝트 루트에 복사하세요:\\n"
                    "D:\\\\Project\\\\CoinTrading\\\\backtest_project\\\\"
                )
                layout.addWidget(instruction)
                layout.addStretch()
                
                self.tab_widget.addTab(fallback, "🧪 알고리즘 검증")
        except Exception as e:
            print(f"❌ 백테스트 탭 생성 실패: {e}")

'''
    
    # 메서드 추가 위치 찾기 (setup_ui 메서드 앞 또는 클래스 내부)
    # create_dashboard_tab 메서드 앞에 추가
    dashboard_pattern = r'(\n    def create_dashboard_tab\(self\):)'
    match = re.search(dashboard_pattern, content)
    
    if match:
        insert_pos = match.start()
        content = content[:insert_pos] + backtest_method + content[insert_pos:]
        print("✅ create_backtest_tab 메서드 추가됨")
    else:
        print("⚠️ create_dashboard_tab을 찾을 수 없어 메서드를 추가하지 못했습니다.")
    
    # 3. setup_ui()에서 create_backtest_tab() 호출 추가
    # create_auto_trading_tab() 다음에 추가
    setup_patterns = [
        (r'(self\.create_auto_trading_tab\(\))', r'\1\n        self.create_backtest_tab()  # 백테스트 탭'),
        (r'(self\.tab_widget\.addTab\([^,]+, "🤖 자동매매"\))', r'\1\n        self.create_backtest_tab()  # 백테스트 탭'),
    ]
    
    patched = False
    for pattern, replacement in setup_patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content, count=1)
            patched = True
            print("✅ setup_ui()에 create_backtest_tab() 호출 추가됨")
            break
    
    if not patched:
        print("⚠️ setup_ui()에 자동 추가하지 못했습니다. 수동으로 추가해주세요:")
        print("   setup_ui() 메서드 내에 self.create_backtest_tab() 추가")
    
    # 파일 저장
    with open(main_window_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 패치 완료: {main_window_path}")
    return True


def main():
    print("=" * 60)
    print("백테스트 탭 추가 패치")
    print("=" * 60)
    
    # 현재 디렉토리 확인
    if not os.path.exists("gui/main_window.py"):
        print("❌ gui/main_window.py를 찾을 수 없습니다.")
        print("   D:\\Project\\CoinTrading 디렉토리에서 실행해주세요.")
        return
    
    # backtest_project 폴더 확인
    if not os.path.exists("backtest_project"):
        print("⚠️ backtest_project 폴더가 없습니다.")
        print("   다운로드한 backtest_project 폴더를 여기에 복사해주세요.")
    
    # 패치 실행
    success = patch_main_window()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 패치 완료!")
        print("=" * 60)
        print("\n다음 단계:")
        print("1. backtest_project 폴더가 있는지 확인")
        print("2. python run_gui.py 실행")
        print("3. '🧪 알고리즘 검증' 탭 확인")
    else:
        print("\n❌ 패치 실패. 수동으로 추가해주세요.")


if __name__ == "__main__":
    main()
