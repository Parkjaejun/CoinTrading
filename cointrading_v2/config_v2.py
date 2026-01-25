# config_v2.py
"""
CoinTrading v2 설정 파일
- Long Only 전략 파라미터
- 듀얼 모드 (Real/Virtual) 설정
- 이메일 알림 설정
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class ParamsV2:
    """v2 파라미터 - Long Only 전략"""
    
    # ===== EMA Periods =====
    # 트렌드 판단용 (30분봉)
    trend_fast: int = 150           # 150 EMA
    trend_slow: int = 200           # 200 EMA
    
    # 진입 조건용
    entry_fast: int = 20            # 20 EMA
    entry_slow: int = 50            # 50 EMA
    
    # 청산 조건용
    exit_fast: int = 20             # 20 EMA
    exit_slow: int = 100            # 100 EMA
    
    # ===== Long 전용 설정 =====
    leverage: float = 10.0          # 레버리지 10배
    trailing_stop: float = 0.10     # 트레일링 스탑 10%
    
    # ===== 듀얼 모드 설정 =====
    # REAL → VIRTUAL 전환: 고점 대비 -20% 하락시
    stop_loss_ratio: float = 0.20
    
    # VIRTUAL → REAL 복귀: 저점 대비 +30% 상승시
    reentry_gain_ratio: float = 0.30
    
    # Virtual 모드 기본 자본 (시장 적합도 평가용)
    virtual_baseline: float = 10000.0
    
    # ===== 자본/수수료 =====
    capital_use_ratio: float = 0.50     # 자본의 50% 사용
    fee_rate_per_side: float = 0.0005   # 편도 0.05% (왕복 0.1%)
    
    # ===== Peak/Trough 리셋 옵션 =====
    reset_real_peak_on_v2r: bool = True   # VIRTUAL→REAL 복귀시 real_peak 리셋
    reset_real_peak_on_r2v: bool = True   # REAL→VIRTUAL 전환시 real_peak 리셋
    
    # ===== 디버깅 옵션 =====
    enable_debug_logging: bool = True
    debug_log_interval: int = 10          # 매 N봉마다 상세 로그
    enable_signal_history: bool = True    # 시그널 히스토리 저장
    max_signal_history: int = 1000        # 최대 시그널 히스토리 개수
    
    # ===== 쿨다운 설정 =====
    entry_cooldown_bars: int = 0          # 진입 후 N봉 동안 재진입 금지 (0=비활성)


@dataclass
class EmailConfig:
    """이메일 알림 설정"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""       # Gmail 앱 비밀번호 사용 권장
    recipient_email: str = ""
    
    # 알림 활성화 옵션
    notify_on_entry: bool = True
    notify_on_exit: bool = True
    notify_on_mode_switch: bool = True
    notify_on_error: bool = True
    
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
        """설정이 완료되었는지 확인"""
        return bool(self.sender_email and self.sender_password and self.recipient_email)


# ===== 기본 설정 인스턴스 =====
DEFAULT_PARAMS = ParamsV2()
DEFAULT_EMAIL_CONFIG = EmailConfig.from_env()


# ===== API 설정 (기존 config.py와 호환) =====
# 실제 사용시 .env 파일에서 로드
API_KEY = os.getenv('OKX_API_KEY', '')
API_SECRET = os.getenv('OKX_API_SECRET', '')
PASSPHRASE = os.getenv('OKX_PASSPHRASE', '')


# ===== EMA Periods (기존 호환용) =====
EMA_PERIODS = {
    'trend_fast': DEFAULT_PARAMS.trend_fast,
    'trend_slow': DEFAULT_PARAMS.trend_slow,
    'entry_fast': DEFAULT_PARAMS.entry_fast,
    'entry_slow': DEFAULT_PARAMS.entry_slow,
    'exit_fast': DEFAULT_PARAMS.exit_fast,
    'exit_slow': DEFAULT_PARAMS.exit_slow,
}
