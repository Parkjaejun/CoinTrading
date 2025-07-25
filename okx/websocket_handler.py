# utils/websocket_handler.py
"""
WebSocket 연결 관리자
실시간 데이터 스트리밍을 위한 WebSocket 핸들러
"""

import json
import time
import threading
import websocket
from typing import Callable, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """OKX WebSocket 연결 관리"""
    
    def __init__(self, url: str = "wss://ws.okx.com:8443/ws/v5/public"):
        self.url = url
        self.ws = None
        self.callbacks = {}
        self.is_connected = False
        self.reconnect_interval = 5
        self.ping_interval = 20
        self.ping_timer = None
        self.thread = None
        
    def connect(self):
        """WebSocket 연결 시작"""
        try:
            if self.thread and self.thread.is_alive():
                logger.warning("WebSocket이 이미 실행 중입니다.")
                return
                
            self.thread = threading.Thread(target=self._connect, daemon=True)
            self.thread.start()
            logger.info("WebSocket 연결 시작")
            
        except Exception as e:
            logger.error(f"WebSocket 연결 시작 실패: {e}")
    
    def _connect(self):
        """실제 연결 수행"""
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            self.ws.run_forever()
            
        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {e}")
            self._schedule_reconnect()
    
    def _on_open(self, ws):
        """연결 성공 시 호출"""
        self.is_connected = True
        logger.info("WebSocket 연결 성공")
        
        # 핑 타이머 시작
        self._start_ping_timer()
        
        # 연결 콜백 호출
        if 'connect' in self.callbacks:
            self.callbacks['connect']()
    
    def _on_message(self, ws, message):
        """메시지 수신 시 호출"""
        try:
            data = json.loads(message)
            
            # Pong 메시지 처리
            if data.get('event') == 'pong':
                logger.debug("Pong 수신")
                return
            
            # 데이터 메시지 처리
            if 'data' in data:
                self._handle_data_message(data)
            
            # 기타 이벤트 처리
            if 'event' in data:
                self._handle_event_message(data)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
        except Exception as e:
            logger.error(f"메시지 처리 실패: {e}")
    
    def _on_error(self, ws, error):
        """에러 발생 시 호출"""
        logger.error(f"WebSocket 에러: {error}")
        
        if 'error' in self.callbacks:
            self.callbacks['error'](error)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """연결 종료 시 호출"""
        self.is_connected = False
        logger.warning(f"WebSocket 연결 종료: {close_status_code} - {close_msg}")
        
        # 핑 타이머 중지
        self._stop_ping_timer()
        
        # 종료 콜백 호출
        if 'close' in self.callbacks:
            self.callbacks['close'](close_status_code, close_msg)
        
        # 재연결 시도
        self._schedule_reconnect()
    
    def _handle_data_message(self, data):
        """데이터 메시지 처리"""
        try:
            arg = data.get('arg', {})
            channel = arg.get('channel')
            inst_id = arg.get('instId')
            
            if channel and channel in self.callbacks:
                self.callbacks[channel](data['data'], inst_id)
            
            # 전체 데이터 콜백
            if 'data' in self.callbacks:
                self.callbacks['data'](data)
                
        except Exception as e:
            logger.error(f"데이터 메시지 처리 실패: {e}")
    
    def _handle_event_message(self, data):
        """이벤트 메시지 처리"""
        try:
            event = data.get('event')
            
            if event == 'subscribe':
                logger.info(f"구독 성공: {data}")
            elif event == 'unsubscribe':
                logger.info(f"구독 해제: {data}")
            elif event == 'error':
                logger.error(f"WebSocket 에러 이벤트: {data}")
                
            # 이벤트 콜백 호출
            if event in self.callbacks:
                self.callbacks[event](data)
                
        except Exception as e:
            logger.error(f"이벤트 메시지 처리 실패: {e}")
    
    def subscribe(self, channel: str, inst_id: str = None):
        """채널 구독"""
        if not self.is_connected:
            logger.warning("WebSocket이 연결되지 않음")
            return False
        
        try:
            sub_data = {
                "op": "subscribe",
                "args": [{
                    "channel": channel
                }]
            }
            
            if inst_id:
                sub_data["args"][0]["instId"] = inst_id
            
            message = json.dumps(sub_data)
            self.ws.send(message)
            logger.info(f"구독 요청: {channel} - {inst_id}")
            return True
            
        except Exception as e:
            logger.error(f"구독 실패: {e}")
            return False
    
    def unsubscribe(self, channel: str, inst_id: str = None):
        """구독 해제"""
        if not self.is_connected:
            logger.warning("WebSocket이 연결되지 않음")
            return False
        
        try:
            unsub_data = {
                "op": "unsubscribe",
                "args": [{
                    "channel": channel
                }]
            }
            
            if inst_id:
                unsub_data["args"][0]["instId"] = inst_id
            
            message = json.dumps(unsub_data)
            self.ws.send(message)
            logger.info(f"구독 해제: {channel} - {inst_id}")
            return True
            
        except Exception as e:
            logger.error(f"구독 해제 실패: {e}")
            return False
    
    def _start_ping_timer(self):
        """핑 타이머 시작"""
        def send_ping():
            if self.is_connected and self.ws:
                try:
                    ping_data = {"op": "ping"}
                    self.ws.send(json.dumps(ping_data))
                    logger.debug("Ping 전송")
                except Exception as e:
                    logger.error(f"Ping 전송 실패: {e}")
            
            # 다음 핑 예약
            if self.is_connected:
                self.ping_timer = threading.Timer(self.ping_interval, send_ping)
                self.ping_timer.daemon = True
                self.ping_timer.start()
        
        send_ping()
    
    def _stop_ping_timer(self):
        """핑 타이머 중지"""
        if self.ping_timer:
            self.ping_timer.cancel()
            self.ping_timer = None
    
    def _schedule_reconnect(self):
        """재연결 예약"""
        if self.is_connected:
            return
        
        logger.info(f"{self.reconnect_interval}초 후 재연결 시도")
        
        def reconnect():
            if not self.is_connected:
                logger.info("재연결 시도 중...")
                self._connect()
        
        timer = threading.Timer(self.reconnect_interval, reconnect)
        timer.daemon = True
        timer.start()
    
    def add_callback(self, event: str, callback: Callable):
        """콜백 함수 등록"""
        self.callbacks[event] = callback
        logger.debug(f"콜백 등록: {event}")
    
    def remove_callback(self, event: str):
        """콜백 함수 제거"""
        if event in self.callbacks:
            del self.callbacks[event]
            logger.debug(f"콜백 제거: {event}")
    
    def close(self):
        """연결 종료"""
        self.is_connected = False
        
        # 핑 타이머 중지
        self._stop_ping_timer()
        
        # WebSocket 연결 종료
        if self.ws:
            self.ws.close()
        
        logger.info("WebSocket 연결 종료 요청")

