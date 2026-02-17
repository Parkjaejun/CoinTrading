# agents/strategist_agent.py
"""
Agent 3: Strategist (전략 최적화)

역할:
- 실시간 PnL/수익률 모니터링
- 시장 변동성 분석
- 성과 저조 시 Claude API로 파라미터 최적화 제안
- 심각한 경우 전략 코드 수정 제안
- 변경 사항을 Monitor에 승인 요청
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List

from agents.base_agent import BaseAgent
from agents.message_bus import (
    MSG_PARAM_CHANGE, MSG_CODE_CHANGE, MSG_TRADE_RESULT,
    MSG_APPROVAL, MSG_REJECTION, MSG_STATUS, MSG_EMERGENCY_STOP,
)
from agents.agent_config import AGENT_TEAM_CONFIG
from config import make_api_request
from utils.logger import log_system, log_error


class StrategistAgent(BaseAgent):
    """전략 최적화 에이전트"""

    def __init__(self, message_bus, state_manager, llm_client, strategy_modifier):
        """
        Args:
            message_bus: MessageBus 인스턴스
            state_manager: StateManager 인스턴스
            llm_client: LLMClient 인스턴스
            strategy_modifier: StrategyModifier 인스턴스
        """
        interval = AGENT_TEAM_CONFIG.get("strategist_interval", 300)
        super().__init__("strategist", message_bus, state_manager, llm_client, interval)

        self._strategy_modifier = strategy_modifier
        self._symbol = AGENT_TEAM_CONFIG.get("symbol", "BTC-USDT-SWAP")
        self._param_limits = AGENT_TEAM_CONFIG.get("param_limits", {})
        self._target_profit = AGENT_TEAM_CONFIG.get("target_profit", 1000.0)

        # 성과 추적
        self._recent_trades: List[Dict] = []
        self._last_optimization: Optional[datetime] = None
        self._optimization_cooldown = 600  # 최소 10분 간격

        # 메시지 구독
        self.message_bus.subscribe("strategist", [
            MSG_TRADE_RESULT, MSG_APPROVAL, MSG_REJECTION,
            MSG_STATUS, MSG_EMERGENCY_STOP,
        ])

    def run_cycle(self) -> None:
        """Strategist 사이클: 성과 분석 → 최적화 제안"""
        # 1. 수신 메시지 처리
        messages = self.get_messages(timeout=0.5)
        for msg in messages:
            self._handle_message(msg)

        # 2. 성과 데이터 수집
        performance = self._collect_performance_data()

        # 3. 시장 데이터 수집
        market_data = self._collect_market_data()

        # 4. 최적화 필요 여부 판단
        if self._should_optimize(performance):
            self._run_optimization(performance, market_data)

        # 5. 목표 달성 확인
        cumulative = self.state_manager.get_cumulative_profit()
        if cumulative >= self._target_profit:
            self.log(f"🎯 목표 수익 달성! ${cumulative:,.2f} >= ${self._target_profit:,.2f}")

    # ==================== 메시지 처리 ====================

    def _handle_message(self, msg: Dict) -> None:
        """수신 메시지 처리"""
        msg_type = msg.get("type")

        if msg_type == MSG_TRADE_RESULT:
            data = msg.get("data", {})
            self._recent_trades.append(data)
            # 최근 50개만 유지
            if len(self._recent_trades) > 50:
                self._recent_trades = self._recent_trades[-50:]

        elif msg_type == MSG_STATUS:
            data = msg.get("data", {})
            if data.get("event") == "entry_blocked":
                self.log("⚠️ 진입 차단 통보 — 즉시 전략 재검토 수행")
                performance = self._collect_performance_data()
                market_data = self._collect_market_data()
                self._run_optimization(performance, market_data)

    # ==================== 성과 데이터 수집 ====================

    def _collect_performance_data(self) -> Dict[str, Any]:
        """성과 데이터 수집"""
        status = self.state_manager.get_team_status()
        trades = self.state_manager.get_trade_history(limit=20)
        params = self.state_manager.get_strategy_params()

        # 승률 계산
        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0

        # 평균 PnL
        pnl_list = [t.get("pnl", 0) for t in trades]
        avg_pnl = sum(pnl_list) / len(pnl_list) if pnl_list else 0.0

        return {
            "current_equity": status.get("current_equity", 0),
            "initial_capital": status.get("initial_capital", 0),
            "cumulative_profit": status.get("cumulative_profit", 0),
            "current_pnl": status.get("current_pnl", 0),
            "drawdown_pct": status.get("drawdown_pct", 0),
            "total_trades": total_trades,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "recent_trades_count": len(self._recent_trades),
            "current_params": params,
            "target_profit": self._target_profit,
        }

    def _collect_market_data(self) -> Dict[str, Any]:
        """시장 데이터 수집"""
        data = {
            "symbol": self._symbol,
            "current_price": self.state_manager.get_current_price(),
            "timestamp": datetime.now().isoformat(),
        }

        # 변동성 측정 (최근 24시간)
        try:
            result = make_api_request(
                "GET", "/api/v5/market/candles",
                params={
                    "instId": self._symbol,
                    "bar": "1H",
                    "limit": "24",
                }
            )
            if result and result.get("code") == "0":
                candles = result.get("data", [])
                if candles:
                    closes = [float(c[4]) for c in candles]
                    highs = [float(c[2]) for c in candles]
                    lows = [float(c[3]) for c in candles]

                    # 변동성 지표
                    price_range = max(highs) - min(lows)
                    avg_price = sum(closes) / len(closes)
                    volatility = price_range / avg_price if avg_price > 0 else 0

                    data["volatility_24h"] = volatility
                    data["high_24h"] = max(highs)
                    data["low_24h"] = min(lows)
                    data["avg_price_24h"] = avg_price
        except Exception as e:
            log_error(f"[Strategist] 시장 데이터 수집 실패: {e}")

        return data

    # ==================== 최적화 판단 ====================

    def _should_optimize(self, performance: Dict) -> bool:
        """최적화 수행 여부 판단"""
        # 쿨다운 확인
        if self._last_optimization:
            elapsed = (datetime.now() - self._last_optimization).total_seconds()
            if elapsed < self._optimization_cooldown:
                return False

        # 거래 횟수 최소 3회 이상
        if performance.get("total_trades", 0) < 3:
            return False

        # 조건 1: 승률 40% 미만
        if performance.get("win_rate", 1.0) < 0.40:
            return True

        # 조건 2: Drawdown 5% 이상
        if performance.get("drawdown_pct", 0) >= 0.05:
            return True

        # 조건 3: 누적 손실
        if performance.get("current_pnl", 0) < 0:
            return True

        return False

    # ==================== 최적화 실행 ====================

    def _run_optimization(self, performance: Dict, market_data: Dict) -> None:
        """Claude API로 최적화 수행"""
        self._last_optimization = datetime.now()

        if not self.llm_client or not self.llm_client.is_available:
            self.log("⚠️ LLM 미사용 — 기본 규칙 기반 최적화")
            self._apply_rule_based_optimization(performance, market_data)
            return

        self.log("🧠 Claude API 전략 최적화 분석 시작...")

        result = self.llm_client.optimize_strategy(performance, market_data)
        param_changes = result.get("param_changes", {})
        reasoning = result.get("reasoning", "")

        if not param_changes:
            self.log(f"📊 변경 불필요: {reasoning}")
            return

        self.log(f"📊 최적화 제안: {param_changes} — {reasoning}")

        # Monitor에 파라미터 변경 승인 요청
        import uuid
        request_id = str(uuid.uuid4())[:8]
        self.send_message(MSG_PARAM_CHANGE, {
            "request_id": request_id,
            "param_changes": param_changes,
            "reasoning": reasoning,
            "performance_data": performance,
        }, to="monitor", requires_approval=True)

    def _apply_rule_based_optimization(self, performance: Dict,
                                        market_data: Dict) -> None:
        """규칙 기반 기본 최적화 (LLM 미사용시)"""
        import uuid
        params = performance.get("current_params", {})
        changes = {}

        drawdown = performance.get("drawdown_pct", 0)
        win_rate = performance.get("win_rate", 0.5)

        # Drawdown 높으면 보수적으로
        if drawdown >= 0.07:
            current_leverage = params.get("leverage", 10)
            new_leverage = max(1, current_leverage - 2)
            if new_leverage != current_leverage:
                changes["leverage"] = new_leverage

            current_ratio = params.get("capital_use_ratio", 0.50)
            new_ratio = max(0.20, current_ratio - 0.10)
            if new_ratio != current_ratio:
                changes["capital_use_ratio"] = round(new_ratio, 2)

        # 승률 낮으면 트레일링 스탑 조정
        if win_rate < 0.35:
            current_ts = params.get("trailing_stop", 0.10)
            new_ts = min(0.15, current_ts + 0.02)
            if new_ts != current_ts:
                changes["trailing_stop"] = round(new_ts, 2)

        if changes:
            self.log(f"📊 규칙 기반 최적화 제안: {changes}")
            request_id = str(uuid.uuid4())[:8]
            self.send_message(MSG_PARAM_CHANGE, {
                "request_id": request_id,
                "param_changes": changes,
                "reasoning": f"규칙 기반 (drawdown={drawdown:.1%}, win_rate={win_rate:.1%})",
                "performance_data": performance,
            }, to="monitor", requires_approval=True)
        else:
            self.log("📊 규칙 기반 검토 완료 — 변경 불필요")
