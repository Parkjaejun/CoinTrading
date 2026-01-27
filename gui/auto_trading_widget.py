# gui/auto_trading_widget.py
"""
자동매매 제어 위젯 - 간소화 버전

구조:
- 상단: 제어 버튼 + 모드 표시
- 중단: 진입 평가 상태 (VIRTUAL → REAL)
- 하단: 시스템 로그

설정은 접기/펼치기 가능한 패널로 통합
"""

import os
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QGroupBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QFrame, QProgressBar,
    QMessageBox, QDialog, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor

# 포지션 저장 경로
POSITION_SAVE_FILE = "data/saved_positions.json"


class CollapsibleSettings(QWidget):
    """접기/펼치기 가능한 설정 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 토글 버튼
        self.toggle_btn = QPushButton("⚙️ 설정 펼치기")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: 8px;
                text-align: left;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #3a3a3a;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_settings)
        layout.addWidget(self.toggle_btn)
        
        # 설정 컨테이너 (숨김 상태로 시작)
        self.settings_container = QFrame()
        self.settings_container.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3a3a3a;
                border-top: none;
            }
        """)
        self.settings_container.setMaximumHeight(0)
        
        settings_layout = QGridLayout(self.settings_container)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(10)
        
        # 설정 항목들
        row = 0
        
        # 심볼 (BTC만)
        settings_layout.addWidget(QLabel("심볼:"), row, 0)
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItem('BTC-USDT-SWAP')
        self.symbol_combo.setEnabled(False)  # BTC만 사용
        settings_layout.addWidget(self.symbol_combo, row, 1)
        row += 1
        
        # 체크 간격
        settings_layout.addWidget(QLabel("체크 간격(초):"), row, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 300)
        self.interval_spin.setValue(60)
        settings_layout.addWidget(self.interval_spin, row, 1)
        row += 1
        
        # 레버리지
        settings_layout.addWidget(QLabel("레버리지:"), row, 0)
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 100)
        self.leverage_spin.setValue(10)
        settings_layout.addWidget(self.leverage_spin, row, 1)
        row += 1
        
        # 트레일링 스탑
        settings_layout.addWidget(QLabel("트레일링 스탑(%):"), row, 0)
        self.trailing_spin = QDoubleSpinBox()
        self.trailing_spin.setRange(1, 50)
        self.trailing_spin.setValue(10)
        settings_layout.addWidget(self.trailing_spin, row, 1)
        row += 1
        
        # 포지션 크기
        settings_layout.addWidget(QLabel("포지션 크기(%):"), row, 0)
        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(1, 100)
        self.position_size_spin.setValue(10)
        settings_layout.addWidget(self.position_size_spin, row, 1)
        
        layout.addWidget(self.settings_container)
    
    def toggle_settings(self):
        """설정 패널 토글"""
        self.is_expanded = not self.is_expanded
        
        if self.is_expanded:
            self.settings_container.setMaximumHeight(200)
            self.toggle_btn.setText("⚙️ 설정 접기")
        else:
            self.settings_container.setMaximumHeight(0)
            self.toggle_btn.setText("⚙️ 설정 펼치기")
    
    def get_config(self) -> dict:
        """설정 반환"""
        return {
            'symbol': 'BTC-USDT-SWAP',
            'check_interval': self.interval_spin.value(),
            'leverage': self.leverage_spin.value(),
            'trailing_stop': self.trailing_spin.value() / 100,
            'position_size': self.position_size_spin.value() / 100,
        }
    
    def set_enabled(self, enabled: bool):
        """설정 활성화/비활성화"""
        self.interval_spin.setEnabled(enabled)
        self.leverage_spin.setEnabled(enabled)
        self.trailing_spin.setEnabled(enabled)
        self.position_size_spin.setEnabled(enabled)


