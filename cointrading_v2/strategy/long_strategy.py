# strategy/long_strategy.py
"""
롱 전략 v2 (Long Only)

기존 인터페이스 유지 + v2 기능 추가:
- SignalPipeline 통합 (디버깅)
- EmailNotifier 통합 (알림)
- 향상된 모니터링

알고리즘:
- 진입: 150>200 EMA (상승장) + 20>50 EMA 골든크로스
- 청산: 20<100 EMA 데드크로스 또는 트레일링 스탑 10%
- 듀얼 모드: 고점 -20% → VIRTUAL, 저점 +30% → REAL
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.signal_pipeline import SignalPipeline, SignalEvent, ValidationResult, TradeRecord
from strategy.email_notifier import EmailNotifier, MockEmailNotifier

try:
    from config import LONG_STRATEGY_CONFIG, DEBUG_CONFIG
except ImportError:
    # 기본 설정
    LONG_STRATEGY_CONFIG = {
        'trend_fast': 150,
        'trend_slow': 200,
        'entry_fast': 20,
        'entry_slow': 50,
        'exit_fast': 20,
        'exit_slow': 100,
        'leverage': 10,
        'trailing_stop': 0.10,
        'stop_loss': 0.20,
        'reentry_gain': 0.30,
        'capital_use_ratio': 0.50,
        'fee_rate': 0.0005,
    }
    DEBUG_CONFIG = {
        'enable_debug_logging': True,
        'monitoring_interval': 30,
    }


class LongStrategy:
    """
    롱 전략 v2 - Long Only
    
    기존 LongStrategy 인터페이스 완전 호환
    + SignalPipeline + EmailNotifier 통합
    """
    
    def __init__(self, symbol: str, initial_capital: float,
                 email_notifier: EmailNotifier = None,
                 config: Dict = None):
        """
        Args:
            symbol: 거래 심볼 (예: 'BTC-USDT-SWAP')
            initial_capital: 초기 자본
            email_notifier: 이메일 알림 객체 (옵션)
            config: 전략 설정 (옵션)
        """
        self.strategy_name = "long_strategy_v2"
        self.symbol = symbol
        
        # 설정 로드
        self.config = config or LONG_STRATEGY_CONFIG
        self.leverage = self.config.get('leverage', 10)
        self.trailing_stop_ratio = self.config.get('trailing_stop', 0.10)
        self.stop_loss_ratio = self.config.get('stop_loss', 0.20)
        self.reentry_gain_ratio = self.config.get('reentry_gain', 0.30)
        self.capital_use_ratio = self.config.get('capital_use_ratio', 0.50)
        self.fee_rate = self.config.get('fee_rate', 0.0005)
        
        # ===== 듀얼 자본 시스템 =====
        self.initial_capital = float(initial_capital)
        self.real_capital = float(initial_capital)
        self.virtual_capital = 10000.0  # 가상 자본 기준값
        self.virtual_baseline = 10000.0
        
        self.is_real_mode = True
        self.real_peak = float(initial_capital)
        self.virtual_trough = self.virtual_baseline
        
        # ===== 포지션 상태 =====
        self.is_position_open = False
        self.entry_price = 0.0
        self.entry_time = None
        self.position_size = 0.0
        self.peak_price = 0.0  # 트레일링 스탑용
        self.entry_capital = 0.0
        self.entry_notional = 0.0
        
        # ===== 거래 기록 =====
        self.trades: List[TradeRecord] = []
        self.trade_count = 0
        self.win_count = 0
        self.total_pnl = 0.0
        
        # ===== 모드 전환 카운터 =====
        self.cnt_r2v = 0  # REAL → VIRTUAL 횟수
        self.cnt_v2r = 0  # VIRTUAL → REAL 횟수
        
        # ===== v2 추가: 시그널 파이프라인 =====
        self.pipeline = SignalPipeline()
        
        # ===== v2 추가: 이메일 알림 =====
        self.email_notifier = email_notifier
        
        # ===== 모니터링 =====
        self.last_ema_values: Dict[str, float] = {}
        self.bar_count = 0
        self.last_signal_check = 0
        self.monitoring_interval = DEBUG_CONFIG.get('monitoring_interval', 30)
        
        # 상태 히스토리 (모니터링용)
        self.trend_history: List[Dict] = []
        self.signal_history: List[Dict] = []
        
        print(f"✅ LongStrategy v2 초기화: {symbol}")
        print(f"   - 자본: ${initial_capital:,.2f}")
        print(f"   - 레버리지: {self.leverage}x")
        print(f"   - 트레일링 스탑: {self.trailing_stop_ratio*100:.1f}%")
        print(f"   - 손절(R→V): {self.stop_loss_ratio*100:.1f}%")
        print(f"   - 복귀(V→R): {self.reentry_gain_ratio*100:.1f}%")
    
    # ===== 헬퍼 메서드 =====
    
    def _mode(self) -> str:
        """현재 모드 문자열"""
        return "REAL" if self.is_real_mode else "VIRTUAL"
    
    def _current_capital(self) -> float:
        """현재 모드의 자본"""
        return self.real_capital if self.is_real_mode else self.virtual_capital
    
    def _fee_roundtrip(self, notional: float) -> float:
        """왕복 수수료 계산"""
        return notional * self.fee_rate * 2.0
    
    def _get_trailing_stop_price(self) -> Optional[float]:
        """트레일링 스탑 가격"""
        if not self.is_position_open:
            return None
        return self.peak_price * (1.0 - self.trailing_stop_ratio)
    
    # ===== 조건 체크 메서드 =====
    
    def check_trend_condition(self, data: Dict[str, Any]) -> bool:
        """
        상승장 확인: 150 EMA > 200 EMA
        
        Args:
            data: 캔들 데이터 딕셔너리
        
        Returns:
            상승장 여부
        """
        ema150 = data.get('ema_trend_fast')
        ema200 = data.get('ema_trend_slow')
        
        # EMA 값 저장
        self.last_ema_values['ema150'] = ema150
        self.last_ema_values['ema200'] = ema200
        
        if ema150 is None or ema200 is None:
            return False
        
        is_uptrend = ema150 > ema200
        
        # 트렌드 히스토리 업데이트
        if ema200 > 0:
            trend_strength = ((ema150 - ema200) / ema200 * 100)
            self.trend_history.append({
                'timestamp': datetime.now(),
                'is_uptrend': is_uptrend,
                'trend_strength': trend_strength,
                'ema150': ema150,
                'ema200': ema200
            })
            if len(self.trend_history) > 10:
                self.trend_history = self.trend_history[-10:]
        
        return is_uptrend
    
    def check_entry_condition(self, data: Dict[str, Any]) -> bool:
        """
        진입 조건: 20 EMA가 50 EMA 상향 돌파 (골든크로스)
        
        Args:
            data: 캔들 데이터 딕셔너리
        
        Returns:
            골든크로스 발생 여부
        """
        curr_20 = data.get('curr_entry_fast')
        curr_50 = data.get('curr_entry_slow')
        prev_20 = data.get('prev_entry_fast')
        prev_50 = data.get('prev_entry_slow')
        
        # EMA 값 저장
        self.last_ema_values.update({
            'curr_20': curr_20, 'curr_50': curr_50,
            'prev_20': prev_20, 'prev_50': prev_50
        })
        
        if None in [curr_20, curr_50, prev_20, prev_50]:
            return False
        
        # 골든크로스: 이전 <= 현재 >
        is_golden_cross = prev_20 <= prev_50 and curr_20 > curr_50
        
        # 시그널 히스토리 업데이트
        if curr_50 > 0:
            current_gap = ((curr_20 - curr_50) / curr_50 * 100)
            self.signal_history.append({
                'timestamp': datetime.now(),
                'is_golden_cross': is_golden_cross,
                'current_gap': current_gap,
                'curr_20': curr_20,
                'curr_50': curr_50
            })
            if len(self.signal_history) > 10:
                self.signal_history = self.signal_history[-10:]
        
        return is_golden_cross
    
    def check_exit_condition(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        청산 조건 확인
        
        1. EMA 데드크로스 (20 < 100)
        2. 트레일링 스탑 (고점 대비 10% 하락)
        
        Args:
            data: 캔들 데이터 딕셔너리
        
        Returns:
            (청산 여부, 청산 이유)
        """
        if not self.is_position_open:
            return False, ""
        
        curr_20 = data.get('curr_exit_fast')
        curr_100 = data.get('curr_exit_slow')
        prev_20 = data.get('prev_exit_fast')
        prev_100 = data.get('prev_exit_slow')
        close_price = data.get('close', 0)
        
        # 1. EMA 데드크로스 (20 < 100)
        if all(v is not None for v in [curr_20, curr_100, prev_20, prev_100]):
            if prev_20 >= prev_100 and curr_20 < curr_100:
                return True, "ema_dead_cross"
        
        # 2. 트레일링 스탑
        stop_price = self._get_trailing_stop_price()
        if stop_price and close_price <= stop_price:
            return True, f"trailing_stop (price={close_price:.2f} <= stop={stop_price:.2f})"
        
        return False, ""
    
    # ===== 기존 인터페이스 호환 메서드 =====
    
    def should_enter(self, data: Dict[str, Any]) -> bool:
        """
        진입 가능 여부 (기존 인터페이스 호환)
        
        Args:
            data: 캔들 데이터
        
        Returns:
            진입 가능 여부
        """
        if self.is_position_open:
            return False
        
        if self._current_capital() < 100:
            return False
        
        trend_ok = self.check_trend_condition(data)
        entry_ok = self.check_entry_condition(data) if trend_ok else False
        
        return trend_ok and entry_ok
    
    def should_exit(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        청산 여부 (기존 인터페이스 호환)
        
        Args:
            data: 캔들 데이터
        
        Returns:
            (청산 여부, 청산 이유)
        """
        return self.check_exit_condition(data)
    
    def enter_position(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        포지션 진입 (기존 인터페이스 호환)
        
        Args:
            data: 캔들 데이터
        
        Returns:
            진입 결과 딕셔너리
        """
        return self._open_position(data, "ema_golden_cross")
    
    def exit_position(self, data: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
        """
        포지션 청산 (기존 인터페이스 호환)
        
        Args:
            data: 캔들 데이터
            reason: 청산 이유
        
        Returns:
            청산 결과 딕셔너리
        """
        trade = self._close_position(data, reason)
        if trade:
            return {
                'action': 'exit',
                'symbol': self.symbol,
                'exit_price': trade.exit_price,
                'pnl': trade.pnl,
                'net_pnl': trade.net_pnl,
                'pnl_percentage': trade.pnl_percentage,
                'is_real_mode': trade.mode == "REAL",
                'reason': trade.reason_exit,
            }
        return None
    
    # ===== 시그널 생성/검증 (v2 파이프라인) =====
    
    def _generate_signal(self, data: Dict[str, Any]) -> SignalEvent:
        """
        시그널 생성
        
        Args:
            data: 캔들 데이터
        
        Returns:
            SignalEvent 객체
        """
        close_price = data.get('close', 0)
        
        trend_ok = self.check_trend_condition(data)
        entry_ok = self.check_entry_condition(data) if not self.is_position_open else False
        exit_ok, exit_reason = self.check_exit_condition(data)
        
        # 트레일링 스탑 체크
        stop_price = self._get_trailing_stop_price()
        trailing_triggered = stop_price and close_price <= stop_price if self.is_position_open else False
        
        # 시그널 결정
        signal_type = "NONE"
        reason = ""
        
        if self.is_position_open:
            if exit_ok:
                signal_type = "EXIT"
                reason = exit_reason
        else:
            if trend_ok and entry_ok:
                signal_type = "ENTRY"
                reason = "ema_golden_cross (20/50) + uptrend (150>200)"
            elif entry_ok and not trend_ok:
                reason = "entry_cross_but_no_trend"
            elif trend_ok and not entry_ok:
                reason = "trend_ok_but_no_entry_cross"
        
        return SignalEvent(
            timestamp=data.get('timestamp', datetime.now()),
            signal_type=signal_type,
            reason=reason,
            close_price=close_price,
            trend_condition=trend_ok,
            entry_condition=entry_ok,
            exit_condition=exit_ok,
            trailing_stop_triggered=trailing_triggered,
            ema_values=self.last_ema_values.copy()
        )
    
    def _validate_signal(self, signal: SignalEvent) -> ValidationResult:
        """
        시그널 검증
        
        Args:
            signal: SignalEvent 객체
        
        Returns:
            ValidationResult 객체
        """
        mode = self._mode()
        capital = self._current_capital()
        
        if signal.signal_type == "NONE":
            return ValidationResult(signal, False, "no_signal", mode, capital)
        
        if signal.signal_type == "ENTRY":
            if self.is_position_open:
                return ValidationResult(signal, False, "already_has_position", mode, capital)
            if capital < 100:
                return ValidationResult(signal, False, f"insufficient_capital ({capital:.2f})", mode, capital)
            return ValidationResult(signal, True, None, mode, capital)
        
        if signal.signal_type == "EXIT":
            if not self.is_position_open:
                return ValidationResult(signal, False, "no_position_to_close", mode, capital)
            return ValidationResult(signal, True, None, mode, capital)
        
        return ValidationResult(signal, False, "unknown_signal", mode, capital)
    
    # ===== 포지션 관리 =====
    
    def _open_position(self, data: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
        """
        포지션 진입
        
        Args:
            data: 캔들 데이터
            reason: 진입 이유
        
        Returns:
            진입 결과 딕셔너리
        """
        price = data.get('close', 0)
        timestamp = data.get('timestamp', datetime.now())
        
        cap = self._current_capital()
        effective = cap * self.capital_use_ratio
        notional = effective * self.leverage
        size = notional / price
        
        self.is_position_open = True
        self.entry_price = price
        self.entry_time = timestamp
        self.position_size = size
        self.peak_price = price
        self.entry_capital = cap
        self.entry_notional = notional
        
        mode = self._mode()
        print(f"📈 [{self.symbol}] LONG 진입 [{mode}] @ ${price:,.2f} | "
              f"size={size:.6f} | cap=${cap:,.2f}")
        
        # 이메일 알림
        if self.email_notifier:
            self.email_notifier.send_entry_alert({
                'symbol': self.symbol,
                'price': price,
                'size': size,
                'leverage': self.leverage,
                'mode': mode,
                'capital': cap,
                'reason': reason,
                'timestamp': timestamp,
            })
        
        return {
            'action': 'entry',
            'symbol': self.symbol,
            'entry_price': price,
            'is_real_mode': self.is_real_mode,
            'size': size,
        }
    
    def _close_position(self, data: Dict[str, Any], reason: str) -> Optional[TradeRecord]:
        """
        포지션 청산
        
        Args:
            data: 캔들 데이터
            reason: 청산 이유
        
        Returns:
            TradeRecord 객체
        """
        if not self.is_position_open:
            return None
        
        price = data.get('close', 0)
        timestamp = data.get('timestamp', datetime.now())
        
        pos_mode = self._mode()
        
        # PnL 계산
        pnl = (price - self.entry_price) * self.position_size
        fee = self._fee_roundtrip(self.entry_notional)
        net_pnl = pnl - fee
        
        # 손익 반영
        if self.is_real_mode:
            self.real_capital += net_pnl
            self.real_peak = max(self.real_peak, self.real_capital)
        else:
            self.virtual_capital += net_pnl
            self.virtual_trough = min(self.virtual_trough, self.virtual_capital)
        
        exit_cap_after = self._current_capital()
        
        # 거래 기록
        trade = TradeRecord(
            symbol=self.symbol,
            side="LONG",
            mode=pos_mode,
            entry_time=self.entry_time,
            entry_price=self.entry_price,
            entry_capital=self.entry_capital,
            exit_time=timestamp,
            exit_price=price,
            exit_capital=exit_cap_after,
            size=self.position_size,
            leverage=self.leverage,
            notional=self.entry_notional,
            pnl=pnl,
            fee=fee,
            net_pnl=net_pnl,
            reason_exit=reason,
        )
        self.trades.append(trade)
        
        # 통계 업데이트
        self.trade_count += 1
        self.total_pnl += net_pnl
        if net_pnl > 0:
            self.win_count += 1
        
        # 포지션 초기화
        self.is_position_open = False
        self.entry_price = 0.0
        self.entry_time = None
        self.position_size = 0.0
        self.peak_price = 0.0
        
        emoji = "💰" if net_pnl > 0 else "📉"
        print(f"{emoji} [{self.symbol}] LONG 청산 [{pos_mode}] @ ${price:,.2f} | "
              f"PnL: ${net_pnl:+,.2f} | reason={reason}")
        
        # 이메일 알림
        if self.email_notifier:
            self.email_notifier.send_exit_alert({
                'symbol': self.symbol,
                'entry_price': trade.entry_price,
                'exit_price': price,
                'net_pnl': net_pnl,
                'mode': pos_mode,
                'reason': reason,
                'capital_after': exit_cap_after,
                'timestamp': timestamp,
            })
        
        return trade
    
    # ===== 모드 전환 =====
    
    def check_mode_switch(self) -> bool:
        """
        모드 전환 체크 및 실행
        
        Returns:
            전환 발생 여부
        """
        switched = False
        
        if self.is_real_mode:
            # REAL → VIRTUAL: 고점 대비 손실률 초과
            if self.real_peak > 0:
                loss_ratio = (self.real_peak - self.real_capital) / self.real_peak
                if loss_ratio >= self.stop_loss_ratio:
                    self._switch_to_virtual(loss_ratio)
                    switched = True
        else:
            # VIRTUAL → REAL: 저점 대비 수익률 달성
            if self.virtual_trough > 0:
                gain_ratio = (self.virtual_capital - self.virtual_trough) / self.virtual_trough
                if gain_ratio >= self.reentry_gain_ratio:
                    self._switch_to_real(gain_ratio)
                    switched = True
        
        return switched
    
    def _switch_to_virtual(self, trigger_value: float):
        """REAL → VIRTUAL 전환"""
        self.cnt_r2v += 1
        
        print(f"⚠️ [{self.symbol}] 모드 전환: REAL → VIRTUAL (#{self.cnt_r2v})")
        print(f"   - 손실률: {trigger_value*100:.2f}% (기준: {self.stop_loss_ratio*100:.1f}%)")
        print(f"   - Real 자본: ${self.real_capital:,.2f}")
        
        self.is_real_mode = False
        self.virtual_capital = self.virtual_baseline
        self.virtual_trough = self.virtual_baseline
        self.real_peak = self.real_capital
        
        if self.email_notifier:
            self.email_notifier.send_mode_switch_alert({
                'symbol': self.symbol,
                'from_mode': 'REAL',
                'to_mode': 'VIRTUAL',
                'reason': f'loss_ratio={trigger_value*100:.2f}%',
                'real_capital': self.real_capital,
                'virtual_capital': self.virtual_capital,
            })
    
    def _switch_to_real(self, trigger_value: float):
        """VIRTUAL → REAL 복귀"""
        self.cnt_v2r += 1
        
        print(f"✅ [{self.symbol}] 모드 전환: VIRTUAL → REAL (#{self.cnt_v2r})")
        print(f"   - 회복률: {trigger_value*100:.2f}% (기준: {self.reentry_gain_ratio*100:.1f}%)")
        print(f"   - Real 자본: ${self.real_capital:,.2f}")
        
        self.is_real_mode = True
        self.virtual_capital = self.virtual_baseline
        self.virtual_trough = self.virtual_baseline
        self.real_peak = self.real_capital
        
        if self.email_notifier:
            self.email_notifier.send_mode_switch_alert({
                'symbol': self.symbol,
                'from_mode': 'VIRTUAL',
                'to_mode': 'REAL',
                'reason': f'gain_ratio={trigger_value*100:.2f}%',
                'real_capital': self.real_capital,
                'virtual_capital': self.virtual_capital,
            })
    
    # ===== 메인 처리 (v2 파이프라인) =====
    
    def process_signal(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        신호 처리 - 메인 엔트리포인트
        
        기존 인터페이스 완전 호환
        
        Args:
            data: 캔들 데이터 딕셔너리
                - close: 종가
                - timestamp: 시간
                - ema_trend_fast: 150 EMA
                - ema_trend_slow: 200 EMA
                - curr_entry_fast: 현재 20 EMA
                - curr_entry_slow: 현재 50 EMA
                - prev_entry_fast: 이전 20 EMA
                - prev_entry_slow: 이전 50 EMA
                - curr_exit_fast: 현재 20 EMA (청산용)
                - curr_exit_slow: 현재 100 EMA (청산용)
                - prev_exit_fast: 이전 20 EMA (청산용)
                - prev_exit_slow: 이전 100 EMA (청산용)
        
        Returns:
            거래 결과 딕셔너리 또는 None
        """
        self.bar_count += 1
        
        try:
            # 1. 모드 전환 체크
            self.check_mode_switch()
            
            # 2. 포지션 peak 갱신
            if self.is_position_open:
                close_price = data.get('close', 0)
                self.peak_price = max(self.peak_price, close_price)
            
            # 3. 시그널 생성 (v2 파이프라인)
            signal = self._generate_signal(data)
            self.pipeline.record_signal(signal)
            
            # 4. 시그널 검증 (v2 파이프라인)
            validation = self._validate_signal(signal)
            self.pipeline.record_validation(validation)
            
            # 5. 검증 통과시 실행
            result = None
            if validation.is_valid:
                if signal.signal_type == "ENTRY":
                    result = self._open_position(data, signal.reason)
                elif signal.signal_type == "EXIT":
                    trade = self._close_position(data, signal.reason)
                    if trade:
                        result = {
                            'action': 'exit',
                            'symbol': self.symbol,
                            'exit_price': trade.exit_price,
                            'pnl': trade.pnl,
                            'net_pnl': trade.net_pnl,
                            'is_real_mode': trade.mode == "REAL",
                            'reason': trade.reason_exit,
                        }
            
            # 6. 봉 종료 후 모드 전환 체크
            self.check_mode_switch()
            
            # 7. Virtual trough 갱신
            if not self.is_real_mode:
                self.virtual_trough = min(self.virtual_trough, self.virtual_capital)
            
            return result
            
        except Exception as e:
            print(f"❌ LongStrategy 오류 ({self.symbol}): {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ===== 상태 조회 =====
    
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 조회"""
        return {
            'symbol': self.symbol,
            'mode': self._mode(),
            'real_capital': self.real_capital,
            'real_peak': self.real_peak,
            'virtual_capital': self.virtual_capital,
            'virtual_trough': self.virtual_trough,
            'is_position_open': self.is_position_open,
            'entry_price': self.entry_price,
            'peak_price': self.peak_price,
            'trade_count': self.trade_count,
            'win_count': self.win_count,
            'total_pnl': self.total_pnl,
            'mode_switches': {'r2v': self.cnt_r2v, 'v2r': self.cnt_v2r},
        }
    
    def get_debug_status(self) -> Dict[str, Any]:
        """디버그 상태 조회 (v2)"""
        return {
            **self.get_status(),
            'pipeline_stats': self.pipeline.get_stats(),
            'recent_signals': self.pipeline.get_recent_signals(5),
            'blocked_entries': self.pipeline.get_blocked_entries(5),
            'last_ema_values': self.last_ema_values,
        }
    
    def print_summary(self):
        """요약 출력"""
        status = self.get_status()
        win_rate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"📊 {self.symbol} LongStrategy v2 Summary")
        print(f"{'='*60}")
        print(f"모드: {status['mode']}")
        print(f"Real 자본: ${status['real_capital']:,.2f} (peak: ${status['real_peak']:,.2f})")
        print(f"Virtual 자본: ${status['virtual_capital']:,.2f}")
        print(f"거래: {self.trade_count}회 | 승률: {win_rate:.1f}%")
        print(f"총 PnL: ${self.total_pnl:+,.2f}")
        print(f"모드 전환: R→V={self.cnt_r2v}, V→R={self.cnt_v2r}")
        
        self.pipeline.print_summary()


# 하위 호환용 별칭
LongStrategyV2 = LongStrategy
