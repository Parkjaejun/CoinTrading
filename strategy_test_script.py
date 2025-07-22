"""
전략 시스템 테스트 스크립트
실제 거래 전에 전략 로직을 검증합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategy.long_strategy import LongStrategy
from strategy.short_strategy import ShortStrategy
from strategy.strategy_manager import StrategyManager, create_strategy_manager_from_preset
from utils.generate_latest_data import generate_strategy_data
from utils.indicators import calculate_ema

def generate_mock_data(num_candles=300, base_price=45000, volatility=0.02):
    """모의 캔들 데이터 생성"""
    print(f"모의 데이터 생성 중: {num_candles}개 캔들")
    
    # 시간 시리즈 생성 (30분 간격)
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=30 * num_candles)
    timestamps = pd.date_range(start=start_time, end=end_time, freq='30T')[:num_candles]
    
    # 랜덤 가격 변동 생성
    np.random.seed(42)  # 재현 가능한 결과를 위해
    
    prices = [base_price]
    for i in range(num_candles - 1):
        # 랜덤 워크 + 작은 트렌드
        trend = 0.0001 * i  # 약간의 상승 트렌드
        change = np.random.normal(trend, volatility)
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1000))  # 최소 가격 보장
    
    # 캔들 데이터 생성 (OHLCV)
    candles = []
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        # 간단한 OHLC 생성
        high = close * (1 + abs(np.random.normal(0, 0.01)))
        low = close * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i-1] if i > 0 else close
        volume = np.random.uniform(1000, 5000)
        
        candles.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(candles)
    print(f"데이터 생성 완료: {len(df)}개 캔들")
    print(f"가격 범위: {df['close'].min():.2f} - {df['close'].max():.2f}")
    
    return df

def test_single_strategy(strategy_class, symbol="BTC-USDT-SWAP", initial_capital=1000):
    """단일 전략 테스트"""
    print(f"\n{'='*60}")
    print(f"{strategy_class.__name__} 테스트")
    print(f"{'='*60}")
    
    # 전략 초기화
    strategy = strategy_class(symbol, initial_capital)
    
    # 모의 데이터 생성
    df = generate_mock_data(300, base_price=45000)
    
    # EMA 기간 설정
    ema_periods = {
        'trend_fast': 150,
        'trend_slow': 200,
        'entry_fast': 20,
        'entry_slow': 50,
        'exit_fast_long': 20,
        'exit_slow_long': 100,
        'exit_fast_short': 100,
        'exit_slow_short': 200
    }
    
    trades = []
    signals = []
    
    # 캔들 하나씩 처리 (실시간 시뮬레이션)
    for i in range(max(ema_periods.values()) + 2, len(df)):
        # 현재까지의 데이터만 사용
        current_df = df.iloc[:i+1].copy()
        
        # 전략용 데이터 생성
        strategy_data = generate_strategy_data(current_df, ema_periods)
        
        if strategy_data:
            # 전략 신호 처리
            signal = strategy.process_signal(strategy_data)
            
            if signal:
                signals.append({
                    'timestamp': strategy_data['timestamp'],
                    'action': signal['action'],
                    'price': signal.get('price', strategy_data['close']),
                    'pnl': signal.get('pnl'),
                    'reason': signal.get('reason'),
                    'is_real_mode': signal.get('is_real_mode', True)
                })
                
                # 거래 완료 시 기록
                if signal['action'].startswith('exit'):
                    trades.append(signal)
    
    # 결과 분석
    print(f"\n=== {strategy_class.__name__} 테스트 결과 ===")
    print(f"총 시그널: {len(signals)}개")
    print(f"완료된 거래: {len(trades)}개")
    
    if trades:
        total_pnl = sum(trade.get('pnl', 0) for trade in trades)
        winning_trades = sum(1 for trade in trades if trade.get('pnl', 0) > 0)
        win_rate = (winning_trades / len(trades)) * 100
        
        print(f"총 PnL: {total_pnl:+.2f} USDT")
        print(f"승률: {win_rate:.1f}% ({winning_trades}/{len(trades)})")
        print(f"평균 PnL: {total_pnl/len(trades):+.2f} USDT")
        
        if total_pnl != 0:
            max_win = max(trade.get('pnl', 0) for trade in trades)
            max_loss = min(trade.get('pnl', 0) for trade in trades)
            print(f"최대 수익: {max_win:+.2f} USDT")
            print(f"최대 손실: {max_loss:+.2f} USDT")
    
    # 전략 상태 출력
    strategy.print_status()
    
    return strategy, signals, trades

def test_strategy_manager():
    """전략 관리자 테스트"""
    print(f"\n{'='*60}")
    print("전략 관리자 테스트")
    print(f"{'='*60}")
    
    # 전략 관리자 생성
    manager = create_strategy_manager_from_preset(
        preset_name='balanced',
        total_capital=10000,
        symbols=['BTC-USDT-SWAP']
    )
    
    print("\n전략 관리자 설정 완료")
    manager.print_detailed_status()
    
    # 모의 데이터로 시뮬레이션
    df = generate_mock_data(200, base_price=45000)
    
    # EMA 기간 (전략 관리자와 동일)
    ema_periods = manager.ema_periods
    
    processed_signals = 0
    
    # 순차적으로 데이터 처리
    for i in range(max(ema_periods.values()) + 2, len(df)):
        current_df = df.iloc[:i+1].copy()
        
        # 전략용 데이터 생성
        strategy_data = generate_strategy_data(current_df, ema_periods)
        
        if strategy_data:
            # 전략 매니저에 신호 전달 (실제 주문은 수행되지 않음)
            try:
                manager.process_signal('BTC-USDT-SWAP', strategy_data)
                processed_signals += 1
            except Exception as e:
                print(f"신호 처리 오류: {e}")
    
    print(f"\n처리된 신호: {processed_signals}개")
    
    # 최종 상태 출력
    manager.print_detailed_status()
    
    return manager

def test_ema_calculations():
    """EMA 계산 검증"""
    print(f"\n{'='*60}")
    print("EMA 계산 검증")
    print(f"{'='*60}")
    
    # 모의 데이터 생성
    df = generate_mock_data(300, base_price=45000)
    
    # EMA 계산
    ema_periods = [20, 50, 100, 150, 200]
    
    for period in ema_periods:
        df[f'ema_{period}'] = calculate_ema(df['close'], period)
    
    # 최신 값들 출력
    latest = df.iloc[-1]
    
    print(f"현재 가격: {latest['close']:.2f}")
    for period in ema_periods:
        ema_value = latest[f'ema_{period}']
        print(f"EMA{period}: {ema_value:.2f}")
    
    # 크로스오버 감지 테스트
    print(f"\n크로스오버 확인:")
    current = df.iloc[-1]
    previous = df.iloc[-2]
    
    # 20EMA vs 50EMA
    if previous['ema_20'] <= previous['ema_50'] and current['ema_20'] > current['ema_50']:
        print("✅ 20EMA/50EMA 골든크로스 감지")
    elif previous['ema_20'] >= previous['ema_50'] and current['ema_20'] < current['ema_50']:
        print("⚠️ 20EMA/50EMA 데드크로스 감지")
    
    # 150EMA vs 200EMA
    if current['ema_150'] > current['ema_200']:
        print("📈 상승 트렌드 (150EMA > 200EMA)")
    else:
        print("📉 하락 트렌드 (150EMA < 200EMA)")

def main():
    """메인 테스트 함수"""
    print("🧪 전략 시스템 종합 테스트")
    print("=" * 80)
    
    try:
        # 1. EMA 계산 검증
        test_ema_calculations()
        
        # 2. 롱 전략 테스트
        long_strategy, long_signals, long_trades = test_single_strategy(LongStrategy)
        
        # 3. 숏 전략 테스트
        short_strategy, short_signals, short_trades = test_single_strategy(ShortStrategy)
        
        # 4. 전략 관리자 테스트
        strategy_manager = test_strategy_manager()
        
        # 5. 종합 결과
        print(f"\n{'='*80}")
        print("종합 테스트 결과")
        print(f"{'='*80}")
        
        print(f"롱 전략: {len(long_trades)}개 거래")
        if long_trades:
            long_pnl = sum(t.get('pnl', 0) for t in long_trades)
            print(f"  PnL: {long_pnl:+.2f} USDT")
        
        print(f"숏 전략: {len(short_trades)}개 거래")
        if short_trades:
            short_pnl = sum(t.get('pnl', 0) for t in short_trades)
            print(f"  PnL: {short_pnl:+.2f} USDT")
        
        print(f"\n✅ 모든 테스트 완료!")
        print(f"실제 거래 전에 충분한 백테스팅을 권장합니다.")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()