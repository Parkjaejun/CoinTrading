# fetch_binance_btcusdt_30m.py
# Python 3.9+
# pip install pandas requests

import time
from datetime import datetime, timezone
from typing import List, Dict, Optional

import requests
import pandas as pd


BINANCE_SPOT_BASE_URL = "https://api.binance.com"  # Spot REST base
KLINES_ENDPOINT = "/api/v3/klines"


def dt_to_ms_utc(dt: datetime) -> int:
    """UTC datetime -> unix ms"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_klines_30m(
    symbol: str = "BTCUSDT",
    start_dt_utc: datetime = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    end_dt_utc: Optional[datetime] = None,
    limit: int = 1000,
    timeout: int = 15,
    sleep_sec: float = 0.2,
    max_retries: int = 8,
) -> List[Dict]:
    """
    Binance Spot /api/v3/klines 를 이용해 전체 기간의 30분봉을 페이지네이션으로 수집합니다.

    반환: [{"timestamp": <open_time_ms>, "open_": "...", "high": "...", "low": "...", "close": "..."} ...]
    """
    if end_dt_utc is None:
        end_dt_utc = datetime.now(timezone.utc)

    start_ms = dt_to_ms_utc(start_dt_utc)
    end_ms = dt_to_ms_utc(end_dt_utc)

    if limit < 1 or limit > 1000:
        raise ValueError("limit은 1~1000 범위여야 합니다.")

    out: List[Dict] = []
    next_start_ms = start_ms

    session = requests.Session()

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

        url = BINANCE_SPOT_BASE_URL + KLINES_ENDPOINT

        # 재시도 로직(간단한 지수 백오프)
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                r = session.get(url, params=params, timeout=timeout)
                if r.status_code == 200:
                    data = r.json()
                    last_err = None
                    break

                # 429/418(레이트리밋) 등 포함한 방어
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
            # 더 이상 데이터 없음
            break

        # kline 배열 포맷:
        # [
        #   [
        #     0 open_time,
        #     1 open,
        #     2 high,
        #     3 low,
        #     4 close,
        #     5 volume,
        #     6 close_time,
        #     ...
        #   ], ...
        # ]
        for k in data:
            out.append(
                {
                    "timestamp": int(k[0]),   # open time (ms)
                    "open_": k[1],
                    "high": k[2],
                    "low": k[3],
                    "close": k[4],
                }
            )

        # 다음 페이지 시작점: 마지막 캔들의 open_time + 1ms
        last_open_time = int(data[-1][0])
        next_start_ms = last_open_time + 1

        # 진행 로그(선택)
        first_ts = out[0]["timestamp"]
        last_ts = out[-1]["timestamp"]
        first_dt = datetime.fromtimestamp(first_ts / 1000, tz=timezone.utc)
        last_dt = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
        print(f"[{symbol}] 누적 {len(out):,}개 | {first_dt.isoformat()} ~ {last_dt.isoformat()}")

        time.sleep(sleep_sec)

    return out


def main():
    symbol = "BTCUSDT"
    start_dt = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime.now(timezone.utc)

    rows = fetch_klines_30m(symbol=symbol, start_dt_utc=start_dt, end_dt_utc=end_dt)

    df = pd.DataFrame(rows)
    # 숫자형으로 쓰고 싶으면 아래 변환(원치 않으면 주석 처리)
    for col in ["open_", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 사람이 보기 좋은 UTC datetime 컬럼도 추가(원치 않으면 제거)
    df["datetime_utc"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    # 저장
    out_csv = f"{symbol}_30m_20260101_to_now_utc.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print("\n완료!")
    print(f"rows: {len(df):,}")
    print(f"saved: {out_csv}")
    print(df.head())


if __name__ == "__main__":
    main()
