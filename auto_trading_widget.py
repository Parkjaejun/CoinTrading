# gui/auto_trading_widget.py
"""
자동매매 제어 위젯
- 자동매매 시작/중지
- 실시간 상태 모니터링
- 전략 설정
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QGroupBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QCheckBox, QMessageBox, QFrame, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
import threading


class AutoTradingWidget(QWidget):
    """자동매매 제어 위젯"""
    
    # 시그널
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = None
        self.is_running = False
        
        # UI 초기화
        self.init_ui()
        
        # 시그널 연결
        self.log_signal.connect(self.append_log)
        self.status_signal.connect(self.update_status_display)
        
        # 상태 업데이트 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(5000)  # 5초마다
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 1. 상단: 제어 패널
        control_group = self.create_control_panel()
        layout.addWidget(control_group)
        
        # 2. 중단: 설정 패널
        settings_group = self.create_settings_panel()
        layout.addWidget(settings_group)
        
        # 3. 전략 상태 테이블
        strategy_group = self.create_strategy_table()
        layout.addWidget(strategy_group)
        
        # 4. 하단: 로그
        log_group = self.create_log_panel()
        layout.addWidget(log_group)
    
    def create_control_panel(self) -> QGroupBox:
        """제어 패널 생성"""
        group = QGroupBox("🎮 자동매매 제어")
        layout = QHBoxLayout(group)
        
        # 상태 표시
        self.status_label = QLabel("⚪ 대기 중")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 시작 버튼
        self.start_button = QPushButton("🚀 자동매매 시작")
        self.start_button.setMinimumSize(150, 50)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.start_button.clicked.connect(self.start_trading)
        layout.addWidget(self.start_button)
        
        # 중지 버튼
        self.stop_button = QPushButton("🛑 중지")
        self.stop_button.setMinimumSize(100, 50)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.stop_button.clicked.connect(self.stop_trading)
        layout.addWidget(self.stop_button)
        
        return group
    
    def create_settings_panel(self) -> QGroupBox:
        """설정 패널 생성"""
        group = QGroupBox("⚙️ 전략 설정")
        layout = QGridLayout(group)
        
        row = 0
        
        # 거래 심볼
        layout.addWidget(QLabel("거래 심볼:"), row, 0)
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems([
            "BTC-USDT-SWAP",
            "ETH-USDT-SWAP",
            "SOL-USDT-SWAP"
        ])
        layout.addWidget(self.symbol_combo, row, 1)
        
        # 초기 자본
        layout.addWidget(QLabel("초기 자본 ($):"), row, 2)
        self.capital_spin = QSpinBox()
        self.capital_spin.setRange(10, 100000)
        self.capital_spin.setValue(1000)
        self.capital_spin.setSingleStep(100)
        layout.addWidget(self.capital_spin, row, 3)
        
        row += 1
        
        # 롱 레버리지
        layout.addWidget(QLabel("롱 레버리지:"), row, 0)
        self.long_leverage_spin = QSpinBox()
        self.long_leverage_spin.setRange(1, 100)
        self.long_leverage_spin.setValue(10)
        layout.addWidget(self.long_leverage_spin, row, 1)
        
        # 롱 트레일링스탑
        layout.addWidget(QLabel("롱 트레일링스탑 (%):"), row, 2)
        self.long_trailing_spin = QDoubleSpinBox()
        self.long_trailing_spin.setRange(0.5, 50)
        self.long_trailing_spin.setValue(10)
        self.long_trailing_spin.setSingleStep(0.5)
        layout.addWidget(self.long_trailing_spin, row, 3)
        
        row += 1
        
        # 숏 레버리지
        layout.addWidget(QLabel("숏 레버리지:"), row, 0)
        self.short_leverage_spin = QSpinBox()
        self.short_leverage_spin.setRange(1, 100)
        self.short_leverage_spin.setValue(3)
        layout.addWidget(self.short_leverage_spin, row, 1)
        
        # 숏 트레일링스탑
        layout.addWidget(QLabel("숏 트레일링스탑 (%):"), row, 2)
        self.short_trailing_spin = QDoubleSpinBox()
        self.short_trailing_spin.setRange(0.5, 50)
        self.short_trailing_spin.setValue(2)
        self.short_trailing_spin.setSingleStep(0.5)
        layout.addWidget(self.short_trailing_spin, row, 3)
        
        row += 1
        
        # 체크 간격
        layout.addWidget(QLabel("체크 간격 (초):"), row, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 600)
        self.interval_spin.setValue(60)
        self.interval_spin.setSingleStep(10)
        layout.addWidget(self.interval_spin, row, 1)
        
        # 포지션 크기
        layout.addWidget(QLabel("포지션 크기 (%):"), row, 2)
        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(1, 100)
        self.position_size_spin.setValue(10)
        self.position_size_spin.setSingleStep(5)
        layout.addWidget(self.position_size_spin, row, 3)
        
        row += 1
        
        # 전략 활성화 체크박스
        self.long_enabled = QCheckBox("롱 전략 활성화")
        self.long_enabled.setChecked(True)
        layout.addWidget(self.long_enabled, row, 0, 1, 2)
        
        self.short_enabled = QCheckBox("숏 전략 활성화")
        self.short_enabled.setChecked(True)
        layout.addWidget(self.short_enabled, row, 2, 1, 2)
        
        return group
    
    def create_strategy_table(self) -> QGroupBox:
        """전략 상태 테이블 생성"""
        group = QGroupBox("📊 전략 상태")
        layout = QVBoxLayout(group)
        
        self.strategy_table = QTableWidget()
        self.strategy_table.setColumnCount(8)
        self.strategy_table.setHorizontalHeaderLabels([
            "전략", "모드", "상태", "자본", "진입가", "손익", "승률", "거래수"
        ])
        self.strategy_table.horizontalHeader().setStretchLastSection(True)
        self.strategy_table.setAlternatingRowColors(True)
        self.strategy_table.setMaximumHeight(150)
        
        layout.addWidget(self.strategy_table)
        
        # 실시간 통계
        stats_layout = QHBoxLayout()
        
        self.runtime_label = QLabel("실행 시간: --:--:--")
        stats_layout.addWidget(self.runtime_label)
        
        self.signals_label = QLabel("총 신호: 0")
        stats_layout.addWidget(self.signals_label)
        
        self.trades_label = QLabel("실행 거래: 0")
        stats_layout.addWidget(self.trades_label)
        
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        return group
    
    def create_log_panel(self) -> QGroupBox:
        """로그 패널 생성"""
        group = QGroupBox("📜 로그")
        layout = QVBoxLayout(group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #dcdcdc;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # 로그 제어 버튼
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("로그 지우기")
        clear_btn.clicked.connect(self.clear_log)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        return group
    
    def get_config(self) -> dict:
        """현재 설정 반환"""
        return {
            'symbols': [self.symbol_combo.currentText()],
            'initial_capital': self.capital_spin.value(),
            'check_interval': self.interval_spin.value(),
            'long_leverage': self.long_leverage_spin.value(),
            'long_trailing_stop': self.long_trailing_spin.value() / 100,
            'short_leverage': self.short_leverage_spin.value(),
            'short_trailing_stop': self.short_trailing_spin.value() / 100,
            'position_size': self.position_size_spin.value() / 100,
            'long_enabled': self.long_enabled.isChecked(),
            'short_enabled': self.short_enabled.isChecked(),
        }
    
    def start_trading(self):
        """자동매매 시작"""
        # 확인 다이얼로그
        reply = QMessageBox.warning(
            self,
            "⚠️ 자동매매 시작",
            "실제 자금으로 자동매매를 시작합니다.\n\n"
            "계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 엔진 임포트 및 생성
            from trading_engine import TradingEngine
            
            config = self.get_config()
            self.append_log(f"⚙️ 설정: {config}")
            
            self.engine = TradingEngine(config)
            
            # 콜백 설정
            self.engine.on_signal_callback = self.on_signal
            self.engine.on_trade_callback = self.on_trade
            
            # 시작
            if self.engine.start():
                self.is_running = True
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.status_label.setText("🟢 실행 중")
                self.status_label.setStyleSheet("color: #27ae60;")
                self.append_log("🚀 자동매매 시작됨!")
            else:
                self.append_log("❌ 엔진 시작 실패")
                QMessageBox.critical(self, "오류", "자동매매 엔진 시작에 실패했습니다.")
                
        except Exception as e:
            self.append_log(f"❌ 오류: {e}")
            QMessageBox.critical(self, "오류", f"자동매매 시작 오류:\n{e}")
    
    def stop_trading(self):
        """자동매매 중지"""
        if self.engine:
            # 별도 스레드에서 중지 (블로킹 방지)
            def stop_engine():
                self.engine.stop()
                self.is_running = False
            
            threading.Thread(target=stop_engine, daemon=True).start()
        
        self.is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("⚪ 중지됨")
        self.status_label.setStyleSheet("color: #7f8c8d;")
        self.append_log("🛑 자동매매 중지됨")
    
    def on_signal(self, signal: dict):
        """신호 콜백"""
        action = signal.get('action', 'unknown')
        strategy = signal.get('strategy_type', 'unknown')
        symbol = signal.get('symbol', 'unknown')
        is_real = "실제" if signal.get('is_real') else "가상"
        
        msg = f"📡 [{is_real}] {strategy} {action}: {symbol}"
        self.log_signal.emit(msg)
    
    def on_trade(self, signal: dict, success: bool):
        """거래 콜백"""
        status = "✅ 성공" if success else "❌ 실패"
        action = signal.get('action', 'unknown')
        
        if action == 'enter':
            msg = f"💰 진입 {status}: ${signal.get('price', 0):,.2f}"
        else:
            pnl = signal.get('pnl', 0)
            msg = f"💰 청산 {status}: 손익 ${pnl:.2f}"
        
        self.log_signal.emit(msg)
    
    def refresh_status(self):
        """상태 새로고침"""
        if not self.engine or not self.is_running:
            return
        
        try:
            status = self.engine.get_status()
            self.status_signal.emit(status)
        except Exception as e:
            pass
    
    def update_status_display(self, status: dict):
        """상태 표시 업데이트"""
        # 통계 업데이트
        if status.get('runtime'):
            self.runtime_label.setText(f"실행 시간: {status['runtime']}")
        
        self.signals_label.setText(f"총 신호: {status.get('total_signals', 0)}")
        self.trades_label.setText(f"실행 거래: {status.get('executed_trades', 0)}")
        
        # 전략 테이블 업데이트
        strategies = status.get('strategies', {})
        self.strategy_table.setRowCount(len(strategies))
        
        for i, (key, strat) in enumerate(strategies.items()):
            self.strategy_table.setItem(i, 0, QTableWidgetItem(key))
            
            mode = "🟢실제" if strat.get('is_real_mode') else "🟡가상"
            self.strategy_table.setItem(i, 1, QTableWidgetItem(mode))
            
            pos_status = "📈보유" if strat.get('is_position_open') else "⏳대기"
            self.strategy_table.setItem(i, 2, QTableWidgetItem(pos_status))
            
            capital = strat.get('real_capital', 0)
            self.strategy_table.setItem(i, 3, QTableWidgetItem(f"${capital:.2f}"))
            
            entry = strat.get('entry_price', 0)
            self.strategy_table.setItem(i, 4, QTableWidgetItem(f"${entry:,.2f}" if entry > 0 else "-"))
            
            pnl = strat.get('total_pnl', 0)
            pnl_item = QTableWidgetItem(f"${pnl:+.2f}")
            pnl_item.setForeground(QColor("#27ae60" if pnl >= 0 else "#e74c3c"))
            self.strategy_table.setItem(i, 5, pnl_item)
            
            win_rate = strat.get('win_rate', 0)
            self.strategy_table.setItem(i, 6, QTableWidgetItem(f"{win_rate:.1f}%"))
            
            trades = strat.get('total_trades', 0)
            self.strategy_table.setItem(i, 7, QTableWidgetItem(str(trades)))
    
    def append_log(self, message: str):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # 스크롤 맨 아래로
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """로그 지우기"""
        self.log_text.clear()


# 테스트
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 다크 테마
    app.setStyleSheet("""
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QGroupBox {
            border: 1px solid #3a3a3a;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            color: #ffffff;
            subcontrol-origin: margin;
            left: 10px;
        }
    """)
    
    widget = AutoTradingWidget()
    widget.setWindowTitle("자동매매 테스트")
    widget.resize(800, 700)
    widget.show()
    
    sys.exit(app.exec_())
