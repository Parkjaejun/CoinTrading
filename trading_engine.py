# trading_engine.py
"""
자동매매 엔진
- 실시간 데이터 수신 (WebSocket)
- EMA 계산 및 전략 신호 생성
- 실제 주문 실행 (OrderManager)
- 포지션 관리 (트레일링스탑)
"""

import time
import threading
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import deque

# 프로젝트 모듈
from config import make_api_request


class PriceBuffer:
    """가격 데이터 버퍼 (EMA 계산용)"""
    
    def __init__(self, maxlen: int = 300):
        self.candles = deque(maxlen=maxlen)
    
    def add_candle(self, candle: Dict):
        """캔들 추가"""
        self.candles.append(candle)
    
    def to_dataframe(self) -> Optional[pd.DataFrame]:
        """DataFrame으로 변환"""
        if len(self.candles) < 10:
            return None
        return pd.DataFrame(list(self.candles))
    
    def __len__(self):
        return len(self.candles)


class TradingStrategy:
    """EMA 기반 트레이딩 전략"""
    
    def __init__(self, symbol: str, strategy_type: str, config: Dict):
        """
        Args:
            symbol: 거래 상품 (예: 'BTC-USDT-SWAP')
            strategy_type: 'long' 또는 'short'
            config: 전략 설정
        """
        self.symbol = symbol
        self.strategy_type = strategy_type
        self.config = config
        
        # 전략 설정
        self.leverage = config.get('leverage', 1)
        self.trailing_stop_pct = config.get('trailing_stop', 0.10)
        self.position_size_pct = config.get('position_size', 0.1)  # 자본의 10%
        
        # EMA 기간 설정
        self.ema_periods = config.get('ema_periods', {
            'trend_fast': 150,
            'trend_slow': 200,
            'entry_fast': 20,
            'entry_slow': 50,
            'exit_slow': 100
        })
        
        # 상태
        self.is_position_open = False
        self.entry_price = 0
        self.entry_time = None
        self.position_size = 0
        self.highest_price = 0  # 롱용 고점
        self.lowest_price = float('inf')  # 숏용 저점
        
        # 모드 관리 (실제/가상)
        self.is_real_mode = True
        self.real_capital = config.get('initial_capital', 1000)
        self.virtual_capital = config.get('initial_capital', 1000)
        
        # 손익 추적
        self.peak_capital = self.real_capital
        self.trough_capital = self.real_capital
        self.drawdown_threshold = config.get('drawdown_threshold', 0.20)  # 20% 하락 시 가상모드
        self.recovery_threshold = config.get('recovery_threshold', 0.30)  # 30% 회복 시 실제모드
        
        # 통계
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0
        
        # 마지막 EMA 값
        self.last_ema_values = {}
    
    def calculate_emas(self, df: pd.DataFrame) -> Dict[str, float]:
        """EMA 계산"""
        emas = {}
        for name, period in self.ema_periods.items():
            if len(df) >= period:
                ema = df['close'].ewm(span=period, adjust=False).mean()
                emas[f'ema_{name}'] = ema.iloc[-1]
                emas[f'prev_ema_{name}'] = ema.iloc[-2] if len(ema) > 1 else ema.iloc[-1]
        return emas
    
    def check_trend(self, emas: Dict) -> bool:
        """
        트렌드 확인
        롱: 150EMA > 200EMA (상승장)
        숏: 150EMA < 200EMA (하락장)
        """
        ema_fast = emas.get('ema_trend_fast')
        ema_slow = emas.get('ema_trend_slow')
        
        if ema_fast is None or ema_slow is None:
            return False
        
        if self.strategy_type == 'long':
            return ema_fast > ema_slow
        else:  # short
            return ema_fast < ema_slow
    
    def check_entry_signal(self, emas: Dict) -> bool:
        """
        진입 신호 확인
        롱: 20EMA가 50EMA 상향 돌파 (골든크로스)
        숏: 20EMA가 50EMA 하향 돌파 (데드크로스)
        """
        curr_fast = emas.get('ema_entry_fast')
        curr_slow = emas.get('ema_entry_slow')
        prev_fast = emas.get('prev_ema_entry_fast')
        prev_slow = emas.get('prev_ema_entry_slow')
        
        if None in [curr_fast, curr_slow, prev_fast, prev_slow]:
            return False
        
        if self.strategy_type == 'long':
            # 골든크로스: 이전에 아래였다가 현재 위로
            was_below = prev_fast <= prev_slow
            is_above = curr_fast > curr_slow
            return was_below and is_above
        else:  # short
            # 데드크로스: 이전에 위였다가 현재 아래로
            was_above = prev_fast >= prev_slow
            is_below = curr_fast < curr_slow
            return was_above and is_below
    
    def check_exit_signal(self, emas: Dict, current_price: float) -> tuple:
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
        
        # 2. EMA 기반 청산 신호
        curr_fast = emas.get('ema_entry_fast')  # 20 EMA
        curr_slow = emas.get('ema_exit_slow')   # 100 EMA
        prev_fast = emas.get('prev_ema_entry_fast')
        prev_slow = emas.get('prev_ema_exit_slow')
        
        if None in [curr_fast, curr_slow, prev_fast, prev_slow]:
            return False, ""
        
        if self.strategy_type == 'long':
            # 데드크로스: 20EMA가 100EMA 하향 돌파
            was_above = prev_fast >= prev_slow
            is_below = curr_fast < curr_slow
            if was_above and is_below:
                return True, "20/100 EMA 데드크로스"
        else:  # short
            # 골든크로스: 100EMA가 200EMA 상향 돌파
            ema_100 = emas.get('ema_exit_slow')
            ema_200 = emas.get('ema_trend_slow')
            prev_100 = emas.get('prev_ema_exit_slow')
            prev_200 = emas.get('prev_ema_trend_slow')
            
            if None not in [ema_100, ema_200, prev_100, prev_200]:
                was_below = prev_100 <= prev_200
                is_above = ema_100 > ema_200
                if was_below and is_above:
                    return True, "100/200 EMA 골든크로스"
        
        return False, ""
    
    def check_mode_switch(self) -> bool:
        """모드 전환 체크 (실제 ↔ 가상)"""
        mode_changed = False
        
        if self.is_real_mode:
            # 실제 → 가상: 고점 대비 손실이 임계값 초과
            if self.real_capital < self.peak_capital * (1 - self.drawdown_threshold):
                self.is_real_mode = False
                self.trough_capital = self.virtual_capital
                mode_changed = True
                print(f"⚠️ [{self.symbol}] {self.strategy_type}: 가상 모드 전환 (손실 {self.drawdown_threshold*100}% 초과)")
        else:
            # 가상 → 실제: 저점 대비 회복이 임계값 초과
            if self.virtual_capital > self.trough_capital * (1 + self.recovery_threshold):
                self.is_real_mode = True
                self.peak_capital = self.real_capital
                mode_changed = True
                print(f"✅ [{self.symbol}] {self.strategy_type}: 실제 모드 전환 (회복 {self.recovery_threshold*100}% 초과)")
        
        return mode_changed
    
    def should_enter(self, emas: Dict, current_price: float) -> bool:
        """진입 가능 여부 종합 판단"""
        if self.is_position_open:
            return False
        
        # 트렌드 확인
        if not self.check_trend(emas):
            return False
        
        # 진입 신호 확인
        if not self.check_entry_signal(emas):
            return False
        
        return True
    
    def enter_position(self, current_price: float, capital: float) -> Dict:
        """포지션 진입"""
        self.is_position_open = True
        self.entry_price = current_price
        self.entry_time = datetime.now()
        self.position_size = (capital * self.position_size_pct * self.leverage) / current_price
        
        # 트레일링스탑 초기화
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
        # PnL 계산
        if self.strategy_type == 'long':
            pnl_pct = (current_price - self.entry_price) / self.entry_price * self.leverage
        else:  # short
            pnl_pct = (self.entry_price - current_price) / self.entry_price * self.leverage
        
        pnl = self.position_size * self.entry_price * pnl_pct / self.leverage
        
        # 통계 업데이트
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        self.total_pnl += pnl
        
        # 자본 업데이트
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
        
        # 상태 초기화
        self.is_position_open = False
        self.entry_price = 0
        self.position_size = 0
        
        return result
    
    def process(self, df: pd.DataFrame, current_price: float) -> Optional[Dict]:
        """전략 처리"""
        # 모드 전환 체크
        self.check_mode_switch()
        
        # EMA 계산
        emas = self.calculate_emas(df)
        self.last_ema_values = emas
        
        # 청산 신호 확인
        should_exit, exit_reason = self.check_exit_signal(emas, current_price)
        if should_exit:
            return self.exit_position(current_price, exit_reason)
        
        # 진입 신호 확인
        if self.should_enter(emas, current_price):
            capital = self.real_capital if self.is_real_mode else self.virtual_capital
            return self.enter_position(current_price, capital)
        
        return None
    
    def get_status(self) -> Dict:
        """전략 상태 조회"""
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
            'win_rate': self.winning_trades / self.total_trades * 100 if self.total_trades > 0 else 0,
            'total_pnl': self.total_pnl,
            'leverage': self.leverage
        }


