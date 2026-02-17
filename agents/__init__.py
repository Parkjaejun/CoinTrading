# agents/__init__.py
"""
자율 매매 에이전트 팀 패키지

4개 에이전트로 구성된 자율 매매 시스템:
- ReaderAgent: 시세 & 뉴스 분석
- TraderAgent: 자율 매매 집행
- StrategistAgent: 전략 최적화
- MonitorAgent: 리스크 관리 & 승인
"""

from agents.base_agent import BaseAgent
from agents.message_bus import MessageBus
from agents.state_manager import StateManager
from agents.agent_config import AGENT_TEAM_CONFIG

__all__ = [
    'BaseAgent',
    'MessageBus',
    'StateManager',
    'AGENT_TEAM_CONFIG',
]
