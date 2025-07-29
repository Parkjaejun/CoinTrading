# balance_debug.py
"""
OKX 잔고 API 응답 구조 디버깅 스크립트
실제 응답 데이터를 출력해서 'bal' 키 문제를 해결
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_balance_response():
    """잔고 API 응답 구조 디버깅"""
    print("🔍 OKX 잔고 API 응답 구조 디버깅")
    print("=" * 60)
    
    try:
        from config import make_api_request
        
        print("📡 OKX 잔고 API 호출 중...")
        
        # 실제 잔고 API 호출
        response = make_api_request('GET', '/api/v5/account/balance')
        
        if response:
            print("✅ API 호출 성공!")
            print(f"⏰ 응답 시간: {datetime.now().strftime('%H:%M:%S')}")
            
            # 전체 응답 구조 출력
            print("\n📋 전체 응답 구조:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            
            # 코드 확인
            if response.get('code') == '0':
                print("\n✅ API 응답 성공 (code: '0')")
                
                # 데이터 구조 분석
                data = response.get('data', [])
                if data:
                    balance_info = data[0]
                    print(f"\n📊 잔고 정보 최상위 키들: {list(balance_info.keys())}")
                    
                    # 각 키의 값 타입과 내용 확인
                    for key, value in balance_info.items():
                        print(f"  {key}: {type(value)} = {value}")
                    
                    # details 배열 구조 확인
                    details = balance_info.get('details', [])
                    if details:
                        print(f"\n💰 details 배열 크기: {len(details)}")
                        print("첫 번째 detail 구조:")
                        first_detail = details[0]
                        print(json.dumps(first_detail, indent=4, ensure_ascii=False))
                        
                        # 모든 통화별 잔고 출력
                        print(f"\n💱 모든 통화 잔고 (총 {len(details)}개):")
                        for i, detail in enumerate(details):
                            currency = detail.get('ccy', 'UNKNOWN')
                            
                            # 가능한 잔고 키들 확인
                            possible_balance_keys = ['bal', 'balance', 'totalBal', 'available', 'availBal']
                            balance_values = {}
                            
                            for key in possible_balance_keys:
                                if key in detail:
                                    balance_values[key] = detail[key]
                            
                            print(f"  {i+1}. {currency}: {balance_values}")
                            
                            # 첫 번째 non-zero 잔고의 모든 키 출력
                            if any(float(v or 0) > 0 for v in balance_values.values()) and i < 3:
                                print(f"     전체 키들: {list(detail.keys())}")
                    else:
                        print("❌ details 배열이 비어있음")
                else:
                    print("❌ data 배열이 비어있음")
            else:
                error_msg = response.get('msg', 'Unknown error')
                print(f"❌ API 응답 오류: {error_msg}")
                
        else:
            print("❌ API 호출 실패 - None 응답")
            
    except Exception as e:
        print(f"❌ 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()

def test_account_manager():
    """AccountManager 클래스 디버깅"""
    print("\n🔧 AccountManager 클래스 디버깅")
    print("=" * 60)
    
    try:
        from okx.account_manager import AccountManager
        
        account = AccountManager()
        print("✅ AccountManager 초기화 성공")
        
        # get_account_balance 메서드 테스트
        print("\n📊 get_account_balance() 메서드 테스트...")
        balance_result = account.get_account_balance()
        
        if balance_result:
            print("✅ get_account_balance() 성공")
            print(f"반환 타입: {type(balance_result)}")
            
            if isinstance(balance_result, dict):
                print(f"최상위 키들: {list(balance_result.keys())}")
                
                # 파싱된 결과 확인
                if 'details' in balance_result:
                    details = balance_result['details']
                    print(f"details 길이: {len(details)}")
                    
                    for detail in details[:3]:  # 처음 3개만
                        currency = detail.get('ccy', 'Unknown')
                        print(f"  {currency}: {detail}")
                else:
                    print("details 키가 없음")
            else:
                print(f"예상외 반환 타입: {balance_result}")
        else:
            print("❌ get_account_balance() 실패 - None 반환")
            
    except Exception as e:
        print(f"❌ AccountManager 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def suggest_fixes():
    """수정 제안"""
    print("\n🛠️ 수정 제안")
    print("=" * 60)
    
    print("1. 'bal' 키 문제 해결:")
    print("   - OKX API에서 잔고 키가 'bal' 대신 다른 이름일 수 있음")
    print("   - 'availBal', 'totalBal', 'balance' 등을 확인")
    print("   - 위 디버깅 결과를 보고 정확한 키 이름 확인")
    
    print("\n2. AccountManager 수정:")
    print("   - get_account_balance() 메서드의 응답 파싱 로직 수정")
    print("   - 올바른 키 이름으로 변경")
    
    print("\n3. 테스트 코드 수정:")
    print("   - connection_test.py의 잔고 파싱 부분 수정")
    print("   - 실제 API 응답 구조에 맞게 조정")

def main():
    """메인 실행 함수"""
    print("🚀 OKX 잔고 API 디버깅 시작")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 원본 API 응답 디버깅
    debug_balance_response()
    
    # 2. AccountManager 디버깅
    test_account_manager()
    
    # 3. 수정 제안
    suggest_fixes()
    
    print("\n✅ 디버깅 완료!")
    print("위 결과를 바탕으로 connection_test.py를 수정하세요.")

if __name__ == "__main__":
    main()