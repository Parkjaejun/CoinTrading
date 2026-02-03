# backtest/data_fetcher.py
"""
Binance 30분봉 데이터 수집 모듈
- REST API를 통한 OHLC 데이터 수집
- 페이지네이션 및 재시도 로직 포함
- 로컬 캐싱 지원
"""

import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional
from pathlib import Path

import requests
import pandas as pd


class DataFetcher:
    """Binance 30분봉 데이터 수집 클래스"""
    
    BINANCE_SPOT_BASE_URL = "https://api.binance.com"
    KLINES_ENDPOINT = "/api/v3/klines"
    
    def __init__(self, cache_dir: str = "./cache"):
        """
        Args:
            cache_dir: 캐시 파일 저장 디렉토리
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
    
    @staticmethod
    def dt_to_ms_utc(dt: datetime) -> int:
        """UTC datetime을 unix ms로 변환"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return int(dt.timestamp() * 1000)
    
    def get_cache_path(self, symbol: str, start_date: datetime, end_date: datetime) -> Path:
        """캐시 파일 경로 생성"""
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        filename = f"{symbol}_30m_{start_str}_to_{end_str}.csv"
        return self.cache_dir / filename
    
    def fetch_klines_30m(
        self,
        symbol: str = "BTCUSDT",
        start_dt_utc: datetime = None,
        end_dt_utc: datetime = None,
        limit: int = 1000,
        timeout: int = 15,
        sleep_sec: float = 0.2,
        max_retries: int = 8,
        progress_callback=None,
    ) -> List[Dict]:
        """
        Binance Spot /api/v3/klines를 이용해 30분봉 데이터 수집
        
        Args:
            symbol: 거래 심볼 (예: BTCUSDT)
            start_dt_utc: 시작 시간 (UTC)
            end_dt_utc: 종료 시간 (UTC)
            limit: 요청당 캔들 수 (1-1000)
            timeout: 요청 타임아웃 (초)
            sleep_sec: 요청 간 대기 시간 (초)
            max_retries: 최대 재시도 횟수
            progress_callback: 진행률 콜백 함수 (current, total, message)
        
        Returns:
            [{"timestamp": ms, "open": float, "high": float, "low": float, "close": float}, ...]
        """
        if start_dt_utc is None:
            start_dt_utc = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        if end_dt_utc is None:
            end_dt_utc = datetime.now(timezone.utc)
        
        start_ms = self.dt_to_ms_utc(start_dt_utc)
        end_ms = self.dt_to_ms_utc(end_dt_utc)
        
        if limit < 1 or limit > 1000:
            raise ValueError("limit은 1~1000 범위여야 합니다.")
        
        # 예상 총 캔들 수 계산 (진행률 표시용)
        total_ms = end_ms - start_ms
        candle_interval_ms = 30 * 60 * 1000  # 30분
        estimated_total = max(1, total_ms // candle_interval_ms)
        
        out: List[Dict] = []
        next_start_ms = start_ms
        
        while True:
            if next_start_ms >= end_ms:
                break
            
            params = {
                "symbol": symbol,
                "interval": "30m",
                "startTime": next_start_ms,
                "endTime": end_ms,
                "limit": limit,
            }
            
            url = self.BINANCE_SPOT_BASE_URL + self.KLINES_ENDPOINT
            
            # 재시도 로직 (지수 백오프)
            last_err = None
            data = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    r = self.session.get(url, params=params, timeout=timeout)
                    if r.status_code == 200:
                        data = r.json()
                        last_err = None
                        break
                    
                    last_err = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
                    wait = min(2 ** attempt, 30)
                    time.sleep(wait)
                    
                except requests.RequestException as e:
                    last_err = e
                    wait = min(2 ** attempt, 30)
                    time.sleep(wait)
            
            if last_err is not None:
                raise RuntimeError(f"요청 실패: {last_err}")
            
            if not data:
                break
            
            # kline 배열 파싱
            for k in data:
                out.append({
                    "timestamp": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
            
            # 다음 페이지
            last_open_time = int(data[-1][0])
            next_start_ms = last_open_time + 1
            
            # 진행률 콜백
            if progress_callback:
                progress = min(100, int(len(out) / estimated_total * 100))
                msg = f"{symbol} {len(out):,}개 수집 중..."
                progress_callback(len(out), estimated_total, msg)
            
            time.sleep(sleep_sec)
        
        return out
    
    def fetch_data(
        self,
        symbol: str = "BTCUSDT",
        start_date: datetime = None,
        end_date: datetime = None,
        use_cache: bool = True,
        progress_callback=None,
    ) -> pd.DataFrame:
        """
        데이터 수집 (캐시 지원)
        
        Args:
            symbol: 거래 심볼
            start_date: 시작일
            end_date: 종료일
            use_cache: 캐시 사용 여부
            progress_callback: 진행률 콜백
        
        Returns:
            pd.DataFrame: OHLC 데이터
        """
        if start_date is None:
            start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        if end_date is None:
            end_date = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        # 캐시 확인
        cache_path = self.get_cache_path(symbol, start_date, end_date)
        if use_cache and cache_path.exists():
            if progress_callback:
                progress_callback(100, 100, f"캐시에서 로드: {cache_path.name}")
            return self.load_from_cache(str(cache_path))
        
        # API에서 데이터 수집
        rows = self.fetch_klines_30m(
            symbol=symbol,
            start_dt_utc=start_date,
            end_dt_utc=end_date,
            progress_callback=progress_callback,
        )
        
        if not rows:
            raise ValueError("데이터를 가져오지 못했습니다.")
        
        df = pd.DataFrame(rows)
        df["datetime_utc"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        
        # 캐시 저장
        if use_cache:
            self.save_to_cache(df, str(cache_path))
            if progress_callback:
                progress_callback(100, 100, f"캐시 저장 완료: {cache_path.name}")
        
        return df
    
    def load_from_cache(self, filepath: str) -> pd.DataFrame:
        """캐시 파일에서 데이터 로드"""
        df = pd.read_csv(filepath)
        
        # 타임스탬프 변환
        if "timestamp" in df.columns:
            if "datetime_utc" not in df.columns:
                df["datetime_utc"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        
        return df
    
    def save_to_cache(self, df: pd.DataFrame, filepath: str):
        """데이터를 캐시 파일로 저장"""
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
    
    def load_existing_csv(self, filepath: str) -> pd.DataFrame:
        """
        기존 CSV 파일 로드 (다양한 형식 지원)
        scratch_2.py의 load_ohlc_csv 로직 활용
        """
        df = pd.read_csv(filepath)
        
        # 컬럼명 정규화
        colmap = {}
        for c in df.columns:
            lc = c.lower().strip()
            if lc in ["timestamp", "time", "datetime", "date"]:
                colmap[c] = "timestamp"
            elif lc in ["open", "open_"]:
                colmap[c] = "open"
            elif lc in ["high", "high_"]:
                colmap[c] = "high"
            elif lc in ["low", "low_"]:
                colmap[c] = "low"
            elif lc in ["close", "close_"]:
                colmap[c] = "close"
            elif lc in ["volume", "vol"]:
                colmap[c] = "volume"
        
        df = df.rename(columns=colmap)
        
        # 필수 컬럼 확인
        required = ["timestamp", "open", "high", "low", "close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"필요한 컬럼이 없습니다: {missing}")
        
        # 타임스탬프 변환
        ts = df["timestamp"]
        if pd.api.types.is_numeric_dtype(ts):
            med = ts.dropna().astype(float).median()
            if med > 1e12:
                df["datetime_utc"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            else:
                df["datetime_utc"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        else:
            df["datetime_utc"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        
        # 정렬 및 정리
        df = df.dropna(subset=["datetime_utc"]).sort_values("datetime_utc").reset_index(drop=True)
        
        for c in ["open", "high", "low", "close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        
        df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
        
        return df
