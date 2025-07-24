# okx/websocket_handler.py
"""
수정된 OKX WebSocket 핸들러
- 통일된 타임스탬프 및 서명 사용
- config.py의 공통 유틸리티 함수 활용
- 안정적인 연결 관리
"""

import websocket
import json
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from config import (
    API_KEY, API_SECRET, PASSPHRASE, EMA_PERIODS,
    get_websocket_auth_data, get_timestamp, generate_signature
)

try:
    from utils.logger import log_system, log_error, log_info
except ImportError:
    # 로거가 없는 경우 기본 print 사용
    def log_system(msg): print(f"[SYSTEM] {msg}")
    def log_error(msg, e=None): print(f"[ERROR] {msg}: {e}" if e else f"[ERROR] {msg}")
    def log_info(msg): print(f"[INFO] {msg}")

class WebSocketHandler:
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
        
        log_system("🔗 WebSocket 핸들러 초기화 완료")
    
    def set_callbacks(self, price_callback=None, account_callback=None, 
                     position_callback=None, connection_callback=None):
        """콜백 함수 설정"""
        if price_callback:
            self.on_price_callback = price_callback
        if account_callback:
            self.on_account_callback = account_callback
        if position_callback:
            self.on_position_callback = position_callback
        if connection_callback:
            self.on_connection_callback = connection_callback
    
    def start_websocket(self, symbols: List[str], channels: List[str] = None):
        """WebSocket 연결 시작"""
        try:
            self.target_symbols = symbols
            self.is_running = True
            
            if channels is None:
                channels = ["tickers"]  # 기본적으로 ticker만 구독
            
            log_system(f"🚀 WebSocket 시작: {symbols} (채널: {channels})")
            
            # Public WebSocket 시작
            self._start_public_websocket(channels)
            
            # Private WebSocket 시작 (필요시)
            if "account" in channels or "positions" in channels:
                self._start_private_websocket()
            
            return True
            
        except Exception as e:
            log_error("WebSocket 시작 실패", e)
            return False
    
    def _start_public_websocket(self, channels: List[str]):
        """Public WebSocket 시작"""
        def on_message(ws, message):
            self._handle_public_message(message)
        
        def on_open(ws):
            log_system("✅ Public WebSocket 연결 성공")
            self.is_public_connected = True
            self.connection_start_time = datetime.now()
            self.current_reconnect_attempts = 0
            
            # 연결 상태 콜백
            if self.on_connection_callback:
                self.on_connection_callback(True)
            
            # 채널 구독
            self._subscribe_channels(channels)
        
        def on_error(ws, error):
            log_error("Public WebSocket 오류", error)
            self.is_public_connected = False
            if self.on_connection_callback:
                self.on_connection_callback(False)
        
        def on_close(ws, close_status_code, close_msg):
            log_system(f"Public WebSocket 연결 종료: {close_status_code}")
            self.is_public_connected = False
            if self.on_connection_callback:
                self.on_connection_callback(False)
            
            # 재연결 시도
            if self.is_running and self.current_reconnect_attempts < self.max_reconnect_attempts:
                self._reconnect_public()
        
        # WebSocket 생성 및 시작
        self.public_ws = websocket.WebSocketApp(
            self.public_ws_url,
            on_message=on_message,
            on_open=on_open,
            on_error=on_error,
            on_close=on_close
        )
        
        # 백그라운드 스레드에서 실행
        public_thread = threading.Thread(
            target=self.public_ws.run_forever,
            daemon=True
        )
        public_thread.start()
        log_system("📡 Public WebSocket 스레드 시작")
    
    def _start_private_websocket(self):
        """Private WebSocket 시작"""
        def on_message(ws, message):
            self._handle_private_message(message)
        
        def on_open(ws):
            log_system("✅ Private WebSocket 연결 성공")
            self.is_private_connected = True
            
            # 인증 실행
            self._authenticate_private_websocket()
        
        def on_error(ws, error):
            log_error("Private WebSocket 오류", error)
            self.is_private_connected = False
            self.is_authenticated = False
        
        def on_close(ws, close_status_code, close_msg):
            log_system(f"Private WebSocket 연결 종료: {close_status_code}")
            self.is_private_connected = False
            self.is_authenticated = False
        
        # WebSocket 생성 및 시작
        self.private_ws = websocket.WebSocketApp(
            self.private_ws_url,
            on_message=on_message,
            on_open=on_open,
            on_error=on_error,
            on_close=on_close
        )
        
        # 백그라운드 스레드에서 실행
        private_thread = threading.Thread(
            target=self.private_ws.run_forever,
            daemon=True
        )
        private_thread.start()
        log_system("🔐 Private WebSocket 스레드 시작")
    
    def _authenticate_private_websocket(self):
        """Private WebSocket 인증"""
        try:
            # config의 공통 함수 사용
            auth_data = get_websocket_auth_data()
            
            if self.private_ws:
                self.private_ws.send(json.dumps(auth_data))
                log_system("🔐 Private WebSocket 인증 요청 전송")
            
        except Exception as e:
            log_error("Private WebSocket 인증 실패", e)
    
    def _subscribe_channels(self, channels: List[str]):
        """채널 구독"""
        try:
            for channel in channels:
                for symbol in self.target_symbols:
                    if channel == "tickers":
                        # Ticker 구독
                        subscribe_msg = {
                            "op": "subscribe",
                            "args": [{"channel": "tickers", "instId": symbol}]
                        }
                    elif channel == "candles":
                        # 캔들 구독 (30분봉)
                        subscribe_msg = {
                            "op": "subscribe", 
                            "args": [{"channel": "candle30m", "instId": symbol}]
                        }
                    elif channel == "books":
                        # 호가 구독
                        subscribe_msg = {
                            "op": "subscribe",
                            "args": [{"channel": "books5", "instId": symbol}]
                        }
                    else:
                        continue
                    
                    if self.public_ws:
                        self.public_ws.send(json.dumps(subscribe_msg))
                        log_system(f"📡 구독 요청: {channel} - {symbol}")
            
        except Exception as e:
            log_error("채널 구독 실패", e)
    
    def _handle_public_message(self, message: str):
        """Public 메시지 처리"""
        try:
            data = json.loads(message)
            self.received_messages += 1
            self.last_heartbeat = datetime.now()
            
            # 이벤트 메시지 처리
            if 'event' in data:
                event = data['event']
                if event == 'subscribe':
                    log_system(f"✅ 구독 성공: {data.get('arg', {})}")
                elif event == 'error':
                    log_error(f"구독 오류: {data.get('msg', 'Unknown error')}")
                return
            
            # 실제 데이터 처리
            if 'data' in data and 'arg' in data:
                channel = data['arg']['channel']
                inst_id = data['arg']['instId']
                
                if channel == 'tickers':
                    self._process_ticker_data(inst_id, data['data'][0])
                elif channel == 'candle30m':
                    self._process_candle_data(inst_id, data['data'][0])
                elif channel == 'books5':
                    self._process_orderbook_data(inst_id, data['data'][0])
                
        except json.JSONDecodeError:
            log_error("Public 메시지 JSON 파싱 오류")
        except Exception as e:
            log_error("Public 메시지 처리 오류", e)
    
    def _handle_private_message(self, message: str):
        """Private 메시지 처리"""
        try:
            data = json.loads(message)
            self.received_messages += 1
            
            # 인증 응답 처리
            if 'event' in data:
                event = data['event']
                if event == 'login':
                    if data.get('code') == '0':
                        self.is_authenticated = True
                        log_system("✅ Private WebSocket 인증 성공")
                        self._subscribe_private_channels()
                    else:
                        log_error(f"Private WebSocket 인증 실패: {data.get('msg', 'Unknown')}")
                return
            
            # 실제 데이터 처리
            if 'data' in data and 'arg' in data:
                channel = data['arg']['channel']
                
                if channel == 'account':
                    self._process_account_data(data['data'])
                elif channel == 'positions':
                    self._process_position_data(data['data'])
                
        except Exception as e:
            log_error("Private 메시지 처리 오류", e)
    
    def _process_ticker_data(self, symbol: str, ticker_data: Dict[str, Any]):
        """Ticker 데이터 처리"""
        try:
            price = float(ticker_data.get('last', 0))
            
            # 주기적 로깅 (100개마다)
            if self.received_messages % 100 == 0:
                log_info(f"📊 {symbol} 현재가: ${price:,.2f}")
            
            # 콜백 호출
            if self.on_price_callback:
                self.on_price_callback(symbol, price, ticker_data)
            
            # 전략 매니저에 데이터 전달
            if self.strategy_manager:
                self.strategy_manager.process_price_update(symbol, ticker_data)
                
        except Exception as e:
            log_error(f"Ticker 데이터 처리 오류 ({symbol})", e)
    
    def _process_candle_data(self, symbol: str, candle_data: List):
        """캔들 데이터 처리"""
        try:
            # 캔들 데이터: [timestamp, open, high, low, close, volume, volume_currency]
            timestamp = int(candle_data[0])
            open_price = float(candle_data[1])
            high_price = float(candle_data[2])
            low_price = float(candle_data[3])
            close_price = float(candle_data[4])
            volume = float(candle_data[5])
            
            candle_info = {
                'timestamp': datetime.fromtimestamp(timestamp / 1000),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            }
            
            log_info(f"🕯️ {symbol} 새 캔들: ${close_price:,.2f} (볼륨: {volume:,.0f})")
            
            # 전략 매니저에 캔들 데이터 전달
            if self.strategy_manager:
                self.strategy_manager.process_candle_update(symbol, candle_info)
                
        except Exception as e:
            log_error(f"캔들 데이터 처리 오류 ({symbol})", e)
    
    def _process_orderbook_data(self, symbol: str, orderbook_data: Dict[str, Any]):
        """호가 데이터 처리"""
        try:
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                spread = best_ask - best_bid
                
                # 스프레드 정보 로깅 (1000개마다)
                if self.received_messages % 1000 == 0:
                    log_info(f"📈 {symbol} 호가: ${best_bid:,.2f} / ${best_ask:,.2f} (스프레드: ${spread:.2f})")
                
        except Exception as e:
            log_error(f"호가 데이터 처리 오류 ({symbol})", e)
    
    def _process_account_data(self, account_data: List[Dict[str, Any]]):
        """계좌 데이터 처리"""
        try:
            for account in account_data:
                log_info(f"💰 계좌 업데이트: 총자산 ${float(account.get('totalEq', 0)):,.2f}")
                
                # 콜백 호출
                if self.on_account_callback:
                    self.on_account_callback(account)
                    
        except Exception as e:
            log_error("계좌 데이터 처리 오류", e)
    
    def _process_position_data(self, position_data: List[Dict[str, Any]]):
        """포지션 데이터 처리"""
        try:
            for position in position_data:
                inst_id = position.get('instId', '')
                pos_size = float(position.get('pos', 0))
                
                if pos_size != 0:
                    pnl = float(position.get('upl', 0))
                    log_info(f"📊 {inst_id} 포지션: {pos_size} (PnL: ${pnl:+.2f})")
                
                # 콜백 호출
                if self.on_position_callback:
                    self.on_position_callback(position)
                    
        except Exception as e:
            log_error("포지션 데이터 처리 오류", e)
    
    def _subscribe_private_channels(self):
        """Private 채널 구독"""
        try:
            # 계좌 정보 구독
            account_msg = {
                "op": "subscribe",
                "args": [{"channel": "account"}]
            }
            
            # 포지션 정보 구독
            position_msg = {
                "op": "subscribe",
                "args": [{"channel": "positions", "instType": "SWAP"}]
            }
            
            if self.private_ws:
                self.private_ws.send(json.dumps(account_msg))
                self.private_ws.send(json.dumps(position_msg))
                log_system("📡 Private 채널 구독 완료")
            
        except Exception as e:
            log_error("Private 채널 구독 실패", e)
    
    def _reconnect_public(self):
        """Public WebSocket 재연결"""
        if not self.is_running:
            return
        
        self.current_reconnect_attempts += 1
        log_system(f"🔄 Public WebSocket 재연결 시도 {self.current_reconnect_attempts}/{self.max_reconnect_attempts}")
        
        time.sleep(self.reconnect_delay)
        
        try:
            self._start_public_websocket(["tickers"])
        except Exception as e:
            log_error("재연결 실패", e)
    
    def stop_websocket(self):
        """WebSocket 연결 중지"""
        try:
            log_system("🛑 WebSocket 연결 중지 중...")
            self.is_running = False
            
            if self.public_ws:
                self.public_ws.close()
                self.is_public_connected = False
            
            if self.private_ws:
                self.private_ws.close()
                self.is_private_connected = False
                self.is_authenticated = False
            
            log_system("✅ WebSocket 연결 중지 완료")
            
        except Exception as e:
            log_error("WebSocket 중지 실패", e)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 정보"""
        uptime = 0
        if self.connection_start_time:
            uptime = (datetime.now() - self.connection_start_time).total_seconds()
        
        return {
            'is_running': self.is_running,
            'public_connected': self.is_public_connected,
            'private_connected': self.is_private_connected,
            'authenticated': self.is_authenticated,
            'received_messages': self.received_messages,
            'uptime_seconds': uptime,
            'target_symbols': self.target_symbols,
            'subscribed_channels': self.subscribed_channels,
            'reconnect_attempts': self.current_reconnect_attempts
        }
    
    def print_status(self):
        """상태 정보 출력"""
        status = self.get_connection_status()
        
        print("\n📡 WebSocket 연결 상태")
        print("-" * 50)
        print(f"🔄 실행 중: {'✅' if status['is_running'] else '❌'}")
        print(f"🌐 Public 연결: {'✅' if status['public_connected'] else '❌'}")
        print(f"🔐 Private 연결: {'✅' if status['private_connected'] else '❌'}")
        print(f"🔑 인증 상태: {'✅' if status['authenticated'] else '❌'}")
        print(f"📊 수신 메시지: {status['received_messages']:,}개")
        print(f"⏰ 가동 시간: {status['uptime_seconds']:.0f}초")
        print(f"📈 구독 심볼: {', '.join(status['target_symbols'])}")
        print(f"🔄 재연결 시도: {status['reconnect_attempts']}/{self.max_reconnect_attempts}")

# 간단한 WebSocket 테스트용 클래스
class SimpleWebSocketHandler:
    """간단한 WebSocket 테스트용 핸들러"""
    
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.received_count = 0
        self.on_price_callback = None
        self.on_connection_callback = None
    
    def set_price_callback(self, callback):
        """가격 업데이트 콜백 설정"""
        self.on_price_callback = callback
    
    def set_connection_callback(self, callback):
        """연결 상태 콜백 설정"""
        self.on_connection_callback = callback
    
    def start_ws_ticker_only(self, symbols: List[str]):
        """Ticker만 구독하는 간단한 WebSocket"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self.received_count += 1
                
                if 'data' in data and 'arg' in data:
                    if data['arg']['channel'] == 'tickers':
                        ticker = data['data'][0]
                        symbol = data['arg']['instId']
                        price = float(ticker.get('last', 0))
                        
                        if self.on_price_callback:
                            self.on_price_callback(symbol, price, ticker)
                            
            except Exception as e:
                print(f"메시지 처리 오류: {e}")
        
        def on_open(ws):
            self.is_connected = True
            print("✅ WebSocket 연결 성공")
            
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
            self.is_connected = False
            print(f"WebSocket 오류: {error}")
            if self.on_connection_callback:
                self.on_connection_callback(False)
        
        def on_close(ws, close_status_code, close_msg):
            self.is_connected = False
            print("⚠️ WebSocket 연결 상태 변경")
            if self.on_connection_callback:
                self.on_connection_callback(False)
        
        self.ws = websocket.WebSocketApp(
            "wss://ws.okx.com:8443/ws/v5/public",
            on_message=on_message,
            on_open=on_open,
            on_error=on_error,
            on_close=on_close
        )
        
        thread = threading.Thread(
            target=self.ws.run_forever,
            daemon=True
        )
        thread.start()
        
        return thread, None
    
    def stop_ws(self):
        """WebSocket 중지"""
        if self.ws:
            self.ws.close()
            self.is_connected = False
            print("🛑 WebSocket 연결 종료")

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
        print(f"📊 실시간 데이터 수신: {symbol} = ${price:,.2f}")
    
    def on_connection(is_connected):
        status = "연결됨" if is_connected else "끊어짐"
        print(f"🔗 연결 상태: {status}")
    
    handler.set_price_callback(on_price)
    handler.set_connection_callback(on_connection)
    
    # 테스트 시작
    print("✅ WebSocket 스레드 시작됨")
    thread, _ = handler.start_ws_ticker_only(symbols)
    
    if thread:
        print(f"⏳ 실시간 데이터 수신 대기 ({duration}초)...")
        
        # 대기 및 상태 체크
        for i in range(duration):
            time.sleep(1)
            if handler.is_connected and not received_data:
                print(f"  ⏳ 대기 중... ({i+1}/{duration}초)")
        
        handler.stop_ws()
        
        if received_data:
            print("✅ WebSocket 테스트 성공!")
            print(f"📊 수신된 메시지: {handler.received_count}건")
            return True
        else:
            print("❌ 데이터 수신 실패")
            return False
    else:
        print("❌ WebSocket 스레드 시작 실패")
        return False

