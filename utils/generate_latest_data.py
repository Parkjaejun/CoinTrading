import pandas as pd
from utils.indicators import calculate_ema

def generate_latest_data_for_dual_asset(df, ema_periods):
    """듀얼 자산 전략을 위한 최신 데이터 생성 (기존 함수 유지)"""
    if len(df) < max(ema_periods.values()) + 2:
        return None
    for key, period in ema_periods.items():
        df[f"ema_{key}"] = calculate_ema(df["close"], period)
    i = -1
    i_prev = -2
    return {
        "timestamp": pd.to_datetime(df["timestamp"].iloc[i]),
        "close": df["close"].iloc[i],
        "ema_A1": df["ema_A1"].iloc[i],
        "ema_A2": df["ema_A2"].iloc[i],
        "prev_B1": df["ema_B1"].iloc[i_prev],
        "prev_B2": df["ema_B2"].iloc[i_prev],
        "curr_B1": df["ema_B1"].iloc[i],
        "curr_B2": df["ema_B2"].iloc[i],
        "prev_C1": df["ema_C1"].iloc[i_prev],
        "prev_C2": df["ema_C2"].iloc[i_prev],
        "curr_C1": df["ema_C1"].iloc[i],
        "curr_C2": df["ema_C2"].iloc[i],
    }

def generate_strategy_data(df, ema_periods):
    """새로운 전략 시스템을 위한 데이터 생성"""
    if len(df) < max(ema_periods.values()) + 2:
        return None
    
    # 모든 EMA 계산
    for key, period in ema_periods.items():
        df[f"ema_{key}"] = calculate_ema(df["close"], period)
    
    # 최신 인덱스
    current_idx = -1
    previous_idx = -2
    
    # 기본 데이터
    data = {
        "timestamp": pd.to_datetime(df["timestamp"].iloc[current_idx]),
        "close": df["close"].iloc[current_idx],
    }
    
    # 트렌드 확인용 EMA (현재 값만 필요)
    data.update({
        "ema_trend_fast": df["ema_trend_fast"].iloc[current_idx],    # 150EMA
        "ema_trend_slow": df["ema_trend_slow"].iloc[current_idx],    # 200EMA
    })
    
    # 진입 신호용 EMA (현재 + 이전 값 필요)
    data.update({
        "ema_entry_fast": df["ema_entry_fast"].iloc[current_idx],     # 현재 20EMA
        "ema_entry_slow": df["ema_entry_slow"].iloc[current_idx],     # 현재 50EMA
        "prev_entry_fast": df["ema_entry_fast"].iloc[previous_idx],   # 이전 20EMA
        "prev_entry_slow": df["ema_entry_slow"].iloc[previous_idx],   # 이전 50EMA
    })
    
    # 롱 전략 청산용 EMA
    data.update({
        "ema_exit_fast_long": df["ema_exit_fast_long"].iloc[current_idx],     # 현재 20EMA
        "ema_exit_slow_long": df["ema_exit_slow_long"].iloc[current_idx],     # 현재 100EMA
        "prev_exit_fast_long": df["ema_exit_fast_long"].iloc[previous_idx],   # 이전 20EMA
        "prev_exit_slow_long": df["ema_exit_slow_long"].iloc[previous_idx],   # 이전 100EMA
    })
    
    # 숏 전략 청산용 EMA
    data.update({
        "ema_exit_fast_short": df["ema_exit_fast_short"].iloc[current_idx],    # 현재 100EMA
        "ema_exit_slow_short": df["ema_exit_slow_short"].iloc[current_idx],    # 현재 200EMA
        "prev_exit_fast_short": df["ema_exit_fast_short"].iloc[previous_idx],  # 이전 100EMA
        "prev_exit_slow_short": df["ema_exit_slow_short"].iloc[previous_idx],  # 이전 200EMA
    })
    
    return data

