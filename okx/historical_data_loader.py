# okx/historical_data_loader.py
"""
OKX 과거 캔들 데이터 로더

자동매매 시작 시 1주일치 과거 데이터를 로드하여
EMA 계산 및 전략 초기화에 사용

30분봉 기준:
- 1주일 = 336개 캔들
- EMA 200 계산에 충분한 데이터
"""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """지수이동평균 계산"""
    return series.ewm(span=period, adjust=False).mean()


class HistoricalDataLoader:
    """OKX API를 통해 과거 캔들 데이터 로드"""
    
    # EMA 기간 설정 (30분봉 기준)
    EMA_PERIODS = {
        'ema_20': 20,
        'ema_50': 50,
        'ema_100': 100,
        'ema_150': 150,
        'ema_200': 200,
    }
    
    def __init__(self, account_manager=None):
        self.account_manager = account_manager
        self.candle_cache: Dict[str, pd.DataFrame] = {}
        
    def load_historical_candles_sync(
        self,
        symbol: str = "BTC-USDT-SWAP",
        timeframe: str = "30m",
        days: int = 7,
        max_candles: int = 500
    ) -> Optional[pd.DataFrame]:
        """동기 방식으로 과거 캔들 데이터 로드"""
        try:
            print(f"📊 과거 데이터 로드 시작: {symbol} {timeframe} ({days}일)")
            
            bar_map = {'1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                       '1H': '1H', '4H': '4H', '1D': '1D'}
            bar = bar_map.get(timeframe, '30m')
            
            candles_per_day = {'1m': 1440, '5m': 288, '15m': 96, '30m': 48,
                              '1H': 24, '4H': 6, '1D': 1}
            needed_candles = min(candles_per_day.get(timeframe, 48) * days, max_candles)
            
            all_candles = []
            
            if self.account_manager and hasattr(self.account_manager, 'market_api'):
                all_candles = self._fetch_from_api(symbol, bar, needed_candles)
            else:
                print("⚠️ AccountManager 없음 - 더미 데이터 생성")
                all_candles = self._generate_dummy_data(symbol, timeframe, needed_candles)
            
            if not all_candles:
                print("❌ 캔들 데이터 로드 실패")
                return None
            
            df = pd.DataFrame(all_candles)
            df = self._process_dataframe(df)
            df = self.calculate_emas(df)
            
            self.candle_cache[symbol] = df
            print(f"✅ {len(df)}개 캔들 로드 완료 (EMA 계산됨)")
            return df
            
        except Exception as e:
            print(f"❌ 과거 데이터 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _fetch_from_api(self, symbol: str, bar: str, needed_candles: int) -> List[Dict]:
        """OKX API에서 캔들 데이터 가져오기"""
        all_candles = []
        after = None
        
        try:
            market_api = self.account_manager.market_api
            
            while len(all_candles) < needed_candles:
                params = {'instId': symbol, 'bar': bar, 'limit': '300'}
                if after:
                    params['after'] = after
                
                result = market_api.get_candlesticks(**params)
                
                if result and result.get('code') == '0':
                    data = result.get('data', [])
                    if not data:
                        break
                    
                    for candle in data:
                        all_candles.append({
                            'timestamp': int(candle[0]),
                            'open': float(candle[1]),
                            'high': float(candle[2]),
                            'low': float(candle[3]),
                            'close': float(candle[4]),
                            'volume': float(candle[5]) if len(candle) > 5 else 0
                        })
                    
                    after = data[-1][0]
                    print(f"  로드 중... {len(all_candles)}/{needed_candles}")
                    time.sleep(0.2)
                else:
                    print(f"⚠️ API 응답 오류: {result}")
                    break
        except Exception as e:
            print(f"❌ API 호출 오류: {e}")
        
        return all_candles
    
    def _generate_dummy_data(self, symbol: str, timeframe: str, count: int) -> List[Dict]:
        """테스트용 더미 데이터 생성"""
        import random
        
        candles = []
        base_price = 97000.0
        
        tf_minutes = {'1m': 1, '5m': 5, '15m': 15, '30m': 30,
                     '1H': 60, '4H': 240, '1D': 1440}
        interval_ms = tf_minutes.get(timeframe, 30) * 60 * 1000
        current_time = int(time.time() * 1000)
        
        for i in range(count):
            timestamp = current_time - ((count - 1 - i) * interval_ms)
            trend = 0.0001 * (i - count/2)
            change = random.uniform(-0.003, 0.003) + trend
            base_price = base_price * (1 + change)
            
            open_price = base_price * (1 + random.uniform(-0.001, 0.001))
            close_price = base_price * (1 + random.uniform(-0.001, 0.001))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.002))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.002))
            
            candles.append({
                'timestamp': timestamp,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': random.uniform(100, 1000)
            })
        
        return candles
    
    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrame 전처리"""
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df
    
    def calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        """EMA 계산 추가"""
        if df is None or len(df) == 0:
            return df
        
        close = df['close'].astype(float)
        
        for name, period in self.EMA_PERIODS.items():
            df[name] = ema(close, period)
        
        # 전략용 별칭
        df['ema_trend_fast'] = df['ema_150']
        df['ema_trend_slow'] = df['ema_200']
        df['ema_entry_fast'] = df['ema_20']
        df['ema_entry_slow'] = df['ema_50']
        df['ema_exit_fast'] = df['ema_20']
        df['ema_exit_slow'] = df['ema_100']
        
        return df
    
    def get_latest_strategy_data(self, symbol: str = "BTC-USDT-SWAP") -> Optional[Dict[str, Any]]:
        """캐시된 데이터에서 최신 전략용 데이터 반환"""
        df = self.candle_cache.get(symbol)
        if df is None or len(df) < 2:
            return None
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        return {
            'timestamp': curr.get('timestamp'),
            'datetime': curr.get('datetime'),
            'close': float(curr['close']),
            'ema_trend_fast': float(curr['ema_150']),
            'ema_trend_slow': float(curr['ema_200']),
            'ema_20': float(curr['ema_20']),
            'ema_50': float(curr['ema_50']),
            'ema_100': float(curr['ema_100']),
            'ema_150': float(curr['ema_150']),
            'ema_200': float(curr['ema_200']),
            'curr_entry_fast': float(curr['ema_20']),
            'curr_entry_slow': float(curr['ema_50']),
            'prev_entry_fast': float(prev['ema_20']),
            'prev_entry_slow': float(prev['ema_50']),
            'curr_exit_fast': float(curr['ema_20']),
            'curr_exit_slow': float(curr['ema_100']),
            'prev_exit_fast': float(prev['ema_20']),
            'prev_exit_slow': float(prev['ema_100']),
        }
    
    def add_new_candle(self, symbol: str, candle_data: Dict) -> bool:
        """새 캔들 추가 및 EMA 재계산"""
        try:
            df = self.candle_cache.get(symbol)
            if df is None:
                return False
            
            new_row = pd.DataFrame([candle_data])
            new_row['datetime'] = pd.to_datetime(new_row['timestamp'], unit='ms')
            
            last_ts = df.iloc[-1]['timestamp']
            new_ts = candle_data.get('timestamp')
            
            if last_ts == new_ts:
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in candle_data:
                        df.iloc[-1, df.columns.get_loc(col)] = candle_data[col]
            else:
                df = pd.concat([df, new_row], ignore_index=True)
            
            if len(df) > 1000:
                df = df.iloc[-1000:]
            
            df = self.calculate_emas(df)
            self.candle_cache[symbol] = df
            return True
        except Exception as e:
            print(f"❌ 캔들 추가 오류: {e}")
            return False
    
    def update_current_price(self, symbol: str, price: float) -> bool:
        """현재 가격만 업데이트"""
        try:
            df = self.candle_cache.get(symbol)
            if df is None or len(df) == 0:
                return False
            
            df.iloc[-1, df.columns.get_loc('close')] = price
            
            if price > df.iloc[-1]['high']:
                df.iloc[-1, df.columns.get_loc('high')] = price
            if price < df.iloc[-1]['low']:
                df.iloc[-1, df.columns.get_loc('low')] = price
            
            df = self.calculate_emas(df)
            self.candle_cache[symbol] = df
            return True
        except Exception as e:
            print(f"❌ 가격 업데이트 오류: {e}")
            return False
    
    def get_cached_dataframe(self, symbol: str = "BTC-USDT-SWAP") -> Optional[pd.DataFrame]:
        """캐시된 DataFrame 반환"""
        return self.candle_cache.get(symbol)


if __name__ == "__main__":
    loader = HistoricalDataLoader()
    df = loader.load_historical_candles_sync(symbol="BTC-USDT-SWAP", timeframe="30m", days=7)
    
    if df is not None:
        print(f"\n데이터 샘플 (마지막 5개):")
        print(df.tail(5)[['datetime', 'close', 'ema_20', 'ema_50', 'ema_150', 'ema_200']])
