# monitoring/condition_monitor.py
"""
실시간 조건 모니터링 시스템
시장 조건과 전략 상태를 실시간으로 분석하고 GUI에 전달
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import queue

# 데이터 분석 모듈들
try:
    from data.okx_data_fetcher import OKXDataFetcher
    from utils.ta_indicators import calculate_ema
    DATA_FETCHER_AVAILABLE = True
except ImportError:
    DATA_FETCHER_AVAILABLE = False

@dataclass
class MarketCondition:
    """시장 조건 데이터 클래스"""
    timestamp: datetime
    symbol: str
    current_price: float
    trend_direction: str  # 'uptrend', 'downtrend', 'sideways'
    trend_strength: float  # -100 ~ +100
    ema_alignment: Dict[str, str]
    crossover_signals: List[str]
    volume_trend: str
    volatility: float

@dataclass
class StrategyCondition:
    """전략 조건 데이터 클래스"""
    strategy_id: str
    is_real_mode: bool
    can_enter: bool
    current_capital: float
    position_size: float
    mode_switch_progress: Dict[str, float]
    last_signal_time: Optional[datetime]
    performance_metrics: Dict[str, float]

class ConditionMonitor:
    """실시간 조건 모니터링 시스템"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC-USDT-SWAP']
        self.is_running = False
        self.monitor_thread = None
        
        # 데이터 저장
        self.condition_history = []
        self.max_history = 100
        
        # 통계 카운터
        self.counters = {
            'total_checks': 0,
            'long_signals': 0,
            'short_signals': 0,
            'trend_changes': 0,
            'api_errors': 0
        }
        
        # 이벤트 큐
        self.event_queue = queue.Queue()
        
        # 콜백 함수들
        self.callbacks = {
            'market_condition_update': [],
            'strategy_condition_update': [],
            'signal_detected': [],
            'error_occurred': []
        }
        
        # 데이터 페처
        if DATA_FETCHER_AVAILABLE:
            self.data_fetcher = OKXDataFetcher()
        else:
            self.data_fetcher = None
        
        # 마지막 데이터 캐시
        self.last_market_data = {}
        self.last_trend_direction = None
        
        print("🔍 조건 모니터 초기화 완료")
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.is_running:
            print("⚠️ 모니터링이 이미 실행 중입니다")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        print("🚀 실시간 조건 모니터링 시작")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        print("⏹️ 실시간 조건 모니터링 중지")
    
    def add_callback(self, event_type: str, callback_func):
        """콜백 함수 등록"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback_func)
        else:
            print(f"⚠️ 알 수 없는 이벤트 타입: {event_type}")
    
    def _monitoring_loop(self):
        """메인 모니터링 루프"""
        while self.is_running:
            try:
                # 각 심볼에 대해 조건 분석
                for symbol in self.symbols:
                    condition_data = self._analyze_conditions(symbol)
                    
                    if condition_data:
                        # 히스토리에 추가
                        self.condition_history.append(condition_data)
                        if len(self.condition_history) > self.max_history:
                            self.condition_history = self.condition_history[-self.max_history:]
                        
                        # 콜백 실행
                        self._trigger_callbacks('market_condition_update', condition_data)
                        
                        # 신호 감지 확인
                        self._check_signals(condition_data)
                
                # 통계 업데이트
                self.counters['total_checks'] += 1
                
                # 30초 대기
                time.sleep(30)
                
            except Exception as e:
                print(f"❌ 모니터링 루프 오류: {e}")
                self.counters['api_errors'] += 1
                self._trigger_callbacks('error_occurred', {'error': str(e), 'timestamp': datetime.now()})
                time.sleep(60)  # 오류 시 더 길게 대기
    
    def _analyze_conditions(self, symbol: str) -> Optional[Dict[str, Any]]:
        """시장 조건 분석"""
        try:
            # 데이터 가져오기
            if not self.data_fetcher:
                # 더미 데이터 생성 (테스트용)
                return self._generate_dummy_condition_data(symbol)
            
            # 실제 데이터 분석
            market_data = self._fetch_market_data(symbol)
            if not market_data:
                return None
            
            # 트렌드 분석
            trend_analysis = self._analyze_trend(market_data)
            
            # 크로스오버 신호 분석
            crossover_signals = self._detect_crossovers(market_data)
            
            # 전략 조건 분석
            strategy_conditions = self._analyze_strategy_conditions(symbol)
            
            condition_data = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'current_price': market_data.get('current_price', 0),
                'market_conditions': {
                    'trend_direction': trend_analysis.get('direction', 'unknown'),
                    'trend_strength': trend_analysis.get('strength', 0),
                    'ema_alignment': trend_analysis.get('ema_alignment', {}),
                    'crossover_signals': crossover_signals,
                    'volume_trend': market_data.get('volume_trend', 'normal'),
                    'volatility': market_data.get('volatility', 0)
                },
                'strategy_conditions': strategy_conditions
            }
            
            return condition_data
            
        except Exception as e:
            print(f"❌ 조건 분석 오류 ({symbol}): {e}")
            return None
    
    def _fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """시장 데이터 가져오기"""
        try:
            # OKX에서 캔들 데이터 가져오기
            candles_1h = self.data_fetcher.get_candles(symbol, '1H', limit=200)
            candles_4h = self.data_fetcher.get_candles(symbol, '4H', limit=50)
            
            if not candles_1h or not candles_4h:
                return {}
            
            # 현재 가격
            current_price = float(candles_1h[0][4])  # 종가
            
            # EMA 계산
            closes_1h = [float(candle[4]) for candle in candles_1h]
            closes_4h = [float(candle[4]) for candle in candles_4h]
            
            ema_20_1h = calculate_ema(closes_1h, 20)
            ema_50_1h = calculate_ema(closes_1h, 50)
            ema_150_4h = calculate_ema(closes_4h, 150) if len(closes_4h) >= 150 else None
            ema_200_4h = calculate_ema(closes_4h, 200) if len(closes_4h) >= 200 else None
            
            # 볼륨 분석
            volumes = [float(candle[5]) for candle in candles_1h[:24]]  # 최근 24시간
            avg_volume = sum(volumes) / len(volumes)
            current_volume = float(candles_1h[0][5])
            volume_trend = 'high' if current_volume > avg_volume * 1.5 else 'normal'
            
            # 변동성 계산 (ATR 기반)
            highs = [float(candle[2]) for candle in candles_1h[:14]]
            lows = [float(candle[3]) for candle in candles_1h[:14]]
            volatility = (max(highs) - min(lows)) / current_price * 100
            
            return {
                'current_price': current_price,
                'ema_20_1h': ema_20_1h[-1] if ema_20_1h else None,
                'ema_50_1h': ema_50_1h[-1] if ema_50_1h else None,
                'ema_150_4h': ema_150_4h[-1] if ema_150_4h else None,
                'ema_200_4h': ema_200_4h[-1] if ema_200_4h else None,
                'volume_trend': volume_trend,
                'volatility': volatility,
                'candles_1h': candles_1h,
                'candles_4h': candles_4h
            }
            
        except Exception as e:
            print(f"❌ 시장 데이터 가져오기 실패 ({symbol}): {e}")
            return {}
    
    def _analyze_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """트렌드 분석"""
        ema_150 = market_data.get('ema_150_4h')
        ema_200 = market_data.get('ema_200_4h')
        current_price = market_data.get('current_price', 0)
        
        if not ema_150 or not ema_200:
            return {
                'direction': 'unknown',
                'strength': 0,
                'ema_alignment': {}
            }
        
        # 트렌드 방향 결정
        if ema_150 > ema_200:
            if current_price > ema_150:
                direction = 'uptrend'
                strength = ((current_price - ema_200) / ema_200 * 100)
            else:
                direction = 'sideways'
                strength = ((ema_150 - ema_200) / ema_200 * 100)
        else:
            if current_price < ema_150:
                direction = 'downtrend'
                strength = -((ema_200 - current_price) / ema_200 * 100)
            else:
                direction = 'sideways'
                strength = -((ema_200 - ema_150) / ema_200 * 100)
        
        # EMA 정렬 상태
        ema_alignment = {
            '150_vs_200': 'above' if ema_150 > ema_200 else 'below',
            'price_vs_150': 'above' if current_price > ema_150 else 'below',
            'price_vs_200': 'above' if current_price > ema_200 else 'below'
        }
        
        return {
            'direction': direction,
            'strength': strength,
            'ema_alignment': ema_alignment
        }
    
    def _detect_crossovers(self, market_data: Dict[str, Any]) -> List[str]:
        """크로스오버 신호 감지"""
        signals = []
        
        ema_20 = market_data.get('ema_20_1h')
        ema_50 = market_data.get('ema_50_1h')
        
        if not ema_20 or not ema_50:
            return signals
        
        # 이전 데이터와 비교하여 크로스오버 감지
        symbol = list(market_data.keys())[0] if market_data else 'BTC-USDT-SWAP'
        last_data = self.last_market_data.get(symbol, {})
        
        last_ema_20 = last_data.get('ema_20_1h')
        last_ema_50 = last_data.get('ema_50_1h')
        
        if last_ema_20 and last_ema_50:
            # 골든 크로스 (20이 50을 위로 돌파)
            if last_ema_20 <= last_ema_50 and ema_20 > ema_50:
                signals.append('entry_golden_cross')
            
            # 데드 크로스 (20이 50을 아래로 돌파)
            elif last_ema_20 >= last_ema_50 and ema_20 < ema_50:
                signals.append('entry_dead_cross')
        
        # 현재 데이터 저장
        self.last_market_data[symbol] = market_data
        
        return signals
    
    def _analyze_strategy_conditions(self, symbol: str) -> Dict[str, Any]:
        """전략 조건 분석"""
        # 실제 전략 매니저와 연동되어야 함
        # 여기서는 더미 데이터 반환
        
        return {
            'long_strategy_main': {
                'is_real_mode': True,
                'can_enter': False,
                'current_capital': 1000.0,
                'position_size': 0.0,
                'mode_switch_progress': {'to_virtual': 25, 'to_real': 0},
                'last_signal_time': None,
                'performance_metrics': {'win_rate': 0.65, 'total_trades': 23}
            },
            'short_strategy_main': {
                'is_real_mode': False,
                'can_enter': True,
                'current_capital': 950.0,
                'position_size': 0.0,
                'mode_switch_progress': {'to_virtual': 0, 'to_real': 75},
                'last_signal_time': None,
                'performance_metrics': {'win_rate': 0.58, 'total_trades': 18}
            }
        }
    
    def _generate_dummy_condition_data(self, symbol: str) -> Dict[str, Any]:
        """더미 조건 데이터 생성 (테스트용)"""
        import random
        
        # 가격 시뮬레이션
        base_price = 65000 if 'BTC' in symbol else 3000
        price_change = random.uniform(-0.02, 0.02)
        current_price = base_price * (1 + price_change)
        
        # 트렌드 시뮬레이션
        trends = ['uptrend', 'downtrend', 'sideways']
        trend_direction = random.choice(trends)
        
        trend_strength = random.uniform(-2, 2)
        if trend_direction == 'uptrend':
            trend_strength = abs(trend_strength)
        elif trend_direction == 'downtrend':
            trend_strength = -abs(trend_strength)
        
        # 신호 시뮬레이션
        crossover_signals = []
        if random.random() < 0.1:  # 10% 확률로 신호 발생
            if trend_direction == 'uptrend':
                crossover_signals.append('entry_golden_cross')
            elif trend_direction == 'downtrend':
                crossover_signals.append('entry_dead_cross')
        
        return {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'current_price': current_price,
            'market_conditions': {
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'ema_alignment': {
                    '150_vs_200': 'above' if trend_direction == 'uptrend' else 'below',
                    'price_vs_150': 'above' if random.random() > 0.5 else 'below',
                    'price_vs_200': 'above' if trend_direction == 'uptrend' else 'below'
                },
                'crossover_signals': crossover_signals,
                'volume_trend': random.choice(['normal', 'high']),
                'volatility': random.uniform(0.5, 3.0)
            },
            'strategy_conditions': self._analyze_strategy_conditions(symbol)
        }
    
    def _check_signals(self, condition_data: Dict[str, Any]):
        """신호 감지 및 통계 업데이트"""
        crossovers = condition_data.get('market_conditions', {}).get('crossover_signals', [])
        
        for signal in crossovers:
            if 'golden_cross' in signal:
                self.counters['long_signals'] += 1
                self._trigger_callbacks('signal_detected', {
                    'type': 'long_entry',
                    'signal': signal,
                    'condition_data': condition_data
                })
            elif 'dead_cross' in signal:
                self.counters['short_signals'] += 1
                self._trigger_callbacks('signal_detected', {
                    'type': 'short_entry',
                    'signal': signal,
                    'condition_data': condition_data
                })
        
        # 트렌드 변화 감지
        current_trend = condition_data.get('market_conditions', {}).get('trend_direction')
        if self.last_trend_direction and self.last_trend_direction != current_trend:
            self.counters['trend_changes'] += 1
        
        self.last_trend_direction = current_trend
    
    def _trigger_callbacks(self, event_type: str, data: Any):
        """콜백 함수 실행"""
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                print(f"❌ 콜백 실행 오류 ({event_type}): {e}")
    
    def get_latest_condition(self, symbol: str = None) -> Optional[Dict[str, Any]]:
        """최신 조건 데이터 반환"""
        if not self.condition_history:
            return None
        
        if symbol:
            for condition in reversed(self.condition_history):
                if condition.get('symbol') == symbol:
                    return condition
            return None
        
        return self.condition_history[-1]
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            'counters': self.counters.copy(),
            'history_count': len(self.condition_history),
            'is_running': self.is_running,
            'last_update': self.condition_history[-1]['timestamp'] if self.condition_history else None
        }


# 전역 모니터 인스턴스
condition_monitor = ConditionMonitor()

# 자동 시작 함수
def start_condition_monitoring():
    """조건 모니터링 자동 시작"""
    if not condition_monitor.is_running:
        condition_monitor.start_monitoring()

def stop_condition_monitoring():
    """조건 모니터링 중지"""
    condition_monitor.stop_monitoring()

# 모듈 로드 시 정보 출력
print("📡 실시간 조건 모니터링 모듈 로드 완료")
print("   - condition_monitor: 전역 모니터 인스턴스")
print("   - start_condition_monitoring(): 모니터링 시작")
print("   - stop_condition_monitoring(): 모니터링 중지")