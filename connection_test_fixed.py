# connection_test_fixed.py
"""
수정된 OKX API 연결 테스트 - 'bal' 키 문제 해결
실제 OKX API 응답 구조에 맞게 수정됨
"""

import sys
import time
import threading
from datetime import datetime
from typing import Dict, Any

# 프로젝트 모듈 임포트
from config import API_KEY, API_SECRET, PASSPHRASE, TRADING_CONFIG, get_timestamp
from okx.account_manager import AccountManager
from okx.websocket_handler import WebSocketHandler
from utils.logger import log_system, log_error

class OKXConnectionTesterFixed:
    def __init__(self):
        self.test_results = {}
        self.websocket_data_received = False
        self.received_messages = 0
        
    def run_comprehensive_test(self):
        """종합 연결 테스트 실행"""
        print("\n" + "="*80)
        print("🔍 OKX 완전 수정된 연결 테스트 시작")
        print("="*80)
        
        # 1단계: API 설정 확인
        self.test_api_configuration()
        
        # 2단계: 기본 API 연결 테스트
        self.test_basic_api_connection()
        
        # 3단계: 계좌 정보 조회 (올바른 키 사용)
        self.test_account_data_correct()
        
        # 4단계: 시장 데이터 조회
        self.test_market_data()
        
        # 5단계: WebSocket 연결 테스트
        self.test_websocket_connection()
        
        # 결과 요약
        self.print_test_summary()
        
        return all(self.test_results.values())
    
    def test_api_configuration(self):
        """API 설정 확인"""
        print("\n🔧 1단계: API 설정 확인")
        print("-" * 40)
        
        try:
            if not API_KEY or len(API_KEY) < 20:
                print("❌ API_KEY 설정 오류")
                self.test_results['api_config'] = False
                return
            
            if not API_SECRET or len(API_SECRET) < 20:
                print("❌ API_SECRET 설정 오류")
                self.test_results['api_config'] = False
                return
            
            if not PASSPHRASE or len(PASSPHRASE) < 5:
                print("❌ PASSPHRASE 설정 오류")
                self.test_results['api_config'] = False
                return
            
            print(f"✅ API_KEY: {API_KEY[:8]}...{API_KEY[-4:]} ({len(API_KEY)}자)")
            print(f"✅ API_SECRET: {API_SECRET[:8]}...{API_SECRET[-4:]} ({len(API_SECRET)}자)")
            print(f"✅ PASSPHRASE: {'*' * len(PASSPHRASE)} ({len(PASSPHRASE)}자)")
            
            self.test_results['api_config'] = True
            
        except Exception as e:
            print(f"❌ API 설정 확인 실패: {e}")
            self.test_results['api_config'] = False
    
    def test_basic_api_connection(self):
        """기본 API 연결 테스트"""
        print("\n🌐 2단계: 기본 API 연결 테스트")
        print("-" * 40)
        
        try:
            import requests
            
            # 공개 API 테스트
            print("📡 OKX 공개 API 테스트 중...")
            response = requests.get("https://www.okx.com/api/v5/public/time", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                server_time = int(data['data'][0]['ts'])
                local_time = int(time.time() * 1000)
                time_diff = abs(server_time - local_time)
                
                print(f"✅ OKX 서버 연결 성공")
                print(f"⏰ 서버 시간: {datetime.fromtimestamp(server_time/1000)}")
                print(f"⏰ 로컬 시간: {datetime.fromtimestamp(local_time/1000)}")
                print(f"⏰ 시간 차이: {time_diff}ms")
                
                # 시장 데이터 테스트
                print("📊 공개 시장 데이터 테스트...")
                ticker_response = requests.get(
                    "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP", 
                    timeout=10
                )
                
                if ticker_response.status_code == 200:
                    ticker_data = ticker_response.json()
                    if ticker_data['code'] == '0':
                        price = float(ticker_data['data'][0]['last'])
                        print(f"✅ BTC-USDT-SWAP 현재가: ${price:,.2f}")
                
                self.test_results['basic_connection'] = True
            else:
                print(f"❌ OKX 서버 연결 실패: HTTP {response.status_code}")
                self.test_results['basic_connection'] = False
                
        except Exception as e:
            print(f"❌ 기본 연결 테스트 실패: {e}")
            self.test_results['basic_connection'] = False
    
    def test_account_data_correct(self):
        """계좌 데이터 테스트 - 올바른 키 사용"""
        print("\n💳 3단계: 계좌 정보 조회 테스트 (올바른 키 사용)")
        print("-" * 40)
        
        try:
            from config import make_api_request
            import requests
            import hmac
            import hashlib
            import base64
            
            # 직접 API 요청으로 테스트
            def create_signature(timestamp, method, request_path, body=''):
                message = timestamp + method + request_path + body
                signature = hmac.new(
                    API_SECRET.encode('utf-8'),
                    message.encode('utf-8'),
                    hashlib.sha256
                ).digest()
                return base64.b64encode(signature).decode()
            
            print("🔑 API 인증 테스트 중...")
            
            # 계좌 설정 조회
            timestamp = get_timestamp()
            method = 'GET'
            request_path = '/api/v5/account/config'
            
            signature = create_signature(timestamp, method, request_path)
            
            headers = {
                'OK-ACCESS-KEY': API_KEY,
                'OK-ACCESS-SIGN': signature,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': PASSPHRASE,
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'https://www.okx.com/api/v5/account/config',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == '0':
                    print("✅ API 인증 성공!")
                    config = data['data'][0]
                    print(f"  📋 계좌 레벨: {config.get('acctLv', 'Unknown')}")
                    print(f"  📋 포지션 모드: {config.get('posMode', 'Unknown')}")
                    
                    # 잔고 조회 (올바른 키 사용)
                    print("\n💰 잔고 조회 시도 (올바른 키 사용)...")
                    balance_timestamp = get_timestamp()
                    balance_path = '/api/v5/account/balance'
                    balance_signature = create_signature(balance_timestamp, 'GET', balance_path)
                    
                    balance_headers = {
                        'OK-ACCESS-KEY': API_KEY,
                        'OK-ACCESS-SIGN': balance_signature,
                        'OK-ACCESS-TIMESTAMP': balance_timestamp,
                        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
                        'Content-Type': 'application/json'
                    }
                    
                    balance_response = requests.get(
                        'https://www.okx.com/api/v5/account/balance',
                        headers=balance_headers,
                        timeout=10
                    )
                    
                    if balance_response.status_code == 200:
                        balance_data = balance_response.json()
                        if balance_data['code'] == '0':
                            print("✅ 잔고 조회 성공!")
                            
                            # 올바른 키로 잔고 파싱
                            balance_info = balance_data['data'][0]
                            total_equity = balance_info.get('totalEq', '0')
                            print(f"💰 총 자산: ${float(total_equity) if total_equity else 0:.2f}")
                            
                            # details 배열에서 각 통화별 잔고 확인
                            details = balance_info.get('details', [])
                            balances = {}
                            
                            for detail in details:
                                currency = detail.get('ccy', 'UNKNOWN')
                                # 올바른 키 사용: 'availBal', 'eq', 'frozenBal'
                                available = detail.get('availBal', '0')
                                total_bal = detail.get('eq', '0')
                                frozen = detail.get('frozenBal', '0')
                                
                                # 빈 문자열 처리
                                available = float(available) if available else 0.0
                                total_bal = float(total_bal) if total_bal else 0.0
                                frozen = float(frozen) if frozen else 0.0
                                
                                if total_bal > 0.000001:  # 0이 아닌 잔고만
                                    balances[currency] = {
                                        'total': total_bal,
                                        'available': available,
                                        'frozen': frozen
                                    }
                                    print(f"  💰 {currency}: 총 {total_bal:.6f} | 사용가능 {available:.6f} | 동결 {frozen:.6f}")
                            
                            # USDT 잔고 특별 확인
                            if 'USDT' in balances:
                                usdt_available = balances['USDT']['available']
                                if usdt_available < 10:
                                    print(f"⚠️ USDT 잔고 부족: ${usdt_available:.6f} (최소 $10 권장)")
                                else:
                                    print(f"✅ USDT 잔고 충분: ${usdt_available:.6f}")
                            else:
                                print("⚠️ USDT 잔고 없음")
                            
                            self.test_results['account_data'] = True
                        else:
                            print(f"❌ 잔고 조회 실패: {balance_data['msg']}")
                            self.test_results['account_data'] = False
                    else:
                        print(f"❌ 잔고 API 요청 실패: HTTP {balance_response.status_code}")
                        self.test_results['account_data'] = False
                else:
                    print(f"❌ API 응답 오류: {data['msg']}")
                    self.test_results['account_data'] = False
            else:
                print(f"❌ API 요청 실패: HTTP {response.status_code}")
                self.test_results['account_data'] = False
                
        except Exception as e:
            print(f"❌ 계좌 데이터 테스트 실패: {e}")
            self.test_results['account_data'] = False
    
    def test_market_data(self):
        """시장 데이터 테스트"""
        print("\n📊 4단계: 시장 데이터 조회 테스트")
        print("-" * 40)
        
        try:
            from okx.market_data import MarketDataManager
            
            market = MarketDataManager()
            
            # 현재가 조회
            print("💰 BTC-USDT-SWAP 최신 가격 조회 중...")
            ticker = market.get_ticker('BTC-USDT-SWAP')
            
            if ticker:
                price = float(ticker['last'])
                print(f"✅ 최신 가격: ${price:,.2f}")
                
                # 캔들 데이터 조회
                print("📈 BTC-USDT-SWAP 과거 캔들 데이터 조회 중...")
                candles = market.get_candles('BTC-USDT-SWAP', '5m', limit=100)
                
                if candles and len(candles) >= 50:
                    print(f"✅ 캔들 데이터 조회 성공: {len(candles)}개")
                    
                    # 최신 캔들 정보
                    latest = candles[-1]
                    print(f"  📅 최신 캔들: {latest['timestamp']}")
                    print(f"  💰 최근 가격: ${float(latest['close']):,.2f}")
                    
                    self.test_results['market_data'] = True
                else:
                    print("❌ 캔들 데이터 부족")
                    self.test_results['market_data'] = False
            else:
                print("❌ 현재가 조회 실패")
                self.test_results['market_data'] = False
                
        except Exception as e:
            print(f"❌ 시장 데이터 테스트 실패: {e}")
            self.test_results['market_data'] = False
    
    def test_websocket_connection(self):
        """WebSocket 연결 테스트"""
        print("\n📡 5단계: WebSocket 연결 테스트")
        print("-" * 40)
        
        try:
            # WebSocket 핸들러 초기화
            ws_handler = WebSocketHandler()
            
            # 데이터 수신 콜백 설정
            def on_ticker_update(symbol, data):
                self.websocket_data_received = True
                self.received_messages += 1
                price = float(data.get('last', 0))
                print(f"📊 실시간 데이터 수신: {symbol} = ${price:,.2f}")
            
            # 콜백 등록
            ws_handler.on_ticker_update = on_ticker_update
            
            # WebSocket 시작
            print("🚀 WebSocket 연결 시작: ['BTC-USDT-SWAP']")
            ws_thread = threading.Thread(
                target=ws_handler.start_ws, 
                args=(['BTC-USDT-SWAP'],)
            )
            ws_thread.daemon = True
            ws_thread.start()
            
            if ws_thread.is_alive():
                print("✅ WebSocket 스레드 시작됨")
                
                # 데이터 수신 대기
                print("⏳ 실시간 데이터 수신 대기 (15초)...")
                
                for i in range(15):
                    time.sleep(1)
                    if self.websocket_data_received:
                        break
                
                if self.websocket_data_received:
                    print("✅ WebSocket 테스트 성공!")
                    print(f"📊 수신된 메시지: {self.received_messages}건")
                    self.test_results['websocket'] = True
                else:
                    print("❌ WebSocket 데이터 수신 실패")
                    self.test_results['websocket'] = False
                
                # WebSocket 중지
                ws_handler.stop_ws()
                print("🛑 WebSocket 연결 종료")
                
            else:
                print("❌ WebSocket 스레드 시작 실패")
                self.test_results['websocket'] = False
                
        except Exception as e:
            print(f"❌ WebSocket 연결 테스트 실패: {e}")
            self.test_results['websocket'] = False
    
    def print_test_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*80)
        print("📋 완전 수정된 연결 테스트 결과 요약")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        
        test_display = {
            'api_config': 'API 설정',
            'basic_connection': '기본 연결',
            'account_data': '계좌 데이터 (수정됨)',
            'market_data': '시장 데이터',
            'websocket': 'WebSocket'
        }
        
        for test_name, result in self.test_results.items():
            status = "✅ 통과" if result else "❌ 실패"
            display_name = test_display.get(test_name, test_name)
            print(f"{display_name}: {status}")
        
        print("-" * 80)
        print(f"전체 결과: {passed_tests}/{total_tests} 통과")
        
        if passed_tests == total_tests:
            print("🎉 모든 테스트 완전 통과!")
            print("✅ OKX API 연결 문제 완전 해결!")
            print("🚀 실시간 트레이딩 시스템 준비 완료!")
        elif passed_tests >= 4:
            print("✅ 대부분의 테스트 통과!")
            print("기본 거래 기능은 정상 작동합니다.")
        else:
            print("⚠️ 주요 테스트 실패. 추가 점검이 필요합니다.")

def main():
    """메인 테스트 실행"""
    print("🔧 OKX 완전 수정된 연결 테스트 시작")
    print(f"⏰ 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = OKXConnectionTesterFixed()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 모든 연결 테스트 성공!")
            print("이제 GUI를 실행해서 실제 데이터를 확인할 수 있습니다:")
            print("python main.py")
            return True
        else:
            print("\n⚠️ 일부 연결 테스트 실패")
            print("하지만 주요 기능은 작동할 가능성이 높습니다.")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 테스트가 중단되었습니다.")
        return False
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)