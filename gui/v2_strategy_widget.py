# gui/v2_strategy_widget.py
"""
v2 전략 모니터링 위젯

SignalPipeline, 거래 이력, 모드 상태 등을 GUI에 표시
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSplitter,
    QTextEdit, QTabWidget, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor


class V2StrategyOverviewWidget(QWidget):
    """v2 전략 개요 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QGridLayout()
        self.setLayout(layout)
        
        # 스타일
        label_style = "font-weight: bold; color: #aaa;"
        value_style = "font-size: 14px; font-weight: bold;"
        
        # 모드 상태
        layout.addWidget(QLabel("모드:"), 0, 0)
        self.mode_label = QLabel("--")
        self.mode_label.setStyleSheet(value_style)
        layout.addWidget(self.mode_label, 0, 1)
        
        # 자본
        layout.addWidget(QLabel("자본:"), 0, 2)
        self.capital_label = QLabel("$0.00")
        self.capital_label.setStyleSheet(value_style)
        layout.addWidget(self.capital_label, 0, 3)
        
        # 총 PnL
        layout.addWidget(QLabel("총 PnL:"), 1, 0)
        self.pnl_label = QLabel("$0.00")
        self.pnl_label.setStyleSheet(value_style)
        layout.addWidget(self.pnl_label, 1, 1)
        
        # 승률
        layout.addWidget(QLabel("승률:"), 1, 2)
        self.winrate_label = QLabel("0.0%")
        self.winrate_label.setStyleSheet(value_style)
        layout.addWidget(self.winrate_label, 1, 3)
        
        # 포지션 상태
        layout.addWidget(QLabel("포지션:"), 2, 0)
        self.position_label = QLabel("없음")
        self.position_label.setStyleSheet(value_style)
        layout.addWidget(self.position_label, 2, 1)
        
        # 거래 수
        layout.addWidget(QLabel("거래:"), 2, 2)
        self.trades_label = QLabel("0회")
        self.trades_label.setStyleSheet(value_style)
        layout.addWidget(self.trades_label, 2, 3)
    
    def update_data(self, data: Dict[str, Any]):
        """데이터 업데이트"""
        # 모드
        mode = data.get('mode', 'UNKNOWN')
        if mode == 'REAL':
            self.mode_label.setText("🟢 REAL")
            self.mode_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #28a745;")
        else:
            self.mode_label.setText("🟡 VIRTUAL")
            self.mode_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffc107;")
        
        # 자본
        capital = data.get('capital', 0)
        self.capital_label.setText(f"${capital:,.2f}")
        
        # PnL
        pnl = data.get('total_pnl', 0)
        color = "#28a745" if pnl >= 0 else "#dc3545"
        self.pnl_label.setText(f"${pnl:+,.2f}")
        self.pnl_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
        
        # 승률
        trade_count = data.get('trade_count', 0)
        win_count = data.get('win_count', 0)
        winrate = (win_count / trade_count * 100) if trade_count > 0 else 0
        self.winrate_label.setText(f"{winrate:.1f}%")
        
        # 포지션
        if data.get('position_open', False):
            entry_price = data.get('entry_price', 0)
            self.position_label.setText(f"🟢 LONG @ ${entry_price:,.2f}")
            self.position_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #28a745;")
        else:
            self.position_label.setText("⚪ 대기 중")
            self.position_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #6c757d;")
        
        # 거래 수
        self.trades_label.setText(f"{trade_count}회")


