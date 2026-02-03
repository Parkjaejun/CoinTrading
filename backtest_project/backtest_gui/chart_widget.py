# backtest_gui/chart_widget.py
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
    QCheckBox, QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates


class BacktestChartWidget(QWidget):
    """백테스트 차트 위젯"""
    
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
        self._pending_redraw = False
        
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
        
        control_layout.addWidget(QLabel("차트:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["라인", "캔들스틱"])
        self.chart_type_combo.currentIndexChanged.connect(self._on_chart_type_changed)
        control_layout.addWidget(self.chart_type_combo)
        
        control_layout.addSpacing(20)
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
        
        reset_btn = QPushButton("🔄 리셋")
        reset_btn.clicked.connect(self._reset_view)
        control_layout.addWidget(reset_btn)
        
        layout.addWidget(control_frame)
        
        # matplotlib Figure - 고정 크기로 초기화
        self.figure = Figure(figsize=(10, 5), dpi=100, tight_layout=False)
        self.figure.patch.set_facecolor('#1e1e1e')
        # subplots_adjust로 여백 수동 설정 (tight_layout 대신)
        self.figure.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.15)
        
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #1e1e1e;")
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumSize(400, 200)
        
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #2b2b2b; color: white;")
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)
        
        self.ax = self.figure.add_subplot(111)
        self._style_axis()
    
    def _style_axis(self):
        """축 스타일링"""
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white', labelsize=8)
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        for spine in ['bottom', 'top', 'left', 'right']:
            self.ax.spines[spine].set_color('#3a3a3a')
        self.ax.grid(True, color='#3a3a3a', linestyle='--', linewidth=0.5, alpha=0.5)
    
    def showEvent(self, event):
        """위젯이 화면에 표시될 때 호출"""
        super().showEvent(event)
        if self._pending_redraw:
            QTimer.singleShot(100, self._redraw)
            self._pending_redraw = False
    
    def set_data(self, df: pd.DataFrame):
        """OHLC 데이터 설정"""
        if df is None or df.empty:
            return
        
        self.df = df.copy()
        
        # datetime 컬럼 확보
        if 'datetime_utc' in self.df.columns:
            self.df['datetime'] = pd.to_datetime(self.df['datetime_utc'])
        elif 'datetime' not in self.df.columns:
            if 'timestamp' in self.df.columns:
                ts = self.df['timestamp']
                if pd.api.types.is_numeric_dtype(ts):
                    if ts.iloc[0] > 1e12:
                        self.df['datetime'] = pd.to_datetime(ts, unit='ms')
                    else:
                        self.df['datetime'] = pd.to_datetime(ts, unit='s')
                else:
                    self.df['datetime'] = pd.to_datetime(ts)
            else:
                self.df['datetime'] = pd.date_range(start='2026-01-01', periods=len(self.df), freq='30min')
        
        # 위젯이 표시된 상태면 바로 그리기, 아니면 대기
        if self.isVisible() and self.canvas.width() > 0:
            self._redraw()
        else:
            self._pending_redraw = True
    
    def set_markers(self, markers: List[Dict]):
        """진입/청산 마커 설정"""
        self.markers = markers
        if self.isVisible() and self.canvas.width() > 0:
            self._redraw()
    
    def _on_chart_type_changed(self, index):
        self._redraw()
    
    def _on_ema_toggle(self, key: str, state: int):
        self.ema_visible[key] = (state == Qt.Checked)
        self._redraw()
    
    def _reset_view(self):
        self.toolbar.home()
        self._redraw()
    
    def _redraw(self):
        """차트 다시 그리기"""
        if self.df is None or self.df.empty:
            return
        
        if 'datetime' not in self.df.columns or 'close' not in self.df.columns:
            return
        
        if len(self.df) < 2:
            return
        
        # 캔버스 크기 확인
        if self.canvas.width() <= 0 or self.canvas.height() <= 0:
            self._pending_redraw = True
            return
        
        self.ax.clear()
        self._style_axis()
        
        df = self.df
        
        # 차트 그리기
        if self.chart_type_combo.currentIndex() == 0:
            self._draw_line_chart(df)
        else:
            self._draw_candlestick(df)
        
        self._draw_ema_lines(df)
        self._draw_markers()
        
        # X축 포맷
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        # X축 레이블 회전
        for label in self.ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        
        # 범례
        handles, labels = self.ax.get_legend_handles_labels()
        if handles:
            self.ax.legend(loc='upper left', facecolor='#2b2b2b', 
                          edgecolor='#3a3a3a', labelcolor='white', fontsize=8)
        
        # 여백 재조정 (tight_layout 대신)
        self.figure.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.18)
        
        self.canvas.draw_idle()
    
    def _draw_line_chart(self, df: pd.DataFrame):
        """라인 차트"""
        self.ax.plot(df['datetime'], df['close'], color='#00d4aa', 
                    linewidth=1.2, label='Close')
        
        # 축 범위
        y_min, y_max = df['close'].min(), df['close'].max()
        margin = (y_max - y_min) * 0.05
        self.ax.set_ylim(y_min - margin, y_max + margin)
    
    def _draw_candlestick(self, df: pd.DataFrame):
        """캔들스틱 차트"""
        required = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required):
            self._draw_line_chart(df)
            return
        
        # 캔들 너비 계산
        if len(df) > 1:
            time_diff = (df['datetime'].iloc[1] - df['datetime'].iloc[0]).total_seconds()
            width = time_diff / 86400 * 0.8  # 80% 너비
        else:
            width = 0.02
        
        up = df[df['close'] >= df['open']]
        down = df[df['close'] < df['open']]
        
        # 상승 캔들 (녹색)
        if not up.empty:
            self.ax.bar(up['datetime'], up['close'] - up['open'], width,
                       bottom=up['open'], color='#26a69a', edgecolor='#26a69a')
            self.ax.vlines(up['datetime'], up['low'], up['high'], color='#26a69a', linewidth=0.8)
        
        # 하락 캔들 (빨강)
        if not down.empty:
            self.ax.bar(down['datetime'], down['open'] - down['close'], width,
                       bottom=down['close'], color='#ef5350', edgecolor='#ef5350')
            self.ax.vlines(down['datetime'], down['low'], down['high'], color='#ef5350', linewidth=0.8)
        
        # 축 범위
        y_min, y_max = df['low'].min(), df['high'].max()
        margin = (y_max - y_min) * 0.05
        self.ax.set_ylim(y_min - margin, y_max + margin)
    
    def _draw_ema_lines(self, df: pd.DataFrame):
        """EMA 라인"""
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
        """진입/청산 마커"""
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
            
            # datetime 변환 (문자열인 경우 처리)
            if isinstance(dt, str):
                dt = pd.to_datetime(dt)
            elif not isinstance(dt, (datetime, pd.Timestamp)):
                dt = pd.to_datetime(dt)
            
            if event_type == "ENTRY":
                if side == "LONG":
                    m_style, color = '^', '#00ff88' if mode == "REAL" else '#00ff8888'
                else:
                    m_style, color = 'v', '#ff6b6b' if mode == "REAL" else '#ff6b6b88'
                size = 100
            elif event_type == "EXIT":
                m_style, color = 'o', '#ffaa00' if mode == "REAL" else '#ffaa0088'
                size = 80
            else:
                continue
            
            self.ax.scatter(dt, price, marker=m_style, s=size, 
                           c=color, edgecolors='white', linewidths=0.5, zorder=10)
    
    def highlight_trade(self, entry_time, exit_time, entry_price, exit_price, side):
        """특정 거래 구간 하이라이트"""
        if self.df is None:
            return
        
        self._redraw()
        
        color = '#00ff8833' if side == "LONG" else '#ff6b6b33'
        self.ax.axvspan(entry_time, exit_time, alpha=0.3, color=color)
        self.ax.axhline(y=entry_price, color='#00ff88', linestyle='--', linewidth=1, alpha=0.5)
        self.ax.axhline(y=exit_price, color='#ffaa00', linestyle='--', linewidth=1, alpha=0.5)
        
        self.canvas.draw_idle()
    
    def zoom_to_range(self, start_time, end_time, padding_ratio=0.1):
        """특정 기간으로 줌"""
        if self.df is None:
            return
        
        duration = (end_time - start_time).total_seconds()
        padding = pd.Timedelta(seconds=duration * padding_ratio)
        
        view_start = start_time - padding
        view_end = end_time + padding
        
        mask = (self.df['datetime'] >= view_start) & (self.df['datetime'] <= view_end)
        subset = self.df[mask]
        
        if not subset.empty:
            self.ax.set_xlim(view_start, view_end)
            if 'low' in subset.columns and 'high' in subset.columns:
                self.ax.set_ylim(subset['low'].min() * 0.998, subset['high'].max() * 1.002)
            self.canvas.draw_idle()
