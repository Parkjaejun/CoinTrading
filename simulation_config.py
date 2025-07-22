# simulation_config.py
"""
실시간 라이브 시뮬레이션 전용 설정
기존 config를 상속받되 시뮬레이션 특화 설정 추가
"""

# 기존 설정 임포트
from config import *

# 시뮬레이션 전용 설정 추가
SIMULATION_CONFIG = {
    # 기본 설정
    "initial_balance": 10000.0,        # 초기 가상 자본
    "currency": "USDT",                # 기준 통화
    
    # 거래 설정
    "fee_rate": 0.0005,               # 수수료율 (0.05%)
    "slippage_rate": 0.001,           # 슬리피지 (0.1%)
    "max_positions": 10,              # 최대 포지션 수
    
    # 시장 데이터 설정
    "symbols": ["BTC-USDT-SWAP"],      # 시뮬레이션 대상 심볼
    "timeframe": "30m",               # 기본 시간프레임
    
    # 위험 관리
    "max_loss_per_trade": 0.02,       # 거래당 최대 2% 손실
    "max_daily_loss": 0.10,           # 일일 최대 10% 손실
    "stop_loss_on_total_loss": 0.30,  # 총 30% 손실시 시뮬레이션 중단
    
    # 성능 설정
    "update_interval": 1.0,           # 업데이트 간격 (초)
    "price_buffer_size": 200,         # 가격 데이터 버퍼 크기
    "log_trades": True,               # 거래 로그 기록
    
    # GUI 설정
    "chart_update_interval": 1000,    # 차트 업데이트 간격 (ms)
    "max_log_lines": 500,             # 최대 로그 라인 수
    "auto_scroll_logs": True,         # 로그 자동 스크롤
    
    # 알림 설정
    "enable_notifications": True,     # 알림 활성화
    "notify_on_trade": True,          # 거래시 알림
    "notify_on_profit": 50.0,         # $50 이상 수익시 알림
    "notify_on_loss": -30.0,          # $30 이상 손실시 알림
}

# 시뮬레이션용 전략 설정 (기존 전략 설정 오버라이드)
SIMULATION_LONG_STRATEGY = {
    **LONG_STRATEGY_CONFIG,           # 기존 설정 상속
    "virtual_mode": True,             # 가상 모드 활성화
    "paper_trading": True,            # Paper Trading 모드
    "leverage": 5,                    # 시뮬레이션용 낮은 레버리지
    "position_size_ratio": 0.1,       # 자본의 10%만 사용
}

SIMULATION_SHORT_STRATEGY = {
    **SHORT_STRATEGY_CONFIG,          # 기존 설정 상속
    "virtual_mode": True,             # 가상 모드 활성화
    "paper_trading": True,            # Paper Trading 모드
    "leverage": 3,                    # 시뮬레이션용 낮은 레버리지
    "position_size_ratio": 0.1,       # 자본의 10%만 사용
}

# 시뮬레이션용 API 설정 (실제 주문 방지)
SIMULATION_API_CONFIG = {
    "enable_real_orders": False,      # 실제 주문 비활성화
    "enable_websocket": True,         # WebSocket 데이터는 활성화
    "enable_paper_trading": True,     # Paper Trading 활성화
    "use_testnet": False,             # Testnet 사용 여부
}

# 로깅 설정
SIMULATION_LOGGING = {
    "log_level": "INFO",              # 로그 레벨
    "log_to_file": True,              # 파일 로깅
    "log_file": "logs/simulation.log", # 로그 파일 경로
    "log_trades_file": "logs/simulation_trades.log", # 거래 로그
    "log_max_size": 10 * 1024 * 1024, # 최대 10MB
    "log_backup_count": 5,            # 백업 파일 수
}

# 데이터 저장 설정
SIMULATION_DATA_CONFIG = {
    "save_results": True,             # 결과 저장
    "results_dir": "simulation_results", # 결과 저장 디렉토리
    "save_trades": True,              # 거래 내역 저장
    "save_portfolio_history": True,   # 포트폴리오 변화 저장
    "export_format": "json",          # 내보내기 형식 (json/csv)
}

