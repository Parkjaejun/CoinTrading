# terminal_dashboard.py
"""
깔끔한 터미널 대시보드
- cls로 화면 갱신
- 실시간 상태 표시
- 중요 이벤트만 기록
"""

import os
import sys
import time
from datetime import datetime, timedelta
from collections import deque

# 전역 대시보드 인스턴스
_dashboard = None


class TerminalDashboard:
    """터미널 대시보드"""
    
    def __init__(self):
        self.start_time = datetime.now()
        
        # 상태 데이터
        self.status = {
            'running': False,
            'balance': 0,
            'btc_price': 0,
            'cycle': 0,
            'total_signals': 0,
            'total_trades': 0,
            'total_pnl': 0,
        }
        
        # 전략 상태
        self.strategies = {}
        
        # 포지션
        self.positions = []
        
        # 최근 이벤트 (최대 10개)
        self.events = deque(maxlen=10)
        
        # 마지막 업데이트
        self.last_update = datetime.now()
        
        # 로그 숨김 활성화
        self._suppress_logs()
    
    def _suppress_logs(self):
        """불필요한 로그 숨김"""
        import builtins
        self._original_print = builtins.print
        builtins.print = self._filtered_print
    
    def _filtered_print(self, *args, **kwargs):
        """필터링된 print"""
        if not args:
            return
        
        msg = str(args[0])
        
        # 숨길 패턴
        hide_patterns = [
            "🔍 전달할", "🔍 생성된", "🔍 서명용", "🔍 API 요청",
            "URL:", "Method:", "Headers:", "Timestamp:", "Request Path",
            "Query String:", "🔍 실제 요청", "포지션 조회", "포지션 정보",
            "✅ 포지션", "✅ 운영", "📊 운영", "💰 잔액", "✅ 잔액",
            "📈 가격", "✅ 가격", "📊 활성", "instType=SWAP",
            "순차 초기화", "잔액 조회", "가격 조회", "포지션 업데이트",
        ]
        
        for pattern in hide_patterns:
            if pattern in msg:
                return
        
        # 중요 이벤트는 대시보드에 추가
        important_patterns = [
            ("신호", "📡"),
            ("거래", "💰"),
            ("주문", "📝"),
            ("청산", "🔴"),
            ("진입", "🟢"),
            ("오류", "❌"),
            ("시작", "🚀"),
            ("중지", "🛑"),
        ]
        
        for pattern, icon in important_patterns:
            if pattern in msg:
                self.add_event(f"{icon} {msg[:60]}")
                return
        
        # 나머지는 원본 print
        # self._original_print(*args, **kwargs)
    
    def add_event(self, message: str):
        """이벤트 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.events.append(f"[{timestamp}] {message}")
    
    def update(self, **kwargs):
        """상태 업데이트"""
        for key, value in kwargs.items():
            if key in self.status:
                self.status[key] = value
        self.last_update = datetime.now()
    
    def update_strategies(self, strategies: dict):
        """전략 상태 업데이트"""
        self.strategies = strategies
    
    def update_positions(self, positions: list):
        """포지션 업데이트"""
        self.positions = positions
    
    def clear_screen(self):
        """화면 클리어"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def render(self):
        """대시보드 렌더링"""
        self.clear_screen()
        
        now = datetime.now()
        uptime = now - self.start_time
        uptime_str = str(uptime).split('.')[0]
        
        # 헤더
        print("╔" + "═" * 70 + "╗")
        print("║" + "  OKX 자동매매 시스템".center(70) + "║")
        print("╠" + "═" * 70 + "╣")
        
        # 상태 표시
        status_icon = "🟢 실행중" if self.status['running'] else "⚪ 대기중"
        print(f"║  상태: {status_icon:<20} 실행시간: {uptime_str:<20}     ║")
        print("╠" + "═" * 70 + "╣")
        
        # 자산 정보
        balance = self.status.get('balance', 0)
        btc_price = self.status.get('btc_price', 0)
        total_pnl = self.status.get('total_pnl', 0)
        pnl_color = "+" if total_pnl >= 0 else ""
        
        print(f"║  💰 USDT 잔고: ${balance:>12,.2f}                                 ║")
        print(f"║  ₿  BTC 가격:  ${btc_price:>12,.2f}                                 ║")
        print(f"║  📊 총 손익:   ${pnl_color}{total_pnl:>12,.2f}                                 ║")
        print("╠" + "═" * 70 + "╣")
        
        # 전략 상태
        print("║  [전략 상태]                                                        ║")
        print("║  ┌────────┬──────┬──────┬───────────┬───────────┬────────┐         ║")
        print("║  │ 전략   │ 모드 │ 상태 │ 자본      │ 손익      │ 승률   │         ║")
        print("║  ├────────┼──────┼──────┼───────────┼───────────┼────────┤         ║")
        
        if self.strategies:
            for key, strat in self.strategies.items():
                name = "LONG " if "long" in key else "SHORT"
                mode = "실제" if strat.get('is_real_mode', True) else "가상"
                status = "보유" if strat.get('is_position_open', False) else "대기"
                capital = strat.get('real_capital', 0)
                pnl = strat.get('total_pnl', 0)
                win_rate = strat.get('win_rate', 0)
                
                pnl_str = f"${pnl:+.2f}"
                print(f"║  │ {name:<6} │ {mode:<4} │ {status:<4} │ ${capital:>8.2f} │ {pnl_str:>9} │ {win_rate:>5.1f}% │         ║")
        else:
            print("║  │        │      │      │           │           │        │         ║")
            print("║  │        │      │      │           │           │        │         ║")
        
        print("║  └────────┴──────┴──────┴───────────┴───────────┴────────┘         ║")
        print("╠" + "═" * 70 + "╣")
        
        # 현재 포지션
        print("║  [현재 포지션]                                                      ║")
        if self.positions:
            for pos in self.positions[:3]:  # 최대 3개
                symbol = pos.get('inst_id', pos.get('instId', ''))[:12]
                side = pos.get('pos_side', pos.get('posSide', 'net'))
                size = float(pos.get('position', pos.get('pos', 0)))
                upl = float(pos.get('upl', 0))
                upl_str = f"${upl:+.2f}"
                print(f"║    {symbol:<12} {side:<6} 수량:{size:<8.4f} 손익:{upl_str:<12}      ║")
        else:
            print("║    포지션 없음                                                      ║")
        print("╠" + "═" * 70 + "╣")
        
        # 통계
        signals = self.status.get('total_signals', 0)
        trades = self.status.get('total_trades', 0)
        cycle = self.status.get('cycle', 0)
        
        print(f"║  📡 신호: {signals:<5}  💰 거래: {trades:<5}  🔄 사이클: {cycle:<10}          ║")
        print("╠" + "═" * 70 + "╣")
        
        # 최근 이벤트
        print("║  [최근 이벤트]                                                      ║")
        if self.events:
            for event in list(self.events)[-5:]:  # 최근 5개
                event_str = event[:66]
                print(f"║    {event_str:<66} ║")
        else:
            print("║    대기 중...                                                      ║")
        
        # 빈 줄 채우기
        event_count = len(list(self.events)[-5:]) if self.events else 1
        for _ in range(5 - event_count):
            print("║" + " " * 70 + "║")
        
        print("╠" + "═" * 70 + "╣")
        
        # 마지막 업데이트
        update_str = self.last_update.strftime("%H:%M:%S")
        print(f"║  마지막 업데이트: {update_str}                    [Ctrl+C 종료]        ║")
        print("╚" + "═" * 70 + "╝")


