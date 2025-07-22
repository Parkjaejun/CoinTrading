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

def validate_config():
    """설정값 검증"""
    errors = []
    
    # API 키 검증
    if API_KEY == "your_api_key_here" or not API_KEY:
        errors.append("API_KEY가 설정되지 않았습니다")
    
    if API_SECRET == "your_api_secret_here" or not API_SECRET:
        errors.append("API_SECRET가 설정되지 않았습니다")
    
    if PASSPHRASE == "your_passphrase_here" or not PASSPHRASE:
        errors.append("PASSPHRASE가 설정되지 않았습니다")
    
    # 자본 검증
    if TRADING_CONFIG['initial_capital'] <= 0:
        errors.append("초기 자본은 0보다 커야 합니다")
    
    # 심볼 검증
    if not TRADING_CONFIG['symbols'] or len(TRADING_CONFIG['symbols']) == 0:
        errors.append("거래 심볼이 설정되지 않았습니다")
    
    if errors:
        raise ValueError("\n설정 오류:\n" + "\n".join([f"- {error}" for error in errors]))
    
    print("✅ 설정 검증 완료")
    return True