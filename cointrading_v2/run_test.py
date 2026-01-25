#!/usr/bin/env python3
# run_test.py
"""CoinTrading v2 테스트 스크립트"""

import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_v2 import ParamsV2
from backtest_v2 import BacktestV2, load_ohlc_csv, prepare_data_with_ema
from trading_engine_v2 import TradingEngineV2
from models import BarData
import pandas as pd
import numpy as np


def generate_sample_csv(filepath: str, n_bars: int = 2000):
    """샘플 CSV 생성"""
    print(f"📊 샘플 데이터 생성: {n_bars}개 봉")
    
    data = []
    price = 50000.0
    timestamp = datetime(2024, 1, 1)
    trend = 1
    trend_duration = 50
    
    for i in range(n_bars):
        if trend_duration <= 0:
            trend = random.choice([-1, 0, 1, 1])
            trend_duration = random.randint(30, 100)
        trend_duration -= 1
        
        change = trend * 0.001 + (random.random() - 0.5) * 0.02
        open_p = price
        close_p = price * (1 + change)
        high_p = max(open_p, close_p) * (1 + random.random() * 0.005)
        low_p = min(open_p, close_p) * (1 - random.random() * 0.005)
        
        data.append({
            'timestamp': timestamp.isoformat(),
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p,
        })
        
        price = close_p
        timestamp += timedelta(minutes=30)
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    print(f"   저장됨: {filepath}")
    return filepath


def test_basic():
    """기본 테스트"""
    print("\n" + "="*60)
    print("🧪 기본 엔진 테스트")
    print("="*60)
    
    params = ParamsV2(enable_debug_logging=False)
    engine = TradingEngineV2(params=params, use_mock_email=True)
    engine.init_capital(10000.0)
    
    print(f"✅ 엔진 초기화 완료")
    print(f"   - 모드: {engine._mode()}")
    print(f"   - 자본: ${engine.real_capital:,.2f}")
    
    # 상태 확인
    status = engine.get_status()
    print(f"   - 상태: {status.to_dict()}")


def test_backtest(csv_path: str = None):
    """백테스트 실행"""
    print("\n" + "="*60)
    print("🧪 백테스트 테스트")
    print("="*60)
    
    # CSV 없으면 생성
    if csv_path is None or not os.path.exists(csv_path):
        csv_path = "/tmp/test_data.csv"
        generate_sample_csv(csv_path, n_bars=2000)
    
    params = ParamsV2(
        enable_debug_logging=False,
        debug_log_interval=500,
    )
    
    bt = BacktestV2(
        params=params,
        initial_capital=10000.0,
        use_mock_email=True
    )
    
    results = bt.run(csv_path=csv_path, print_trades=False, quiet=False)
    
    print(f"\n📈 결과 요약:")
    print(f"   - ROI: {results['real_roi_pct']:+.2f}%")
    print(f"   - MDD: -{results['real_mdd_pct']:.2f}%")
    print(f"   - 거래 수: {results['real_trade_count']} (REAL)")
    print(f"   - 승률: {results['real_win_rate_pct']:.1f}%")
    print(f"   - 모드 전환: R→V={results['mode_switch_r2v']}, V→R={results['mode_switch_v2r']}")
    
    return results


def test_pipeline():
    """파이프라인 테스트"""
    print("\n" + "="*60)
    print("🧪 시그널 파이프라인 테스트")
    print("="*60)
    
    from signal_pipeline import SignalPipeline, SignalGenerator
    
    params = ParamsV2()
    pipeline = SignalPipeline(params, symbol="TEST")
    
    # 진입 조건 시그널
    bar = BarData(
        timestamp=datetime.now(),
        open=50000, high=50500, low=49500, close=50200,
        ema_trend_fast=50100, ema_trend_slow=50000,  # 상승장
        ema_entry_fast=50150, ema_entry_slow=50100,  # 골든크로스
        ema_exit_fast=50200, ema_exit_slow=50000,
        prev_entry_fast=50050, prev_entry_slow=50100,  # 이전엔 아래
        prev_exit_fast=50100, prev_exit_slow=50000,
    )
    
    signal, validation = pipeline.process(
        data=bar,
        position=None,
        is_real_mode=True,
        current_capital=10000.0,
    )
    
    print(f"✅ 시그널 생성: {signal.signal_type}")
    print(f"   - 이유: {signal.reason}")
    print(f"   - 검증: {'통과' if validation.is_valid else '거부'}")
    
    status = pipeline.get_status()
    print(f"   - 통계: {status['stats']}")


def main():
    """메인 테스트 실행"""
    print("="*60)
    print("🚀 CoinTrading v2 테스트 시작")
    print("="*60)
    
    # 1. 기본 테스트
    test_basic()
    
    # 2. 파이프라인 테스트
    test_pipeline()
    
    # 3. 백테스트
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    test_backtest(csv_path)
    
    print("\n" + "="*60)
    print("✅ 모든 테스트 완료!")
    print("="*60)


if __name__ == "__main__":
    main()
