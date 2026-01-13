# strategy/real_only_strategy_manager.py
"""
실제 거래 전용 전략 관리자
시뮬레이션/가상 모드 없이 실제 거래만 수행
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple


class RealOnlyStrategyManager:
    """
    실제 거래 전용 전략 관리자
    - 시뮬레이션 모드 완전 제거
    - 실제 주문만 실행
    - 실패 시 시뮬레이션으로 대체하지 않음
    """
    
    def __init__(self, order_manager, symbols: List[str] = None, leverage: int = 1):
        # 주문 관리자
        self.order_manager = order_manager
        
        # 거래 설정
        self.symbols = symbols or ['BTC-USDT-SWAP']
        self.leverage = leverage
        
        # 거래 상태
        self.is_running = False
        self.active_positions = {}  # symbol -> position_info
        
        # 거래 기록
        self.trade_history = []
        self.last_trade_time = None
        
        # 안전 설정
        self.max_position_per_symbol = 1  # 심볼당 최대 포지션 수
        self.min_trade_interval = 60  # 최소 거래 간격 (초)
        self.max_daily_trades = 50  # 일일 최대 거래 수
        self.daily_trade_count = 0
        self.last_daily_reset = datetime.now().date()
        
        # 손익 추적
        self.total_realized_pnl = 0.0
        self.total_fees = 0.0
        
        print("=" * 60)
        print("💰 실제 거래 전용 전략 관리자 초기화")
        print("=" * 60)
        print(f"📌 거래 심볼: {', '.join(self.symbols)}")
        print(f"📊 레버리지: {self.leverage}x")
        print(f"⚠️ 시뮬레이션 모드: 비활성화")
        print("=" * 60)
        
    def _reset_daily_counter(self):
        """일일 거래 카운터 리셋"""
        today = datetime.now().date()
        if today != self.last_daily_reset:
            self.daily_trade_count = 0
            self.last_daily_reset = today
            print(f"📅 일일 거래 카운터 리셋: {today}")
    
    def _can_trade(self) -> Tuple[bool, str]:
        """거래 가능 여부 확인"""
        self._reset_daily_counter()
        
        # 일일 거래 한도 확인
        if self.daily_trade_count >= self.max_daily_trades:
            return False, f"일일 거래 한도 초과 ({self.max_daily_trades}회)"
        
        # 최소 거래 간격 확인
        if self.last_trade_time:
            elapsed = (datetime.now() - self.last_trade_time).total_seconds()
            if elapsed < self.min_trade_interval:
                return False, f"최소 거래 간격 미충족 ({self.min_trade_interval - elapsed:.0f}초 남음)"
        
        return True, ""
    
    def _has_position(self, symbol: str) -> bool:
        """해당 심볼에 포지션이 있는지 확인"""
        positions = self.order_manager.get_positions(symbol)
        return len(positions) > 0
    
    def update_positions(self):
        """모든 포지션 업데이트"""
        self.active_positions.clear()
        
        for symbol in self.symbols:
            positions = self.order_manager.get_positions(symbol)
            if positions:
                self.active_positions[symbol] = positions
        
        return self.active_positions
    
    def execute_entry(self, symbol: str, side: str, usdt_amount: float) -> Dict:
        """
        진입 주문 실행 (실제 거래)
        
        Args:
            symbol: 거래 심볼 (예: 'BTC-USDT-SWAP')
            side: 'buy' (롱) 또는 'sell' (숏)
            usdt_amount: 투입할 USDT 금액
            
        Returns:
            실행 결과 딕셔너리
        """
        print(f"\n{'='*60}")
        print(f"🚀 실제 진입 주문 실행")
        print(f"{'='*60}")
        print(f"📌 심볼: {symbol}")
        print(f"📊 방향: {'롱(매수)' if side == 'buy' else '숏(매도)'}")
        print(f"💰 금액: ${usdt_amount:.2f}")
        print(f"⚡ 레버리지: {self.leverage}x")
        
        # 거래 가능 여부 확인
        can_trade, reason = self._can_trade()
        if not can_trade:
            print(f"❌ 거래 불가: {reason}")
            return {
                'success': False,
                'error': reason,
                'is_real_trade': True
            }
        
        # 기존 포지션 확인
        if self._has_position(symbol):
            print(f"❌ 이미 {symbol} 포지션이 존재합니다")
            return {
                'success': False,
                'error': '이미 포지션 존재',
                'is_real_trade': True
            }
        
        # 주문 수량 계산
        order_size, calc_info = self.order_manager.calculate_order_size(symbol, usdt_amount)
        
        if order_size <= 0:
            print(f"❌ 주문 수량 계산 실패: {calc_info.get('error')}")
            return {
                'success': False,
                'error': calc_info.get('error', '수량 계산 실패'),
                'is_real_trade': True
            }
        
        print(f"📊 계산된 계약 수: {order_size}")
        print(f"💵 실제 주문 금액: ${calc_info.get('actual_notional', 0):.2f}")
        
        # 실제 주문 실행
        result = self.order_manager.place_market_order(
            inst_id=symbol,
            side=side,
            size=order_size,
            leverage=self.leverage
        )
        
        if result.get('success'):
            # 거래 기록 업데이트
            self.daily_trade_count += 1
            self.last_trade_time = datetime.now()
            
            # 수수료 기록
            detail = result.get('detail', {})
            fee = abs(detail.get('fee', 0))
            self.total_fees += fee
            
            # 거래 이력 저장
            trade_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'action': 'ENTRY',
                'side': side,
                'size': order_size,
                'price': detail.get('avg_price', 0),
                'usdt_amount': usdt_amount,
                'fee': fee,
                'order_id': result.get('order_id'),
                'is_real': True
            }
            self.trade_history.append(trade_record)
            
            print(f"\n✅ 진입 성공!")
            print(f"📌 주문 ID: {result.get('order_id')}")
            print(f"💵 체결가: ${detail.get('avg_price', 0):,.2f}")
            print(f"💸 수수료: ${fee:.6f}")
            
            result['trade_record'] = trade_record
        else:
            print(f"\n❌ 진입 실패: {result.get('error')}")
            print("⚠️ 시뮬레이션 모드로 대체하지 않습니다")
        
        result['is_real_trade'] = True
        return result
    
    def execute_exit(self, symbol: str, pos_side: str = 'long') -> Dict:
        """
        청산 주문 실행 (실제 거래)
        
        Args:
            symbol: 거래 심볼
            pos_side: 청산할 포지션 방향 ('long' 또는 'short')
            
        Returns:
            실행 결과 딕셔너리
        """
        print(f"\n{'='*60}")
        print(f"📤 실제 청산 주문 실행")
        print(f"{'='*60}")
        print(f"📌 심볼: {symbol}")
        print(f"📊 포지션 방향: {pos_side.upper()}")
        
        # 현재 포지션 확인
        positions = self.order_manager.get_positions(symbol)
        target_pos = None
        
        for pos in positions:
            if pos['pos_side'] == pos_side:
                target_pos = pos
                break
        
        if not target_pos:
            print(f"❌ 청산할 {pos_side} 포지션이 없습니다")
            return {
                'success': False,
                'error': '청산할 포지션 없음',
                'is_real_trade': True
            }
        
        print(f"📊 현재 포지션:")
        print(f"  수량: {target_pos['position']}")
        print(f"  평균가: ${target_pos['avg_price']:,.2f}")
        print(f"  미실현 손익: ${target_pos['upl']:.2f}")
        
        # 청산 실행
        result = self.order_manager.close_position(symbol, pos_side)
        
        if result.get('success'):
            # 실현 손익 기록
            realized_pnl = target_pos['upl']
            self.total_realized_pnl += realized_pnl
            
            # 거래 이력 저장
            trade_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'action': 'EXIT',
                'side': pos_side,
                'size': target_pos['position'],
                'entry_price': target_pos['avg_price'],
                'realized_pnl': realized_pnl,
                'is_real': True
            }
            self.trade_history.append(trade_record)
            
            print(f"\n✅ 청산 성공!")
            print(f"💰 실현 손익: ${realized_pnl:.2f}")
            print(f"📊 누적 손익: ${self.total_realized_pnl:.2f}")
            
            result['trade_record'] = trade_record
            result['realized_pnl'] = realized_pnl
        else:
            print(f"\n❌ 청산 실패: {result.get('error')}")
        
        result['is_real_trade'] = True
        return result
    
    def process_signal(self, symbol: str, signal: str, data: Dict[str, Any],
                       entry_amount: float = 10) -> Optional[Dict]:
        """
        전략 신호 처리
        
        Args:
            symbol: 거래 심볼
            signal: 신호 유형 ('LONG_ENTRY', 'SHORT_ENTRY', 'LONG_EXIT', 'SHORT_EXIT')
            data: 시장 데이터
            entry_amount: 진입 금액 (USDT)
            
        Returns:
            실행 결과 또는 None
        """
        print(f"\n📡 신호 수신: {signal} @ {symbol}")
        
        if signal == 'LONG_ENTRY':
            return self.execute_entry(symbol, 'buy', entry_amount)
        
        elif signal == 'SHORT_ENTRY':
            return self.execute_entry(symbol, 'sell', entry_amount)
        
        elif signal == 'LONG_EXIT':
            return self.execute_exit(symbol, 'long')
        
        elif signal == 'SHORT_EXIT':
            return self.execute_exit(symbol, 'short')
        
        else:
            print(f"⚠️ 알 수 없는 신호: {signal}")
            return None
    
    def get_status(self) -> Dict:
        """현재 상태 조회"""
        self.update_positions()
        
        # 잔고 조회
        balance = self.order_manager.get_account_balance('USDT')
        
        return {
            'is_running': self.is_running,
            'symbols': self.symbols,
            'leverage': self.leverage,
            'active_positions': len(self.active_positions),
            'positions': self.active_positions,
            'daily_trades': self.daily_trade_count,
            'max_daily_trades': self.max_daily_trades,
            'total_realized_pnl': self.total_realized_pnl,
            'total_fees': self.total_fees,
            'balance': balance,
            'trade_history_count': len(self.trade_history),
            'last_trade_time': self.last_trade_time,
            'simulation_mode': False  # 항상 False
        }
    
    def print_status(self):
        """상태 출력"""
        status = self.get_status()
        
        print(f"\n{'='*60}")
        print(f"📊 실제 거래 전략 관리자 상태")
        print(f"{'='*60}")
        print(f"🔄 실행 상태: {'실행 중' if status['is_running'] else '대기 중'}")
        print(f"📌 거래 심볼: {', '.join(status['symbols'])}")
        print(f"⚡ 레버리지: {status['leverage']}x")
        print(f"📈 활성 포지션: {status['active_positions']}개")
        print(f"📊 오늘 거래: {status['daily_trades']}/{status['max_daily_trades']}회")
        print(f"💰 누적 실현 손익: ${status['total_realized_pnl']:.2f}")
        print(f"💸 누적 수수료: ${status['total_fees']:.6f}")
        
        if status['balance']:
            print(f"💵 USDT 잔고: ${status['balance']['available']:.2f}")
        
        print(f"⚠️ 시뮬레이션 모드: 비활성화")
        print(f"{'='*60}")
    
    def get_trade_history(self, limit: int = 20) -> List[Dict]:
        """거래 이력 조회"""
        return self.trade_history[-limit:]
    
    def calculate_statistics(self) -> Dict:
        """거래 통계 계산"""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0
            }
        
        # 청산 거래만 필터링
        exits = [t for t in self.trade_history if t['action'] == 'EXIT']
        
        winning = [t for t in exits if t.get('realized_pnl', 0) > 0]
        losing = [t for t in exits if t.get('realized_pnl', 0) < 0]
        
        total_pnl = sum(t.get('realized_pnl', 0) for t in exits)
        
        return {
            'total_trades': len(self.trade_history),
            'entry_trades': len([t for t in self.trade_history if t['action'] == 'ENTRY']),
            'exit_trades': len(exits),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': len(winning) / len(exits) * 100 if exits else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(exits) if exits else 0,
            'total_fees': self.total_fees,
            'net_pnl': total_pnl - self.total_fees
        }


class RealTradeTester:
    """실제 거래 테스터 클래스"""
    
    def __init__(self, order_manager):
        self.order_manager = order_manager
    
    def check_minimum_requirements(self, symbol: str = 'BTC-USDT-SWAP') -> Dict:
        """최소 주문 요건 확인"""
        print(f"\n{'='*60}")
        print(f"📋 {symbol} 최소 주문 요건 확인")
        print(f"{'='*60}")
        
        # 상품 정보 조회
        inst_info = self.order_manager.get_instrument_info(symbol)
        current_price = self.order_manager.get_current_price(symbol)
        balance = self.order_manager.get_account_balance('USDT')
        
        if not inst_info or not current_price:
            return {'error': '정보 조회 실패'}
        
        # 최소 주문 금액 계산
        ct_val = inst_info['ct_val']
        min_size = inst_info['min_size']
        min_notional = min_size * ct_val * current_price
        
        result = {
            'symbol': symbol,
            'current_price': current_price,
            'contract_value': ct_val,
            'min_contracts': min_size,
            'lot_size': inst_info['lot_size'],
            'min_notional_usdt': min_notional,
            'recommended_amount': max(10, min_notional * 1.5),
            'available_balance': balance['available'] if balance else 0,
            'can_trade': balance['available'] >= min_notional if balance else False
        }
        
        print(f"💵 현재가: ${current_price:,.2f}")
        print(f"📊 계약 가치: {ct_val} {symbol.split('-')[0]}")
        print(f"📊 최소 계약 수: {min_size}")
        print(f"📊 수량 단위: {inst_info['lot_size']}")
        print(f"💰 최소 주문금액: ${min_notional:.2f} USDT")
        print(f"✅ 권장 테스트금액: ${result['recommended_amount']:.2f} USDT")
        
        if balance:
            print(f"\n💳 사용 가능 잔고: ${balance['available']:.2f} USDT")
            if result['can_trade']:
                print(f"✅ 거래 가능")
            else:
                print(f"❌ 잔고 부족 (최소 ${min_notional:.2f} 필요)")
        
        print(f"{'='*60}")
        
        return result
    
    def run_buy_test(self, symbol: str = 'BTC-USDT-SWAP', 
                     usdt_amount: float = 10, leverage: int = 1) -> Dict:
        """
        실제 구매 테스트 실행
        
        Returns:
            테스트 결과 (성공 시 포지션 정보 포함)
        """
        print(f"\n{'🔥'*20}")
        print(f"🛒 실제 구매 테스트 시작")
        print(f"{'🔥'*20}")
        
        # 1. 최소 요건 확인
        requirements = self.check_minimum_requirements(symbol)
        
        if requirements.get('error'):
            return {'success': False, 'error': requirements['error']}
        
        if not requirements['can_trade']:
            return {
                'success': False, 
                'error': f"잔고 부족: ${requirements['available_balance']:.2f} < ${requirements['min_notional_usdt']:.2f}"
            }
        
        # 2. 주문 금액 검증
        if usdt_amount < requirements['min_notional_usdt']:
            print(f"⚠️ 요청 금액(${usdt_amount})이 최소 금액(${requirements['min_notional_usdt']:.2f})보다 작습니다")
            usdt_amount = requirements['recommended_amount']
            print(f"📊 권장 금액으로 조정: ${usdt_amount:.2f}")
        
        # 3. 구매 실행
        result = self.order_manager.test_buy_order(
            inst_id=symbol,
            usdt_amount=usdt_amount,
            leverage=leverage
        )
        
        return result
    
    def run_close_test(self, symbol: str = 'BTC-USDT-SWAP', 
                       pos_side: str = 'long') -> Dict:
        """포지션 청산 테스트"""
        return self.order_manager.test_close_position(symbol, pos_side)


# 실행 예제
if __name__ == "__main__":
    print("=" * 60)
    print("실제 거래 전용 시스템 테스트")
    print("=" * 60)
    
    # 설정 로드
    try:
        from config import API_KEY, API_SECRET, PASSPHRASE
        from okx.real_order_manager import RealOrderManager
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
        print("필요한 파일:")
        print("  - config.py (API_KEY, API_SECRET, PASSPHRASE)")
        print("  - okx/real_order_manager.py")
        exit(1)
    
    # 주문 관리자 초기화
    order_manager = RealOrderManager(API_KEY, API_SECRET, PASSPHRASE)
    
    # 테스터 초기화
    tester = RealTradeTester(order_manager)
    
    # 최소 요건 확인
    print("\n" + "="*60)
    print("📋 BTC 최소 주문 요건")
    print("="*60)
    btc_req = tester.check_minimum_requirements('BTC-USDT-SWAP')
    
    print("\n" + "="*60)
    print("📋 ETH 최소 주문 요건")
    print("="*60)
    eth_req = tester.check_minimum_requirements('ETH-USDT-SWAP')
    
    # 테스트 실행 여부 안내
    print("\n" + "="*60)
    print("⚠️ 실제 거래 테스트")
    print("="*60)
    print("이 테스트는 실제 자금을 사용합니다.")
    print("테스트를 진행하려면 아래 코드의 주석을 해제하세요.")
    print("""
# 실제 구매 테스트 (주석 해제 시 실행)
# result = tester.run_buy_test('BTC-USDT-SWAP', 10, 1)
# print(result)

# 청산 테스트 (주석 해제 시 실행)
# close_result = tester.run_close_test('BTC-USDT-SWAP', 'long')
# print(close_result)
    """)
