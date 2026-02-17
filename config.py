# config.py
"""
OKX 자동매매 시스템 통합 설정 파일
- 기존 설정 유지 (GUI 호환)
- v2 Long Only 설정 추가
"""

import os
import json
import hmac
import hashlib
import base64
import socket
import requests
from requests.adapters import HTTPAdapter
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from dataclasses import dataclass


# =================================================================
# IPv4 강제 사용 (OKX IP 화이트리스트 호환)
# =================================================================
_original_getaddrinfo = socket.getaddrinfo

def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """IPv4만 사용하도록 강제"""
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = _ipv4_only_getaddrinfo


# =================================================================
# OKX API 인증 정보
# =================================================================
API_KEY = os.getenv('OKX_API_KEY', '56b17443-24b5-4cf6-91e7-90dc87f8dbed')
API_SECRET = os.getenv('OKX_API_SECRET', '4BB49817B72012ADA616B0634696B8CA')
PASSPHRASE = os.getenv('OKX_PASSPHRASE', 'Qkrwowns123!@')

# API 서버 정보
API_BASE_URL = "https://www.okx.com"


# =================================================================
# 연결 설정
# =================================================================
CONNECTION_CONFIG = {
    "request_timeout": 10,
    "timeout": 10,
    "max_retries": 3,
    "retry_count": 3,
    "retry_delay": 1,
    "max_connections": 5,
}


# =================================================================
# 거래 기본 설정
# =================================================================
TRADING_CONFIG = {
    "initial_capital": 100,
    "symbols": ["BTC-USDT-SWAP"],
    "timeframe": "30m",
    "fee_rate": 0.0005,
    "paper_trading": False,
    "max_capital_per_trade": 0.20,
    "max_daily_trades": 100,
    "emergency_stop_loss": 0.50,
    "initial_balance": 10000,
    "default_leverage": 10,
    "max_position_size": 1000,
    "risk_per_trade": 0.02,
    "max_daily_loss": 0.05,
}


# =================================================================
# EMA 기간 설정 (WebSocket에서 사용)
# =================================================================
EMA_PERIODS = {
    'trend_fast': 150,
    'trend_slow': 200,
    'entry_fast': 20,
    'entry_slow': 50,
    'exit_fast': 20,
    'exit_slow': 100,
    'exit_fast_long': 20,
    'exit_slow_long': 100,
    'exit_fast_short': 100,
    'exit_slow_short': 200,
    # 추가 호환 키
    "trend_medium": 50,
    "trend_long": 150,
    "trend_super": 200,
}


# =================================================================
# v2 Long Only 전략 설정 (메인)
# =================================================================
LONG_STRATEGY_CONFIG = {
    # EMA 기간
    'trend_fast': 150,
    'trend_slow': 200,
    'entry_fast': 20,
    'entry_slow': 50,
    'exit_fast': 20,
    'exit_slow': 100,
    
    # 거래 설정
    'leverage': 10,
    'trailing_stop': 0.10,
    
    # 듀얼 모드 설정
    'stop_loss': 0.20,
    'reentry_gain': 0.30,
    
    # 자본 설정
    'capital_use_ratio': 0.50,
    'capital_allocation': 0.5,
    'fee_rate': 0.0005,
    
    # 하위 호환 (기존 키)
    "trend_ema": [150, 200],
    "entry_ema": [20, 50],
    "exit_ema": [20, 100],
    "min_volume_ratio": 1.2,
    "max_rsi": 70,
}

LONG_STRATEGY_CONFIG_V2 = LONG_STRATEGY_CONFIG


# =================================================================
# Short 전략 설정 (DEPRECATED - 하위 호환용)
# =================================================================
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
    "capital_allocation": 0.5,
    'deprecated': True,
}


# =================================================================
# 알림 설정
# =================================================================
NOTIFICATION_CONFIG = {
    "enabled": True,
    "slack": {
        "enabled": False,
        "webhook_url": "",
        "channel": "#trading-alerts",
        "username": "Trading Bot"
    },
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": ""
    },
    "email": {
        "enabled": True,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender": "jpark3971@gmail.com",
        "password": "chfm mtuc zxyk zwrb",
        "recipient": "jpark3971@gmail.com"
    }
}


