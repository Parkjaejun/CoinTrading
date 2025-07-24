# config.py
"""
수정된 OKX API 설정 파일 - API 서명 문제 해결
"""

import os
import json
import hmac
import hashlib
import base64
import requests
from datetime import datetime, timezone
from typing import Dict, Optional

# =================================================================
# ⚠️ 실제 API 정보를 입력하세요
# =================================================================
# OKX API 인증 정보
API_KEY = "56b17443-24b5-4cf6-91e7-90dc87f8dbed"
API_SECRET = "4BB49817B72012ADA616B0634696B8CA" 
PASSPHRASE = "Qkrwowns123!@"

# 환경변수에서 가져오기 (더 안전한 방법)
if os.getenv('OKX_API_KEY'):
    API_KEY = os.getenv('OKX_API_KEY')
    API_SECRET = os.getenv('OKX_API_SECRET')
    PASSPHRASE = os.getenv('OKX_PASSPHRASE')

# =================================================================
# API 기본 설정
# =================================================================
API_BASE_URL = "https://www.okx.com"
ENVIRONMENT = "production"  # "sandbox" 또는 "production"

# 연결 설정
CONNECTION_CONFIG = {
    "request_timeout": 10,
    "max_retries": 3,
    "retry_delay": 1
}

# =================================================================
# 수정된 타임스탬프 함수 (OKX 표준 준수)
# =================================================================
def get_timestamp():
    """OKX API 표준 타임스탬프 생성 (ISO 8601 Z 형식)"""
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

# =================================================================
# 수정된 서명 생성 함수
# =================================================================
def generate_signature(timestamp: str, method: str, request_path: str, body: str = "") -> str:
    """OKX API 서명 생성 (HMAC-SHA256)"""
    try:
        # 서명 생성을 위한 메시지 구성
        message = timestamp + method.upper() + request_path + body
        
        # HMAC-SHA256으로 서명 생성
        signature = hmac.new(
            API_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Base64 인코딩
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"❌ 서명 생성 실패: {e}")
        raise

# =================================================================
# API 헤더 생성 함수
# =================================================================
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

