#!/usr/bin/env python3
# debug_order_test.py
"""
주문 API 디버깅 테스트
API 요청/응답을 상세히 출력하여 문제 파악
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_order_debug():
    """주문 API 상세 디버깅"""
    print("=" * 60)
    print("🔍 주문 API 디버깅 테스트")
    print("=" * 60)
    
    # 1. config 로드
    print("\n📋 1단계: 설정 로드")
    try:
        from config import API_KEY, API_SECRET, PASSPHRASE, make_api_request
        print(f"  ✅ API_KEY: {API_KEY[:8]}...{API_KEY[-4:]}")
        print(f"  ✅ API_SECRET: {API_SECRET[:8]}...{API_SECRET[-4:]}")
        print(f"  ✅ PASSPHRASE: {'*' * len(PASSPHRASE)}")
    except ImportError as e:
        print(f"  ❌ config.py 로드 실패: {e}")
        return
    
    # 2. 공개 API 테스트 (인증 불필요)
    print("\n📋 2단계: 공개 API 테스트")
    try:
        import requests
        response = requests.get(
            "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                price = float(data['data'][0]['last'])
                print(f"  ✅ BTC 현재가: ${price:,.2f}")
            else:
                print(f"  ❌ API 오류: {data.get('msg')}")
        else:
            print(f"  ❌ HTTP 오류: {response.status_code}")
    except Exception as e:
        print(f"  ❌ 공개 API 실패: {e}")
        return
    
    # 3. 인증 API 테스트 (계좌 설정)
    print("\n📋 3단계: 인증 API 테스트")
    try:
        result = make_api_request('GET', '/api/v5/account/config')
        if result:
            if result.get('code') == '0':
                print(f"  ✅ 인증 성공!")
                config_data = result['data'][0]
                print(f"  계좌 레벨: {config_data.get('acctLv')}")
                print(f"  포지션 모드: {config_data.get('posMode')}")
            else:
                print(f"  ❌ API 오류: [{result.get('code')}] {result.get('msg')}")
                return
        else:
            print(f"  ❌ API 응답 없음 (None)")
            return
    except Exception as e:
        print(f"  ❌ 인증 API 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. 잔고 확인
    print("\n📋 4단계: 잔고 확인")
    try:
        result = make_api_request('GET', '/api/v5/account/balance')
        if result and result.get('code') == '0':
            balances = result['data'][0].get('details', [])
            for bal in balances:
                if bal.get('ccy') == 'USDT':
                    available = float(bal.get('availBal', 0))
                    print(f"  ✅ USDT 잔고: ${available:.2f}")
                    if available < 10:
                        print(f"  ⚠️ 잔고 부족! 최소 $10 필요")
                    break
            else:
                print(f"  ⚠️ USDT 잔고 없음")
        else:
            print(f"  ❌ 잔고 조회 실패")
    except Exception as e:
        print(f"  ❌ 잔고 조회 예외: {e}")
    
    # 5. 상품 정보 확인
    print("\n📋 5단계: 상품 정보 확인")
    try:
        result = make_api_request('GET', '/api/v5/public/instruments', 
                                  params={'instType': 'SWAP', 'instId': 'BTC-USDT-SWAP'})
        if result and result.get('code') == '0':
            inst = result['data'][0]
            print(f"  ✅ 상품: {inst.get('instId')}")
            print(f"  최소 수량: {inst.get('minSz')}")
            print(f"  계약 가치: {inst.get('ctVal')}")
            print(f"  상태: {inst.get('state')}")
            
            min_sz = float(inst.get('minSz', 1))
            ct_val = float(inst.get('ctVal', 0.01))
        else:
            print(f"  ❌ 상품 정보 조회 실패")
            return
    except Exception as e:
        print(f"  ❌ 상품 정보 예외: {e}")
        return
    
    # 6. 레버리지 설정 테스트
    print("\n📋 6단계: 레버리지 설정 테스트")
    try:
        lever_data = {
            "instId": "BTC-USDT-SWAP",
            "lever": "1",
            "mgnMode": "cross"
        }
        result = make_api_request('POST', '/api/v5/account/set-leverage', data=lever_data)
        print(f"  📤 요청: {lever_data}")
        print(f"  📥 응답: {result}")
        
        if result:
            if result.get('code') == '0':
                print(f"  ✅ 레버리지 설정 성공")
            else:
                print(f"  ❌ 레버리지 설정 실패: [{result.get('code')}] {result.get('msg')}")
        else:
            print(f"  ❌ 레버리지 API 응답 없음")
    except Exception as e:
        print(f"  ❌ 레버리지 설정 예외: {e}")
        import traceback
        traceback.print_exc()
    
    # 7. 주문 테스트 (실제 주문!)
    print("\n📋 7단계: 주문 API 테스트")
    print("⚠️ 이 단계는 실제 주문을 전송합니다!")
    
    confirm = input("\n실제 주문을 테스트하시겠습니까? (yes 입력): ").strip().lower()
    if confirm != 'yes':
        print("주문 테스트를 건너뜁니다.")
        return
    
    try:
        # 최소 주문 수량 계산
        order_size = max(min_sz, 1)  # 최소 1계약
        
        order_data = {
            "instId": "BTC-USDT-SWAP",
            "tdMode": "cross",
            "side": "buy",
            "ordType": "market",
            "sz": str(order_size),
            "posSide": "net"
        }
        
        print(f"\n  📤 주문 요청:")
        print(f"     {order_data}")
        
        result = make_api_request('POST', '/api/v5/trade/order', data=order_data)
        
        print(f"\n  📥 주문 응답:")
        print(f"     {result}")
        
        if result:
            if result.get('code') == '0':
                order_info = result['data'][0]
                order_id = order_info.get('ordId')
                print(f"\n  ✅ 주문 성공!")
                print(f"  주문 ID: {order_id}")
                
                # 주문 상태 확인
                import time
                time.sleep(2)
                
                status_result = make_api_request('GET', '/api/v5/trade/order',
                                                  params={'instId': 'BTC-USDT-SWAP', 'ordId': order_id})
                if status_result and status_result.get('code') == '0':
                    status_data = status_result['data'][0]
                    print(f"  상태: {status_data.get('state')}")
                    print(f"  체결 수량: {status_data.get('fillSz')}")
                    print(f"  체결 가격: {status_data.get('avgPx')}")
            else:
                error_code = result.get('code')
                error_msg = result.get('msg')
                print(f"\n  ❌ 주문 실패!")
                print(f"  오류 코드: {error_code}")
                print(f"  오류 메시지: {error_msg}")
                
                # 오류 코드별 해결책
                if error_code == '51000':
                    print(f"\n  💡 해결책: 잔고가 부족합니다. USDT를 충전하세요.")
                elif error_code == '51001':
                    print(f"\n  💡 해결책: 주문 수량이 잘못되었습니다. 최소 {min_sz} 이상 필요.")
                elif error_code == '51008':
                    print(f"\n  💡 해결책: 주문 금액이 최소 금액보다 작습니다.")
                elif error_code == '51010':
                    print(f"\n  💡 해결책: 계좌에 충분한 증거금이 없습니다.")
                elif error_code == '50014':
                    print(f"\n  💡 해결책: API 권한이 없습니다. OKX에서 '거래' 권한을 활성화하세요.")
                elif error_code == '59000':
                    print(f"\n  💡 해결책: 이 상품은 거래 불가합니다.")
                else:
                    print(f"\n  💡 OKX 오류 코드 확인: https://www.okx.com/docs-v5/en/#error-code")
        else:
            print(f"\n  ❌ API 응답 없음 (None)")
            print(f"\n  💡 가능한 원인:")
            print(f"     1. 네트워크 연결 문제")
            print(f"     2. API 요청 타임아웃")
            print(f"     3. make_api_request 함수 내부 오류")
            
            # make_api_request 함수 직접 디버깅
            print(f"\n  🔍 직접 API 요청 시도...")
            import hmac
            import hashlib
            import base64
            import json
            from datetime import datetime
            
            timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.') + \
                        datetime.utcnow().strftime('%f')[:3] + 'Z'
            
            body = json.dumps(order_data, separators=(',', ':'))
            request_path = '/api/v5/trade/order'
            
            message = timestamp + 'POST' + request_path + body
            signature = base64.b64encode(
                hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).digest()
            ).decode()
            
            headers = {
                'OK-ACCESS-KEY': API_KEY,
                'OK-ACCESS-SIGN': signature,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': PASSPHRASE,
                'Content-Type': 'application/json'
            }
            
            print(f"  Timestamp: {timestamp}")
            print(f"  Body: {body}")
            
            response = requests.post(
                'https://www.okx.com/api/v5/trade/order',
                headers=headers,
                data=body,
                timeout=10
            )
            
            print(f"\n  HTTP 상태: {response.status_code}")
            print(f"  응답: {response.text}")
            
    except Exception as e:
        print(f"  ❌ 주문 테스트 예외: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("디버깅 테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    test_order_debug()
