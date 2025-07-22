# simulation/strategy_adapter.py
"""
기존 전략을 시뮬레이션용으로 변환하는 어댑터
실제 주문 대신 가상 주문 매니저를 사용
"""

from typing import Dict, Any, Optional
from datetime import datetime
from simulation.virtual_order_manager import virtual_order_manager

class SimulationStrategyAdapter:
    """시뮬레이션용 전략 어댑터"""
    
    def __init__(self, strategy_instance, symbol: str):
        self.strategy = strategy_instance
        self.symbol = symbol
        self.strategy_name = strategy_instance.strategy_name
        
        # 가상 포지션 추적
        self.virtual_position_open = False
        self.virtual_entry_price = 0.0
        self.virtual_position_side = None
        
        print(f"🎮 시뮬레이션 전략 어댑터 초기화: {self.strategy_name} - {symbol}")
    
    def process_signal(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """전략 신호 처리 (시뮬레이션 모드)"""
        try:
            # 기존 전략의 신호 처리 로직 호출
            signal = self.strategy.process_signal(data)
            
            if signal:
                # 실제 주문 대신 가상 주문으로 변환
                return self._convert_to_virtual_signal(signal, data)
            
            return None
            
        except Exception as e:
            print(f"❌ 시뮬레이션 전략 오류 ({self.symbol}): {e}")
            return None
    
    def _convert_to_virtual_signal(self, signal: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """실제 신호를 가상 신호로 변환"""
        action = signal['action']
        current_price = data.get('close', 0)
        
        if action.startswith('enter'):
            # 진입 신호 → 가상 주문
            return self._handle_virtual_entry(signal, current_price)
        
        elif action.startswith('exit'):
            # 청산 신호 → 가상 청산
            return self._handle_virtual_exit(signal, current_price)
        
        return None
    
    def _handle_virtual_entry(self, signal: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """가상 진입 처리"""
        if self.virtual_position_open:
            return None  # 이미 포지션이 있음
        
        side = signal.get('side', 'long')
        size = signal.get('size', 0.01)
        leverage = signal.get('leverage', 1)
        
        # 가상 주문 실행
        order_side = 'buy' if side == 'long' else 'sell'
        order_id = virtual_order_manager.place_market_order(
            symbol=self.symbol,
            side=order_side,
            size=size,
            strategy_name=self.strategy_name,
            leverage=leverage
        )
        
        if order_id:
            # 가상 포지션 상태 업데이트
            self.virtual_position_open = True
            self.virtual_entry_price = current_price
            self.virtual_position_side = side
            
            # 트레일링 스탑 설정 (있는 경우)
            trailing_ratio = signal.get('trailing_stop_ratio')
            if trailing_ratio:
                virtual_order_manager.place_trailing_stop(self.symbol, trailing_ratio)
            
            # 신호 리턴 (알림용)
            return {
                'action': f'virtual_{signal["action"]}',
                'symbol': self.symbol,
                'side': side,
                'size': size,
                'price': current_price,
                'leverage': leverage,
                'strategy_name': self.strategy_name,
                'order_id': order_id,
                'timestamp': datetime.now()
            }
        
        return None
    
    def _handle_virtual_exit(self, signal: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """가상 청산 처리"""
        if not self.virtual_position_open:
            return None  # 포지션이 없음
        
        reason = signal.get('reason', 'strategy')
        
        # 가상 포지션 청산
        success = virtual_order_manager.close_position(self.symbol, reason)
        
        if success:
            # 가상 포지션 상태 초기화
            self.virtual_position_open = False
            
            # PnL 계산
            if self.virtual_position_side == 'long':
                pnl = (current_price - self.virtual_entry_price) * signal.get('size', 0.01)
            else:
                pnl = (self.virtual_entry_price - current_price) * signal.get('size', 0.01)
            
            # 신호 리턴 (알림용)
            return {
                'action': f'virtual_{signal["action"]}',
                'symbol': self.symbol,
                'side': self.virtual_position_side,
                'exit_price': current_price,
                'pnl': pnl,
                'reason': reason,
                'strategy_name': self.strategy_name,
                'timestamp': datetime.now()
            }
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """전략 상태 (가상 + 원본 결합)"""
        original_status = self.strategy.get_status()
        
        # 가상 거래 정보 추가
        virtual_info = {
            'virtual_position_open': self.virtual_position_open,
            'virtual_entry_price': self.virtual_entry_price,
            'virtual_position_side': self.virtual_position_side
        }
        
        # 포트폴리오 정보 추가
        portfolio = virtual_order_manager.get_portfolio_summary()
        virtual_info.update({
            'virtual_balance': portfolio['current_balance'],
            'virtual_total_value': portfolio['total_value'],
            'virtual_unrealized_pnl': portfolio['unrealized_pnl'],
            'virtual_total_return': portfolio['total_return']
        })
        
        # 원본 상태와 병합
        combined_status = {**original_status, **virtual_info}
        return combined_status

class SimulationDualManager:
    """시뮬레이션용 듀얼 전략 매니저"""
    
    def __init__(self, long_strategy, short_strategy, symbols: list):
        self.symbols = symbols
        self.strategy_adapters = {}
        
        # 각 심볼별로 전략 어댑터 생성
        for symbol in symbols:
            self.strategy_adapters[f"long_{symbol}"] = SimulationStrategyAdapter(long_strategy, symbol)
            self.strategy_adapters[f"short_{symbol}"] = SimulationStrategyAdapter(short_strategy, symbol)
        
        print(f"🎮 시뮬레이션 듀얼 매니저 초기화: {len(self.strategy_adapters)}개 전략")
    
    def process_signal(self, symbol: str, raw_data: Dict[str, Any]):
        """실시간 신호 처리 (시뮬레이션)"""
        try:
            # 시장 가격 업데이트
            current_price = raw_data.get('close')
            if current_price:
                virtual_order_manager.update_market_price(symbol, current_price)
            
            signals_processed = 0
            
            # 롱 전략 처리
            long_adapter = self.strategy_adapters.get(f"long_{symbol}")
            if long_adapter:
                long_signal = long_adapter.process_signal(raw_data)
                if long_signal:
                    self._handle_signal_notification(long_signal)
                    signals_processed += 1
            
            # 숏 전략 처리  
            short_adapter = self.strategy_adapters.get(f"short_{symbol}")
            if short_adapter:
                short_signal = short_adapter.process_signal(raw_data)
                if short_signal:
                    self._handle_signal_notification(short_signal)
                    signals_processed += 1
            
            return signals_processed > 0
            
        except Exception as e:
            print(f"❌ 시뮬레이션 신호 처리 오류 ({symbol}): {e}")
            return False
    
    def _handle_signal_notification(self, signal: Dict[str, Any]):
        """신호 알림 처리"""
        action = signal['action']
        symbol = signal['symbol']
        strategy = signal['strategy_name']
        
        if action.startswith('virtual_enter'):
            side = signal['side'].upper()
            price = signal['price']
            print(f"🎮 [{strategy}] {symbol} {side} 진입 @ ${price:.2f}")
        
        elif action.startswith('virtual_exit'):
            side = signal['side'].upper()
            price = signal['exit_price']
            pnl = signal['pnl']
            reason = signal['reason']
            pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            print(f"🎮 [{strategy}] {symbol} {side} 청산 @ ${price:.2f} | PnL: {pnl_str} | {reason}")
    
    def get_portfolio_summary(self):
        """포트폴리오 요약"""
        return virtual_order_manager.get_portfolio_summary()
    
    def get_trade_summary(self):
        """거래 요약"""
        return virtual_order_manager.get_trade_summary()
    
    def print_status(self):
        """상태 출력"""
        virtual_order_manager.print_status()
    
    def close_all_positions(self):
        """모든 포지션 청산"""
        print("🛑 모든 가상 포지션 청산 중...")
        symbols_to_close = list(virtual_order_manager.positions.keys())
        
        for symbol in symbols_to_close:
            virtual_order_manager.close_position(symbol, "system_shutdown")
        
        print(f"✅ {len(symbols_to_close)}개 포지션 청산 완료")