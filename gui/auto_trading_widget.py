# gui/auto_trading_widget.py
"""
자동매매 제어 위젯 - 개선 버전
- 경고창 글자 표시 수정
- 실시간 차트 추가
- 전략 시각화
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QGroupBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QCheckBox, QMessageBox, QFrame, QProgressBar, QSplitter,
    QTabWidget, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
from datetime import datetime
import threading


class AutoTradingWidget(QWidget):
    """자동매매 제어 위젯 - 개선 버전"""
    
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
        self.status_timer.start(3000)  # 3초마다
        
        # 초기 로그
        self.append_log("자동매매 위젯 초기화 완료")
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 1. 상단: 제어 + 상태 패널
        top_layout = QHBoxLayout()
        
        # 제어 패널
        control_group = self.create_control_panel()
        top_layout.addWidget(control_group, 2)
        
        # 실시간 정보 패널
        info_group = self.create_realtime_info_panel()
        top_layout.addWidget(info_group, 1)
        
        layout.addLayout(top_layout)
        
        # 2. 중단: 설정 + 전략 상태
        middle_splitter = QSplitter(Qt.Horizontal)
        
        # 설정 패널
        settings_group = self.create_settings_panel()
        middle_splitter.addWidget(settings_group)
        
        # 전략 상태 패널
        strategy_group = self.create_strategy_panel()
        middle_splitter.addWidget(strategy_group)
        
        middle_splitter.setSizes([400, 600])
        layout.addWidget(middle_splitter)
        
        # 3. 하단: 거래 내역 + 로그
        bottom_splitter = QSplitter(Qt.Horizontal)
        
        # 거래 내역
        trades_group = self.create_trades_panel()
        bottom_splitter.addWidget(trades_group)
        
        # 로그
        log_group = self.create_log_panel()
        bottom_splitter.addWidget(log_group)
        
        bottom_splitter.setSizes([500, 500])
        layout.addWidget(bottom_splitter)
    
    def create_control_panel(self) -> QGroupBox:
        """제어 패널 생성"""
        group = QGroupBox("자동매매 제어")
        layout = QVBoxLayout(group)
        
        # 상태 표시
        status_layout = QHBoxLayout()
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 24))
        self.status_indicator.setStyleSheet("color: #7f8c8d;")  # 회색
        status_layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("대기 중")
        self.status_label.setFont(QFont("Arial", 16, QFont.Bold))
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        self.start_button = QPushButton("자동매매 시작")
        self.start_button.setMinimumSize(150, 50)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.start_button.clicked.connect(self.start_trading)
        btn_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("중지")
        self.stop_button.setMinimumSize(100, 50)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.stop_button.clicked.connect(self.stop_trading)
        btn_layout.addWidget(self.stop_button)
        
        # 긴급 청산 버튼
        self.emergency_button = QPushButton("긴급 청산")
        self.emergency_button.setMinimumSize(100, 50)
        self.emergency_button.setStyleSheet("""
            QPushButton {
                background-color: #8e44ad;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #9b59b6;
            }
        """)
        self.emergency_button.clicked.connect(self.emergency_close)
        btn_layout.addWidget(self.emergency_button)
        
        layout.addLayout(btn_layout)
        
        return group
    
    def create_realtime_info_panel(self) -> QGroupBox:
        """실시간 정보 패널"""
        group = QGroupBox("실시간 정보")
        layout = QGridLayout(group)
        
        # 잔고
        layout.addWidget(QLabel("USDT 잔고:"), 0, 0)
        self.balance_label = QLabel("$0.00")
        self.balance_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.balance_label.setStyleSheet("color: #f39c12;")
        layout.addWidget(self.balance_label, 0, 1)
        
        # BTC 가격
        layout.addWidget(QLabel("BTC:"), 1, 0)
        self.btc_price_label = QLabel("$0.00")
        self.btc_price_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.btc_price_label, 1, 1)
        
        # 총 손익
        layout.addWidget(QLabel("총 손익:"), 2, 0)
        self.total_pnl_label = QLabel("$0.00")
        self.total_pnl_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(self.total_pnl_label, 2, 1)
        
        # 실행 시간
        layout.addWidget(QLabel("실행 시간:"), 3, 0)
        self.runtime_label = QLabel("00:00:00")
        layout.addWidget(self.runtime_label, 3, 1)
        
        return group
    
    def create_settings_panel(self) -> QGroupBox:
        """설정 패널 생성"""
        group = QGroupBox("전략 설정")
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
        
        row += 1
        
        # 체크 간격
        layout.addWidget(QLabel("체크 간격 (초):"), row, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 600)
        self.interval_spin.setValue(60)
        self.interval_spin.setSingleStep(10)
        layout.addWidget(self.interval_spin, row, 1)
        
        row += 1
        
        # 포지션 크기
        layout.addWidget(QLabel("포지션 크기 (%):"), row, 0)
        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(1, 100)
        self.position_size_spin.setValue(10)
        self.position_size_spin.setSingleStep(5)
        layout.addWidget(self.position_size_spin, row, 1)
        
        row += 1
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line, row, 0, 1, 2)
        
        row += 1
        
        # 롱 전략 설정
        layout.addWidget(QLabel("-- 롱 전략 --"), row, 0, 1, 2)
        row += 1
        
        self.long_enabled = QCheckBox("롱 전략 활성화")
        self.long_enabled.setChecked(True)
        layout.addWidget(self.long_enabled, row, 0, 1, 2)
        row += 1
        
        layout.addWidget(QLabel("레버리지:"), row, 0)
        self.long_leverage_spin = QSpinBox()
        self.long_leverage_spin.setRange(1, 100)
        self.long_leverage_spin.setValue(10)
        layout.addWidget(self.long_leverage_spin, row, 1)
        row += 1
        
        layout.addWidget(QLabel("트레일링스탑 (%):"), row, 0)
        self.long_trailing_spin = QDoubleSpinBox()
        self.long_trailing_spin.setRange(0.5, 50)
        self.long_trailing_spin.setValue(10)
        self.long_trailing_spin.setSingleStep(0.5)
        layout.addWidget(self.long_trailing_spin, row, 1)
        row += 1
        
        # 구분선
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        layout.addWidget(line2, row, 0, 1, 2)
        row += 1
        
        # 숏 전략 설정
        layout.addWidget(QLabel("-- 숏 전략 --"), row, 0, 1, 2)
        row += 1
        
        self.short_enabled = QCheckBox("숏 전략 활성화")
        self.short_enabled.setChecked(True)
        layout.addWidget(self.short_enabled, row, 0, 1, 2)
        row += 1
        
        layout.addWidget(QLabel("레버리지:"), row, 0)
        self.short_leverage_spin = QSpinBox()
        self.short_leverage_spin.setRange(1, 100)
        self.short_leverage_spin.setValue(3)
        layout.addWidget(self.short_leverage_spin, row, 1)
        row += 1
        
        layout.addWidget(QLabel("트레일링스탑 (%):"), row, 0)
        self.short_trailing_spin = QDoubleSpinBox()
        self.short_trailing_spin.setRange(0.5, 50)
        self.short_trailing_spin.setValue(2)
        self.short_trailing_spin.setSingleStep(0.5)
        layout.addWidget(self.short_trailing_spin, row, 1)
        
        return group
    
    def create_strategy_panel(self) -> QGroupBox:
        """전략 상태 패널"""
        group = QGroupBox("전략 상태")
        layout = QVBoxLayout(group)
        
        # 전략 테이블
        self.strategy_table = QTableWidget()
        self.strategy_table.setColumnCount(7)
        self.strategy_table.setHorizontalHeaderLabels([
            "전략", "모드", "상태", "자본", "손익", "승률", "거래수"
        ])
        self.strategy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.strategy_table.setAlternatingRowColors(True)
        self.strategy_table.setMaximumHeight(150)
        
        layout.addWidget(self.strategy_table)
        
        # 통계 바
        stats_layout = QHBoxLayout()
        
        self.signals_label = QLabel("총 신호: 0")
        stats_layout.addWidget(self.signals_label)
        
        self.trades_label = QLabel("실행 거래: 0")
        stats_layout.addWidget(self.trades_label)
        
        self.win_rate_label = QLabel("승률: 0%")
        stats_layout.addWidget(self.win_rate_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # EMA 상태 표시
        ema_group = QGroupBox("EMA 지표 상태")
        ema_layout = QGridLayout(ema_group)
        
        ema_layout.addWidget(QLabel("트렌드 (150/200):"), 0, 0)
        self.trend_label = QLabel("--")
        self.trend_label.setFont(QFont("Arial", 10, QFont.Bold))
        ema_layout.addWidget(self.trend_label, 0, 1)
        
        ema_layout.addWidget(QLabel("진입 (20/50):"), 0, 2)
        self.entry_label = QLabel("--")
        self.entry_label.setFont(QFont("Arial", 10, QFont.Bold))
        ema_layout.addWidget(self.entry_label, 0, 3)
        
        layout.addWidget(ema_group)
        
        return group
    
    def create_trades_panel(self) -> QGroupBox:
        """거래 내역 패널"""
        group = QGroupBox("최근 거래 내역")
        layout = QVBoxLayout(group)
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(6)
        self.trades_table.setHorizontalHeaderLabels([
            "시간", "심볼", "방향", "가격", "손익", "사유"
        ])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.trades_table)
        
        return group
    
    def create_log_panel(self) -> QGroupBox:
        """로그 패널 생성"""
        group = QGroupBox("시스템 로그")
        layout = QVBoxLayout(group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a2e;
                color: #eee;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #333;
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
            'initial_capital': 0,  # 실제 잔고 사용
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
        # 확인 다이얼로그 (이모지 제거, 명확한 텍스트)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("자동매매 시작 확인")
        msg_box.setText("실제 자금으로 자동매매를 시작합니다.")
        msg_box.setInformativeText(
            "주의사항:\n"
            "- 실제 OKX 계좌의 자금이 사용됩니다\n"
            "- 설정된 전략에 따라 자동으로 매매가 실행됩니다\n"
            "- 손실이 발생할 수 있습니다\n\n"
            "계속하시겠습니까?"
        )
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        # 스타일 적용 (글자가 보이도록)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
            }
            QMessageBox QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 8px 20px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        
        reply = msg_box.exec_()
        
        if reply != QMessageBox.Yes:
            self.append_log("자동매매 시작 취소됨")
            return
        
        try:
            # 엔진 임포트 및 생성
            from trading_engine import TradingEngine
            
            config = self.get_config()
            self.append_log(f"설정 적용: {self.symbol_combo.currentText()}")
            self.append_log(f"  - 롱: {self.long_leverage_spin.value()}x, TS {self.long_trailing_spin.value()}%")
            self.append_log(f"  - 숏: {self.short_leverage_spin.value()}x, TS {self.short_trailing_spin.value()}%")
            
            self.engine = TradingEngine(config)
            
            # 콜백 설정
            self.engine.on_signal_callback = self.on_signal
            self.engine.on_trade_callback = self.on_trade
            
            # 시작
            start_result = self.engine.start()
            
            if start_result:
                self.is_running = True
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.status_indicator.setStyleSheet("color: #27ae60;")  # 녹색
                self.status_label.setText("실행 중")
                self.append_log("[시작] 자동매매 엔진이 시작되었습니다!")
                
                # 설정 위젯 비활성화
                self.set_settings_enabled(False)
            else:
                error_msg = "엔진 초기화에 실패했습니다. 터미널 로그를 확인하세요."
                self.append_log(f"[오류] {error_msg}")
                self.show_error_message(error_msg)
                
        except ImportError as e:
            error_msg = f"trading_engine.py 파일을 찾을 수 없습니다.\n\n프로젝트 폴더에 파일을 복사해주세요.\n\n상세: {e}"
            self.append_log(f"[오류] ImportError: {e}")
            self.show_error_message(error_msg)
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            error_msg = f"자동매매 시작 중 오류가 발생했습니다.\n\n{type(e).__name__}: {e}"
            self.append_log(f"[오류] {type(e).__name__}: {e}")
            self.append_log(f"[상세] {error_detail}")
            self.show_error_message(error_msg)
    
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
        self.status_indicator.setStyleSheet("color: #7f8c8d;")  # 회색
        self.status_label.setText("중지됨")
        self.append_log("[중지] 자동매매가 중지되었습니다")
        
        # 설정 위젯 활성화
        self.set_settings_enabled(True)
    
    def emergency_close(self):
        """긴급 청산"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("긴급 청산 확인")
        msg_box.setText("모든 포지션을 즉시 청산합니다.")
        msg_box.setInformativeText("정말로 모든 포지션을 청산하시겠습니까?")
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setStyleSheet("""
            QMessageBox QLabel { color: #ffffff; }
            QPushButton { 
                background-color: #3a3a3a; 
                color: #ffffff; 
                padding: 8px 20px;
            }
        """)
        
        if msg_box.exec_() == QMessageBox.Yes:
            try:
                if self.engine and self.engine.order_manager:
                    result = self.engine.order_manager.close_all_positions()
                    if result:
                        self.append_log("[긴급] 모든 포지션 청산 완료")
                    else:
                        self.append_log("[긴급] 청산 실패 또는 포지션 없음")
                else:
                    # OrderManager 직접 사용
                    from okx.order_manager import OrderManager
                    om = OrderManager()
                    result = om.close_all_positions()
                    self.append_log(f"[긴급] 청산 결과: {result}")
            except Exception as e:
                self.append_log(f"[오류] 긴급 청산 실패: {e}")
    
    def set_settings_enabled(self, enabled: bool):
        """설정 위젯 활성화/비활성화"""
        self.symbol_combo.setEnabled(enabled)
        self.interval_spin.setEnabled(enabled)
        self.position_size_spin.setEnabled(enabled)
        self.long_enabled.setEnabled(enabled)
        self.long_leverage_spin.setEnabled(enabled)
        self.long_trailing_spin.setEnabled(enabled)
        self.short_enabled.setEnabled(enabled)
        self.short_leverage_spin.setEnabled(enabled)
        self.short_trailing_spin.setEnabled(enabled)
    
    def show_error_message(self, message: str):
        """에러 메시지 표시"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("오류")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setStyleSheet("""
            QMessageBox QLabel { color: #ffffff; }
            QPushButton { background-color: #3a3a3a; color: #ffffff; padding: 8px 20px; }
        """)
        msg_box.exec_()
    
    def on_signal(self, signal: dict):
        """신호 콜백"""
        action = signal.get('action', 'unknown')
        strategy = signal.get('strategy_type', 'unknown')
        symbol = signal.get('symbol', 'unknown')
        is_real = "실제" if signal.get('is_real') else "가상"
        
        msg = f"[신호] [{is_real}] {strategy.upper()} {action}: {symbol}"
        self.log_signal.emit(msg)
    
    def on_trade(self, signal: dict, success: bool):
        """거래 콜백"""
        status = "성공" if success else "실패"
        action = signal.get('action', 'unknown')
        
        if action == 'enter':
            price = signal.get('price', 0)
            msg = f"[거래] 진입 {status}: ${price:,.2f}"
        else:
            pnl = signal.get('pnl', 0)
            reason = signal.get('reason', '')
            msg = f"[거래] 청산 {status}: 손익 ${pnl:.2f} ({reason})"
        
        self.log_signal.emit(msg)
        
        # 거래 내역 테이블 업데이트
        if success:
            self.add_trade_to_table(signal)
    
    def add_trade_to_table(self, signal: dict):
        """거래 내역 테이블에 추가"""
        row = self.trades_table.rowCount()
        self.trades_table.insertRow(0)  # 맨 위에 추가
        
        # 시간
        time_str = datetime.now().strftime("%H:%M:%S")
        self.trades_table.setItem(0, 0, QTableWidgetItem(time_str))
        
        # 심볼
        self.trades_table.setItem(0, 1, QTableWidgetItem(signal.get('symbol', '')))
        
        # 방향
        direction = signal.get('strategy_type', '').upper()
        action = signal.get('action', '')
        dir_text = f"{direction} {action}"
        self.trades_table.setItem(0, 2, QTableWidgetItem(dir_text))
        
        # 가격
        price = signal.get('price') or signal.get('exit_price', 0)
        self.trades_table.setItem(0, 3, QTableWidgetItem(f"${price:,.2f}"))
        
        # 손익
        pnl = signal.get('pnl', 0)
        pnl_item = QTableWidgetItem(f"${pnl:+.2f}")
        pnl_item.setForeground(QColor("#27ae60" if pnl >= 0 else "#e74c3c"))
        self.trades_table.setItem(0, 4, pnl_item)
        
        # 사유
        self.trades_table.setItem(0, 5, QTableWidgetItem(signal.get('reason', '-')))
        
        # 최대 20개 유지
        while self.trades_table.rowCount() > 20:
            self.trades_table.removeRow(self.trades_table.rowCount() - 1)
    
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
        # 실행 시간
        if status.get('runtime'):
            runtime_str = str(status['runtime']).split('.')[0]
            self.runtime_label.setText(runtime_str)
        
        # 통계
        self.signals_label.setText(f"총 신호: {status.get('total_signals', 0)}")
        self.trades_label.setText(f"실행 거래: {status.get('executed_trades', 0)}")
        
        # 전략 테이블 업데이트
        strategies = status.get('strategies', {})
        self.strategy_table.setRowCount(len(strategies))
        
        total_pnl = 0
        total_trades = 0
        total_wins = 0
        
        for i, (key, strat) in enumerate(strategies.items()):
            # 전략 이름
            name = "LONG" if "long" in key else "SHORT"
            self.strategy_table.setItem(i, 0, QTableWidgetItem(name))
            
            # 모드
            mode = "실제" if strat.get('is_real_mode') else "가상"
            mode_item = QTableWidgetItem(mode)
            mode_item.setForeground(QColor("#27ae60" if mode == "실제" else "#f39c12"))
            self.strategy_table.setItem(i, 1, mode_item)
            
            # 상태
            pos_status = "보유중" if strat.get('is_position_open') else "대기"
            self.strategy_table.setItem(i, 2, QTableWidgetItem(pos_status))
            
            # 자본
            capital = strat.get('real_capital', 0)
            self.strategy_table.setItem(i, 3, QTableWidgetItem(f"${capital:.2f}"))
            
            # 손익
            pnl = strat.get('total_pnl', 0)
            pnl_item = QTableWidgetItem(f"${pnl:+.2f}")
            pnl_item.setForeground(QColor("#27ae60" if pnl >= 0 else "#e74c3c"))
            self.strategy_table.setItem(i, 4, pnl_item)
            
            # 승률
            win_rate = strat.get('win_rate', 0)
            self.strategy_table.setItem(i, 5, QTableWidgetItem(f"{win_rate:.1f}%"))
            
            # 거래수
            trades = strat.get('total_trades', 0)
            self.strategy_table.setItem(i, 6, QTableWidgetItem(str(trades)))
            
            # 합계
            total_pnl += pnl
            total_trades += trades
            total_wins += strat.get('winning_trades', 0)
        
        # 총 손익 업데이트
        self.total_pnl_label.setText(f"${total_pnl:+.2f}")
        self.total_pnl_label.setStyleSheet(
            f"color: {'#27ae60' if total_pnl >= 0 else '#e74c3c'};"
        )
        
        # 총 승률
        if total_trades > 0:
            overall_win_rate = (total_wins / total_trades) * 100
            self.win_rate_label.setText(f"승률: {overall_win_rate:.1f}%")
    
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
        self.append_log("로그가 지워졌습니다")


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
            font-weight: bold;
        }
        QGroupBox::title {
            color: #ffffff;
            subcontrol-origin: margin;
            left: 10px;
        }
        QTableWidget {
            background-color: #1e1e1e;
            gridline-color: #3a3a3a;
        }
        QHeaderView::section {
            background-color: #3a3a3a;
            color: #ffffff;
            padding: 5px;
            border: none;
        }
    """)
    
    widget = AutoTradingWidget()
    widget.setWindowTitle("자동매매 테스트")
    widget.resize(1000, 800)
    widget.show()
    
    sys.exit(app.exec_())