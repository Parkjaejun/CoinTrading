# agents/trader_agent.py
"""
Agent 2: Trader (자율 매매 집행)

역할:
- Reader 신호 수신
- Monitor에 거래 승인 요청
- 승인 시 OrderManager로 주문 실행
- 거래 결과를 Message Bus에 발행
"""

import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent
from agents.message_bus import (
    MSG_SIGNAL, MSG_TRADE_REQUEST, MSG_TRADE_RESULT,
    MSG_APPROVAL, MSG_REJECTION, MSG_EMERGENCY_STOP,
)
from agents.agent_config import AGENT_TEAM_CONFIG
from utils.logger import log_system, log_error


class TraderAgent(BaseAgent):
    """자율 매매 집행 에이전트"""

    def __init__(self, message_bus, state_manager, llm_client, order_manager):
        """
        Args:
            message_bus: MessageBus 인스턴스
            state_manager: StateManager 인스턴스
            llm_client: LLMClient 인스턴스
            order_manager: OrderManager 인스턴스
        """
        interval = AGENT_TEAM_CONFIG.get("trader_interval", 5)
        super().__init__("trader", message_bus, state_manager, llm_client, interval)

        self._order_manager = order_manager
        self._symbol = AGENT_TEAM_CONFIG.get("symbol", "BTC-USDT-SWAP")
        self._leverage = AGENT_TEAM_CONFIG.get("leverage", 10)
        self._dry_run = AGENT_TEAM_CONFIG.get("dry_run", False)

        # 승인 대기 중인 요청
        self._pending_requests: Dict[str, Dict] = {}
        # 승인 대기 타임아웃 (초)
        self._approval_timeout = 60

        # 메시지 구독
        self.message_bus.subscribe("trader", [
            MSG_SIGNAL, MSG_APPROVAL, MSG_REJECTION, MSG_EMERGENCY_STOP,
        ])

    def run_cycle(self) -> None:
        """Trader 사이클: 신호 수신 → 승인 요청 → 주문 실행"""
        messages = self.get_messages(timeout=1.0)

        for msg in messages:
            msg_type = msg.get("type")

            if msg_type == MSG_SIGNAL:
                self._handle_signal(msg)
            elif msg_type == MSG_APPROVAL:
                self._handle_approval(msg)
            elif msg_type == MSG_REJECTION:
                self._handle_rejection(msg)
            elif msg_type == MSG_EMERGENCY_STOP:
                self.log("🚨 긴급 정지 수신 — 모든 대기 요청 취소")
                self._pending_requests.clear()

        # 타임아웃된 요청 정리
        self._cleanup_expired_requests()

    # ==================== 신호 처리 ====================

    def _handle_signal(self, msg: Dict) -> None:
        """Reader 신호 수신 및 거래 요청 생성"""
        data = msg.get("data", {})
        signal = data.get("signal", "HOLD")
        confidence = data.get("confidence", 0.0)
        price = data.get("price", 0.0)

        if signal == "HOLD":
            return

        self.log(f"📨 신호 수신: {signal} (신뢰도: {confidence:.2f}, 가격: ${price:,.0f})")

        # 현재 포지션 확인
        positions = self.state_manager.get_positions()
        pos_dir = self.state_manager.get_position_direction()
        has_position = len(positions) > 0

        # 신호와 포지션 상태 검증
        if signal == "BUY" and has_position:
            self.log(f"이미 {pos_dir} 포지션 보유 중 — BUY 신호 무시")
            return
        if signal == "SHORT" and has_position:
            self.log(f"이미 {pos_dir} 포지션 보유 중 — SHORT 신호 무시")
            return
        if signal == "SELL" and pos_dir != "long":
            self.log("롱 포지션 없음 — SELL 신호 무시")
            return
        if signal == "COVER" and pos_dir != "short":
            self.log("숏 포지션 없음 — COVER 신호 무시")
            return

        # 매매 수량 계산
        trade_info = self._calculate_trade(signal, price, positions)
        if not trade_info:
            return

        # Monitor에 승인 요청
        request_id = str(uuid.uuid4())[:8]
        trade_request = {
            "request_id": request_id,
            "action": signal,
            "symbol": self._symbol,
            "price": price,
            "confidence": confidence,
            "reasoning": data.get("reasoning", ""),
            **trade_info,
        }

        self._pending_requests[request_id] = {
            "request": trade_request,
            "created_at": datetime.now(),
        }

        self.log(f"📤 거래 승인 요청: {request_id} ({signal} {trade_info.get('size', 0)} 계약)")
        self.send_message(
            MSG_TRADE_REQUEST, trade_request,
            to="monitor", requires_approval=True,
        )

    # ==================== 승인/거부 처리 ====================

    def _handle_approval(self, msg: Dict) -> None:
        """Monitor 승인 처리 → 주문 실행"""
        data = msg.get("data", {})
        request_id = data.get("request_id")

        pending = self._pending_requests.pop(request_id, None)
        if not pending:
            self.log(f"⚠️ 만료된 승인: {request_id}")
            return

        request = pending["request"]
        action = request["action"]
        self.log(f"✅ 승인 수신: {request_id} — 주문 실행 시작")

        # 주문 실행
        result = self._execute_trade(request)

        # 거래 결과 발행
        self.send_message(MSG_TRADE_RESULT, {
            "request_id": request_id,
            "action": action,
            "success": result is not None,
            "order_result": result,
            "timestamp": datetime.now().isoformat(),
        })

    def _handle_rejection(self, msg: Dict) -> None:
        """Monitor 거부 처리"""
        data = msg.get("data", {})
        request_id = data.get("request_id")
        reason = data.get("reason", "N/A")

        self._pending_requests.pop(request_id, None)
        self.log(f"❌ 거래 거부: {request_id} — {reason}")

    # ==================== 주문 실행 ====================

    def _calculate_trade(self, signal: str, price: float,
                         positions: list) -> Optional[Dict]:
        """매매 수량 및 방향 계산"""
        params = self.state_manager.get_strategy_params()
        capital_use = params.get("capital_use_ratio", 0.50)
        leverage = params.get("leverage", self._leverage)

        # 신규 진입 (BUY / SHORT)
        if signal in ("BUY", "SHORT"):
            equity = self.state_manager.get_current_equity()
            if equity <= 0:
                self.log("⚠️ 잔고 없음")
                return None

            trade_amount = equity * capital_use
            contract_value = 0.01 * price  # BTC-USDT-SWAP: 1계약 = 0.01 BTC
            size = int((trade_amount * leverage) / contract_value)

            if size < 1:
                self.log(f"⚠️ 주문 수량 부족: ${trade_amount:.2f} → {size} 계약")
                return None

            side = "buy" if signal == "BUY" else "sell"
            return {
                "side": side,
                "size": size,
                "leverage": leverage,
                "trade_amount_usdt": trade_amount,
            }

        # 포지션 청산 (SELL / COVER)
        elif signal in ("SELL", "COVER"):
            if not positions:
                return None
            pos = positions[0]
            # SELL(롱 청산) → sell, COVER(숏 청산) → buy
            side = "sell" if signal == "SELL" else "buy"
            return {
                "side": side,
                "size": abs(pos["position"]),
                "leverage": leverage,
                "trade_amount_usdt": abs(pos.get("notional_usd", 0)),
                "close_position": True,
            }

        return None

    def _execute_trade(self, request: Dict) -> Optional[Dict]:
        """실제 주문 실행"""
        action = request["action"]
        side = request.get("side", "buy")
        size = request.get("size", 0)
        leverage = request.get("leverage", self._leverage)

        if self._dry_run:
            self.log(f"🏷️ [DRY-RUN] 주문 시뮬레이션: {action} {side} {size}계약")
            result = {
                "order_id": f"dry_{uuid.uuid4().hex[:8]}",
                "side": side,
                "size": size,
                "status": "simulated",
                "dry_run": True,
            }
            # PnL 기록 (시뮬레이션)
            if request.get("close_position"):
                self.state_manager.record_trade({
                    "action": action,
                    "side": side,
                    "size": size,
                    "pnl": 0.0,
                    "dry_run": True,
                    "timestamp": datetime.now().isoformat(),
                })
            return result

        if not self._order_manager:
            self.log("⚠️ OrderManager 없음 — 주문 실행 불가")
            return None

        try:
            if request.get("close_position"):
                # 포지션 청산 (SELL 또는 COVER)
                action_label = "롱 청산" if action == "SELL" else "숏 청산"
                self.log(f"📤 {action_label} 실행: {self._symbol}")
                result = self._order_manager.close_position(self._symbol)
            else:
                # 신규 진입 (BUY 또는 SHORT)
                action_label = "롱 진입" if action == "BUY" else "숏 진입"
                self.log(f"🚀 {action_label}: {side.upper()} {size}계약 (레버리지: {leverage}x)")
                result = self._order_manager.place_market_order(
                    inst_id=self._symbol,
                    side=side,
                    size=size,
                    leverage=leverage,
                )

            if result:
                self.log(f"✅ 주문 성공: {result.get('order_id', 'N/A')}")
                # 거래 기록
                self.state_manager.record_trade({
                    "action": action,
                    "side": side,
                    "size": size,
                    "order_id": result.get("order_id"),
                    "timestamp": datetime.now().isoformat(),
                })
            else:
                self.log("❌ 주문 실패: 응답 없음")

            return result

        except Exception as e:
            log_error(f"[Trader] 주문 실행 오류: {e}")
            return None

    # ==================== 타임아웃 관리 ====================

    def _cleanup_expired_requests(self) -> None:
        """만료된 승인 대기 요청 정리"""
        now = datetime.now()
        expired = []
        for req_id, info in self._pending_requests.items():
            elapsed = (now - info["created_at"]).total_seconds()
            if elapsed > self._approval_timeout:
                expired.append(req_id)

        for req_id in expired:
            self._pending_requests.pop(req_id, None)
            self.log(f"⏰ 승인 타임아웃: {req_id}")
