# utils/data_generator.py
"""
데이터 생성 유틸

EMA 계산 및 전략용 데이터 생성
"""

from typing import Dict, Any, Optional
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """
    지수이동평균(EMA) 계산
    
    Args:
        series: 가격 시리즈
        period: EMA 기간
    
    Returns:
        EMA 시리즈
    """
    return series.ewm(span=period, adjust=False).mean()


def generate_strategy_data(df: pd.DataFrame, ema_periods: Dict[str, int]) -> Optional[Dict[str, Any]]:
    """
    DataFrame에서 전략용 데이터 생성
    
    Args:
        df: OHLCV DataFrame
        ema_periods: EMA 기간 딕셔너리
            - trend_fast: 트렌드용 빠른 EMA (기본: 150)
            - trend_slow: 트렌드용 느린 EMA (기본: 200)
            - entry_fast: 진입용 빠른 EMA (기본: 20)
            - entry_slow: 진입용 느린 EMA (기본: 50)
            - exit_fast: 청산용 빠른 EMA (기본: 20)
            - exit_slow: 청산용 느린 EMA (기본: 100)
    
    Returns:
        전략용 데이터 딕셔너리
    """
    if df is None or len(df) < 2:
        return None
    
    # 기본 EMA 기간
    trend_fast = ema_periods.get('trend_fast', 150)
    trend_slow = ema_periods.get('trend_slow', 200)
    entry_fast = ema_periods.get('entry_fast', 20)
    entry_slow = ema_periods.get('entry_slow', 50)
    exit_fast = ema_periods.get('exit_fast', 20)
    exit_slow = ema_periods.get('exit_slow', 100)
    
    # 최소 데이터 확인
    min_required = max(trend_fast, trend_slow, entry_fast, entry_slow, exit_fast, exit_slow) + 1
    if len(df) < min_required:
        return None
    
    close = df['close'].astype(float)
    
    # EMA 계산
    ema_trend_fast = ema(close, trend_fast)
    ema_trend_slow = ema(close, trend_slow)
    ema_entry_fast = ema(close, entry_fast)
    ema_entry_slow = ema(close, entry_slow)
    ema_exit_fast = ema(close, exit_fast)
    ema_exit_slow = ema(close, exit_slow)
    
    # 현재/이전 인덱스
    curr_idx = len(df) - 1
    prev_idx = len(df) - 2
    
    current_row = df.iloc[curr_idx]
    
    strategy_data = {
        # 기본 데이터
        'timestamp': current_row.get('timestamp'),
        'open': float(current_row.get('open', 0)),
        'high': float(current_row.get('high', 0)),
        'low': float(current_row.get('low', 0)),
        'close': float(current_row.get('close', 0)),
        'volume': float(current_row.get('volume', 0)) if 'volume' in current_row else 0,
        
        # 트렌드 EMA (현재)
        'ema_trend_fast': float(ema_trend_fast.iloc[curr_idx]),
        'ema_trend_slow': float(ema_trend_slow.iloc[curr_idx]),
        
        # 진입 EMA (현재/이전)
        'curr_entry_fast': float(ema_entry_fast.iloc[curr_idx]),
        'curr_entry_slow': float(ema_entry_slow.iloc[curr_idx]),
        'prev_entry_fast': float(ema_entry_fast.iloc[prev_idx]),
        'prev_entry_slow': float(ema_entry_slow.iloc[prev_idx]),
        
        # 청산 EMA (현재/이전)
        'curr_exit_fast': float(ema_exit_fast.iloc[curr_idx]),
        'curr_exit_slow': float(ema_exit_slow.iloc[curr_idx]),
        'prev_exit_fast': float(ema_exit_fast.iloc[prev_idx]),
        'prev_exit_slow': float(ema_exit_slow.iloc[prev_idx]),
    }
    
    return strategy_data


def convert_to_strategy_data(candle: Dict[str, Any], 
                             price_buffer,
                             ema_periods: Dict[str, int]) -> Optional[Dict[str, Any]]:
    """
    단일 캔들을 전략용 데이터로 변환
    
    PriceBuffer를 사용하여 히스토리와 함께 EMA 계산
    
    Args:
        candle: 캔들 데이터 딕셔너리
        price_buffer: PriceBuffer 객체
        ema_periods: EMA 기간 딕셔너리
    
    Returns:
        전략용 데이터 딕셔너리
    """
    if price_buffer is None:
        return None
    
    df = price_buffer.to_dataframe()
    if df is None:
        return None
    
    return generate_strategy_data(df, ema_periods)


def prepare_backtest_data(df: pd.DataFrame, ema_periods: Dict[str, int]) -> pd.DataFrame:
    """
    백테스트용 데이터 준비
    
    전체 DataFrame에 EMA 컬럼 추가
    
    Args:
        df: OHLCV DataFrame
        ema_periods: EMA 기간 딕셔너리
    
    Returns:
        EMA 컬럼이 추가된 DataFrame
    """
    df = df.copy()
    close = df['close'].astype(float)
    
    # 기본 EMA 기간
    trend_fast = ema_periods.get('trend_fast', 150)
    trend_slow = ema_periods.get('trend_slow', 200)
    entry_fast = ema_periods.get('entry_fast', 20)
    entry_slow = ema_periods.get('entry_slow', 50)
    exit_fast = ema_periods.get('exit_fast', 20)
    exit_slow = ema_periods.get('exit_slow', 100)
    
    # EMA 계산 및 추가
    df['ema_trend_fast'] = ema(close, trend_fast)
    df['ema_trend_slow'] = ema(close, trend_slow)
    df['ema_entry_fast'] = ema(close, entry_fast)
    df['ema_entry_slow'] = ema(close, entry_slow)
    df['ema_exit_fast'] = ema(close, exit_fast)
    df['ema_exit_slow'] = ema(close, exit_slow)
    
    return df


def row_to_strategy_data(df: pd.DataFrame, idx: int) -> Optional[Dict[str, Any]]:
    """
    DataFrame의 특정 행을 전략용 데이터로 변환
    
    prepare_backtest_data()로 준비된 DataFrame에서 사용
    
    Args:
        df: EMA 컬럼이 포함된 DataFrame
        idx: 행 인덱스
    
    Returns:
        전략용 데이터 딕셔너리
    """
    if idx < 1 or idx >= len(df):
        return None
    
    curr_row = df.iloc[idx]
    prev_row = df.iloc[idx - 1]
    
    return {
        'timestamp': curr_row.get('timestamp'),
        'close': float(curr_row['close']),
        
        'ema_trend_fast': float(curr_row['ema_trend_fast']),
        'ema_trend_slow': float(curr_row['ema_trend_slow']),
        
        'curr_entry_fast': float(curr_row['ema_entry_fast']),
        'curr_entry_slow': float(curr_row['ema_entry_slow']),
        'prev_entry_fast': float(prev_row['ema_entry_fast']),
        'prev_entry_slow': float(prev_row['ema_entry_slow']),
        
        'curr_exit_fast': float(curr_row['ema_exit_fast']),
        'curr_exit_slow': float(curr_row['ema_exit_slow']),
        'prev_exit_fast': float(prev_row['ema_exit_fast']),
        'prev_exit_slow': float(prev_row['ema_exit_slow']),
    }
