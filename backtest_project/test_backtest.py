# test_backtest.py
"""
백테스트 모듈 테스트 스크립트
- GUI 없이 백테스트 엔진 테스트
- 결과 출력
"""

import os
import sys

# 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
import pandas as pd

from backtest.data_fetcher import DataFetcher
from backtest.backtest_engine import BacktestEngine, Params
from backtest.result_analyzer import ResultAnalyzer


def test_with_sample_data():
    """샘플 데이터로 테스트"""
    print("=" * 60)
    print("샘플 데이터로 백테스트 테스트")
    print("=" * 60)
    
    # 샘플 데이터 생성 (랜덤 가격)
    import numpy as np
    
    np.random.seed(42)
    
    # 1000개 봉 생성
    n_bars = 1000
    base_price = 50000
    
    timestamps = pd.date_range(
        start='2026-01-01 00:00:00',
        periods=n_bars,
        freq='30min',
        tz='UTC'
    )
    
    # 랜덤 워크로 가격 생성
    returns = np.random.normal(0, 0.005, n_bars)
    prices = base_price * np.cumprod(1 + returns)
    
    # OHLC 생성
    data = []
    for i, (t, p) in enumerate(zip(timestamps, prices)):
        # 랜덤 변동폭
        high = p * (1 + abs(np.random.normal(0, 0.002)))
        low = p * (1 - abs(np.random.normal(0, 0.002)))
        open_ = (p + np.random.normal(0, p * 0.001))
        
        data.append({
            'timestamp': int(t.timestamp() * 1000),
            'datetime_utc': t,
            'open': open_,
            'high': high,
            'low': low,
            'close': p,
        })
    
    df = pd.DataFrame(data)
    
    print(f"샘플 데이터 생성: {len(df)}개 봉")
    print(f"기간: {df['datetime_utc'].min()} ~ {df['datetime_utc'].max()}")
    print(f"가격 범위: ${df['close'].min():.2f} ~ ${df['close'].max():.2f}")
    print()
    
    # 백테스트 실행
    params = Params(long_only=True)
    engine = BacktestEngine(params=params, initial_capital=10000.0)
    
    print("백테스트 실행 중...")
    result = engine.run(df)
    
    # 결과 분석
    analyzer = ResultAnalyzer(result)
    
    print()
    print(analyzer.generate_summary_text())
    
    # 마커 정보
    print("\n=== 진입/청산 마커 ===")
    markers = engine.get_entry_exit_points()
    for m in markers[:10]:  # 처음 10개만
        print(f"  {m['type']:5s} | {m['side']:5s} | {m['mode']:8s} | "
              f"${m['price']:,.2f} | {m['time']}")
    
    if len(markers) > 10:
        print(f"  ... 외 {len(markers) - 10}개")
    
    return result


def test_with_csv(csv_path: str):
    """CSV 파일로 테스트"""
    print("=" * 60)
    print(f"CSV 파일로 백테스트 테스트: {csv_path}")
    print("=" * 60)
    
    # 데이터 로드
    fetcher = DataFetcher()
    
    try:
        df = fetcher.load_existing_csv(csv_path)
        print(f"데이터 로드: {len(df)}개 봉")
        print(f"기간: {df['datetime_utc'].min()} ~ {df['datetime_utc'].max()}")
        print()
        
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {csv_path}")
        return None
    except Exception as e:
        print(f"파일 로드 오류: {e}")
        return None
    
    # 백테스트 실행
    params = Params(long_only=True)
    engine = BacktestEngine(params=params, initial_capital=10000.0)
    
    print("백테스트 실행 중...")
    result = engine.run(df)
    
    # 결과 분석
    analyzer = ResultAnalyzer(result)
    
    print()
    print(analyzer.generate_summary_text())
    
    return result


def main():
    """메인 함수"""
    print("\n" + "=" * 60)
    print("백테스트 모듈 테스트")
    print("=" * 60 + "\n")
    
    # 샘플 데이터 테스트
    result = test_with_sample_data()
    
    print("\n" + "-" * 60 + "\n")
    
    # CSV 파일이 있으면 테스트
    csv_path = "BTCUSDT_30m_20260101_to_now_utc.csv"
    if os.path.exists(csv_path):
        test_with_csv(csv_path)
    else:
        print(f"CSV 파일이 없습니다: {csv_path}")
        print("데이터를 다운로드하려면 GUI에서 '데이터 가져오기' 버튼을 사용하세요.")
    
    print("\n테스트 완료!")


if __name__ == "__main__":
    main()
