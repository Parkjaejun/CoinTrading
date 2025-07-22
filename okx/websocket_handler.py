"""
단순화된 WebSocket 핸들러
불필요한 기능 제거하고 핵심 기능만 유지
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
from config import API_KEY, API_SECRET, PASSPHRASE, EMA_PERIODS
from utils.price_buffer import PriceBuffer
from utils.data_generator import generate_strategy_data

class WebSocketHandler:
    def __init__(self, strategy_manager=None):
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.private_ws_url = "wss://ws.okx.com:8443/ws/v5/private"
        
        self.public_ws = None
        self.private_ws = None
        self.strategy_manager = strategy_manager
        
        # 가격 데이터 버퍼
        self.price_buffers = {}
        self.is_running = False
        
        print("📡 WebSocket 핸들러 초기화")
    
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
    
    def on_public_message(self, ws, message):
        """Public 메시지 처리 (캔들 데이터)"""
        try:
            data = json.loads(message)
            
            # 이벤트 메시지 처리
            if 'event' in data:
                if data['event'] == 'subscribe':
                    print(f"✅ 구독 성공: {data.get('arg', {}).get('instId')}")
                elif data['event'] == 'error':
                    print(f"❌ WebSocket 오류: {data}")
                return
            
            # 캔들 데이터 처리
            if 'data' in data and data.get('arg', {}).get('channel') == 'candle30m':
                self._process_candle_data(data)
                
        except Exception as e:
            print(f"❌ Public 메시지 처리 오류: {e}")
    
    def on_private_message(self, ws, message):
        """Private 메시지 처리 (계좌 정보)"""
        try:
            data = json.loads(message)
            
            if 'event' in data:
                if data['event'] == 'login' and data.get('code') == '0':
                    print("✅ Private WebSocket 인증 성공")
                    self._subscribe_private_channels()
                return
            
            # 포지션 업데이트 등 처리 (필요시 구현)
                
        except Exception as e:
            print(f"❌ Private 메시지 처리 오류: {e}")
    
    def _process_candle_data(self, data):
        """캔들 데이터 처리 및 전략 신호 생성"""
        try:
            inst_id = data['arg']['instId']
            candle_raw = data['data'][0]
            
            # 확정된 캔들만 처리
            if candle_raw[8] != "1":
                return
            
            # 캔들 데이터 파싱
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
                self.price_buffers[inst_id] = PriceBuffer(maxlen=250)
            
            self.price_buffers[inst_id].add_candle(candle)
            
            # 전략 신호 생성
            if self.strategy_manager:
                self._generate_strategy_signals(inst_id)
                
        except Exception as e:
            print(f"❌ 캔들 데이터 처리 오류: {e}")
    
    def _generate_strategy_signals(self, symbol):
        """전략 신호 생성"""
        try:
            df = self.price_buffers[symbol].to_dataframe()
            if df is None or len(df) < max(EMA_PERIODS.values()) + 2:
                return
            
            # 전략용 데이터 생성
            strategy_data = generate_strategy_data(df)
            if strategy_data is None:
                return
            
            # 전략 매니저에게 신호 전달
            self.strategy_manager.process_signal(symbol, strategy_data)
                
        except Exception as e:
            print(f"❌ 전략 신호 생성 오류 ({symbol}): {e}")
    
    def _subscribe_private_channels(self):
        """Private 채널 구독 (간소화)"""
        channels = [
            {"channel": "account", "ccy": "USDT"},
            {"channel": "positions", "instType": "SWAP"}
        ]
        
        for channel in channels:
            subscribe_msg = {"op": "subscribe", "args": [channel]}
            if self.private_ws:
                self.private_ws.send(json.dumps(subscribe_msg))
    
    def on_error(self, ws, error):
        """WebSocket 오류 처리"""
        print(f"❌ WebSocket 오류: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket 연결 종료"""
        print(f"📴 WebSocket 연결 종료: {close_status_code}")
        self.is_running = False
    
    def on_open(self, ws):
        """WebSocket 연결 성공"""
        if ws == self.private_ws:
            self._authenticate_private_ws()
    
    def subscribe_candle_data(self, symbol):
        """캔들 데이터 구독"""
        if not self.public_ws:
            print("❌ Public WebSocket 미연결")
            return False
        
        subscribe_msg = {
            "op": "subscribe",
            "args": [{
                "channel": "candle30m",
                "instId": symbol
            }]
        }
        
        try:
            self.public_ws.send(json.dumps(subscribe_msg))
            print(f"📊 캔들 데이터 구독 요청: {symbol}")
            return True
        except Exception as e:
            print(f"❌ 구독 요청 실패: {e}")
            return False
    
    def start_ws(self, symbols):
        """WebSocket 시작"""
        if self.is_running:
            print("⚠️ WebSocket 이미 실행 중")
            return
        
        self.is_running = True
        print(f"🚀 WebSocket 시작: {symbols}")
        
        # Public WebSocket 시작
        self.public_ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_public_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        public_thread = threading.Thread(
            target=self.public_ws.run_forever,
            kwargs={'ping_interval': 30, 'ping_timeout': 10}
        )
        public_thread.daemon = True
        public_thread.start()
        
        # Private WebSocket 시작
        self.private_ws = websocket.WebSocketApp(
            self.private_ws_url,
            on_message=self.on_private_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        private_thread = threading.Thread(
            target=self.private_ws.run_forever,
            kwargs={'ping_interval': 30, 'ping_timeout': 10}
        )
        private_thread.daemon = True
        private_thread.start()
        
        # 연결 대기
        time.sleep(3)
        
        # 캔들 데이터 구독
        for symbol in symbols:
            self.subscribe_candle_data(symbol)
            time.sleep(0.5)
        
        print("✅ WebSocket 시작 완료")
        return public_thread, private_thread
    
    def stop_ws(self):
        """WebSocket 중지"""
        print("🛑 WebSocket 중지 중...")
        self.is_running = False
        
        if self.public_ws:
            self.public_ws.close()
        if self.private_ws:
            self.private_ws.close()
        
        print("✅ WebSocket 중지 완료")
    
    def get_latest_price(self, symbol):
        """최신 가격 조회"""
        if symbol in self.price_buffers:
            df = self.price_buffers[symbol].to_dataframe()
            if df is not None and len(df) > 0:
                return df.iloc[-1]['close']
        return None
            