def get_dashboard() -> TerminalDashboard:
    """전역 대시보드 가져오기"""
    global _dashboard
    if _dashboard is None:
        _dashboard = TerminalDashboard()
    return _dashboard


def init_dashboard():
    """대시보드 초기화"""
    global _dashboard
    _dashboard = TerminalDashboard()
    return _dashboard


# ============================================================
# trading_engine.py 통합용 래퍼
# ============================================================

class DashboardIntegration:
    """자동매매 엔진과 대시보드 통합"""
    
    def __init__(self, engine):
        self.engine = engine
        self.dashboard = init_dashboard()
        self.running = False
    
    def start(self):
        """통합 시작"""
        import threading
        
        self.running = True
        self.dashboard.status['running'] = True
        self.dashboard.add_event("🚀 자동매매 시스템 시작")
        
        # 대시보드 업데이트 스레드
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        # 엔진 시작
        return self.engine.start()
    
    def stop(self):
        """통합 중지"""
        self.running = False
        self.dashboard.status['running'] = False
        self.dashboard.add_event("🛑 자동매매 시스템 중지")
        self.engine.stop()
    
    def _update_loop(self):
        """대시보드 업데이트 루프"""
        while self.running:
            try:
                # 엔진 상태 가져오기
                status = self.engine.get_status()
                
                self.dashboard.update(
                    running=self.engine.is_running,
                    total_signals=status.get('total_signals', 0),
                    total_trades=status.get('executed_trades', 0),
                )
                
                # 전략 상태
                if 'strategies' in status:
                    self.dashboard.update_strategies(status['strategies'])
                    
                    # 총 손익 계산
                    total_pnl = sum(
                        s.get('total_pnl', 0) 
                        for s in status['strategies'].values()
                    )
                    self.dashboard.update(total_pnl=total_pnl)
                
                # 잔고 및 가격
                if self.engine.order_manager:
                    try:
                        balance = self.engine.order_manager.get_account_balance('USDT')
                        if balance:
                            self.dashboard.update(balance=float(balance.get('available', 0)))
                        
                        price = self.engine.order_manager.get_current_price('BTC-USDT-SWAP')
                        if price:
                            self.dashboard.update(btc_price=price)
                        
                        positions = self.engine.order_manager.get_positions()
                        if positions:
                            self.dashboard.update_positions(positions)
                        else:
                            self.dashboard.update_positions([])
                    except:
                        pass
                
                # 사이클 카운트
                cycle = self.dashboard.status.get('cycle', 0) + 1
                self.dashboard.update(cycle=cycle)
                
                # 화면 렌더링
                self.dashboard.render()
                
                time.sleep(3)  # 3초마다 업데이트
                
            except Exception as e:
                self.dashboard.add_event(f"❌ 업데이트 오류: {str(e)[:30]}")
                time.sleep(5)


