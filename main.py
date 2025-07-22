"""
단순화된 OKX 듀얼 자산 트레이딩 봇
"""

import time
from datetime import datetime
from okx.websocket_handler import WebSocketHandler
from strategy.dual_manager import DualStrategyManager
from config import TRADING_CONFIG, validate_config
from utils.logger import trading_logger, log_system

def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("OKX 듀얼 자산 트레이딩 봇 시작")
    print("=" * 50)
    
    try:
        # 설정 검증
        log_system("설정 검증 중...")
        validate_config()
        
        # 전략 관리자 초기화
        strategy_manager = DualStrategyManager(
            total_capital=TRADING_CONFIG.get('initial_capital', 10000),
            symbols=TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
        )
        
        # WebSocket 핸들러 초기화
        ws_handler = WebSocketHandler(strategy_manager=strategy_manager)
        
        # 실시간 데이터 수신 시작
        symbols = TRADING_CONFIG.get('symbols', ['BTC-USDT-SWAP'])
        ws_handler.start_ws(symbols)
        
        print(f"실시간 트레이딩 시작 - 대상: {symbols}")
        print("중지하려면 Ctrl+C를 누르세요")
        print("=" * 50)
        
        # 메인 루프
        last_status_time = 0
        while True:
            current_time = time.time()
            
            # 5분마다 상태 출력
            if current_time - last_status_time >= 300:  # 5분 = 300초
                strategy_manager.print_status()
                last_status_time = current_time
            
            time.sleep(10)  # 10초마다 체크
            
    except KeyboardInterrupt:
        print("\n사용자 종료 요청")
    except Exception as e:
        print(f"시스템 오류: {e}")
    finally:
        # 정리 작업
        if 'ws_handler' in locals():
            ws_handler.stop_ws()
        if 'strategy_manager' in locals():
            strategy_manager.close_all_positions()
            strategy_manager.print_final_summary()
        
        print("트레이딩 봇 종료 완료")

if __name__ == "__main__":
    main()