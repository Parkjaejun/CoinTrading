# okx/market_data.py
from okx.account import AccountManager
import json

class MarketDataManager(AccountManager):
    """실시간 시장 데이터 관리"""
    
    def __init__(self):
        super().__init__()
    
    def get_ticker(self, inst_id):
        """현재가 정보 조회"""
        endpoint = "/api/v5/market/ticker"
        params = {"instId": inst_id}
        
        response = self._make_request('GET', endpoint, params=params)
        
        if response and response.get('code') == '0':
            data = response.get('data', [])
            if data:
                ticker = data[0]
                return {
                    'last': float(ticker.get('last', 0)),
                    'bid': float(ticker.get('bidPx', 0)),
                    'ask': float(ticker.get('askPx', 0)),
                    'volume': float(ticker.get('vol24h', 0)),
                    'high': float(ticker.get('high24h', 0)),
                    'low': float(ticker.get('low24h', 0)),
                    'change': float(ticker.get('sodUtc0', 0))
                }
        return None
    
    def get_orderbook(self, inst_id, size=5):
        """호가창 조회"""
        endpoint = "/api/v5/market/books"
        params = {
            "instId": inst_id,
            "sz": str(size)
        }
        
        response = self._make_request('GET', endpoint, params=params)
        
        if response and response.get('code') == '0':
            data = response.get('data', [])
            if data:
                book = data[0]
                return {
                    'asks': [[float(p), float(s)] for p, s, _, _ in book.get('asks', [])],
                    'bids': [[float(p), float(s)] for p, s, _, _ in book.get('bids', [])],
                    'timestamp': book.get('ts')
                }
        return None