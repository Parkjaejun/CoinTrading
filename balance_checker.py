#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
향상된 OKX 잔고 확인 스크립트
- API 서명 오류 해결
- 자금계정/거래계정 모두 확인
- 입금 내역 조회
- 자동 이체 기능
"""

import time
from datetime import datetime
from config import (
    API_KEY, API_SECRET, PASSPHRASE,
    make_api_request, validate_config, test_api_connection
)

def check_comprehensive_balance():
    """종합적인 잔고 확인"""
    print("="*80)
    print("🔍 OKX 종합 잔고 확인 (API 서명 오류 해결 버전)")
    print("="*80)
    
    # 0. 설정 검증
    print("\n🔧 0단계: 설정 검증")
    print("-" * 40)
    if not validate_config():
        print("❌ API 설정이 올바르지 않습니다. config.py를 수정하세요.")
        return False
    
    print(f"✅ API 키 확인: {API_KEY[:8]}...{API_KEY[-4:]}")
    
    # 1. API 연결 테스트
    print("\n📡 1단계: API 연결 테스트")
    print("-" * 40)
    if not test_api_connection():
        print("❌ API 연결 실패. 네트워크나 API 키를 확인하세요.")
        return False
    
    # 2. 거래 계정 잔고 확인
    print("\n💰 2단계: 거래 계정 (Trading Account)")
    print("-" * 40)
    
    trading_usdt = 0
    try:
        trading_balance = make_api_request('GET', '/api/v5/account/balance')
        if trading_balance and trading_balance.get('data'):
            balance_data = trading_balance['data'][0]
            total_eq = balance_data.get('totalEq', '0')
            
            # 문자열이 비어있는 경우 처리
            if total_eq == '' or total_eq is None:
                total_eq = '0'
            
            print(f"총 자산: ${float(total_eq):,.2f}")
            
            print("\n거래계정 통화별 잔고:")
            has_trading_balance = False
            for detail in balance_data.get('details', []):
                ccy = detail['ccy']
                cash_bal = detail.get('cashBal', '0')
                avail_bal = detail.get('availBal', '0')
                
                # 빈 문자열 처리
                if cash_bal == '': cash_bal = '0'
                if avail_bal == '': avail_bal = '0'
                
                cash_bal = float(cash_bal)
                avail_bal = float(avail_bal)
                
                if cash_bal > 0.001:  # 0.001 이상만 표시
                    has_trading_balance = True
                    print(f"  {ccy:>8}: 총 {cash_bal:>12.6f} | 사용가능 {avail_bal:>12.6f}")
                    
                    if ccy == 'USDT':
                        trading_usdt = avail_bal
            
            if not has_trading_balance:
                print("  거래 계정에 잔고가 없습니다.")
        else:
            print("❌ 거래 계정 잔고 조회 실패")
    except Exception as e:
        print(f"❌ 거래 계정 오류: {e}")
    
    # 3. 자금 계정 잔고 확인  
    print("\n💰 3단계: 자금 계정 (Funding Account)")
    print("-" * 40)
    
    funding_usdt = 0
    try:
        funding_balance = make_api_request('GET', '/api/v5/asset/balances')
        if funding_balance and funding_balance.get('data'):
            print("자금계정 잔고:")
            has_funding_balance = False
            
            for balance in funding_balance['data']:
                ccy = balance['ccy']
                avail_bal = balance.get('availBal', '0')
                frozen_bal = balance.get('frozenBal', '0')
                
                # 빈 문자열 처리
                if avail_bal == '': avail_bal = '0'
                if frozen_bal == '': frozen_bal = '0'
                
                avail_bal = float(avail_bal)
                frozen_bal = float(frozen_bal)
                total_bal = avail_bal + frozen_bal
                
                if total_bal > 0.001:
                    has_funding_balance = True
                    print(f"  {ccy:>8}: 총 {total_bal:>12.6f} | 사용가능 {avail_bal:>12.6f} | 동결 {frozen_bal:>12.6f}")
                    
                    if ccy == 'USDT':
                        funding_usdt = avail_bal
            
            if not has_funding_balance:
                print("  자금 계정에 잔고가 없습니다.")
        else:
            print("❌ 자금 계정 잔고 조회 실패")
    except Exception as e:
        print(f"❌ 자금 계정 오류: {e}")
    
    # 4. 입금 내역 확인
    print("\n💰 4단계: 최근 입금 내역 (최근 20건)")
    print("-" * 40)
    
    try:
        deposit_history = make_api_request('GET', '/api/v5/asset/deposit-history', params={'limit': '20'})
        if deposit_history and deposit_history.get('data'):
            deposits = deposit_history['data']
            
            if deposits:
                print("최근 입금 내역:")
                tron_deposits = []
                
                for deposit in deposits:
                    ts = deposit.get('ts', '')
                    ccy = deposit.get('ccy', '')
                    amt = deposit.get('amt', '0')
                    state = deposit.get('state', '')
                    chain = deposit.get('chain', '')
                    
                    if ts:
                        dt = datetime.fromtimestamp(int(ts)/1000)
                        
                        status_map = {
                            '0': '⏳ 대기중',
                            '1': '🔄 입금 중', 
                            '2': '✅ 완료',
                            '8': '⏳ 대기중',
                            '12': '❌ 취소',
                            '13': '❌ 실패'
                        }
                        
                        status_text = status_map.get(state, f"상태: {state}")
                        
                        print(f"  {dt.strftime('%m-%d %H:%M')} | {ccy} {amt:>10} | {chain:>8} | {status_text}")
                        
                        # Tron 네트워크 USDT 입금 찾기
                        if chain.upper() in ['USDT-TRC20', 'TRC20', 'TRON'] and ccy == 'USDT':
                            tron_deposits.append({
                                'amount': float(amt),
                                'status': state,
                                'time': dt
                            })
                
                # Tron 입금 특별 분석
                if tron_deposits:
                    print(f"\n🟢 Tron 네트워크 USDT 입금 발견: {len(tron_deposits)}건")
                    for dep in tron_deposits:
                        status = '완료' if dep['status'] == '2' else '처리중/실패'
                        print(f"  💰 {dep['amount']} USDT | {status} | {dep['time'].strftime('%Y-%m-%d %H:%M')}")
            else:
                print("  최근 입금 내역이 없습니다.")
        else:
            print("  입금 내역 조회 실패 (권한 확인 필요)")
    except Exception as e:
        print(f"❌ 입금 내역 오류: {e}")
    
    # 5. 잔고 요약 및 권장사항
    print("\n📊 5단계: 잔고 요약 및 권장사항")
    print("-" * 40)
    
    total_usdt = trading_usdt + funding_usdt
    print(f"💰 USDT 총 잔고: ${total_usdt:.2f}")
    print(f"  - 거래계정: ${trading_usdt:.2f}")
    print(f"  - 자금계정: ${funding_usdt:.2f}")
    
    if total_usdt < 10:
        print("\n❌ 거래에 필요한 최소 자금이 부족합니다 (최소 $50 권장)")
        if funding_usdt > 0:
            print("💡 자금계정에서 거래계정으로 이체가 필요합니다!")
            print("   명령어: python transfer_funds.py")
        else:
            print("💡 OKX 웹사이트에서 입금 상태를 확인하세요:")
            print("   1. OKX 로그인 → 자산 → 개요")
            print("   2. 입금 → 내역에서 Tron 입금 확인")
            print("   3. 블록체인 확인이 완료되었는지 체크")
    elif funding_usdt > 10 and trading_usdt < 10:
        print("\n🔄 자금계정에서 거래계정으로 이체가 필요합니다!")
        print("   명령어: python transfer_funds.py")
    elif trading_usdt >= 10:
        print("\n✅ 거래 가능한 상태입니다!")
        print("   명령어: python main.py")
    
    # 6. 다음 단계 안내
    print("\n🚀 6단계: 다음 단계")
    print("-" * 40)
    
    if funding_usdt > 0:
        print("1️⃣ 자금 이체: python transfer_funds.py")
        print("2️⃣ 시스템 실행: python main.py")
    elif total_usdt < 10:
        print("1️⃣ OKX 웹사이트에서 입금 상태 확인")
        print("2️⃣ Tron 네트워크 확인 대기 (최대 30분)")
        print("3️⃣ 입금 완료 후 다시 실행: python balance_checker.py")
    else:
        print("1️⃣ 시스템 바로 실행: python main.py")
    
    return True

if __name__ == "__main__":
    try:
        check_comprehensive_balance()
    except KeyboardInterrupt:
        print("\n\n⏹️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        print("config.py 설정을 다시 확인해주세요.")