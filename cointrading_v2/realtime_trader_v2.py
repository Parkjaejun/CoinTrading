# realtime_trader_v2.py
"""
CoinTrading v2 실시간 트레이딩 모듈
- WebSocket 기반 실시간 데이터 수신
- 전략 엔진 연동
- OKX API 주문 실행
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from collections import deque
import threading
import time
import json

from config_v2 import ParamsV2, EmailConfig, DEFAULT_EMAIL_CONFIG
from models import BarData
from trading_engine_v2 import TradingEngineV2
from email_notifier import EmailNotifier


def ema_update(prev_ema: float, new_value: float, period: int) -> float:
    """EMA 점진적 업데이트"""
    multiplier = 2 / (period + 1)
    return (new_value - prev_ema) * multiplier + prev_ema


class PriceBuffer:
    """가격 데이터 버퍼 - EMA 계산용"""
    
    def __init__(self, params: ParamsV2, max_candles: int = 500):
        self.params = params
        self.max_candles = max_candles
        
        # 캔들 데이터
        self.candles: deque = deque(maxlen=max_candles)
        
        # 현재 EMA 값들
        self.ema_trend_fast: float = 0.0
        self.ema_trend_slow: float = 0.0
        self.ema_entry_fast: float = 0.0
        self.ema_entry_slow: float = 0.0
        self.ema_exit_fast: float = 0.0
        self.ema_exit_slow: float = 0.0
        
        # 이전 봉 EMA (크로스 판단용)
        self.prev_entry_fast: float = 0.0
        self.prev_entry_slow: float = 0.0
        self.prev_exit_fast: float = 0.0
        self.prev_exit_slow: float = 0.0
        
        self.is_initialized = False
        self.last_candle_time: Optional[datetime] = None
    
    def add_historical_candles(self, candles: List[Dict]):
        """히스토리 캔들로 초기화"""
        import pandas as pd
        
        for c in candles:
            self.candles.append(c)
        
        if len(self.candles) < self.params.trend_slow + 10:
            print(f"⚠️ 캔들 부족: {len(self.candles)}개 (최소 {self.params.trend_slow + 10}개 필요)")
            return
        
        # DataFrame으로 EMA 계산
        df = pd.DataFrame(list(self.candles))
        close = df['close'].astype(float)
        
        # EMA 계산
        def calc_ema(series, period):
            return series.ewm(span=period, adjust=False).mean()
        
        self.ema_trend_fast = calc_ema(close, self.params.trend_fast).iloc[-1]
        self.ema_trend_slow = calc_ema(close, self.params.trend_slow).iloc[-1]
        self.ema_entry_fast = calc_ema(close, self.params.entry_fast).iloc[-1]
        self.ema_entry_slow = calc_ema(close, self.params.entry_slow).iloc[-1]
        self.ema_exit_fast = calc_ema(close, self.params.exit_fast).iloc[-1]
        self.ema_exit_slow = calc_ema(close, self.params.exit_slow).iloc[-1]
        
        # 이전 봉 EMA
        if len(close) >= 2:
            self.prev_entry_fast = calc_ema(close, self.params.entry_fast).iloc[-2]
            self.prev_entry_slow = calc_ema(close, self.params.entry_slow).iloc[-2]
            self.prev_exit_fast = calc_ema(close, self.params.exit_fast).iloc[-2]
            self.prev_exit_slow = calc_ema(close, self.params.exit_slow).iloc[-2]
        
        self.is_initialized = True
        self.last_candle_time = df['timestamp'].iloc[-1] if 'timestamp' in df.columns else None
        
        print(f"✅ 버퍼 초기화 완료: {len(self.candles)}개 캔들")
        print(f"   - 트렌드 EMA: {self.ema_trend_fast:.2f} / {self.ema_trend_slow:.2f}")
    
    def update_with_new_candle(self, candle: Dict):
        """새 캔들로 EMA 업데이트"""
        if not self.is_initialized:
            self.candles.append(candle)
            return
        
        close = float(candle['close'])
        
        # 이전 값 저장
        self.prev_entry_fast = self.ema_entry_fast
        self.prev_entry_slow = self.ema_entry_slow
        self.prev_exit_fast = self.ema_exit_fast
        self.prev_exit_slow = self.ema_exit_slow
        
        # EMA 업데이트
        self.ema_trend_fast = ema_update(self.ema_trend_fast, close, self.params.trend_fast)
        self.ema_trend_slow = ema_update(self.ema_trend_slow, close, self.params.trend_slow)
        self.ema_entry_fast = ema_update(self.ema_entry_fast, close, self.params.entry_fast)
        self.ema_entry_slow = ema_update(self.ema_entry_slow, close, self.params.entry_slow)
        self.ema_exit_fast = ema_update(self.ema_exit_fast, close, self.params.exit_fast)
        self.ema_exit_slow = ema_update(self.ema_exit_slow, close, self.params.exit_slow)
        
        self.candles.append(candle)
        self.last_candle_time = candle.get('timestamp')
    
    def get_bar_data(self, candle: Dict) -> Optional[BarData]:
        """현재 상태로 BarData 생성"""
        if not self.is_initialized:
            return None
        
        return BarData(
            timestamp=candle.get('timestamp', datetime.now()),
            open=float(candle.get('open', 0)),
            high=float(candle.get('high', 0)),
            low=float(candle.get('low', 0)),
            close=float(candle.get('close', 0)),
            ema_trend_fast=self.ema_trend_fast,
            ema_trend_slow=self.ema_trend_slow,
            ema_entry_fast=self.ema_entry_fast,
            ema_entry_slow=self.ema_entry_slow,
            ema_exit_fast=self.ema_exit_fast,
            ema_exit_slow=self.ema_exit_slow,
            prev_entry_fast=self.prev_entry_fast,
            prev_entry_slow=self.prev_entry_slow,
            prev_exit_fast=self.prev_exit_fast,
            prev_exit_slow=self.prev_exit_slow,
        )


class RealtimeTraderV2:
    """실시간 트레이더 v2"""
    
    def __init__(self,
                 symbol: str = "BTC-USDT-SWAP",
                 params: ParamsV2 = None,
                 initial_capital: float = 10000.0,
                 email_config: EmailConfig = None,
                 dry_run: bool = True):
        """
        Args:
            symbol: 거래 심볼
            params: 전략 파라미터
            initial_capital: 초기 자본
            email_config: 이메일 설정
            dry_run: True면 실제 주문 없이 시뮬레이션
        """
        self.symbol = symbol
        self.params = params or ParamsV2()
        self.initial_capital = initial_capital
        self.dry_run = dry_run
        
        # 이메일 알림
        email_config = email_config or DEFAULT_EMAIL_CONFIG
        self.email_notifier = EmailNotifier(email_config) if email_config.is_configured else None
        
        # 가격 버퍼
        self.price_buffer = PriceBuffer(self.params)
        
        # 트레이딩 엔진
        self.engine = TradingEngineV2(
            params=self.params,
            email_notifier=self.email_notifier,
            symbol=symbol,
            use_mock_email=False
        )
        self.engine.init_capital(initial_capital)
        
        # 상태
        self.is_running = False
        self.last_processed_candle: Optional[Dict] = None
        
        # 콜백
        self.on_signal_callback: Optional[Callable] = None
        self.on_order_callback: Optional[Callable] = None
        self.on_mode_switch_callback: Optional[Callable] = None
        
        print(f"🚀 RealtimeTraderV2 초기화")
        print(f"   - 심볼: {symbol}")
        print(f"   - 초기 자본: ${initial_capital:,.2f}")
        print(f"   - Dry Run: {dry_run}")
        print(f"   - 이메일 알림: {'활성화' if self.email_notifier else '비활성화'}")
    
    def initialize_with_history(self, candles: List[Dict]):
        """히스토리 데이터로 초기화"""
        print(f"📊 히스토리 데이터로 초기화: {len(candles)}개 캔들")
        self.price_buffer.add_historical_candles(candles)
    
    def on_new_candle(self, candle: Dict):
        """
        새 캔들 수신시 호출
        
        Args:
            candle: {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        """
        if not self.price_buffer.is_initialized:
            print("⚠️ 버퍼 초기화 필요")
            return
        
        # EMA 업데이트
        self.price_buffer.update_with_new_candle(candle)
        
        # BarData 생성
        bar_data = self.price_buffer.get_bar_data(candle)
        if bar_data is None:
            return
        
        # 엔진 처리
        prev_position = self.engine.position
        prev_mode = self.engine.is_real_mode
        
        self.engine.on_bar(bar_data)
        
        # 포지션 변화 감지
        curr_position = self.engine.position
        curr_mode = self.engine.is_real_mode
        
        # 진입 감지
        if prev_position is None and curr_position is not None:
            self._on_entry(bar_data, curr_position)
        
        # 청산 감지
        if prev_position is not None and curr_position is None:
            self._on_exit(bar_data, self.engine.trades[-1] if self.engine.trades else None)
        
        # 모드 전환 감지
        if prev_mode != curr_mode:
            self._on_mode_switch(bar_data)
        
        self.last_processed_candle = candle
    
    def _on_entry(self, bar_data: BarData, position):
        """진입 발생"""
        print(f"\n{'='*50}")
        print(f"🟢 진입 시그널 발생!")
        print(f"   - 시간: {bar_data.timestamp}")
        print(f"   - 가격: ${bar_data.close:,.2f}")
        print(f"   - 모드: {self.engine._mode()}")
        print(f"{'='*50}\n")
        
        if not self.dry_run and self.engine.is_real_mode:
            self._execute_entry_order(bar_data.close)
        
        if self.on_signal_callback:
            self.on_signal_callback('ENTRY', bar_data, position)
    
    def _on_exit(self, bar_data: BarData, trade):
        """청산 발생"""
        pnl = trade.net_pnl if trade else 0
        print(f"\n{'='*50}")
        print(f"🔴 청산 시그널 발생!")
        print(f"   - 시간: {bar_data.timestamp}")
        print(f"   - 가격: ${bar_data.close:,.2f}")
        print(f"   - PnL: ${pnl:+,.2f}")
        print(f"   - 이유: {trade.reason_exit if trade else 'N/A'}")
        print(f"{'='*50}\n")
        
        if not self.dry_run and trade and trade.mode == "REAL":
            self._execute_exit_order(bar_data.close)
        
        if self.on_signal_callback:
            self.on_signal_callback('EXIT', bar_data, trade)
    
    def _on_mode_switch(self, bar_data: BarData):
        """모드 전환"""
        mode = self.engine._mode()
        print(f"\n{'='*50}")
        print(f"⚠️ 모드 전환!")
        print(f"   - 새 모드: {mode}")
        print(f"   - Real 자본: ${self.engine.real_capital:,.2f}")
        print(f"{'='*50}\n")
        
        if self.on_mode_switch_callback:
            self.on_mode_switch_callback(mode, self.engine.get_status())
    
    def _execute_entry_order(self, price: float):
        """실제 진입 주문 실행 (구현 필요)"""
        print(f"📤 [ORDER] LONG 진입 주문 @ ${price:,.2f}")
        # TODO: OKX API 연동
    
    def _execute_exit_order(self, price: float):
        """실제 청산 주문 실행 (구현 필요)"""
        print(f"📤 [ORDER] LONG 청산 주문 @ ${price:,.2f}")
        # TODO: OKX API 연동
    
    def get_status(self) -> Dict[str, Any]:
        """현재 상태"""
        return {
            'symbol': self.symbol,
            'dry_run': self.dry_run,
            'is_running': self.is_running,
            'buffer_initialized': self.price_buffer.is_initialized,
            'candle_count': len(self.price_buffer.candles),
            'engine_status': self.engine.get_status().to_dict(),
            'last_candle_time': self.last_processed_candle.get('timestamp') if self.last_processed_candle else None,
        }
    
    def get_debug_status(self) -> Dict[str, Any]:
        """디버그 상태"""
        return {
            **self.get_status(),
            'pipeline_status': self.engine.pipeline.get_status(),
            'recent_signals': self.engine.pipeline.get_recent_signals(5),
            'blocked_entries': self.engine.pipeline.get_blocked_entries(5),
            'ema_values': {
                'trend_fast': self.price_buffer.ema_trend_fast,
                'trend_slow': self.price_buffer.ema_trend_slow,
                'entry_fast': self.price_buffer.ema_entry_fast,
                'entry_slow': self.price_buffer.ema_entry_slow,
                'exit_fast': self.price_buffer.ema_exit_fast,
                'exit_slow': self.price_buffer.ema_exit_slow,
            }
        }
    
    def print_status(self):
        """상태 출력"""
        status = self.get_status()
        eng = status['engine_status']
        
        print(f"\n{'='*60}")
        print(f"📊 RealtimeTraderV2 Status - {self.symbol}")
        print(f"{'='*60}")
        print(f"모드: {eng['mode']} | Dry Run: {self.dry_run}")
        print(f"Real 자본: ${eng['real_capital']:,.2f} (peak: ${eng['real_peak']:,.2f})")
        print(f"Virtual 자본: ${eng['virtual_capital']:,.2f}")
        print(f"포지션: {'있음' if eng['has_position'] else '없음'}")
        print(f"거래 수: REAL={eng['real_trades']}, VIRTUAL={eng['virtual_trades']}")
        print(f"모드 전환: R→V={eng['mode_switches_r2v']}, V→R={eng['mode_switches_v2r']}")
        
        if self.price_buffer.is_initialized:
            print(f"\nEMA Values:")
            print(f"  Trend: {self.price_buffer.ema_trend_fast:.2f} / {self.price_buffer.ema_trend_slow:.2f}")
            print(f"  Entry: {self.price_buffer.ema_entry_fast:.2f} / {self.price_buffer.ema_entry_slow:.2f}")
            print(f"  Exit: {self.price_buffer.ema_exit_fast:.2f} / {self.price_buffer.ema_exit_slow:.2f}")
        
        print(f"{'='*60}\n")


# ===== 테스트용 시뮬레이터 =====

class RealtimeSimulator:
    """실시간 시뮬레이터 (테스트용)"""
    
    def __init__(self, trader: RealtimeTraderV2):
        self.trader = trader
        self.is_running = False
    
    def run_from_csv(self, csv_path: str, speed: float = 0.0):
        """
        CSV 데이터로 실시간 시뮬레이션
        
        Args:
            csv_path: CSV 파일 경로
            speed: 봉 간 딜레이 (초). 0이면 즉시 실행
        """
        from backtest_v2 import load_ohlc_csv, prepare_data_with_ema
        
        print(f"📂 시뮬레이션 데이터 로딩: {csv_path}")
        df = load_ohlc_csv(csv_path)
        df = prepare_data_with_ema(df, self.trader.params)
        
        # warmup 기간
        warmup = self.trader.params.trend_slow + 10
        
        # 히스토리로 초기화
        history_candles = []
        for i in range(warmup):
            row = df.iloc[i]
            history_candles.append({
                'timestamp': row['timestamp'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
            })
        
        self.trader.initialize_with_history(history_candles)
        
        # 시뮬레이션 실행
        print(f"\n🚀 시뮬레이션 시작: {len(df) - warmup}개 봉")
        self.is_running = True
        
        for i in range(warmup, len(df)):
            if not self.is_running:
                break
            
            row = df.iloc[i]
            candle = {
                'timestamp': row['timestamp'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
            }
            
            self.trader.on_new_candle(candle)
            
            if speed > 0:
                time.sleep(speed)
        
        print(f"\n✅ 시뮬레이션 완료")
        self.trader.print_status()
        self.trader.engine.print_summary()
    
    def stop(self):
        """시뮬레이션 중지"""
        self.is_running = False


# ===== 메인 =====

if __name__ == "__main__":
    import sys
    
    # 파라미터
    params = ParamsV2(
        enable_debug_logging=False,
        debug_log_interval=50,
    )
    
    # 트레이더 생성
    trader = RealtimeTraderV2(
        symbol="BTC-USDT-SWAP",
        params=params,
        initial_capital=10000.0,
        dry_run=True
    )
    
    # CSV로 시뮬레이션
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT_30m_20180101_to_now_utc.csv"
    
    simulator = RealtimeSimulator(trader)
    simulator.run_from_csv(csv_path, speed=0)
