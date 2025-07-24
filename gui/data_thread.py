# gui/data_thread.py
"""
거래 데이터 처리 스레드
실시간 데이터 수집 및 처리
"""

import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

from PyQt5.QtCore import QThread, pyqtSignal

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from gui.balance_manager import GUIBalanceManager
    from okx.account_manager import AccountManager
    from utils.logger import log_system, log_error
    from utils.websocket_handler import WebSocketHandler
    from main import TradingSystem
except ImportError as e:
    print(f"⚠️ 모듈 임포트 경고: {e}")

class TradingDataThread(QThread):
    """거래 데이터 처리 스레드"""
    
    # 시그널 정의
    account_updated = pyqtSignal(dict)
    price_updated = pyqtSignal(str, float, dict)
    position_updated = pyqtSignal(dict)
    trade_executed = pyqtSignal(dict)
    strategy_updated = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    system_stats_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.account_manager = None
        self.websocket_handler = None
        self.trading_system = None
        self.running = False
        self.account_data = {}
        self.latest_prices = {}
        self.update_interval = 3  # 3초마다 업데이트
        
    def run(self):
        """메인 실행 루프"""
        try:
            self.running = True
            print("🚀 거래 데이터 스레드 시작")
            
            # 연결 설정
            if not self._setup_connections():
                self.connection_status_changed.emit(False)
                return
            
            self.connection_status_changed.emit(True)
            
            # 초기 데이터 로드
            self._load_initial_data()
            
            # 메인 업데이트 루프
            while self.running:
                try:
                    self._update_account_data()
                    self._update_system_stats()
                    self._check_trading_system_status()
                    
                    self.msleep(self.update_interval * 1000)
                    
                except Exception as e:
                    print(f"⚠️ 업데이트 루프 오류: {e}")
                    self.error_occurred.emit(f"데이터 업데이트 오류: {str(e)}")
                    self.msleep(10000)  # 오류 시 10초 대기
                    
        except Exception as e:
            print(f"❌ 데이터 스레드 치명적 오류: {e}")
            traceback.print_exc()
            self.error_occurred.emit(f"스레드 오류: {str(e)}")
            self.connection_status_changed.emit(False)
        
        finally:
            self._cleanup()
    
    def _setup_connections(self) -> bool:
        """연결 설정"""
        try:
            # AccountManager 초기화
            print("🔗 AccountManager 초기화...")
            self.account_manager = AccountManager()
            
            # 연결 테스트
            test_data = self.account_manager.get_account_balance()
            if not test_data:
                print("❌ API 연결 테스트 실패")
                return False
            
            print("✅ API 연결 테스트 성공")
            
            # WebSocket 핸들러 초기화
            try:
                self.websocket_handler = WebSocketHandler(['BTC-USDT-SWAP', 'ETH-USDT-SWAP'], ['tickers'])
                self.websocket_handler.start_ws(['BTC-USDT-SWAP', 'ETH-USDT-SWAP'])
                print("✅ WebSocket 핸들러 초기화 완료")
            except Exception as e:
                print(f"⚠️ WebSocket 초기화 실패 (계속 진행): {e}")
                self.websocket_handler = None
            
            return True
            
        except Exception as e:
            print(f"❌ 연결 설정 실패: {e}")
            return False
    
    def _load_initial_data(self):
        """초기 데이터 로드"""
        try:
            print("📊 초기 데이터 로드 중...")
            self._update_account_data()
            self._update_system_stats()
            print("✅ 초기 데이터 로드 완료")
        except Exception as e:
            print(f"⚠️ 초기 데이터 로드 실패: {e}")
    
    def _update_account_data(self):
        """계정 정보 업데이트"""
        try:
            if not self.account_manager:
                return
            
            raw_balance_data = self.account_manager.get_account_balance()
            
            if raw_balance_data:
                parsed_balances = GUIBalanceManager.parse_okx_balance(raw_balance_data)
                
                if self._validate_balance_data(parsed_balances):
                    self.account_data = parsed_balances
                    self.account_updated.emit(parsed_balances)
                    
                    # 간단한 로그 (30초에 한 번)
                    if not hasattr(self, '_last_balance_log'):
                        self._last_balance_log = 0
                    
                    current_time = time.time()
                    if current_time - self._last_balance_log >= 30:
                        usdt_balance = GUIBalanceManager.get_usdt_balance(parsed_balances)
                        total_equity = GUIBalanceManager.get_total_equity(parsed_balances)
                        print(f"💰 계정 업데이트: USDT ${usdt_balance:.2f}, 총 자산 ${total_equity:.2f}")
                        self._last_balance_log = current_time
            
        except Exception as e:
            print(f"❌ 계정 정보 업데이트 오류: {e}")
            self.error_occurred.emit(f"계정 정보 오류: {str(e)}")
    
    def _update_system_stats(self):
        """시스템 통계 업데이트"""
        try:
            if not PSUTIL_AVAILABLE:
                return
            
            stats = {
                'cpu_percent': psutil.cpu_percent(interval=None),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'timestamp': datetime.now()
            }
            
            self.system_stats_updated.emit(stats)
            
        except Exception as e:
            print(f"⚠️ 시스템 통계 업데이트 오류: {e}")
    
    def _check_trading_system_status(self):
        """거래 시스템 상태 확인"""
        try:
            # TradingSystem 상태 확인 (있다면)
            if hasattr(self, 'trading_system') and self.trading_system:
                status = {
                    'is_running': getattr(self.trading_system, 'is_running', False),
                    'active_strategies': getattr(self.trading_system, 'active_strategies', 0),
                    'uptime': getattr(self.trading_system, 'uptime', 0)
                }
                self.strategy_updated.emit(status)
                
        except Exception as e:
            print(f"⚠️ 거래 시스템 상태 확인 오류: {e}")
    
    def _validate_balance_data(self, data: Dict[str, Any]) -> bool:
        """잔액 데이터 검증"""
        try:
            if not isinstance(data, dict):
                return False
            
            if 'USDT' not in data:
                return False
            
            usdt_data = data['USDT']
            if not isinstance(usdt_data, dict):
                return False
            
            required_keys = ['total', 'available', 'frozen']
            for key in required_keys:
                if key not in usdt_data:
                    return False
                
                value = usdt_data[key]
                if not isinstance(value, (int, float)):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _cleanup(self):
        """정리 작업"""
        try:
            print("🧹 데이터 스레드 정리 중...")
            
            if self.websocket_handler:
                try:
                    self.websocket_handler.stop_ws()
                except:
                    pass
            
            self.running = False
            print("✅ 데이터 스레드 정리 완료")
            
        except Exception as e:
            print(f"⚠️ 정리 작업 오류: {e}")
    
    def stop(self):
        """스레드 중지"""
        self.running = False
    
    def start_trading_system(self):
        """거래 시스템 시작"""
        try:
            if not self.trading_system:
                self.trading_system = TradingSystem()
            
            if self.trading_system.initialize_system():
                # 별도 스레드에서 시작
                import threading
                trading_thread = threading.Thread(target=self.trading_system.start_trading)
                trading_thread.daemon = True
                trading_thread.start()
                return True
            return False
            
        except Exception as e:
            print(f"❌ 거래 시스템 시작 오류: {e}")
            self.error_occurred.emit(f"거래 시스템 시작 오류: {str(e)}")
            return False
    
    def stop_trading_system(self):
        """거래 시스템 중지"""
        try:
            if self.trading_system and hasattr(self.trading_system, 'stop_trading'):
                self.trading_system.stop_trading()
                return True
            return False
            
        except Exception as e:
            print(f"❌ 거래 시스템 중지 오류: {e}")
            self.error_occurred.emit(f"거래 시스템 중지 오류: {str(e)}")
            return False