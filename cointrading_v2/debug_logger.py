# debug_logger.py
"""
CoinTrading v2 디버그 로거
- 상세한 시그널/주문 로깅
- 문제 추적 및 분석
- 파일/콘솔 출력
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import json
import sys


class DebugLogger:
    """디버그 로거"""
    
    def __init__(self, 
                 name: str = "CoinTrading",
                 log_to_file: bool = True,
                 log_to_console: bool = True,
                 log_dir: str = "logs",
                 log_level: str = "INFO"):
        """
        Args:
            name: 로거 이름
            log_to_file: 파일 로깅 여부
            log_to_console: 콘솔 출력 여부
            log_dir: 로그 디렉토리
            log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
        """
        self.name = name
        self.log_to_file = log_to_file
        self.log_to_console = log_to_console
        self.log_dir = Path(log_dir)
        self.log_level = log_level
        
        self.levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        self.current_level = self.levels.get(log_level, 1)
        
        # 로그 파일 설정
        if log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = self.log_dir / f"{name}_{timestamp}.log"
            self.signal_file = self.log_dir / f"{name}_signals_{timestamp}.jsonl"
            self.trade_file = self.log_dir / f"{name}_trades_{timestamp}.jsonl"
        
        self._log("INFO", f"DebugLogger 초기화: {name}")
    
    def _should_log(self, level: str) -> bool:
        """로그 레벨 체크"""
        return self.levels.get(level, 1) >= self.current_level
    
    def _format_message(self, level: str, message: str) -> str:
        """로그 메시지 포맷"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return f"[{timestamp}] [{level:7}] [{self.name}] {message}"
    
    def _log(self, level: str, message: str):
        """로그 출력"""
        if not self._should_log(level):
            return
        
        formatted = self._format_message(level, message)
        
        if self.log_to_console:
            # 레벨별 색상
            colors = {
                "DEBUG": "\033[90m",    # 회색
                "INFO": "\033[0m",       # 기본
                "WARNING": "\033[93m",   # 노랑
                "ERROR": "\033[91m",     # 빨강
            }
            reset = "\033[0m"
            color = colors.get(level, "")
            print(f"{color}{formatted}{reset}")
        
        if self.log_to_file and hasattr(self, 'log_file'):
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
    
    def debug(self, message: str):
        self._log("DEBUG", message)
    
    def info(self, message: str):
        self._log("INFO", message)
    
    def warning(self, message: str):
        self._log("WARNING", message)
    
    def error(self, message: str):
        self._log("ERROR", message)
    
    # ===== 특화 로깅 =====
    
    def log_signal(self, signal_data: Dict[str, Any]):
        """시그널 로깅 (JSONL)"""
        signal_data['_logged_at'] = datetime.now().isoformat()
        
        self.debug(f"Signal: {signal_data.get('signal_type', 'NONE')} - {signal_data.get('reason', '')}")
        
        if self.log_to_file and hasattr(self, 'signal_file'):
            with open(self.signal_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(signal_data, default=str) + "\n")
    
    def log_trade(self, trade_data: Dict[str, Any]):
        """거래 로깅 (JSONL)"""
        trade_data['_logged_at'] = datetime.now().isoformat()
        
        pnl = trade_data.get('net_pnl', 0)
        emoji = "💰" if pnl > 0 else "📉"
        self.info(f"{emoji} Trade: PnL=${pnl:+,.2f} | {trade_data.get('reason_exit', '')}")
        
        if self.log_to_file and hasattr(self, 'trade_file'):
            with open(self.trade_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(trade_data, default=str) + "\n")
    
    def log_mode_switch(self, from_mode: str, to_mode: str, reason: str, details: Dict = None):
        """모드 전환 로깅"""
        emoji = "⚠️" if to_mode == "VIRTUAL" else "✅"
        self.warning(f"{emoji} Mode Switch: {from_mode} → {to_mode} | {reason}")
        
        if details:
            self.debug(f"Mode Switch Details: {json.dumps(details, default=str)}")
    
    def log_order(self, action: str, details: Dict[str, Any]):
        """주문 로깅"""
        price = details.get('price', 0)
        mode = details.get('mode', 'UNKNOWN')
        
        if action == "ENTRY":
            self.info(f"📈 Order ENTRY [{mode}] @ ${price:,.2f}")
        else:
            pnl = details.get('net_pnl', 0)
            self.info(f"📉 Order EXIT [{mode}] @ ${price:,.2f} | PnL=${pnl:+,.2f}")
    
    def log_engine_status(self, status: Dict[str, Any]):
        """엔진 상태 로깅"""
        self.debug(f"Engine Status: mode={status.get('mode')}, "
                   f"real=${status.get('real_capital', 0):,.2f}, "
                   f"position={'Yes' if status.get('has_position') else 'No'}")
    
    def log_pipeline_status(self, status: Dict[str, Any]):
        """파이프라인 상태 로깅"""
        stats = status.get('stats', {})
        self.debug(f"Pipeline: signals={stats.get('total_signals', 0)}, "
                   f"valid={stats.get('valid_signals', 0)}, "
                   f"rejected={stats.get('rejected_signals', 0)}")
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any] = None):
        """컨텍스트와 함께 에러 로깅"""
        import traceback
        
        self.error(f"Exception: {type(error).__name__}: {str(error)}")
        self.error(f"Traceback:\n{traceback.format_exc()}")
        
        if context:
            self.error(f"Context: {json.dumps(context, default=str)}")
    
    # ===== 분석 도구 =====
    
    def get_signal_summary(self) -> Dict[str, Any]:
        """시그널 로그 요약"""
        if not hasattr(self, 'signal_file') or not self.signal_file.exists():
            return {}
        
        signals = []
        with open(self.signal_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    signals.append(json.loads(line))
                except:
                    pass
        
        if not signals:
            return {}
        
        entry_signals = [s for s in signals if s.get('signal_type') == 'ENTRY']
        exit_signals = [s for s in signals if s.get('signal_type') == 'EXIT']
        
        return {
            'total_signals': len(signals),
            'entry_signals': len(entry_signals),
            'exit_signals': len(exit_signals),
            'first_signal': signals[0].get('_logged_at') if signals else None,
            'last_signal': signals[-1].get('_logged_at') if signals else None,
        }
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """거래 로그 요약"""
        if not hasattr(self, 'trade_file') or not self.trade_file.exists():
            return {}
        
        trades = []
        with open(self.trade_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    trades.append(json.loads(line))
                except:
                    pass
        
        if not trades:
            return {}
        
        pnls = [t.get('net_pnl', 0) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'total_pnl': sum(pnls),
            'avg_win': sum(wins) / len(wins) if wins else 0,
            'avg_loss': sum(losses) / len(losses) if losses else 0,
        }


# ===== 조건 모니터 =====

class ConditionMonitor:
    """거래 조건 모니터링"""
    
    def __init__(self, logger: DebugLogger = None):
        self.logger = logger or DebugLogger("ConditionMonitor", log_to_file=False)
        
        # 조건 히스토리
        self.condition_history: List[Dict] = []
        self.max_history = 100
        
        # 카운터
        self.counters = {
            'total_checks': 0,
            'trend_uptrend': 0,
            'trend_downtrend': 0,
            'entry_signals': 0,
            'exit_signals': 0,
            'blocked_entries': 0,
        }
    
    def check_and_log(self, 
                      timestamp: Any,
                      close_price: float,
                      ema_trend_fast: float,
                      ema_trend_slow: float,
                      entry_condition: bool,
                      exit_condition: bool,
                      has_position: bool,
                      mode: str) -> Dict[str, Any]:
        """조건 체크 및 로깅"""
        self.counters['total_checks'] += 1
        
        # 트렌드 분석
        is_uptrend = ema_trend_fast > ema_trend_slow
        trend_strength = ((ema_trend_fast - ema_trend_slow) / ema_trend_slow * 100) if ema_trend_slow else 0
        
        if is_uptrend:
            self.counters['trend_uptrend'] += 1
        else:
            self.counters['trend_downtrend'] += 1
        
        # 시그널 분석
        if entry_condition and is_uptrend and not has_position:
            self.counters['entry_signals'] += 1
        
        if exit_condition and has_position:
            self.counters['exit_signals'] += 1
        
        if entry_condition and not is_uptrend:
            self.counters['blocked_entries'] += 1
        
        # 결과 기록
        result = {
            'timestamp': str(timestamp),
            'close_price': close_price,
            'is_uptrend': is_uptrend,
            'trend_strength': trend_strength,
            'entry_condition': entry_condition,
            'exit_condition': exit_condition,
            'has_position': has_position,
            'mode': mode,
            'would_enter': entry_condition and is_uptrend and not has_position,
            'would_exit': exit_condition and has_position,
        }
        
        self.condition_history.append(result)
        if len(self.condition_history) > self.max_history:
            self.condition_history = self.condition_history[-self.max_history:]
        
        return result
    
    def print_summary(self):
        """요약 출력"""
        total = self.counters['total_checks']
        if total == 0:
            print("조건 체크 기록 없음")
            return
        
        print(f"\n{'='*50}")
        print(f"📊 Condition Monitor Summary")
        print(f"{'='*50}")
        print(f"총 체크: {total}")
        print(f"상승장 비율: {self.counters['trend_uptrend'] / total * 100:.1f}%")
        print(f"하락장 비율: {self.counters['trend_downtrend'] / total * 100:.1f}%")
        print(f"진입 시그널: {self.counters['entry_signals']}")
        print(f"청산 시그널: {self.counters['exit_signals']}")
        print(f"차단된 진입: {self.counters['blocked_entries']} (트렌드 불일치)")
        print(f"{'='*50}\n")
    
    def get_recent_conditions(self, n: int = 10) -> List[Dict]:
        """최근 조건 조회"""
        return self.condition_history[-n:]


# ===== 전역 로거 =====

_default_logger: Optional[DebugLogger] = None


def get_logger() -> DebugLogger:
    """전역 로거 가져오기"""
    global _default_logger
    if _default_logger is None:
        _default_logger = DebugLogger()
    return _default_logger


def set_logger(logger: DebugLogger):
    """전역 로거 설정"""
    global _default_logger
    _default_logger = logger


# 편의 함수
def log_debug(msg: str): get_logger().debug(msg)
def log_info(msg: str): get_logger().info(msg)
def log_warning(msg: str): get_logger().warning(msg)
def log_error(msg: str): get_logger().error(msg)
