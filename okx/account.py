# okx/account.py
"""
기본 Account 클래스 - account_manager.py를 상속받아 사용
"""

from okx.account_manager import AccountManager

# 기본 클래스로 AccountManager를 사용
Account = AccountManager

# 편의 함수들
def get_account():
    """계좌 인스턴스 반환"""
    return AccountManager()

def check_connection():
    """연결 상태 확인"""
    try:
        account = AccountManager()
        balances = account.get_account_balance()
        return balances is not None and len(balances) > 0
    except:
        return False