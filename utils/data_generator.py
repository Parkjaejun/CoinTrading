"""
단순화된 데이터 생성 유틸리티
복잡한 데이터 변환 없이 필수 기능만 제공
"""

import pandas as pd
from utils.indicators import calculate_ema
from config import EMA_PERIODS

def generate_strategy_data(df, ema_periods=None):
    """전략용 데이터 생성 (WebSocket에서 호출)"""
    if ema_periods is None:
        ema_periods = EMA_PERIODS
        
    if len(df) < max(ema_periods.values()) + 2:
        return None
    
    # 모든 EMA 계산
    for key, period in ema_periods.items():
        df[f"ema_{key}"] = calculate_ema(df["close"], period)
    
    # 최신/이전 인덱스
    current = -1
    previous = -2
    
    # 기본 데이터
    data = {
        "timestamp": pd.to_datetime(df["timestamp"].iloc[current]),
        "close": df["close"].iloc[current],
        # 트렌드 확인용
        "ema_trend_fast": df["ema_trend_fast"].iloc[current],
        "ema_trend_slow": df["ema_trend_slow"].iloc[current],
        # 진입용 (현재 + 이전)
        "curr_entry_fast": df["ema_entry_fast"].iloc[current],
        "curr_entry_slow": df["ema_entry_slow"].iloc[current],
        "prev_entry_fast": df["ema_entry_fast"].iloc[previous],
        "prev_entry_slow": df["ema_entry_slow"].iloc[previous],
        # 롱 청산용
        "curr_exit_fast_long": df["ema_exit_fast_long"].iloc[current],
        "curr_exit_slow_long": df["ema_exit_slow_long"].iloc[current],
        "prev_exit_fast_long": df["ema_exit_fast_long"].iloc[previous],
        "prev_exit_slow_long": df["ema_exit_slow_long"].iloc[previous],
        # 숏 청산용
        "curr_exit_fast_short": df["ema_exit_fast_short"].iloc[current],
        "curr_exit_slow_short": df["ema_exit_slow_short"].iloc[current],
        "prev_exit_fast_short": df["ema_exit_fast_short"].iloc[previous],
        "prev_exit_slow_short": df["ema_exit_slow_short"].iloc[previous],
    }
    
    return data

def convert_to_strategy_data(raw_data, strategy_type):
    """전략별 데이터 변환"""
    # 기본 데이터 복사
    strategy_data = dict(raw_data)
    
    # 전략별 exit EMA 매핑
    if strategy_type == 'long':
        strategy_data['curr_exit_fast'] = raw_data.get('curr_exit_fast_long')
        strategy_data['curr_exit_slow'] = raw_data.get('curr_exit_slow_long')
        strategy_data['prev_exit_fast'] = raw_data.get('prev_exit_fast_long')
        strategy_data['prev_exit_slow'] = raw_data.get('prev_exit_slow_long')
    else:  # short
        strategy_data['curr_exit_fast'] = raw_data.get('curr_exit_fast_short')
        strategy_data['curr_exit_slow'] = raw_data.get('curr_exit_slow_short')
        strategy_data['prev_exit_fast'] = raw_data.get('prev_exit_fast_short')
        strategy_data['prev_exit_slow'] = raw_data.get('prev_exit_slow_short')
    
    return strategy_data

def validate_data(data):
    """데이터 유효성 검증"""
    required_fields = [
        'close', 'ema_trend_fast', 'ema_trend_slow',
        'curr_entry_fast', 'curr_entry_slow', 
        'prev_entry_fast', 'prev_entry_slow'
    ]
    
    for field in required_fields:
        if field not in data or data[field] is None:
            return False
    
    return True

def detect_crossovers(data):
    """크로스오버 감지 (디버깅용)"""
    crossovers = []
    
    # 진입용 크로스오버
    if all(k in data for k in ['curr_entry_fast', 'curr_entry_slow', 'prev_entry_fast', 'prev_entry_slow']):
        prev_above = data['prev_entry_fast'] >= data['prev_entry_slow']
        curr_above = data['curr_entry_fast'] >= data['curr_entry_slow']
        
        if not prev_above and curr_above:
            crossovers.append('entry_golden_cross')
        elif prev_above and not curr_above:
            crossovers.append('entry_dead_cross')
    
    # 트렌드 확인
    if data.get('ema_trend_fast', 0) > data.get('ema_trend_slow', 0):
        crossovers.append('uptrend')
    else:
        crossovers.append('downtrend')
    
    return crossovers