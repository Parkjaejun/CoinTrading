# trading_engine_v2.py
"""
CoinTrading v2 트레이딩 엔진
- Long Only 전략
- 듀얼 모드 (Real/Virtual) 관리
- 시그널 파이프라인 통합
- 상세 디버깅 로깅

핵심 로직:
1. REAL 모드: 실제 자본으로 거래, 고점 대비 -20% 하락시 VIRTUAL 전환
2. VIRTUAL 모드: 가상 자본으로 모의 거래, 저점 대비 +30% 상승시 REAL 복귀
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

from config_v2 import ParamsV2, EmailConfig
from models import (
    Trade, Position, BarData, 
    SignalEvent, ValidationResult, OrderEvent, 
    ModeSwitchEvent, EngineStatus
)
from signal_pipeline import SignalPipeline
from email_notifier import EmailNotifier, MockEmailNotifier


class TradingEngineV2:
    """
    v2 트레이딩 엔진 - Long Only
    
    특징:
    - Short 포지션 완전 제거 (Long Only)
    - 듀얼 모드 (Real/Virtual) 자동 전환
    - 시그널 파이프라인 기반 디버깅
    - 이메일 알림 통합
    """
    
    def __init__(self, 
                 params: ParamsV2 = None,
                 email_notifier: Optional[EmailNotifier] = None,
                 symbol: str = "BTC-USDT-SWAP",
                 use_mock_email: bool = False):
        """
        Args:
            params: 전략 파라미터
            email_notifier: 이메일 알림기 (None이면 알림 비활성화)
            symbol: 거래 심볼
            use_mock_email: True면 실제 발송 없이 로그만
        """
        self.params = params or ParamsV2()
        self.symbol = symbol
        
        # 이메일 알림
        if use_mock_email:
            self.email_notifier = MockEmailNotifier()
        else:
            self.email_notifier = email_notifier
        
        # ===== 자본 관리 =====
        self.real_capital: float = 0.0
        self.real_peak: float = 0.0
        
        self.virtual_capital: float = self.params.virtual_baseline
        self.virtual_trough: float = self.params.virtual_baseline
        
        # ===== 모드 관리 =====
        self.is_real_mode: bool = True
        
        # ===== 포지션 =====
        self.position: Optional[Position] = None
        
        # ===== 거래/이벤트 기록 =====
        self.trades: List[Trade] = []
        self.mode_switches: List[ModeSwitchEvent] = []
        
        # ===== 시그널 파이프라인 =====
        self.pipeline = SignalPipeline(
            params=self.params,
            email_notifier=self.email_notifier,
            symbol=symbol
        )
        
        # ===== 통계 =====
        self.cnt_r2v: int = 0  # REAL→VIRTUAL 전환 횟수
        self.cnt_v2r: int = 0  # VIRTUAL→REAL 복귀 횟수
        self.bar_count: int = 0
        
        # ===== 디버깅 =====
        self.debug_log: List[str] = []
        self.equity_history_real: List[float] = []
        self.equity_history_virtual: List[float] = []
        
        self._log(f"🚀 TradingEngineV2 초기화: {symbol}")
        self._log(f"   - 레버리지: {self.params.leverage}x")
        self._log(f"   - 트레일링 스탑: {self.params.trailing_stop*100:.1f}%")
        self._log(f"   - 손절(R→V): {self.params.stop_loss_ratio*100:.1f}%")
        self._log(f"   - 복귀(V→R): {self.params.reentry_gain_ratio*100:.1f}%")
    
    # ===== 초기화 =====
    
    def init_capital(self, initial_real_capital: float):
        """자본 초기화"""
        self.real_capital = float(initial_real_capital)
        self.real_peak = self.real_capital
        
        self.virtual_capital = self.params.virtual_baseline
        self.virtual_trough = self.params.virtual_baseline
        
        self.is_real_mode = True
        self.position = None
        self.trades = []
        self.mode_switches = []
        
        self.cnt_r2v = 0
        self.cnt_v2r = 0
        self.bar_count = 0
        
        self.equity_history_real = [self.real_capital]
        self.equity_history_virtual = [self.virtual_capital]
        
        self._log(f"💰 자본 초기화: ${initial_real_capital:,.2f}")
    
    # ===== 헬퍼 메서드 =====
    
    def _log(self, msg: str):
        """디버그 로그"""
        if self.params.enable_debug_logging:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {msg}"
            self.debug_log.append(log_entry)
            print(log_entry)
    
    def _mode(self) -> Literal["REAL", "VIRTUAL"]:
        """현재 모드"""
        return "REAL" if self.is_real_mode else "VIRTUAL"
    
    def _current_capital(self) -> float:
        """현재 모드의 자본"""
        return self.real_capital if self.is_real_mode else self.virtual_capital
    
    def _fee_roundtrip(self, notional: float) -> float:
        """왕복 수수료"""
        return notional * self.params.fee_rate_per_side * 2.0
    
    def _get_trailing_stop_price(self) -> Optional[float]:
        """현재 포지션의 트레일링 스탑 가격"""
        if self.position is None:
            return None
        return self.position.peak_price * (1.0 - self.params.trailing_stop)
    
    # ===== 포지션 관리 =====
    
    def _open_position(self, timestamp: Any, price: float):
        """롱 포지션 진입"""
        cap = self._current_capital()
        effective = cap * self.params.capital_use_ratio
        
        notional = effective * self.params.leverage
        size = notional / price
        
        self.position = Position(
            side="LONG",
            mode=self._mode(),
            entry_time=timestamp,
            entry_price=price,
            size=size,
            leverage=self.params.leverage,
            peak_price=price,
            entry_capital=cap,
            entry_notional=notional,
        )
        
        # 주문 이벤트 기록
        order = OrderEvent(
            timestamp=timestamp,
            action="ENTRY",
            symbol=self.symbol,
            side="LONG",
            mode=self._mode(),
            price=price,
            size=size,
            leverage=self.params.leverage,
            capital_used=effective,
            reason="ema_golden_cross",
        )
        self.pipeline.record_entry_order(order)
        
        self._log(f"📈 LONG 진입 [{self._mode()}] @ ${price:,.2f} | "
                  f"size={size:.6f} | cap={cap:,.2f} | notional={notional:,.2f}")
    
    def _close_position(self, timestamp: Any, price: float, reason: str):
        """포지션 청산"""
        assert self.position is not None
        pos = self.position
        pos_mode = pos.mode
        
        # 청산 전 자본
        exit_cap_before = self.real_capital if pos_mode == "REAL" else self.virtual_capital
        
        # PnL 계산 (LONG only)
        pnl = (price - pos.entry_price) * pos.size
        fee = self._fee_roundtrip(pos.entry_notional)
        net_pnl = pnl - fee
        
        # 손익 반영
        self._apply_pnl(pos_mode, net_pnl)
        
        # 청산 후 자본
        exit_cap_after = self.real_capital if pos_mode == "REAL" else self.virtual_capital
        
        # Trade 기록
        trade = Trade(
            side="LONG",
            mode=pos_mode,
            entry_time=pos.entry_time,
            entry_price=pos.entry_price,
            exit_time=timestamp,
            exit_price=price,
            size=pos.size,
            leverage=pos.leverage,
            reason_exit=reason,
            pnl=pnl,
            fee=fee,
            net_pnl=net_pnl,
            entry_capital=pos.entry_capital,
            entry_notional=pos.entry_notional,
            exit_capital_before=exit_cap_before,
            exit_capital_after=exit_cap_after,
        )
        self.trades.append(trade)
        
        # 주문 이벤트 기록
        order = OrderEvent(
            timestamp=timestamp,
            action="EXIT",
            symbol=self.symbol,
            side="LONG",
            mode=pos_mode,
            price=price,
            size=pos.size,
            leverage=pos.leverage,
            capital_used=0,
            reason=reason,
            pnl=pnl,
            net_pnl=net_pnl,
            capital_after=exit_cap_after,
        )
        self.pipeline.record_exit_order(order)
        
        pnl_emoji = "💰" if net_pnl > 0 else "📉"
        self._log(f"{pnl_emoji} LONG 청산 [{pos_mode}] @ ${price:,.2f} | "
                  f"PnL: ${net_pnl:+,.2f} | reason={reason} | "
                  f"cap: {exit_cap_before:,.2f} → {exit_cap_after:,.2f}")
        
        self.position = None
    
    def _apply_pnl(self, mode: Literal["REAL", "VIRTUAL"], net_pnl: float):
        """손익 반영"""
        if mode == "REAL":
            self.real_capital += net_pnl
            self.real_peak = max(self.real_peak, self.real_capital)
        else:
            self.virtual_capital += net_pnl
            self.virtual_trough = min(self.virtual_trough, self.virtual_capital)
    
    # ===== 모드 전환 =====
    
    def _switch_to_virtual(self, timestamp: Any, trigger_value: float):
        """REAL → VIRTUAL 전환"""
        self.cnt_r2v += 1
        
        event = ModeSwitchEvent(
            timestamp=timestamp,
            from_mode="REAL",
            to_mode="VIRTUAL",
            reason=f"real_capital <= real_peak * (1 - {self.params.stop_loss_ratio})",
            real_capital=self.real_capital,
            real_peak=self.real_peak,
            virtual_capital=self.virtual_capital,
            virtual_trough=self.virtual_trough,
            trigger_value=trigger_value,
            threshold=self.params.stop_loss_ratio,
        )
        self.mode_switches.append(event)
        
        # 모드 전환
        self.is_real_mode = False
        
        # Virtual 자본 리셋
        self.virtual_capital = self.params.virtual_baseline
        self.virtual_trough = self.params.virtual_baseline
        
        # Real peak 리셋 (옵션)
        if self.params.reset_real_peak_on_r2v:
            self.real_peak = self.real_capital
        
        self._log(f"⚠️ 모드 전환: REAL → VIRTUAL (#{self.cnt_r2v})")
        self._log(f"   - 손실률: {trigger_value*100:.2f}% (기준: {self.params.stop_loss_ratio*100:.1f}%)")
        self._log(f"   - Real 자본: ${self.real_capital:,.2f}")
        
        # 이메일 알림
        if self.email_notifier:
            self.email_notifier.send_mode_switch_alert(event.to_dict())
    
    def _switch_to_real(self, timestamp: Any, trigger_value: float):
        """VIRTUAL → REAL 복귀"""
        self.cnt_v2r += 1
        
        event = ModeSwitchEvent(
            timestamp=timestamp,
            from_mode="VIRTUAL",
            to_mode="REAL",
            reason=f"virtual_capital >= virtual_trough * (1 + {self.params.reentry_gain_ratio})",
            real_capital=self.real_capital,
            real_peak=self.real_peak,
            virtual_capital=self.virtual_capital,
            virtual_trough=self.virtual_trough,
            trigger_value=trigger_value,
            threshold=self.params.reentry_gain_ratio,
        )
        self.mode_switches.append(event)
        
        # 모드 전환
        self.is_real_mode = True
        
        # Virtual 자본 리셋
        self.virtual_capital = self.params.virtual_baseline
        self.virtual_trough = self.params.virtual_baseline
        
        # Real peak 리셋 (옵션)
        if self.params.reset_real_peak_on_v2r:
            self.real_peak = self.real_capital
        
        self._log(f"✅ 모드 전환: VIRTUAL → REAL (#{self.cnt_v2r})")
        self._log(f"   - 회복률: {trigger_value*100:.2f}% (기준: {self.params.reentry_gain_ratio*100:.1f}%)")
        self._log(f"   - Real 자본: ${self.real_capital:,.2f}")
        
        # 이메일 알림
        if self.email_notifier:
            self.email_notifier.send_mode_switch_alert(event.to_dict())
    
    def _check_and_switch_mode(self, timestamp: Any):
        """모드 전환 조건 체크"""
        if self.is_real_mode:
            # REAL → VIRTUAL 조건: 고점 대비 손실률 초과
            if self.real_peak > 0:
                loss_ratio = (self.real_peak - self.real_capital) / self.real_peak
                if loss_ratio >= self.params.stop_loss_ratio:
                    self._switch_to_virtual(timestamp, loss_ratio)
        else:
            # VIRTUAL → REAL 조건: 저점 대비 수익률 달성
            if self.virtual_trough > 0:
                gain_ratio = (self.virtual_capital - self.virtual_trough) / self.virtual_trough
                if gain_ratio >= self.params.reentry_gain_ratio:
                    self._switch_to_real(timestamp, gain_ratio)
    
    # ===== 메인 처리 =====
    
    def on_bar(self, data: BarData):
        """
        봉 데이터 처리 (메인 엔트리포인트)
        
        Args:
            data: BarData 객체
        """
        self.bar_count += 1
        
        # 1. 봉 시작: 모드 전환 체크
        self._check_and_switch_mode(data.timestamp)
        
        # 2. 포지션 peak 갱신 (트레일링 스탑용)
        if self.position is not None:
            self.position.peak_price = max(self.position.peak_price, data.close)
        
        # 3. 시그널 파이프라인 처리
        trailing_stop_price = self._get_trailing_stop_price()
        
        signal, validation = self.pipeline.process(
            data=data,
            position=self.position,
            is_real_mode=self.is_real_mode,
            current_capital=self._current_capital(),
            trailing_stop_price=trailing_stop_price
        )
        
        # 4. 검증 통과시 실행
        if validation.is_valid:
            if signal.signal_type == "ENTRY":
                self._open_position(data.timestamp, data.close)
            elif signal.signal_type == "EXIT":
                self._close_position(data.timestamp, data.close, signal.reason)
        
        # 5. 봉 종료: 모드 전환 체크
        self._check_and_switch_mode(data.timestamp)
        
        # 6. Virtual trough 갱신
        if not self.is_real_mode:
            self.virtual_trough = min(self.virtual_trough, self.virtual_capital)
        
        # 7. Equity 히스토리 기록
        self.equity_history_real.append(self.real_capital)
        self.equity_history_virtual.append(self.virtual_capital)
        
        # 8. 주기적 디버그 로그
        if self.params.enable_debug_logging and self.bar_count % self.params.debug_log_interval == 0:
            self._print_periodic_status(data)
    
    def _print_periodic_status(self, data: BarData):
        """주기적 상태 출력"""
        mode_emoji = "🟢" if self.is_real_mode else "🟡"
        pos_str = f"LONG @ ${self.position.entry_price:,.2f}" if self.position else "None"
        
        print(f"\n--- Bar #{self.bar_count} | {data.timestamp} ---")
        print(f"Price: ${data.close:,.2f} | Mode: {mode_emoji} {self._mode()}")
        print(f"Real: ${self.real_capital:,.2f} (peak: ${self.real_peak:,.2f})")
        print(f"Virtual: ${self.virtual_capital:,.2f} (trough: ${self.virtual_trough:,.2f})")
        print(f"Position: {pos_str}")
        print(f"Trend: 150>{200 if data.ema_trend_fast > data.ema_trend_slow else '150<200'} "
              f"({data.ema_trend_fast:.2f} vs {data.ema_trend_slow:.2f})")
    
    # ===== 상태 조회 =====
    
    def get_status(self) -> EngineStatus:
        """엔진 상태 스냅샷"""
        initial_capital = self.equity_history_real[0] if self.equity_history_real else 10000
        real_roi = (self.real_capital - initial_capital) / initial_capital * 100 if initial_capital else 0
        
        # MDD 계산
        real_mdd = self._calc_mdd(self.equity_history_real) * 100
        
        return EngineStatus(
            timestamp=datetime.now(),
            is_real_mode=self.is_real_mode,
            mode=self._mode(),
            real_capital=self.real_capital,
            real_peak=self.real_peak,
            virtual_capital=self.virtual_capital,
            virtual_trough=self.virtual_trough,
            has_position=self.position is not None,
            position=self.position.to_dict() if self.position else None,
            total_trades=len(self.trades),
            real_trades=sum(1 for t in self.trades if t.mode == "REAL"),
            virtual_trades=sum(1 for t in self.trades if t.mode == "VIRTUAL"),
            mode_switches_r2v=self.cnt_r2v,
            mode_switches_v2r=self.cnt_v2r,
            real_roi_pct=real_roi,
            real_mdd_pct=real_mdd,
        )
    
    def _calc_mdd(self, equity_curve: List[float]) -> float:
        """MDD 계산"""
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]
        max_dd = 0.0
        for v in equity_curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd
    
    def get_debug_status(self) -> Dict[str, Any]:
        """디버깅용 상세 상태"""
        return {
            'engine': self.get_status().to_dict(),
            'pipeline': self.pipeline.get_status(),
            'recent_signals': self.pipeline.get_recent_signals(5),
            'blocked_entries': self.pipeline.get_blocked_entries(5),
            'mode_switches': [m.to_dict() for m in self.mode_switches[-5:]],
        }
    
    def print_summary(self):
        """최종 요약 출력"""
        status = self.get_status()
        initial = self.equity_history_real[0] if self.equity_history_real else 10000
        
        print(f"\n{'='*70}")
        print(f"📊 CoinTrading v2 - Final Summary")
        print(f"{'='*70}")
        print(f"심볼: {self.symbol}")
        print(f"총 봉 수: {self.bar_count}")
        print(f"초기 자본: ${initial:,.2f}")
        print()
        print(f"[REAL 성과]")
        print(f"  - 최종 자본: ${self.real_capital:,.2f}")
        print(f"  - ROI: {status.real_roi_pct:+.2f}%")
        print(f"  - MDD: -{status.real_mdd_pct:.2f}%")
        print(f"  - 거래 수: {status.real_trades}")
        print()
        print(f"[VIRTUAL 성과]")
        print(f"  - 현재 자본: ${self.virtual_capital:,.2f}")
        print(f"  - 거래 수: {status.virtual_trades}")
        print()
        print(f"[모드 전환]")
        print(f"  - REAL → VIRTUAL: {self.cnt_r2v}회")
        print(f"  - VIRTUAL → REAL: {self.cnt_v2r}회")
        print(f"  - 현재 모드: {self._mode()}")
        print()
        
        # 파이프라인 통계
        self.pipeline.print_debug_summary()
        
        # 최근 거래
        if self.trades:
            print(f"[최근 거래 (최대 5건)]")
            for trade in self.trades[-5:]:
                emoji = "💰" if trade.net_pnl > 0 else "📉"
                print(f"  {emoji} [{trade.mode}] {trade.entry_time} → {trade.exit_time} | "
                      f"PnL: ${trade.net_pnl:+,.2f} | {trade.reason_exit}")
        
        print(f"{'='*70}")