# 시뮬레이션 제한 설정
SIMULATION_LIMITS = {
    "max_runtime_hours": 24,          # 최대 24시간 실행
    "max_trades_per_day": 100,        # 일일 최대 거래 수
    "max_positions_per_symbol": 3,    # 심볼당 최대 포지션 수
    "min_balance_threshold": 1000,    # 최소 잔고 임계값
}

# 성과 분석 설정
SIMULATION_ANALYTICS = {
    "calculate_sharpe_ratio": True,   # 샤프 비율 계산
    "calculate_max_drawdown": True,   # 최대 낙폭 계산
    "calculate_win_rate": True,       # 승률 계산
    "calculate_profit_factor": True,  # 수익 팩터 계산
    "benchmark_symbol": "BTC-USDT-SWAP", # 벤치마크 심볼
}

def get_simulation_config():
    """시뮬레이션 설정 반환"""
    return {
        "simulation": SIMULATION_CONFIG,
        "long_strategy": SIMULATION_LONG_STRATEGY,
        "short_strategy": SIMULATION_SHORT_STRATEGY,
        "api": SIMULATION_API_CONFIG,
        "logging": SIMULATION_LOGGING,
        "data": SIMULATION_DATA_CONFIG,
        "limits": SIMULATION_LIMITS,
        "analytics": SIMULATION_ANALYTICS,
    }

def validate_simulation_config():
    """시뮬레이션 설정 검증"""
    errors = []
    
    # 기본 설정 검증
    if SIMULATION_CONFIG["initial_balance"] < 100:
        errors.append("초기 자본이 너무 적습니다 (최소 $100)")
    
    if not SIMULATION_CONFIG["symbols"]:
        errors.append("거래 심볼이 설정되지 않았습니다")
    
    # 위험 관리 설정 검증
    if SIMULATION_CONFIG["max_loss_per_trade"] > 0.1:
        errors.append("거래당 최대 손실이 너무 큽니다 (최대 10%)")
    
    # 전략 설정 검증
    if SIMULATION_LONG_STRATEGY["leverage"] > 20:
        errors.append("롱 전략 레버리지가 너무 높습니다 (최대 20배)")
    
    if SIMULATION_SHORT_STRATEGY["leverage"] > 20:
        errors.append("숏 전략 레버리지가 너무 높습니다 (최대 20배)")
    
    if errors:
        print("❌ 시뮬레이션 설정 오류:")
        for error in errors:
            print(f"  - {error}")
        raise ValueError("시뮬레이션 설정 검증 실패")
    
    print("✅ 시뮬레이션 설정 검증 완료")

def print_simulation_config_summary():
    """시뮬레이션 설정 요약 출력"""
    print("\n📋 시뮬레이션 설정 요약:")
    print(f"  💰 초기 자본: ${SIMULATION_CONFIG['initial_balance']:,.2f}")
    print(f"  📊 거래 심볼: {', '.join(SIMULATION_CONFIG['symbols'])}")
    print(f"  📈 롱 레버리지: {SIMULATION_LONG_STRATEGY['leverage']}배")
    print(f"  📉 숏 레버리지: {SIMULATION_SHORT_STRATEGY['leverage']}배")
    print(f"  💸 수수료율: {SIMULATION_CONFIG['fee_rate']*100:.3f}%")
    print(f"  📉 슬리피지: {SIMULATION_CONFIG['slippage_rate']*100:.3f}%")
    print(f"  🛡️  거래당 최대 손실: {SIMULATION_CONFIG['max_loss_per_trade']*100:.1f}%")
    print(f"  🔔 알림: {'활성화' if SIMULATION_CONFIG['enable_notifications'] else '비활성화'}")

