# gui/dashboard_chart_widget.py
"""
대시보드용 누적 차트 위젯

특징:
- 최대 1주일(약 336개 30분봉) 데이터 누적 표시
- 가격 차트 (캔들스틱/라인)
- EMA 라인 표시 (20, 50, 100, 150, 200)
- 실시간 업데이트

수정사항 (2024-02-12):
- update_price_only(): 데이터 없을 때 새 DataFrame 생성하도록 개선 (수정됨)
- 30분 단위 새 캔들 자동 생성 로직 추가 (수정됨)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCheckBox, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def ema(series: pd.Series, period: int) -> pd.Series:
    """지수이동평균 계산"""
    return series.ewm(span=period, adjust=False).mean()


class DashboardChartWidget(QWidget):
    """대시보드용 실시간 차트 위젯 - 가격 + EMA 통합"""
    
    chart_updated = pyqtSignal()
    
    # EMA 설정
    EMA_CONFIG = {
        'ema_20': {'period': 20, 'color': '#FF6B6B', 'label': 'EMA 20', 'width': 1.0},
        'ema_50': {'period': 50, 'color': '#4ECDC4', 'label': 'EMA 50', 'width': 1.0},
        'ema_100': {'period': 100, 'color': '#45B7D1', 'label': 'EMA 100', 'width': 1.2},
        'ema_150': {'period': 150, 'color': '#96CEB4', 'label': 'EMA 150', 'width': 1.5},
        'ema_200': {'period': 200, 'color': '#FFEAA7', 'label': 'EMA 200', 'width': 1.5},
    }
    
    MAX_CANDLES = 500
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.df: Optional[pd.DataFrame] = None
        self.chart_type = 'line'
        
        self.ema_visible = {k: True for k in self.EMA_CONFIG.keys()}
        self._pending_redraw = False
        
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 상단 컨트롤 바
        control_frame = QFrame()
        control_frame.setMaximumHeight(45)
        control_frame.setStyleSheet("""
            QFrame { background-color: #2b2b2b; border-radius: 4px; }
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 5, 10, 5)
        control_layout.setSpacing(15)
        
        # 차트 타입
        control_layout.addWidget(QLabel("차트:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["라인", "캔들스틱"])
        self.chart_type_combo.setMinimumWidth(80)
        self.chart_type_combo.currentIndexChanged.connect(self._on_chart_type_changed)
        control_layout.addWidget(self.chart_type_combo)
        
        control_layout.addSpacing(20)
        control_layout.addWidget(QLabel("EMA:"))
        
        # EMA 체크박스
        self.ema_checks = {}
        for key, config in self.EMA_CONFIG.items():
            cb = QCheckBox(str(config['period']))
            cb.setChecked(True)
            cb.setStyleSheet(f"QCheckBox {{ color: {config['color']}; font-weight: bold; }}")
            cb.toggled.connect(lambda checked, k=key: self._toggle_ema(k, checked))
            self.ema_checks[key] = cb
            control_layout.addWidget(cb)
        
        control_layout.addStretch()
        
        self.info_label = QLabel("데이터 대기 중...")
        self.info_label.setStyleSheet("color: #888888; font-size: 11px;")
        control_layout.addWidget(self.info_label)
        
        layout.addWidget(control_frame)
        
        # 차트 영역
        self.figure = Figure(figsize=(10, 6), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.ax = self.figure.add_subplot(111)
        self._setup_axes()
        
        layout.addWidget(self.canvas)
        
    def _setup_axes(self):
        """축 초기 설정"""
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='#888888', labelsize=9)
        for spine in self.ax.spines.values():
            spine.set_color('#3a3a3a')
        self.ax.grid(True, linestyle='--', alpha=0.3, color='#3a3a3a')
        
    def _on_chart_type_changed(self, index):
        self.chart_type = 'line' if index == 0 else 'candlestick'
        self._schedule_redraw()
        
    def _toggle_ema(self, ema_key: str, visible: bool):
        self.ema_visible[ema_key] = visible
        self._schedule_redraw()
        
    def _schedule_redraw(self):
        if self._pending_redraw:
            return
        self._pending_redraw = True
        QTimer.singleShot(50, self._do_redraw)
        
    def _do_redraw(self):
        self._pending_redraw = False
        self._draw_chart()
        
    def set_historical_data(self, df: pd.DataFrame):
        """과거 데이터 일괄 로드"""
        if df is None or len(df) == 0:
            return
        
        self.df = df.copy()
        
        if 'datetime' not in self.df.columns and 'timestamp' in self.df.columns:
            self.df['datetime'] = pd.to_datetime(self.df['timestamp'], unit='ms')
        
        if 'ema_20' not in self.df.columns:
            self._calculate_emas()
        
        self._draw_chart()
        self._update_info()
        
    def update_candle(self, candle_data: Dict[str, Any]):
        """새 캔들 데이터 추가/업데이트"""
        if candle_data is None:
            return
        
        timestamp = candle_data.get('timestamp', 0)
        
        # DataFrame 없으면 새로 생성
        if self.df is None:
            self.df = pd.DataFrame([candle_data])
            if 'timestamp' in self.df.columns:
                self.df['datetime'] = pd.to_datetime(self.df['timestamp'], unit='ms')
            self._calculate_emas()
            self._schedule_redraw()
            self._update_info()
            return
        
        # datetime 변환
        new_row = pd.DataFrame([candle_data])
        if 'timestamp' in new_row.columns:
            new_row['datetime'] = pd.to_datetime(new_row['timestamp'], unit='ms')
        
        # 마지막 캔들과 비교
        if len(self.df) > 0:
            last_ts = self.df.iloc[-1].get('timestamp', 0)
            new_ts = candle_data.get('timestamp', 0)
            
            if last_ts == new_ts:
                # 같은 캔들 - 업데이트
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in candle_data:
                        self.df.iloc[-1, self.df.columns.get_loc(col)] = candle_data[col]
            else:
                # 새 캔들 - 추가
                self.df = pd.concat([self.df, new_row], ignore_index=True)
        else:
            self.df = pd.concat([self.df, new_row], ignore_index=True)
        
        # 최대 캔들 수 제한
        if len(self.df) > self.MAX_CANDLES:
            self.df = self.df.iloc[-self.MAX_CANDLES:]
        
        self._calculate_emas()
        self._schedule_redraw()
        self._update_info()
    
    # ========================================
    # ★ 수정됨: update_price_only - 데이터 없을 때 새 DataFrame 생성
    # ========================================
    def update_price_only(self, price: float, timestamp: int = None):
        """
        가격만 업데이트 (실시간 틱) - 개선된 버전 (수정됨)
        
        - df가 없으면 새로 생성하여 데이터 축적 시작
        - 30분 단위로 새 캔들 생성
        - 같은 캔들 내에서는 close만 업데이트
        """
        import time as time_module
        
        if timestamp is None:
            timestamp = int(time_module.time() * 1000)
        
        current_dt = datetime.fromtimestamp(timestamp / 1000)
        
        # ========================================
        # Case 1: DataFrame이 없으면 새로 생성
        # ========================================
        if self.df is None or len(self.df) == 0:
            # 첫 데이터 포인트로 시작
            self.df = pd.DataFrame([{
                'timestamp': timestamp,
                'datetime': current_dt,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': 0
            }])
            self._calculate_emas()
            self._schedule_redraw()
            self._update_info()
            print(f"📊 차트 데이터 시작: ${price:,.2f}")
            return
        
        # ========================================
        # Case 2: 기존 데이터가 있는 경우
        # ========================================
        last_row = self.df.iloc[-1]
        last_dt = last_row['datetime']
        
        # datetime 타입 확인 및 변환
        if isinstance(last_dt, pd.Timestamp):
            last_dt = last_dt.to_pydatetime()
        elif isinstance(last_dt, str):
            last_dt = datetime.fromisoformat(last_dt)
        
        # 30분 단위로 새 캔들 여부 판단
        # 현재 시간의 30분 블록과 마지막 캔들의 30분 블록 비교
        current_block = current_dt.replace(minute=(current_dt.minute // 30) * 30, second=0, microsecond=0)
        last_block = last_dt.replace(minute=(last_dt.minute // 30) * 30, second=0, microsecond=0)
        
        is_new_candle = current_block > last_block
        
        if is_new_candle:
            # ========================================
            # 새 캔들 추가
            # ========================================
            new_row = pd.DataFrame([{
                'timestamp': timestamp,
                'datetime': current_dt,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': 0
            }])
            self.df = pd.concat([self.df, new_row], ignore_index=True)
            
            # 최대 캔들 수 제한
            if len(self.df) > self.MAX_CANDLES:
                self.df = self.df.iloc[-self.MAX_CANDLES:]
            
            print(f"📊 새 캔들 추가: {current_block.strftime('%H:%M')} ${price:,.2f}")
        else:
            # ========================================
            # 기존 캔들 업데이트
            # ========================================
            idx = len(self.df) - 1
            
            # close 업데이트
            self.df.iloc[idx, self.df.columns.get_loc('close')] = price
            
            # high/low 업데이트
            current_high = self.df.iloc[idx]['high']
            current_low = self.df.iloc[idx]['low']
            
            if price > current_high:
                self.df.iloc[idx, self.df.columns.get_loc('high')] = price
            if price < current_low:
                self.df.iloc[idx, self.df.columns.get_loc('low')] = price
        
        # EMA 재계산 및 차트 업데이트
        self._calculate_emas()
        self._schedule_redraw()
        
    def _calculate_emas(self):
        """EMA 계산"""
        if self.df is None or len(self.df) == 0:
            return
        
        close = self.df['close'].astype(float)
        for key, config in self.EMA_CONFIG.items():
            self.df[key] = ema(close, config['period'])
    
    def _draw_chart(self):
        """차트 그리기"""
        if self.df is None or len(self.df) == 0:
            return
        
        try:
            self.ax.clear()
            self._setup_axes()
            
            df = self.df.copy()
            if 'datetime' not in df.columns:
                return
            
            # 가격 차트
            if self.chart_type == 'candlestick':
                self._draw_candlestick(df)
            else:
                self._draw_line_chart(df)
            
            # EMA 라인
            self._draw_ema_lines(df)
            
            # X축 포맷
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.figure.autofmt_xdate(rotation=30)
            
            # Y축 범위
            y_min = df['low'].min() if 'low' in df.columns else df['close'].min()
            y_max = df['high'].max() if 'high' in df.columns else df['close'].max()
            margin = (y_max - y_min) * 0.05
            self.ax.set_ylim(y_min - margin, y_max + margin)
            
            # Y축 가격 포맷
            self.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            # 범례
            handles, labels = self.ax.get_legend_handles_labels()
            if handles:
                self.ax.legend(handles, labels, loc='upper left', fontsize=8,
                              facecolor='#2b2b2b', edgecolor='#3a3a3a', labelcolor='#ffffff')
            
            self.figure.tight_layout()
            self.canvas.draw()
            self.chart_updated.emit()
            
        except Exception as e:
            print(f"❌ 차트 그리기 오류: {e}")
    
    def _draw_line_chart(self, df: pd.DataFrame):
        """라인 차트"""
        x = df['datetime']
        y = df['close']
        self.ax.plot(x, y, color='#ffffff', linewidth=1.5, label='Price', zorder=10)
        self.ax.fill_between(x, y.min(), y, alpha=0.1, color='#4ECDC4')
    
    def _draw_candlestick(self, df: pd.DataFrame):
        """캔들스틱 차트"""
        if len(df) > 1:
            width = (df['datetime'].iloc[1] - df['datetime'].iloc[0]) * 0.8
        else:
            width = timedelta(minutes=24)
        
        up = df[df['close'] >= df['open']]
        down = df[df['close'] < df['open']]
        
        if not up.empty:
            self.ax.bar(up['datetime'], up['close'] - up['open'], width,
                       bottom=up['open'], color='#26a69a', edgecolor='#26a69a', zorder=5)
            self.ax.vlines(up['datetime'], up['low'], up['high'],
                          color='#26a69a', linewidth=0.8, zorder=4)
        
        if not down.empty:
            self.ax.bar(down['datetime'], down['open'] - down['close'], width,
                       bottom=down['close'], color='#ef5350', edgecolor='#ef5350', zorder=5)
            self.ax.vlines(down['datetime'], down['low'], down['high'],
                          color='#ef5350', linewidth=0.8, zorder=4)
    
    def _draw_ema_lines(self, df: pd.DataFrame):
        """EMA 라인"""
        x = df['datetime']
        
        for key, config in self.EMA_CONFIG.items():
            if not self.ema_visible.get(key, True) or key not in df.columns:
                continue
            
            y = df[key]
            valid = ~y.isna()
            if not valid.any():
                continue
            
            self.ax.plot(x[valid], y[valid], color=config['color'],
                        linewidth=config['width'], label=config['label'], alpha=0.8, zorder=3)
    
    # ========================================
    # ★ 수정됨: _update_info - 마지막 가격 정보 포함
    # ========================================
    def _update_info(self):
        """정보 라벨 업데이트 (수정됨)"""
        if self.df is None or len(self.df) == 0:
            self.info_label.setText("데이터 대기 중...")
            return
        
        count = len(self.df)
        
        # 마지막 가격 정보
        last_close = self.df.iloc[-1]['close']
        
        # 시간 범위
        if 'datetime' in self.df.columns:
            start = self.df.iloc[0]['datetime']
            end = self.df.iloc[-1]['datetime']
            
            if isinstance(start, pd.Timestamp):
                start_str = start.strftime('%m/%d %H:%M')
                end_str = end.strftime('%m/%d %H:%M')
            else:
                start_str = str(start)[:16]
                end_str = str(end)[:16]
            
            self.info_label.setText(
                f"{count}개 캔들 | ${last_close:,.2f} | {start_str} ~ {end_str}"
            )
        else:
            self.info_label.setText(f"{count}개 캔들 | ${last_close:,.2f}")
    
    def get_current_ema_values(self) -> Dict[str, float]:
        """현재 EMA 값들 반환"""
        if self.df is None or len(self.df) == 0:
            return {}
        
        result = {}
        last_row = self.df.iloc[-1]
        for key in self.EMA_CONFIG.keys():
            if key in self.df.columns:
                result[key] = float(last_row[key])
        return result
    
    def clear_data(self):
        """데이터 초기화"""
        self.df = None
        self.ax.clear()
        self._setup_axes()
        self.canvas.draw()
        self.info_label.setText("데이터 대기 중...")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import random
    
    app = QApplication(sys.argv)
    app.setStyleSheet("QMainWindow, QWidget { background-color: #1e1e1e; color: #ffffff; }")
    
    window = QMainWindow()
    window.setWindowTitle("Dashboard Chart Test")
    window.setGeometry(100, 100, 1200, 700)
    
    chart = DashboardChartWidget()
    window.setCentralWidget(chart)
    
    # 테스트 데이터
    data = []
    base_price = 97000
    current_time = datetime.now() - timedelta(days=7)
    
    for i in range(336):
        change = random.uniform(-0.002, 0.002)
        base_price = base_price * (1 + change)
        
        open_p = base_price * (1 + random.uniform(-0.001, 0.001))
        close_p = base_price * (1 + random.uniform(-0.001, 0.001))
        high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.002))
        low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.002))
        
        data.append({
            'timestamp': int(current_time.timestamp() * 1000),
            'datetime': current_time,
            'open': open_p, 'high': high_p, 'low': low_p, 'close': close_p,
            'volume': random.uniform(100, 1000)
        })
        current_time += timedelta(minutes=30)
    
    chart.set_historical_data(pd.DataFrame(data))
    
    window.show()
    sys.exit(app.exec_())
