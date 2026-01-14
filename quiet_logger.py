# quiet_logger.py
"""
조용한 로거 - GUI 메인, 터미널은 에러/중요 로그만
- 반복 로그만 숨김
- 초기화, 거래, 신호, 에러 로그는 모두 표시

사용법:
    # run_gui.py 맨 위에 추가
    import quiet_logger
"""

import builtins
from datetime import datetime

# 원본 print 저장
_original_print = builtins.print

# 활성화 상태
_quiet_mode_enabled = False


def _quiet_print(*args, **kwargs):
    """필터링된 print - 반복 로그만 숨김"""
    if not args:
        _original_print(*args, **kwargs)
        return
    
    msg = str(args[0])
    
    # ========== 숨길 패턴 (반복되는 것만!) ==========
    hide_patterns = [
        # API 디버그 상세 로그
        "🔍 전달할 파라미터",
        "🔍 생성된 쿼리",
        "🔍 서명용 request_path",
        "🔍 API 요청 디버그",
        "🔍 실제 요청 URL",
        "Method: GET",
        "Method: POST",
        "Headers:",
        "Timestamp:",
        "Request Path:",
        "Query String:",
        
        # 반복 포지션/잔액 로그 (5초마다 반복)
        "포지션 조회 시작",
        "🔍 포지션 조회 시작",
        "📊 포지션 조회 시작",
        "📊 포지션 정보 업데이트",
        "instType=SWAP",
    ]
    
    for pattern in hide_patterns:
        if pattern in msg:
            return  # 숨김
    
    # ========== 나머지는 모두 표시 ==========
    _original_print(*args, **kwargs)


def enable_quiet_mode():
    """조용한 모드 활성화"""
    global _quiet_mode_enabled
    if _quiet_mode_enabled:
        return
    
    _quiet_mode_enabled = True
    builtins.print = _quiet_print
    
    _original_print("")
    _original_print("=" * 60)
    _original_print("🔇 조용한 모드 - 반복 로그만 숨김")
    _original_print("=" * 60)
    _original_print("")


def disable_quiet_mode():
    """조용한 모드 비활성화"""
    global _quiet_mode_enabled
    _quiet_mode_enabled = False
    builtins.print = _original_print
    _original_print("🔊 일반 모드로 전환")


def force_print(*args, **kwargs):
    """필터 무시하고 강제 출력"""
    _original_print(*args, **kwargs)


# ========== 자동 활성화 ==========
enable_quiet_mode()