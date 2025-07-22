"""
숏 전략 (단순화 버전)
알고리즘 2: 30분봉, 150/200 EMA 데드크로스 하락장에서
20/50 EMA 데드크로스로 숏 진입, 100/200 EMA 골든크로스로 청산
"""

from datetime import datetime
from typing import Optional, Dict, Any
from config import SHORT_STRATEGY_CONFIG

class ShortStrategy:
    def __init__(self, symbol: str, initial_capital: float):
        self.strategy_name = "short_strategy"
        self.symbol = symbol
        
        # 설정값 로드
        self.config = SHORT_STRATEGY_CONFIG
        self.leverage = self.config['leverage']
        self.trailing_stop_ratio = self.config['trailing_stop']
        self.stop_loss_ratio = self.config['stop_loss']
        self.reentry_gain_ratio = self.config['reentry_gain']
        
        # 듀얼 자산 시스템
        self.real_capital = initial_capital
        self.virtual_capital = initial_capital
        self.is_real_mode = True
        self.real_peak = initial_capital
        self.virtual_trough = initial_capital
        
        # 포지션 상태
        self.is_position_open = False
        self.entry_price = 0.0
        self.trough_price = 0.0  # 숏용 최저가
        
        # 거래 통계
        self.trade_count = 0
        self.win_count = 0
        self.total_pnl = 0.0
        
        print(f"✅ 숏 전략 초기화: {symbol} (자본: ${initial_capital:,.0f})")
    
    def check_trend_condition(self, data: Dict[str, Any]) -> bool:
        """하락장 확인: 150EMA < 200EMA"""
        ema150 = data.get('ema_trend_fast')
        ema200 = data.get('ema_trend_slow')
        
        if ema150 is None or ema200 is None:
            return False
        
        return ema150 < ema200
    
    def check_entry_condition(self, data: Dict[str, Any]) -> bool:
        """진입 조건: 20EMA가 50EMA 하향 돌파"""
        curr_20 = data.get('curr_entry_fast')
        curr_50 = data.get('curr_entry_slow')
        prev_20 = data.get('prev_entry_fast')
        prev_50 = data.get('prev_entry_slow')
        
        if None in [curr_20, curr_50, prev_20, prev_50]:
            return False
        
        # 데드크로스: 이전 >= 현재 <
        return prev_20 >= prev_50 and curr_20 < curr_50
    
    def check_exit_condition(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """청산 조건 확인"""
        if not self.is_position_open:
            return False, ""
        
        # EMA 골든크로스: 100EMA > 200EMA
        curr_100 = data.get('curr_exit_fast')
        curr_200 = data.get('curr_exit_slow')
        prev_100 = data.get('prev_exit_fast')
        prev_200 = data.get('prev_exit_slow')
        
        if None not in [curr_100, curr_200, prev_100, prev_200]:
            if prev_100 <= prev_200 and curr_100 > curr_200:
                return True, "ema_golden_cross"
        
        # 트레일링 스탑 (숏용)
        current_price = data.get('close')
        if current_price and self.trough_price > 0:
            if current_price < self.trough_price:
                self.trough_price = current_price
            
            trailing_stop_price = self.trough_price * (1 + self.trailing_stop_ratio)
            if current_price >= trailing_stop_price:
                return True, "trailing_stop"
        
        return False, ""
    
    def should_enter(self, data: Dict[str, Any]) -> bool:
        """진입 가능한가?"""
        if self.is_position_open:
            return False
        
        current_capital = self.real_capital if self.is_real_mode else self.virtual_capital
        if current_capital <= 10:
            return False
        
        return self.check_trend_condition(data) and self.check_entry_condition(data)
    
    def should_exit(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """청산해야 하는가?"""
        return self.check_exit_condition(data)
    
    def enter_position(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """포지션 진입"""
        if not self.should_enter(data):
            return None
        
        current_price = data.get('close')
        if not current_price:
            return None
        
        current_capital = self.real_capital if self.is_real_mode else self.virtual_capital
        effective_capital = current_capital * 0.95
        notional_value = effective_capital * self.leverage
        position_size = notional_value / current_price
        
        # 포지션 상태 업데이트
        self.is_position_open = True
        self.entry_price = current_price
        self.trough_price = current_price
        
        mode_str = "실제" if self.is_real_mode else "가상"
        print(f"📉 [{self.symbol}] 숏 진입 ({mode_str}): ${current_price:.2f}, 크기: {position_size:.6f}")
        
        return {
            'action': 'enter_short',
            'symbol': self.symbol,
            'side': 'short',
            'size': position_size,
            'price': current_price,
            'leverage': self.leverage,
            'is_real_mode': self.is_real_mode,
            'strategy_name': self.strategy_name,
            'trailing_stop_ratio': self.trailing_stop_ratio
        }
    
    def exit_position(self, data: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
        """포지션 청산"""
        if not self.is_position_open:
            return None
        
        current_price = data.get('close')
        if not current_price:
            return None
        
        # PnL 계산 (숏: 진입가 - 현재가)
        price_change = self.entry_price - current_price
        notional_size = (self.real_capital if self.is_real_mode else self.virtual_capital) * 0.95 * self.leverage
        position_size = notional_size / self.entry_price
        pnl = price_change * position_size
        fee = notional_size * 0.0005 * 2  # 진입 + 청산 수수료
        net_pnl = pnl - fee
        
        # 자본 업데이트
        if self.is_real_mode:
            self.real_capital += net_pnl
            if self.real_capital > self.real_peak:
                self.real_peak = self.real_capital
        else:
            self.virtual_capital += net_pnl
            if self.virtual_capital < self.virtual_trough:
                self.virtual_trough = self.virtual_capital
        
        # 통계 업데이트
        self.trade_count += 1
        self.total_pnl += net_pnl
        if net_pnl > 0:
            self.win_count += 1
        
        # 포지션 상태 초기화
        self.is_position_open = False
        self.entry_price = 0.0
        self.trough_price = 0.0
        
        mode_str = "실제" if self.is_real_mode else "가상"
        pnl_pct = (price_change / self.entry_price) * 100 * self.leverage
        print(f"📈 [{self.symbol}] 숏 청산 ({mode_str}): ${current_price:.2f}, PnL: {net_pnl:+.2f} ({pnl_pct:+.2f}%), 사유: {reason}")
        
        return {
            'action': 'exit_short',
            'symbol': self.symbol,
            'side': 'short',
            'exit_price': current_price,
            'pnl': net_pnl,
            'pnl_percentage': pnl_pct,
            'reason': reason,
            'is_real_mode': self.is_real_mode,
            'strategy_name': self.strategy_name
        }
    
    def check_mode_switch(self) -> bool:
        """실제/가상 모드 전환 체크"""
        mode_changed = False
        
        # 실제 → 가상: 피크 대비 10% 하락 (숏은 더 보수적)
        if self.is_real_mode:
            if self.real_capital <= self.real_peak * (1 - self.stop_loss_ratio):
                self.is_real_mode = False
                self.virtual_capital = self.real_capital
                self.virtual_trough = self.virtual_capital
                mode_changed = True
                print(f"🔄 [{self.symbol}] 숏 전략: 실제 → 가상 모드 전환")
        
        # 가상 → 실제: 트러프 대비 20% 상승
        else:
            if self.virtual_capital >= self.virtual_trough * (1 + self.reentry_gain_ratio):
                self.is_real_mode = True
                self.real_capital = self.virtual_capital
                self.real_peak = self.real_capital
                mode_changed = True
                print(f"🔄 [{self.symbol}] 숏 전략: 가상 → 실제 모드 전환")
        
        return mode_changed
    
    def process_signal(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """신호 처리 메인 함수"""
        try:
            # 모드 전환 체크
            self.check_mode_switch()
            
            # 청산 우선 확인
            should_exit, exit_reason = self.should_exit(data)
            if should_exit:
                return self.exit_position(data, exit_reason)
            
            # 진입 확인
            if self.should_enter(data):
                return self.enter_position(data)
            
            return None
            
        except Exception as e:
            print(f"❌ 숏 전략 오류 ({self.symbol}): {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """전략 상태"""
        current_capital = self.real_capital if self.is_real_mode else self.virtual_capital
        win_rate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'is_real_mode': self.is_real_mode,
            'is_position_open': self.is_position_open,
            'current_capital': current_capital,
            'real_capital': self.real_capital,
            'virtual_capital': self.virtual_capital,
            'trade_count': self.trade_count,
            'win_count': self.win_count,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'leverage': self.leverage
        }