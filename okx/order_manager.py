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
        

    def place_test_order(self, inst_id, side, size, leverage=1, test_mode=True):
        """테스트 주문 실행 (실제 거래 없음)"""
        
        if not test_mode:
            print("⚠️ 실제 거래 모드입니다. test_mode=True로 설정하세요.")
            return None
        
        # 테스트 주문 ID 생성
        test_order_id = f"TEST_{inst_id}_{side}_{int(time.time())}"
        
        # 현재 시장 가격 시뮬레이션 (실제로는 WebSocket에서 가져와야 함)
        simulated_price = {
            'BTC-USDT-SWAP': 45000 + (time.time() % 1000),
            'ETH-USDT-SWAP': 2800 + (time.time() % 100)
        }.get(inst_id, 1000)
        
        test_result = {
            'order_id': test_order_id,
            'instrument': inst_id,
            'side': side,
            'size': size,
            'price': simulated_price,
            'leverage': leverage,
            'order_type': 'market',
            'status': 'TEST_FILLED',
            'timestamp': datetime.now(),
            'test_mode': True,
            'notional_value': size * simulated_price,
            'margin_required': (size * simulated_price) / leverage,
            'fee': size * simulated_price * 0.0005
        }
        
        print(f"🧪 테스트 주문 실행:")
        print(f"  주문 ID: {test_order_id}")
        print(f"  상품: {inst_id}")
        print(f"  방향: {side}")
        print(f"  수량: {size}")
        print(f"  가격: ${simulated_price:,.2f}")
        print(f"  레버리지: {leverage}x")
        print(f"  명목가치: ${test_result['notional_value']:,.2f}")
        print(f"  필요증거금: ${test_result['margin_required']:,.2f}")
        print(f"  수수료: ${test_result['fee']:,.2f}")
        
        # 테스트 주문 기록
        self.order_history.append(test_result)
        
        return test_result

    def validate_and_execute_test(self, inst_id, side, size, leverage=1):
        """검증 후 테스트 거래 실행"""
        from okx.order_validator import OrderValidator
        
        validator = OrderValidator()
        
        # 심볼 검증
        is_valid, error_msg = validator.validate_symbol(inst_id)
        if not is_valid:
            return {'success': False, 'error': error_msg}
        
        # 테스트 가격 가져오기
        test_price = {
            'BTC-USDT-SWAP': 45000,
            'ETH-USDT-SWAP': 2800
        }.get(inst_id, 1000)
        
        # 주문 크기 검증
        is_valid, error_msg = validator.validate_order_size(inst_id, size, test_price)
        if not is_valid:
            return {'success': False, 'error': error_msg}
        
        # 레버리지 검증
        is_valid, error_msg = validator.validate_leverage(inst_id, leverage)
        if not is_valid:
            return {'success': False, 'error': error_msg}
        
        # 모든 검증 통과 시 테스트 주문 실행
        result = self.place_test_order(inst_id, side, size, leverage, test_mode=True)
        
        return {'success': True, 'order': result}








