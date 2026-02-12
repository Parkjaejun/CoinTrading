# gui/auto_trading_widget.py
"""
자동매매 위젯

구성:
- 왼쪽: 제어 패널 (모드 표시, 설정, 버튼, 통계)
- 중앙: 조건 모니터링 위젯
- 오른쪽: 실행 로그

수정사항 (2024-02-12):
- 전략 모드 선택 기능 추가 (Long Only / Long + Short) (신규)
- strategy_mode_changed 시그널 추가 (신규)
- update_balance() 메서드 추가 (신규)
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

try:
    from gui.condition_monitor_widget import ConditionMonitorWidget
    CONDITION_MONITOR_AVAILABLE = True
except ImportError:
    CONDITION_MONITOR_AVAILABLE = False
    print("⚠️ ConditionMonitorWidget 로드 실패")


class AutoTradingWidget(QWidget):
    """
    자동매매 제어 위젯
    레이아웃: [제어 패널 25%] [조건 모니터링 50%] [로그 25%]
    """
    
    trading_started = pyqtSignal()
    trading_stopped = pyqtSignal()
    trade_executed = pyqtSignal(dict)
    request_historical_data = pyqtSignal()
    strategy_mode_changed = pyqtSignal(str)  # ★ 신규: "long_only" 또는 "long_short"
    
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
        
        # ★ 신규: 전략 모드 (기본값: Long Only)
        self.strategy_mode = "long_only"  # "long_only" 또는 "long_short"
        
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
        
        if CONDITION_MONITOR_AVAILABLE:
            self.condition_monitor = ConditionMonitorWidget()
            monitor_layout.addWidget(self.condition_monitor)
        else:
            placeholder = QLabel("조건 모니터링 위젯 로드 실패")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #888888;")
            monitor_layout.addWidget(placeholder)
            self.condition_monitor = None
        
        # 3. 오른쪽: 실행 로그 (25%)
        log_group = QGroupBox("📋 실행 로그")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(5, 10, 5, 5)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #dcdcdc;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # 로그 제어 버튼
        log_btn_layout = QHBoxLayout()
        clear_log_btn = QPushButton("로그 지우기")
        clear_log_btn.clicked.connect(self.clear_log)
        log_btn_layout.addWidget(clear_log_btn)
        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)
        
        # 레이아웃 비율 설정
        main_layout.addWidget(control_panel, 25)
        main_layout.addWidget(monitor_group, 50)
        main_layout.addWidget(log_group, 25)
    
    def _create_control_panel(self) -> QWidget:
        """제어 패널 생성"""
        panel = QWidget()
        control_layout = QVBoxLayout(panel)
        control_layout.setSpacing(10)
        
        # ★ 신규: 전략 모드 설정 그룹
        strategy_mode_group = self._create_strategy_mode_group()
        control_layout.addWidget(strategy_mode_group)
        
        # 모드 표시 그룹
        mode_group = QGroupBox("📊 현재 모드")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_indicator = QLabel("⏸️ 대기 중")
        self.mode_indicator.setFont(QFont("Arial", 14, QFont.Bold))
        self.mode_indicator.setAlignment(Qt.AlignCenter)
        self.mode_indicator.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border-radius: 8px;
                padding: 15px;
                color: #888888;
            }
        """)
        mode_layout.addWidget(self.mode_indicator)
        
        control_layout.addWidget(mode_group)
        
        # 자본 정보 그룹
        capital_group = QGroupBox("💰 자본 현황")
        capital_layout = QGridLayout(capital_group)
        
        capital_layout.addWidget(QLabel("가상 자본:"), 0, 0)
        self.virtual_capital_label = QLabel("$10,000.00")
        self.virtual_capital_label.setStyleSheet("color: #ffc107;")
        capital_layout.addWidget(self.virtual_capital_label, 0, 1)
        
        capital_layout.addWidget(QLabel("실제 자본:"), 1, 0)
        self.real_capital_label = QLabel("$10,000.00")
        self.real_capital_label.setStyleSheet("color: #00ff88;")
        capital_layout.addWidget(self.real_capital_label, 1, 1)
        
        # ★ 신규: 잔고 표시
        capital_layout.addWidget(QLabel("계좌 잔고:"), 2, 0)
        self.balance_value_label = QLabel("$0.00")
        self.balance_value_label.setStyleSheet("color: #4ECDC4;")
        capital_layout.addWidget(self.balance_value_label, 2, 1)
        
        control_layout.addWidget(capital_group)
        
        # 통계 그룹
        stats_group = QGroupBox("📈 통계")
        stats_layout = QGridLayout(stats_group)
        
        stats_layout.addWidget(QLabel("체크 횟수:"), 0, 0)
        self.check_count_label = QLabel("0")
        stats_layout.addWidget(self.check_count_label, 0, 1)
        
        stats_layout.addWidget(QLabel("신호 횟수:"), 1, 0)
        self.signal_count_label = QLabel("0")
        stats_layout.addWidget(self.signal_count_label, 1, 1)
        
        stats_layout.addWidget(QLabel("가상 거래:"), 2, 0)
        self.virtual_trade_label = QLabel("0")
        self.virtual_trade_label.setStyleSheet("color: #ffc107;")
        stats_layout.addWidget(self.virtual_trade_label, 2, 1)
        
        stats_layout.addWidget(QLabel("실제 거래:"), 3, 0)
        self.real_trade_label = QLabel("0")
        self.real_trade_label.setStyleSheet("color: #00ff88;")
        stats_layout.addWidget(self.real_trade_label, 3, 1)
        
        control_layout.addWidget(stats_group)
        
        # 제어 버튼 그룹
        btn_group = QGroupBox("🎮 제어")
        btn_layout = QVBoxLayout(btn_group)
        
        self.start_btn = QPushButton("▶️ 자동매매 시작")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.start_btn.clicked.connect(self.start_auto_trading)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 자동매매 정지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_auto_trading)
        btn_layout.addWidget(self.stop_btn)
        
        control_layout.addWidget(btn_group)
        control_layout.addStretch()
        
        return panel
    
    # ========================================
    # ★ 신규: 전략 모드 선택 그룹
    # ========================================
    def _create_strategy_mode_group(self) -> QGroupBox:
        """전략 모드 선택 그룹 (신규)"""
        group = QGroupBox("🎯 전략 설정")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        # 전략 모드 선택
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("전략 모드:"))
        
        self.strategy_mode_combo = QComboBox()
        self.strategy_mode_combo.addItem("📈 Long Only", "long_only")
        self.strategy_mode_combo.addItem("📊 Long + Short", "long_short")
        self.strategy_mode_combo.setMinimumWidth(150)
        self.strategy_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
            }
            QComboBox:hover {
                border-color: #0078d4;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
        """)
        self.strategy_mode_combo.currentIndexChanged.connect(self._on_strategy_mode_changed)
        mode_layout.addWidget(self.strategy_mode_combo)
        mode_layout.addStretch()
        
        layout.addLayout(mode_layout)
        
        # 현재 상태 표시
        self.strategy_status_label = QLabel("🟢 Long Only 모드 활성")
        self.strategy_status_label.setStyleSheet("color: #28a745; font-size: 12px;")
        layout.addWidget(self.strategy_status_label)
        
        # 설명
        desc_label = QLabel(
            "• Long Only: 상승장에서 롱 포지션만 진입\n"
            "• Long + Short: 상승/하락장 모두 진입 가능"
        )
        desc_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(desc_label)
        
        # 경고 (Long+Short 선택 시)
        self.strategy_warning_label = QLabel(
            "⚠️ 숏 전략: 레버리지 3x, 트레일링스탑 2%"
        )
        self.strategy_warning_label.setStyleSheet("color: #f39c12; font-size: 11px;")
        self.strategy_warning_label.hide()
        layout.addWidget(self.strategy_warning_label)
        
        return group
    
    # ========================================
    # ★ 신규: 전략 모드 변경 핸들러
    # ========================================
    def _on_strategy_mode_changed(self, index: int):
        """전략 모드 변경 처리 (신규)"""
        if self.is_running:
            current_index = 0 if self.strategy_mode == "long_only" else 1
            self.strategy_mode_combo.blockSignals(True)
            self.strategy_mode_combo.setCurrentIndex(current_index)
            self.strategy_mode_combo.blockSignals(False)
            
            QMessageBox.warning(
                self, "모드 변경 불가",
                "자동매매 실행 중에는 전략 모드를 변경할 수 없습니다.\n"
                "먼저 자동매매를 정지하세요."
            )
            return
        
        new_mode = self.strategy_mode_combo.currentData()
        self.strategy_mode = new_mode
        
        if new_mode == "long_only":
            self.strategy_status_label.setText("🟢 Long Only 모드 활성")
            self.strategy_status_label.setStyleSheet("color: #28a745; font-size: 12px;")
            self.strategy_warning_label.hide()
        else:
            self.strategy_status_label.setText("🟡 Long + Short 모드 활성")
            self.strategy_status_label.setStyleSheet("color: #f39c12; font-size: 12px;")
            self.strategy_warning_label.show()
        
        self.strategy_mode_changed.emit(new_mode)
        
        mode_name = "Long Only" if new_mode == "long_only" else "Long + Short"
        self.add_log(f"📊 전략 모드 변경: {mode_name}", "설정")
    
    def _setup_connections(self):
        """시그널-슬롯 연결"""
        pass
    
    def _update_mode_indicator(self, mode: str):
        """모드 표시 업데이트"""
        if mode == "virtual":
            self.mode_indicator.setText("🟡 가상 모드")
            self.mode_indicator.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    border-radius: 8px;
                    padding: 15px;
                    color: #ffc107;
                    border: 2px solid #ffc107;
                }
            """)
        elif mode == "real":
            self.mode_indicator.setText("🟢 실제 모드")
            self.mode_indicator.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    border-radius: 8px;
                    padding: 15px;
                    color: #00ff88;
                    border: 2px solid #00ff88;
                }
            """)
        elif mode == "loading":
            self.mode_indicator.setText("⏳ 로딩 중...")
            self.mode_indicator.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    border-radius: 8px;
                    padding: 15px;
                    color: #17a2b8;
                }
            """)
        else:
            self.mode_indicator.setText("⏸️ 대기 중")
            self.mode_indicator.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    border-radius: 8px;
                    padding: 15px;
                    color: #888888;
                }
            """)
    
    def add_log(self, message: str, log_type: str = "정보"):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        color_map = {
            "정보": "#dcdcdc",
            "신호": "#ffc107",
            "거래": "#00ff88",
            "경고": "#fd7e14",
            "오류": "#dc3545",
            "설정": "#17a2b8"
        }
        color = color_map.get(log_type, "#dcdcdc")
        
        log_entry = f'<span style="color: #888888;">[{timestamp}]</span> '
        log_entry += f'<span style="color: {color};">[{log_type}]</span> '
        log_entry += f'<span style="color: #ffffff;">{message}</span>'
        
        self.log_text.append(log_entry)
        
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """로그 지우기"""
        self.log_text.clear()
        self.add_log("로그가 초기화되었습니다.", "정보")
    
    def start_auto_trading(self):
        """자동매매 시작"""
        reply = QMessageBox.question(
            self, "자동매매 시작",
            f"자동매매를 시작하시겠습니까?\n\n"
            f"전략 모드: {'Long Only' if self.strategy_mode == 'long_only' else 'Long + Short'}\n"
            f"가상 모드로 시작하며, 조건 충족 시 실제 거래로 전환됩니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            self.add_log("자동매매 시작 중...", "정보")
            self._update_mode_indicator("loading")
            
            mode_name = "Long Only" if self.strategy_mode == "long_only" else "Long + Short"
            self.add_log(f"📊 전략 모드: {mode_name}", "설정")
            
            self.add_log("📊 과거 데이터 로드 중...", "정보")
            
            if self.data_loader:
                df = self.data_loader.load_historical_candles_sync(
                    symbol="BTC-USDT-SWAP", timeframe="30m", days=7
                )
                
                if df is not None and len(df) > 0:
                    self.add_log(f"✅ {len(df)}개 캔들 로드 완료", "정보")
                    self.request_historical_data.emit()
                else:
                    self.add_log("⚠️ 과거 데이터 로드 실패 - 테스트 모드", "경고")
            else:
                self.add_log("⚠️ 데이터 로더 없음 - 테스트 모드", "경고")
            
            self.is_running = True
            self.is_real_mode = False
            self.virtual_capital = 10000.0
            self.virtual_trough = 10000.0
            
            self._update_mode_indicator("virtual")
            self.add_log("🟡 가상 모드로 자동매매 시작", "정보")
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            # ★ 신규: 전략 모드 콤보박스 비활성화
            self.strategy_mode_combo.setEnabled(False)
            
            if self.check_timer is None:
                self.check_timer = QTimer()
                self.check_timer.timeout.connect(self._check_conditions)
            self.check_timer.start(10000)
            
            self._check_conditions()
            if self.condition_monitor:
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
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            self.add_log("자동매매 정지 중...", "정보")
            
            if self.check_timer:
                self.check_timer.stop()
            
            self.is_running = False
            self._update_mode_indicator("stopped")
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
            # ★ 신규: 전략 모드 콤보박스 활성화
            self.strategy_mode_combo.setEnabled(True)
            
            if self.condition_monitor:
                self.condition_monitor.stop_monitoring()
            self.add_log("⏹️ 자동매매가 정지되었습니다.", "정보")
            self.trading_stopped.emit()
            
        except Exception as e:
            self.add_log(f"❌ 자동매매 정지 실패: {e}", "오류")
    
    def _reset_state(self):
        """상태 초기화"""
        self.is_running = False
        self.is_real_mode = False
        self._update_mode_indicator("stopped")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.strategy_mode_combo.setEnabled(True)
        
        if self.check_timer:
            self.check_timer.stop()
    
    def _check_conditions(self):
        """조건 체크"""
        if not self.is_running:
            return
        
        self.check_count += 1
        self.check_count_label.setText(str(self.check_count))
        
        if self.data_loader:
            data = self.data_loader.get_latest_strategy_data()
            if data and self.condition_monitor:
                self.condition_monitor.update_conditions(data)
                
                if self._evaluate_entry_conditions(data):
                    self.signal_count += 1
                    self.signal_count_label.setText(str(self.signal_count))
                    self._handle_signal(data)
    
    def _evaluate_entry_conditions(self, data: Dict[str, Any]) -> bool:
        """진입 조건 평가"""
        return False
    
    def _handle_signal(self, data: Dict[str, Any]):
        """신호 처리"""
        self.add_log("📡 진입 신호 감지!", "신호")
        
        if self.is_real_mode:
            self.add_log("실제 거래 실행 준비 중...", "거래")
            self.real_trade_count += 1
            self.real_trade_label.setText(str(self.real_trade_count))
        else:
            self.add_log("가상 거래 체결", "거래")
            self.virtual_trade_count += 1
            self.virtual_trade_label.setText(str(self.virtual_trade_count))
    
    def update_from_external(self, data: Dict[str, Any]):
        """외부에서 데이터 업데이트"""
        if self.is_running and self.condition_monitor:
            self.condition_monitor.update_conditions(data)
    
    # ========================================
    # ★ 신규: 전략 모드 관련 메서드
    # ========================================
    def get_strategy_mode(self) -> str:
        """현재 전략 모드 반환"""
        return self.strategy_mode
    
    def set_strategy_mode(self, mode: str):
        """전략 모드 설정"""
        if mode not in ["long_only", "long_short"]:
            return
        
        if self.is_running:
            return
        
        self.strategy_mode = mode
        
        index = 0 if mode == "long_only" else 1
        self.strategy_mode_combo.blockSignals(True)
        self.strategy_mode_combo.setCurrentIndex(index)
        self.strategy_mode_combo.blockSignals(False)
        
        if mode == "long_only":
            self.strategy_status_label.setText("🟢 Long Only 모드 활성")
            self.strategy_status_label.setStyleSheet("color: #28a745; font-size: 12px;")
            self.strategy_warning_label.hide()
        else:
            self.strategy_status_label.setText("🟡 Long + Short 모드 활성")
            self.strategy_status_label.setStyleSheet("color: #f39c12; font-size: 12px;")
            self.strategy_warning_label.show()
    
    # ========================================
    # ★ 신규: 잔고 업데이트 메서드
    # ========================================
    def update_balance(self, available_balance: float):
        """잔고 업데이트 - main_window에서 호출"""
        try:
            if hasattr(self, 'balance_value_label'):
                self.balance_value_label.setText(f"${available_balance:,.2f}")
            
            if self.is_running and self.is_real_mode:
                self.real_capital = available_balance
                self.real_capital_label.setText(f"${self.real_capital:,.2f}")
                
                if available_balance > self.real_peak:
                    self.real_peak = available_balance
                    
        except Exception as e:
            print(f"⚠️ 잔고 업데이트 오류: {e}")
    
    def update_capital_display(self):
        """자본 표시 업데이트"""
        self.virtual_capital_label.setText(f"${self.virtual_capital:,.2f}")
        self.real_capital_label.setText(f"${self.real_capital:,.2f}")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow, QWidget { background-color: #1e1e1e; color: #ffffff; }
        QGroupBox { font-weight: bold; border: 1px solid #3a3a3a; border-radius: 5px; margin-top: 10px; padding-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
    """)
    
    window = QMainWindow()
    window.setWindowTitle("Auto Trading Widget Test")
    window.setGeometry(100, 100, 1400, 800)
    
    widget = AutoTradingWidget()
    window.setCentralWidget(widget)
    
    window.show()
    sys.exit(app.exec_())
