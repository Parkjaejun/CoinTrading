# monitoring/condition_monitor.py
"""
실시간 조건 모니터링 시스템
가상 시뮬레이션 상태와 실제 거래 조건을 지속적으로 감시
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class TrendDirection(Enum):
    UPTREND = "상승장"
    DOWNTREND = "하락장"
    SIDEWAYS = "횡보"
    UNKNOWN = "미확인"

class SignalStatus(Enum):
    WAITING = "대기"
    APPROACHING = "접근"
    TRIGGERED = "발생"
    MISSED = "놓침"

@dataclass
class MarketCondition:
    """시장 조건 정보"""
    symbol: str
    timestamp: datetime
    current_price: float
    trend_direction: TrendDirection
    trend_strength: float  # 퍼센트
    ema_150: float
    ema_200: float
    ema_20: float
    ema_50: float
    ema_100: float

@dataclass
class SignalCondition:
    """신호 조건 정보"""
    signal_type: str  # "golden_cross", "dead_cross"
    status: SignalStatus
    distance_pct: float  # 크로스까지 거리 (%)
    estimated_time: Optional[str]  # 예상 시간
    confidence: float  # 신뢰도 (0-1)

@dataclass
class StrategyCondition:
    """전략 조건 정보"""
    strategy_name: str
    is_real_mode: bool
    current_capital: float
    initial_capital: float
    return_pct: float
    switch_threshold: float  # 실제거래 전환 임계값
    distance_to_switch: float  # 전환까지 거리

class ConditionMonitor:
    """거래 조건 실시간 모니터링"""
    
    def __init__(self):
        self.monitoring_active = True
        self.check_interval = 5  # 5초마다 체크
        self.last_check_time = 0
        self.condition_history = []
        self.max_history = 100  # 최대 히스토리 개수
        
        # 조건별 카운터
        self.counters = {
            'total_checks': 0,
            'trend_uptrend': 0,
            'trend_downtrend': 0,
            'trend_sideways': 0,
            'golden_cross_signals': 0,
            'dead_cross_signals': 0,
            'virtual_mode_count': 0,
            'real_mode_count': 0,
            'switch_opportunities': 0
        }
        
        # 알림 설정
        self.last_alert_time = {}
        self.alert_cooldown = 30  # 30초 쿨다운
        
        print("🔍 거래 조건 모니터링 시스템 초기화")
    
    def check_conditions(self, symbol: str, price_data: Dict[str, Any], 
                        strategy_manager=None) -> Dict[str, Any]:
        """실시간 조건 체크"""
        current_time = time.time()
        
        # 체크 간격 확인
        if current_time - self.last_check_time < self.check_interval:
            return {}
        
        self.last_check_time = current_time
        self.counters['total_checks'] += 1
        
        try:
            # 시장 조건 분석
            market_condition = self._analyze_market_conditions(symbol, price_data)
            
            # 신호 조건 체크
            signal_conditions = self._check_signal_conditions(price_data)
            
            # 전략 조건 체크
            strategy_conditions = self._check_strategy_conditions(strategy_manager)
            
            # 종합 상태
            overall_status = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'market_condition': market_condition,
                'signal_conditions': signal_conditions,
                'strategy_conditions': strategy_conditions,
                'counters': self.counters.copy(),
                'next_check_in': self.check_interval
            }
            
            # 히스토리 저장
            self._save_to_history(overall_status)
            
            # 중요한 변화 감지 및 로깅
            self._log_important_changes(overall_status)
            
            return overall_status
            
        except Exception as e:
            print(f"⚠️ 조건 체크 오류: {e}")
            return {}
    
    def _analyze_market_conditions(self, symbol: str, data: Dict[str, Any]) -> MarketCondition:
        """시장 조건 분석"""
        current_price = float(data.get('close', 0))
        ema_150 = float(data.get('ema_trend_fast', 0))
        ema_200 = float(data.get('ema_trend_slow', 0))
        ema_20 = float(data.get('curr_entry_fast', 0))
        ema_50 = float(data.get('curr_entry_slow', 0))
        ema_100 = float(data.get('curr_exit_slow', 0))
        
        # 트렌드 방향 및 강도 계산
        if ema_150 > 0 and ema_200 > 0:
            if ema_150 > ema_200:
                trend_direction = TrendDirection.UPTREND
                trend_strength = ((ema_150 - ema_200) / ema_200) * 100
                self.counters['trend_uptrend'] += 1
            elif ema_150 < ema_200:
                trend_direction = TrendDirection.DOWNTREND  
                trend_strength = ((ema_200 - ema_150) / ema_200) * 100
                self.counters['trend_downtrend'] += 1
            else:
                trend_direction = TrendDirection.SIDEWAYS
                trend_strength = 0
                self.counters['trend_sideways'] += 1
        else:
            trend_direction = TrendDirection.UNKNOWN
            trend_strength = 0
        
        return MarketCondition(
            symbol=symbol,
            timestamp=datetime.now(),
            current_price=current_price,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            ema_150=ema_150,
            ema_200=ema_200,
            ema_20=ema_20,
            ema_50=ema_50,
            ema_100=ema_100
        )
    
    def _check_signal_conditions(self, data: Dict[str, Any]) -> List[SignalCondition]:
        """신호 조건 체크"""
        conditions = []
        
        ema_20 = float(data.get('curr_entry_fast', 0))
        ema_50 = float(data.get('curr_entry_slow', 0))
        ema_100 = float(data.get('curr_exit_slow', 0))
        
        if ema_20 > 0 and ema_50 > 0:
            # 20/50 EMA 골든크로스 조건
            distance_pct = ((ema_20 - ema_50) / ema_50) * 100
            
            if distance_pct > 0.1:  # 이미 골든크로스
                status = SignalStatus.TRIGGERED
                self.counters['golden_cross_signals'] += 1
            elif distance_pct > -0.5:  # 접근 중
                status = SignalStatus.APPROACHING
            else:  # 대기 중
                status = SignalStatus.WAITING
            
            conditions.append(SignalCondition(
                signal_type="20/50 골든크로스",
                status=status,
                distance_pct=abs(distance_pct),
                estimated_time=self._estimate_cross_time(distance_pct),
                confidence=self._calculate_confidence(distance_pct)
            ))
        
        if ema_20 > 0 and ema_100 > 0:
            # 20/100 EMA 데드크로스 조건 (청산 신호)
            distance_pct = ((ema_20 - ema_100) / ema_100) * 100
            
            if distance_pct < -0.1:  # 이미 데드크로스
                status = SignalStatus.TRIGGERED
                self.counters['dead_cross_signals'] += 1
            elif distance_pct < 0.5:  # 접근 중
                status = SignalStatus.APPROACHING
            else:  # 대기 중
                status = SignalStatus.WAITING
            
            conditions.append(SignalCondition(
                signal_type="20/100 데드크로스",
                status=status,
                distance_pct=abs(distance_pct),
                estimated_time=self._estimate_cross_time(distance_pct),
                confidence=self._calculate_confidence(distance_pct)
            ))
        
        return conditions
    
    def _check_strategy_conditions(self, strategy_manager) -> List[StrategyCondition]:
        """전략 조건 체크"""
        conditions = []
        
        if not strategy_manager:
            return conditions
        
        try:
            # 전략 매니저에서 전략 정보 가져오기 (가상의 인터페이스)
            strategies = getattr(strategy_manager, 'strategies', {})
            
            for strategy_name, strategy in strategies.items():
                is_real_mode = getattr(strategy, 'is_real_mode', False)
                current_capital = getattr(strategy, 'current_capital', 0)
                initial_capital = getattr(strategy, 'initial_capital', 10000)
                
                if current_capital > 0 and initial_capital > 0:
                    return_pct = ((current_capital - initial_capital) / initial_capital) * 100
                    
                    # 전환 임계값 (롱: +30%, 숏: +20%)
                    switch_threshold = 30 if 'long' in strategy_name.lower() else 20
                    distance_to_switch = switch_threshold - return_pct
                    
                    if is_real_mode:
                        self.counters['real_mode_count'] += 1
                    else:
                        self.counters['virtual_mode_count'] += 1
                        
                        # 실제거래 전환 기회 감지
                        if return_pct >= switch_threshold:
                            self.counters['switch_opportunities'] += 1
                    
                    conditions.append(StrategyCondition(
                        strategy_name=strategy_name,
                        is_real_mode=is_real_mode,
                        current_capital=current_capital,
                        initial_capital=initial_capital,
                        return_pct=return_pct,
                        switch_threshold=switch_threshold,
                        distance_to_switch=max(0, distance_to_switch)
                    ))
        
        except Exception as e:
            print(f"⚠️ 전략 조건 체크 오류: {e}")
        
        return conditions
    
    def _estimate_cross_time(self, distance_pct: float) -> Optional[str]:
        """크로스오버 예상 시간 계산"""
        if abs(distance_pct) < 0.1:
            return "곧"
        elif abs(distance_pct) < 0.5:
            return "10-30분"
        elif abs(distance_pct) < 1.0:
            return "1-2시간"
        else:
            return "2시간 이상"
    
    def _calculate_confidence(self, distance_pct: float) -> float:
        """신호 신뢰도 계산"""
        abs_distance = abs(distance_pct)
        if abs_distance < 0.1:
            return 0.9
        elif abs_distance < 0.5:
            return 0.7
        elif abs_distance < 1.0:
            return 0.5
        else:
            return 0.3
    
    def _save_to_history(self, status: Dict[str, Any]):
        """히스토리에 저장"""
        self.condition_history.append(status)
        
        # 최대 개수 제한
        if len(self.condition_history) > self.max_history:
            self.condition_history = self.condition_history[-self.max_history:]
    
    def _log_important_changes(self, status: Dict[str, Any]):
        """중요한 변화 로깅"""
        market = status.get('market_condition')
        signals = status.get('signal_conditions', [])
        strategies = status.get('strategy_conditions', [])
        
        # 트렌드 변화 감지
        if market:
            trend_key = f"trend_{market.symbol}"
            if self._should_alert(trend_key):
                print(f"📊 {market.symbol}: {market.trend_direction.value} "
                      f"(강도: {market.trend_strength:.2f}%)")
        
        # 신호 상태 변화 감지
        for signal in signals:
            if signal.status == SignalStatus.APPROACHING:
                signal_key = f"signal_{signal.signal_type}"
                if self._should_alert(signal_key):
                    print(f"⚡ {signal.signal_type} 접근 중 "
                          f"(거리: {signal.distance_pct:.2f}%, "
                          f"예상: {signal.estimated_time})")
            
            elif signal.status == SignalStatus.TRIGGERED:
                print(f"🚨 {signal.signal_type} 발생!")
        
        # 전략 상태 변화 감지
        for strategy in strategies:
            if not strategy.is_real_mode and strategy.distance_to_switch < 5:
                strategy_key = f"strategy_{strategy.strategy_name}"
                if self._should_alert(strategy_key):
                    print(f"🎯 {strategy.strategy_name}: 실제거래 전환 임박 "
                          f"(+{strategy.return_pct:.1f}%, "
                          f"목표: +{strategy.switch_threshold}%)")
    
    def _should_alert(self, alert_key: str) -> bool:
        """알림 쿨다운 체크"""
        current_time = time.time()
        last_time = self.last_alert_time.get(alert_key, 0)
        
        if current_time - last_time > self.alert_cooldown:
            self.last_alert_time[alert_key] = current_time
            return True
        return False
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """요약 통계 반환"""
        total_checks = self.counters['total_checks']
        
        return {
            'total_checks': total_checks,
            'uptime_minutes': (time.time() - (total_checks * self.check_interval if total_checks > 0 else time.time())) / 60,
            'trend_distribution': {
                'uptrend': self.counters['trend_uptrend'],
                'downtrend': self.counters['trend_downtrend'],
                'sideways': self.counters['trend_sideways']
            },
            'signal_counts': {
                'golden_cross': self.counters['golden_cross_signals'],
                'dead_cross': self.counters['dead_cross_signals']
            },
            'mode_distribution': {
                'virtual': self.counters['virtual_mode_count'],
                'real': self.counters['real_mode_count']
            },
            'switch_opportunities': self.counters['switch_opportunities']
        }
    
    def get_recent_history(self, minutes: int = 30) -> List[Dict[str, Any]]:
        """최근 히스토리 반환"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        return [
            entry for entry in self.condition_history
            if entry.get('timestamp', datetime.min) > cutoff_time
        ]
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        print("🛑 조건 모니터링 시스템 중지됨")
