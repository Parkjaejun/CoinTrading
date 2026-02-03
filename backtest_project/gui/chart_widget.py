# gui/chart_widget.py
"""
백테스트 차트 위젯
- matplotlib 기반 캔들스틱/라인 차트
- EMA 라인 표시
- 진입/청산 마커 표시
"""

from typing import List, Dict, Optional
from datetime import datetime

import pandas as pd
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QCheckBox, QLabel, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates


class BacktestChartWidget(QWidget):
    """백테스트 차트 위젯"""
    
    # 마커 클릭 시그널
    marker_clicked = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.df: Optional[pd.DataFrame] = None
        self.markers: List[Dict] = []
        self.ema_visible = {
            'ema20': True,
            'ema50': True,
            'ema100': True,
            'ema150': True,
            'ema200': True,
        }
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 상단 컨트롤 바
        control_frame = QFrame()
        control_frame.setMaximumHeight(40)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        # 차트 타입 선택
        control_layout.addWidget(QLabel("차트:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["라인", "캔들스틱"])
        self.chart_type_combo.currentIndexChanged.connect(self._on_chart_type_changed)
        control_layout.addWidget(self.chart_type_combo)
        
        control_layout.addSpacing(20)
        
        # EMA 체크박스들
        control_layout.addWidget(QLabel("EMA:"))
        
        self.ema_checks = {}
        ema_colors = {
            'ema20': ('#FF6B6B', '20'),
            'ema50': ('#4ECDC4', '50'),
            'ema100': ('#45B7D1', '100'),
            'ema150': ('#96CEB4', '150'),
            'ema200': ('#FFEAA7', '200'),
        }
        
        for key, (color, label) in ema_colors.items():
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(f"QCheckBox {{ color: {color}; }}")
            cb.stateChanged.connect(lambda state, k=key: self._on_ema_toggle(k, state))
            self.ema_checks[key] = cb
            control_layout.addWidget(cb)
        
        control_layout.addStretch()
        
        # 리셋 버튼
        reset_btn = QPushButton("🔄 리셋")
        reset_btn.clicked.connect(self._reset_view)
        control_layout.addWidget(reset_btn)
        
        layout.addWidget(control_frame)
        
        # matplotlib Figure
        self.figure = Figure(figsize=(12, 6), dpi=100)
        self.figure.patch.set_facecolor('#1e1e1e')
        
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #1e1e1e;")
        
        # 네비게이션 툴바
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #2b2b2b; color: white;")
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)
        
        # 서브플롯 생성
        self.ax = self.figure.add_subplot(111)
        self._style_axis()
    
    def _style_axis(self):
        """축 스타일링"""
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.spines['bottom'].set_color('#3a3a3a')
        self.ax.spines['top'].set_color('#3a3a3a')
        self.ax.spines['left'].set_color('#3a3a3a')
        self.ax.spines['right'].set_color('#3a3a3a')
        self.ax.grid(True, color='#3a3a3a', linestyle='--', linewidth=0.5, alpha=0.5)
    
    def set_data(self, df: pd.DataFrame):
        """OHLC 데이터 설정"""
        self.df = df.copy()
        
        # datetime 컬럼 확인
        if 'datetime_utc' in self.df.columns:
            self.df['datetime'] = pd.to_datetime(self.df['datetime_utc'])
        elif 'timestamp' in self.df.columns:
            self.df['datetime'] = pd.to_datetime(self.df['timestamp'], unit='ms')
        
        self._redraw()
    
    def set_markers(self, markers: List[Dict]):
        """진입/청산 마커 설정"""
        self.markers = markers
        self._redraw()
    
    def _on_chart_type_changed(self, index):
        """차트 타입 변경"""
        self._redraw()
    
    def _on_ema_toggle(self, key: str, state: int):
        """EMA 표시 토글"""
        self.ema_visible[key] = (state == Qt.Checked)
        self._redraw()
    
    def _reset_view(self):
        """뷰 리셋"""
        self.toolbar.home()
        self._redraw()
    
    def _redraw(self):
        """차트 다시 그리기"""
        if self.df is None or self.df.empty:
            return
        
        self.ax.clear()
        self._style_axis()
        
        df = self.df
        
        # 차트 타입에 따라 그리기
        if self.chart_type_combo.currentIndex() == 0:  # 라인
            self._draw_line_chart(df)
        else:  # 캔들스틱
            self._draw_candlestick(df)
        
        # EMA 라인 그리기
        self._draw_ema_lines(df)
        
        # 마커 그리기
        self._draw_markers()
        
        # X축 날짜 포맷
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.figure.autofmt_xdate()
        
        # 범례
        self.ax.legend(loc='upper left', facecolor='#2b2b2b', 
                       edgecolor='#3a3a3a', labelcolor='white', fontsize=8)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _draw_line_chart(self, df: pd.DataFrame):
        """라인 차트 그리기"""
        self.ax.plot(df['datetime'], df['close'], color='#00d4aa', 
                    linewidth=1, label='Close', alpha=0.9)
    
    def _draw_candlestick(self, df: pd.DataFrame):
        """캔들스틱 차트 그리기"""
        width = 0.0004  # 캔들 너비 (30분봉용)
        
        for idx, row in df.iterrows():
            dt = row['datetime']
            o, h, l, c = row['open'], row['high'], row['low'], row['close']
            
            # 색상 결정
            if c >= o:
                color = '#26a69a'  # 상승 (녹색)
                body_bottom = o
            else:
                color = '#ef5350'  # 하락 (빨강)
                body_bottom = c
            
            body_height = abs(c - o)
            
            # 캔들 몸통
            rect = Rectangle(
                (mdates.date2num(dt) - width/2, body_bottom),
                width, body_height,
                facecolor=color, edgecolor=color
            )
            self.ax.add_patch(rect)
            
            # 꼬리 (위/아래)
            self.ax.plot([mdates.date2num(dt), mdates.date2num(dt)], 
                        [l, h], color=color, linewidth=0.8)
        
        # 축 범위 조정
        self.ax.set_xlim(df['datetime'].min(), df['datetime'].max())
        self.ax.set_ylim(df['low'].min() * 0.995, df['high'].max() * 1.005)
    
    def _draw_ema_lines(self, df: pd.DataFrame):
        """EMA 라인 그리기"""
        ema_config = {
            'ema20': ('ema_e20', '#FF6B6B', 'EMA 20'),
            'ema50': ('ema_e50', '#4ECDC4', 'EMA 50'),
            'ema100': ('ema_lx_slow', '#45B7D1', 'EMA 100'),
            'ema150': ('ema_trend_fast', '#96CEB4', 'EMA 150'),
            'ema200': ('ema_trend_slow', '#FFEAA7', 'EMA 200'),
        }
        
        for key, (col, color, label) in ema_config.items():
            if self.ema_visible.get(key, True) and col in df.columns:
                self.ax.plot(df['datetime'], df[col], color=color, 
                            linewidth=1, label=label, alpha=0.7)
    
    def _draw_markers(self):
        """진입/청산 마커 그리기"""
        if not self.markers:
            return
        
        for marker in self.markers:
            dt = marker.get('time')
            price = marker.get('price')
            event_type = marker.get('type')
            side = marker.get('side')
            mode = marker.get('mode', 'REAL')
            
            if dt is None or price is None:
                continue
            
            # 마커 스타일 결정
            if event_type == "ENTRY":
                if side == "LONG":
                    marker_style = '^'  # 위 삼각형
                    color = '#00ff88' if mode == "REAL" else '#00ff8888'
                    size = 100
                else:
                    marker_style = 'v'  # 아래 삼각형
                    color = '#ff6b6b' if mode == "REAL" else '#ff6b6b88'
                    size = 100
            elif event_type == "EXIT":
                marker_style = 'o'  # 원
                color = '#ffaa00' if mode == "REAL" else '#ffaa0088'
                size = 80
            else:
                continue
            
            self.ax.scatter(dt, price, marker=marker_style, s=size, 
                           c=color, edgecolors='white', linewidths=0.5,
                           zorder=10)
    
    def highlight_trade(self, entry_time, exit_time, entry_price, exit_price, side):
        """특정 거래 구간 하이라이트"""
        if self.df is None:
            return
        
        # 기존 하이라이트 제거 후 다시 그리기
        self._redraw()
        
        # 거래 구간 배경색
        try:
            color = '#00ff8833' if side == "LONG" else '#ff6b6b33'
            self.ax.axvspan(entry_time, exit_time, alpha=0.3, color=color)
            
            # 진입/청산 가격 수평선
            self.ax.axhline(y=entry_price, color='#00ff88', linestyle='--', 
                           linewidth=1, alpha=0.5)
            self.ax.axhline(y=exit_price, color='#ffaa00', linestyle='--', 
                           linewidth=1, alpha=0.5)
            
            self.canvas.draw()
        except Exception as e:
            print(f"하이라이트 오류: {e}")
    
    def zoom_to_range(self, start_time, end_time, padding_ratio=0.1):
        """특정 기간으로 줌"""
        if self.df is None:
            return
        
        try:
            # 시간 범위 계산
            duration = (end_time - start_time).total_seconds()
            padding = pd.Timedelta(seconds=duration * padding_ratio)
            
            view_start = start_time - padding
            view_end = end_time + padding
            
            # 해당 구간 데이터
            mask = (self.df['datetime'] >= view_start) & (self.df['datetime'] <= view_end)
            subset = self.df[mask]
            
            if not subset.empty:
                self.ax.set_xlim(view_start, view_end)
                self.ax.set_ylim(subset['low'].min() * 0.998, subset['high'].max() * 1.002)
                self.canvas.draw()
        except Exception as e:
            print(f"줌 오류: {e}")