def validate_ema_data(data, required_emas):
    """EMA 데이터 유효성 검증"""
    missing_emas = []
    
    for ema_key in required_emas:
        if ema_key not in data or data[ema_key] is None:
            missing_emas.append(ema_key)
    
    if missing_emas:
        print(f"누락된 EMA 데이터: {missing_emas}")
        return False
    
    return True

def calculate_ema_crossovers(data):
    """EMA 크로스오버 감지"""
    crossovers = {}
    
    # 진입용 크로스오버 (20EMA vs 50EMA)
    if all(key in data for key in ['ema_entry_fast', 'ema_entry_slow', 'prev_entry_fast', 'prev_entry_slow']):
        prev_above = data['prev_entry_fast'] >= data['prev_entry_slow']
        curr_above = data['ema_entry_fast'] >= data['ema_entry_slow']
        
        if not prev_above and curr_above:
            crossovers['entry_golden_cross'] = True
        elif prev_above and not curr_above:
            crossovers['entry_dead_cross'] = True
    
    # 롱 청산용 크로스오버 (20EMA vs 100EMA)
    if all(key in data for key in ['ema_exit_fast_long', 'ema_exit_slow_long', 'prev_exit_fast_long', 'prev_exit_slow_long']):
        prev_above = data['prev_exit_fast_long'] >= data['prev_exit_slow_long']
        curr_above = data['ema_exit_fast_long'] >= data['ema_exit_slow_long']
        
        if prev_above and not curr_above:
            crossovers['long_exit_dead_cross'] = True
    
    # 숏 청산용 크로스오버 (100EMA vs 200EMA)
    if all(key in data for key in ['ema_exit_fast_short', 'ema_exit_slow_short', 'prev_exit_fast_short', 'prev_exit_slow_short']):
        prev_above = data['prev_exit_fast_short'] >= data['prev_exit_slow_short']
        curr_above = data['ema_exit_fast_short'] >= data['ema_exit_slow_short']
        
        if not prev_above and curr_above:
            crossovers['short_exit_golden_cross'] = True
    
    # 트렌드 확인용 (150EMA vs 200EMA)
    if all(key in data for key in ['ema_trend_fast', 'ema_trend_slow']):
        if data['ema_trend_fast'] > data['ema_trend_slow']:
            crossovers['uptrend'] = True
        else:
            crossovers['downtrend'] = True
    
    return crossovers

def print_data_summary(data):
    """데이터 요약 정보 출력 (디버깅용)"""
    print(f"\n=== 데이터 요약 ({data.get('timestamp', 'N/A')}) ===")
    print(f"현재가: {data.get('close', 0):.2f}")
    
    # 트렌드 EMA
    print(f"트렌드: 150EMA({data.get('ema_trend_fast', 0):.2f}) vs 200EMA({data.get('ema_trend_slow', 0):.2f})")
    
    # 진입 EMA
    print(f"진입: 20EMA({data.get('prev_entry_fast', 0):.2f}→{data.get('ema_entry_fast', 0):.2f}) vs 50EMA({data.get('prev_entry_slow', 0):.2f}→{data.get('ema_entry_slow', 0):.2f})")
    
    # 청산 EMA
    print(f"롱청산: 20EMA({data.get('prev_exit_fast_long', 0):.2f}→{data.get('ema_exit_fast_long', 0):.2f}) vs 100EMA({data.get('prev_exit_slow_long', 0):.2f}→{data.get('ema_exit_slow_long', 0):.2f})")
    print(f"숏청산: 100EMA({data.get('prev_exit_fast_short', 0):.2f}→{data.get('ema_exit_fast_short', 0):.2f}) vs 200EMA({data.get('prev_exit_slow_short', 0):.2f}→{data.get('ema_exit_slow_short', 0):.2f})")
    
    # 크로스오버 감지
    crossovers = calculate_ema_crossovers(data)
    if crossovers:
        print(f"크로스오버: {list(crossovers.keys())}")
    
    print("=" * 50)