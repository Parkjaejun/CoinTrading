
def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()
