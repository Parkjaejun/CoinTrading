# utils/data_generator.py
"""
전략용 데이터 생성 유틸

WebSocket에서 받은 캔들 데이터를 전략에서 사용하는 형식으로 변환
"""

import pandas as pd
from typing import Dict, Any, Optional


def ema(series: pd.Series, period: int) -> pd.Series:
    """
    지수이동평균 계산
    
    Args:
        series: 가격 시리즈
        period: EMA 기간
    
    Returns:
        EMA 시리즈
    """
    return series.ewm(span=period, adjust=False).mean()


def generate_strategy_data(df: pd.DataFrame, ema_periods: Dict[str, int]) -> Optional[Dict[str, Any]]:
    """
    전략용 데이터 생성
    
    DataFrame에서 EMA를 계산하고 전략에서 사용하는 형식으로 변환
    
    Args:
        df: OHLCV DataFrame (timestamp, open, high, low, close 컬럼 필요)
        ema_periods: EMA 기간 딕셔너리
            - trend_fast: 트렌드 빠른 EMA (150)
            - trend_slow: 트렌드 느린 EMA (200)
            - entry_fast: 진입 빠른 EMA (20)
            - entry_slow: 진입 느린 EMA (50)
            - exit_fast: 청산 빠른 EMA (20)
            - exit_slow: 청산 느린 EMA (100)
    
    Returns:
        전략용 데이터 딕셔너리
    """
    if df is None or len(df) < 2:
        return None
    
    # 필요한 최소 데이터 길이
    max_period = max(ema_periods.values())
    if len(df) < max_period + 2:
        return None
    
    close = df['close'].astype(float)
    
    # EMA 계산
    ema_trend_fast = ema(close, ema_periods.get('trend_fast', 150))
    ema_trend_slow = ema(close, ema_periods.get('trend_slow', 200))
    ema_entry_fast = ema(close, ema_periods.get('entry_fast', 20))
    ema_entry_slow = ema(close, ema_periods.get('entry_slow', 50))
    ema_exit_fast = ema(close, ema_periods.get('exit_fast', 20))
    ema_exit_slow = ema(close, ema_periods.get('exit_slow', 100))
    
    # 현재 봉 (마지막)
    curr_idx = len(df) - 1
    prev_idx = len(df) - 2
    
    current_row = df.iloc[curr_idx]
    
    # 전략용 데이터 구성
    strategy_data = {
        # 기본 OHLCV
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
    
    # EMA 컬럼 추가
    df['ema_trend_fast'] = ema(close, ema_periods.get('trend_fast', 150))
    df['ema_trend_slow'] = ema(close, ema_periods.get('trend_slow', 200))
    df['ema_entry_fast'] = ema(close, ema_periods.get('entry_fast', 20))
    df['ema_entry_slow'] = ema(close, ema_periods.get('entry_slow', 50))
    df['ema_exit_fast'] = ema(close, ema_periods.get('exit_fast', 20))
    df['ema_exit_slow'] = ema(close, ema_periods.get('exit_slow', 100))
    
    return df


def row_to_strategy_data(row: pd.Series, prev_row: pd.Series) -> Dict[str, Any]:
    """
    DataFrame 행을 전략용 데이터로 변환
    
    백테스트에서 사용
    
    Args:
        row: 현재 행
        prev_row: 이전 행
    
    Returns:
        전략용 데이터 딕셔너리
    """
    return {
        'timestamp': row.get('timestamp'),
        'open': float(row.get('open', 0)),
        'high': float(row.get('high', 0)),
        'low': float(row.get('low', 0)),
        'close': float(row.get('close', 0)),
        
        'ema_trend_fast': float(row.get('ema_trend_fast', 0)),
        'ema_trend_slow': float(row.get('ema_trend_slow', 0)),
        
        'curr_entry_fast': float(row.get('ema_entry_fast', 0)),
        'curr_entry_slow': float(row.get('ema_entry_slow', 0)),
        'prev_entry_fast': float(prev_row.get('ema_entry_fast', 0)),
        'prev_entry_slow': float(prev_row.get('ema_entry_slow', 0)),
        
        'curr_exit_fast': float(row.get('ema_exit_fast', 0)),
        'curr_exit_slow': float(row.get('ema_exit_slow', 0)),
        'prev_exit_fast': float(prev_row.get('ema_exit_fast', 0)),
        'prev_exit_slow': float(prev_row.get('ema_exit_slow', 0)),
    }
