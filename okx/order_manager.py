import json
import time
from datetime import datetime
from okx.account import AccountManager

class OrderManager(AccountManager):
    def __init__(self):
        super().__init__()
        self.open_orders = {}
        self.order_history = []
        
    def place_market_order(self, inst_id, side, size, leverage=1, position_side="net", 
                          trade_mode="cross", reduce_only=False):
        """시장가 주문 실행
        
        Args:
            inst_id: 거래 상품 (예: BTC-USDT-SWAP)
            side: buy 또는 sell
            size: 주문 수량 (계약 수)
            leverage: 레버리지 배수
            position_side: net(양방향), long, short
            trade_mode: cross(전체), isolated(격리)
            reduce_only: 포지션 감소 전용 여부
        """
        endpoint = "/api/v5/trade/order"
        
        order_data = {
            "instId": inst_id,
            "tdMode": trade_mode,
            "side": side,
            "ordType": "market",
            "sz": str(size),
            "posSide": position_side
        }
        
        # 포지션 감소 전용이 아닐 때만 레버리지 설정
        if not reduce_only and leverage > 1:
            # 먼저 레버리지 설정
            lever_result = self.set_leverage(inst_id, leverage, trade_mode, position_side)
            if not lever_result:
                print(f"레버리지 설정 실패 - 주문 취소")
                return None
        
        if reduce_only:
            order_data["reduceOnly"] = "true"
            
        response = self._make_request('POST', endpoint, data=order_data)
        
        if response and response.get('code') == '0':
            order_info = response.get('data', [{}])[0]
            order_id = order_info.get('ordId')
            client_order_id = order_info.get('clOrdId')
            
            order_result = {
                'order_id': order_id,
                'client_order_id': client_order_id,
                'instrument': inst_id,
                'side': side,
                'size': size,
                'order_type': 'market',
                'status': 'submitted',
                'timestamp': datetime.now(),
                'leverage': leverage
            }
            
            # 주문 추적을 위해 저장
            self.open_orders[order_id] = order_result
            self.order_history.append(order_result)
            
            print(f"주문 성공: {side} {size} {inst_id} (주문ID: {order_id})")
            return order_result
        else:
            error_msg = response.get('msg', '알 수 없는 오류') if response else 'API 응답 없음'
            print(f"주문 실패: {error_msg}")
            return None
    
    def place_limit_order(self, inst_id, side, size, price, leverage=1, 
                         position_side="net", trade_mode="cross"):
        """지정가 주문 실행"""
        endpoint = "/api/v5/trade/order"
        
        # 레버리지 설정
        if leverage > 1:
            lever_result = self.set_leverage(inst_id, leverage, trade_mode, position_side)
            if not lever_result:
                return None
        
        order_data = {
            "instId": inst_id,
            "tdMode": trade_mode,
            "side": side,
            "ordType": "limit",
            "sz": str(size),
            "px": str(price),
            "posSide": position_side
        }
        
        response = self._make_request('POST', endpoint, data=order_data)
        
        if response and response.get('code') == '0':
            order_info = response.get('data', [{}])[0]
            order_id = order_info.get('ordId')
            
            order_result = {
                'order_id': order_id,
                'client_order_id': order_info.get('clOrdId'),
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
            
            print(f"지정가 주문 성공: {side} {size} {inst_id} @ {price}")
            return order_result
        else:
            error_msg = response.get('msg', '알 수 없는 오류') if response else 'API 응답 없음'
            print(f"지정가 주문 실패: {error_msg}")
            return None
    
    def cancel_order(self, inst_id, order_id=None, client_order_id=None):
        """주문 취소"""
        endpoint = "/api/v5/trade/cancel-order"
        
        cancel_data = {"instId": inst_id}
        if order_id:
            cancel_data["ordId"] = order_id
        elif client_order_id:
            cancel_data["clOrdId"] = client_order_id
        else:
            print("주문 ID 또는 클라이언트 주문 ID가 필요합니다")
            return False
            
        response = self._make_request('POST', endpoint, data=cancel_data)
        
        if response and response.get('code') == '0':
            print(f"주문 취소 성공: {order_id or client_order_id}")
            # 추적 목록에서 제거
            if order_id in self.open_orders:
                del self.open_orders[order_id]
            return True
        else:
            error_msg = response.get('msg', '알 수 없는 오류') if response else 'API 응답 없음'
            print(f"주문 취소 실패: {error_msg}")
            return False
    
    def close_position(self, inst_id, position_side="net", trade_mode="cross"):
        """전체 포지션 청산"""
        # 현재 포지션 조회
        positions = self.get_positions()
        target_position = None
        
        for pos in positions:
            if pos['instrument'] == inst_id:
                if position_side == "net" or pos['position_side'] == position_side:
                    target_position = pos
                    break
        
        if not target_position:
            print(f"청산할 포지션이 없습니다: {inst_id}")
            return False
            
        # 포지션의 반대 방향으로 주문
        position_size = abs(target_position['size'])
        if target_position['size'] > 0:
            close_side = "sell"
        else:
            close_side = "buy"
            
        print(f"포지션 청산 시도: {close_side} {position_size} {inst_id}")
        
        # 시장가 청산 주문
        result = self.place_market_order(
            inst_id=inst_id,
            side=close_side,
            size=position_size,
            position_side=position_side,
            trade_mode=trade_mode,
            reduce_only=True
        )
        
        return result is not None
    
    def set_leverage(self, inst_id, leverage, margin_mode="cross", position_side="net"):
        """레버리지 설정"""
        endpoint = "/api/v5/account/set-leverage"
        
        lever_data = {
            "instId": inst_id,
            "lever": str(leverage),
            "mgnMode": margin_mode
        }
        
        if position_side != "net":
            lever_data["posSide"] = position_side
            
        response = self._make_request('POST', endpoint, data=lever_data)
        
        if response and response.get('code') == '0':
            print(f"레버리지 설정 성공: {inst_id} - {leverage}배")
            return True
        else:
            error_msg = response.get('msg', '알 수 없는 오류') if response else 'API 응답 없음'
            print(f"레버리지 설정 실패: {error_msg}")
            return False
    
    def get_order_status(self, inst_id, order_id=None, client_order_id=None):
        """주문 상태 조회"""
        endpoint = "/api/v5/trade/order"
        
        params = {"instId": inst_id}
        if order_id:
            params["ordId"] = order_id
        elif client_order_id:
            params["clOrdId"] = client_order_id
        else:
            print("주문 ID가 필요합니다")
            return None
            
        response = self._make_request('GET', endpoint, params=params)
        
        if response and response.get('code') == '0':
            order_data = response.get('data', [{}])[0]
            return {
                'order_id': order_data.get('ordId'),
                'client_order_id': order_data.get('clOrdId'),
                'status': order_data.get('state'),
                'filled_size': float(order_data.get('fillSz', 0)),
                'avg_price': float(order_data.get('avgPx', 0)),
                'fee': float(order_data.get('fee', 0)),
                'pnl': float(order_data.get('pnl', 0)),
                'update_time': order_data.get('uTime')
            }
        else:
            print(f"주문 상태 조회 실패: {response}")
            return None
    
    def get_order_history(self, inst_id=None, limit=100):
        """주문 내역 조회"""
        endpoint = "/api/v5/trade/orders-history-archive"
        
        params = {"limit": str(limit)}
        if inst_id:
            params["instId"] = inst_id
            
        response = self._make_request('GET', endpoint, params=params)
        
        if response and response.get('code') == '0':
            orders = []
            for order_data in response.get('data', []):
                order_info = {
                    'order_id': order_data.get('ordId'),
                    'instrument': order_data.get('instId'),
                    'side': order_data.get('side'),
                    'size': float(order_data.get('sz', 0)),
                    'price': float(order_data.get('px', 0)),
                    'filled_size': float(order_data.get('fillSz', 0)),
                    'avg_price': float(order_data.get('avgPx', 0)),
                    'status': order_data.get('state'),
                    'fee': float(order_data.get('fee', 0)),
                    'pnl': float(order_data.get('pnl', 0)),
                    'create_time': order_data.get('cTime'),
                    'update_time': order_data.get('uTime')
                }
                orders.append(order_info)
            return orders
        else:
            print(f"주문 내역 조회 실패: {response}")
            return []
    
    def place_trailing_stop(self, inst_id, callback_ratio, position_side="net", 
                          trade_mode="cross", active_px=None):
        """트레일링 스탑 주문 (OKX 알고리즘 주문 사용)"""
        endpoint = "/api/v5/trade/order-algo"
        
        # 현재 포지션 확인
        positions = self.get_positions()
        target_position = None
        
        for pos in positions:
            if pos['instrument'] == inst_id:
                target_position = pos
                break
                
        if not target_position:
            print(f"트레일링 스탑을 설정할 포지션이 없습니다: {inst_id}")
            return None
        
        position_size = abs(target_position['size'])
        # 포지션 방향의 반대로 청산 주문
        side = "sell" if target_position['size'] > 0 else "buy"
        
        algo_data = {
            "instId": inst_id,
            "tdMode": trade_mode,
            "side": side,
            "posSide": position_side,
            "ordType": "move_order_stop",  # 트레일링 스탑
            "sz": str(position_size),
            "callbackRatio": str(callback_ratio),  # 콜백 비율 (예: 0.01 = 1%)
            "reduceOnly": "true"
        }
        
        if active_px:
            algo_data["activePx"] = str(active_px)
            
        response = self._make_request('POST', endpoint, data=algo_data)
        
        if response and response.get('code') == '0':
            algo_info = response.get('data', [{}])[0]
            algo_id = algo_info.get('algoId')
            
            print(f"트레일링 스탑 설정 성공: {callback_ratio*100:.1f}% (ID: {algo_id})")
            return {
                'algo_id': algo_id,
                'instrument': inst_id,
                'callback_ratio': callback_ratio,
                'size': position_size,
                'side': side
            }
        else:
            error_msg = response.get('msg', '알 수 없는 오류') if response else 'API 응답 없음'
            print(f"트레일링 스탑 설정 실패: {error_msg}")
            return None
    
    def cancel_algo_order(self, algo_id, inst_id):
        """알고리즘 주문 취소 (트레일링 스탑 등)"""
        endpoint = "/api/v5/trade/cancel-algos"
        
        cancel_data = [{
            "algoId": algo_id,
            "instId": inst_id
        }]
        
        response = self._make_request('POST', endpoint, data=cancel_data)
        
        if response and response.get('code') == '0':
            print(f"알고리즘 주문 취소 성공: {algo_id}")
            return True
        else:
            error_msg = response.get('msg', '알 수 없는 오류') if response else 'API 응답 없음'
            print(f"알고리즘 주문 취소 실패: {error_msg}")
            return False