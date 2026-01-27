# okx/account_manager.py
"""
계좌 관리자 - 로그 정리 버전

수정 사항:
- 불필요한 반복 로그 제거:
  - 계좌 레벨, 포지션 모드
  - 초기화 완료
  - 조회 성공 메시지
- 중요 로그만 유지:
  - 에러
  - 경고
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import (
    API_KEY, API_SECRET, PASSPHRASE, API_BASE_URL,
    make_api_request
)


class AccountManager:
    """계좌 관리자 - 로그 정리 버전"""
    
    def __init__(self, verbose: bool = False):
        """
        Args:
            verbose: True면 상세 로그 출력
        """
        self.api_key = API_KEY
        self.secret_key = API_SECRET
        self.passphrase = PASSPHRASE
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        self.verbose = verbose
        
        # verbose 모드에서만 초기화 로그
        if self.verbose:
            print("✅ 계좌 관리자 초기화 완료")
    
    def _log(self, message: str, force: bool = False):
        """로그 출력"""
        if force or self.verbose:
            print(message)
    
    def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """계좌 잔고 조회"""
        try:
            result = make_api_request('GET', '/api/v5/account/balance')
            if result and result.get('data'):
                return result['data'][0]
            return None
        except Exception as e:
            self._log(f"❌ 계좌 잔고 조회 실패: {e}", force=True)
            return None
    
    def get_account_config(self) -> Optional[Dict[str, Any]]:
        """계좌 설정 조회"""
        try:
            result = make_api_request('GET', '/api/v5/account/config')
            if result and result.get('data'):
                return result['data'][0]
            return None
        except Exception as e:
            self._log(f"❌ 계좌 설정 조회 실패: {e}", force=True)
            return None
    
    def get_positions(self, inst_type: str = "SWAP") -> List[Dict[str, Any]]:
        """포지션 조회 - 로그 제거"""
        try:
            params = {"instType": inst_type}
            result = make_api_request('GET', '/api/v5/account/positions', params=params)
            
            if result and result.get('data'):
                return result['data']
            return []
        except Exception as e:
            self._log(f"❌ 포지션 조회 실패: {e}", force=True)
            return []
    
    def get_account_bills(self, inst_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """계좌 변동 내역 조회"""
        try:
            params = {"limit": str(limit)}
            if inst_type:
                params["instType"] = inst_type
            
            result = make_api_request('GET', '/api/v5/account/bills', params=params)
            if result and result.get('data'):
                return result['data']
            return []
        except Exception as e:
            self._log(f"❌ 계좌 변동 내역 조회 실패: {e}", force=True)
            return []
    
    def get_trading_fees(self, inst_type: str = "SWAP") -> List[Dict[str, Any]]:
        """거래 수수료율 조회"""
        try:
            params = {"instType": inst_type}
            result = make_api_request('GET', '/api/v5/account/trade-fee', params=params)
            if result and result.get('data'):
                return result['data']
            return []
        except Exception as e:
            self._log(f"❌ 거래 수수료율 조회 실패: {e}", force=True)
            return []
    
    def set_leverage(self, inst_id: str, lever: str, mgn_mode: str = "cross") -> bool:
        """레버리지 설정"""
        try:
            data = {
                "instId": inst_id,
                "lever": str(lever),
                "mgnMode": mgn_mode
            }
            
            result = make_api_request('POST', '/api/v5/account/set-leverage', data=data)
            if result and result.get('code') == '0':
                return True
            return False
        except Exception as e:
            self._log(f"❌ 레버리지 설정 실패: {e}", force=True)
            return False
    
    def check_account_status(self) -> Dict[str, Any]:
        """계좌 상태 종합 체크 - 로그 선택적"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'balance': None,
            'config': None,
            'positions': [],
            'available_balance': 0,
            'total_equity': 0,
            'is_healthy': False
        }
        
        try:
            # 잔고 조회
            balance = self.get_account_balance()
            if balance:
                status['balance'] = balance
                
                for detail in balance.get('details', []):
                    if detail['ccy'] == 'USDT':
                        status['available_balance'] = float(detail.get('availBal', 0))
                        status['total_equity'] = float(detail.get('eq', 0))
                        break
            
            # 설정 조회
            config = self.get_account_config()
            if config:
                status['config'] = config
            
            # 포지션 조회
            positions = self.get_positions()
            status['positions'] = positions
            
            # 건강도 판단
            if status['available_balance'] > 100:
                active_positions = [p for p in positions if float(p.get('pos', 0)) != 0]
                if len(active_positions) < 10:
                    status['is_healthy'] = True
            
            return status
            
        except Exception as e:
            self._log(f"❌ 계좌 상태 조회 실패: {e}", force=True)
            return status
    
    def get_balance_summary(self) -> Dict[str, float]:
        """잔고 요약"""
        try:
            balance = self.get_account_balance()
            if not balance:
                return {}
            
            summary = {}
            for detail in balance.get('details', []):
                ccy = detail['ccy']
                cash_bal = float(detail.get('cashBal', 0))
                avail_bal = float(detail.get('availBal', 0))
                
                if cash_bal > 0 or avail_bal > 0:
                    summary[ccy] = {
                        'total': cash_bal,
                        'available': avail_bal,
                        'frozen': cash_bal - avail_bal
                    }
            
            return summary
            
        except Exception as e:
            self._log(f"❌ 잔고 요약 조회 실패: {e}", force=True)
            return {}
    
    def validate_trading_permission(self) -> bool:
        """거래 권한 검증 - 로그 선택적"""
        try:
            # 설정 확인
            config = self.get_account_config()
            if not config:
                return False
            
            # 잔고 확인
            balance = self.get_balance_summary()
            usdt_balance = balance.get('USDT', {}).get('available', 0)
            
            if usdt_balance < 10:
                self._log(f"⚠️ USDT 잔고 부족: ${usdt_balance:.2f}", force=True)
                return False
            
            # 포지션 조회 테스트
            self.get_positions()
            
            return True
            
        except Exception as e:
            self._log(f"❌ 거래 권한 검증 실패: {e}", force=True)
            return False
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """리스크 지표"""
        try:
            balance = self.get_account_balance()
            positions = self.get_positions()
            
            if not balance:
                return {}
            
            total_eq = float(balance.get('totalEq', 0))
            avail_bal = 0
            
            for detail in balance.get('details', []):
                if detail['ccy'] == 'USDT':
                    avail_bal = float(detail.get('availBal', 0))
                    break
            
            # 포지션 리스크
            total_notional = 0
            total_pnl = 0
            position_count = 0
            
            for pos in positions:
                pos_size = float(pos.get('pos', 0))
                if pos_size != 0:
                    position_count += 1
                    total_notional += abs(float(pos.get('notionalUsd', 0)))
                    total_pnl += float(pos.get('upl', 0))
            
            # 지표 계산
            leverage_ratio = total_notional / total_eq if total_eq > 0 else 0
            utilization_ratio = (total_eq - avail_bal) / total_eq if total_eq > 0 else 0
            pnl_ratio = total_pnl / total_eq if total_eq > 0 else 0
            
            # 리스크 레벨
            if leverage_ratio > 10 or utilization_ratio > 0.9 or position_count > 10:
                risk_level = "HIGH"
            elif leverage_ratio > 5 or utilization_ratio > 0.7 or position_count > 5:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            return {
                'total_equity': total_eq,
                'available_balance': avail_bal,
                'total_notional': total_notional,
                'total_pnl': total_pnl,
                'position_count': position_count,
                'leverage_ratio': leverage_ratio,
                'utilization_ratio': utilization_ratio,
                'pnl_ratio': pnl_ratio,
                'risk_level': risk_level
            }
            
        except Exception as e:
            self._log(f"❌ 리스크 지표 계산 실패: {e}", force=True)
            return {}