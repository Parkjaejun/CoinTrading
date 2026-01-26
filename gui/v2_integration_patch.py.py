# gui/v2_integration_patch.py
"""
main_window.py에 v2 전략 모니터링 통합 패치

사용법:
    main_window.py의 __init__ 또는 setup_ui에서 이 모듈의 함수 호출

    # 예시
    from gui.v2_integration_patch import integrate_v2_monitoring
    integrate_v2_monitoring(self)  # self = MainWindow 인스턴스
"""

from typing import Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget

# v2 모듈 import
V2_WIDGETS_AVAILABLE = False
V2_BRIDGE_AVAILABLE = False

try:
    from gui.v2_strategy_widget import V2StrategyMonitoringWidget
    V2_WIDGETS_AVAILABLE = True
except ImportError:
    V2StrategyMonitoringWidget = None

try:
    from gui.v2_strategy_bridge import V2StrategyBridge, setup_strategy_bridge, GUILoggingEmailNotifier
    V2_BRIDGE_AVAILABLE = True
except ImportError:
    V2StrategyBridge = None
    setup_strategy_bridge = None
    GUILoggingEmailNotifier = None


def integrate_v2_monitoring(main_window, strategy_manager=None) -> bool:
    """
    v2 전략 모니터링을 메인 윈도우에 통합
    
    Args:
        main_window: TradingMainWindow 인스턴스
        strategy_manager: v2 StrategyManager 인스턴스 (없으면 나중에 설정)
    
    Returns:
        통합 성공 여부
    """
    if not V2_WIDGETS_AVAILABLE:
        print("⚠️ v2 위젯 모듈 없음 - gui/v2_strategy_widget.py 필요")
        return False
    
    if not V2_BRIDGE_AVAILABLE:
        print("⚠️ v2 브릿지 모듈 없음 - gui/v2_strategy_bridge.py 필요")
        return False
    
    try:
        # 1. 브릿지 생성
        main_window.v2_bridge = V2StrategyBridge()
        
        # 2. 전략 매니저 연결 (있으면)
        if strategy_manager:
            main_window.v2_bridge.set_strategy_manager(strategy_manager)
        
        # 3. v2 모니터링 위젯 생성
        main_window.v2_monitoring_widget = V2StrategyMonitoringWidget(main_window.v2_bridge)
        
        # 4. 기존 탭 위젯에 추가
        if hasattr(main_window, 'tab_widget'):
            main_window.tab_widget.addTab(
                main_window.v2_monitoring_widget, 
                "🎯 v2 전략"
            )
            print("✅ v2 전략 모니터링 탭 추가됨")
        
        # 5. 모니터링 시작
        main_window.v2_bridge.start_monitoring()
        
        # 6. 로그 연결 (기존 로그 위젯에도 표시)
        if hasattr(main_window, 'log_display'):
            main_window.v2_bridge.log_message.connect(
                lambda msg, t: add_to_main_log(main_window, msg, t)
            )
        
        print("✅ v2 전략 모니터링 통합 완료")
        return True
        
    except Exception as e:
        print(f"❌ v2 통합 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def add_to_main_log(main_window, message: str, log_type: str):
    """메인 로그 위젯에 v2 로그 추가"""
    try:
        if hasattr(main_window, 'log_display'):
            if hasattr(main_window.log_display, 'add_log'):
                main_window.log_display.add_log(f"[v2] {message}", log_type)
            elif hasattr(main_window.log_display, 'append'):
                main_window.log_display.append(f"[v2][{log_type}] {message}")
    except:
        pass


def connect_strategy_manager_to_v2(main_window, strategy_manager) -> bool:
    """
    전략 매니저를 v2 브릿지에 연결
    
    TradingDataThread에서 전략 매니저가 초기화된 후 호출
    
    Args:
        main_window: TradingMainWindow 인스턴스
        strategy_manager: StrategyManager 인스턴스
    
    Returns:
        연결 성공 여부
    """
    try:
        if not hasattr(main_window, 'v2_bridge') or not main_window.v2_bridge:
            print("⚠️ v2 브릿지가 초기화되지 않음")
            return False
        
        main_window.v2_bridge.set_strategy_manager(strategy_manager)
        print("✅ 전략 매니저 ↔ v2 브릿지 연결됨")
        return True
        
    except Exception as e:
        print(f"❌ 전략 매니저 연결 실패: {e}")
        return False


def create_v2_email_notifier_with_gui(main_window) -> Optional[object]:
    """
    GUI 연동 이메일 알림 객체 생성
    
    이 함수로 생성한 notifier를 전략에 전달하면
    이메일 발송 시 GUI에도 로그가 표시됨
    
    Args:
        main_window: TradingMainWindow 인스턴스
    
    Returns:
        GUILoggingEmailNotifier 인스턴스
    """
    if not V2_BRIDGE_AVAILABLE or not GUILoggingEmailNotifier:
        return None
    
    try:
        # 실제 이메일 알림 객체 생성
        from cointrading_v2.strategy.email_notifier import EmailNotifier, MockEmailNotifier
        from config import NOTIFICATION_CONFIG, DEFAULT_EMAIL_CONFIG
        
        # 이메일 설정 확인
        real_notifier = None
        
        if DEFAULT_EMAIL_CONFIG and DEFAULT_EMAIL_CONFIG.is_configured:
            real_notifier = EmailNotifier(
                smtp_server=DEFAULT_EMAIL_CONFIG.smtp_server,
                smtp_port=DEFAULT_EMAIL_CONFIG.smtp_port,
                sender_email=DEFAULT_EMAIL_CONFIG.sender_email,
                sender_password=DEFAULT_EMAIL_CONFIG.sender_password,
                recipient_email=DEFAULT_EMAIL_CONFIG.recipient_email
            )
            print("✅ 실제 이메일 알림 활성화")
        else:
            email_cfg = NOTIFICATION_CONFIG.get('email', {})
            if email_cfg.get('enabled') and email_cfg.get('sender'):
                real_notifier = EmailNotifier(
                    smtp_server=email_cfg.get('smtp_server', 'smtp.gmail.com'),
                    smtp_port=email_cfg.get('smtp_port', 587),
                    sender_email=email_cfg.get('sender', ''),
                    sender_password=email_cfg.get('password', ''),
                    recipient_email=email_cfg.get('recipient', '')
                )
                print("✅ 실제 이메일 알림 활성화 (config.py)")
            else:
                real_notifier = MockEmailNotifier()
                print("⚠️ MockEmailNotifier 사용 (이메일 설정 없음)")
        
        # GUI 연동 래퍼
        bridge = getattr(main_window, 'v2_bridge', None)
        gui_notifier = GUILoggingEmailNotifier(real_notifier, bridge)
        
        return gui_notifier
        
    except Exception as e:
        print(f"❌ GUI 이메일 알림 생성 실패: {e}")
        return None


# =================================================================
# main_window.py 수정 가이드
# =================================================================
"""
main_window.py에 다음 코드를 추가하세요:

1. import 추가:
   ```python
   from gui.v2_integration_patch import integrate_v2_monitoring, connect_strategy_manager_to_v2
   ```

2. __init__ 또는 setup_ui 끝에 추가:
   ```python
   # v2 전략 모니터링 통합
   integrate_v2_monitoring(self)
   ```

3. TradingDataThread에서 strategy_manager 초기화 후:
   ```python
   # 메인 윈도우에 전략 매니저 연결 (v2 브릿지용)
   if hasattr(self, 'main_window') and self.main_window:
       from gui.v2_integration_patch import connect_strategy_manager_to_v2
       connect_strategy_manager_to_v2(self.main_window, self.strategy_manager)
   ```

4. 또는 더 간단하게, run_gui.py에서:
   ```python
   # GUI 시작 후
   window = TradingMainWindow()
   
   # v2 통합
   from gui.v2_integration_patch import integrate_v2_monitoring
   integrate_v2_monitoring(window)
   
   window.show()
   ```
"""
