# agents/message_bus.py
"""
에이전트 간 통신 메시지 버스

Queue 기반 thread-safe 구독/발행 패턴.
각 에이전트는 관심 있는 메시지 타입을 구독하고,
해당 타입의 메시지만 수신한다.
"""

import queue
import threading
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

from utils.logger import log_system


# 메시지 타입 상수
MSG_SIGNAL = "SIGNAL"                   # Reader → 매매 신호
MSG_TRADE_REQUEST = "TRADE_REQUEST"     # Trader → Monitor 거래 승인 요청
MSG_TRADE_RESULT = "TRADE_RESULT"       # Trader → 거래 결과
MSG_PARAM_CHANGE = "PARAM_CHANGE"       # Strategist → 파라미터 변경 요청
MSG_CODE_CHANGE = "CODE_CHANGE"         # Strategist → 코드 변경 요청
MSG_APPROVAL = "APPROVAL"              # Monitor → 승인
MSG_REJECTION = "REJECTION"            # Monitor → 거부
MSG_EMERGENCY_STOP = "EMERGENCY_STOP"  # Monitor → 긴급 정지
MSG_STATUS = "STATUS"                  # 상태 보고


class MessageBus:
    """Thread-safe 메시지 버스"""

    def __init__(self, max_history: int = 500):
        """
        Args:
            max_history: 메시지 히스토리 최대 보관 수
        """
        self._lock = threading.Lock()
        # 에이전트별 메시지 큐
        self._queues: Dict[str, queue.Queue] = {}
        # 에이전트별 구독 메시지 타입
        self._subscriptions: Dict[str, List[str]] = {}
        # 전체 메시지 히스토리
        self._history: deque = deque(maxlen=max_history)
        self._message_count = 0

    def subscribe(self, agent_name: str, message_types: List[str]) -> None:
        """
        메시지 타입 구독 등록

        Args:
            agent_name: 에이전트 이름
            message_types: 구독할 메시지 타입 목록
        """
        with self._lock:
            self._subscriptions[agent_name] = message_types
            if agent_name not in self._queues:
                self._queues[agent_name] = queue.Queue()
        log_system(f"[MessageBus] {agent_name} 구독: {message_types}")

    def publish(self, message: dict) -> None:
        """
        메시지 발행 — 구독자에게 전달

        Args:
            message: 메시지 딕셔너리 (type, from, to, data, ...)
        """
        with self._lock:
            self._message_count += 1
            message["_seq"] = self._message_count
            self._history.append(message)

            msg_type = message.get("type", "")
            msg_to = message.get("to", "all")
            msg_from = message.get("from", "unknown")

            for agent_name, subscribed_types in self._subscriptions.items():
                # 자기 자신에게는 전달하지 않음
                if agent_name == msg_from:
                    continue
                # 수신 대상 필터
                if msg_to != "all" and msg_to != agent_name:
                    continue
                # 구독 타입 필터
                if msg_type in subscribed_types:
                    self._queues[agent_name].put(message)

    def get_messages(self, agent_name: str, timeout: float = 0.1) -> List[dict]:
        """
        에이전트의 수신 메시지 모두 가져오기

        Args:
            agent_name: 에이전트 이름
            timeout: 최초 대기 시간 (초)

        Returns:
            수신된 메시지 리스트
        """
        messages = []
        q = self._queues.get(agent_name)
        if q is None:
            return messages

        # 첫 메시지는 timeout 대기
        try:
            msg = q.get(timeout=timeout)
            messages.append(msg)
        except queue.Empty:
            return messages

        # 나머지는 즉시 가져오기
        while not q.empty():
            try:
                messages.append(q.get_nowait())
            except queue.Empty:
                break

        return messages

    def broadcast(self, message: dict) -> None:
        """모든 에이전트에게 메시지 발송"""
        message["to"] = "all"
        self.publish(message)

    def get_history(self, limit: int = 50, msg_type: Optional[str] = None) -> List[dict]:
        """
        메시지 히스토리 조회

        Args:
            limit: 최대 반환 개수
            msg_type: 필터할 메시지 타입 (None이면 전체)

        Returns:
            메시지 히스토리 리스트 (최신순)
        """
        with self._lock:
            history = list(self._history)
            if msg_type:
                history = [m for m in history if m.get("type") == msg_type]
            return history[-limit:]

    def get_stats(self) -> dict:
        """메시지 버스 통계"""
        with self._lock:
            return {
                "total_messages": self._message_count,
                "subscribers": list(self._subscriptions.keys()),
                "history_size": len(self._history),
                "queue_sizes": {
                    name: q.qsize() for name, q in self._queues.items()
                },
            }
