# okx/connection_manager.py
"""
API 연결 안정성 관리
재연결, 상태 모니터링, 오류 복구
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
from okx.account_manager import AccountManager
from utils.logger import log_system, log_error

class ConnectionManager:
    def __init__(self, reconnect_interval: int = 30, max_retries: int = 5):
        self.account_manager = AccountManager()
        self.reconnect_interval = reconnect_interval
        self.max_retries = max_retries
        
        # 연결 상태
        self.is_connected = False
        self.last_successful_request = datetime.now()
        self.connection_failures = 0
        self.is_monitoring = False
        
        # 모니터링 스레드
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
        # 콜백 함수들
        self.on_reconnect_callbacks: list[Callable] = []
        self.on_disconnect_callbacks: list[Callable] = []
    
    def test_connection(self) -> bool:
        """연결 상태 테스트"""
        try:
            # 간단한 API 호출로 연결 테스트
            balances = self.account_manager.get_account_balance()
            
            if balances is not None:
                self.last_successful_request = datetime.now()
                self.connection_failures = 0
                
                if not self.is_connected:
                    self.is_connected = True
                    log_system("API 연결 복구됨")
                    self._trigger_reconnect_callbacks()
                
                return True
            else:
                self._handle_connection_failure()
                return False
                
        except Exception as e:
            log_error(f"연결 테스트 실패", e)
            self._handle_connection_failure()
            return False
    
    def _handle_connection_failure(self):
        """연결 실패 처리"""
        self.connection_failures += 1
        
        if self.is_connected:
            self.is_connected = False
            log_system(f"API 연결 끊어짐 (실패 횟수: {self.connection_failures})")
            self._trigger_disconnect_callbacks()
    
    def ensure_connection(self) -> bool:
        """연결 보장 (필요시 재연결 시도)"""
        if self.is_connected:
            # 마지막 성공 요청이 5분 이상 지났으면 재테스트
            if datetime.now() - self.last_successful_request > timedelta(minutes=5):
                return self.test_connection()
            return True
        
        # 연결되지 않은 상태면 재연결 시도
        return self._attempt_reconnection()
    
    def _attempt_reconnection(self) -> bool:
        """재연결 시도"""
        log_system(f"재연결 시도 중... (시도 {self.connection_failures + 1}/{self.max_retries})")
        
        for attempt in range(self.max_retries):
            if self.test_connection():
                log_system(f"재연결 성공 (시도 {attempt + 1}회)")
                return True
            
            if attempt < self.max_retries - 1:
                time.sleep(5 * (attempt + 1))  # 지수 백오프
        
        log_error(f"재연결 실패 - {self.max_retries}회 시도 후 포기")
        return False
    
    def start_monitoring(self):
        """연결 모니터링 시작"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.stop_monitoring.clear()
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_connection,
            name="ConnectionMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        
        log_system("연결 모니터링 시작")
    
    def stop_connection_monitoring(self):
        """연결 모니터링 중지"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.stop_monitoring.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        log_system("연결 모니터링 중지")
    
    def _monitor_connection(self):
        """연결 모니터링 메인 루프"""
        while not self.stop_monitoring.is_set():
            try:
                self.test_connection()
                
                # 다음 체크까지 대기
                self.stop_monitoring.wait(self.reconnect_interval)
                
            except Exception as e:
                log_error("연결 모니터링 중 오류 발생", e)
                time.sleep(10)
    
    def add_reconnect_callback(self, callback: Callable):
        """재연결 시 호출할 콜백 함수 추가"""
        self.on_reconnect_callbacks.append(callback)
    
    def add_disconnect_callback(self, callback: Callable):
        """연결 끊어질 때 호출할 콜백 함수 추가"""
        self.on_disconnect_callbacks.append(callback)
    
    def _trigger_reconnect_callbacks(self):
        """재연결 콜백 함수들 호출"""
        for callback in self.on_reconnect_callbacks:
            try:
                callback()
            except Exception as e:
                log_error("재연결 콜백 실행 오류", e)
    
    def _trigger_disconnect_callbacks(self):
        """연결 끊김 콜백 함수들 호출"""
        for callback in self.on_disconnect_callbacks:
            try:
                callback()
            except Exception as e:
                log_error("연결 끊김 콜백 실행 오류", e)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 정보"""
        return {
            'is_connected': self.is_connected,
            'last_successful_request': self.last_successful_request,
            'connection_failures': self.connection_failures,
            'is_monitoring': self.is_monitoring,
            'uptime': datetime.now() - self.last_successful_request if self.is_connected else None
        }
    
    def safe_api_call(self, api_function: Callable, *args, **kwargs):
        """안전한 API 호출 (재연결 포함)"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            # 연결 보장
            if not self.ensure_connection():
                if attempt == max_attempts - 1:
                    raise ConnectionError("API 연결을 복구할 수 없습니다")
                continue
            
            try:
                # API 호출 실행
                result = api_function(*args, **kwargs)
                self.last_successful_request = datetime.now()
                return result
                
            except Exception as e:
                log_error(f"API 호출 실패 (시도 {attempt + 1}/{max_attempts})", e)
                self._handle_connection_failure()
                
                if attempt < max_attempts - 1:
                    time.sleep(2 ** attempt)  # 지수 백오프
                else:
                    raise e

# 전역 연결 매니저
connection_manager = ConnectionManager()

def ensure_api_connection() -> bool:
    """API 연결 보장"""
    return connection_manager.ensure_connection()

def safe_api_call(api_function: Callable, *args, **kwargs):
    """안전한 API 호출"""
    return connection_manager.safe_api_call(api_function, *args, **kwargs)