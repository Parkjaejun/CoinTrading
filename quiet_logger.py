# quiet_logger.py
"""
조용한 로거 - 반복 API 로그만 숨김, 나머지는 모두 표시
"""

import builtins
from datetime import datetime

_original_print = builtins.print
_quiet_mode_enabled = False


def _quiet_print(*args, **kwargs):
    """반복 API 로그만 숨김"""
    if not args:
        _original_print(*args, **kwargs)
        return
    
    msg = str(args[0])
    
    # ========== 숨길 패턴 (API 디버그 로그만!) ==========
    hide_patterns = [
        "🔍 전달할 파라미터",
        "🔍 생성된 쿼리",
        "🔍 서명용 request_path",
        "🔍 API 요청 디버그",
        "🔍 실제 요청 URL",
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
    _original_print("🔇 조용한 모드 - API 디버그 로그만 숨김")
    _original_print("=" * 60)
    _original_print("")


def disable_quiet_mode():
    """조용한 모드 비활성화"""
    global _quiet_mode_enabled
    _quiet_mode_enabled = False
    builtins.print = _original_print


# 자동 활성화
enable_quiet_mode()