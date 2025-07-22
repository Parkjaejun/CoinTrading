# okx/order_validator.py
"""
주문 검증 시스템
안전하고 정확한 주문 실행을 위한 검증 로직
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from okx.account_manager import AccountManager
from utils.logger import log_error, log_system
import re

class OrderValidator:
    def __init__(self):
        self.account_manager = AccountManager()
        
        # 검증 기준 설정
        self.min_order_values = {
            'BTC-USDT-SWAP': {'min_size': 0.001, 'min_notional': 10},
            'ETH-USDT-SWAP': {'min_size': 0.01, 'min_notional': 10},
            'DEFAULT': {'min_size': 1, 'min_notional': 10}
        }
        
        self.max_position_limits = {
            'BTC-USDT-SWAP': {'max_notional': 100000, 'max_leverage': 100},
            'ETH-USDT-SWAP': {'max_notional': 100000, 'max_leverage': 100},
            'DEFAULT': {'max_notional': 50000, 'max_leverage': 50}
        }
        
        # 주문 속도 제한
        self.order_history = []
        self.max_orders_per_minute = 30
        
        # 안전 설정
        self.max_capital_per_trade = 0.20  # 거래당 최대 20%
        self.max_daily_trades = 100
        
    def validate_symbol(self, symbol: str) -> Tuple[bool, str]:
        """심볼 유효성 검증"""
        if not symbol:
            return False, "심볼이 없습니다"
        
        # OKX SWAP 심볼 패턴 검증
        pattern = r'^[A-Z]+-[A-Z]+-SWAP
        if not re.match(pattern, symbol):
            return False, f"잘못된 심볼 형식: {symbol} (예: BTC-USDT-SWAP)"
        
        return True, ""
    
    def validate_order_size(self, symbol: str, size: float, price: float) -> Tuple[bool, str]:
        """주문 크기 검증"""
        if size <= 0:
            return False, "주문 크기는 0보다 커야 합니다"
        
        # 심볼별 최소 크기 확인
        limits = self.min_order_values.get(symbol, self.min_order_values['DEFAULT'])
        
        if size < limits['min_size']:
            return False, f"최소 주문 크기: {limits['min_size']}, 요청: {size}"
        
        # 최소 명목 가치 확인
        notional_value = size * price
        if notional_value < limits['min_notional']:
            return False, f"최소 주문 금액: ${limits['min_notional']}, 요청: ${notional_value:.2f}"
        
        return True, ""
    
    def validate_leverage(self, symbol: str, leverage: int) -> Tuple[bool, str]:
        """레버리지 검증"""
        if leverage < 1:
            return False, "레버리지는 1 이상이어야 합니다"
        
        max_leverage = self.max_position_limits.get(symbol, self.max_position_limits['DEFAULT'])['max_leverage']
        
        if leverage > max_leverage:
            return False, f"최대 레버리지: {max_leverage}, 요청: {leverage}"
        
        return True, ""
    
    def validate_balance(self, required_margin: float, symbol: str = None) -> Tuple[bool, str]:
        """잔고 검증"""
        try:
            balances = self.account_manager.get_account_balance()
            
            if not balances or 'USDT' not in balances:
                return False, "USDT 잔고 조회 실패"
            
            available_balance = balances['USDT']['available']
            
            if available_balance < required_margin:
                return False, f"잔고 부족: 필요 ${required_margin:.2f}, 보유 ${available_balance:.2f}"
            
            # 안전 마진 (5% 여유분)
            safe_margin = required_margin * 1.05
            if available_balance < safe_margin:
                return False, f"안전 마진 부족: 권장 ${safe_margin:.2f}, 보유 ${available_balance:.2f}"
            
            return True, ""
            
        except Exception as e:
            return False, f"잔고 검증 오류: {str(e)}"
    
    def validate_position_limits(self, symbol: str, new_size: float, new_leverage: int, 
                               current_positions: List[Dict] = None) -> Tuple[bool, str]:
        """포지션 한계 검증"""
        try:
            # 현재 포지션 조회
            if current_positions is None:
                current_positions = self.account_manager.get_positions()
            
            # 동일 심볼 기존 포지션 확인
            existing_position = None
            for pos in current_positions:
                if pos['instrument'] == symbol:
                    existing_position = pos
                    break
            
            # 총 포지션 크기 계산
            total_size = new_size
            if existing_position:
                total_size += abs(existing_position['size'])
            
            # 최대 포지션 크기 확인
            max_limits = self.max_position_limits.get(symbol, self.max_position_limits['DEFAULT'])
            max_notional = max_limits['max_notional']
            
            # 현재 가격으로 명목 가치 계산 (간략화)
            estimated_price = self._get_estimated_price(symbol)
            if estimated_price:
                total_notional = total_size * estimated_price * new_leverage
                
                if total_notional > max_notional:
                    return False, f"최대 포지션 한계 초과: ${max_notional:,} vs ${total_notional:,.0f}"
            
            return True, ""
            
        except Exception as e:
            log_error("포지션 한계 검증 오류", e)
            return False, f"포지션 검증 실패: {str(e)}"
    
    def validate_order_rate(self) -> Tuple[bool, str]:
        """주문 속도 제한 검증"""
        current_time = datetime.now()
        
        # 1분 이내 주문만 카운트
        recent_orders = [
            order_time for order_time in self.order_history
            if current_time - order_time <= timedelta(minutes=1)
        ]
        
        if len(recent_orders) >= self.max_orders_per_minute:
            return False, f"주문 속도 제한: 분당 최대 {self.max_orders_per_minute}회"
        
        return True, ""
    
    def validate_capital_allocation(self, required_capital: float, 
                                  total_capital: float) -> Tuple[bool, str]:
        """자본 배분 검증"""
        if total_capital <= 0:
            return False, "총 자본이 0 이하입니다"
        
        allocation_ratio = required_capital / total_capital
        
        if allocation_ratio > self.max_capital_per_trade:
            return False, f"거래당 최대 자본 비율 초과: {self.max_capital_per_trade*100:.0f}% vs {allocation_ratio*100:.1f}%"
        
        return True, ""
    
    def _get_estimated_price(self, symbol: str) -> Optional[float]:
        """예상 가격 조회 (간단한 구현)"""
        try:
            # 실제로는 현재 시장가를 조회해야 함
            # 여기서는 간략화
            return 50000.0 if 'BTC' in symbol else 3000.0 if 'ETH' in symbol else 1.0
        except:
            return None
    
    def validate_market_conditions(self, symbol: str) -> Tuple[bool, str]:
        """시장 상황 검증"""
        try:
            # 시장 개장 시간 확인 (암호화폐는 24시간이므로 항상 True)
            
            # 거래량 확인 (실제 구현 시 필요)
            # 높은 변동성 시간대 체크 등
            
            return True, ""
            
        except Exception as e:
            return False, f"시장 상황 검증 실패: {str(e)}"
    
    def comprehensive_validation(self, order_params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """종합 주문 검증"""
        errors = []
        
        # 필수 파라미터 확인
        required_params = ['symbol', 'side', 'size', 'price', 'leverage']
        for param in required_params:
            if param not in order_params or order_params[param] is None:
                errors.append(f"필수 파라미터 누락: {param}")
        
        if errors:
            return False, errors
        
        symbol = order_params['symbol']
        size = float(order_params['size'])
        price = float(order_params['price'])
        leverage = int(order_params.get('leverage', 1))
        side = order_params['side']
        
        # 개별 검증 실행
        validations = [
            self.validate_symbol(symbol),
            self.validate_order_size(symbol, size, price),
            self.validate_leverage(symbol, leverage),
            self.validate_order_rate(),
            self.validate_market_conditions(symbol)
        ]
        
        for is_valid, error_msg in validations:
            if not is_valid:
                errors.append(error_msg)
        
        # 잔고 검증
        required_margin = (size * price) / leverage
        balance_valid, balance_error = self.validate_balance(required_margin, symbol)
        if not balance_valid:
            errors.append(balance_error)
        
        # 포지션 한계 검증
        position_valid, position_error = self.validate_position_limits(symbol, size, leverage)
        if not position_valid:
            errors.append(position_error)
        
        # 자본 배분 검증 (총 자본 정보가 있다면)
        if 'total_capital' in order_params:
            capital_valid, capital_error = self.validate_capital_allocation(
                required_margin, order_params['total_capital']
            )
            if not capital_valid:
                errors.append(capital_error)
        
        return len(errors) == 0, errors
    
    def record_order_attempt(self):
        """주문 시도 기록 (속도 제한용)"""
        self.order_history.append(datetime.now())
        
        # 오래된 기록 정리 (메모리 절약)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.order_history = [
            order_time for order_time in self.order_history
            if order_time > cutoff_time
        ]
    
    def get_validation_summary(self, symbol: str) -> Dict[str, Any]:
        """검증 기준 요약"""
        min_limits = self.min_order_values.get(symbol, self.min_order_values['DEFAULT'])
        max_limits = self.max_position_limits.get(symbol, self.max_position_limits['DEFAULT'])
        
        return {
            'symbol': symbol,
            'min_order_size': min_limits['min_size'],
            'min_notional_value': min_limits['min_notional'],
            'max_leverage': max_limits['max_leverage'],
            'max_position_notional': max_limits['max_notional'],
            'max_orders_per_minute': self.max_orders_per_minute,
            'max_capital_per_trade': f"{self.max_capital_per_trade*100:.0f}%"
        }

# 전역 검증기 인스턴스
order_validator = OrderValidator()

def validate_order(order_params: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """주문 검증 (메인 함수)"""
    is_valid, errors = order_validator.comprehensive_validation(order_params)
    
    if is_valid:
        order_validator.record_order_attempt()
        log_system(f"주문 검증 통과: {order_params.get('symbol', 'Unknown')}")
    else:
        log_error(f"주문 검증 실패: {'; '.join(errors)}")
    
    return is_valid, errors

def get_order_limits(symbol: str) -> Dict[str, Any]:
    """주문 한계 정보 조회"""
    return order_validator.get_validation_summary(symbol)