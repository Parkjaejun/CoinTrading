# simulation/virtual_order_manager.py
"""
가상 주문 관리자 - 실제 주문 없이 시뮬레이션만 처리
실시간 시장 데이터를 받아와서 가상 거래 실행
"""

import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"

@dataclass
class VirtualOrder:
    """가상 주문 데이터 클래스"""
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: OrderType
    size: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    trailing_ratio: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    create_time: datetime = None
    fill_time: Optional[datetime] = None
    fill_price: Optional[float] = None
    fee: float = 0.0
    strategy_name: str = "unknown"
    
    def __post_init__(self):
        if self.create_time is None:
            self.create_time = datetime.now()

@dataclass
class VirtualPosition:
    """가상 포지션 데이터 클래스"""
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    entry_time: datetime = None
    strategy_name: str = "unknown"
    leverage: int = 1
    peak_price: float = 0.0  # 트레일링 스탑용
    trough_price: float = 0.0  # 트레일링 스탑용 (숏)
    
    def __post_init__(self):
        if self.entry_time is None:
            self.entry_time = datetime.now()
        self.peak_price = self.entry_price
        self.trough_price = self.entry_price

class VirtualOrderManager:
    """가상 주문 관리자 - 실제 주문 없이 시뮬레이션"""
    
    def __init__(self, initial_balance: float = 10000.0, fee_rate: float = 0.0005):
        # 계좌 정보
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.fee_rate = fee_rate
        self.total_fees_paid = 0.0
        
        # 주문 및 포지션 관리
        self.orders: Dict[str, VirtualOrder] = {}
        self.positions: Dict[str, VirtualPosition] = {}
        self.order_history: List[VirtualOrder] = []
        self.trade_history: List[Dict] = []
        
        # 현재 시장 가격
        self.current_prices: Dict[str, float] = {}
        
        # 슬리피지 시뮬레이션
        self.slippage_rate = 0.001  # 0.1% 슬리피지
        
        print(f"🎮 가상 거래 시스템 초기화 - 초기 잔고: ${initial_balance:,.2f}")
    
    def update_market_price(self, symbol: str, price: float):
        """시장 가격 업데이트 (WebSocket에서 호출)"""
        self.current_prices[symbol] = price
        
        # 기존 포지션 PnL 업데이트
        if symbol in self.positions:
            self._update_position_pnl(symbol, price)
        
        # 대기 중인 주문 체크
        self._check_pending_orders(symbol, price)
    
    def place_market_order(self, symbol: str, side: str, size: float, 
                          strategy_name: str = "manual", leverage: int = 1) -> str:
        """시장가 주문 (즉시 체결 시뮬레이션)"""
        if symbol not in self.current_prices:
            print(f"❌ {symbol} 시장 가격 정보 없음")
            return None
        
        # 주문 ID 생성
        order_id = str(uuid.uuid4())[:8]
        
        # 현재 시장가 + 슬리피지
        market_price = self.current_prices[symbol]
        slippage = market_price * self.slippage_rate
        fill_price = market_price + slippage if side == 'buy' else market_price - slippage
        
        # 잔고 확인
        required_margin = (size * fill_price) / leverage
        if required_margin > self.current_balance:
            print(f"❌ 잔고 부족 - 필요: ${required_margin:.2f}, 보유: ${self.current_balance:.2f}")
            return None
        
        # 수수료 계산
        notional_value = size * fill_price
        fee = notional_value * self.fee_rate
        
        # 주문 생성 및 즉시 체결
        order = VirtualOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            size=size,
            status=OrderStatus.FILLED,
            fill_time=datetime.now(),
            fill_price=fill_price,
            fee=fee,
            strategy_name=strategy_name
        )
        
        # 포지션 생성 또는 업데이트
        self._execute_order(order, leverage)
        
        print(f"✅ 시장가 주문 체결: {side.upper()} {size:.6f} {symbol} @ ${fill_price:.2f}")
        return order_id
    
    def place_limit_order(self, symbol: str, side: str, size: float, 
                         price: float, strategy_name: str = "manual") -> str:
        """지정가 주문 (조건 만족시 체결)"""
        order_id = str(uuid.uuid4())[:8]
        
        order = VirtualOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            size=size,
            price=price,
            strategy_name=strategy_name
        )
        
        self.orders[order_id] = order
        print(f"📝 지정가 주문 등록: {side.upper()} {size:.6f} {symbol} @ ${price:.2f}")
        return order_id
    
    def place_trailing_stop(self, symbol: str, trailing_ratio: float) -> str:
        """트레일링 스탑 주문"""
        if symbol not in self.positions:
            print(f"❌ {symbol} 포지션이 없습니다")
            return None
        
        position = self.positions[symbol]
        order_id = str(uuid.uuid4())[:8]
        
        # 트레일링 스탑 주문 생성
        order = VirtualOrder(
            order_id=order_id,
            symbol=symbol,
            side='sell' if position.side == 'long' else 'buy',
            order_type=OrderType.TRAILING_STOP,
            size=position.size,
            trailing_ratio=trailing_ratio,
            strategy_name=position.strategy_name
        )
        
        self.orders[order_id] = order
        print(f"🎯 트레일링 스탑 설정: {trailing_ratio*100:.1f}% | {symbol}")
        return order_id
    
    def close_position(self, symbol: str, reason: str = "manual") -> bool:
        """포지션 청산"""
        if symbol not in self.positions:
            print(f"❌ {symbol} 포지션이 없습니다")
            return False
        
        position = self.positions[symbol]
        
        # 반대 방향으로 시장가 주문
        close_side = 'sell' if position.side == 'long' else 'buy'
        order_id = self.place_market_order(
            symbol=symbol,
            side=close_side,
            size=position.size,
            strategy_name=f"{position.strategy_name}_close"
        )
        
        if order_id:
            # 거래 기록 추가
            self.trade_history.append({
                'symbol': symbol,
                'strategy': position.strategy_name,
                'side': position.side,
                'entry_price': position.entry_price,
                'exit_price': self.current_prices.get(symbol, 0),
                'size': position.size,
                'pnl': position.unrealized_pnl,
                'entry_time': position.entry_time,
                'exit_time': datetime.now(),
                'close_reason': reason
            })
            print(f"💰 포지션 청산: {symbol} | PnL: ${position.unrealized_pnl:+.2f}")
            return True
        
        return False
    
    def _execute_order(self, order: VirtualOrder, leverage: int = 1):
        """주문 실행 처리"""
        symbol = order.symbol
        
        # 수수료 차감
        self.current_balance -= order.fee
        self.total_fees_paid += order.fee
        
        # 포지션 생성 또는 청산
        if symbol in self.positions:
            position = self.positions[symbol]
            
            # 같은 방향이면 포지션 확장, 반대 방향이면 청산
            if (position.side == 'long' and order.side == 'sell') or \
               (position.side == 'short' and order.side == 'buy'):
                # 포지션 청산
                self._close_position(position, order.fill_price)
            else:
                # 포지션 확장 (현재는 단순 구현)
                pass
        else:
            # 새 포지션 생성
            self._create_position(order, leverage)
        
        # 주문 기록
        self.order_history.append(order)
        if order.order_id in self.orders:
            del self.orders[order.order_id]
    
    def _create_position(self, order: VirtualOrder, leverage: int):
        """새 포지션 생성"""
        position_side = 'long' if order.side == 'buy' else 'short'
        
        position = VirtualPosition(
            symbol=order.symbol,
            side=position_side,
            size=order.size,
            entry_price=order.fill_price,
            current_price=order.fill_price,
            strategy_name=order.strategy_name,
            leverage=leverage
        )
        
        self.positions[order.symbol] = position
        
        # 마진 차감
        required_margin = (order.size * order.fill_price) / leverage
        self.current_balance -= required_margin
    
    def _close_position(self, position: VirtualPosition, exit_price: float):
        """포지션 청산 처리"""
        # PnL 계산
        if position.side == 'long':
            pnl = (exit_price - position.entry_price) * position.size
        else:  # short
            pnl = (position.entry_price - exit_price) * position.size
        
        # 레버리지 효과 적용
        pnl *= position.leverage
        
        # 마진 반환 + PnL
        margin_return = (position.size * position.entry_price) / position.leverage
        self.current_balance += margin_return + pnl
        
        # 포지션 제거
        del self.positions[position.symbol]
    
    def _update_position_pnl(self, symbol: str, current_price: float):
        """포지션 미실현 PnL 업데이트"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        position.current_price = current_price
        
        # 미실현 PnL 계산
        if position.side == 'long':
            position.unrealized_pnl = (current_price - position.entry_price) * position.size * position.leverage
            # 트레일링용 최고가 업데이트
            if current_price > position.peak_price:
                position.peak_price = current_price
        else:  # short
            position.unrealized_pnl = (position.entry_price - current_price) * position.size * position.leverage
            # 트레일링용 최저가 업데이트
            if current_price < position.trough_price or position.trough_price == 0:
                position.trough_price = current_price
    
    def _check_pending_orders(self, symbol: str, current_price: float):
        """대기 중인 주문 체결 확인"""
        orders_to_execute = []
        
        for order_id, order in self.orders.items():
            if order.symbol != symbol or order.status != OrderStatus.PENDING:
                continue
            
            should_execute = False
            
            # 지정가 주문 체결 확인
            if order.order_type == OrderType.LIMIT:
                if (order.side == 'buy' and current_price <= order.price) or \
                   (order.side == 'sell' and current_price >= order.price):
                    should_execute = True
                    order.fill_price = order.price
            
            # 트레일링 스탑 체결 확인
            elif order.order_type == OrderType.TRAILING_STOP:
                if symbol in self.positions:
                    position = self.positions[symbol]
                    
                    if position.side == 'long':
                        stop_price = position.peak_price * (1 - order.trailing_ratio)
                        if current_price <= stop_price:
                            should_execute = True
                    else:  # short
                        stop_price = position.trough_price * (1 + order.trailing_ratio)
                        if current_price >= stop_price:
                            should_execute = True
                    
                    if should_execute:
                        order.fill_price = current_price
            
            if should_execute:
                order.status = OrderStatus.FILLED
                order.fill_time = datetime.now()
                orders_to_execute.append(order)
        
        # 체결된 주문들 실행
        for order in orders_to_execute:
            self._execute_order(order)
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """포트폴리오 요약 정보"""
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized_pnl = sum(trade['pnl'] for trade in self.trade_history)
        
        total_value = self.current_balance + total_unrealized_pnl
        total_return = ((total_value - self.initial_balance) / self.initial_balance) * 100
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_value': total_value,
            'unrealized_pnl': total_unrealized_pnl,
            'realized_pnl': total_realized_pnl,
            'total_return': total_return,
            'total_fees': self.total_fees_paid,
            'active_positions': len(self.positions),
            'total_trades': len(self.trade_history),
            'positions': dict(self.positions)
        }
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """거래 요약 통계"""
        if not self.trade_history:
            return {'total_trades': 0, 'win_rate': 0, 'profit_factor': 0}
        
        profitable_trades = [t for t in self.trade_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trade_history if t['pnl'] < 0]
        
        win_rate = len(profitable_trades) / len(self.trade_history) * 100
        
        total_profit = sum(t['pnl'] for t in profitable_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        return {
            'total_trades': len(self.trade_history),
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': total_profit / len(profitable_trades) if profitable_trades else 0,
            'avg_loss': total_loss / len(losing_trades) if losing_trades else 0
        }
    
    def print_status(self):
        """현재 상태 출력"""
        summary = self.get_portfolio_summary()
        trade_stats = self.get_trade_summary()
        
        print(f"\n{'='*60}")
        print(f"🎮 가상 거래 포트폴리오 현황")
        print(f"{'='*60}")
        print(f"💰 총 자산: ${summary['total_value']:,.2f} ({summary['total_return']:+.2f}%)")
        print(f"💳 현금 잔고: ${summary['current_balance']:,.2f}")
        print(f"📊 미실현 PnL: ${summary['unrealized_pnl']:+,.2f}")
        print(f"💸 수수료: ${summary['total_fees']:,.2f}")
        print(f"📈 활성 포지션: {summary['active_positions']}개")
        print(f"🎯 총 거래: {trade_stats['total_trades']}회 (승률: {trade_stats['win_rate']:.1f}%)")
        
        if self.positions:
            print(f"\n📊 활성 포지션:")
            for symbol, position in self.positions.items():
                print(f"  {symbol}: {position.side.upper()} {position.size:.6f} @ ${position.entry_price:.2f}")
                print(f"    현재가: ${position.current_price:.2f} | PnL: ${position.unrealized_pnl:+.2f}")
        
        print(f"{'='*60}")

# 전역 가상 주문 관리자
virtual_order_manager = VirtualOrderManager()