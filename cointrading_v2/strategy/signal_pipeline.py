# strategy/signal_pipeline.py
"""
시그널 파이프라인 - 디버깅 및 추적 핵심 모듈

시그널 생성 → 검증 → 실행의 전 과정을 기록하고 분석
- SignalEvent: 시그널 이벤트 데이터
- ValidationResult: 검증 결과
- TradeRecord: 거래 기록
- SignalPipeline: 파이프라인 관리자
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from collections import deque
from datetime import datetime


@dataclass
class SignalEvent:
    """
    시그널 이벤트 데이터 클래스
    
    시그널 생성 시점의 모든 정보를 캡처
    """
    timestamp: Any                          # 시그널 발생 시간
    signal_type: str                        # "ENTRY", "EXIT", "NONE"
    reason: str                             # 시그널 발생 이유
    close_price: float                      # 현재 종가
    
    # 조건 상태
    trend_condition: bool = False           # 트렌드 조건 충족
    entry_condition: bool = False           # 진입 조건 충족
    exit_condition: bool = False            # 청산 조건 충족
    trailing_stop_triggered: bool = False   # 트레일링 스탑 도달
    
    # EMA 값들 (디버깅용)
    ema_values: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'timestamp': str(self.timestamp),
            'signal_type': self.signal_type,
            'reason': self.reason,
            'close_price': self.close_price,
            'trend_condition': self.trend_condition,
            'entry_condition': self.entry_condition,
            'exit_condition': self.exit_condition,
            'trailing_stop_triggered': self.trailing_stop_triggered,
            'ema_values': self.ema_values.copy(),
        }


@dataclass
class ValidationResult:
    """
    시그널 검증 결과 데이터 클래스
    
    시그널이 실행 가능한지 검증한 결과
    """
    signal: SignalEvent                     # 검증 대상 시그널
    is_valid: bool                          # 검증 통과 여부
    rejection_reason: Optional[str] = None  # 거부 이유 (실패 시)
    mode: str = ""                          # 현재 모드 ("REAL" | "VIRTUAL")
    capital: float = 0.0                    # 현재 자본
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'signal': self.signal.to_dict(),
            'is_valid': self.is_valid,
            'rejection_reason': self.rejection_reason,
            'mode': self.mode,
            'capital': self.capital,
        }


@dataclass
class TradeRecord:
    """
    거래 기록 데이터 클래스
    
    완료된 거래의 전체 정보
    """
    symbol: str                             # 거래 심볼
    side: str                               # 포지션 방향 ("LONG")
    mode: str                               # 거래 모드 ("REAL" | "VIRTUAL")
    
    # 진입 정보
    entry_time: Any                         # 진입 시간
    entry_price: float                      # 진입가
    entry_capital: float                    # 진입 시 자본
    
    # 청산 정보
    exit_time: Any                          # 청산 시간
    exit_price: float                       # 청산가
    exit_capital: float                     # 청산 후 자본
    
    # 포지션 정보
    size: float                             # 포지션 크기
    leverage: float                         # 레버리지
    notional: float = 0.0                   # 명목 가치
    
    # 손익 정보
    pnl: float = 0.0                        # 손익 (수수료 전)
    fee: float = 0.0                        # 수수료
    net_pnl: float = 0.0                    # 순손익 (수수료 후)
    
    # 청산 이유
    reason_exit: str = ""                   # 청산 이유
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'mode': self.mode,
            'entry_time': str(self.entry_time),
            'entry_price': self.entry_price,
            'entry_capital': self.entry_capital,
            'exit_time': str(self.exit_time),
            'exit_price': self.exit_price,
            'exit_capital': self.exit_capital,
            'size': self.size,
            'leverage': self.leverage,
            'notional': self.notional,
            'pnl': self.pnl,
            'fee': self.fee,
            'net_pnl': self.net_pnl,
            'reason_exit': self.reason_exit,
        }
    
    @property
    def pnl_percentage(self) -> float:
        """수익률 계산"""
        if self.entry_capital > 0:
            return (self.net_pnl / self.entry_capital) * 100
        return 0.0
    
    @property
    def is_win(self) -> bool:
        """승리 여부"""
        return self.net_pnl > 0


class SignalPipeline:
    """
    시그널 처리 파이프라인 - 디버깅 핵심 클래스
    
    시그널 생성부터 검증까지의 전 과정을 기록하고 분석
    """
    
    def __init__(self, max_history: int = 500):
        """
        Args:
            max_history: 히스토리 최대 크기
        """
        self.max_history = max_history
        
        # 히스토리 저장소
        self.signal_history: deque = deque(maxlen=max_history)
        self.validation_history: deque = deque(maxlen=max_history)
        
        # 통계
        self.stats = {
            'total_signals': 0,
            'entry_signals': 0,
            'exit_signals': 0,
            'valid_signals': 0,
            'rejected_signals': 0,
        }
        
        # 거부 이유별 카운트
        self.rejection_reasons: Dict[str, int] = {}
    
    def record_signal(self, signal: SignalEvent):
        """
        시그널 기록
        
        Args:
            signal: 시그널 이벤트
        """
        self.signal_history.append(signal)
        self.stats['total_signals'] += 1
        
        if signal.signal_type == "ENTRY":
            self.stats['entry_signals'] += 1
        elif signal.signal_type == "EXIT":
            self.stats['exit_signals'] += 1
    
    def record_validation(self, validation: ValidationResult):
        """
        검증 결과 기록
        
        Args:
            validation: 검증 결과
        """
        self.validation_history.append(validation)
        
        if validation.is_valid:
            self.stats['valid_signals'] += 1
        else:
            self.stats['rejected_signals'] += 1
            reason = validation.rejection_reason or "unknown"
            self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1
    
    def get_recent_signals(self, n: int = 10) -> List[Dict]:
        """
        최근 N개 시그널 조회
        
        Args:
            n: 조회할 개수
            
        Returns:
            시그널 리스트 (딕셔너리)
        """
        signals = list(self.signal_history)[-n:]
        return [
            {
                'timestamp': s.timestamp,
                'type': s.signal_type,
                'reason': s.reason,
                'price': s.close_price,
                'trend_ok': s.trend_condition,
                'entry_ok': s.entry_condition,
            }
            for s in signals
        ]
    
    def get_blocked_entries(self, n: int = 10) -> List[Dict]:
        """
        차단된 진입 시그널 조회
        
        ENTRY 시그널이 생성되었지만 검증에서 거부된 경우
        
        Args:
            n: 조회할 개수
            
        Returns:
            차단된 진입 시그널 리스트
        """
        blocked = [
            v for v in self.validation_history
            if v.signal.signal_type == "ENTRY" and not v.is_valid
        ]
        return [
            {
                'timestamp': v.signal.timestamp,
                'reason': v.rejection_reason,
                'mode': v.mode,
                'capital': v.capital,
                'price': v.signal.close_price,
            }
            for v in blocked[-n:]
        ]
    
    def get_entry_signals(self, n: int = 10) -> List[Dict]:
        """
        실행된 진입 시그널 조회
        
        Args:
            n: 조회할 개수
            
        Returns:
            실행된 진입 시그널 리스트
        """
        executed = [
            v for v in self.validation_history
            if v.signal.signal_type == "ENTRY" and v.is_valid
        ]
        return [
            {
                'timestamp': v.signal.timestamp,
                'mode': v.mode,
                'capital': v.capital,
                'price': v.signal.close_price,
            }
            for v in executed[-n:]
        ]
    
    def get_rejection_summary(self) -> Dict[str, int]:
        """
        거부 이유 요약
        
        Returns:
            거부 이유별 카운트 (no_signal 제외)
        """
        return {
            reason: count
            for reason, count in sorted(
                self.rejection_reasons.items(),
                key=lambda x: -x[1]
            )
            if "no_signal" not in reason
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        전체 통계 조회
        
        Returns:
            통계 딕셔너리
        """
        return {
            **self.stats,
            'rejection_reasons': self.get_rejection_summary(),
        }
    
    def print_summary(self):
        """파이프라인 요약 출력"""
        print(f"\n{'='*60}")
        print(f"📊 Signal Pipeline Summary")
        print(f"{'='*60}")
        print(f"총 시그널: {self.stats['total_signals']}")
        print(f"  - ENTRY: {self.stats['entry_signals']}")
        print(f"  - EXIT: {self.stats['exit_signals']}")
        print(f"검증 통과: {self.stats['valid_signals']}")
        print(f"검증 거부: {self.stats['rejected_signals']}")
        
        rejection_summary = self.get_rejection_summary()
        if rejection_summary:
            print(f"\n거부 이유:")
            for reason, count in rejection_summary.items():
                print(f"  - {reason}: {count}회")
        
        print(f"{'='*60}\n")
    
    def reset(self):
        """파이프라인 초기화"""
        self.signal_history.clear()
        self.validation_history.clear()
        self.stats = {
            'total_signals': 0,
            'entry_signals': 0,
            'exit_signals': 0,
            'valid_signals': 0,
            'rejected_signals': 0,
        }
        self.rejection_reasons.clear()