# 환경별 설정 로드
def load_simulation_environment(env: str = "simulation"):
    """시뮬레이션 환경 설정 로드"""
    print(f"🎮 시뮬레이션 환경: {env}")
    
    if env == "safe":
        # 안전 모드 - 더 보수적인 설정
        SIMULATION_CONFIG["initial_balance"] = 5000.0
        SIMULATION_LONG_STRATEGY["leverage"] = 2
        SIMULATION_SHORT_STRATEGY["leverage"] = 2
        SIMULATION_CONFIG["max_loss_per_trade"] = 0.01  # 1%
        print("🛡️ 안전 모드: 보수적 설정 적용")
        
    elif env == "aggressive":
        # 공격적 모드 - 더 활발한 거래
        SIMULATION_CONFIG["initial_balance"] = 20000.0
        SIMULATION_LONG_STRATEGY["leverage"] = 10
        SIMULATION_SHORT_STRATEGY["leverage"] = 5
        SIMULATION_CONFIG["max_loss_per_trade"] = 0.05  # 5%
        print("⚡ 공격적 모드: 활발한 거래 설정 적용")
        
    else:
        # 기본 시뮬레이션 모드
        print("🎮 기본 시뮬레이션 모드")

# 시뮬레이션 결과 저장 설정
def setup_simulation_directories():
    """시뮬레이션 디렉토리 설정"""
    import os
    from datetime import datetime
    
    # 기본 디렉토리 생성
    directories = [
        "simulation",
        "simulation_gui", 
        "simulation_results",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # 세션별 결과 디렉토리 생성
    session_dir = f"simulation_results/session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(session_dir, exist_ok=True)
    
    SIMULATION_DATA_CONFIG["session_dir"] = session_dir
    
    print(f"📁 시뮬레이션 디렉토리 설정 완료")
    print(f"📊 결과 저장 경로: {session_dir}")

# 시뮬레이션 백업 및 복원
def backup_simulation_state():
    """시뮬레이션 상태 백업"""
    import json
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"simulation_results/backup_{timestamp}.json"
    
    try:
        from simulation.virtual_order_manager import virtual_order_manager
        
        backup_data = {
            'timestamp': timestamp,
            'portfolio': virtual_order_manager.get_portfolio_summary(),
            'trade_stats': virtual_order_manager.get_trade_summary(),
            'positions': {k: v.__dict__ for k, v in virtual_order_manager.positions.items()},
            'trade_history': virtual_order_manager.trade_history,
            'config': get_simulation_config()
        }
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"💾 시뮬레이션 상태 백업: {backup_file}")
        return backup_file
        
    except Exception as e:
        print(f"❌ 백업 실패: {e}")
        return None

# 메인 시뮬레이션 설정 함수
def initialize_simulation_config(env: str = "simulation", balance: float = None):
    """시뮬레이션 설정 초기화"""
    print("🎮 시뮬레이션 설정 초기화")
    
    # 환경별 설정 로드
    load_simulation_environment(env)
    
    # 사용자 지정 초기 자본
    if balance:
        SIMULATION_CONFIG["initial_balance"] = balance
        print(f"💰 사용자 지정 초기 자본: ${balance:,.2f}")
    
    # 디렉토리 설정
    setup_simulation_directories()
    
    # 설정 검증
    validate_simulation_config()
    
    # 요약 출력
    print_simulation_config_summary()
    
    print("✅ 시뮬레이션 설정 초기화 완료")

# 설정 내보내기/가져오기
def export_simulation_config(filename: str = None):
    """시뮬레이션 설정 내보내기"""
    import json
    from datetime import datetime
    
    if filename is None:
        filename = f"simulation_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        config_data = get_simulation_config()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"📤 설정 내보내기 완료: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ 설정 내보내기 실패: {e}")
        return None

def import_simulation_config(filename: str):
    """시뮬레이션 설정 가져오기"""
    import json
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 전역 설정 업데이트
        global SIMULATION_CONFIG, SIMULATION_LONG_STRATEGY, SIMULATION_SHORT_STRATEGY
        
        SIMULATION_CONFIG.update(config_data.get('simulation', {}))
        SIMULATION_LONG_STRATEGY.update(config_data.get('long_strategy', {}))
        SIMULATION_SHORT_STRATEGY.update(config_data.get('short_strategy', {}))
        
        print(f"📥 설정 가져오기 완료: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ 설정 가져오기 실패: {e}")
        return False