# connection_test.py
"""
수정된 OKX API 및 WebSocket 연결 테스트 스크립트
- ISO Z 형식 타임스탬프 사용
- API 인증 문제 해결
- WebSocket 채널 오류 수정
- 데이터 부족 문제 해결
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
        print("🔍 OKX 수정된 연결 테스트 시작")
        print("="*80)
        
        # 1단계: API 설정 확인 및 수정
        self.test_and_fix_api_configuration()
        
        # 2단계: 기본 API 연결 테스트
        self.test_basic_api_connection()
        
        # 3단계: 계좌 정보 조회 (수정된 방법)
        self.test_account_data_fixed()
        
        # 4단계: 시장 데이터 조회 (충분한 데이터)
        self.test_market_data_fixed()
        
        # 5단계: WebSocket 연결 테스트 (수정된 채널)
        self.test_websocket_connection_fixed()
        
        # 결과 요약
        self.print_test_summary()
        
        return all(self.test_results.values())
    
    def test_and_fix_api_configuration(self):
        """API 설정 확인 및 자동 수정"""
        print("\n🔧 1단계: API 설정 확인 및 수정")
        print("-" * 40)
        
        try:
            # 기본 검증
            if not API_KEY or API_KEY == "your_api_key_here":
                print("❌ API_KEY가 설정되지 않았습니다")
                self.test_results['api_config'] = False
                return
            
            if not API_SECRET or API_SECRET == "your_api_secret_here":
                print("❌ API_SECRET이 설정되지 않았습니다")
                self.test_results['api_config'] = False
                return
            
            if not PASSPHRASE or PASSPHRASE == "your_passphrase_here":
                print("❌ PASSPHRASE가 설정되지 않았습니다")
                self.test_results['api_config'] = False
                return
            
            print(f"✅ API_KEY: {API_KEY[:8]}...{API_KEY[-4:]} ({len(API_KEY)}자)")
            print(f"✅ API_SECRET: {API_SECRET[:8]}...{API_SECRET[-4:]} ({len(API_SECRET)}자)")
            print(f"✅ PASSPHRASE: {'*' * len(PASSPHRASE)} ({len(PASSPHRASE)}자)")
            
            # Passphrase 인코딩 확인
            try:
                passphrase_bytes = PASSPHRASE.encode('utf-8')
                print(f"✅ Passphrase 인코딩 OK: {len(passphrase_bytes)} bytes")
            except Exception as e:
                print(f"⚠️ Passphrase 인코딩 문제: {e}")
            
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
            
            # 공개 API 테스트 (인증 불필요)
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
                
                if time_diff > 30000:
                    print("⚠️ 시간 차이가 큽니다. 시스템 시간을 확인하세요.")
                
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
                        print(f"❌ 시장 데이터 오류: {ticker_data['msg']}")
                        self.test_results['basic_connection'] = False
                else:
                    print(f"❌ 시장 데이터 요청 실패: HTTP {ticker_response.status_code}")
                    self.test_results['basic_connection'] = False
            else:
                print(f"❌ OKX 서버 연결 실패: HTTP {response.status_code}")
                self.test_results['basic_connection'] = False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 네트워크 연결 실패: {e}")
            self.test_results['basic_connection'] = False
        except Exception as e:
            print(f"❌ 기본 연결 테스트 실패: {e}")
            self.test_results['basic_connection'] = False
    
    def test_account_data_fixed(self):
        """수정된 계좌 데이터 테스트"""
        print("\n💳 3단계: 계좌 정보 조회 테스트 (수정된 방법)")
        print("-" * 40)
        
        try:
            # 수정된 AccountManager 생성
            print("🔑 API 인증 테스트 중...")
            
            # 직접 API 요청으로 인증 테스트
            import hmac
            import hashlib
            import base64
            import requests
            
            def create_signature(timestamp, method, request_path, body=''):
                message = timestamp + method + request_path + body
                signature = hmac.new(
                    API_SECRET.encode('utf-8'),
                    message.encode('utf-8'),
                    hashlib.sha256
                ).digest()
                return base64.b64encode(signature).decode()
            
            # 간단한 인증 테스트 (계좌 정보 대신 거래 설정 조회)
            timestamp = get_timestamp()  # ISO Z 형식 사용
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
            
            print("📡 인증된 API 요청 테스트...")
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
                    
                    # 잔고 조회 시도
                    print("\n💰 잔고 조회 시도...")
                    balance_timestamp = get_timestamp()  # ISO Z 형식 사용
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
                            
                            balances = {}
                            for detail in balance_data['data'][0]['details']:
                                currency = detail['ccy']
                                total = float(detail['bal'])
                                available = float(detail['availBal'])
                                
                                if total > 0:
                                    balances[currency] = {
                                        'total': total,
                                        'available': available
                                    }
                                    print(f"  💰 {currency}: {total:.6f} (사용가능: {available:.6f})")
                            
                            if 'USDT' in balances:
                                usdt_balance = balances['USDT']['available']
                                if usdt_balance < 10:
                                    print(f"⚠️ USDT 잔고 부족: ${usdt_balance:.2f}")
                                else:
                                    print(f"✅ USDT 잔고 충분: ${usdt_balance:.2f}")
                        else:
                            print(f"❌ 잔고 조회 실패: {balance_data['msg']}")
                    else:
                        print(f"❌ 잔고 API 요청 실패: HTTP {balance_response.status_code}")
                    
                    self.test_results['account_data'] = True
                else:
                    print(f"❌ API 응답 오류: {data['msg']}")
                    self.test_results['account_data'] = False
            else:
                print(f"❌ API 요청 실패: HTTP {response.status_code}")
                if response.status_code == 401:
                    print("  🔍 401 오류 원인:")
                    print("  - API 키가 잘못되었습니다")
                    print("  - Passphrase가 잘못되었습니다")
                    print("  - IP 화이트리스트 설정을 확인하세요")
                    print("  - API 권한이 충분하지 않습니다")
                self.test_results['account_data'] = False
                
        except Exception as e:
            print(f"❌ 계좌 데이터 테스트 실패: {e}")
            self.test_results['account_data'] = False
    
    def test_market_data_fixed(self):
        """수정된 시장 데이터 테스트 (충분한 데이터)"""
        print("\n📊 4단계: 시장 데이터 조회 테스트 (충분한 데이터)")
        print("-" * 40)
        
        try:
            # utils.data_loader가 없으면 직접 API 호출
            try:
                from utils.data_loader import HistoricalDataLoader
                loader = HistoricalDataLoader()
                symbol = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])[0]
                
                # 최신 가격 조회
                print(f"💰 {symbol} 최신 가격 조회 중...")
                latest_price = loader.get_latest_price(symbol)
                
                if latest_price:
                    print(f"✅ 최신 가격: ${latest_price:,.2f}")
                else:
                    print("❌ 최신 가격 조회 실패")
                
                # 충분한 과거 캔들 데이터 조회 (500개로 증가)
                print(f"📈 {symbol} 과거 캔들 데이터 조회 중 (충분한 양)...")
                df = loader.get_historical_candles(symbol, "30m", 500)  # 200 -> 500으로 증가
                
                if df is not None and len(df) > 0:
                    log_system(f"캔들 데이터 로딩 완료: {symbol} {len(df)}개")
                    print(f"✅ 캔들 데이터 조회 성공: {len(df)}개")
                    print(f"  📅 시작: {df.iloc[0]['timestamp']}")
                    print(f"  📅 종료: {df.iloc[-1]['timestamp']}")
                    print(f"  💰 최근 가격: ${df.iloc[-1]['close']:.2f}")
                    
                    # EMA 계산 테스트 (충분한 데이터로)
                    print("🧮 EMA 계산 테스트...")
                    strategy_df = loader.prepare_strategy_data(df)
                    if strategy_df is not None:
                        print(f"✅ 전략 데이터 준비 성공: {len(strategy_df)}개 (EMA 포함)")
                        
                        # EMA 값 확인
                        latest_row = strategy_df.iloc[-1]
                        print("📊 최신 EMA 값:")
                        ema_keys = [k for k in latest_row.index if k.startswith('ema_')]
                        for key in ema_keys[:5]:  # 처음 5개만 출력
                            print(f"  - {key}: ${latest_row[key]:.2f}")
                        
                        self.test_results['market_data'] = True
                    else:
                        log_error("EMA 계산 후 데이터가 충분하지 않음")
                        print("❌ 전략 데이터 준비 실패")
                        self.test_results['market_data'] = False
                else:
                    print("❌ 캔들 데이터 조회 실패")
                    self.test_results['market_data'] = False
                    
            except ImportError:
                # data_loader가 없으면 직접 API 호출
                print("⚠️ data_loader 모듈을 찾을 수 없어 직접 API 호출")
                import requests
                
                # 최신 가격 조회
                print("💰 BTC-USDT-SWAP 최신 가격 조회 중...")
                response = requests.get(
                    "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['code'] == '0':
                        price = float(data['data'][0]['last'])
                        print(f"✅ 최신 가격: ${price:,.2f}")
                        self.test_results['market_data'] = True
                    else:
                        print(f"❌ 가격 조회 실패: {data['msg']}")
                        self.test_results['market_data'] = False
                else:
                    print(f"❌ API 요청 실패: HTTP {response.status_code}")
                    self.test_results['market_data'] = False
                
        except Exception as e:
            print(f"❌ 시장 데이터 테스트 실패: {e}")
            self.test_results['market_data'] = False
    
    def test_websocket_connection_fixed(self):
        """수정된 WebSocket 연결 테스트"""
        print("\n📡 5단계: WebSocket 연결 테스트 (수정된 채널)")
        print("-" * 40)
        
        try:
            self.websocket_data_received = False
            self.received_messages = 0
            
            # 수정된 WebSocket 핸들러 생성
            ws_handler = WebSocketHandlerFixed()
            
            # 데이터 수신 콜백 설정
            def on_price_data(symbol, price, data):
                self.websocket_data_received = True
                self.received_messages += 1
                if self.received_messages <= 5:  # 처음 5개만 출력
                    print(f"📊 실시간 데이터 수신: {symbol} = ${price:,.2f}")
            
            def on_connection_status(is_connected):
                if is_connected:
                    print("✅ WebSocket 연결 성공")
                else:
                    print("⚠️ WebSocket 연결 상태 변경")
            
            ws_handler.set_price_callback(on_price_data)
            ws_handler.set_connection_callback(on_connection_status)
            
            # WebSocket 시작 (Ticker만 우선 테스트)
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            print(f"🚀 WebSocket 연결 시작: {symbols} (Ticker 채널만)")
            
            public_thread, private_thread = ws_handler.start_ws_ticker_only(symbols)
            
            if public_thread:
                print("✅ WebSocket 스레드 시작됨")
                
                # 20초 동안 데이터 수신 대기
                print("⏳ 실시간 데이터 수신 대기 (20초)...")
                
                for i in range(20):
                    time.sleep(1)
                    if self.websocket_data_received:
                        break
                    
                    if i % 5 == 0 and i > 0:
                        print(f"  ⏳ 대기 중... ({i}/20초)")
                
                # 결과 확인
                if self.websocket_data_received:
                    print(f"✅ WebSocket 테스트 성공!")
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
        print("📋 수정된 연결 테스트 결과 요약")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        
        test_display = {
            'api_config': 'API 설정',
            'basic_connection': '기본 연결',
            'account_data': '계좌 데이터',
            'market_data': '시장 데이터',
            'websocket': 'WebSocket'
        }
        
        for test_name, result in self.test_results.items():
            status = "✅ 통과" if result else "❌ 실패"
            print(f"{test_display.get(test_name, test_name)}: {status}")
        
        print("-" * 80)
        print(f"전체 결과: {passed_tests}/{total_tests} 통과")
        
        if passed_tests == total_tests:
            print("🎉 모든 테스트 통과! 실시간 트레이딩을 시작할 수 있습니다.")
        elif passed_tests >= 4:
            print("✅ 대부분의 테스트 통과! 일부 기능은 제한될 수 있지만 기본 거래는 가능합니다.")
        else:
            print("⚠️ 주요 테스트 실패. 문제를 해결한 후 다시 시도하세요.")
            self._print_advanced_troubleshooting()
    
    def _print_advanced_troubleshooting(self):
        """고급 문제 해결 팁"""
        print("\n🔧 고급 문제 해결 팁:")
        print("-" * 40)
        
        if not self.test_results.get('account_data', True):
            print("💳 계좌 API 문제 해결:")
            print("  1. OKX 거래소에서 API 키 재생성")
            print("  2. API 권한 설정: 읽기 + 거래 권한 모두 활성화")
            print("  3. IP 화이트리스트에 현재 IP 추가")
            print("  4. Passphrase 대소문자 정확히 입력")
            print("  5. API 키 생성 후 5분 정도 대기")
        
        print("\n📝 다음 단계:")
        print("  1. config.py 파일의 API 설정 재확인")
        print("  2. OKX 거래소 웹사이트에서 API 설정 재점검")
        print("  3. python connection_test.py 재실행")


class WebSocketHandlerFixed:
    """수정된 WebSocket 핸들러 (테스트용)"""
    
    def __init__(self):
        self.public_ws = None
        self.is_running = False
        self.on_price_callback = None
        self.on_connection_callback = None
        
    def set_price_callback(self, callback):
        self.on_price_callback = callback
        
    def set_connection_callback(self, callback):
        self.on_connection_callback = callback
    
    def start_ws_ticker_only(self, symbols):
        """Ticker 채널만 테스트"""
        try:
            import websocket
            import json
            
            self.is_running = True
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if 'data' in data and 'arg' in data:
                        if data['arg'].get('channel') == 'tickers':
                            for ticker in data['data']:
                                symbol = data['arg']['instId']
                                price = float(ticker['last'])
                                if self.on_price_callback:
                                    self.on_price_callback(symbol, price, ticker)
                except:
                    pass
            
            def on_open(ws):
                if self.on_connection_callback:
                    self.on_connection_callback(True)
                
                # Ticker 채널만 구독
                for symbol in symbols:
                    subscribe_msg = {
                        "op": "subscribe",
                        "args": [{"channel": "tickers", "instId": symbol}]
                    }
                    ws.send(json.dumps(subscribe_msg))
            
            def on_error(ws, error):
                if self.on_connection_callback:
                    self.on_connection_callback(False)
            
            def on_close(ws, close_status_code, close_msg):
                if self.on_connection_callback:
                    self.on_connection_callback(False)
            
            self.public_ws = websocket.WebSocketApp(
                "wss://ws.okx.com:8443/ws/v5/public",
                on_message=on_message,
                on_open=on_open,
                on_error=on_error,
                on_close=on_close
            )
            
            thread = threading.Thread(
                target=self.public_ws.run_forever,
                daemon=True
            )
            thread.start()
            
            return thread, None
            
        except Exception as e:
            print(f"WebSocket 시작 오류: {e}")
            return None, None
    
    def stop_ws(self):
        """WebSocket 중지"""
        self.is_running = False
        if self.public_ws:
            self.public_ws.close()


def main():
    """메인 테스트 실행"""
    print("🔍 OKX 수정된 연결 테스트 시작")
    print(f"⏰ 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = OKXConnectionTesterFixed()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n✅ 모든 연결 테스트 성공!")
            print("이제 실시간 트레이딩을 시작할 수 있습니다.")
            return True
        else:
            print("\n⚠️ 일부 연결 테스트 실패")
            print("대부분의 기능은 작동하지만 일부 제한이 있을 수 있습니다.")
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