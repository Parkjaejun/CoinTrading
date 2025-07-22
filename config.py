# OKX API 인증 정보
# 실제 사용시에는 환경변수나 별도 보안 파일로 관리하세요
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here" 
PASSPHRASE = "your_passphrase_here"

# 거래 기본 설정
TRADING_CONFIG = {
    # 기본 거래 상품
    "default_symbol": "BTC-USDT-SWAP",
    
    # 시간프레임
    "timeframe": "30m",
    
    # 레버리지 설정
    "max_leverage": 10,
    "default_leverage": 3,
    
    # 위험 관리
    "max_drawdown_limit": 0.20,  # 20% 손실시 거래 중단
    "reentry_threshold": 0.30,   # 30% 상승시 재진입
    
    # 수수료율 (기본값, API에서 실제 값 조회)
    "default_fee_rate": 0.0005,  # 0.05%
    
    # 자금 관리
    "risk_per_trade": 0.02,      # 거래당 위험 자본의 2%
    "max_position_size": 0.5,    # 최대 포지션 크기 (자본의 50%)
}

# 알고리즘 설정
ALGORITHM_CONFIG = {
    # 알고리즘 1 (롱 전략)
    "long_strategy": {
        "ema_periods": {
            "trend_fast": 150,    # 150EMA (트렌드 판단)
            "trend_slow": 200,    # 200EMA (트렌드 판단)
            "entry_fast": 20,     # 20EMA (진입 신호)
            "entry_slow": 50,     # 50EMA (진입 신호)
            "exit_fast": 20,      # 20EMA (청산 신호)
            "exit_slow": 100      # 100EMA (청산 신호)
        },
        "leverage": 10,
        "trailing_stop": 0.10,    # 10% 트레일링 스탑
        "stop_loss": 0.20,        # 20% 손실시 거래 중단
        "reentry_gain": 0.30      # 30% 상승시 재진입
    },
    
    # 알고리즘 2 (숏 전략)  
    "short_strategy": {
        "ema_periods": {
            "trend_fast": 150,    # 150EMA (트렌드 판단)
            "trend_slow": 200,    # 200EMA (트렌드 판단)
            "entry_fast": 20,     # 20EMA (진입 신호)
            "entry_slow": 50,     # 50EMA (진입 신호)
            "exit_fast": 100,     # 100EMA (청산 신호)
            "exit_slow": 200      # 200EMA (청산 신호)
        },
        "leverage": 3,
        "trailing_stop": 0.02,    # 2% 트레일링 스탑
        "stop_loss": 0.10,        # 10% 손실시 거래 중단
        "reentry_gain": 0.20      # 20% 상승시 재진입
    }
}

# 알림 설정
NOTIFICATION_CONFIG = {
    "enabled": True,
    
    # 텔레그램 설정
    "telegram": {
        "enabled": False,
        "bot_token": "your_telegram_bot_token",
        "chat_id": "your_chat_id"
    },
    
    # 이메일 설정
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your_email@gmail.com",
        "password": "your_app_password",
        "recipient": "your_email@gmail.com"
    },
    
    # 슬랙 설정
    "slack": {
        "enabled": False,
        "webhook_url": "your_slack_webhook_url",
        "channel": "#trading-alerts"
    }
}

# 백테스팅 설정
BACKTEST_CONFIG = {
    "initial_capital": 10000,    # 초기 자본 (USDT)
    "start_date": "2023-01-01",
    "end_date": "2024-12-31",
    "data_source": "okx",        # 데이터 소스
    "symbols": ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
}

# 로깅 설정
LOGGING_CONFIG = {
    "level": "INFO",
    "file_path": "logs/trading.log",
    "max_file_size": 10,         # MB
    "backup_count": 5,
    "console_output": True
}

# 데이터베이스 설정 (선택사항)
DATABASE_CONFIG = {
    "enabled": False,
    "type": "sqlite",            # sqlite, mysql, postgresql
    "connection_string": "trading_data.db"
}

# 개발/운영 모드 설정
ENVIRONMENT = {
    "mode": "development",       # development, production
    "paper_trading": True,       # 모의투자 모드
    "debug": True
}