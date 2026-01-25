# utils/price_buffer.py
"""
가격 데이터 버퍼

실시간 캔들 데이터를 저장하고 DataFrame으로 변환
"""

from collections import deque
from typing import Dict, Any, Optional
import pandas as pd


class PriceBuffer:
    """
    가격 데이터 버퍼
    
    실시간으로 들어오는 캔들 데이터를 저장하고
    EMA 계산을 위한 DataFrame으로 변환
    """
    
    def __init__(self, maxlen: int = 300):
        """
        Args:
            maxlen: 최대 저장 개수 (EMA 200 + 여유)
        """
        self.maxlen = maxlen
        self.candles = deque(maxlen=maxlen)
    
    def add_candle(self, candle: Dict[str, Any]):
        """
        캔들 추가
        
        Args:
            candle: 캔들 데이터 딕셔너리
                - timestamp: 시간
                - open: 시가
                - high: 고가
                - low: 저가
                - close: 종가
                - volume: 거래량 (옵션)
        """
        self.candles.append(candle)
    
    def to_dataframe(self) -> Optional[pd.DataFrame]:
        """
        DataFrame으로 변환
        
        Returns:
            캔들 데이터 DataFrame
        """
        if not self.candles:
            return None
        
        return pd.DataFrame(list(self.candles))
    
    def get_latest(self) -> Optional[Dict[str, Any]]:
        """
        최신 캔들 조회
        
        Returns:
            최신 캔들 딕셔너리
        """
        if not self.candles:
            return None
        return self.candles[-1]
    
    def get_latest_close(self) -> Optional[float]:
        """
        최신 종가 조회
        
        Returns:
            최신 종가
        """
        latest = self.get_latest()
        if latest:
            return float(latest.get('close', 0))
        return None
    
    def __len__(self) -> int:
        """버퍼 크기"""
        return len(self.candles)
    
    def is_ready(self, min_length: int = 200) -> bool:
        """
        EMA 계산 가능 여부
        
        Args:
            min_length: 최소 필요 데이터 수
        
        Returns:
            계산 가능 여부
        """
        return len(self.candles) >= min_length
    
    def clear(self):
        """버퍼 초기화"""
        self.candles.clear()
