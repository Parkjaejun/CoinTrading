# backtest_gui/backtest_widget.py
"""
메인 백테스트 탭 위젯
- Long Only / Long+Short 선택 가능
- 모든 하위 위젯 통합
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
    QDateEdit, QProgressBar, QFrame, QFileDialog,
    QMessageBox, QGroupBox, QCheckBox, QComboBox,
    QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont

# 상위 디렉토리 추가
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from backtest.data_fetcher import DataFetcher
from backtest.backtest_engine import BacktestEngine, Params, BacktestResult
from backtest.result_analyzer import ResultAnalyzer

from backtest_gui.chart_widget import BacktestChartWidget
from backtest_gui.trade_table_widget import TradeTableWidget
from backtest_gui.stats_widget import StatsWidget


class BacktestWorker(QThread):
    """백테스트 작업 스레드"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, engine: BacktestEngine, df, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.df = df
    
    def run(self):
        try:
            result = self.engine.run(
                self.df,
                progress_callback=lambda c, t, m: self.progress.emit(c, t, m)
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DataFetchWorker(QThread):
    """데이터 수집 작업 스레드"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, fetcher: DataFetcher, symbol: str, 
                 start_date: datetime, end_date: datetime, 
                 use_cache: bool = True, parent=None):
        super().__init__(parent)
        self.fetcher = fetcher
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.use_cache = use_cache
    
    def run(self):
        try:
            df = self.fetcher.fetch_data(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                use_cache=self.use_cache,
                progress_callback=lambda c, t, m: self.progress.emit(c, t, m)
            )
            self.finished.emit(df)
        except Exception as e:
            self.error.emit(str(e))


class BacktestWidget(QWidget):
    """메인 백테스트 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.df = None
        self.result: Optional[BacktestResult] = None
        self.fetcher = DataFetcher(cache_dir="./cache")
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # === 상단: 설정 패널 ===
        settings_frame = QFrame()
        settings_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
            }
        """)
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(15, 10, 15, 10)
        
        # 첫째 줄: 기간, 자본
        row1_layout = QHBoxLayout()
        
        row1_layout.addWidget(QLabel("기간:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate(2026, 1, 1))
        self.start_date.setStyleSheet("background-color: #3a3a3a; color: white; padding: 5px;")
        row1_layout.addWidget(self.start_date)
        
        row1_layout.addWidget(QLabel("~"))
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate(2026, 1, 31))
        self.end_date.setStyleSheet("background-color: #3a3a3a; color: white; padding: 5px;")
        row1_layout.addWidget(self.end_date)
        
        row1_layout.addSpacing(20)
        
        row1_layout.addWidget(QLabel("초기자본:"))
        self.initial_capital = QDoubleSpinBox()
        self.initial_capital.setRange(100, 10000000)
        self.initial_capital.setValue(10000)
        self.initial_capital.setPrefix("$")
        self.initial_capital.setDecimals(0)
        self.initial_capital.setStyleSheet("background-color: #3a3a3a; color: white; padding: 5px;")
        row1_layout.addWidget(self.initial_capital)
        
        row1_layout.addStretch()
        settings_layout.addLayout(row1_layout)
        
        # 둘째 줄: 전략 모드 선택
        row2_layout = QHBoxLayout()
        
        row2_layout.addWidget(QLabel("전략 모드:"))
        
        # 라디오 버튼 그룹
        self.strategy_mode_group = QButtonGroup(self)
        
        self.long_only_radio = QRadioButton("Long Only")
        self.long_only_radio.setChecked(True)
        self.long_only_radio.setStyleSheet("color: #00ff88;")
        self.strategy_mode_group.addButton(self.long_only_radio, 0)
        row2_layout.addWidget(self.long_only_radio)
        
        self.long_short_radio = QRadioButton("Long + Short")
        self.long_short_radio.setStyleSheet("color: #ffaa00;")
        self.strategy_mode_group.addButton(self.long_short_radio, 1)
        row2_layout.addWidget(self.long_short_radio)
        
        row2_layout.addSpacing(30)
        
        # 레버리지 설정
        row2_layout.addWidget(QLabel("롱 레버리지:"))
        self.leverage_long = QSpinBox()
        self.leverage_long.setRange(1, 100)
        self.leverage_long.setValue(10)
        self.leverage_long.setStyleSheet("background-color: #3a3a3a; color: white; padding: 3px;")
        row2_layout.addWidget(self.leverage_long)
        
        row2_layout.addWidget(QLabel("숏 레버리지:"))
        self.leverage_short = QSpinBox()
        self.leverage_short.setRange(1, 100)
        self.leverage_short.setValue(3)
        self.leverage_short.setStyleSheet("background-color: #3a3a3a; color: white; padding: 3px;")
        self.leverage_short.setEnabled(False)  # Long Only일 때 비활성화
        row2_layout.addWidget(self.leverage_short)
        
        row2_layout.addStretch()
        
        # 버튼들
        self.load_csv_btn = QPushButton("📂 CSV 로드")
        self.load_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #666666; }
        """)
        row2_layout.addWidget(self.load_csv_btn)
        
        self.fetch_btn = QPushButton("📥 데이터 가져오기")
        self.fetch_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #106ebe; }
        """)
        row2_layout.addWidget(self.fetch_btn)
        
        self.run_btn = QPushButton("▶️ 시뮬레이션 실행")
        self.run_btn.setEnabled(False)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #00aa55;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #00cc66; }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        row2_layout.addWidget(self.run_btn)
        
        settings_layout.addLayout(row2_layout)
        
        main_layout.addWidget(settings_frame)
        
        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3a3a3a;
                border: none;
                border-radius: 3px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 상태 라벨
        self.status_label = QLabel("데이터를 로드하거나 가져오세요.")
        self.status_label.setStyleSheet("color: #888888;")
        main_layout.addWidget(self.status_label)
        
        # === 메인 스플리터 ===
        main_splitter = QSplitter(Qt.Vertical)
        
        self.chart_widget = BacktestChartWidget()
        main_splitter.addWidget(self.chart_widget)
        
        bottom_splitter = QSplitter(Qt.Horizontal)
        
        self.trade_table = TradeTableWidget()
        bottom_splitter.addWidget(self.trade_table)
        
        self.stats_widget = StatsWidget()
        self.stats_widget.setMaximumWidth(350)
        bottom_splitter.addWidget(self.stats_widget)
        
        bottom_splitter.setSizes([600, 350])
        
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setSizes([500, 300])
        
        main_layout.addWidget(main_splitter, 1)
    
    def _connect_signals(self):
        self.load_csv_btn.clicked.connect(self._on_load_csv)
        self.fetch_btn.clicked.connect(self._on_fetch_data)
        self.run_btn.clicked.connect(self._on_run_backtest)
        self.trade_table.trade_selected.connect(self._on_trade_selected)
        
        # 전략 모드 변경 시 숏 레버리지 활성화/비활성화
        self.long_only_radio.toggled.connect(self._on_strategy_mode_changed)
    
    def _on_strategy_mode_changed(self, checked):
        """전략 모드 변경"""
        # Long Only 선택 시 숏 레버리지 비활성화
        self.leverage_short.setEnabled(not checked)
    
    def _on_load_csv(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "CSV 파일 선택", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filepath:
            return
        
        try:
            self.status_label.setText(f"로딩 중: {filepath}")
            self.df = self.fetcher.load_existing_csv(filepath)
            
            self.status_label.setText(f"로드 완료: {len(self.df):,}개 캔들")
            self.run_btn.setEnabled(True)
            
            self._update_chart_data()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"CSV 로드 실패:\n{str(e)}")
            self.status_label.setText("CSV 로드 실패")
    
    def _on_fetch_data(self):
        start = self.start_date.date().toPyDate()
        end = self.end_date.date().toPyDate()
        
        start_dt = datetime(start.year, start.month, start.day, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.fetch_btn.setEnabled(False)
        self.status_label.setText("데이터 가져오는 중...")
        
        self.fetch_worker = DataFetchWorker(
            self.fetcher, "BTCUSDT", start_dt, end_dt, use_cache=True
        )
        self.fetch_worker.progress.connect(self._on_fetch_progress)
        self.fetch_worker.finished.connect(self._on_fetch_finished)
        self.fetch_worker.error.connect(self._on_fetch_error)
        self.fetch_worker.start()
    
    def _on_fetch_progress(self, current, total, message):
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(current)
        self.status_label.setText(message)
    
    def _on_fetch_finished(self, df):
        self.df = df
        self.progress_bar.setVisible(False)
        self.fetch_btn.setEnabled(True)
        self.run_btn.setEnabled(True)
        
        self.status_label.setText(f"데이터 로드 완료: {len(df):,}개 캔들")
        self._update_chart_data()
    
    def _on_fetch_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.fetch_btn.setEnabled(True)
        self.status_label.setText(f"오류: {error_msg}")
        QMessageBox.critical(self, "오류", f"데이터 가져오기 실패:\n{error_msg}")
    
    def _on_run_backtest(self):
        if self.df is None:
            QMessageBox.warning(self, "경고", "먼저 데이터를 로드하세요.")
            return
        
        # 파라미터 설정
        is_long_only = self.long_only_radio.isChecked()
        
        params = Params(
            long_only=is_long_only,
            leverage_long=float(self.leverage_long.value()),
            leverage_short=float(self.leverage_short.value()),
        )
        
        engine = BacktestEngine(
            params=params,
            initial_capital=self.initial_capital.value()
        )
        
        mode_str = "Long Only" if is_long_only else "Long + Short"
        self.status_label.setText(f"백테스트 실행 중... ({mode_str})")
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.run_btn.setEnabled(False)
        
        self.backtest_worker = BacktestWorker(engine, self.df)
        self.backtest_worker.progress.connect(self._on_backtest_progress)
        self.backtest_worker.finished.connect(self._on_backtest_finished)
        self.backtest_worker.error.connect(self._on_backtest_error)
        self.backtest_worker.start()
    
    def _on_backtest_progress(self, current, total, message):
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(current)
        self.status_label.setText(message)
    
    def _on_backtest_finished(self, result: BacktestResult):
        self.result = result
        self.progress_bar.setVisible(False)
        self.run_btn.setEnabled(True)
        
        self._display_results()
        
        mode_str = "Long Only" if self.long_only_radio.isChecked() else "Long + Short"
        self.status_label.setText(
            f"백테스트 완료 ({mode_str}): {result.total_trades}건 거래, "
            f"REAL ROI: {result.real_roi:+.2f}%"
        )
    
    def _on_backtest_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.run_btn.setEnabled(True)
        self.status_label.setText(f"오류: {error_msg}")
        QMessageBox.critical(self, "오류", f"백테스트 실패:\n{error_msg}")
    
    def _update_chart_data(self):
        if self.df is None:
            return
        self.chart_widget.set_data(self.df)
    
    def _display_results(self):
        if self.result is None:
            return
        
        # 차트에 마커 추가
        if self.result.ema_data is not None:
            self.chart_widget.set_data(self.result.ema_data)
        
        markers = []
        for m in self.result.markers:
            if m.event_type in ["ENTRY", "EXIT"]:
                markers.append({
                    "time": m.time,
                    "price": m.price,
                    "type": m.event_type,
                    "side": m.side,
                    "mode": m.mode,
                    "reason": m.reason,
                })
        self.chart_widget.set_markers(markers)
        
        # 거래 테이블 업데이트
        self.trade_table.set_trades(self.result.trades)
        
        # 통계 업데이트
        analyzer = ResultAnalyzer(self.result)
        stats = analyzer.get_summary_dict()
        self.stats_widget.update_stats(
            stats,
            self.result.equity_curve_real,
            self.result.equity_curve_virtual
        )
    
    def _on_trade_selected(self, trade_idx: int):
        if self.result is None or trade_idx >= len(self.result.trades):
            return
        
        trade = self.result.trades[trade_idx]
        
        self.chart_widget.highlight_trade(
            trade.entry_time,
            trade.exit_time,
            trade.entry_price,
            trade.exit_price,
            trade.side
        )
        
        self.chart_widget.zoom_to_range(
            trade.entry_time,
            trade.exit_time,
            padding_ratio=0.5
        )
