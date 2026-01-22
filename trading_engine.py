# trading_engine.py
"""
멀티 타임프레임 자동매매 엔진
- 30분봉: 트렌드 판단 (2주 데이터, 150/200 EMA)
- 1분봉: 진입 타이밍 (실시간, 20/50 EMA)
"""

import time
import threading
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import deque

from config import make_api_request


class PriceBuffer:
    """가격 데이터 버퍼"""
    
    def __init__(self, maxlen: int = 300):
        self.candles = deque(maxlen=maxlen)
        self.last_timestamp = None
    
    def add_candle(self, candle: Dict):
        """캔들 추가"""
        self.candles.append(candle)
        self.last_timestamp = candle.get('timestamp')
    
    def update_last(self, close: float, high: float, low: float):
        """마지막 캔들 업데이트"""
        if len(self.candles) > 0:
            self.candles[-1]['close'] = close
            self.candles[-1]['high'] = max(self.candles[-1]['high'], high)
            self.candles[-1]['low'] = min(self.candles[-1]['low'], low)
    
    def to_dataframe(self) -> Optional[pd.DataFrame]:
        """DataFrame으로 변환"""
        if len(self.candles) < 10:
            return None
        return pd.DataFrame(list(self.candles))
    
    def __len__(self):
        return len(self.candles)


