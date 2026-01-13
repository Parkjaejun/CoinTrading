# gui/real_trade_test_widget.py
"""
실제 거래 테스트 위젯
시뮬레이션이 아닌 실제 거래를 테스트하기 위한 GUI 컴포넌트
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
    QTextEdit, QGroupBox, QComboBox, QProgressBar,
    QMessageBox, QFrame, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
import json


class OrderExecutionThread(QThread):
    """주문 실행 스레드"""
    progress = pyqtSignal(str)
    result = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    
    def __init__(self, order_manager, action: str, params: dict):
        super().__init__()
        self.order_manager = order_manager
        self.action = action
        self.params = params
    
    def run(self):
        try:
            if self.action == 'test_buy':
                result = self.order_manager.test_buy_order(
                    inst_id=self.params.get('inst_id', 'BTC-USDT-SWAP'),
                    usdt_amount=self.params.get('usdt_amount', 10),
                    leverage=self.params.get('leverage', 1)
                )
            elif self.action == 'close_position':
                result = self.order_manager.test_close_position(
                    inst_id=self.params.get('inst_id', 'BTC-USDT-SWAP'),
                    pos_side=self.params.get('pos_side', 'long')
                )
            elif self.action == 'get_min_info':
                result = self.order_manager.get_min_order_info(
                    inst_id=self.params.get('inst_id', 'BTC-USDT-SWAP')
                )
            else:
                result = {'success': False, 'error': f'Unknown action: {self.action}'}
            
            self.result.emit(result)
        except Exception as e:
            self.result.emit({'success': False, 'error': str(e)})
        finally:
            self.finished_signal.emit()


class RealTradeTestWidget(QWidget):
    """실제 거래 테스트 위젯"""
    
    def __init__(self, order_manager=None):
        super().__init__()
        self.order_manager = order_manager
        self.current_positions = []
        self.min_order_info = {}
        self.execution_thread = None
        
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 상단 경고 배너
        self.create_warning_banner(layout)
        
        # 메인 컨텐츠 영역
        content_layout = QHBoxLayout()
        
        # 좌측: 거래 설정 및 실행
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel, 1)
        
        # 우측: 결과 및 로그
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel, 1)
        
        layout.addLayout(content_layout)
        
        # 하단: 포지션 테이블
        positions_group = self.create_positions_panel()
        layout.addWidget(positions_group)
    
    def create_warning_banner(self, layout):
        """경고 배너 생성"""
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: #ff4444;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
        """)
        warning_layout = QHBoxLayout(warning_frame)
        
        warning_icon = QLabel("⚠️")
        warning_icon.setFont(QFont('Arial', 20))
        warning_layout.addWidget(warning_icon)
        
        warning_text = QLabel(
            "실제 거래 테스트 - 이 기능은 실제 자금을 사용합니다! "
            "테스트 전 잔고와 설정을 반드시 확인하세요."
        )
        warning_text.setFont(QFont('Arial', 11))
        warning_text.setWordWrap(True)
        warning_layout.addWidget(warning_text, 1)
        
        layout.addWidget(warning_frame)
    
    def create_left_panel(self):
        """좌측 패널 생성 (설정 및 실행)"""
        panel = QGroupBox("📊 거래 테스트 설정")
        panel.setFont(QFont('Arial', 10, QFont.Bold))
        layout = QVBoxLayout(panel)
        
        # 상품 선택
        symbol_layout = QHBoxLayout()
        symbol_layout.addWidget(QLabel("거래 상품:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(['BTC-USDT-SWAP', 'ETH-USDT-SWAP'])
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        symbol_layout.addWidget(self.symbol_combo)
        layout.addLayout(symbol_layout)
        
        # 최소 주문 정보 표시
        self.min_info_frame = QFrame()
        self.min_info_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                color: #aaa;
            }
        """)
        min_info_layout = QGridLayout(self.min_info_frame)
        
        min_info_layout.addWidget(QLabel("현재가:"), 0, 0)
        self.current_price_label = QLabel("-")
        self.current_price_label.setStyleSheet("color: #00ff88; font-weight: bold;")
        min_info_layout.addWidget(self.current_price_label, 0, 1)
        
        min_info_layout.addWidget(QLabel("최소 주문금액:"), 1, 0)
        self.min_notional_label = QLabel("-")
        self.min_notional_label.setStyleSheet("color: #ffaa00;")
        min_info_layout.addWidget(self.min_notional_label, 1, 1)
        
        min_info_layout.addWidget(QLabel("권장 테스트금액:"), 2, 0)
        self.recommended_label = QLabel("-")
        self.recommended_label.setStyleSheet("color: #00aaff;")
        min_info_layout.addWidget(self.recommended_label, 2, 1)
        
        layout.addWidget(self.min_info_frame)
        
        # 주문 정보 새로고침 버튼
        refresh_btn = QPushButton("🔄 주문 정보 새로고침")
        refresh_btn.clicked.connect(self.refresh_min_order_info)
        layout.addWidget(refresh_btn)
        
        layout.addWidget(QLabel(""))  # 스페이서
        
        # 주문 금액 설정
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("주문 금액 (USDT):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(5, 1000)
        self.amount_spin.setValue(10)
        self.amount_spin.setSuffix(" USDT")
        self.amount_spin.setDecimals(2)
        amount_layout.addWidget(self.amount_spin)
        layout.addLayout(amount_layout)
        
        # 빠른 금액 선택 버튼
        quick_amounts_layout = QHBoxLayout()
        for amount in [5, 10, 20, 50]:
            btn = QPushButton(f"${amount}")
            btn.setMaximumWidth(60)
            btn.clicked.connect(lambda checked, a=amount: self.amount_spin.setValue(a))
            quick_amounts_layout.addWidget(btn)
        layout.addLayout(quick_amounts_layout)
        
        # 레버리지 설정
        leverage_layout = QHBoxLayout()
        leverage_layout.addWidget(QLabel("레버리지:"))
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 10)
        self.leverage_spin.setValue(1)
        self.leverage_spin.setSuffix("x")
        leverage_layout.addWidget(self.leverage_spin)
        layout.addLayout(leverage_layout)
        
        # 실제 거래 확인 체크박스
        self.confirm_checkbox = QCheckBox("실제 자금 사용에 동의합니다")
        self.confirm_checkbox.setStyleSheet("color: #ff8800;")
        self.confirm_checkbox.stateChanged.connect(self.update_button_state)
        layout.addWidget(self.confirm_checkbox)
        
        layout.addWidget(QLabel(""))  # 스페이서
        
        # 실행 버튼들
        buttons_layout = QVBoxLayout()
        
        # 구매 테스트 버튼
        self.buy_test_btn = QPushButton("🛒 실제 구매 테스트")
        self.buy_test_btn.setFont(QFont('Arial', 12, QFont.Bold))
        self.buy_test_btn.setMinimumHeight(50)
        self.buy_test_btn.setStyleSheet("""
            QPushButton {
                background-color: #006400;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #008000;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #666;
            }
        """)
        self.buy_test_btn.setEnabled(False)
        self.buy_test_btn.clicked.connect(self.execute_buy_test)
        buttons_layout.addWidget(self.buy_test_btn)
        
        # 청산 버튼
        self.close_btn = QPushButton("📤 포지션 청산")
        self.close_btn.setFont(QFont('Arial', 11))
        self.close_btn.setMinimumHeight(40)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B0000;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #B22222;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #666;
            }
        """)
        self.close_btn.clicked.connect(self.execute_close_position)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
        # 진행 상태
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        return panel
    
    def create_right_panel(self):
        """우측 패널 생성 (결과 및 로그)"""
        panel = QGroupBox("📝 실행 결과 및 로그")
        panel.setFont(QFont('Arial', 10, QFont.Bold))
        layout = QVBoxLayout(panel)
        
        # 잔고 정보
        balance_frame = QFrame()
        balance_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border: 1px solid #333;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        balance_layout = QHBoxLayout(balance_frame)
        
        balance_layout.addWidget(QLabel("💰 USDT 잔고:"))
        self.balance_label = QLabel("-")
        self.balance_label.setStyleSheet("color: #00ff88; font-size: 16px; font-weight: bold;")
        balance_layout.addWidget(self.balance_label)
        balance_layout.addStretch()
        
        refresh_balance_btn = QPushButton("새로고침")
        refresh_balance_btn.setMaximumWidth(80)
        refresh_balance_btn.clicked.connect(self.refresh_balance)
        balance_layout.addWidget(refresh_balance_btn)
        
        layout.addWidget(balance_frame)
        
        # 결과 로그
        self.result_log = QTextEdit()
        self.result_log.setReadOnly(True)
        self.result_log.setFont(QFont('Consolas', 9))
        self.result_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.result_log)
        
        # 로그 클리어 버튼
        clear_btn = QPushButton("로그 클리어")
        clear_btn.clicked.connect(self.result_log.clear)
        layout.addWidget(clear_btn)
        
        return panel
    
    def create_positions_panel(self):
        """포지션 테이블 패널"""
        panel = QGroupBox("📊 현재 포지션")
        panel.setFont(QFont('Arial', 10, QFont.Bold))
        layout = QVBoxLayout(panel)
        
        # 포지션 테이블
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(8)
        self.positions_table.setHorizontalHeaderLabels([
            '상품', '방향', '수량', '평균가', '미실현 손익', '손익률', '레버리지', '청산가'
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.positions_table.setMaximumHeight(150)
        layout.addWidget(self.positions_table)
        
        # 새로고침 버튼
        refresh_positions_btn = QPushButton("🔄 포지션 새로고침")
        refresh_positions_btn.clicked.connect(self.refresh_positions)
        layout.addWidget(refresh_positions_btn)
        
        return panel
    
    def set_order_manager(self, order_manager):
        """주문 관리자 설정"""
        self.order_manager = order_manager
        self.refresh_all_data()
    
    def refresh_all_data(self):
        """모든 데이터 새로고침"""
        if not self.order_manager:
            self.log_message("⚠️ 주문 관리자가 설정되지 않았습니다.", "warning")
            return
        
        self.refresh_min_order_info()
        self.refresh_balance()
        self.refresh_positions()
    
    def on_symbol_changed(self, symbol):
        """심볼 변경 시 호출"""
        self.refresh_min_order_info()
    
    def refresh_min_order_info(self):
        """최소 주문 정보 새로고침"""
        if not self.order_manager:
            return
        
        symbol = self.symbol_combo.currentText()
        
        try:
            info = self.order_manager.get_min_order_info(symbol)
            
            if 'error' not in info:
                self.min_order_info = info
                self.current_price_label.setText(f"${info['current_price']:,.2f}")
                self.min_notional_label.setText(f"${info['min_notional_usdt']:.2f}")
                self.recommended_label.setText(f"${info['recommended_test_amount']:.2f}")
                
                self.log_message(f"✅ {symbol} 주문 정보 로드 완료", "success")
            else:
                self.log_message(f"❌ 주문 정보 조회 실패: {info['error']}", "error")
                
        except Exception as e:
            self.log_message(f"❌ 예외 발생: {str(e)}", "error")
    
    def refresh_balance(self):
        """잔고 새로고침"""
        if not self.order_manager:
            return
        
        try:
            balance = self.order_manager.get_account_balance('USDT')
            
            if balance:
                self.balance_label.setText(f"${balance['available']:,.2f}")
                self.log_message(f"✅ 잔고 조회: ${balance['available']:,.2f} USDT", "success")
            else:
                self.balance_label.setText("조회 실패")
                self.log_message("❌ 잔고 조회 실패", "error")
                
        except Exception as e:
            self.log_message(f"❌ 잔고 조회 예외: {str(e)}", "error")
    
    def refresh_positions(self):
        """포지션 새로고침"""
        if not self.order_manager:
            return
        
        try:
            positions = self.order_manager.get_positions()
            self.current_positions = positions
            
            self.positions_table.setRowCount(len(positions))
            
            for i, pos in enumerate(positions):
                self.positions_table.setItem(i, 0, QTableWidgetItem(pos['inst_id']))
                
                side_item = QTableWidgetItem(pos['pos_side'].upper())
                side_item.setForeground(QColor('#00ff88' if pos['pos_side'] == 'long' else '#ff4444'))
                self.positions_table.setItem(i, 1, side_item)
                
                self.positions_table.setItem(i, 2, QTableWidgetItem(str(pos['position'])))
                self.positions_table.setItem(i, 3, QTableWidgetItem(f"${pos['avg_price']:,.2f}"))
                
                upl_item = QTableWidgetItem(f"${pos['upl']:.2f}")
                upl_item.setForeground(QColor('#00ff88' if pos['upl'] >= 0 else '#ff4444'))
                self.positions_table.setItem(i, 4, upl_item)
                
                upl_ratio_item = QTableWidgetItem(f"{pos['upl_ratio']*100:.2f}%")
                upl_ratio_item.setForeground(QColor('#00ff88' if pos['upl_ratio'] >= 0 else '#ff4444'))
                self.positions_table.setItem(i, 5, upl_ratio_item)
                
                self.positions_table.setItem(i, 6, QTableWidgetItem(f"{pos['lever']}x"))
                self.positions_table.setItem(i, 7, QTableWidgetItem(
                    f"${pos['liq_price']:,.2f}" if pos['liq_price'] else "-"
                ))
            
            if positions:
                self.log_message(f"✅ {len(positions)}개 포지션 로드됨", "success")
            else:
                self.log_message("ℹ️ 보유 포지션 없음", "info")
                
        except Exception as e:
            self.log_message(f"❌ 포지션 조회 예외: {str(e)}", "error")
    
    def update_button_state(self, state):
        """체크박스 상태에 따른 버튼 활성화"""
        self.buy_test_btn.setEnabled(state == Qt.Checked)
    
    def execute_buy_test(self):
        """구매 테스트 실행"""
        if not self.order_manager:
            QMessageBox.warning(self, "경고", "주문 관리자가 설정되지 않았습니다.")
            return
        
        if not self.confirm_checkbox.isChecked():
            QMessageBox.warning(self, "경고", "실제 자금 사용에 동의해야 합니다.")
            return
        
        symbol = self.symbol_combo.currentText()
        amount = self.amount_spin.value()
        leverage = self.leverage_spin.value()
        
        # 최종 확인
        reply = QMessageBox.question(
            self, "실제 구매 확인",
            f"정말 실제 구매를 진행하시겠습니까?\n\n"
            f"상품: {symbol}\n"
            f"금액: ${amount:.2f} USDT\n"
            f"레버리지: {leverage}x\n\n"
            f"⚠️ 이 작업은 실제 자금을 사용합니다!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.log_message(f"\n{'='*50}", "info")
        self.log_message(f"🛒 실제 구매 테스트 시작", "info")
        self.log_message(f"상품: {symbol} | 금액: ${amount} | 레버리지: {leverage}x", "info")
        self.log_message(f"{'='*50}", "info")
        
        # UI 비활성화
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        # 스레드로 실행
        self.execution_thread = OrderExecutionThread(
            self.order_manager,
            'test_buy',
            {
                'inst_id': symbol,
                'usdt_amount': amount,
                'leverage': leverage
            }
        )
        self.execution_thread.result.connect(self.on_buy_test_result)
        self.execution_thread.finished_signal.connect(self.on_execution_finished)
        self.execution_thread.start()
    
    def on_buy_test_result(self, result):
        """구매 테스트 결과 처리"""
        if result.get('success'):
            self.log_message("\n🎉 구매 테스트 성공!", "success")
            
            order = result.get('order', {})
            if order:
                self.log_message(f"📌 주문 ID: {order.get('order_id')}", "success")
                
                detail = order.get('detail', {})
                if detail:
                    self.log_message(f"💰 체결 수량: {detail.get('filled_size')}", "success")
                    self.log_message(f"💵 체결 가격: ${detail.get('avg_price', 0):,.2f}", "success")
                    self.log_message(f"💸 수수료: ${abs(detail.get('fee', 0)):.6f}", "info")
            
            # 포지션 갱신
            QTimer.singleShot(1000, self.refresh_positions)
        else:
            self.log_message(f"\n❌ 구매 테스트 실패: {result.get('error')}", "error")
            
            # 상세 단계별 결과 출력
            for step in result.get('steps', []):
                status_icon = "✅" if step.get('status') == 'SUCCESS' else "❌"
                self.log_message(f"  {status_icon} {step.get('name')}: {step.get('status')}", 
                               "success" if step.get('status') == 'SUCCESS' else "error")
        
        # 잔고 갱신
        self.refresh_balance()
    
    def execute_close_position(self):
        """포지션 청산 실행"""
        if not self.order_manager:
            QMessageBox.warning(self, "경고", "주문 관리자가 설정되지 않았습니다.")
            return
        
        symbol = self.symbol_combo.currentText()
        
        # 해당 심볼 포지션 확인
        target_position = None
        for pos in self.current_positions:
            if pos['inst_id'] == symbol:
                target_position = pos
                break
        
        if not target_position:
            QMessageBox.information(self, "알림", f"{symbol}에 청산할 포지션이 없습니다.")
            return
        
        # 최종 확인
        reply = QMessageBox.question(
            self, "포지션 청산 확인",
            f"정말 포지션을 청산하시겠습니까?\n\n"
            f"상품: {symbol}\n"
            f"방향: {target_position['pos_side'].upper()}\n"
            f"수량: {target_position['position']}\n"
            f"현재 손익: ${target_position['upl']:.2f}\n\n"
            f"⚠️ 이 작업은 실제 포지션을 청산합니다!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.log_message(f"\n{'='*50}", "info")
        self.log_message(f"📤 포지션 청산 시작", "info")
        self.log_message(f"{'='*50}", "info")
        
        # UI 비활성화
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # 스레드로 실행
        self.execution_thread = OrderExecutionThread(
            self.order_manager,
            'close_position',
            {
                'inst_id': symbol,
                'pos_side': target_position['pos_side']
            }
        )
        self.execution_thread.result.connect(self.on_close_position_result)
        self.execution_thread.finished_signal.connect(self.on_execution_finished)
        self.execution_thread.start()
    
    def on_close_position_result(self, result):
        """청산 결과 처리"""
        if result.get('success'):
            self.log_message("\n🎉 포지션 청산 성공!", "success")
            
            closed_pos = result.get('closed_position', {})
            if closed_pos:
                self.log_message(f"📌 상품: {closed_pos.get('inst_id')}", "success")
                self.log_message(f"📊 수량: {closed_pos.get('position')}", "success")
                self.log_message(f"💰 실현 손익: ${closed_pos.get('upl', 0):.2f}", "success")
            
            # 포지션 갱신
            QTimer.singleShot(1000, self.refresh_positions)
        else:
            self.log_message(f"\n❌ 포지션 청산 실패: {result.get('error')}", "error")
        
        # 잔고 갱신
        self.refresh_balance()
    
    def on_execution_finished(self):
        """실행 완료 후 처리"""
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        self.confirm_checkbox.setChecked(False)  # 안전을 위해 체크 해제
    
    def set_ui_enabled(self, enabled: bool):
        """UI 활성화/비활성화"""
        self.symbol_combo.setEnabled(enabled)
        self.amount_spin.setEnabled(enabled)
        self.leverage_spin.setEnabled(enabled)
        self.confirm_checkbox.setEnabled(enabled)
        self.buy_test_btn.setEnabled(enabled and self.confirm_checkbox.isChecked())
        self.close_btn.setEnabled(enabled)
    
    def log_message(self, message: str, level: str = "info"):
        """로그 메시지 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        color_map = {
            'info': '#d4d4d4',
            'success': '#00ff88',
            'warning': '#ffaa00',
            'error': '#ff4444'
        }
        
        color = color_map.get(level, '#d4d4d4')
        
        html = f'<span style="color: #888;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
        self.result_log.append(html)
        
        # 스크롤 맨 아래로
        self.result_log.verticalScrollBar().setValue(
            self.result_log.verticalScrollBar().maximum()
        )


# 테스트용 메인
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    
    # 다크 테마 적용
    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
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
    
    widget = RealTradeTestWidget()
    widget.setWindowTitle("실제 거래 테스트")
    widget.resize(1000, 700)
    widget.show()
    
    sys.exit(app.exec_())
