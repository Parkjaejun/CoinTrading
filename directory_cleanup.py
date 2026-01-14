# directory_cleanup.py
"""
CoinTrading 디렉토리 정리 스크립트
불필요한 테스트/디버깅 파일들을 일괄 삭제합니다.

사용법: python directory_cleanup.py
"""

import os
import shutil
from datetime import datetime

# 프로젝트 루트 디렉토리 (이 스크립트가 있는 위치)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 삭제할 파일 목록
# ============================================================

# 루트 디렉토리의 테스트/디버깅 파일들
ROOT_FILES_TO_DELETE = [
    "api_connection_test.py",
    "api_permissions_test.py",
    "balance_checker.py",
    "balance_debug.py",
    "balance_test.py",
    "buy_test_net_mode.py",
    "check_account_mode.py",
    "config_check.py",
    "connection_test.py",
    "connection_test_fixed.py",
    "debug_order_test.py",
    "full_account_check.py",
    "quick_buy_test.py",
    "simple_test.py",
    "verify_and_order.py",
    "okx_debug_tool.py",
    "test_condition_monitoring.py",
    "condition_monitoring_tab.py",
    "monitoring_condition_monitor.py",
]

# 하위 디렉토리의 삭제할 파일들
SUBDIR_FILES_TO_DELETE = [
    "gui/debug_condition_monitoring.py",
]

# 삭제할 __pycache__ 디렉토리들
PYCACHE_DIRS_TO_DELETE = [
    "__pycache__",
    "gui/__pycache__",
    "okx/__pycache__",
    "utils/__pycache__",
    "monitoring/__pycache__",
    "strategy/__pycache__",
    "simulation/__pycache__",
    "simulation_gui/__pycache__",
    "backtest/__pycache__",
]

# ============================================================
# 정리 함수들
# ============================================================

def print_header():
    """헤더 출력"""
    print("=" * 60)
    print("🧹 CoinTrading 디렉토리 정리 스크립트")
    print("=" * 60)
    print(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 프로젝트 경로: {PROJECT_ROOT}")
    print("=" * 60)


def delete_files(file_list, base_path=PROJECT_ROOT):
    """파일 목록 삭제"""
    deleted_count = 0
    failed_count = 0
    
    for file_name in file_list:
        file_path = os.path.join(base_path, file_name)
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  ✅ 삭제됨: {file_name}")
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ 삭제 실패: {file_name} - {e}")
                failed_count += 1
        else:
            print(f"  ⏭️  없음: {file_name}")
    
    return deleted_count, failed_count


def delete_pycache_dirs(dir_list, base_path=PROJECT_ROOT):
    """__pycache__ 디렉토리 삭제"""
    deleted_count = 0
    failed_count = 0
    
    for dir_name in dir_list:
        dir_path = os.path.join(base_path, dir_name)
        
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"  ✅ 삭제됨: {dir_name}/")
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ 삭제 실패: {dir_name}/ - {e}")
                failed_count += 1
        else:
            print(f"  ⏭️  없음: {dir_name}/")
    
    return deleted_count, failed_count


def show_files_to_delete():
    """삭제할 파일 목록 미리보기"""
    print("\n📋 삭제 예정 파일 목록:")
    print("-" * 40)
    
    existing_files = []
    
    # 루트 파일 확인
    print("\n[루트 디렉토리 파일]")
    for file_name in ROOT_FILES_TO_DELETE:
        file_path = os.path.join(PROJECT_ROOT, file_name)
        if os.path.exists(file_path):
            print(f"  📄 {file_name}")
            existing_files.append(file_name)
    
    # 하위 디렉토리 파일 확인
    print("\n[하위 디렉토리 파일]")
    for file_name in SUBDIR_FILES_TO_DELETE:
        file_path = os.path.join(PROJECT_ROOT, file_name)
        if os.path.exists(file_path):
            print(f"  📄 {file_name}")
            existing_files.append(file_name)
    
    # __pycache__ 디렉토리 확인
    print("\n[__pycache__ 디렉토리]")
    existing_dirs = []
    for dir_name in PYCACHE_DIRS_TO_DELETE:
        dir_path = os.path.join(PROJECT_ROOT, dir_name)
        if os.path.exists(dir_path):
            print(f"  📁 {dir_name}/")
            existing_dirs.append(dir_name)
    
    print("-" * 40)
    print(f"총 {len(existing_files)}개 파일, {len(existing_dirs)}개 디렉토리 삭제 예정")
    
    return len(existing_files) + len(existing_dirs)


def main():
    """메인 실행 함수"""
    print_header()
    
    # 삭제할 파일 미리보기
    total_items = show_files_to_delete()
    
    if total_items == 0:
        print("\n✨ 삭제할 파일이 없습니다. 이미 정리되어 있습니다!")
        return
    
    # 사용자 확인
    print("\n" + "=" * 60)
    print("⚠️  경고: 위 파일들이 영구적으로 삭제됩니다!")
    print("=" * 60)
    
    confirm = input("\n정말 삭제하시겠습니까? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("\n🚫 삭제가 취소되었습니다.")
        return
    
    # 삭제 실행
    print("\n🗑️  파일 삭제 중...")
    print("-" * 40)
    
    # 1. 루트 파일 삭제
    print("\n[루트 디렉토리 파일 삭제]")
    root_deleted, root_failed = delete_files(ROOT_FILES_TO_DELETE)
    
    # 2. 하위 디렉토리 파일 삭제
    print("\n[하위 디렉토리 파일 삭제]")
    sub_deleted, sub_failed = delete_files(SUBDIR_FILES_TO_DELETE)
    
    # 3. __pycache__ 디렉토리 삭제
    print("\n[__pycache__ 디렉토리 삭제]")
    cache_deleted, cache_failed = delete_pycache_dirs(PYCACHE_DIRS_TO_DELETE)
    
    # 결과 요약
    total_deleted = root_deleted + sub_deleted + cache_deleted
    total_failed = root_failed + sub_failed + cache_failed
    
    print("\n" + "=" * 60)
    print("📊 정리 결과")
    print("=" * 60)
    print(f"  ✅ 삭제 성공: {total_deleted}개")
    print(f"  ❌ 삭제 실패: {total_failed}개")
    print("=" * 60)
    
    if total_failed == 0:
        print("\n🎉 디렉토리 정리가 완료되었습니다!")
    else:
        print("\n⚠️  일부 파일 삭제에 실패했습니다. 수동으로 확인해주세요.")


if __name__ == "__main__":
    main()
