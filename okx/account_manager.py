import hmac
import hashlib
import base64
import json
import time
import requests
from datetime import datetime
from config import API_KEY, API_SECRET, PASSPHRASE

class AccountManager:
    def __init__(self):
        self.api_key = API_KEY
        self.secret_key = API_SECRET
        self.passphrase = PASSPHRASE
        self.base_url = "https://www.okx.com"
        self.session = requests.Session()
        
    def _generate_signature(self, timestamp, method, request_path, body=""):
        """OKX API 서명 생성"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf-8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _get_headers(self, method, request_path, body=""):
        """API 요청 헤더 생성"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method, endpoint, params=None, data=None):
        """API 요청 실행"""
        url = self.base_url + endpoint
        body = json.dumps(data) if data else ""
        headers = self._get_headers(method, endpoint, body)
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, data=body)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"API 요청 실패: {e}")
            return None
        except Exception as e:
            print(f"예상치 못한 오류: {e}")
            return None
    
    def get_account_balance(self):
        """계좌 잔고 조회"""
        endpoint = "/api/v5/account/balance"
        response = self._make_request('GET', endpoint)
        
        if response and response.get('code') == '0':
            balances = {}
            for balance_info in response.get('data', []):
                for detail in balance_info.get('details', []):
                    currency = detail.get('ccy')
                    available = float(detail.get('availBal', 0))
                    total = float(detail.get('bal', 0))
                    frozen = float(detail.get('frozenBal', 0))
                    
                    balances[currency] = {
                        'available': available,
                        'total': total,
                        'frozen': frozen
                    }
            return balances
        else:
            print(f"잔고 조회 실패: {response}")
            return {}
    
    def get_positions(self, inst_type="SWAP"):
        """현재 포지션 조회"""
        endpoint = "/api/v5/account/positions"
        params = {'instType': inst_type}
        response = self._make_request('GET', endpoint, params=params)
        
        if response and response.get('code') == '0':
            positions = []
            for pos_data in response.get('data', []):
                if float(pos_data.get('pos', 0)) != 0:  # 포지션이 있는 것만
                    position = {
                        'instrument': pos_data.get('instId'),
                        'position_side': pos_data.get('posSide'),
                        'size': float(pos_data.get('pos', 0)),
                        'avg_price': float(pos_data.get('avgPx', 0)),
                        'mark_price': float(pos_data.get('markPx', 0)),
                        'unrealized_pnl': float(pos_data.get('upl', 0)),
                        'unrealized_pnl_ratio': float(pos_data.get('uplRatio', 0)),
                        'margin': float(pos_data.get('margin', 0)),
                        'leverage': float(pos_data.get('lever', 0)),
                        'last_trade_id': pos_data.get('tradeId')
                    }
                    positions.append(position)
            return positions
        else:
            print(f"포지션 조회 실패: {response}")
            return []
    
    def get_account_config(self):
        """계좌 설정 정보 조회"""
        endpoint = "/api/v5/account/config"
        response = self._make_request('GET', endpoint)
        
        if response and response.get('code') == '0':
            config_data = response.get('data', [{}])[0]
            return {
                'account_level': config_data.get('acctLv'),
                'position_mode': config_data.get('posMode'),
                'auto_loan': config_data.get('autoLoan'),
                'account_role': config_data.get('roleType'),
                'margin_mode': config_data.get('mgnIsoMode')
            }
        else:
            print(f"계좌 설정 조회 실패: {response}")
            return {}
    
    def calculate_position_size(self, capital, leverage, price, fee_rate=0.0005):
        """주문 가능한 포지션 크기 계산"""
        try:
            # 수수료를 고려한 실제 투입 가능 자금
            effective_capital = capital * 0.99  # 1% 여유분 확보
            
            # 레버리지를 적용한 명목 거래 금액
            notional_value = effective_capital * leverage
            
            # 계약 수량 계산 (USDT 기준)
            position_size = notional_value / price
            
            # 예상 수수료 계산
            estimated_fee = notional_value * fee_rate
            
            return {
                'position_size': round(position_size, 4),
                'notional_value': round(notional_value, 2),
                'estimated_fee': round(estimated_fee, 2),
                'required_margin': round(effective_capital, 2)
            }
        except Exception as e:
            print(f"포지션 크기 계산 오류: {e}")
            return None
    
    def get_trading_fee_rate(self, inst_type="SWAP", inst_family="BTC-USD"):
        """거래 수수료율 조회"""
        endpoint = "/api/v5/account/trade-fee"
        params = {
            'instType': inst_type,
            'instFamily': inst_family
        }
        response = self._make_request('GET', endpoint, params=params)
        
        if response and response.get('code') == '0':
            fee_data = response.get('data', [{}])[0]
            return {
                'maker_fee': float(fee_data.get('maker', 0)),
                'taker_fee': float(fee_data.get('taker', 0)),
                'delivery_fee': float(fee_data.get('delivery', 0))
            }
        else:
            return {
                'maker_fee': 0.0002,  # 기본값
                'taker_fee': 0.0005,  # 기본값
                'delivery_fee': 0.0000
            }
    
    def get_max_leverage(self, inst_id="BTC-USDT-SWAP", margin_mode="cross"):
        """최대 레버리지 조회"""
        endpoint = "/api/v5/account/max-size"
        params = {
            'instId': inst_id,
            'tdMode': margin_mode
        }
        response = self._make_request('GET', endpoint, params=params)
        
        if response and response.get('code') == '0':
            max_data = response.get('data', [{}])[0]
            return {
                'max_buy': float(max_data.get('maxBuy', 0)),
                'max_sell': float(max_data.get('maxSell', 0))
            }
        else:
            print(f"최대 레버리지 조회 실패: {response}")
            return {'max_buy': 0, 'max_sell': 0}
    
    def check_account_status(self):
        """계좌 상태 종합 점검"""
        print("=== 계좌 상태 점검 ===")
        
        # 잔고 확인
        balances = self.get_account_balance()
        print(f"잔고 정보: {balances}")
        
        # 포지션 확인
        positions = self.get_positions()
        print(f"현재 포지션 수: {len(positions)}")
        for pos in positions:
            print(f"  - {pos['instrument']}: {pos['size']} (PnL: {pos['unrealized_pnl']:.2f})")
        
        # 계좌 설정 확인
        config = self.get_account_config()
        print(f"계좌 설정: {config}")
        
        # 수수료율 확인
        fees = self.get_trading_fee_rate()
        print(f"수수료율: Maker {fees['maker_fee']*100:.3f}%, Taker {fees['taker_fee']*100:.3f}%")
        
        return {
            'balances': balances,
            'positions': positions,
            'config': config,
            'fees': fees
        }