# =================================================================
# 이메일 알림 설정 (v2)
# =================================================================
@dataclass
class EmailConfig:
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    recipient_email: str = ""
    notify_on_entry: bool = True
    notify_on_exit: bool = True
    notify_on_mode_switch: bool = True
    notify_on_error: bool = True
    
    @classmethod
    def from_env(cls) -> 'EmailConfig':
        return cls(
            smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            sender_email=os.getenv('ALERT_EMAIL', ''),
            sender_password=os.getenv('ALERT_PASSWORD', ''),
            recipient_email=os.getenv('RECIPIENT_EMAIL', ''),
        )
    
    @property
    def is_configured(self) -> bool:
        return bool(self.sender_email and self.sender_password and self.recipient_email)


DEFAULT_EMAIL_CONFIG = EmailConfig.from_env()


# =================================================================
# 디버깅 설정
# =================================================================
DEBUG_CONFIG = {
    'enable_debug_logging': True,
    'log_interval_bars': 10,
    'enable_signal_history': True,
    'max_signal_history': 1000,
    'monitoring_interval': 30,
}


# =================================================================
# 로깅 설정
# =================================================================
LOGGING_CONFIG = {
    "level": "INFO",
    "file_enabled": True,
    "console_enabled": True,
    "max_file_size": 10,
    "backup_count": 5
}


# =================================================================
# WebSocket 설정
# =================================================================
WEBSOCKET_CONFIG = {
    'public_url': 'wss://ws.okx.com:8443/ws/v5/public',
    'private_url': 'wss://ws.okx.com:8443/ws/v5/private',
    'reconnect_attempts': 5,
    'reconnect_delay': 5,
    'heartbeat_interval': 25,
}


# =================================================================
# GUI 설정
# =================================================================
GUI_CONFIG = {
    'window_title': 'OKX 자동매매 시스템 v2 (Long Only)',
    'window_width': 1600,
    'window_height': 1000,
    'min_width': 1200,
    'min_height': 800,
    'dark_theme': True,
}


# =================================================================
# Rate Limiting
# =================================================================
_api_lock = threading.Lock()
_last_request_time = 0
_min_request_interval = 0.1

_timestamp_lock = threading.Lock()
_last_timestamp = ""


# =================================================================
# API 유틸리티 함수
# =================================================================
def get_timestamp() -> str:
    """OKX API 표준 타임스탬프 생성 - 유니크 보장"""
    global _last_timestamp
    
    with _timestamp_lock:
        while True:
            current_timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            if current_timestamp != _last_timestamp:
                _last_timestamp = current_timestamp
                return current_timestamp
            time.sleep(0.001)


def get_iso_timestamp() -> str:
    """ISO 형식 타임스탬프 (별칭)"""
    return get_timestamp()


def generate_signature(timestamp: str, method: str, request_path: str, body: str = "") -> str:
    """OKX API 서명 생성"""
    message = timestamp + method.upper() + request_path + body
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')


def get_headers(method: str, request_path: str, body: str = "") -> Dict[str, str]:
    """API 요청 헤더 생성"""
    timestamp = get_timestamp()
    signature = generate_signature(timestamp, method, request_path, body)
    
    return {
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json'
    }


def get_api_headers(method: str = "GET", endpoint: str = "", body: str = "") -> Dict[str, str]:
    """API 요청 헤더 생성 (별칭)"""
    return get_headers(method, endpoint, body)


