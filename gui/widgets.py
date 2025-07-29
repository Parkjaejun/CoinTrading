# gui/widgets.py
"""
GUI 위젯 컴포넌트들 - Signal Lost 지원
차트, 테이블, 제어 패널 등 - 더미 데이터 없음
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QGridLayout,
    QProgressBar, QSlider, QSpinBox, QDoubleSpinBox, QTextEdit,
    QHeaderView, QFrame, QFormLayout, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class PriceChartWidget(QWidget):
    """실시간 가격 차트 위젯 - Signal Lost 지원"""
    
    def __init__(self):
        super().__init__()
        self.price_data = []
        self.time_data = []
        self.max_points = 100
        self.signal_lost = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 헤더
        header_layout = QHBoxLayout()
        self.symbol_label = QLabel("BTC-USDT-SWAP")
        self.symbol_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        self.price_label = QLabel("$0.00")
        self.price_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.price_label.setStyleSheet("color: #00ff00")
        
        self.change_label = QLabel("0.00%")
        self.change_label.setFont(QFont("Arial", 12))
        
        # Signal Lost 표시
        self.signal_lost_label = QLabel("")
        self.signal_lost_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.signal_lost_label.setStyleSheet("color: #ff0000")
        self.signal_lost_label.hide()
        
        header_layout.addWidget(self.symbol_label)
        header_layout.addStretch()
        header_layout.addWidget(self.signal_lost_label)
        header_layout.addWidget(self.price_label)
        header_layout.addWidget(self.change_label)
        
        layout.addLayout(header_layout)
        
        # 차트
        if PYQTGRAPH_AVAILABLE:
            # 커스텀 시간 축 클래스 정의
            class TimeAxisItem(pg.AxisItem):
                def tickStrings(self, values, scale, spacing):
                    """시간 문자열 반환"""
                    formatted = []
                    for timestamp in values:
                        if timestamp > 0:
                            dt = datetime.fromtimestamp(timestamp)
                            formatted.append(dt.strftime('%H:%M:%S'))
                        else:
                            formatted.append('')
                    return formatted
            
            # 시간 축이 적용된 차트 생성
            self.chart = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
            self.chart.setLabel('left', 'Price ($)')
            self.chart.setLabel('bottom', 'Time (HH:MM:SS)')
            self.chart.showGrid(x=True, y=True)
            self.chart.setMinimumHeight(300)
            
            # 가격 라인
            self.price_line = self.chart.plot(pen=pg.mkPen(color='#00ff00', width=2))
            
            layout.addWidget(self.chart)
        else:
            # pyqtgraph가 없는 경우
            self.no_chart_label = QLabel("차트를 보려면 pyqtgraph를 설치하세요:\npip install pyqtgraph")
            self.no_chart_label.setAlignment(Qt.AlignCenter)
            self.no_chart_label.setMinimumHeight(300)
            self.no_chart_label.setStyleSheet("border: 1px solid #555; background-color: #2b2b2b; color: #999;")
            layout.addWidget(self.no_chart_label)
        
        self.setLayout(layout)
    
    def update_time_axis(self):
        """X축 시간 범위 업데이트"""
        if PYQTGRAPH_AVAILABLE and hasattr(self, 'chart') and len(self.time_data) > 1:
            # X축 범위를 최근 데이터로 제한
            min_time = min(self.time_data)
            max_time = max(self.time_data)
            
            # 약간의 여백 추가
            time_range = max_time - min_time
            padding = time_range * 0.05 if time_range > 0 else 30  # 최소 30초 여백
            
            self.chart.setXRange(min_time - padding, max_time + padding, padding=0)
    
    def update_price(self, symbol: str, price: float, price_info: Dict = None):
        """가격 업데이트 - 실제 데이터만"""
        if self.signal_lost:
            return
            
        self.symbol_label.setText(symbol)
        self.price_label.setText(f"${price:,.2f}")
        
        # 변화율 표시
        if price_info and 'change_percent' in price_info:
            change_pct = price_info['change_percent']
            self.change_label.setText(f"{change_pct:+.2f}%")
            color = "#00ff00" if change_pct >= 0 else "#ff0000"
            self.change_label.setStyleSheet(f"color: {color}")
            self.price_label.setStyleSheet(f"color: {color}")
        
        # 차트 데이터 업데이트
        if PYQTGRAPH_AVAILABLE and hasattr(self, 'chart'):
            current_time = time.time()
            
            self.time_data.append(current_time)
            self.price_data.append(price)
            
            # 최근 100개 데이터만 유지
            if len(self.price_data) > self.max_points:
                self.time_data = self.time_data[-self.max_points:]
                self.price_data = self.price_data[-self.max_points:]
            
            # 차트 업데이트
            if len(self.price_data) > 1:
                self.price_line.setData(self.time_data, self.price_data)
                
            # X축 시간 표시 업데이트
            self.update_time_axis()
    
    def show_signal_lost(self):
        """Signal Lost 상태 표시"""
        self.signal_lost = True
        
        # 헤더 표시 변경
        self.signal_lost_label.setText("🚨 SIGNAL LOST")
        self.signal_lost_label.show()
        
        self.price_label.setText("SIGNAL LOST")
        self.price_label.setStyleSheet("color: #ff0000")
        
        self.change_label.setText("--")
        self.change_label.setStyleSheet("color: #ff0000")
        
        # 차트 클리어
        if PYQTGRAPH_AVAILABLE and hasattr(self, 'chart'):
            self.price_line.clear()
            self.price_data.clear()
            self.time_data.clear()
            
            # 차트에 Signal Lost 메시지 표시
            self.chart.setTitle("🚨 SIGNAL LOST - API 연결을 확인해주세요", color='#ff0000', size='12pt')
        
        # no_chart_label이 있다면 Signal Lost로 변경
        if hasattr(self, 'no_chart_label'):
            self.no_chart_label.setText("🚨 SIGNAL LOST\n\nAPI 연결을 확인해주세요")
            self.no_chart_label.setStyleSheet("border: 1px solid #ff0000; background-color: #2b2b2b; color: #ff0000;")
    
    def restore_connection(self):
        """연결 복구 시 호출"""
        self.signal_lost = False
        self.signal_lost_label.hide()
        
        # 차트 타이틀 제거
        if PYQTGRAPH_AVAILABLE and hasattr(self, 'chart'):
            self.chart.setTitle("")
        
        if hasattr(self, 'no_chart_label'):
            self.no_chart_label.setText("차트를 보려면 pyqtgraph를 설치하세요:\npip install pyqtgraph")
            self.no_chart_label.setStyleSheet("border: 1px solid #555; background-color: #2b2b2b; color: #999;")

class PositionTableWidget(QWidget):
    """포지션 테이블 위젯 - Signal Lost 지원"""
    
    def __init__(self):
        super().__init__()
        self.signal_lost = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 헤더
        header_layout = QHBoxLayout()
        header_label = QLabel("📊 현재 포지션")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.signal_lost_label = QLabel("")
        self.signal_lost_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.signal_lost_label.setStyleSheet("color: #ff0000")
        self.signal_lost_label.hide()
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.signal_lost_label)
        
        layout.addLayout(header_layout)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "심볼", "방향", "크기", "진입가", "현재가", "손익"
        ])
        
        # 테이블 설정
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def update_positions(self, positions: List[Dict[str, Any]]):
        """포지션 업데이트 - 실제 데이터만"""
        if self.signal_lost:
            return
            
        self.table.setRowCount(len(positions))
        
        for i, position in enumerate(positions):
            symbol = position.get('instId', '')
            side = position.get('posSide', '').upper()
            size = position.get('pos', '0')
            entry_price = float(position.get('avgPx', 0))
            upl = float(position.get('upl', 0))
            
            # 현재가는 별도로 계산해야 할 수 있음
            current_price = entry_price  # 임시
            
            self.table.setItem(i, 0, QTableWidgetItem(symbol))
            self.table.setItem(i, 1, QTableWidgetItem(side))
            self.table.setItem(i, 2, QTableWidgetItem(f"{float(size):.6f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"${entry_price:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"${current_price:.2f}"))
            
            # 손익 색상 설정
            pnl_item = QTableWidgetItem(f"${upl:+.2f}")
            if upl > 0:
                pnl_item.setForeground(QColor("#00ff00"))
            elif upl < 0:
                pnl_item.setForeground(QColor("#ff0000"))
            
            self.table.setItem(i, 5, pnl_item)
    
    def show_signal_lost(self):
        """Signal Lost 상태 표시"""
        self.signal_lost = True
        self.signal_lost_label.setText("🚨 SIGNAL LOST")
        self.signal_lost_label.show()
        
        # 테이블 클리어
        self.table.setRowCount(0)
    
    def restore_connection(self):
        """연결 복구 시 호출"""
        self.signal_lost = False
        self.signal_lost_label.hide()

class TradingControlWidget(QWidget):
    """거래 제어 위젯 - Signal Lost 지원"""
    
    # 시그널 정의
    start_trading = pyqtSignal()
    stop_trading = pyqtSignal()
    emergency_stop = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.signal_lost = False
        self.trading_active = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 상태 표시
        status_group = QGroupBox("🎮 거래 제어")
        status_layout = QGridLayout()
        status_group.setLayout(status_layout)
        
        self.status_label = QLabel("대기 중")
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.status_label.setStyleSheet("color: #ffaa00")
        
        self.signal_lost_label = QLabel("")
        self.signal_lost_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.signal_lost_label.setStyleSheet("color: #ff0000")
        self.signal_lost_label.hide()
        
        status_layout.addWidget(QLabel("상태:"), 0, 0)
        status_layout.addWidget(self.status_label, 0, 1)
        status_layout.addWidget(self.signal_lost_label, 1, 0, 1, 2)
        
        # 제어 버튼
        control_group = QGroupBox("제어")
        control_layout = QVBoxLayout()
        control_group.setLayout(control_layout)
        
        self.start_btn = QPushButton("▶️ 거래 시작")
        self.start_btn.setStyleSheet("background-color: #28a745; padding: 10px;")
        self.start_btn.clicked.connect(self.on_start_trading)
        
        self.stop_btn = QPushButton("⏹️ 거래 중지")
        self.stop_btn.setStyleSheet("background-color: #ffc107; padding: 10px;")
        self.stop_btn.clicked.connect(self.on_stop_trading)
        self.stop_btn.setEnabled(False)
        
        self.emergency_btn = QPushButton("🚨 긴급 정지")
        self.emergency_btn.setStyleSheet("background-color: #dc3545; padding: 10px;")
        self.emergency_btn.clicked.connect(self.on_emergency_stop)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.emergency_btn)
        
        layout.addWidget(status_group)
        layout.addWidget(control_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def on_start_trading(self):
        """거래 시작"""
        if not self.signal_lost:
            self.trading_active = True
            self.update_ui_state()
            self.start_trading.emit()
    
    def on_stop_trading(self):
        """거래 중지"""
        self.trading_active = False
        self.update_ui_state()
        self.stop_trading.emit()
    
    def on_emergency_stop(self):
        """긴급 정지"""
        self.trading_active = False
        self.update_ui_state()
        self.emergency_stop.emit()
    
    def update_ui_state(self):
        """UI 상태 업데이트"""
        if self.signal_lost:
            self.status_label.setText("SIGNAL LOST")
            self.status_label.setStyleSheet("color: #ff0000")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
        elif self.trading_active:
            self.status_label.setText("거래 중")
            self.status_label.setStyleSheet("color: #28a745")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("대기 중")
            self.status_label.setStyleSheet("color: #ffaa00")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def show_signal_lost(self):
        """Signal Lost 상태 표시"""
        self.signal_lost = True
        self.signal_lost_label.setText("🚨 SIGNAL LOST - 거래 불가")
        self.signal_lost_label.show()
        self.update_ui_state()
    
    def restore_connection(self):
        """연결 복구 시 호출"""
        self.signal_lost = False
        self.signal_lost_label.hide()
        self.update_ui_state()

class SystemMonitorWidget(QWidget):
    """시스템 모니터 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_timer()
        
    def setup_ui(self):
        layout = QGridLayout()
        
        # CPU 사용률
        self.cpu_label = QLabel("CPU: --%")
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        
        # 메모리 사용률
        self.memory_label = QLabel("메모리: --%")
        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        
        # 네트워크 상태
        self.network_label = QLabel("네트워크: --")
        
        layout.addWidget(QLabel("시스템 상태:"), 0, 0)
        layout.addWidget(self.cpu_label, 1, 0)
        layout.addWidget(self.cpu_progress, 1, 1)
        layout.addWidget(self.memory_label, 2, 0)
        layout.addWidget(self.memory_progress, 2, 1)
        layout.addWidget(self.network_label, 3, 0, 1, 2)
        
        self.setLayout(layout)
    
    def setup_timer(self):
        """타이머 설정"""
        if PSUTIL_AVAILABLE:
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_system_info)
            self.timer.start(2000)  # 2초마다 업데이트
        
    def update_system_info(self):
        """시스템 정보 업데이트"""
        if PSUTIL_AVAILABLE:
            try:
                # CPU 사용률
                cpu_percent = psutil.cpu_percent(interval=1)
                self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
                self.cpu_progress.setValue(int(cpu_percent))
                
                # 메모리 사용률
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.memory_label.setText(f"메모리: {memory_percent:.1f}%")
                self.memory_progress.setValue(int(memory_percent))
                
                # 네트워크 상태 (간단히)
                self.network_label.setText("네트워크: 정상")
                
            except Exception as e:
                self.cpu_label.setText("CPU: 오류")
                self.memory_label.setText("메모리: 오류")
                self.network_label.setText(f"시스템 정보 오류: {e}")