class OKXPriceStream:
    """OKX 가격 스트림 관리자"""
    
    def __init__(self, symbols: list = None):
        self.symbols = symbols or ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
        self.ws_handler = WebSocketHandler()
        self.price_callbacks = {}
        
        # 콜백 등록
        self.ws_handler.add_callback('connect', self._on_connect)
        self.ws_handler.add_callback('tickers', self._on_ticker_update)
        self.ws_handler.add_callback('error', self._on_error)
    
    def start(self):
        """가격 스트림 시작"""
        self.ws_handler.connect()
    
    def stop(self):
        """가격 스트림 중지"""
        self.ws_handler.close()
    
    def _on_connect(self):
        """연결 성공 시 구독 시작"""
        for symbol in self.symbols:
            self.ws_handler.subscribe('tickers', symbol)
    
    def _on_ticker_update(self, data, inst_id):
        """가격 업데이트 처리"""
        try:
            for ticker in data:
                symbol = ticker.get('instId')
                price = float(ticker.get('last', 0))
                
                # 가격 콜백 호출
                if symbol in self.price_callbacks:
                    self.price_callbacks[symbol](symbol, price, ticker)
                
                # 전체 가격 콜백 호출
                if 'all' in self.price_callbacks:
                    self.price_callbacks['all'](symbol, price, ticker)
                    
        except Exception as e:
            logger.error(f"가격 업데이트 처리 실패: {e}")
    
    def _on_error(self, error):
        """에러 처리"""
        logger.error(f"가격 스트림 에러: {error}")
    
    def add_price_callback(self, symbol: str, callback: Callable):
        """가격 콜백 등록"""
        self.price_callbacks[symbol] = callback
    
    def remove_price_callback(self, symbol: str):
        """가격 콜백 제거"""
        if symbol in self.price_callbacks:
            del self.price_callbacks[symbol]

# 간단한 사용 예제
if __name__ == "__main__":
    import time
    
    def on_price_update(symbol, price, data):
        print(f"{symbol}: ${price:,.2f}")
    
    # 가격 스트림 시작
    stream = OKXPriceStream(['BTC-USDT-SWAP'])
    stream.add_price_callback('all', on_price_update)
    stream.start()
    
    try:
        time.sleep(30)  # 30초 동안 실행
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop()