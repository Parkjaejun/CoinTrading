# gui/data_thread.py
"""
GUI용 데이터 수집 스레드
실시간 가격, 계정 정보, 포지션 등을 주기적으로 업데이트
"""

import time
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

from PyQt5.QtCore import QThread, pyqtSignal

try:
    from okx.account_manager import AccountManager
    from gui.balance_manager import GUIBalanceManager
    ACCOUNT_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ AccountManager 임포트 실패: {e}")
    ACCOUNT_MANAGER_AVAILABLE = False

class TradingDataThread(QThread):
    """거래 데이터 수집 스레드"""
    
    # 시그널 정의
    account_updated = pyqtSignal(dict)  # 계정 정보 업데이트
    price_updated = pyqtSignal(str, float, dict)  # 가격 업데이트 (심볼, 가격, 추가정보)
    position_updated = pyqtSignal(dict)  # 포지션 업데이트
    strategy_updated = pyqtSignal(dict)  # 전략 상태 업데이트
    connection_changed = pyqtSignal(bool)  # 연결 상태 변경
    error_occurred = pyqtSignal(str)  # 에러 발생
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.account_manager = None
        self.last_price_update = 0
        self.last_account_update = 0
        self.last_position_update = 0
        
        # 업데이트 간격 (초)
        self.price_update_interval = 2  # 2초마다 가격 업데이트
        self.account_update_interval = 10  # 10초마다 계정 업데이트
        self.position_update_interval = 5  # 5초마다 포지션 업데이트
        
        # 연결 상태
        self.is_connected = False
        
        # AccountManager 초기화
        if ACCOUNT_MANAGER_AVAILABLE:
            try:
                self.account_manager = AccountManager()
                self.is_connected = True
                print("✅ TradingDataThread - AccountManager 초기화 성공")
            except Exception as e:
                print(f"❌ TradingDataThread - AccountManager 초기화 실패: {e}")
                self.is_connected = False
        else:
            print("⚠️ TradingDataThread - AccountManager 사용 불가")
    
    def run(self):
        """스레드 실행"""
        self.running = True
        print("🔄 TradingDataThread 시작됨")
        
        # 초기 연결 상태 전송
        self.connection_changed.emit(self.is_connected)
        
        while self.running:
            try:
                current_time = time.time()
                
                # 계정 정보 업데이트
                if current_time - self.last_account_update >= self.account_update_interval:
                    self.update_account_info()
                    self.last_account_update = current_time
                
                # 가격 정보 업데이트
                if current_time - self.last_price_update >= self.price_update_interval:
                    self.update_price_info()
                    self.last_price_update = current_time
                
                # 포지션 정보 업데이트
                if current_time - self.last_position_update >= self.position_update_interval:
                    self.update_position_info()
                    self.last_position_update = current_time
                
                # 전략 상태 업데이트 (임시 데이터)
                self.update_strategy_info()
                
                # 1초 대기
                time.sleep(1)
                
            except Exception as e:
                error_msg = f"데이터 스레드 오류: {e}"
                print(f"❌ {error_msg}")
                self.error_occurred.emit(error_msg)
                
                # 연결 끊김 처리
                if self.is_connected:
                    self.is_connected = False
                    self.connection_changed.emit(False)
                
                time.sleep(5)  # 5초 후 재시도
        
        print("⏹️ TradingDataThread 종료됨")
    
    def update_account_info(self):
        """계정 정보 업데이트"""
        if not self.account_manager:
            return
        
        try:
            # 잔액 정보 가져오기
            raw_balance = self.account_manager.get_account_balance()
            
            if raw_balance:
                # GUIBalanceManager로 파싱
                if GUIBalanceManager:
                    parsed_balance = GUIBalanceManager.parse_okx_balance(raw_balance)
                    self.account_updated.emit(parsed_balance)
                else:
                    # 기본 처리
                    self.account_updated.emit({
                        'total_equity': 0,
                        'usdt_balance': 0,
                        'currencies': {}
                    })
                
                # 연결 상태 복구
                if not self.is_connected:
                    self.is_connected = True
                    self.connection_changed.emit(True)
            
        except Exception as e:
            error_msg = f"계정 정보 업데이트 오류: {e}"
            print(f"⚠️ {error_msg}")
            self.error_occurred.emit(error_msg)
            
            # 연결 문제로 간주
            if self.is_connected:
                self.is_connected = False
                self.connection_changed.emit(False)
    
    def update_price_info(self):
        """가격 정보 업데이트"""
        if not self.account_manager:
            # 임시 더미 데이터
            self.emit_dummy_price_data()
            return
        
        try:
            # 주요 심볼들의 가격 정보
            symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
            
            for symbol in symbols:
                try:
                    # OKX API에서 가격 정보 가져오기 (실제 구현 필요)
                    # price_data = self.account_manager.get_ticker(symbol)
                    
                    # 임시로 더미 데이터 사용
                    if symbol == "BTC-USDT-SWAP":
                        price = 65000 + (time.time() % 100 - 50) * 10
                    elif symbol == "ETH-USDT-SWAP":
                        price = 3200 + (time.time() % 50 - 25) * 5
                    else:  # SOL
                        price = 150 + (time.time() % 20 - 10) * 2
                    
                    price_info = {
                        'change_percent': (time.time() % 10 - 5) * 0.5,
                        'volume_24h': 1000000,
                        'timestamp': time.time()
                    }
                    
                    self.price_updated.emit(symbol, price, price_info)
                    
                except Exception as e:
                    print(f"⚠️ {symbol} 가격 업데이트 오류: {e}")
            
        except Exception as e:
            error_msg = f"가격 정보 업데이트 오류: {e}"
            print(f"⚠️ {error_msg}")
            self.error_occurred.emit(error_msg)
    
    def emit_dummy_price_data(self):
        """더미 가격 데이터 전송"""
        symbols_prices = {
            "BTC-USDT-SWAP": 65000,
            "ETH-USDT-SWAP": 3200,
            "SOL-USDT-SWAP": 150
        }
        
        for symbol, base_price in symbols_prices.items():
            # 시간에 따른 변동
            variation = (time.time() % 100 - 50) * (base_price * 0.001)
            price = base_price + variation
            
            price_info = {
                'change_percent': (time.time() % 10 - 5) * 0.5,
                'volume_24h': 1000000,
                'timestamp': time.time()
            }
            
            self.price_updated.emit(symbol, price, price_info)
    
    def update_position_info(self):
        """포지션 정보 업데이트"""
        if not self.account_manager:
            # 임시 더미 데이터
            self.emit_dummy_position_data()
            return
        
        try:
            # 실제 포지션 정보 가져오기 (구현 필요)
            # positions = self.account_manager.get_positions()
            
            # 임시 더미 데이터
            positions_data = {
                'positions': [
                    {
                        'symbol': 'BTC-USDT-SWAP',
                        'side': 'long',
                        'size': 0.1,
                        'entry_price': 64500,
                        'current_price': 65000,
                        'unrealized_pnl': 50.0,
                        'margin_used': 645.0
                    }
                ],
                'total_unrealized_pnl': 50.0,
                'total_margin_used': 645.0,
                'margin_ratio': 0.1
            }
            
            self.position_updated.emit(positions_data)
            
        except Exception as e:
            error_msg = f"포지션 정보 업데이트 오류: {e}"
            print(f"⚠️ {error_msg}")
            self.error_occurred.emit(error_msg)
    
    def emit_dummy_position_data(self):
        """더미 포지션 데이터 전송"""
        positions_data = {
            'positions': [],
            'total_unrealized_pnl': 0.0,
            'total_margin_used': 0.0,
            'margin_ratio': 0.0
        }
        
        self.position_updated.emit(positions_data)
    
    def update_strategy_info(self):
        """전략 상태 정보 업데이트"""
        try:
            # 임시 전략 상태 데이터
            strategy_data = {
                'is_running': False,
                'active_strategies': 0,
                'uptime': int(time.time() % 3600),  # 1시간 단위로 리셋
                'total_trades': int(time.time() % 100),
                'total_pnl': (time.time() % 200 - 100) * 5,
                'last_signal': 'none',
                'last_trade_time': datetime.now().isoformat()
            }
            
            self.strategy_updated.emit(strategy_data)
            
        except Exception as e:
            error_msg = f"전략 정보 업데이트 오류: {e}"
            print(f"⚠️ {error_msg}")
            self.error_occurred.emit(error_msg)
    
    def stop(self):
        """스레드 중지"""
        print("🛑 TradingDataThread 중지 요청됨")
        self.running = False
    
    def is_running(self):
        """실행 상태 확인"""
        return self.running
    
    def reconnect(self):
        """재연결 시도"""
        if ACCOUNT_MANAGER_AVAILABLE:
            try:
                self.account_manager = AccountManager()
                self.is_connected = True
                self.connection_changed.emit(True)
                print("✅ TradingDataThread 재연결 성공")
            except Exception as e:
                print(f"❌ TradingDataThread 재연결 실패: {e}")
                self.is_connected = False
                self.connection_changed.emit(False)
        else:
            print("⚠️ AccountManager 사용 불가로 재연결 불가")

