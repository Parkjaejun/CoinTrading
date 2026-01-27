# main_window_balance_fix.py
"""
main_window.py 잔고 표시 통일 패치

문제:
- 대시보드 오른쪽 위의 자산과 상단 패널의 자산이 다르게 표시됨

해결:
- 단일 소스에서 잔고를 가져와 모든 위치에 동일하게 표시

적용 방법:
1. main_window.py의 잔고 업데이트 관련 메서드를 수정
2. 또는 이 파일의 클래스를 상속하여 사용
"""

from PyQt5.QtWidgets import QMainWindow, QLabel
from PyQt5.QtCore import QTimer


class BalanceSyncMixin:
    """
    잔고 동기화 믹스인
    
    main_window.py의 TradingMainWindow 클래스에 믹스인으로 추가하거나,
    해당 메서드들을 복사하여 사용
    """
    
    def setup_balance_sync(self):
        """
        잔고 동기화 설정
        
        main_window.py의 __init__ 또는 setup_ui 끝에 호출
        """
        # 단일 잔고 값
        self._synced_balance = 0.0
        self._synced_available = 0.0
        self._synced_margin = 0.0
        self._synced_pnl = 0.0
        
        # 잔고 동기화 타이머
        self.balance_sync_timer = QTimer()
        self.balance_sync_timer.timeout.connect(self.sync_all_balances)
        self.balance_sync_timer.start(5000)  # 5초마다
        
        print("✅ 잔고 동기화 설정 완료")
    
    def fetch_unified_balance(self) -> dict:
        """
        통일된 잔고 조회 - 단일 소스
        
        Returns:
            dict: {
                'total': 총 자산,
                'available': 사용 가능,
                'margin': 증거금,
                'pnl': 미실현 손익
            }
        """
        try:
            from okx.order_manager import OrderManager
            om = OrderManager()
            
            # 계좌 잔고 조회
            balance_info = om.get_account_balance('USDT')
            
            if balance_info:
                self._synced_available = balance_info.get('available', 0)
                self._synced_balance = balance_info.get('equity', self._synced_available)
                self._synced_margin = balance_info.get('frozen', 0)
            
            # 미실현 손익 조회
            positions = om.get_positions()
            total_pnl = sum(p.get('upl', 0) for p in positions)
            self._synced_pnl = total_pnl
            
            return {
                'total': self._synced_balance,
                'available': self._synced_available,
                'margin': self._synced_margin,
                'pnl': self._synced_pnl
            }
            
        except Exception as e:
            print(f"⚠️ 잔고 조회 오류: {e}")
            return {
                'total': self._synced_balance,
                'available': self._synced_available,
                'margin': self._synced_margin,
                'pnl': self._synced_pnl
            }
    
    def sync_all_balances(self):
        """
        모든 잔고 표시 동기화
        
        이 메서드를 5초마다 호출하여 모든 위치의 잔고를 동일하게 유지
        """
        balance = self.fetch_unified_balance()
        
        total = balance['total']
        available = balance['available']
        margin = balance['margin']
        pnl = balance['pnl']
        
        # 1. 상단 상태바 잔고 업데이트
        if hasattr(self, 'balance_label') and isinstance(self.balance_label, QLabel):
            self.balance_label.setText(f"잔고: ${total:,.2f}")
        
        # 2. 대시보드 계좌 정보 업데이트
        if hasattr(self, 'total_balance_label'):
            self.total_balance_label.setText(f"${total:,.2f}")
        
        if hasattr(self, 'available_balance_label'):
            self.available_balance_label.setText(f"사용 가능: ${available:,.2f}")
        
        if hasattr(self, 'margin_balance_label'):
            self.margin_balance_label.setText(f"증거금: ${margin:,.2f}")
        
        if hasattr(self, 'unrealized_pnl_label'):
            pnl_color = "#00ff00" if pnl >= 0 else "#ff0000"
            self.unrealized_pnl_label.setText(f"미실현손익: ${pnl:+,.2f}")
            self.unrealized_pnl_label.setStyleSheet(f"color: {pnl_color}")
        
        # 3. 자동매매 위젯 잔고 업데이트
        if hasattr(self, 'auto_trading_widget') and self.auto_trading_widget:
            if hasattr(self.auto_trading_widget, 'balance_label'):
                self.auto_trading_widget.balance_label.setText(f"${available:,.2f}")
            if hasattr(self.auto_trading_widget, 'on_balance_updated'):
                self.auto_trading_widget.on_balance_updated(available)


