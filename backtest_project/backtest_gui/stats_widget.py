# backtest_gui/stats_widget.py
"""
통계 요약 위젯
- 백테스트 결과 통계 표시
- 미니 자산곡선 차트
"""

from typing import Dict, Any, List, Tuple, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QGroupBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class StatLabel(QWidget):
    """통계 라벨 위젯"""
    
    def __init__(self, label: str, value: str = "-", color: str = "white", parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #888888;")
        
        self.value = QLabel(value)
        self.value.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.value.setAlignment(Qt.AlignRight)
        
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.value)
    
    def set_value(self, value: str, color: str = None):
        self.value.setText(value)
        if color:
            self.value.setStyleSheet(f"color: {color}; font-weight: bold;")


class MiniEquityChart(QWidget):
    """미니 자산곡선 차트"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending_data = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Figure 생성 - tight_layout 사용하지 않음
        self.figure = Figure(figsize=(3, 1.5), dpi=80, tight_layout=False)
        self.figure.patch.set_facecolor('#2b2b2b')
        self.figure.subplots_adjust(left=0.12, right=0.95, top=0.90, bottom=0.15)
        
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #2b2b2b;")
        self.canvas.setMinimumSize(150, 80)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self._style_axis()
    
    def _style_axis(self):
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='#888888', labelsize=6)
        self.ax.spines['bottom'].set_color('#3a3a3a')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['left'].set_color('#3a3a3a')
        self.ax.spines['right'].set_visible(False)
        self.ax.grid(True, color='#3a3a3a', linestyle='--', linewidth=0.3, alpha=0.5)
    
    def showEvent(self, event):
        super().showEvent(event)
        if self._pending_data:
            QTimer.singleShot(100, self._draw_pending)
    
    def _draw_pending(self):
        if self._pending_data:
            equity_real, equity_virtual = self._pending_data
            self._pending_data = None
            self._draw(equity_real, equity_virtual)
    
    def set_data(self, equity_real: List[Tuple], equity_virtual: List[Tuple] = None):
        if not equity_real:
            self.ax.clear()
            self._style_axis()
            self.canvas.draw_idle()
            return
        
        if self.isVisible() and self.canvas.width() > 0:
            self._draw(equity_real, equity_virtual)
        else:
            self._pending_data = (equity_real, equity_virtual)
    
    def _draw(self, equity_real: List[Tuple], equity_virtual: List[Tuple] = None):
        self.ax.clear()
        self._style_axis()
        
        times = [e[0] for e in equity_real]
        values_real = [e[1] for e in equity_real]
        
        self.ax.plot(times, values_real, color='#00d4aa', linewidth=1.2, label='REAL')
        
        if equity_virtual:
            values_virtual = [e[1] for e in equity_virtual]
            self.ax.plot(times, values_virtual, color='#888888', linewidth=0.8, 
                        linestyle='--', label='VIRTUAL', alpha=0.7)
        
        self.ax.legend(loc='upper left', fontsize=6, facecolor='#2b2b2b', 
                      edgecolor='#3a3a3a', labelcolor='white')
        
        # 여백 재조정
        self.figure.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        self.canvas.draw_idle()


class StatsWidget(QWidget):
    """통계 요약 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        title = QLabel("📊 통계 요약")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        layout.addWidget(title)
        
        group_style = """
            QGroupBox {
                color: white;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """
        
        # 수익률 그룹
        roi_group = QGroupBox("수익률")
        roi_group.setStyleSheet(group_style)
        roi_layout = QVBoxLayout(roi_group)
        roi_layout.setSpacing(2)
        
        self.stat_real_roi = StatLabel("REAL 수익률:", "-")
        self.stat_virtual_roi = StatLabel("VIRTUAL 수익률:", "-")
        self.stat_mdd_real = StatLabel("REAL MDD:", "-")
        self.stat_mdd_virtual = StatLabel("VIRTUAL MDD:", "-")
        
        roi_layout.addWidget(self.stat_real_roi)
        roi_layout.addWidget(self.stat_virtual_roi)
        roi_layout.addWidget(self.stat_mdd_real)
        roi_layout.addWidget(self.stat_mdd_virtual)
        layout.addWidget(roi_group)
        
        # 거래 통계 그룹
        trade_group = QGroupBox("거래 통계")
        trade_group.setStyleSheet(group_style)
        trade_layout = QVBoxLayout(trade_group)
        trade_layout.setSpacing(2)
        
        self.stat_total_trades = StatLabel("총 거래 수:", "-")
        self.stat_real_virtual = StatLabel("REAL / VIRTUAL:", "-")
        self.stat_win_rate = StatLabel("승률:", "-")
        self.stat_win_lose = StatLabel("승 / 패:", "-")
        self.stat_profit_factor = StatLabel("손익비:", "-")
        
        trade_layout.addWidget(self.stat_total_trades)
        trade_layout.addWidget(self.stat_real_virtual)
        trade_layout.addWidget(self.stat_win_rate)
        trade_layout.addWidget(self.stat_win_lose)
        trade_layout.addWidget(self.stat_profit_factor)
        layout.addWidget(trade_group)
        
        # 손익 그룹
        pnl_group = QGroupBox("손익")
        pnl_group.setStyleSheet(group_style)
        pnl_layout = QVBoxLayout(pnl_group)
        pnl_layout.setSpacing(2)
        
        self.stat_avg_profit = StatLabel("평균 수익:", "-")
        self.stat_avg_loss = StatLabel("평균 손실:", "-")
        self.stat_max_profit = StatLabel("최대 수익:", "-")
        self.stat_max_loss = StatLabel("최대 손실:", "-")
        self.stat_total_fees = StatLabel("총 수수료:", "-")
        self.stat_net_pnl = StatLabel("순손익:", "-")
        
        pnl_layout.addWidget(self.stat_avg_profit)
        pnl_layout.addWidget(self.stat_avg_loss)
        pnl_layout.addWidget(self.stat_max_profit)
        pnl_layout.addWidget(self.stat_max_loss)
        pnl_layout.addWidget(self.stat_total_fees)
        pnl_layout.addWidget(self.stat_net_pnl)
        layout.addWidget(pnl_group)
        
        # 모드 전환 그룹
        mode_group = QGroupBox("모드 전환")
        mode_group.setStyleSheet(group_style)
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(2)
        
        self.stat_r2v = StatLabel("REAL→VIRTUAL:", "-")
        self.stat_v2r = StatLabel("VIRTUAL→REAL:", "-")
        self.stat_consecutive = StatLabel("연속 최대 승/패:", "-")
        
        mode_layout.addWidget(self.stat_r2v)
        mode_layout.addWidget(self.stat_v2r)
        mode_layout.addWidget(self.stat_consecutive)
        layout.addWidget(mode_group)
        
        # 미니 자산곡선
        chart_group = QGroupBox("자산 변화")
        chart_group.setStyleSheet(group_style)
        chart_layout = QVBoxLayout(chart_group)
        
        self.mini_chart = MiniEquityChart()
        chart_layout.addWidget(self.mini_chart)
        layout.addWidget(chart_group)
        
        layout.addStretch()
    
    def update_stats(self, stats: Dict[str, Any], 
                     equity_real: List[Tuple] = None, 
                     equity_virtual: List[Tuple] = None):
        # 수익률
        real_roi = stats.get('real_roi', 0)
        virtual_roi = stats.get('virtual_roi', 0)
        mdd_real = stats.get('mdd_real', 0)
        mdd_virtual = stats.get('mdd_virtual', 0)
        
        roi_color = '#00ff88' if real_roi > 0 else '#ff6b6b' if real_roi < 0 else 'white'
        self.stat_real_roi.set_value(f"{real_roi:+.2f}%", roi_color)
        
        vroi_color = '#00ff88' if virtual_roi > 0 else '#ff6b6b' if virtual_roi < 0 else 'white'
        self.stat_virtual_roi.set_value(f"{virtual_roi:+.2f}%", vroi_color)
        
        self.stat_mdd_real.set_value(f"-{mdd_real:.2f}%", '#ff6b6b')
        self.stat_mdd_virtual.set_value(f"-{mdd_virtual:.2f}%", '#ff6b6b')
        
        # 거래 통계
        total_trades = stats.get('total_trades', 0)
        real_trades = stats.get('real_trades', 0)
        virtual_trades = stats.get('virtual_trades', 0)
        win_rate = stats.get('win_rate', 0)
        winning = stats.get('winning_trades', 0)
        losing = stats.get('losing_trades', 0)
        profit_factor = stats.get('profit_factor', 0)
        
        self.stat_total_trades.set_value(str(total_trades))
        self.stat_real_virtual.set_value(f"{real_trades} / {virtual_trades}")
        
        wr_color = '#00ff88' if win_rate >= 50 else '#ff6b6b'
        self.stat_win_rate.set_value(f"{win_rate:.1f}%", wr_color)
        self.stat_win_lose.set_value(f"{winning} / {losing}")
        
        pf_color = '#00ff88' if profit_factor >= 1 else '#ff6b6b'
        pf_str = f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞"
        self.stat_profit_factor.set_value(pf_str, pf_color)
        
        # 손익
        avg_profit = stats.get('avg_profit', 0)
        avg_loss = stats.get('avg_loss', 0)
        max_profit = stats.get('max_profit', 0)
        max_loss = stats.get('max_loss', 0)
        total_fees = stats.get('total_fees', 0)
        net_pnl = stats.get('net_pnl', 0)
        
        self.stat_avg_profit.set_value(f"${avg_profit:+,.2f}", '#00ff88')
        self.stat_avg_loss.set_value(f"${avg_loss:+,.2f}", '#ff6b6b')
        self.stat_max_profit.set_value(f"${max_profit:+,.2f}", '#00ff88')
        self.stat_max_loss.set_value(f"${max_loss:+,.2f}", '#ff6b6b')
        self.stat_total_fees.set_value(f"${total_fees:,.2f}", '#ffaa00')
        
        net_color = '#00ff88' if net_pnl > 0 else '#ff6b6b' if net_pnl < 0 else 'white'
        self.stat_net_pnl.set_value(f"${net_pnl:+,.2f}", net_color)
        
        # 모드 전환
        r2v = stats.get('r2v_switches', 0)
        v2r = stats.get('v2r_switches', 0)
        max_wins = stats.get('max_consecutive_wins', 0)
        max_losses = stats.get('max_consecutive_losses', 0)
        
        self.stat_r2v.set_value(f"{r2v}회")
        self.stat_v2r.set_value(f"{v2r}회")
        self.stat_consecutive.set_value(f"{max_wins} / {max_losses}")
        
        # 미니 차트
        if equity_real:
            self.mini_chart.set_data(equity_real, equity_virtual)
    
    def clear(self):
        for widget in [
            self.stat_real_roi, self.stat_virtual_roi,
            self.stat_mdd_real, self.stat_mdd_virtual,
            self.stat_total_trades, self.stat_real_virtual,
            self.stat_win_rate, self.stat_win_lose, self.stat_profit_factor,
            self.stat_avg_profit, self.stat_avg_loss,
            self.stat_max_profit, self.stat_max_loss,
            self.stat_total_fees, self.stat_net_pnl,
            self.stat_r2v, self.stat_v2r, self.stat_consecutive,
        ]:
            widget.set_value("-")
        self.mini_chart.set_data([])
