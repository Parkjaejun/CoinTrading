# gui/v2_strategy_bridge.py
"""
v2 전략 ↔ GUI 연동 브릿지

v2 LongStrategy의 SignalPipeline 로그를 GUI의 조건 모니터링 위젯에 표시
이메일 알림 상태도 GUI에서 확인 가능
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

# v2 모듈 import
try:
    from cointrading_v2.strategy.signal_pipeline import SignalPipeline, SignalEvent, ValidationResult
    from cointrading_v2.strategy.email_notifier import EmailNotifier
    V2_AVAILABLE = True
except ImportError:
    V2_AVAILABLE = False
    SignalPipeline = None
    SignalEvent = None
    ValidationResult = None
    EmailNotifier = None


class V2StrategyBridge(QObject):
    """
    v2 전략과 GUI를 연결하는 브릿지 클래스
    
    SignalPipeline의 이벤트를 GUI 시그널로 변환
    """
    
    # GUI 업데이트용 시그널
    signal_generated = pyqtSignal(dict)      # 시그널 생성됨
    trade_executed = pyqtSignal(dict)        # 거래 실행됨
    mode_switched = pyqtSignal(dict)         # 모드 전환됨
    validation_failed = pyqtSignal(dict)     # 검증 실패
    stats_updated = pyqtSignal(dict)         # 통계 업데이트
    log_message = pyqtSignal(str, str)       # (메시지, 타입)
    email_sent = pyqtSignal(dict)            # 이메일 발송됨
    
    def __init__(self, strategy_manager=None):
        super().__init__()
        self.strategy_manager = strategy_manager
        self.last_update_time = datetime.now()
        self.update_interval = 2  # 2초마다 업데이트
        
        # 통계 캐시
        self._cached_stats = {}
        self._last_signal_count = 0
        self._last_trade_count = 0
        
        # 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._periodic_update)
        
        if V2_AVAILABLE:
            print("✅ V2StrategyBridge 초기화 완료")
        else:
            print("⚠️ V2StrategyBridge: v2 모듈 없음")
    
    def set_strategy_manager(self, strategy_manager):
        """전략 매니저 설정"""
        self.strategy_manager = strategy_manager
        self.log_message.emit("전략 매니저 연결됨", "정보")
    
    def start_monitoring(self):
        """모니터링 시작"""
        self.update_timer.start(self.update_interval * 1000)
        self.log_message.emit("v2 전략 모니터링 시작", "정보")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.update_timer.stop()
        self.log_message.emit("v2 전략 모니터링 중지", "정보")
    
    def _periodic_update(self):
        """주기적 업데이트"""
        if not self.strategy_manager:
            return
        
        try:
            # 전략 상태 수집
            status = self._collect_strategy_status()
            if status:
                self.stats_updated.emit(status)
            
            # 새 이벤트 확인
            self._check_new_events()
            
        except Exception as e:
            self.log_message.emit(f"업데이트 오류: {e}", "오류")
    
    def _collect_strategy_status(self) -> Dict[str, Any]:
        """전략 상태 수집"""
        if not self.strategy_manager:
            return {}
        
        try:
            # v2 StrategyManager.get_total_status() 호출
            if hasattr(self.strategy_manager, 'get_total_status'):
                status = self.strategy_manager.get_total_status()
            elif hasattr(self.strategy_manager, 'get_status'):
                status = self.strategy_manager.get_status()
            else:
                return {}
            
            # GUI용 포맷 변환
            gui_status = {
                'total_capital': status.get('total_capital', 0),
                'total_pnl': status.get('total_pnl', 0),
                'total_trades': status.get('total_trades', 0),
                'win_rate': status.get('win_rate', 0),
                'signals_received': status.get('signals_received', 0),
                'signals_processed': status.get('signals_processed', 0),
                'uptime': status.get('uptime', '0:00:00'),
                'mode': status.get('mode', 'unknown'),
                'strategies': {}
            }
            
            # 개별 전략 상태
            for key, strat_status in status.get('strategies', {}).items():
                if isinstance(strat_status, dict):
                    gui_status['strategies'][key] = {
                        'mode': strat_status.get('mode', 'UNKNOWN'),
                        'capital': strat_status.get('real_capital', 0),
                        'position_open': strat_status.get('is_position_open', False),
                        'entry_price': strat_status.get('entry_price', 0),
                        'total_pnl': strat_status.get('total_pnl', 0),
                        'trade_count': strat_status.get('trade_count', 0),
                        'win_count': strat_status.get('win_count', 0),
                    }
            
            self._cached_stats = gui_status
            return gui_status
            
        except Exception as e:
            self.log_message.emit(f"상태 수집 오류: {e}", "오류")
            return {}
    
    def _check_new_events(self):
        """새 이벤트 확인 및 시그널 발송"""
        if not self.strategy_manager:
            return
        
        try:
            # 각 전략의 파이프라인 확인
            strategies = getattr(self.strategy_manager, 'strategies', {})
            
            for key, strategy in strategies.items():
                if not hasattr(strategy, 'pipeline'):
                    continue
                
                pipeline = strategy.pipeline
                
                # 새 시그널 확인
                current_signal_count = pipeline.signal_count
                if current_signal_count > self._last_signal_count:
                    # 새 시그널 발생
                    recent = pipeline.get_recent_signals(5)
                    for event in recent:
                        self._emit_signal_event(key, event)
                    self._last_signal_count = current_signal_count
                
                # 새 거래 확인
                current_trade_count = getattr(strategy, 'trade_count', 0)
                if current_trade_count > self._last_trade_count:
                    # 새 거래 발생
                    if hasattr(strategy, 'trades') and strategy.trades:
                        latest_trade = strategy.trades[-1]
                        self._emit_trade_event(key, latest_trade)
                    self._last_trade_count = current_trade_count
                    
        except Exception as e:
            pass  # 조용히 실패
    
    def _emit_signal_event(self, strategy_key: str, event):
        """시그널 이벤트 발송"""
        try:
            event_dict = {
                'strategy': strategy_key,
                'timestamp': str(event.timestamp) if hasattr(event, 'timestamp') else str(datetime.now()),
                'signal_type': event.signal_type if hasattr(event, 'signal_type') else 'UNKNOWN',
                'reason': event.reason if hasattr(event, 'reason') else '',
                'price': event.close_price if hasattr(event, 'close_price') else 0,
            }
            
            self.signal_generated.emit(event_dict)
            
            # 로그 메시지
            if event_dict['signal_type'] == 'ENTRY':
                self.log_message.emit(
                    f"[{strategy_key}] 진입 시그널 @ ${event_dict['price']:,.2f}",
                    "시그널"
                )
            elif event_dict['signal_type'] == 'EXIT':
                self.log_message.emit(
                    f"[{strategy_key}] 청산 시그널 @ ${event_dict['price']:,.2f} ({event_dict['reason']})",
                    "시그널"
                )
                
        except Exception as e:
            pass
    
    def _emit_trade_event(self, strategy_key: str, trade):
        """거래 이벤트 발송"""
        try:
            trade_dict = {
                'strategy': strategy_key,
                'entry_price': trade.entry_price if hasattr(trade, 'entry_price') else 0,
                'exit_price': trade.exit_price if hasattr(trade, 'exit_price') else 0,
                'pnl': trade.net_pnl if hasattr(trade, 'net_pnl') else 0,
                'is_win': trade.is_win if hasattr(trade, 'is_win') else False,
                'reason': trade.exit_reason if hasattr(trade, 'exit_reason') else '',
            }
            
            self.trade_executed.emit(trade_dict)
            
            # 로그 메시지
            emoji = "💰" if trade_dict['is_win'] else "📉"
            self.log_message.emit(
                f"{emoji} [{strategy_key}] 거래 완료: ${trade_dict['pnl']:+,.2f}",
                "거래"
            )
            
        except Exception as e:
            pass
    
    def notify_mode_switch(self, strategy_key: str, from_mode: str, to_mode: str, reason: str):
        """모드 전환 알림 (외부에서 호출)"""
        event_dict = {
            'strategy': strategy_key,
            'from_mode': from_mode,
            'to_mode': to_mode,
            'reason': reason,
            'timestamp': str(datetime.now()),
        }
        
        self.mode_switched.emit(event_dict)
        
        emoji = "⚠️" if to_mode == 'VIRTUAL' else "✅"
        self.log_message.emit(
            f"{emoji} [{strategy_key}] 모드 전환: {from_mode} → {to_mode}",
            "모드전환"
        )
    
    def notify_email_sent(self, email_type: str, details: dict):
        """이메일 발송 알림"""
        event_dict = {
            'type': email_type,
            'details': details,
            'timestamp': str(datetime.now()),
        }
        
        self.email_sent.emit(event_dict)
        self.log_message.emit(f"📧 이메일 발송: {email_type}", "이메일")
    
    def get_pipeline_summary(self, strategy_key: str = None) -> Dict[str, Any]:
        """파이프라인 요약 조회"""
        if not self.strategy_manager:
            return {}
        
        try:
            strategies = getattr(self.strategy_manager, 'strategies', {})
            
            if strategy_key and strategy_key in strategies:
                strategy = strategies[strategy_key]
                if hasattr(strategy, 'pipeline'):
                    return strategy.pipeline.get_stats()
                return {}
            
            # 전체 요약
            total_summary = {
                'total_signals': 0,
                'entry_signals': 0,
                'exit_signals': 0,
                'valid_signals': 0,
                'rejected_signals': 0,
            }
            
            for key, strategy in strategies.items():
                if hasattr(strategy, 'pipeline'):
                    stats = strategy.pipeline.get_stats()
                    total_summary['total_signals'] += stats.get('total_signals', 0)
                    total_summary['entry_signals'] += stats.get('entry_signals', 0)
                    total_summary['exit_signals'] += stats.get('exit_signals', 0)
                    total_summary['valid_signals'] += stats.get('valid_signals', 0)
                    total_summary['rejected_signals'] += stats.get('rejected_signals', 0)
            
            return total_summary
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_blocked_entries(self, count: int = 10) -> List[Dict]:
        """차단된 진입 시그널 조회"""
        if not self.strategy_manager:
            return []
        
        blocked = []
        try:
            strategies = getattr(self.strategy_manager, 'strategies', {})
            
            for key, strategy in strategies.items():
                if hasattr(strategy, 'pipeline'):
                    entries = strategy.pipeline.get_blocked_entries(count)
                    for entry in entries:
                        blocked.append({
                            'strategy': key,
                            'timestamp': str(entry.signal.timestamp) if hasattr(entry, 'signal') else '',
                            'reason': entry.rejection_reason if hasattr(entry, 'rejection_reason') else '',
                            'mode': entry.mode if hasattr(entry, 'mode') else '',
                        })
            
            return blocked[-count:]  # 최신 N개
            
        except Exception as e:
            return []


class GUILoggingEmailNotifier:
    """
    GUI 연동 이메일 알림 래퍼
    
    실제 EmailNotifier를 감싸서 GUI에도 로그 전송
    """
    
    def __init__(self, real_notifier=None, bridge: V2StrategyBridge = None):
        self.real_notifier = real_notifier
        self.bridge = bridge
        self.sent_count = 0
    
    def send_entry_alert(self, data: dict):
        """진입 알림"""
        self.sent_count += 1
        
        # 실제 이메일 발송
        if self.real_notifier:
            self.real_notifier.send_entry_alert(data)
        
        # GUI 알림
        if self.bridge:
            self.bridge.notify_email_sent('entry', data)
    
    def send_exit_alert(self, data: dict):
        """청산 알림"""
        self.sent_count += 1
        
        if self.real_notifier:
            self.real_notifier.send_exit_alert(data)
        
        if self.bridge:
            self.bridge.notify_email_sent('exit', data)
    
    def send_mode_switch_alert(self, data: dict):
        """모드 전환 알림"""
        self.sent_count += 1
        
        if self.real_notifier:
            self.real_notifier.send_mode_switch_alert(data)
        
        if self.bridge:
            self.bridge.notify_email_sent('mode_switch', data)
            self.bridge.notify_mode_switch(
                data.get('symbol', ''),
                data.get('from_mode', ''),
                data.get('to_mode', ''),
                data.get('reason', '')
            )
    
    def send_error_alert(self, data: dict):
        """오류 알림"""
        self.sent_count += 1
        
        if self.real_notifier:
            self.real_notifier.send_error_alert(data)
        
        if self.bridge:
            self.bridge.notify_email_sent('error', data)


# 전역 브릿지 인스턴스
_global_bridge: Optional[V2StrategyBridge] = None


def get_strategy_bridge() -> V2StrategyBridge:
    """전역 브릿지 인스턴스 조회"""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = V2StrategyBridge()
    return _global_bridge


def setup_strategy_bridge(strategy_manager, start_monitoring: bool = True) -> V2StrategyBridge:
    """
    브릿지 설정 및 시작
    
    사용법:
        from gui.v2_strategy_bridge import setup_strategy_bridge
        bridge = setup_strategy_bridge(strategy_manager)
        bridge.log_message.connect(my_log_function)
    """
    bridge = get_strategy_bridge()
    bridge.set_strategy_manager(strategy_manager)
    
    if start_monitoring:
        bridge.start_monitoring()
    
    return bridge
