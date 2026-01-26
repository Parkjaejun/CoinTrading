# strategy/dual_manager.py
"""
듀얼 전략 관리자 v2 (Long Only + 이메일 알림 + GUI 연동)

v2 기능:
- Long Only 전략 (Short 제거)
- 이메일 알림 (진입/청산/모드전환)
- SignalPipeline 디버깅
- GUI 브릿지 연동

기존 인터페이스 완전 호환
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from collections import deque
import time

# 로깅
try:
    from utils.logger import log_system, log_error, log_info
except ImportError:
    def log_system(msg): print(f"[SYSTEM] {msg}")
    def log_error(msg, e=None): print(f"[ERROR] {msg}: {e}" if e else f"[ERROR] {msg}")
    def log_info(msg): print(f"[INFO] {msg}")

# v2 전략 import
try:
    from cointrading_v2.strategy.long_strategy import LongStrategy
    from cointrading_v2.strategy.email_notifier import EmailNotifier, MockEmailNotifier
    from cointrading_v2.strategy.signal_pipeline import SignalPipeline
    V2_AVAILABLE = True
    log_system("✅ v2 LongStrategy + EmailNotifier 로드 성공")
except ImportError as e:
    V2_AVAILABLE = False
    log_error(f"v2 모듈 로드 실패, 기존 방식 사용", e)
    try:
        from strategy.long_strategy import LongStrategy
        from strategy.short_strategy import ShortStrategy
    except ImportError:
        LongStrategy = None
        ShortStrategy = None

# 설정 import
try:
    from config import (
        TRADING_CONFIG, LONG_STRATEGY_CONFIG, 
        EMA_PERIODS, NOTIFICATION_CONFIG
    )
except ImportError:
    TRADING_CONFIG = {'symbols': ['BTC-USDT-SWAP'], 'initial_capital': 10000}
    LONG_STRATEGY_CONFIG = {'leverage': 10, 'trailing_stop': 0.10}
    EMA_PERIODS = {'trend_fast': 150, 'trend_slow': 200}
    NOTIFICATION_CONFIG = {'email': {'enabled': False}}

# GUI 브릿지 (옵션)
try:
    from gui.v2_strategy_bridge import V2StrategyBridge, GUILoggingEmailNotifier
    GUI_BRIDGE_AVAILABLE = True
except ImportError:
    GUI_BRIDGE_AVAILABLE = False
    V2StrategyBridge = None
    GUILoggingEmailNotifier = None


def create_email_notifier(gui_bridge=None) -> Optional[Any]:
    """
    이메일 알림 객체 생성
    
    Args:
        gui_bridge: GUI 브릿지 (있으면 GUI에도 로그 표시)
    
    Returns:
        EmailNotifier 또는 MockEmailNotifier
    """
    if not V2_AVAILABLE:
        return None
    
    try:
        # 이메일 설정 확인
        email_config = NOTIFICATION_CONFIG.get('email', {})
        
        real_notifier = None
        
        if email_config.get('enabled') and email_config.get('sender'):
            real_notifier = EmailNotifier(
                smtp_server=email_config.get('smtp_server', 'smtp.gmail.com'),
                smtp_port=email_config.get('smtp_port', 587),
                sender_email=email_config.get('sender', ''),
                sender_password=email_config.get('password', ''),
                recipient_email=email_config.get('recipient', '')
            )
            log_system("✅ 이메일 알림 활성화")
        else:
            real_notifier = MockEmailNotifier()
            log_system("⚠️ 이메일 설정 없음 - MockEmailNotifier 사용")
        
        # GUI 브릿지 연동
        if gui_bridge and GUI_BRIDGE_AVAILABLE and GUILoggingEmailNotifier:
            return GUILoggingEmailNotifier(real_notifier, gui_bridge)
        
        return real_notifier
        
    except Exception as e:
        log_error("이메일 알림 초기화 실패", e)
        return MockEmailNotifier() if V2_AVAILABLE else None


class DualStrategyManager:
    """
    듀얼 전략 관리자 v2
    
    v2 모드: Long Only + 이메일 알림 + GUI 연동
    폴백 모드: 기존 Long + Short
    """
    
    def __init__(self, total_capital: float = 10000, 
                 symbols: List[str] = None,
                 capital_allocation: float = 1.0,
                 email_notifier: Any = None,
                 gui_bridge: Any = None):
        """
        Args:
            total_capital: 총 자본
            symbols: 거래 심볼 리스트
            capital_allocation: 자본 사용 비율
            email_notifier: 이메일 알림 객체 (None이면 자동 생성)
            gui_bridge: GUI 브릿지 객체 (GUI 연동용)
        """
        self.total_capital = total_capital
        self.symbols = symbols or TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
        self.capital_allocation = capital_allocation
        self.gui_bridge = gui_bridge
        
        effective_capital = total_capital * capital_allocation
        
        # 이메일 알림 설정
        self.email_notifier = email_notifier or create_email_notifier(gui_bridge)
        
        # 전략 초기화
        self.strategies = {}
        self._use_v2 = V2_AVAILABLE
        
        if self._use_v2:
            self._init_v2_strategies(effective_capital)
        else:
            self._init_legacy_strategies(effective_capital)
        
        # 상태 추적
        self.start_time = datetime.now()
        self.total_signals_received = 0
        self.total_signals_processed = 0
        self.executed_trades = 0
        self.last_status_time = datetime.now()
        
        # 로그 콜백 (GUI용)
        self._log_callbacks: List[Callable] = []
        
        # 성능 통계
        self.performance_stats = {
            'ticker_updates': 0,
            'strategy_signals': 0,
            'ema_calculations': 0,
            'failed_trades': 0
        }
        
        self._print_init_summary()
    
    def _init_v2_strategies(self, capital: float):
        """v2 전략 초기화 (Long Only)"""
        capital_per_symbol = capital / len(self.symbols)
        
        for symbol in self.symbols:
            strategy = LongStrategy(
                symbol=symbol,
                initial_capital=capital_per_symbol,
                email_notifier=self.email_notifier
            )
            self.strategies[f"long_{symbol}"] = strategy
        
        log_system(f"✅ v2 Long Only 전략 초기화: {len(self.strategies)}개")
        log_system(f"   - 심볼당 자본: ${capital_per_symbol:,.2f}")
        log_system(f"   - 이메일 알림: {'활성화' if self.email_notifier else '비활성화'}")
    
    def _init_legacy_strategies(self, capital: float):
        """기존 전략 초기화 (Long + Short)"""
        if LongStrategy is None:
            log_error("전략 클래스를 찾을 수 없습니다")
            return
        
        capital_per_strategy = capital * 0.5
        
        for symbol in self.symbols:
            self.strategies[f"long_{symbol}"] = LongStrategy(symbol, capital_per_strategy)
            if ShortStrategy:
                self.strategies[f"short_{symbol}"] = ShortStrategy(symbol, capital_per_strategy)
        
        log_system(f"⚠️ 기존 Long+Short 전략 초기화: {len(self.strategies)}개")
    
    def _print_init_summary(self):
        """초기화 요약 출력"""
        print(f"\n{'='*70}")
        print(f"🎯 전략 매니저 v2 초기화 {'(Long Only)' if self._use_v2 else '(기존 모드)'}")
        print(f"{'='*70}")
        print(f"📊 총 자본: ${self.total_capital:,.2f}")
        print(f"📈 심볼: {', '.join(self.symbols)}")
        print(f"⚡ 전략 수: {len(self.strategies)}개")
        
        if self._use_v2:
            print(f"📧 이메일 알림: {'✅ 활성화' if self.email_notifier else '❌ 비활성화'}")
            print(f"🔍 SignalPipeline: ✅ 활성화")
            print(f"🖥️ GUI 연동: {'✅ 활성화' if self.gui_bridge else '❌ 비활성화'}")
            print(f"\n📋 알고리즘:")
            print(f"   진입: EMA 150>200 (상승장) + EMA 20>50 골든크로스")
            print(f"   청산: EMA 20<100 데드크로스 또는 트레일링 스탑 10%")
            print(f"   모드전환: -20% → VIRTUAL, +30% → REAL")
        
        print(f"{'='*70}\n")
        
        self._emit_log("전략 매니저 초기화 완료", "정보")
    
    def set_gui_bridge(self, bridge):
        """GUI 브릿지 설정 (나중에 연결)"""
        self.gui_bridge = bridge
        if bridge:
            bridge.set_strategy_manager(self)
            self._emit_log("GUI 브릿지 연결됨", "정보")
    
    def add_log_callback(self, callback: Callable):
        """로그 콜백 추가"""
        self._log_callbacks.append(callback)
    
    def _emit_log(self, message: str, log_type: str = "정보"):
        """로그 발송"""
        for callback in self._log_callbacks:
            try:
                callback(message, log_type)
            except:
                pass
        
        # GUI 브릿지로도 전송
        if self.gui_bridge and hasattr(self.gui_bridge, 'log_message'):
            try:
                self.gui_bridge.log_message.emit(message, log_type)
            except:
                pass
    
    def process_signal(self, symbol: str, raw_data: Dict[str, Any]) -> bool:
        """
        실시간 신호 처리
        
        Args:
            symbol: 거래 심볼
            raw_data: 캔들/가격 데이터
        
        Returns:
            거래 실행 여부
        """
        self.total_signals_received += 1
        
        try:
            signals_generated = 0
            results = []
            
            # Long 전략 처리
            long_key = f"long_{symbol}"
            if long_key in self.strategies:
                strategy = self.strategies[long_key]
                result = strategy.process_signal(raw_data)
                
                if result:
                    signals_generated += 1
                    results.append(result)
                    self._handle_trade_result(symbol, result)
            
            # v2에서는 Short 전략 없음
            if not self._use_v2:
                short_key = f"short_{symbol}"
                if short_key in self.strategies:
                    strategy = self.strategies[short_key]
                    result = strategy.process_signal(raw_data)
                    
                    if result:
                        signals_generated += 1
                        results.append(result)
                        self._handle_trade_result(symbol, result)
            
            if signals_generated > 0:
                self.total_signals_processed += signals_generated
                self.executed_trades += signals_generated
                self.performance_stats['strategy_signals'] += signals_generated
            
            # 주기적 상태 출력 (2분마다)
            self._periodic_status_print()
            
            return signals_generated > 0
            
        except Exception as e:
            log_error(f"신호 처리 오류 ({symbol})", e)
            self._emit_log(f"신호 처리 오류: {e}", "오류")
            self.performance_stats['failed_trades'] += 1
            return False
    
    def _handle_trade_result(self, symbol: str, result: Dict[str, Any]):
        """거래 결과 처리 및 로깅"""
        action = result.get('action', 'unknown')
        price = result.get('entry_price') or result.get('exit_price', 0)
        mode = 'REAL' if result.get('is_real_mode', True) else 'VIRTUAL'
        
        if action == 'entry':
            log_msg = f"📈 [{symbol}] LONG 진입 [{mode}] @ ${price:,.2f}"
            log_info(log_msg)
            self._emit_log(log_msg, "거래")
            
        elif action == 'exit':
            pnl = result.get('pnl', 0)
            emoji = '💰' if pnl > 0 else '📉'
            log_msg = f"{emoji} [{symbol}] LONG 청산 [{mode}] @ ${price:,.2f} | PnL: ${pnl:+,.2f}"
            log_info(log_msg)
            self._emit_log(log_msg, "거래")
    
    def _periodic_status_print(self):
        """주기적 상태 출력"""
        now = datetime.now()
        if (now - self.last_status_time).total_seconds() >= 120:  # 2분
            self.print_status()
            self.last_status_time = now
    
    def get_status(self) -> Dict[str, Any]:
        """전체 상태 조회"""
        status = {
            'mode': 'v2_long_only' if self._use_v2 else 'legacy',
            'total_capital': self.total_capital,
            'symbols': self.symbols,
            'signals_received': self.total_signals_received,
            'signals_processed': self.total_signals_processed,
            'executed_trades': self.executed_trades,
            'uptime': str(datetime.now() - self.start_time),
            'strategies': {}
        }
        
        total_pnl = 0
        total_trades = 0
        total_wins = 0
        
        for key, strategy in self.strategies.items():
            try:
                strat_status = strategy.get_status()
                status['strategies'][key] = strat_status
                
                if 'total_pnl' in strat_status:
                    total_pnl += strat_status['total_pnl']
                if 'trade_count' in strat_status:
                    total_trades += strat_status['trade_count']
                if 'win_count' in strat_status:
                    total_wins += strat_status['win_count']
                    
            except Exception as e:
                status['strategies'][key] = {'error': str(e)}
        
        status['total_pnl'] = total_pnl
        status['total_trades'] = total_trades
        status['win_rate'] = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        return status
    
    def get_total_status(self) -> Dict[str, Any]:
        """get_status 별칭 (v2 호환)"""
        return self.get_status()
    
    def get_strategy(self, symbol: str, side: str = 'long') -> Optional[Any]:
        """특정 전략 조회"""
        key = f"{side}_{symbol}"
        return self.strategies.get(key)
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """SignalPipeline 요약 (v2 전용)"""
        if not self._use_v2:
            return {}
        
        total = {
            'total_signals': 0,
            'entry_signals': 0,
            'exit_signals': 0,
            'valid_signals': 0,
            'rejected_signals': 0,
        }
        
        for key, strategy in self.strategies.items():
            if hasattr(strategy, 'pipeline'):
                stats = strategy.pipeline.get_stats()
                total['total_signals'] += stats.get('total_signals', 0)
                total['entry_signals'] += stats.get('entry_signals', 0)
                total['exit_signals'] += stats.get('exit_signals', 0)
                total['valid_signals'] += stats.get('valid_signals', 0)
                total['rejected_signals'] += stats.get('rejected_signals', 0)
        
        return total
    
    def print_status(self):
        """상태 출력"""
        status = self.get_status()
        
        print(f"\n{'='*70}")
        print(f"📊 전략 매니저 상태 ({status['mode']})")
        print(f"{'='*70}")
        print(f"운영시간: {status['uptime']}")
        print(f"신호: {status['signals_received']} 수신 / {status['signals_processed']} 처리")
        print(f"거래: {status['executed_trades']}건")
        print(f"총 PnL: ${status['total_pnl']:+,.2f}")
        print(f"승률: {status['win_rate']:.1f}%")
        
        print(f"\n📈 전략별 상태:")
        for key, strat in status['strategies'].items():
            if isinstance(strat, dict) and 'error' not in strat:
                mode = strat.get('mode', 'UNKNOWN')
                capital = strat.get('real_capital', 0)
                pos = '포지션 있음' if strat.get('is_position_open') else '대기 중'
                print(f"   {key}: [{mode}] ${capital:,.2f} | {pos}")
        
        # SignalPipeline 요약
        if self._use_v2:
            pipeline = self.get_pipeline_summary()
            print(f"\n🔍 SignalPipeline:")
            print(f"   총 시그널: {pipeline.get('total_signals', 0)}")
            print(f"   검증 통과: {pipeline.get('valid_signals', 0)}")
            print(f"   검증 거부: {pipeline.get('rejected_signals', 0)}")
        
        print(f"{'='*70}\n")
        
        self._emit_log(f"상태 출력 - PnL: ${status['total_pnl']:+,.2f}", "정보")
    
    def print_summary(self):
        """요약 출력 (print_status 별칭)"""
        self.print_status()


# 하위 호환 별칭
StrategyManager = DualStrategyManager
RealTimeDualStrategyManager = DualStrategyManager
EnhancedDualStrategyManager = DualStrategyManager
