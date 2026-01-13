# okx/real_order_manager.py
"""
실제 OKX 거래 실행을 위한 주문 관리자
시뮬레이션 대체 없이 실제 거래만 수행
"""

import hmac
import hashlib
import base64
import time
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

class RealOrderManager:
    """실제 거래 전용 주문 관리자"""
    
    def __init__(self, api_key: str, api_secret: str, passphrase: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        
        self.base_url = "https://www.okx.com"
        self.timeout = 10
        
        # 거래소별 최소 주문 요건
        self.min_order_requirements = {
            'BTC-USDT-SWAP': {
                'min_size': 0.001,      # 최소 수량 (BTC)
                'min_notional': 5,      # 최소 명목가치 (USDT)
                'lot_size': 0.001,      # 수량 단위
                'tick_size': 0.1        # 가격 단위
            },
            'ETH-USDT-SWAP': {
                'min_size': 0.01,
                'min_notional': 5,
                'lot_size': 0.01,
                'tick_size': 0.01
            },
            'DEFAULT': {
                'min_size': 1,
                'min_notional': 5,
                'lot_size': 1,
                'tick_size': 0.01
            }
        }
        
        # 주문 이력
        self.order_history = []
        self.last_order_time = None
        
    def _get_timestamp(self) -> str:
        """ISO 형식 타임스탬프 생성"""
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    def _generate_signature(self, timestamp: str, method: str, 
                           request_path: str, body: str = "") -> str:
        """API 서명 생성"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.api_secret, encoding='utf-8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _make_request(self, method: str, endpoint: str, 
                      body: Optional[Dict] = None) -> Dict:
        """API 요청 수행"""
        timestamp = self._get_timestamp()
        body_str = json.dumps(body) if body else ""
        
        signature = self._generate_signature(timestamp, method, endpoint, body_str)
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        url = self.base_url + endpoint
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=self.timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, 
                                        data=body_str, timeout=self.timeout)
            else:
                return {'code': '-1', 'msg': f'Unsupported method: {method}'}
            
            return response.json()
            
        except requests.exceptions.Timeout:
            return {'code': '-1', 'msg': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            return {'code': '-1', 'msg': str(e)}
        except json.JSONDecodeError:
            return {'code': '-1', 'msg': 'Invalid JSON response'}
    
    def get_instrument_info(self, inst_id: str) -> Optional[Dict]:
        """상품 정보 조회 (최소 주문 요건 포함)"""
        endpoint = f"/api/v5/public/instruments?instType=SWAP&instId={inst_id}"
        
        result = self._make_request('GET', endpoint)
        
        if result.get('code') == '0' and result.get('data'):
            info = result['data'][0]
            return {
                'inst_id': info.get('instId'),
                'min_size': float(info.get('minSz', 0.001)),
                'lot_size': float(info.get('lotSz', 0.001)),
                'tick_size': float(info.get('tickSz', 0.01)),
                'ct_val': float(info.get('ctVal', 1)),  # 계약 가치
                'ct_mult': float(info.get('ctMult', 1)),  # 계약 승수
                'settle_ccy': info.get('settleCcy', 'USDT'),
                'state': info.get('state', 'live')
            }
        return None
    
    def get_current_price(self, inst_id: str) -> Optional[float]:
        """현재 시장 가격 조회"""
        endpoint = f"/api/v5/market/ticker?instId={inst_id}"
        
        result = self._make_request('GET', endpoint)
        
        if result.get('code') == '0' and result.get('data'):
            return float(result['data'][0].get('last', 0))
        return None
    
    def get_account_balance(self, ccy: str = "USDT") -> Optional[Dict]:
        """계좌 잔고 조회"""
        endpoint = f"/api/v5/account/balance?ccy={ccy}"
        
        result = self._make_request('GET', endpoint)
        
        if result.get('code') == '0' and result.get('data'):
            for balance in result['data'][0].get('details', []):
                if balance.get('ccy') == ccy:
                    return {
                        'currency': ccy,
                        'available': float(balance.get('availBal', 0)),
                        'equity': float(balance.get('eq', 0)),
                        'frozen': float(balance.get('frozenBal', 0))
                    }
        return None
    
    def calculate_order_size(self, inst_id: str, usdt_amount: float) -> Tuple[float, Dict]:
        """
        USDT 금액을 기준으로 주문 수량 계산
        
        Returns:
            (계산된 수량, 상세 정보)
        """
        # 상품 정보 조회
        inst_info = self.get_instrument_info(inst_id)
        if not inst_info:
            return 0, {'error': '상품 정보 조회 실패'}
        
        # 현재 가격 조회
        current_price = self.get_current_price(inst_id)
        if not current_price:
            return 0, {'error': '가격 조회 실패'}
        
        # 계약 가치 계산
        ct_val = inst_info['ct_val']  # 1계약 = ct_val (예: 0.001 BTC)
        contract_value_usdt = ct_val * current_price
        
        # 필요한 계약 수 계산
        contracts = usdt_amount / contract_value_usdt
        
        # 최소 단위(lot_size)로 반올림
        lot_size = inst_info['lot_size']
        contracts = int(contracts / lot_size) * lot_size
        
        # 최소 주문 수량 확인
        min_size = inst_info['min_size']
        if contracts < min_size:
            contracts = min_size
        
        # 실제 주문 금액 계산
        actual_notional = contracts * ct_val * current_price
        
        details = {
            'inst_id': inst_id,
            'current_price': current_price,
            'ct_val': ct_val,
            'lot_size': lot_size,
            'min_size': min_size,
            'requested_usdt': usdt_amount,
            'calculated_contracts': contracts,
            'actual_notional': actual_notional,
            'contract_value_usdt': contract_value_usdt
        }
        
        return contracts, details
    
    def set_leverage(self, inst_id: str, leverage: int = 1, 
                     margin_mode: str = 'isolated') -> Dict:
        """레버리지 설정"""
        endpoint = "/api/v5/account/set-leverage"
        
        body = {
            'instId': inst_id,
            'lever': str(leverage),
            'mgnMode': margin_mode  # 'isolated' or 'cross'
        }
        
        result = self._make_request('POST', endpoint, body)
        
        return {
            'success': result.get('code') == '0',
            'leverage': leverage,
            'margin_mode': margin_mode,
            'response': result
        }
    
    def place_market_order(self, inst_id: str, side: str, 
                           size: float, leverage: int = 1,
                           reduce_only: bool = False) -> Dict:
        """
        시장가 주문 실행 (실제 거래)
        
        Args:
            inst_id: 상품 ID (예: 'BTC-USDT-SWAP')
            side: 'buy' 또는 'sell'
            size: 주문 수량 (계약 수)
            leverage: 레버리지 배수
            reduce_only: 청산 전용 여부
        
        Returns:
            주문 결과 딕셔너리
        """
        # 1. 레버리지 설정
        lever_result = self.set_leverage(inst_id, leverage)
        if not lever_result['success']:
            return {
                'success': False,
                'error': '레버리지 설정 실패',
                'details': lever_result
            }
        
        # 2. 주문 실행
        endpoint = "/api/v5/trade/order"
        
        # 포지션 사이드 결정
        pos_side = 'long' if side == 'buy' else 'short'
        
        body = {
            'instId': inst_id,
            'tdMode': 'isolated',  # 격리 마진
            'side': side,
            'posSide': pos_side,
            'ordType': 'market',
            'sz': str(size)
        }
        
        # 청산 주문인 경우
        if reduce_only:
            body['reduceOnly'] = True
        
        result = self._make_request('POST', endpoint, body)
        
        # 결과 처리
        if result.get('code') == '0' and result.get('data'):
            order_data = result['data'][0]
            order_id = order_data.get('ordId')
            
            # 주문 상세 조회
            order_detail = self.get_order_detail(inst_id, order_id)
            
            order_record = {
                'success': True,
                'order_id': order_id,
                'inst_id': inst_id,
                'side': side,
                'size': size,
                'leverage': leverage,
                'order_time': datetime.now(),
                'status': order_data.get('sCode'),
                'message': order_data.get('sMsg'),
                'detail': order_detail,
                'is_real_order': True
            }
            
            self.order_history.append(order_record)
            self.last_order_time = datetime.now()
            
            return order_record
        else:
            return {
                'success': False,
                'error': result.get('msg', 'Unknown error'),
                'error_code': result.get('code'),
                'details': result
            }
    
    def get_order_detail(self, inst_id: str, order_id: str) -> Optional[Dict]:
        """주문 상세 조회"""
        endpoint = f"/api/v5/trade/order?instId={inst_id}&ordId={order_id}"
        
        result = self._make_request('GET', endpoint)
        
        if result.get('code') == '0' and result.get('data'):
            order = result['data'][0]
            return {
                'order_id': order.get('ordId'),
                'state': order.get('state'),
                'filled_size': float(order.get('fillSz', 0)),
                'avg_price': float(order.get('avgPx', 0)),
                'fee': float(order.get('fee', 0)),
                'pnl': float(order.get('pnl', 0)),
                'fill_time': order.get('fillTime'),
                'create_time': order.get('cTime'),
                'update_time': order.get('uTime')
            }
        return None
    
    def get_positions(self, inst_id: Optional[str] = None) -> List[Dict]:
        """포지션 조회"""
        endpoint = "/api/v5/account/positions"
        if inst_id:
            endpoint += f"?instId={inst_id}"
        
        result = self._make_request('GET', endpoint)
        
        positions = []
        if result.get('code') == '0' and result.get('data'):
            for pos in result['data']:
                if float(pos.get('pos', 0)) != 0:
                    positions.append({
                        'inst_id': pos.get('instId'),
                        'pos_side': pos.get('posSide'),
                        'position': float(pos.get('pos', 0)),
                        'avg_price': float(pos.get('avgPx', 0)),
                        'upl': float(pos.get('upl', 0)),
                        'upl_ratio': float(pos.get('uplRatio', 0)),
                        'lever': int(pos.get('lever', 1)),
                        'margin': float(pos.get('margin', 0)),
                        'liq_price': float(pos.get('liqPx', 0)) if pos.get('liqPx') else None,
                        'create_time': pos.get('cTime'),
                        'update_time': pos.get('uTime')
                    })
        
        return positions
    
    def close_position(self, inst_id: str, pos_side: str = 'long') -> Dict:
        """포지션 청산"""
        endpoint = "/api/v5/trade/close-position"
        
        body = {
            'instId': inst_id,
            'mgnMode': 'isolated',
            'posSide': pos_side
        }
        
        result = self._make_request('POST', endpoint, body)
        
        if result.get('code') == '0':
            return {
                'success': True,
                'inst_id': inst_id,
                'pos_side': pos_side,
                'response': result
            }
        else:
            return {
                'success': False,
                'error': result.get('msg', 'Unknown error'),
                'response': result
            }
    
    def test_buy_order(self, inst_id: str = 'BTC-USDT-SWAP', 
                       usdt_amount: float = 10,
                       leverage: int = 1) -> Dict:
        """
        구매 테스트 실행 (실제 거래)
        
        Args:
            inst_id: 상품 ID
            usdt_amount: 구매할 USDT 금액 (기본: 10 USDT)
            leverage: 레버리지 (기본: 1x)
        
        Returns:
            테스트 결과 딕셔너리
        """
        test_result = {
            'test_type': 'REAL_BUY_TEST',
            'inst_id': inst_id,
            'requested_amount': usdt_amount,
            'leverage': leverage,
            'timestamp': datetime.now().isoformat(),
            'steps': [],
            'success': False
        }
        
        print(f"\n{'='*60}")
        print(f"🧪 실제 구매 테스트 시작")
        print(f"{'='*60}")
        print(f"📌 상품: {inst_id}")
        print(f"💰 금액: {usdt_amount} USDT")
        print(f"📊 레버리지: {leverage}x")
        print(f"{'='*60}")
        
        # Step 1: 잔고 확인
        print("\n📋 1단계: 잔고 확인")
        balance = self.get_account_balance('USDT')
        
        if not balance:
            test_result['steps'].append({'step': 1, 'name': '잔고 확인', 'status': 'FAILED', 'error': '잔고 조회 실패'})
            test_result['error'] = '잔고 조회 실패'
            return test_result
        
        available_balance = balance['available']
        print(f"   ✅ 사용 가능 잔고: {available_balance:.2f} USDT")
        test_result['steps'].append({
            'step': 1, 
            'name': '잔고 확인', 
            'status': 'SUCCESS',
            'available_balance': available_balance
        })
        
        if available_balance < usdt_amount:
            test_result['steps'].append({
                'step': 1, 
                'name': '잔고 확인', 
                'status': 'INSUFFICIENT',
                'error': f'잔고 부족: {available_balance:.2f} < {usdt_amount}'
            })
            test_result['error'] = f'잔고 부족: {available_balance:.2f} < {usdt_amount}'
            print(f"   ❌ 잔고 부족!")
            return test_result
        
        # Step 2: 상품 정보 및 현재가 조회
        print("\n📋 2단계: 상품 정보 조회")
        inst_info = self.get_instrument_info(inst_id)
        
        if not inst_info:
            test_result['steps'].append({'step': 2, 'name': '상품 정보', 'status': 'FAILED'})
            test_result['error'] = '상품 정보 조회 실패'
            return test_result
        
        current_price = self.get_current_price(inst_id)
        print(f"   ✅ 현재가: ${current_price:,.2f}")
        print(f"   📊 최소 수량: {inst_info['min_size']}")
        print(f"   📊 계약 가치: {inst_info['ct_val']}")
        test_result['steps'].append({
            'step': 2, 
            'name': '상품 정보', 
            'status': 'SUCCESS',
            'price': current_price,
            'instrument_info': inst_info
        })
        
        # Step 3: 주문 수량 계산
        print("\n📋 3단계: 주문 수량 계산")
        order_size, calc_details = self.calculate_order_size(inst_id, usdt_amount)
        
        if order_size <= 0:
            test_result['steps'].append({'step': 3, 'name': '수량 계산', 'status': 'FAILED', 'error': calc_details.get('error')})
            test_result['error'] = calc_details.get('error', '수량 계산 실패')
            return test_result
        
        print(f"   ✅ 계산된 계약 수: {order_size}")
        print(f"   💵 실제 주문 금액: ${calc_details['actual_notional']:.2f}")
        test_result['steps'].append({
            'step': 3, 
            'name': '수량 계산', 
            'status': 'SUCCESS',
            'order_size': order_size,
            'calculation_details': calc_details
        })
        
        # Step 4: 실제 주문 실행
        print("\n📋 4단계: 실제 주문 실행")
        print(f"   🚀 시장가 매수 주문 실행 중...")
        
        order_result = self.place_market_order(
            inst_id=inst_id,
            side='buy',
            size=order_size,
            leverage=leverage
        )
        
        if order_result.get('success'):
            print(f"   ✅ 주문 성공!")
            print(f"   📌 주문 ID: {order_result.get('order_id')}")
            
            # 주문 상세 확인
            if order_result.get('detail'):
                detail = order_result['detail']
                print(f"   💰 체결 수량: {detail.get('filled_size')}")
                print(f"   💵 체결 가격: ${detail.get('avg_price', 0):,.2f}")
                print(f"   💸 수수료: ${abs(detail.get('fee', 0)):.6f}")
            
            test_result['steps'].append({
                'step': 4, 
                'name': '주문 실행', 
                'status': 'SUCCESS',
                'order_result': order_result
            })
            test_result['success'] = True
            test_result['order'] = order_result
        else:
            print(f"   ❌ 주문 실패: {order_result.get('error')}")
            test_result['steps'].append({
                'step': 4, 
                'name': '주문 실행', 
                'status': 'FAILED',
                'error': order_result.get('error')
            })
            test_result['error'] = order_result.get('error')
            return test_result
        
        # Step 5: 포지션 확인
        print("\n📋 5단계: 포지션 확인")
        time.sleep(1)  # API 동기화 대기
        
        positions = self.get_positions(inst_id)
        
        if positions:
            for pos in positions:
                print(f"   ✅ 포지션 생성됨:")
                print(f"      📊 수량: {pos['position']}")
                print(f"      💵 평균가: ${pos['avg_price']:,.2f}")
                print(f"      📈 미실현 손익: ${pos['upl']:.2f}")
            
            test_result['steps'].append({
                'step': 5, 
                'name': '포지션 확인', 
                'status': 'SUCCESS',
                'positions': positions
            })
            test_result['positions'] = positions
        else:
            print(f"   ⚠️ 포지션 조회 실패 또는 빈 포지션")
            test_result['steps'].append({
                'step': 5, 
                'name': '포지션 확인', 
                'status': 'WARNING',
                'message': '포지션 조회 실패'
            })
        
        print(f"\n{'='*60}")
        print(f"🎉 구매 테스트 완료!")
        print(f"{'='*60}")
        
        return test_result
    
    def test_close_position(self, inst_id: str = 'BTC-USDT-SWAP', 
                            pos_side: str = 'long') -> Dict:
        """
        포지션 청산 테스트
        """
        print(f"\n{'='*60}")
        print(f"🧪 포지션 청산 테스트")
        print(f"{'='*60}")
        print(f"📌 상품: {inst_id}")
        print(f"📊 포지션 방향: {pos_side}")
        
        # 현재 포지션 확인
        positions = self.get_positions(inst_id)
        target_position = None
        
        for pos in positions:
            if pos['pos_side'] == pos_side:
                target_position = pos
                break
        
        if not target_position:
            print(f"   ❌ 청산할 포지션이 없습니다")
            return {
                'success': False,
                'error': '청산할 포지션이 없음'
            }
        
        print(f"\n📋 현재 포지션:")
        print(f"   📊 수량: {target_position['position']}")
        print(f"   💵 평균가: ${target_position['avg_price']:,.2f}")
        print(f"   📈 미실현 손익: ${target_position['upl']:.2f} ({target_position['upl_ratio']*100:.2f}%)")
        
        # 청산 실행
        print(f"\n🚀 청산 실행 중...")
        close_result = self.close_position(inst_id, pos_side)
        
        if close_result['success']:
            print(f"   ✅ 청산 성공!")
            return {
                'success': True,
                'closed_position': target_position,
                'result': close_result
            }
        else:
            print(f"   ❌ 청산 실패: {close_result.get('error')}")
            return {
                'success': False,
                'error': close_result.get('error'),
                'result': close_result
            }
    
    def get_min_order_info(self, inst_id: str = 'BTC-USDT-SWAP') -> Dict:
        """최소 주문 정보 조회 (상세)"""
        inst_info = self.get_instrument_info(inst_id)
        current_price = self.get_current_price(inst_id)
        
        if not inst_info or not current_price:
            return {'error': '정보 조회 실패'}
        
        ct_val = inst_info['ct_val']
        min_size = inst_info['min_size']
        
        # 최소 주문 금액 계산
        min_notional = min_size * ct_val * current_price
        
        return {
            'inst_id': inst_id,
            'current_price': current_price,
            'contract_value': ct_val,
            'min_contracts': min_size,
            'min_notional_usdt': min_notional,
            'lot_size': inst_info['lot_size'],
            'tick_size': inst_info['tick_size'],
            'recommended_test_amount': max(10, min_notional * 1.2)  # 최소의 120% 또는 10 USDT
        }


# 테스트 실행 예제
if __name__ == "__main__":
    # 설정값 로드 (실제 사용 시에는 config.py에서 가져옴)
    from config import API_KEY, API_SECRET, PASSPHRASE
    
    manager = RealOrderManager(API_KEY, API_SECRET, PASSPHRASE)
    
    # 최소 주문 정보 확인
    print("\n" + "="*60)
    print("📊 최소 주문 정보 조회")
    print("="*60)
    
    for symbol in ['BTC-USDT-SWAP', 'ETH-USDT-SWAP']:
        info = manager.get_min_order_info(symbol)
        if 'error' not in info:
            print(f"\n{symbol}:")
            print(f"  현재가: ${info['current_price']:,.2f}")
            print(f"  계약 가치: {info['contract_value']}")
            print(f"  최소 계약: {info['min_contracts']}")
            print(f"  최소 주문금액: ${info['min_notional_usdt']:.2f}")
            print(f"  권장 테스트금액: ${info['recommended_test_amount']:.2f}")
