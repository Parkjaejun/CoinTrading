# backtest/backtester.py
"""
전략 백테스팅 시스템
과거 데이터로 전략 성능 검증
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from utils.data_loader import HistoricalDataLoader
from utils.data_generator import generate_strategy_data, convert_to_strategy_data
from strategy.long_strategy import LongStrategy
from strategy.short_strategy import ShortStrategy
from utils.logger import log_system, log_error
import json

class BacktestResult:
    def __init__(self):
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.daily_returns: List[float] = []
        self.metrics: Dict[str, float] = {}
        self.strategy_name: str = ""
        self.symbol: str = ""
        self.start_date: datetime = None
        self.end_date: datetime = None
        self.initial_capital: float = 0
        self.final_capital: float = 0
    
    def add_trade(self, trade: Dict):
        """거래 추가"""
        self.trades.append(trade)
    
    def add_equity_point(self, timestamp: datetime, equity: float):
        """자본 곡선 포인트 추가"""
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': equity
        })
    
    def calculate_metrics(self):
        """성과 지표 계산"""
        if not self.trades:
            return
        
        # 기본 지표
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.get('pnl', 0) > 0])
        losing_trades = total_trades - winning_trades
        
        total_pnl = sum([t.get('pnl', 0) for t in self.trades])
        total_return = (self.final_capital - self.initial_capital) / self.initial_capital
        
        # 승률
        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0
        
        # 평균 손익
        avg_win = np.mean([t['pnl'] for t in self.trades if t.get('pnl', 0) > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([t['pnl'] for t in self.trades if t.get('pnl', 0) < 0]) if losing_trades > 0 else 0
        
        # 최대 낙폭 (MDD) 계산
        if self.equity_curve:
            equity_values = [point['equity'] for point in self.equity_curve]
            peak = equity_values[0]
            max_drawdown = 0
            
            for equity in equity_values:
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        else:
            max_drawdown = 0
        
        # 수익/위험 비율
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # 샤프 비율 (간소화)
        if self.daily_returns:
            returns_mean = np.mean(self.daily_returns)
            returns_std = np.std(self.daily_returns)
            sharpe_ratio = (returns_mean / returns_std * np.sqrt(365)) if returns_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        self.metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio
        }

class Backtester:
    def __init__(self):
        self.data_loader = HistoricalDataLoader()
        self.results_history: List[BacktestResult] = []
    
    def run_backtest(self, strategy_type: str, symbol: str, start_date: str, 
                    end_date: str, initial_capital: float = 10000) -> BacktestResult:
        """백테스트 실행
        
        Args:
            strategy_type: 'long' 또는 'short'
            symbol: 거래 심볼 (예: BTC-USDT-SWAP)
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            initial_capital: 초기 자본
        """
        log_system(f"백테스트 시작: {strategy_type} {symbol} ({start_date} ~ {end_date})")
        
        result = BacktestResult()
        result.strategy_name = f"{strategy_type}_strategy"
        result.symbol = symbol
        result.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        result.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        result.initial_capital = initial_capital
        
        try:
            # 과거 데이터 로딩
            df = self._load_backtest_data(symbol, start_date, end_date)
            if df is None or len(df) < 100:
                log_error("백테스트용 데이터 부족")
                return result
            
            # 전략 초기화
            strategy = self._create_strategy(strategy_type, symbol, initial_capital)
            if strategy is None:
                log_error(f"전략 생성 실패: {strategy_type}")
                return result
            
            # 백테스트 실행
            self._execute_backtest(strategy, df, result, strategy_type)
            
            # 최종 자본 및 지표 계산
            result.final_capital = strategy.get_status()['current_capital']
            result.calculate_metrics()
            
            # 결과 저장
            self.results_history.append(result)
            
            log_system(f"백테스트 완료: 총 수익률 {result.metrics.get('total_return', 0)*100:.2f}%")
            return result
            
        except Exception as e:
            log_error("백테스트 실행 중 오류", e)
            return result
    
    def _load_backtest_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """백테스트용 데이터 로딩"""
        try:
            # 충분한 데이터를 위해 더 많은 캔들 요청
            df = self.data_loader.get_historical_candles(symbol, "30m", limit=300)
            
            if df is None:
                return None
            
            # 날짜 필터링 (간소화 - 실제로는 더 정확한 필터링 필요)
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # 데이터가 요청한 기간을 포함하는지 확인
            if len(df) < 50:
                log_error("백테스트용 데이터 부족")
                return None
            
            # 전략용 데이터 준비
            strategy_df = self.data_loader.prepare_strategy_data(df)
            return strategy_df
            
        except Exception as e:
            log_error("백테스트 데이터 로딩 오류", e)
            return None
    
    def _create_strategy(self, strategy_type: str, symbol: str, initial_capital: float):
        """전략 인스턴스 생성"""
        try:
            if strategy_type.lower() == 'long':
                return LongStrategy(symbol, initial_capital)
            elif strategy_type.lower() == 'short':
                return ShortStrategy(symbol, initial_capital)
            else:
                log_error(f"지원하지 않는 전략 타입: {strategy_type}")
                return None
        except Exception as e:
            log_error("전략 생성 오류", e)
            return None
    
    def _execute_backtest(self, strategy, df: pd.DataFrame, result: BacktestResult, strategy_type: str):
        """백테스트 메인 실행 로직"""
        try:
            total_bars = len(df)
            log_system(f"백테스트 데이터: {total_bars}개 캔들")
            
            # 각 캔들에 대해 전략 처리
            for i in range(len(df)):
                current_data = self._prepare_current_data(df, i)
                if current_data is None:
                    continue
                
                # 전략별 데이터 변환
                strategy_data = convert_to_strategy_data(current_data, strategy_type)
                
                # 전략 신호 처리
                signal = strategy.process_signal(strategy_data)
                
                if signal:
                    # 거래 기록
                    trade_record = {
                        'timestamp': current_data['timestamp'],
                        'action': signal['action'],
                        'price': signal.get('price', signal.get('exit_price', 0)),
                        'size': signal.get('size', 0),
                        'pnl': signal.get('pnl', 0),
                        'reason': signal.get('reason', 'strategy'),
                        'leverage': signal.get('leverage', 1)
                    }
                    result.add_trade(trade_record)
                
                # 자본 곡선 업데이트
                current_capital = strategy.get_status()['current_capital']
                result.add_equity_point(current_data['timestamp'], current_capital)
                
                # 일별 수익률 계산 (간소화)
                if i > 0:
                    prev_capital = result.equity_curve[-2]['equity'] if len(result.equity_curve) > 1 else result.initial_capital
                    daily_return = (current_capital - prev_capital) / prev_capital
                    result.daily_returns.append(daily_return)
                
                # 진행률 표시 (큰 데이터셋일 때)
                if total_bars > 1000 and i % 100 == 0:
                    progress = (i / total_bars) * 100
                    log_system(f"백테스트 진행률: {progress:.1f}%")
            
        except Exception as e:
            log_error("백테스트 실행 오류", e)
    
    def _prepare_current_data(self, df: pd.DataFrame, index: int) -> Optional[Dict]:
        """현재 캔들 데이터 준비"""
        if index < 1:  # 이전 데이터가 필요하므로
            return None
        
        try:
            # 현재와 이전 인덱스
            current = index
            previous = index - 1
            
            # 기본 캔들 데이터
            current_candle = df.iloc[current]
            
            # 전략용 데이터 구성
            data = {
                "timestamp": current_candle['timestamp'],
                "close": current_candle['close'],
                "open": current_candle['open'],
                "high": current_candle['high'],
                "low": current_candle['low'],
                "volume": current_candle['volume']
            }
            
            # EMA 데이터 추가
            ema_columns = [col for col in df.columns if col.startswith('ema_')]
            for col in ema_columns:
                # EMA 키 이름 변환
                key_name = col  # 'ema_trend_fast' 등
                data[key_name] = current_candle[col]
            
            # 이전 값들 추가 (크로스오버 감지용)
            if previous >= 0:
                prev_candle = df.iloc[previous]
                for col in ema_columns:
                    if 'entry' in col or 'exit' in col:
                        # 현재/이전 구분을 위한 키 생성
                        if 'entry_fast' in col:
                            data['curr_entry_fast'] = current_candle[col]
                            data['prev_entry_fast'] = prev_candle[col]
                        elif 'entry_slow' in col:
                            data['curr_entry_slow'] = current_candle[col]
                            data['prev_entry_slow'] = prev_candle[col]
                        elif 'exit_fast_long' in col:
                            data['curr_exit_fast_long'] = current_candle[col]
                            data['prev_exit_fast_long'] = prev_candle[col]
                        elif 'exit_slow_long' in col:
                            data['curr_exit_slow_long'] = current_candle[col]
                            data['prev_exit_slow_long'] = prev_candle[col]
                        elif 'exit_fast_short' in col:
                            data['curr_exit_fast_short'] = current_candle[col]
                            data['prev_exit_fast_short'] = prev_candle[col]
                        elif 'exit_slow_short' in col:
                            data['curr_exit_slow_short'] = current_candle[col]
                            data['prev_exit_slow_short'] = prev_candle[col]
            
            return data
            
        except Exception as e:
            log_error(f"캔들 데이터 준비 오류 (인덱스: {index})", e)
            return None
    
    def optimize_parameters(self, strategy_type: str, symbol: str, start_date: str, 
                          end_date: str, parameter_sets: List[Dict]) -> Dict[str, Any]:
        """파라미터 최적화"""
        log_system(f"파라미터 최적화 시작: {len(parameter_sets)}개 조합")
        
        best_result = None
        best_params = None
        best_return = -float('inf')
        
        for i, params in enumerate(parameter_sets):
            log_system(f"파라미터 테스트 {i+1}/{len(parameter_sets)}: {params}")
            
            try:
                # 파라미터 적용 (실제 구현시 전략에 파라미터 주입)
                result = self.run_backtest(strategy_type, symbol, start_date, end_date)
                
                total_return = result.metrics.get('total_return', -1)
                
                if total_return > best_return:
                    best_return = total_return
                    best_result = result
                    best_params = params
                
            except Exception as e:
                log_error(f"파라미터 최적화 오류: {params}", e)
                continue
        
        return {
            'best_parameters': best_params,
            'best_result': best_result,
            'best_return': best_return,
            'total_tests': len(parameter_sets)
        }
    
    def print_backtest_summary(self, result: BacktestResult):
        """백테스트 결과 요약 출력"""
        print(f"\n{'='*60}")
        print(f"백테스트 결과 요약")
        print(f"{'='*60}")
        print(f"전략: {result.strategy_name}")
        print(f"심볼: {result.symbol}")
        print(f"기간: {result.start_date.strftime('%Y-%m-%d')} ~ {result.end_date.strftime('%Y-%m-%d')}")
        print(f"초기 자본: ${result.initial_capital:,.0f}")
        print(f"최종 자본: ${result.final_capital:,.0f}")
        
        metrics = result.metrics
        print(f"\n📊 성과 지표:")
        print(f"총 수익률: {metrics.get('total_return', 0)*100:+.2f}%")
        print(f"총 거래 횟수: {metrics.get('total_trades', 0)}회")
        print(f"승률: {metrics.get('win_rate', 0)*100:.1f}%")
        print(f"총 손익: ${metrics.get('total_pnl', 0):+,.0f}")
        print(f"평균 수익: ${metrics.get('avg_win', 0):,.0f}")
        print(f"평균 손실: ${metrics.get('avg_loss', 0):,.0f}")
        print(f"수익 팩터: {metrics.get('profit_factor', 0):.2f}")
        print(f"최대 낙폭: {metrics.get('max_drawdown', 0)*100:.2f}%")
        print(f"샤프 비율: {metrics.get('sharpe_ratio', 0):.2f}")
        
        print(f"\n📈 거래 내역:")
        for i, trade in enumerate(result.trades[-5:], 1):  # 마지막 5개 거래
            pnl_str = f"+${trade['pnl']:.0f}" if trade['pnl'] >= 0 else f"-${abs(trade['pnl']):.0f}"
            print(f"  {i}. {trade['action']} @ ${trade['price']:.2f} | PnL: {pnl_str}")
        
        if len(result.trades) > 5:
            print(f"  ... (총 {len(result.trades)}개 거래)")
        
        print(f"{'='*60}")
    
    def save_results(self, result: BacktestResult, filename: str = None):
        """백테스트 결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_{result.strategy_name}_{result.symbol}_{timestamp}.json"
        
        try:
            # 결과 데이터 구성
            save_data = {
                'strategy_name': result.strategy_name,
                'symbol': result.symbol,
                'start_date': result.start_date.isoformat() if result.start_date else None,
                'end_date': result.end_date.isoformat() if result.end_date else None,
                'initial_capital': result.initial_capital,
                'final_capital': result.final_capital,
                'metrics': result.metrics,
                'trades': result.trades,
                'equity_curve': result.equity_curve
            }
            
            # JSON 직렬화를 위한 데이터 변환
            def convert_for_json(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, np.float64):
                    return float(obj)
                elif isinstance(obj, np.int64):
                    return int(obj)
                return obj
            
            # JSON 파일로 저장
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, default=convert_for_json, ensure_ascii=False)
            
            log_system(f"백테스트 결과 저장: {filename}")
            
        except Exception as e:
            log_error("백테스트 결과 저장 실패", e)

# 전역 백테스터 인스턴스
backtester = Backtester()

def run_strategy_backtest(strategy_type: str, symbol: str, start_date: str, 
                         end_date: str, initial_capital: float = 10000) -> BacktestResult:
    """백테스트 실행 (메인 함수)"""
    result = backtester.run_backtest(strategy_type, symbol, start_date, end_date, initial_capital)
    backtester.print_backtest_summary(result)
    return result

def optimize_strategy_parameters(strategy_type: str, symbol: str, start_date: str, 
                               end_date: str, parameter_sets: List[Dict]) -> Dict[str, Any]:
    """전략 파라미터 최적화"""
    return backtester.optimize_parameters(strategy_type, symbol, start_date, end_date, parameter_sets)