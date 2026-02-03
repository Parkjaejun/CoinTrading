# gui/trade_table_widget.py
"""
거래 내역 테이블 위젯
- 거래 목록 표시
- 행 선택 시 차트 연동
"""

from typing import List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel, QFrame, QHBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtest_engine import Trade


class TradeTableWidget(QWidget):
    """거래 내역 테이블 위젯"""
    
    # 거래 선택 시그널 (trade_index)
    trade_selected = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.trades: List[Trade] = []
        self._setup_ui()
    
    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 헤더
        header_frame = QFrame()
        header_frame.setMaximumHeight(30)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        self.title_label = QLabel("📋 거래 내역 (0건)")
        self.title_label.setStyleSheet("font-weight: bold; color: white;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "#", "방향", "모드", "진입시간", "청산시간", 
            "진입가", "청산가", "수익률(%)", "순손익", "청산사유"
        ])
        
        # 스타일
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                color: white;
                gridline-color: #3a3a3a;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: white;
                padding: 5px;
                border: 1px solid #2b2b2b;
                font-weight: bold;
            }
        """)
        
        # 설정
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # 컬럼 너비
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # #
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # 방향
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # 모드
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 진입시간
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # 청산시간
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # 진입가
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # 청산가
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # 수익률
        header.setSectionResizeMode(8, QHeaderView.Fixed)  # 순손익
        header.setSectionResizeMode(9, QHeaderView.Stretch)  # 청산사유
        
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 90)
        self.table.setColumnWidth(7, 80)
        self.table.setColumnWidth(8, 80)
        
        # 시그널 연결
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        layout.addWidget(self.table)
    
    def set_trades(self, trades: List[Trade]):
        """거래 목록 설정"""
        self.trades = trades
        self._populate_table()
        self.title_label.setText(f"📋 거래 내역 ({len(trades)}건)")
    
    def _populate_table(self):
        """테이블 채우기"""
        self.table.setRowCount(len(self.trades))
        
        for row, trade in enumerate(self.trades):
            # # (번호)
            item = QTableWidgetItem(str(row + 1))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item)
            
            # 방향
            side_item = QTableWidgetItem(trade.side)
            side_item.setTextAlignment(Qt.AlignCenter)
            if trade.side == "LONG":
                side_item.setForeground(QBrush(QColor("#00ff88")))
            else:
                side_item.setForeground(QBrush(QColor("#ff6b6b")))
            self.table.setItem(row, 1, side_item)
            
            # 모드
            mode_item = QTableWidgetItem(trade.mode)
            mode_item.setTextAlignment(Qt.AlignCenter)
            if trade.mode == "REAL":
                mode_item.setForeground(QBrush(QColor("#00d4aa")))
            else:
                mode_item.setForeground(QBrush(QColor("#888888")))
            self.table.setItem(row, 2, mode_item)
            
            # 진입시간
            entry_time_str = self._format_time(trade.entry_time)
            self.table.setItem(row, 3, QTableWidgetItem(entry_time_str))
            
            # 청산시간
            exit_time_str = self._format_time(trade.exit_time)
            self.table.setItem(row, 4, QTableWidgetItem(exit_time_str))
            
            # 진입가
            entry_item = QTableWidgetItem(f"${trade.entry_price:,.2f}")
            entry_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 5, entry_item)
            
            # 청산가
            exit_item = QTableWidgetItem(f"${trade.exit_price:,.2f}")
            exit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 6, exit_item)
            
            # 수익률
            pnl_pct = trade.pnl_percentage
            pnl_item = QTableWidgetItem(f"{pnl_pct:+.2f}%")
            pnl_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if pnl_pct > 0:
                pnl_item.setForeground(QBrush(QColor("#00ff88")))
            elif pnl_pct < 0:
                pnl_item.setForeground(QBrush(QColor("#ff6b6b")))
            self.table.setItem(row, 7, pnl_item)
            
            # 순손익
            net_pnl_item = QTableWidgetItem(f"${trade.net_pnl:+,.2f}")
            net_pnl_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if trade.net_pnl > 0:
                net_pnl_item.setForeground(QBrush(QColor("#00ff88")))
            elif trade.net_pnl < 0:
                net_pnl_item.setForeground(QBrush(QColor("#ff6b6b")))
            self.table.setItem(row, 8, net_pnl_item)
            
            # 청산사유
            reason_item = QTableWidgetItem(self._format_reason(trade.reason_exit))
            self.table.setItem(row, 9, reason_item)
    
    def _format_time(self, t) -> str:
        """시간 포맷"""
        try:
            if hasattr(t, 'strftime'):
                return t.strftime("%m-%d %H:%M")
            return str(t)
        except:
            return str(t)
    
    def _format_reason(self, reason: str) -> str:
        """청산 사유 포맷"""
        reason_map = {
            'ema_dead_cross': 'EMA 데드크로스',
            'ema_golden_cross': 'EMA 골든크로스',
            'trailing_stop': '트레일링 스탑',
            'reverse_to_short': '숏 전환',
            'reverse_to_long': '롱 전환',
        }
        return reason_map.get(reason, reason)
    
    def _on_selection_changed(self):
        """선택 변경 처리"""
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            self.trade_selected.emit(row)
    
    def highlight_row(self, row_idx: int):
        """특정 행 하이라이트"""
        if 0 <= row_idx < self.table.rowCount():
            self.table.selectRow(row_idx)
            self.table.scrollToItem(self.table.item(row_idx, 0))
    
    def get_selected_trade(self) -> Optional[Trade]:
        """선택된 거래 반환"""
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            if 0 <= row < len(self.trades):
                return self.trades[row]
        return None
    
    def clear(self):
        """테이블 초기화"""
        self.trades = []
        self.table.setRowCount(0)
        self.title_label.setText("📋 거래 내역 (0건)")
