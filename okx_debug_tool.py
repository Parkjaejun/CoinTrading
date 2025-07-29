# okx_api_debug_tool.py
"""
OKX API 디버깅 도구
API 요청을 단계별로 분석하여 정확한 문제 원인을 파악
"""

import requests
import hmac
import hashlib
import base64
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

class OKXAPIDebugger:
    def __init__(self, api_key, api_secret, passphrase):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = "https://www.okx.com"
        
    def generate_timestamp(self):
        """정확한 타임스탬프 생성"""
        return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    
    def generate_signature(self, timestamp, method, request_path, body=""):
        """서명 생성 과정을 단계별로 분석"""
        print(f"\n🔍 서명 생성 과정 분석:")
        print(f"  1. Timestamp: {timestamp}")
        print(f"  2. Method: {method}")
        print(f"  3. Request Path: {request_path}")
        print(f"  4. Body: '{body}'")
        
        # 서명 메시지 구성
        message = timestamp + method.upper() + request_path + body
        print(f"  5. 서명 메시지: '{message}'")
        print(f"  6. 메시지 길이: {len(message)} bytes")
        
        # HMAC-SHA256 계산
        try:
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            # Base64 인코딩
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            print(f"  7. 서명 (Base64): {signature_b64[:20]}...{signature_b64[-10:]}")
            return signature_b64
            
        except Exception as e:
            print(f"  ❌ 서명 생성 실패: {e}")
            return None
    
    def create_headers(self, method, request_path, body=""):
        """헤더 생성 및 검증"""
        timestamp = self.generate_timestamp()
        signature = self.generate_signature(timestamp, method, request_path, body)
        
        if not signature:
            return None
            
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        print(f"\n📋 요청 헤더:")
        for key, value in headers.items():
            if key == 'OK-ACCESS-SIGN':
                print(f"  {key}: {value[:20]}...{value[-10:]}")
            else:
                print(f"  {key}: {value}")
                
        return headers
    
    def test_endpoint(self, method, endpoint, params=None, expected_success=True):
        """특정 엔드포인트 테스트"""
        print(f"\n{'='*80}")
        print(f"🧪 엔드포인트 테스트: {method} {endpoint}")
        print(f"{'='*80}")
        
        # URL 구성
        url = self.base_url + endpoint
        
        # 파라미터 처리
        query_string = ""
        if params:
            query_string = "?" + urlencode(params)
            print(f"📝 파라미터: {params}")
            print(f"📝 쿼리 스트링: {query_string}")
        
        # 요청 경로 (서명용)
        request_path = endpoint + query_string
        
        # 헤더 생성
        headers = self.create_headers(method, request_path)
        if not headers:
            print("❌ 헤더 생성 실패")
            return False
        
        try:
            print(f"\n🚀 API 요청 실행:")
            print(f"  URL: {url}{query_string}")
            
            # 요청 실행
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=params or {}, timeout=15)
            else:
                print(f"❌ 지원하지 않는 메서드: {method}")
                return False
            
            # 응답 분석
            print(f"\n📊 응답 분석:")
            print(f"  상태 코드: {response.status_code}")
            print(f"  응답 헤더: {dict(response.headers)}")
            
            try:
                response_data = response.json()
                print(f"  응답 데이터: {json.dumps(response_data, indent=2)}")
                
                if response.status_code == 200:
                    if response_data.get('code') == '0':
                        print("✅ 요청 성공!")
                        return True
                    else:
                        print(f"❌ API 오류: {response_data.get('msg', 'Unknown')}")
                        return False
                else:
                    print(f"❌ HTTP 오류: {response.status_code}")
                    return False
                    
            except json.JSONDecodeError:
                print(f"  응답 텍스트: {response.text}")
                print("❌ JSON 파싱 실패")
                return False
                
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            return False
    
    def comprehensive_debug(self):
        """종합적인 디버깅 실행"""
        print("🔍 OKX API 종합 디버깅 시작")
        print(f"⏰ 시작 시간: {datetime.now()}")
        
        # API 키 정보 확인
        print(f"\n🔑 API 키 정보:")
        print(f"  API Key: {self.api_key[:8]}...{self.api_key[-8:]}")
        print(f"  API Secret: {self.api_secret[:8]}...{self.api_secret[-8:]}")
        print(f"  Passphrase: {'*' * len(self.passphrase)} ({len(self.passphrase)}자)")
        
        results = {}
        
        # 1. 공개 API 테스트 (인증 불필요)
        print(f"\n{'🌐 공개 API 테스트 (인증 불필요)'}")
        print("-" * 50)
        
        try:
            response = requests.get(f"{self.base_url}/api/v5/public/time", timeout=10)
            if response.status_code == 200:
                data = response.json()
                server_time = int(data['data'][0]['ts'])
                local_time = int(time.time() * 1000)
                time_diff = abs(server_time - local_time)
                
                print(f"✅ 서버 연결 성공")
                print(f"  서버 시간: {datetime.fromtimestamp(server_time/1000)}")
                print(f"  로컬 시간: {datetime.fromtimestamp(local_time/1000)}")
                print(f"  시간 차이: {time_diff}ms")
                
                if time_diff > 30000:
                    print("⚠️ 시간 동기화 문제! 30초 이상 차이")
                
                results['public_api'] = True
            else:
                print(f"❌ 서버 연결 실패: {response.status_code}")
                results['public_api'] = False
        except Exception as e:
            print(f"❌ 공개 API 테스트 실패: {e}")
            results['public_api'] = False
        
        # 2. 인증 API 테스트들
        test_cases = [
            {
                'name': '계좌 설정 조회',
                'method': 'GET',
                'endpoint': '/api/v5/account/config',
                'params': None,
                'description': '가장 기본적인 인증 API'
            },
            {
                'name': '계좌 잔고 조회',
                'method': 'GET', 
                'endpoint': '/api/v5/account/balance',
                'params': None,
                'description': '잔고 정보 조회'
            },
            {
                'name': '포지션 조회 (파라미터 없음)',
                'method': 'GET',
                'endpoint': '/api/v5/account/positions',
                'params': None,
                'description': '파라미터 없이 포지션 조회 (실패 예상)'
            },
            {
                'name': '포지션 조회 (SWAP)',
                'method': 'GET',
                'endpoint': '/api/v5/account/positions',
                'params': {'instType': 'SWAP'},
                'description': 'SWAP 타입 포지션 조회'
            },
            {
                'name': '포지션 조회 (SPOT)',
                'method': 'GET',
                'endpoint': '/api/v5/account/positions',
                'params': {'instType': 'SPOT'},
                'description': 'SPOT 타입 포지션 조회'
            },
            {
                'name': '포지션 조회 (FUTURES)',
                'method': 'GET',
                'endpoint': '/api/v5/account/positions',
                'params': {'instType': 'FUTURES'},
                'description': 'FUTURES 타입 포지션 조회'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. {test_case['name']}")
            print(f"   설명: {test_case['description']}")
            
            success = self.test_endpoint(
                test_case['method'],
                test_case['endpoint'], 
                test_case['params']
            )
            
            results[test_case['name']] = success
            
            # 요청 간 간격
            time.sleep(0.5)
        
        # 3. 결과 요약
        print(f"\n{'='*80}")
        print("📊 디버깅 결과 요약")
        print(f"{'='*80}")
        
        for test_name, result in results.items():
            status = "✅ 성공" if result else "❌ 실패"
            print(f"{test_name}: {status}")
        
        # 4. 문제 분석 및 해결책 제시
        self.analyze_results(results)
    
    def analyze_results(self, results):
        """결과 분석 및 해결책 제시"""
        print(f"\n🔍 문제 분석:")
        print("-" * 50)
        
        # 공개 API 실패
        if not results.get('public_api', False):
            print("❌ 기본 네트워크 연결 문제")
            print("   해결책: 인터넷 연결, 방화벽 설정 확인")
            return
        
        # 모든 인증 API 실패
        auth_tests = [k for k in results.keys() if k != 'public_api']
        auth_successes = [results[k] for k in auth_tests]
        
        if not any(auth_successes):
            print("❌ 모든 인증 API 실패")
            print("   가능한 원인:")
            print("   1. API 키, 시크릿, 패스프레이즈 오류")
            print("   2. IP 화이트리스트 미설정")
            print("   3. API 권한 부족")
            print("   4. 시간 동기화 문제")
            return
        
        # 일부 인증 API만 실패
        config_success = results.get('계좌 설정 조회', False)
        balance_success = results.get('계좌 잔고 조회', False)
        
        if config_success and balance_success:
            print("✅ 기본 인증 API는 정상 작동")
            
            # 포지션 관련 분석
            pos_no_param = results.get('포지션 조회 (파라미터 없음)', False)
            pos_swap = results.get('포지션 조회 (SWAP)', False)
            pos_spot = results.get('포지션 조회 (SPOT)', False)
            
            if not pos_no_param and pos_swap:
                print("🎯 문제 발견: 포지션 조회는 instType 파라미터가 필수!")
                print("   해결책: get_positions() 호출 시 instType='SWAP' 파라미터 추가")
            elif not any([pos_no_param, pos_swap, pos_spot]):
                print("❌ 모든 포지션 조회 실패")
                print("   가능한 원인: 거래 권한 없음 또는 계좌 타입 문제")
        else:
            print("❌ 기본 인증 API 실패")
            print("   API 키 설정을 다시 확인하세요")

def main():
    """메인 실행 함수"""
    try:
        from config import API_KEY, API_SECRET, PASSPHRASE
        
        print("🔍 OKX API 디버깅 도구 v1.0")
        print("=" * 60)
        
        debugger = OKXAPIDebugger(API_KEY, API_SECRET, PASSPHRASE)
        debugger.comprehensive_debug()
        
        print(f"\n🏁 디버깅 완료: {datetime.now()}")
        
    except ImportError:
        print("❌ config.py에서 API 키 정보를 가져올 수 없습니다")
    except Exception as e:
        print(f"❌ 디버깅 도구 실행 실패: {e}")

if __name__ == "__main__":
    main()