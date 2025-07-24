# config.py
"""
타임스탬프 문제 해결된 설정 파일
OKX API 인증을 위한 공통 유틸리티 함수 포함
"""
import os
import json
import time
import hmac
import hashlib
import base64
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# OKX API 인증 정보
API_KEY = "56b17443-24b5-4cf6-91e7-90dc87f8dbed"
API_SECRET = "4BB49817B72012ADA616B0634696B8CA" 
PASSPHRASE = "Qkrwowns123!@"

# API 서버 정보
API_BASE_URL = "https://www.okx.com"

# 거래 기본 설정
TRADING_CONFIG = {
    "initial_capital": 100, 
    "symbols": ["BTC-USDT-SWAP"],
    "timeframe": "30m",
    "fee_rate": 0.0005,
    "paper_trading": False,
    "max_capital_per_trade": 0.20,
    "max_daily_trades": 100,
    "emergency_stop_loss": 0.50
}

# 롱 전략 설정 (알고리즘 1)
LONG_STRATEGY_CONFIG = {
    "trend_ema": [150, 200],
    "entry_ema": [20, 50],
    "exit_ema": [20, 100],
    "leverage": 10,
    "trailing_stop": 0.10,
    "stop_loss": 0.20,
    "reentry_gain": 0.30,
    "min_volume_ratio": 1.2,
    "max_rsi": 70,
}

# 숏 전략 설정 (알고리즘 2)
SHORT_STRATEGY_CONFIG = {
    "trend_ema": [150, 200],
    "entry_ema": [20, 50],
    "exit_ema": [100, 200],
    "leverage": 3,
    "trailing_stop": 0.02,
    "stop_loss": 0.10,
    "reentry_gain": 0.20,
    "min_volume_ratio": 1.5,
    "min_rsi": 30,
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
    "slack": {
        "enabled": False,
        "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
        "channel": "#trading-alerts",
        "username": "Trading Bot"
    },
    "telegram": {
        "enabled": False,
        "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
        "chat_id": "YOUR_TELEGRAM_CHAT_ID"
    },
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "your_email@gmail.com",
        "sender_password": "your_app_password",
        "recipient_email": "recipient@gmail.com"
    },
    "levels": {
        "trade_entry": True,
        "trade_exit": True,
        "profit_threshold": 50,
        "loss_threshold": -30,
        "system_errors": True,
        "connection_issues": True
    }
}

# 연결 관리 설정
CONNECTION_CONFIG = {
    "reconnect_interval": 30,
    "max_retries": 5,
    "request_timeout": 10,
    "websocket_ping_interval": 30,
    "rate_limit_delay": 0.1
}

# 백테스팅 설정
BACKTEST_CONFIG = {
    "default_start_date": "2024-01-01",
    "default_end_date": "2024-12-31",
    "commission_rate": 0.0005,
    "slippage": 0.0001,
    "initial_capital": 10000,
    "benchmark_symbol": "BTC-USDT-SWAP"
}

# 로깅 설정
LOGGING_CONFIG = {
    "log_level": "INFO",
    "log_to_file": True,
    "log_to_console": True,
    "max_log_files": 30,
}

# ==================== API 유틸리티 함수 ====================

