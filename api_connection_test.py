#!/usr/bin/env python3
# api_test.py
"""
API 연결 문제 진단 및 해결 스크립트
"""

import requests
import json
from config import API_KEY, API_SECRET, PASSPHRASE, make_api_request

def test_public_api():
    """공개 API 테스트 (인증 불필요)"""
    print("🔍 1. 공개 API 테스트 (인증 없음)")
    print("-" * 40)
    
    try:
        # 서버 시간 조회
        response = requests.get("https://www.okx.com/api/v5/public/time", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 서버 시간: {data['data'][0]['ts']}")
        else:
            print(f"❌ 서버 시간 조회 실패: {response.status_code}")
            return False
        
        # BTC 가격 조회
        response = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['code'] == '0':
                price = float(data['data'][0]['last'])
                print(f"✅ BTC 현재가: ${price:,.2f}")
                return True
            else:
                print(f"❌ BTC 가격 조회 실패: {data['msg']}")
                return False
        else:
            print(f"❌ BTC 가격 HTTP 오류: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 공개 API 테스트 실패: {e}")
        return False

def test_private_api():
    """인증 API 테스트"""
    print("\n🔐 2. 인증 API 테스트")
    print("-" * 40)
    
    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"Secret Key: {API_SECRET[:8]}...{API_SECRET[-4:]}")
    print(f"Passphrase: {'*' * len(PASSPHRASE)}")
    
    try:
        # 계좌 설정 조회 (가장 간단한 인증 API)
        result = make_api_request('GET', '/api/v5/account/config')
        
        if result:
            if result.get('code') == '0':
                print("✅ API 인증 성공!")
                config_data = result['data'][0]
                print(f"  계좌 레벨: {config_data.get('acctLv', 'Unknown')}")
                print(f"  포지션 모드: {config_data.get('posMode', 'Unknown')}")
                return True
            else:
                print(f"❌ API 응답 오류: {result.get('msg', 'Unknown')}")
                return False
        else:
            print("❌ API 요청 실패 - make_api_request에서 None 반환")
            return False
            
    except Exception as e:
        print(f"❌ 인증 API 테스트 실패: {e}")
        return False

def test_balance_api():
    """잔액 API 테스트"""
    print("\n💰 3. 잔액 API 테스트")
    print("-" * 40)
    
    try:
        from okx.account_manager import AccountManager
        
        account = AccountManager()
        balance = account.get_account_balance()
        
        if balance:
            total_eq = balance.get('totalEq', '0')
            if total_eq == '':
                total_eq = '0'
            
            print(f"✅ 총 자산: ${float(total_eq):,.2f}")
            
            # USDT 잔액 확인
            for detail in balance.get('details', []):
                if detail['ccy'] == 'USDT':
                    usdt_bal = float(detail.get('availBal', '0') or '0')
                    print(f"✅ USDT 사용가능: ${usdt_bal:.6f}")
                    break
            else:
                print("⚠️ USDT 잔액 없음")
            
            return True
        else:
            print("❌ 잔액 조회 실패")
            return False
            
    except Exception as e:
        print(f"❌ 잔액 API 테스트 실패: {e}")
        return False

def main():
    """종합 API 테스트"""
    print("🧪 OKX API 연결 종합 테스트")
    print("=" * 50)
    
    results = []
    
    # 1. 공개 API 테스트
    results.append(test_public_api())
    
    # 2. 인증 API 테스트
    results.append(test_private_api())
    
    # 3. 잔액 API 테스트
    results.append(test_balance_api())
    
    # 결과 요약
    print("\n📊 테스트 결과 요약")
    print("=" * 50)
    test_names = ["공개 API", "인증 API", "잔액 API"]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{i+1}. {name}: {status}")
    
    all_passed = all(results)
    
    if all_passed:
        print("\n🎉 모든 API 테스트 통과!")
        print("GUI에서 실제 데이터를 볼 수 있어야 합니다.")
    else:
        print("\n⚠️ 일부 API 테스트 실패")
        print("실패한 부분을 확인하고 config.py를 점검하세요.")
        
        if not results[0]:
            print("\n🔧 네트워크 연결 문제:")
            print("  - 인터넷 연결 확인")
            print("  - VPN 사용 시 해제")
            print("  - 방화벽 설정 확인")
        
        if not results[1]:
            print("\n🔧 API 인증 문제:")
            print("  - config.py의 API 키 재확인")
            print("  - OKX에서 새 API 키 생성")
            print("  - 대소문자 정확히 입력")
            print("  - IP 화이트리스트 설정")

if __name__ == "__main__":
    main()