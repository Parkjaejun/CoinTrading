# quiet_mode_patch.py
"""
터미널 로그를 조용한 모드로 변경하고
고정 화면에서 실시간 상태를 표시하는 패치

기능:
- API 요청 로그 숨김
- 고정 상태 화면 표시
- 특이 사항만 로그 출력
"""

import os
import sys
import time
import threading
from datetime import datetime

# 전역 설정
QUIET_MODE = True  # 조용한 모드 활성화
DEBUG_API = False  # API 디버그 로그 비활성화


class TerminalStatusDisplay:
    """고정 화면 상태 표시기"""
    
    def __init__(self):
        self.is_running = False
        self.update_thread = None
        
        # 상태 데이터
        self.status = {
            'api_connected': False,
            'last_update': None,
            'cycle_count': 0,
            'balance': 0,
            'btc_price': 0,
            'eth_price': 0,
            'positions': 0,
            'errors': [],
            'last_signal': None,
            'uptime': 0
        }
        
        self.start_time = datetime.now()
        self.last_error_count = 0
    
    def start(self):
        """상태 표시 시작"""
        self.is_running = True
        self.update_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.update_thread.start()
        print("\n" + "=" * 60)
        print("🚀 OKX 트레이딩 시스템 시작")
        print("=" * 60)
    
    def stop(self):
        """상태 표시 중지"""
        self.is_running = False
    
    def update(self, **kwargs):
        """상태 업데이트"""
        for key, value in kwargs.items():
            if key in self.status:
                self.status[key] = value
        self.status['last_update'] = datetime.now()
    
    def add_error(self, error_msg: str):
        """에러 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status['errors'].append(f"[{timestamp}] {error_msg}")
        # 최근 5개만 유지
        self.status['errors'] = self.status['errors'][-5:]
    
    def add_signal(self, signal_msg: str):
        """신호 추가"""
        self.status['last_signal'] = f"[{datetime.now().strftime('%H:%M:%S')}] {signal_msg}"
    
    def _clear_screen(self):
        """화면 클리어 (Windows/Linux 호환)"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _move_cursor_up(self, lines: int):
        """커서를 위로 이동"""
        sys.stdout.write(f"\033[{lines}A")
        sys.stdout.flush()
    
    def _display_loop(self):
        """상태 표시 루프"""
        first_display = True
        display_lines = 20
        
        while self.is_running:
            try:
                # 첫 표시가 아니면 커서를 위로 이동
                if not first_display:
                    self._move_cursor_up(display_lines)
                else:
                    first_display = False
                
                # 상태 화면 생성
                self._render_status()
                
                time.sleep(1)  # 1초마다 업데이트
                
            except Exception as e:
                pass
    
    def _render_status(self):
        """상태 화면 렌더링"""
        now = datetime.now()
        uptime = now - self.start_time
        uptime_str = str(uptime).split('.')[0]  # 마이크로초 제거
        
        # 연결 상태
        api_icon = "🟢" if self.status['api_connected'] else "🔴"
        
        # 마지막 업데이트
        if self.status['last_update']:
            last_update = self.status['last_update'].strftime("%H:%M:%S")
            since_update = (now - self.status['last_update']).seconds
            update_status = "✅" if since_update < 10 else "⚠️"
        else:
            last_update = "--:--:--"
            update_status = "⏳"
            since_update = 0
        
        # 화면 출력
        lines = []
        lines.append("┌" + "─" * 58 + "┐")
        lines.append(f"│  🤖 OKX 트레이딩 시스템 모니터링          {now.strftime('%H:%M:%S')} │")
        lines.append("├" + "─" * 58 + "┤")
        lines.append(f"│  {api_icon} API 연결     {update_status} 마지막 업데이트: {last_update} ({since_update}초 전)  │")
        lines.append(f"│  ⏱️  실행 시간: {uptime_str:<20} 사이클: {self.status['cycle_count']:<10} │")
        lines.append("├" + "─" * 58 + "┤")
        lines.append(f"│  💰 잔고: ${self.status['balance']:>12,.2f}                          │")
        lines.append(f"│  ₿  BTC:  ${self.status['btc_price']:>12,.2f}                          │")
        lines.append(f"│  Ξ  ETH:  ${self.status['eth_price']:>12,.2f}                          │")
        lines.append(f"│  📊 포지션: {self.status['positions']}개                                      │")
        lines.append("├" + "─" * 58 + "┤")
        
        # 마지막 신호
        if self.status['last_signal']:
            signal_text = self.status['last_signal'][:50]
            lines.append(f"│  📡 {signal_text:<53} │")
        else:
            lines.append(f"│  📡 대기 중...                                           │")
        
        lines.append("├" + "─" * 58 + "┤")
        
        # 최근 에러
        if self.status['errors']:
            lines.append(f"│  ⚠️  최근 알림:                                          │")
            for err in self.status['errors'][-3:]:
                err_text = err[:54]
                lines.append(f"│    {err_text:<54} │")
        else:
            lines.append(f"│  ✅ 정상 작동 중                                         │")
            lines.append(f"│                                                          │")
            lines.append(f"│                                                          │")
        
        lines.append("└" + "─" * 58 + "┘")
        lines.append("  [Ctrl+C로 종료]")
        lines.append("")
        
        # 출력
        for line in lines:
            print(line)


