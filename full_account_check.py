#!/usr/bin/env python3
# full_account_check.py
"""
OKX 계좌 전체 설정 확인 및 문제 진단
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import make_api_request

def check_everything():
    print("=" * 70)
    print("🔍 OKX 계좌 전체 진단")
    print("=" * 70)
    
    # 1. 계좌 설정 전체 출력
    print("\n" + "=" * 70)
    print("1️⃣ 계좌 설정 (전체 필드)")
    print("=" * 70)
    
    result = make_api_request('GET', '/api/v5/account/config')
    if result and result.get('code') == '0':
        config = result['data'][0]
        for key, value in config.items():
            print(f"   {key}: {value}")
        
        acct_lv = config.get('acctLv')
        pos_mode = config.get('posMode')
    else:
        print(f"❌ 실패: {result}")
        return
    
    # 2. 계좌 레벨 확인
    print("\n" + "=" * 70)
    print("2️⃣ 계좌 레벨 해석")
    print("=" * 70)
    
    acct_levels = {
        '1': 'Simple Mode (단순 거래) - SPOT만 가능, SWAP 불가!',
        '2': 'Single-currency Margin (단일 통화 마진) - SWAP 가능',
        '3': 'Multi-currency Margin (다중 통화 마진) - SWAP 가능',
        '4': 'Portfolio Margin (포트폴리오 마진) - SWAP 가능'
    }
    
    level_desc = acct_levels.get(acct_lv, '알 수 없음')
    print(f"   현재 레벨: {acct_lv}")
    print(f"   설명: {level_desc}")
    
    if acct_lv == '1':
        print("\n   ⚠️ Simple Mode에서는 선물(SWAP) 거래가 불가능합니다!")
        print("   💡 OKX 앱/웹에서 계좌 모드를 변경해야 합니다.")
        print("\n   변경 방법:")
        print("   1. OKX 앱 또는 웹 로그인")
        print("   2. 설정 → 계좌 모드 (Account Mode)")
        print("   3. 'Single-currency margin' 또는 'Multi-currency margin' 선택")
        print("   4. 확인 후 다시 시도")
    
    # 3. 거래 가능한 상품 타입 확인
    print("\n" + "=" * 70)
    print("3️⃣ SPOT(현물) 거래 테스트")
    print("=" * 70)
    
    # 현물 가격 확인
    result = make_api_request('GET', '/api/v5/market/ticker',
                               params={'instId': 'BTC-USDT'})
    if result and result.get('code') == '0':
        price = float(result['data'][0]['last'])
        print(f"   ✅ BTC-USDT 현재가: ${price:,.2f}")
    else:
        print(f"   ❌ 현물 가격 조회 실패")
    
    # 4. 현물 주문 테스트 (소액)
    print("\n" + "=" * 70)
    print("4️⃣ 현물(SPOT) 주문 테스트")
    print("=" * 70)
    
    # 현물은 tdMode가 'cash'
    spot_order = {
        "instId": "BTC-USDT",
        "tdMode": "cash",  # 현물은 cash!
        "side": "buy",
        "ordType": "market",
        "sz": "10",  # 10 USDT 어치 (tgtCcy 사용 시)
        "tgtCcy": "quote_ccy"  # quote 통화(USDT) 기준으로 주문
    }
    
    print(f"   주문 데이터: {spot_order}")
    print(f"   (약 $10 USDT 어치 BTC 매수)")
    
    test_spot = input("\n   현물 주문을 테스트하시겠습니까? (yes): ").strip().lower()
    if test_spot == 'yes':
        result = make_api_request('POST', '/api/v5/trade/order', data=spot_order)
        print(f"\n   📥 응답: {result}")
        
        if result and result.get('code') == '0':
            print(f"   ✅ 현물 주문 성공!")
        else:
            if result and result.get('data'):
                error = result['data'][0]
                print(f"   ❌ 오류: [{error.get('sCode')}] {error.get('sMsg')}")
    
    # 5. API 권한 확인
    print("\n" + "=" * 70)
    print("5️⃣ API 권한 확인")
    print("=" * 70)
    
    # 주문 내역 조회로 권한 테스트
    result = make_api_request('GET', '/api/v5/trade/orders-history',
                               params={'instType': 'SPOT', 'limit': '1'})
    if result and result.get('code') == '0':
        print("   ✅ 거래 권한: 있음")
    else:
        print(f"   ❌ 거래 권한 확인 실패: {result}")
    
    # 6. 결론
    print("\n" + "=" * 70)
    print("📋 진단 결과")
    print("=" * 70)
    
    if acct_lv == '1':
        print("""
   ❌ 문제 발견: Simple Mode (acctLv=1)
   
   Simple Mode에서는 선물(SWAP) 거래가 불가능합니다.
   현물(SPOT) 거래만 가능합니다.
   
   🔧 해결 방법:
   
   1. OKX 웹사이트 또는 앱에 로그인
   2. 우측 상단 프로필 → 'Account mode' 클릭
   3. 'Single-currency margin' 선택
   4. 약관 동의 후 변경
   5. 다시 테스트
   
   또는 현물(SPOT) 거래로 테스트하세요.
        """)
    else:
        print(f"""
   계좌 레벨: {acct_lv} - SWAP 거래 가능
   포지션 모드: {pos_mode}
   
   다른 문제가 있을 수 있습니다.
   OKX 고객센터에 문의하거나 웹에서 직접 거래를 테스트해보세요.
        """)


if __name__ == "__main__":
    check_everything()
