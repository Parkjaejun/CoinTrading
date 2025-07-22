"""
단순화된 테스트 스크립트
핵심 기능만 테스트
"""

import sys
from datetime import datetime
from okx.account import AccountManager

def test_api_connection():
    """기본 API 연결 테스트"""
    print("=" * 40)
    print("OKX API 연결 테스트")
    print("=" * 40)
    
    try:
        account = AccountManager()
        
        # 계좌 조회
        print("1. 계좌 정보 조회...")
        balances = account.get_account_balance()
        
        if balances:
            print("✅ API 연결 성공")
            for currency, balance in balances.items():
                if balance['total'] > 0:
                    print(f"   {currency}: {balance['total']:.4f}")
        else:
            print("❌ API 연결 실패")
            return False
        
        # 수수료 조회
        print("\n2. 수수료율 조회...")
        fees = account.get_trading_fee_rate()
        print(f"   Maker: {fees['maker_fee']*100:.3f}%")
        print(f"   Taker: {fees['taker_fee']*100:.3f}%")
        
        print("\n🎉 테스트 완료 - API 정상 작동")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

def main():
    """테스트 실행"""
    print("🧪 단순화된 시스템 테스트")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_api_connection()
    
    if success:
        print("\n✅ 기본 테스트 통과")
        print("main.py를 실행하여 트레이딩을 시작할 수 있습니다.")
    else:
        print("\n❌ 테스트 실패")
        print("config.py의 API 설정을 확인해주세요.")

if __name__ == "__main__":
    main()