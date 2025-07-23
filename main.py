# main_fixed.py
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

# 모든 필요한 모듈 임포트
from config import (
    validate_config, print_config_summary, TRADING_CONFIG, NOTIFICATION_CONFIG,
    CONNECTION_CONFIG, load_environment_config, backup_config
)
from utils.logger import log_system, log_error, log_info
from utils.notifications import initialize_notifications, send_system_alert
from okx.connection_manager import connection_manager
from okx.websocket_handler import WebSocketHandler
from strategy.dual_manager import DualStrategyManager
from utils.data_loader import load_initial_data
from okx.order_validator import order_validator
from backtest.backtester import run_strategy_backtest

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
            
            # 환경별 설정 로드
            load_environment_config(environment)
            log_system(f"환경 설정 로드: {environment}")
            
            # 설정 검증
            log_system("설정 검증 중...")
            validate_config()
            print_config_summary()
            
            # 설정 백업
            backup_file = backup_config()
            if backup_file:
                log_system(f"설정 백업 생성: {backup_file}")
            
            # 알림 시스템 초기화
            log_system("알림 시스템 초기화...")
            initialize_notifications(NOTIFICATION_CONFIG)
            
            # API 연결 상태 확인 및 시작
            log_system("API 연결 상태 확인...")
            if not self._test_api_connection():
                raise ConnectionError("초기 API 연결 실패 - API 키를 확인하세요")
            
            connection_manager.start_monitoring()
            
            # 초기 데이터 로딩 (필수)
            log_system("초기 시장 데이터 로딩...")
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            initial_data = load_initial_data(symbols)
            
            if not initial_data:
                log_error("초기 데이터 로딩 실패")
                raise ValueError("초기 시장 데이터를 로드할 수 없습니다")
            
            log_system(f"초기 데이터 로딩 완료: {len(initial_data)}개 심볼")
            
            # 전략 관리자 초기화
            log_system("전략 관리자 초기화...")
            self.strategy_manager = DualStrategyManager(
                total_capital=TRADING_CONFIG.get('initial_capital', 10000),
                symbols=symbols
            )
            
            # 초기 데이터로 전략 준비
            for symbol, df in initial_data.items():
                if len(df) > 0:
                    log_system(f"{symbol} 전략 데이터 준비 완료: {len(df)}개 캔들")
            
            # WebSocket 핸들러 초기화 (실제 연결)
            log_system("실시간 데이터 WebSocket 초기화...")
            self.ws_handler = WebSocketHandler(strategy_manager=self.strategy_manager)
            
            # 실시간 데이터 콜백 설정
            self._setup_websocket_callbacks()
            
            # 연결 이벤트 콜백 등록
            connection_manager.add_reconnect_callback(self._on_api_reconnect)
            connection_manager.add_disconnect_callback(self._on_api_disconnect)
            
            log_system("✅ 시스템 초기화 완료")
            send_system_alert("시스템 초기화 완료", f"환경: {environment}\n심볼: {symbols}", "info")
            
            return True
            
        except Exception as e:
            log_error("시스템 초기화 실패", e)
            send_system_alert("시스템 초기화 실패", str(e), "error")
            return False
    
    def _test_api_connection(self) -> bool:
        """API 연결 테스트 강화"""
        try:
            log_system("OKX API 연결 테스트 중...")
            
            # 기본 연결 테스트
            if not connection_manager.test_connection():
                log_error("기본 API 연결 실패")
                return False
            
            # 계좌 정보 확인
            from okx.account_manager import AccountManager
            account = AccountManager()
            
            balances = account.get_account_balance()
            if not balances:
                log_error("계좌 정보 조회 실패")
                return False
            
            log_system("✅ API 연결 성공")
            
            # USDT 잔고 확인
            usdt_balance = balances.get('USDT', {}).get('available', 0)
            log_system(f"USDT 잔고: ${usdt_balance:,.2f}")
            
            if usdt_balance < 10:
                log_error("USDT 잔고 부족 - 거래에 필요한 최소 잔고가 부족합니다")
                return False
            
            return True
            
        except Exception as e:
            log_error("API 연결 테스트 실패", e)
            return False
    
    def _setup_websocket_callbacks(self):
        """WebSocket 콜백 설정"""
        # 가격 데이터 수신 콜백
        def on_price_data(symbol, price_data):
            try:
                self.received_data_count += 1
                self.last_price_update = datetime.now()
                self.performance_stats['websocket_messages'] += 1
                
                # 전략 매니저에 실시간 데이터 전달
                if self.strategy_manager and 'last' in price_data:
                    # 가격 데이터를 전략용 형식으로 변환
                    strategy_data = {
                        'symbol': symbol,
                        'close': price_data['last'],
                        'timestamp': datetime.now(),
                        'volume': price_data.get('vol24h', 0),
                        'high': price_data.get('high_24h', 0),
                        'low': price_data.get('low_24h', 0)
                    }
                    
                    # 전략 처리
                    signal_generated = self.strategy_manager.process_signal(symbol, strategy_data)
                    if signal_generated:
                        self.performance_stats['signals_processed'] += 1
                
                # 주기적 로그 (100개마다)
                if self.received_data_count % 100 == 0:
                    log_info(f"📊 실시간 데이터 수신: {self.received_data_count}건 ({symbol}: ${price_data.get('last', 0):.2f})")
                
            except Exception as e:
                log_error(f"가격 데이터 처리 오류 ({symbol})", e)
        
        # 계좌 데이터 수신 콜백
        def on_account_data(account_data):
            try:
                log_info("💳 계좌 정보 업데이트 수신")
                # 필요시 계좌 변화에 따른 추가 처리
            except Exception as e:
                log_error("계좌 데이터 처리 오류", e)
        
        # 포지션 데이터 수신 콜백
        def on_position_data(position_data):
            try:
                log_info(f"📊 포지션 정보 업데이트: {len(position_data)}개")
                # 포지션 변화 모니터링
            except Exception as e:
                log_error("포지션 데이터 처리 오류", e)
        
        # WebSocket 연결 상태 콜백
        def on_connection_status(is_connected):
            self.websocket_connected = is_connected
            if is_connected:
                log_system("✅ WebSocket 연결 성공")
                send_system_alert("실시간 데이터 연결", "WebSocket 연결이 설정되었습니다", "info")
            else:
                log_error("❌ WebSocket 연결 끊어짐")
                send_system_alert("실시간 데이터 연결 끊어짐", "WebSocket 재연결을 시도합니다", "warning")
        
        # 콜백 등록 (WebSocket 핸들러에 메서드가 있다면)
        if hasattr(self.ws_handler, 'set_price_callback'):
            self.ws_handler.set_price_callback(on_price_data)
        if hasattr(self.ws_handler, 'set_account_callback'):
            self.ws_handler.set_account_callback(on_account_data)
        if hasattr(self.ws_handler, 'set_position_callback'):
            self.ws_handler.set_position_callback(on_position_data)
    
    def start_trading(self):
        """실제 트레이딩 시작 - WebSocket 연결 포함"""
        if self.is_running:
            log_system("시스템이 이미 실행 중입니다")
            return
        
        try:
            log_system("🎯 실시간 트레이딩 시작")
            self.is_running = True
            self.start_time = datetime.now()
            
            # WebSocket 실제 시작
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            
            log_system(f"📡 실시간 데이터 WebSocket 시작: {symbols}")
            public_thread, private_thread = self.ws_handler.start_ws(symbols)
            
            # WebSocket 연결 대기 및 확인
            connection_timeout = 30  # 30초 대기
            start_wait = time.time()
            
            while time.time() - start_wait < connection_timeout:
                if self.websocket_connected:
                    break
                time.sleep(1)
                log_system("📡 WebSocket 연결 대기 중...")
            
            if not self.websocket_connected:
                log_error("WebSocket 연결 타임아웃")
                raise ConnectionError("WebSocket 연결에 실패했습니다")
            
            # 시작 알림
            trading_mode = "Paper Trading" if TRADING_CONFIG.get('paper_trading', False) else "Live Trading"
            send_system_alert(
                "실시간 트레이딩 시작", 
                f"대상: {', '.join(symbols)}\n모드: {trading_mode}\n시작 시간: {self.start_time.strftime('%H:%M:%S')}", 
                "info"
            )
            
            print(f"\n🚀 실시간 트레이딩 시작")
            print(f"📊 대상 심볼: {', '.join(symbols)}")
            print(f"💰 초기 자본: ${TRADING_CONFIG.get('initial_capital', 10000):,}")
            print(f"📝 모드: {trading_mode}")
            print(f"📡 WebSocket: {'✅ 연결됨' if self.websocket_connected else '❌ 끊어짐'}")
            print(f"🔔 알림 채널: {len([c for c in NOTIFICATION_CONFIG.keys() if isinstance(NOTIFICATION_CONFIG[c], dict) and NOTIFICATION_CONFIG[c].get('enabled', False)])}개 활성화")
            print("📴 중지하려면 Ctrl+C를 누르세요")
            print("="*70)
            
            # 메인 실행 루프
            self._main_loop()
            
        except KeyboardInterrupt:
            log_system("사용자에 의한 종료 요청")
        except Exception as e:
            log_error("트레이딩 실행 중 오류", e)
            self.error_count += 1
            send_system_alert("트레이딩 오류", str(e), "error")
        finally:
            self.stop_trading()
    
    def _main_loop(self):
        """메인 실행 루프 - 실시간 모니터링 강화"""
        last_status_time = 0
        last_heartbeat_time = 0
        last_connection_check = 0
        
        status_interval = 300  # 5분마다 상태 출력
        heartbeat_interval = 60  # 1분마다 heartbeat
        connection_check_interval = 30  # 30초마다 연결 상태 확인
        
        while self.is_running and not self.shutdown_event.is_set():
            try:
                current_time = time.time()
                
                # 5분마다 상태 출력
                if current_time - last_status_time >= status_interval:
                    self._print_system_status()
                    last_status_time = current_time
                
                # 1분마다 heartbeat
                if current_time - last_heartbeat_time >= heartbeat_interval:
                    self._heartbeat_check()
                    last_heartbeat_time = current_time
                
                # 30초마다 연결 상태 확인
                if current_time - last_connection_check >= connection_check_interval:
                    self._check_connections()
                    last_connection_check = current_time
                
                # 오류 임계값 확인
                if self.error_count >= self.max_errors:
                    log_error(f"최대 오류 수 초과 ({self.error_count}회) - 시스템 종료")
                    send_system_alert("시스템 오류 한계 초과", f"오류 {self.error_count}회 발생", "error")
                    break
                
                # 10초마다 체크
                self.shutdown_event.wait(10)
                
            except Exception as e:
                log_error("메인 루프 오류", e)
                self.error_count += 1
                time.sleep(5)
    
    def _check_connections(self):
        """연결 상태 종합 확인"""
        issues = []
        
        # API 연결 확인
        if not connection_manager.is_connected:
            issues.append("API 연결 끊어짐")
        
        # WebSocket 연결 확인
        if not self.websocket_connected or not self.ws_handler.is_running:
            issues.append("WebSocket 연결 끊어짐")
        
        # 실시간 데이터 수신 확인 (5분 이상 수신 안됨)
        if (datetime.now() - self.last_price_update).total_seconds() > 300:
            issues.append("실시간 데이터 수신 중단")
        
        if issues:
            log_error(f"연결 문제 감지: {', '.join(issues)}")
            self._attempt_reconnection()
        else:
            # 모든 연결이 정상일 때만 간헐적 로그
            if self.received_data_count % 1000 == 0:  # 1000개마다
                log_info("🔗 모든 연결 정상")
    
    def _attempt_reconnection(self):
        """재연결 시도"""
        log_system("🔄 연결 복구 시도 중...")
        
        try:
            # API 연결 복구
            if not connection_manager.is_connected:
                connection_manager.test_connection()
            
            # WebSocket 재연결
            if not self.websocket_connected:
                symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
                self.ws_handler.stop_ws()
                time.sleep(2)
                self.ws_handler.start_ws(symbols)
                
                # 재연결 확인 (10초 대기)
                for _ in range(10):
                    if self.websocket_connected:
                        log_system("✅ WebSocket 재연결 성공")
                        break
                    time.sleep(1)
            
        except Exception as e:
            log_error("재연결 시도 실패", e)
    
    def _heartbeat_check(self):
        """시스템 생존 확인 - 상세 체크"""
        try:
            self.last_heartbeat = datetime.now()
            
            # 기본 상태 확인
            api_status = "✅" if connection_manager.is_connected else "❌"
            ws_status = "✅" if self.websocket_connected else "❌"
            
            # 데이터 수신 상태
            time_since_last_data = (datetime.now() - self.last_price_update).total_seconds()
            data_status = "✅" if time_since_last_data < 60 else "⚠️" if time_since_last_data < 300 else "❌"
            
            # 전략 상태
            strategy_status = "✅" if self.strategy_manager and self.strategy_manager.is_healthy() else "❌"
            
            log_info(f"💓 시스템 상태: API {api_status} | WS {ws_status} | 데이터 {data_status} | 전략 {strategy_status}")
            log_info(f"📊 수신 데이터: {self.received_data_count}건 | 처리 신호: {self.performance_stats['signals_processed']}개")
            
            # 문제 상황 알림
            if time_since_last_data > 300:  # 5분 이상 데이터 없음
                send_system_alert("데이터 수신 중단", f"마지막 데이터: {time_since_last_data:.0f}초 전", "warning")
            
        except Exception as e:
            log_error("Heartbeat 체크 오류", e)
    
    def _print_system_status(self):
        """시스템 상태 출력 - 실시간 데이터 포함"""
        if not self.strategy_manager:
            return
        
        # 운영 시간 계산
        uptime = datetime.now() - self.start_time if self.start_time else None
        
        print(f"\n{'='*70}")
        print(f"📊 실시간 트레이딩 시스템 상태 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        if uptime:
            print(f"⏱️  운영 시간: {uptime}")
        
        # 연결 상태
        print(f"🔗 API 연결: {'✅ 정상' if connection_manager.is_connected else '❌ 끊어짐'}")
        print(f"📡 WebSocket: {'✅ 정상' if self.websocket_connected else '❌ 끊어짐'}")
        
        # 데이터 수신 상태
        time_since_data = (datetime.now() - self.last_price_update).total_seconds()
        print(f"📊 실시간 데이터: {self.received_data_count}건 (마지막: {time_since_data:.0f}초 전)")
        
        # 성능 통계
        print(f"⚡ 처리된 신호: {self.performance_stats['signals_processed']}개")
        print(f"⚠️  오류 횟수: {self.error_count}/{self.max_errors}")
        
        # 전략 상태 출력
        self.strategy_manager.print_status()
        
        print(f"{'='*70}")
    
    def _on_api_reconnect(self):
        """API 연결 복구 시 콜백"""
        log_system("🔄 API 연결 복구됨")
        send_system_alert("API 연결 복구", "API 연결이 복구되었습니다", "info")
    
    def _on_api_disconnect(self):
        """API 연결 끊김 시 콜백"""
        log_error("🚨 API 연결 끊어짐")
        send_system_alert("API 연결 끊어짐", "API 연결이 끊어졌습니다. 재연결 시도 중...", "warning")
    
    def stop_trading(self):
        """트레이딩 중지"""
        if not self.is_running:
            return
        
        log_system("🛑 실시간 트레이딩 시스템 종료 시작...")
        self.is_running = False
        self.shutdown_event.set()
        
        try:
            # WebSocket 중지
            if self.ws_handler:
                log_system("📡 WebSocket 연결 종료 중...")
                self.ws_handler.stop_ws()
                self.websocket_connected = False
            
            # 모든 포지션 청산
            if self.strategy_manager:
                log_system("📤 모든 포지션 청산 중...")
                self.strategy_manager.close_all_positions()
                
                # 최종 요약 출력
                self.strategy_manager.print_final_summary()
            
            # 연결 모니터링 중지
            connection_manager.stop_connection_monitoring()
            
            # 종료 알림
            uptime = datetime.now() - self.start_time if self.start_time else None
            send_system_alert(
                "시스템 종료", 
                f"운영 시간: {uptime}\n수신 데이터: {self.received_data_count}건\n처리 신호: {self.performance_stats['signals_processed']}개\n오류 횟수: {self.error_count}회",
                "info"
            )
            
            print("\n" + "="*70)
            print("✅ 실시간 트레이딩 봇 종료 완료")
            if uptime:
                print(f"총 운영 시간: {uptime}")
            print(f"수신된 실시간 데이터: {self.received_data_count:,}건")
            print(f"처리된 신호: {self.performance_stats['signals_processed']}개")
            print(f"총 오류 횟수: {self.error_count}회")
            print("="*70)
            
        except Exception as e:
            log_error("시스템 종료 중 오류", e)
    
    def run_backtest(self, strategy_type: str, start_date: str, end_date: str):
        """백테스트 실행"""
        log_system(f"백테스트 시작: {strategy_type}")
        
        symbol = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])[0]
        initial_capital = TRADING_CONFIG.get('initial_capital', 10000)
        
        result = run_strategy_backtest(strategy_type, symbol, start_date, end_date, initial_capital)
        
        # 백테스트 결과 알림
        if result.metrics:
            total_return = result.metrics.get('total_return', 0) * 100
            win_rate = result.metrics.get('win_rate', 0) * 100
            max_dd = result.metrics.get('max_drawdown', 0) * 100
            
            send_system_alert(
                f"백테스트 완료 - {strategy_type}",
                f"수익률: {total_return:+.2f}%\n승률: {win_rate:.1f}%\n최대낙폭: {max_dd:.2f}%",
                "info"
            )
        
        return result