# 전역 상태 표시기
_status_display = None


def get_status_display() -> TerminalStatusDisplay:
    """전역 상태 표시기 가져오기"""
    global _status_display
    if _status_display is None:
        _status_display = TerminalStatusDisplay()
    return _status_display


def quiet_print(msg: str, force: bool = False):
    """조용한 모드 프린트"""
    if not QUIET_MODE or force:
        print(msg)


def log_important(msg: str):
    """중요한 로그만 출력"""
    display = get_status_display()
    display.add_error(msg)


def log_signal(msg: str):
    """신호 로그"""
    display = get_status_display()
    display.add_signal(msg)


# API 요청 래퍼 (로그 숨김)
original_print = print


def quiet_mode_print(*args, **kwargs):
    """조용한 모드에서는 특정 로그 숨김"""
    if not QUIET_MODE:
        original_print(*args, **kwargs)
        return
    
    # 첫 번째 인자를 문자열로 변환
    msg = str(args[0]) if args else ""
    
    # 숨길 패턴들
    hide_patterns = [
        "🔍 전달할 파라미터",
        "🔍 생성된 쿼리",
        "🔍 서명용 request_path",
        "🔍 API 요청 디버그",
        "URL:",
        "Method:",
        "Headers:",
        "Timestamp:",
        "Request Path",
        "Query String:",
        "🔍 실제 요청 URL",
        "✅ 포지션 조회 성공",
        "✅ 포지션 업데이트",
        "✅ 운영 사이클",
        "📊 운영 사이클",
        "💰 잔액 정보 업데이트",
        "✅ 잔액 업데이트",
        "📈 가격 정보 업데이트",
        "✅ 가격 업데이트",
        "📊 활성 포지션",
    ]
    
    # 숨길 패턴 체크
    for pattern in hide_patterns:
        if pattern in msg:
            return
    
    # 나머지는 출력
    original_print(*args, **kwargs)


def enable_quiet_mode():
    """조용한 모드 활성화"""
    global QUIET_MODE
    import builtins
    QUIET_MODE = True
    builtins.print = quiet_mode_print
    print("🔇 조용한 모드 활성화됨")


def disable_quiet_mode():
    """조용한 모드 비활성화"""
    global QUIET_MODE
    import builtins
    QUIET_MODE = False
    builtins.print = original_print
    print("🔊 일반 모드로 전환됨")


# ============================================================
# config.py 패치용 함수
# ============================================================

