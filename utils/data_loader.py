# utils/data_loader.py 수정된 부분

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import API_KEY, API_SECRET, PASSPHRASE, EMA_PERIODS
from utils.logger import log_system, log_error
from utils.indicators import calculate_ema

class HistoricalDataLoader:
    def __init__(self):
        self.base_url = "https://www.okx.com"
        self.session = requests.Session()
        
        # 요청 간격 제한 (Rate limiting)
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms
    
    def _wait_for_rate_limit(self):
        """Rate Limit 준수를 위한 대기"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        
        self.last_request_time = time.time()
    
    def get_historical_candles(self, inst_id: str, timeframe: str = "30m", 
                             limit: int = 300) -> Optional[pd.DataFrame]:
        """과거 캔들 데이터 조회 - 타임스탬프 변환 오류 수정"""
        self._wait_for_rate_limit()
        
        endpoint = "/api/v5/market/history-candles"
        
        params = {
            'instId': inst_id,
            'bar': timeframe,
            'limit': str(min(limit, 300))  # OKX 최대 300개 제한
        }
        
        try:
            url = self.base_url + endpoint
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') != '0':
                log_error(f"캔들 데이터 조회 실패: {data.get('msg', 'Unknown error')}")
                return None
            
            # 데이터 변환
            candles_raw = data.get('data', [])
            if not candles_raw:
                log_error("캔들 데이터가 비어있습니다")
                return None
            
            # DataFrame 생성
            df = pd.DataFrame(candles_raw, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'volCcy', 'volCcyQuote', 'confirm'
            ])
            
            # 타임스탬프 변환 수정 - int 크기 문제 해결
            try:
                # 문자열을 정수로 변환한 후 ms 단위를 s 단위로 변환
                timestamps = []
                for ts in df['timestamp']:
                    # 문자열을 정수로 변환
                    ts_int = int(ts)
                    # 밀리초를 초로 변환 (13자리 → 10자리)
                    if ts_int > 10**10:  # 밀리초인 경우
                        ts_int = ts_int // 1000
                    timestamps.append(ts_int)
                
                df['timestamp'] = pd.to_datetime(timestamps, unit='s')
            except (ValueError, OverflowError) as e:
                log_error(f"타임스탬프 변환 오류: {e}")
                # 대안: 현재 시간부터 역산
                now = datetime.now()
                df['timestamp'] = [now - timedelta(minutes=30*i) for i in range(len(df)-1, -1, -1)]
            
            # 데이터 타입 변환
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # NaN 값이 있는 행 제거
            df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
            
            # 시간순 정렬 (오래된 것부터)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            log_system(f"캔들 데이터 로딩 완료: {inst_id} {len(df)}개")
            return df
            
        except requests.exceptions.RequestException as e:
            log_error(f"캔들 데이터 요청 실패: {inst_id}", e)
            return None
        except Exception as e:
            log_error(f"캔들 데이터 처리 오류: {inst_id}", e)
            return None
    
    def prepare_strategy_data(self, df: pd.DataFrame, 
                            ema_periods: Dict[str, int] = None) -> Optional[pd.DataFrame]:
        """전략용 데이터 준비 (EMA 계산 포함)"""
        if df is None or len(df) < 10:
            return None
        
        if ema_periods is None:
            ema_periods = EMA_PERIODS
        
        # DataFrame 복사
        strategy_df = df.copy()
        
        try:
            # 모든 EMA 계산
            for ema_name, period in ema_periods.items():
                if len(df) >= period:
                    strategy_df[f'ema_{ema_name}'] = calculate_ema(df['close'], period)
                else:
                    log_error(f"EMA 계산 불가 - 데이터 부족: {ema_name} (필요: {period}, 보유: {len(df)})")
                    return None
            
            # NaN 값이 있는 초기 행들 제거
            max_period = max(ema_periods.values())
            strategy_df = strategy_df.iloc[max_period:].reset_index(drop=True)
            
            if len(strategy_df) < 5:
                log_error("EMA 계산 후 데이터가 충분하지 않음")
                return None
            
            log_system(f"전략 데이터 준비 완료: {len(strategy_df)}개 캔들")
            return strategy_df
            
        except Exception as e:
            log_error("전략 데이터 준비 중 오류", e)
            return None
    
    def load_multiple_symbols(self, symbols: List[str], 
                            timeframe: str = "30m") -> Dict[str, pd.DataFrame]:
        """여러 심볼의 데이터 동시 로딩"""
        results = {}
        
        log_system(f"다중 심볼 데이터 로딩 시작: {symbols}")
        
        for symbol in symbols:
            try:
                # 원본 캔들 데이터 로딩
                df = self.get_historical_candles(symbol, timeframe, limit=300)
                
                if df is not None:
                    # 전략용 데이터 준비
                    strategy_df = self.prepare_strategy_data(df)
                    
                    if strategy_df is not None:
                        results[symbol] = strategy_df
                        log_system(f"✅ {symbol} 데이터 로딩 성공")
                    else:
                        log_error(f"❌ {symbol} 전략 데이터 준비 실패")
                else:
                    log_error(f"❌ {symbol} 캔들 데이터 로딩 실패")
                
                # Rate limit 준수
                time.sleep(0.2)
                
            except Exception as e:
                log_error(f"❌ {symbol} 데이터 로딩 중 오류", e)
                continue
        
        log_system(f"다중 심볼 데이터 로딩 완료: {len(results)}/{len(symbols)}개 성공")
        return results
    
    def get_latest_price(self, inst_id: str) -> Optional[float]:
        """최신 가격 조회"""
        self._wait_for_rate_limit()
        
        endpoint = "/api/v5/market/ticker"
        params = {'instId': inst_id}
        
        try:
            url = self.base_url + endpoint
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') != '0':
                return None
            
            ticker_data = data.get('data', [])
            if ticker_data:
                return float(ticker_data[0].get('last', 0))
            
            return None
            
        except Exception as e:
            log_error(f"최신 가격 조회 실패: {inst_id}", e)
            return None

# 전역 데이터 로더 인스턴스
historical_loader = HistoricalDataLoader()

def load_initial_data(symbols: List[str], timeframe: str = "30m") -> Dict[str, pd.DataFrame]:
    """초기 데이터 로딩 (메인 함수)"""
    return historical_loader.load_multiple_symbols(symbols, timeframe)

def get_historical_data(symbol: str, limit: int = 300) -> Optional[pd.DataFrame]:
    """단일 심볼 과거 데이터 조회"""
    return historical_loader.get_historical_candles(symbol, "30m", limit)