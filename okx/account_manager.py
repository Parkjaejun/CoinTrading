# okx/account_manager.py
"""
수정된 계좌 관리자 - 통일된 타임스탬프 사용
config.py의 공통 API 유틸리티 함수 활용
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import (
    API_KEY, API_SECRET, PASSPHRASE, API_BASE_URL,
    make_api_request, get_api_headers, CONNECTION_CONFIG
)

class AccountManager:
    def __init__(self):
        self.api_key = API_KEY
        self.secret_key = API_SECRET
        self.passphrase = PASSPHRASE
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        
        print("✅ 계좌 관리자 초기화 완료")
    
    def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """계좌 잔고 조회"""
        try:
            result = make_api_request('GET', '/api/v5/account/balance')
            if result and result.get('data'):
                return result['data'][0]
            return None
        except Exception as e:
            print(f"❌ 계좌 잔고 조회 실패: {e}")
            return None
    
    def get_account_config(self) -> Optional[Dict[str, Any]]:
        """계좌 설정 조회"""
        try:
            result = make_api_request('GET', '/api/v5/account/config')
            if result and result.get('data'):
                return result['data'][0]
            return None
        except Exception as e:
            print(f"❌ 계좌 설정 조회 실패: {e}")
            return None
    
    def get_positions(self, inst_type: str = "SWAP") -> List[Dict[str, Any]]:
        """포지션 조회"""
        try:
            params = {"instType": inst_type}
            result = make_api_request('GET', '/api/v5/account/positions', params=params)
            if result and result.get('data'):
                return result['data']
            return []
        except Exception as e:
            print(f"❌ 포지션 조회 실패: {e}")
            return []
    
    def get_position_history(self, inst_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """포지션 히스토리 조회"""
        try:
            params = {"limit": str(limit)}
            if inst_id:
                params["instId"] = inst_id
            
            result = make_api_request('GET', '/api/v5/account/positions-history', params=params)
            if result and result.get('data'):
                return result['data']
            return []
        except Exception as e:
            print(f"❌ 포지션 히스토리 조회 실패: {e}")
            return []
    
    def get_bills(self, inst_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """계좌 변동 내역 조회"""
        try:
            params = {"limit": str(limit)}
            if inst_id:
                params["instId"] = inst_id
            
            result = make_api_request('GET', '/api/v5/account/bills', params=params)
            if result and result.get('data'):
                return result['data']
            return []
        except Exception as e:
            print(f"❌ 계좌 변동 내역 조회 실패: {e}")
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
            print(f"❌ 거래 수수료율 조회 실패: {e}")
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
            if result:
                print(f"✅ {inst_id} 레버리지 {lever}배로 설정 완료")
                return True
            return False
        except Exception as e:
            print(f"❌ 레버리지 설정 실패: {e}")
            return False
    
    def check_account_status(self) -> Dict[str, Any]:
        """계좌 상태 종합 체크"""
        try:
            print("\n📊 계좌 상태 종합 조회")
            print("-" * 50)
            
            status = {
                'timestamp': datetime.now().isoformat(),
                'balance': None,
                'config': None,
                'positions': [],
                'trading_fees': [],
                'available_balance': 0,
                'total_equity': 0,
                'margin_ratio': 0,
                'is_healthy': False
            }
            
            # 1. 계좌 잔고 조회
            balance = self.get_account_balance()
            if balance:
                status['balance'] = balance
                
                # 사용 가능 잔고 계산
                for detail in balance.get('details', []):
                    if detail['ccy'] == 'USDT':
                        status['available_balance'] = float(detail.get('availBal', 0))
                        status['total_equity'] = float(detail.get('eq', 0))
                        break
                
                print(f"💰 총 자산: ${status['total_equity']:,.2f}")
                print(f"💵 사용가능: ${status['available_balance']:,.2f}")
            else:
                print("❌ 계좌 잔고 조회 실패")
                return status
            
            # 2. 계좌 설정 조회
            config = self.get_account_config()
            if config:
                status['config'] = config
                print(f"📋 계좌 레벨: {config.get('acctLv', 'Unknown')}")
                print(f"📋 포지션 모드: {config.get('posMode', 'Unknown')}")
            else:
                print("⚠️ 계좌 설정 조회 실패")
            
            # 3. 현재 포지션 조회
            positions = self.get_positions()
            if positions:
                status['positions'] = positions
                print(f"📊 현재 포지션: {len(positions)}개")
                
                for pos in positions:
                    if float(pos.get('pos', 0)) != 0:
                        pnl = float(pos.get('upl', 0))
                        pnl_ratio = float(pos.get('uplRatio', 0)) * 100
                        print(f"  - {pos['instId']}: {pos['posSide']} {pos['pos']} (PnL: ${pnl:.2f}, {pnl_ratio:.2f}%)")
            else:
                print("📊 현재 포지션: 없음")
            
            # 4. 거래 수수료율 조회
            fees = self.get_trading_fees()
            if fees:
                status['trading_fees'] = fees
                for fee in fees[:3]:  # 상위 3개만 출력
                    maker_fee = float(fee.get('maker', 0)) * 100
                    taker_fee = float(fee.get('taker', 0)) * 100
                    print(f"💸 {fee['instType']} 수수료 - Maker: {maker_fee:.3f}%, Taker: {taker_fee:.3f}%")
            
            # 5. 계좌 건강도 판단
            if status['available_balance'] > 100:  # 최소 $100 이상
                if len([p for p in positions if float(p.get('pos', 0)) != 0]) < 10:  # 포지션 수 제한
                    status['is_healthy'] = True
                    print("✅ 계좌 상태: 건강함")
                else:
                    print("⚠️ 계좌 상태: 포지션 과다")
            else:
                print("❌ 계좌 상태: 잔고 부족")
            
            print(f"🎯 종합 상태: {'정상' if status['is_healthy'] else '주의'}")
            return status
            
        except Exception as e:
            print(f"❌ 계좌 상태 조회 실패: {e}")
            return status
    
    def get_balance_summary(self) -> Dict[str, float]:
        """잔고 요약 정보"""
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
            print(f"❌ 잔고 요약 조회 실패: {e}")
            return {}
    
    def print_balance_details(self):
        """잔고 상세 정보 출력"""
        try:
            print("\n💰 계좌 잔고 상세")
            print("-" * 50)
            
            balance = self.get_account_balance()
            if not balance:
                print("❌ 잔고 정보를 조회할 수 없습니다")
                return
            
            # 전체 정보
            total_eq = float(balance.get('totalEq', 0))
            adj_eq = float(balance.get('adjEq', 0))
            print(f"📊 총 자산: ${total_eq:,.2f}")
            print(f"📊 조정 자산: ${adj_eq:,.2f}")
            
            # 통화별 잔고
            print("\n💵 통화별 잔고:")
            for detail in balance.get('details', []):
                ccy = detail['ccy']
                cash_bal = float(detail.get('cashBal', 0))
                avail_bal = float(detail.get('availBal', 0))
                frozen_bal = cash_bal - avail_bal
                
                if cash_bal > 0.01:  # 0.01 이상만 표시
                    print(f"  {ccy:>8}: 총 {cash_bal:>12.4f} | 사용가능 {avail_bal:>12.4f} | 동결 {frozen_bal:>12.4f}")
            
        except Exception as e:
            print(f"❌ 잔고 상세 출력 실패: {e}")
    
    def validate_trading_permission(self) -> bool:
        """거래 권한 검증"""
        try:
            print("\n🔍 거래 권한 검증")
            print("-" * 50)
            
            # 1. 계좌 설정 확인
            config = self.get_account_config()
            if not config:
                print("❌ 계좌 설정을 가져올 수 없습니다")
                return False
            
            account_level = config.get('acctLv', '1')
            pos_mode = config.get('posMode', 'net_mode')
            
            print(f"📋 계좌 레벨: {account_level}")
            print(f"📋 포지션 모드: {pos_mode}")
            
            # 2. 잔고 확인
            balance = self.get_balance_summary()
            usdt_balance = balance.get('USDT', {}).get('available', 0)
            
            if usdt_balance < 100:
                print(f"❌ USDT 잔고 부족: ${usdt_balance:.2f} (최소 $100 필요)")
                return False
            
            print(f"✅ USDT 잔고 충분: ${usdt_balance:.2f}")
            
            # 3. API 권한 테스트 (포지션 조회로 확인)
            positions = self.get_positions()
            print(f"✅ 포지션 조회 권한: 정상 (현재 {len(positions)}개 포지션)")
            
            # 4. 수수료율 확인
            fees = self.get_trading_fees()
            if fees:
                swap_fee = next((f for f in fees if f.get('instType') == 'SWAP'), None)
                if swap_fee:
                    maker_rate = float(swap_fee.get('maker', 0)) * 100
                    taker_rate = float(swap_fee.get('taker', 0)) * 100
                    print(f"💸 SWAP 수수료 - Maker: {maker_rate:.3f}%, Taker: {taker_rate:.3f}%")
            
            print("✅ 거래 권한 검증 완료")
            return True
            
        except Exception as e:
            print(f"❌ 거래 권한 검증 실패: {e}")
            return False
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """리스크 지표 계산"""
        try:
            balance = self.get_account_balance()
            positions = self.get_positions()
            
            if not balance:
                return {}
            
            total_eq = float(balance.get('totalEq', 0))
            avail_bal = 0
            
            # 사용가능 잔고 계산
            for detail in balance.get('details', []):
                if detail['ccy'] == 'USDT':
                    avail_bal = float(detail.get('availBal', 0))
                    break
            
            # 포지션 리스크 계산
            total_notional = 0
            total_pnl = 0
            position_count = 0
            
            for pos in positions:
                pos_size = float(pos.get('pos', 0))
                if pos_size != 0:
                    position_count += 1
                    notional = float(pos.get('notionalUsd', 0))
                    pnl = float(pos.get('upl', 0))
                    
                    total_notional += abs(notional)
                    total_pnl += pnl
            
            # 리스크 지표
            leverage_ratio = total_notional / total_eq if total_eq > 0 else 0
            utilization_ratio = (total_eq - avail_bal) / total_eq if total_eq > 0 else 0
            pnl_ratio = total_pnl / total_eq if total_eq > 0 else 0
            
            return {
                'total_equity': total_eq,
                'available_balance': avail_bal,
                'total_notional': total_notional,
                'total_pnl': total_pnl,
                'position_count': position_count,
                'leverage_ratio': leverage_ratio,
                'utilization_ratio': utilization_ratio,
                'pnl_ratio': pnl_ratio,
                'risk_level': self._assess_risk_level(leverage_ratio, utilization_ratio, position_count)
            }
            
        except Exception as e:
            print(f"❌ 리스크 지표 계산 실패: {e}")
            return {}
    
    def _assess_risk_level(self, leverage_ratio: float, utilization_ratio: float, position_count: int) -> str:
        """리스크 레벨 평가"""
        score = 0
        
        # 레버리지 비율 평가
        if leverage_ratio > 10:
            score += 3
        elif leverage_ratio > 5:
            score += 2
        elif leverage_ratio > 2:
            score += 1
        
        # 자금 사용률 평가
        if utilization_ratio > 0.9:
            score += 3
        elif utilization_ratio > 0.7:
            score += 2
        elif utilization_ratio > 0.5:
            score += 1
        
        # 포지션 수 평가
        if position_count > 10:
            score += 2
        elif position_count > 5:
            score += 1
        
        # 리스크 레벨 결정
        if score >= 6:
            return "HIGH"
        elif score >= 3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def print_risk_summary(self):
        """리스크 요약 출력"""
        try:
            print("\n⚡ 리스크 분석")
            print("-" * 50)
            
            metrics = self.get_risk_metrics()
            if not metrics:
                print("❌ 리스크 지표를 계산할 수 없습니다")
                return
            
            print(f"📊 총 자산: ${metrics['total_equity']:,.2f}")
            print(f"💵 사용가능: ${metrics['available_balance']:,.2f}")
            print(f"📈 포지션 수: {metrics['position_count']}개")
            print(f"💰 총 명목가치: ${metrics['total_notional']:,.2f}")
            print(f"📊 미실현 손익: ${metrics['total_pnl']:+,.2f}")
            print(f"⚖️ 레버리지 비율: {metrics['leverage_ratio']:.2f}x")
            print(f"📊 자금 사용률: {metrics['utilization_ratio']:.1%}")
            print(f"📊 손익 비율: {metrics['pnl_ratio']:+.2%}")
            
            risk_level = metrics['risk_level']
            risk_color = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
            print(f"⚠️ 리스크 레벨: {risk_color.get(risk_level, '')} {risk_level}")
            
            # 리스크 경고
            if risk_level == "HIGH":
                print("\n🚨 높은 리스크 경고:")
                if metrics['leverage_ratio'] > 10:
                    print("  - 과도한 레버리지 사용")
                if metrics['utilization_ratio'] > 0.9:
                    print("  - 높은 자금 사용률")
                if metrics['position_count'] > 10:
                    print("  - 과다한 포지션 수")
            
        except Exception as e:
            print(f"❌ 리스크 요약 출력 실패: {e}")

# 사용 예시 및 테스트 함수
def test_account_manager():
    """계좌 관리자 테스트"""
    try:
        print("🧪 계좌 관리자 테스트 시작")
        print("=" * 80)
        
        # 계좌 관리자 생성
        account = AccountManager()
        
        # 1. 거래 권한 검증
        permission_ok = account.validate_trading_permission()
        
        if permission_ok:
            # 2. 계좌 상태 종합 체크
            status = account.check_account_status()
            
            # 3. 잔고 상세 출력
            account.print_balance_details()
            
            # 4. 리스크 분석
            account.print_risk_summary()
            
            print("\n🎉 계좌 관리자 테스트 완료")
            return True
        else:
            print("\n❌ 거래 권한 검증 실패")
            return False
            
    except Exception as e:
        print(f"❌ 계좌 관리자 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_account_manager()