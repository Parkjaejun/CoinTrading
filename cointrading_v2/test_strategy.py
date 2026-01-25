# test_strategy.py
"""
전략 시스템 테스트 스크립트

1. 기본 초기화 테스트
2. 시그널 파이프라인 테스트
3. 백테스트 테스트
"""

import sys
import os

# 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_sample_data(n_bars: int = 500, start_price: float = 50000.0) -> pd.DataFrame:
    """
    샘플 OHLCV 데이터 생성
    
    트렌드와 횡보 구간이 포함된 데이터
    """
    np.random.seed(42)
    
    timestamps = []
    opens = []
    highs = []
    lows = []
    closes = []
    
    price = start_price
    base_time = datetime.now() - timedelta(minutes=30 * n_bars)
    
    for i in range(n_bars):
        # 트렌드 시뮬레이션
        if i < n_bars * 0.3:
            # 상승 트렌드
            drift = 0.001
        elif i < n_bars * 0.5:
            # 하락 트렌드
            drift = -0.0015
        elif i < n_bars * 0.7:
            # 상승 트렌드
            drift = 0.002
        else:
            # 횡보
            drift = 0.0
        
        # 변동성
        volatility = 0.008
        change = drift + volatility * np.random.randn()
        
        open_price = price
        close_price = price * (1 + change)
        high_price = max(open_price, close_price) * (1 + abs(np.random.randn() * 0.002))
        low_price = min(open_price, close_price) * (1 - abs(np.random.randn() * 0.002))
        
        timestamps.append(base_time + timedelta(minutes=30 * i))
        opens.append(open_price)
        highs.append(high_price)
        lows.append(low_price)
        closes.append(close_price)
        
        price = close_price
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
    })


def test_basic_initialization():
    """테스트 1: 기본 초기화"""
    print("\n" + "="*60)
    print("테스트 1: 기본 초기화")
    print("="*60)
    
    from strategy.long_strategy import LongStrategy
    from strategy.email_notifier import MockEmailNotifier
    
    # 전략 초기화
    notifier = MockEmailNotifier()
    strategy = LongStrategy(
        symbol="BTC-USDT-SWAP",
        initial_capital=10000.0,
        email_notifier=notifier
    )
    
    # 상태 확인
    status = strategy.get_status()
    
    assert status['symbol'] == "BTC-USDT-SWAP"
    assert status['mode'] == "REAL"
    assert status['real_capital'] == 10000.0
    assert status['is_position_open'] == False
    
    print(f"✅ 심볼: {status['symbol']}")
    print(f"✅ 모드: {status['mode']}")
    print(f"✅ 자본: ${status['real_capital']:,.2f}")
    print(f"✅ 포지션: {'있음' if status['is_position_open'] else '없음'}")
    
    print("\n✅ 테스트 1 통과!")
    return True


def test_signal_pipeline():
    """테스트 2: 시그널 파이프라인"""
    print("\n" + "="*60)
    print("테스트 2: 시그널 파이프라인")
    print("="*60)
    
    from strategy.long_strategy import LongStrategy
    from strategy.email_notifier import MockEmailNotifier
    
    notifier = MockEmailNotifier()
    strategy = LongStrategy(
        symbol="BTC-USDT-SWAP",
        initial_capital=10000.0,
        email_notifier=notifier
    )
    
    # 골든크로스 시뮬레이션 데이터
    data = {
        'timestamp': datetime.now(),
        'close': 50000.0,
        'ema_trend_fast': 50100.0,  # 150 EMA
        'ema_trend_slow': 50000.0,  # 200 EMA (상승장)
        'curr_entry_fast': 50050.0,  # 현재 20 EMA
        'curr_entry_slow': 50000.0,  # 현재 50 EMA
        'prev_entry_fast': 49950.0,  # 이전 20 EMA
        'prev_entry_slow': 50000.0,  # 이전 50 EMA (골든크로스)
        'curr_exit_fast': 50050.0,
        'curr_exit_slow': 49900.0,
        'prev_exit_fast': 49950.0,
        'prev_exit_slow': 49900.0,
    }
    
    # 시그널 처리
    result = strategy.process_signal(data)
    
    # 결과 확인
    assert result is not None, "시그널이 생성되어야 함"
    assert result['action'] == 'entry', "진입 시그널이어야 함"
    assert strategy.is_position_open == True, "포지션이 열려야 함"
    
    print(f"✅ 시그널 결과: {result}")
    print(f"✅ 포지션 상태: 열림")
    print(f"✅ 진입가: ${strategy.entry_price:,.2f}")
    
    # 파이프라인 통계
    stats = strategy.pipeline.get_stats()
    print(f"\n📊 파이프라인 통계:")
    print(f"   - 총 시그널: {stats['total_signals']}")
    print(f"   - ENTRY 시그널: {stats['entry_signals']}")
    print(f"   - 검증 통과: {stats['valid_signals']}")
    
    print("\n✅ 테스트 2 통과!")
    return True