def patch_config_py():
    """config.py에 조용한 모드 적용"""
    
    config_path = "config.py"
    
    if not os.path.exists(config_path):
        print(f"❌ {config_path} 파일을 찾을 수 없습니다.")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 이미 패치되어 있는지 확인
    if "QUIET_MODE" in content:
        print("ℹ️ config.py가 이미 패치되어 있습니다.")
        return True
    
    # 백업
    backup_path = f"config.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 백업 생성: {backup_path}")
    
    # 패치 추가 (파일 상단에)
    patch_code = '''
# ============================================================
# 조용한 모드 설정
# ============================================================
QUIET_MODE = True  # True: API 로그 숨김, False: 모든 로그 표시
DEBUG_API_REQUESTS = False  # API 요청 디버그 로그

def _should_print_log(msg: str) -> bool:
    """로그 출력 여부 결정"""
    if not QUIET_MODE:
        return True
    
    # 숨길 패턴
    hide_patterns = [
        "🔍 전달할", "🔍 생성된", "🔍 서명용", "🔍 API 요청",
        "URL:", "Method:", "Headers:", "Timestamp:", "Request Path",
        "Query String:", "🔍 실제 요청", "✅ 포지션 조회 성공",
        "✅ 포지션 업데이트", "✅ 운영 사이클", "📊 운영 사이클",
        "💰 잔액 정보", "✅ 잔액 업데이트", "📈 가격 정보",
        "✅ 가격 업데이트", "📊 활성 포지션",
    ]
    
    for pattern in hide_patterns:
        if pattern in str(msg):
            return False
    return True

# print 함수 래핑
_original_print = print

def _quiet_print(*args, **kwargs):
    if args and not _should_print_log(str(args[0])):
        return
    _original_print(*args, **kwargs)

# 조용한 모드 적용
if QUIET_MODE:
    import builtins
    builtins.print = _quiet_print

'''
    
    # 파일 시작 부분에 추가
    new_content = patch_code + "\n" + content
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ config.py 패치 완료!")
    print("   QUIET_MODE = True  (API 로그 숨김)")
    print("   False로 변경하면 모든 로그가 표시됩니다.")
    
    return True


# ============================================================
# 실시간 상태 모니터링 통합
# ============================================================

class QuietModeMonitor:
    """조용한 모드 모니터링"""
    
    def __init__(self):
        self.display = TerminalStatusDisplay()
        self.is_running = False
    
    def start(self):
        """모니터링 시작"""
        enable_quiet_mode()
        self.display.start()
        self.is_running = True
    
    def stop(self):
        """모니터링 중지"""
        self.display.stop()
        disable_quiet_mode()
        self.is_running = False
    
    def update_status(self, **kwargs):
        """상태 업데이트"""
        self.display.update(**kwargs)
    
    def log_error(self, msg: str):
        """에러 로그"""
        self.display.add_error(msg)
    
    def log_signal(self, msg: str):
        """신호 로그"""
        self.display.add_signal(msg)


# ============================================================
# 테스트 및 메인
# ============================================================

def test_quiet_mode():
    """조용한 모드 테스트"""
    print("=" * 60)
    print("🧪 조용한 모드 테스트")
    print("=" * 60)
    
    monitor = QuietModeMonitor()
    monitor.start()
    
    # 테스트 데이터
    import random
    
    try:
        cycle = 0
        while True:
            cycle += 1
            
            # 상태 업데이트
            monitor.update_status(
                api_connected=True,
                cycle_count=cycle,
                balance=random.uniform(80, 120),
                btc_price=random.uniform(94000, 95000),
                eth_price=random.uniform(3300, 3400),
                positions=random.randint(0, 2)
            )
            
            # 가끔 신호 발생
            if cycle % 10 == 0:
                monitor.log_signal(f"📊 사이클 {cycle} 완료")
            
            # 가끔 에러 발생 (테스트용)
            if cycle % 30 == 0:
                monitor.log_error(f"⚠️ 테스트 알림 #{cycle}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 테스트 종료")
        monitor.stop()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--patch":
        # config.py 패치
        patch_config_py()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 테스트 실행
        test_quiet_mode()
    else:
        print("사용법:")
        print("  python quiet_mode_patch.py --patch  : config.py에 조용한 모드 적용")
        print("  python quiet_mode_patch.py --test   : 상태 표시 테스트")
