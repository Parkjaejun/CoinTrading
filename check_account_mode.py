#!/usr/bin/env python3
# check_account_mode.py
"""
OKX 계좌 설정 상세 확인 및 모드 변경
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import make_api_request

def check_account_details():
    """계좌 설정 상세 확인"""
    print("=" * 60)
    print("📋 OKX 계좌 설정 상세 확인")
    print("=" * 60)
    
    # 1. 계좌 설정 조회
    print("\n1️⃣ 계좌 설정 (account/config)")
    result = make_api_request('GET', '/api/v5/account/config')
    
    if result and result.get('code') == '0':
        config = result['data'][0]
        print(f"   계좌 레벨: {config.get('acctLv')}")
        print(f"   포지션 모드: {config.get('posMode')}")  # long_short_mode or net_mode
        print(f"   자동 차입: {config.get('autoLoan')}")
        print(f"   그리스 타입: {config.get('greeksType')}")
        print(f"   레벨: {config.get('level')}")
        print(f"   레벨 임시: {config.get('levelTmp')}")
        print(f"   계좌 타입: {config.get('ctIsoMode')}")
        print(f"   마진 타입: {config.get('mgnIsoMode')}")
        
        pos_mode = config.get('posMode')
    else:
        print(f"   ❌ 조회 실패: {result}")
        return
    
    # 2. 현재 포지션 확인
    print("\n2️⃣ 현재 포지션")
    positions = make_api_request('GET', '/api/v5/account/positions', 
                                  params={'instType': 'SWAP'})
    
    if positions and positions.get('code') == '0':
        pos_list = positions['data']
        if pos_list:
            for pos in pos_list:
                if float(pos.get('pos', 0)) != 0:
                    print(f"   📊 {pos.get('instId')}")
                    print(f"      posSide: {pos.get('posSide')}")
                    print(f"      수량: {pos.get('pos')}")
                    print(f"      평균가: {pos.get('avgPx')}")
        else:
            print("   포지션 없음")
    
    # 3. 레버리지 설정 확인
    print("\n3️⃣ BTC 레버리지 설정 확인")
    lever = make_api_request('GET', '/api/v5/account/leverage-info',
                              params={'instId': 'BTC-USDT-SWAP', 'mgnMode': 'cross'})
    
    if lever and lever.get('code') == '0':
        for lev in lever['data']:
            print(f"   instId: {lev.get('instId')}")
            print(f"   posSide: {lev.get('posSide')}")
            print(f"   lever: {lev.get('lever')}")
            print(f"   mgnMode: {lev.get('mgnMode')}")
            print()
    else:
        print(f"   조회 결과: {lever}")
    
    return pos_mode


def change_position_mode(new_mode):
    """
    포지션 모드 변경
    
    Args:
        new_mode: 'long_short_mode' (양방향) or 'net_mode' (단방향)
    """
    print(f"\n{'='*60}")
    print(f"🔄 포지션 모드 변경: {new_mode}")
    print(f"{'='*60}")
    
    # 주의: 포지션이 있으면 변경 불가!
    positions = make_api_request('GET', '/api/v5/account/positions',
                                  params={'instType': 'SWAP'})
    
    if positions and positions.get('code') == '0':
        for pos in positions['data']:
            if float(pos.get('pos', 0)) != 0:
                print(f"❌ 포지션이 있어서 모드 변경 불가!")
                print(f"   {pos.get('instId')}: {pos.get('pos')}")
                print(f"   먼저 모든 포지션을 청산하세요.")
                return False
    
    # 모드 변경
    result = make_api_request('POST', '/api/v5/account/set-position-mode',
                               data={'posMode': new_mode})
    
    if result and result.get('code') == '0':
        print(f"✅ 포지션 모드 변경 성공!")
        return True
    else:
        print(f"❌ 변경 실패: {result}")
        return False


def test_order_with_net_mode():
    """net_mode로 주문 테스트"""
    print("\n" + "=" * 60)
    print("🧪 net_mode 주문 테스트")
    print("=" * 60)
    
    order_data = {
        "instId": "BTC-USDT-SWAP",
        "tdMode": "cross",
        "side": "buy",
        "ordType": "market",
        "sz": "0.01",
        "posSide": "net"  # net_mode용
    }
    
    print(f"주문 데이터: {order_data}")
    
    confirm = input("\n주문을 전송하시겠습니까? (yes): ").strip().lower()
    if confirm != 'yes':
        return
    
    result = make_api_request('POST', '/api/v5/trade/order', data=order_data)
    print(f"\n응답: {result}")
    
    if result and result.get('code') == '0':
        print("✅ 주문 성공!")
    else:
        if result and result.get('data'):
            error = result['data'][0]
            print(f"❌ 오류: [{error.get('sCode')}] {error.get('sMsg')}")


def test_order_with_long_short_mode():
    """long_short_mode로 주문 테스트"""
    print("\n" + "=" * 60)
    print("🧪 long_short_mode 주문 테스트")
    print("=" * 60)
    
    order_data = {
        "instId": "BTC-USDT-SWAP",
        "tdMode": "cross",
        "side": "buy",
        "ordType": "market",
        "sz": "0.01",
        "posSide": "long"  # long_short_mode용
    }
    
    print(f"주문 데이터: {order_data}")
    
    confirm = input("\n주문을 전송하시겠습니까? (yes): ").strip().lower()
    if confirm != 'yes':
        return
    
    result = make_api_request('POST', '/api/v5/trade/order', data=order_data)
    print(f"\n응답: {result}")
    
    if result and result.get('code') == '0':
        print("✅ 주문 성공!")
    else:
        if result and result.get('data'):
            error = result['data'][0]
            print(f"❌ 오류: [{error.get('sCode')}] {error.get('sMsg')}")


if __name__ == "__main__":
    # 1. 먼저 현재 설정 확인
    pos_mode = check_account_details()
    
    print("\n" + "=" * 60)
    print("📌 다음 중 선택하세요:")
    print("=" * 60)
    print(f"현재 포지션 모드: {pos_mode}")
    print()
    print("  1. net_mode로 변경 (단방향 - posSide='net' 사용)")
    print("  2. long_short_mode로 변경 (양방향 - posSide='long'/'short' 사용)")
    print("  3. net_mode로 주문 테스트")
    print("  4. long_short_mode로 주문 테스트")
    print("  0. 종료")
    
    choice = input("\n선택: ").strip()
    
    if choice == '1':
        change_position_mode('net_mode')
    elif choice == '2':
        change_position_mode('long_short_mode')
    elif choice == '3':
        test_order_with_net_mode()
    elif choice == '4':
        test_order_with_long_short_mode()
    else:
        print("종료")
