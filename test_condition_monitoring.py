#!/usr/bin/env python3
# test_condition_monitoring.py
"""
조건 모니터링 시스템 테스트 스크립트
GUI 없이 백엔드 조건 모니터링 기능을 테스트
"""

import sys
import time
import random
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("🔍 조건 모니터링 시스템 테스트")
print("=" * 50)

def test_condition_monitor_import():
    """조건 모니터 임포트 테스트"""
    print("1️⃣ 모듈 임포트 테스트...")
    
    try:
        from monitoring.condition_monitor import ConditionMonitor, TrendDirection, SignalStatus
        print("✅ ConditionMonitor 임포트 성공")
        return True
    except ImportError as e:
        print(f"❌ ConditionMonitor 임포트 실패: {e}")
        print("💡 해결방법:")
        print("   1. monitoring 디렉토리가 있는지 확인")
        print("   2. monitoring/__init__.py 파일이 있는지 확인")
        print("   3. monitoring/condition_monitor.py 파일이 있는지 확인")
        return False

def generate_test_market_data(trend_type="uptrend"):
    """테스트용 시장 데이터 생성"""
    base_price = 45000 + random.uniform(-500, 500)
    
    if trend_type == "uptrend":
        # 상승장 시나리오
        ema_150 = base_price * 1.02  # EMA 150이 높음
        ema_200 = base_price * 1.01  # EMA 200보다 높음
        ema_20 = base_price * 1.001
        ema_50 = base_price * 0.999  # 골든크로스 임박
        ema_100 = base_price * 0.998
    elif trend_type == "downtrend":
        # 하락장 시나리오
        ema_150 = base_price * 0.98  # EMA 150이 낮음
        ema_200 = base_price * 0.99  # EMA 200보다 낮음
        ema_20 = base_price * 0.999
        ema_50 = base_price * 1.001  # 데드크로스 임박
        ema_100 = base_price * 1.002
    else:
        # 횡보 시나리오
        ema_150 = base_price * 1.0001
        ema_200 = base_price * 0.9999
        ema_20 = base_price * 1.0005
        ema_50 = base_price * 0.9995
        ema_100 = base_price * 1.0002
    
    return {
        'close': base_price,
        'ema_trend_fast': ema_150,
        'ema_trend_slow': ema_200,
        'curr_entry_fast': ema_20,
        'curr_entry_slow': ema_50,
        'curr_exit_slow': ema_100,
        'volume': random.uniform(1000000, 3000000),
        'change_24h': random.uniform(-3, 3)
    }

