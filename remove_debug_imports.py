# remove_debug_imports.py
"""
main_window.py에서 debug_condition_monitoring 관련 코드를 제거하는 스크립트
사용법: python remove_debug_imports.py
"""

import re

def remove_debug_code():
    """debug_condition_monitoring 관련 코드 제거"""
    
    # main_window.py 읽기
    with open('gui/main_window.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. import 구문 제거
    patterns_to_remove = [
        r'from gui\.debug_condition_monitoring import ConditionMonitoringDebugger, add_debugger_to_main_window\n',
        r'from gui\.debug_condition_monitoring import ConditionMonitoringDebugger\n',
        r'from gui\.debug_condition_monitoring import DebugLevel\n',
        r'\s*from gui\.debug_condition_monitoring import DebugLevel\n',
    ]
    
    for pattern in patterns_to_remove:
        content = re.sub(pattern, '', content)
    
    # 2. self.setup_debugger() 호출 제거
    content = re.sub(r'\s*self\.setup_debugger\(\)\s*\n', '\n', content)
    
    # 3. setup_debugger 메서드 전체 제거
    setup_debugger_pattern = r'''    def setup_debugger\(self\):
        """.*?"""
        try:
            .*?
        except Exception as e:
            print\(f".*?"\)
            import traceback
            traceback\.print_exc\(\)\n'''
    content = re.sub(setup_debugger_pattern, '', content, flags=re.DOTALL)
    
    # 4. debugger 관련 사용 코드 제거 (if hasattr(self, 'debugger') 블록들)
    debugger_usage_patterns = [
        r'\s*# 디버거에도 로그 추가\s*\n\s*if hasattr\(self, \'debugger\'\):.*?DebugLevel\.\w+\)',
        r'\s*if hasattr\(self, \'debugger\'\):\s*\n\s*from gui\.debug_condition_monitoring import DebugLevel\s*\n\s*self\.debugger\.add_debug_log\([^)]+\)',
    ]
    
    for pattern in debugger_usage_patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 5. closeEvent에서 debugger 정리 코드 제거
    debugger_cleanup_pattern = r'''        # 디버거 정리
        if hasattr\(self, 'debugger'\):
            try:
                if hasattr\(self\.debugger, 'auto_debug_timer'\):
                    self\.debugger\.auto_debug_timer\.stop\(\)
                if hasattr\(self\.debugger, 'continuous_test_timer'\):
                    self\.debugger\.continuous_test_timer\.stop\(\)
            except:
                pass
        \n'''
    content = re.sub(debugger_cleanup_pattern, '', content)
    
    # 6. sync_debugger 관련 메서드들의 debugger 참조 제거
    content = re.sub(r'\s*if hasattr\(self, \'debugger\'\):\s*\n\s*from gui\.debug_condition_monitoring import DebugLevel\s*\n\s*self\.debugger\.add_debug_log\([^)]+, DebugLevel\.\w+\)', '', content)
    
    # 7. QTimer.singleShot으로 debugger 관련 호출 제거
    content = re.sub(r'\s*# \d+초 후.*?동기화.*?\n\s*QTimer\.singleShot\(\d+, self\.sync_debugger_to_main_gui\)', '', content)
    content = re.sub(r'\s*# \d+초 후.*?동기화.*?\n\s*QTimer\.singleShot\(\d+, self\.start_continuous_sync\)', '', content)
    
    # 8. sync_debugger_to_main_gui 메서드 전체를 빈 메서드로 대체
    sync_method_pattern = r'(    def sync_debugger_to_main_gui\(self\):)\s*\n\s*""".*?"""\s*\n.*?return False\n'
    content = re.sub(sync_method_pattern, r'''\1
        """디버거 동기화 (비활성화됨)"""
        pass
    
''', content, flags=re.DOTALL)
    
    # 9. start_continuous_sync 메서드를 빈 메서드로 대체
    continuous_sync_pattern = r'(    def start_continuous_sync\(self\):)\s*\n\s*""".*?"""\s*\n.*?print\(f".*?"\)\n'
    content = re.sub(continuous_sync_pattern, r'''\1
        """지속적 동기화 (비활성화됨)"""
        pass
    
''', content, flags=re.DOTALL)
    
    # 변경사항 확인
    if content == original_content:
        print("⚠️ 변경사항 없음 - 이미 정리되었거나 패턴이 맞지 않음")
        return False
    
    # 백업 생성
    backup_path = 'gui/main_window_backup.py'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original_content)
    print(f"✅ 백업 생성됨: {backup_path}")
    
    # 수정된 파일 저장
    with open('gui/main_window.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ gui/main_window.py 수정 완료!")
    print("\n삭제된 항목:")
    print("  - debug_condition_monitoring import 구문들")
    print("  - setup_debugger() 메서드")
    print("  - debugger 관련 사용 코드")
    print("  - closeEvent의 debugger 정리 코드")
    
    return True


def manual_removal_guide():
    """수동 제거 가이드"""
    print("""
===============================================================
🔧 main_window.py 수동 수정 가이드
===============================================================

자동 스크립트가 작동하지 않을 경우, 아래 내용을 수동으로 제거하세요:

1️⃣ 파일 상단 import 제거 (라인 17, 31):
   - from gui.debug_condition_monitoring import ConditionMonitoringDebugger, add_debugger_to_main_window
   - from gui.debug_condition_monitoring import ConditionMonitoringDebugger

2️⃣ __init__ 메서드에서 제거 (라인 113):
   - self.setup_debugger()

3️⃣ setup_debugger 메서드 전체 제거 (라인 118-139):
   def setup_debugger(self): 부터 traceback.print_exc() 까지 전체 삭제

4️⃣ DebugLevel 사용 부분 제거 (여러 곳):
   검색어: "from gui.debug_condition_monitoring import DebugLevel"
   해당 줄과 그 아래 self.debugger.add_debug_log(...) 줄 함께 삭제

5️⃣ closeEvent에서 debugger 정리 코드 제거 (라인 894-901):
   "# 디버거 정리" 주석부터 "pass" 까지 삭제

6️⃣ 선택사항 - sync_debugger 관련 메서드들:
   - sync_debugger_to_main_gui()
   - start_continuous_sync()
   - manual_sync_from_debugger()
   이 메서드들은 삭제하거나 pass로 대체

===============================================================
검색 명령어 (VS Code):
  Ctrl+Shift+F → "debug_condition_monitoring" 검색
  모든 관련 코드를 찾아서 제거
===============================================================
""")


if __name__ == "__main__":
    print("🔧 debug_condition_monitoring 코드 제거 스크립트")
    print("=" * 50)
    
    try:
        success = remove_debug_code()
        if not success:
            print("\n자동 제거 실패. 수동 가이드를 확인하세요:")
            manual_removal_guide()
    except FileNotFoundError:
        print("❌ gui/main_window.py 파일을 찾을 수 없습니다.")
        print("   CoinTrading 폴더에서 이 스크립트를 실행하세요.")
        manual_removal_guide()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        manual_removal_guide()
