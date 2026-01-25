# __init__.py
"""
CoinTrading v2 - Long Only 자동 트레이딩 시스템

주요 특징:
- Long Only 전략 (Short 제거)
- 듀얼 모드 (Real/Virtual) 자동 전환
- 시그널 파이프라인 기반 디버깅
- 이메일 알림 시스템

사용법:
    from cointrading_v2 import (
        TradingEngineV2,
        BacktestV2,
        ParamsV2,
        run_backtest
    )
    
    # 백테스트
    results = run_backtest("data.csv", initial_capital=10000)
    
    # 커스텀 파라미터
    params = ParamsV2(
        leverage=10.0,
        trailing_stop=0.10,
        stop_loss_ratio=0.20,
        reentry_gain_ratio=0.30,
    )
    results = run_backtest("data.csv", params=params)
"""

__version__ = "2.0.0"
__author__ = "CoinTrading Team"

# Config
from .config_v2 import (
    ParamsV2,
    EmailConfig,
    DEFAULT_PARAMS,
    DEFAULT_EMAIL_CONFIG,
)

# Models
from .models import (
    Trade,
    Position,
    SignalEvent,
    ValidationResult,
    OrderEvent,
    ModeSwitchEvent,
    BarData,
    EngineStatus,
)

# Core Engine
from .trading_engine_v2 import TradingEngineV2

# Signal Pipeline
from .signal_pipeline import (
    SignalGenerator,
    SignalValidator,
    SignalPipeline,
    cross_up,
    cross_down,
)

# Email
from .email_notifier import (
    EmailNotifier,
    MockEmailNotifier,
)

# Backtest
from .backtest_v2 import (
    BacktestV2,
    run_backtest,
    load_ohlc_csv,
    prepare_data_with_ema,
    calc_mdd,
    calc_win_rate,
    calc_profit_factor,
)

# Realtime
from .realtime_trader_v2 import (
    RealtimeTraderV2,
    RealtimeSimulator,
    PriceBuffer,
)

# Debug
from .debug_logger import (
    DebugLogger,
    ConditionMonitor,
    get_logger,
    set_logger,
    log_debug,
    log_info,
    log_warning,
    log_error,
)

__all__ = [
    # Version
    "__version__",
    
    # Config
    "ParamsV2",
    "EmailConfig",
    "DEFAULT_PARAMS",
    "DEFAULT_EMAIL_CONFIG",
    
    # Models
    "Trade",
    "Position",
    "SignalEvent",
    "ValidationResult",
    "OrderEvent",
    "ModeSwitchEvent",
    "BarData",
    "EngineStatus",
    
    # Engine
    "TradingEngineV2",
    
    # Pipeline
    "SignalGenerator",
    "SignalValidator",
    "SignalPipeline",
    "cross_up",
    "cross_down",
    
    # Email
    "EmailNotifier",
    "MockEmailNotifier",
    
    # Backtest
    "BacktestV2",
    "run_backtest",
    "load_ohlc_csv",
    "prepare_data_with_ema",
    "calc_mdd",
    "calc_win_rate",
    "calc_profit_factor",
    
    # Realtime
    "RealtimeTraderV2",
    "RealtimeSimulator",
    "PriceBuffer",
    
    # Debug
    "DebugLogger",
    "ConditionMonitor",
    "get_logger",
    "set_logger",
    "log_debug",
    "log_info",
    "log_warning",
    "log_error",
]