# =========================================================
# main_window.py에 적용하는 방법
# =========================================================

"""
방법 1: 메서드 복사

main_window.py의 TradingMainWindow 클래스에 위의 3개 메서드를 복사:
- setup_balance_sync()
- fetch_unified_balance()
- sync_all_balances()

그리고 __init__ 또는 setup_ui() 끝에 다음 추가:
    self.setup_balance_sync()


방법 2: 믹스인 사용

from main_window_balance_fix import BalanceSyncMixin

class TradingMainWindow(QMainWindow, BalanceSyncMixin):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_balance_sync()  # 추가


방법 3: 기존 update_account_info 메서드 수정

기존 main_window.py의 update_account_info 메서드를 찾아서 아래처럼 수정:

def update_account_info(self, data):
    '''계좌 정보 업데이트 - 통일된 방식'''
    try:
        # 데이터 추출
        total_eq = float(data.get('totalEq', 0))
        
        details = data.get('details', [])
        usdt_info = next((d for d in details if d.get('ccy') == 'USDT'), {})
        
        available = float(usdt_info.get('availBal', 0))
        frozen = float(usdt_info.get('frozenBal', 0))
        
        # 모든 위치 업데이트
        # 1. 상단 상태바
        if hasattr(self, 'balance_label'):
            self.balance_label.setText(f"잔고: ${total_eq:,.2f}")
        
        # 2. 대시보드
        if hasattr(self, 'total_balance_label'):
            self.total_balance_label.setText(f"${total_eq:,.2f}")
        if hasattr(self, 'available_balance_label'):
            self.available_balance_label.setText(f"사용 가능: ${available:,.2f}")
        if hasattr(self, 'margin_balance_label'):
            self.margin_balance_label.setText(f"증거금: ${frozen:,.2f}")
        
        # 3. 자동매매 위젯
        if hasattr(self, 'auto_trading_widget') and self.auto_trading_widget:
            if hasattr(self.auto_trading_widget, 'balance_label'):
                self.auto_trading_widget.balance_label.setText(f"${available:,.2f}")
        
    except Exception as e:
        print(f"⚠️ 계좌 정보 업데이트 오류: {e}")
"""


# =========================================================
# 즉시 적용 가능한 패치 함수
# =========================================================

def patch_main_window_balance(main_window):
    """
    main_window 인스턴스에 잔고 동기화 패치 적용
    
    사용법 (main_window.py의 __init__ 끝에):
        from main_window_balance_fix import patch_main_window_balance
        patch_main_window_balance(self)
    """
    import types
    
    # 메서드 바인딩
    main_window._synced_balance = 0.0
    main_window._synced_available = 0.0
    main_window._synced_margin = 0.0
    main_window._synced_pnl = 0.0
    
    main_window.fetch_unified_balance = types.MethodType(
        BalanceSyncMixin.fetch_unified_balance, main_window
    )
    main_window.sync_all_balances = types.MethodType(
        BalanceSyncMixin.sync_all_balances, main_window
    )
    
    # 타이머 설정
    main_window.balance_sync_timer = QTimer()
    main_window.balance_sync_timer.timeout.connect(main_window.sync_all_balances)
    main_window.balance_sync_timer.start(5000)
    
    # 즉시 한번 실행
    main_window.sync_all_balances()
    
    print("✅ main_window 잔고 동기화 패치 적용됨")
