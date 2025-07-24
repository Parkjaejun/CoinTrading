"""
balance_test.py - 잔액 조회 테스트 스크립트
GUI 수정 후 제대로 작동하는지 확인용
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from okx.account_manager import AccountManager
from gui.balance_manager import GUIBalanceManager

def test_balance_parsing():
    """잔액 파싱 테스트"""
    print("=" * 50)
    print("🧪 잔액 파싱 테스트")
    print("=" * 50)
    
    try:
        # 1. AccountManager로 원본 데이터 조회
        print("1. 원본 데이터 조회...")
        account = AccountManager()
        raw_data = account.get_account_balance()
        
        if not raw_data:
            print("❌ 원본 데이터 조회 실패")
            return False
        
        print(f"✅ 원본 데이터 조회 성공")
        print(f"   데이터 타입: {type(raw_data)}")
        print(f"   주요 키들: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'N/A'}")
        
        # 2. GUIBalanceManager로 파싱
        print("\n2. GUI 방식으로 파싱...")
        parsed_data = GUIBalanceManager.parse_okx_balance(raw_data)
        
        print(f"✅ 파싱 완료")
        print(f"   파싱된 통화 수: {len([k for k in parsed_data.keys() if not k.startswith('_')])}")
        
        # 3. 주요 값들 추출
        print("\n3. 주요 값 추출...")
        usdt_balance = GUIBalanceManager.get_usdt_balance(parsed_data)
        total_equity = GUIBalanceManager.get_total_equity(parsed_data)
        
        print(f"💰 USDT 잔액: ${usdt_balance:.6f}")
        print(f"💰 총 자산: ${total_equity:.2f}")
        
        # 4. 상세 정보 출력
        print("\n4. 상세 잔액 정보:")
        for currency, info in parsed_data.items():
            if currency.startswith('_'):
                continue
            
            if isinstance(info, dict):
                total = info.get('total', 0)
                available = info.get('available', 0)
                frozen = info.get('frozen', 0)
                
                if total > 0.000001:
                    print(f"   {currency}:")
                    print(f"     총: {total:.6f}")
                    print(f"     사용가능: {available:.6f}")
                    if frozen > 0.000001:
                        print(f"     동결: {frozen:.6f}")
        
        # 5. 요약 문자열 테스트
        print("\n5. 요약 문자열:")
        summary = GUIBalanceManager.format_balance_summary(parsed_data)
        print(summary)
        
        print("\n🎉 모든 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_with_main():
    """main.py 방식과 비교"""
    print("\n" + "=" * 50)
    print("🔄 main.py와 비교 테스트")
    print("=" * 50)
    
    try:
        # GUI 방식
        print("1. GUI 방식으로 조회...")
        account = AccountManager()
        raw_data = account.get_account_balance()
        gui_parsed = GUIBalanceManager.parse_okx_balance(raw_data)
        gui_usdt = GUIBalanceManager.get_usdt_balance(gui_parsed)
        gui_equity = GUIBalanceManager.get_total_equity(gui_parsed)
        
        print(f"   GUI 방식 - USDT: ${gui_usdt:.6f}, 총 자산: ${gui_equity:.2f}")
        
        # 원본 방식 (main.py에서 사용하는 방식)
        print("2. 원본 방식으로 조회...")
        if raw_data and 'details' in raw_data:
            original_usdt = 0.0
            for detail in raw_data.get('details', []):
                if detail.get('ccy') == 'USDT':
                    avail_bal = detail.get('availBal', '0')
                    if avail_bal == '':
                        avail_bal = '0'
                    original_usdt = float(avail_bal)
                    break
            
            original_equity = raw_data.get('totalEq', '0')
            if original_equity == '':
                original_equity = '0'
            original_equity = float(original_equity)
            
            print(f"   원본 방식 - USDT: ${original_usdt:.6f}, 총 자산: ${original_equity:.2f}")
            
            # 비교
            print("3. 결과 비교:")
            usdt_match = abs(gui_usdt - original_usdt) < 0.000001
            equity_match = abs(gui_equity - original_equity) < 0.01
            
            print(f"   USDT 일치: {'✅' if usdt_match else '❌'}")
            print(f"   총 자산 일치: {'✅' if equity_match else '❌'}")
            
            if usdt_match and equity_match:
                print("🎉 GUI와 원본 방식 결과 일치!")
                return True
            else:
                print("⚠️ 결과 불일치 발견")
                return False
        else:
            print("❌ 원본 데이터 구조 문제")
            return False
            
    except Exception as e:
        print(f"❌ 비교 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """테스트 실행"""
    print("🔧 잔액 처리 통합 테스트")
    print(f"시간: {__import__('datetime').datetime.now()}")
    
    # 기본 파싱 테스트
    test1_result = test_balance_parsing()
    
    # 비교 테스트
    test2_result = compare_with_main()
    
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    print(f"파싱 테스트: {'✅ 통과' if test1_result else '❌ 실패'}")
    print(f"비교 테스트: {'✅ 통과' if test2_result else '❌ 실패'}")
    
    if test1_result and test2_result:
        print("\n🎉 모든 테스트 통과! GUI 실행 준비 완료")
        print("다음 명령으로 GUI를 실행하세요:")
        print("python run_gui.py")
    else:
        print("\n❌ 일부 테스트 실패. 설정을 확인해주세요.")
    
    return test1_result and test2_result

if __name__ == "__main__":
    main()