class MultiTimeframeStrategy:
    """멀티 타임프레임 전략"""
    
    def __init__(self, symbol: str, strategy_type: str, config: Dict):
        self.symbol = symbol
        self.strategy_type = strategy_type  # 'long' or 'short'
        self.config = config
        
        # 전략 설정
        self.leverage = config.get('leverage', 1)
        self.trailing_stop_pct = config.get('trailing_stop', 0.10)
        self.position_size_pct = config.get('position_size', 0.1)
        
        # 30분봉 EMA (트렌드)
        self.ema_trend_fast = 150   # 75시간 ≈ 3일
        self.ema_trend_slow = 200   # 100시간 ≈ 4일
        
        # 1분봉 EMA (진입/청산)
        self.ema_entry_fast = 20    # 20분
        self.ema_entry_slow = 50    # 50분
        self.ema_exit_slow = 100    # 100분
        
        # 상태
        self.is_position_open = False
        self.entry_price = 0
        self.entry_time = None
        self.position_size = 0
        self.highest_price = 0
        self.lowest_price = float('inf')
        
        # 모드 관리
        self.is_real_mode = True
        self.real_capital = config.get('initial_capital', 1000)
        self.virtual_capital = config.get('initial_capital', 1000)
        
        # 손익 추적
        self.peak_capital = self.real_capital
        self.trough_capital = self.real_capital
        self.drawdown_threshold = config.get('drawdown_threshold', 0.20)
        self.recovery_threshold = config.get('recovery_threshold', 0.30)
        
        # 통계
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0
        
        # EMA 캐시
        self.last_ema_30m = {}
        self.last_ema_1m = {}
        self.prev_ema_1m = {}  # 크로스 감지용
        self.last_price = 0
    
    def calculate_ema(self, df: pd.DataFrame, period: int) -> tuple:
        """EMA 계산 (현재값, 이전값)"""
        if len(df) < period:
            return None, None
        ema = df['close'].ewm(span=period, adjust=False).mean()
        return ema.iloc[-1], ema.iloc[-2] if len(ema) > 1 else ema.iloc[-1]
    
    def update_30m_emas(self, df_30m: pd.DataFrame):
        """30분봉 EMA 업데이트"""
        if df_30m is None or len(df_30m) < self.ema_trend_slow:
            return False
        
        ema150, prev150 = self.calculate_ema(df_30m, self.ema_trend_fast)
        ema200, prev200 = self.calculate_ema(df_30m, self.ema_trend_slow)
        ema100, prev100 = self.calculate_ema(df_30m, 100)  # 숏 청산용
        
        if ema150 and ema200:
            self.last_ema_30m = {
                'ema_150': ema150,
                'ema_200': ema200,
                'ema_100': ema100,
                'prev_ema_150': prev150,
                'prev_ema_200': prev200,
                'prev_ema_100': prev100,
            }
            return True
        return False
    
    def update_1m_emas(self, df_1m: pd.DataFrame):
        """1분봉 EMA 업데이트"""
        if df_1m is None or len(df_1m) < self.ema_exit_slow:
            return False
        
        # 이전 값 저장 (크로스 감지용)
        self.prev_ema_1m = self.last_ema_1m.copy()
        
        ema20, _ = self.calculate_ema(df_1m, self.ema_entry_fast)
        ema50, _ = self.calculate_ema(df_1m, self.ema_entry_slow)
        ema100, _ = self.calculate_ema(df_1m, self.ema_exit_slow)
        
        if ema20 and ema50:
            self.last_ema_1m = {
                'ema_20': ema20,
                'ema_50': ema50,
                'ema_100': ema100,
            }
            return True
        return False
    
    def check_trend(self) -> tuple:
        """
        30분봉 트렌드 확인
        Returns: (is_valid, description)
        """
        ema150 = self.last_ema_30m.get('ema_150')
        ema200 = self.last_ema_30m.get('ema_200')
        
        if not ema150 or not ema200:
            return False, "EMA 데이터 없음"
        
        diff_pct = ((ema150 - ema200) / ema200) * 100
        
        if self.strategy_type == 'long':
            if ema150 > ema200:
                return True, f"[OK] 상승장 (150>200, +{diff_pct:.2f}%)"
            else:
                return False, f"[대기] 하락장 (150<200, {diff_pct:.2f}%)"
        else:  # short
            if ema150 < ema200:
                return True, f"[OK] 하락장 (150<200, {diff_pct:.2f}%)"
            else:
                return False, f"[대기] 상승장 (150>200, +{diff_pct:.2f}%)"
    
    def check_entry_signal(self) -> tuple:
        """
        1분봉 진입 신호 확인
        Returns: (is_signal, description)
        """
        curr_20 = self.last_ema_1m.get('ema_20')
        curr_50 = self.last_ema_1m.get('ema_50')
        prev_20 = self.prev_ema_1m.get('ema_20')
        prev_50 = self.prev_ema_1m.get('ema_50')
        
        if not all([curr_20, curr_50, prev_20, prev_50]):
            return False, "EMA 데이터 없음"
        
        diff_pct = ((curr_20 - curr_50) / curr_50) * 100
        
        if self.strategy_type == 'long':
            # 골든크로스: 20이 50 아래에서 위로
            was_below = prev_20 <= prev_50
            is_above = curr_20 > curr_50
            
            if was_below and is_above:
                return True, f"[신호] 골든크로스! ({diff_pct:+.2f}%)"
            elif diff_pct < 0:
                return False, f"[대기] 상승중 ({diff_pct:.2f}%)"
            else:
                return False, f"[이미위] ({diff_pct:+.2f}%)"
        else:  # short
            # 데드크로스: 20이 50 위에서 아래로
            was_above = prev_20 >= prev_50
            is_below = curr_20 < curr_50
            
            if was_above and is_below:
                return True, f"[신호] 데드크로스! ({diff_pct:.2f}%)"
            elif diff_pct > 0:
                return False, f"[대기] 하락중 ({diff_pct:+.2f}%)"
            else:
                return False, f"[이미아래] ({diff_pct:.2f}%)"
    
    def check_exit_signal(self, current_price: float) -> tuple:
        """
        청산 신호 확인
        Returns: (should_exit, reason)
        """
        if not self.is_position_open:
            return False, ""
        
        # 1. 트레일링스탑 체크
        if self.strategy_type == 'long':
            self.highest_price = max(self.highest_price, current_price)
            drop_pct = (self.highest_price - current_price) / self.highest_price
            if drop_pct >= self.trailing_stop_pct:
                return True, f"트레일링스탑 ({drop_pct*100:.1f}% 하락)"
        else:  # short
            self.lowest_price = min(self.lowest_price, current_price)
            rise_pct = (current_price - self.lowest_price) / self.lowest_price
            if rise_pct >= self.trailing_stop_pct:
                return True, f"트레일링스탑 ({rise_pct*100:.1f}% 상승)"
        
        # 2. EMA 기반 청산
        if self.strategy_type == 'long':
            # 1분봉 20/100 데드크로스
            ema20 = self.last_ema_1m.get('ema_20')
            ema100 = self.last_ema_1m.get('ema_100')
            prev_20 = self.prev_ema_1m.get('ema_20')
            prev_100 = self.prev_ema_1m.get('ema_100')
            
            if all([ema20, ema100, prev_20, prev_100]):
                was_above = prev_20 >= prev_100
                is_below = ema20 < ema100
                if was_above and is_below:
                    return True, "1분봉 20/100 데드크로스"
        else:  # short
            # 30분봉 100/200 골든크로스
            ema100 = self.last_ema_30m.get('ema_100')
            ema200 = self.last_ema_30m.get('ema_200')
            prev_100 = self.last_ema_30m.get('prev_ema_100')
            prev_200 = self.last_ema_30m.get('prev_ema_200')
            
            if all([ema100, ema200, prev_100, prev_200]):
                was_below = prev_100 <= prev_200
                is_above = ema100 > ema200
                if was_below and is_above:
                    return True, "30분봉 100/200 골든크로스"
        
        return False, ""
    
    def calculate_proximity(self) -> Dict:
        """근접도 계산 (멀티 타임프레임)"""
        result = {
            'trend_proximity': 0,
            'entry_proximity': 0,
            'overall_proximity': 0,
            'trend_status': '',
            'entry_status': '',
        }
        
        # 1. 30분봉 트렌드 근접도
        ema150 = self.last_ema_30m.get('ema_150')
        ema200 = self.last_ema_30m.get('ema_200')
        
        if ema150 and ema200:
            diff_pct = ((ema150 - ema200) / ema200) * 100
            
            if self.strategy_type == 'long':
                if diff_pct > 0:
                    result['trend_proximity'] = 100
                    result['trend_status'] = f"[OK] 상승장 ({diff_pct:+.2f}%)"
                else:
                    result['trend_proximity'] = max(0, 100 + diff_pct * 10)
                    result['trend_status'] = f"[대기] ({diff_pct:.2f}%)"
            else:
                if diff_pct < 0:
                    result['trend_proximity'] = 100
                    result['trend_status'] = f"[OK] 하락장 ({diff_pct:.2f}%)"
                else:
                    result['trend_proximity'] = max(0, 100 - diff_pct * 10)
                    result['trend_status'] = f"[대기] ({diff_pct:+.2f}%)"
        
        # 2. 1분봉 진입 근접도
        ema20 = self.last_ema_1m.get('ema_20')
        ema50 = self.last_ema_1m.get('ema_50')
        prev_20 = self.prev_ema_1m.get('ema_20')
        prev_50 = self.prev_ema_1m.get('ema_50')
        
        if ema20 and ema50:
            entry_diff = ((ema20 - ema50) / ema50) * 100
            
            if self.strategy_type == 'long':
                if prev_20 and prev_50:
                    was_below = prev_20 <= prev_50
                    is_above = ema20 > ema50
                    
                    if was_below and is_above:
                        result['entry_proximity'] = 100
                        result['entry_status'] = "[신호] 골든크로스!"
                    elif entry_diff < 0:
                        result['entry_proximity'] = max(0, 100 + entry_diff * 20)
                        result['entry_status'] = f"[대기] 상승중 ({entry_diff:.2f}%)"
                    else:
                        result['entry_proximity'] = 50
                        result['entry_status'] = f"[이미위] ({entry_diff:+.2f}%)"
            else:
                if prev_20 and prev_50:
                    was_above = prev_20 >= prev_50
                    is_below = ema20 < ema50
                    
                    if was_above and is_below:
                        result['entry_proximity'] = 100
                        result['entry_status'] = "[신호] 데드크로스!"
                    elif entry_diff > 0:
                        result['entry_proximity'] = max(0, 100 - entry_diff * 20)
                        result['entry_status'] = f"[대기] 하락중 ({entry_diff:+.2f}%)"
                    else:
                        result['entry_proximity'] = 50
                        result['entry_status'] = f"[이미아래] ({entry_diff:.2f}%)"
        
        # 3. 전체 근접도 (트렌드 40% + 진입 60%)
        result['overall_proximity'] = (
            result['trend_proximity'] * 0.4 +
            result['entry_proximity'] * 0.6
        )
        
        return result
    
    def should_enter(self) -> bool:
        """진입 가능 여부"""
        if self.is_position_open:
            return False
        
        trend_ok, _ = self.check_trend()
        if not trend_ok:
            return False
        
        entry_ok, _ = self.check_entry_signal()
        if not entry_ok:
            return False
        
        return True
    
    def enter_position(self, current_price: float, capital: float) -> Dict:
        """포지션 진입"""
        self.is_position_open = True
        self.entry_price = current_price
        self.entry_time = datetime.now()
        self.position_size = (capital * self.position_size_pct * self.leverage) / current_price
        self.highest_price = current_price
        self.lowest_price = current_price
        
        return {
            'action': 'enter',
            'strategy_type': self.strategy_type,
            'symbol': self.symbol,
            'side': 'buy' if self.strategy_type == 'long' else 'sell',
            'price': current_price,
            'size': self.position_size,
            'leverage': self.leverage,
            'is_real': self.is_real_mode
        }
    
    def exit_position(self, current_price: float, reason: str) -> Dict:
        """포지션 청산"""
        if self.strategy_type == 'long':
            pnl_pct = (current_price - self.entry_price) / self.entry_price * self.leverage
        else:
            pnl_pct = (self.entry_price - current_price) / self.entry_price * self.leverage
        
        pnl = self.position_size * self.entry_price * pnl_pct / self.leverage
        
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        self.total_pnl += pnl
        
        if self.is_real_mode:
            self.real_capital += pnl
            self.peak_capital = max(self.peak_capital, self.real_capital)
        else:
            self.virtual_capital += pnl
        
        result = {
            'action': 'exit',
            'strategy_type': self.strategy_type,
            'symbol': self.symbol,
            'side': 'sell' if self.strategy_type == 'long' else 'buy',
            'entry_price': self.entry_price,
            'exit_price': current_price,
            'size': self.position_size,
            'pnl': pnl,
            'pnl_pct': pnl_pct * 100,
            'reason': reason,
            'is_real': self.is_real_mode
        }
        
        self.is_position_open = False
        self.entry_price = 0
        self.position_size = 0
        
        return result
    
    def check_mode_switch(self) -> bool:
        """모드 전환 체크"""
        mode_changed = False
        
        if self.is_real_mode:
            if self.real_capital < self.peak_capital * (1 - self.drawdown_threshold):
                self.is_real_mode = False
                self.trough_capital = self.virtual_capital
                mode_changed = True
                print(f"[!] [{self.symbol}] {self.strategy_type}: 가상 모드 전환")
        else:
            if self.virtual_capital > self.trough_capital * (1 + self.recovery_threshold):
                self.is_real_mode = True
                self.peak_capital = self.real_capital
                mode_changed = True
                print(f"[OK] [{self.symbol}] {self.strategy_type}: 실제 모드 전환")
        
        return mode_changed
    
    def get_status(self) -> Dict:
        """전략 상태 조회"""
        proximity = {}
        if not self.is_position_open:
            proximity = self.calculate_proximity()
        
        return {
            'symbol': self.symbol,
            'type': self.strategy_type,
            'is_real_mode': self.is_real_mode,
            'is_position_open': self.is_position_open,
            'entry_price': self.entry_price,
            'real_capital': self.real_capital,
            'virtual_capital': self.virtual_capital,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'total_pnl': self.total_pnl,
            'leverage': self.leverage,
            'proximity': proximity,
            'ema_30m': self.last_ema_30m,
            'ema_1m': self.last_ema_1m,
        }


