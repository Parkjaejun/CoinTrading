# okx/order_manager.py
"""
OKX 주문 관리자 - 실제 거래 지원
- net_mode / long_short_mode 자동 감지
- 선물(SWAP) 거래 지원
- 레버리지, 트레일링스탑 지원

수정 사항:
- 불필요한 반복 로그 제거 (계좌 레벨, 포지션 모드, 초기화 완료)
- 중요한 로그만 유지 (에러, 주문 성공/실패)
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
    
    def __init__(self, verbose: bool = False):
        """
        Args:
            verbose: True면 상세 로그 출력, False면 최소 로그
        """
        self.open_orders = {}
        self.order_history = []
        self.position_mode = None  # 'net_mode' or 'long_short_mode'
        self.account_level = None  # 1=Simple, 2=Single-currency, 3=Multi-currency, 4=Portfolio
        self.verbose = verbose  # 상세 로그 여부
        
        # 계좌 설정 확인
        self._load_account_config()
    
    def _load_account_config(self):
        """계좌 설정 로드 - 로그 최소화"""
        try:
            result = make_api_request('GET', '/api/v5/account/config')
            if result and result.get('code') == '0':
                config = result['data'][0]
                self.position_mode = config.get('posMode', 'net_mode')
                self.account_level = config.get('acctLv', '1')
                # verbose 모드에서만 출력
                if self.verbose:
                    print(f"📊 계좌 레벨: {self.account_level}")
                    print(f"📊 포지션 모드: {self.position_mode}")
            else:
                self.position_mode = 'net_mode'
                self.account_level = '2'
        except Exception as e:
            if self.verbose:
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
            return 'short' if side == 'buy' else 'long'
        else:
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
        if pos_side is None:
            pos_side = self._get_pos_side(side, reduce_only)
        
        # 주문 로그는 유지 (중요)
        print(f"🚀 시장가 주문: {side.upper()} {size} {inst_id}")
        
        # 레버리지 설정 (진입 시에만)
        if not reduce_only and leverage >= 1:
            self.set_leverage(inst_id, leverage, trade_mode, pos_side)
        
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
        """지정가 주문 실행"""
        if pos_side is None:
            pos_side = self._get_pos_side(side)
        
        print(f"📝 지정가 주문: {side.upper()} {size} {inst_id} @ ${price:,.2f}")
        
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
    
    def _handle_order_error(self, response: Dict):
        """주문 에러 처리 - 에러는 항상 출력"""
        if response:
            code = response.get('code', 'Unknown')
            msg = response.get('msg', 'Unknown error')
            print(f"❌ 주문 실패: [{code}] {msg}")
            
            # 상세 에러 정보
            for order_data in response.get('data', []):
                s_code = order_data.get('sCode', '')
                s_msg = order_data.get('sMsg', '')
                if s_code:
                    print(f"   상세: [{s_code}] {s_msg}")
                    
                    error_hints = {
                        '51000': "💡 USDT 잔고 부족",
                        '51001': "💡 주문 수량 오류",
                        '51008': "💡 주문 금액이 너무 작습니다",
                        '51010': "💡 포지션 모드 불일치",
                        '51020': "💡 주문 수량 초과",
                        '50014': "💡 API 권한 없음",
                    }
                    if s_code in error_hints:
                        print(error_hints[s_code])
        else:
            print(f"❌ 주문 실패: API 응답 없음")
    
    # ==================== 포지션 관련 ====================
    
    def get_positions(self, inst_type: str = "SWAP", inst_id: str = None) -> List[Dict]:
        """포지션 조회 - 로그 제거"""
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
        """포지션 청산"""
        positions = self.get_positions(inst_id=inst_id)
        
        if not positions:
            print(f"❌ 청산할 포지션이 없습니다: {inst_id}")
            return None
        
        if self.position_mode == 'net_mode':
            pos = positions[0]
            pos_side = 'net'
        else:
            for p in positions:
                if pos_side is None or p['pos_side'] == pos_side:
                    pos = p
                    break
            else:
                print(f"❌ 해당 포지션을 찾을 수 없습니다: {pos_side}")
                return None
        
        size = abs(pos['position'])
        side = 'sell' if pos['position'] > 0 else 'buy'
        
        print(f"📤 포지션 청산: {inst_id} {pos_side} {size}")
        
        return self.place_market_order(
            inst_id=inst_id,
            side=side,
            size=size,
            pos_side=pos_side,
            trade_mode=trade_mode,
            reduce_only=True
        )
    
    def close_all_positions(self, inst_type: str = "SWAP") -> bool:
        """모든 포지션 청산"""
        positions = self.get_positions(inst_type=inst_type)
        
        if not positions:
            return False
        
        print(f"🚨 모든 포지션 청산 시작: {len(positions)}개")
        
        success_count = 0
        for pos in positions:
            result = self.close_position(pos['inst_id'], pos['pos_side'])
            if result:
                success_count += 1
        
        print(f"✅ 청산 완료: {success_count}/{len(positions)}")
        return success_count > 0
    
    # ==================== 레버리지 ====================
    
    def set_leverage(self, inst_id: str, lever: int, 
                    mgn_mode: str = "cross", pos_side: str = "net") -> bool:
        """레버리지 설정 - 로그 최소화"""
        data = {
            "instId": inst_id,
            "lever": str(lever),
            "mgnMode": mgn_mode,
        }
        
        if self.position_mode != 'net_mode':
            data["posSide"] = pos_side
        
        response = make_api_request('POST', '/api/v5/account/set-leverage', data=data)
        
        if response and response.get('code') == '0':
            # 성공 로그 제거 (불필요한 반복)
            return True
        else:
            print(f"⚠️ 레버리지 설정 실패: {response.get('msg') if response else 'API 오류'}")
            return False
    
    # ==================== 주문 조회 ====================
    
    def get_order_status(self, inst_id: str, order_id: str) -> Optional[Dict]:
        """주문 상태 조회"""
        params = {
            "instId": inst_id,
            "ordId": order_id
        }
        
        response = make_api_request('GET', '/api/v5/trade/order', params=params)
        
        if response and response.get('code') == '0':
            order_data = response.get('data', [{}])[0]
            return {
                'order_id': order_data.get('ordId'),
                'status': order_data.get('state'),
                'filled_size': float(order_data.get('fillSz') or 0),
                'avg_price': float(order_data.get('avgPx') or 0),
                'fee': float(order_data.get('fee') or 0),
            }
        return None
    
    def cancel_order(self, inst_id: str, order_id: str) -> bool:
        """주문 취소"""
        data = {
            "instId": inst_id,
            "ordId": order_id
        }
        
        response = make_api_request('POST', '/api/v5/trade/cancel-order', data=data)
        
        if response and response.get('code') == '0':
            print(f"✅ 주문 취소 성공: {order_id}")
            if order_id in self.open_orders:
                del self.open_orders[order_id]
            return True
        else:
            print(f"❌ 주문 취소 실패: {response.get('msg') if response else 'API 오류'}")
            return False
    
    # ==================== 잔고 조회 ====================
    
    def get_account_balance(self, currency: str = None) -> Optional[Dict]:
        """계좌 잔고 조회 - 로그 제거"""
        response = make_api_request('GET', '/api/v5/account/balance')
        
        if response and response.get('code') == '0':
            data = response.get('data', [{}])[0]
            
            if currency:
                for detail in data.get('details', []):
                    if detail.get('ccy') == currency:
                        return {
                            'currency': currency,
                            'available': float(detail.get('availBal') or 0),
                            'frozen': float(detail.get('frozenBal') or 0),
                            'equity': float(detail.get('eq') or 0),
                        }
                return None
            
            return data
        return None
    
    def get_current_price(self, inst_id: str) -> Optional[float]:
        """현재가 조회 - 로그 제거"""
        response = make_api_request(
            'GET',
            '/api/v5/market/ticker',
            params={'instId': inst_id}
        )
        
        if response and response.get('code') == '0':
            data = response.get('data', [{}])[0]
            return float(data.get('last', 0))
        return None
    
    # ==================== 트레일링 스탑 ====================
    
    def set_trailing_stop(self, inst_id: str, pos_side: str, 
                         callback_ratio: float, active_price: float = None) -> bool:
        """
        트레일링 스탑 설정
        
        Args:
            callback_ratio: 콜백 비율 (예: 0.05 = 5%)
            active_price: 활성화 가격 (None이면 즉시 활성화)
        """
        data = {
            "instId": inst_id,
            "tdMode": "cross",
            "side": "sell" if pos_side in ['long', 'net'] else "buy",
            "posSide": pos_side,
            "ordType": "move_order_stop",
            "sz": "-1",  # 전체 포지션
            "callbackRatio": str(callback_ratio),
        }
        
        if active_price:
            data["activePx"] = str(active_price)
        
        response = make_api_request('POST', '/api/v5/trade/order-algo', data=data)
        
        if response and response.get('code') == '0':
            print(f"✅ 트레일링 스탑 설정: {callback_ratio*100:.1f}%")
            return True
        else:
            print(f"❌ 트레일링 스탑 설정 실패")
            return False
    
    # ==================== USDT 기반 주문 ====================
    
    def buy_usdt(self, inst_id: str, usdt_amount: float, 
                leverage: int = 1, trade_mode: str = "cross") -> Optional[Dict]:
        """USDT 금액으로 매수"""
        price = self.get_current_price(inst_id)
        if not price:
            print(f"❌ 가격 조회 실패: {inst_id}")
            return None
        
        # 계약 수 계산 (BTC-USDT-SWAP: 1계약 = 0.01 BTC)
        contract_value = 0.01  # BTC 기준
        btc_amount = usdt_amount / price
        size = int(btc_amount / contract_value)
        
        if size < 1:
            print(f"❌ 주문 수량 부족: ${usdt_amount} -> {size} 계약")
            return None
        
        return self.place_market_order(
            inst_id=inst_id,
            side='buy',
            size=size,
            leverage=leverage,
            trade_mode=trade_mode
        )
    
    def sell_usdt(self, inst_id: str, usdt_amount: float, 
                 leverage: int = 1, trade_mode: str = "cross") -> Optional[Dict]:
        """USDT 금액으로 매도 (숏)"""
        price = self.get_current_price(inst_id)
        if not price:
            print(f"❌ 가격 조회 실패: {inst_id}")
            return None
        
        contract_value = 0.01
        btc_amount = usdt_amount / price
        size = int(btc_amount / contract_value)
        
        if size < 1:
            print(f"❌ 주문 수량 부족: ${usdt_amount} -> {size} 계약")
            return None
        
        return self.place_market_order(
            inst_id=inst_id,
            side='sell',
            size=size,
            leverage=leverage,
            trade_mode=trade_mode
        )