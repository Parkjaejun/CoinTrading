# agents/monitor_agent.py
"""
Agent 4: Monitor (리스크 관리 & 승인)

역할:
- 포트폴리오 상태 실시간 감시 (30초 주기)
- 거래 요청 승인/거부
- 파라미터 변경 범위 검증
- 코드 변경 Claude API 리뷰
- 긴급 정지 조건 감시 (Drawdown 기반)
"""

from datetime import datetime
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent
from agents.message_bus import (
    MSG_TRADE_REQUEST, MSG_TRADE_RESULT, MSG_PARAM_CHANGE,
    MSG_CODE_CHANGE, MSG_APPROVAL, MSG_REJECTION, MSG_EMERGENCY_STOP,
    MSG_SIGNAL, MSG_STATUS,
)
from agents.agent_config import AGENT_TEAM_CONFIG
from utils.logger import log_system, log_error


class MonitorAgent(BaseAgent):
    """리스크 관리 & 승인 에이전트"""

    def __init__(self, message_bus, state_manager, llm_client,
                 strategy_modifier, order_manager=None):
        """
        Args:
            message_bus: MessageBus 인스턴스
            state_manager: StateManager 인스턴스
            llm_client: LLMClient 인스턴스
            strategy_modifier: StrategyModifier 인스턴스
            order_manager: OrderManager 인스턴스 (긴급 청산용)
        """
        interval = AGENT_TEAM_CONFIG.get("monitor_interval", 30)
        super().__init__("monitor", message_bus, state_manager, llm_client, interval)

        self._strategy_modifier = strategy_modifier
        self._order_manager = order_manager
        self._param_limits = AGENT_TEAM_CONFIG.get("param_limits", {})
        self._max_drawdown = AGENT_TEAM_CONFIG.get("max_drawdown_pct", 0.10)
        self._emergency_drawdown = AGENT_TEAM_CONFIG.get("emergency_stop_loss_pct", 0.15)
        self._fee_tolerance = AGENT_TEAM_CONFIG.get("fee_tolerance_pct", 0.02)
        self._min_confidence = AGENT_TEAM_CONFIG.get("min_signal_confidence", 0.7)
        self._max_position_pct = AGENT_TEAM_CONFIG.get("max_position_pct", 0.30)
        self._dry_run = AGENT_TEAM_CONFIG.get("dry_run", False)

        # Monitor는 긴급 정지 중에도 실행 (복구 판단 위해)
        self._skip_emergency_check = True

        # 메시지 구독
        self.message_bus.subscribe("monitor", [
            MSG_TRADE_REQUEST, MSG_PARAM_CHANGE, MSG_CODE_CHANGE,
            MSG_TRADE_RESULT, MSG_STATUS,
        ])

    def run_cycle(self) -> None:
        """Monitor 사이클 실행"""
        # 1. 상태 갱신
        self.state_manager.refresh_balance()
        self.state_manager.refresh_positions()

        # 2. Drawdown 모니터링
        self._check_drawdown()

        # 3. 수신 메시지 처리 (승인 요청 등)
        messages = self.get_messages(timeout=0.5)
        for msg in messages:
            self._handle_message(msg)

        # 4. 보류 중인 코드 변경 처리
        self._process_pending_code_changes()

    # ==================== Drawdown 감시 ====================

    def _check_drawdown(self) -> None:
        """Drawdown 기반 안전장치

        소액 계좌($70)에서는 수수료와 소폭 변동으로 원금 이하가 흔히 발생하므로,
        절대금액 기준이 아닌 고점 대비 Drawdown 비율로만 판단한다.

        - 5% Drawdown: 경고 로그 (정보성)
        - 10% Drawdown: 신규 진입 차단 + Strategist에 재검토 요청
        - 15% Drawdown: 전 포지션 청산 + 긴급 정지
        """
        drawdown = self.state_manager.get_drawdown_pct()
        equity = self.state_manager.get_current_equity()
        initial = self.state_manager.get_initial_capital()

        # === 긴급 정지 자동 복구 ===
        # Drawdown이 max_drawdown(10%) 아래로 회복되면 긴급 정지 해제
        if self.state_manager.is_emergency_stopped():
            if drawdown < self._max_drawdown:
                self.log(
                    f"✅ Drawdown 회복: {drawdown:.1%} < {self._max_drawdown:.0%} "
                    f"— 긴급 정지 해제 (자산: ${equity:.2f})"
                )
                self.state_manager.clear_emergency_stop()
                self.state_manager.set_entry_blocked(False)
            else:
                pnl = equity - initial
                self.log(f"🚨 긴급 정지 유지: Drawdown {drawdown:.1%}, 자산 ${equity:.2f} (PnL: ${pnl:+.2f})")
            return

        # === 15% Drawdown: 긴급 정지 + 전 포지션 청산 ===
        if drawdown >= self._emergency_drawdown:
            self.state_manager.set_emergency_stop(
                f"Drawdown {drawdown:.1%} >= {self._emergency_drawdown:.0%} 긴급 정지"
            )
            self._emergency_close_all(f"Drawdown {drawdown:.1%}")
            self._broadcast_emergency(f"Drawdown {drawdown:.1%} → 긴급 정지 + 전 포지션 청산")
            return

        # === 10% Drawdown: 신규 진입 차단 ===
        if drawdown >= self._max_drawdown:
            if not self.state_manager.is_entry_blocked():
                self.state_manager.set_entry_blocked(
                    True, f"Drawdown {drawdown:.1%} >= {self._max_drawdown:.0%}"
                )
                self.log(f"⚠️ 신규 진입 차단: Drawdown {drawdown:.1%}")
                self.send_message(MSG_STATUS, {
                    "event": "entry_blocked",
                    "drawdown": drawdown,
                    "reason": "Drawdown 한도 초과 — 전략 재검토 필요",
                }, to="strategist")
        else:
            # Drawdown 회복 시 차단 해제
            if self.state_manager.is_entry_blocked():
                self.state_manager.set_entry_blocked(False)
                self.log("✅ Drawdown 회복 — 신규 진입 허용")

            # 5% Drawdown: 경고 (정보성)
            if drawdown >= 0.05:
                self.log(f"⚠️ Drawdown 경고: {drawdown:.1%} (자산: ${equity:.2f})")

    def _emergency_close_all(self, reason: str) -> None:
        """긴급 전 포지션 청산"""
        if self._dry_run:
            self.log(f"🏷️ [DRY-RUN] 긴급 청산 시뮬레이션: {reason}")
            return

        if not self._order_manager:
            self.log("⚠️ OrderManager 없음 — 수동 청산 필요")
            return

        try:
            self.log(f"🚨 긴급 전 포지션 청산: {reason}")
            self._order_manager.close_all_positions()
        except Exception as e:
            log_error(f"[Monitor] 긴급 청산 실패: {e}")

    def _broadcast_emergency(self, reason: str) -> None:
        """긴급 정지 브로드캐스트"""
        self.send_message(MSG_EMERGENCY_STOP, {
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })

    # ==================== 메시지 처리 ====================

    def _handle_message(self, msg: Dict) -> None:
        """수신 메시지 라우팅"""
        msg_type = msg.get("type")

        if msg_type == MSG_TRADE_REQUEST:
            self._handle_trade_request(msg)
        elif msg_type == MSG_PARAM_CHANGE:
            self._handle_param_change(msg)
        elif msg_type == MSG_CODE_CHANGE:
            self._handle_code_change(msg)

    # ==================== 거래 승인 ====================

    def _handle_trade_request(self, msg: Dict) -> None:
        """거래 요청 승인/거부"""
        data = msg.get("data", {})
        request_id = data.get("request_id", "unknown")

        action = data.get("action", "")
        is_close = action in ("SELL", "COVER")  # 포지션 청산
        is_entry = action in ("BUY", "SHORT")   # 신규 진입

        # 청산(SELL/COVER)은 긴급 정지 중에도 허용 (포지션 정리 우선)
        if self.state_manager.is_emergency_stopped() and not is_close:
            self._reject(msg, request_id, "긴급 정지 상태")
            return

        # 신규 진입 차단 중이면 BUY/SHORT 모두 거부
        if is_entry and self.state_manager.is_entry_blocked():
            self._reject(msg, request_id, "신규 진입 차단 중 (Drawdown 한도)")
            return

        # 기본 검증 (청산은 신뢰도 검증 생략)
        if not is_close:
            confidence = data.get("confidence", 0.0)
            if confidence < self._min_confidence:
                self._reject(msg, request_id, f"신뢰도 부족: {confidence:.2f} < {self._min_confidence}")
                return

        # 포지션 비율 검증 (신규 진입만 — 청산은 무조건 허용)
        if not is_close:
            equity = self.state_manager.get_current_equity()
            trade_amount = data.get("trade_amount_usdt", 0)
            if equity > 0 and trade_amount / equity > self._max_position_pct:
                self._reject(
                    msg, request_id,
                    f"포지션 비율 초과: {trade_amount/equity:.1%} > {self._max_position_pct:.0%}"
                )
                return

        # LLM 판단 (신규 진입만 — 청산은 즉시 승인)
        if not is_close and self.llm_client and self.llm_client.is_available:
            portfolio_state = self.state_manager.get_team_status()
            result = self.llm_client.evaluate_trade_request(data, portfolio_state)
            if not result.get("approved", False):
                self._reject(msg, request_id, f"LLM 거부: {result.get('reasoning', 'N/A')}")
                return

        # 승인
        reason = "청산 승인" if is_close else "모든 검증 통과"
        self._approve(msg, request_id, reason)

    def _approve(self, original_msg: Dict, request_id: str, reason: str) -> None:
        """거래 승인 응답"""
        self.log(f"✅ 거래 승인: {request_id} — {reason}")
        self.send_message(MSG_APPROVAL, {
            "request_id": request_id,
            "original_type": original_msg.get("type"),
            "reason": reason,
        }, to=original_msg.get("from", "trader"))

    def _reject(self, original_msg: Dict, request_id: str, reason: str) -> None:
        """거래 거부 응답"""
        self.log(f"❌ 거래 거부: {request_id} — {reason}")
        self.send_message(MSG_REJECTION, {
            "request_id": request_id,
            "original_type": original_msg.get("type"),
            "reason": reason,
        }, to=original_msg.get("from", "trader"))

    # ==================== 파라미터 변경 검증 ====================

    def _handle_param_change(self, msg: Dict) -> None:
        """파라미터 변경 요청 검증"""
        data = msg.get("data", {})
        request_id = data.get("request_id", "unknown")
        param_changes = data.get("param_changes", {})

        # 범위 검증
        for key, value in param_changes.items():
            if key in self._param_limits:
                limits = self._param_limits[key]
                if not (limits["min"] <= value <= limits["max"]):
                    self._reject(
                        msg, request_id,
                        f"파라미터 범위 초과: {key}={value} (허용: {limits['min']}~{limits['max']})"
                    )
                    return

        # 승인
        self._approve(msg, request_id, f"파라미터 변경 승인: {param_changes}")

    # ==================== 코드 변경 리뷰 ====================

    def _handle_code_change(self, msg: Dict) -> None:
        """코드 변경 요청 리뷰"""
        data = msg.get("data", {})
        change_id = data.get("change_id", "unknown")

        # 보류 중인 변경 확인
        pending = self._strategy_modifier.list_pending_changes()
        target = None
        for change in pending:
            if change["change_id"] == change_id:
                target = change
                break

        if not target:
            self._reject(msg, change_id, "변경 ID를 찾을 수 없음")
            return

        # LLM 코드 리뷰
        if self.llm_client and self.llm_client.is_available:
            review = self.llm_client.review_code_change(
                target["original_code"],
                target["new_code"],
                target["reason"],
            )

            if not review.get("approved", False):
                self.log(f"❌ 코드 변경 거부: {change_id} — {review.get('feedback', 'N/A')}")
                self._strategy_modifier.rollback_code_change(change_id)
                self._reject(msg, change_id, f"코드 리뷰 거부: {review.get('feedback', '')}")
                return
        else:
            # LLM 미사용 시 보수적으로 거부
            self.log(f"❌ 코드 변경 거부: {change_id} — LLM 리뷰 불가")
            self._strategy_modifier.rollback_code_change(change_id)
            self._reject(msg, change_id, "LLM 리뷰 불가 — 코드 변경 거부")
            return

        # 승인 및 적용
        if self._strategy_modifier.apply_code_change(change_id):
            self._approve(msg, change_id, "코드 리뷰 통과 — 적용 완료")
        else:
            self._reject(msg, change_id, "코드 적용 실패")

    def _process_pending_code_changes(self) -> None:
        """외부에서 직접 제출된 보류 코드 변경 처리"""
        # 메시지 버스를 통하지 않은 변경은 여기서 처리하지 않음
        # (모든 코드 변경은 메시지 버스 통해 제출되어야 함)
        pass
