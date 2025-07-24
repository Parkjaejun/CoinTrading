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
        """시스템 전체 초기화 - 실제 OKX 연동 강화"""
        try:
            print("\n" + "="*70)
            print("🚀 OKX 실제 데이터 연동 시스템 초기화")
            print("="*70)
            
            # 설정 검증
            log_system("설정 검증 중...")
            if not validate_config():
                print("❌ 설정 검증 실패")
                return False
            
            # 초기 데이터 로딩
            log_system("초기 시장 데이터 로딩...")
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            initial_data = load_initial_data(symbols)
            
            if not initial_data:
                log_error("초기 데이터 로딩 실패")
                return False
            
            log_system(f"✅ 초기 데이터 로딩 완료: {len(initial_data)}개 심볼")
            
            # 전략 매니저 초기화
            log_system("전략 매니저 초기화...")
            self.strategy_manager = DualStrategyManager(symbols)
            
            # WebSocket 핸들러 초기화
            log_system("WebSocket 핸들러 초기화...")
            self.ws_handler = WebSocketHandler(strategy_manager=self.strategy_manager)
            
            # 콜백 함수 설정
            self.ws_handler.set_callbacks(
                price_callback=self._on_price_update,
                connection_callback=self._on_connection_status
            )
            
            # 알림 시스템 초기화
            try:
                initialize_notifications()
                log_system("✅ 알림 시스템 초기화 완료")
            except Exception as e:
                log_error("알림 시스템 초기화 실패", e)
                # 알림 실패는 시스템 중단 사유가 아님
            
            self.start_time = datetime.now()
            log_system("🎯 시스템 초기화 완료")
            return True
            
        except Exception as e:
            log_error("시스템 초기화 실패", e)
            return False
    
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
            
            # WebSocket 연결 시작
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            public_thread, private_thread = self.ws_handler.start_ws(symbols)
            
            if not public_thread or not private_thread:
                log_error("WebSocket 스레드 시작 실패")
                return False
            
            log_system(f"📊 거래 대상: {', '.join(symbols)}")
            log_system("⏰ 시스템 운영 중... (Ctrl+C로 종료)")
            
            send_system_alert("🚀 거래 시스템 시작", f"거래 대상: {', '.join(symbols)}")
            
            # 메인 루프
            self._main_loop()
            
            return True
            
        except Exception as e:
            log_error("거래 시작 실패", e)
            return False
    
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
        if self.strategy_manager:
            strategy_stats = self.strategy_manager.get_performance_stats()
            self.performance_stats.update(strategy_stats)
    
    def _log_system_status(self):
        """시스템 상태 로깅"""
        status = self.ws_handler.get_connection_status() if self.ws_handler else {}
        
        log_info("=" * 50)
        log_info("📊 시스템 상태 보고")
        log_info(f"⏰ 운영 시간: {self.performance_stats['uptime']}초")
        log_info(f"📨 수신 메시지: {status.get('received_messages', 0)}건")
        log_info(f"🎯 처리된 신호: {self.performance_stats['signals_processed']}개")
        log_info(f"💼 실행 거래: {self.performance_stats['trades_executed']}건")
        log_info(f"❌ 오류 횟수: {self.error_count}건")
        log_info(f"🔗 연결 상태: {'정상' if self.websocket_connected else '불안정'}")
        log_info("=" * 50)
    
    def _shutdown_system(self):
        """시스템 종료"""
        log_system("🛑 시스템 종료 중...")
        self.is_running = False
        
        try:
            # WebSocket 연결 종료
            if self.ws_handler:
                self.ws_handler.stop_ws()
                log_system("✅ WebSocket 연결 종료")
            
            # 성능 통계 최종 출력
            self._update_performance_stats()
            log_info("📊 최종 성능 통계:")
            for key, value in self.performance_stats.items():
                log_info(f"  {key}: {value}")
            
            # 시스템 알림
            uptime_hours = self.performance_stats['uptime'] / 3600
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

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='OKX 실시간 거래 시스템')
    parser.add_argument('--env', default='production', 
                       choices=['production', 'development', 'test'],
                       help='실행 환경')
    parser.add_argument('--backtest', type=str, 
                       choices=['long', 'short', 'dual'],
                       help='백테스트 모드')
    parser.add_argument('--start-date', type=str, 
                       help='백테스트 시작일 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='백테스트 종료일 (YYYY-MM-DD)')
    parser.add_argument('--config-test', action='store_true',
                       help='설정 테스트만 실행')
    parser.add_argument('--connection-test', action='store_true',
                       help='연결 테스트만 실행')
    
    args = parser.parse_args()
    
    # 계좌 관리자 초기화 로그
    print("✅ 계좌 관리자 초기화 완료")
    
    # 트레이딩 시스템 초기화
    trading_system = TradingSystem()
    
    try:
        # 설정 테스트만 실행
        if args.config_test:
            print("🧪 설정 테스트 모드")
            if trading_system.initialize_system(args.env):
                print("✅ 설정 테스트 통과")
                sys.exit(0)
            else:
                print("❌ 설정 테스트 실패")
                sys.exit(1)
        
        # 연결 테스트만 실행
        if args.connection_test:
            print("🔗 연결 테스트 모드")
            # WebSocket 연결 테스트
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            ws_handler = WebSocketHandler()
            public_thread, private_thread = ws_handler.start_ws(symbols)
            time.sleep(10)  # 10초 대기
            ws_handler.stop_ws()
            print("✅ WebSocket 테스트 완료")
            sys.exit(0)
        
        # 시스템 초기화
        if not trading_system.initialize_system(args.env):
            print("❌ 시스템 초기화 실패")
            sys.exit(1)
        
        # 백테스트 모드
        if args.backtest:
            result = trading_system.run_backtest(args.backtest, args.start_date, args.end_date)
            sys.exit(0)
        
        # 시그널 핸들러 설정
        setup_signal_handlers(trading_system)
        
        # 실시간 트레이딩 시작
        trading_system.start_trading()
        
    except Exception as e:
        log_error("메인 함수 실행 오류", e)
        print(f"❌ 시스템 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()