# 테스트 함수
def test_data_thread():
    """데이터 스레드 테스트"""
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    def on_account_updated(data):
        print(f"📊 계정 업데이트: {data}")
    
    def on_price_updated(symbol, price, info):
        print(f"💰 가격 업데이트: {symbol} = ${price:.2f}")
    
    def on_position_updated(data):
        print(f"📋 포지션 업데이트: {len(data.get('positions', []))}개")
    
    def on_connection_changed(connected):
        print(f"🔗 연결 상태: {'연결됨' if connected else '끊어짐'}")
    
    def on_error(error):
        print(f"❌ 오류: {error}")
    
    # 데이터 스레드 생성 및 연결
    thread = TradingDataThread()
    thread.account_updated.connect(on_account_updated)
    thread.price_updated.connect(on_price_updated)
    thread.position_updated.connect(on_position_updated)
    thread.connection_changed.connect(on_connection_changed)
    thread.error_occurred.connect(on_error)
    
    print("🚀 데이터 스레드 테스트 시작...")
    thread.start()
    
    try:
        # 10초 후 종료
        import threading
        def stop_after_delay():
            time.sleep(10)
            thread.stop()
            app.quit()
        
        threading.Thread(target=stop_after_delay, daemon=True).start()
        
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("🛑 테스트 중단됨")
        thread.stop()
        thread.wait()

if __name__ == "__main__":
    test_data_thread()