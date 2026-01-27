# gui/data_thread.py
"""
거래 데이터 스레드 - BTC 전용, 로그 정리 버전

변경 사항:
- BTC만 감시 (ETH 비활성화)
- 불필요한 로그 제거
- 가격/잔고 업데이트 로그 제거
"""

import time
from datetime import datetime
from typing import Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal

try:
    from config import make_api_request
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

try:
    from okx.account_manager import AccountManager
    ACCOUNT_MANAGER_AVAILABLE = True
except ImportError:
    ACCOUNT_MANAGER_AVAILABLE = False


class TradingDataThread(QThread):
    """거래 데이터 스레드 - BTC 전용"""
    
    # 시그널
    price_updated = pyqtSignal(str, float, dict)
    balance_updated = pyqtSignal(dict)
    positions_updated = pyqtSignal(list)
    connection_changed = pyqtSignal(bool)
    signal_lost = pyqtSignal()
    error_occurred = pyqtSignal(str)
    strategy_updated = pyqtSignal(dict)
    
    def __init__(self, account_manager=None, parent=None):
        super().__init__(parent)
        
        self.running = False
        self.is_connected = False
        self.account_manager = account_manager
        
        # 업데이트 간격 (초)
        self.balance_update_interval = 10
        self.price_update_interval = 5
        self.position_update_interval = 10
        
        # 마지막 업데이트 시간
        self.last_balance_update = 0
        self.last_price_update = 0
        self.last_position_update = 0
        
        # 연속 실패 카운트
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        
        # BTC만 감시
        self.symbols = ['BTC-USDT-SWAP']
        self.latest_prices = {}
        
        # 전략 매니저
        self.strategy_manager = None
        
        # AccountManager 초기화
        self._init_account_manager()
    
    def _init_account_manager(self):
        """AccountManager 초기화"""
        if self.account_manager:
            self.is_connected = True
        elif ACCOUNT_MANAGER_AVAILABLE:
            try:
                self.account_manager = AccountManager(verbose=False)
                self.is_connected = True
            except:
                self.is_connected = False
    
    def run(self):
        """스레드 실행"""
        self.running = True
        self.connection_changed.emit(self.is_connected)
        
        # 초기화
        self._init_data()
        
        # 메인 루프
        while self.running:
            try:
                current_time = time.time()
                
                # 잔고
                if current_time - self.last_balance_update >= self.balance_update_interval:
                    if self.update_balance():
                        self.consecutive_failures = 0
                    self.last_balance_update = current_time
                    time.sleep(1)
                
                if not self.running:
                    break
                
                # 가격
                if current_time - self.last_price_update >= self.price_update_interval:
                    self.update_price()
                    self.last_price_update = current_time
                    time.sleep(1)
                
                if not self.running:
                    break
                
                # 포지션
                if current_time - self.last_position_update >= self.position_update_interval:
                    self.update_positions()
                    self.last_position_update = current_time
                    time.sleep(1)
                
                # 연결 상태
                if self.consecutive_failures == 0 and not self.is_connected:
                    self.is_connected = True
                    self.connection_changed.emit(True)
                
                time.sleep(2)
                
            except Exception as e:
                self.error_occurred.emit(str(e))
                self.handle_failure()
                time.sleep(5)
    
    def _init_data(self):
        """초기 데이터 로드"""
        try:
            self.update_balance()
            self.last_balance_update = time.time()
        except:
            pass
        time.sleep(1)
        
        try:
            self.update_price()
            self.last_price_update = time.time()
        except:
            pass
        time.sleep(1)
        
        try:
            self.update_positions()
            self.last_position_update = time.time()
        except:
            pass
    
    def stop(self):
        """중지"""
        self.running = False
    
    def handle_failure(self):
        """실패 처리"""
        self.consecutive_failures += 1
        
        if self.consecutive_failures >= self.max_consecutive_failures:
            if self.is_connected:
                self.is_connected = False
                self.connection_changed.emit(False)
                self.signal_lost.emit()
    
    def update_balance(self) -> bool:
        """잔고 업데이트"""
        if not self.account_manager:
            return False
        
        try:
            raw = self.account_manager.get_account_balance()
            
            if raw:
                data = {
                    'currencies': {},
                    'total_equity': float(raw.get('totalEq', 0)),
                    'usdt_balance': 0.0,
                    'available_balance': 0.0,
                }
                
                for detail in raw.get('details', []):
                    ccy = detail.get('ccy', '')
                    data['currencies'][ccy] = {
                        'equity': float(detail.get('eq', 0)),
                        'available': float(detail.get('availBal', 0)),
                        'frozen': float(detail.get('frozenBal', 0)),
                    }
                    
                    if ccy == 'USDT':
                        data['usdt_balance'] = float(detail.get('eq', 0))
                        data['available_balance'] = float(detail.get('availBal', 0))
                
                self.balance_updated.emit(data)
                return True
            
            return False
            
        except:
            return False
    
    def update_price(self) -> bool:
        """가격 업데이트 - BTC만"""
        if not CONFIG_AVAILABLE:
            return False
        
        try:
            symbol = 'BTC-USDT-SWAP'
            
            response = make_api_request(
                'GET',
                '/api/v5/market/ticker',
                params={'instId': symbol}
            )
            
            if response and response.get('code') == '0':
                data = response['data'][0]
                price = float(data.get('last', 0))
                
                if price > 0:
                    self.latest_prices[symbol] = price
                    
                    info = {
                        'last': price,
                        'high24h': float(data.get('high24h', 0)),
                        'low24h': float(data.get('low24h', 0)),
                        'vol24h': float(data.get('vol24h', 0)),
                    }
                    
                    self.price_updated.emit(symbol, price, info)
                    return True
            
            return False
            
        except:
            return False
    
    def update_positions(self) -> bool:
        """포지션 업데이트"""
        if not self.account_manager:
            return False
        
        try:
            positions = self.account_manager.get_positions("SWAP")
            
            if positions is not None:
                # BTC 포지션만 필터링
                btc_positions = []
                for p in positions:
                    if 'BTC' in p.get('instId', ''):
                        try:
                            if abs(float(p.get('pos', 0))) > 0.001:
                                btc_positions.append(p)
                        except:
                            pass
                
                self.positions_updated.emit(btc_positions)
                return True
            
            self.positions_updated.emit([])
            return True
            
        except:
            self.positions_updated.emit([])
            return True
    
    def set_strategy_manager(self, manager):
        """전략 매니저 설정"""
        self.strategy_manager = manager