def test_condition_analysis():
    """조건 분석 테스트"""
    print("\n2️⃣ 조건 분석 테스트...")
    
    try:
        from monitoring.condition_monitor import ConditionMonitor
        
        # 조건 모니터 생성
        monitor = ConditionMonitor()
        print("✅ ConditionMonitor 인스턴스 생성 성공")
        
        # 다양한 시나리오 테스트
        scenarios = [
            ("상승장 (골든크로스 임박)", "uptrend"),
            ("하락장 (데드크로스 임박)", "downtrend"),
            ("횡보장", "sideways")
        ]
        
        for scenario_name, trend_type in scenarios:
            print(f"\n📊 시나리오: {scenario_name}")
            
            # 테스트 데이터 생성
            test_data = generate_test_market_data(trend_type)
            
            # 조건 체크 실행
            result = monitor.check_conditions(
                symbol="BTC-USDT-SWAP",
                price_data=test_data,
                strategy_manager=None
            )
            
            if result:
                # 결과 출력
                market = result.get('market_condition')
                if market:
                    print(f"   트렌드: {market.trend_direction.value} (강도: {market.trend_strength:.2f}%)")
                    print(f"   현재가: ${market.current_price:,.2f}")
                
                signals = result.get('signal_conditions', [])
                for signal in signals:
                    print(f"   신호: {signal.signal_type} - {signal.status.value} "
                          f"(거리: {signal.distance_pct:.3f}%)")
                
                strategies = result.get('strategy_conditions', [])
                if strategies:
                    for strategy in strategies:
                        mode = "실제" if strategy.is_real_mode else "가상"
                        print(f"   전략: {strategy.strategy_name} - {mode} 모드 "
                              f"(수익률: {strategy.return_pct:+.1f}%)")
            else:
                print("   ⚠️ 조건 체크 결과 없음")
            
            time.sleep(1)  # 1초 대기
        
        return True
        
    except Exception as e:
        print(f"❌ 조건 분석 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_widgets_import():
    """GUI 위젯 임포트 테스트"""
    print("\n3️⃣ GUI 위젯 임포트 테스트...")
    
    try:
        from PyQt5.QtWidgets import QApplication
        print("✅ PyQt5 사용 가능")
        
        from gui.condition_widgets import (
            ConditionStatusWidget, ConditionLogWidget, 
            ConditionStatsWidget, ConditionMonitoringWidget
        )
        print("✅ 조건 모니터링 GUI 위젯 임포트 성공")
        return True
        
    except ImportError as e:
        print(f"⚠️ GUI 위젯 임포트 실패: {e}")
        print("💡 해결방법:")
        print("   1. PyQt5 설치: pip install PyQt5")
        print("   2. gui/condition_widgets.py 파일 확인")
        return False

def test_integration():
    """통합 테스트"""
    print("\n4️⃣ 통합 테스트...")
    
    try:
        from monitoring.condition_monitor import ConditionMonitor
        
        # 5회 연속 조건 체크
        monitor = ConditionMonitor()
        
        print("📈 5회 연속 조건 체크 시작...")
        for i in range(5):
            print(f"\n--- 체크 {i+1}/5 ---")
            
            # 랜덤 트렌드 선택
            trend_types = ["uptrend", "downtrend", "sideways"]
            trend_type = random.choice(trend_types)
            
            test_data = generate_test_market_data(trend_type)
            result = monitor.check_conditions("BTC-USDT-SWAP", test_data, None)
            
            if result:
                market = result.get('market_condition')
                if market:
                    print(f"트렌드: {market.trend_direction.value} "
                          f"(${market.current_price:,.0f})")
            
            time.sleep(2)  # 2초 대기
        
        # 통계 확인
        stats = monitor.get_summary_stats()
        print(f"\n📊 최종 통계:")
        print(f"   총 체크: {stats['total_checks']}회")
        print(f"   트렌드 분포: {stats['trend_distribution']}")
        print(f"   신호 카운트: {stats['signal_counts']}")
        
        print("✅ 통합 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_file_structure_guide():
    """파일 구조 가이드 표시"""
    print("\n📁 필요한 파일 구조:")
    print("""
CoinTrading/
├── monitoring/
│   ├── __init__.py              # 빈 파일 (필수)
│   └── condition_monitor.py     # 조건 모니터링 백엔드
├── gui/
│   ├── condition_widgets.py     # 조건 모니터링 GUI 위젯
│   └── main_window.py          # 메인 윈도우 (수정 필요)
└── test_condition_monitoring.py # 이 파일
    """)
    
    print("\n🚀 파일 생성 명령어:")
    print("mkdir monitoring")
    print("echo. > monitoring/__init__.py  # Windows")
    print("touch monitoring/__init__.py    # macOS/Linux")

def main():
    """메인 테스트 함수"""
    print(f"🕒 테스트 시작 시간: {datetime.now()}")
    
    test_results = []
    
    # 1. 임포트 테스트
    import_success = test_condition_monitor_import()
    test_results.append(("모듈 임포트", import_success))
    
    if import_success:
        # 2. 조건 분석 테스트
        analysis_success = test_condition_analysis()
        test_results.append(("조건 분석", analysis_success))
        
        # 3. GUI 위젯 테스트
        gui_success = test_gui_widgets_import()
        test_results.append(("GUI 위젯", gui_success))
        
        if analysis_success:
            # 4. 통합 테스트
            integration_success = test_integration()
            test_results.append(("통합 테스트", integration_success))
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📋 테스트 결과 요약")
    print("=" * 50)
    
    for test_name, success in test_results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{test_name:15} : {status}")
    
    # 전체 성공률
    success_count = sum(1 for _, success in test_results if success)
    total_count = len(test_results)
    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
    
    print(f"\n전체 성공률: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("\n🎉 모든 테스트 통과! GUI를 실행할 준비가 되었습니다.")
        print("다음 명령어로 GUI를 실행하세요:")
        print("python run_gui.py")
    else:
        print("\n⚠️ 일부 테스트 실패. 파일 구조를 확인하세요.")
        show_file_structure_guide()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 테스트 중단됨")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()