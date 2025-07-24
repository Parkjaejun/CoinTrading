# gui/widgets.py
"""
GUI 위젯 컴포넌트들 - 완전한 버전
차트, 테이블, 제어 패널 등
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
    """실시간 가격 차트 위젯"""
    
    def __init__(self):
        super().__init__()
        self.price_data = []
        self.time_data = []
        self.max_points = 100
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
        
        header_layout.addWidget(self.symbol_label)
        header_layout.addStretch()
        header_layout.addWidget(self.price_label)
        header_layout.addWidget(self.change_label)
        
        layout.addLayout(header_layout)
        
        # 차트
        if PYQTGRAPH_AVAILABLE:
            self.chart = pg.PlotWidget()
            self.chart.setLabel('left', 'Price ($)')
            self.chart.setLabel('bottom', 'Time')
            self.chart.showGrid(x=True, y=True)
            self.chart.setMinimumHeight(300)
            
            # 가격 라인
            self.price_line = self.chart.plot(pen=pg.mkPen(color='#00ff00', width=2))
            
            layout.addWidget(self.chart)
        else:
            # pyqtgraph가 없는 경우 간단한 텍스트
            no_chart_label = QLabel("차트를 보려면 pyqtgraph를 설치하세요:\npip install pyqtgraph")
            no_chart_label.setAlignment(Qt.AlignCenter)
            no_chart_label.setMinimumHeight(300)
            no_chart_label.setStyleSheet("border: 1px solid #555; background-color: #2b2b2b; color: #999;")
            layout.addWidget(no_chart_label)
        
        self.setLayout(layout)
    
    def update_price(self, symbol: str, price: float, price_info: Dict = None):
        """가격 업데이트"""
        self.symbol_label.setText(symbol)
        self.price_label.setText(f"${price:,.2f}")
        
        # 변화율 표시
        if price_info and 'change_percent' in price_info:
            change_pct = price_info['change_percent']
            self.change_label.setText(f"{change_pct:+.2f}%")
            color = "#00ff00" if change_pct >= 0 else "#ff0000"
            self.change_label.setStyleSheet(f"color: {color}")
        
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

class PositionTableWidget(QWidget):
    """포지션 테이블 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 헤더
        header_label = QLabel("📊 현재 포지션")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header_label)
        
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
    
    def update_positions(self, positions: List[Dict]):
        """포지션 업데이트"""
        self.table.setRowCount(len(positions))
        
        for row, position in enumerate(positions):
            self.table.setItem(row, 0, QTableWidgetItem(position.get('symbol', '')))
            self.table.setItem(row, 1, QTableWidgetItem(position.get('side', '').upper()))
            self.table.setItem(row, 2, QTableWidgetItem(f"{position.get('size', 0):.6f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"${position.get('entry_price', 0):.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"${position.get('current_price', 0):.2f}"))
            
            # 손익 색상 설정
            pnl = position.get('unrealized_pnl', 0)
            pnl_item = QTableWidgetItem(f"${pnl:+.2f}")
            if pnl > 0:
                pnl_item.setForeground(QColor("#4CAF50"))
            elif pnl < 0:
                pnl_item.setForeground(QColor("#F44336"))
            self.table.setItem(row, 5, pnl_item)

class TradingControlWidget(QWidget):
    """거래 제어 위젯"""
    
    # 시그널
    start_trading_requested = pyqtSignal()
    stop_trading_requested = pyqtSignal()
    emergency_stop_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_trading = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 제어 그룹
        control_group = QGroupBox("🎮 거래 제어")
        control_layout = QGridLayout()
        
        # 시작/중지 버튼
        self.start_btn = QPushButton("▶️ 자동매매 시작")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.start_btn.clicked.connect(self.on_start_clicked)
        
        self.stop_btn = QPushButton("⏹️ 자동매매 중지")
        self.stop_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 10px;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        
        # 긴급 중지 버튼
        self.emergency_btn = QPushButton("🚨 긴급 중지")
        self.emergency_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; padding: 10px;")
        self.emergency_btn.clicked.connect(self.on_emergency_clicked)
        
        control_layout.addWidget(self.start_btn, 0, 0)
        control_layout.addWidget(self.stop_btn, 0, 1)
        control_layout.addWidget(self.emergency_btn, 1, 0, 1, 2)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 상태 표시
        status_group = QGroupBox("📊 상태")
        status_layout = QFormLayout()
        
        self.status_label = QLabel("대기 중")
        self.status_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        
        self.uptime_label = QLabel("00:00:00")
        self.trades_label = QLabel("0")
        self.pnl_label = QLabel("$0.00")
        
        status_layout.addRow("상태:", self.status_label)
        status_layout.addRow("실행 시간:", self.uptime_label)
        status_layout.addRow("총 거래:", self.trades_label)
        status_layout.addRow("손익:", self.pnl_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        self.setLayout(layout)
    
    def on_start_clicked(self):
        """시작 버튼 클릭"""
        self.is_trading = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("실행 중")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.start_trading_requested.emit()
    
    def on_stop_clicked(self):
        """중지 버튼 클릭"""
        self.is_trading = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("대기 중")
        self.status_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        self.stop_trading_requested.emit()
    
    def on_emergency_clicked(self):
        """긴급 중지 버튼 클릭"""
        self.is_trading = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("긴급 중지됨")
        self.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
        self.emergency_stop_requested.emit()
    
    def update_status(self, strategy_data: Dict):
        """상태 업데이트"""
        is_running = strategy_data.get('is_running', False)
        uptime = strategy_data.get('uptime', 0)
        total_trades = strategy_data.get('total_trades', 0)
        total_pnl = strategy_data.get('total_pnl', 0)
        
        # 실행 시간 포맷팅
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        
        self.uptime_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self.trades_label.setText(str(total_trades))
        
        # 손익 색상 설정
        pnl_color = "#4CAF50" if total_pnl >= 0 else "#F44336"
        self.pnl_label.setText(f"${total_pnl:+.2f}")
        self.pnl_label.setStyleSheet(f"color: {pnl_color}; font-weight: bold;")

class LogDisplayWidget(QWidget):
    """로그 표시 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 헤더
        header_layout = QHBoxLayout()
        header_label = QLabel("📝 거래 로그")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        # 클리어 버튼
        clear_btn = QPushButton("🗑️ 지우기")
        clear_btn.setMaximumWidth(80)
        clear_btn.clicked.connect(self.clear_logs)
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # 로그 텍스트
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                border: 1px solid #555;
            }
        """)
        
        layout.addWidget(self.log_text)
        self.setLayout(layout)
    
    def add_log(self, message: str, level: str = "INFO"):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 레벨별 색상
        colors = {
            "INFO": "#FFFFFF",
            "SUCCESS": "#4CAF50", 
            "WARNING": "#FFA500",
            "ERROR": "#F44336",
            "DEBUG": "#9E9E9E"
        }
        
        color = colors.get(level, "#FFFFFF")
        formatted_msg = f'<span style="color: {color}">[{timestamp}] {message}</span>'
        
        self.log_text.append(formatted_msg)
        
        # 스크롤을 맨 아래로
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)
    
    def clear_logs(self):
        """로그 지우기"""
        self.log_text.clear()

