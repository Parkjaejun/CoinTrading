# agents/agent_config.py
"""
에이전트 팀 설정

모든 에이전트가 공유하는 설정값 관리.
환경변수 또는 기본값으로 구성.

=== 자본 $70 기준 설정 ===
BTC-USDT-SWAP 1계약 = 0.01 BTC ≈ $685
15x 레버리지: 마진 $45.7/계약 → $70으로 1계약 가능 (버퍼 $24)
capital_use_ratio 0.65: 실사용 $45.5 → 1계약 정확히 매수
max_position_pct 0.95: 소액이므로 거의 전액 사용 허용
"""

import os
from typing import Dict, Any


AGENT_TEAM_CONFIG: Dict[str, Any] = {
    # Claude API 설정
    "claude_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    "claude_model": "claude-sonnet-4-5-20250929",

    # 목표 및 리스크 한도
    "target_profit": 1000.0,             # 목표 누적 수익 $1000
    "max_drawdown_pct": 0.10,            # 최대 허용 손실 10% ($7)
    "emergency_stop_loss_pct": 0.15,     # 긴급 정지 15% ($10.5)
    "fee_tolerance_pct": 0.02,           # 수수료 허용 버퍼 2% ($1.40) — 원금 이하 판단 시 적용

    # 에이전트 실행 주기 (초)
    "reader_interval": 60,               # Reader 분석 주기 (1분)
    "strategist_interval": 21600,        # Strategist LLM 최적화 주기 (6시간)
    "monitor_interval": 30,              # Monitor 체크 주기 (30초)
    "trader_interval": 5,                # Trader 메시지 폴링 주기 (5초)

    # 뉴스 소스
    "news_sources": ["cryptopanic", "rss"],

    # 포지션 / 신호 제한
    "max_position_pct": 0.95,            # 최대 포지션 비율 95% (소액 계좌)
    "min_signal_confidence": 0.7,        # 최소 신호 신뢰도

    # 거래 대상
    "symbol": "BTC-USDT-SWAP",
    "leverage": 15,                      # 15x (소액 계좌용, 1계약 매수 가능)
    "trade_mode": "cross",

    # 전략 파라미터 허용 범위 (Monitor 검증용)
    "param_limits": {
        "leverage": {"min": 1, "max": 25},
        "trailing_stop": {"min": 0.03, "max": 0.20},
        "entry_fast": {"min": 5, "max": 50},
        "entry_slow": {"min": 20, "max": 100},
        "exit_fast": {"min": 5, "max": 50},
        "exit_slow": {"min": 50, "max": 200},
        "trend_fast": {"min": 50, "max": 200},
        "trend_slow": {"min": 100, "max": 300},
        "capital_use_ratio": {"min": 0.10, "max": 0.95},
    },

    # 코드 수정 허용 경로
    "allowed_code_paths": [
        "strategy/",
        "cointrading_v2/",
    ],

    # 로깅
    "log_dir": "logs",
    "log_level": "INFO",

    # dry-run 모드 (실제 주문 없이 테스트)
    "dry_run": False,
}