# ============================================================
# 메인 실행 (독립 실행 또는 통합)
# ============================================================

def run_with_dashboard():
    """대시보드와 함께 자동매매 실행"""
    from trading_engine import TradingEngine
    
    # 설정
    config = {
        'symbols': ['BTC-USDT-SWAP'],
        'initial_capital': 0,  # 실제 잔고 사용
        'check_interval': 60,
        'long_leverage': 10,
        'long_trailing_stop': 0.10,
        'short_leverage': 3,
        'short_trailing_stop': 0.02,
        'position_size': 0.1,
    }
    
    # 대시보드 초기화
    dashboard = init_dashboard()
    dashboard.add_event("🔧 시스템 초기화 중...")
    dashboard.render()
    
    # 엔진 생성
    engine = TradingEngine(config)
    
    # 콜백 설정
    def on_signal(signal):
        action = signal.get('action', '')
        strategy = signal.get('strategy_type', '')
        is_real = "실제" if signal.get('is_real') else "가상"
        dashboard.add_event(f"📡 [{is_real}] {strategy.upper()} {action}")
    
    def on_trade(signal, success):
        status = "성공" if success else "실패"
        pnl = signal.get('pnl', 0)
        if signal.get('action') == 'enter':
            dashboard.add_event(f"🟢 진입 {status}: ${signal.get('price', 0):,.2f}")
        else:
            dashboard.add_event(f"🔴 청산 {status}: 손익 ${pnl:+.2f}")
    
    engine.on_signal_callback = on_signal
    engine.on_trade_callback = on_trade
    
    # 통합 시작
    integration = DashboardIntegration(engine)
    
    try:
        dashboard.add_event("🚀 자동매매 시작...")
        integration.start()
        
        # 메인 루프
        while integration.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        dashboard.add_event("⚠️ 사용자 중지 요청")
        integration.stop()
        dashboard.render()
        print("\n\n👋 자동매매가 종료되었습니다.\n")


if __name__ == "__main__":
    run_with_dashboard()
