# trading_engine.py
"""
멀티 타임프레임 자동매매 엔진 - 로그 정리 버전

수정 사항:
- 불필요한 반복 로그 제거:
  - 운영 사이클 시작/완료
  - 가격 업데이트 성공
  - 포지션 조회 성공
  - EMA DEBUG 정보
  - 진입 근접도 반복 출력
- 중요 로그만 유지:
  - 엔진 시작/중지
  - 신호 발생 (진입/청산)
  - 주문 실행 결과
  - 에러
  - 1분마다 간략한 상태 (선택적)
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import deque

import pandas as pd
import numpy as np

from config import make_api_request


class PriceBuffer:
    """가격 데이터 버퍼"""
    
    def __init__(self, max_size: int = 1000):
        self.data: deque = deque(maxlen=max_size)
        self.max_size = max_size
        self.last_timestamp = None
    
    def add_candle(self, candle: Dict):
        self.data.append(candle)
        self.last_timestamp = candle.get('timestamp')
    
    def update_last(self, close: float, high: float = None, low: float = None):
        if self.data:
            self.data[-1]['close'] = close
            if high:
                self.data[-1]['high'] = max(self.data[-1]['high'], high)
            if low:
                self.data[-1]['low'] = min(self.data[-1]['low'], low)
    
    def to_dataframe(self) -> Optional[pd.DataFrame]:
        if not self.data:
            return None
        df = pd.DataFrame(list(self.data))
        df.set_index('timestamp', inplace=True)
        return df
    
    def __len__(self):
        return len(self.data)


class MultiTimeframeStrategy:
    """멀티 타임프레임 전략"""
    
    def __init__(self, symbol: str, strategy_type: str, config: Dict):
        self.symbol = symbol
        self.strategy_type = strategy_type  # 'long' or 'short'
        
        # 자본 관리
        self.initial_capital = config.get('initial_capital', 1000)
        self.real_capital = self.initial_capital
        self.virtual_capital = self.initial_capital
        
        # 모드 관리
        self.is_real_mode = True
        self.peak_capital = self.initial_capital
        self.trough_capital = self.initial_capital
        
        # 전환 임계값
        if strategy_type == 'long':
            self.drawdown_threshold = 0.20  # 20% 손실시 가상
            self.recovery_threshold = 0.30  # 30% 회복시 실제
            self.leverage = config.get('long_leverage', 10)
            self.trailing_stop_pct = config.get('long_trailing_stop', 0.10)
        else:
            self.drawdown_threshold = 0.10
            self.recovery_threshold = 0.20
            self.leverage = config.get('short_leverage', 3)
            self.trailing_stop_pct = config.get('short_trailing_stop', 0.02)
        
        # 포지션 상태
        self.is_position_open = False
        self.entry_price = 0
        self.position_size = 0
        self.highest_price = 0
        self.lowest_price = float('inf')
        
        # EMA 데이터
        self.last_ema_30m = {}
        self.last_ema_1m = {}
        self.prev_ema_30m = {}
        self.prev_ema_1m = {}
        
        # 현재가
        self.last_price = 0
        
        # 통계
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0
    
    def update_30m_emas(self, df: pd.DataFrame):
        """30분봉 EMA 업데이트"""
        if df is None or len(df) < 200:
            return
        
        self.prev_ema_30m = self.last_ema_30m.copy()
        
        close = df['close']
        self.last_ema_30m = {
            'ema_100': close.ewm(span=100, adjust=False).mean().iloc[-1],
            'ema_150': close.ewm(span=150, adjust=False).mean().iloc[-1],
            'ema_200': close.ewm(span=200, adjust=False).mean().iloc[-1],
        }
    
    def update_1m_emas(self, df: pd.DataFrame):
        """1분봉 EMA 업데이트"""
        if df is None or len(df) < 100:
            return
        
        self.prev_ema_1m = self.last_ema_1m.copy()
        
        close = df['close']
        self.last_ema_1m = {
            'ema_20': close.ewm(span=20, adjust=False).mean().iloc[-1],
            'ema_50': close.ewm(span=50, adjust=False).mean().iloc[-1],
            'ema_100': close.ewm(span=100, adjust=False).mean().iloc[-1],
        }
    
    def check_entry_signal(self) -> tuple:
        """
        진입 신호 확인
        Returns: (should_enter, status_message)
        """
        if self.is_position_open:
            return False, "[보유중]"
        
        ema150 = self.last_ema_30m.get('ema_150')
        ema200 = self.last_ema_30m.get('ema_200')
        ema20 = self.last_ema_1m.get('ema_20')
        ema50 = self.last_ema_1m.get('ema_50')
        prev_20 = self.prev_ema_1m.get('ema_20')
        prev_50 = self.prev_ema_1m.get('ema_50')
        
        if not all([ema150, ema200, ema20, ema50]):
            return False, "[데이터부족]"
        
        diff_pct = ((ema20 - ema50) / ema50) * 100 if ema50 else 0
        
        if self.strategy_type == 'long':
            # 롱: 30분봉 150>200 + 1분봉 20 상향돌파 50
            trend_ok = ema150 > ema200
            
            if not trend_ok:
                return False, "[트렌드X]"
            
            was_below = prev_20 and prev_50 and prev_20 <= prev_50
            is_above = ema20 > ema50
            crossover = was_below and is_above
            near_cross = ema20 >= ema50 * 0.99
            
            if crossover or near_cross:
                return True, "[진입OK]"
            else:
                return False, f"[대기]"
        
        else:  # short
            trend_ok = ema150 < ema200
            
            if not trend_ok:
                return False, "[트렌드X]"
            
            was_above = prev_20 and prev_50 and prev_20 >= prev_50
            is_below = ema20 < ema50
            crossover = was_above and is_below
            
            if crossover:
                return True, "[진입OK]"
            else:
                return False, "[대기]"
    
    def check_exit_signal(self, current_price: float) -> tuple:
        """청산 신호 확인"""
        if not self.is_position_open:
            return False, ""
        
        # 트레일링스탑
        if self.strategy_type == 'long':
            self.highest_price = max(self.highest_price, current_price)
            drop_pct = (self.highest_price - current_price) / self.highest_price
            if drop_pct >= self.trailing_stop_pct:
                return True, f"트레일링스탑 ({drop_pct*100:.1f}%)"
        else:
            self.lowest_price = min(self.lowest_price, current_price)
            rise_pct = (current_price - self.lowest_price) / self.lowest_price
            if rise_pct >= self.trailing_stop_pct:
                return True, f"트레일링스탑 ({rise_pct*100:.1f}%)"
        
        # EMA 기반 청산
        if self.strategy_type == 'long':
            ema20 = self.last_ema_1m.get('ema_20')
            ema100 = self.last_ema_1m.get('ema_100')
            prev_20 = self.prev_ema_1m.get('ema_20')
            prev_100 = self.prev_ema_1m.get('ema_100')
            
            if all([ema20, ema100, prev_20, prev_100]):
                was_above = prev_20 >= prev_100
                is_below = ema20 < ema100
                if was_above and is_below:
                    return True, "EMA 20/100 데드크로스"
        else:
            ema100 = self.last_ema_30m.get('ema_100')
            ema200 = self.last_ema_30m.get('ema_200')
            if ema100 and ema200 and ema100 > ema200:
                return True, "EMA 100/200 골든크로스"
        
        return False, ""
    
    def enter_position(self, price: float) -> Dict:
        """포지션 진입"""
        self.is_position_open = True
        self.entry_price = price
        self.highest_price = price
        self.lowest_price = price
        
        capital = self.real_capital if self.is_real_mode else self.virtual_capital
        self.position_size = capital * 0.1 / price
        
        return {
            'action': 'enter',
            'symbol': self.symbol,
            'strategy_type': self.strategy_type,
            'price': price,
            'size': self.position_size,
            'is_real': self.is_real_mode,
            'leverage': self.leverage,
        }
    
    def exit_position(self, price: float, reason: str) -> Dict:
        """포지션 청산"""
        if self.strategy_type == 'long':
            pnl_pct = (price - self.entry_price) / self.entry_price
        else:
            pnl_pct = (self.entry_price - price) / self.entry_price
        
        pnl_pct *= self.leverage
        
        capital = self.real_capital if self.is_real_mode else self.virtual_capital
        pnl = capital * 0.1 * pnl_pct
        
        if self.is_real_mode:
            self.real_capital += pnl
        else:
            self.virtual_capital += pnl
        
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        self.total_pnl += pnl
        
        signal = {
            'action': 'exit',
            'symbol': self.symbol,
            'strategy_type': self.strategy_type,
            'price': price,
            'entry_price': self.entry_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct * 100,
            'reason': reason,
            'is_real': self.is_real_mode,
        }
        
        self.is_position_open = False
        self.entry_price = 0
        self.position_size = 0
        
        return signal
    
    def check_mode_switch(self) -> bool:
        """모드 전환 체크"""
        mode_changed = False
        
        if self.is_real_mode:
            self.peak_capital = max(self.peak_capital, self.real_capital)
            if self.real_capital < self.peak_capital * (1 - self.drawdown_threshold):
                self.is_real_mode = False
                self.trough_capital = self.virtual_capital
                mode_changed = True
        else:
            if self.virtual_capital > self.trough_capital * (1 + self.recovery_threshold):
                self.is_real_mode = True
                self.peak_capital = self.real_capital
                mode_changed = True
        
        return mode_changed
    
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
            'total_pnl': self.total_pnl,
            'leverage': self.leverage,
            'ema_30m': self.last_ema_30m,
            'ema_1m': self.last_ema_1m,
        }


class MultiTimeframeTradingEngine:
    """멀티 타임프레임 자동매매 엔진 - 로그 정리 버전"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        self.symbols = self.config.get('symbols', ['BTC-USDT-SWAP'])
        self.initial_capital = self.config.get('initial_capital', 1000)
        self.check_interval = self.config.get('check_interval', 60)
        
        # 로그 설정
        self.verbose = self.config.get('verbose', False)  # 상세 로그
        self.status_interval = self.config.get('status_interval', 300)  # 상태 출력 간격 (초)
        
        self.is_running = False
        self.engine_thread = None
        
        # 버퍼
        self.buffers_30m: Dict[str, PriceBuffer] = {}
        self.buffers_1m: Dict[str, PriceBuffer] = {}
        
        # 전략
        self.strategies: Dict[str, MultiTimeframeStrategy] = {}
        
        # OrderManager
        self.order_manager = None
        
        # 콜백
        self.on_signal_callback: Optional[Callable] = None
        self.on_trade_callback: Optional[Callable] = None
        self.on_mode_change_callback: Optional[Callable] = None
        self.on_log_callback: Optional[Callable] = None  # GUI 로그 콜백
        
        # 통계
        self.start_time = None
        self.total_signals = 0
        self.executed_trades = 0
        self.cycle_count = 0
        
        self.last_30m_update = None
    
    def _log(self, message: str, level: str = "INFO", force: bool = False):
        """
        로그 출력
        
        Args:
            message: 로그 메시지
            level: 로그 레벨 (INFO, WARNING, ERROR, SIGNAL, TRADE)
            force: True면 verbose 설정 무시하고 항상 출력
        """
        # 중요 레벨은 항상 출력
        important_levels = ["ERROR", "SIGNAL", "TRADE", "MODE"]
        
        if force or level in important_levels or self.verbose:
            print(message, flush=True)
        
        # GUI 콜백
        if self.on_log_callback:
            self.on_log_callback(message, level)
    
    def initialize(self):
        """엔진 초기화"""
        self._log("=" * 60)
        self._log("[*] 멀티 타임프레임 엔진 초기화", force=True)
        self._log("=" * 60)
        
        # OrderManager 초기화 (조용히)
        try:
            from okx.order_manager import OrderManager
            self.order_manager = OrderManager(verbose=False)
            self._log("[OK] OrderManager 연결", force=True)
        except Exception as e:
            self._log(f"[!] OrderManager 없음: {e}", "WARNING", force=True)
        
        # 버퍼 초기화
        for symbol in self.symbols:
            self.buffers_30m[symbol] = PriceBuffer(max_size=1000)
            self.buffers_1m[symbol] = PriceBuffer(max_size=500)
        
        # 30분봉 과거 데이터 로드 (2주치)
        self._log("[*] 과거 데이터 로드 중...", force=True)
        for symbol in self.symbols:
            self._load_historical_data(symbol, '30m', self.buffers_30m[symbol], 672)
            self._load_historical_data(symbol, '1m', self.buffers_1m[symbol], 200)
            self._log(f"    {symbol}: 30m={len(self.buffers_30m[symbol])}, 1m={len(self.buffers_1m[symbol])}", force=True)
        
        # 전략 초기화
        for symbol in self.symbols:
            # Long 전략
            self.strategies[f'long_{symbol}'] = MultiTimeframeStrategy(
                symbol, 'long', self.config
            )
            # Short 전략 (config에서 비활성화 가능)
            if not self.config.get('long_only', False):
                self.strategies[f'short_{symbol}'] = MultiTimeframeStrategy(
                    symbol, 'short', self.config
                )
        
        self._log(f"[OK] 전략 초기화: {len(self.strategies)}개", force=True)
        return True
    
    def _load_historical_data(self, symbol: str, bar: str, buffer: PriceBuffer, limit: int):
        """과거 데이터 로드"""
        try:
            response = make_api_request(
                'GET',
                '/api/v5/market/candles',
                params={
                    'instId': symbol,
                    'bar': bar,
                    'limit': str(min(limit, 300))
                }
            )
            
            if response and response.get('code') == '0':
                candles = response['data']
                for candle in reversed(candles):
                    buffer.add_candle({
                        'timestamp': pd.to_datetime(int(candle[0]), unit='ms'),
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5]),
                    })
        except Exception as e:
            self._log(f"[!] 데이터 로드 오류 ({bar}): {e}", "ERROR")
    
    def _fetch_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회 (로그 제거)"""
        try:
            response = make_api_request(
                'GET',
                '/api/v5/market/ticker',
                params={'instId': symbol}
            )
            if response and response.get('code') == '0':
                return float(response['data'][0].get('last', 0))
        except:
            pass
        return None
    
    def _fetch_latest_candle(self, symbol: str, bar: str) -> Optional[Dict]:
        """최신 캔들 조회 (로그 제거)"""
        try:
            response = make_api_request(
                'GET',
                '/api/v5/market/candles',
                params={'instId': symbol, 'bar': bar, 'limit': '1'}
            )
            
            if response and response.get('code') == '0':
                c = response['data'][0]
                return {
                    'timestamp': pd.to_datetime(int(c[0]), unit='ms'),
                    'open': float(c[1]),
                    'high': float(c[2]),
                    'low': float(c[3]),
                    'close': float(c[4]),
                    'volume': float(c[5]),
                    'confirm': c[8] if len(c) > 8 else '0'
                }
        except:
            pass
        return None
    
    def _update_buffers(self, symbol: str, current_price: float):
        """버퍼 업데이트 (로그 제거)"""
        # 1분봉
        latest_1m = self._fetch_latest_candle(symbol, '1m')
        if latest_1m:
            buffer = self.buffers_1m[symbol]
            is_new = buffer.last_timestamp is None or latest_1m['timestamp'] > buffer.last_timestamp
            is_confirmed = latest_1m.get('confirm') == '1'
            
            if is_new and is_confirmed:
                buffer.add_candle(latest_1m)
            elif len(buffer) > 0:
                buffer.update_last(latest_1m['close'], latest_1m['high'], latest_1m['low'])
        
        # 30분봉 (30분마다)
        now = datetime.now()
        if self.last_30m_update is None or (now - self.last_30m_update).seconds >= 1800:
            latest_30m = self._fetch_latest_candle(symbol, '30m')
            if latest_30m:
                buffer = self.buffers_30m[symbol]
                is_new = buffer.last_timestamp is None or latest_30m['timestamp'] > buffer.last_timestamp
                is_confirmed = latest_30m.get('confirm') == '1'
                
                if is_new and is_confirmed:
                    buffer.add_candle(latest_30m)
                    self.last_30m_update = now
                elif len(buffer) > 0:
                    buffer.update_last(latest_30m['close'], latest_30m['high'], latest_30m['low'])
    
    def _process_strategies(self):
        """전략 처리"""
        for symbol in self.symbols:
            current_price = self._fetch_current_price(symbol)
            if not current_price:
                continue
            
            self._update_buffers(symbol, current_price)
            
            df_30m = self.buffers_30m[symbol].to_dataframe()
            df_1m = self.buffers_1m[symbol].to_dataframe()
            
            if df_30m is None or len(df_30m) < 200:
                continue
            if df_1m is None or len(df_1m) < 100:
                continue
            
            for strategy_key, strategy in self.strategies.items():
                if symbol not in strategy_key:
                    continue
                
                try:
                    # EMA 업데이트
                    strategy.update_30m_emas(df_30m)
                    strategy.update_1m_emas(df_1m)
                    strategy.last_price = current_price
                    
                    # 모드 체크
                    if strategy.check_mode_switch():
                        mode = "REAL" if strategy.is_real_mode else "VIRTUAL"
                        self._log(f"🔄 [{strategy.strategy_type.upper()}] 모드 전환 → {mode}", "MODE", force=True)
                        if self.on_mode_change_callback:
                            prev_mode = "VIRTUAL" if strategy.is_real_mode else "REAL"
                            self.on_mode_change_callback(prev_mode, mode, "자동 전환")
                    
                    # 청산 체크
                    should_exit, exit_reason = strategy.check_exit_signal(current_price)
                    if should_exit:
                        signal = strategy.exit_position(current_price, exit_reason)
                        self.total_signals += 1
                        
                        self._log(f"🔴 [{signal['strategy_type'].upper()}] 청산: ${current_price:,.0f} | {exit_reason} | PnL: ${signal['pnl']:+.2f}", "SIGNAL", force=True)
                        
                        if self.on_signal_callback:
                            self.on_signal_callback(signal)
                        
                        if signal['is_real']:
                            success = self._execute_trade(signal)
                            if self.on_trade_callback:
                                self.on_trade_callback(signal, success)
                        continue
                    
                    # 진입 체크
                    should_enter, status = strategy.check_entry_signal()
                    if should_enter:
                        signal = strategy.enter_position(current_price)
                        self.total_signals += 1
                        
                        mode = "REAL" if signal['is_real'] else "VIRT"
                        self._log(f"🟢 [{signal['strategy_type'].upper()}] 진입: ${current_price:,.0f} | [{mode}] | 레버리지: {signal['leverage']}x", "SIGNAL", force=True)
                        
                        if self.on_signal_callback:
                            self.on_signal_callback(signal)
                        
                        if signal['is_real']:
                            success = self._execute_trade(signal)
                            if self.on_trade_callback:
                                self.on_trade_callback(signal, success)
                
                except Exception as e:
                    self._log(f"[X] 전략 처리 오류: {e}", "ERROR", force=True)
    
    def _execute_trade(self, signal: Dict) -> bool:
        """거래 실행"""
        if not self.order_manager:
            self._log("[!] OrderManager 없음 - 주문 스킵", "WARNING")
            return False
        
        try:
            symbol = signal['symbol']
            action = signal['action']
            strategy_type = signal['strategy_type']
            
            if action == 'enter':
                side = 'buy' if strategy_type == 'long' else 'sell'
                
                # 주문 수량 계산
                balance = self.order_manager.get_account_balance('USDT')
                if not balance:
                    return False
                
                available = balance.get('available', 0)
                trade_amount = available * 0.1  # 10%
                trade_amount = min(trade_amount, 100)  # 최대 $100
                
                price = signal['price']
                contract_value = 0.01
                size = int((trade_amount / price) / contract_value)
                
                if size < 1:
                    self._log(f"[!] 주문 수량 부족: ${trade_amount:.2f}", "WARNING")
                    return False
                
                result = self.order_manager.place_market_order(
                    inst_id=symbol,
                    side=side,
                    size=size,
                    leverage=signal.get('leverage', 1)
                )
                
                if result:
                    self.executed_trades += 1
                    return True
            
            elif action == 'exit':
                result = self.order_manager.close_position(symbol)
                if result:
                    self.executed_trades += 1
                    return True
        
        except Exception as e:
            self._log(f"[X] 거래 실행 오류: {e}", "ERROR", force=True)
        
        return False
    
    def _print_status(self):
        """상태 출력 (간략화)"""
        if not self.start_time:
            return
        
        runtime = datetime.now() - self.start_time
        runtime_str = str(runtime).split('.')[0]
        
        self._log(f"\n[상태] {datetime.now().strftime('%H:%M:%S')} | 실행: {runtime_str} | 신호: {self.total_signals} | 거래: {self.executed_trades}", force=True)
        
        for key, strategy in self.strategies.items():
            status = strategy.get_status()
            mode = "R" if status['is_real_mode'] else "V"
            pos = "●" if status['is_position_open'] else "○"
            name = "L" if "long" in key else "S"
            self._log(f"  [{name}] {mode}{pos} ${status['real_capital']:.0f} PnL:${status['total_pnl']:+.0f}", force=True)
    
    def _engine_loop(self):
        """엔진 메인 루프"""
        self._log("\n[*] 엔진 루프 시작", force=True)
        
        self.start_time = datetime.now()
        self.cycle_count = 0
        last_status_time = time.time()
        
        while self.is_running:
            try:
                self.cycle_count += 1
                
                # 전략 처리 (로그 없음)
                self._process_strategies()
                
                # 주기적 상태 출력
                if time.time() - last_status_time >= self.status_interval:
                    self._print_status()
                    last_status_time = time.time()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self._log(f"[X] 루프 오류: {e}", "ERROR", force=True)
                time.sleep(10)
        
        self._log("[!] 엔진 중지됨", force=True)
    
    def start(self):
        """엔진 시작"""
        if self.is_running:
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
        
        self._log("[*] 엔진 중지 중...", force=True)
        self.is_running = False
        
        if self.engine_thread:
            self.engine_thread.join(timeout=10)
        
        self._print_status()
        self._log("[OK] 엔진 중지 완료", force=True)
    
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


# 기존 호환성
TradingEngine = MultiTimeframeTradingEngine
TradingStrategy = MultiTimeframeStrategy