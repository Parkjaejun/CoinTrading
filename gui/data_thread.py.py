# gui/data_thread.py 수정 패치
# 
# 이 파일의 내용을 기존 gui/data_thread.py에 적용하세요.
# 
# 변경 사항:
# 1. DualStrategyManager → StrategyManager (v2)
# 2. import 경로 변경

# ============================================================
# 수정 전 (기존 코드)
# ============================================================
"""
from strategy.dual_manager import DualStrategyManager

# ... 중간 코드 ...

self.strategy_manager = DualStrategyManager(
    symbols=symbols,
    capital_allocation=0.95
)
"""

# ============================================================
# 수정 후 (v2 코드)
# ============================================================
"""
# v2 전략 매니저 import
try:
    from cointrading_v2.strategy import StrategyManager
    STRATEGY_V2_AVAILABLE = True
except ImportError:
    # 폴백: 기존 DualStrategyManager 사용
    try:
        from strategy.dual_manager import DualStrategyManager as StrategyManager
        STRATEGY_V2_AVAILABLE = False
    except ImportError:
        StrategyManager = None
        STRATEGY_V2_AVAILABLE = False

# ... 중간 코드 ...

# 전략 매니저 초기화 (v2)
symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
initial_capital = TRADING_CONFIG.get('initial_capital', 10000)

if STRATEGY_V2_AVAILABLE:
    self.strategy_manager = StrategyManager(
        total_capital=initial_capital * 0.95,  # 95% 사용
        symbols=symbols,
        email_notifier=None  # GUI에서는 이메일 알림 비활성화
    )
else:
    # 폴백: 기존 방식
    self.strategy_manager = StrategyManager(
        symbols=symbols,
        capital_allocation=0.95
    )
"""

# ============================================================
# 전체 수정된 파일 내용 (복사해서 사용)
# ============================================================

# gui/data_thread.py
"""
거래 데이터 처리 스레드 (v2 호환)

실시간 데이터 수집 및 전략 실행
"""

import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

from PyQt5.QtCore import QThread, pyqtSignal

# 설정 import
try:
    from config import TRADING_CONFIG, API_KEY
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    TRADING_CONFIG = {'symbols': ['BTC-USDT-SWAP'], 'initial_capital': 10000}

# AccountManager import
try:
    from okx.account_manager import AccountManager
    ACCOUNT_MANAGER_AVAILABLE = True
except ImportError:
    AccountManager = None
    ACCOUNT_MANAGER_AVAILABLE = False

# WebSocketHandler import
try:
    from okx.websocket_handler import WebSocketHandler
    WEBSOCKET_AVAILABLE = True
except ImportError:
    try:
        from websocket_handler import WebSocketHandler
        WEBSOCKET_AVAILABLE = True
    except ImportError:
        WebSocketHandler = None
        WEBSOCKET_AVAILABLE = False

# v2 전략 매니저 import (우선)
try:
    from cointrading_v2.strategy import StrategyManager
    STRATEGY_V2_AVAILABLE = True
    print("✅ v2 StrategyManager 로드 성공")
except ImportError:
    STRATEGY_V2_AVAILABLE = False
    # 폴백: 기존 DualStrategyManager
    try:
        from strategy.dual_manager import DualStrategyManager as StrategyManager
        print("⚠️ 기존 DualStrategyManager 사용 (v2 미설치)")
    except ImportError:
        StrategyManager = None
        print("❌ 전략 매니저를 찾을 수 없습니다")

# 로깅 유틸
try:
    from utils.logger import log_system, log_error, log_info
except ImportError:
    def log_system(msg): print(f"[SYSTEM] {msg}")
    def log_error(msg, e=None): print(f"[ERROR] {msg}: {e}" if e else f"[ERROR] {msg}")
    def log_info(msg): print(f"[INFO] {msg}")


# 거래 모듈 사용 가능 여부
TRADING_MODULES_AVAILABLE = (
    ACCOUNT_MANAGER_AVAILABLE and 
    WEBSOCKET_AVAILABLE and 
    StrategyManager is not None
)