def setup_signal_handlers(trading_system: TradingSystem):
    """시그널 핸들러 설정 (우아한 종료)"""
    def signal_handler(signum, frame):
        print(f"\n🛑 종료 신호 수신: {signum}")
        trading_system.stop_trading()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 종료 신호

def main():
    """메인 함수"""
    # 명령행 인수 처리
    import argparse
    
    parser = argparse.ArgumentParser(description='OKX 실시간 데이터 연동 트레이딩 봇')
    parser.add_argument('--env', choices=['development', 'testing', 'production'], 
                       default='production', help='실행 환경')
    parser.add_argument('--backtest', help='백테스트 모드 (long 또는 short)')
    parser.add_argument('--start-date', default='2024-01-01', help='백테스트 시작 날짜')
    parser.add_argument('--end-date', default='2024-12-31', help='백테스트 종료 날짜')
    parser.add_argument('--config-test', action='store_true', help='설정 테스트만 실행')
    parser.add_argument('--connection-test', action='store_true', help='연결 테스트만 실행')
    
    args = parser.parse_args()
    
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
            if trading_system._test_api_connection():
                print("✅ 연결 테스트 통과")
                # WebSocket 연결도 테스트
                symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
                ws_handler = WebSocketHandler()
                public_thread, private_thread = ws_handler.start_ws(symbols)
                time.sleep(10)  # 10초 대기
                ws_handler.stop_ws()
                print("✅ WebSocket 테스트 완료")
                sys.exit(0)
            else:
                print("❌ 연결 테스트 실패")
                sys.exit(1)
        
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