def get_server_time() -> Optional[int]:
    """OKX 서버 시간 조회 (밀리초 타임스탬프)"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v5/public/time", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return int(data['data'][0]['ts'])
        return None
    except Exception:
        return None

def get_timestamp() -> str:
    """OKX API가 요구하는 ISO Z 형식 타임스탬프 생성"""
    from datetime import datetime, timezone
    
    # UTC 시간을 ISO Z 형식으로 생성
    now = datetime.now(timezone.utc)
    iso_timestamp = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    return iso_timestamp
    
    # 로컬 UTC 시간 사용
    utc_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    return str(utc_timestamp)

def generate_signature(timestamp: str, method: str, request_path: str, body: str = "") -> str:
    """OKX API 서명 생성"""
    try:
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(API_SECRET, encoding='utf-8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
    except Exception as e:
        print(f"❌ 서명 생성 오류: {e}")
        return ""

def get_api_headers(method: str, request_path: str, body: str = "") -> Dict[str, str]:
    """OKX API 요청 헤더 생성"""
    timestamp = get_timestamp()
    signature = generate_signature(timestamp, method, request_path, body)
    
    return {
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json'
    }

def make_api_request(method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
    """통합 API 요청 함수"""
    try:
        url = API_BASE_URL + endpoint
        body = json.dumps(data) if data else ""
        headers = get_api_headers(method, endpoint, body)
        
        # 요청 실행
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=CONNECTION_CONFIG['request_timeout'])
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, data=body, timeout=CONNECTION_CONFIG['request_timeout'])
        else:
            print(f"❌ 지원하지 않는 HTTP 메소드: {method}")
            return None
        
        # 응답 처리
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == '0':
                return result
            else:
                print(f"❌ API 오류: {result}")
                return None
        else:
            print(f"❌ HTTP 오류 {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ API 요청 타임아웃")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ API 연결 오류")
        return None
    except Exception as e:
        print(f"❌ API 요청 실패: {e}")
        return None

def test_api_connection() -> bool:
    """API 연결 및 인증 테스트"""
    print("🔍 API 연결 테스트 중...")
    
    # 1. 공개 API 테스트
    try:
        response = requests.get(f"{API_BASE_URL}/api/v5/public/time", timeout=10)
        if response.status_code != 200:
            print("❌ 공개 API 연결 실패")
            return False
        print("✅ 공개 API 연결 성공")
    except Exception as e:
        print(f"❌ 공개 API 연결 오류: {e}")
        return False
    
    # 2. 인증 API 테스트
    result = make_api_request('GET', '/api/v5/account/balance')
    if result:
        print("✅ 인증 API 연결 성공")
        
        # 잔고 정보 출력
        if result.get('data') and len(result['data']) > 0:
            balances = result['data'][0]['details']
            print("💰 계좌 잔고:")
            for balance in balances:
                if float(balance['cashBal']) > 0:
                    print(f"  - {balance['ccy']}: {balance['cashBal']}")
        
        return True
    else:
        print("❌ 인증 API 연결 실패")
        return False

def get_websocket_auth_data() -> Dict[str, Any]:
    """WebSocket 인증 데이터 생성"""
    timestamp = get_timestamp()
    signature = generate_signature(timestamp, 'GET', '/users/self/verify', '')
    
    return {
        "op": "login",
        "args": [{
            "apiKey": API_KEY,
            "passphrase": PASSPHRASE,
            "timestamp": timestamp,
            "sign": signature
        }]
    }

# ==================== 설정 검증 함수 ====================

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
    
    # API 키 형식 검증
    if len(API_KEY) != 36:
        errors.append(f"API_KEY 길이가 올바르지 않습니다 (현재: {len(API_KEY)}, 예상: 36)")
    
    if len(API_SECRET) != 32:
        errors.append(f"API_SECRET 길이가 올바르지 않습니다 (현재: {len(API_SECRET)}, 예상: 32)")
    
    # 거래 설정 검증
    if TRADING_CONFIG.get('initial_capital', 0) < 100:
        errors.append("초기 자본이 너무 적습니다 (최소 $100)")
    
    symbols = TRADING_CONFIG.get('symbols', [])
    if not symbols:
        errors.append("거래 심볼이 설정되지 않았습니다")
    
    # 실제 API 연결 테스트
    if not errors:  # 기본 설정이 올바를 때만 API 테스트
        print("📡 실제 API 연결 테스트...")
        if not test_api_connection():
            errors.append("API 연결 테스트 실패 - API 키나 네트워크를 확인하세요")
    
    if errors:
        print("❌ 설정 오류:")
        for error in errors:
            print(f"  - {error}")
        raise ValueError("설정 검증 실패")
    
    print("✅ 설정 검증 완료")
    return True

def print_config_summary():
    """설정 요약 출력"""
    print("\n📋 현재 설정 요약:")
    print(f"  💰 초기 자본: ${TRADING_CONFIG.get('initial_capital', 0):,}")
    print(f"  📊 거래 심볼: {', '.join(TRADING_CONFIG.get('symbols', []))}")
    print(f"  📈 롱 레버리지: {LONG_STRATEGY_CONFIG.get('leverage', 0)}배")
    print(f"  📉 숏 레버리지: {SHORT_STRATEGY_CONFIG.get('leverage', 0)}배")
    
    # 현재 시간 및 타임스탬프 표시
    current_timestamp = get_timestamp()
    current_time = datetime.now(timezone.utc)
    print(f"  🕐 현재 UTC 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  ⏱️ 현재 타임스탬프: {current_timestamp}")
    
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

# ==================== 개발용 테스트 함수 ====================

def test_timestamp_sync():
    """타임스탬프 동기화 테스트"""
    print("\n🕐 타임스탬프 동기화 테스트")
    print("-" * 50)
    
    # 서버 시간 조회
    server_time = get_server_time()
    local_time = int(time.time() * 1000)
    
    if server_time:
        time_diff = server_time - local_time
        server_datetime = datetime.fromtimestamp(server_time / 1000, tz=timezone.utc)
        local_datetime = datetime.fromtimestamp(local_time / 1000, tz=timezone.utc)
        
        print(f"🏢 서버 시간: {server_datetime} ({server_time})")
        print(f"🖥️ 로컬 시간: {local_datetime} ({local_time})")
        print(f"⏰ 시간 차이: {time_diff/1000:.2f}초")
        
        if abs(time_diff) > 30000:
            print("⚠️ 시간 차이가 30초를 초과합니다!")
            return False
        else:
            print("✅ 시간 동기화 정상")
            return True
    else:
        print("❌ 서버 시간을 가져올 수 없습니다")
        return False

def run_full_api_test():
    """전체 API 기능 테스트"""
    print("\n🔍 전체 API 기능 테스트")
    print("=" * 80)
    
    # 1. 타임스탬프 동기화 테스트
    timestamp_ok = test_timestamp_sync()
    
    # 2. API 연결 테스트
    api_ok = test_api_connection()
    
    # 3. WebSocket 인증 데이터 생성 테스트
    print("\n🔐 WebSocket 인증 데이터 테스트")
    print("-" * 50)
    try:
        auth_data = get_websocket_auth_data()
        print("✅ WebSocket 인증 데이터 생성 성공")
        print(f"  - 타임스탬프: {auth_data['args'][0]['timestamp']}")
        print(f"  - 서명: {auth_data['args'][0]['sign'][:20]}...{auth_data['args'][0]['sign'][-10:]}")
        websocket_ok = True
    except Exception as e:
        print(f"❌ WebSocket 인증 데이터 생성 실패: {e}")
        websocket_ok = False
    
    # 결과 요약
    print("\n📋 테스트 결과 요약")
    print("=" * 80)
    print(f"타임스탬프 동기화: {'✅ 통과' if timestamp_ok else '❌ 실패'}")
    print(f"API 연결: {'✅ 통과' if api_ok else '❌ 실패'}")
    print(f"WebSocket 인증: {'✅ 통과' if websocket_ok else '❌ 실패'}")
    
    all_ok = timestamp_ok and api_ok and websocket_ok
    if all_ok:
        print("\n🎉 모든 테스트 통과! 시스템을 시작할 수 있습니다.")
    else:
        print("\n⚠️ 일부 테스트 실패. 문제를 해결한 후 다시 시도하세요.")
    
    return all_ok

# 직접 실행시 테스트 수행
if __name__ == "__main__":
    try:
        print("🚀 Config 설정 및 API 연결 테스트")
        run_full_api_test()
    except Exception as e:
        print(f"❌ 테스트 실행 오류: {e}")