# utils/logger.py
"""
로깅 유틸

시스템 로그, 오류 로그, 정보 로그 출력
"""

from datetime import datetime
from typing import Any, Optional


def get_timestamp() -> str:
    """현재 시간 문자열"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_system(message: str):
    """
    시스템 로그
    
    Args:
        message: 로그 메시지
    """
    print(f"[{get_timestamp()}] 🔧 {message}")


def log_error(message: str, error: Optional[Exception] = None):
    """
    오류 로그
    
    Args:
        message: 로그 메시지
        error: 예외 객체 (옵션)
    """
    if error:
        print(f"[{get_timestamp()}] ❌ {message}: {error}")
    else:
        print(f"[{get_timestamp()}] ❌ {message}")


def log_info(message: str):
    """
    정보 로그
    
    Args:
        message: 로그 메시지
    """
    print(f"[{get_timestamp()}] ℹ️ {message}")


def log_trade(action: str, symbol: str, price: float, 
              mode: str, pnl: Optional[float] = None):
    """
    거래 로그
    
    Args:
        action: 거래 액션 (entry/exit)
        symbol: 심볼
        price: 가격
        mode: 모드 (REAL/VIRTUAL)
        pnl: 손익 (청산시)
    """
    if action == "entry":
        print(f"[{get_timestamp()}] 📈 [{symbol}] LONG 진입 [{mode}] @ ${price:,.2f}")
    elif action == "exit":
        emoji = "💰" if pnl and pnl > 0 else "📉"
        pnl_str = f" | PnL: ${pnl:+,.2f}" if pnl is not None else ""
        print(f"[{get_timestamp()}] {emoji} [{symbol}] LONG 청산 [{mode}] @ ${price:,.2f}{pnl_str}")


def log_mode_switch(symbol: str, from_mode: str, to_mode: str, reason: str):
    """
    모드 전환 로그
    
    Args:
        symbol: 심볼
        from_mode: 이전 모드
        to_mode: 새 모드
        reason: 전환 이유
    """
    emoji = "⚠️" if to_mode == "VIRTUAL" else "✅"
    print(f"[{get_timestamp()}] {emoji} [{symbol}] 모드 전환: {from_mode} → {to_mode}")
    print(f"    이유: {reason}")
