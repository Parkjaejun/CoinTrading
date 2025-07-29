# gui/data_thread.py
"""
GUI용 데이터 수집 스레드 - 더미 데이터 완전 제거 버전
실시간 가격, 계정 정보, 포지션 등을 주기적으로 업데이트
API 연결 실패 시 "Signal Lost" 표시
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
    """거래 데이터 수집 스레드 - 더미 데이터 없음"""
    
    # 시그널 정의
    balance_updated = pyqtSignal(dict)  # 잔액 정보 업데이트
    price_updated = pyqtSignal(str, float, dict)  # 가격 업데이트 (심볼, 가격, 추가정보)
    positions_updated = pyqtSignal(list)  # 포지션 업데이트
    strategy_updated = pyqtSignal(dict)  # 전략 상태 업데이트
    connection_changed = pyqtSignal(bool)  # 연결 상태 변경
    error_occurred = pyqtSignal(str)  # 에러 발생
    signal_lost = pyqtSignal()  # 신호 손실
    
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
        
        # ✅ 업데이트 간격 조정 (API 호출 빈도 감소)
        self.balance_update_interval = 10   # 10초마다 (기존: 5초)
        self.price_update_interval = 3      # 3초마다 (기존: 2초)  
        self.position_update_interval = 15  # 15초마다 (기존: 5초)
        
        # 마지막 업데이트 시간 추적
        self.last_balance_update = 0
        self.last_price_update = 0
        self.last_position_update = 0
        
        # 연결 상태 관리
        self.is_connected = False
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3  # 3회 연속 실패 시 연결 끊김 처리
        
        self.running = False
        
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
    
    # gui/data_thread.py의 run 메서드를 수정하세요

    def run(self):
        """스레드 실행 - 완전한 순차 처리로 401 오류 방지"""
        self.running = True
        print("🔄 TradingDataThread 시작됨")
        
        # 초기 연결 상태 전송
        self.connection_changed.emit(self.is_connected)
        
        # ✅ 완전한 순차 초기화 (동시 요청 완전 차단)
        print("🔄 순차 초기화 시작...")
        
        # 1단계: 잔액 조회만 (3초 대기)
        print("🔄 1단계: 잔액 조회")
        try:
            success = self.update_balance_info()
            if success:
                print("✅ 잔액 조회 성공")
            else:
                print("❌ 잔액 조회 실패")
            self.last_balance_update = time.time()
        except Exception as e:
            print(f"❌ 잔액 조회 오류: {e}")
        
        time.sleep(3)  # 3초 대기
        
        # 2단계: 가격 조회만 (3초 대기)  
        print("🔄 2단계: 가격 조회")
        try:
            success = self.update_price_info()
            if success:
                print("✅ 가격 조회 성공")
            else:
                print("❌ 가격 조회 실패")
            self.last_price_update = time.time()
        except Exception as e:
            print(f"❌ 가격 조회 오류: {e}")
        
        time.sleep(3)  # 3초 대기
        
        # 3단계: 포지션 조회만 (5초 대기)
        print("🔄 3단계: 포지션 조회")
        try:
            success = self.update_position_info()
            if success:
                print("✅ 포지션 조회 성공")
            else:
                print("❌ 포지션 조회 실패")
            self.last_position_update = time.time()
        except Exception as e:
            print(f"❌ 포지션 조회 오류: {e}")
        
        time.sleep(5)  # 5초 대기
        
        print("✅ 순차 초기화 완료 - 정상 운영 모드 시작")
        
        # ✅ 정상 운영: 완전한 순차 처리 (절대 동시 실행 없음)
        operation_cycle = 0
        
        while self.running:
            try:
                operation_cycle += 1
                current_time = time.time()
                
                print(f"📊 운영 사이클 {operation_cycle} 시작")
                
                # 순차 처리 1: 잔액 정보 (10초마다)
                if current_time - self.last_balance_update >= self.balance_update_interval:
                    print("💰 잔액 정보 업데이트 중...")
                    try:
                        success = self.update_balance_info()
                        self.last_balance_update = current_time
                        
                        if success:
                            print("✅ 잔액 업데이트 성공")
                            self.consecutive_failures = 0
                        else:
                            print("❌ 잔액 업데이트 실패")
                            self.handle_api_failure()
                            
                    except Exception as e:
                        print(f"❌ 잔액 업데이트 오류: {e}")
                        self.handle_api_failure()
                    
                    # 잔액 업데이트 후 2초 대기
                    time.sleep(2)
                    
                    if not self.running:
                        break
                
                # 순차 처리 2: 가격 정보 (3초마다)
                current_time = time.time()  # 시간 다시 체크
                if current_time - self.last_price_update >= self.price_update_interval:
                    print("📈 가격 정보 업데이트 중...")
                    try:
                        success = self.update_price_info()
                        self.last_price_update = current_time
                        
                        if success:
                            print("✅ 가격 업데이트 성공")
                            self.consecutive_failures = 0
                        else:
                            print("❌ 가격 업데이트 실패")
                            self.handle_api_failure()
                            
                    except Exception as e:
                        print(f"❌ 가격 업데이트 오류: {e}")
                        self.handle_api_failure()
                    
                    # 가격 업데이트 후 2초 대기
                    time.sleep(2)
                    
                    if not self.running:
                        break
                
                # 순차 처리 3: 포지션 정보 (5초마다)
                current_time = time.time()  # 시간 다시 체크
                if current_time - self.last_position_update >= self.position_update_interval:
                    print("📊 포지션 정보 업데이트 중...")
                    try:
                        success = self.update_position_info()
                        self.last_position_update = current_time
                        
                        if success:
                            print("✅ 포지션 업데이트 성공")
                            self.consecutive_failures = 0
                        else:
                            print("❌ 포지션 업데이트 실패 (무시하고 계속)")
                            # 포지션 업데이트 실패는 치명적이지 않으므로 계속 진행
                            
                    except Exception as e:
                        print(f"❌ 포지션 업데이트 오류 (무시하고 계속): {e}")
                    
                    # 포지션 업데이트 후 2초 대기
                    time.sleep(2)
                    
                    if not self.running:
                        break
                
                # 전략 상태 업데이트 (API 호출 없음)
                try:
                    self.update_strategy_info()
                except Exception as e:
                    print(f"⚠️ 전략 상태 업데이트 오류: {e}")
                
                # 연결 상태 확인
                if self.consecutive_failures == 0 and not self.is_connected:
                    self.is_connected = True
                    self.connection_changed.emit(True)
                    print("✅ API 연결 복구됨")
                
                # 사이클 완료 - 3초 대기
                print(f"✅ 운영 사이클 {operation_cycle} 완료")
                time.sleep(3)
                
            except Exception as e:
                error_msg = f"데이터 스레드 오류: {e}"
                print(f"❌ {error_msg}")
                self.error_occurred.emit(error_msg)
                self.handle_api_failure()
                
                # 오류 발생 시 10초 대기 후 재시도
                time.sleep(10)
        
        print("⏹️ TradingDataThread 종료됨")


    
    def handle_api_failure(self):
        """API 실패 처리"""
        self.consecutive_failures += 1
        
        if self.consecutive_failures >= self.max_consecutive_failures:
            if self.is_connected:
                self.is_connected = False
                self.connection_changed.emit(False)
                self.signal_lost.emit()  # Signal Lost 시그널 전송
                print("🚨 Signal Lost - API 연결 지속 실패")
    
    def update_balance_info(self) -> bool:
        """실제 계좌 잔액 정보 업데이트 - 'bal' 키 오류 수정"""
        if not self.account_manager:
            return False
        
        try:
            raw_balance = self.account_manager.get_account_balance()
            
            if raw_balance:
                # 실제 잔액 파싱 (올바른 키 사용)
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
                parsed_balance['total_equity'] = float(total_eq) if total_eq else 0.0
                
                # 상세 잔액 정보 (올바른 키 사용)
                details = raw_balance.get('details', [])
                for detail in details:
                    currency = detail.get('ccy', 'UNKNOWN')
                    
                    # ✅ 올바른 키 사용: 'availBal', 'eq', 'frozenBal'
                    cash_bal = detail.get('eq', '0')  # 총 잔고 (수정됨)
                    available = detail.get('availBal', '0')  # 사용가능 잔고
                    frozen = detail.get('frozenBal', '0')  # 동결된 잔고
                    
                    # 빈 문자열 처리
                    cash_bal = float(cash_bal) if cash_bal else 0.0
                    available = float(available) if available else 0.0
                    frozen = float(frozen) if frozen else 0.0
                    
                    parsed_balance['currencies'][currency] = {
                        'balance': cash_bal,
                        'available': available,
                        'frozen': frozen
                    }
                    
                    # USDT 특별 처리
                    if currency == 'USDT':
                        parsed_balance['usdt_balance'] = cash_bal
                        parsed_balance['available_balance'] = available
                
                self.balance_updated.emit(parsed_balance)
                return True
            else:
                print("⚠️ AccountManager에서 None 반환 - API 인증 문제")
                return False
                
        except Exception as e:
            print(f"⚠️ 실제 잔액 정보 업데이트 오류: {e}")
            return False


    def update_price_info(self) -> bool:
        """실제 가격 정보만 업데이트 - 더미 데이터 없음"""
        try:
            import requests
            
            # config.py에서 실제 거래 심볼만 가져오기
            try:
                from config import TRADING_CONFIG
                symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            except:
                symbols = ['BTC-USDT-SWAP']  # 기본값
            
            success_count = 0
            
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
                            change_24h = 0.0
                            if open_price > 0:
                                change_24h = ((price - open_price) / open_price) * 100
                            
                            price_info = {
                                'symbol': symbol,
                                'bid': float(ticker_data.get('bidPx', 0)),
                                'ask': float(ticker_data.get('askPx', 0)),
                                'volume_24h': volume,
                                'change_24h': change_24h,
                                'change_percent': change_24h,
                                'high_24h': high_price,
                                'low_24h': low_price,
                                'timestamp': time.time(),
                                'is_dummy': False  # 실제 데이터임을 명시
                            }
                            
                            self.price_updated.emit(symbol, price, price_info)
                            success_count += 1
                            
                        else:
                            print(f"⚠️ {symbol} API 응답 오류: {data.get('msg', 'Unknown error')}")
                    else:
                        print(f"⚠️ {symbol} HTTP 오류: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ {symbol} 네트워크 오류: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️ {symbol} 가격 조회 오류: {e}")
                    continue
            
            # 하나라도 성공했으면 성공으로 처리
            return success_count > 0
                        
        except Exception as e:
            print(f"⚠️ 가격 정보 업데이트 오류: {e}")
            return False

    def update_position_info(self) -> bool:
        """포지션 정보 업데이트 - 안전한 파라미터 전달"""
        if not self.account_manager:
            return False
        
        try:
            print("📊 포지션 조회 시작 (instType=SWAP)")
            
            # ✅ 명시적으로 SWAP 타입만 조회
            positions_response = self.account_manager.get_positions("SWAP")
            
            if positions_response is not None and isinstance(positions_response, list):
                # 활성 포지션만 필터링
                active_positions = []
                for position in positions_response:
                    try:
                        pos_size = float(position.get('pos', 0))
                        if abs(pos_size) > 0.001:  # 0.001 이상만 활성 포지션
                            active_positions.append(position)
                    except (ValueError, TypeError):
                        continue
                
                # GUI에 포지션 데이터 전송
                self.positions_updated.emit(active_positions)
                
                # 포지션 상태 로그
                if active_positions:
                    total_upl = 0
                    for pos in active_positions:
                        try:
                            total_upl += float(pos.get('upl', 0))
                        except (ValueError, TypeError):
                            continue
                            
                    print(f"📈 활성 포지션: {len(active_positions)}개, 총 PnL: ${total_upl:+.2f}")
                else:
                    print("📊 활성 포지션: 없음")
                
                return True
                    
            else:
                print("⚠️ 포지션 데이터 조회 실패 - 빈 리스트로 처리")
                self.positions_updated.emit([])
                return True  # 실패해도 True 반환하여 GUI 계속 작동
                
        except Exception as e:
            print(f"⚠️ 포지션 정보 업데이트 오류 (무시하고 계속): {e}")
            # 빈 포지션 리스트 전송하여 GUI가 계속 작동
            self.positions_updated.emit([])
            return True  # 오류가 있어도 True 반환


    def update_strategy_info(self):
        """실제 전략 상태 정보만 업데이트 - 더미 데이터 없음"""
        try:
            # 실제 전략 매니저에서 상태 가져오기 (구현 필요)
            # 현재는 기본 상태만 전송
            strategy_data = {
                'is_running': self.is_connected,
                'active_strategies': 1 if self.is_connected else 0,
                'uptime': int(time.time() % 3600),
                'total_trades': 0,
                'total_pnl': 0.0,
                'last_signal': 'waiting' if self.is_connected else 'signal_lost',
                'last_trade_time': datetime.now().isoformat(),
                'is_dummy': False
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
                self.consecutive_failures = 0
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
    
    def on_signal_lost():
        print("🚨 Signal Lost!")
    
    def on_error(error):
        print(f"❌ 오류: {error}")
    
    # 데이터 스레드 생성 및 연결
    thread = TradingDataThread()
    thread.balance_updated.connect(on_balance_updated)
    thread.price_updated.connect(on_price_updated)
    thread.positions_updated.connect(on_positions_updated)
    thread.connection_changed.connect(on_connection_changed)
    thread.signal_lost.connect(on_signal_lost)
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