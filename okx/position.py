"""
간단한 포지션 관리
복잡한 ORM이나 클래스 없이 기본 기능만 제공
"""

import time
from datetime import datetime
from okx.order_manager import OrderManager

class SimplePositionManager:
    """단순화된 포지션 관리"""
    
    def __init__(self):
        self.order_manager = OrderManager()
        self.positions = {}  # symbol -> position_info
        self.trades_history = []  # 거래 기록
        
    def open_position(self, symbol, side, size, leverage, strategy_name, trailing_stop_ratio=None):
        """포지션 오픈"""
        try:
            # 실제 주문 실행
            order_side = "buy" if side == "long" else "sell"
            order_result = self.order_manager.place_market_order(
                inst_id=symbol,
                side=order_side,
                size=size,
                leverage=leverage
            )
            
            if not order_result:
                print(f"❌ 주문 실패: {symbol}")
                return None
            
            # 체결 확인 대기
            time.sleep(2)
            order_status = self.order_manager.get_order_status(symbol, order_result['order_id'])
            
            if not order_status or order_status['status'] != 'filled':
                print(f"❌ 주문 미체결: {symbol}")
                return None
            
            entry_price = float(order_status.get('avg_price', 0))
            actual_size = float(order_status.get('filled_size', size))
            
            # 포지션 정보 저장
            position_info = {
                'symbol': symbol,
                'side': side,
                'size': actual_size,
                'leverage': leverage,
                'strategy': strategy_name,
                'entry_price': entry_price,
                'entry_time': datetime.now(),
                'peak_price': entry_price if side == 'long' else 0,
                'trough_price': entry_price if side == 'short' else 0,
                'trailing_stop_ratio': trailing_stop_ratio,
                'order_id': order_result['order_id']
            }
            
            self.positions[symbol] = position_info
            
            # 트레일링 스탑 설정
            if trailing_stop_ratio:
                self._set_trailing_stop(symbol, trailing_stop_ratio)
            
            print(f"✅ {strategy_name} 포지션 오픈: {side.upper()} {actual_size} {symbol} @ ${entry_price:.2f}")
            return symbol
            
        except Exception as e:
            print(f"❌ 포지션 오픈 실패: {e}")
            return None
    
    def close_position(self, symbol, reason="manual"):
        """포지션 청산"""
        if symbol not in self.positions:
            return False
            
        position = self.positions[symbol]
        
        try:
            # 포지션 청산
            success = self.order_manager.close_position(symbol)
            
            if success:
                # 거래 기록에 추가
                trade_record = {
                    'symbol': symbol,
                    'strategy': position['strategy'],
                    'side': position['side'],
                    'entry_time': position['entry_time'],
                    'exit_time': datetime.now(),
                    'close_reason': reason,
                    'size': position['size']
                }
                
                self.trades_history.append(trade_record)
                
                # 포지션 목록에서 제거
                del self.positions[symbol]
                
                print(f"✅ 포지션 청산: {symbol} (사유: {reason})")
                return True
            else:
                print(f"❌ 포지션 청산 실패: {symbol}")
                return False
                
        except Exception as e:
            print(f"❌ 포지션 청산 오류: {e}")
            return False
    
    def _set_trailing_stop(self, symbol, callback_ratio):
        """트레일링 스탑 설정"""
        try:
            result = self.order_manager.place_trailing_stop(
                inst_id=symbol,
                callback_ratio=callback_ratio
            )
            
            if result:
                self.positions[symbol]['trailing_algo_id'] = result['algo_id']
                print(f"🎯 트레일링 스탑 설정: {symbol} ({callback_ratio*100:.1f}%)")
        except Exception as e:
            print(f"⚠️ 트레일링 스탑 설정 실패: {e}")
    
    def update_position_prices(self, price_data):
        """포지션 가격 업데이트"""
        for symbol, position in self.positions.items():
            if symbol in price_data:
                current_price = price_data[symbol]
                
                # 피크/트러프 가격 업데이트
                if position['side'] == 'long':
                    if current_price > position['peak_price']:
                        position['peak_price'] = current_price
                else:  # short
                    if position['trough_price'] == 0 or current_price < position['trough_price']:
                        position['trough_price'] = current_price
    
    def get_active_positions(self):
        """활성 포지션 목록"""
        return list(self.positions.keys())
    
    def get_position_info(self, symbol):
        """특정 포지션 정보"""
        return self.positions.get(symbol, {})
    
    def close_all_positions(self):
        """모든 포지션 청산"""
        symbols_to_close = list(self.positions.keys())
        
        for symbol in symbols_to_close:
            self.close_position(symbol, "system_shutdown")
        
        print(f"📤 모든 포지션 청산 완료: {len(symbols_to_close)}개")
    
    def get_summary(self):
        """포지션 요약"""
        active_count = len(self.positions)
        total_trades = len(self.trades_history)
        
        return {
            'active_positions': active_count,
            'total_trades': total_trades,
            'positions': dict(self.positions),
            'recent_trades': self.trades_history[-5:] if self.trades_history else []
        }
    
    def print_status(self):
        """상태 출력"""
        summary = self.get_summary()
        
        print(f"\n📊 포지션 현황")
        print(f"활성 포지션: {summary['active_positions']}개")
        print(f"총 거래 횟수: {summary['total_trades']}회")
        
        if summary['positions']:
            for symbol, pos in summary['positions'].items():
                print(f"  {symbol}: {pos['side'].upper()} {pos['size']} ({pos['strategy']})")