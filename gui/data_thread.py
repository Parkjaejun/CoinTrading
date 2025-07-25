# gui/data_thread.py
"""
GUI용 데이터 수집 스레드 - 수정된 버전
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
    balance_updated = pyqtSignal(dict)  # 잔액 정보 업데이트
    price_updated = pyqtSignal(str, float, dict)  # 가격 업데이트 (심볼, 가격, 추가정보)
    positions_updated = pyqtSignal(list)  # 포지션 업데이트
    strategy_updated = pyqtSignal(dict)  # 전략 상태 업데이트
    connection_changed = pyqtSignal(bool)  # 연결 상태 변경
    error_occurred = pyqtSignal(str)  # 에러 발생
    
    def __init__(self, account_manager=None):
        """
        생성자
        
        Args:
            account_manager: AccountManager 인스턴스 (선택사항)
        """
        super().__init__()
        self.running = False
        self.account_manager = account_manager
        self.last_price_update = 0
        self.last_balance_update = 0
        self.last_position_update = 0
        
        # 업데이트 간격 (초)
        self.price_update_interval = 3  # 3초마다 가격 업데이트
        self.balance_update_interval = 10  # 10초마다 잔액 업데이트
        self.position_update_interval = 5  # 5초마다 포지션 업데이트
        
        # 연결 상태
        self.is_connected = False
        
        # AccountManager 초기화
        if not self.account_manager and ACCOUNT_MANAGER_AVAILABLE:
            try:
                self.account_manager = AccountManager()
                self.is_connected = True
                print("✅ TradingDataThread - AccountManager 초기화 성공")
            except Exception as e:
                print(f"❌ TradingDataThread - AccountManager 초기화 실패: {e}")
                self.is_connected = False
        elif self.account_manager:
            self.is_connected = True
            print("✅ TradingDataThread - 외부 AccountManager 사용")
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
                
                # 잔액 정보 업데이트
                if current_time - self.last_balance_update >= self.balance_update_interval:
                    self.update_balance_info()
                    self.last_balance_update = current_time
                
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
    
    def update_balance_info(self):
        """GUI 안전한 실제 계좌 잔액 정보 업데이트"""
        if not self.account_manager:
            self.emit_dummy_balance_data()
            return
        
        try:
            # AccountManager의 get_account_balance() 메서드 직접 사용
            # 이 메서드는 이미 config.py의 make_api_request를 사용함
            raw_balance = self.account_manager.get_account_balance()
            
            if raw_balance:
                # 실제 잔액 파싱 (main.py 방식과 동일)
                parsed_balance = {
                    'currencies': {},
                    'total_equity': 0.0,
                    'usdt_balance': 0.0,
                    'available_balance': 0.0,
                    'margin_balance': 0.0,
                    'unrealized_pnl': 0.0
                }
                
                # 총 자산
                total_eq = raw_balance.get('totalEq', '0')
                if total_eq == '' or total_eq is None:
                    total_eq = '0'
                parsed_balance['total_equity'] = float(total_eq)
                
                # 미실현 손익
                upl = raw_balance.get('upl', '0')
                if upl == '' or upl is None:
                    upl = '0'
                parsed_balance['unrealized_pnl'] = float(upl)
                
                # 각 통화별 잔액 파싱
                for detail in raw_balance.get('details', []):
                    ccy = detail['ccy']
                    cash_bal = detail.get('cashBal', '0')
                    avail_bal = detail.get('availBal', '0')
                    
                    # 빈 문자열 처리
                    if cash_bal == '':
                        cash_bal = '0'
                    if avail_bal == '':
                        avail_bal = '0'
                    
                    cash_bal = float(cash_bal)
                    avail_bal = float(avail_bal)
                    
                    if cash_bal > 0.001:  # 0.001 이상만 저장
                        parsed_balance['currencies'][ccy] = {
                            'total': cash_bal,
                            'available': avail_bal,
                            'frozen': cash_bal - avail_bal
                        }
                        
                        # USDT 특별 처리
                        if ccy == 'USDT':
                            parsed_balance['usdt_balance'] = cash_bal
                            parsed_balance['available_balance'] = avail_bal
                
                # 마진 잔액 계산
                parsed_balance['margin_balance'] = parsed_balance['total_equity'] - parsed_balance['unrealized_pnl']
                
                # GUI에 실제 데이터 전송
                self.balance_updated.emit(parsed_balance)
                
                # 연결 상태 복구
                if not self.is_connected:
                    self.is_connected = True
                    self.connection_changed.emit(True)
                    print("✅ 실제 잔액 API 연결 복구됨")
                
                # 성공 로그
                usdt_balance = parsed_balance['usdt_balance']
                total_equity = parsed_balance['total_equity']
                print(f"💰 실제 잔액 성공: USDT ${usdt_balance:.6f}, 총 자산 ${total_equity:.2f}")
                
            else:
                print("⚠️ AccountManager에서 None 반환 - API 인증 문제 가능성")
                self.emit_dummy_balance_data()
                
                # 연결 끊김 처리
                if self.is_connected:
                    self.is_connected = False
                    self.connection_changed.emit(False)
                
        except Exception as e:
            error_msg = f"실제 잔액 정보 업데이트 오류: {e}"
            print(f"⚠️ {error_msg}")
            self.error_occurred.emit(error_msg)
            
            # 연결 끊김 처리
            if self.is_connected:
                self.is_connected = False
                self.connection_changed.emit(False)
            
            # 더미 데이터라도 전송
            self.emit_dummy_balance_data()

    def emit_dummy_balance_data(self):
        """더미 잔액 데이터 전송"""
        dummy_balance = {
            'total_equity': 1000.0,
            'usdt_balance': 1000.0,
            'available_balance': 1000.0,
            'margin_balance': 0.0,
            'unrealized_pnl': 0.0,
            'currencies': {
                'USDT': {
                    'balance': 1000.0,
                    'available': 1000.0,
                    'frozen': 0.0
                }
            },
            'is_dummy': True  # 더미 데이터임을 표시
        }
        
        self.balance_updated.emit(dummy_balance)
    
    def update_price_info(self):
        """공개 API를 사용한 실제 코인 가격 정보 업데이트 (인증 불필요)"""
        try:
            import requests
            
            # 공개 API 사용 (인증 불필요)
            symbols = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']
            
            for symbol in symbols:
                try:
                    # OKX 공개 API: 인증 없이 ticker 데이터 조회
                    url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}"
                    
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get('code') == '0' and data.get('data'):
                            ticker_data = data['data'][0]
                            
                            # 실제 가격 정보 파싱
                            price = float(ticker_data.get('last', 0))
                            open_price = float(ticker_data.get('open24h', 0))
                            high_price = float(ticker_data.get('high24h', 0))
                            low_price = float(ticker_data.get('low24h', 0))
                            volume = float(ticker_data.get('vol24h', 0))
                            
                            # 24시간 변화율 계산
                            change_24h = 0
                            if open_price > 0:
                                change_24h = ((price - open_price) / open_price) * 100
                            
                            price_info = {
                                'symbol': symbol,
                                'last': price,
                                'open24h': open_price,
                                'high24h': high_price,
                                'low24h': low_price,
                                'vol24h': volume,
                                'change_24h': change_24h,
                                'bid': float(ticker_data.get('bidPx', price * 0.9999)),
                                'ask': float(ticker_data.get('askPx', price * 1.0001)),
                                'timestamp': time.time(),
                                'source': 'public_api',  # 공개 API 소스 표시
                                'is_real': True
                            }
                            
                            # GUI에 실제 가격 데이터 전송
                            self.price_updated.emit(symbol, price, price_info)
                            
                            # 연결 상태 복구
                            if not self.is_connected:
                                self.is_connected = True
                                self.connection_changed.emit(True)
                                print("✅ 공개 API 가격 데이터 연결 활성화됨")
                            
                            # 주기적 로그 (60초마다)
                            if int(time.time()) % 60 == 0:
                                print(f"📊 실제 가격 (공개 API): {symbol} = ${price:,.2f} (24h: {change_24h:+.2f}%)")
                                
                        else:
                            print(f"⚠️ {symbol} 공개 API 응답 오류: {data.get('msg', 'Unknown')}")
                            continue
                            
                    else:
                        print(f"⚠️ {symbol} 공개 API HTTP 오류: {response.status_code}")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ {symbol} 네트워크 오류: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️ {symbol} 가격 조회 오류: {e}")
                    continue
            
            # 하나라도 성공했으면 연결 상태 활성화
            if not self.is_connected:
                self.is_connected = True
                self.connection_changed.emit(True)
                print("✅ 공개 API 가격 스트림 활성화됨")
                        
        except Exception as e:
            error_msg = f"공개 API 가격 정보 업데이트 오류: {e}"
            print(f"⚠️ {error_msg}")
            self.error_occurred.emit(error_msg)
            
            # 실패 시 더미 데이터로 폴백
            self.emit_dummy_price_data()

    def emit_dummy_price_data(self):
        """더미 가격 데이터 전송"""
        import random
        symbols = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']
        base_prices = {
            'BTC-USDT-SWAP': 65000,
            'ETH-USDT-SWAP': 3500,
            'SOL-USDT-SWAP': 150
        }
        
        for symbol in symbols:
            base_price = base_prices.get(symbol, 100)
            price = base_price * (1 + (random.random() - 0.5) * 0.02)
            
            price_info = {
                'symbol': symbol,
                'bid': price * 0.9999,
                'ask': price * 1.0001,
                'volume_24h': random.randint(100000, 1000000),
                'change_24h': (random.random() - 0.5) * 0.1,
                'timestamp': time.time(),
                'is_dummy': True
            }
            
            self.price_updated.emit(symbol, price, price_info)
    
    def update_position_info(self):
        """간단한 실제 포지션 정보 업데이트"""
        if not self.account_manager:
            self.emit_dummy_position_data()
            return
        
        try:
            # AccountManager의 get_positions() 메서드 사용
            positions_response = self.account_manager.get_positions()
            
            if positions_response and isinstance(positions_response, list):
                # 활성 포지션만 필터링 (포지션 크기가 0이 아닌 것)
                active_positions = []
                for position in positions_response:
                    pos_size = float(position.get('pos', 0))
                    if abs(pos_size) > 0.001:  # 0.001 이상만 활성 포지션으로 간주
                        active_positions.append(position)
                
                # GUI에 실제 포지션 데이터 전송
                self.positions_updated.emit(active_positions)
                
                # 포지션 상태 로그
                if active_positions:
                    total_upl = sum(float(pos.get('upl', 0)) for pos in active_positions)
                    print(f"📈 실제 포지션: {len(active_positions)}개 활성, 총 미실현손익: ${total_upl:+.2f}")
                else:
                    print("📊 실제 포지션: 활성 포지션 없음")
                    
            else:
                print("⚠️ 포지션 데이터가 예상된 형식이 아님")
                # 빈 포지션 리스트 전송
                self.positions_updated.emit([])
                
        except Exception as e:
            error_msg = f"포지션 정보 업데이트 오류: {e}"
            print(f"⚠️ {error_msg}")
            self.error_occurred.emit(error_msg)
            
            # 더미 데이터라도 전송
            self.emit_dummy_position_data()

    def emit_dummy_position_data(self):
        """더미 포지션 데이터 전송"""
        import random
        
        # 가끔 더미 포지션 생성
        if random.random() < 0.3:  # 30% 확률로 포지션 있음
            positions = [
                {
                    'instId': 'BTC-USDT-SWAP',
                    'posSide': 'long',
                    'pos': '0.1',
                    'avgPx': '64500',
                    'upl': str(random.randint(-100, 200)),  # 미실현 손익
                    'uplRatio': str((random.random() - 0.3) * 0.1),  # 수익률
                    'margin': '645',
                    'lever': '10',
                    'uTime': str(int(time.time() * 1000)),
                    'is_dummy': True
                }
            ]
        else:
            positions = []
        
        self.positions_updated.emit(positions)
    
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
                'last_trade_time': datetime.now().isoformat(),
                'is_dummy': True
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
    
    def on_balance_updated(data):
        print(f"📊 잔액 업데이트: USDT ${data.get('usdt_balance', 0):,.2f}")
    
    def on_price_updated(symbol, price, info):
        print(f"💰 가격 업데이트: {symbol} = ${price:,.2f}")
    
    def on_positions_updated(positions):
        print(f"📋 포지션 업데이트: {len(positions)}개")
    
    def on_connection_changed(connected):
        print(f"🔗 연결 상태: {'연결됨' if connected else '끊어짐'}")
    
    def on_error(error):
        print(f"❌ 오류: {error}")
    
    # 데이터 스레드 생성 및 연결
    thread = TradingDataThread()
    thread.balance_updated.connect(on_balance_updated)
    thread.price_updated.connect(on_price_updated)
    thread.positions_updated.connect(on_positions_updated)
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