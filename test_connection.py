"""
OKX API 연결 테스트 스크립트
실제 거래 전에 API 연결 및 기능을 테스트합니다.
"""

import sys
import time
from datetime import datetime
from okx.account import AccountManager
from okx.order_manager import OrderManager
from okx.websocket_handler import WebSocketHandler

def test_api_connection():
    """API 연결 테스트"""
    print("=" * 50)
    print("OKX API 연결 테스트 시작")
    print("=" * 50)
    
    try:
        account = AccountManager()
        
        # 1. 계좌 정보 조회 테스트
        print("\n[1] 계좌 정보 조회 테스트")
        balances = account.get_account_balance()
        if balances:
            print("✅ 계좌 조회 성공")
            for currency, balance in balances.items():
                if balance['total'] > 0:
                    print(f"   {currency}: {balance['total']:.4f} (사용가능: {balance['available']:.4f})")
        else:
            print("❌ 계좌 조회 실패")
            return False
        
        # 2. 계좌 설정 조회
        print("\n[2] 계좌 설정 조회 테스트")
        config = account.get_account_config()
        if config:
            print("✅ 계좌 설정 조회 성공")
            print(f"   계좌 레벨: {config.get('account_level')}")
            print(f"   포지션 모드: {config.get('position_mode')}")
            print(f"   마진 모드: {config.get('margin_mode')}")
        else:
            print("❌ 계좌 설정 조회 실패")
            
        # 3. 포지션 조회
        print("\n[3] 포지션 조회 테스트")
        positions = account.get_positions()
        print(f"✅ 현재 포지션 수: {len(positions)}")
        if positions:
            for pos in positions:
                print(f"   {pos['instrument']}: {pos['size']} (PnL: {pos['unrealized_pnl']:.2f})")
        
        # 4. 수수료율 조회
        print("\n[4] 수수료율 조회 테스트")
        fees = account.get_trading_fee_rate()
        print(f"✅ Maker: {fees['maker_fee']*100:.3f}%, Taker: {fees['taker_fee']*100:.3f}%")
        
        print("\n🎉 API 연결 테스트 완료 - 모든 기능 정상 작동")
        return True
        
    except Exception as e:
        print(f"❌ API 연결 테스트 실패: {e}")
        return False

def test_order_functions():
    """주문 관련 기능 테스트 (실제 주문 없이 기능만 테스트)"""
    print("\n" + "=" * 50)
    print("주문 기능 테스트 (실제 주문 제외)")
    print("=" * 50)
    
    try:
        order_manager = OrderManager()
        
        # 1. 포지션 크기 계산 테스트
        print("\n[1] 포지션 크기 계산 테스트")
        btc_price = 45000  # 예시 BTC 가격
        capital = 1000     # 예시 자본
        leverage = 10
        
        position_calc = order_manager.calculate_position_size(
            capital=capital, 
            leverage=leverage, 
            price=btc_price
        )
        
        if position_calc:
            print("✅ 포지션 크기 계산 성공")
            print(f"   투입 자본: ${capital}")
            print(f"   BTC 가격: ${btc_price}")
            print(f"   레버리지: {leverage}배")
            print(f"   포지션 크기: {position_calc['position_size']} BTC")
            print(f"   명목 거래금액: ${position_calc['notional_value']}")
            print(f"   예상 수수료: ${position_calc['estimated_fee']}")
        else:
            print("❌ 포지션 크기 계산 실패")
            
        # 2. 최대 레버리지 조회
        print("\n[2] 최대 레버리지 조회 테스트")
        max_leverage = order_manager.get_max_leverage("BTC-USDT-SWAP")
        print(f"✅ 최대 매수 포지션: {max_leverage['max_buy']}")
        print(f"✅ 최대 매도 포지션: {max_leverage['max_sell']}")
        
        print("\n🎉 주문 기능 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 주문 기능 테스트 실패: {e}")
        return False