class SignalPipelineWidget(QWidget):
    """SignalPipeline 정보 표시 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 통계 그룹
        stats_group = QGroupBox("📊 시그널 통계")
        stats_layout = QGridLayout()
        stats_group.setLayout(stats_layout)
        
        # 총 시그널
        stats_layout.addWidget(QLabel("총 시그널:"), 0, 0)
        self.total_signals_label = QLabel("0")
        self.total_signals_label.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self.total_signals_label, 0, 1)
        
        # ENTRY 시그널
        stats_layout.addWidget(QLabel("진입 시그널:"), 0, 2)
        self.entry_signals_label = QLabel("0")
        self.entry_signals_label.setStyleSheet("font-weight: bold; color: #28a745;")
        stats_layout.addWidget(self.entry_signals_label, 0, 3)
        
        # EXIT 시그널
        stats_layout.addWidget(QLabel("청산 시그널:"), 1, 0)
        self.exit_signals_label = QLabel("0")
        self.exit_signals_label.setStyleSheet("font-weight: bold; color: #dc3545;")
        stats_layout.addWidget(self.exit_signals_label, 1, 1)
        
        # 검증 통과
        stats_layout.addWidget(QLabel("검증 통과:"), 1, 2)
        self.valid_signals_label = QLabel("0")
        self.valid_signals_label.setStyleSheet("font-weight: bold; color: #17a2b8;")
        stats_layout.addWidget(self.valid_signals_label, 1, 3)
        
        # 검증 거부
        stats_layout.addWidget(QLabel("검증 거부:"), 2, 0)
        self.rejected_signals_label = QLabel("0")
        self.rejected_signals_label.setStyleSheet("font-weight: bold; color: #ffc107;")
        stats_layout.addWidget(self.rejected_signals_label, 2, 1)
        
        # 통과율 프로그레스바
        stats_layout.addWidget(QLabel("통과율:"), 2, 2)
        self.pass_rate_bar = QProgressBar()
        self.pass_rate_bar.setMaximum(100)
        self.pass_rate_bar.setValue(0)
        self.pass_rate_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #17a2b8;
            }
        """)
        stats_layout.addWidget(self.pass_rate_bar, 2, 3)
        
        layout.addWidget(stats_group)
        
        # 최근 거부 사유 테이블
        rejected_group = QGroupBox("🚫 최근 거부된 진입 시그널")
        rejected_layout = QVBoxLayout()
        rejected_group.setLayout(rejected_layout)
        
        self.rejected_table = QTableWidget()
        self.rejected_table.setColumnCount(4)
        self.rejected_table.setHorizontalHeaderLabels(["시간", "전략", "거부 사유", "모드"])
        self.rejected_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rejected_table.setMaximumHeight(150)
        rejected_layout.addWidget(self.rejected_table)
        
        layout.addWidget(rejected_group)
    
    def update_stats(self, stats: Dict[str, Any]):
        """통계 업데이트"""
        total = stats.get('total_signals', 0)
        entry = stats.get('entry_signals', 0)
        exit = stats.get('exit_signals', 0)
        valid = stats.get('valid_signals', 0)
        rejected = stats.get('rejected_signals', 0)
        
        self.total_signals_label.setText(str(total))
        self.entry_signals_label.setText(str(entry))
        self.exit_signals_label.setText(str(exit))
        self.valid_signals_label.setText(str(valid))
        self.rejected_signals_label.setText(str(rejected))
        
        # 통과율
        if total > 0:
            pass_rate = int(valid / total * 100)
            self.pass_rate_bar.setValue(pass_rate)
            self.pass_rate_bar.setFormat(f"{pass_rate}%")
        else:
            self.pass_rate_bar.setValue(0)
            self.pass_rate_bar.setFormat("0%")
    
    def update_rejected_entries(self, entries: List[Dict]):
        """거부된 진입 시그널 업데이트"""
        self.rejected_table.setRowCount(len(entries))
        
        for row, entry in enumerate(entries):
            self.rejected_table.setItem(row, 0, QTableWidgetItem(entry.get('timestamp', '')[:19]))
            self.rejected_table.setItem(row, 1, QTableWidgetItem(entry.get('strategy', '')))
            self.rejected_table.setItem(row, 2, QTableWidgetItem(entry.get('reason', '')))
            self.rejected_table.setItem(row, 3, QTableWidgetItem(entry.get('mode', '')))


