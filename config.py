# config.py
"""
OKX 자동매매 시스템 통합 설정 파일
- 기존 설정 유지 (GUI 호환)
- v2 Long Only 설정 추가
"""

import os
import time
import hmac
import hashlib
import base64
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass


# =================================================================
# OKX API 인증 정보
# =================================================================
API_KEY = os.getenv('OKX_API_KEY', 'your_api_key_here')
API_SECRET = os.getenv('OKX_API_SECRET', 'your_api_secret_here')
PASSPHRASE = os.getenv('OKX_PASSPHRASE', 'your_passphrase_here')

# API 서버 정보
API_BASE_URL = "https://www.okx.com"


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
    "emergency_stop_loss": 0.50
}


# =================================================================
# EMA 기간 설정 (WebSocket에서 사용)
# =================================================================
EMA_PERIODS = {
    'trend_fast': 150,
    'trend_slow': 200,
    'entry_fast': 20,
    'entry_slow': 50,
    'exit_fast': 20,           # Long 청산용
    'exit_slow': 100,          # Long 청산용
    'exit_fast_long': 20,      # 하위 호환
    'exit_slow_long': 100,     # 하위 호환
    'exit_fast_short': 100,    # 하위 호환 (Short deprecated)
    'exit_slow_short': 200     # 하위 호환 (Short deprecated)
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
    'leverage': 10,                  # 레버리지 10배
    'trailing_stop': 0.10,           # 트레일링 스탑 10%
    
    # 듀얼 모드 설정
    'stop_loss': 0.20,               # 고점 대비 -20% → VIRTUAL 전환
    'reentry_gain': 0.30,            # 저점 대비 +30% → REAL 복귀
    
    # 자본 설정
    'capital_use_ratio': 0.50,       # 자본의 50% 사용
    'fee_rate': 0.0005,              # 편도 수수료 0.05%
    
    # 하위 호환 (기존 키)
    "trend_ema": [150, 200],
    "entry_ema": [20, 50],
    "exit_ema": [20, 100],
    "min_volume_ratio": 1.2,
    "max_rsi": 70,
}

# v2 별칭
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
    
    # v2에서 사용하지 않음
    'deprecated': True,
    'deprecation_note': 'v2는 Long Only 전략입니다.',
}


# =================================================================
# 이메일 알림 설정 (v2)
# =================================================================
@dataclass
class EmailConfig:
    """이메일 알림 설정"""
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
# 알림 설정 (기존)
# =================================================================
NOTIFICATION_CONFIG = {
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
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender": "",
        "password": "",
        "recipient": ""
    }
}


# =================================================================
# 디버깅 설정 (v2)
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
# API 유틸리티 함수
# =================================================================
def get_timestamp() -> str:
    """OKX API용 타임스탬프 생성"""
    return str(int(time.time() * 1000))


def get_iso_timestamp() -> str:
    """ISO 형식 타임스탬프"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def generate_signature(timestamp: str, method: str, request_path: str, body: str = "") -> str:
    """API 서명 생성"""
    message = timestamp + method.upper() + request_path + body
    mac = hmac.new(
        bytes(API_SECRET, encoding='utf-8'),
        bytes(message, encoding='utf-8'),
        digestmod='sha256'
    )
    return base64.b64encode(mac.digest()).decode()


def get_headers(method: str, request_path: str, body: str = "") -> Dict[str, str]:
    """API 요청 헤더 생성"""
    timestamp = get_iso_timestamp()
    signature = generate_signature(timestamp, method, request_path, body)
    
    return {
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json'
    }


def make_api_request(method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
    """
    OKX API 요청 실행
    
    Args:
        method: HTTP 메서드 (GET, POST, DELETE 등)
        endpoint: API 엔드포인트 (예: /api/v5/account/balance)
        params: 쿼리 파라미터 (GET 요청)
        data: 요청 바디 (POST 요청)
    
    Returns:
        API 응답 딕셔너리 또는 None
    """
    import json
    
    try:
        url = f"{API_BASE_URL}{endpoint}"
        body = ""
        
        # POST 요청의 경우 body를 JSON으로 변환
        if data:
            body = json.dumps(data)
        
        # GET 요청에 쿼리 파라미터 추가
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint_with_params = f"{endpoint}?{query_string}"
            url = f"{API_BASE_URL}{endpoint_with_params}"
        else:
            endpoint_with_params = endpoint
        
        # 헤더 생성
        headers = get_headers(method.upper(), endpoint_with_params, body)
        
        # 요청 실행
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, data=body, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            print(f"❌ 지원하지 않는 HTTP 메서드: {method}")
            return None
        
        # 응답 처리
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == '0':
                return result
            else:
                print(f"❌ API 오류: {result.get('msg', 'Unknown error')}")
                return result
        else:
            print(f"❌ HTTP 오류: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ API 요청 타임아웃")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API 요청 오류: {e}")
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return None


def get_account_balance() -> Optional[Dict]:
    """계좌 잔고 조회"""
    return make_api_request("GET", "/api/v5/account/balance")


def get_positions(inst_type: str = "SWAP") -> Optional[Dict]:
    """포지션 조회"""
    return make_api_request("GET", "/api/v5/account/positions", params={"instType": inst_type})


def place_order(inst_id: str, td_mode: str, side: str, ord_type: str, 
                sz: str, px: str = None, reduce_only: bool = False) -> Optional[Dict]:
    """
    주문 실행
    
    Args:
        inst_id: 상품 ID (예: BTC-USDT-SWAP)
        td_mode: 거래 모드 (cross, isolated, cash)
        side: 주문 방향 (buy, sell)
        ord_type: 주문 유형 (market, limit)
        sz: 수량
        px: 가격 (limit 주문시)
        reduce_only: 포지션 축소 전용
    """
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
    if not API_KEY or API_KEY == 'your_api_key_here':
        print("❌ API_KEY가 설정되지 않았습니다")
        return False
    if not API_SECRET or API_SECRET == 'your_api_secret_here':
        print("❌ API_SECRET가 설정되지 않았습니다")
        return False
    if not PASSPHRASE or PASSPHRASE == 'your_passphrase_here':
        print("❌ PASSPHRASE가 설정되지 않았습니다")
        return False
    print("✅ API 설정이 유효합니다")
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
        request_path = "/api/v5/account/balance"
        headers = get_headers("GET", request_path)
        response = requests.get(f"{API_BASE_URL}{request_path}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print("✅ Private API 인증 성공")
                return True
            else:
                print(f"❌ API 응답 오류: {data.get('msg')}")
                return False
        else:
            print(f"❌ Private API 연결 실패: {response.status_code}")
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