class TradingEngine:
    """자동매매 엔진"""
    
    def __init__(self, config: Dict = None):
        """
        Args:
            config: 엔진 설정
        """
        self.config = config or {}
        
        # 기본 설정
        self.symbols = self.config.get('symbols', ['BTC-USDT-SWAP'])
        self.initial_capital = self.config.get('initial_capital', 1000)
        self.check_interval = self.config.get('check_interval', 60)  # 60초마다 체크
        
        # 상태
        self.is_running = False
        self.engine_thread = None
        
        # 가격 버퍼 (심볼별)
        self.price_buffers: Dict[str, PriceBuffer] = {}
        
        # 전략 (심볼별 롱/숏)
        self.strategies: Dict[str, TradingStrategy] = {}
        
        # OrderManager
        self.order_manager = None
        
        # 콜백
        self.on_signal_callback: Optional[Callable] = None
        self.on_trade_callback: Optional[Callable] = None
        self.on_status_callback: Optional[Callable] = None
        
        # 통계
        self.start_time = None
        self.total_signals = 0
        self.executed_trades = 0
        
        print("🔧 자동매매 엔진 초기화", flush=True)
    
    def initialize(self):
        """엔진 초기화"""
        import sys
        
        print("=" * 60, flush=True)
        print("🚀 자동매매 엔진 초기화 중...", flush=True)
        print("=" * 60, flush=True)
        sys.stdout.flush()
        
        # OrderManager 초기화
        try:
            from okx.order_manager import OrderManager
            self.order_manager = OrderManager()
            print("✅ OrderManager 연결 완료", flush=True)
        except Exception as e:
            print(f"❌ OrderManager 초기화 실패: {e}", flush=True)
            return False
        
        # 🔥 실제 OKX 잔고 조회
        try:
            balance = self.order_manager.get_account_balance('USDT')
            if balance and balance.get('available', 0) > 0:
                self.initial_capital = float(balance['available'])
                print(f"💰 실제 OKX 잔고 로드: ${self.initial_capital:.2f} USDT", flush=True)
            else:
                print(f"⚠️ 잔고 조회 실패, 설정값 사용: ${self.initial_capital:.2f}", flush=True)
        except Exception as e:
            print(f"⚠️ 잔고 조회 오류: {e}, 설정값 사용: ${self.initial_capital:.2f}", flush=True)
        
        # 가격 버퍼 초기화
        for symbol in self.symbols:
            self.price_buffers[symbol] = PriceBuffer(maxlen=300)
            print(f"✅ 가격 버퍼 생성: {symbol}", flush=True)
        
        # 전략 초기화
        capital_per_strategy = self.initial_capital / (len(self.symbols) * 2)
        
        # 롱 전략 설정
        long_config = {
            'initial_capital': capital_per_strategy,
            'leverage': self.config.get('long_leverage', 10),
            'trailing_stop': self.config.get('long_trailing_stop', 0.10),
            'position_size': self.config.get('position_size', 0.5),
            'drawdown_threshold': 0.20,
            'recovery_threshold': 0.30,
            'ema_periods': {
                'trend_fast': 150,
                'trend_slow': 200,
                'entry_fast': 20,
                'entry_slow': 50,
                'exit_slow': 100
            }
        }
        
        # 숏 전략 설정
        short_config = {
            'initial_capital': capital_per_strategy,
            'leverage': self.config.get('short_leverage', 3),
            'trailing_stop': self.config.get('short_trailing_stop', 0.02),
            'position_size': self.config.get('position_size', 0.5),
            'drawdown_threshold': 0.10,
            'recovery_threshold': 0.20,
            'ema_periods': {
                'trend_fast': 150,
                'trend_slow': 200,
                'entry_fast': 20,
                'entry_slow': 50,
                'exit_slow': 100
            }
        }
        
        for symbol in self.symbols:
            # 롱 전략
            self.strategies[f'long_{symbol}'] = TradingStrategy(
                symbol, 'long', long_config
            )
            print(f"✅ 롱 전략 생성: {symbol} (레버리지: {long_config['leverage']}x)", flush=True)
            
            # 숏 전략
            self.strategies[f'short_{symbol}'] = TradingStrategy(
                symbol, 'short', short_config
            )
            print(f"✅ 숏 전략 생성: {symbol} (레버리지: {short_config['leverage']}x)", flush=True)
        
        # 과거 캔들 데이터 로드 (EMA 계산용)
        for symbol in self.symbols:
            self._load_historical_candles(symbol)
        
        print("=" * 60, flush=True)
        print("✅ 자동매매 엔진 초기화 완료!", flush=True)
        print(f"📊 거래 심볼: {', '.join(self.symbols)}", flush=True)
        print(f"💰 초기 자본: ${self.initial_capital:.2f}", flush=True)
        print(f"⏰ 체크 간격: {self.check_interval}초", flush=True)
        print("=" * 60, flush=True)
        
        import sys
        sys.stdout.flush()
        
        return True
    
    def _load_historical_candles(self, symbol: str, limit: int = 200):
        """과거 캔들 데이터 로드"""
        try:
            print(f"📊 {symbol} 과거 데이터 로드 중...")
            
            response = make_api_request(
                'GET',
                '/api/v5/market/candles',
                params={
                    'instId': symbol,
                    'bar': '30m',  # 30분봉
                    'limit': str(limit)
                }
            )
            
            if response and response.get('code') == '0':
                candles_raw = response.get('data', [])
                
                # 시간순으로 정렬 (오래된 것부터)
                candles_raw.reverse()
                
                for candle_raw in candles_raw:
                    candle = {
                        'timestamp': pd.to_datetime(int(candle_raw[0]), unit='ms'),
                        'open': float(candle_raw[1]),
                        'high': float(candle_raw[2]),
                        'low': float(candle_raw[3]),
                        'close': float(candle_raw[4]),
                        'volume': float(candle_raw[5])
                    }
                    self.price_buffers[symbol].add_candle(candle)
                
                print(f"✅ {symbol}: {len(candles_raw)}개 캔들 로드 완료")
            else:
                print(f"⚠️ {symbol} 과거 데이터 로드 실패: {response}")
                
        except Exception as e:
            print(f"❌ {symbol} 과거 데이터 로드 오류: {e}")
    
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
            print(f"❌ 가격 조회 오류 ({symbol}): {e}")
        
        return None
    
    def _fetch_latest_candle(self, symbol: str) -> Optional[Dict]:
        """최신 캔들 조회"""
        try:
            response = make_api_request(
                'GET',
                '/api/v5/market/candles',
                params={
                    'instId': symbol,
                    'bar': '30m',
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
            print(f"❌ 캔들 조회 오류 ({symbol}): {e}")
        
        return None
    
    def _execute_trade(self, signal: Dict) -> bool:
        """실제 거래 실행"""
        if not self.order_manager:
            print("❌ OrderManager가 없습니다")
            return False
        
        if not signal.get('is_real', False):
            print(f"📊 [가상] {signal['strategy_type']} {signal['action']}: {signal['symbol']}")
            return True
        
        try:
            symbol = signal['symbol']
            action = signal['action']
            side = signal['side']
            
            if action == 'enter':
                # 포지션 진입
                leverage = signal.get('leverage', 1)
                
                # 주문 금액 계산 (자본의 일정 비율)
                balance = self.order_manager.get_account_balance('USDT')
                if not balance:
                    print("❌ 잔고 조회 실패")
                    return False
                
                available = balance['available']
                order_amount = min(available * 0.1, 100)  # 잔고의 10% 또는 $100 중 작은 값
                
                print(f"🚀 [실제] {signal['strategy_type']} 진입: {symbol}")
                print(f"   방향: {side}, 금액: ${order_amount:.2f}, 레버리지: {leverage}x")
                
                # 주문 실행
                if side == 'buy':
                    result = self.order_manager.buy_usdt(symbol, order_amount, leverage)
                else:
                    result = self.order_manager.sell_usdt(symbol, order_amount, leverage)
                
                if result:
                    print(f"✅ 주문 성공! ID: {result.get('order_id')}")
                    
                    # 트레일링스탑 설정
                    trailing_pct = signal.get('trailing_stop', 0.05)
                    self.order_manager.set_trailing_stop(symbol, trailing_pct)
                    
                    self.executed_trades += 1
                    return True
                else:
                    print("❌ 주문 실패")
                    return False
                    
            elif action == 'exit':
                # 포지션 청산
                print(f"📤 [실제] {signal['strategy_type']} 청산: {symbol}")
                print(f"   사유: {signal.get('reason', 'N/A')}")
                print(f"   손익: ${signal.get('pnl', 0):.2f} ({signal.get('pnl_pct', 0):.2f}%)")
                
                result = self.order_manager.close_position(symbol)
                
                if result:
                    print(f"✅ 청산 성공!")
                    self.executed_trades += 1
                    return True
                else:
                    print("❌ 청산 실패")
                    return False
                    
        except Exception as e:
            print(f"❌ 거래 실행 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_strategies(self):
        """전략 처리"""
        for symbol in self.symbols:
            # 현재가 조회
            current_price = self._fetch_current_price(symbol)
            if not current_price:
                continue
            
            # 최신 캔들 확인 및 추가
            latest_candle = self._fetch_latest_candle(symbol)
            if latest_candle:
                buffer = self.price_buffers[symbol]
                
                # 새 캔들이면 추가
                if len(buffer) == 0 or latest_candle['timestamp'] > buffer.candles[-1]['timestamp']:
                    if latest_candle.get('confirm') == '1':  # 확정된 캔들만
                        buffer.add_candle(latest_candle)
                        print(f"📊 새 캔들 추가: {symbol} @ ${latest_candle['close']:,.2f}")
            
            # DataFrame 변환
            df = self.price_buffers[symbol].to_dataframe()
            if df is None or len(df) < 200:
                print(f"⏳ {symbol}: 데이터 부족 ({len(self.price_buffers[symbol])}/200)")
                continue
            
            # 각 전략 처리
            for strategy_key in [f'long_{symbol}', f'short_{symbol}']:
                strategy = self.strategies.get(strategy_key)
                if not strategy:
                    continue
                
                try:
                    signal = strategy.process(df, current_price)
                    
                    if signal:
                        self.total_signals += 1
                        
                        # 콜백 호출
                        if self.on_signal_callback:
                            self.on_signal_callback(signal)
                        
                        # 거래 실행
                        success = self._execute_trade(signal)
                        
                        if self.on_trade_callback:
                            self.on_trade_callback(signal, success)
                            
                except Exception as e:
                    print(f"❌ 전략 처리 오류 ({strategy_key}): {e}")
    
    def _engine_loop(self):
        """엔진 메인 루프"""
        import sys
        
        print("\n" + "=" * 60, flush=True)
        print("🔄 자동매매 엔진 루프 시작!", flush=True)
        print("=" * 60, flush=True)
        sys.stdout.flush()
        
        self.start_time = datetime.now()
        self.cycle_count = 0
        
        last_status_time = 0
        status_interval = 60  # 1분마다 상태 출력 (테스트용, 나중에 300으로 변경)
        
        # 첫 상태 출력
        self._print_status()
        
        while self.is_running:
            try:
                current_time = time.time()
                self.cycle_count += 1
                
                # 매 사이클 로그 (간단히)
                print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] 사이클 #{self.cycle_count} 시작", flush=True)
                sys.stdout.flush()
                
                # 전략 처리
                self._process_strategies()
                
                print(f"✅ 사이클 #{self.cycle_count} 완료 (다음 체크: {self.check_interval}초 후)", flush=True)
                sys.stdout.flush()
                
                # 상태 출력 (1분마다)
                if current_time - last_status_time >= status_interval:
                    self._print_status()
                    last_status_time = current_time
                
                # 대기
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ 엔진 루프 오류: {e}", flush=True)
                import traceback
                traceback.print_exc()
                sys.stdout.flush()
                time.sleep(10)
        
        print("🛑 자동매매 엔진 중지됨", flush=True)
    
    def _print_status(self):
        """상태 출력"""
        import sys
        
        runtime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        runtime_str = str(runtime).split('.')[0]  # 마이크로초 제거
        
        print("\n" + "=" * 60, flush=True)
        print(f"📊 자동매매 상태 - {datetime.now().strftime('%H:%M:%S')}", flush=True)
        print("=" * 60, flush=True)
        print(f"⏱️  실행: {runtime_str} | 사이클: {getattr(self, 'cycle_count', 0)}", flush=True)
        print(f"📈 신호: {self.total_signals}개 | 거래: {self.executed_trades}개", flush=True)
        
        # 각 전략 상태
        print("-" * 60, flush=True)
        for key, strategy in self.strategies.items():
            status = strategy.get_status()
            mode = "🟢실제" if status['is_real_mode'] else "🟡가상"
            pos = "📈보유" if status['is_position_open'] else "⏳대기"
            
            name = "LONG " if "long" in key else "SHORT"
            print(f"  {name}: {mode} {pos} | 자본: ${status['real_capital']:.2f} | 손익: ${status['total_pnl']:+.2f}", flush=True)
        
        print("=" * 60, flush=True)
        sys.stdout.flush()
    
    def start(self):
        """엔진 시작"""
        if self.is_running:
            print("⚠️ 엔진이 이미 실행 중입니다")
            return False
        
        # 초기화
        if not self.initialize():
            return False
        
        self.is_running = True
        self.engine_thread = threading.Thread(target=self._engine_loop, daemon=True)
        self.engine_thread.start()
        
        return True
    
    def stop(self):
        """엔진 중지"""
        if not self.is_running:
            print("⚠️ 엔진이 실행 중이 아닙니다")
            return
        
        print("🛑 자동매매 엔진 중지 중...")
        self.is_running = False
        
        if self.engine_thread:
            self.engine_thread.join(timeout=10)
        
        self._print_status()
        print("✅ 자동매매 엔진 중지 완료")
    
    def get_status(self) -> Dict:
        """엔진 상태 조회"""
        return {
            'is_running': self.is_running,
            'start_time': self.start_time,
            'runtime': str(datetime.now() - self.start_time) if self.start_time else None,
            'total_signals': self.total_signals,
            'executed_trades': self.executed_trades,
            'strategies': {k: v.get_status() for k, v in self.strategies.items()}
        }


# ==================== 실행 스크립트 ====================

def run_trading_engine():
    """자동매매 엔진 실행"""
    print("=" * 60)
    print("🤖 OKX 자동매매 엔진")
    print("=" * 60)
    
    # 설정
    config = {
        'symbols': ['BTC-USDT-SWAP'],
        'initial_capital': 1000,
        'check_interval': 60,  # 60초마다 체크
        'long_leverage': 10,
        'long_trailing_stop': 0.10,  # 10%
        'short_leverage': 3,
        'short_trailing_stop': 0.02,  # 2%
        'position_size': 0.1,  # 자본의 10%
    }
    
    # 엔진 생성
    engine = TradingEngine(config)
    
    # 콜백 설정
    def on_signal(signal):
        action = signal.get('action', 'unknown')
        strategy_type = signal.get('strategy_type', 'unknown')
        symbol = signal.get('symbol', 'unknown')
        is_real = "실제" if signal.get('is_real') else "가상"
        print(f"📡 신호 발생: [{is_real}] {strategy_type} {action} - {symbol}")
    
    def on_trade(signal, success):
        status = "✅ 성공" if success else "❌ 실패"
        print(f"💰 거래 결과: {status}")
    
    engine.on_signal_callback = on_signal
    engine.on_trade_callback = on_trade
    
    # 시작
    print("\n⚠️ 이 프로그램은 실제 자금으로 거래합니다!")
    confirm = input("자동매매를 시작하시겠습니까? (yes 입력): ").strip().lower()
    
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    engine.start()
    
    print("\n🔄 자동매매 실행 중... (Ctrl+C로 중지)")
    
    try:
        while engine.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 중지 요청...")
    finally:
        engine.stop()


if __name__ == "__main__":
    run_trading_engine()