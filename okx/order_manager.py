# okx/order_manager.py
"""
OKX 주문 관리자 - 실제 거래 지원
- net_mode / long_short_mode 자동 감지
- 선물(SWAP) 거래 지원
- 레버리지, 트레일링스탑 지원
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from config import make_api_request


class OrderManager:
    """
    OKX 주문 관리자
    
    주요 기능:
    - 시장가/지정가 주문
    - 포지션 관리 (조회, 청산)
    - 레버리지 설정
    - 트레일링스탑
    """
    
    def __init__(self):
        self.open_orders = {}
        self.order_history = []
        self.position_mode = None  # 'net_mode' or 'long_short_mode'
        self.account_level = None  # 1=Simple, 2=Single-currency, 3=Multi-currency, 4=Portfolio
        
        # 계좌 설정 확인
        self._load_account_config()
        print("✅ OrderManager 초기화 완료")
    
    def _load_account_config(self):
        """계좌 설정 로드"""
        try:
            result = make_api_request('GET', '/api/v5/account/config')
            if result and result.get('code') == '0':
                config = result['data'][0]
                self.position_mode = config.get('posMode', 'net_mode')
                self.account_level = config.get('acctLv', '1')
                print(f"📊 계좌 레벨: {self.account_level}")
                print(f"📊 포지션 모드: {self.position_mode}")
            else:
                print("⚠️ 계좌 설정 로드 실패, 기본값 사용")
                self.position_mode = 'net_mode'
                self.account_level = '2'
        except Exception as e:
            print(f"⚠️ 계좌 설정 로드 예외: {e}")
            self.position_mode = 'net_mode'
            self.account_level = '2'
    
    def _get_pos_side(self, side: str, reduce_only: bool = False) -> str:
        """
        포지션 모드에 따라 posSide 결정
        
        net_mode: posSide = 'net'
        long_short_mode: posSide = 'long' or 'short'
        """
        if self.position_mode == 'net_mode':
            return 'net'
        
        # long_short_mode
        if reduce_only:
            # 청산 시: 기존 포지션 방향 유지
            return 'short' if side == 'buy' else 'long'
        else:
            # 진입 시: buy=long, sell=short
            return 'long' if side == 'buy' else 'short'
    
    # ==================== 주문 관련 ====================
    
    def place_market_order(self, inst_id: str, side: str, size: float, 
                          leverage: int = 1, pos_side: str = None,
                          trade_mode: str = "cross", reduce_only: bool = False) -> Optional[Dict]:
        """
        시장가 주문 실행
        
        Args:
            inst_id: 거래 상품 (예: 'BTC-USDT-SWAP')
            side: 'buy' 또는 'sell'
            size: 주문 수량 (계약 수)
            leverage: 레버리지 배수 (기본 1)
            pos_side: 포지션 방향 (None이면 자동 결정)
            trade_mode: 'cross'(전체) 또는 'isolated'(격리)
            reduce_only: True면 청산 전용
            
        Returns:
            성공 시 주문 정보, 실패 시 None
        """
        # posSide 결정
        if pos_side is None:
            pos_side = self._get_pos_side(side, reduce_only)
        
        print(f"🚀 시장가 주문: {side.upper()} {size} {inst_id}")
        print(f"   posSide: {pos_side}, 레버리지: {leverage}x")
        
        # 레버리지 설정 (진입 시에만)
        if not reduce_only and leverage >= 1:
            self.set_leverage(inst_id, leverage, trade_mode, pos_side)
        
        # 주문 데이터 구성
        order_data = {
            "instId": inst_id,
            "tdMode": trade_mode,
            "side": side,
            "ordType": "market",
            "sz": str(size),
            "posSide": pos_side
        }
        
        if reduce_only:
            order_data["reduceOnly"] = "true"
        
        # 주문 전송
        response = make_api_request('POST', '/api/v5/trade/order', data=order_data)
        
        if response and response.get('code') == '0':
            order_info = response.get('data', [{}])[0]
            order_id = order_info.get('ordId')
            
            order_result = {
                'order_id': order_id,
                'client_order_id': order_info.get('clOrdId'),
                'instrument': inst_id,
                'side': side,
                'pos_side': pos_side,
                'size': size,
                'order_type': 'market',
                'status': 'submitted',
                'timestamp': datetime.now(),
                'leverage': leverage
            }
            
            self.open_orders[order_id] = order_result
            self.order_history.append(order_result)
            
            print(f"✅ 주문 성공! ID: {order_id}")
            return order_result
        else:
            self._handle_order_error(response)
            return None
    
    def place_limit_order(self, inst_id: str, side: str, size: float, price: float,
                         leverage: int = 1, pos_side: str = None,
                         trade_mode: str = "cross") -> Optional[Dict]:
        """
        지정가 주문 실행
        
        Args:
            inst_id: 거래 상품
            side: 'buy' 또는 'sell'
            size: 주문 수량
            price: 지정가
            leverage: 레버리지
            pos_side: 포지션 방향
            trade_mode: 마진 모드
        """
        if pos_side is None:
            pos_side = self._get_pos_side(side)
        
        print(f"📝 지정가 주문: {side.upper()} {size} {inst_id} @ ${price:,.2f}")
        
        # 레버리지 설정
        if leverage >= 1:
            self.set_leverage(inst_id, leverage, trade_mode, pos_side)
        
        order_data = {
            "instId": inst_id,
            "tdMode": trade_mode,
            "side": side,
            "ordType": "limit",
            "sz": str(size),
            "px": str(price),
            "posSide": pos_side
        }
        
        response = make_api_request('POST', '/api/v5/trade/order', data=order_data)
        
        if response and response.get('code') == '0':
            order_info = response.get('data', [{}])[0]
            order_id = order_info.get('ordId')
            
            order_result = {
                'order_id': order_id,
                'instrument': inst_id,
                'side': side,
                'size': size,
                'price': price,
                'order_type': 'limit',
                'status': 'submitted',
                'timestamp': datetime.now()
            }
            
            self.open_orders[order_id] = order_result
            self.order_history.append(order_result)
            
            print(f"✅ 지정가 주문 성공! ID: {order_id}")
            return order_result
        else:
            self._handle_order_error(response)
            return None
    
    def cancel_order(self, inst_id: str, order_id: str = None, 
                    client_order_id: str = None) -> bool:
        """주문 취소"""
        cancel_data = {"instId": inst_id}
        
        if order_id:
            cancel_data["ordId"] = order_id
        elif client_order_id:
            cancel_data["clOrdId"] = client_order_id
        else:
            print("❌ 주문 ID가 필요합니다")
            return False
        
        response = make_api_request('POST', '/api/v5/trade/cancel-order', data=cancel_data)
        
        if response and response.get('code') == '0':
            print(f"✅ 주문 취소 성공: {order_id or client_order_id}")
            if order_id in self.open_orders:
                del self.open_orders[order_id]
            return True
        else:
            print(f"❌ 주문 취소 실패: {response}")
            return False
    
    def get_order_status(self, inst_id: str, order_id: str) -> Optional[Dict]:
        """주문 상태 조회"""
        params = {"instId": inst_id, "ordId": order_id}
        response = make_api_request('GET', '/api/v5/trade/order', params=params)
        
        if response and response.get('code') == '0':
            data = response.get('data', [{}])[0]
            return {
                'order_id': data.get('ordId'),
                'status': data.get('state'),
                'filled_size': float(data.get('fillSz') or 0),
                'avg_price': float(data.get('avgPx') or 0),
                'fee': float(data.get('fee') or 0),
                'pnl': float(data.get('pnl') or 0),
            }
        return None
    
    def _handle_order_error(self, response: Dict):
        """주문 오류 처리"""
        if response and response.get('data'):
            error = response['data'][0]
            s_code = error.get('sCode', '')
            s_msg = error.get('sMsg', '')
            print(f"❌ 주문 실패: [{s_code}] {s_msg}")
            
            # 오류별 해결책 제안
            error_hints = {
                '51000': "💡 잔고 부족. USDT를 충전하세요.",
                '51001': "💡 주문 수량 오류. 최소 수량을 확인하세요.",
                '51008': "💡 주문 금액이 너무 작습니다.",
                '51010': "💡 포지션 모드 불일치. 계좌 설정을 확인하세요.",
                '51020': "💡 주문 수량 초과.",
                '50014': "💡 API 권한 없음. 거래 권한을 확인하세요.",
            }
            if s_code in error_hints:
                print(error_hints[s_code])
        else:
            print(f"❌ 주문 실패: API 응답 없음")
    
    # ==================== 포지션 관련 ====================
    
    def get_positions(self, inst_type: str = "SWAP", inst_id: str = None) -> List[Dict]:
        """
        포지션 조회
        
        Args:
            inst_type: 상품 유형 ('SWAP', 'FUTURES', 'MARGIN')
            inst_id: 특정 상품만 조회 (선택)
        """
        params = {"instType": inst_type}
        if inst_id:
            params["instId"] = inst_id
        
        response = make_api_request('GET', '/api/v5/account/positions', params=params)
        
        if response and response.get('code') == '0':
            positions = []
            for pos in response.get('data', []):
                pos_size = float(pos.get('pos') or 0)
                if pos_size != 0:
                    positions.append({
                        'inst_id': pos.get('instId'),
                        'pos_side': pos.get('posSide'),
                        'position': pos_size,
                        'avg_price': float(pos.get('avgPx') or 0),
                        'upl': float(pos.get('upl') or 0),
                        'upl_ratio': float(pos.get('uplRatio') or 0),
                        'leverage': pos.get('lever'),
                        'liq_price': pos.get('liqPx'),
                        'margin': float(pos.get('margin') or 0),
                        'mgn_mode': pos.get('mgnMode'),
                    })
            return positions
        return []
    
    def close_position(self, inst_id: str, pos_side: str = None, 
                      trade_mode: str = "cross") -> Optional[Dict]:
        """
        포지션 청산
        
        Args:
            inst_id: 거래 상품
            pos_side: 청산할 포지션 방향 ('long', 'short', 'net')
        """
        # 포지션 조회
        positions = self.get_positions(inst_id=inst_id)
        
        if not positions:
            print(f"❌ 청산할 포지션이 없습니다: {inst_id}")
            return None
        
        # net_mode에서는 첫 번째 포지션 사용
        if self.position_mode == 'net_mode':
            target_pos = positions[0]
        else:
            # long_short_mode에서는 지정된 방향 찾기
            target_pos = None
            for pos in positions:
                if pos_side is None or pos['pos_side'] == pos_side:
                    target_pos = pos
                    break
            
            if not target_pos:
                print(f"❌ 해당 방향의 포지션이 없습니다: {pos_side}")
                return None
        
        pos_size = abs(target_pos['position'])
        current_pos_side = target_pos['pos_side']
        
        # 청산 방향 결정
        if self.position_mode == 'net_mode':
            # net_mode: 양수면 매도, 음수면 매수
            close_side = 'sell' if target_pos['position'] > 0 else 'buy'
            close_pos_side = 'net'
        else:
            # long_short_mode: long청산=sell, short청산=buy
            close_side = 'sell' if current_pos_side == 'long' else 'buy'
            close_pos_side = current_pos_side
        
        print(f"📤 포지션 청산: {close_side} {pos_size} {inst_id} ({close_pos_side})")
        print(f"   미실현 손익: ${target_pos['upl']:.2f}")
        
        return self.place_market_order(
            inst_id=inst_id,
            side=close_side,
            size=pos_size,
            pos_side=close_pos_side,
            trade_mode=trade_mode,
            reduce_only=True
        )
    
    def close_all_positions(self, inst_type: str = "SWAP") -> List[Dict]:
        """모든 포지션 청산"""
        positions = self.get_positions(inst_type)
        results = []
        
        for pos in positions:
            result = self.close_position(pos['inst_id'], pos['pos_side'])
            results.append({
                'inst_id': pos['inst_id'],
                'pos_side': pos['pos_side'],
                'success': result is not None
            })
        
        return results
    
    # ==================== 레버리지 ====================
    
    def set_leverage(self, inst_id: str, leverage: int, 
                    margin_mode: str = "cross", pos_side: str = None) -> bool:
        """
        레버리지 설정
        
        Args:
            inst_id: 거래 상품
            leverage: 레버리지 배수
            margin_mode: 'cross' 또는 'isolated'
            pos_side: 포지션 방향 (long_short_mode에서 필요)
        """
        lever_data = {
            "instId": inst_id,
            "lever": str(leverage),
            "mgnMode": margin_mode
        }
        
        # long_short_mode에서는 posSide 필요
        if self.position_mode == 'long_short_mode' and pos_side and pos_side != 'net':
            lever_data["posSide"] = pos_side
        
        response = make_api_request('POST', '/api/v5/account/set-leverage', data=lever_data)
        
        if response and response.get('code') == '0':
            print(f"✅ 레버리지 설정: {inst_id} {leverage}x")
            return True
        else:
            print(f"⚠️ 레버리지 설정 실패: {response}")
            return False
    
    def get_leverage(self, inst_id: str, margin_mode: str = "cross") -> Optional[Dict]:
        """레버리지 조회"""
        params = {"instId": inst_id, "mgnMode": margin_mode}
        response = make_api_request('GET', '/api/v5/account/leverage-info', params=params)
        
        if response and response.get('code') == '0':
            return response.get('data', [])
        return None
    
    # ==================== 트레일링스탑 ====================
    
    def set_trailing_stop(self, inst_id: str, callback_ratio: float,
                         active_px: float = None, pos_side: str = None,
                         trade_mode: str = "cross") -> Optional[Dict]:
        """
        트레일링 스탑 설정
        
        Args:
            inst_id: 거래 상품
            callback_ratio: 콜백 비율 (예: 0.01 = 1%)
            active_px: 활성화 가격 (선택)
            pos_side: 포지션 방향
        """
        # 현재 포지션 확인
        positions = self.get_positions(inst_id=inst_id)
        if not positions:
            print(f"❌ 트레일링스탑 설정 실패: 포지션 없음")
            return None
        
        target_pos = positions[0]
        if pos_side:
            for pos in positions:
                if pos['pos_side'] == pos_side:
                    target_pos = pos
                    break
        
        pos_size = abs(target_pos['position'])
        current_pos_side = target_pos['pos_side'] if self.position_mode == 'long_short_mode' else 'net'
        
        # 청산 방향
        if self.position_mode == 'net_mode':
            side = 'sell' if target_pos['position'] > 0 else 'buy'
        else:
            side = 'sell' if current_pos_side == 'long' else 'buy'
        
        algo_data = {
            "instId": inst_id,
            "tdMode": trade_mode,
            "side": side,
            "posSide": current_pos_side,
            "ordType": "move_order_stop",
            "sz": str(pos_size),
            "callbackRatio": str(callback_ratio),
            "reduceOnly": "true"
        }
        
        if active_px:
            algo_data["activePx"] = str(active_px)
        
        response = make_api_request('POST', '/api/v5/trade/order-algo', data=algo_data)
        
        if response and response.get('code') == '0':
            algo_id = response['data'][0].get('algoId')
            print(f"✅ 트레일링스탑 설정: {callback_ratio*100:.1f}% (ID: {algo_id})")
            return {'algo_id': algo_id, 'callback_ratio': callback_ratio}
        else:
            print(f"❌ 트레일링스탑 설정 실패: {response}")
            return None
    
    def cancel_trailing_stop(self, inst_id: str, algo_id: str) -> bool:
        """트레일링스탑 취소"""
        cancel_data = [{"algoId": algo_id, "instId": inst_id}]
        response = make_api_request('POST', '/api/v5/trade/cancel-algos', data=cancel_data)
        
        if response and response.get('code') == '0':
            print(f"✅ 트레일링스탑 취소: {algo_id}")
            return True
        return False
    
    # ==================== 시장 정보 ====================
    
    def get_current_price(self, inst_id: str) -> Optional[float]:
        """현재가 조회"""
        params = {"instId": inst_id}
        response = make_api_request('GET', '/api/v5/market/ticker', params=params)
        
        if response and response.get('code') == '0':
            data = response.get('data', [{}])[0]
            return float(data.get('last') or 0)
        return None
    
    def get_instrument_info(self, inst_id: str) -> Optional[Dict]:
        """상품 정보 조회"""
        inst_type = "SWAP" if inst_id.endswith("-SWAP") else "SPOT"
        params = {"instType": inst_type, "instId": inst_id}
        
        response = make_api_request('GET', '/api/v5/public/instruments', params=params)
        
        if response and response.get('code') == '0':
            data = response.get('data', [])
            if data:
                inst = data[0]
                return {
                    'inst_id': inst.get('instId'),
                    'min_size': float(inst.get('minSz') or 0.01),
                    'lot_size': float(inst.get('lotSz') or 0.01),
                    'tick_size': float(inst.get('tickSz') or 0.01),
                    'ct_val': float(inst.get('ctVal') or 0.01),
                    'settle_ccy': inst.get('settleCcy', 'USDT'),
                }
        return None
    
    def calculate_order_size(self, inst_id: str, usdt_amount: float) -> Tuple[float, Dict]:
        """
        USDT 금액으로 주문 수량 계산
        
        Returns:
            (계약 수, 계산 정보)
        """
        inst_info = self.get_instrument_info(inst_id)
        current_price = self.get_current_price(inst_id)
        
        if not inst_info or not current_price:
            return 0, {'error': '정보 조회 실패'}
        
        ct_val = inst_info['ct_val']
        contract_value = ct_val * current_price
        contracts = usdt_amount / contract_value
        
        # 최소 단위로 조정
        lot_size = inst_info['lot_size']
        contracts = int(contracts / lot_size) * lot_size
        
        # 최소 수량 확인
        min_size = inst_info['min_size']
        if contracts < min_size:
            contracts = min_size
        
        actual_notional = contracts * ct_val * current_price
        
        return contracts, {
            'current_price': current_price,
            'ct_val': ct_val,
            'min_size': min_size,
            'lot_size': lot_size,
            'requested_usdt': usdt_amount,
            'contracts': contracts,
            'actual_notional': actual_notional
        }
    
    # ==================== 잔고 ====================
    
    def get_account_balance(self, ccy: str = 'USDT') -> Optional[Dict]:
        """잔고 조회"""
        response = make_api_request('GET', '/api/v5/account/balance')
        
        if response and response.get('code') == '0':
            for bal in response['data'][0].get('details', []):
                if bal.get('ccy') == ccy:
                    return {
                        'currency': ccy,
                        'available': float(bal.get('availBal') or 0),
                        'equity': float(bal.get('eq') or 0),
                        'frozen': float(bal.get('frozenBal') or 0),
                    }
        return None
    
    # ==================== 편의 메서드 ====================
    
    def buy(self, inst_id: str, size: float, leverage: int = 1) -> Optional[Dict]:
        """롱 포지션 진입 (매수)"""
        return self.place_market_order(inst_id, 'buy', size, leverage)
    
    def sell(self, inst_id: str, size: float, leverage: int = 1) -> Optional[Dict]:
        """숏 포지션 진입 (매도)"""
        return self.place_market_order(inst_id, 'sell', size, leverage)
    
    def buy_usdt(self, inst_id: str, usdt_amount: float, leverage: int = 1) -> Optional[Dict]:
        """USDT 금액으로 롱 포지션 진입"""
        size, info = self.calculate_order_size(inst_id, usdt_amount)
        if size > 0:
            print(f"📊 ${usdt_amount} → {size} 계약 (실제: ${info['actual_notional']:.2f})")
            return self.buy(inst_id, size, leverage)
        return None
    
    def sell_usdt(self, inst_id: str, usdt_amount: float, leverage: int = 1) -> Optional[Dict]:
        """USDT 금액으로 숏 포지션 진입"""
        size, info = self.calculate_order_size(inst_id, usdt_amount)
        if size > 0:
            print(f"📊 ${usdt_amount} → {size} 계약 (실제: ${info['actual_notional']:.2f})")
            return self.sell(inst_id, size, leverage)
        return None
    
    # ==================== 테스트 ====================
    
    def test_buy_order(self, inst_id: str = 'BTC-USDT-SWAP', 
                       usdt_amount: float = 10, leverage: int = 1) -> Dict:
        """
        구매 테스트 (실제 거래!)
        """
        print(f"\n{'='*60}")
        print(f"🛒 구매 테스트 (실제 거래)")
        print(f"{'='*60}")
        print(f"상품: {inst_id}")
        print(f"금액: ${usdt_amount}")
        print(f"레버리지: {leverage}x")
        
        result = self.buy_usdt(inst_id, usdt_amount, leverage)
        
        if result:
            # 체결 확인
            time.sleep(2)
            status = self.get_order_status(inst_id, result['order_id'])
            
            print(f"\n✅ 구매 성공!")
            if status:
                print(f"   상태: {status['status']}")
                print(f"   체결가: ${status['avg_price']:,.2f}")
                print(f"   수수료: ${abs(status['fee']):.6f}")
            
            return {'success': True, 'order': result, 'status': status}
        
        return {'success': False, 'error': '주문 실패'}
    
    def test_close_position(self, inst_id: str = 'BTC-USDT-SWAP') -> Dict:
        """포지션 청산 테스트"""
        print(f"\n{'='*60}")
        print(f"📤 청산 테스트")
        print(f"{'='*60}")
        
        result = self.close_position(inst_id)
        
        if result:
            print(f"\n✅ 청산 성공!")
            return {'success': True, 'order': result}
        
        return {'success': False, 'error': '청산 실패'}


# ==================== 테스트 실행 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("OrderManager 테스트")
    print("=" * 60)
    
    manager = OrderManager()
    
    # 가격 조회
    price = manager.get_current_price('BTC-USDT-SWAP')
    if price:
        print(f"\n💵 BTC 현재가: ${price:,.2f}")
    
    # 상품 정보
    info = manager.get_instrument_info('BTC-USDT-SWAP')
    if info:
        print(f"📊 최소 수량: {info['min_size']}")
        print(f"📊 계약 가치: {info['ct_val']}")
    
    # 잔고 확인
    balance = manager.get_account_balance('USDT')
    if balance:
        print(f"💰 USDT 잔고: ${balance['available']:.2f}")
    
    # 주문 수량 계산
    size, calc = manager.calculate_order_size('BTC-USDT-SWAP', 10)
    print(f"\n📊 $10 USDT → {size} 계약")
    print(f"   실제 금액: ${calc.get('actual_notional', 0):.2f}")
    
    # 포지션 확인
    positions = manager.get_positions()
    print(f"\n📊 현재 포지션: {len(positions)}개")
    for pos in positions:
        print(f"   {pos['inst_id']} {pos['pos_side']}: {pos['position']}")
        print(f"   손익: ${pos['upl']:.2f} ({pos['upl_ratio']*100:.2f}%)")