# websocket_handler_fixed.py
"""
수정된 OKX WebSocket 핸들러
- 올바른 채널 이름 사용
- 간소화된 구독 방식
- 안정적인 연결 관리
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
from utils.logger import log_system, log_error, log_info

class FixedWebSocketHandler:
    def __init__(self, strategy_manager=None):
        # WebSocket URLs
        self.public_ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.private_ws_url = "wss://ws.okx.com:8443/ws/v5/private"
        
        # WebSocket 연결
        self.public_ws = None
        self.private_ws = None
        self.strategy_manager = strategy_manager
        
        # 상태 관리
        self.is_running = False
        self.is_public_connected = False
        self.is_private_connected = False
        self.is_authenticated = False
        
        # 콜백 함수들
        self.on_price_callback: Optional[Callable] = None
        self.on_account_callback: Optional[Callable] = None
        self.on_position_callback: Optional[Callable] = None
        self.on_connection_callback: Optional[Callable] = None
        
        # 데이터 수신 통계
        self.received_messages = 0
        self.last_heartbeat = datetime.now()
        self.connection_start_time = None
        
        # 구독 대상
        self.target_symbols = []
        self.subscribed_channels = []
        
        # 재연결 설정
        self.max_reconnect_attempts = 3
        self.reconnect_delay = 5
        self.current_reconnect_attempts = 0
        
        log_system("🔗 수정된 WebSocket 핸들러 초기화")
    
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
            signature = self._generate_signature(timestamp, 'GET', '/users/self/verify', '')
            
            if not signature:
                log_error("Private WebSocket 서명 생성 실패")
                return
            
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
                log_system("🔐 Private WebSocket 인증 요청 전송")
                
        except Exception as e:
            log_error("Private WebSocket 인증 실패", e)
    
    def on_public_open(self, ws):
        """Public WebSocket 연결 성공"""
        log_system("✅ Public WebSocket 연결 성공")
        self.is_public_connected = True
        self.connection_start_time = datetime.now()
        self.current_reconnect_attempts = 0
        
        if self.on_connection_callback:
            self.on_connection_callback(True)
        
        # 채널 구독
        if self.target_symbols:
            self._subscribe_public_channels()
    
    def on_private_open(self, ws):
        """Private WebSocket 연결 성공"""
        log_system("✅ Private WebSocket 연결 성공")
        self.is_private_connected = True
        
        # 인증 시작
        self._authenticate_private_ws()
    
    def on_public_message(self, ws, message):
        """Public 메시지 처리"""
        try:
            data = json.loads(message)
            self.received_messages += 1
            self.last_heartbeat = datetime.now()
            
            # 이벤트 메시지 처리
            if 'event' in data:
                self._handle_public_event(data)
                return
            
            # 실제 데이터 처리
            if 'data' in data and 'arg' in data:
                self._process_public_data(data)
                
        except json.JSONDecodeError:
            log_error("Public 메시지 JSON 파싱 오류")
        except Exception as e:
            log_error("Public 메시지 처리 오류", e)
    
    def on_private_message(self, ws, message):
        """Private 메시지 처리"""
        try:
            data = json.loads(message)
            self.received_messages += 1
            
            # 이벤트 메시지 처리
            if 'event' in data:
                self._handle_private_event(data)
                return
            
            # 실제 데이터 처리
            if 'data' in data and 'arg' in data:
                self._process_private_data(data)
                
        except json.JSONDecodeError:
            log_error("Private 메시지 JSON 파싱 오류")
        except Exception as e:
            log_error("Private 메시지 처리 오류", e)
    
    def _handle_public_event(self, data):
        """Public 이벤트 처리"""
        event = data.get('event')
        
        if event == 'subscribe':
            channel = data.get('arg', {}).get('channel', 'unknown')
            inst_id = data.get('arg', {}).get('instId', 'unknown')
            log_system(f"✅ Public 구독 성공: {channel} - {inst_id}")
            
        elif event == 'error':
            error_msg = data.get('msg', 'Unknown error')
            error_code = data.get('code', 'Unknown')
            log_error(f"❌ Public WebSocket 오류: {error_code} - {error_msg}")
            
            # 특정 오류에 대한 처리
            if "doesn't exist" in error_msg:
                log_error("채널이 존재하지 않습니다. 채널명을 확인하세요.")
                
        elif event == 'ping':
            # Ping에 대한 Pong 응답
            if self.public_ws:
                self.public_ws.send(json.dumps({"event": "pong"}))
    
    def _handle_private_event(self, data):
        """Private 이벤트 처리"""
        event = data.get('event')
        
        if event == 'login':
            if data.get('code') == '0':
                log_system("✅ Private WebSocket 인증 성공")
                self.is_authenticated = True
                self._subscribe_private_channels()
            else:
                error_msg = data.get('msg', 'Unknown error')
                log_error(f"❌ Private WebSocket 인증 실패: {error_msg}")
                
                # Passphrase 오류 처리
                if "passphrase" in error_msg.lower():
                    log_error("Passphrase가 잘못되었습니다. config.py를 확인하세요.")
                
        elif event == 'subscribe':
            channel = data.get('arg', {}).get('channel', 'unknown')
            log_system(f"✅ Private 구독 성공: {channel}")
            
        elif event == 'error':
            error_msg = data.get('msg', 'Unknown error')
            error_code = data.get('code', 'Unknown')
            log_error(f"❌ Private WebSocket 오류: {error_code} - {error_msg}")
    
    def _process_public_data(self, data):
        """Public 데이터 처리"""
        try:
            arg = data.get('arg', {})
            channel = arg.get('channel')
            inst_id = arg.get('instId')
            
            if channel == 'tickers':
                # 실시간 Ticker 데이터
                self._process_ticker_data(inst_id, data['data'])
                
            elif channel in ['candle30M', 'candle30m']:  # 두 가지 형식 모두 지원
                # 30분 캔들 데이터
                self._process_candle_data(inst_id, data['data'])
                
            elif channel == 'books5':
                # 호가창 데이터
                self._process_orderbook_data(inst_id, data['data'])
                
            elif channel == 'books':
                # 호가창 데이터 (다른 형식)
                self._process_orderbook_data(inst_id, data['data'])
                
        except Exception as e:
            log_error("Public 데이터 처리 오류", e)
    
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
    
    def _process_ticker_data(self, inst_id, ticker_data):
        """Ticker 데이터 처리"""
        try:
            for ticker in ticker_data:
                current_price = float(ticker.get('last', 0))
                
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
                
                # 외부 콜백 호출
                if self.on_price_callback:
                    self.on_price_callback(inst_id, current_price, price_info)
                
                # 전략 매니저에 데이터 전달
                if self.strategy_manager and current_price > 0:
                    strategy_data = {
                        'symbol': inst_id,
                        'close': current_price,
                        'timestamp': datetime.now(),
                        'volume': price_info['vol24h'],
                        'high': price_info['high_24h'],
                        'low': price_info['low_24h']
                    }
                    
                    try:
                        signal_generated = self.strategy_manager.process_signal(inst_id, strategy_data)
                        if signal_generated:
                            log_info(f"📈 전략 신호 생성: {inst_id}")
                    except Exception as e:
                        log_error(f"전략 신호 처리 오류 ({inst_id})", e)
                
                # 주기적 로깅 (매 100번째마다)
                if self.received_messages % 100 == 0:
                    change_24h = price_info['change_24h']
                    change_str = f"{change_24h:+.2f}%" if change_24h != 0 else "0.00%"
                    log_info(f"💰 {inst_id}: ${current_price:,.2f} ({change_str})")
                
        except Exception as e:
            log_error(f"Ticker 데이터 처리 오류 ({inst_id})", e)
    
    def _process_candle_data(self, inst_id, candle_data):
        """캔들 데이터 처리"""
        try:
            for candle_raw in candle_data:
                # 확정된 캔들만 처리 (confirm = "1")
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
                
                log_info(f"📊 {inst_id} 새 캔들: O:${candle['open']:.2f} C:${candle['close']:.2f}")
                
                # 전략 매니저에 캔들 데이터 전달
                if self.strategy_manager:
                    try:
                        self.strategy_manager.process_candle(inst_id, candle)
                    except Exception as e:
                        log_error(f"캔들 전략 처리 오류 ({inst_id})", e)
                
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
                    
                    # 비정상적으로 큰 스프레드만 로깅
                    if spread_pct > 0.1:  # 0.1% 이상
                        log_info(f"📖 {inst_id} 넓은 스프레드: {spread_pct:.3f}%")
                
        except Exception as e:
            log_error(f"호가창 데이터 처리 오류 ({inst_id})", e)
    
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
                
                # 중요한 잔고 변화만 로깅
                if 'USDT' in account_info:
                    usdt_balance = account_info['USDT']['available']
                    log_info(f"💳 USDT 잔고 업데이트: ${usdt_balance:,.2f}")
            
            if self.on_account_callback:
                self.on_account_callback(account_info)
                
        except Exception as e:
            log_error("계좌 데이터 처리 오류", e)
    
    def _process_position_data(self, position_data):
        """포지션 데이터 처리"""
        try:
            positions = []
            total_unrealized_pnl = 0
            
            for pos_data in position_data:
                position_size = float(pos_data.get('pos', 0))
                
                if position_size != 0:  # 포지션이 있는 것만
                    unrealized_pnl = float(pos_data.get('upl', 0))
                    total_unrealized_pnl += unrealized_pnl
                    
                    position = {
                        'instrument': pos_data.get('instId'),
                        'position_side': pos_data.get('posSide'),
                        'size': position_size,
                        'avg_price': float(pos_data.get('avgPx', 0)),
                        'mark_price': float(pos_data.get('markPx', 0)),
                        'unrealized_pnl': unrealized_pnl,
                        'unrealized_pnl_ratio': float(pos_data.get('uplRatio', 0)),
                        'margin': float(pos_data.get('margin', 0)),
                        'leverage': float(pos_data.get('lever', 0))
                    }
                    positions.append(position)
            
            # 포지션 변화가 있을 때만 로깅
            if positions:
                log_info(f"📊 포지션 업데이트: {len(positions)}개 | 총 미실현 PnL: ${total_unrealized_pnl:+,.2f}")
            
            if self.on_position_callback:
                self.on_position_callback(positions)
                
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
                size = float(order.get('sz', 0))
                filled_size = float(order.get('fillSz', 0))
                
                # 중요한 주문 상태 변화만 로깅
                if state in ['filled', 'canceled', 'live']:
                    log_info(f"📋 주문 {state}: {inst_id} {side} {size:.6f} (체결: {filled_size:.6f})")
                
        except Exception as e:
            log_error("주문 데이터 처리 오류", e)
    
    def _subscribe_public_channels(self):
        """Public 채널 구독 (안전한 채널만)"""
        if not self.is_public_connected or not self.target_symbols:
            return
        
        channels = []
        
        for symbol in self.target_symbols:
            # 안전하게 작동하는 채널들만 구독
            channels.extend([
                {"channel": "tickers", "instId": symbol},
                {"channel": "books5", "instId": symbol}
            ])
        
        # 구독 요청
        for channel in channels:
            subscribe_msg = {"op": "subscribe", "args": [channel]}
            try:
                if self.public_ws:
                    self.public_ws.send(json.dumps(subscribe_msg))
                    log_system(f"📡 Public 채널 구독: {channel['channel']} - {channel['instId']}")
                    time.sleep(0.1)  # 요청 간격
                    
                    self.subscribed_channels.append(channel)
                    
            except Exception as e:
                log_error(f"Public 채널 구독 실패: {channel}", e)
    
    def _subscribe_private_channels(self):
        """Private 채널 구독"""
        if not self.is_authenticated:
            log_error("⚠️ 인증되지 않음 - Private 채널 구독 불가")
            return
        
        channels = [
            {"channel": "account", "ccy": "USDT"},
            {"channel": "positions", "instType": "SWAP"},
            {"channel": "orders", "instType": "SWAP"}
        ]
        
        for channel in channels:
            subscribe_msg = {"op": "subscribe", "args": [channel]}
            try:
                if self.private_ws:
                    self.private_ws.send(json.dumps(subscribe_msg))
                    log_system(f"📡 Private 채널 구독: {channel['channel']}")
                    time.sleep(0.1)
            except Exception as e:
                log_error(f"Private 채널 구독 실패: {channel}", e)
    
    def subscribe_public_channels(self, symbols):
        """외부에서 호출되는 Public 채널 구독"""
        self.target_symbols = symbols
        
        if self.is_public_connected:
            self._subscribe_public_channels()
        else:
            log_system("WebSocket 연결 대기 중 - 연결 후 자동 구독됩니다")
        
        return True
    
    def on_error(self, ws, error):
        """WebSocket 오류 처리"""
        error_msg = str(error)
        
        if ws == self.public_ws:
            log_error(f"❌ Public WebSocket 오류: {error_msg}")
            self.is_public_connected = False
        elif ws == self.private_ws:
            log_error(f"❌ Private WebSocket 오류: {error_msg}")
            self.is_private_connected = False
            self.is_authenticated = False
        
        if self.on_connection_callback:
            self.on_connection_callback(False)
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket 연결 종료"""
        if ws == self.public_ws:
            log_system(f"📴 Public WebSocket 연결 종료: {close_status_code}")
            self.is_public_connected = False
        elif ws == self.private_ws:
            log_system(f"📴 Private WebSocket 연결 종료: {close_status_code}")
            self.is_private_connected = False
            self.is_authenticated = False
        
        # 자동 재연결 시도
        if self.is_running and self.current_reconnect_attempts < self.max_reconnect_attempts:
            self._attempt_reconnect()
        
        if self.on_connection_callback:
            self.on_connection_callback(False)
    
    def _attempt_reconnect(self):
        """자동 재연결 시도"""
        self.current_reconnect_attempts += 1
        
        log_system(f"🔄 WebSocket 재연결 시도 {self.current_reconnect_attempts}/{self.max_reconnect_attempts}")
        
        def reconnect_worker():
            time.sleep(self.reconnect_delay)
            if self.is_running:
                self.start_ws(self.target_symbols)
        
        threading.Thread(target=reconnect_worker, daemon=True).start()
    
    def start_ws(self, symbols):
        """WebSocket 연결 시작"""
        if self.is_running:
            log_system("⚠️ WebSocket 이미 실행 중")
            return None, None
        
        self.is_running = True
        self.target_symbols = symbols
        self.subscribed_channels = []
        
        log_system(f"🚀 수정된 WebSocket 시작: {symbols}")
        
        try:
            # Public WebSocket 시작
            log_system("📡 Public WebSocket 연결 중...")
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
            
            # Private WebSocket 시작 (선택적)
            private_thread = None
            try:
                log_system("🔐 Private WebSocket 연결 중...")
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
                
            except Exception as e:
                log_error("Private WebSocket 시작 실패", e)
                private_thread = None
            
            log_system("✅ WebSocket 스레드 시작 완료")
            return public_thread, private_thread
            
        except Exception as e:
            log_error("WebSocket 시작 오류", e)
            self.is_running = False
            return None, None
    
    def stop_ws(self):
        """WebSocket 연결 중지"""
        log_system("🛑 WebSocket 연결 중지 중...")
        self.is_running = False
        
        try:
            if self.public_ws:
                self.public_ws.close()
                self.is_public_connected = False
            
            if self.private_ws:
                self.private_ws.close()
                self.is_private_connected = False
                self.is_authenticated = False
            
            # 상태 초기화
            self.subscribed_channels = []
            self.current_reconnect_attempts = 0
            
            if self.on_connection_callback:
                self.on_connection_callback(False)
            
            log_system("✅ WebSocket 연결 중지 완료")
            
        except Exception as e:
            log_error("WebSocket 중지 중 오류", e)
    
    def get_connection_status(self):
        """상세 연결 상태 정보"""
        uptime = None
        if self.connection_start_time:
            uptime = datetime.now() - self.connection_start_time
        
        return {
            'is_running': self.is_running,
            'public_connected': self.is_public_connected,
            'private_connected': self.is_private_connected,
            'authenticated': self.is_authenticated,
            'received_messages': self.received_messages,
            'last_heartbeat': self.last_heartbeat,
            'uptime': uptime,
            'subscribed_channels': len(self.subscribed_channels),
            'target_symbols': self.target_symbols,
            'reconnect_attempts': self.current_reconnect_attempts
        }
    
    def get_latest_price(self, symbol):
        """최신 가격 조회 (캐시된 값이 있다면)"""
        # 이 메서드는 추후 가격 캐시 기능을 추가할 때 사용
        return None
    
    def get_price_buffer_status(self, symbol):
        """가격 버퍼 상태 조회 (추후 확장용)"""
        # 이 메서드는 추후 가격 버퍼 기능을 추가할 때 사용
        return None
    
    # 콜백 설정 메서드들
    def set_price_callback(self, callback: Callable):
        """가격 업데이트 콜백 설정"""
        self.on_price_callback = callback
    
    def set_account_callback(self, callback: Callable):
        """계좌 업데이트 콜백 설정"""
        self.on_account_callback = callback
    
    def set_position_callback(self, callback: Callable):
        """포지션 업데이트 콜백 설정"""
        self.on_position_callback = callback
    
    def set_connection_callback(self, callback: Callable):
        """연결 상태 콜백 설정"""
        self.on_connection_callback = callback
    
    def print_status(self):
        """WebSocket 상태 출력"""
        status = self.get_connection_status()
        
        print(f"\n📡 WebSocket 연결 상태")
        print(f"{'='*50}")
        print(f"실행 상태: {'✅ 실행 중' if status['is_running'] else '❌ 중지됨'}")
        print(f"Public: {'✅ 연결됨' if status['public_connected'] else '❌ 끊어짐'}")
        print(f"Private: {'✅ 연결됨' if status['private_connected'] else '❌ 끊어짐'}")
        print(f"인증: {'✅ 완료' if status['authenticated'] else '❌ 실패'}")
        print(f"수신 메시지: {status['received_messages']:,}건")
        print(f"구독 채널: {status['subscribed_channels']}개")
        print(f"대상 심볼: {', '.join(status['target_symbols'])}")
        
        if status['uptime']:
            print(f"연결 시간: {status['uptime']}")
        
        if status['reconnect_attempts'] > 0:
            print(f"재연결 시도: {status['reconnect_attempts']}회")
        
        print(f"{'='*50}")