def make_api_request(method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
    """
    통합 API 요청 함수
    
    Args:
        method: HTTP 메서드 (GET, POST, DELETE)
        endpoint: API 엔드포인트
        params: 쿼리 파라미터 (GET)
        data: 요청 바디 (POST)
    
    Returns:
        API 응답 딕셔너리
    """
    base_url = API_BASE_URL + endpoint
    body = json.dumps(data, separators=(',', ':')) if data else ""
    
    for attempt in range(CONNECTION_CONFIG['max_retries']):
        try:
            # 쿼리 스트링 생성
            query_string = ""
            if params and method.upper() == 'GET':
                query_string = urlencode(params)
            
            # 서명용 request_path 생성
            request_path = endpoint
            if query_string:
                request_path = endpoint + "?" + query_string
            
            # 헤더 생성
            headers = get_headers(method.upper(), request_path, body)
            
            # 요청 실행
            if method.upper() == 'GET':
                if params:
                    response = requests.get(
                        base_url, 
                        headers=headers, 
                        params=params,
                        timeout=CONNECTION_CONFIG['request_timeout']
                    )
                else:
                    response = requests.get(
                        base_url, 
                        headers=headers, 
                        timeout=CONNECTION_CONFIG['request_timeout']
                    )
            elif method.upper() == 'POST':
                response = requests.post(
                    base_url, 
                    headers=headers, 
                    data=body, 
                    timeout=CONNECTION_CONFIG['request_timeout']
                )
            elif method.upper() == 'DELETE':
                response = requests.delete(
                    base_url, 
                    headers=headers, 
                    timeout=CONNECTION_CONFIG['request_timeout']
                )
            else:
                print(f"❌ 지원하지 않는 HTTP 메서드: {method}")
                return None
            
            # 응답 처리
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"HTTP 오류 {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {response.text}"
                
                print(f"❌ {error_msg} (시도 {attempt + 1})")
                
                if response.status_code == 401:
                    print("🚨 API 인증 오류 - API 키를 확인하세요!")
                    break
                
                time.sleep(CONNECTION_CONFIG['retry_delay'])
                
        except requests.exceptions.Timeout:
            print(f"❌ 요청 타임아웃 (시도 {attempt + 1})")
            if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                time.sleep(CONNECTION_CONFIG['retry_delay'])
        except requests.exceptions.RequestException as e:
            print(f"❌ 네트워크 오류: {e} (시도 {attempt + 1})")
            if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                time.sleep(CONNECTION_CONFIG['retry_delay'])
        except Exception as e:
            print(f"❌ 요청 처리 오류: {e} (시도 {attempt + 1})")
            if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                time.sleep(CONNECTION_CONFIG['retry_delay'])
    
    return None


def get_account_balance() -> Optional[Dict]:
    """계좌 잔고 조회"""
    return make_api_request("GET", "/api/v5/account/balance")


def get_positions(inst_type: str = "SWAP") -> Optional[Dict]:
    """포지션 조회"""
    return make_api_request("GET", "/api/v5/account/positions", params={"instType": inst_type})


def place_order(inst_id: str, td_mode: str, side: str, ord_type: str, 
                sz: str, px: str = None, reduce_only: bool = False) -> Optional[Dict]:
    """주문 실행"""
    data = {
        "instId": inst_id,
        "tdMode": td_mode,
        "side": side,
        "ordType": ord_type,
        "sz": sz
    }
    if px:
        data["px"] = px
    if reduce_only:
        data["reduceOnly"] = True
    
    return make_api_request("POST", "/api/v5/trade/order", data=data)


def validate_config() -> bool:
    """설정 유효성 검증"""
    print("🔍 API 설정 검증 중...")
    
    if not API_KEY or API_KEY == 'your_api_key_here':
        print("❌ API_KEY가 설정되지 않았습니다")
        return False
    if not API_SECRET or API_SECRET == 'your_api_secret_here':
        print("❌ API_SECRET가 설정되지 않았습니다")
        return False
    if not PASSPHRASE or PASSPHRASE == 'your_passphrase_here':
        print("❌ PASSPHRASE가 설정되지 않았습니다")
        return False
    
    if len(API_KEY) < 20:
        print(f"❌ API_KEY가 너무 짧습니다: {len(API_KEY)}자")
        return False
    if len(API_SECRET) < 20:
        print(f"❌ API_SECRET이 너무 짧습니다: {len(API_SECRET)}자")
        return False
    
    print("✅ API 설정이 유효합니다")
    print(f"   API_KEY: {API_KEY[:8]}...{API_KEY[-4:]}")
    return True


def test_api_connection() -> bool:
    """API 연결 테스트"""
    try:
        # Public API 테스트
        response = requests.get(f"{API_BASE_URL}/api/v5/public/time", timeout=10)
        if response.status_code != 200:
            print(f"❌ Public API 연결 실패: {response.status_code}")
            return False
        print("✅ Public API 연결 성공")
        
        # Private API 테스트
        result = make_api_request("GET", "/api/v5/account/balance")
        if result and result.get('code') == '0':
            print("✅ Private API 인증 성공")
            return True
        else:
            print(f"❌ Private API 오류: {result}")
            return False
            
    except Exception as e:
        print(f"❌ API 연결 오류: {e}")
        return False


# =================================================================
# 메인 실행 시 설정 검증
# =================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🔧 OKX API 설정 검증")
    print("=" * 60)
    
    if validate_config():
        if test_api_connection():
            print("\n🎉 모든 테스트 통과!")
        else:
            print("\n❌ API 연결 실패")
    else:
        print("\n❌ API 설정이 올바르지 않습니다")