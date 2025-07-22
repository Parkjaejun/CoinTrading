"""
전략 관리 시스템
- 여러 전략의 병렬 실행
- 자금 분배 관리
- 실시간 신호 처리 및 주문 실행
- 전략 우선순위 관리
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from strategy.long_strategy import LongStrategy
from strategy.short_strategy import ShortStrategy
from okx.position_manager import PositionManager
from okx.position_tracker import PositionTracker
from okx.websocket_handler import WebSocketHandler
from utils.generate_latest_data import generate_latest_data_for_dual_asset
from config import TRADING_CONFIG, NOTIFICATION_CONFIG

class StrategyManager:
    def __init__(self, total_capital: float = 10000.0):
        self.total_capital = total_capital
        self.strategies: Dict[str, Dict] = {}
        
        # 컴포넌트 초기화
        self.position_manager = PositionManager()
        self.position_tracker = PositionTracker()
        self.ws_handler = None
        
        # 실행 상태
        self.is_running = False
        self.main_thread = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # EMA 기간 매핑 (각 전략의 EMA를 통합 관리)
        self.ema_periods = {
            'trend_fast': 150,    # 트렌드 확인용 150EMA
            'trend_slow': 200,    # 트렌드 확인용 200EMA
            'entry_fast': 20,     # 진입 신호용 20EMA
            'entry_slow': 50,     # 진입 신호용 50EMA
            'exit_fast_long': 20,     # 롱 청산용 20EMA
            'exit_slow_long': 100,    # 롱 청산용 100EMA
            'exit_fast_short': 100,   # 숏 청산용 100EMA  
            'exit_slow_short': 200    # 숏 청산용 200EMA
        }
        
        # 성과 추적
        self.start_time = None
        self.total_trades = 0
        self.successful_trades = 0
        
        print(f"전략 관리자 초기화 완료")
        print(f"총 자본: {total_capital} USDT")
    
    def add_strategy(self, strategy_type: str, symbol: str, capital_allocation: float = 0.5,
                    priority: int = 1, enabled: bool = True) -> bool:
        """전략 추가
        
        Args:
            strategy_type: 'long' 또는 'short'
            symbol: 거래 심볼 (예: BTC-USDT-SWAP)
            capital_allocation: 자본 할당 비율 (0.0 ~ 1.0)
            priority: 우선순위 (1이 가장 높음)
            enabled: 활성화 여부
        """
        try:
            strategy_id = f"{strategy_type}_{symbol}"
            allocated_capital = self.total_capital * capital_allocation
            
            if strategy_type == 'long':
                strategy_instance = LongStrategy(symbol, allocated_capital)
            elif strategy_type == 'short':
                strategy_instance = ShortStrategy(symbol, allocated_capital)
            else:
                print(f"지원하지 않는 전략 타입: {strategy_type}")
                return False
            
            self.strategies[strategy_id] = {
                'instance': strategy_instance,
                'type': strategy_type,
                'symbol': symbol,
                'capital_allocation': capital_allocation,
                'allocated_capital': allocated_capital,
                'priority': priority,
                'enabled': enabled,
                'last_signal_time': None,
                'position_id': None  # 현재 활성 포지션 ID
            }
            
            print(f"전략 추가 완료: {strategy_id}")
            print(f"  할당 자본: {allocated_capital:.2f} USDT ({capital_allocation*100:.1f}%)")
            print(f"  우선순위: {priority}")
            
            return True
            
        except Exception as e:
            print(f"전략 추가 실패: {e}")
            return False
    
    def remove_strategy(self, strategy_type: str, symbol: str) -> bool:
        """전략 제거"""
        strategy_id = f"{strategy_type}_{symbol}"
        
        if strategy_id not in self.strategies:
            print(f"전략을 찾을 수 없음: {strategy_id}")
            return False
        
        # 활성 포지션이 있으면 청산
        strategy_info = self.strategies[strategy_id]
        if strategy_info['position_id']:
            print(f"활성 포지션 청산 중: {strategy_id}")
            self.position_manager.close_position(strategy_info['position_id'], "strategy_removed")
        
        del self.strategies[strategy_id]
        print(f"전략 제거 완료: {strategy_id}")
        return True
    
    def set_strategy_priority(self, strategy_type: str, symbol: str, priority: int):
        """전략 우선순위 설정"""
        strategy_id = f"{strategy_type}_{symbol}"
        
        if strategy_id in self.strategies:
            self.strategies[strategy_id]['priority'] = priority
            print(f"우선순위 변경: {strategy_id} -> {priority}")
        else:
            print(f"전략을 찾을 수 없음: {strategy_id}")
    
    def enable_strategy(self, strategy_type: str, symbol: str, enabled: bool = True):
        """전략 활성화/비활성화"""
        strategy_id = f"{strategy_type}_{symbol}"
        
        if strategy_id in self.strategies:
            self.strategies[strategy_id]['enabled'] = enabled
            self.strategies[strategy_id]['instance'].is_active = enabled
            status = "활성화" if enabled else "비활성화"
            print(f"전략 {status}: {strategy_id}")
        else:
            print(f"전략을 찾을 수 없음: {strategy_id}")
    
    def start(self, symbols: List[str] = None):
        """전략 실행 시작"""
        if self.is_running:
            print("전략 관리자가 이미 실행 중입니다.")
            return
        
        if not self.strategies:
            print("실행할 전략이 없습니다. 먼저 전략을 추가하세요.")
            return
        
        # 기본 심볼 설정
        if symbols is None:
            symbols = list(set([info['symbol'] for info in self.strategies.values()]))
        
        print(f"전략 실행 시작: {len(self.strategies)}개 전략, {len(symbols)}개 심볼")
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # WebSocket 핸들러 초기화 및 시작
        self.ws_handler = WebSocketHandler(strategy_manager=self)
        
        try:
            # WebSocket 연결 시작
            public_thread, private_thread = self.ws_handler.start_ws(symbols)
            
            # 메인 실행 루프를 별도 스레드에서 실행
            self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
            self.main_thread.start()
            
            print("전략 실행 시작 완료")
            print("중지하려면 stop() 메서드를 호출하세요.")
            
        except Exception as e:
            print(f"전략 실행 시작 실패: {e}")
            self.stop()
    
    def stop(self):
        """전략 실행 중지"""
        if not self.is_running:
            print("전략 관리자가 실행되지 않고 있습니다.")
            return
        
        print("전략 실행 중지 중...")
        self.is_running = False
        
        # WebSocket 중지
        if self.ws_handler:
            self.ws_handler.stop_ws()
        
        # 모든 활성 포지션 청산
        self.close_all_positions()
        
        # 스레드 정리
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5)
        
        self.executor.shutdown(wait=True)
        
        # 최종 성과 리포트
        self._print_final_report()
        
        print("전략 실행 중지 완료")
    
    def _main_loop(self):
        """메인 실행 루프"""
        print("메인 루프 시작")
        
        while self.is_running:
            try:
                # 5초마다 상태 업데이트
                time.sleep(5)
                
                # 포지션 상태 업데이트
                self._update_positions()
                
                # 10분마다 상태 출력
                if int(time.time()) % 600 == 0:
                    self._print_status_summary()
                
            except Exception as e:
                print(f"메인 루프 오류: {e}")
                time.sleep(5)
    
    def process_signal(self, symbol: str, latest_data: Dict[str, Any]):
        """실시간 신호 처리"""
        try:
            # 해당 심볼의 모든 전략에 신호 전달
            relevant_strategies = [
                (strategy_id, info) for strategy_id, info in self.strategies.items()
                if info['symbol'] == symbol and info['enabled']
            ]
            
            if not relevant_strategies:
                return
            
            # 우선순위 순서로 정렬
            relevant_strategies.sort(key=lambda x: x[1]['priority'])
            
            # 전략별 데이터 변환 및 신호 처리
            for strategy_id, strategy_info in relevant_strategies:
                try:
                    # 전략에 맞는 데이터 형식으로 변환
                    strategy_data = self._convert_data_for_strategy(latest_data, strategy_info['type'])
                    
                    # 전략 인스턴스에서 신호 처리
                    signal = strategy_info['instance'].process_signal(strategy_data)
                    
                    if signal:
                        # 실제 주문 실행
                        self._execute_signal(strategy_id, signal)
                        
                except Exception as e:
                    print(f"전략 {strategy_id} 신호 처리 오류: {e}")
                    
        except Exception as e:
            print(f"신호 처리 오류: {e}")
    
    def _convert_data_for_strategy(self, latest_data: Dict[str, Any], strategy_type: str) -> Dict[str, Any]:
        """전략별로 데이터 형식 변환"""
        # 기본 데이터
        converted_data = {
            'timestamp': latest_data.get('timestamp'),
            'close': latest_data.get('close'),
            'ema_trend_fast': latest_data.get('ema_trend_fast'),    # 150EMA
            'ema_trend_slow': latest_data.get('ema_trend_slow'),    # 200EMA
            'curr_entry_fast': latest_data.get('ema_entry_fast'),  # 현재 20EMA
            'curr_entry_slow': latest_data.get('ema_entry_slow'),  # 현재 50EMA
            'prev_entry_fast': latest_data.get('prev_entry_fast'), # 이전 20EMA
            'prev_entry_slow': latest_data.get('prev_entry_slow')  # 이전 50EMA
        }
        
        # 전략별 청산 EMA 설정
        if strategy_type == 'long':
            converted_data.update({
                'curr_exit_fast': latest_data.get('ema_exit_fast_long'),   # 현재 20EMA
                'curr_exit_slow': latest_data.get('ema_exit_slow_long'),   # 현재 100EMA
                'prev_exit_fast': latest_data.get('prev_exit_fast_long'),  # 이전 20EMA
                'prev_exit_slow': latest_data.get('prev_exit_slow_long')   # 이전 100EMA
            })
        else:  # short
            converted_data.update({
                'curr_exit_fast': latest_data.get('ema_exit_fast_short'),  # 현재 100EMA
                'curr_exit_slow': latest_data.get('ema_exit_slow_short'),  # 현재 200EMA
                'prev_exit_fast': latest_data.get('prev_exit_fast_short'), # 이전 100EMA
                'prev_exit_slow': latest_data.get('prev_exit_slow_short')  # 이전 200EMA
            })
        
        return converted_data
    
    def _execute_signal(self, strategy_id: str, signal: Dict[str, Any]):
        """신호 실행 (실제 주문)"""
        try:
            strategy_info = self.strategies[strategy_id]
            
            if signal['action'].startswith('enter'):
                # 포지션 진입
                if signal['is_real_mode']:  # 실제 거래 모드만 실제 주문 실행
                    position_id = self.position_manager.open_position(
                        inst_id=signal['symbol'],
                        side=signal['side'],
                        size=signal['size'],
                        leverage=signal['leverage'],
                        strategy_name=signal['strategy_name'],
                        trailing_stop_ratio=signal.get('trailing_stop_ratio')
                    )
                    
                    if position_id:
                        strategy_info['position_id'] = position_id
                        
                        # 포지션 추적 시작
                        self.position_tracker.add_position(
                            position_id=position_id,
                            inst_id=signal['symbol'],
                            strategy_name=signal['strategy_name'],
                            side=signal['side'],
                            size=signal['size'],
                            entry_price=signal['price'],
                            leverage=signal['leverage'],
                            trailing_stop_ratio=signal.get('trailing_stop_ratio')
                        )
                        
                        # 알림 전송
                        self._send_notification(f"📈 포지션 진입", signal)
                        
                else:
                    print(f"[{strategy_id}] 가상 모드 - 실제 주문 생략")
            
            elif signal['action'].startswith('exit'):
                # 포지션 청산
                if strategy_info['position_id']:
                    success = self.position_manager.close_position(
                        strategy_info['position_id'],
                        signal['reason']
                    )
                    
                    if success:
                        # 포지션 추적 완료
                        self.position_tracker.close_position(
                            position_id=strategy_info['position_id'],
                            exit_price=signal['exit_price'],
                            realized_pnl=signal['pnl'],
                            exit_reason=signal['reason'],
                            fees=signal.get('fee', 0)
                        )
                        
                        strategy_info['position_id'] = None
                        self.total_trades += 1
                        if signal['pnl'] > 0:
                            self.successful_trades += 1
                        
                        # 알림 전송
                        self._send_notification(f"📉 포지션 청산", signal)
                
                strategy_info['last_signal_time'] = datetime.now()
                
        except Exception as e:
            print(f"신호 실행 오류: {e}")
    
    def _send_notification(self, title: str, signal: Dict[str, Any]):
        """알림 전송"""
        try:
            if not NOTIFICATION_CONFIG.get('enabled', False):
                return
            
            message = f"{title}\n"
            message += f"전략: {signal['strategy_name']}\n"
            message += f"심볼: {signal['symbol']}\n"
            message += f"방향: {signal['side'].upper()}\n"
            message += f"가격: {signal.get('price', signal.get('exit_price', 0)):.2f} USDT\n"
            
            if 'pnl' in signal:
                message += f"PnL: {signal['pnl']:+.2f} USDT\n"
                message += f"사유: {signal.get('reason', 'N/A')}\n"
            
            message += f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            print(f"알림: {message}")
            
            # TODO: 실제 알림 서비스 