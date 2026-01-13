#!/usr/bin/env python3
# verify_and_order.py
"""
계좌 모드 확인 후 올바른 방식으로 주문
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import make_api_request

def main():
    print("=" * 60)
    print("🔍 계좌 모드 확인 및 주문 테스트")
    print("=" * 60)
    
    # 1. 현재 계좌 모드 확인
    print("\n1️⃣ 현재 계좌 설정 확인...")
    result = make_api_request('GET', '/api/v5/account/config')
    
    if not result or result.get('code') != '0':
        print(f"❌ 계좌 설정 조회 실패: {result}")
        return
    
    config = result['data'][0]
    pos_mode = config.get('posMode')
    print(f"   포지션 모드: {pos_mode}")
    
    # 2. 모드에 따라 posSide 결정
    if pos_mode == 'net_mode':
        pos_side = 'net'
        print(f"   ✅ net_mode → posSide='net' 사용")
    else:  # long_short_mode
        pos_side = 'long'
        print(f"   ✅ long_short_mode → posSide='long' 사용")
    
    # 3. 가격 확인
    print("\n2️⃣ BTC 가격 확인...")
    result = make_api_request('GET', '/api/v5/market/ticker', 
                               params={'instId': 'BTC-USDT-SWAP'})
    if result and result.get('code') == '0':
        price = float(result['data'][0]['last'])
        print(f"   현재가: ${price:,.2f}")
    else:
        print("❌ 가격 조회 실패")
        return
    
    # 4. 잔고 확인
    print("\n3️⃣ USDT 잔고 확인...")
    result = make_api_request('GET', '/api/v5/account/balance')
    if result and result.get('code') == '0':
        for bal in result['data'][0].get('details', []):
            if bal.get('ccy') == 'USDT':
                available = float(bal.get('availBal', 0))
                print(f"   사용 가능: ${available:.2f}")
                break
    
    # 5. 레버리지 설정
    print("\n4️⃣ 레버리지 설정...")
    lever_data = {
        "instId": "BTC-USDT-SWAP",
        "lever": "1",
        "mgnMode": "cross"
    }
    # long_short_mode에서는 posSide 필요
    if pos_mode == 'long_short_mode':
        lever_data["posSide"] = "long"
    
    result = make_api_request('POST', '/api/v5/account/set-leverage', data=lever_data)
    if result and result.get('code') == '0':
        print(f"   ✅ 레버리지 설정 성공")
    else:
        print(f"   ⚠️ 레버리지 응답: {result}")
    
    # 6. 주문 데이터 구성
    order_data = {
        "instId": "BTC-USDT-SWAP",
        "tdMode": "cross",
        "side": "buy",
        "ordType": "market",
        "sz": "0.01",
        "posSide": pos_side
    }
    
    print("\n" + "=" * 60)
    print("⚠️ 주문 정보")
    print("=" * 60)
    print(f"포지션 모드: {pos_mode}")
    print(f"주문 데이터: {order_data}")
    print(f"예상 금액: ${price * 0.01:.2f}")
    
    confirm = input("\n주문을 전송하시겠습니까? (yes): ").strip().lower()
    if confirm != 'yes':
        print("취소됨")
        return
    
    # 7. 주문 전송
    print("\n5️⃣ 주문 전송...")
    result = make_api_request('POST', '/api/v5/trade/order', data=order_data)
    
    print(f"\n📥 응답: {result}")
    
    if result and result.get('code') == '0':
        order_id = result['data'][0].get('ordId')
        print(f"\n🎉 주문 성공!")
        print(f"   주문 ID: {order_id}")
        
        # 체결 확인
        time.sleep(2)
        status = make_api_request('GET', '/api/v5/trade/order',
                                   params={'instId': 'BTC-USDT-SWAP', 'ordId': order_id})
        if status and status.get('code') == '0':
            order = status['data'][0]
            print(f"\n📊 체결 정보:")
            print(f"   상태: {order.get('state')}")
            print(f"   체결가: ${float(order.get('avgPx') or 0):,.2f}")
            print(f"   수수료: ${abs(float(order.get('fee') or 0)):.6f}")
    else:
        # 상세 오류
        if result and result.get('data'):
            error = result['data'][0]
            s_code = error.get('sCode')
            s_msg = error.get('sMsg')
            print(f"\n❌ 주문 실패!")
            print(f"   오류 코드: {s_code}")
            print(f"   오류 메시지: {s_msg}")
            
            # 51010 오류 추가 디버깅
            if s_code == '51010':
                print(f"\n🔍 추가 디버깅...")
                print(f"   현재 posMode: {pos_mode}")
                print(f"   사용한 posSide: {pos_side}")
                
                # 다른 posSide로 시도
                if pos_side == 'net':
                    print(f"\n   → 'long'으로 재시도...")
                    order_data['posSide'] = 'long'
                else:
                    print(f"\n   → 'net'으로 재시도...")
                    order_data['posSide'] = 'net'
                
                retry = input("다른 posSide로 재시도하시겠습니까? (yes): ").strip().lower()
                if retry == 'yes':
                    result2 = make_api_request('POST', '/api/v5/trade/order', data=order_data)
                    print(f"\n📥 재시도 응답: {result2}")


if __name__ == "__main__":
    main()