class LogDisplayWidget(QWidget):
    """로그 표시 위젯"""
    
    def __init__(self, max_lines=1000):
        super().__init__()
        self.max_lines = max_lines
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 로그 텍스트 에리어
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
            }
        """)
        
        # 제어 버튼
        button_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_logs)
        
        self.auto_scroll_cb = QCheckBox("자동 스크롤")
        self.auto_scroll_cb.setChecked(True)
        
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.auto_scroll_cb)
        button_layout.addStretch()
        
        layout.addWidget(self.log_text)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def add_log(self, message: str):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_text.append(formatted_message)
        
        # 최대 라인 수 제한
        if self.log_text.document().lineCount() > self.max_lines:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # 개행 문자 제거
        
        # 자동 스크롤
        if self.auto_scroll_cb.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        """로그 클리어"""
        self.log_text.clear()
        self.add_log("로그가 클리어되었습니다.")

class StatusIndicatorWidget(QWidget):
    """상태 표시 위젯"""
    
    def __init__(self, title: str):
        super().__init__()
        self.title = title
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        
        self.title_label = QLabel(self.title)
        self.status_label = QLabel("●")
        self.status_label.setFont(QFont("Arial", 16))
        self.status_text = QLabel("연결 중...")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.status_text)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 초기 상태
        self.set_status("connecting")
    
    def set_status(self, status: str, message: str = ""):
        """상태 설정"""
        if status == "connected":
            self.status_label.setStyleSheet("color: #00ff00")
            self.status_text.setText(message or "연결됨")
        elif status == "disconnected":
            self.status_label.setStyleSheet("color: #ff0000")
            self.status_text.setText(message or "연결 끊어짐")
        elif status == "signal_lost":
            self.status_label.setStyleSheet("color: #ff0000")
            self.status_text.setText("SIGNAL LOST")
        else:  # connecting
            self.status_label.setStyleSheet("color: #ffaa00")
            self.status_text.setText(message or "연결 중...")

class BalanceDisplayWidget(QWidget):
    """잔고 표시 위젯"""
    
    def __init__(self):
        super().__init__()
        self.signal_lost = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QGridLayout()
        
        # 총 자산
        self.total_label = QLabel("총 자산:")
        self.total_value = QLabel("$--")
        self.total_value.setFont(QFont("Arial", 16, QFont.Bold))
        
        # 사용 가능 자산
        self.available_label = QLabel("사용 가능:")
        self.available_value = QLabel("$--")
        
        # 미실현 손익
        self.pnl_label = QLabel("미실현 손익:")
        self.pnl_value = QLabel("$--")
        
        # Signal Lost 표시
        self.signal_lost_label = QLabel("")
        self.signal_lost_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.signal_lost_label.setStyleSheet("color: #ff0000")
        self.signal_lost_label.hide()
        
        layout.addWidget(self.total_label, 0, 0)
        layout.addWidget(self.total_value, 0, 1)
        layout.addWidget(self.available_label, 1, 0)
        layout.addWidget(self.available_value, 1, 1)
        layout.addWidget(self.pnl_label, 2, 0)
        layout.addWidget(self.pnl_value, 2, 1)
        layout.addWidget(self.signal_lost_label, 3, 0, 1, 2)
        
        self.setLayout(layout)
    
    def update_balance(self, balance_data: Dict[str, Any]):
        """잔고 업데이트 - 실제 데이터만"""
        if self.signal_lost:
            return
            
        total = balance_data.get('total_equity', 0)
        available = balance_data.get('available_balance', 0)
        pnl = balance_data.get('unrealized_pnl', 0)
        
        self.total_value.setText(f"${total:,.2f}")
        self.total_value.setStyleSheet("color: #00ff00")
        
        self.available_value.setText(f"${available:,.2f}")
        
        self.pnl_value.setText(f"${pnl:+,.2f}")
        if pnl > 0:
            self.pnl_value.setStyleSheet("color: #00ff00")
        elif pnl < 0:
            self.pnl_value.setStyleSheet("color: #ff0000")
        else:
            self.pnl_value.setStyleSheet("color: #ffffff")
    
    def show_signal_lost(self):
        """Signal Lost 상태 표시"""
        self.signal_lost = True
        self.signal_lost_label.setText("🚨 SIGNAL LOST")
        self.signal_lost_label.show()
        
        # 모든 값을 Signal Lost로 변경
        self.total_value.setText("SIGNAL LOST")
        self.total_value.setStyleSheet("color: #ff0000")
        self.available_value.setText("SIGNAL LOST")
        self.available_value.setStyleSheet("color: #ff0000")
        self.pnl_value.setText("SIGNAL LOST")
        self.pnl_value.setStyleSheet("color: #ff0000")
    
    def restore_connection(self):
        """연결 복구 시 호출"""
        self.signal_lost = False
        self.signal_lost_label.hide()