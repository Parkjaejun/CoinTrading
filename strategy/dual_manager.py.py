# strategy/dual_manager.py
"""
듀얼 전략 관리자 (v2 호환 래퍼)

v2 StrategyManager를 DualStrategyManager 인터페이스로 제공
기존 코드 호환성 유지
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

# v2 StrategyManager import 시도
try:
    from cointrading_v2.strategy import StrategyManager as StrategyManagerV2
    from cointrading_v2.strategy import LongStrategy
    V2_AVAILABLE = True
    print("✅ v2 StrategyManager 로드 성공")
except ImportError:
    V2_AVAILABLE = False
    print("⚠️ v2 StrategyManager 없음 - 기존 로직 사용")


class DualStrategyManager:
    """
    듀얼 전략 관리자 (v2 호환)
    
    v2가 설치되어 있으면 v2 StrategyManager 사용 (Long Only)
    없으면 기존 Long+Short 로직 사용
    """
    
    def __init__(self, total_capital: float = 10000, 
                 symbols: List[str] = None,
                 capital_allocation: float = 1.0):
        """
        Args:
            total_capital: 총 자본
            symbols: 거래 심볼 리스트
            capital_allocation: 자본 사용 비율 (0.0~1.0)
        """
        self.total_capital = total_capital
        self.symbols = symbols or ['BTC-USDT-SWAP']
        self.capital_allocation = capital_allocation
        
        effective_capital = total_capital * capital_allocation
        
        if V2_AVAILABLE:
            # v2 StrategyManager 사용
            self._manager = StrategyManagerV2(
                total_capital=effective_capital,
                symbols=self.symbols,
                email_notifier=None
            )
            self._use_v2 = True
            print(f"✅ DualStrategyManager 초기화 (v2 Long Only)")
        else:
            # 기존 로직 (Long + Short)
            self._manager = None
            self._use_v2 = False
            self._init_legacy_strategies(effective_capital)
            print(f"✅ DualStrategyManager 초기화 (기존 Long+Short)")
        
        # 상태 추적
        self.start_time = datetime.now()
        self.total_signals = 0
        self.executed_trades = 0
    
    def _init_legacy_strategies(self, capital: float):
        """기존 Long+Short 전략 초기화 (폴백)"""
        try:
            from strategy.long_strategy import LongStrategy
            from strategy.short_strategy import ShortStrategy
            
            capital_per_strategy = capital * 0.5
            
            self.strategies = {}
            for symbol in self.symbols:
                self.strategies[f"long_{symbol}"] = LongStrategy(symbol, capital_per_strategy)
                self.strategies[f"short_{symbol}"] = ShortStrategy(symbol, capital_per_strategy)
                
        except ImportError as e:
            print(f"⚠️ 기존 전략 로드 실패: {e}")
            self.strategies = {}
    
    def process_signal(self, symbol: str, raw_data: Dict[str, Any]) -> bool:
        """
        실시간 신호 처리
        
        Args:
            symbol: 거래 심볼
            raw_data: 캔들 데이터
        
        Returns:
            거래 실행 여부
        """
        self.total_signals += 1
        
        if self._use_v2:
            # v2: StrategyManager.process_signal() 호출
            results = self._manager.process_signal(symbol, raw_data)
            if results:
                self.executed_trades += len(results)
                return True
            return False
        else:
            # 기존 로직
            return self._process_legacy_signal(symbol, raw_data)
    
    def _process_legacy_signal(self, symbol: str, raw_data: Dict[str, Any]) -> bool:
        """기존 Long+Short 신호 처리"""
        signals_processed = 0
        
        # 롱 전략
        long_key = f"long_{symbol}"
        if long_key in self.strategies:
            try:
                result = self.strategies[long_key].process_signal(raw_data)
                if result:
                    signals_processed += 1
            except Exception as e:
                print(f"⚠️ 롱 전략 오류: {e}")
        
        # 숏 전략
        short_key = f"short_{symbol}"
        if short_key in self.strategies:
            try:
                result = self.strategies[short_key].process_signal(raw_data)
                if result:
                    signals_processed += 1
            except Exception as e:
                print(f"⚠️ 숏 전략 오류: {e}")
        
        if signals_processed > 0:
            self.executed_trades += signals_processed
            return True
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """전체 상태 조회"""
        if self._use_v2:
            return self._manager.get_total_status()
        else:
            return self._get_legacy_status()
    
    def _get_legacy_status(self) -> Dict[str, Any]:
        """기존 전략 상태 조회"""
        status = {
            'total_capital': self.total_capital,
            'symbols': self.symbols,
            'total_signals': self.total_signals,
            'executed_trades': self.executed_trades,
            'uptime': str(datetime.now() - self.start_time),
            'strategies': {}
        }
        
        for key, strategy in self.strategies.items():
            try:
                status['strategies'][key] = strategy.get_status()
            except:
                status['strategies'][key] = {'error': 'status unavailable'}
        
        return status
    
    def get_strategy(self, symbol: str, side: str = 'long') -> Optional[Any]:
        """
        특정 전략 조회
        
        Args:
            symbol: 심볼
            side: 'long' 또는 'short'
        """
        if self._use_v2:
            # v2는 Long Only
            if side == 'long':
                return self._manager.get_strategy(symbol)
            return None
        else:
            key = f"{side}_{symbol}"
            return self.strategies.get(key)
    
    def print_status(self):
        """상태 출력"""
        if self._use_v2:
            self._manager.print_summary()
        else:
            status = self.get_status()
            print(f"\n{'='*60}")
            print(f"📊 DualStrategyManager 상태")
            print(f"{'='*60}")
            print(f"자본: ${status['total_capital']:,.2f}")
            print(f"심볼: {status['symbols']}")
            print(f"신호: {status['total_signals']}")
            print(f"거래: {status['executed_trades']}")
            print(f"운영시간: {status['uptime']}")
            print(f"{'='*60}\n")


# 하위 호환 별칭
StrategyManager = DualStrategyManager
