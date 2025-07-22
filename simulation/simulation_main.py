# simulation/simulation_main.py
"""
실시간 라이브 시뮬레이션 메인 시스템
실제 시장 데이터를 받아와서 가상 거래만 실행
"""

import sys
import time
import signal
import threading
from datetime import datetime
from typing import Optional

# 기존 모듈들 임포트
sys.path.append('..')
from config import TRADING_CONFIG, LONG_STRATEGY_CONFIG, SHORT_STRATEGY_CONFIG
from okx.websocket_handler import WebSocketHandler
from strategy.long_strategy import LongStrategy
from strategy.short_strategy import ShortStrategy
from utils.logger import log_system, log_error
from utils.notifications import send_system_alert

# 시뮬레이션 모듈들
from simulation.strategy_adapter import SimulationDualManager
from simulation.virtual_order_manager import virtual_order_manager

class LiveSimulationSystem:
    """실시간 라이브 시뮬레이션 시스템"""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.simulation_manager: Optional[SimulationDualManager] = None
        self.ws_handler: Optional[WebSocketHandler] = None
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        # 시스템 상태
        self.start_time: Optional[datetime] = None
        self.last_heartbeat = datetime.now()
        
        # 성능 통계
        self.signals_processed = 0
        self.virtual_trades_executed = 0
        
        print(f"🎮 실시간 라이브 시뮬레이션 시스템 초기화")
        print(f"💰 초기 가상 자본: ${initial_balance:,.2f}")
    
    def initialize_system(self):
        """시뮬레이션 시스템 초기화"""
        try:
            print("\n" + "="*70)
            print("🎮 실시간 라이브 시뮬레이션 시작")
            print("="*70)
            
            # 가상 주문 매니저 초기화 (이미 전역으로 생성됨)
            print(f"💰 가상 자본: ${self.initial_balance:,.2f}")
            
            # 거래 심볼
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            print(f"📊 대상 심볼: {', '.join(symbols)}")
            
            # 실제 전략 인스턴스 생성 (기존 코드 활용)
            long_strategy = LongStrategy(symbols[0], self.initial_balance / 2)
            short_strategy = ShortStrategy(symbols[0], self.initial_balance / 2)
            
            # 시뮬레이션용 듀얼 매니저 생성
            self.simulation_manager = SimulationDualManager(
                long_strategy=long_strategy,
                short_strategy=short_strategy,
                symbols=symbols
            )
            
            # WebSocket 핸들러 초기화 (실시간 데이터용)
            self.ws_handler = SimulationWebSocketHandler(
                simulation_manager=self.simulation_manager
            )
            
            print("✅ 시뮬레이션 시스템 초기화 완료")
            return True
            
        except Exception as e:
            log_error("시뮬레이션 시스템 초기화 실패", e)
            return False
    
    def start_simulation(self):
        """시뮬레이션 시작"""
        if self.is_running:
            print("⚠️ 시뮬레이션이 이미 실행 중입니다")
            return
        
        try:
            if not self.initialize_system():
                print("❌ 시스템 초기화 실패")
                return
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # WebSocket 시작 (실시간 데이터 수신)
            symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
            public_thread, private_thread = self.ws_handler.start_ws(symbols)
            
            print(f"\n🚀 실시간 라이브 시뮬레이션 시작")
            print(f"📊 대상 심볼: {', '.join(symbols)}")
            print(f"💰 초기 가상 자본: ${self.initial_balance:,.2f}")
            print(f"🎯 모드: 가상 거래 (실제 주문 없음)")
            print("📴 중지하려면 Ctrl+C를 누르세요")
            print("="*70)
            
            # 메인 실행 루프
            self._main_loop()
            
        except KeyboardInterrupt:
            print("\n🛑 사용자에 의한 시뮬레이션 중지")
        except Exception as e:
            log_error("시뮬레이션 실행 중 오류", e)
        finally:
            self.stop_simulation()
    
    def _main_loop(self):
        """메인 실행 루프"""
        last_status_time = 0
        last_heartbeat_time = 0
        status_interval = 300  # 5분마다 상태 출력
        heartbeat_interval = 60  # 1분마다 heartbeat
        
        while self.is_running and not self.shutdown_event.is_set():
            try:
                current_time = time.time()
                
                # 5분마다 포트폴리오 상태 출력
                if current_time - last_status_time >= status_interval:
                    self._print_simulation_status()
                    last_status_time = current_time
                
                # 1분마다 heartbeat
                if current_time - last_heartbeat_time >= heartbeat_interval:
                    self._heartbeat_check()
                    last_heartbeat_time = current_time
                
                # 10초마다 체크
                self.shutdown_event.wait(10)
                
            except Exception as e:
                log_error("시뮬레이션 메인 루프 오류", e)
                time.sleep(5)
    
    def _print_simulation_status(self):
        """시뮬레이션 상태 출력"""
        if not self.simulation_manager:
            return
        
        # 운영 시간 계산
        uptime = datetime.now() - self.start_time if self.start_time else None
        
        print(f"\n{'='*70}")
        print(f"🎮 실시간 라이브 시뮬레이션 상태 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        if uptime:
            print(f"⏱️  시뮬레이션 시간: {uptime}")
        
        print(f"📡 실시간 데이터: {'✅ 정상' if self.ws_handler.is_running else '❌ 끊어짐'}")
        print(f"📊 처리된 신호: {self.signals_processed}개")
        
        # 포트폴리오 상태 출력
        self.simulation_manager.print_status()
        
        print(f"{'='*70}")
    
    def _heartbeat_check(self):
        """시스템 생존 확인"""
        try:
            self.last_heartbeat = datetime.now()
            
            # WebSocket 상태 확인
            if not self.ws_handler.is_running:
                log_error("WebSocket 연결 끊어짐 감지")
                return
            
            # 가상 주문 매니저 상태 확인
            portfolio = virtual_order_manager.get_portfolio_summary()
            if portfolio['total_value'] <= 0:
                log_error("가상 자본 소진 - 시뮬레이션 중단")
                self.stop_simulation()
                return
            
            print(f"💓 시뮬레이션 정상 작동 중 - 가상 자산: ${portfolio['total_value']:,.2f}")
            
        except Exception as e:
            log_error("Heartbeat 체크 오류", e)
    
    def stop_simulation(self):
        """시뮬레이션 중지"""
        if not self.is_running:
            return
        
        print("\n🛑 시뮬레이션 시스템 종료 시작...")
        self.is_running = False
        self.shutdown_event.set()
        
        try:
            # WebSocket 중지
            if self.ws_handler:
                self.ws_handler.stop_ws()
                print("📡 실시간 데이터 수신 중지")
            
            # 모든 가상 포지션 청산
            if self.simulation_manager:
                self.simulation_manager.close_all_positions()
            
            # 최종 결과 출력
            self._print_final_results()
            
            print("\n✅ 실시간 라이브 시뮬레이션 종료 완료")
            
        except Exception as e:
            log_error("시뮬레이션 종료 중 오류", e)
    
    def _print_final_results(self):
        """최종 결과 출력"""
        if not self.simulation_manager:
            return
        
        uptime = datetime.now() - self.start_time if self.start_time else None
        portfolio = self.simulation_manager.get_portfolio_summary()
        trade_stats = self.simulation_manager.get_trade_summary()
        
        print(f"\n🏁 실시간 시뮬레이션 최종 결과")
        print(f"=" * 50)
        if uptime:
            print(f"총 시뮬레이션 시간: {uptime}")
        print(f"처리된 신호: {self.signals_processed:,}개")
        
        print(f"\n💰 포트폴리오 결과:")
        print(f"초기 자본: ${portfolio['initial_balance']:,.2f}")
        print(f"최종 자산: ${portfolio['total_value']:,.2f}")
        
        total_return = portfolio['total_return']
        print(f"총 수익률: {total_return:+.2f}%")
        
        if total_return > 0:
            print(f"🎉 수익 달성!")
        else:
            print(f"😞 손실 발생")
        
        print(f"\n📊 거래 통계:")
        print(f"총 거래: {trade_stats['total_trades']}회")
        print(f"승률: {trade_stats['win_rate']:.1f}%")
        print(f"수수료: ${portfolio['total_fees']:,.2f}")
        
        print(f"=" * 50)

class SimulationWebSocketHandler(WebSocketHandler):
    """시뮬레이션용 WebSocket 핸들러"""
    
    def __init__(self, simulation_manager):
        super().__init__()
        self.simulation_manager = simulation_manager
        print("📡 시뮬레이션용 WebSocket 핸들러 초기화")
    
    def _generate_strategy_signals(self, symbol):
        """전략 신호 생성 (시뮬레이션 버전)"""
        try:
            df = self.price_buffers[symbol].to_dataframe()
            if df is None or len(df) < max(EMA_PERIODS.values()) + 2:
                return
            
            # 기존 전략용 데이터 생성 로직 사용
            from utils.data_generator import generate_strategy_data
            from config import EMA_PERIODS
            
            strategy_data = generate_strategy_data(df, EMA_PERIODS)
            if strategy_data is None:
                return
            
            # 시뮬레이션 매니저에게 신호 전달
            signal_processed = self.simulation_manager.process_signal(symbol, strategy_data)
            
            if signal_processed:
                # 전역 신호 카운터 업데이트
                import simulation.simulation_main
                if hasattr(simulation.simulation_main, 'live_simulation'):
                    simulation.simulation_main.live_simulation.signals_processed += 1
                
        except Exception as e:
            log_error(f"시뮬레이션 신호 생성 오류 ({symbol})", e)

def setup_signal_handlers(simulation_system: LiveSimulationSystem):
    """시그널 핸들러 설정 (우아한 종료)"""
    def signal_handler(signum, frame):
        print(f"\n🛑 종료 신호 수신: {signum}")
        simulation_system.stop_simulation()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 종료 신호

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='OKX 실시간 라이브 트레이딩 시뮬레이션')
    parser.add_argument('--balance', type=float, default=10000.0, help='초기 가상 자본 ($)')
    parser.add_argument('--console', action='store_true', help='콘솔 모드 실행')
    
    args = parser.parse_args()
    
    # 전역 변수로 시뮬레이션 시스템 저장 (signal handler용)
    global live_simulation
    live_simulation = LiveSimulationSystem(initial_balance=args.balance)
    
    try:
        # 시그널 핸들러 설정
        setup_signal_handlers(live_simulation)
        
        # 시뮬레이션 시작
        live_simulation.start_simulation()
        
    except Exception as e:
        log_error("시뮬레이션 메인 함수 오류", e)
        print(f"❌ 시뮬레이션 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()