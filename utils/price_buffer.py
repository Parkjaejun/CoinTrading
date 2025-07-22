
from collections import deque
import pandas as pd

class PriceBuffer:
    def __init__(self, maxlen=200):
        self.buffer = deque(maxlen=maxlen)

    def add_candle(self, candle_dict):
        self.buffer.append(candle_dict)

    def to_dataframe(self):
        if len(self.buffer) < 3:
            return None
        return pd.DataFrame(self.buffer)
