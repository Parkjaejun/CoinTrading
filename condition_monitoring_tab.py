# gui/condition_monitoring_tab.py
"""
기존 GUI 시스템에 통합할 조건 모니터링 탭
main_window.py에서 임포트하여 사용
"""

import time
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QGroupBox, QGridLayout,
    QComboBox, QPlainTextEdit, QProgressBar, QSplitter, QFrame
)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor

class TradingMode(Enum):
    """거래 모드"""
    VIRTUAL_ONLY = "가상거래만"
    REAL_ONLY = "실거래만"  
    HYBRID = "하이브리드"
    STOPPED = "중지"

class ConditionStatus(Enum):
    """조건 상태"""
    CHECKING = "확인중"
    MET = "조건만족"
    NOT_MET = "조건불만족"
    ERROR = "오류"

@dataclass
class TradingCondition:
    """거래 조건 데이터 클래스"""
    name: str
    description: str
    status: ConditionStatus
    value: float
    threshold: float
    last_check: datetime
    meet_count: int = 0
    total_checks: int = 0

class ConditionMonitoringWorker(QThread):
    """조건 모니터링 백그라운드 워커 (통합용)"""
    
    # 시그널 정의
    condition_updated = pyqtSignal(dict)
    log_message = pyqtSignal(str, str)  # message, level
    trade_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.trading_mode = TradingMode.VIRTUAL_ONLY
        self.check_interval = 5  # 5초마다 확인
        
        # 모니터링 조건들
        self.conditions = {
            'trend_condition': TradingCondition(
                name="트렌드 조건",
                description="150EMA > 200EMA (상승장)",
                status=ConditionStatus.CHECKING,
                value=0.0,
                threshold=0.0,
                last_check=datetime.now()
            ),
            'golden_cross': TradingCondition(
                name="골든크로스",
                description="20EMA > 50EMA",
                status=ConditionStatus.CHECKING,
                value=0.0,
                threshold=0.0,
                last_check=datetime.now()
            ),
            'volume_condition': TradingCondition(
                name="거래량 조건",
                description="평균 거래량 대비 1.5배 이상",
                status=ConditionStatus.CHECKING,
                value=0.0,
                threshold=1.5,
                last_check=datetime.now()
            ),
            'rsi_condition': TradingCondition(
                name="RSI 조건",
                description="RSI 30-70 범위",
                status=ConditionStatus.CHECKING,
                value=50.0,
                threshold=70.0,
                last_check=datetime.now()
            )
        }
        
        # 통계
        self.total_checks = 0
        self.conditions_met_count = 0
        
        # 가상 시장 데이터 (실제로는 외부에서 받아옴)
        self.market_data = {
            'price': 45000.0,
            'ema_20': 45000.0,
            'ema_50': 44950.0,
            'ema_150': 44800.0,
            'ema_200': 44700.0,
            'rsi': 50.0,
            'volume_ratio': 1.0
        }
    
    def run(self):
        """모니터링 메인 루프"""
        self.is_running = True
        self.log_message.emit("🚀 조건 모니터링 시작", "INFO")
        
        while self.is_running:
            try:
                # 시장 데이터 업데이트 (시뮬레이션)
                self._simulate_market_data()
                
                # 조건 확인
                self._check_all_conditions()
                
                # 거래 시그널 생성
                self._generate_trade_signals()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.log_message.emit(f"❌ 모니터링 오류: {str(e)}", "ERROR")
                time.sleep(self.check_interval)
    
    def _simulate_market_data(self):
        """시장 데이터 시뮬레이션"""
        import random
        
        # 가격 변동 시뮬레이션
        volatility = 0.01  # 1% 변동성
        self.market_data['price'] *= (1 + random.uniform(-volatility, volatility))
        
        # EMA 값들 업데이트
        self.market_data['ema_20'] = self.market_data['price'] * (1 + random.uniform(-0.002, 0.002))
        self.market_data['ema_50'] = self.market_data['price'] * (1 + random.uniform(-0.005, 0.005))
        self.market_data['ema_150'] = self.market_data['price'] * (1 + random.uniform(-0.01, 0.01))
        self.market_data['ema_200'] = self.market_data['price'] * (1 + random.uniform(-0.015, 0.015))
        
        # RSI 업데이트
        self.market_data['rsi'] = max(20, min(80, 
            self.market_data['rsi'] + random.uniform(-3, 3)))
        
        # 거래량 비율 업데이트
        self.market_data['volume_ratio'] = max(0.5, min(3.0,
            self.market_data['volume_ratio'] + random.uniform(-0.1, 0.1)))
    
    def _check_all_conditions(self):
        """모든 조건 확인"""
        self.total_checks += 1
        now = datetime.now()
        
        # 1. 트렌드 조건
        trend_met = self.market_data['ema_150'] > self.market_data['ema_200']
        self.conditions['trend_condition'].status = (
            ConditionStatus.MET if trend_met else ConditionStatus.NOT_MET
        )
        self.conditions['trend_condition'].value = (
            (self.market_data['ema_150'] - self.market_data['ema_200']) / 
            self.market_data['ema_200'] * 100
        )
        self.conditions['trend_condition'].last_check = now
        self.conditions['trend_condition'].total_checks += 1
        if trend_met:
            self.conditions['trend_condition'].meet_count += 1
        
        # 2. 골든크로스 조건
        golden_cross_met = self.market_data['ema_20'] > self.market_data['ema_50']
        self.conditions['golden_cross'].status = (
            ConditionStatus.MET if golden_cross_met else ConditionStatus.NOT_MET
        )
        self.conditions['golden_cross'].value = (
            (self.market_data['ema_20'] - self.market_data['ema_50']) / 
            self.market_data['ema_50'] * 100
        )
        self.conditions['golden_cross'].last_check = now
        self.conditions['golden_cross'].total_checks += 1
        if golden_cross_met:
            self.conditions['golden_cross'].meet_count += 1
        
        # 3. 거래량 조건
        volume_met = self.market_data['volume_ratio'] >= 1.5
        self.conditions['volume_condition'].status = (
            ConditionStatus.MET if volume_met else ConditionStatus.NOT_MET
        )
        self.conditions['volume_condition'].value = self.market_data['volume_ratio']
        self.conditions['volume_condition'].last_check = now
        self.conditions['volume_condition'].total_checks += 1
        if volume_met:
            self.conditions['volume_condition'].meet_count += 1
        
        # 4. RSI 조건
        rsi_met = 30 <= self.market_data['rsi'] <= 70
        self.conditions['rsi_condition'].status = (
            ConditionStatus.MET if rsi_met else ConditionStatus.NOT_MET
        )
        self.conditions['rsi_condition'].value = self.market_data['rsi']
        self.conditions['rsi_condition'].last_check = now
        self.conditions['rsi_condition'].total_checks += 1
        if rsi_met:
            self.conditions['rsi_condition'].meet_count += 1
        
        # 조건 업데이트 시그널
        all_met = all(c.status == ConditionStatus.MET for c in self.conditions.values())
        condition_data = {
            'conditions': self.conditions.copy(),
            'market_data': self.market_data.copy(),
            'all_met': all_met,
            'timestamp': now
        }
        self.condition_updated.emit(condition_data)
        
        # 로그 출력
        self._log_condition_status(all_met)
    
    def _log_condition_status(self, all_met: bool):
        """조건 상태 로그"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # 간결한 상태 로그
        if all_met:
            self.log_message.emit("🎯 모든 조건 만족! 거래 신호 생성", "SUCCESS")
        else:
            unmet_count = sum(1 for c in self.conditions.values() 
                            if c.status != ConditionStatus.MET)
            self.log_message.emit(f"⏳ 미충족 조건: {unmet_count}개", "INFO")
        
        # 30초마다 상세 로그
        if self.total_checks % 6 == 0:  # 5초 * 6 = 30초
            for name, condition in self.conditions.items():
                meet_rate = (condition.meet_count / condition.total_checks * 100) if condition.total_checks > 0 else 0
                status_icon = "✅" if condition.status == ConditionStatus.MET else "❌"
                self.log_message.emit(
                    f"{status_icon} {condition.name}: {condition.value:.3f} (만족률: {meet_rate:.1f}%)",
                    "INFO"
                )
    
    def _generate_trade_signals(self):
        """거래 시그널 생성"""
        all_met = all(c.status == ConditionStatus.MET for c in self.conditions.values())
        
        if all_met:
            self.conditions_met_count += 1
            
            signal = {
                'type': 'LONG_ENTRY',
                'symbol': 'BTC-USDT-SWAP',
                'price': self.market_data['price'],
                'timestamp': datetime.now(),
                'mode': self.trading_mode.value,
                'conditions': {name: c.value for name, c in self.conditions.items()}
            }
            
            self.trade_signal.emit(signal)
            self.log_message.emit(
                f"📈 거래 신호: {signal['type']} @ ${signal['price']:,.2f} (모드: {signal['mode']})",
                "SUCCESS"
            )
    
    def set_trading_mode(self, mode: TradingMode):
        """거래 모드 설정"""
        self.trading_mode = mode
        self.log_message.emit(f"🔄 거래 모드: {mode.value}", "INFO")
    
    def stop(self):
        """모니터링 중지"""
        self.is_running = False
        self.log_message.emit("⏹️ 조건 모니터링 중지", "WARNING")

class ConditionMonitoringTab(QWidget):
    """조건 모니터링 탭 (기존 GUI에 통합용)"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
        self.setup_connections()
        
        # 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # 1초마다
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 상단 제어 패널
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        
        # 중앙 스플리터
        splitter = QSplitter(Qt.Horizontal)
        
        # 왼쪽: 조건 상태 + 시장 데이터
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # 오른쪽: 로그
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 2)  # 왼쪽이 더 넓게
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
    def _create_control_panel(self) -> QWidget:
        """제어 패널 생성"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMaximumHeight(80)
        
        layout = QHBoxLayout()
        panel.setLayout(layout)
        
        # 거래 모드 선택
        layout.addWidget(QLabel("거래 모드:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([mode.value for mode in TradingMode])
        self.mode_combo.setCurrentText(TradingMode.VIRTUAL_ONLY.value)
        layout.addWidget(self.mode_combo)
        
        layout.addStretch()
        
        # 제어 버튼
        self.start_btn = QPushButton("모니터링 시작")
        self.stop_btn = QPushButton("모니터링 중지")
        self.stop_btn.setEnabled(False)
        
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        
        # 상태 정보
        layout.addStretch()
        self.status_label = QLabel("상태: 대기중")
        self.checks_label = QLabel("확인: 0회")
        self.signals_label = QLabel("신호: 0회")
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.checks_label)
        layout.addWidget(self.signals_label)
        
        return panel
    
    def _create_left_panel(self) -> QWidget:
        """왼쪽 패널 (조건 + 시장 데이터)"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # 시장 데이터 그룹
        market_group = QGroupBox("현재 시장 정보")
        market_layout = QGridLayout()
        market_group.setLayout(market_layout)
        
        self.price_label = QLabel("$0.00")
        self.price_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.price_label.setStyleSheet("color: #00ff88;")
        
        self.ema_labels = {}
        for i, ema in enumerate(['20', '50', '150', '200']):
            self.ema_labels[ema] = QLabel(f"EMA{ema}: $0.00")
            market_layout.addWidget(QLabel(f"EMA{ema}:"), i // 2, (i % 2) * 2)
            market_layout.addWidget(self.ema_labels[ema], i // 2, (i % 2) * 2 + 1)
        
        self.rsi_label = QLabel("RSI: 50.0")
        self.volume_label = QLabel("거래량: 1.0x")
        
        market_layout.addWidget(QLabel("현재가:"), 0, 4)
        market_layout.addWidget(self.price_label, 0, 5)
        market_layout.addWidget(QLabel("RSI:"), 1, 4)
        market_layout.addWidget(self.rsi_label, 1, 5)
        market_layout.addWidget(QLabel("거래량:"), 2, 4)
        market_layout.addWidget(self.volume_label, 2, 5)
        
        layout.addWidget(market_group)
        
        # 조건 상태 그룹
        condition_group = QGroupBox("거래 조건 상태")
        condition_layout = QVBoxLayout()
        condition_group.setLayout(condition_layout)
        
        self.condition_table = QTableWidget()
        self.condition_table.setColumnCount(5)
        self.condition_table.setHorizontalHeaderLabels([
            '조건명', '상태', '현재값', '만족률', '설명'
        ])
        self.condition_table.setMaximumHeight(200)
        
        condition_layout.addWidget(self.condition_table)
        layout.addWidget(condition_group)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """오른쪽 패널 (로그)"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        log_group = QGroupBox("실시간 모니터링 로그")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        
        self.log_display = QPlainTextEdit()
        self.log_display.setMaximumBlockCount(500)  # 최대 500줄
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        
        log_layout.addWidget(self.log_display)
        layout.addWidget(log_group)
        
        return panel
    
    def setup_connections(self):
        """시그널-슬롯 연결"""
        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.mode_combo.currentTextChanged.connect(self.change_trading_mode)
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.worker is None or not self.worker.isRunning():
            self.worker = ConditionMonitoringWorker()
            
            # 시그널 연결
            self.worker.condition_updated.connect(self.update_conditions)
            self.worker.log_message.connect(self.add_log)
            self.worker.trade_signal.connect(self.handle_trade_signal)
            
            # 워커 시작
            self.worker.start()
            
            # UI 상태 업데이트
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText("상태: 모니터링 중")
            
            self.add_log("🚀 조건 모니터링 시작", "SUCCESS")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
            # UI 상태 업데이트
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("상태: 중지됨")
            
            self.add_log("⏹️ 조건 모니터링 중지", "WARNING")
    
    def change_trading_mode(self, mode_text: str):
        """거래 모드 변경"""
        try:
            mode = TradingMode(mode_text)
            if self.worker and self.worker.isRunning():
                self.worker.set_trading_mode(mode)
        except ValueError:
            pass
    
    def update_conditions(self, condition_data: dict):
        """조건 상태 업데이트"""
        conditions = condition_data['conditions']
        market_data = condition_data['market_data']
        
        # 시장 데이터 업데이트
        self.price_label.setText(f"${market_data['price']:,.2f}")
        for ema in ['20', '50', '150', '200']:
            self.ema_labels[ema].setText(f"EMA{ema}: ${market_data[f'ema_{ema}']:,.2f}")
        self.rsi_label.setText(f"RSI: {market_data['rsi']:.1f}")
        self.volume_label.setText(f"거래량: {market_data['volume_ratio']:.1f}x")
        
        # 조건 테이블 업데이트
        self.condition_table.setRowCount(len(conditions))
        for row, (name, condition) in enumerate(conditions.items()):
            # 조건명
            self.condition_table.setItem(row, 0, QTableWidgetItem(condition.name))
            
            # 상태
            status_item = QTableWidgetItem(condition.status.value)
            if condition.status == ConditionStatus.MET:
                status_item.setBackground(QColor(0, 150, 0, 100))
            elif condition.status == ConditionStatus.NOT_MET:
                status_item.setBackground(QColor(150, 0, 0, 100))
            self.condition_table.setItem(row, 1, status_item)
            
            # 현재값
            self.condition_table.setItem(row, 2, QTableWidgetItem(f"{condition.value:.3f}"))
            
            # 만족률
            meet_rate = (condition.meet_count / condition.total_checks * 100) if condition.total_checks > 0 else 0
            self.condition_table.setItem(row, 3, QTableWidgetItem(f"{meet_rate:.1f}%"))
            
            # 설명
            self.condition_table.setItem(row, 4, QTableWidgetItem(condition.description))
        
        self.condition_table.resizeColumnsToContents()
    
    def handle_trade_signal(self, signal: dict):
        """거래 신호 처리"""
        signal_type = signal['type']
        price = signal['price']
        mode = signal['mode']
        
        self.add_log(f"📈 거래 신호: {signal_type} @ ${price:,.2f} (모드: {mode})", "SUCCESS")
    
    def add_log(self, message: str, level: str = 'INFO'):
        """로그 추가"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        colors = {
            'INFO': '#ffffff',
            'WARNING': '#ffaa00', 
            'ERROR': '#ff0000',
            'SUCCESS': '#00ff88'
        }
        
        color = colors.get(level, '#ffffff')
        formatted_message = f"<span style='color: {color}'>[{timestamp}] {message}</span>"
        
        self.log_display.appendHtml(formatted_message)
        
        # 스크롤 맨 아래로
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_display(self):
        """디스플레이 업데이트"""
        if self.worker and self.worker.isRunning():
            self.checks_label.setText(f"확인: {self.worker.total_checks}회")
            self.signals_label.setText(f"신호: {self.worker.conditions_met_count}회")
    
    def cleanup(self):
        """정리 작업"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

# gui/main_window.py에 추가할 코드:
"""
기존 main_window.py의 create_tabs 메서드에 다음 라인 추가:

from gui.condition_monitoring_tab import ConditionMonitoringTab

def create_tabs(self):
    # 기존 탭들...
    self.create_dashboard_tab()
    self.create_positions_tab()
    self.create_settings_tab()
    
    # 새로운 조건 모니터링 탭 추가
    self.condition_tab = ConditionMonitoringTab()
    self.tab_widget.addTab(self.condition_tab, "🎯 조건 모니터링")
    
    # 기존 탭들 계속...

그리고 closeEvent에 정리 코드 추가:

def closeEvent(self, event):
    # 기존 정리 코드...
    
    # 조건 모니터링 탭 정리
    if hasattr(self, 'condition_tab'):
        self.condition_tab.cleanup()
    
    event.accept()
"""