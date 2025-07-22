"""
포지션 관리 및 트레일링 스탑 로직
"""

import time
from datetime import datetime
from typing import Dict, List, Optional
from okx.order_manager import OrderManager

class Position:
    """개별 포지션 클래스"""
    def __init__(self, inst_id: str, side: str, size: float, entry_price: float, 
                 leverage: float, strategy_name: str):
        self.inst_id = inst_id
        self.side = side  # 'long' or 'short'
        self.size = abs(size)
        self.entry_price = entry_price
        self.leverage = leverage
        self.strategy_name = strategy_name
        
        self.entry_time = datetime.now()
        self.current_price = entry_price
        self.peak_price = entry_price  # 최고가 (롱) 또는 최저가 (숏)
        self.unrealized_pnl = 0.0
        self.unrealized_pnl_ratio = 0.0
        
        # 트레일링 스탑 설정
        self.trailing_stop_enabled = False
        self.trailing_stop_ratio = 0.0
        self.trailing_stop_price = 0.0
        self.trailing_algo_id = None
        
        # 위험 관리
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0
        
        self.is_active = True
        self.last_update = datetime.now()
    
    def update_price(self, current_price: float):
        """현재 가격 업데이트 및 PnL 계산"""
        self.current_price = current_price
        self.last_update = datetime.now()
        
        # PnL 계산
        if self.side == 'long':
            pnl = (current_price - self.entry_price) * self.size
            # 피크 가격 업데이트 (롱 포지션의 경우 최고가)
            if current_price > self.peak_price:
                self.peak_price = current_price
        else:  # short
            pnl = (self.entry_price - current_price) * self.size
            # 피크 가격 업데이트 (숏 포지션의 경우 최저가)
            if current_price < self.peak_price:
                self.peak_price = current_price
        
        self.unrealized_pnl = pnl
        self.unrealized_pnl_ratio = pnl / (self.entry_price * self.size) if self.size > 0 else 0
        
        # 트레일링 스탑 가격 업데이트
        if self.trailing_stop_enabled:
            self._update_trailing_stop()
    
    def _update_trailing_stop(self):
        """트레일링 스탑 가격 업데이트"""
        if not self.trailing_stop_enabled:
            return
            
        if self.side == 'long':
            # 롱 포지션: 피크 가격에서 일정 비율 하락한 지점
            new_stop_price = self.peak_price * (1 - self.trailing_stop_ratio)
        else:  # short
            # 숏 포지션: 피크 가격에서 일정 비율 상승한 지점
            new_stop_price = self.peak_price * (1 + self.trailing_stop_ratio)
        
        # 스탑 가격이 더 유리한 방향으로만 업데이트
        if self.side == 'long' and new_stop_price > self.trailing_stop_price:
            self.trailing_stop_price = new_stop_price
        elif self.side == 'short' and new_stop_price < self.trailing_stop_price:
            self.trailing_stop_price = new_stop_price
    
    def should_trigger_trailing_stop(self) -> bool:
        """트레일링 스탑 발동 조건 확인"""
        if not self.trailing_stop_enabled or self.trailing_stop_price == 0:
            return False
            
        if self.side == 'long':
            return self.current_price <= self.trailing_stop_price
        else:  # short
            return self.current_price >= self.trailing_stop_price
    
    def set_trailing_stop(self, ratio: float):
        """트레일링 스탑 설정"""
        self.trailing_stop_enabled = True
        self.trailing_stop_ratio = ratio
        
        if self.side == 'long':
            self.trailing_stop_price = self.peak_price * (1 - ratio)
        else:
            self.trailing_stop_price = self.peak_price * (1 + ratio)
    
    def set_stop_loss(self, price: float):
        """손절가 설정"""
        self.stop_loss_price = price
    
    def set_take_profit(self, price: float):
        """익절가 설정"""
        self.take_profit_price = price
    
    def get_info(self) -> dict:
        """포지션 정보 반환"""
        return {
            'inst_id': self.inst_id,
            'strategy': self.strategy_name,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'peak_price': self.peak_price,
            'entry_time': self.entry_time,
            'leverage': self.leverage,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_ratio': self.unrealized_pnl_ratio,
            'trailing_stop_enabled': self.trailing_stop_enabled,
            'trailing_stop_price': self.trailing_stop_price,
            'stop_loss_price': self.stop_loss_price,
            'take_profit_price': self.take_profit_price,
            'is_active': self.is_active
        }