# 기존 WebSocketHandler와의 호환성을 위한 래퍼 클래스
class WebSocketHandler(FixedWebSocketHandler):
    """기존 코드와의 호환성을 위한 래퍼"""
    pass


# 테스트 전용 간단한 WebSocket 핸들러
class SimpleWebSocketHandler:
    """테스트 전용 간단한 WebSocket 핸들러"""
    
    def __init__(self):
        self.public_ws = None
        self.is_running = False
        self.is_public_connected = False
        self.on_price_callback = None
        self.on_connection_callback = None
        self.received_messages = 0
        
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
                    self.received_messages += 1
                    
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
                self.is_public_connected = True
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
                self.is_public_connected = False
                if self.on_connection_callback:
                    self.on_connection_callback(False)
            
            def on_close(ws, close_status_code, close_msg):
                self.is_public_connected = False
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
            self.is_public_connected = False


# 유틸리티 함수들
def test_websocket_connection(symbols=None, duration=10):
    """WebSocket 연결 간단 테스트"""
    if symbols is None:
        symbols = ['BTC-USDT-SWAP']
    
    print(f"🧪 WebSocket 연결 테스트 시작: {symbols}")
    
    handler = SimpleWebSocketHandler()
    received_data = False
    
    def on_price(symbol, price, data):
        nonlocal received_data
        received_data = True
        print(f"📊 데이터 수신: {symbol} = ${price:,.2f}")
    
    def on_connection(is_connected):
        status = "연결됨" if is_connected else "끊어짐"
        print(f"🔗 연결 상태: {status}")
    
    handler.set_price_callback(on_price)
    handler.set_connection_callback(on_connection)
    
    # 테스트 시작
    thread, _ = handler.start_ws_ticker_only(symbols)
    
    if thread:
        print(f"⏳ {duration}초 동안 데이터 수신 대기...")
        time.sleep(duration)
        
        handler.stop_ws()
        
        if received_data:
            print("✅ WebSocket 테스트 성공!")
            return True
        else:
            print("❌ 데이터 수신 실패")
            return False
    else:
        print("❌ WebSocket 시작 실패")
        return False


