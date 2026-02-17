# agents/base_agent.py
"""
BaseAgent 추상 클래스

모든 에이전트의 공통 인터페이스 및 라이프사이클 관리.
스레드 기반으로 run_cycle()을 주기적으로 실행한다.
"""

import threading
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from utils.logger import log_system, log_error, log_info


class BaseAgent(ABC):
    """에이전트 기본 클래스"""

    def __init__(self, name: str, message_bus, state_manager, llm_client,
                 interval: float = 60.0):
        """
        Args:
            name: 에이전트 이름 (reader, trader, strategist, monitor)
            message_bus: MessageBus 인스턴스
            state_manager: StateManager 인스턴스
            llm_client: LLMClient 인스턴스
            interval: 실행 주기 (초)
        """
        self.name = name
        self.message_bus = message_bus
        self.state_manager = state_manager
        self.llm_client = llm_client
        self.interval = interval

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._cycle_count = 0
        self._last_error: Optional[str] = None
        self._started_at: Optional[datetime] = None
        self._skip_emergency_check = False  # Monitor는 True로 설정
        self._last_emergency_log = 0  # 긴급 정지 로그 스팸 방지

    # ==================== 라이프사이클 ====================

    def start(self) -> None:
        """에이전트 스레드 시작"""
        if self._running:
            self.log("이미 실행 중")
            return

        self._running = True
        self._started_at = datetime.now()
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"agent-{self.name}",
            daemon=True,
        )
        self._thread.start()
        self.log(f"🚀 에이전트 시작 (주기: {self.interval}초)")

    def stop(self) -> None:
        """에이전트 안전 정지"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self.log("🛑 에이전트 정지")

    @property
    def is_running(self) -> bool:
        return self._running

    # ==================== 실행 루프 ====================

    def _run_loop(self) -> None:
        """메인 실행 루프"""
        self.log("실행 루프 시작")
        while self._running:
            try:
                # 긴급 정지 확인 (Monitor는 복구 판단을 위해 계속 실행)
                if (self.state_manager.is_emergency_stopped()
                        and not self._skip_emergency_check):
                    # 60초마다만 로그 출력 (스팸 방지)
                    now = time.time()
                    if now - self._last_emergency_log >= 60:
                        self.log("⚠️ 긴급 정지 상태 — 사이클 건너뜀")
                        self._last_emergency_log = now
                    time.sleep(self.interval)
                    continue

                self._cycle_count += 1
                self.run_cycle()
                self._last_error = None

            except Exception as e:
                self._last_error = str(e)
                self.log(f"사이클 오류: {e}", level="error")
                log_error(f"[{self.name}] {traceback.format_exc()}")

            time.sleep(self.interval)

    @abstractmethod
    def run_cycle(self) -> None:
        """한 사이클 실행 (서브클래스에서 구현)"""
        ...

    # ==================== 메시지 ====================

    def send_message(self, msg_type: str, data: dict,
                     to: str = "all", requires_approval: bool = False) -> None:
        """메시지 버스로 메시지 발송"""
        message = {
            "type": msg_type,
            "from": self.name,
            "to": to,
            "timestamp": datetime.now(),
            "data": data,
            "requires_approval": requires_approval,
        }
        self.message_bus.publish(message)

    def get_messages(self, timeout: float = 0.1) -> list:
        """수신 메시지 가져오기"""
        return self.message_bus.get_messages(self.name, timeout=timeout)

    # ==================== 로깅 ====================

    def log(self, message: str, level: str = "info") -> None:
        """에이전트 로그 출력"""
        prefix = f"[{self.name.upper()}]"
        if level == "error":
            log_error(f"{prefix} {message}")
        else:
            log_system(f"{prefix} {message}")

    # ==================== 상태 ====================

    def get_status(self) -> dict:
        """에이전트 상태 반환"""
        return {
            "name": self.name,
            "running": self._running,
            "cycle_count": self._cycle_count,
            "interval": self.interval,
            "last_error": self._last_error,
            "started_at": self._started_at.isoformat() if self._started_at else None,
        }