def test_websocket_connection(duration=30):
    """WebSocket 연결 테스트"""
    print(f"\n" + "=" * 50)
    print(f"WebSocket 연결 테스트 ({duration}초)")
    print("=" * 50)
    
    try:
        ws_handler = WebSocketHandler()
        
        print("\n[1] WebSocket 연결 시작")
        public_thread, private_thread = ws_handler.start_ws(["BTC-USDT-SWAP"])
        
        print(f"[2] {duration}초 동안 데이터 수신 대기...")
        start_time = time.time()
        data_received = False
        
        while time.time() - start_time < duration:
            # 최신 가격 확인
            latest_price = ws_handler.get_latest_price("BTC-USDT-SWAP")
            if latest_price and not data_received:
                print(f"✅ 실시간 데이터 수신 성공: BTC 가격 ${latest_price}")
                data_received = True
            
            # 매 5초마다 상태 출력
            elapsed = int(time.time() - start_time)
            if elapsed % 5 == 0 and elapsed > 0:
                if latest_price:
                    print(f"   [{elapsed}s] BTC: ${latest_price}")
                else:
                    print(f"   [{elapsed}s] 데이터 수신 대기 중...")
            
            time.sleep(1)
        
        # WebSocket 중지
        print("\n[3] WebSocket 연결 중지")
        ws_handler.stop_ws()
        
        if data_received:
            print("🎉 WebSocket 테스트 완료 - 실시간 데이터 수신 성공")
            return True
        else:
            print("⚠️ WebSocket 연결은 되었으나 데이터 수신 실패")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket 테스트 실패: {e}")
        return False

def test_paper_trade():
    """모의 거래 테스트"""
    print("\n" + "=" * 50)
    print("모의 거래 테스트")
    print("=" * 50)
    
    print("⚠️ 주의: 이 테스트는 실제 주문을 생성합니다!")
    print("소액으로 진행하며, 즉시 취소할 예정입니다.")
    
    response = input("계속 진행하시겠습니까? (y/N): ").lower()
    if response != 'y':
        print("모의 거래 테스트 취소")
        return True
    
    try:
        order_manager = OrderManager()
        
        # 매우 소액의 테스트 주문 (0.001 BTC)
        print("\n[1] 소액 테스트 주문 생성")
        test_order = order_manager.place_limit_order(
            inst_id="BTC-USDT-SWAP",
            side="buy",
            size=0.001,
            price=20000,  # 현재가보다 훨씬 낮은 가격 (체결되지 않도록)
            leverage=1
        )
        
        if test_order:
            print(f"✅ 테스트 주문 생성 성공: {test_order['order_id']}")
            
            # 주문 상태 확인
            time.sleep(2)
            order_status = order_manager.get_order_status(
                "BTC-USDT-SWAP", 
                test_order['order_id']
            )
            
            if order_status:
                print(f"   주문 상태: {order_status['status']}")
                
            # 주문 취소
            print("\n[2] 테스트 주문 취소")
            cancel_result = order_manager.cancel_order(
                "BTC-USDT-SWAP",
                test_order['order_id']
            )
            
            if cancel_result:
                print("✅ 테스트 주문 취소 성공")
                print("🎉 모의 거래 테스트 완료")
                return True
            else:
                print("❌ 주문 취소 실패")
                return False
        else:
            print("❌ 테스트 주문 생성 실패")
            return False
            
    except Exception as e:
        print(f"❌ 모의 거래 테스트 실패: {e}")
        return False

def main():
    """전체 테스트 실행"""
    print("🚀 OKX 거래 시스템 종합 테스트 시작")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 1. API 연결 테스트
    test_results.append(("API 연결", test_api_connection()))
    
    # 2. 주문 기능 테스트
    test_results.append(("주문 기능", test_order_functions()))
    
    # 3. WebSocket 테스트 (선택사항)
    ws_test = input("\nWebSocket 테스트를 진행하시겠습니까? (30초 소요) (y/N): ").lower()
    if ws_test == 'y':
        test_results.append(("WebSocket", test_websocket_connection(30)))
    
    # 4. 모의 거래 테스트 (선택사항)
    paper_test = input("\n모의 거래 테스트를 진행하시겠습니까? (실제 주문 생성 후 취소) (y/N): ").lower()
    if paper_test == 'y':
        test_results.append(("모의 거래", test_paper_trade()))
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name:15s}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 모든 테스트 통과! 거래 시스템이 정상 작동합니다.")
        print("이제 실제 전략을 구현하고 백테스팅을 진행할 수 있습니다.")
    else:
        print("⚠️ 일부 테스트 실패. config.py 설정과 API 키를 확인해주세요.")
        print("문제가 지속되면 OKX API 문서를 참조하시기 바랍니다.")
    
    print("\n테스트 완료!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n테스트 실행 중 오류 발생: {e}")
        sys.exit(1)