def check_websocket_channels():
    """WebSocket 채널 유효성 검사"""
    print("🔍 WebSocket 채널 유효성 검사...")
    
    # 공개 API로 사용 가능한 채널 확인
    import requests
    
    try:
        # 기본 연결 테스트
        response = requests.get("https://www.okx.com/api/v5/public/time", timeout=5)
        if response.status_code == 200:
            print("✅ OKX API 서버 연결 정상")
        else:
            print("❌ OKX API 서버 연결 실패")
            return False
        
        # 심볼 유효성 확인
        response = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print("✅ BTC-USDT-SWAP 심볼 유효")
                price = float(data['data'][0]['last'])
                print(f"💰 현재가: ${price:,.2f}")
            else:
                print(f"❌ 심볼 오류: {data.get('msg')}")
                return False
        else:
            print("❌ 심볼 확인 실패")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 채널 검사 실패: {e}")
        return False


if __name__ == "__main__":
    """테스트 실행"""
    print("🔍 WebSocket 핸들러 테스트")
    
    # 1. 채널 유효성 검사
    if check_websocket_channels():
        # 2. WebSocket 연결 테스트
        test_websocket_connection(['BTC-USDT-SWAP'], 15)
    else:
        print("❌ 기본 연결 문제로 WebSocket 테스트를 건너뜁니다.")