class EntryEvaluationWidget(QWidget):
    """진입 평가 상태 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 제목
        title = QLabel("📊 진입 평가 (VIRTUAL → REAL 전환)")
        title.setFont(QFont("Arial", 11, QFont.Bold))
        title.setStyleSheet("color: #00aaff;")
        layout.addWidget(title)
        
        # 조건 프레임
        conditions_frame = QFrame()
        conditions_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border: 1px solid #333;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        conditions_layout = QVBoxLayout(conditions_frame)
        conditions_layout.setSpacing(12)
        
        # 1. 트렌드 조건
        self.trend_row = self._create_condition_row("📈 트렌드 (30분봉)", "EMA150 > EMA200")
        conditions_layout.addLayout(self.trend_row['layout'])
        
        # 2. 진입 조건
        self.entry_row = self._create_condition_row("🎯 진입 (1분봉)", "EMA20 ≥ EMA50×99%")
        conditions_layout.addLayout(self.entry_row['layout'])
        
        # 3. 연속 충족
        self.count_row = self._create_condition_row("🔄 연속 충족", "3회 필요")
        conditions_layout.addLayout(self.count_row['layout'])
        
        layout.addWidget(conditions_frame)
        
        # 결과
        result_layout = QHBoxLayout()
        result_layout.addWidget(QLabel("결과:"))
        self.result_label = QLabel("대기 중...")
        self.result_label.setFont(QFont("Arial", 12, QFont.Bold))
        result_layout.addWidget(self.result_label)
        result_layout.addStretch()
        layout.addLayout(result_layout)
        
        # 진행률
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setFormat("%p%")
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 3px;
                background-color: #1a1a1a;
                text-align: center;
                color: white;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
        layout.addWidget(self.progress)
    
    def _create_condition_row(self, name: str, target: str) -> dict:
        """조건 행 생성"""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        name_label = QLabel(name)
        name_label.setMinimumWidth(130)
        name_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(name_label)
        
        current_label = QLabel("--")
        current_label.setMinimumWidth(80)
        current_label.setStyleSheet("color: #ffc107;")
        layout.addWidget(current_label)
        
        target_label = QLabel(f"({target})")
        target_label.setMinimumWidth(120)
        target_label.setStyleSheet("color: #666;")
        layout.addWidget(target_label)
        
        status_label = QLabel("⏳")
        status_label.setMinimumWidth(25)
        layout.addWidget(status_label)
        
        gap_label = QLabel("")
        gap_label.setMinimumWidth(100)
        gap_label.setStyleSheet("color: #e74c3c;")
        layout.addWidget(gap_label)
        
        layout.addStretch()
        
        return {
            'layout': layout,
            'current': current_label,
            'status': status_label,
            'gap': gap_label
        }
    
    def update_evaluation(self, data: dict):
        """평가 상태 업데이트"""
        # 트렌드
        trend = data.get('trend', {})
        trend_diff = trend.get('diff_pct', 0)
        trend_passed = trend.get('passed', False)
        
        self.trend_row['current'].setText(f"{trend_diff:+.3f}%")
        if trend_passed:
            self.trend_row['status'].setText("✅")
            self.trend_row['current'].setStyleSheet("color: #27ae60;")
            self.trend_row['gap'].setText("")
        else:
            self.trend_row['status'].setText("❌")
            self.trend_row['current'].setStyleSheet("color: #e74c3c;")
            self.trend_row['gap'].setText(f"미달: {abs(trend_diff):.3f}%p")
        
        # 진입
        entry = data.get('entry', {})
        entry_diff = entry.get('diff_pct', 0)
        entry_passed = entry.get('passed', False)
        threshold = entry.get('threshold', -1.0)
        
        self.entry_row['current'].setText(f"{entry_diff:+.3f}%")
        if entry_passed:
            self.entry_row['status'].setText("✅")
            self.entry_row['current'].setStyleSheet("color: #27ae60;")
            self.entry_row['gap'].setText("")
        else:
            self.entry_row['status'].setText("❌")
            self.entry_row['current'].setStyleSheet("color: #e74c3c;")
            gap = threshold - entry_diff
            self.entry_row['gap'].setText(f"미달: {abs(gap):.3f}%p")
        
        # 연속 충족
        count = data.get('consecutive_count', 0)
        required = data.get('required_count', 3)
        count_passed = count >= required
        
        self.count_row['current'].setText(f"{count}/{required}회")
        if count_passed:
            self.count_row['status'].setText("✅")
            self.count_row['current'].setStyleSheet("color: #27ae60;")
            self.count_row['gap'].setText("")
        else:
            self.count_row['status'].setText("⏳")
            self.count_row['current'].setStyleSheet("color: #ffc107;")
            self.count_row['gap'].setText(f"남음: {required - count}회")
        
        # 결과
        overall = data.get('overall_passed', False)
        if overall:
            self.result_label.setText("✅ REAL 전환 준비 완료!")
            self.result_label.setStyleSheet("color: #27ae60;")
        else:
            issues = []
            if not trend_passed:
                issues.append("트렌드")
            if not entry_passed:
                issues.append("진입")
            if not count_passed:
                issues.append("연속")
            self.result_label.setText(f"⏳ 대기 ({', '.join(issues)})")
            self.result_label.setStyleSheet("color: #ffc107;")
        
        # 진행률
        progress = 0
        if trend_passed:
            progress += 33
        if entry_passed:
            progress += 33
        progress += int(34 * count / required)
        
        self.progress.setValue(min(progress, 100))
        
        # 색상
        if overall:
            self.progress.setStyleSheet(self.progress.styleSheet().replace("#3498db", "#27ae60"))
        elif progress >= 66:
            self.progress.setStyleSheet(self.progress.styleSheet().replace("#3498db", "#f39c12"))


class AutoTradingWidget(QWidget):
    """자동매매 제어 위젯 - 간소화 버전"""
    
    log_signal = pyqtSignal(str)
    mode_changed = pyqtSignal(str, str)
    balance_updated = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.engine = None
        self.is_running = False
        self.current_mode = "VIRTUAL"
        self.current_balance = 0.0
        self.consecutive_pass_count = 0
        
        self.setup_ui()
        self.connect_signals()
        
        # 평가 타이머
        self.eval_timer = QTimer()
        self.eval_timer.timeout.connect(self.update_evaluation)
        self.eval_timer.start(3000)
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 1. 제어 패널
        control_group = self.create_control_panel()
        layout.addWidget(control_group)
        
        # 2. 접이식 설정
        self.settings_panel = CollapsibleSettings()
        layout.addWidget(self.settings_panel)
        
        # 3. 진입 평가 상태
        self.eval_widget = EntryEvaluationWidget()
        layout.addWidget(self.eval_widget)
        
        # 4. 로그
        log_group = self.create_log_panel()
        layout.addWidget(log_group)
    
    def create_control_panel(self) -> QGroupBox:
        """제어 패널"""
        group = QGroupBox("🤖 자동매매 제어")
        layout = QVBoxLayout(group)
        
        # 상태 행
        status_layout = QHBoxLayout()
        
        # 모드
        self.mode_indicator = QLabel("🟡")
        self.mode_indicator.setFont(QFont("Arial", 22))
        status_layout.addWidget(self.mode_indicator)
        
        self.mode_label = QLabel("VIRTUAL")
        self.mode_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.mode_label.setStyleSheet("color: #ffc107;")
        status_layout.addWidget(self.mode_label)
        
        status_layout.addSpacing(30)
        
        # 실행 상태
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 22))
        self.status_indicator.setStyleSheet("color: #7f8c8d;")
        status_layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("대기 중")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # BTC 가격 (메인에서 업데이트)
        self.btc_price_label = QLabel("BTC: $--")
        self.btc_price_label.setFont(QFont("Arial", 12))
        self.btc_price_label.setStyleSheet("color: #f39c12;")
        status_layout.addWidget(self.btc_price_label)
        
        layout.addLayout(status_layout)
        
        # 버튼 행
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 시작")
        self.start_btn.setMinimumSize(120, 45)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:disabled { background-color: #555; }
        """)
        self.start_btn.clicked.connect(self.start_trading)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("🛑 중지")
        self.stop_btn.setMinimumSize(100, 45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:disabled { background-color: #555; }
        """)
        self.stop_btn.clicked.connect(self.stop_trading)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout.addSpacing(30)
        
        self.emergency_btn = QPushButton("🚨 긴급 청산")
        self.emergency_btn.setMinimumSize(120, 45)
        self.emergency_btn.setStyleSheet("""
            QPushButton {
                background-color: #8e44ad;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                border: 2px solid #9b59b6;
            }
            QPushButton:hover { background-color: #9b59b6; }
        """)
        self.emergency_btn.clicked.connect(self.emergency_close)
        btn_layout.addWidget(self.emergency_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def create_log_panel(self) -> QGroupBox:
        """로그 패널"""
        group = QGroupBox("📜 시스템 로그")
        layout = QVBoxLayout(group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #dcdcdc;
                font-family: Consolas, monospace;
                font-size: 11px;
                border: 1px solid #333;
            }
        """)
        layout.addWidget(self.log_text)
        
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("지우기")
        clear_btn.setMaximumWidth(80)
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def connect_signals(self):
        """시그널 연결"""
        self.log_signal.connect(self.append_log)
        self.mode_changed.connect(self.on_mode_changed)
    
    # =========================================================
    # 자동매매 제어
    # =========================================================
    
    def start_trading(self):
        """자동매매 시작"""
        # 확인 대화상자
        reply = QMessageBox.question(
            self,
            "자동매매 시작",
            "v2 Long Only 자동매매를 시작합니다.\n\n"
            "• VIRTUAL 모드로 시작\n"
            "• 진입 조건 충족 시 REAL 전환\n"
            "• BTC-USDT-SWAP만 거래\n\n"
            "계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 엔진 import
            try:
                from cointrading_v2.trading_engine_v2 import TradingEngineV2 as Engine
                self.append_log("✅ v2 엔진 로드")
            except ImportError:
                from trading_engine import TradingEngine as Engine
                self.append_log("⚠️ 기본 엔진 사용")
            
            # 설정
            settings = self.settings_panel.get_config()
            config = {
                'symbols': ['BTC-USDT-SWAP'],
                'check_interval': settings['check_interval'],
                'long_leverage': settings['leverage'],
                'long_trailing_stop': settings['trailing_stop'],
                'position_size': settings['position_size'],
                'start_in_virtual_mode': True,
                'long_only': True,
                'verbose': False,
            }
            
            self.engine = Engine(config)
            
            # 콜백
            if hasattr(self.engine, 'on_signal_callback'):
                self.engine.on_signal_callback = self.on_signal
            if hasattr(self.engine, 'on_trade_callback'):
                self.engine.on_trade_callback = self.on_trade
            if hasattr(self.engine, 'on_mode_change_callback'):
                self.engine.on_mode_change_callback = self.on_engine_mode_change
            if hasattr(self.engine, 'on_log_callback'):
                self.engine.on_log_callback = self.on_engine_log
            
            # 시작
            if self.engine.start():
                self.is_running = True
                self.consecutive_pass_count = 0
                self.update_mode_display("VIRTUAL")
                
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                self.status_indicator.setStyleSheet("color: #27ae60;")
                self.status_label.setText("실행 중")
                self.settings_panel.set_enabled(False)
                
                self.append_log("🚀 자동매매 시작 (VIRTUAL)")
            else:
                self.append_log("❌ 시작 실패")
                
        except Exception as e:
            import traceback
            self.append_log(f"❌ 오류: {e}")
            traceback.print_exc()
    
    def stop_trading(self):
        """중지"""
        if self.engine:
            def stop():
                if hasattr(self.engine, 'stop'):
                    self.engine.stop()
                self.is_running = False
            threading.Thread(target=stop, daemon=True).start()
        
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_indicator.setStyleSheet("color: #7f8c8d;")
        self.status_label.setText("중지됨")
        self.settings_panel.set_enabled(True)
        
        self.append_log("🛑 자동매매 중지")
    
    def emergency_close(self):
        """긴급 청산"""
        dialog = QDialog(self)
        dialog.setWindowTitle("🚨 긴급 청산")
        dialog.setFixedSize(380, 220)
        dialog.setStyleSheet("QDialog { background-color: #2b2b2b; } QLabel { color: #fff; }")
        
        layout = QVBoxLayout(dialog)
        
        title = QLabel("⚠️ 모든 포지션을 즉시 청산합니다!")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setStyleSheet("color: #e74c3c;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        warning = QLabel("• 시장가로 청산됩니다\n• 되돌릴 수 없습니다\n• 슬리피지 발생 가능")
        warning.setStyleSheet("padding: 15px;")
        layout.addWidget(warning)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        
        no_btn = QPushButton("취소")
        no_btn.setStyleSheet("background-color: #3a3a3a; color: white; padding: 10px 25px;")
        no_btn.clicked.connect(dialog.reject)
        
        yes_btn = QPushButton("청산 실행")
        yes_btn.setStyleSheet("background-color: #c0392b; color: white; padding: 10px 25px;")
        yes_btn.clicked.connect(dialog.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(no_btn)
        btn_layout.addWidget(yes_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            try:
                self.append_log("🚨 긴급 청산 실행...")
                from okx.order_manager import OrderManager
                om = OrderManager(verbose=False)
                if om.close_all_positions():
                    self.append_log("✅ 청산 완료")
                else:
                    self.append_log("⚠️ 포지션 없음")
            except Exception as e:
                self.append_log(f"❌ 청산 오류: {e}")
    
    # =========================================================
    # 진입 평가
    # =========================================================
    
    def update_evaluation(self):
        """진입 평가 업데이트"""
        if not self.is_running or not self.engine:
            return
        
        try:
            data = self.get_evaluation_data()
            self.eval_widget.update_evaluation(data)
        except:
            pass
    
    def get_evaluation_data(self) -> dict:
        """평가 데이터 계산"""
        data = {
            'trend': {'diff_pct': 0, 'passed': False},
            'entry': {'diff_pct': 0, 'threshold': -1.0, 'passed': False},
            'consecutive_count': 0,
            'required_count': 3,
            'overall_passed': False
        }
        
        if not self.engine:
            return data
        
        try:
            # 전략 찾기
            strategy = None
            if hasattr(self.engine, 'strategy'):
                strategy = self.engine.strategy
            elif hasattr(self.engine, 'strategies'):
                for k, s in self.engine.strategies.items():
                    if 'long' in k.lower():
                        strategy = s
                        break
            
            if not strategy:
                return data
            
            # 30분봉 EMA
            if hasattr(strategy, 'last_ema_30m'):
                ema = strategy.last_ema_30m
                ema150 = ema.get('ema_150', 0)
                ema200 = ema.get('ema_200', 0)
                if ema200 > 0:
                    diff = ((ema150 - ema200) / ema200) * 100
                    data['trend'] = {
                        'diff_pct': diff,
                        'passed': ema150 > ema200
                    }
            
            # 1분봉 EMA
            if hasattr(strategy, 'last_ema_1m'):
                ema = strategy.last_ema_1m
                ema20 = ema.get('ema_20', 0)
                ema50 = ema.get('ema_50', 0)
                if ema50 > 0:
                    diff = ((ema20 - ema50) / ema50) * 100
                    data['entry'] = {
                        'diff_pct': diff,
                        'threshold': -1.0,
                        'passed': ema20 >= ema50 * 0.99
                    }
            
            # 연속 충족
            if hasattr(strategy, 'entry_ready_count'):
                data['consecutive_count'] = strategy.entry_ready_count
            else:
                if data['trend']['passed'] and data['entry']['passed']:
                    self.consecutive_pass_count += 1
                else:
                    self.consecutive_pass_count = 0
                data['consecutive_count'] = self.consecutive_pass_count
            
            data['overall_passed'] = (
                data['trend']['passed'] and
                data['entry']['passed'] and
                data['consecutive_count'] >= 3
            )
            
        except:
            pass
        
        return data
    
    # =========================================================
    # 콜백
    # =========================================================
    
    def on_signal(self, signal: dict):
        """신호"""
        action = signal.get('action', '')
        is_real = "REAL" if signal.get('is_real') else "VIRT"
        self.log_signal.emit(f"📡 [{is_real}] {action}")
    
    def on_trade(self, signal: dict, success: bool):
        """거래"""
        status = "✅" if success else "❌"
        if signal.get('action') == 'enter':
            self.log_signal.emit(f"💰 {status} 진입: ${signal.get('price', 0):,.0f}")
        else:
            self.log_signal.emit(f"💰 {status} 청산: PnL ${signal.get('pnl', 0):+.2f}")
    
    def on_engine_mode_change(self, from_mode: str, to_mode: str, reason: str = ""):
        """모드 전환"""
        self.mode_changed.emit(from_mode, to_mode)
        self.append_log(f"🔄 모드 전환: {from_mode} → {to_mode}")
        if to_mode == "REAL":
            self.append_log("⚠️ 실제 자금 거래 시작!")
    
    def on_engine_log(self, message: str, level: str = "INFO"):
        """엔진 로그"""
        if level in ["ERROR", "SIGNAL", "TRADE", "MODE"]:
            self.log_signal.emit(message)
    
    def on_mode_changed(self, from_mode: str, to_mode: str):
        """모드 UI 업데이트"""
        self.current_mode = to_mode
        self.update_mode_display(to_mode)
    
    def update_mode_display(self, mode: str):
        """모드 표시"""
        if mode == "REAL":
            self.mode_indicator.setText("🟢")
            self.mode_label.setText("REAL")
            self.mode_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.mode_indicator.setText("🟡")
            self.mode_label.setText("VIRTUAL")
            self.mode_label.setStyleSheet("color: #ffc107; font-weight: bold;")
    
    def on_balance_updated(self, balance: float):
        """잔고 업데이트"""
        self.current_balance = balance
    
    def append_log(self, message: str):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )