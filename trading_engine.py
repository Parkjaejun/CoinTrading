# trading_engine.py
"""
멀티 타임프레임 자동매매 엔진 - 전략 모드 선택 기능 추가 버전

변경 사항:
- strategy_mode 속성 추가 ("long_only" 또는 "long_short")
- set_strategy_mode() 메서드 추가
- 전략 생성 시 모드에 따른 활성화 제어
- 메인 루프에서 비활성화된 전략 스킵

수정된 부분은 ⭐ 표시
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
        
        # ⭐ 전략 활성화 상태 추가
        self.is_active = True
        
        # 자본 관리
        self.initial_capital = config.get('initial_capital', 1000)
        self.real_capital = self.initial_capital
        self.virtual_capital = self.initial_capital
        
        # 모드 관리
        self.is_real_mode = True
        self.peak_capital = self.initial_capital
        self.trough_capital = self.initial_capital
        
        # 전환 임계값 (롱/숏 차별화)
        if strategy_type == 'long':
            self.drawdown_threshold = 0.20  # 20% 손실시 가상
            self.recovery_threshold = 0.30  # 30% 회복시 실제
            self.leverage = config.get('leverage', 10)
            self.trailing_stop = config.get('trailing_stop', 0.10)
        else:  # short
            self.drawdown_threshold = 0.10  # 10% 손실시 가상
            self.recovery_threshold = 0.20  # 20% 회복시 실제
            self.leverage = config.get('leverage', 3)
            self.trailing_stop = config.get('trailing_stop', 0.02)
        
        # 포지션 상태
        self.is_position_open = False
        self.entry_price = 0
        self.position_size = 0
        self.peak_price = 0
        
        # 거래 통계
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0
        
        # EMA 캐시
        self.last_ema_30m = {}
        self.last_ema_1m = {}
        self.last_price = 0
    
    def update_30m_emas(self, df: pd.DataFrame):
        """30분봉 EMA 업데이트"""
        if df is None or len(df) < 200:
            return
        
        close = df['close']
        self.last_ema_30m = {
            'ema20': close.ewm(span=20).mean().iloc[-1],
            'ema50': close.ewm(span=50).mean().iloc[-1],
            'ema100': close.ewm(span=100).mean().iloc[-1],
            'ema150': close.ewm(span=150).mean().iloc[-1],
            'ema200': close.ewm(span=200).mean().iloc[-1],
        }
    
    def update_1m_emas(self, df: pd.DataFrame):
        """1분봉 EMA 업데이트"""
        if df is None or len(df) < 100:
            return
        
        close = df['close']
        self.last_ema_1m = {
            'ema20': close.ewm(span=20).mean().iloc[-1],
            'ema50': close.ewm(span=50).mean().iloc[-1],
            'ema100': close.ewm(span=100).mean().iloc[-1],
        }
    
    def check_trend_condition(self, price: float = None) -> bool:
        """트렌드 조건 확인 (30분봉)"""
        if not self.last_ema_30m:
            return False
        
        ema150 = self.last_ema_30m.get('ema150', 0)
        ema200 = self.last_ema_30m.get('ema200', 0)
        
        if self.strategy_type == 'long':
            return ema150 > ema200  # 상승 트렌드
        else:
            return ema150 < ema200  # 하락 트렌드
    
    def check_entry_signal(self) -> tuple:
        """진입 신호 확인"""
        # ⭐ 비활성화된 전략은 진입 불가
        if not self.is_active:
            return False, "strategy_inactive"
        
        if self.is_position_open:
            return False, "position_open"
        
        if not self.check_trend_condition():
            return False, "trend_not_ok"
        
        if not self.last_ema_1m:
            return False, "no_1m_data"
        
        ema20 = self.last_ema_1m.get('ema20', 0)
        ema50 = self.last_ema_1m.get('ema50', 0)
        
        if self.strategy_type == 'long':
            # 롱: EMA20 >= EMA50 * 0.99 (99% 이상)
            if ema20 >= ema50 * 0.99:
                return True, "golden_cross_approaching"
        else:
            # 숏: EMA20 <= EMA50 * 1.01 (101% 이하)
            if ema20 <= ema50 * 1.01:
                return True, "dead_cross_approaching"
        
        return False, "entry_condition_not_met"
    
    def check_exit_signal(self, price: float) -> tuple:
        """청산 신호 확인"""
        if not self.is_position_open:
            return False, ""
        
        # 트레일링스탑
        if self.strategy_type == 'long':
            stop_price = self.peak_price * (1 - self.trailing_stop)
            if price <= stop_price:
                return True, "trailing_stop"
            
            # EMA 데드크로스 (1분봉)
            if self.last_ema_1m:
                ema20 = self.last_ema_1m.get('ema20', 0)
                ema100 = self.last_ema_1m.get('ema100', 0)
                if ema20 < ema100:
                    return True, "ema_dead_cross"
        else:
            stop_price = self.peak_price * (1 + self.trailing_stop)
            if price >= stop_price:
                return True, "trailing_stop"
            
            # EMA 골든크로스 (1분봉)
            if self.last_ema_1m:
                ema100 = self.last_ema_1m.get('ema100', 0)
                ema200 = self.last_ema_30m.get('ema200', 0)  # 30분봉 사용
                if ema100 > ema200:
                    return True, "ema_golden_cross"
        
        return False, ""
    
    def enter_position(self, price: float) -> Dict:
        """포지션 진입"""
        capital = self.real_capital if self.is_real_mode else self.virtual_capital
        
        # 포지션 크기 계산
        use_capital = capital * 0.5
        notional = use_capital * self.leverage
        size = notional / price
        
        self.is_position_open = True
        self.entry_price = price
        self.position_size = size
        self.peak_price = price
        
        signal = {
            'action': 'enter',
            'symbol': self.symbol,
            'strategy_type': self.strategy_type,
            'price': price,
            'size': size,
            'leverage': self.leverage,
            'is_real': self.is_real_mode,
        }
        
        return signal
    
    def exit_position(self, price: float, reason: str) -> Dict:
        """포지션 청산"""
        if not self.is_position_open:
            return {}
        
        # PnL 계산
        if self.strategy_type == 'long':
            pnl_pct = (price - self.entry_price) / self.entry_price
        else:
            pnl_pct = (self.entry_price - price) / self.entry_price
        
        pnl = self.position_size * self.entry_price * pnl_pct * self.leverage
        
        # 자본 업데이트
        if self.is_real_mode:
            self.real_capital += pnl
        else:
            self.virtual_capital += pnl
        
        # 통계 업데이트
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
            'is_active': self.is_active,  # ⭐ 활성화 상태 추가
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
    """멀티 타임프레임 자동매매 엔진 - 전략 모드 선택 기능 포함"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        self.symbols = self.config.get('symbols', ['BTC-USDT-SWAP'])
        self.check_interval = self.config.get('check_interval', 60)
        
        # ⭐⭐⭐ 전략 모드 설정 (핵심 추가 부분) ⭐⭐⭐
        self.strategy_mode = self.config.get('strategy_mode', 'long_only')
        self.long_enabled = self.config.get('long_enabled', True)
        self.short_enabled = self.config.get('short_enabled', False)
        
        # long_only 설정 호환
        if self.config.get('long_only', True):
            self.strategy_mode = 'long_only'
            self.short_enabled = False
        
        # 전략 저장소
        self.strategies: Dict[str, MultiTimeframeStrategy] = {}
        
        # 가격 버퍼
        self.price_buffers_30m: Dict[str, PriceBuffer] = {}
        self.price_buffers_1m: Dict[str, PriceBuffer] = {}
        
        # 상태
        self.is_running = False
        self.run_thread = None
        self.start_time = None
        
        # 통계
        self.total_signals = 0
        self.executed_trades = 0
        
        # 콜백
        self.on_signal_callback: Optional[Callable] = None
        self.on_trade_callback: Optional[Callable] = None
        self.on_mode_change_callback: Optional[Callable] = None
        
        # OrderManager
        self.order_manager = None
        try:
            from okx.order_manager import OrderManager
            self.order_manager = OrderManager()
        except ImportError:
            print("⚠️ OrderManager를 로드할 수 없습니다.")
        
        # 전략 생성
        self._create_strategies()
        
        # 가격 버퍼 생성
        self._create_price_buffers()
        
        # ⭐ 초기화 로그
        self._log_init_status()
    
    def _log_init_status(self):
        """초기화 상태 로그"""
        print(f"\n{'='*60}")
        print(f"🚀 자동매매 엔진 초기화")
        print(f"{'='*60}")
        print(f"📊 전략 모드: {self.strategy_mode}")
        print(f"📈 롱 전략: {'✅ 활성' if self.long_enabled else '⛔ 비활성'}")
        print(f"📉 숏 전략: {'✅ 활성' if self.short_enabled else '⛔ 비활성'}")
        print(f"🎯 심볼: {', '.join(self.symbols)}")
        print(f"⏱️ 체크 간격: {self.check_interval}초")
        print(f"{'='*60}\n")
    
    # ⭐⭐⭐ 전략 모드 설정 메서드 (핵심 추가) ⭐⭐⭐
    def set_strategy_mode(self, mode: str) -> bool:
        """
        전략 모드 설정
        
        Args:
            mode: "long_only" 또는 "long_short"
            
        Returns:
            bool: 성공 여부
        """
        if mode not in ["long_only", "long_short"]:
            self._log(f"⚠️ 알 수 없는 전략 모드: {mode}", "WARNING", force=True)
            return False
        
        previous_mode = self.strategy_mode
        self.strategy_mode = mode
        
        if mode == "long_only":
            self.long_enabled = True
            self.short_enabled = False
        else:  # long_short
            self.long_enabled = True
            self.short_enabled = True
        
        # 전략 객체들의 활성화 상태 업데이트
        for strategy_key, strategy in self.strategies.items():
            if 'short' in strategy_key.lower():
                strategy.is_active = self.short_enabled
        
        # 로그 출력
        self._log(f"\n{'='*60}", force=True)
        self._log(f"🔄 전략 모드 변경: {previous_mode} → {mode}", "MODE", force=True)
        self._log(f"{'='*60}", force=True)
        self._log(f"  📈 롱 전략: {'✅ 활성' if self.long_enabled else '⛔ 비활성'}", force=True)
        self._log(f"  📉 숏 전략: {'✅ 활성' if self.short_enabled else '⛔ 비활성'}", force=True)
        self._log(f"{'='*60}\n", force=True)
        
        return True
    
    def get_strategy_mode(self) -> str:
        """현재 전략 모드 반환"""
        return self.strategy_mode
    
    def is_short_enabled_check(self) -> bool:
        """숏 전략 활성화 여부"""
        return self.short_enabled
    
    def _create_strategies(self):
        """전략 생성 - 모드에 따라 활성화 상태 설정"""
        for symbol in self.symbols:
            # 롱 전략 (항상 생성, 항상 활성화)
            long_config = {
                'initial_capital': self.config.get('initial_capital', 1000),
                'leverage': self.config.get('long_leverage', 10),
                'trailing_stop': self.config.get('long_trailing_stop', 0.10),
            }
            long_strategy = MultiTimeframeStrategy(symbol, 'long', long_config)
            long_strategy.is_active = True  # 롱은 항상 활성화
            self.strategies[f'long_{symbol}'] = long_strategy
            
            self._log(f"✅ 롱 전략 생성: {symbol} (레버리지: {long_config['leverage']}x)", force=True)
            
            # 숏 전략 (생성은 하되 모드에 따라 활성화)
            short_config = {
                'initial_capital': self.config.get('initial_capital', 1000),
                'leverage': self.config.get('short_leverage', 3),
                'trailing_stop': self.config.get('short_trailing_stop', 0.02),
            }
            short_strategy = MultiTimeframeStrategy(symbol, 'short', short_config)
            short_strategy.is_active = self.short_enabled  # ⭐ 모드에 따라 활성화
            self.strategies[f'short_{symbol}'] = short_strategy
            
            status = "✅ 활성" if self.short_enabled else "⛔ 비활성"
            self._log(f"{status} 숏 전략 생성: {symbol} (레버리지: {short_config['leverage']}x)", force=True)
    
    def _create_price_buffers(self):
        """가격 버퍼 생성"""
        for symbol in self.symbols:
            self.price_buffers_30m[symbol] = PriceBuffer(500)
            self.price_buffers_1m[symbol] = PriceBuffer(200)
    
    def _log(self, message: str, category: str = "INFO", force: bool = False):
        """로그 출력"""
        if force or category in ["ERROR", "SIGNAL", "MODE", "WARNING"]:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")
    
    def start(self) -> bool:
        """엔진 시작"""
        if self.is_running:
            return False
        
        self._log("🚀 자동매매 엔진 시작 중...", force=True)
        
        # 초기 데이터 로드
        self._load_initial_data()
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # 백그라운드 스레드 시작
        self.run_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.run_thread.start()
        
        self._log("✅ 자동매매 엔진 시작됨!", force=True)
        return True
    
    def stop(self):
        """엔진 중지"""
        self.is_running = False
        if self.run_thread:
            self.run_thread.join(timeout=5)
        self._log("🛑 자동매매 엔진 중지됨", force=True)
    
    def _load_initial_data(self):
        """초기 데이터 로드"""
        for symbol in self.symbols:
            try:
                # 30분봉 데이터 로드
                df_30m = self._fetch_candles(symbol, '30m', 300)
                if df_30m is not None:
                    for _, row in df_30m.iterrows():
                        self.price_buffers_30m[symbol].add_candle(row.to_dict())
                    self._log(f"✅ {symbol} 30분봉 {len(df_30m)}개 로드", force=True)
                
                # 1분봉 데이터 로드
                df_1m = self._fetch_candles(symbol, '1m', 150)
                if df_1m is not None:
                    for _, row in df_1m.iterrows():
                        self.price_buffers_1m[symbol].add_candle(row.to_dict())
                    self._log(f"✅ {symbol} 1분봉 {len(df_1m)}개 로드", force=True)
                    
            except Exception as e:
                self._log(f"❌ {symbol} 데이터 로드 실패: {e}", "ERROR", force=True)
    
    def _fetch_candles(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        try:
            bar_map = {'30m': '30m', '1m': '1m', '1H': '1H'}
            bar = bar_map.get(timeframe, '30m')
            
            response = make_api_request(
                'GET',
                '/api/v5/market/candles',
                params={'instId': symbol, 'bar': bar, 'limit': str(limit)}
            )
            
            if response and response.get('code') == '0':
                data = response.get('data', [])
                if data:
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 
                        'volume', 'volCcy', 'volCcyQuote', 'confirm'
                    ])
                    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    return df.sort_values('timestamp').reset_index(drop=True)
            
            return None
            
        except Exception as e:
            self._log(f"캔들 조회 오류: {e}", "ERROR")
            return None
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """현재 가격 조회"""
        try:
            response = make_api_request(
                'GET',
                '/api/v5/market/ticker',
                params={'instId': symbol}
            )
            
            if response and response.get('code') == '0':
                data = response.get('data', [])
                if data:
                    return float(data[0].get('last', 0))
            
            return None
            
        except Exception as e:
            self._log(f"가격 조회 오류: {e}", "ERROR")
            return None
    
    def _run_loop(self):
        """메인 루프"""
        while self.is_running:
            try:
                for symbol in self.symbols:
                    # 현재 가격
                    current_price = self._get_current_price(symbol)
                    if not current_price:
                        continue
                    
                    # 데이터 업데이트
                    df_30m = self.price_buffers_30m[symbol].to_dataframe()
                    df_1m = self.price_buffers_1m[symbol].to_dataframe()
                    
                    if df_30m is None or len(df_30m) < 200:
                        continue
                    if df_1m is None or len(df_1m) < 100:
                        continue
                    
                    # 전략 처리
                    for strategy_key, strategy in self.strategies.items():
                        if symbol not in strategy_key:
                            continue
                        
                        # ⭐⭐⭐ 비활성화된 전략 스킵 (핵심 수정) ⭐⭐⭐
                        if not strategy.is_active:
                            continue
                        
                        # ⭐ 숏 전략 비활성화 확인 (이중 체크)
                        if 'short' in strategy_key and not self.short_enabled:
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
                            
                            # 포지션 보유 시 청산 체크
                            if strategy.is_position_open:
                                # peak 갱신
                                if strategy.strategy_type == 'long':
                                    strategy.peak_price = max(strategy.peak_price, current_price)
                                else:
                                    strategy.peak_price = min(strategy.peak_price, current_price)
                                
                                should_exit, exit_reason = strategy.check_exit_signal(current_price)
                                if should_exit:
                                    signal = strategy.exit_position(current_price, exit_reason)
                                    self.total_signals += 1
                                    
                                    self._log(
                                        f"🔴 [{signal['strategy_type'].upper()}] 청산: "
                                        f"${current_price:,.0f} | {exit_reason} | "
                                        f"PnL: ${signal['pnl']:+.2f}",
                                        "SIGNAL", force=True
                                    )
                                    
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
                                self._log(
                                    f"🟢 [{signal['strategy_type'].upper()}] 진입: "
                                    f"${current_price:,.0f} | [{mode}] | "
                                    f"레버리지: {signal['leverage']}x",
                                    "SIGNAL", force=True
                                )
                                
                                if self.on_signal_callback:
                                    self.on_signal_callback(signal)
                                
                                if signal['is_real']:
                                    success = self._execute_trade(signal)
                                    if self.on_trade_callback:
                                        self.on_trade_callback(signal, success)
                        
                        except Exception as e:
                            self._log(f"[X] 전략 처리 오류: {e}", "ERROR", force=True)
                
            except Exception as e:
                self._log(f"[X] 루프 오류: {e}", "ERROR", force=True)
            
            time.sleep(self.check_interval)
    
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
                    self._log(f"[!] 주문 수량 부족: {size}", "WARNING")
                    return False
                
                # 주문 실행
                result = self.order_manager.place_market_order(
                    symbol=symbol,
                    side=side,
                    size=size
                )
                
                if result:
                    self.executed_trades += 1
                    return True
                    
            elif action == 'exit':
                # 포지션 청산
                result = self.order_manager.close_position(symbol)
                if result:
                    self.executed_trades += 1
                    return True
            
            return False
            
        except Exception as e:
            self._log(f"[X] 주문 실행 오류: {e}", "ERROR", force=True)
            return False
    
    def get_status(self) -> Dict:
        """엔진 상태 조회"""
        runtime = ""
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            runtime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return {
            'is_running': self.is_running,
            'strategy_mode': self.strategy_mode,
            'long_enabled': self.long_enabled,
            'short_enabled': self.short_enabled,
            'runtime': runtime,
            'total_signals': self.total_signals,
            'executed_trades': self.executed_trades,
            'strategies': {k: v.get_status() for k, v in self.strategies.items()}
        }


# 별칭 (호환성)
TradingEngine = MultiTimeframeTradingEngine