class TradingDataThread(QThread):
    """
    거래 데이터 처리 스레드
    
    실시간 가격, 계정, 포지션 업데이트
    """
    
    # 시그널 정의
    account_updated = pyqtSignal(dict)
    price_updated = pyqtSignal(str, float, dict)
    position_updated = pyqtSignal(dict)
    trade_executed = pyqtSignal(dict)
    strategy_updated = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str)
    system_stats_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.account_manager = None
        self.ws_handler = None
        self.strategy_manager = None
        
        self.running = False
        self.is_running = False
        self.account_data = {}
        self.latest_prices = {}
        self.update_interval = 3  # 3초
        
        print("✅ TradingDataThread 초기화")
        if STRATEGY_V2_AVAILABLE:
            print("   - 전략: v2 StrategyManager (Long Only)")
        else:
            print("   - 전략: 기존 DualStrategyManager")
    
    def initialize_trading_system(self) -> bool:
        """거래 시스템 초기화"""
        try:
            if not TRADING_MODULES_AVAILABLE:
                self.connection_status_changed.emit(False, "거래 모듈을 사용할 수 없습니다")
                return False
            
            log_system("GUI용 거래 시스템 초기화 중...")
            
            # 설정 로드
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            initial_capital = TRADING_CONFIG.get('initial_capital', 10000)
            
            # 전략 매니저 초기화 (v2 우선)
            if STRATEGY_V2_AVAILABLE:
                self.strategy_manager = StrategyManager(
                    total_capital=initial_capital * 0.95,
                    symbols=symbols,
                    email_notifier=None  # GUI에서는 이메일 비활성화
                )
                log_system("v2 StrategyManager 초기화 완료 (Long Only)")
            else:
                # 폴백: 기존 방식
                self.strategy_manager = StrategyManager(
                    symbols=symbols,
                    capital_allocation=0.95
                )
                log_system("기존 DualStrategyManager 초기화 완료")
            
            # WebSocket 핸들러 초기화
            self.ws_handler = WebSocketHandler(strategy_manager=self.strategy_manager)
            
            # 콜백 설정
            self.ws_handler.on_price_callback = self._on_price_update
            self.ws_handler.on_connection_callback = self._on_connection_status
            self.ws_handler.on_account_callback = self._on_account_update
            self.ws_handler.on_position_callback = self._on_position_update
            
            log_system("GUI용 거래 시스템 초기화 완료")
            return True
            
        except Exception as e:
            log_error("GUI 거래 시스템 초기화 실패", e)
            self.connection_status_changed.emit(False, f"초기화 실패: {e}")
            return False
    
    def start_websocket(self) -> bool:
        """WebSocket 연결 시작"""
        try:
            if not self.ws_handler:
                if not self.initialize_trading_system():
                    return False
            
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            success = self.ws_handler.start_websocket(symbols)
            
            if success:
                self.is_running = True
                self.connection_status_changed.emit(True, "WebSocket 연결 성공")
                log_system("GUI WebSocket 연결 시작")
                return True
            else:
                self.connection_status_changed.emit(False, "WebSocket 연결 실패")
                return False
                
        except Exception as e:
            log_error("GUI WebSocket 시작 실패", e)
            self.connection_status_changed.emit(False, f"WebSocket 오류: {e}")
            return False
    
    def stop_websocket(self):
        """WebSocket 연결 중지"""
        try:
            if self.ws_handler:
                self.ws_handler.stop_websocket()
            self.is_running = False
            self.connection_status_changed.emit(False, "WebSocket 연결 종료")
            log_system("GUI WebSocket 연결 종료")
        except Exception as e:
            log_error("WebSocket 종료 오류", e)
    
    def run(self):
        """메인 실행 루프"""
        try:
            self.running = True
            print("🚀 TradingDataThread 시작")
            
            # AccountManager 초기화
            if ACCOUNT_MANAGER_AVAILABLE:
                try:
                    self.account_manager = AccountManager()
                    print("✅ TradingDataThread - AccountManager 초기화 성공")
                except Exception as e:
                    print(f"⚠️ AccountManager 초기화 실패: {e}")
                    self.account_manager = None
            
            # 초기 데이터 로드
            self._load_initial_data()
            
            # 메인 루프
            while self.running:
                try:
                    self._update_account_data()
                    self._update_strategy_status()
                    self.msleep(self.update_interval * 1000)
                except Exception as e:
                    print(f"⚠️ 업데이트 오류: {e}")
                    self.msleep(5000)
                    
        except Exception as e:
            print(f"❌ TradingDataThread 오류: {e}")
            traceback.print_exc()
        finally:
            self._cleanup()
            print("⏹️ TradingDataThread 종료됨")
    
    def stop(self):
        """스레드 중지"""
        print("🛑 TradingDataThread 중지 요청됨")
        self.running = False
        self.stop_websocket()
    
    def _load_initial_data(self):
        """초기 데이터 로드"""
        if self.account_manager:
            try:
                balance = self.account_manager.get_account_balance()
                if balance:
                    self.account_data = balance
                    self.account_updated.emit(balance)
            except Exception as e:
                print(f"⚠️ 초기 잔고 로드 실패: {e}")
    
    def _update_account_data(self):
        """계정 데이터 업데이트"""
        if self.account_manager:
            try:
                balance = self.account_manager.get_account_balance()
                if balance:
                    self.account_data = balance
                    self.account_updated.emit(balance)
            except Exception as e:
                pass  # 조용히 실패
    
    def _update_strategy_status(self):
        """전략 상태 업데이트"""
        if self.strategy_manager:
            try:
                if STRATEGY_V2_AVAILABLE:
                    # v2: get_total_status() 사용
                    status = self.strategy_manager.get_total_status()
                else:
                    # 기존: get_status() 또는 유사 메서드
                    status = getattr(self.strategy_manager, 'get_status', lambda: {})()
                
                if status:
                    self.strategy_updated.emit(status)
            except Exception as e:
                pass  # 조용히 실패
    
    def _on_price_update(self, symbol: str, price: float, price_info: dict):
        """가격 업데이트 콜백"""
        self.latest_prices[symbol] = price
        self.price_updated.emit(symbol, price, price_info)
    
    def _on_connection_status(self, connected: bool, message: str = ""):
        """연결 상태 콜백"""
        self.connection_status_changed.emit(connected, message)
    
    def _on_account_update(self, account_data: dict):
        """계정 업데이트 콜백"""
        self.account_data = account_data
        self.account_updated.emit(account_data)
    
    def _on_position_update(self, position_data: dict):
        """포지션 업데이트 콜백"""
        self.position_updated.emit(position_data)
    
    def _cleanup(self):
        """정리"""
        self.stop_websocket()
        self.account_manager = None
        self.ws_handler = None
        self.strategy_manager = None


# 테스트
if __name__ == "__main__":
    print("TradingDataThread 테스트")
    print(f"  - CONFIG_AVAILABLE: {CONFIG_AVAILABLE}")
    print(f"  - ACCOUNT_MANAGER_AVAILABLE: {ACCOUNT_MANAGER_AVAILABLE}")
    print(f"  - WEBSOCKET_AVAILABLE: {WEBSOCKET_AVAILABLE}")
    print(f"  - STRATEGY_V2_AVAILABLE: {STRATEGY_V2_AVAILABLE}")
    print(f"  - TRADING_MODULES_AVAILABLE: {TRADING_MODULES_AVAILABLE}")