class SystemMonitorWidget(QWidget):
    """시스템 모니터링 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
        # 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(5000)  # 5초마다 업데이트
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 헤더
        header_label = QLabel("🖥️ 시스템 모니터")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header_label)
        
        # 시스템 정보
        info_layout = QFormLayout()
        
        self.cpu_label = QLabel("0%")
        self.memory_label = QLabel("0%")
        self.network_label = QLabel("0 KB/s")
        
        # CPU 진행바
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setMaximum(100)
        
        # 메모리 진행바
        self.memory_bar = QProgressBar()
        self.memory_bar.setMaximum(100)
        
        info_layout.addRow("CPU:", self.cpu_bar)
        info_layout.addRow("", self.cpu_label)
        info_layout.addRow("메모리:", self.memory_bar)
        info_layout.addRow("", self.memory_label)
        info_layout.addRow("네트워크:", self.network_label)
        
        layout.addLayout(info_layout)
        self.setLayout(layout)
    
    def update_stats(self):
        """시스템 통계 업데이트"""
        if PSUTIL_AVAILABLE:
            try:
                # CPU 사용률
                cpu_percent = psutil.cpu_percent()
                self.cpu_bar.setValue(int(cpu_percent))
                self.cpu_label.setText(f"{cpu_percent:.1f}%")
                
                # 메모리 사용률
                memory = psutil.virtual_memory()
                self.memory_bar.setValue(int(memory.percent))
                self.memory_label.setText(f"{memory.percent:.1f}%")
                
                # 네트워크 (간단한 표시)
                self.network_label.setText("N/A")
                
            except Exception as e:
                print(f"시스템 모니터링 오류: {e}")
        else:
            self.cpu_label.setText("psutil 필요")
            self.memory_label.setText("psutil 필요")