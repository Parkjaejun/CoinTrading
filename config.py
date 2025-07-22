# config_updated.py
"""
업데이트된 설정 파일 - 알림 시스템 포함
기존 config.py를 이 파일로 교체하세요
"""

# OKX API 인증 정보
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here" 
PASSPHRASE = "your_passphrase_here"

# 거래 기본 설정
TRADING_CONFIG = {
    # 초기 자본
    "initial_capital": 10000,
    
    # 거래 대상
    "symbols": ["BTC-USDT-SWAP"],
    
    # 시간프레임
    "timeframe": "30m",
    
    # 기본 수수료율
    "fee_rate": 0.0005,  # 0.05%
    
    # Paper Trading 모드 (개발/테스트용)
    "paper_trading": False,  # True로 설정하면 실제 주문 없이 시뮬레이션
    
    # 안전 설정
    "max_capital_per_trade": 0.20,  # 거래당 최대 20% 자본 사용
    "max_daily_trades": 100,        # 일일 최대 거래 수
    "emergency_stop_loss": 0.50     # 총 자본의 50% 손실시 전체 중단
}

# 롱 전략 설정 (알고리즘 1)
LONG_STRATEGY_CONFIG = {
    # EMA 기간
    "trend_ema": [150, 200],      # 트렌드 확인: 150EMA > 200EMA
    "entry_ema": [20, 50],        # 진입: 20EMA > 50EMA 골든크로스
    "exit_ema": [20, 100],        # 청산: 20EMA < 100EMA 데드크로스
    
    # 거래 설정
    "leverage": 10,               # 10배 레버리지
    "trailing_stop": 0.10,        # 10% 트레일링 스탑
    "stop_loss": 0.20,            # 20% 손실시 가상모드 전환
    "reentry_gain": 0.30,         # 30% 수익시 실제모드 복귀
    
    # 진입 필터
    "min_volume_ratio": 1.2,      # 평균 거래량의 120% 이상
    "max_rsi": 70,                # RSI 70 이하에서만 진입
}

# 숏 전략 설정 (알고리즘 2)
SHORT_STRATEGY_CONFIG = {
    # EMA 기간
    "trend_ema": [150, 200],      # 트렌드 확인: 150EMA < 200EMA
    "entry_ema": [20, 50],        # 진입: 20EMA < 50EMA 데드크로스
    "exit_ema": [100, 200],       # 청산: 100EMA > 200EMA 골든크로스
    
    # 거래 설정
    "leverage": 3,                # 3배 레버리지
    "trailing_stop": 0.02,        # 2% 트레일링 스탑
    "stop_loss": 0.10,            # 10% 손실시 가상모드 전환
    "reentry_gain": 0.20,         # 20% 수익시 실제모드 복귀
    
    # 진입 필터
    "min_volume_ratio": 1.5,      # 평균 거래량의 150% 이상
    "min_rsi": 30,                # RSI 30 이상에서만 진입
}

# EMA 기간 통합 (WebSocket에서 사용)
EMA_PERIODS = {
    'trend_fast': 150,
    'trend_slow': 200,
    'entry_fast': 20,
    'entry_slow': 50,
    'exit_fast_long': 20,
    'exit_slow_long': 100,
    'exit_fast_short': 100,
    'exit_slow_short': 200
}

# 알림 설정
NOTIFICATION_CONFIG = {
    # 슬랙 설정
    "slack": {
        "enabled": False,  # True로 변경하여 활성화
        "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
        "channel": "#trading-alerts",
        "username": "Trading Bot"
    },
    
    # 텔레그램 설정
    "telegram": {
        "enabled": False,  # True로 변경하여 활성화
        "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
        "chat_id": "YOUR_TELEGRAM_CHAT_ID"
    },
    
    # 이메일 설정
    "email": {
        "enabled": False,  # True로 변경하여 활성화
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "your_email@gmail.com",
        "sender_password": "your_app_password",  # Gmail 앱 비밀번호
        "recipient_email": "recipient@gmail.com"
    },
    
    # 알림 레벨 설정
    "levels": {
        "trade_entry": True,      # 진입 알림
        "trade_exit": True,       # 청산 알림
        "profit_threshold": 50,   # $50 이상 수익시 알림
        "loss_threshold": -30,    # $30 이상 손실시 알림
        "system_errors": True,    # 시스템 오류 알림
        "connection_issues": True # 연결 문제 알림
    }
}

# 연결 관리 설정
CONNECTION_CONFIG = {
    "reconnect_interval": 30,     # 30초마다 연결 상태 확인
    "max_retries": 5,             # 최대 5회 재연결 시도
    "request_timeout": 10,        # API 요청 타임아웃 (초)
    "websocket_ping_interval": 30, # WebSocket 핑 간격
    "rate_limit_delay": 0.1       # API 요청간 최소 간격 (초)
}

# 백테스팅 설정
BACKTEST_CONFIG = {
    "default_start_date": "2024-01-01",
    "default_end_date": "2024-12-31",
    "commission_rate": 0.0005,    # 수수료율
    "slippage": 0.0001,          # 슬리피지 (0.01%)
    "initial_capital": 10000,     # 백테스트 초기 자본
    "benchmark_symbol": "BTC-USDT-SWAP"  # 벤치마크 심볼
}

# 로깅 설정
LOGGING_CONFIG = {
    "log_level": "INFO",          # DEBUG, INFO, WARNING, ERROR
    "log_to_file": True,          # 파일 로깅 활성화
    "log_to_console": True,       # 콘솔 로깅 활성화
    "max_log_files": 30,          # 최대 로그 파일 수
    