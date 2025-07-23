# config_updated.py
"""
업데이트된 설정 파일 - 알림 시스템 포함
기존 config.py를 이 파일로 교체하세요
"""
import os
import json
from datetime import datetime


# OKX API 인증 정보
API_KEY = "ea882939-e193-4c0b-b2c2-0ab9363a3c09"
API_SECRET = "06A9784F2379D554478A61FE85CAF240" 
PASSPHRASE = "Fortis931!@"
#참고
APIkeyname = "TradingAPI"
Permissions = "Read/Trade"

# 거래 기본 설정
TRADING_CONFIG = {
    # 초기 자본 #$
    "initial_capital": 100, 
    
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
}

def validate_config():
    """기본 설정 검증"""
    errors = []
    
    # API 키 검증
    if not API_KEY or API_KEY == "your_api_key_here":
        errors.append("API_KEY가 설정되지 않았습니다")
    
    if not API_SECRET or API_SECRET == "your_api_secret_here":
        errors.append("API_SECRET이 설정되지 않았습니다")
    
    if not PASSPHRASE or PASSPHRASE == "your_passphrase_here":
        errors.append("PASSPHRASE가 설정되지 않았습니다")
    
    # 거래 설정 검증
    if TRADING_CONFIG.get('initial_capital', 0) < 100:
        errors.append("초기 자본이 너무 적습니다 (최소 $100)")
    
    symbols = TRADING_CONFIG.get('symbols', [])
    if not symbols:
        errors.append("거래 심볼이 설정되지 않았습니다")
    
    if errors:
        print("❌ 설정 오류:")
        for error in errors:
            print(f"  - {error}")
        raise ValueError("설정 검증 실패")
    
    print("✅ 설정 검증 완료")

def print_config_summary():
    """설정 요약 출력"""
    print("\n📋 현재 설정 요약:")
    print(f"  💰 초기 자본: ${TRADING_CONFIG.get('initial_capital', 0):,}")
    print(f"  📊 거래 심볼: {', '.join(TRADING_CONFIG.get('symbols', []))}")
    print(f"  📈 롱 레버리지: {LONG_STRATEGY_CONFIG.get('leverage', 0)}배")
    print(f"  📉 숏 레버리지: {SHORT_STRATEGY_CONFIG.get('leverage', 0)}배")
    
    # 알림 채널 확인
    active_notifications = []
    for channel, config in NOTIFICATION_CONFIG.items():
        if isinstance(config, dict) and config.get('enabled', False):
            active_notifications.append(channel)
    
    if active_notifications:
        print(f"  🔔 활성 알림: {', '.join(active_notifications)}")
    else:
        print(f"  🔕 알림: 비활성화")

def load_environment_config(environment="production"):
    """환경별 설정 로드"""
    print(f"📍 환경 설정: {environment}")
    
    if environment == "development":
        TRADING_CONFIG["paper_trading"] = True
        TRADING_CONFIG["initial_capital"] = min(TRADING_CONFIG.get("initial_capital", 10000), 1000)
        print("🧪 개발 모드: Paper Trading 활성화")
    elif environment == "testing":
        TRADING_CONFIG["paper_trading"] = True
        print("🔬 테스트 모드: Paper Trading 활성화")
    else:
        print("🚀 실제 거래 모드")

def backup_config():
    """설정 백업"""
    try:
        backup_dir = "config_backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f"config_backup_{timestamp}.json")
        
        config_data = {
            'trading_config': TRADING_CONFIG,
            'long_strategy_config': LONG_STRATEGY_CONFIG,
            'short_strategy_config': SHORT_STRATEGY_CONFIG,
            'notification_config': NOTIFICATION_CONFIG,
            'backup_time': datetime.now().isoformat()
        }
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        return backup_file
    except Exception as e:
        print(f"⚠️ 설정 백업 실패: {e}")
        return None