# strategy/strategy_manager.py
"""
전략 매니저 v2 (Long Only)

여러 심볼에 대한 Long 전략을 통합 관리
- Short 전략 제거 (Long Only)
- 향상된 모니터링
- 포트폴리오 수준 상태 관리
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List

from strategy.long_strategy import LongStrategy
from strategy.email_notifier import EmailNotifier, MockEmailNotifier


class StrategyManager:
    """
    Long Only 전략 매니저 v2
    
    기존 DualStrategyManager 대체
    """
    
    def __init__(self, total_capital: float, symbols: List[str] = None,
                 email_notifier: EmailNotifier = None):
        """
        Args:
            total_capital: 총 자본
            symbols: 거래 심볼 리스트
            email_notifier: 이메일 알림 객체 (옵션)
        """
        self.total_capital = total_capital
        self.symbols = symbols or ['BTC-USDT-SWAP']
        self.strategies: Dict[str, LongStrategy] = {}
        
        # 이메일 알림
        self.email_notifier = email_notifier
        
        # 모니터링 관련
        self.last_status_time = 0
        self.status_interval = 120  # 2분마다 전체 상태 출력
        self.total_signals_processed = 0
        
        # 성과 추적
        self.start_time = datetime.now()
        self.trade_history: List[Dict] = []
        
        # 각 심볼별로 Long 전략 생성
        capital_per_strategy = total_capital / len(self.symbols)
        
        for symbol in self.symbols:
            strategy_key = f"long_{symbol}"
            self.strategies[strategy_key] = LongStrategy(
                symbol=symbol,
                initial_capital=capital_per_strategy,
                email_notifier=email_notifier
            )
        
        print(f"✅ StrategyManager v2 초기화 (Long Only)")
        print(f"   - 심볼: {self.symbols}")
        print(f"   - 전략 수: {len(self.strategies)}")
        print(f"   - 전략별 자본: ${capital_per_strategy:,.2f}")
        
        self._print_strategy_overview()
    
    def process_signal(self, symbol: str, data: Dict[str, Any]) -> List[Dict]:
        """
        신호 처리
        
        Args:
            symbol: 거래 심볼
            data: 캔들 데이터
        
        Returns:
            거래 결과 리스트
        """
        current_time = time.time()
        
        # 전체 상태 출력 (2분마다)
        if current_time - self.last_status_time >= self.status_interval:
            self._print_comprehensive_status(data)
            self.last_status_time = current_time
        
        strategy_key = f"long_{symbol}"
        results = []
        
        if strategy_key in self.strategies:
            result = self.strategies[strategy_key].process_signal(data)
            if result:
                results.append(result)
                self.trade_history.append({
                    **result,
                    'timestamp': datetime.now(),
                    'strategy_type': 'long'
                })
                self.total_signals_processed += 1
        
        return results
    
    def get_strategy(self, symbol: str) -> Optional[LongStrategy]:
        """
        특정 심볼의 전략 조회
        
        Args:
            symbol: 거래 심볼
        
        Returns:
            LongStrategy 객체 또는 None
        """
        strategy_key = f"long_{symbol}"
        return self.strategies.get(strategy_key)
    
    def get_all_strategies(self) -> Dict[str, LongStrategy]:
        """모든 전략 조회"""
        return self.strategies
    
    def _print_strategy_overview(self):
        """전략 개요 출력"""
        print(f"\n{'='*80}")
        print(f"🎯 Long Only 전략 매니저 v2 개요")
        print(f"{'='*80}")
        
        for strategy_key, strategy in self.strategies.items():
            print(f"📊 {strategy_key}:")
            print(f"    💰 초기 자본: ${strategy.initial_capital:,.2f}")
            print(f"    ⚡ 레버리지: {strategy.leverage}x")
            print(f"    📉 트레일링 스탑: {strategy.trailing_stop_ratio*100:.1f}%")
            print(f"    🎯 진입: 150>200 EMA + 20>50 EMA 골든크로스")
            print(f"    🛑 청산: 20<100 EMA 데드크로스 또는 트레일링 스탑")
            print(f"    🔄 모드전환: {strategy.stop_loss_ratio*100:.0f}% 손실→가상, "
                  f"{strategy.reentry_gain_ratio*100:.0f}% 회복→실제")
            print()
        
        print(f"{'='*80}\n")
    
    def _print_comprehensive_status(self, latest_data: Dict[str, Any]):
        """종합 상태 출력"""
        current_price = latest_data.get('close', 0)
        uptime = datetime.now() - self.start_time
        
        real_mode_count = sum(1 for s in self.strategies.values() if s.is_real_mode)
        virtual_mode_count = len(self.strategies) - real_mode_count
        
        print(f"\n{'🔍' * 40}")
        print(f"📊 Long Only 전략 매니저 v2 종합 상태")
        print(f"{'🔍' * 40}")
        print(f"⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕒 운영 시간: {uptime}")
        print(f"💰 현재가: ${current_price:,.2f}")
        print(f"📡 처리된 신호: {self.total_signals_processed}개")
        print(f"🎯 실제 모드: {real_mode_count}개 전략")
        print(f"🎮 가상 모드: {virtual_mode_count}개 전략")
        
        # 전략별 상세 상태
        print(f"\n📋 전략별 상세 상태:")
        print(f"{'─' * 80}")
        
        total_real_capital = 0
        total_pnl = 0
        
        for strategy_key, strategy in self.strategies.items():
            mode = "실제" if strategy.is_real_mode else "가상"
            current_capital = strategy.real_capital if strategy.is_real_mode else strategy.virtual_capital
            
            if strategy.is_real_mode:
                total_real_capital += strategy.real_capital
            total_pnl += strategy.total_pnl
            
            win_rate = (strategy.win_count / strategy.trade_count * 100) if strategy.trade_count > 0 else 0
            
            print(f"  {strategy_key:20} | {mode:2} | "
                  f"${current_capital:10,.2f} | "
                  f"거래:{strategy.trade_count:3}회 | "
                  f"승률:{win_rate:5.1f}% | "
                  f"PnL:{strategy.total_pnl:+10.2f}")
            
            # 활성 포지션 정보
            if strategy.is_position_open:
                pnl = (current_price - strategy.entry_price) * strategy.position_size
                pnl_pct = ((current_price - strategy.entry_price) / strategy.entry_price * 100 * strategy.leverage)
                print(f"    📈 활성 포지션: 진입가 ${strategy.entry_price:.2f} → "
                      f"PnL {pnl:+.2f} ({pnl_pct:+.2f}%)")
        
        print(f"{'─' * 80}")
        
        # 포트폴리오 요약
        total_return = ((total_real_capital - self.total_capital) / self.total_capital * 100) if self.total_capital > 0 else 0
        
        print(f"\n💼 포트폴리오 요약:")
        print(f"  💰 초기 자본: ${self.total_capital:,.2f}")
        print(f"  💎 현재 자본 (REAL): ${total_real_capital:,.2f}")
        print(f"  📊 총 수익률: {total_return:+.2f}%")
        print(f"  🏆 총 PnL: ${total_pnl:+,.2f}")
        
        print(f"{'🔍' * 40}\n")
    
    def get_total_status(self) -> Dict[str, Any]:
        """전체 상태 조회"""
        total_real = sum(s.real_capital for s in self.strategies.values())
        total_pnl = sum(s.total_pnl for s in self.strategies.values())
        total_trades = sum(s.trade_count for s in self.strategies.values())
        total_wins = sum(s.win_count for s in self.strategies.values())
        
        return {
            'total_capital': total_real,
            'initial_capital': self.total_capital,
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'total_wins': total_wins,
            'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
            'roi_pct': (total_real - self.total_capital) / self.total_capital * 100 if self.total_capital > 0 else 0,
            'strategies': {k: s.get_status() for k, s in self.strategies.items()},
            'uptime': str(datetime.now() - self.start_time),
        }
    
    def get_debug_status(self) -> Dict[str, Any]:
        """디버그 상태 조회"""
        return {
            **self.get_total_status(),
            'strategies_debug': {k: s.get_debug_status() for k, s in self.strategies.items()},
            'trade_history': self.trade_history[-20:],  # 최근 20개
        }
    
    def print_summary(self):
        """전체 요약 출력"""
        status = self.get_total_status()
        
        print(f"\n{'='*70}")
        print(f"📊 Long Only 전략 매니저 v2 최종 요약")
        print(f"{'='*70}")
        print(f"⏰ 운영 시간: {status['uptime']}")
        print(f"💰 초기 자본: ${status['initial_capital']:,.2f}")
        print(f"💎 현재 자본: ${status['total_capital']:,.2f}")
        print(f"📈 총 수익률: {status['roi_pct']:+.2f}%")
        print(f"🏆 총 PnL: ${status['total_pnl']:+,.2f}")
        print(f"📊 총 거래: {status['total_trades']}회")
        print(f"🎯 승률: {status['win_rate']:.1f}%")
        print(f"{'='*70}")
        
        # 각 전략별 요약
        for strategy_key, strategy in self.strategies.items():
            strategy.print_summary()


# 하위 호환용 별칭
LongOnlyStrategyManager = StrategyManager
DualStrategyManager = StrategyManager  # 기존 코드 호환


class EnhancedMonitoringStrategyManager(StrategyManager):
    """
    향상된 모니터링 기능이 포함된 전략 매니저
    
    기존 EnhancedDualStrategyManager 대체
    """
    
    def __init__(self, total_capital: float, symbols: List[str] = None,
                 email_notifier: EmailNotifier = None):
        super().__init__(total_capital, symbols, email_notifier)
        
        # 향상된 모니터링 설정
        self.status_interval = 60  # 1분마다 상태 출력 (더 자주)
        self.detailed_logging = True
        
        print(f"✅ EnhancedMonitoringStrategyManager 초기화")
    
    def process_signal(self, symbol: str, data: Dict[str, Any]) -> List[Dict]:
        """신호 처리 - 향상된 로깅"""
        results = super().process_signal(symbol, data)
        
        # 거래 발생 시 상세 로깅
        if results and self.detailed_logging:
            for result in results:
                self._log_trade_event(result)
        
        return results
    
    def _log_trade_event(self, result: Dict[str, Any]):
        """거래 이벤트 상세 로깅"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        action = result.get('action', '')
        symbol = result.get('symbol', '')
        
        if action == 'entry':
            price = result.get('entry_price', 0)
            mode = "실제" if result.get('is_real_mode', True) else "가상"
            print(f"\n{'🔥' * 20}")
            print(f"[{timestamp}] 📈 LONG 진입 이벤트")
            print(f"  심볼: {symbol}")
            print(f"  가격: ${price:,.2f}")
            print(f"  모드: {mode}")
            print(f"{'🔥' * 20}\n")
            
        elif action == 'exit':
            price = result.get('exit_price', 0)
            pnl = result.get('net_pnl', 0)
            reason = result.get('reason', '')
            mode = "실제" if result.get('is_real_mode', True) else "가상"
            emoji = "💰" if pnl > 0 else "📉"
            
            print(f"\n{emoji * 20}")
            print(f"[{timestamp}] 📉 LONG 청산 이벤트")
            print(f"  심볼: {symbol}")
            print(f"  가격: ${price:,.2f}")
            print(f"  PnL: ${pnl:+,.2f}")
            print(f"  모드: {mode}")
            print(f"  이유: {reason}")
            print(f"{emoji * 20}\n")


# 하위 호환용 별칭
EnhancedDualStrategyManager = EnhancedMonitoringStrategyManager
