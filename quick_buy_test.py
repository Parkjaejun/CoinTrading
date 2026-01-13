#!/usr/bin/env python3
# quick_buy_test.py
"""
빠른 구매 테스트 - long_short_mode 지원
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import make_api_request

def quick_buy_test():
    """빠른 구매 테스트"""
    print("=" * 60)
    print("🛒 실제 구매 테스트 (long_short_mode)")
    print("=" * 60)
    
    # 1. 현재가 확인
    result = make_api_request('GET', '/api/v5/market/ticker', 
                               params={'instId': 'BTC-USDT-SWAP'})
    if result and result.get('code') == '0':
        price = float(result['data'][0]['last'])
        print(f"✅ BTC 현재가: ${price:,.2f}")
    else:
        print("❌ 가격 조회 실패")
        return
    
    # 2. 잔고 확인
    result = make_api_request('GET', '/api/v5/account/balance')
    if result and result.get('code') == '0':
        for bal in result['data'][0].get('details', []):
            if bal.get('ccy') == 'USDT':
                available = float(bal.get('availBal', 0))
                print(f"✅ USDT 잔고: ${available:.2f}")
                break
    
    # 3. 레버리지 설정 (long 포지션용)
    print("\n📊 레버리지 설정 (long)...")
    lever_data = {
        "instId": "BTC-USDT-SWAP",
        "lever": "1",
        "mgnMode": "cross",
        "posSide": "long"  # ← long_short_mode에서 필요!
    }
    result = make_api_request('POST', '/api/v5/account/set-leverage', data=lever_data)
    if result and result.get('code') == '0':
        print("✅ 레버리지 설정 성공")
    else:
        print(f"⚠️ 레버리지 설정: {result}")
    
    # 4. 주문 확인
    print("\n" + "=" * 60)
    print("⚠️ 실제 주문을 전송합니다!")
    print("=" * 60)
    print(f"상품: BTC-USDT-SWAP")
    print(f"방향: 매수 (롱 포지션)")
    print(f"수량: 0.01 계약 (약 ${price * 0.01:.2f})")
    print(f"레버리지: 1x")
    
    confirm = input("\n계속하시겠습니까? (yes 입력): ").strip().lower()
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    # 5. 실제 주문 전송 (long_short_mode용)
    order_data = {
        "instId": "BTC-USDT-SWAP",
        "tdMode": "cross",
        "side": "buy",
        "ordType": "market",
        "sz": "0.01",
        "posSide": "long"  # ← 핵심! net이 아니라 long
    }
    
    print(f"\n📤 주문 전송 중...")
    print(f"   {order_data}")
    
    result = make_api_request('POST', '/api/v5/trade/order', data=order_data)
    
    print(f"\n📥 응답:")
    print(f"   {result}")
    
    if result and result.get('code') == '0':
        order_id = result['data'][0].get('ordId')
        print(f"\n✅ 주문 성공!")
        print(f"   주문 ID: {order_id}")
        
        # 체결 확인
        import time
        time.sleep(2)
        
        status = make_api_request('GET', '/api/v5/trade/order',
                                   params={'instId': 'BTC-USDT-SWAP', 'ordId': order_id})
        if status and status.get('code') == '0':
            order = status['data'][0]
            print(f"\n📊 체결 정보:")
            print(f"   상태: {order.get('state')}")
            print(f"   체결가: ${float(order.get('avgPx') or 0):,.2f}")
            print(f"   체결량: {order.get('fillSz')}")
            print(f"   수수료: ${abs(float(order.get('fee') or 0)):.4f}")
        
        # 포지션 확인
        positions = make_api_request('GET', '/api/v5/account/positions',
                                      params={'instType': 'SWAP'})
        if positions and positions.get('code') == '0':
            print(f"\n📊 현재 포지션:")
            for pos in positions['data']:
                if float(pos.get('pos', 0)) != 0:
                    print(f"   {pos.get('instId')} {pos.get('posSide')}: {pos.get('pos')} @ ${float(pos.get('avgPx') or 0):,.2f}")
                    print(f"   미실현 손익: ${float(pos.get('upl') or 0):.2f}")
        
        return {'success': True, 'order_id': order_id}
    else:
        # 오류 상세
        if result and result.get('data'):
            error = result['data'][0]
            print(f"\n❌ 주문 실패!")
            print(f"   오류 코드: {error.get('sCode')}")
            print(f"   오류 메시지: {error.get('sMsg')}")
        else:
            print(f"\n❌ 주문 실패: {result}")
        
        return {'success': False}


def close_position_test():
    """포지션 청산 테스트"""
    print("\n" + "=" * 60)
    print("📤 포지션 청산")
    print("=" * 60)
    
    # 현재 포지션 확인
    positions = make_api_request('GET', '/api/v5/account/positions',
                                  params={'instType': 'SWAP'})
    
    if not positions or positions.get('code') != '0':
        print("❌ 포지션 조회 실패")
        return
    
    long_positions = []
    for pos in positions['data']:
        if pos.get('posSide') == 'long' and float(pos.get('pos', 0)) > 0:
            long_positions.append(pos)
    
    if not long_positions:
        print("청산할 롱 포지션이 없습니다.")
        return
    
    for pos in long_positions:
        print(f"\n포지션: {pos.get('instId')}")
        print(f"  수량: {pos.get('pos')}")
        print(f"  평균가: ${float(pos.get('avgPx') or 0):,.2f}")
        print(f"  미실현 손익: ${float(pos.get('upl') or 0):.2f}")
    
    confirm = input("\n청산하시겠습니까? (yes 입력): ").strip().lower()
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    # 청산 주문 (롱 포지션 → 매도)
    for pos in long_positions:
        close_data = {
            "instId": pos.get('instId'),
            "tdMode": "cross",
            "side": "sell",  # 롱 청산은 매도
            "ordType": "market",
            "sz": str(abs(float(pos.get('pos')))),
            "posSide": "long",  # 롱 포지션 청산
            "reduceOnly": "true"
        }
        
        print(f"\n📤 청산 주문: {close_data}")
        result = make_api_request('POST', '/api/v5/trade/order', data=close_data)
        
        if result and result.get('code') == '0':
            print(f"✅ 청산 성공!")
        else:
            print(f"❌ 청산 실패: {result}")


if __name__ == "__main__":
    print("선택:")
    print("  1. 구매 테스트 (롱 포지션 진입)")
    print("  2. 청산 테스트 (롱 포지션 종료)")
    print("  0. 종료")
    
    choice = input("\n선택: ").strip()
    
    if choice == '1':
        quick_buy_test()
    elif choice == '2':
        close_position_test()
    else:
        print("종료")
