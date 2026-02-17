# agents/state_manager.py
"""
공유 상태 관리자

잔고, 포지션, PnL, 전략 파라미터 등
모든 에이전트가 공유하는 상태를 thread-safe하게 관리한다.
OKX API를 통해 실시간 데이터를 갱신한다.
"""

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from copy import deepcopy

from config import make_api_request, LONG_STRATEGY_CONFIG, EMA_PERIODS
from utils.logger import log_system, log_error


class StateManager:
    """에이전트 팀 공유 상태 관리"""

    def __init__(self, initial_capital: float = 100.0, symbol: str = "BTC-USDT-SWAP",
                 dry_run: bool = False):
        """
        Args:
            initial_capital: 초기 자본 (USDT)
            symbol: 거래 대상 심볼
            dry_run: True면 private API 호출 건너뜀
        """
        self._lock = threading.RLock()
        self._symbol = symbol
        self._initial_capital = initial_capital
        self._dry_run = dry_run

        # 잔고 / 포지션 캐시
        self._balance: Optional[Dict] = None
        self._positions: List[Dict] = []
        self._current_price: float = 0.0
        self._last_balance_update: Optional[datetime] = None
        self._last_price_update: Optional[datetime] = None

        # PnL 추적
        self._cumulative_profit: float = 0.0
        self._peak_equity: float = initial_capital
        self._trade_history: List[Dict] = []

        # 전략 파라미터 (런타임 변경 가능)
        # agent_config에서 가져오되, 없으면 기존 config 기본값 사용
        from agents.agent_config import AGENT_TEAM_CONFIG as _atc
        self._strategy_params: Dict[str, Any] = {
            "leverage": _atc.get("leverage", LONG_STRATEGY_CONFIG.get("leverage", 10)),
            "trailing_stop": LONG_STRATEGY_CONFIG.get("trailing_stop", 0.10),
            "entry_fast": EMA_PERIODS.get("entry_fast", 20),
            "entry_slow": EMA_PERIODS.get("entry_slow", 50),
            "exit_fast": EMA_PERIODS.get("exit_fast", 20),
            "exit_slow": EMA_PERIODS.get("exit_slow", 100),
            "trend_fast": EMA_PERIODS.get("trend_fast", 150),
            "trend_slow": EMA_PERIODS.get("trend_slow", 200),
            "capital_use_ratio": 0.80,  # $59 계좌: 80% 사용($47) × 15x = $708 → 1계약
        }

        # 긴급 정지
        self._emergency_stop = False
        self._emergency_reason: Optional[str] = None
        self._entry_blocked = False  # 신규 진입만 차단

    # ==================== 잔고 / 포지션 ====================

    def refresh_balance(self) -> Optional[Dict]:
        """OKX API에서 잔고 갱신"""
        if self._dry_run:
            return self._balance
        try:
            result = make_api_request("GET", "/api/v5/account/balance")
            if result and result.get("code") == "0":
                with self._lock:
                    self._balance = result["data"][0]
                    self._last_balance_update = datetime.now()

                    # peak equity 갱신
                    equity = self._get_usdt_equity_unlocked()
                    if equity > self._peak_equity:
                        self._peak_equity = equity

                return self._balance
        except Exception as e:
            log_error(f"[StateManager] 잔고 갱신 실패: {e}")
        return None

    def refresh_positions(self) -> List[Dict]:
        """OKX API에서 포지션 갱신"""
        if self._dry_run:
            return self._positions
        try:
            result = make_api_request(
                "GET", "/api/v5/account/positions",
                params={"instType": "SWAP"}
            )
            if result and result.get("code") == "0":
                with self._lock:
                    self._positions = []
                    for pos in result.get("data", []):
                        pos_size = float(pos.get("pos") or 0)
                        if pos_size != 0:
                            self._positions.append({
                                "inst_id": pos.get("instId"),
                                "pos_side": pos.get("posSide"),
                                "position": pos_size,
                                "avg_price": float(pos.get("avgPx") or 0),
                                "upl": float(pos.get("upl") or 0),
                                "upl_ratio": float(pos.get("uplRatio") or 0),
                                "leverage": pos.get("lever"),
                                "margin": float(pos.get("margin") or 0),
                                "notional_usd": float(pos.get("notionalUsd") or 0),
                            })
                return self._positions
        except Exception as e:
            log_error(f"[StateManager] 포지션 갱신 실패: {e}")
        return []

    def refresh_price(self) -> float:
        """OKX API에서 현재가 갱신"""
        try:
            result = make_api_request(
                "GET", "/api/v5/market/ticker",
                params={"instId": self._symbol}
            )
            if result and result.get("code") == "0":
                price = float(result["data"][0].get("last", 0))
                with self._lock:
                    self._current_price = price
                    self._last_price_update = datetime.now()
                return price
        except Exception as e:
            log_error(f"[StateManager] 가격 갱신 실패: {e}")
        return 0.0

    def get_balance(self) -> Optional[Dict]:
        """캐시된 잔고 반환"""
        with self._lock:
            return deepcopy(self._balance)

    def get_positions(self) -> List[Dict]:
        """캐시된 포지션 반환"""
        with self._lock:
            return deepcopy(self._positions)

    def get_current_price(self) -> float:
        """캐시된 현재가 반환"""
        with self._lock:
            return self._current_price

    def has_open_position(self) -> bool:
        """포지션 보유 여부"""
        with self._lock:
            return len(self._positions) > 0

    def get_position_direction(self) -> str:
        """포지션 방향 반환: 'long', 'short', 'none'"""
        with self._lock:
            if not self._positions:
                return "none"
            pos = self._positions[0]
            size = pos.get("position", 0)
            if size > 0:
                return "long"
            elif size < 0:
                return "short"
            return "none"

    # ==================== PnL ====================

    def get_initial_capital(self) -> float:
        return self._initial_capital

    def _get_usdt_equity_unlocked(self) -> float:
        """USDT 자산 (lock 미사용 — 내부 전용)"""
        if not self._balance:
            return self._initial_capital
        for detail in self._balance.get("details", []):
            if detail.get("ccy") == "USDT":
                return float(detail.get("eq") or 0)
        total_eq = float(self._balance.get("totalEq") or 0)
        return total_eq if total_eq > 0 else self._initial_capital

    def get_current_equity(self) -> float:
        """현재 자산 (USDT)"""
        with self._lock:
            return self._get_usdt_equity_unlocked()

    def get_current_pnl(self) -> float:
        """현재 손익 = 현재 자산 - 초기 자본"""
        return self.get_current_equity() - self._initial_capital

    def get_drawdown_pct(self) -> float:
        """고점 대비 Drawdown 비율 (0.0 ~ 1.0)"""
        with self._lock:
            equity = self._get_usdt_equity_unlocked()
            if self._peak_equity <= 0:
                return 0.0
            dd = (self._peak_equity - equity) / self._peak_equity
            return max(0.0, dd)

    def get_cumulative_profit(self) -> float:
        """누적 실현 수익"""
        with self._lock:
            return self._cumulative_profit

    def record_trade(self, trade: Dict) -> None:
        """거래 기록 추가"""
        with self._lock:
            self._trade_history.append(trade)
            pnl = trade.get("pnl", 0.0)
            self._cumulative_profit += pnl

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """거래 이력 조회"""
        with self._lock:
            return list(self._trade_history[-limit:])

    # ==================== 전략 파라미터 ====================

    def get_strategy_params(self) -> Dict[str, Any]:
        """현재 전략 파라미터 반환"""
        with self._lock:
            return deepcopy(self._strategy_params)

    def update_strategy_params(self, params: Dict[str, Any]) -> None:
        """전략 파라미터 업데이트"""
        with self._lock:
            self._strategy_params.update(params)
        log_system(f"[StateManager] 전략 파라미터 변경: {params}")

    # ==================== 긴급 정지 ====================

    def is_emergency_stopped(self) -> bool:
        with self._lock:
            return self._emergency_stop

    def set_emergency_stop(self, reason: str) -> None:
        """긴급 정지 설정"""
        with self._lock:
            self._emergency_stop = True
            self._emergency_reason = reason
        log_error(f"[StateManager] 🚨 긴급 정지: {reason}")

    def clear_emergency_stop(self) -> None:
        """긴급 정지 해제"""
        with self._lock:
            self._emergency_stop = False
            self._emergency_reason = None
        log_system("[StateManager] ✅ 긴급 정지 해제")

    def is_entry_blocked(self) -> bool:
        """신규 진입 차단 여부"""
        with self._lock:
            return self._entry_blocked or self._emergency_stop

    def set_entry_blocked(self, blocked: bool, reason: str = "") -> None:
        with self._lock:
            self._entry_blocked = blocked
        if blocked:
            log_system(f"[StateManager] 🚫 신규 진입 차단: {reason}")
        else:
            log_system("[StateManager] ✅ 신규 진입 허용")

    # ==================== 팀 상태 ====================

    def get_team_status(self) -> Dict[str, Any]:
        """팀 전체 상태 요약"""
        with self._lock:
            equity = self._get_usdt_equity_unlocked()
            return {
                "timestamp": datetime.now().isoformat(),
                "symbol": self._symbol,
                "initial_capital": self._initial_capital,
                "current_equity": equity,
                "current_pnl": equity - self._initial_capital,
                "cumulative_profit": self._cumulative_profit,
                "peak_equity": self._peak_equity,
                "drawdown_pct": self.get_drawdown_pct(),
                "current_price": self._current_price,
                "open_positions": len(self._positions),
                "total_trades": len(self._trade_history),
                "emergency_stop": self._emergency_stop,
                "emergency_reason": self._emergency_reason,
                "entry_blocked": self._entry_blocked,
                "strategy_params": deepcopy(self._strategy_params),
                "last_balance_update": (
                    self._last_balance_update.isoformat()
                    if self._last_balance_update else None
                ),
            }
