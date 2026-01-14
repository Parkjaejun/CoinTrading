# patch_main_window.py
"""
main_window.py에 자동매매 탭을 추가하는 패치 스크립트
실행: python patch_main_window.py
"""

import os
import shutil
from datetime import datetime

def patch_main_window():
    """main_window.py에 자동매매 탭 추가"""
    
    main_window_path = "gui/main_window.py"
    
    if not os.path.exists(main_window_path):
        print(f"❌ {main_window_path} 파일을 찾을 수 없습니다.")
        print("   프로젝트 루트 디렉토리에서 실행하세요.")
        return False
    
    # 백업 생성
    backup_path = f"{main_window_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(main_window_path, backup_path)
    print(f"✅ 백업 생성: {backup_path}")
    
    # 파일 읽기
    with open(main_window_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 자동매매 위젯 import 추가
    import_patch = '''
try:
    from gui.auto_trading_widget import AutoTradingWidget
    print("✅ AutoTradingWidget 임포트 성공")
    AUTO_TRADING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ AutoTradingWidget 임포트 실패: {e}")
    AUTO_TRADING_AVAILABLE = False
'''
    
    # import 위치 찾기 (CONDITION_MONITORING_AVAILABLE 다음)
    if "AUTO_TRADING_AVAILABLE" not in content:
        insert_pos = content.find("CONDITION_MONITORING_AVAILABLE = False")
        if insert_pos != -1:
            insert_pos = content.find("\n", insert_pos) + 1
            content = content[:insert_pos] + import_patch + content[insert_pos:]
            print("✅ AutoTradingWidget import 추가됨")
        else:
            print("⚠️ import 위치를 찾을 수 없습니다. 수동으로 추가하세요.")
    else:
        print("ℹ️ AutoTradingWidget import가 이미 존재합니다.")
    
    # 2. 자동매매 탭 생성 메서드 추가
    auto_trading_tab_method = '''
    def create_auto_trading_tab(self):
        """🤖 자동매매 탭 생성"""
        if AUTO_TRADING_AVAILABLE:
            try:
                self.auto_trading_widget = AutoTradingWidget()
                self.tab_widget.addTab(self.auto_trading_widget, "🤖 자동매매")
                print("✅ 자동매매 탭 생성 완료")
            except Exception as e:
                print(f"❌ 자동매매 탭 생성 실패: {e}")
                # 대체 위젯
                fallback = QWidget()
                layout = QVBoxLayout(fallback)
                layout.addWidget(QLabel("자동매매 위젯을 로드할 수 없습니다."))
                layout.addWidget(QLabel(f"오류: {e}"))
                self.tab_widget.addTab(fallback, "🤖 자동매매")
        else:
            # AutoTradingWidget 사용 불가 시 대체 UI
            fallback_widget = QWidget()
            layout = QVBoxLayout(fallback_widget)
            
            info_label = QLabel("⚠️ 자동매매 위젯을 로드할 수 없습니다.")
            info_label.setStyleSheet("font-size: 14px; color: #f39c12;")
            layout.addWidget(info_label)
            
            instruction = QLabel(
                "auto_trading_widget.py 파일을 gui/ 폴더에 복사하세요:\\n"
                "copy auto_trading_widget.py gui\\\\"
            )
            layout.addWidget(instruction)
            
            # 대안: CLI 실행 버튼
            run_btn = QPushButton("🚀 CLI에서 자동매매 실행")
            run_btn.clicked.connect(self.run_trading_engine_cli)
            layout.addWidget(run_btn)
            
            layout.addStretch()
            self.tab_widget.addTab(fallback_widget, "🤖 자동매매")
    
    def run_trading_engine_cli(self):
        """CLI에서 자동매매 엔진 실행"""
        import subprocess
        import sys
        
        reply = QMessageBox.question(
            self,
            "자동매매 실행",
            "새 터미널에서 자동매매 엔진을 실행하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if sys.platform == 'win32':
                    subprocess.Popen(['start', 'cmd', '/k', 'python', 'trading_engine.py'], shell=True)
                else:
                    subprocess.Popen(['gnome-terminal', '--', 'python', 'trading_engine.py'])
                QMessageBox.information(self, "실행", "자동매매 엔진이 새 터미널에서 시작됩니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"실행 실패: {e}")

'''
    
    # 메서드 추가 위치 찾기 (create_test_trading_tab 메서드 앞)
    if "def create_auto_trading_tab" not in content:
        insert_pos = content.find("def create_test_trading_tab")
        if insert_pos != -1:
            content = content[:insert_pos] + auto_trading_tab_method + "\n    " + content[insert_pos:]
            print("✅ create_auto_trading_tab 메서드 추가됨")
        else:
            print("⚠️ 메서드 삽입 위치를 찾을 수 없습니다.")
    else:
        print("ℹ️ create_auto_trading_tab 메서드가 이미 존재합니다.")
    
    # 3. 탭 생성 호출 추가
    # create_test_trading_tab() 호출 다음에 create_auto_trading_tab() 호출 추가
    if "self.create_auto_trading_tab()" not in content:
        old_line = "self.create_test_trading_tab()"
        new_line = "self.create_test_trading_tab()\n        \n        # 🤖 자동매매 탭 추가\n        self.create_auto_trading_tab()"
        
        if old_line in content:
            content = content.replace(old_line, new_line)
            print("✅ create_auto_trading_tab() 호출 추가됨")
        else:
            print("⚠️ 탭 생성 호출 위치를 찾을 수 없습니다.")
    else:
        print("ℹ️ create_auto_trading_tab() 호출이 이미 존재합니다.")
    
    # 파일 저장
    with open(main_window_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ 패치 완료!")
    print("   GUI를 다시 실행하세요: python run_gui.py")
    
    return True


def create_simple_auto_trading_widget():
    """간단한 자동매매 위젯 파일 생성"""
    
    widget_path = "gui/auto_trading_widget.py"
    
    if os.path.exists(widget_path):
        print(f"ℹ️ {widget_path} 파일이 이미 존재합니다.")
        return True
    
    # auto_trading_widget.py 내용
    widget_content = '''# gui/auto_trading_widget.py
"""
자동매매 제어 위젯 (간소화 버전)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QGroupBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QCheckBox, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
import threading
import sys
import os

# 상위 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AutoTradingWidget(QWidget):
    """자동매매 제어 위젯"""
    
    log_signal = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = None
        self.is_running = False
        
        self.init_ui()
        self.log_signal.connect(self.append_log)
        
        # 상태 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(5000)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 제어 패널
        control_group = QGroupBox("🎮 자동매매 제어")
        control_layout = QHBoxLayout(control_group)
        
        self.status_label = QLabel("⚪ 대기 중")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        
        self.start_btn = QPushButton("🚀 자동매매 시작")
        self.start_btn.setMinimumSize(150, 50)
        self.start_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.start_btn.clicked.connect(self.start_trading)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("🛑 중지")
        self.stop_btn.setMinimumSize(100, 50)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.stop_btn.clicked.connect(self.stop_trading)
        control_layout.addWidget(self.stop_btn)
        
        layout.addWidget(control_group)
        
        # 설정 패널
        settings_group = QGroupBox("⚙️ 전략 설정")
        settings_layout = QGridLayout(settings_group)
        
        settings_layout.addWidget(QLabel("거래 심볼:"), 0, 0)
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTC-USDT-SWAP", "ETH-USDT-SWAP"])
        settings_layout.addWidget(self.symbol_combo, 0, 1)
        
        settings_layout.addWidget(QLabel("초기 자본 ($):"), 0, 2)
        self.capital_spin = QSpinBox()
        self.capital_spin.setRange(10, 100000)
        self.capital_spin.setValue(1000)
        settings_layout.addWidget(self.capital_spin, 0, 3)
        
        settings_layout.addWidget(QLabel("롱 레버리지:"), 1, 0)
        self.long_lev = QSpinBox()
        self.long_lev.setRange(1, 100)
        self.long_lev.setValue(10)
        settings_layout.addWidget(self.long_lev, 1, 1)
        
        settings_layout.addWidget(QLabel("숏 레버리지:"), 1, 2)
        self.short_lev = QSpinBox()
        self.short_lev.setRange(1, 100)
        self.short_lev.setValue(3)
        settings_layout.addWidget(self.short_lev, 1, 3)
        
        layout.addWidget(settings_group)
        
        # 상태 테이블
        status_group = QGroupBox("📊 전략 상태")
        status_layout = QVBoxLayout(status_group)
        
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(6)
        self.status_table.setHorizontalHeaderLabels(["전략", "모드", "상태", "자본", "손익", "거래수"])
        self.status_table.setMaximumHeight(120)
        status_layout.addWidget(self.status_table)
        
        stats_layout = QHBoxLayout()
        self.runtime_label = QLabel("실행 시간: --:--:--")
        self.signals_label = QLabel("총 신호: 0")
        self.trades_label = QLabel("실행 거래: 0")
        stats_layout.addWidget(self.runtime_label)
        stats_layout.addWidget(self.signals_label)
        stats_layout.addWidget(self.trades_label)
        stats_layout.addStretch()
        status_layout.addLayout(stats_layout)
        
        layout.addWidget(status_group)
        
        # 로그
        log_group = QGroupBox("📜 로그")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas;")
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    def get_config(self):
        return {
            'symbols': [self.symbol_combo.currentText()],
            'initial_capital': self.capital_spin.value(),
            'check_interval': 60,
            'long_leverage': self.long_lev.value(),
            'short_leverage': self.short_lev.value(),
            'long_trailing_stop': 0.10,
            'short_trailing_stop': 0.02,
            'position_size': 0.1,
        }
    
    def start_trading(self):
        reply = QMessageBox.warning(
            self, "⚠️ 자동매매 시작",
            "실제 자금으로 자동매매를 시작합니다.\\n계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            from trading_engine import TradingEngine
            
            config = self.get_config()
            self.append_log(f"⚙️ 설정: {config}")
            
            self.engine = TradingEngine(config)
            self.engine.on_signal_callback = self.on_signal
            self.engine.on_trade_callback = self.on_trade
            
            if self.engine.start():
                self.is_running = True
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                self.status_label.setText("🟢 실행 중")
                self.append_log("🚀 자동매매 시작!")
            else:
                self.append_log("❌ 엔진 시작 실패")
                
        except Exception as e:
            self.append_log(f"❌ 오류: {e}")
            QMessageBox.critical(self, "오류", f"자동매매 시작 오류: {e}")
    
    def stop_trading(self):
        if self.engine:
            def stop():
                self.engine.stop()
            threading.Thread(target=stop, daemon=True).start()
        
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("⚪ 중지됨")
        self.append_log("🛑 자동매매 중지")
    
    def on_signal(self, signal):
        msg = f"📡 [{signal.get('strategy_type')}] {signal.get('action')}: {signal.get('symbol')}"
        self.log_signal.emit(msg)
    
    def on_trade(self, signal, success):
        status = "✅" if success else "❌"
        self.log_signal.emit(f"💰 거래 {status}")
    
    def refresh_status(self):
        if not self.engine or not self.is_running:
            return
        try:
            status = self.engine.get_status()
            if status.get('runtime'):
                self.runtime_label.setText(f"실행 시간: {status['runtime']}")
            self.signals_label.setText(f"총 신호: {status.get('total_signals', 0)}")
            self.trades_label.setText(f"실행 거래: {status.get('executed_trades', 0)}")
        except:
            pass
    
    def append_log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")
'''
    
    # 디렉토리 확인
    os.makedirs("gui", exist_ok=True)
    
    with open(widget_path, 'w', encoding='utf-8') as f:
        f.write(widget_content)
    
    print(f"✅ {widget_path} 파일 생성됨")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 main_window.py 자동매매 탭 패치")
    print("=" * 60)
    
    # 1. auto_trading_widget.py 생성
    create_simple_auto_trading_widget()
    
    # 2. main_window.py 패치
    patch_main_window()
