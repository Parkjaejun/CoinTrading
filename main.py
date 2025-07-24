# main.py
"""
실제 OKX 데이터 연동을 위해 수정된 메인 시스템
WebSocket 연결 및 데이터 플로우 개선
"""

import sys
import time
import signal
import threading
from datetime import datetime
from typing import Optional
import argparse

# 핵심 설정 먼저 로드
try:
    from config import (
        validate_config, TRADING_CONFIG, EMA_PERIODS, API_KEY, API_SECRET, PASSPHRASE
    )
    print("✅ 설정 파일 로드 완료")
except ImportError as e:
    print(f"❌ 설정 파일 로드 실패: {e}")
    print("config.py 파일에 EMA_PERIODS가 정의되어 있는지 확인하세요.")
    sys.exit(1)

# 나머지 모듈들 import
try:
    from utils.logger import log_system, log_error, log_info
    from utils.notifications import initialize_notifications, send_system_alert
    from okx.websocket_handler import WebSocketHandler
    from strategy.dual_manager import DualStrategyManager
    from utils.data_loader import load_initial_data
    print("✅ 모든 모듈 로드 완료")
except ImportError as e:
    print(f"❌ 모듈 로드 실패: {e}")
    sys.exit(1)

class TradingSystem:
    def __init__(self):
        self.strategy_manager: Optional[DualStrategyManager] = None
        self.ws_handler: Optional[WebSocketHandler] = None
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        # 시스템 상태
        self.start_time: Optional[datetime] = None
        self.last_heartbeat = datetime.now()
        self.error_count = 0
        self.max_errors = 10
        
        # 실시간 데이터 수신 상태
        self.last_price_update = datetime.now()
        self.received_data_count = 0
        self.websocket_connected = False
        
        # 성능 모니터링
        self.performance_stats = {
            'signals_processed': 0,
            'trades_executed': 0,
            'uptime': 0,
            'errors': 0,
            'api_calls': 0,
            'websocket_messages': 0
        }
    
    def initialize_system(self, environment: str = "production"):
        """시스템 전체 초기화 - 실제 잔액 연동 수정"""
        try:
            print("\n" + "="*70)
            print("🚀 OKX 실제 데이터 연동 시스템 초기화")
            print("="*70)
            
            # 설정 검증
            log_system("설정 검증 중...")
            if not validate_config():
                print("❌ 설정 검증 실패")
                return False
            
            # 🔧 실제 잔액 확인 (수정된 부분)
            log_system("실제 계좌 잔액 확인 중...")
            
            # balance_utils 모듈이 없을 경우 직접 잔액 조회
            try:
                from utils.balance_utils import check_minimum_trading_balance
                has_balance, current_usdt, balance_message = check_minimum_trading_balance(100.0)
            except ImportError:
                # balance_utils가 없으면 직접 구현
                has_balance, current_usdt, balance_message = self._check_balance_direct()
            
            print(balance_message)
            
            if not has_balance:
                print(f"\n💡 현재 USDT 잔액: ${current_usdt:.6f}")
                print("해결 방법:")
                print("1. 🏦 OKX 웹사이트에서 USDT 입금")
                print("2. 💱 다른 코인을 USDT로 환전")
                print("3. 🎮 테스트 모드로 실행:")
                print("   python main.py --paper-trading")
                print("\n⚠️ 테스트 모드는 실제 거래 없이 시뮬레이션만 합니다.")
                return False
            
            # 초기 데이터 로딩
            log_system("초기 시장 데이터 로딩...")
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            initial_data = load_initial_data(symbols)
            
            if not initial_data:
                log_error("초기 데이터 로딩 실패")
                return False
            
            log_system(f"✅ 초기 데이터 로딩 완료: {len(initial_data)}개 심볼")
            
            # 🔧 실제 잔액으로 전략 매니저 초기화
            log_system("전략 매니저 초기화...")
            
            # 실제 USDT 잔액 사용 (안전을 위해 95% 사용)
            actual_capital = current_usdt * 0.95  # 5% 여유 유지
            
            self.strategy_manager = DualStrategyManager(
                total_capital=actual_capital,
                symbols=symbols
            )
            
            log_system(f"💰 실제 자본으로 거래 시작: ${actual_capital:.2f} (원본: ${current_usdt:.2f})")
            
            # WebSocket 핸들러 초기화
            log_system("WebSocket 핸들러 초기화...")
            self.ws_handler = WebSocketHandler(strategy_manager=self.strategy_manager)
            
            # 나머지 초기화 과정...
            log_system("🔗 WebSocket 핸들러 초기화 완료")
            return True
            
        except Exception as e:
            log_error("시스템 초기화 실패", e)
            return False

    def _check_balance_direct(self):
        """직접 잔액 조회 (balance_utils가 없을 경우)"""
        try:
            from config import make_api_request
            
            log_system("거래 계정 잔액 직접 조회...")
            
            # API 호출로 잔액 조회
            trading_balance = make_api_request('GET', '/api/v5/account/balance')
            
            if not trading_balance or trading_balance.get('code') != '0':
                return False, 0.0, "❌ 잔액 조회 실패"
            
            data = trading_balance.get('data')
            if not data:
                return False, 0.0, "❌ 잔액 데이터 없음"
            
            balance_data = data[0]
            
            # USDT 잔액 찾기
            for detail in balance_data.get('details', []):
                if detail['ccy'] == 'USDT':
                    avail_bal = detail.get('availBal', '0')
                    
                    # 빈 문자열 처리
                    if avail_bal == '':
                        avail_bal = '0'
                    
                    usdt_balance = float(avail_bal)
                    
                    if usdt_balance >= 50.0:
                        return True, usdt_balance, f"✅ 거래 가능: ${usdt_balance:.2f}"
                    else:
                        return False, usdt_balance, f"❌ 잔액 부족: ${usdt_balance:.2f} (최소 $50 필요)"
            
            return False, 0.0, "❌ USDT 잔액 없음"
            
        except Exception as e:
            log_error("직접 잔액 조회 오류", e)
            return False, 0.0, f"❌ 조회 실패: {e}"

    def _on_price_update(self, price_data):
        """가격 업데이트 콜백"""
        self.last_price_update = datetime.now()
        self.received_data_count += 1
        self.performance_stats['websocket_messages'] += 1
        
        # 주기적으로 상태 로깅
        if self.received_data_count % 100 == 0:
            log_info(f"📊 데이터 수신 상태: {self.received_data_count}건 처리됨")
    
    def _on_connection_status(self, connected):
        """연결 상태 변경 콜백"""
        self.websocket_connected = connected
        if connected:
            log_system("🔗 WebSocket 연결 활성화")
            send_system_alert("✅ 거래 시스템 연결 복구", "WebSocket 연결이 정상화되었습니다.")
        else:
            log_error("🔌 WebSocket 연결 끊어짐")
            send_system_alert("⚠️ 거래 시스템 연결 불안정", "WebSocket 연결에 문제가 발생했습니다.")
    
    def start_trading(self):
        """실시간 거래 시작"""
        if not self.strategy_manager or not self.ws_handler:
            log_error("시스템이 초기화되지 않았습니다")
            return False
        
        try:
            log_system("🚀 실시간 거래 시작")
            self.is_running = True
            self.start_time = datetime.now()
            
            # WebSocket 연결 시작 - 🔧 수정된 부분
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            
            # WebSocketHandler의 실제 메서드 사용
            success = self.ws_handler.start_websocket(symbols, ["tickers"])
            
            if not success:
                log_error("WebSocket 연결 실패")
                return False
            
            log_system(f"📊 거래 대상: {', '.join(symbols)}")
            log_system("⏰ 시스템 운영 중... (Ctrl+C로 종료)")
            
            # 연결 상태 확인을 위한 콜백 설정
            def on_connection_status(is_connected):
                self.websocket_connected = is_connected
                if is_connected:
                    log_system("🔌 WebSocket 연결 성공")
                    send_system_alert("🚀 거래 시스템 시작", f"거래 대상: {', '.join(symbols)}")
                else:
                    log_error("🔌 WebSocket 연결 끊어짐")
                    send_system_alert("⚠️ 거래 시스템 연결 불안정", "WebSocket 연결에 문제가 발생했습니다.")
            
            # 가격 데이터 처리 콜백 설정
            def on_price_update(symbol, price, data):
                self.received_data_count += 1
                self.last_price_update = datetime.now()
                
                # 전략 매니저에 데이터 전달
                if self.strategy_manager:
                    self.strategy_manager.process_signal(symbol, data)
            
            # 콜백 설정
            self.ws_handler.set_callbacks(
                price_callback=on_price_update,
                connection_callback=on_connection_status
            )
            
            # 메인 루프 실행
            self._main_loop()
            
            return True
            
        except Exception as e:
            log_error("거래 시작 실패", e)
            return False

    def stop_trading(self):
        """거래 중지"""
        try:
            log_system("🛑 거래 시스템 종료 시작...")
            self.is_running = False
            self.shutdown_event.set()
            
            # WebSocket 연결 종료
            if self.ws_handler:
                # WebSocketHandler의 실제 종료 메서드 호출
                if hasattr(self.ws_handler, 'stop_ws'):
                    self.ws_handler.stop_ws()
                else:
                    # 직접 연결 종료
                    self.ws_handler.is_running = False
                    if hasattr(self.ws_handler, 'public_ws') and self.ws_handler.public_ws:
                        self.ws_handler.public_ws.close()
                    if hasattr(self.ws_handler, 'private_ws') and self.ws_handler.private_ws:
                        self.ws_handler.private_ws.close()
            
            # 전략 매니저 종료
            if self.strategy_manager:
                log_system("💼 전략 매니저 종료...")
                if hasattr(self.strategy_manager, 'shutdown'):
                    self.strategy_manager.shutdown()
            
            log_system("✅ 거래 시스템 종료 완료")
            send_system_alert("🛑 거래 시스템 종료", "시스템이 안전하게 종료되었습니다.")
            
        except Exception as e:
            log_error("거래 시스템 종료 중 오류", e)    
    
    def _main_loop(self):
        """메인 실행 루프"""
        last_status_update = datetime.now()
        
        try:
            while self.is_running and not self.shutdown_event.is_set():
                current_time = datetime.now()
                
                # 주기적 상태 업데이트 (5분마다)
                if (current_time - last_status_update).seconds >= 300:
                    self._update_performance_stats()
                    self._log_system_status()
                    last_status_update = current_time
                
                # 연결 상태 모니터링
                if not self.websocket_connected:
                    log_error("WebSocket 연결 끊어짐 감지")
                    self.error_count += 1
                    
                    if self.error_count >= self.max_errors:
                        log_error(f"최대 오류 횟수 초과: {self.max_errors}")
                        break
                
                # 1초 대기
                time.sleep(1)
                
        except KeyboardInterrupt:
            log_system("사용자 종료 요청")
        except Exception as e:
            log_error("메인 루프 오류", e)
        finally:
            self._shutdown_system()
    
    def _update_performance_stats(self):
        """성능 통계 업데이트"""
        if self.start_time:
            uptime = datetime.now() - self.start_time
            self.performance_stats['uptime'] = int(uptime.total_seconds())
        
        self.performance_stats['errors'] = self.error_count
        
        # 전략 매니저 통계 수집
        if self.strategy_manager and hasattr(self.strategy_manager, 'get_performance_stats'):
            try:
                strategy_stats = self.strategy_manager.get_performance_stats()
                self.performance_stats.update(strategy_stats)
            except Exception as e:
                log_error("전략 통계 수집 오류", e)
    
    def _log_system_status(self):
        """시스템 상태 로깅"""
        try:
            status = {}
            if self.ws_handler and hasattr(self.ws_handler, 'get_connection_status'):
                status = self.ws_handler.get_connection_status()
            
            log_info("=" * 50)
            log_info("📊 시스템 상태 보고")
            log_info(f"⏰ 운영 시간: {self.performance_stats['uptime']}초")
            log_info(f"📨 수신 메시지: {status.get('messages_received', self.received_data_count)}건")
            log_info(f"🎯 처리된 신호: {self.performance_stats['signals_processed']}개")
            log_info(f"💼 실행 거래: {self.performance_stats['trades_executed']}건")
            log_info(f"❌ 오류 횟수: {self.error_count}건")
            log_info(f"🔗 연결 상태: {'정상' if self.websocket_connected else '불안정'}")
            log_info("=" * 50)
        except Exception as e:
            log_error("상태 로깅 오류", e)
    
    def _shutdown_system(self):
        """시스템 종료"""
        log_system("🛑 시스템 종료 중...")
        self.is_running = False
        
        try:
            # WebSocket 연결 종료
            if self.ws_handler:
                if hasattr(self.ws_handler, 'stop_ws'):
                    self.ws_handler.stop_ws()
                log_system("✅ WebSocket 연결 종료")
            
            # 성능 통계 최종 출력
            self._update_performance_stats()
            log_info("📊 최종 성능 통계:")
            for key, value in self.performance_stats.items():
                log_info(f"  {key}: {value}")
            
            # 시스템 알림
            uptime_hours = self.performance_stats['uptime'] / 3600 if self.performance_stats['uptime'] > 0 else 0
            send_system_alert(
                "🛑 거래 시스템 종료", 
                f"운영 시간: {uptime_hours:.1f}시간\n"
                f"처리 신호: {self.performance_stats['signals_processed']}개\n"
                f"실행 거래: {self.performance_stats['trades_executed']}건"
            )
            
            log_system("✅ 시스템 종료 완료")
            
        except Exception as e:
            log_error("시스템 종료 중 오류", e)
    
    def run_backtest(self, strategy_type: str, start_date: str, end_date: str):
        """백테스트 실행"""
        try:
            log_system(f"📈 백테스트 시작: {strategy_type} ({start_date} ~ {end_date})")
            
            # 백테스트 모듈 동적 import
            from backtest.backtester import run_strategy_backtest
            
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            result = run_strategy_backtest(
                strategy_type=strategy_type,
                symbol=symbols[0],
                start_date=start_date,
                end_date=end_date
            )
            
            if result:
                log_system("✅ 백테스트 완료")
                print(f"\n📊 백테스트 결과:")
                print(f"총 수익률: {result.get('total_return', 0):.2f}%")
                print(f"거래 횟수: {result.get('total_trades', 0)}회")
                print(f"승률: {result.get('win_rate', 0):.1f}%")
            else:
                log_error("백테스트 실행 실패")
                
            return result
            
        except Exception as e:
            log_error("백테스트 오류", e)
            return None

def setup_signal_handlers(trading_system: TradingSystem):
    """시그널 핸들러 설정"""
    def signal_handler(signum, frame):
        print(f"\n🛑 종료 신호 수신: {signum}")
        trading_system.shutdown_event.set()
        trading_system.is_running = False
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 종료 신호

def quick_balance_check():
    """빠른 잔액 확인"""
    print("💰 빠른 잔액 확인")
    print("="*30)
    
    try:
        from config import make_api_request
        
        # 거래 계정 잔액 조회
        trading_balance = make_api_request('GET', '/api/v5/account/balance')
        
        if trading_balance and trading_balance.get('code') == '0':
            data = trading_balance.get('data', [])
            if data:
                balance_data = data[0]
                total_eq = balance_data.get('totalEq', '0')
                
                if total_eq == '':
                    total_eq = '0'
                
                print(f"📊 총 자산: ${float(total_eq):.2f}")
                
                # 통화별 잔액
                for detail in balance_data.get('details', []):
                    ccy = detail['ccy']
                    cash_bal = detail.get('cashBal', '0')
                    avail_bal = detail.get('availBal', '0')
                    
                    if cash_bal == '':
                        cash_bal = '0'
                    if avail_bal == '':
                        avail_bal = '0'
                    
                    cash_bal = float(cash_bal)
                    avail_bal = float(avail_bal)
                    
                    if cash_bal > 0.001:
                        print(f"  {ccy}: ${cash_bal:.6f} (사용가능: ${avail_bal:.6f})")
                
                # USDT 특별 확인
                usdt_found = False
                for detail in balance_data.get('details', []):
                    if detail['ccy'] == 'USDT':
                        usdt_bal = float(detail.get('availBal', '0') or '0')
                        usdt_found = True
                        if usdt_bal >= 100:
                            print(f"\n✅ 거래 가능: ${usdt_bal:.2f}")
                        else:
                            print(f"\n⚠️ 거래 자금 부족: ${usdt_bal:.2f}")
                        break
                
                if not usdt_found:
                    print("\n❌ USDT 잔액 없음")
        else:
            print("❌ 잔액 조회 실패")
    except Exception as e:
        print(f"❌ 잔액 확인 오류: {e}")

