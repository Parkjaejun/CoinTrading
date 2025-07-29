# config.py - 수정된 버전 (API 서명 문제 해결)
"""
OKX API 설정 파일 - Invalid Sign 오류 수정
"""

import os
import json
import hmac
import hashlib
import base64
import requests
import time
from datetime import datetime, timezone
from typing import Dict, Optional

# =================================================================
# ⚠️ 여기에 실제 API 정보를 입력하세요
# =================================================================
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
    """OKX API 표준 타임스탬프 생성"""
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

# =================================================================
# 수정된 서명 생성 함수 (OKX 정확한 방식)
# =================================================================
def generate_signature(timestamp: str, method: str, request_path: str, body: str = "") -> str:
    """OKX API 서명 생성 - 정확한 방식"""
    try:
        # OKX API 서명 메시지 형식: timestamp + method + request_path + body
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
# API 요청 함수 (재시도 로직 포함)
# =================================================================
def make_api_request(method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
    """통합 API 요청 함수"""
    url = API_BASE_URL + endpoint
    body = json.dumps(data, separators=(',', ':')) if data else ""
    
    for attempt in range(CONNECTION_CONFIG['max_retries']):
        try:
            headers = get_api_headers(method, endpoint, body)
            
            print(f"🔍 API 요청 디버그 (시도 {attempt + 1}):")
            print(f"  URL: {url}")
            print(f"  Method: {method}")
            print(f"  Headers: OK-ACCESS-KEY={headers['OK-ACCESS-KEY'][:8]}...")
            print(f"  Timestamp: {headers['OK-ACCESS-TIMESTAMP']}")
            
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
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
            
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
                
                # 401 Unauthorized의 경우 즉시 중단 (API 키 문제)
                if response.status_code == 401:
                    print("🚨 API 인증 오류 - API 키를 확인하세요!")
                    return None
                
                if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                    time.sleep(CONNECTION_CONFIG['retry_delay'])
                    continue
                return None
                
        except requests.exceptions.Timeout:
            print(f"⏰ API 요청 타임아웃 (시도 {attempt + 1})")
            if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                time.sleep(CONNECTION_CONFIG['retry_delay'])
                continue
            return None
            
        except requests.exceptions.ConnectionError:
            print(f"🌐 네트워크 연결 오류 (시도 {attempt + 1})")
            if attempt < CONNECTION_CONFIG['max_retries'] - 1:
                time.sleep(CONNECTION_CONFIG['retry_delay'])
                continue
            return None
            
        except Exception as e:
            print(f"❌ API 요청 실패: {e}")
            return None
    
    return None

# =================================================================
# API 연결 테스트 함수
# =================================================================
def test_api_connection() -> bool:
    """API 연결 및 인증 테스트"""
    print("🔍 API 연결 테스트 시작...")
    
    # 1. 공개 API 테스트 (인증 불필요)
    try:
        response = requests.get(f"{API_BASE_URL}/api/v5/public/time", timeout=10)
        if response.status_code == 200:
            print("✅ 공개 API 연결 성공")
        else:
            print("❌ 공개 API 연결 실패")
            return False
    except Exception as e:
        print(f"❌ 공개 API 연결 오류: {e}")
        return False
    
    # 2. 인증 API 테스트 (계좌 정보 조회)
    try:
        result = make_api_request('GET', '/api/v5/account/balance')
        if result and result.get('code') == '0':
            print("✅ 인증 API 연결 성공")
            
            # 잔액 정보 표시
            if result.get('data'):
                total_eq = result['data'][0].get('totalEq', '0')
                print(f"💰 계좌 총 자산: ${float(total_eq):,.2f}")
                
                # USDT 잔액 표시
                details = result['data'][0].get('details', [])
                for detail in details:
                    if detail.get('ccy') == 'USDT':
                        usdt_balance = float(detail.get('availBal', 0))
                        print(f"💵 USDT 사용 가능: ${usdt_balance:,.2f}")
                        break
            return True
        else:
            print("❌ 인증 API 연결 실패")
            if result:
                print(f"   오류 메시지: {result}")
            return False
            
    except Exception as e:
        print(f"❌ 인증 API 테스트 오류: {e}")
        return False

# =================================================================
# 설정 검증 함수
# =================================================================
def validate_config() -> bool:
    """설정 검증"""
    print("🔍 API 설정 검증 중...")
    
    # API 키 존재 확인
    if not API_KEY or API_KEY == "your_actual_api_key_here":
        print("❌ API_KEY가 설정되지 않았습니다")
        print("   config.py 파일에서 API_KEY를 실제 값으로 변경하세요")
        return False
    
    if not API_SECRET or API_SECRET == "your_actual_secret_key_here":
        print("❌ API_SECRET이 설정되지 않았습니다")
        print("   config.py 파일에서 API_SECRET을 실제 값으로 변경하세요")
        return False
    
    if not PASSPHRASE or PASSPHRASE == "your_actual_passphrase_here":
        print("❌ PASSPHRASE가 설정되지 않았습니다")
        print("   config.py 파일에서 PASSPHRASE를 실제 값으로 변경하세요")
        return False
    
    # API 키 길이 확인
    if len(API_KEY) < 20:
        print(f"❌ API_KEY가 너무 짧습니다: {len(API_KEY)}자")
        return False
        
    if len(API_SECRET) < 20:
        print(f"❌ API_SECRET이 너무 짧습니다: {len(API_SECRET)}자")
        return False
    
    print("✅ API 설정이 유효합니다")
    print(f"   API_KEY: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"   API_SECRET: {API_SECRET[:8]}...{API_SECRET[-4:]}")
    print(f"   PASSPHRASE: {'*' * len(PASSPHRASE)}")
    
    return True

# =================================================================
# 기존 설정들 (호환성 유지)
# =================================================================
TRADING_CONFIG = {
    "symbols": ["BTC-USDT-SWAP"],
    "initial_balance": 10000,
    "paper_trading": False,
    "default_leverage": 10,
    "max_position_size": 1000,
    "risk_per_trade": 0.02,
    "max_daily_loss": 0.05,
    "emergency_stop_loss": 0.20,
}

EMA_PERIODS = {
    "trend_fast": 20,
    "trend_medium": 50,
    "trend_slow": 100,
    "trend_long": 150,
    "trend_super": 200
}

LONG_STRATEGY_CONFIG = {
    "leverage": 10,
    "trailing_stop": 0.10,
    "capital_allocation": 0.5
}

SHORT_STRATEGY_CONFIG = {
    "leverage": 3,
    "trailing_stop": 0.02,
    "capital_allocation": 0.5
}

NOTIFICATION_CONFIG = {
    "enabled": True,
    "slack": {"enabled": False},
    "telegram": {"enabled": False},
    "email": {"enabled": False}
}

LOGGING_CONFIG = {
    "level": "INFO",
    "file_enabled": True,
    "console_enabled": True,
    "max_file_size": 10,
    "backup_count": 5
}

# =================================================================
# 메인 실행 시 설정 검증
# =================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🔧 OKX API 설정 검증")
    print("=" * 60)
    
    if validate_config():
        if test_api_connection():
            print("\n🎉 모든 테스트 통과! 시스템을 시작할 수 있습니다.")
        else:
            print("\n❌ API 연결 실패. 다음을 확인해주세요:")
            print("   1. API 키가 올바른지 확인")
            print("   2. API 권한이 '읽기' + '거래'로 설정되었는지 확인") 
            print("   3. IP 제한이 설정되어 있다면 현재 IP가 포함되었는지 확인")
            print("   4. OKX에서 새 API 키를 생성해보세요")
    else:
        print("\n❌ API 설정이 올바르지 않습니다. config.py를 확인해주세요.")