def test_backtest():
    """테스트 3: 백테스트"""
    print("\n" + "="*60)
    print("테스트 3: 백테스트")
    print("="*60)
    
    from strategy.long_strategy import LongStrategy
    from strategy.email_notifier import MockEmailNotifier
    from utils.data_generator import prepare_backtest_data, row_to_strategy_data
    from config import EMA_PERIODS
    
    # 샘플 데이터 생성
    print("📊 샘플 데이터 생성 중...")
    df = generate_sample_data(n_bars=500, start_price=50000.0)
    print(f"   - 봉 수: {len(df)}")
    print(f"   - 기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
    
    # EMA 계산
    df = prepare_backtest_data(df, EMA_PERIODS)
    
    # 전략 초기화
    notifier = MockEmailNotifier()
    strategy = LongStrategy(
        symbol="BACKTEST",
        initial_capital=10000.0,
        email_notifier=notifier
    )
    
    # 시작 인덱스 (EMA 계산에 필요한 기간 이후)
    start_idx = max(EMA_PERIODS.values()) + 2
    
    print(f"\n🚀 백테스트 시작 (봉 {start_idx}부터)")
    
    # 백테스트 실행
    for i in range(start_idx, len(df)):
        prev_row = df.iloc[i - 1]
        curr_row = df.iloc[i]
        
        data = row_to_strategy_data(curr_row, prev_row)
        strategy.process_signal(data)
    
    # 결과 출력
    status = strategy.get_status()
    win_rate = (strategy.win_count / strategy.trade_count * 100) if strategy.trade_count > 0 else 0
    
    print(f"\n📊 백테스트 결과:")
    print(f"   - 초기 자본: $10,000.00")
    print(f"   - 최종 자본: ${status['real_capital']:,.2f}")
    print(f"   - 수익률: {((status['real_capital'] - 10000) / 10000 * 100):+.2f}%")
    print(f"   - 거래 횟수: {strategy.trade_count}")
    print(f"   - 승률: {win_rate:.1f}%")
    print(f"   - 총 PnL: ${strategy.total_pnl:+,.2f}")
    print(f"   - 모드 전환: R→V={strategy.cnt_r2v}, V→R={strategy.cnt_v2r}")
    
    # 이메일 알림 통계
    print(f"\n📧 Mock 이메일: {notifier.send_count}건 발송")
    
    # 파이프라인 요약
    strategy.pipeline.print_summary()
    
    print("✅ 테스트 3 통과!")
    return True


def test_strategy_manager():
    """테스트 4: 전략 매니저"""
    print("\n" + "="*60)
    print("테스트 4: 전략 매니저")
    print("="*60)
    
    from strategy.strategy_manager import StrategyManager
    from strategy.email_notifier import MockEmailNotifier
    
    notifier = MockEmailNotifier()
    manager = StrategyManager(
        total_capital=10000.0,
        symbols=['BTC-USDT-SWAP'],
        email_notifier=notifier
    )
    
    # 상태 확인
    status = manager.get_total_status()
    
    print(f"✅ 전략 수: {len(manager.strategies)}")
    print(f"✅ 총 자본: ${status['total_capital']:,.2f}")
    print(f"✅ 심볼: {manager.symbols}")
    
    print("\n✅ 테스트 4 통과!")
    return True


def main():
    """메인 테스트 실행"""
    print("\n" + "🚀" * 30)
    print("CoinTrading v2 전략 테스트")
    print("🚀" * 30)
    
    tests = [
        ("기본 초기화", test_basic_initialization),
        ("시그널 파이프라인", test_signal_pipeline),
        ("백테스트", test_backtest),
        ("전략 매니저", test_strategy_manager),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n❌ {name} 실패: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"📊 테스트 결과: {passed}/{len(tests)} 통과")
    if failed == 0:
        print("✅ 모든 테스트 통과!")
    else:
        print(f"❌ {failed}개 테스트 실패")
    print("="*60)


if __name__ == "__main__":
    main()
