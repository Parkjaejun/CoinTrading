# strategy/__init__.py
"""
전략 패키지 v2 (Long Only)

주요 클래스:
- LongStrategy: 롱 전략 (v2)
- StrategyManager: 전략 매니저
- SignalPipeline: 시그널 파이프라인
- EmailNotifier: 이메일 알림
"""

from strategy.long_strategy import LongStrategy, LongStrategyV2
from strategy.strategy_manager import (
    StrategyManager,
    LongOnlyStrategyManager,
    DualStrategyManager,  # 하위 호환
    EnhancedMonitoringStrategyManager,
    EnhancedDualStrategyManager,  # 하위 호환
)
from strategy.signal_pipeline import (
    SignalPipeline,
    SignalEvent,
    ValidationResult,
    TradeRecord,
)
from strategy.email_notifier import (
    EmailNotifier,
    MockEmailNotifier,
)

__all__ = [
    # 전략
    'LongStrategy',
    'LongStrategyV2',
    
    # 매니저
    'StrategyManager',
    'LongOnlyStrategyManager',
    'DualStrategyManager',
    'EnhancedMonitoringStrategyManager',
    'EnhancedDualStrategyManager',
    
    # 파이프라인
    'SignalPipeline',
    'SignalEvent',
    'ValidationResult',
    'TradeRecord',
    
    # 알림
    'EmailNotifier',
    'MockEmailNotifier',
]