def test_full_websocket():
    """전체 WebSocket 기능 테스트"""
    print("🧪 전체 WebSocket 기능 테스트")
    print("=" * 80)
    
    # 1. 간단한 연결 테스트
    simple_ok = test_websocket_connection(['BTC-USDT-SWAP'], 15)
    
    # 2. 고급 핸들러 테스트
    print("\n📡 고급 WebSocket 핸들러 테스트")
    print("-" * 50)
    
    handler = WebSocketHandler()
    
    # 콜백 설정
    def on_price_update(symbol, price, data):
        print(f"💰 가격 업데이트: {symbol} = ${price:,.2f}")
    
    def on_connection_change(is_connected):
        status = "연결됨" if is_connected else "끊어짐"
        print(f"🔗 연결 변경: {status}")
    
    handler.set_callbacks(
        price_callback=on_price_update,
        connection_callback=on_connection_change
    )
    
    # WebSocket 시작
    success = handler.start_websocket(['BTC-USDT-SWAP'], ['tickers'])
    
    if success:
        print("✅ 고급 WebSocket 시작 성공")
        
        # 15초 대기
        time.sleep(15)
        
        # 상태 출력
        handler.print_status()
        
        # 중지
        handler.stop_websocket()
        
        advanced_ok = True
    else:
        print("❌ 고급 WebSocket 시작 실패")
        advanced_ok = False
    
    # 결과 요약
    print("\n📋 WebSocket 테스트 결과")
    print("=" * 80)
    print(f"간단한 연결: {'✅ 통과' if simple_ok else '❌ 실패'}")
    print(f"고급 핸들러: {'✅ 통과' if advanced_ok else '❌ 실패'}")
    
    if simple_ok and advanced_ok:
        print("\n🎉 모든 WebSocket 테스트 통과!")
        return True
    else:
        print("\n⚠️ 일부 WebSocket 테스트 실패")
        return False

# 직접 실행시 테스트 수행
if __name__ == "__main__":
    try:
        print("🚀 WebSocket 핸들러 테스트")
        test_full_websocket()
    except Exception as e:
        print(f"❌ 테스트 실행 오류: {e}")