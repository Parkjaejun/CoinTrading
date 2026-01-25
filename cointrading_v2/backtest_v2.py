# backtest_v2.py
"""
CoinTrading v2 백테스트 모듈
- CSV 데이터 로딩
- EMA 계산
- 백테스트 실행
- 결과 분석 및 시각화
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from config_v2 import ParamsV2, EmailConfig
from models import BarData, Trade
from trading_engine_v2 import TradingEngineV2
from email_notifier import EmailNotifier, MockEmailNotifier


# ===== 유틸리티 함수 =====

def ema(series: pd.Series, period: int) -> pd.Series:
    """EMA 계산"""
    return series.ewm(span=period, adjust=False).mean()


def calc_mdd(equity_curve: List[float]) -> float:
    """MDD 계산 (비율)"""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def calc_sharpe(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """샤프 비율 계산"""
    if not returns or len(returns) < 2:
        return 0.0
    returns_arr = np.array(returns)
    excess_returns = returns_arr - risk_free_rate
    if np.std(excess_returns) == 0:
        return 0.0
    return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)


def calc_win_rate(trades: List[Trade]) -> float:
    """승률 계산"""
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.net_pnl > 0)
    return wins / len(trades) * 100


def calc_profit_factor(trades: List[Trade]) -> float:
    """이익 팩터 계산"""
    if not trades:
        return 0.0
    gross_profit = sum(t.net_pnl for t in trades if t.net_pnl > 0)
    gross_loss = abs(sum(t.net_pnl for t in trades if t.net_pnl < 0))
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


# ===== CSV 로더 =====

def load_ohlc_csv(csv_path: str) -> pd.DataFrame:
    """OHLC CSV 파일 로드"""
    df = pd.read_csv(csv_path)
    
    # 컬럼명 정규화
    colmap = {}
    for c in df.columns:
        lc = c.lower().strip()
        if lc in ["timestamp", "time", "datetime", "date"]:
            colmap[c] = "timestamp"
        elif lc in ["open", "open_"]:
            colmap[c] = "open"
        elif lc in ["high", "high_"]:
            colmap[c] = "high"
        elif lc in ["low", "low_"]:
            colmap[c] = "low"
        elif lc in ["close", "close_"]:
            colmap[c] = "close"
        elif lc in ["volume", "vol"]:
            colmap[c] = "volume"
    
    df = df.rename(columns=colmap)
    
    # 필수 컬럼 확인
    required = ["timestamp", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV에 필요한 컬럼이 없습니다. missing={missing}")
    
    # 타임스탬프 파싱
    ts = df["timestamp"]
    if pd.api.types.is_numeric_dtype(ts):
        med = ts.dropna().astype(float).median()
        if med > 1e12:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        else:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    
    return df


def prepare_data_with_ema(df: pd.DataFrame, params: ParamsV2) -> pd.DataFrame:
    """EMA 컬럼 추가"""
    df = df.copy()
    close = df["close"].astype(float)
    
    df["ema_trend_fast"] = ema(close, params.trend_fast)
    df["ema_trend_slow"] = ema(close, params.trend_slow)
    df["ema_entry_fast"] = ema(close, params.entry_fast)
    df["ema_entry_slow"] = ema(close, params.entry_slow)
    df["ema_exit_fast"] = ema(close, params.exit_fast)
    df["ema_exit_slow"] = ema(close, params.exit_slow)
    
    return df


# ===== 백테스트 클래스 =====

class BacktestV2:
    """v2 백테스트 실행기"""
    
    def __init__(self, 
                 params: ParamsV2 = None,
                 initial_capital: float = 10000.0,
                 symbol: str = "BTC-USDT-SWAP",
                 use_mock_email: bool = True):
        self.params = params or ParamsV2()
        self.initial_capital = initial_capital
        self.symbol = symbol
        self.use_mock_email = use_mock_email
        
        self.engine: Optional[TradingEngineV2] = None
        self.df: Optional[pd.DataFrame] = None
        self.results: Dict[str, Any] = {}
    
    def load_data(self, csv_path: str) -> pd.DataFrame:
        """데이터 로드 및 전처리"""
        print(f"📂 데이터 로딩: {csv_path}")
        df = load_ohlc_csv(csv_path)
        print(f"   - 로드된 봉 수: {len(df)}")
        print(f"   - 기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
        
        df = prepare_data_with_ema(df, self.params)
        self.df = df
        return df
    
    def run(self, csv_path: str = None, df: pd.DataFrame = None, 
            print_trades: bool = False, quiet: bool = False) -> Dict[str, Any]:
        """백테스트 실행"""
        if df is not None:
            self.df = df
        elif csv_path is not None:
            self.load_data(csv_path)
        
        if self.df is None:
            raise ValueError("데이터가 필요합니다.")
        
        df = self.df
        
        # 시작 인덱스
        start_idx = max(
            self.params.trend_slow,
            self.params.entry_slow,
            self.params.exit_slow
        ) + 2
        
        if len(df) <= start_idx:
            raise ValueError(f"데이터가 너무 짧습니다. 최소 {start_idx+1}개 봉 필요")
        
        # 엔진 초기화
        params = self.params
        if quiet:
            params = ParamsV2(**{k: v for k, v in self.params.__dict__.items()})
            params.enable_debug_logging = False
        
        self.engine = TradingEngineV2(
            params=params,
            symbol=self.symbol,
            use_mock_email=self.use_mock_email
        )
        self.engine.init_capital(self.initial_capital)
        
        if not quiet:
            print(f"\n🚀 백테스트 시작")
            print(f"   - 초기 자본: ${self.initial_capital:,.2f}")
            print(f"   - 테스트 봉 수: {len(df) - start_idx}")
        
        # 메인 루프
        for i in range(start_idx, len(df)):
            prev = df.iloc[i - 1]
            row = df.iloc[i]
            
            bar_data = BarData(
                timestamp=row["timestamp"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                ema_trend_fast=float(row["ema_trend_fast"]),
                ema_trend_slow=float(row["ema_trend_slow"]),
                ema_entry_fast=float(row["ema_entry_fast"]),
                ema_entry_slow=float(row["ema_entry_slow"]),
                ema_exit_fast=float(row["ema_exit_fast"]),
                ema_exit_slow=float(row["ema_exit_slow"]),
                prev_entry_fast=float(prev["ema_entry_fast"]),
                prev_entry_slow=float(prev["ema_entry_slow"]),
                prev_exit_fast=float(prev["ema_exit_fast"]),
                prev_exit_slow=float(prev["ema_exit_slow"]),
            )
            
            self.engine.on_bar(bar_data)
        
        self.results = self._calculate_results()
        
        if not quiet:
            self.print_results(print_trades=print_trades)
        
        return self.results
    
    def _calculate_results(self) -> Dict[str, Any]:
        """결과 계산"""
        eng = self.engine
        
        real_trades = [t for t in eng.trades if t.mode == "REAL"]
        virtual_trades = [t for t in eng.trades if t.mode == "VIRTUAL"]
        
        real_roi = (eng.real_capital - self.initial_capital) / self.initial_capital * 100
        real_mdd = calc_mdd(eng.equity_history_real) * 100
        
        real_win_rate = calc_win_rate(real_trades)
        real_profit_factor = calc_profit_factor(real_trades)
        
        total_win_rate = calc_win_rate(eng.trades)
        total_profit_factor = calc_profit_factor(eng.trades)
        
        real_wins = [t.net_pnl for t in real_trades if t.net_pnl > 0]
        real_losses = [t.net_pnl for t in real_trades if t.net_pnl < 0]
        avg_win = np.mean(real_wins) if real_wins else 0
        avg_loss = np.mean(real_losses) if real_losses else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': eng.real_capital,
            'real_roi_pct': real_roi,
            'real_mdd_pct': real_mdd,
            'real_trade_count': len(real_trades),
            'real_win_rate_pct': real_win_rate,
            'real_profit_factor': real_profit_factor,
            'real_avg_win': avg_win,
            'real_avg_loss': avg_loss,
            'virtual_trade_count': len(virtual_trades),
            'total_trade_count': len(eng.trades),
            'total_win_rate_pct': total_win_rate,
            'total_profit_factor': total_profit_factor,
            'mode_switch_r2v': eng.cnt_r2v,
            'mode_switch_v2r': eng.cnt_v2r,
            'final_mode': eng._mode(),
            'bar_count': eng.bar_count,
            'has_open_position': eng.position is not None,
            'equity_history_real': eng.equity_history_real,
            'equity_history_virtual': eng.equity_history_virtual,
            'trades': eng.trades,
            'mode_switches': eng.mode_switches,
        }
    
    def print_results(self, print_trades: bool = False):
        """결과 출력"""
        r = self.results
        
        print(f"\n{'='*70}")
        print(f"📊 CoinTrading v2 백테스트 결과")
        print(f"{'='*70}")
        
        print(f"\n[자본 변화]")
        print(f"  초기 자본: ${r['initial_capital']:,.2f}")
        print(f"  최종 자본: ${r['final_capital']:,.2f}")
        print(f"  수익률: {r['real_roi_pct']:+.2f}%")
        print(f"  MDD: -{r['real_mdd_pct']:.2f}%")
        
        print(f"\n[REAL 거래 성과]")
        print(f"  거래 횟수: {r['real_trade_count']}")
        print(f"  승률: {r['real_win_rate_pct']:.1f}%")
        print(f"  이익팩터: {r['real_profit_factor']:.2f}")
        print(f"  평균 수익: ${r['real_avg_win']:+,.2f}")
        print(f"  평균 손실: ${r['real_avg_loss']:,.2f}")
        
        print(f"\n[VIRTUAL 거래]")
        print(f"  거래 횟수: {r['virtual_trade_count']}")
        
        print(f"\n[모드 전환]")
        print(f"  REAL → VIRTUAL: {r['mode_switch_r2v']}회")
        print(f"  VIRTUAL → REAL: {r['mode_switch_v2r']}회")
        print(f"  최종 모드: {r['final_mode']}")
        
        print(f"\n[기타]")
        print(f"  처리된 봉: {r['bar_count']}")
        print(f"  미청산 포지션: {'있음' if r['has_open_position'] else '없음'}")
        
        if self.engine:
            self.engine.pipeline.print_debug_summary()
        
        if print_trades and r['trades']:
            print(f"\n[전체 거래 내역]")
            print("-" * 100)
            for idx, t in enumerate(r['trades'], 1):
                emoji = "💰" if t.net_pnl > 0 else "📉"
                print(f"[{idx:04d}] {emoji} [{t.mode}] "
                      f"{t.entry_time} @ ${t.entry_price:,.2f} → "
                      f"{t.exit_time} @ ${t.exit_price:,.2f} | "
                      f"PnL: ${t.net_pnl:+,.2f} | {t.reason_exit}")
        
        print(f"\n{'='*70}")
    
    def get_equity_dataframe(self) -> pd.DataFrame:
        """Equity curve DataFrame"""
        if not self.results:
            raise ValueError("먼저 run()을 실행하세요.")
        return pd.DataFrame({
            'real_equity': self.results['equity_history_real'],
            'virtual_equity': self.results['equity_history_virtual'],
        })
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """거래 내역 DataFrame"""
        if not self.results:
            raise ValueError("먼저 run()을 실행하세요.")
        trades = self.results['trades']
        if not trades:
            return pd.DataFrame()
        return pd.DataFrame([t.to_dict() for t in trades])


def run_backtest(
    csv_path: str,
    initial_capital: float = 10000.0,
    params: ParamsV2 = None,
    print_trades: bool = True,
    quiet: bool = False,
) -> Dict[str, Any]:
    """간편 백테스트 실행"""
    bt = BacktestV2(
        params=params or ParamsV2(),
        initial_capital=initial_capital,
        use_mock_email=True
    )
    return bt.run(csv_path=csv_path, print_trades=print_trades, quiet=quiet)


if __name__ == "__main__":
    import sys
    
    csv_path = "BTCUSDT_30m_20180101_to_now_utc.csv"
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    
    params = ParamsV2(
        enable_debug_logging=False,
        debug_log_interval=100,
    )
    
    results = run_backtest(
        csv_path=csv_path,
        initial_capital=10000.0,
        params=params,
        print_trades=True,
        quiet=False
    )
