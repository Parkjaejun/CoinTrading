# signal_pipeline.py
"""
CoinTrading v2 시그널 파이프라인
- 시그널 생성 (Signal Generator)
- 시그널 검증 (Signal Validator)  
- 주문 실행 (Order Executor)

핵심 디버깅 기능:
- 모든 시그널 이벤트 기록
- 왜 주문이 안 들어갔는지 추적
- 각 단계별 상태 확인
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Callable, TYPE_CHECKING
from datetime import datetime
from collections import deque

from models import (
    SignalEvent, ValidationResult, OrderEvent, 
    BarData, Position
)
from config_v2 import ParamsV2

if TYPE_CHECKING:
    from email_notifier import EmailNotifier


def cross_up(prev_fast: float, prev_slow: float, curr_fast: float, curr_slow: float) -> bool:
    """골든크로스 (상향 돌파)"""
    return (prev_fast <= prev_slow) and (curr_fast > curr_slow)


def cross_down(prev_fast: float, prev_slow: float, curr_fast: float, curr_slow: float) -> bool:
    """데드크로스 (하향 돌파)"""
    return (prev_fast >= prev_slow) and (curr_fast < curr_slow)


class SignalGenerator:
    """시그널 생성기 - Long Only"""
    
    def __init__(self, params: ParamsV2):
        self.params = params
    
    def generate(self, 
                 data: BarData, 
                 position: Optional[Position],
                 trailing_stop_price: Optional[float] = None) -> SignalEvent:
        """
        시그널 생성
        
        Returns:
            SignalEvent with signal_type: "ENTRY" | "EXIT" | "NONE"
        """
        # 조건 체크
        trend_ok = data.ema_trend_fast > data.ema_trend_slow
        
        entry_cross = cross_up(
            data.prev_entry_fast, data.prev_entry_slow,
            data.ema_entry_fast, data.ema_entry_slow
        )
        
        exit_cross = cross_down(
            data.prev_exit_fast, data.prev_exit_slow,
            data.ema_exit_fast, data.ema_exit_slow
        )
        
        # 트레일링 스탑 체크
        trailing_triggered = False
        if position and trailing_stop_price:
            trailing_triggered = data.close <= trailing_stop_price
        
        has_position = position is not None
        
        # 시그널 결정
        signal_type = "NONE"
        reason = ""
        
        if has_position:
            # 청산 조건 체크
            if trailing_triggered:
                signal_type = "EXIT"
                reason = f"trailing_stop (price={data.close:.2f} <= stop={trailing_stop_price:.2f})"
            elif exit_cross:
                signal_type = "EXIT"
                reason = "ema_dead_cross (20/100)"
        else:
            # 진입 조건 체크
            if trend_ok and entry_cross:
                signal_type = "ENTRY"
                reason = "ema_golden_cross (20/50) + uptrend (150>200)"
            elif entry_cross and not trend_ok:
                reason = "entry_cross_but_no_trend (150<200)"
            elif trend_ok and not entry_cross:
                reason = "trend_ok_but_no_entry_cross"
        
        return SignalEvent(
            timestamp=data.timestamp,
            signal_type=signal_type,
            reason=reason,
            close_price=data.close,
            ema_trend_fast=data.ema_trend_fast,
            ema_trend_slow=data.ema_trend_slow,
            ema_entry_fast=data.ema_entry_fast,
            ema_entry_slow=data.ema_entry_slow,
            ema_exit_fast=data.ema_exit_fast,
            ema_exit_slow=data.ema_exit_slow,
            prev_entry_fast=data.prev_entry_fast,
            prev_entry_slow=data.prev_entry_slow,
            prev_exit_fast=data.prev_exit_fast,
            prev_exit_slow=data.prev_exit_slow,
            trend_condition_met=trend_ok,
            entry_condition_met=entry_cross,
            exit_condition_met=exit_cross,
            trailing_stop_triggered=trailing_triggered,
            has_position=has_position,
            position_peak_price=position.peak_price if position else None,
        )


class SignalValidator:
    """시그널 검증기 - 주문 전 확인"""
    
    def __init__(self, params: ParamsV2):
        self.params = params
        self.last_entry_bar: int = -9999  # 쿨다운용
        self.current_bar: int = 0
    
    def validate(self,
                 signal: SignalEvent,
                 is_real_mode: bool,
                 current_capital: float,
                 has_position: bool) -> ValidationResult:
        """
        시그널 검증
        
        Returns:
            ValidationResult with is_valid and rejection_reason
        """
        mode = "REAL" if is_real_mode else "VIRTUAL"
        
        # 시그널이 없으면 패스
        if signal.signal_type == "NONE":
            return ValidationResult(
                signal=signal,
                is_valid=False,
                rejection_reason="no_signal",
                current_mode=mode,
                current_capital=current_capital,
            )
        
        # 진입 시그널 검증
        if signal.signal_type == "ENTRY":
            # 1. 포지션 체크 (중복 진입 방지)
            if has_position:
                return ValidationResult(
                    signal=signal,
                    is_valid=False,
                    rejection_reason="already_has_position",
                    position_check=False,
                    current_mode=mode,
                    current_capital=current_capital,
                )
            
            # 2. 자본 체크
            min_capital = 100  # 최소 $100
            if current_capital < min_capital:
                return ValidationResult(
                    signal=signal,
                    is_valid=False,
                    rejection_reason=f"insufficient_capital ({current_capital:.2f} < {min_capital})",
                    capital_check=False,
                    current_mode=mode,
                    current_capital=current_capital,
                )
            
            # 3. 쿨다운 체크
            if self.params.entry_cooldown_bars > 0:
                bars_since_last = self.current_bar - self.last_entry_bar
                if bars_since_last < self.params.entry_cooldown_bars:
                    return ValidationResult(
                        signal=signal,
                        is_valid=False,
                        rejection_reason=f"cooldown ({bars_since_last}/{self.params.entry_cooldown_bars} bars)",
                        cooldown_check=False,
                        current_mode=mode,
                        current_capital=current_capital,
                    )
            
            # 검증 통과
            return ValidationResult(
                signal=signal,
                is_valid=True,
                current_mode=mode,
                current_capital=current_capital,
            )
        
        # 청산 시그널 검증
        if signal.signal_type == "EXIT":
            # 포지션 체크
            if not has_position:
                return ValidationResult(
                    signal=signal,
                    is_valid=False,
                    rejection_reason="no_position_to_close",
                    position_check=False,
                    current_mode=mode,
                    current_capital=current_capital,
                )
            
            # 검증 통과
            return ValidationResult(
                signal=signal,
                is_valid=True,
                current_mode=mode,
                current_capital=current_capital,
            )
        
        # 알 수 없는 시그널
        return ValidationResult(
            signal=signal,
            is_valid=False,
            rejection_reason=f"unknown_signal_type: {signal.signal_type}",
            current_mode=mode,
            current_capital=current_capital,
        )
    
    def record_entry(self):
        """진입 기록 (쿨다운용)"""
        self.last_entry_bar = self.current_bar
    
    def advance_bar(self):
        """봉 카운터 증가"""
        self.current_bar += 1


class SignalPipeline:
    """
    시그널 파이프라인 - 시그널 처리 전체 흐름
    
    [Data] → [Generator] → [Validator] → [Executor] → [Notifier]
              ↓             ↓              ↓
           signal_log   validation_log  order_log
    """
    
    def __init__(self, 
                 params: ParamsV2,
                 email_notifier: Optional['EmailNotifier'] = None,
                 symbol: str = "BTC-USDT-SWAP"):
        self.params = params
        self.email_notifier = email_notifier
        self.symbol = symbol
        
        # 서브 컴포넌트
        self.generator = SignalGenerator(params)
        self.validator = SignalValidator(params)
        
        # 히스토리 (디버깅용)
        max_history = params.max_signal_history if params.enable_signal_history else 100
        self.signal_history: deque = deque(maxlen=max_history)
        self.validation_history: deque = deque(maxlen=max_history)
        self.order_history: List[OrderEvent] = []
        
        # 통계
        self.stats = {
            'total_signals': 0,
            'entry_signals': 0,
            'exit_signals': 0,
            'valid_signals': 0,
            'rejected_signals': 0,
            'executed_orders': 0,
        }
        
        # 거부 이유 카운터
        self.rejection_reasons: Dict[str, int] = {}
    
    def process(self,
                data: BarData,
                position: Optional[Position],
                is_real_mode: bool,
                current_capital: float,
                trailing_stop_price: Optional[float] = None
               ) -> tuple[SignalEvent, ValidationResult]:
        """
        파이프라인 전체 실행
        
        Returns:
            (signal, validation) 튜플
        """
        # 1. 시그널 생성
        signal = self.generator.generate(data, position, trailing_stop_price)
        self.signal_history.append(signal)
        self.stats['total_signals'] += 1
        
        if signal.signal_type == "ENTRY":
            self.stats['entry_signals'] += 1
        elif signal.signal_type == "EXIT":
            self.stats['exit_signals'] += 1
        
        # 2. 시그널 검증
        validation = self.validator.validate(
            signal, is_real_mode, current_capital, position is not None
        )
        self.validation_history.append(validation)
        
        if validation.is_valid:
            self.stats['valid_signals'] += 1
        else:
            self.stats['rejected_signals'] += 1
            reason = validation.rejection_reason or "unknown"
            self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1
        
        # 봉 카운터 증가
        self.validator.advance_bar()
        
        return signal, validation
    
    def record_entry_order(self, order: OrderEvent):
        """진입 주문 기록"""
        self.order_history.append(order)
        self.stats['executed_orders'] += 1
        self.validator.record_entry()
        
        # 이메일 알림
        if self.email_notifier:
            self.email_notifier.send_entry_alert({
                'symbol': self.symbol,
                'entry_price': order.price,
                'leverage': order.leverage,
                'mode': order.mode,
                'capital_used': order.capital_used,
                'size': order.size,
                'reason': order.reason,
                'timestamp': order.timestamp,
            })
    
    def record_exit_order(self, order: OrderEvent):
        """청산 주문 기록"""
        self.order_history.append(order)
        self.stats['executed_orders'] += 1
        
        # 이메일 알림
        if self.email_notifier:
            self.email_notifier.send_exit_alert({
                'symbol': self.symbol,
                'entry_price': order.price,  # 이 시점에서는 exit_price로 사용됨
                'exit_price': order.price,
                'mode': order.mode,
                'reason': order.reason,
                'net_pnl': order.net_pnl,
                'fee': 0,  # Trade에서 가져와야 함
                'capital_after': order.capital_after,
                'timestamp': order.timestamp,
            })
    
    def get_status(self) -> Dict[str, Any]:
        """파이프라인 상태 조회"""
        last_signal = self.signal_history[-1] if self.signal_history else None
        last_validation = self.validation_history[-1] if self.validation_history else None
        
        return {
            'stats': self.stats.copy(),
            'rejection_reasons': self.rejection_reasons.copy(),
            'last_signal': last_signal.to_dict() if last_signal else None,
            'last_validation': last_validation.to_dict() if last_validation else None,
            'recent_signals_count': len(self.signal_history),
            'total_orders': len(self.order_history),
        }
    
    def get_recent_signals(self, n: int = 10) -> List[Dict]:
        """최근 시그널 조회"""
        signals = list(self.signal_history)[-n:]
        return [s.to_dict() for s in signals]
    
    def get_recent_rejections(self, n: int = 10) -> List[Dict]:
        """최근 거부된 시그널 조회"""
        rejections = [v for v in self.validation_history if not v.is_valid]
        return [r.to_dict() for r in rejections[-n:]]
    
    def get_blocked_entries(self, n: int = 10) -> List[Dict]:
        """진입이 차단된 시그널만 조회"""
        blocked = [
            v for v in self.validation_history 
            if v.signal.signal_type == "ENTRY" and not v.is_valid
        ]
        return [b.to_dict() for b in blocked[-n:]]
    
    def print_debug_summary(self):
        """디버그 요약 출력"""
        status = self.get_status()
        stats = status['stats']
        
        print(f"\n{'='*60}")
        print(f"📊 Signal Pipeline Debug Summary")
        print(f"{'='*60}")
        print(f"총 시그널: {stats['total_signals']}")
        print(f"  - ENTRY 시그널: {stats['entry_signals']}")
        print(f"  - EXIT 시그널: {stats['exit_signals']}")
        print(f"검증 통과: {stats['valid_signals']}")
        print(f"검증 거부: {stats['rejected_signals']}")
        print(f"실행된 주문: {stats['executed_orders']}")
        
        if status['rejection_reasons']:
            print(f"\n📋 거부 이유 분석:")
            for reason, count in sorted(status['rejection_reasons'].items(), key=lambda x: -x[1]):
                if "no_signal" not in reason:  # no_signal은 제외
                    print(f"  - {reason}: {count}회")
        
        if status['last_signal']:
            print(f"\n🔔 마지막 시그널:")
            sig = status['last_signal']
            print(f"  Type: {sig['signal_type']}")
            print(f"  Reason: {sig['reason']}")
            print(f"  Price: ${sig['close_price']:,.2f}")
            print(f"  Trend OK: {sig['trend_condition_met']}")
        
        print(f"{'='*60}\n")