# =================================================================
# API 요청 함수
# =================================================================
def make_api_request(method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
    """통합 API 요청 함수 (재시도 로직 포함)"""
    url = API_BASE_URL + endpoint
    body = json.dumps(data) if data else ""
    
    for attempt in range(CONNECTION_CONFIG['max_retries']):
        try:
            headers = get_api_headers(method, endpoint, body)
            
            # 요청 실행
            if method.upper() == 'GET':
                response = requests.get(
                    url, 
                    headers=headers, 
                    params=params, 
                    timeout=CONNECTION_CONFIG['request_timeout']
                )
            elif method.upper() == 'POST':
                response = requests.post(
                    url, 
                    headers=headers, 
                    data=body, 
                    timeout=CONNECTION_CONFIG['request_timeout']
                )
            else:
                print(f"❌ 지원하지 않는 HTTP 메소드: {method}")
                return None
            
            # 응답 처리
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == '0':
                    return result
                else:
                    error_msg = result.get('msg', 'Unknown error')
                    print(f"❌ API 오류 (시도 {attempt + 1}/{CONNECTION_CONFIG['max_retries']}): {error_msg}")
                    
                    # 재시도 가능한 오류인 경우
                    if 'rate limit' in error_msg.lower() or 'timeout' in error_msg.lower():
                        if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                            import time
                            time.sleep(CONNECTION_CONFIG['retry_delay'] * (attempt + 1))
                            continue
                    return None
            else:
                print(f"❌ HTTP 오류 {response.status_code} (시도 {attempt + 1}): {response.text}")
                if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                    import time
                    time.sleep(CONNECTION_CONFIG['retry_delay'])
                    continue
                return None
                
        except requests.exceptions.Timeout:
            print(f"❌ API 요청 타임아웃 (시도 {attempt + 1}/{CONNECTION_CONFIG['max_retries']})")
            if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                import time
                time.sleep(CONNECTION_CONFIG['retry_delay'])
                continue
            return None
        except requests.exceptions.ConnectionError:
            print(f"❌ API 연결 오류 (시도 {attempt + 1}/{CONNECTION_CONFIG['max_retries']})")
            if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                import time
                time.sleep(CONNECTION_CONFIG['retry_delay'])
                continue
            return None
        except Exception as e:
            print(f"❌ API 요청 실패: {e}")
            return None
    
    return None

# =================================================================
# WebSocket 인증 데이터 생성
# =================================================================
def get_websocket_auth_data() -> Dict:
    """WebSocket 인증 데이터 생성"""
    timestamp = get_timestamp()
    method = 'GET'
    request_path = '/users/self/verify'
    
    signature = generate_signature(timestamp, method, request_path)
    
    return {
        "op": "login",
        "args": [{
            "apiKey": API_KEY,
            "passphrase": PASSPHRASE,
            "timestamp": timestamp,
            "sign": signature
        }]
    }

# =================================================================
# 설정 검증 함수
# =================================================================
def validate_config() -> bool:
    """설정 검증"""
    print("🔍 API 설정 검증 중...")
    
    # 1. API 키 존재 확인
    if not API_KEY or API_KEY == "your_actual_api_key_here":
        print("❌ API_KEY가 설정되지 않았습니다")
        return False
    
    if not API_SECRET or API_SECRET == "your_actual_secret_key_here":
        print("❌ API_SECRET이 설정되지 않았습니다")
        return False
    
    if not PASSPHRASE or PASSPHRASE == "your_actual_passphrase_here":
        print("❌ PASSPHRASE가 설정되지 않았습니다")
        return False
    
    # 2. API 키 길이 확인 (최소 길이)
    if len(API_KEY) < 20:
        print(f"❌ API_KEY가 너무 짧습니다: {len(API_KEY)}자")
        return False
        
    if len(API_SECRET) < 20:
        print(f"❌ API_SECRET이 너무 짧습니다: {len(API_SECRET)}자")
        return False
    
    print("✅ API 설정이 유효합니다")
    return True

# =================================================================
# API 연결 테스트
# =================================================================
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
    try:
        result = make_api_request('GET', '/api/v5/account/config')
        if result:
            print("✅ 인증 API 연결 성공")
            return True
        else:
            print("❌ 인증 API 연결 실패")
            return False
    except Exception as e:
        print(f"❌ 인증 API 테스트 오류: {e}")
        return False

# =================================================================
# 거래 설정
# =================================================================
TRADING_CONFIG = {
    "initial_balance": 50.0,
    "symbol": "BTC-USDT-SWAP",
    "long_leverage": 10,
    "short_leverage": 3,
    "position_size_ratio": 0.1,
    "trailing_stop_ratio": 0.15,
    "max_positions": 5,
    "risk_limit": 0.02
}

# =================================================================
# 알림 설정
# =================================================================
NOTIFICATION_CONFIG = {
    "enabled": False,
    "slack": {
        "enabled": False,
        "webhook_url": "",
        "channel": "#trading-alerts"
    },
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": ""
    },
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "",
        "password": "",
        "to_email": ""
    }
}

# EMA 기간 통합 (WebSocket에서 사용) - 누락되었던 부분
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

# =================================================================
# 로깅 설정
# =================================================================
import logging
import os

# 로그 디렉토리 생성
os.makedirs("logs", exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trading.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# =================================================================
# 메인 실행부 (테스트용)
# =================================================================
if __name__ == "__main__":
    print("🚀 OKX API 설정 테스트")
    print("=" * 50)
    
    # 설정 검증
    if not validate_config():
        print("\n❌ 설정을 먼저 수정해주세요!")
        print("API_KEY, API_SECRET, PASSPHRASE를 올바르게 입력하세요.")
        exit(1)
    
    # API 연결 테스트  
    if test_api_connection():
        print("\n🎉 모든 테스트 통과! 시스템을 시작할 수 있습니다.")
    else:
        print("\n❌ API 연결 실패. API 키를 다시 확인해주세요.")


        # main.py 호환성을 위한 임시 함수들
def print_config_summary():
    print("📋 현재 설정 요약:")
    print(f"  💰 초기 자본: ${TRADING_CONFIG.get('initial_balance', 50)}")
    print(f"  📊 거래 심볼: {TRADING_CONFIG.get('symbol', 'BTC-USDT-SWAP')}")

def load_environment_config(environment="production"):
    print(f"📍 환경 설정: {environment}")

def backup_config():
    return None