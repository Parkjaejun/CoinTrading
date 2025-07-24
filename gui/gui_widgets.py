# gui/widgets.py
"""
GUI 위젯 컴포넌트들
차트, 테이블, 제어 패널 등
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QGridLayout,
    QProgressBar, QSlider, QSpinBox, QDoubleSpinBox, QTextEdit,
    QHeaderView, QFrame, QFormLayout
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
            no_chart_label = QLabel("차트를 보려면 pyqtgraph를 설치하세요:\npip install pyqtgraph")
            no_chart_label.setAlignment(Qt.AlignCenter)
            no_chart_label.setStyleSheet("color: #ffaa00; font-size: 14px;")
            layout.addWidget(no_chart_label)
        
        self.setLayout(layout)
    
    def update_price(self, symbol: str, price: float, price_info: Dict[str, Any]):
        """가격 업데이트"""
        self.symbol_label.setText(symbol)
        self.price_label.setText(f"${price:,.2f}")
        
        # 변화율 계산 및 표시
        change_24h = price_info.get('change_24h', 0)
        if change_24h > 0:
            self.change_label.setText(f"+{change_24h:.2f}%")
            self.change_label.setStyleSheet("color: #00ff00")
            self.price_label.setStyleSheet("color: #00ff00")
        elif change_24h < 0:
            self.change_label.setText(f"{change_24h:.2f}%")
            self.change_label.setStyleSheet("color: #ff4444")
            self.price_label.setStyleSheet("color: #ff4444")
        else:
            self.change_label.setText("0.00%")
            self.change_label.setStyleSheet("color: #ffffff")
            self.price_label.setStyleSheet("color: #ffffff")
        
        # 차트 업데이트
        if PYQTGRAPH_AVAILABLE and hasattr(self, 'chart'):
            current_time = time.time()
            
            self.time_data.append(current_time)
            self.price_data.append(price)
            
            # 최대 포인트 수 제한
            if len(self.price_data) > self.max_points:
                self.time_data = self.time_data[-self.max_points:]
                self.price_data = self.price_data[-self.max_points:]
            
            # 차트 업데이트
            if len(self.price_data) > 1:
                self.price_line.setData(self.time_data, self.price_data)

class PositionTableWidget(QWidget):
    """포지션 테이블 위젯"""
    
    position_close_requested = pyqtSignal(str)  # 포지션 ID
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 헤더
        header_layout = QHBoxLayout()
        title_label = QLabel("💼 활성 포지션")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        # 전체 청산 버튼
        self.close_all_btn = QPushButton("🚨 전체 청산")
        self.close_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_all_btn)
        
        layout.addLayout(header_layout)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "심볼", "방향", "수량", "진입가", "현재가", "PnL", "액션"
        ])
        
        # 헤더 스타일
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def update_positions(self, positions: List[Dict[str, Any]]):
        """포지션 데이터 업데이트"""
        self.table.setRowCount(len(positions))
        
        for row, position in enumerate(positions):
            # 기본 정보
            self.table.setItem(row, 0, QTableWidgetItem(position.get('symbol', '')))
            self.table.setItem(row, 1, QTableWidgetItem(position.get('side', '').upper()))
            self.table.setItem(row, 2, QTableWidgetItem(f"{position.get('size', 0):.6f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"${position.get('entry_price', 0):.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"${position.get('current_price', 0):.2f}"))
            
            # PnL 색상 설정
            pnl = position.get('pnl', 0)
            pnl_item = QTableWidgetItem(f"${pnl:+.2f}")
            if pnl > 0:
                pnl_item.setForeground(QColor("#00ff00"))
            elif pnl < 0:
                pnl_item.setForeground(QColor("#ff4444"))
            self.table.setItem(row, 5, pnl_item)
            
            # 청산 버튼
            close_btn = QPushButton("청산")
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff6600;
                    color: white;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #ff8833;
                }
            """)
            
            position_id = position.get('id', '')
            close_btn.clicked.connect(lambda checked, pid=position_id: self.position_close_requested.emit(pid))
            
            self.table.setCellWidget(row, 6, close_btn)

class TradingControlWidget(QWidget):
    """거래 제어 위젯"""
    
    start_trading_requested = pyqtSignal()
    stop_trading_requested = pyqtSignal()
    emergency_stop_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.trading_active = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 제어 그룹
        control_group = QGroupBox("🎯 거래 시스템 제어")
        control_layout = QGridLayout()
        
        # 시작/중지 버튼
        self.start_btn = QPushButton("▶️ 거래 시작")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #5CBF60;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
        """)
        
        self.stop_btn = QPushButton("⏹️ 거래 중지")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #ffad33;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
        """)
        self.stop_btn.setEnabled(False)
        
        # 긴급 정지 버튼
        self.emergency_btn = QPushButton("🚨 긴급 정지")
        self.emergency_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #f66356;
            }
        """)
        
        control_layout.addWidget(self.start_btn, 0, 0)
        control_layout.addWidget(self.stop_btn, 0, 1)
        control_layout.addWidget(self.emergency_btn, 1, 0, 1, 2)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 상태 그룹
        status_group = QGroupBox("📊 시스템 상태")
        status_layout = QFormLayout()
        
        self.status_label = QLabel("중지됨")
        self.status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        
        self.uptime_label = QLabel("00:00:00")
        self.active_strategies_label = QLabel("0")
        self.connection_status_label = QLabel("연결 중...")
        
        status_layout.addRow("거래 상태:", self.status_label)
        status_layout.addRow("가동 시간:", self.uptime_label)
        status_layout.addRow("활성 전략:", self.active_strategies_label)
        status_layout