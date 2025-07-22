"""
듀얼 전략 관리자
롱/숏 전략을 병렬로 실행하되 복잡한 스레드 풀 없이 순차 처리
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from strategy.long_strategy import LongStrategy
from strategy.short_strategy import ShortStrategy
from okx.position import SimplePositionManager
from utils.data_generator import convert_to_strategy_data

class DualStrategyManager:
    """듀얼 자산 전략 관리자"""
    
    def __init__(self, total_capital: float = 10000, symbols: List[str] = None):
        self.total_capital = total_capital
        self.symbols = symbols or ['BTC-USDT-SWAP']
        
        # 자본 분배 (50:50)
        capital_per_strategy = total_capital * 0.5
        
        # 전략 인스턴스 생성
        self.strategies = {}
        for symbol in self.symbols:
            self.strategies[f"long_{symbol}"] = LongStrategy(symbol, capital_per_strategy)
            self.strategies[f"short_{symbol}"] = ShortStrategy(symbol, capital_per_strategy)
        
        # 포지션 관리자
        self.position_manager = SimplePositionManager()
        
        # 상태 추적
        self.start_time = datetime.now()
        self.total_signals = 0
        self.executed_trades = 0
        self.last_status_update = datetime.now()
        
        print(f"🚀 듀얼 전략 관리자 초기화")
        print(f"총 자본: ${total_capital:,.0f}")
        print(f"전략별 할당: ${capital_per_strategy:,.0f} (롱/숏 각각)")
        print(f"대상 심볼: {', '.join(self.symbols)}")
        print(f"활성 전략: {len(self.strategies)}개")
    
    def process_signal(self, symbol: str, raw_data: Dict[str, Any]):
        """실시간 신호 처리"""
        try:
            self.total_signals += 1
            
            # 해당 심볼의 전략들 처리
            long_strategy_key = f"long_{symbol}"
            short_strategy_key = f"short_{symbol}"
            
            signals_processed = 0
            
            # 롱 전략 처리
            if long_strategy_key in self.strategies:
                long_data = convert_to_strategy_data(raw_data, 'long')
                long_signal = self.strategies[long_strategy_key].process_signal(long_data)
                
                if long_signal:
                    self._execute_signal(long_signal)
                    signals_processed += 1
            
            # 숏 전략 처리
            if short_strategy_key in self.strategies:
                short_data = convert_to_strategy_data(raw_data, 'short')
                short_signal = self.strategies[short_strategy_key].process_signal(short_data)
                
                if short_signal:
                    self._execute_signal(short_signal)
                    signals_processed += 1
            
            # 포지션 가격 업데이트
            if 'close' in raw_data:
                self.position_manager.update_position_prices({symbol: raw_data['close']})
            
            return signals_processed > 0
            
        except Exception as e:
            print(f"❌ 신호 처리 오류 ({symbol}): {e}")
            return False
    
    def _execute_signal(self, signal: Dict[str, Any]):
        """신호 실행"""
        try:
            action = signal['action']
            symbol = signal['symbol']
            strategy_name = signal['strategy_name']
            
            if action.startswith('enter'):
                # 진입 신호
                if signal.get('is_real_mode', True):  # 실제 거래 모드만 실행
                    position_id = self.position_manager.open_position(
                        symbol=symbol,
                        side=signal['side'],
                        size=signal['size'],
                        leverage=signal['leverage'],
                        strategy_name=strategy_name,
                        trailing_stop_ratio=signal.get('trailing_stop_ratio')
                    )
                    
                    if position_id:
                        self.executed_trades += 1
                        self._notify(f"📈 {strategy_name} 진입", signal)
                else:
                    print(f"🔄 {strategy_name} 가상 모드 진입 (실제 주문 없음)")
                    
            elif action.startswith('exit'):
                # 청산 신호
                success = self.position_manager.close_position(symbol, signal.get('reason', 'strategy'))
                if success:
                    self.executed_trades += 1
                    self._notify(f"📉 {strategy_name} 청산", signal)
            
        except Exception as e:
            print(f"❌ 신호 실행 오류: {e}")
    
    def _notify(self, title: str, signal: Dict[str, Any]):
        """알림 (콘솔 출력)"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        symbol = signal.get('symbol', 'N/A')
        side = signal.get('side', 'N/A').upper()
        price = signal.get('price', signal.get('exit_price', 0))
        
        print(f"[{timestamp}] {title}")
        print(f"  📊 {symbol} {side} @ ${price:.2f}")
        
        if 'pnl' in signal:
            pnl = signal['pnl']
            pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            print(f"  💰 PnL: {pnl_str}")
        
        if 'reason' in signal:
            print(f"  📝 사유: {signal['reason']}")
    
    def get_strategy_status(self, strategy_key: str):
        """개별 전략 상태"""
        if strategy_key not in self.strategies:
            return {}
        
        return self.strategies[strategy_key].get_status()
    
    def close_all_positions(self):
        """모든 포지션 강제 청산"""
        print("🛑 모든 포지션 청산 중...")
        self.position_manager.close_all_positions()
    
    def print_status(self):
        """현재 상태 출력"""
        current_time = datetime.now()
        runtime = current_time - self.start_time
        
        print(f"\n{'='*60}")
        print(f"🤖 듀얼 전략 시스템 상태")
        print(f"{'='*60}")
        print(f"실행 시간: {runtime}")
        print(f"처리된 신호: {self.total_signals:,}개")
        print(f"실행된 거래: {self.executed_trades}건")
        
        # 포지션 상태
        self.position_manager.print_status()
        
        # 전략별 상태
        print(f"\n📋 전략별 상태:")
        for strategy_key, strategy in self.strategies.items():
            status = strategy.get_status()
            mode = "🟢 실제" if status.get('is_real_mode', True) else "🔵 가상"
            capital = status.get('current_capital', 0)
            trades = status.get('trade_count', 0)
            win_rate = status.get('win_rate', 0)
            
            print(f"  {strategy_key}: {mode} | 자본: ${capital:.0f} | 거래: {trades}회 | 승률: {win_rate:.1f}%")
        
        self.last_status_update = current_time
        print(f"{'='*60}")
    
    def print_final_summary(self):
        """최종 요약"""
        runtime = datetime.now() - self.start_time
        
        print(f"\n🏁 최종 거래 요약")
        print(f"=" * 40)
        print(f"총 실행 시간: {runtime}")
        print(f"처리된 신호: {self.total_signals:,}개")
        print(f"실행된 거래: {self.executed_trades}건")
        
        # 전략별 최종 자본
        total_final_capital = 0
        for strategy_key, strategy in self.strategies.items():
            status = strategy.get_status()
            final_capital = status.get('current_capital', 0)
            total_final_capital += final_capital
            
            initial_capital = self.total_capital * 0.5
            pnl = final_capital - initial_capital
            pnl_pct = (pnl / initial_capital) * 100
            
            print(f"{strategy_key}: ${final_capital:.0f} ({pnl:+.0f}, {pnl_pct:+.1f}%)")
        
        total_pnl = total_final_capital - self.total_capital
        total_pnl_pct = (total_pnl / self.total_capital) * 100
        
        print(f"=" * 40)
        print(f"초기 자본: ${self.total_capital:,.0f}")
        print(f"최종 자본: ${total_final_capital:,.0f}")
        print(f"총 손익: {total_pnl:+,.0f} ({total_pnl_pct:+.2f}%)")
        print(f"=" * 40)
    
    def is_healthy(self):
        """시스템 건강 상태 확인"""
        try:
            # 기본 체크
            if not self.strategies:
                return False
            
            # 각 전략이 정상 작동하는지 확인
            for strategy in self.strategies.values():
                if not hasattr(strategy, 'get_status'):
                    return False
            
            return True
        except:
            return False