class MultiTimeframeTradingEngine:
    """멀티 타임프레임 자동매매 엔진"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        self.symbols = self.config.get('symbols', ['BTC-USDT-SWAP'])
        self.initial_capital = self.config.get('initial_capital', 1000)
        self.check_interval = self.config.get('check_interval', 60)
        
        self.is_running = False
        self.engine_thread = None
        
        # 멀티 타임프레임 버퍼
        self.buffers_30m: Dict[str, PriceBuffer] = {}  # 30분봉 (2주)
        self.buffers_1m: Dict[str, PriceBuffer] = {}   # 1분봉 (실시간)
        
        # 전략
        self.strategies: Dict[str, MultiTimeframeStrategy] = {}
        
        # OrderManager
        self.order_manager = None
        
        # 콜백
        self.on_signal_callback: Optional[Callable] = None
        self.on_trade_callback: Optional[Callable] = None
        
        # 통계
        self.start_time = None
        self.total_signals = 0
        self.executed_trades = 0
        self.cycle_count = 0
        
        # 30분봉 마지막 업데이트 시간
        self.last_30m_update = None
        
        print("[*] 멀티 타임프레임 엔진 초기화", flush=True)
    
    def initialize(self):
        """엔진 초기화"""
        import sys
        
        print("=" * 60, flush=True)
        print("[*] 멀티 타임프레임 엔진 초기화 중...", flush=True)
        print("=" * 60, flush=True)
        
        # OrderManager 초기화
        try:
            from okx.order_manager import OrderManager
            self.order_manager = OrderManager()
            print("[OK] OrderManager 연결 완료", flush=True)
        except Exception as e:
            print(f"[!] OrderManager 연결 실패: {e}", flush=True)
            self.order_manager = None
        
        # 실제 잔고 로드
        try:
            if self.order_manager:
                balance_info = self.order_manager.get_account_balance('USDT')
                if balance_info and balance_info.get('available', 0) > 0:
                    self.initial_capital = balance_info['available']
                    print(f"[OK] 실제 OKX 잔고: ${self.initial_capital:.2f} USDT", flush=True)
        except Exception as e:
            print(f"[!] 잔고 조회 실패: {e}", flush=True)
        
        # 심볼별 초기화
        for symbol in self.symbols:
            # 버퍼 생성
            self.buffers_30m[symbol] = PriceBuffer(maxlen=700)  # 2주 + 여유
            self.buffers_1m[symbol] = PriceBuffer(maxlen=300)
            print(f"[OK] 버퍼 생성: {symbol}", flush=True)
            
            # 롱 전략
            long_config = {
                'initial_capital': self.initial_capital / 2,
                'leverage': self.config.get('long_leverage', 10),
                'trailing_stop': self.config.get('long_trailing_stop', 0.10),
                'position_size': self.config.get('position_size', 0.1),
            }
            self.strategies[f'long_{symbol}'] = MultiTimeframeStrategy(symbol, 'long', long_config)
            print(f"[OK] 롱 전략 생성 (레버리지: {long_config['leverage']}x)", flush=True)
            
            # 숏 전략
            short_config = {
                'initial_capital': self.initial_capital / 2,
                'leverage': self.config.get('short_leverage', 3),
                'trailing_stop': self.config.get('short_trailing_stop', 0.02),
                'position_size': self.config.get('position_size', 0.1),
            }
            self.strategies[f'short_{symbol}'] = MultiTimeframeStrategy(symbol, 'short', short_config)
            print(f"[OK] 숏 전략 생성 (레버리지: {short_config['leverage']}x)", flush=True)
            
            # 과거 데이터 로드
            print(f"\n[*] {symbol} 과거 데이터 로드 중...", flush=True)
            self._load_historical_30m(symbol)
            self._load_historical_1m(symbol)
        
        print("=" * 60, flush=True)
        print("[OK] 멀티 타임프레임 엔진 초기화 완료!", flush=True)
        print(f"[*] 거래 심볼: {', '.join(self.symbols)}", flush=True)
        print(f"[*] 초기 자본: ${self.initial_capital:.2f}", flush=True)
        print(f"[*] 체크 간격: {self.check_interval}초", flush=True)
        print(f"[*] 30분봉: {len(self.buffers_30m[self.symbols[0]])}개 (트렌드)", flush=True)
        print(f"[*] 1분봉: {len(self.buffers_1m[self.symbols[0]])}개 (진입)", flush=True)
        print("=" * 60, flush=True)
        
        sys.stdout.flush()
        return True
    
    def _load_historical_30m(self, symbol: str):
        """30분봉 2주 데이터 로드"""
        try:
            # OKX는 한 번에 최대 300개까지 조회 가능
            # 2주 = 672개이므로 3번 나눠서 조회
            all_candles = []
            
            for i in range(3):
                params = {
                    'instId': symbol,
                    'bar': '30m',
                    'limit': '300'
                }
                
                # 이전 조회의 가장 오래된 타임스탬프 이전 데이터 조회
                if all_candles:
                    params['after'] = str(int(all_candles[-1]['timestamp'].timestamp() * 1000))
                
                response = make_api_request('GET', '/api/v5/market/candles', params=params)
                
                if response and response.get('code') == '0':
                    candles_raw = response.get('data', [])
                    
                    for candle_raw in candles_raw:
                        candle = {
                            'timestamp': pd.to_datetime(int(candle_raw[0]), unit='ms'),
                            'open': float(candle_raw[1]),
                            'high': float(candle_raw[2]),
                            'low': float(candle_raw[3]),
                            'close': float(candle_raw[4]),
                            'volume': float(candle_raw[5])
                        }
                        all_candles.append(candle)
                    
                    print(f"    30분봉 배치 {i+1}: {len(candles_raw)}개 로드", flush=True)
                    
                    if len(candles_raw) < 300:
                        break
                else:
                    break
                
                time.sleep(0.2)  # API 레이트 리밋 방지
            
            # 시간순 정렬 후 버퍼에 추가
            all_candles.sort(key=lambda x: x['timestamp'])
            for candle in all_candles:
                self.buffers_30m[symbol].add_candle(candle)
            
            print(f"[OK] 30분봉 총 {len(self.buffers_30m[symbol])}개 로드 완료", flush=True)
            
        except Exception as e:
            print(f"[X] 30분봉 로드 오류: {e}", flush=True)
    
    def _load_historical_1m(self, symbol: str):
        """1분봉 200개 로드"""
        try:
            response = make_api_request(
                'GET',
                '/api/v5/market/candles',
                params={
                    'instId': symbol,
                    'bar': '1m',
                    'limit': '200'
                }
            )
            
            if response and response.get('code') == '0':
                candles_raw = response.get('data', [])
                candles_raw.reverse()  # 시간순 정렬
                
                for candle_raw in candles_raw:
                    candle = {
                        'timestamp': pd.to_datetime(int(candle_raw[0]), unit='ms'),
                        'open': float(candle_raw[1]),
                        'high': float(candle_raw[2]),
                        'low': float(candle_raw[3]),
                        'close': float(candle_raw[4]),
                        'volume': float(candle_raw[5])
                    }
                    self.buffers_1m[symbol].add_candle(candle)
                
                print(f"[OK] 1분봉 {len(self.buffers_1m[symbol])}개 로드 완료", flush=True)
            
        except Exception as e:
            print(f"[X] 1분봉 로드 오류: {e}", flush=True)
    
    def _fetch_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        try:
            response = make_api_request(
                'GET',
                '/api/v5/market/ticker',
                params={'instId': symbol}
            )
            
            if response and response.get('code') == '0':
                return float(response['data'][0]['last'])
        except Exception as e:
            print(f"[X] 가격 조회 오류: {e}", flush=True)
        return None
    
    def _fetch_latest_candle(self, symbol: str, bar: str) -> Optional[Dict]:
        """최신 캔들 조회"""
        try:
            response = make_api_request(
                'GET',
                '/api/v5/market/candles',
                params={
                    'instId': symbol,
                    'bar': bar,
                    'limit': '1'
                }
            )
            
            if response and response.get('code') == '0':
                candle_raw = response['data'][0]
                return {
                    'timestamp': pd.to_datetime(int(candle_raw[0]), unit='ms'),
                    'open': float(candle_raw[1]),
                    'high': float(candle_raw[2]),
                    'low': float(candle_raw[3]),
                    'close': float(candle_raw[4]),
                    'volume': float(candle_raw[5]),
                    'confirm': candle_raw[8] if len(candle_raw) > 8 else '0'
                }
        except Exception as e:
            print(f"[X] 캔들 조회 오류 ({bar}): {e}", flush=True)
        return None
    
    def _update_buffers(self, symbol: str, current_price: float):
        """버퍼 업데이트"""
        # 1분봉 업데이트
        latest_1m = self._fetch_latest_candle(symbol, '1m')
        if latest_1m:
            buffer = self.buffers_1m[symbol]
            is_new = buffer.last_timestamp is None or latest_1m['timestamp'] > buffer.last_timestamp
            is_confirmed = latest_1m.get('confirm') == '1'
            
            if is_new and is_confirmed:
                buffer.add_candle(latest_1m)
                print(f"[+] 1분봉 추가: ${latest_1m['close']:,.2f}", flush=True)
            elif len(buffer) > 0:
                buffer.update_last(latest_1m['close'], latest_1m['high'], latest_1m['low'])
        
        # 30분봉 업데이트 (30분마다)
        now = datetime.now()
        if self.last_30m_update is None or (now - self.last_30m_update).seconds >= 1800:
            latest_30m = self._fetch_latest_candle(symbol, '30m')
            if latest_30m:
                buffer = self.buffers_30m[symbol]
                is_new = buffer.last_timestamp is None or latest_30m['timestamp'] > buffer.last_timestamp
                is_confirmed = latest_30m.get('confirm') == '1'
                
                if is_new and is_confirmed:
                    buffer.add_candle(latest_30m)
                    print(f"[+] 30분봉 추가: ${latest_30m['close']:,.2f}", flush=True)
                    self.last_30m_update = now
                elif len(buffer) > 0:
                    buffer.update_last(latest_30m['close'], latest_30m['high'], latest_30m['low'])
    
    def _process_strategies(self):
        """전략 처리"""
        for symbol in self.symbols:
            # 현재가 조회
            current_price = self._fetch_current_price(symbol)
            if not current_price:
                continue
            
            # 버퍼 업데이트
            self._update_buffers(symbol, current_price)
            
            # DataFrame 생성
            df_30m = self.buffers_30m[symbol].to_dataframe()
            df_1m = self.buffers_1m[symbol].to_dataframe()
            
            if df_30m is None or len(df_30m) < 200:
                print(f"[대기] 30분봉 데이터 부족 ({len(self.buffers_30m[symbol])}/200)")
                continue
            
            if df_1m is None or len(df_1m) < 100:
                print(f"[대기] 1분봉 데이터 부족 ({len(self.buffers_1m[symbol])}/100)")
                continue
            
            # 각 전략 처리
            for strategy_key in [f'long_{symbol}', f'short_{symbol}']:
                strategy = self.strategies.get(strategy_key)
                if not strategy:
                    continue
                
                try:
                    # EMA 업데이트
                    strategy.update_30m_emas(df_30m)
                    strategy.update_1m_emas(df_1m)
                    strategy.last_price = current_price
                    
                    # 모드 체크
                    strategy.check_mode_switch()
                    
                    # 청산 체크
                    should_exit, exit_reason = strategy.check_exit_signal(current_price)
                    if should_exit:
                        signal = strategy.exit_position(current_price, exit_reason)
                        self.total_signals += 1
                        self._execute_trade(signal)
                        continue
                    
                    # 진입 체크
                    if strategy.should_enter():
                        capital = strategy.real_capital if strategy.is_real_mode else strategy.virtual_capital
                        signal = strategy.enter_position(current_price, capital)
                        self.total_signals += 1
                        self._execute_trade(signal)
                
                except Exception as e:
                    print(f"[X] 전략 처리 오류 ({strategy_key}): {e}", flush=True)
    
    def _execute_trade(self, signal: Dict) -> bool:
        """거래 실행"""
        if not self.order_manager:
            print("[X] OrderManager가 없습니다")
            return False
        
        action = signal.get('action')
        is_real = signal.get('is_real', False)
        strategy_type = signal.get('strategy_type')
        symbol = signal.get('symbol')
        
        if not is_real:
            print(f"[*] [가상] {strategy_type} {action}: {symbol}")
            return True
        
        try:
            if action == 'enter':
                side = signal.get('side')
                leverage = signal.get('leverage', 1)
                
                balance_info = self.order_manager.get_account_balance('USDT')
                balance = balance_info.get('available', 0) if balance_info else 0
                
                if balance < 10:
                    print("[X] 잔액 부족")
                    return False
                
                order_amount = min(balance * 0.1, 100)
                
                print(f"[*] [실제] {strategy_type} 진입: {symbol}")
                print(f"    방향: {side}, 레버리지: {leverage}x, 금액: ${order_amount:.2f}")
                
                if side == 'buy':
                    result = self.order_manager.buy_usdt(symbol, order_amount, leverage)
                else:
                    result = self.order_manager.sell_usdt(symbol, order_amount, leverage)
                
                if result:
                    print(f"[OK] 주문 성공!")
                    self.executed_trades += 1
                    return True
                
            elif action == 'exit':
                print(f"[*] [실제] {strategy_type} 청산: {symbol}")
                print(f"    사유: {signal.get('reason')}")
                print(f"    손익: ${signal.get('pnl', 0):.2f}")
                
                result = self.order_manager.close_position(symbol)
                if result:
                    print("[OK] 청산 성공!")
                    self.executed_trades += 1
                    return True
        
        except Exception as e:
            print(f"[X] 거래 실행 오류: {e}")
        
        return False
    
    def _print_status(self):
        """상태 출력"""
        import sys
        
        runtime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        runtime_str = str(runtime).split('.')[0]
        
        current_prices = {}
        for symbol in self.symbols:
            price = self._fetch_current_price(symbol)
            if price:
                current_prices[symbol] = price
        
        print("\n" + "=" * 75, flush=True)
        print(f"[상태] 멀티타임프레임 자동매매 - {datetime.now().strftime('%H:%M:%S')}", flush=True)
        print("=" * 75, flush=True)
        print(f"  실행: {runtime_str} | 사이클: {self.cycle_count}", flush=True)
        print(f"  신호: {self.total_signals}개 | 거래: {self.executed_trades}개", flush=True)
        
        for symbol, price in current_prices.items():
            print(f"  {symbol}: ${price:,.2f}", flush=True)
        
        print("-" * 75, flush=True)
        
        for key, strategy in self.strategies.items():
            status = strategy.get_status()
            mode = "[실제]" if status['is_real_mode'] else "[가상]"
            pos = "[보유]" if status['is_position_open'] else "[대기]"
            name = "LONG " if "long" in key else "SHORT"
            
            print(f"  {name}: {mode} {pos} | 자본: ${status['real_capital']:.2f} | 손익: ${status['total_pnl']:+.2f}", flush=True)
            
            if not status['is_position_open']:
                proximity = status.get('proximity', {})
                ema_30m = status.get('ema_30m', {})
                ema_1m = status.get('ema_1m', {})
                
                if proximity:
                    overall = proximity.get('overall_proximity', 0)
                    trend_status = proximity.get('trend_status', '')
                    entry_status = proximity.get('entry_status', '')
                    
                    bar_len = 20
                    filled = int(overall / 100 * bar_len)
                    bar = '#' * filled + '-' * (bar_len - filled)
                    
                    print(f"        진입 근접도: [{bar}] {overall:.1f}%", flush=True)
                    print(f"        [30분봉] 트렌드: {trend_status}", flush=True)
                    print(f"        [1분봉]  진입: {entry_status}", flush=True)
                
                # EMA 디버그
                if ema_30m and ema_1m:
                    ema150 = ema_30m.get('ema_150', 0)
                    ema200 = ema_30m.get('ema_200', 0)
                    ema20 = ema_1m.get('ema_20', 0)
                    ema50 = ema_1m.get('ema_50', 0)
                    
                    if ema150 and ema200:
                        diff_30m = ((ema150 - ema200) / ema200) * 100
                        diff_1m = ((ema20 - ema50) / ema50) * 100 if ema50 else 0
                        print(f"        [DEBUG] 30분봉 EMA150: ${ema150:,.0f} | EMA200: ${ema200:,.0f} | diff: {diff_30m:+.3f}%", flush=True)
                        print(f"        [DEBUG] 1분봉  EMA20: ${ema20:,.0f} | EMA50: ${ema50:,.0f} | diff: {diff_1m:+.3f}%", flush=True)
        
        print("=" * 75, flush=True)
        sys.stdout.flush()
    
    def _engine_loop(self):
        """엔진 메인 루프"""
        import sys
        
        print("\n" + "=" * 60, flush=True)
        print("[*] 멀티 타임프레임 엔진 루프 시작!", flush=True)
        print("=" * 60, flush=True)
        
        self.start_time = datetime.now()
        self.cycle_count = 0
        
        last_status_time = 0
        status_interval = 60
        
        self._print_status()
        
        while self.is_running:
            try:
                current_time = time.time()
                self.cycle_count += 1
                
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 사이클 #{self.cycle_count}", flush=True)
                
                self._process_strategies()
                
                print(f"[OK] 사이클 #{self.cycle_count} 완료", flush=True)
                
                if current_time - last_status_time >= status_interval:
                    self._print_status()
                    last_status_time = current_time
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"[X] 엔진 루프 오류: {e}", flush=True)
                import traceback
                traceback.print_exc()
                time.sleep(10)
        
        print("[!] 엔진 중지됨", flush=True)
    
    def start(self):
        """엔진 시작"""
        if self.is_running:
            print("[!] 이미 실행 중")
            return False
        
        if not self.initialize():
            return False
        
        self.is_running = True
        self.engine_thread = threading.Thread(target=self._engine_loop, daemon=True)
        self.engine_thread.start()
        
        return True
    
    def stop(self):
        """엔진 중지"""
        if not self.is_running:
            return
        
        print("[*] 엔진 중지 중...")
        self.is_running = False
        
        if self.engine_thread:
            self.engine_thread.join(timeout=10)
        
        self._print_status()
        print("[OK] 엔진 중지 완료")
    
    def get_status(self) -> Dict:
        """엔진 상태 조회"""
        return {
            'is_running': self.is_running,
            'start_time': self.start_time,
            'cycle_count': self.cycle_count,
            'total_signals': self.total_signals,
            'executed_trades': self.executed_trades,
            'strategies': {k: v.get_status() for k, v in self.strategies.items()}
        }


# 기존 호환성을 위한 alias
TradingEngine = MultiTimeframeTradingEngine
TradingStrategy = MultiTimeframeStrategy


def run_trading_engine():
    """자동매매 엔진 실행"""
    print("=" * 60)
    print("[*] OKX 멀티 타임프레임 자동매매 엔진")
    print("=" * 60)
    
    config = {
        'symbols': ['BTC-USDT-SWAP'],
        'initial_capital': 1000,
        'check_interval': 60,
        'long_leverage': 10,
        'long_trailing_stop': 0.10,
        'short_leverage': 3,
        'short_trailing_stop': 0.02,
        'position_size': 0.1,
    }
    
    engine = MultiTimeframeTradingEngine(config)
    
    print("\n[!] 이 프로그램은 실제 자금으로 거래합니다!")
    confirm = input("시작하시겠습니까? (yes): ").strip().lower()
    
    if confirm != 'yes':
        print("취소됨")
        return
    
    engine.start()
    
    print("\n[*] 실행 중... (Ctrl+C로 중지)")
    
    try:
        while engine.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] 중지 요청...")
    finally:
        engine.stop()


if __name__ == "__main__":
    run_trading_engine()