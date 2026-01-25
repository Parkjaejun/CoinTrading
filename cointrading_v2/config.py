# config.py
"""
CoinTrading 설정 파일
- 기존 설정 유지 + v2 Long Only 설정 추가
- Short 전략은 deprecated (하위 호환용으로 유지)
"""

import os
from dataclasses import dataclass
from typing import Optional


# ===== OKX API 설정 =====
API_KEY = os.getenv('OKX_API_KEY', '')
API_SECRET = os.getenv('OKX_API_SECRET', '')
PASSPHRASE = os.getenv('OKX_PASSPHRASE', '')

# API 모드 (True: 실거래, False: 테스트)
IS_LIVE_TRADING = os.getenv('IS_LIVE_TRADING', 'False').lower() == 'true'


# ===== EMA 기간 설정 =====
EMA_PERIODS = {
    'trend_fast': 150,      # 트렌드 판단 - 빠른 EMA
    'trend_slow': 200,      # 트렌드 판단 - 느린 EMA
    'entry_fast': 20,       # 진입 신호 - 빠른 EMA
    'entry_slow': 50,       # 진입 신호 - 느린 EMA
    'exit_fast': 20,        # 청산 신호 - 빠른 EMA (Long)
    'exit_slow': 100,       # 청산 신호 - 느린 EMA (Long)
}


# ===== v2 Long Only 전략 설정 (메인) =====
LONG_STRATEGY_CONFIG = {
    # EMA 기간 (EMA_PERIODS와 동일)
    'trend_fast': 150,
    'trend_slow': 200,
    'entry_fast': 20,
    'entry_slow': 50,
    'exit_fast': 20,
    'exit_slow': 100,
    
    # 거래 설정
    'leverage': 10,                  # 레버리지 10배
    'trailing_stop': 0.10,           # 트레일링 스탑 10%
    
    # 듀얼 모드 설정
    'stop_loss': 0.20,               # 고점 대비 -20% → VIRTUAL 전환
    'reentry_gain': 0.30,            # 저점 대비 +30% → REAL 복귀
    
    # 자본 설정
    'capital_use_ratio': 0.50,       # 자본의 50% 사용
    'fee_rate': 0.0005,              # 편도 수수료 0.05%
}

# v2 별칭
LONG_STRATEGY_CONFIG_V2 = LONG_STRATEGY_CONFIG


# ===== Short 전략 설정 (DEPRECATED - 하위 호환용) =====
SHORT_STRATEGY_CONFIG = {
    'trend_fast': 150,
    'trend_slow': 200,
    'entry_fast': 20,
    'entry_slow': 50,
    'exit_fast': 100,               # Short 청산용
    'exit_slow': 200,               # Short 청산용
    
    'leverage': 3,                   # 레버리지 3배
    'trailing_stop': 0.02,           # 트레일링 스탑 2%
    
    'stop_loss': 0.10,               # 10% 손실 시 VIRTUAL
    'reentry_gain': 0.20,            # 20% 회복 시 REAL
    
    'capital_use_ratio': 0.50,
    'fee_rate': 0.0005,
    
    # v2에서 사용하지 않음
    'deprecated': True,
    'deprecation_note': 'v2는 Long Only 전략입니다. Short 전략은 사용되지 않습니다.',
}


# ===== 이메일 알림 설정 =====
@dataclass
class EmailConfig:
    """이메일 알림 설정"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""        # Gmail 앱 비밀번호
    recipient_email: str = ""
    
    # 알림 활성화 옵션
    notify_on_entry: bool = True     # 진입 시 알림
    notify_on_exit: bool = True      # 청산 시 알림
    notify_on_mode_switch: bool = True  # 모드 전환 시 알림
    notify_on_error: bool = True     # 오류 시 알림
    
    @classmethod
    def from_env(cls) -> 'EmailConfig':
        """환경변수에서 설정 로드"""
        return cls(
            smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            sender_email=os.getenv('ALERT_EMAIL', ''),
            sender_password=os.getenv('ALERT_PASSWORD', ''),
            recipient_email=os.getenv('RECIPIENT_EMAIL', ''),
        )
    
    @property
    def is_configured(self) -> bool:
        """이메일 설정 완료 여부"""
        return bool(self.sender_email and self.sender_password and self.recipient_email)


# 기본 이메일 설정 인스턴스
DEFAULT_EMAIL_CONFIG = EmailConfig.from_env()


# ===== 디버깅 설정 =====
DEBUG_CONFIG = {
    'enable_debug_logging': True,        # 디버그 로깅 활성화
    'log_interval_bars': 10,             # N봉마다 상세 로그
    'enable_signal_history': True,       # 시그널 히스토리 저장
    'max_signal_history': 1000,          # 최대 히스토리 크기
    'monitoring_interval': 30,           # 모니터링 출력 간격 (초)
}


# ===== 거래 심볼 설정 =====
DEFAULT_SYMBOLS = ['BTC-USDT-SWAP']

# 타임프레임 설정
TIMEFRAME = '30m'  # 30분봉


# ===== WebSocket 설정 =====
WEBSOCKET_CONFIG = {
    'public_url': 'wss://ws.okx.com:8443/ws/v5/public',
    'private_url': 'wss://ws.okx.com:8443/ws/v5/private',
    'reconnect_attempts': 5,
    'reconnect_delay': 5,
    'heartbeat_interval': 25,
}


# ===== GUI 설정 =====
GUI_CONFIG = {
    'window_title': 'OKX 자동매매 시스템 v2 (Long Only)',
    'window_width': 1600,
    'window_height': 1000,
    'min_width': 1200,
    'min_height': 800,
    'dark_theme': True,
}
