# okx/websocket_handler.py
"""
수정된 WebSocket 핸들러 - strategy_manager 매개변수 지원
"""

import websocket
import json
import threading
import time
import hmac
import hashlib
import base64
import pandas as pd
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from config import API_KEY, API_SECRET, PASSPHRASE, EMA_PERIODS
from utils.price_buffer import PriceBuffer
from utils.logger import log_system, log_error, log_info

class WebSocketHandler:
    def __init__(self, strategy_manager=None):  # 매개변수 추가
        # WebSocket URLs
        self.public_ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.private_ws_url = "wss://ws.okx.com:8443/ws/v5/private"
        
        # WebSocket 연결
        self.public_ws = None
        self.private_ws = None
        self.strategy_manager = strategy_manager  # 전략 매니저 저장
        
        # 가격 데이터 버퍼 (EMA 계산용)
        self.price_buffers = {}
        self.is_running = False
        
        # 콜백 함수들
        self.on_price_callback: Optional[Callable] = None
        self.on_account_callback: Optional[Callable] = None
        self.on_position_callback: Optional[Callable] = None
        self.on_connection_callback: Optional[Callable] = None
        
        # 연결 상태 추적
        self.is_public_connected = False
        self.is_private_connected = False
        self.is_authenticated = False
        
        # 데이터 수신 통계
        self.received_messages = 0
        self.last_heartbeat = datetime.now()
        self.connection_start_time = None
        
        # 재연결 설정
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # 초
        self.current_reconnect_attempts = 0
        
        # 구독된 채널 추적
        self.subscribed_channels = []
        self.target_symbols = []
        
        log_system("WebSocket 핸들러 초기화 완료")
    
    def _generate_signature(self, timestamp, method, request_path, body=""):
        """WebSocket 인증용 서명 생성"""
        try:
            message = timestamp + method + request_path + body
            mac = hmac.new(
                bytes(API_SECRET, encoding='utf-8'),
                bytes(message, encoding='utf-8'),
                digestmod='sha256'
            )
            return base64.b64encode(mac.digest()).decode()
        except Exception as e:
            log_error("서명 생성 오류", e)
            return None
    
    def _authenticate_private_ws(self):
        """Private WebSocket 인증"""
        try:
            timestamp = str(int(time.time()))
            signature = self._generate_signature(
                timestamp, 'GET', '/users/self/verify', ''
            )
            
            if not signature:
                log_error("서명 생성 실패 - 인증 중단")
                return False
            
            auth_message = {
                "op": "login",
                "args": [{
                    "apiKey": API_KEY,
                    "passphrase": PASSPHRASE,
                    "timestamp": timestamp,
                    "sign": signature
                }]
            }
            
            self.private_ws.send(json.dumps(auth_message))
            log_system("Private WebSocket 인증 요청 전송")
            return True
            
        except Exception as e:
            log_error("Private WebSocket 인증 오류", e)
            return False
    
    def _on_public_message(self, ws, message):
        """Public WebSocket 메시지 처리"""
        try:
            data = json.loads(message)
            
            # 연결 성공 응답
            if 'event' in data and data['event'] == 'subscribe':
                log_system(f"채널 구독 성공: {data.get('arg', {}).get('channel')}")
                return
            
            # 실제 데이터 처리
            if 'data' in data:
                self._process_public_data(data)
                self.received_messages += 1
                self.last_heartbeat = datetime.now()
                
        except Exception as e:
            log_error("Public 메시지 처리 오류", e)
    
    def _on_private_message(self, ws, message):
        """Private WebSocket 메시지 처리"""
        try:
            data = json.loads(message)
            
            # 로그인 응답 처리
            if 'event' in data and data['event'] == 'login':
                if data.get('code') == '0':
                    self.is_authenticated = True
                    log_system("Private WebSocket 인증 성공")
                else:
                    log_error(f"Private WebSocket 인증 실패: {data.get('msg')}")
                return
            
            # 실제 데이터 처리
            if 'data' in data:
                self._process_private_data(data)
                
        except Exception as e:
            log_error("Private 메시지 처리 오류", e)
    
    def _process_public_data(self, data):
        """Public 데이터 처리"""
        try:
            arg = data.get('arg', {})
            channel = arg.get('channel')
            inst_id = arg.get('instId')
            
            if channel == 'tickers':
                self._process_ticker_data(inst_id, data['data'])
            elif channel == 'candle30m':
                self._process_candle_data(inst_id, data['data'])
            elif channel == 'books':
                self._process_orderbook_data(inst_id, data['data'])
                
        except Exception as e:
            log_error("Public 데이터 처리 오류", e)
    
    def _process_ticker_data(self, inst_id, ticker_data):
        """Ticker 데이터 처리 및 전략 신호 생성"""
        try:
            for ticker in ticker_data:
                # 가격 정보 추출
                current_price = float(ticker.get('last', 0))
                
                # 🔧 즉시 가격 정보 출력 (디버깅용)
                if current_price > 0:
                    change_24h = float(ticker.get('sodUtc8', 0))
                    volume_24h = float(ticker.get('vol24h', 0))
                    
                    change_str = f"{change_24h:+.2f}%" if change_24h != 0 else "0.00%"
                    
                    # 실시간 가격 정보 즉시 출력
                    print(f"💰 실시간 가격: {inst_id} = ${current_price:,.2f} ({change_str}) | 거래량: {volume_24h:,.0f}")
                    log_info(f"실시간 가격 수신: {inst_id} = ${current_price:,.2f} ({change_str})")
                
                price_info = {
                    'last': current_price,
                    'bid': float(ticker.get('bidPx', 0)),
                    'ask': float(ticker.get('askPx', 0)),
                    'vol24h': float(ticker.get('vol24h', 0)),
                    'change_24h': float(ticker.get('sodUtc8', 0)),
                    'high_24h': float(ticker.get('high24h', 0)),
                    'low_24h': float(ticker.get('low24h', 0)),
                    'timestamp': int(ticker.get('ts', time.time() * 1000))
                }
                
                # 외부 콜백 호출 (GUI 등)
                if self.on_price_callback:
                    self.on_price_callback(inst_id, current_price, price_info)
                
                # 전략 매니저에 실시간 데이터 전달
                if self.strategy_manager and current_price > 0:
                    strategy_data = {
                        'symbol': inst_id,
                        'close': current_price,
                        'timestamp': datetime.now(),
                        'volume': price_info['vol24h'],
                        'high': price_info['high_24h'],
                        'low': price_info['low_24h']
                    }
                    
                    # 전략 신호 처리
                    try:
                        signal_generated = self.strategy_manager.process_signal(inst_id, strategy_data)
                        if signal_generated:
                            log_info(f"📈 전략 신호 생성: {inst_id}")
                            print(f"🎯 전략 신호 발생: {inst_id} @ ${current_price:,.2f}")
                    except Exception as e:
                        log_error(f"전략 신호 처리 오류 ({inst_id})", e)
                
        except Exception as e:
            log_error(f"Ticker 데이터 처리 오류 ({inst_id})", e)
    
    def _process_candle_data(self, inst_id, candle_data):
        """캔들 데이터 처리"""
        try:
            for candle_raw in candle_data:
                # 확정된 캔들만 처리
                if len(candle_raw) > 8 and candle_raw[8] != "1":
                    continue
                
                candle = {
                    'timestamp': pd.to_datetime(int(candle_raw[0]), unit='ms'),
                    'open': float(candle_raw[1]),
                    'high': float(candle_raw[2]),
                    'low': float(candle_raw[3]),
                    'close': float(candle_raw[4]),
                    'volume': float(candle_raw[5])
                }
                
                # 가격 버퍼에 추가
                if inst_id not in self.price_buffers:
                    self.price_buffers[inst_id] = PriceBuffer(maxlen=300)
                
                self.price_buffers[inst_id].add_candle(candle)
                log_info(f"{inst_id} 새 캔들: ${candle['close']:.2f}")
                
        except Exception as e:
            log_error(f"캔들 데이터 처리 오류 ({inst_id})", e)
    
    def _process_orderbook_data(self, inst_id, orderbook_data):
        """호가창 데이터 처리"""
        try:
            for book in orderbook_data:
                asks = book.get('asks', [])
                bids = book.get('bids', [])
                
                if asks and bids:
                    best_ask = float(asks[0][0]) if asks[0] else 0
                    best_bid = float(bids[0][0]) if bids[0] else 0
                    spread = best_ask - best_bid
                    spread_pct = (spread / best_ask) * 100 if best_ask > 0 else 0
                    
                    # 스프레드가 비정상적으로 클 때만 로깅
                    if spread_pct > 0.1:
                        log_info(f"{inst_id} 넓은 스프레드: {spread_pct:.3f}%")
                
        except Exception as e:
            log_error(f"호가창 데이터 처리 오류 ({inst_id})", e)
    
    def _process_private_data(self, data):
        """Private 데이터 처리"""
        try:
            arg = data.get('arg', {})
            channel = arg.get('channel')
            
            if channel == 'account':
                self._process_account_data(data['data'])
            elif channel == 'positions':
                self._process_position_data(data['data'])
            elif channel == 'orders':
                self._process_order_data(data['data'])
                
        except Exception as e:
            log_error("Private 데이터 처리 오류", e)
    
    def _process_account_data(self, account_data):
        """계좌 데이터 처리"""
        try:
            account_info = {}
            
            for account in account_data:
                details = account.get('details', [])
                
                for detail in details:
                    currency = detail.get('ccy')
                    available = float(detail.get('availBal', 0))
                    total = float(detail.get('bal', 0))
                    frozen = float(detail.get('frozenBal', 0))
                    
                    account_info[currency] = {
                        'available': available,
                        'total': total,
                        'frozen': frozen
                    }
                
                # USDT 잔고 변화 로깅
                if 'USDT' in account_info:
                    usdt_balance = account_info['USDT']['available']
                    log_info(f"USDT 잔고 업데이트: ${usdt_balance:,.2f}")
            
            if self.on_account_callback:
                self.on_account_callback(account_info)
                
        except Exception as e:
            log_error("계좌 데이터 처리 오류", e)
    
    def _process_position_data(self, position_data):
        """포지션 데이터 처리"""
        try:
            positions = []
            
            for position in position_data:
                if float(position.get('pos', 0)) != 0:  # 활성 포지션만
                    pos_info = {
                        'instId': position.get('instId'),
                        'posSide': position.get('posSide'),
                        'pos': float(position.get('pos', 0)),
                        'avgPx': float(position.get('avgPx', 0)),
                        'markPx': float(position.get('markPx', 0)),
                        'upl': float(position.get('upl', 0)),
                        'uplRatio': float(position.get('uplRatio', 0)),
                        'last': float(position.get('last', 0)),
                        'lever': float(position.get('lever', 1))
                    }
                    positions.append(pos_info)
            
            if positions and self.on_position_callback:
                self.on_position_callback(positions)
                
        except Exception as e:
            log_error("포지션 데이터 처리 오류", e)
    
    def _process_order_data(self, order_data):
        """주문 데이터 처리"""
        try:
            for order in order_data:
                order_info = {
                    'instId': order.get('instId'),
                    'ordId': order.get('ordId'),
                    'side': order.get('side'),
                    'sz': float(order.get('sz', 0)),
                    'px': float(order.get('px', 0)),
                    'state': order.get('state'),
                    'fillSz': float(order.get('fillSz', 0)),
                    'avgPx': float(order.get('avgPx', 0))
                }
                
                log_info(f"주문 업데이트: {order_info['instId']} {order_info['side']} {order_info['state']}")
                
        except Exception as e:
            log_error("주문 데이터 처리 오류", e)
    
    def _on_error(self, ws, error):
        """WebSocket 오류 처리"""
        log_error("WebSocket 오류", error)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket 연결 종료 처리"""
        log_system(f"WebSocket 연결 종료: {close_status_code}")
        
        if self.is_running and self.current_reconnect_attempts < self.max_reconnect_attempts:
            self.current_reconnect_attempts += 1
            log_system(f"재연결 시도 {self.current_reconnect_attempts}/{self.max_reconnect_attempts}")
            time.sleep(self.reconnect_delay)
            self.start_websocket()
    
    def _on_open(self, ws):
        """WebSocket 연결 성공 처리"""
        if ws == self.public_ws:
            self.is_public_connected = True
            log_system("Public WebSocket 연결 성공")
        elif ws == self.private_ws:
            self.is_private_connected = True
            log_system("Private WebSocket 연결 성공")
            # Private 연결 시 자동 인증
            self._authenticate_private_ws()
        
        self.current_reconnect_attempts = 0  # 성공 시 재연결 카운터 리셋
    
    def start_websocket(self, symbols=None, channels=None):
        """WebSocket 연결 시작"""
        try:
            self.is_running = True
            self.target_symbols = symbols or ['BTC-USDT-SWAP']
            self.target_channels = channels or ["tickers", "candle30m"]
            
            log_system(f"WebSocket 연결 시작: {self.target_symbols} | 채널: {self.target_channels}")
            
            # Public WebSocket 연결
            self.public_ws = websocket.WebSocketApp(
                self.public_ws_url,
                on_message=self._on_public_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Private WebSocket 연결
            self.private_ws = websocket.WebSocketApp(
                self.private_ws_url,
                on_message=self._on_private_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # 별도 스레드에서 실행
            public_thread = threading.Thread(
                target=self.public_ws.run_forever,
                name="PublicWebSocket",
                daemon=True
            )
            
            private_thread = threading.Thread(
                target=self.private_ws.run_forever,
                name="PrivateWebSocket",
                daemon=True
            )
            
            public_thread.start()
            private_thread.start()
            
            # 연결 대기
            time.sleep(2)
            
            # 채널 구독
            self._subscribe_channels()
            
            return True
            
        except Exception as e:
            log_error("WebSocket 시작 오류", e)
            return False
    
    def _subscribe_channels(self):
        """채널 구독"""
        try:
            for symbol in self.target_symbols:
                # 🔧 구독 요청을 더 명확하게 로깅
                print(f"📡 구독 요청: {symbol} 실시간 가격 데이터")
                
                # Ticker 구독 (실시간 가격)
                ticker_sub = {
                    "op": "subscribe",
                    "args": [{
                        "channel": "tickers",
                        "instId": symbol
                    }]
                }
                
                # 30분 캔들 구독
                candle_sub = {
                    "op": "subscribe",
                    "args": [{
                        "channel": "candle30m",
                        "instId": symbol
                    }]
                }
                
                if self.public_ws:
                    self.public_ws.send(json.dumps(ticker_sub))
                    time.sleep(0.1)  # 요청 간격
                    self.public_ws.send(json.dumps(candle_sub))
                    time.sleep(0.1)
                    
                    log_system(f"📡 Public 채널 구독 요청 전송: {symbol}")
                    print(f"✅ 구독 요청 전송 완료: {symbol}")
            
            # Private 채널 구독 (인증 후)
            if self.is_authenticated and self.private_ws:
                account_sub = {
                    "op": "subscribe",
                    "args": [{"channel": "account"}]
                }
                
                position_sub = {
                    "op": "subscribe",
                    "args": [{"channel": "positions", "instType": "SWAP"}]
                }
                
                self.private_ws.send(json.dumps(account_sub))
                time.sleep(0.1)
                self.private_ws.send(json.dumps(position_sub))
                
                log_system("📡 Private 채널 구독 완료")
                print("✅ 계좌 및 포지션 채널 구독 완료")
                
        except Exception as e:
            log_error("채널 구독 오류", e)
            print(f"❌ 채널 구독 실패: {e}")
    
    def stop_websocket(self):
        """WebSocket 연결 중지"""
        try:
            self.is_running = False
            
            if self.public_ws:
                self.public_ws.close()
            
            if self.private_ws:
                self.private_ws.close()
            
            log_system("WebSocket 연결 종료")
            
        except Exception as e:
            log_error("WebSocket 종료 오류", e)
    
    def get_connection_status(self):
        """연결 상태 반환"""
        return {
            'public_connected': self.is_public_connected,
            'private_connected': self.is_private_connected,
            'authenticated': self.is_authenticated,
            'running': self.is_running,
            'messages_received': self.received_messages,
            'last_heartbeat': self.last_heartbeat
        }