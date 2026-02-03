# backtest/backtest_engine.py
"""
백테스트 엔진 모듈
- scratch_2.py의 CrossReverseDualModeVirtualResetEngine 기반
- GUI 연동을 위한 마커 데이터 및 이벤트 기록 추가
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any, List, Literal, Tuple, Dict
from datetime import datetime

import pandas as pd


# =========================
# 지표/교차 유틸
# =========================
def ema(series: pd.Series, period: int) -> pd.Series:
    """지수이동평균 계산"""
    return series.ewm(span=period, adjust=False).mean()


def cross_up(prev_fast: float, prev_slow: float, curr_fast: float, curr_slow: float) -> bool:
    """골든크로스 감지"""
    return (prev_fast <= prev_slow) and (curr_fast > curr_slow)


def cross_down(prev_fast: float, prev_slow: float, curr_fast: float, curr_slow: float) -> bool:
    """데드크로스 감지"""
    return (prev_fast >= prev_slow) and (curr_fast < curr_slow)


def calc_mdd(equity_curve: List[float]) -> float:
    """MDD (최대 낙폭) 계산 - 비율로 반환 (0~1)"""
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


# =========================
# 데이터 구조
# =========================
@dataclass
class Trade:
    """완료된 거래 기록"""
    side: Literal["LONG", "SHORT"]
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
    
    # 검증용 (자본 연속성)
    entry_capital: float
    entry_notional: float
    exit_capital_before: float
    exit_capital_after: float
    
    @property
    def pnl_percentage(self) -> float:
        """수익률 (%)"""
        if self.entry_capital > 0:
            return (self.net_pnl / self.entry_capital) * 100
        return 0.0
    
    @property
    def holding_bars(self) -> int:
        """보유 기간 (봉 개수) - 대략적 계산"""
        if isinstance(self.entry_time, pd.Timestamp) and isinstance(self.exit_time, pd.Timestamp):
            delta = self.exit_time - self.entry_time
            return max(1, int(delta.total_seconds() / (30 * 60)))
        return 1


@dataclass
class Position:
    """활성 포지션"""
    side: Literal["LONG", "SHORT"]
    mode: Literal["REAL", "VIRTUAL"]
    entry_time: Any
    entry_price: float
    size: float
    leverage: float
    peak_price: float
    trough_price: float
    
    # 검증용
    entry_capital: float
    entry_notional: float


@dataclass
class MarkerEvent:
    """차트 마커 이벤트"""
    time: Any
    price: float
    event_type: Literal["ENTRY", "EXIT", "TRAILING_STOP_HIT", "MODE_SWITCH"]
    side: Optional[Literal["LONG", "SHORT"]] = None
    mode: Optional[Literal["REAL", "VIRTUAL"]] = None
    reason: str = ""
    details: Dict = field(default_factory=dict)


@dataclass
class Params:
    """백테스트 파라미터"""
    # EMA periods
    trend_fast: int = 150
    trend_slow: int = 200
    entry_fast: int = 20
    entry_slow: int = 50
    long_exit_fast: int = 20
    long_exit_slow: int = 100
    short_exit_fast: int = 100
    short_exit_slow: int = 200
    
    # leverage
    leverage_long: float = 10.0
    leverage_short: float = 3.0
    
    # trailing stop
    trailing_stop_long: float = 0.10  # 10%
    trailing_stop_short: float = 0.02  # 2%
    
    # stop loss / reentry
    stop_loss_ratio_long: float = 0.20
    reentry_gain_ratio_long: float = 0.30
    stop_loss_ratio_short: float = 0.10
    reentry_gain_ratio_short: float = 0.20
    
    # 공유 계좌 임계값 방식
    use_conservative_shared_thresholds: bool = True
    
    # sizing
    capital_use_ratio: float = 0.50
    
    # fee
    fee_rate_per_side: float = 0.0005  # 0.05%
    
    # 피크 리셋
    reset_real_peak_on_v2r: bool = True
    reset_real_peak_on_r2v: bool = True
    
    # Long Only 모드
    long_only: bool = True


@dataclass
class BacktestResult:
    """백테스트 결과"""
    # 기본 정보
    initial_capital: float
    final_real_capital: float
    final_virtual_capital: float
    
    # 거래 기록
    trades: List[Trade]
    
    # 마커 이벤트 (차트용)
    markers: List[MarkerEvent]
    
    # 자산 곡선
    equity_curve_real: List[Tuple[Any, float]]
    equity_curve_virtual: List[Tuple[Any, float]]
    
    # 통계
    total_trades: int
    real_trades: int
    virtual_trades: int
    winning_trades: int
    losing_trades: int
    
    # 수익률
    real_roi: float
    virtual_roi: float
    mdd_real: float
    mdd_virtual: float
    
    # 모드 전환
    r2v_switches: int
    v2r_switches: int
    
    # 현재 상태
    has_open_position: bool
    open_position: Optional[Position]
    
    # EMA 데이터 (차트용)
    ema_data: Optional[pd.DataFrame] = None
    
    @property
    def win_rate(self) -> float:
        """승률 (%)"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def avg_profit(self) -> float:
        """평균 수익 (이익 거래만)"""
        profits = [t.net_pnl for t in self.trades if t.net_pnl > 0]
        return sum(profits) / len(profits) if profits else 0.0
    
    @property
    def avg_loss(self) -> float:
        """평균 손실 (손실 거래만)"""
        losses = [t.net_pnl for t in self.trades if t.net_pnl < 0]
        return sum(losses) / len(losses) if losses else 0.0
    
    @property
    def profit_factor(self) -> float:
        """손익비"""
        gross_profit = sum(t.net_pnl for t in self.trades if t.net_pnl > 0)
        gross_loss = abs(sum(t.net_pnl for t in self.trades if t.net_pnl < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')


# =========================
# 백테스트 엔진
# =========================
class BacktestEngine:
    """
    백테스트 엔진 (Long Only 지원)
    - scratch_2.py의 CrossReverseDualModeVirtualResetEngine 기반
    - GUI 연동을 위한 마커 데이터 기록
    """
    
    def __init__(self, params: Params = None, initial_capital: float = 10000.0):
        self.p = params or Params()
        self.initial_capital = initial_capital
        self.virtual_baseline = 10000.0
        
        # 자본
        self.real_capital: float = initial_capital
        self.real_peak: float = initial_capital
        self.virtual_capital: float = self.virtual_baseline
        self.virtual_trough: float = self.virtual_baseline
        
        # 모드
        self.is_real_mode: bool = True
        
        # 포지션 및 거래
        self.pos: Optional[Position] = None
        self.trades: List[Trade] = []
        self.markers: List[MarkerEvent] = []
        
        # 자산 곡선
        self.equity_curve_real: List[Tuple[Any, float]] = []
        self.equity_curve_virtual: List[Tuple[Any, float]] = []
        
        # 전환 카운터
        self.cnt_r2v: int = 0
        self.cnt_v2r: int = 0
    
    def reset(self):
        """엔진 상태 초기화"""
        self.real_capital = self.initial_capital
        self.real_peak = self.initial_capital
        self.virtual_capital = self.virtual_baseline
        self.virtual_trough = self.virtual_baseline
        self.is_real_mode = True
        self.pos = None
        self.trades = []
        self.markers = []
        self.equity_curve_real = []
        self.equity_curve_virtual = []
        self.cnt_r2v = 0
        self.cnt_v2r = 0
    
    # --------- 유틸리티 ----------
    def _fee_roundtrip(self, notional: float) -> float:
        return notional * self.p.fee_rate_per_side * 2.0
    
    def _shared_thresholds(self) -> Tuple[float, float]:
        if self.p.use_conservative_shared_thresholds:
            stop_loss = min(self.p.stop_loss_ratio_long, self.p.stop_loss_ratio_short)
            reentry = min(self.p.reentry_gain_ratio_long, self.p.reentry_gain_ratio_short)
        else:
            stop_loss = self.p.stop_loss_ratio_long
            reentry = self.p.reentry_gain_ratio_long
        return stop_loss, reentry
    
    def _mode(self) -> Literal["REAL", "VIRTUAL"]:
        return "REAL" if self.is_real_mode else "VIRTUAL"
    
    def _current_capital(self) -> float:
        return self.real_capital if self.is_real_mode else self.virtual_capital
    
    def _apply_pnl_to_account(self, pos_mode: Literal["REAL", "VIRTUAL"], net: float):
        if pos_mode == "REAL":
            self.real_capital += net
            self.real_peak = max(self.real_peak, self.real_capital)
        else:
            self.virtual_capital += net
            self.virtual_trough = min(self.virtual_trough, self.virtual_capital)
    
    # --------- 포지션 관리 ----------
    def _open_position(self, side: Literal["LONG", "SHORT"], t, price: float):
        cap = self._current_capital()
        effective = cap * self.p.capital_use_ratio
        lev = self.p.leverage_long if side == "LONG" else self.p.leverage_short
        notional = effective * lev
        size = notional / price
        
        self.pos = Position(
            side=side,
            mode=self._mode(),
            entry_time=t,
            entry_price=price,
            size=size,
            leverage=lev,
            peak_price=price,
            trough_price=price,
            entry_capital=cap,
            entry_notional=notional,
        )
        
        # 마커 추가
        self.markers.append(MarkerEvent(
            time=t,
            price=price,
            event_type="ENTRY",
            side=side,
            mode=self._mode(),
            reason=f"{side} 진입",
            details={
                "capital": cap,
                "leverage": lev,
                "size": size,
                "notional": notional,
            }
        ))
    
    def _close_position(self, t, price: float, reason: str):
        if self.pos is None:
            return
        
        pos = self.pos
        pos_mode = pos.mode
        
        exit_cap_before = self.real_capital if pos_mode == "REAL" else self.virtual_capital
        
        # PnL 계산
        if pos.side == "LONG":
            pnl = (price - pos.entry_price) * pos.size
        else:
            pnl = (pos.entry_price - price) * pos.size
        
        fee = self._fee_roundtrip(pos.entry_notional)
        net = pnl - fee
        
        # 손익 반영
        self._apply_pnl_to_account(pos_mode, net)
        
        exit_cap_after = self.real_capital if pos_mode == "REAL" else self.virtual_capital
        
        # 거래 기록
        trade = Trade(
            side=pos.side,
            mode=pos_mode,
            entry_time=pos.entry_time,
            entry_price=pos.entry_price,
            exit_time=t,
            exit_price=price,
            size=pos.size,
            leverage=pos.leverage,
            reason_exit=reason,
            pnl=pnl,
            fee=fee,
            net_pnl=net,
            entry_capital=pos.entry_capital,
            entry_notional=pos.entry_notional,
            exit_capital_before=exit_cap_before,
            exit_capital_after=exit_cap_after,
        )
        self.trades.append(trade)
        
        # 마커 추가
        self.markers.append(MarkerEvent(
            time=t,
            price=price,
            event_type="EXIT",
            side=pos.side,
            mode=pos_mode,
            reason=reason,
            details={
                "pnl": pnl,
                "net_pnl": net,
                "fee": fee,
                "pnl_pct": trade.pnl_percentage,
            }
        ))
        
        self.pos = None
    
    # --------- 모드 전환 ----------
    def _switch_to_virtual(self, t, price):
        self.cnt_r2v += 1
        self.is_real_mode = False
        self.virtual_capital = self.virtual_baseline
        self.virtual_trough = self.virtual_baseline
        
        if self.p.reset_real_peak_on_r2v:
            self.real_peak = self.real_capital
        
        self.markers.append(MarkerEvent(
            time=t,
            price=price,
            event_type="MODE_SWITCH",
            mode="VIRTUAL",
            reason="REAL→VIRTUAL (손실 임계값 도달)",
            details={"real_capital": self.real_capital, "real_peak": self.real_peak}
        ))
    
    def _switch_to_real(self, t, price):
        self.cnt_v2r += 1
        self.is_real_mode = True
        self.virtual_capital = self.virtual_baseline
        self.virtual_trough = self.virtual_baseline
        
        if self.p.reset_real_peak_on_v2r:
            self.real_peak = self.real_capital
        
        self.markers.append(MarkerEvent(
            time=t,
            price=price,
            event_type="MODE_SWITCH",
            mode="REAL",
            reason="VIRTUAL→REAL (회복 임계값 도달)",
            details={"virtual_capital": self.virtual_capital, "virtual_trough": self.virtual_trough}
        ))
    
    def _check_and_switch_mode(self, t, price):
        stop_loss, reentry = self._shared_thresholds()
        
        if self.is_real_mode:
            if self.real_capital <= self.real_peak * (1.0 - stop_loss):
                self._switch_to_virtual(t, price)
        else:
            if self.virtual_capital >= self.virtual_trough * (1.0 + reentry):
                self._switch_to_real(t, price)
    
    # --------- 봉 처리 ----------
    def on_bar(
        self,
        t,
        close_price: float,
        trend_fast: float,
        trend_slow: float,
        prev_e20: float,
        prev_e50: float,
        curr_e20: float,
        curr_e50: float,
        prev_lx_fast: float,
        prev_lx_slow: float,
        curr_lx_fast: float,
        curr_lx_slow: float,
        prev_sx_fast: float = 0,
        prev_sx_slow: float = 0,
        curr_sx_fast: float = 0,
        curr_sx_slow: float = 0,
    ):
        # (A) 전환 체크
        self._check_and_switch_mode(t, close_price)
        
        # (B) 포지션 peak/trough 갱신
        if self.pos is not None:
            if self.pos.side == "LONG":
                self.pos.peak_price = max(self.pos.peak_price, close_price)
            else:
                self.pos.trough_price = min(self.pos.trough_price, close_price)
        
        # (C) 진입 신호
        long_trend_ok = trend_fast > trend_slow
        short_trend_ok = trend_fast < trend_slow
        long_entry = long_trend_ok and cross_up(prev_e20, prev_e50, curr_e20, curr_e50)
        short_entry = False if self.p.long_only else (short_trend_ok and cross_down(prev_e20, prev_e50, curr_e20, curr_e50))
        
        # (D) 리버스 (Long Only면 숏 진입 없음)
        if self.pos is not None and not self.p.long_only:
            if self.pos.side == "LONG" and short_entry:
                self._close_position(t, close_price, "reverse_to_short")
                self._open_position("SHORT", t, close_price)
                self._check_and_switch_mode(t, close_price)
                return
            
            if self.pos.side == "SHORT" and long_entry:
                self._close_position(t, close_price, "reverse_to_long")
                self._open_position("LONG", t, close_price)
                self._check_and_switch_mode(t, close_price)
                return
        
        # (E) 일반 청산
        if self.pos is not None:
            if self.pos.side == "LONG":
                # EMA 데드크로스
                if cross_down(prev_lx_fast, prev_lx_slow, curr_lx_fast, curr_lx_slow):
                    self._close_position(t, close_price, "ema_dead_cross")
                    self._check_and_switch_mode(t, close_price)
                    return
                
                # 트레일링 스탑
                stop_price = self.pos.peak_price * (1.0 - self.p.trailing_stop_long)
                if close_price <= stop_price:
                    self._close_position(t, close_price, "trailing_stop")
                    self._check_and_switch_mode(t, close_price)
                    return
            
            else:  # SHORT
                if cross_up(prev_sx_fast, prev_sx_slow, curr_sx_fast, curr_sx_slow):
                    self._close_position(t, close_price, "ema_golden_cross")
                    self._check_and_switch_mode(t, close_price)
                    return
                
                stop_price = self.pos.trough_price * (1.0 + self.p.trailing_stop_short)
                if close_price >= stop_price:
                    self._close_position(t, close_price, "trailing_stop")
                    self._check_and_switch_mode(t, close_price)
                    return
        
        # (F) 신규 진입
        if self.pos is None:
            if long_entry:
                self._open_position("LONG", t, close_price)
                self._check_and_switch_mode(t, close_price)
                return
            if short_entry:
                self._open_position("SHORT", t, close_price)
                self._check_and_switch_mode(t, close_price)
                return
        
        # (G) virtual trough 갱신
        if not self.is_real_mode:
            self.virtual_trough = min(self.virtual_trough, self.virtual_capital)
        
        # (H) 마지막 전환 체크
        self._check_and_switch_mode(t, close_price)
    
    # --------- 백테스트 실행 ----------
    def run(self, df: pd.DataFrame, progress_callback=None) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            df: OHLC 데이터 (timestamp, open, high, low, close 컬럼 필요)
            progress_callback: 진행률 콜백 (current, total, message)
        
        Returns:
            BacktestResult
        """
        self.reset()
        
        close = df["close"].astype(float)
        
        # EMA 계산
        df = df.copy()
        df["ema_trend_fast"] = ema(close, self.p.trend_fast)
        df["ema_trend_slow"] = ema(close, self.p.trend_slow)
        df["ema_e20"] = ema(close, self.p.entry_fast)
        df["ema_e50"] = ema(close, self.p.entry_slow)
        df["ema_lx_fast"] = ema(close, self.p.long_exit_fast)
        df["ema_lx_slow"] = ema(close, self.p.long_exit_slow)
        df["ema_sx_fast"] = ema(close, self.p.short_exit_fast)
        df["ema_sx_slow"] = ema(close, self.p.short_exit_slow)
        
        # 시작 인덱스
        start_idx = max(
            self.p.trend_slow, 
            self.p.short_exit_slow, 
            self.p.long_exit_slow, 
            self.p.entry_slow
        )
        
        if len(df) <= start_idx + 2:
            raise ValueError("데이터가 너무 짧습니다.")
        
        total_bars = len(df) - start_idx - 1
        
        # 초기 자산곡선 기록
        self.equity_curve_real.append((df.iloc[start_idx]["datetime_utc"], self.real_capital))
        self.equity_curve_virtual.append((df.iloc[start_idx]["datetime_utc"], self.virtual_capital))
        
        # 봉 순회
        for i in range(start_idx + 1, len(df)):
            prev = df.iloc[i - 1]
            row = df.iloc[i]
            
            t = row["datetime_utc"] if "datetime_utc" in row else row["timestamp"]
            
            self.on_bar(
                t=t,
                close_price=float(row["close"]),
                trend_fast=float(row["ema_trend_fast"]),
                trend_slow=float(row["ema_trend_slow"]),
                prev_e20=float(prev["ema_e20"]),
                prev_e50=float(prev["ema_e50"]),
                curr_e20=float(row["ema_e20"]),
                curr_e50=float(row["ema_e50"]),
                prev_lx_fast=float(prev["ema_lx_fast"]),
                prev_lx_slow=float(prev["ema_lx_slow"]),
                curr_lx_fast=float(row["ema_lx_fast"]),
                curr_lx_slow=float(row["ema_lx_slow"]),
                prev_sx_fast=float(prev["ema_sx_fast"]),
                prev_sx_slow=float(prev["ema_sx_slow"]),
                curr_sx_fast=float(row["ema_sx_fast"]),
                curr_sx_slow=float(row["ema_sx_slow"]),
            )
            
            # 자산곡선 기록
            self.equity_curve_real.append((t, self.real_capital))
            self.equity_curve_virtual.append((t, self.virtual_capital))
            
            # 진행률 콜백
            if progress_callback and (i % 100 == 0 or i == len(df) - 1):
                progress = int((i - start_idx) / total_bars * 100)
                progress_callback(i - start_idx, total_bars, f"백테스트 진행 중... {progress}%")
        
        # 결과 생성
        equity_real_values = [e[1] for e in self.equity_curve_real]
        equity_virtual_values = [e[1] for e in self.equity_curve_virtual]
        
        real_roi = (self.real_capital - self.initial_capital) / self.initial_capital * 100
        virtual_roi = (self.virtual_capital - self.virtual_baseline) / self.virtual_baseline * 100
        
        mdd_real = calc_mdd(equity_real_values) * 100
        mdd_virtual = calc_mdd(equity_virtual_values) * 100
        
        winning = sum(1 for t in self.trades if t.net_pnl > 0)
        losing = sum(1 for t in self.trades if t.net_pnl <= 0)
        real_cnt = sum(1 for t in self.trades if t.mode == "REAL")
        virtual_cnt = sum(1 for t in self.trades if t.mode == "VIRTUAL")
        
        return BacktestResult(
            initial_capital=self.initial_capital,
            final_real_capital=self.real_capital,
            final_virtual_capital=self.virtual_capital,
            trades=self.trades,
            markers=self.markers,
            equity_curve_real=self.equity_curve_real,
            equity_curve_virtual=self.equity_curve_virtual,
            total_trades=len(self.trades),
            real_trades=real_cnt,
            virtual_trades=virtual_cnt,
            winning_trades=winning,
            losing_trades=losing,
            real_roi=real_roi,
            virtual_roi=virtual_roi,
            mdd_real=mdd_real,
            mdd_virtual=mdd_virtual,
            r2v_switches=self.cnt_r2v,
            v2r_switches=self.cnt_v2r,
            has_open_position=self.pos is not None,
            open_position=self.pos,
            ema_data=df[["datetime_utc", "close", "ema_trend_fast", "ema_trend_slow", 
                         "ema_e20", "ema_e50", "ema_lx_fast", "ema_lx_slow"]].copy() if "datetime_utc" in df.columns else None,
        )
    
    def get_entry_exit_points(self) -> List[Dict]:
        """차트 마커용 진입/청산 포인트 반환"""
        points = []
        for marker in self.markers:
            if marker.event_type in ["ENTRY", "EXIT"]:
                points.append({
                    "time": marker.time,
                    "price": marker.price,
                    "type": marker.event_type,
                    "side": marker.side,
                    "mode": marker.mode,
                    "reason": marker.reason,
                })
        return points
