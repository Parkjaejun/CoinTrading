"""
알고리즘 1번 - 롱 전략
30분봉, 150EMA/200EMA 골든크로스(상승장), 20EMA/50EMA 골든크로스에서 매수
20EMA/100EMA 데드크로스에서 청산, 레버리지 10배, 트레일링스탑 10%
"""

from datetime import datetime
from typing import Optional, Dict, Any
from config import ALGORITHM_CONFIG

class LongStrategy:
    def __init__(self, symbol: str, initial_capital: float = 1000.0):
        self.strategy_name = "long_strategy"
        self.symbol = symbol
        
        # 전략 파라미터 (config.py에서 로드)
        config = ALGORITHM_CONFIG['long_strategy']
        self.ema_periods = config['ema_periods']
        self.leverage = config['leverage']
        self.trailing_stop_ratio = config['trailing_stop']
        self.stop_loss_ratio = config['stop_loss']
        self.reentry_gain_ratio = config['reentry_gain']
        
        # 자본 관리 (듀얼 자산 시스템)
        self.real_capital = initial_capital      # 실제 거래 자본 (A)
        self.virtual_capital = initial_capital   # 가상 거래 자본 (B) 
        self.is_real_mode = True                 # True: 실제 거래, False: 가상 거래
        
        # 자본 추적
        self.real_peak = initial_capital         # 실제 자본 최고점
        self.virtual_trough = initial_capital    # 가상 자본 최저점
        
        # 포지션 상태
        self.position_size = 0.0
        self.entry_price = 0.0
        self.entry_time = None
        self.peak_price = 0.0
        self.is_position_open = False
        
        # 전략 상태
        self.is_active = True                    # 전략 활성화 여부
        self.last_signal_time = None
        self.trade_count = 0
        self.win_count = 0
        self.total_pnl = 0.0
        
        print(f"롱 전략 초기화: {symbol}")
        print(f"  레버리지: {self.leverage}배")
        print(f"  트레일링 스탑: {self.trailing_stop_ratio*100}%")
        print(f"  초기 자본: {initial_capital} USDT")
    
    def check_trend_condition(self, data: Dict[str, Any]) -> bool:
        """트렌드 조건 확인: 150EMA > 200EMA (상승장)"""
        ema150 = data.get('ema_trend_fast')  # 150EMA
        ema200 = data.get('ema_trend_slow')  # 200EMA
        
        if ema150 is None or ema200 is None:
            return False
            
        is_uptrend = ema150 > ema200
        
        if is_uptrend:
            print(f"[{self.symbol}] 상승장 확인: 150EMA({ema150:.2f}) > 200EMA({ema200:.2f})")
        
        return is_uptrend
    
    def check_entry_condition(self, data: Dict[str, Any]) -> bool:
        """진입 조건: 20EMA가 50EMA를 상향 돌파 (골든크로스)"""
        # 현재 EMA 값들
        ema20_now = data.get('curr_entry_fast')  # 현재 20EMA
        ema50_now = data.get('curr_entry_slow')  # 현재 50EMA
        
        # 이전 EMA 값들  
        ema20_prev = data.get('prev_entry_fast')  # 이전 20EMA
        ema50_prev = data.get('prev_entry_slow')  # 이전 50EMA
        
        if None in [ema20_now, ema50_now, ema20_prev, ema50_prev]:
            return False
        
        # 골든크로스 조건: 이전에는 20EMA <= 50EMA, 현재는 20EMA > 50EMA
        golden_cross = (ema20_prev <= ema50_prev) and (ema20_now > ema50_now)
        
        if golden_cross:
            print(f"[{self.symbol}] 롱 진입 신호 감지!")
            print(f"  20EMA: {ema20_prev:.2f} → {ema20_now:.2f}")
            print(f"  50EMA: {ema50_prev:.2f} → {ema50_now:.2f}")
        
        return golden_cross
    
    def check_exit_condition(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """청산 조건 확인"""
        if not self.is_position_open:
            return False, ""
        
        # 조건 1: 20EMA가 100EMA를 하향 돌파 (데드크로스)
        ema20_now = data.get('curr_exit_fast')   # 현재 20EMA
        ema100_now = data.get('curr_exit_slow')  # 현재 100EMA
        ema20_prev = data.get('prev_exit_fast')  # 이전 20EMA
        ema100_prev = data.get('prev_exit_slow') # 이전 100EMA
        
        if None not in [ema20_now, ema100_now, ema20_prev, ema100_prev]:
            # 데드크로스: 이전에는 20EMA >= 100EMA, 현재는 20EMA < 100EMA
            dead_cross = (ema20_prev >= ema100_prev) and (ema20_now < ema100_now)
            
            if dead_cross:
                print(f"[{self.symbol}] EMA 데드크로스 청산 신호!")
                print(f"  20EMA: {ema20_prev:.2f} → {ema20_now:.2f}")
                print(f"  100EMA: {ema100_prev:.2f} → {ema100_now:.2f}")
                return True, "ema_dead_cross"
        
        # 조건 2: 트레일링 스탑 확인
        current_price = data.get('close')
        if current_price and self.peak_price > 0:
            # 피크 가격 업데이트
            if current_price > self.peak_price:
                self.peak_price = current_price
                print(f"[{self.symbol}] 피크 가격 업데이트: {self.peak_price:.2f}")
            
            # 트레일링 스탑 조건
            trailing_stop_price = self.peak_price * (1 - self.trailing_stop_ratio)
            
            if current_price <= trailing_stop_price:
                drawdown_pct = ((self.peak_price - current_price) / self.peak_price) * 100
                print(f"[{self.symbol}] 트레일링 스탑 발동!")
                print(f"  피크: {self.peak_price:.2f}, 현재: {current_price:.2f}")
                print(f"  하락폭: {drawdown_pct:.2f}%")
                return True, "trailing_stop"
        
        return False, ""
    
    def should_enter_position(self, data: Dict[str, Any]) -> bool:
        """포지션 진입 가능 여부 확인"""
        if not self.is_active:
            return False
            
        if self.is_position_open:
            return False
        
        # 충분한 자본이 있는지 확인
        current_capital = self.real_capital if self.is_real_mode else self.virtual_capital
        if current_capital <= 10:  # 최소 자본 $10
            print(f"[{self.symbol}] 자본 부족: {current_capital:.2f} USDT")
            return False
        
        # 1. 트렌드 조건 확인
        if not self.check_trend_condition(data):
            return False
        
        # 2. 진입 조건 확인  
        if not self.check_entry_condition(data):
            return False
        
        return True
    
    def should_exit_position(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """포지션 청산 가능 여부 확인"""
        if not self.is_position_open:
            return False, ""
            
        return self.check_exit_condition(data)
    
    def enter_position(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """포지션 진입 실행"""
        if not self.should_enter_position(data):
            return None
        
        current_price = data.get('close')
        if not current_price:
            return None
        
        # 사용할 자본 결정
        current_capital = self.real_capital if self.is_real_mode else self.virtual_capital
        
        # 포지션 크기 계산 (레버리지 적용)
        # 자본의 95%를 사용하여 5% 여유분 확보
        effective_capital = current_capital * 0.95
        notional_value = effective_capital * self.leverage
        position_size = notional_value / current_price
        
        # 포지션 정보 저장
        self.position_size = position_size
        self.entry_price = current_price
        self.entry_time = data.get('timestamp') or datetime.now()
        self.peak_price = current_price
        self.is_position_open = True
        self.last_signal_time = datetime.now()
        
        mode_str = "실제" if self.is_real_mode else "가상"
        
        print(f"[{self.symbol}] 롱 포지션 진입 ({mode_str})")
        print(f"  진입가: {current_price:.2f} USDT")
        print(f"  포지션 크기: {position_size:.6f} BTC")
        print(f"  명목 거래금액: ${notional_value:.2f}")
        print(f"  레버리지: {self.leverage}배")
        print(f"  사용 자본: ${effective_capital:.2f}")
        
        return {
            'action': 'enter_long',
            'symbol': self.symbol,
            'side': 'long',
            'size': position_size,
            'price': current_price,
            'leverage': self.leverage,
            'is_real_mode': self.is_real_mode,
            'capital_used': effective_capital,
            'trailing_stop_ratio': self.trailing_stop_ratio,
            'strategy_name': self.strategy_name
        }
    
    def exit_position(self, data: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """포지션 청산 실행"""
        if not self.is_position_open:
            return None
        
        current_price = data.get('close')
        if not current_price:
            return None
        
        # PnL 계산
        price_change = current_price - self.entry_price
        pnl = price_change * self.position_size
        pnl_percentage = (price_change / self.entry_price) * 100 * self.leverage
        
        # 수수료 계산 (진입 + 청산)
        notional_value = self.position_size * current_price
        fee = notional_value * 0.0005 * 2  # 0.05% * 2 (진입 + 청산)
        net_pnl = pnl - fee
        
        # 자본 업데이트
        if self.is_real_mode:
            self.real_capital += net_pnl
            # 피크 업데이트
            if self.real_capital > self.real_peak:
                self.real_peak = self.real_capital
        else:
            self.virtual_capital += net_pnl
            # 트러프 업데이트  
            if self.virtual_capital < self.virtual_trough:
                self.virtual_trough = self.virtual_capital
        
        # 거래 통계 업데이트
        self.trade_count += 1
        self.total_pnl += net_pnl
        if net_pnl > 0:
            self.win_count += 1
        
        mode_str = "실제" if self.is_real_mode else "가상"
        
        print(f"[{self.symbol}] 롱 포지션 청산 ({mode_str})")
        print(f"  진입가: {self.entry_price:.2f} USDT")
        print(f"  청산가: {current_price:.2f} USDT") 
        print(f"  가격 변동: {price_change:+.2f} USDT ({pnl_percentage:+.2f}%)")
        print(f"  실현 PnL: {net_pnl:+.2f} USDT (수수료: {fee:.2f})")
        print(f"  청산 사유: {reason}")
        print(f"  현재 자본: {self.real_capital:.2f} USDT" if self.is_real_mode else f"  현재 자본: {self.virtual_capital:.2f} USDT")
        
        # 포지션 정리
        position_info = {
            'action': 'exit_long',
            'symbol': self.symbol,
            'side': 'long', 
            'size': self.position_size,
            'entry_price': self.entry_price,
            'exit_price': current_price,
            'pnl': net_pnl,
            'pnl_percentage': pnl_percentage,
            'fee': fee,
            'reason': reason,
            'is_real_mode': self.is_real_mode,
            'strategy_name': self.strategy_name,
            'duration_seconds': (datetime.now() - self.entry_time).total_seconds() if self.entry_time else 0
        }
        
        # 포지션 상태 리셋
        self.position_size = 0.0
        self.entry_price = 0.0
        self.entry_time = None
        self.peak_price = 0.0
        self.is_position_open = False
        
        return position_info
    
    def check_mode_switch(self) -> bool:
        """실제/가상 모드 전환 확인"""
        mode_changed = False
        
        # 실제 → 가상 전환 조건: 실제 자본이 피크 대비 20% 하락
        if self.is_real_mode:
            if self.real_capital <= self.real_peak * (1 - self.stop_loss_ratio):
                print(f"[{self.symbol}] 실제 → 가상 모드 전환")
                print(f"  피크 자본: {self.real_peak:.2f}")
                print(f"  현재 자본: {self.real_capital:.2f}")
                print(f"  하락률: {((self.real_peak - self.real_capital) / self.real_peak * 100):.1f}%")
                
                self.is_real_mode = False
                self.virtual_capital = self.real_capital  # 가상 자본을 현재 실제 자본으로 초기화
                self.virtual_trough = self.virtual_capital
                self.is_active = True  # 가상 모드에서 계속 거래
                mode_changed = True
        
        # 가상 → 실제 전환 조건: 가상 자본이 트러프 대비 30% 상승
        else:
            if self.virtual_capital >= self.virtual_trough * (1 + self.reentry_gain_ratio):
                print(f"[{self.symbol}] 가상 → 실제 모드 전환")
                print(f"  트러프 자본: {self.virtual_trough:.2f}")
                print(f"  현재 자본: {self.virtual_capital:.2f}")
                print(f"  상승률: {((self.virtual_capital - self.virtual_trough) / self.virtual_trough * 100):.1f}%")
                
                self.is_real_mode = True
                self.real_capital = self.virtual_capital  # 실제 자본을 현재 가상 자본으로 업데이트
                self.real_peak = self.real_capital
                mode_changed = True
        
        return mode_changed
    
    def process_signal(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """시그널 처리 메인 함수"""
        try:
            # 모드 전환 확인
            mode_switched = self.check_mode_switch()
            
            # 청산 조건 먼저 확인
            should_exit, exit_reason = self.should_exit_position(data)
            if should_exit:
                return self.exit_position(data, exit_reason)
            
            # 진입 조건 확인
            if self.should_enter_position(data):
                return self.enter_position(data)
            
            return None
            
        except Exception as e:
            print(f"[{self.symbol}] 롱 전략 시그널 처리 오류: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """전략 현재 상태 반환"""
        current_capital = self.real_capital if self.is_real_mode else self.virtual_capital
        win_rate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'is_active': self.is_active,
            'is_real_mode': self.is_real_mode,
            'is_position_open': self.is_position_open,
            'current_capital': current_capital,
            'real_capital': self.real_capital,
            'virtual_capital': self.virtual_capital,
            'real_peak': self.real_peak,
            'virtual_trough': self.virtual_trough,
            'position_size': self.position_size,
            'entry_price': self.entry_price,
            'peak_price': self.peak_price,
            'trade_count': self.trade_count,
            'win_count': self.win_count,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'leverage': self.leverage,
            'trailing_stop_ratio': self.trailing_stop_ratio
        }
    
    def print_status(self):
        """전략 상태 출력"""
        status = self.get_status()
        mode_str = "실제 거래" if status['is_real_mode'] else "가상 거래"
        position_str = f"LONG {status['position_size']:.6f}" if status['is_position_open'] else "대기 중"
        
        print(f"\n=== 롱 전략 상태 ({status['symbol']}) ===")
        print(f"모드: {mode_str}")
        print(f"포지션: {position_str}")
        print(f"현재 자본: {status['current_capital']:.2f} USDT")
        print(f"거래 횟수: {status['trade_count']}회")
        print(f"승률: {status['win_rate']:.1f}%")
        print(f"총 PnL: {status['total_pnl']:+.2f} USDT")
        
        if status['is_position_open']:
            print(f"진입가: {status['entry_price']:.2f}")
            print(f"피크가: {status['peak_price']:.2f}")
