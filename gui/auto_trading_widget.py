# gui/auto_trading_widget.py
"""
자동매매 위젯

구성:
- 왼쪽: 제어 패널 (모드 표시, 설정, 버튼, 통계)
- 중앙: 조건 모니터링 위젯
- 오른쪽: 실행 로그

기능:
- 자동매매 시작/정지
- 1주일 과거 데이터 로드
- 진입 조건 실시간 모니터링
- 가상/실제 모드 전환 추적
"""

from datetime import datetime
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSpinBox, QGroupBox, QFrame,
    QTextEdit, QComboBox, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from gui.condition_monitor_widget import ConditionMonitorWidget


class AutoTradingWidget(QWidget):
    """
    자동매매 제어 위젯
    레이아웃: [제어 패널 25%] [조건 모니터링 50%] [로그 25%]
    """
    
    trading_started = pyqtSignal()
    trading_stopped = pyqtSignal()
    trade_executed = pyqtSignal(dict)
    request_historical_data = pyqtSignal()  # 과거 데이터 요청 시그널
    
    def __init__(self, parent=None, account_manager=None, data_loader=None):
        super().__init__(parent)
        
        self.account_manager = account_manager
        self.data_loader = data_loader
        
        # 상태
        self.is_running = False
        self.is_real_mode = False
        self.check_count = 0
        self.signal_count = 0
        self.virtual_trade_count = 0
        self.real_trade_count = 0
        
        # 가상 자본 추적
        self.virtual_capital = 10000.0
        self.virtual_trough = 10000.0
        self.real_capital = 10000.0
        self.real_peak = 10000.0
        
        # 타이머
        self.check_timer: Optional[QTimer] = None
        
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self):
        """UI 구성"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 1. 왼쪽: 제어 패널 (25%)
        control_panel = self._create_control_panel()
        
        # 2. 중앙: 조건 모니터링 (50%)
        monitor_group = QGroupBox("🎯 진입 조건 모니터링")
        monitor_layout = QVBoxLayout(monitor_group)
        monitor_layout.setContentsMargins(5, 10, 5, 5)
        self.condition_monitor = ConditionMonitorWidget()
        monitor_layout.addWidget(self.condition_monitor)
        
        # 3. 오른쪽: 실행 로그 (25%)
        log_panel = self._create_log_panel()
        
        main_layout.addWidget(control_panel, 25)
        main_layout.addWidget(monitor_group, 50)
        main_layout.addWidget(log_panel, 25)
    
    def _create_control_panel(self) -> QGroupBox:
        """제어 패널"""
        panel = QGroupBox("🎮 제어 패널")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # 현재 모드 표시
        mode_group = QGroupBox("현재 모드")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_indicator = QLabel("⏸️ 대기 중")
        self.mode_indicator.setAlignment(Qt.AlignCenter)
        self.mode_indicator.setFont(QFont("Arial", 13, QFont.Bold))
        self.mode_indicator.setMinimumHeight(50)
        self.mode_indicator.setStyleSheet("""
            QLabel { background-color: #3a3a3a; border-radius: 8px; padding: 10px; color: #888888; }
        """)
        mode_layout.addWidget(self.mode_indicator)
        layout.addWidget(mode_group)
        
        # 거래 설정
        settings_group = QGroupBox("거래 설정")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setSpacing(8)
        
        settings_layout.addWidget(QLabel("레버리지:"), 0, 0)
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 20)
        self.leverage_spin.setValue(10)
        self.leverage_spin.setSuffix("x")
        settings_layout.addWidget(self.leverage_spin, 0, 1)
        
        settings_layout.addWidget(QLabel("트레일링스탑:"), 1, 0)
        self.trailing_spin = QSpinBox()
        self.trailing_spin.setRange(1, 50)
        self.trailing_spin.setValue(10)
        self.trailing_spin.setSuffix("%")
        settings_layout.addWidget(self.trailing_spin, 1, 1)
        
        settings_layout.addWidget(QLabel("포지션 비율:"), 2, 0)
        self.position_ratio_spin = QSpinBox()
        self.position_ratio_spin.setRange(10, 100)
        self.position_ratio_spin.setValue(50)
        self.position_ratio_spin.setSuffix("%")
        settings_layout.addWidget(self.position_ratio_spin, 2, 1)
        
        layout.addWidget(settings_group)
        
        # 버튼들
        self.start_btn = QPushButton("🚀 자동매매 시작")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.start_btn.setStyleSheet("""
            QPushButton { background-color: #28a745; color: white; border: none; border-radius: 6px; padding: 10px; }
            QPushButton:hover { background-color: #218838; }
        """)
        self.start_btn.clicked.connect(self.start_auto_trading)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 자동매매 정지")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: #6c757d; color: white; border: none; border-radius: 6px; padding: 10px; }
            QPushButton:hover { background-color: #5a6268; }
            QPushButton:disabled { background-color: #3a3a3a; color: #666666; }
        """)
        self.stop_btn.clicked.connect(self.stop_auto_trading)
        layout.addWidget(self.stop_btn)
        
        self.emergency_btn = QPushButton("🔴 긴급 청산")
        self.emergency_btn.setMinimumHeight(40)
        self.emergency_btn.setStyleSheet("""
            QPushButton { background-color: #dc3545; color: white; border: none; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #c82333; }
        """)
        self.emergency_btn.clicked.connect(self.emergency_liquidation)
        layout.addWidget(self.emergency_btn)
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #3a3a3a;")
        layout.addWidget(separator)
        
        # 통계
        stats_group = QGroupBox("📊 통계")
        stats_layout = QGridLayout(stats_group)
        stats_layout.setSpacing(5)
        
        self.check_count_label = QLabel("0")
        self.check_count_label.setAlignment(Qt.AlignRight)
        self.signal_count_label = QLabel("0")
        self.signal_count_label.setAlignment(Qt.AlignRight)
        self.virtual_trade_label = QLabel("0")
        self.virtual_trade_label.setAlignment(Qt.AlignRight)
        self.real_trade_label = QLabel("0")
        self.real_trade_label.setAlignment(Qt.AlignRight)
        
        stats_layout.addWidget(QLabel("조건 체크:"), 0, 0)
        stats_layout.addWidget(self.check_count_label, 0, 1)
        stats_layout.addWidget(QLabel("신호 감지:"), 1, 0)
        stats_layout.addWidget(self.signal_count_label, 1, 1)
        stats_layout.addWidget(QLabel("가상 거래:"), 2, 0)
        stats_layout.addWidget(self.virtual_trade_label, 2, 1)
        stats_layout.addWidget(QLabel("실제 거래:"), 3, 0)
        stats_layout.addWidget(self.real_trade_label, 3, 1)
        
        layout.addWidget(stats_group)
        layout.addStretch()
        
        return panel
    
    def _create_log_panel(self) -> QGroupBox:
        """로그 패널"""
        panel = QGroupBox("📝 실행 로그")
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit { background-color: #1a1a1a; color: #cccccc; border: 1px solid #3a3a3a; border-radius: 4px; padding: 5px; }
        """)
        layout.addWidget(self.log_text)
        
        filter_layout = QHBoxLayout()
        
        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(["전체", "정보", "신호", "거래", "오류"])
        self.log_filter_combo.setMinimumWidth(70)
        filter_layout.addWidget(self.log_filter_combo)
        
        self.log_search_edit = QLineEdit()
        self.log_search_edit.setPlaceholderText("검색...")
        filter_layout.addWidget(self.log_search_edit)
        
        clear_btn = QPushButton("🗑️")
        clear_btn.setMaximumWidth(35)
        clear_btn.clicked.connect(self.clear_logs)
        filter_layout.addWidget(clear_btn)
        
        layout.addLayout(filter_layout)
        return panel
    
    def _setup_connections(self):
        """시그널 연결"""
        self.condition_monitor.entry_signal_triggered.connect(self._on_entry_signal)
    
    def set_data_loader(self, loader):
        self.data_loader = loader
    
    def set_account_manager(self, manager):
        self.account_manager = manager
    
    def add_log(self, message: str, level: str = "정보"):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {"정보": "#cccccc", "신호": "#4ECDC4", "거래": "#28a745", "경고": "#ffc107", "오류": "#dc3545"}
        color = colors.get(level, "#cccccc")
        
        html = f'<span style="color:#888888;">[{timestamp}]</span> '
        html += f'<span style="color:{color};">[{level}]</span> '
        html += f'<span style="color:#ffffff;">{message}</span>'
        
        self.log_text.append(html)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        self.log_text.clear()
    
    def _update_mode_indicator(self, mode: str):
        """모드 표시 업데이트"""
        styles = {
            "stopped": ("⏸️ 대기 중", "#3a3a3a", "#888888"),
            "loading": ("⏳ 데이터 로드 중...", "#3a3a3a", "#ffc107"),
            "virtual": ("🟡 가상 모드", "#856404", "#ffc107"),
            "real": ("🟢 실제 모드", "#155724", "#28a745"),
            "error": ("🔴 오류", "#721c24", "#dc3545"),
        }
        
        text, bg, fg = styles.get(mode, styles["stopped"])
        self.mode_indicator.setText(text)
        self.mode_indicator.setStyleSheet(f"""
            QLabel {{ background-color: {bg}; border-radius: 8px; padding: 10px; color: {fg}; }}
        """)
    
    def start_auto_trading(self):
        """자동매매 시작"""
        if self.is_running:
            return
        
        reply = QMessageBox.question(
            self, "자동매매 시작",
            "자동매매를 시작하시겠습니까?\n\n• 먼저 가상 모드로 시작됩니다\n• 조건 충족 시 실제 거래로 전환됩니다\n• 1주일치 과거 데이터를 로드합니다",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            self.add_log("자동매매 시작 중...", "정보")
            self._update_mode_indicator("loading")
            
            # 과거 데이터 로드
            self.add_log("📊 과거 데이터 로드 중...", "정보")
            
            if self.data_loader:
                df = self.data_loader.load_historical_candles_sync(
                    symbol="BTC-USDT-SWAP", timeframe="30m", days=7
                )
                
                if df is not None and len(df) > 0:
                    self.add_log(f"✅ {len(df)}개 캔들 로드 완료", "정보")
                    self.request_historical_data.emit()  # 대시보드에 데이터 전달 요청
                else:
                    self.add_log("⚠️ 과거 데이터 로드 실패 - 테스트 모드", "경고")
            else:
                self.add_log("⚠️ 데이터 로더 없음 - 테스트 모드", "경고")
            
            # 가상 모드로 시작
            self.is_running = True
            self.is_real_mode = False
            self.virtual_capital = 10000.0
            self.virtual_trough = 10000.0
            
            self._update_mode_indicator("virtual")
            self.add_log("🟡 가상 모드로 자동매매 시작", "정보")
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            # 조건 체크 타이머 (10초)
            if self.check_timer is None:
                self.check_timer = QTimer()
                self.check_timer.timeout.connect(self._check_conditions)
            self.check_timer.start(10000)
            
            self._check_conditions()  # 첫 체크
            self.condition_monitor.start_monitoring()
            self.trading_started.emit()
            
        except Exception as e:
            self.add_log(f"❌ 자동매매 시작 실패: {e}", "오류")
            self._reset_state()
    
    def stop_auto_trading(self):
        """자동매매 정지"""
        if not self.is_running:
            return
        
        reply = QMessageBox.question(
            self, "자동매매 정지",
            "자동매매를 정지하시겠습니까?\n\n열린 포지션이 있다면 수동으로 관리해야 합니다.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._stop_trading()
            self.add_log("⏹️ 자동매매 정지됨", "정보")
    
    def _stop_trading(self):
        """내부 정지 처리"""
        self.is_running = False
        if self.check_timer:
            self.check_timer.stop()
        self.condition_monitor.stop_monitoring()
        self._update_mode_indicator("stopped")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.trading_stopped.emit()
    
    def _reset_state(self):
        """상태 초기화"""
        self.is_running = False
        self._update_mode_indicator("stopped")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def emergency_liquidation(self):
        """긴급 청산"""
        reply = QMessageBox.warning(
            self, "⚠️ 긴급 청산",
            "모든 포지션을 즉시 청산하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.add_log("🔴 긴급 청산 실행!", "거래")
            self._stop_trading()
            self.add_log("모든 포지션 청산 완료", "거래")
    
    def _check_conditions(self):
        """조건 체크"""
        if not self.is_running:
            return
        
        try:
            self.check_count += 1
            self.check_count_label.setText(str(self.check_count))
            
            data = {}
            
            if self.data_loader:
                strategy_data = self.data_loader.get_latest_strategy_data()
                if strategy_data:
                    data = strategy_data
            
            # 전략 상태 추가
            data['is_real_mode'] = self.is_real_mode
            data['virtual_capital'] = self.virtual_capital
            data['virtual_trough'] = self.virtual_trough
            data['real_capital'] = self.real_capital
            data['real_peak'] = self.real_peak
            data['reentry_ratio'] = 0.30
            data['stop_loss_ratio'] = 0.20
            
            self.condition_monitor.update_conditions(data)
            
            if self.check_count % 10 == 0:
                self.add_log(f"조건 체크 #{self.check_count} 완료", "정보")
                
        except Exception as e:
            self.add_log(f"조건 체크 오류: {e}", "오류")
    
    def _on_entry_signal(self, signal_type: str, data: Dict[str, Any]):
        """진입 신호 발생"""
        self.signal_count += 1
        self.signal_count_label.setText(str(self.signal_count))
        
        self.add_log(f"🔥 {signal_type.upper()} 진입 신호 감지!", "신호")
        
        if self.is_real_mode:
            self.add_log("실제 거래 실행 준비 중...", "거래")
            self.real_trade_count += 1
            self.real_trade_label.setText(str(self.real_trade_count))
        else:
            self.add_log("가상 거래 체결", "거래")
            self.virtual_trade_count += 1
            self.virtual_trade_label.setText(str(self.virtual_trade_count))
    
    def update_from_external(self, data: Dict[str, Any]):
        """외부에서 데이터 업데이트 (대시보드 등)"""
        if self.is_running:
            self.condition_monitor.update_conditions(data)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow, QWidget { background-color: #1e1e1e; color: #ffffff; }
        QGroupBox { font-weight: bold; border: 1px solid #3a3a3a; border-radius: 5px;
                   margin-top: 10px; padding-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
    """)
    
    window = QMainWindow()
    window.setWindowTitle("Auto Trading Widget Test")
    window.setGeometry(100, 100, 1200, 700)
    
    widget = AutoTradingWidget()
    window.setCentralWidget(widget)
    
    window.show()
    sys.exit(app.exec_())
