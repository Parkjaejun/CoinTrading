from config import make_api_request
from utils.logger import log_system, log_error

def get_trading_account_balance() -> dict:
    """거래 계정 잔액 조회 (balance_checker.py와 동일한 방식)"""
    try:
        log_system("실제 거래 계정 잔액 조회 중...")
        
        # balance_checker.py와 동일한 API 호출
        trading_balance = make_api_request('GET', '/api/v5/account/balance')
        
        if not trading_balance or trading_balance.get('code') != '0':
            log_error("거래 계정 잔고 조회 실패")
            return {}
        
        data = trading_balance.get('data')
        if not data:
            log_error("거래 계정 데이터 없음")
            return {}
        
        balance_data = data[0]
        balances = {}
        
        # 각 통화별 잔액 파싱
        for detail in balance_data.get('details', []):
            ccy = detail['ccy']
            cash_bal = detail.get('cashBal', '0')
            avail_bal = detail.get('availBal', '0')
            
            # 빈 문자열 처리 (balance_checker.py와 동일)
            if cash_bal == '': 
                cash_bal = '0'
            if avail_bal == '': 
                avail_bal = '0'
            
            cash_bal = float(cash_bal)
            avail_bal = float(avail_bal)
            
            if cash_bal > 0.001:  # 0.001 이상만 저장
                balances[ccy] = {
                    'total': cash_bal,
                    'available': avail_bal
                }
        
        # 총 자산 정보 추가
        total_eq = balance_data.get('totalEq', '0')
        if total_eq == '' or total_eq is None:
            total_eq = '0'
        
        result = {
            'currencies': balances,
            'total_equity': float(total_eq)
        }
        
        log_system(f"✅ 거래 계정 잔액 조회 성공: 총 자산 ${float(total_eq):,.2f}")
        
        # USDT 잔액 특별 로깅
        if 'USDT' in balances:
            usdt_balance = balances['USDT']['available']
            log_system(f"💰 USDT 사용가능 잔액: ${usdt_balance:.6f}")
        else:
            log_system("⚠️ USDT 잔액 없음")
        
        return result
        
    except Exception as e:
        log_error("거래 계정 잔액 조회 오류", e)
        return {}

def check_minimum_trading_balance(minimum: float = 50.0) -> tuple:
    """최소 거래 가능 잔액 확인"""
    try:
        balance_info = get_trading_account_balance()
        
        if not balance_info or 'currencies' not in balance_info:
            return False, 0.0, "❌ 잔액 조회 실패"
        
        currencies = balance_info['currencies']
        
        if 'USDT' not in currencies:
            return False, 0.0, "❌ USDT 잔액 없음"
        
        usdt_available = currencies['USDT']['available']
        
        if usdt_available >= minimum:
            return True, usdt_available, f"✅ 거래 가능: ${usdt_available:.2f}"
        else:
            return False, usdt_available, f"❌ 잔액 부족: ${usdt_available:.2f} (최소 ${minimum:.2f} 필요)"
            
    except Exception as e:
        log_error("최소 잔액 확인 오류", e)
        return False, 0.0, f"❌ 확인 실패: {e}"