"""
GUI 전용 잔액 관리 유틸리티
main.py와 동일한 방식으로 잔액 정보 처리
"""

from typing import Dict, Any, Optional
import traceback

class GUIBalanceManager:
    """GUI에서 사용할 잔액 데이터 관리자"""
    
    @staticmethod
    def parse_okx_balance(balance_data: Dict[str, Any]) -> Dict[str, Any]:
        """OKX API 잔액 응답을 표준 형태로 파싱"""
        try:
            if not balance_data or not isinstance(balance_data, dict):
                return GUIBalanceManager._get_empty_balance()
            
            parsed_balances = {}
            
            # OKX API 표준 응답 구조 처리
            if 'details' in balance_data:
                for detail in balance_data.get('details', []):
                    ccy = detail.get('ccy')  # 통화 코드
                    if not ccy:
                        continue
                    
                    # 각 필드 안전하게 파싱
                    cash_bal = detail.get('cashBal', '0')
                    avail_bal = detail.get('availBal', '0')
                    frozen_bal = detail.get('frozenBal', '0')
                    
                    # 빈 문자열이나 None 처리
                    cash_bal = GUIBalanceManager._safe_float(cash_bal)
                    avail_bal = GUIBalanceManager._safe_float(avail_bal)
                    frozen_bal = GUIBalanceManager._safe_float(frozen_bal)
                    
                    # 실제 동결 금액 계산 (cash_bal - avail_bal이 더 정확)
                    actual_frozen = max(0, cash_bal - avail_bal)
                    
                    # 잔고가 있는 통화만 저장 (매우 작은 값 제외)
                    if cash_bal > 0.000001:
                        parsed_balances[ccy] = {
                            'total': cash_bal,
                            'available': avail_bal,
                            'frozen': actual_frozen
                        }
                
                # 총 자산 정보 추가
                total_eq = balance_data.get('totalEq', '0')
                total_eq = GUIBalanceManager._safe_float(total_eq)
                parsed_balances['_metadata'] = {
                    'total_equity': total_eq,
                    'last_updated': balance_data.get('uTime', ''),
                    'currency_count': len(parsed_balances)
                }
                
            else:
                # 이미 파싱된 형태이거나 다른 구조
                parsed_balances = balance_data
            
            return parsed_balances
            
        except Exception as e:
            print(f"❌ 잔액 파싱 오류: {e}")
            print(f"원본 데이터: {balance_data}")
            traceback.print_exc()
            return GUIBalanceManager._get_empty_balance()
    
    @staticmethod
    def _safe_float(value: Any) -> float:
        """안전한 float 변환"""
        try:
            if value == '' or value is None:
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def _get_empty_balance() -> Dict[str, Any]:
        """기본 빈 잔액 데이터"""
        return {
            'USDT': {'total': 0.0, 'available': 0.0, 'frozen': 0.0},
            'BTC': {'total': 0.0, 'available': 0.0, 'frozen': 0.0},
            '_metadata': {
                'total_equity': 0.0,
                'last_updated': '',
                'currency_count': 0
            }
        }
    
    @staticmethod
    def get_usdt_balance(parsed_balances: Dict[str, Any]) -> float:
        """USDT 사용가능 잔액 추출"""
        try:
            usdt_info = parsed_balances.get('USDT', {})
            return usdt_info.get('available', 0.0)
        except:
            return 0.0
    
    @staticmethod
    def get_total_equity(parsed_balances: Dict[str, Any]) -> float:
        """총 자산 추출"""
        try:
            metadata = parsed_balances.get('_metadata', {})
            return metadata.get('total_equity', 0.0)
        except:
            return 0.0
    
    @staticmethod
    def format_balance_summary(parsed_balances: Dict[str, Any]) -> str:
        """잔액 요약 문자열 생성"""
        try:
            summary_lines = []
            
            # 메타데이터 확인
            metadata = parsed_balances.get('_metadata', {})
            total_equity = metadata.get('total_equity', 0)
            
            if total_equity > 0:
                summary_lines.append(f"💰 총 자산: ${total_equity:.2f}")
                summary_lines.append("")
            
            # 각 통화별 정보
            for currency, info in parsed_balances.items():
                if currency.startswith('_'):  # 메타데이터 건너뛰기
                    continue
                
                if isinstance(info, dict):
                    total = info.get('total', 0)
                    available = info.get('available', 0)
                    frozen = info.get('frozen', 0)
                    
                    # 잔고가 있는 통화만 표시
                    if total > 0.000001:
                        summary_lines.append(f"{currency}:")
                        summary_lines.append(f"  💵 총 잔고: {total:.6f}")
                        summary_lines.append(f"  ✅ 사용가능: {available:.6f}")
                        if frozen > 0.000001:
                            summary_lines.append(f"  🔒 동결: {frozen:.6f}")
                        summary_lines.append("")
            
            return "\n".join(summary_lines) if summary_lines else "잔액 정보 없음"
            
        except Exception as e:
            return f"잔액 정보 처리 오류: {e}"