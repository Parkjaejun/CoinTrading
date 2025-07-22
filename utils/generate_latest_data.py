
import pandas as pd
from utils.indicators import calculate_ema

def generate_latest_data_for_dual_asset(df, ema_periods):
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
