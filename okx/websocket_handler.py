import websocket
import json
import threading
import time
import hmac
import hashlib
import base64
from datetime import datetime
from config import API_KEY, API_SECRET, PASSPHRASE
from utils.price_buffer import PriceBuffer
from utils.generate_latest_data import generate_strategy_data
from utils.indicators import calculate_ema

class WebSocketHandler:
    def __init__(self, strategy_manager=None):
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.private_ws_url = "wss://ws.okx.com:8443/ws/v5/private"
        self.public_ws = None
        self.private_ws = None
        
        self.api_key = API_KEY
        self.secret_key = API_SECRET
        self.passphrase = PASSPHRASE
        
        self.strategy_manager = strategy_manager
        self.price_buffers = {}  # 심볼별 가격 데이터 버퍼
        self.subscribed_channels = set()
        self.is_running = False
        
        # 새로운 전략 시스템용 EMA 기간 설정
        self.ema_periods = {
            'trend_fast': 150,        # 트렌드 확인용 150EMA
            'trend_slow': 200,        # 트렌드 확인용 200EMA
            'entry_fast': 20,         # 진입 신호용 20EMA
            'entry_slow': 50,         # 진입 신호용 50EMA
            'exit_fast_long': 20,     # 롱 청산용 20EMA
            'exit_slow_long': 100,    # 롱 청산용 100EMA
            'exit_fast_short': 100,   # 숏 청산용 100EMA  
            'exit_slow_short': 200    # 숏 청산용 200EMA
        }
    
    def _generate_signature(self, timestamp, method, request_path, body=""):
        """WebSocket 인증용 서명 생성"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf-8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _authenticate_private_ws(self):
        """Private WebSocket 인증"""
        timestamp = str(int(time.time()))
        signature = self._generate_signature(timestamp, 'GET', '/users/self/verify', '')
        
        auth_data = {
            "op": "login",
            "args": [{
                "apiKey": self.api_key,
                "passphrase": self.passphrase,
                "timestamp": timestamp,
                "sign": signature
            }]
        }
        
        if self.private_ws:
            self.private_ws.send(json.dumps(auth_data))
            print("Private WebSocket 인증 요청 전송")
    
    def on_public_message(self, ws, message):
        """Public WebSocket 메시지 처리"""
        try:
            data = json.loads(message)
            
            if 'event' in data:
                if data['event'] == 'subscribe':
                    print(f"구독 성공: {data.get('arg', {})}")
                elif data['event'] == 'error':
                    print(f"WebSocket 오류: {data}")
                return
            
            # 캔들스틱 데이터 처리
            if 'data' in data and data.get('arg', {}).get('channel') == 'candle30m':
                self._process_candle_data(data)
                
        except json.JSONDecodeError:
            print(f"JSON 파싱 오류: {message}")
        except Exception as e:
            print(f"메시지 처리 오류: {e}")
    
    def on_private_message(self, ws, message):
        """Private WebSocket 메시지 처리 (계좌 정보, 주문 상태 등)"""
        try:
            data = json.loads(message)
            
            if 'event' in data:
                if data['event'] == 'login':
                    if data.get('code') == '0':
                        print("Private WebSocket 인증 성공")
                        self._subscribe_private_channels()
                    else:
                        print(f"Private WebSocket 인증 실패: {data}")
                elif data['event'] == 'subscribe':
                    print(f"Private 채널 구독 성공: {data.get('arg', {})}")
                elif data['event'] == 'error':
                    print(f"Private WebSocket 오류: {data}")
                return
            
            # 계좌 정보 업데이트
            if 'data' in data:
                channel = data.get('arg', {}).get('channel')
                if channel == 'account':
                    self._process_account_update(data['data'])
                elif channel == 'positions':
                    self._process_position_update(data['data'])
                elif channel == 'orders':
                    self._process_order_update(data['data'])
                    
        except json.JSONDecodeError:
            print(f"Private JSON 파싱 오류: {message}")
        except Exception as e:
            print(f"Private 메시지 처리 오류: {e}")
    
    def _process_candle_data(self, data):
        """캔들스틱 데이터 처리 및 전략 신호 확인"""
        try:
            inst_id = data['arg']['instId']
            candle_data = data['data'][0]  # [timestamp, open, high, low, close, volume, volCcy, volCcyQuote, confirm]
            
            # 확정된 캔들만 처리 (confirm = "1")
            if candle_data[8] != "1":
                return
            
            # 캔들 데이터 파싱
            candle = {
                'timestamp': int(candle_data[0]),
                'open': float(candle_data[1]),
                'high': float(candle_data[2]),
                'low': float(candle_data[3]),
                'close': float(candle_data[4]),
                'volume': float(candle_data[5])
            }
            
            # 가격 버퍼에 추가
            if inst_id not in self.price_buffers:
                self.price_buffers[inst_id] = PriceBuffer(maxlen=250)  # EMA 계산을 위해 충분한 데이터
            
            self.price_buffers[inst_id].add_candle(candle)
            
            # 전략 신호 확인
            if self.strategy_manager:
                self._check_strategy_signals(inst_id)
                
            # 30분에 한 번만 로그 출력 (너무 많은 로그 방지)
            if int(time.time()) % 1800 == 0:  # 30분마다
                print(f"캔들 데이터 업데이트: {inst_id} - 종가: {candle['close']:.2f}")
            
        except Exception as e:
            print(f"캔들 데이터 처리 오류: {e}")
    
    def _check_strategy_signals(self, inst_id):
        """전략 신호 확인 및 실행"""
        try:
            df = self.price_buffers[inst_id].to_dataframe()
            if df is None or len(df) < max(self.ema_periods.values()) + 2:
                return
            
            # 새로운 전략 시스템용 데이터 생성
            latest_data = generate_strategy_data(df, self.ema_periods)
            if latest_data is None:
                return
            
            # 전략 매니저에게 신호 전달
            self.strategy_manager.process_signal(inst_id, latest_data)
            
        except Exception as e:
            print(f"전략 신호 확인 오류: {e}")
    
    def _process_account_update(self, account_data):
        """계좌 정보 업데이트 처리"""
        for account in account_data:
            # 5분마다만 로그 출력 (너무 빈번한 로그 방지)
            if int(time.time()) % 300 == 0:
                print(f"계좌 업데이트: 총 자산 {account.get('totalEq', 0)}")
    
    def _process_position_update(self, position_data):
        """포지션 정보 업데이트 처리"""
        for position in position_data:
            if float(position.get('pos', 0)) != 0:
                print(f"포지션 업데이트: {position.get('instId')} - "
                      f"크기: {position.get('pos')}, "
                      f"미실현 PnL: {position.get('upl')}")
    
    def _process_order_update(self, order_data):
        """주문 상태 업데이트 처리"""
        for order in order_data:
            print(f"주문 업데이트: {order.get('instId')} - "
                  f"상태: {order.get('state')}, "
                  f"체결량: {order.get('fillSz')}")
            
            # 전략 매니저에게 주문 완료 알림
            if self.strategy_manager and order.get('state') == 'filled':
                self.strategy_manager.on_order_filled(order)
    
    def _subscribe_private_channels(self):
        """Private 채널 구독"""
        private_channels = [
            {"channel": "account", "ccy": "USDT"},
            {"channel": "positions", "instType": "SWAP"},
            {"channel": "orders", "instType": "SWAP"}
        ]
        
        for channel in private_channels:
            subscribe_msg = {
                "op": "subscribe",
                "args": [channel]
            }
            if self.private_ws:
                self.private_ws.send(json.dumps(subscribe_msg))
                print(f"Private 채널 구독 요청: {channel}")
    
    def on_error(self, ws, error):
        """WebSocket 오류 처리"""
        print(f"WebSocket 오류: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket 연결 종료 처리"""
        print(f"WebSocket 연결 종료: {close_status_code} - {close_msg}")
        self.is_running = False
    
    def on_open(self, ws):
        """WebSocket 연결 성공 처리"""
        print("WebSocket 연결 성공")
        
        # Private WebSocket인 경우 인증 시작
        if ws == self.private_ws:
            self._authenticate_private_ws()
    
    def subscribe_kline_data(self, symbol, timeframe="30m"):
        """캔들스틱 데이터 구독"""
        if not self.public_ws:
            print("Public WebSocket이 연결되지 않았습니다")
            return False
        
        channel_key = f"candle{timeframe}:{symbol}"
        if channel_key in self.subscribed_channels:
            print(f"이미 구독 중: {symbol} {timeframe}")
            return True
        
        subscribe_msg = {
            "op": "subscribe",
            "args": [{
                "channel": f"candle{timeframe}",
                "instId": symbol
            }]
        }
        
        try:
            self.public_ws.send(json.dumps(subscribe_msg))
            self.subscribed_channels.add(channel_key)
            print(f"캔들스틱 구독 요청: {symbol} {timeframe}")
            return True
        except Exception as e:
            print(f"구독 요청 실패: {e}")
            return False
    
    def unsubscribe_kline_data(self, symbol, timeframe="30m"):
        """캔들스틱 데이터 구독 해제"""
        channel_key = f"candle{timeframe}:{symbol}"
        if channel_key not in self.subscribed_channels:
            print(f"구독하지 않은 채널: {symbol} {timeframe}")
            return
        
        unsubscribe_msg = {
            "op": "unsubscribe",
            "args": [{
                "channel": f"candle{timeframe}",
                "instId": symbol
            }]
        }
        
        try:
            self.public_ws.send(json.dumps(unsubscribe_msg))
            self.subscribed_channels.remove(channel_key)
            print(f"구독 해제: {symbol} {timeframe}")
        except Exception as e:
            print(f"구독 해제 실패: {e}")
    
    def start_public_ws(self):
        """Public WebSocket 시작"""
        websocket.enableTrace(False)
        self.public_ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_public_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        public_thread = threading.Thread(
            target=self.public_ws.run_forever,
            kwargs={
                'ping_interval': 30,
                'ping_timeout': 10
            }
        )
        public_thread.daemon = True
        public_thread.start()
        print("Public WebSocket 스레드 시작")
        
        return public_thread
    
    def start_private_ws(self):
        """Private WebSocket 시작"""
        websocket.enableTrace(False)
        self.private_ws = websocket.WebSocketApp(
            self.private_ws_url,
            on_message=self.on_private_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        private_thread = threading.Thread(
            target=self.private_ws.run_forever,
            kwargs={
                'ping_interval': 30,
                'ping_timeout': 10
            }
        )
        private_thread.daemon = True
        private_thread.start()
        print("Private WebSocket 스레드 시작")
        
        return private_thread
    
    def start_ws(self, symbols=None):
        """WebSocket 시작 (Public + Private)"""
        if symbols is None:
            symbols = ["BTC-USDT-SWAP"]  # 기본값
        
        self.is_running = True
        
        # Public WebSocket 시작
        public_thread = self.start_public_ws()
        time.sleep(2)  # 연결 대기
        
        # Private WebSocket 시작  
        private_thread = self.start_private_ws()
        time.sleep(2)  # 연결 대기
        
        # 캔들스틱 데이터 구독
        for symbol in symbols:
            self.subscribe_kline_data(symbol, "30m")
            time.sleep(0.5)  # 구독 간격
        
        print("WebSocket 시작 완료")
        return public_thread, private_thread
    
    def stop_ws(self):
        """WebSocket 중지"""
        self.is_running = False
        
        if self.public_ws:
            self.public_ws.close()
            print("Public WebSocket 중지")
        
        if self.private_ws:
            self.private_ws.close()
            print("Private WebSocket 중지")
        
        self.subscribed_channels.clear()
        print("WebSocket 중지 완료")
    
    def get_latest_price(self, symbol):
        """최신 가격 조회"""
        if symbol in self.price_buffers:
            df = self.price_buffers[symbol].to_dataframe()
            if df is not None and len(df) > 0:
                return df.iloc[-1]['close']
        return None
    
    def get_price_history(self, symbol, limit=100):
        """가격 히스토리 조회"""
        if symbol in self.price_buffers:
            df = self.price_buffers[symbol].to_dataframe()
            if df is not None:
                return df.tail(limit)
        return None


def start_ws():
    """WebSocket 시작 함수 (main.py에서 호출)"""
    # 전략 관리자와 함께 WebSocket 실행
    from strategy.strategy_manager import create_strategy_manager_from_preset
    
    print("=== 전략 시스템 시작 ===")
    
    # 사전 설정으로 전략 관리자 생성
    strategy_manager = create_strategy_manager_from_preset(
        preset_name='balanced',  # conservative, aggressive, balanced
        total_capital=10000,     # 총 자본 10,000 USDT
        symbols=['BTC-USDT-SWAP']
    )
    
    try:
        # 전략 시스템 시작
        strategy_manager.start(['BTC-USDT-SWAP'])
        
        print("=== 전략 시스템 실행 중 ===")
        print("종료하려면 Ctrl+C를 누르세요")
        print("상세 상태를 보려면 's'를 입력하고 Enter를 누르세요")
        
        # 메인 루프 (사용자 입력 처리)
        while strategy_manager.is_running:
            try:
                # 비블로킹 입력 확인
                import select
                import sys
                
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    user_input = input().strip().lower()
                    
                    if user_input == 's':
                        strategy_manager.print_detailed_status()
                    elif user_input == 'q':
                        print("사용자 요청으로 종료합니다.")
                        break
                    elif user_input == 'h':
                        print("명령어:")
                        print("  s: 상세 상태 출력")
                        print("  q: 종료")
                        print("  h: 도움말")
                
                time.sleep(1)
                
            except (EOFError, KeyboardInterrupt):
                break
            except ImportError:
                # Windows에서는 select가 없으므로 단순 대기
                time.sleep(60)  # 1분마다 체크
    
    except KeyboardInterrupt:
        print("\n사용자 중단 요청")
    except Exception as e:
        print(f"전략 시스템 실행 오류: {e}")
    finally:
        strategy_manager.stop()
        print("전략 시스템 종료")