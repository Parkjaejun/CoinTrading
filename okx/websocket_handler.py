# okx/websocket_handler_improved.py
"""
실제 OKX 데이터 연동을 위한 개선된 WebSocket 핸들러
- 실제 시장 데이터 수신
- 계좌 및 포지션 실시간 업데이트
- GUI와의 완전한 연동
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
from typing import Optional, Callable, Dict, Any
from config import API_KEY, API_SECRET, PASSPHRASE, EMA_PERIODS
from utils.price_buffer import PriceBuffer
from utils.logger import log_system, log_error

class ImprovedWebSocketHandler:
    def __init__(self, strategy_manager=None):
        # WebSocket URLs
        self.public_ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.private_ws_url = "wss://ws.okx.com:8443/ws/v5/private"
        
        # WebSocket 연결
        self.public_ws = None
        self.private_ws = None
        self.strategy_manager = strategy_manager
        
        # 가격 데이터 버퍼
        self.price_buffers = {}
        self.is_running = False
        
        # 실시간 데이터 콜백
        self.on_price_callback: Optional[Callable] = None
        self.on_account_callback: Optional[Callable] = None
        self.on_position_callback: Optional[Callable] = None
        
        # 연결 상태
        self.is_public_connected = False
        self.is_private_connected = False
        self.is_authenticated = False
        
        # 데이터 카운터
        self.received_messages = 0
        self.last_heartbeat = datetime.now()
        
        print("📡 개선된 WebSocket 핸들러 초기화")
    
    def _generate_signature(self, timestamp, method, request_path, body=""):
        """WebSocket 인증용 서명 생성"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(API_SECRET, encoding='utf-8'),
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
                "apiKey": API_KEY,
                "passphrase": PASSPHRASE,
                "timestamp": timestamp,
                "sign": signature
            }]
        }
        
        if self.private_ws:
            self.private_ws.send(json.dumps(auth_data))
            print("🔐 Private WebSocket 인증 요청 전송")
    
    def on_public_open(self, ws):
        """Public WebSocket 연결 성공"""
        print("✅ Public WebSocket 연결 성공")
        self.is_public_connected = True
    
    def on_private_open(self, ws):
        """Private WebSocket 연결 성공"""
        print("✅ Private WebSocket 연결 성공")
        self.is_private_connected = True
        # 인증 시작
        self._authenticate_private_ws()
    
    def on_public_message(self, ws, message):
        """Public 메시지 처리 (시장 데이터)"""
        try:
            data = json.loads(message)
            self.received_messages += 1
            
            # 이벤트 메시지 처리
            if 'event' in data:
                if data['event'] == 'subscribe':
                    channel = data.get('arg', {}).get('channel', 'unknown')
                    inst_id = data.get('arg', {}).get('instId', 'unknown')
                    print(f"✅ Public 구독 성공: {channel} - {inst_id}")
                elif data['event'] == 'error':
                    print(f"❌ Public WebSocket 오류: {data}")
                return
            
            # 데이터 처리
            if 'data' in data and 'arg' in data:
                self._process_public_data(data)
                
        except Exception as e:
            log_error("Public 메시지 처리 오류", e)
    
    def on_private_message(self, ws, message):
        """Private 메시지 처리 (계좌/포지션 데이터)"""
        try:
            data = json.loads(message)
            self.received_messages += 1
            
            # 이벤트 메시지 처리
            if 'event' in data:
                if data['event'] == 'login':
                    if data.get('code') == '0':
                        print("✅ Private WebSocket 인증 성공")
                        self.is_authenticated = True
                        self._subscribe_private_channels()
                    else:
                        print(f"❌ Private WebSocket 인증 실패: {data}")
                elif data['event'] == 'subscribe':
                    channel = data.get('arg', {}).get('channel', 'unknown')
                    print(f"✅ Private 구독 성공: {channel}")
                elif data['event'] == 'error':
                    print(f"❌ Private WebSocket 오류: {data}")
                return
            
            # 데이터 처리
            if 'data' in data and 'arg' in data:
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
                # 실시간 Ticker 데이터
                self._process_ticker_data(inst_id, data['data'])
            elif channel == 'candle30m':
                # 30분 캔들 데이터
                self._process_candle_data(inst_id, data['data'])
            elif channel == 'books5':
                # 호가창 데이터 (선택적)
                self._process_orderbook_data(inst_id, data['data'])
                
        except Exception as e:
            log_error("Public 데이터 처리 오류", e)
    
    def _process_private_data(self, data):
        """Private 데이터 처리"""
        try:
            arg = data.get('arg', {})
            channel = arg.get('channel')
            
            if channel == 'account':
                # 계좌 정보 업데이트
                self._process_account_data(data['data'])
            elif channel == 'positions':
                # 포지션 정보 업데이트
                self._process_position_data(data['data'])
            elif channel == 'orders':
                # 주문 정보 업데이트
                self._process_order_data(data['data'])
                
        except Exception as e:
            log_error("Private 데이터 처리 오류", e)
    
    def _process_ticker_data(self, inst_id, ticker_data):
        """Ticker 데이터 처리"""
        try:
            for ticker in ticker_data:
                price_info = {
                    'last': float(ticker.get('last', 0)),
                    'bid': float(ticker.get('bidPx', 0)),
                    'ask': float(ticker.get('askPx', 0)),
                    'vol24h': float(ticker.get('vol24h', 0)),
                    'change_24h': float(ticker.get('changePx24h', 0)),
                    'high_24h': float(ticker.get('high24h', 0)),
                    'low_24h': float(ticker.get('low24h', 0)),
                    'timestamp': ticker.get('ts')
                }
                
                # GUI 콜백 호출
                if self.on_price_callback:
                    self.on_price_callback(inst_id, price_info)
                
                # 전략 매니저에 전달 (있는 경우)
                if self.strategy_manager:
                    strategy_data = {
                        'symbol': inst_id,
                        'close': price_info['last'],
                        'timestamp': datetime.now()
                    }
                    self.strategy_manager.process_signal(inst_id, strategy_data)
                
                print(f"💰 {inst_id}: ${price_info['last']:,.2f} (Vol: {price_info['vol24h']:,.0f})")
                
        except Exception as e:
            log_error(f"Ticker 데이터 처리 오류 ({inst_id})", e)
    
    def _process_candle_data(self, inst_id, candle_data):
        """캔들 데이터 처리"""
        try:
            for candle_raw in candle_data:
                # 확정된 캔들만 처리
                if candle_raw[8] != "1":
                    continue
                
                candle = {
                    'timestamp': pd.to_datetime(int(candle_raw[0]), unit='ms'),
                    'open': float(candle_raw[1]),
                    'high': float(candle_raw[2]),
                    'low': float(candle_raw[3]),
                    'close': float(candle_raw[4]),
                    'volume': float(candle_raw[5])
                }
                
                # 버퍼에 추가
                if inst_id not in self.price_buffers:
                    self.price_buffers[inst_id] = PriceBuffer(maxlen=300)
                
                self.price_buffers[inst_id].add_candle(candle)
                
                # 전략 신호 생성
                if self.strategy_manager:
                    self._generate_strategy_signals(inst_id)
                
                print(f"📊 {inst_id} 캔들: ${candle['close']:,.2f}")
                
        except Exception as e:
            log_error(f"캔들 데이터 처리 오류 ({inst_id})", e)
    
    def _process_orderbook_data(self, inst_id, orderbook_data):
        """호가창 데이터 처리 (선택적)"""
        try:
            for book in orderbook_data:
                asks = book.get('asks', [])
                bids = book.get('bids', [])
                
                if asks and bids:
                    best_ask = float(asks[0][0]) if asks[0] else 0
                    best_bid = float(bids[0][0]) if bids[0] else 0
                    spread = best_ask - best_bid
                    
                    print(f"📖 {inst_id} 호가: Bid ${best_bid:.2f} | Ask ${best_ask:.2f} | Spread ${spread:.2f}")
                
        except Exception as e:
            log_error(f"호가창 데이터 처리 오류 ({inst_id})", e)
    
    def _process_account_data(self, account_data):
        """계좌 데이터 처리"""
        try:
            for account in account_data:
                details = account.get('details', [])
                
                account_info = {}
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
                
                # GUI 콜백 호출
                if self.on_account_callback:
                    self.on_account_callback(account_info)
                
                print(f"💳 계좌 업데이트: {len(account_info)}개 통화")
                
        except Exception as e:
            log_error("계좌 데이터 처리 오류", e)
    
    def _process_position_data(self, position_data):
        """포지션 데이터 처리"""
        try:
            positions = []
            
            for pos_data in position_data:
                if float(pos_data.get('pos', 0)) != 0:  # 포지션이 있는 것만
                    position = {
                        'instrument': pos_data.get('instId'),
                        'position_side': pos_data.get('posSide'),
                        'size': float(pos_data.get('pos', 0)),
                        'avg_price': float(pos_data.get('avgPx', 0)),
                        'mark_price': float(pos_data.get('markPx', 0)),
                        'unrealized_pnl': float(pos_data.get('upl', 0)),
                        'unrealized_pnl_ratio': float(pos_data.get('uplRatio', 0)),
                        'margin': float(pos_data.get('margin', 0)),
                        'leverage': float(pos_data.get('lever', 0)),
                        'last_trade_id': pos_data.get('tradeId')
                    }
                    positions.append(position)
            
            # GUI 콜백 호출
            if self.on_position_callback:
                self.on_position_callback(positions)
            
            print(f"📊 포지션 업데이트: {len(positions)}개")
            
        except Exception as e:
            log_error("포지션 데이터 처리 오류", e)
    
    def _process_order_data(self, order_data):
        """주문 데이터 처리"""
        try:
            for order in order_data:
                order_id = order.get('ordId')
                inst_id = order.get('instId')
                state = order.get('state')
                side = order.get('side')
                
                print(f"📋 주문 업데이트: {inst_id} {side} {state} (ID: {order_id})")
                
        except Exception as e:
            log_error("주문 데이터 처리 오류", e)
    
    def _generate_strategy_signals(self, symbol):
        """전략 신호 생성"""
        try:
            df = self.price_buffers[symbol].to_dataframe()
            if df is None or len(df) < max(EMA_PERIODS.values()) + 2:
                return
            
            # 전략용 데이터 생성
            from utils.data_generator import generate_strategy_data
            strategy_data = generate_strategy_data(df, EMA_PERIODS)
            if strategy_data is None:
                return
            
            # 전략 매니저에게 신호 전달
            if self.strategy_manager:
                self.strategy_manager.process_signal(symbol, strategy_data)
                
        except Exception as e:
            log_error(f"전략 신호 생성 오류 ({symbol})", e)
    
    def _subscribe_private_channels(self):
        """Private 채널 구독"""
        if not self.is_authenticated:
            print("⚠️ 인증되지 않음 - Private 채널 구독 건너뜀")
            return
        
        channels = [
            {"channel": "account", "ccy": "USDT"},
            {"channel": "positions", "instType": "SWAP"},
            {"channel": "orders", "instType": "SWAP"}
        ]
        
        for channel in channels:
            subscribe_msg = {"op": "subscribe", "args": [channel]}
            if self.private_ws:
                self.private_ws.send(json.dumps(subscribe_msg))
                print(f"📡 Private 채널 구독: {channel['channel']}")
    
    def subscribe_public_channels(self, symbols):
        """Public 채널 구독"""
        if not self.is_public_connected:
            print("⚠️ Public WebSocket 미연결")
            return False
        
        channels = []
        
        for symbol in symbols:
            # Ticker 데이터 (실시간 가격)
            channels.append({
                "channel": "tickers",
                "instId": symbol
            })
            
            # 30분 캔들 데이터
            channels.append({
                "channel": "candle30m",
                "instId": symbol
            })
            
            # 호가창 데이터 (선택적)
            channels.append({
                "channel": "books5",
                "instId": symbol
            })
        
        # 구독 요청
        for channel in channels:
            subscribe_msg = {"op": "subscribe", "args": [channel]}
            try:
                self.public_ws.send(json.dumps(subscribe_msg))
                print(f"📡 Public 채널 구독: {channel['channel']} - {channel['instId']}")
                time.sleep(0.1)  # 요청 간격
            except Exception as e:
                log_error(f"채널 구독 실패: {channel}", e)
        
        return True
    
    def on_error(self, ws, error):
        """WebSocket 오류 처리"""
        print(f"❌ WebSocket 오류: {error}")
        log_error("WebSocket 오류", error)
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket 연결 종료"""
        if ws == self.public_ws:
            print(f"📴 Public WebSocket 연결 종료: {close_status_code}")
            self.is_public_connected = False
        elif ws == self.private_ws:
            print(f"📴 Private WebSocket 연결 종료: {close_status_code}")
            self.is_private_connected = False
            self.is_authenticated = False
        
        self.is_running = False
    
    def start_ws(self, symbols):
        """WebSocket 시작"""
        if self.is_running:
            print("⚠️ WebSocket 이미 실행 중")
            return
        
        self.is_running = True
        print(f"🚀 개선된 WebSocket 시작: {symbols}")
        
        try:
            # Public WebSocket 시작
            self.public_ws = websocket.WebSocketApp(
                self.public_ws_url,
                on_message=self.on_public_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_public_open
            )
            
            public_thread = threading.Thread(
                target=self.public_ws.run_forever,
                kwargs={'ping_interval': 30, 'ping_timeout': 10},
                name="PublicWebSocket",
                daemon=True
            )
            public_thread.start()
            
            # Private WebSocket 시작
            self.private_ws = websocket.WebSocketApp(
                self.private_ws_url,
                on_message=self.on_private_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_private_open
            )
            
            private_thread = threading.Thread(
                target=self.private_ws.run_forever,
                kwargs={'ping_interval': 30, 'ping_timeout': 10},
                name="PrivateWebSocket",
                daemon=True
            )
            private_thread.start()
            
            # 연결 대기
            time.sleep(3)
            
            # Public 채널 구독
            if self.is_public_connected:
                self.subscribe_public_channels(symbols)
            else:
                print("❌ Public WebSocket 연결 실패")
            
            print("✅ 개선된 WebSocket 시작 완료")
            return public_thread, private_thread
            
        except Exception as e:
            log_error("WebSocket 시작 오류", e)
            return None, None
    
    def stop_ws(self):
        """WebSocket 중지"""
        print("🛑 WebSocket 중지 중...")
        self.is_running = False
        
        if self.public_ws:
            self.public_ws.close()
            self.is_public_connected = False
        
        if self.private_ws:
            self.private_ws.close()
            self.is_private_connected = False
            self.is_authenticated = False
        
        print("✅ WebSocket 중지 완료")
    
    def get_connection_status(self):
        """연결 상태 정보"""
        return {
            'is_running': self.is_running,
            'public_connected': self.is_public_connected,
            'private_connected': self.is_private_connected,
            'authenticated': self.is_authenticated,
            'received_messages': self.received_messages,
            'last_heartbeat': self.last_heartbeat
        }
    
    def get_latest_price(self, symbol):
        """최신 가격 조회"""
        if symbol in self.price_buffers:
            df = self.price_buffers[symbol].to_dataframe()
            if df is not None and len(df) > 0:
                return df.iloc[-1]['close']
        return None
    
    def set_price_callback(self, callback: Callable):
        """가격 업데이트 콜백 설정"""
        self.on_price_callback = callback
    
    def set_account_callback(self, callback: Callable):
        """계좌 업데이트 콜백 설정"""
        self.on_account_callback = callback
    
    def set_position_callback(self, callback: Callable):
        """포지션 업데이트 콜백 설정"""
        self.on_position_callback = callback

# 편의를 위한 래퍼 클래스 (기존 코드와의 호환성)
class WebSocketHandler(ImprovedWebSocketHandler):
    """기존 코드와의 호환성을 위한 래퍼"""
    pass