class TradeHistoryWidget(QWidget):
    """거래 이력 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 거래 테이블
        self.trade_table = QTableWidget()
        self.trade_table.setColumnCount(6)
        self.trade_table.setHorizontalHeaderLabels([
            "시간", "전략", "진입가", "청산가", "PnL", "결과"
        ])
        self.trade_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.trade_table)
    
    def add_trade(self, trade: Dict[str, Any]):
        """거래 추가"""
        row = self.trade_table.rowCount()
        self.trade_table.insertRow(row)
        
        self.trade_table.setItem(row, 0, QTableWidgetItem(
            trade.get('timestamp', str(datetime.now()))[:19]
        ))
        self.trade_table.setItem(row, 1, QTableWidgetItem(trade.get('strategy', '')))
        self.trade_table.setItem(row, 2, QTableWidgetItem(f"${trade.get('entry_price', 0):,.2f}"))
        self.trade_table.setItem(row, 3, QTableWidgetItem(f"${trade.get('exit_price', 0):,.2f}"))
        
        pnl = trade.get('pnl', 0)
        pnl_item = QTableWidgetItem(f"${pnl:+,.2f}")
        if pnl >= 0:
            pnl_item.setForeground(QColor("#28a745"))
        else:
            pnl_item.setForeground(QColor("#dc3545"))
        self.trade_table.setItem(row, 4, pnl_item)
        
        result = "✅ 승" if trade.get('is_win', False) else "❌ 패"
        self.trade_table.setItem(row, 5, QTableWidgetItem(result))
        
        # 최신 거래가 위에 오도록
        self.trade_table.scrollToTop()


class V2LogWidget(QWidget):
    """v2 전략 로그 위젯"""
    
    def __init__(self):
        super().__init__()
        self.max_logs = 500
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 로그 텍스트
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ddd;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("로그 지우기")
        clear_btn.clicked.connect(self.clear_logs)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def add_log(self, message: str, log_type: str = "정보"):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 타입별 색상
        colors = {
            "정보": "#17a2b8",
            "시그널": "#28a745",
            "거래": "#ffc107",
            "모드전환": "#e83e8c",
            "이메일": "#6f42c1",
            "오류": "#dc3545",
            "경고": "#fd7e14",
        }
        color = colors.get(log_type, "#aaa")
        
        html = f'<span style="color:#888">[{timestamp}]</span> ' \
               f'<span style="color:{color}">[{log_type}]</span> ' \
               f'<span style="color:#ddd">{message}</span><br>'
        
        self.log_text.insertHtml(html)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
        # 로그 수 제한
        if self.log_text.document().blockCount() > self.max_logs:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 100)
            cursor.removeSelectedText()
    
    def clear_logs(self):
        """로그 지우기"""
        self.log_text.clear()
        self.add_log("로그가 초기화되었습니다", "정보")


class V2StrategyMonitoringWidget(QWidget):
    """
    v2 전략 통합 모니터링 위젯
    
    이 위젯을 GUI의 조건 모니터링 탭에 추가
    """
    
    def __init__(self, bridge=None):
        super().__init__()
        self.bridge = bridge
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 타이틀
        title = QLabel("🎯 v2 Long Only 전략 모니터링")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # 탭 위젯
        tab_widget = QTabWidget()
        
        # 탭 1: 전략 개요
        self.overview_widget = V2StrategyOverviewWidget()
        tab_widget.addTab(self.overview_widget, "📊 개요")
        
        # 탭 2: SignalPipeline
        self.pipeline_widget = SignalPipelineWidget()
        tab_widget.addTab(self.pipeline_widget, "🔍 파이프라인")
        
        # 탭 3: 거래 이력
        self.history_widget = TradeHistoryWidget()
        tab_widget.addTab(self.history_widget, "📈 거래 이력")
        
        # 탭 4: 로그
        self.log_widget = V2LogWidget()
        tab_widget.addTab(self.log_widget, "📝 로그")
        
        layout.addWidget(tab_widget)
    
    def connect_signals(self):
        """브릿지 시그널 연결"""
        if not self.bridge:
            return
        
        self.bridge.stats_updated.connect(self.on_stats_updated)
        self.bridge.signal_generated.connect(self.on_signal_generated)
        self.bridge.trade_executed.connect(self.on_trade_executed)
        self.bridge.mode_switched.connect(self.on_mode_switched)
        self.bridge.log_message.connect(self.on_log_message)
        self.bridge.email_sent.connect(self.on_email_sent)
    
    def set_bridge(self, bridge):
        """브릿지 설정"""
        self.bridge = bridge
        self.connect_signals()
        self.log_widget.add_log("v2 전략 브릿지 연결됨", "정보")
    
    def on_stats_updated(self, stats: Dict[str, Any]):
        """통계 업데이트"""
        # 전략 개요
        for key, strat_data in stats.get('strategies', {}).items():
            self.overview_widget.update_data(strat_data)
            break  # 첫 번째 전략만 표시 (단일 심볼 가정)
        
        # 파이프라인 통계
        if self.bridge:
            pipeline_stats = self.bridge.get_pipeline_summary()
            self.pipeline_widget.update_stats(pipeline_stats)
            
            blocked = self.bridge.get_blocked_entries(10)
            self.pipeline_widget.update_rejected_entries(blocked)
    
    def on_signal_generated(self, event: Dict[str, Any]):
        """시그널 생성 이벤트"""
        signal_type = event.get('signal_type', '')
        strategy = event.get('strategy', '')
        price = event.get('price', 0)
        
        self.log_widget.add_log(
            f"[{strategy}] {signal_type} 시그널 @ ${price:,.2f}",
            "시그널"
        )
    
    def on_trade_executed(self, trade: Dict[str, Any]):
        """거래 실행 이벤트"""
        self.history_widget.add_trade(trade)
        
        pnl = trade.get('pnl', 0)
        emoji = "💰" if trade.get('is_win') else "📉"
        self.log_widget.add_log(
            f"{emoji} 거래 완료: ${pnl:+,.2f}",
            "거래"
        )
    
    def on_mode_switched(self, event: Dict[str, Any]):
        """모드 전환 이벤트"""
        from_mode = event.get('from_mode', '')
        to_mode = event.get('to_mode', '')
        reason = event.get('reason', '')
        
        emoji = "⚠️" if to_mode == 'VIRTUAL' else "✅"
        self.log_widget.add_log(
            f"{emoji} 모드 전환: {from_mode} → {to_mode} ({reason})",
            "모드전환"
        )
    
    def on_log_message(self, message: str, log_type: str):
        """로그 메시지"""
        self.log_widget.add_log(message, log_type)
    
    def on_email_sent(self, event: Dict[str, Any]):
        """이메일 발송 이벤트"""
        email_type = event.get('type', '')
        self.log_widget.add_log(f"이메일 발송: {email_type}", "이메일")
