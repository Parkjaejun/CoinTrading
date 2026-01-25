# models.py
"""
CoinTrading v2 데이터 모델
- Trade: 완료된 거래 기록
- Position: 현재 포지션
- SignalEvent: 시그널 이벤트
- ValidationResult: 시그널 검증 결과
- OrderEvent: 주문 이벤트
- ModeSwitchEvent: 모드 전환 이벤트
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any, Literal, Dict
from datetime import datetime


@dataclass
class Trade:
    """완료된 거래 기록"""
    side: Literal["LONG"]           # v2는 LONG only
    mode: Literal["REAL", "VIRTUAL"]
    entry_time: Any
    entry_price: float
    exit_time: Any
    exit_price: float
    size: float
    leverage: float
    reason_exit: str
    pnl: float
    fee: float
    net_pnl: float
    
    # 자본 연속성 검증용
    entry_capital: float
    entry_notional: float
    exit_capital_before: float
    exit_capital_after: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'side': self.side,
            'mode': self.mode,
            'entry_time': str(self.entry_time),
            'entry_price': self.entry_price,
            'exit_time': str(self.exit_time),
            'exit_price': self.exit_price,
            'size': self.size,
            'leverage': self.leverage,
            'reason_exit': self.reason_exit,
            'pnl': self.pnl,
            'fee': self.fee,
            'net_pnl': self.net_pnl,
            'entry_capital': self.entry_capital,
            'entry_notional': self.entry_notional,
            'exit_capital_before': self.exit_capital_before,
            'exit_capital_after': self.exit_capital_after,
        }


@dataclass
class Position:
    """현재 보유 포지션"""
    side: Literal["LONG"]           # v2는 LONG only
    mode: Literal["REAL", "VIRTUAL"]
    entry_time: Any
    entry_price: float
    size: float
    leverage: float
    peak_price: float               # 트레일링 스탑용 고점
    
    # 진입 당시 자본/노셔널
    entry_capital: float
    entry_notional: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'side': self.side,
            'mode': self.mode,
            'entry_time': str(self.entry_time),
            'entry_price': self.entry_price,
            'size': self.size,
            'leverage': self.leverage,
            'peak_price': self.peak_price,
            'entry_capital': self.entry_capital,
            'entry_notional': self.entry_notional,
        }
    
    def get_unrealized_pnl(self, current_price: float) -> float:
        """미실현 손익 계산"""
        return (current_price - self.entry_price) * self.size
    
    def get_unrealized_pnl_pct(self, current_price: float) -> float:
        """미실현 손익률 (%) - 레버리지 고려"""
        price_change_pct = (current_price - self.entry_price) / self.entry_price
        return price_change_pct * self.leverage * 100


@dataclass
class SignalEvent:
    """시그널 이벤트 기록 - 디버깅 핵심"""
    timestamp: Any
    signal_type: Literal["ENTRY", "EXIT", "NONE"]
    reason: str                     # 시그널 발생 이유
    
    # 시그널 생성 시점의 시장 데이터
    close_price: float
    ema_trend_fast: float
    ema_trend_slow: float
    ema_entry_fast: float
    ema_entry_slow: float
    ema_exit_fast: float
    ema_exit_slow: float
    
    # 이전 봉 EMA (크로스 판단용)
    prev_entry_fast: float
    prev_entry_slow: float
    prev_exit_fast: float
    prev_exit_slow: float
    
    # 조건 충족 여부
    trend_condition_met: bool       # 150 > 200 (상승장)
    entry_condition_met: bool       # 20/50 골든크로스
    exit_condition_met: bool        # 20/100 데드크로스
    trailing_stop_triggered: bool   # 트레일링 스탑 도달
    
    # 포지션 상태
    has_position: bool
    position_peak_price: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': str(self.timestamp),
            'signal_type': self.signal_type,
            'reason': self.reason,
            'close_price': self.close_price,
            'ema_trend_fast': self.ema_trend_fast,
            'ema_trend_slow': self.ema_trend_slow,
            'trend_diff_pct': ((self.ema_trend_fast - self.ema_trend_slow) / self.ema_trend_slow * 100) if self.ema_trend_slow else 0,
            'trend_condition_met': self.trend_condition_met,
            'entry_condition_met': self.entry_condition_met,
            'exit_condition_met': self.exit_condition_met,
            'trailing_stop_triggered': self.trailing_stop_triggered,
            'has_position': self.has_position,
        }


@dataclass
class ValidationResult:
    """시그널 검증 결과 - 왜 주문이 안 들어갔는지 추적"""
    signal: SignalEvent
    is_valid: bool
    rejection_reason: Optional[str] = None
    
    # 검증 상세
    mode_check: bool = True         # REAL/VIRTUAL 상태 확인
    capital_check: bool = True      # 자본 충분 여부
    position_check: bool = True     # 기존 포지션 상태 (중복 진입 방지)
    cooldown_check: bool = True     # 쿨다운 체크
    
    # 추가 정보
    current_mode: str = ""
    current_capital: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'signal': self.signal.to_dict(),
            'is_valid': self.is_valid,
            'rejection_reason': self.rejection_reason,
            'mode_check': self.mode_check,
            'capital_check': self.capital_check,
            'position_check': self.position_check,
            'cooldown_check': self.cooldown_check,
            'current_mode': self.current_mode,
            'current_capital': self.current_capital,
        }


@dataclass
class OrderEvent:
    """주문 이벤트 (실행된 주문)"""
    timestamp: Any
    action: Literal["ENTRY", "EXIT"]
    symbol: str
    side: Literal["LONG"]
    mode: Literal["REAL", "VIRTUAL"]
    price: float
    size: float
    leverage: float
    capital_used: float
    reason: str
    
    # 청산시 추가 정보
    pnl: Optional[float] = None
    net_pnl: Optional[float] = None
    capital_after: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'timestamp': str(self.timestamp),
            'action': self.action,
            'symbol': self.symbol,
            'side': self.side,
            'mode': self.mode,
            'price': self.price,
            'size': self.size,
            'leverage': self.leverage,
            'capital_used': self.capital_used,
            'reason': self.reason,
        }
        if self.action == "EXIT":
            result.update({
                'pnl': self.pnl,
                'net_pnl': self.net_pnl,
                'capital_after': self.capital_after,
            })
        return result


@dataclass
class ModeSwitchEvent:
    """모드 전환 이벤트"""
    timestamp: Any
    from_mode: Literal["REAL", "VIRTUAL"]
    to_mode: Literal["REAL", "VIRTUAL"]
    reason: str
    
    # 전환 시점 자본 상태
    real_capital: float
    real_peak: float
    virtual_capital: float
    virtual_trough: float
    
    # 추가 정보
    trigger_value: float = 0.0      # 전환 트리거 값 (예: 손실률)
    threshold: float = 0.0          # 전환 기준값
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': str(self.timestamp),
            'from_mode': self.from_mode,
            'to_mode': self.to_mode,
            'reason': self.reason,
            'real_capital': self.real_capital,
            'real_peak': self.real_peak,
            'virtual_capital': self.virtual_capital,
            'virtual_trough': self.virtual_trough,
            'trigger_value': self.trigger_value,
            'threshold': self.threshold,
        }


@dataclass
class BarData:
    """봉 데이터 (on_bar 입력용)"""
    timestamp: Any
    open: float
    high: float
    low: float
    close: float
    
    # EMA 값들
    ema_trend_fast: float
    ema_trend_slow: float
    ema_entry_fast: float
    ema_entry_slow: float
    ema_exit_fast: float
    ema_exit_slow: float
    
    # 이전 봉 EMA (크로스 판단용)
    prev_entry_fast: float
    prev_entry_slow: float
    prev_exit_fast: float
    prev_exit_slow: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': str(self.timestamp),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'ema_trend_fast': self.ema_trend_fast,
            'ema_trend_slow': self.ema_trend_slow,
            'ema_entry_fast': self.ema_entry_fast,
            'ema_entry_slow': self.ema_entry_slow,
            'ema_exit_fast': self.ema_exit_fast,
            'ema_exit_slow': self.ema_exit_slow,
        }


@dataclass  
class EngineStatus:
    """엔진 상태 스냅샷 (디버깅용)"""
    timestamp: Any
    
    # 모드 상태
    is_real_mode: bool
    mode: str
    
    # 자본 상태
    real_capital: float
    real_peak: float
    virtual_capital: float
    virtual_trough: float
    
    # 포지션 상태
    has_position: bool
    position: Optional[Dict] = None
    
    # 거래 통계
    total_trades: int = 0
    real_trades: int = 0
    virtual_trades: int = 0
    mode_switches_r2v: int = 0
    mode_switches_v2r: int = 0
    
    # 성과
    real_roi_pct: float = 0.0
    real_mdd_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': str(self.timestamp),
            'is_real_mode': self.is_real_mode,
            'mode': self.mode,
            'real_capital': self.real_capital,
            'real_peak': self.real_peak,
            'virtual_capital': self.virtual_capital,
            'virtual_trough': self.virtual_trough,
            'has_position': self.has_position,
            'position': self.position,
            'total_trades': self.total_trades,
            'real_trades': self.real_trades,
            'virtual_trades': self.virtual_trades,
            'mode_switches_r2v': self.mode_switches_r2v,
            'mode_switches_v2r': self.mode_switches_v2r,
            'real_roi_pct': self.real_roi_pct,
            'real_mdd_pct': self.real_mdd_pct,
        }