class PositionManager(OrderManager):
    """포지션 관리 클래스"""
    
    def __init__(self):
        super().__init__()
        self.positions: Dict[str, Position] = {}  # position_id -> Position
        self.position_counter = 0
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_equity = 0.0
        
    def open_position(self, inst_id: str, side: str, size: float, 
                     leverage: float, strategy_name: str,
                     trailing_stop_ratio: Optional[float] = None,
                     stop_loss_ratio: Optional[float] = None,
                     take_profit_ratio: Optional[float] = None) -> Optional[str]:
        """포지션 오픈"""
        try:
            # 실제 주문 실행
            order_side = "buy" if side == "long" else "sell"
            order_result = self.place_market_order(
                inst_id=inst_id,
                side=order_side,
                size=size,
                leverage=leverage,
                trade_mode="cross"
            )
            
            if not order_result:
                print(f"포지션 오픈 실패: 주문 실행 오류")
                return None
            
            # 주문 체결 확인
            time.sleep(2)  # 체결 대기
            order_status = self.get_order_status(inst_id, order_result['order_id'])
            
            if not order_status or order_status['status'] != 'filled':
                print(f"포지션 오픈 실패: 주문 미체결")
                return None
            
            entry_price = order_status['avg_price']
            actual_size = order_status['filled_size']
            
            # Position 객체 생성
            self.position_counter += 1
            position_id = f"{strategy_name}_{inst_id}_{self.position_counter}"
            
            position = Position(
                inst_id=inst_id,
                side=side,
                size=actual_size,
                entry_price=entry_price,
                leverage=leverage,
                strategy_name=strategy_name
            )
            
            # 트레일링 스탑 설정
            if trailing_stop_ratio:
                position.set_trailing_stop(trailing_stop_ratio)
                
                # OKX 트레일링 스탑 주문 생성
                trailing_result = self.place_trailing_stop(
                    inst_id=inst_id,
                    callback_ratio=trailing_stop_ratio,
                    position_side="net"
                )
                
                if trailing_result:
                    position.trailing_algo_id = trailing_result['algo_id']
                    print(f"트레일링 스탑 설정: {trailing_stop_ratio*100:.1f}%")
            
            # 손절/익절 설정
            if stop_loss_ratio:
                if side == "long":
                    stop_price = entry_price * (1 - stop_loss_ratio)
                else:
                    stop_price = entry_price * (1 + stop_loss_ratio)
                position.set_stop_loss(stop_price)
            
            if take_profit_ratio:
                if side == "long":
                    tp_price = entry_price * (1 + take_profit_ratio)
                else:
                    tp_price = entry_price * (1 - take_profit_ratio)
                position.set_take_profit(tp_price)
            
            # 포지션 등록
            self.positions[position_id] = position
            
            print(f"포지션 오픈 성공: {position_id}")
            print(f"  {side.upper()} {actual_size} {inst_id} @ {entry_price}")
            print(f"  레버리지: {leverage}배, 전략: {strategy_name}")
            
            return position_id
            
        except Exception as e:
            print(f"포지션 오픈 오류: {e}")
            return None
    
    def close_position(self, position_id: str, reason: str = "manual") -> bool:
        """포지션 청산"""
        if position_id not in self.positions:
            print(f"포지션을 찾을 수 없습니다: {position_id}")
            return False
        
        position = self.positions[position_id]
        
        try:
            # 트레일링 스탑 취소
            if position.trailing_algo_id:
                self.cancel_algo_order(position.trailing_algo_id, position.inst_id)
            
            # 반대 방향 시장가 주문으로 청산
            close_side = "sell" if position.side == "long" else "buy"
            close_result = self.place_market_order(
                inst_id=position.inst_id,
                side=close_side,
                size=position.size,
                reduce_only=True
            )
            
            if not close_result:
                print(f"포지션 청산 실패: {position_id}")
                return False
            
            # 청산 가격 확인
            time.sleep(2)
            order_status = self.get_order_status(position.inst_id, close_result['order_id'])
            
            if order_status and order_status['status'] == 'filled':
                exit_price = order_status['avg_price']
                realized_pnl = order_status['pnl']
                
                print(f"포지션 청산 완료: {position_id}")
                print(f"  진입가: {position.entry_price:.2f}")
                print(f"  청산가: {exit_price:.2f}")
                print(f"  실현 PnL: {realized_pnl:.2f} USDT")
                print(f"  청산 사유: {reason}")
                
                # 포지션 비활성화
                position.is_active = False
                self.total_pnl += realized_pnl
                
                return True
            else:
                print(f"포지션 청산 확인 실패: {position_id}")
                return False
                
        except Exception as e:
            print(f"포지션 청산 오류: {e}")
            return False
    
    def update_all_positions(self, price_data: Dict[str, float]):
        """모든 포지션 가격 업데이트"""
        for position_id, position in self.positions.items():
            if not position.is_active:
                continue
                
            if position.inst_id in price_data:
                position.update_price(price_data[position.inst_id])
                
                # 트레일링 스탑 확인
                if position.should_trigger_trailing_stop():
                    print(f"트레일링 스탑 발동: {position_id}")
                    self.close_position(position_id, "trailing_stop")
                    continue
                
                # 손절/익절 확인
                current_price = position.current_price
                
                if position.stop_loss_price > 0:
                    if (position.side == "long" and current_price <= position.stop_loss_price) or \
                       (position.side == "short" and current_price >= position.stop_loss_price):
                        print(f"손절 발동: {position_id}")
                        self.close_position(position_id, "stop_loss")
                        continue
                
                if position.take_profit_price > 0:
                    if (position.side == "long" and current_price >= position.take_profit_price) or \
                       (position.side == "short" and current_price <= position.take_profit_price):
                        print(f"익절 발동: {position_id}")
                        self.close_position(position_id, "take_profit")
                        continue
    
    def get_active_positions(self) -> List[Position]:
        """활성 포지션 목록 반환"""
        return [pos for pos in self.positions.values() if pos.is_active]
    
    def get_position_summary(self) -> dict:
        """포지션 요약 정보"""
        active_positions = self.get_active_positions()
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in active_positions)
        
        # 전략별 통계
        strategy_stats = {}
        for pos in active_positions:
            strategy = pos.strategy_name
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    'count': 0,
                    'total_pnl': 0.0,
                    'positions': []
                }
            strategy_stats[strategy]['count'] += 1
            strategy_stats[strategy]['total_pnl'] += pos.unrealized_pnl
            strategy_stats[strategy]['positions'].append(pos.get_info())
        
        return {
            'active_position_count': len(active_positions),
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'max_drawdown': self.max_drawdown,
            'strategy_stats': strategy_stats,
            'positions': [pos.get_info() for pos in active_positions]
        }
    
    def close_all_positions(self, strategy_filter: Optional[str] = None) -> bool:
        """모든 포지션 청산"""
        active_positions = self.get_active_positions()
        
        if strategy_filter:
            active_positions = [pos for pos in active_positions 
                              if pos.strategy_name == strategy_filter]
        
        success_count = 0
        for pos in active_positions:
            position_id = None
            for pid, p in self.positions.items():
                if p == pos:
                    position_id = pid
                    break
            
            if position_id and self.close_position(position_id, "manual_close_all"):
                success_count += 1
        
        print(f"포지션 청산 완료: {success_count}/{len(active_positions)}")
        return success_count == len(active_positions)
    
    def calculate_drawdown(self, current_equity: float):
        """최대 낙폭(MDD) 계산"""
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        if self.peak_equity > 0:
            current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
    
    def print_position_status(self):
        """포지션 상태 출력"""
        summary = self.get_position_summary()
        
        print("\n" + "=" * 60)
        print("포지션 현황")
        print("=" * 60)
        print(f"활성 포지션 수: {summary['active_position_count']}")
        print(f"미실현 PnL: {summary['total_unrealized_pnl']:.2f} USDT")
        print(f"실현 PnL: {summary['total_realized_pnl']:.2f} USDT")
        print(f"일일 PnL: {summary['daily_pnl']:.2f} USDT")
        print(f"최대 낙폭: {summary['max_drawdown']*100:.2f}%")
        
        if summary['strategy_stats']:
            print("\n전략별 현황:")
            for strategy, stats in summary['strategy_stats'].items():
                print(f"  {strategy}: {stats['count']}개 포지션, PnL: {stats['total_pnl']:.2f} USDT")
        
        if summary['positions']:
            print("\n개별 포지션:")
            for pos in summary['positions']:
                pnl_ratio = pos['unrealized_pnl_ratio'] * 100
                print(f"  {pos['inst_id']} {pos['side'].upper()}: "
                      f"크기 {pos['size']:.4f}, "
                      f"진입가 {pos['entry_price']:.2f}, "
                      f"현재가 {pos['current_price']:.2f}, "
                      f"PnL {pos['unrealized_pnl']:.2f} ({pnl_ratio:+.2f}%)")
        
        print("=" * 60)