def main():
    """메인 함수 - 실제/테스트 모드 지원"""
    parser = argparse.ArgumentParser(description='OKX 자동매매 시스템')
    parser.add_argument('--paper-trading', action='store_true',
                       help='페이퍼 트레이딩 모드 (가상 자금 사용)')
    parser.add_argument('--virtual-balance', type=float, default=10000,
                       help='가상 모드에서 사용할 초기 자금 (기본값: $10,000)')
    parser.add_argument('--check-balance', action='store_true',
                       help='잔액만 확인하고 종료')
    parser.add_argument('--backtest', type=str, 
                       choices=['long', 'short', 'dual'],
                       help='백테스트 모드')
    parser.add_argument('--start-date', type=str, 
                       help='백테스트 시작일 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='백테스트 종료일 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # 잔액 확인만 하고 종료
    if args.check_balance:
        quick_balance_check()
        return
    
    print("✅ 계좌 관리자 초기화 완료")
    
    # 트레이딩 시스템 초기화
    trading_system = TradingSystem()
    
    try:
        # 백테스트 모드
        if args.backtest:
            result = trading_system.run_backtest(args.backtest, args.start_date, args.end_date)
            return
        
        # 시그널 핸들러 설정
        setup_signal_handlers(trading_system)
        
        if args.paper_trading:
            # 🎮 페이퍼 트레이딩 모드
            print(f"\n🎮 페이퍼 트레이딩 모드 실행")
            print(f"💰 가상 자금: ${args.virtual_balance:,.0f}")
            print("⚠️ 실제 거래는 실행되지 않습니다!")
            
            # 시장 데이터는 실제로 로딩
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            initial_data = load_initial_data(symbols)
            
            if initial_data:
                # 가상 자금으로 전략 매니저 생성
                trading_system.strategy_manager = DualStrategyManager(
                    total_capital=args.virtual_balance,
                    symbols=symbols
                )
                
                # WebSocket은 실제 데이터 사용
                trading_system.ws_handler = WebSocketHandler(
                    strategy_manager=trading_system.strategy_manager
                )
                
                log_system("✅ 페이퍼 트레이딩 시스템 초기화 완료")
                print("🚀 가상 거래 시작 (실제 API 데이터 사용)")
                
                # 거래 시작
                trading_system.start_trading()
            else:
                print("❌ 초기 데이터 로딩 실패")
        else:
            # 🚀 실제 거래 모드
            print("🚀 실제 거래 모드")
            if not trading_system.initialize_system():
                print("❌ 시스템 초기화 실패")
                return
            
            # 실제 거래 시작
            trading_system.start_trading()
        
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의한 시스템 종료")
    except Exception as e:
        log_error("메인 함수 실행 오류", e)
        print(f"❌ 시스템 오류: {e}")
    finally:
        # 정리 작업
        try:
            trading_system.stop_trading()
        except:
            pass

if __name__ == "__main__":
    main()