# gui/backtest_widget.py
"""
메인 백테스트 탭 위젯
- 모든 하위 위젯 통합
- 백테스트 워크플로우 관리
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
    QDateEdit, QProgressBar, QFrame, QFileDialog,
    QMessageBox, QGroupBox, QCheckBox, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont

# 상위 디렉토리 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.data_fetcher import DataFetcher
from backtest.backtest_engine import BacktestEngine, Params, BacktestResult
from backtest.result_analyzer import ResultAnalyzer

from gui.chart_widget import BacktestChartWidget
from gui.trade_table_widget import TradeTableWidget
from gui.stats_widget import StatsWidget


class BacktestWorker(QThread):
    """백테스트 작업 스레드"""
    
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(object)  # BacktestResult
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
    finished = pyqtSignal(object)  # DataFrame
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
        """UI 구성"""
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
        settings_layout = QHBoxLayout(settings_frame)
        settings_layout.setContentsMargins(15, 10, 15, 10)
        
        # 기간 설정
        settings_layout.addWidget(QLabel("기간:"))
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate(2026, 1, 1))
        self.start_date.setStyleSheet("background-color: #3a3a3a; color: white; padding: 5px;")
        settings_layout.addWidget(self.start_date)
        
        settings_layout.addWidget(QLabel("~"))
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate(2026, 1, 31))
        self.end_date.setStyleSheet("background-color: #3a3a3a; color: white; padding: 5px;")
        settings_layout.addWidget(self.end_date)
        
        settings_layout.addSpacing(20)
        
        # 초기 자본
        settings_layout.addWidget(QLabel("초기자본:"))
        self.initial_capital = QDoubleSpinBox()
        self.initial_capital.setRange(100, 10000000)
        self.initial_capital.setValue(10000)
        self.initial_capital.setPrefix("$")
        self.initial_capital.setDecimals(0)
        self.initial_capital.setStyleSheet("background-color: #3a3a3a; color: white; padding: 5px;")
        settings_layout.addWidget(self.initial_capital)
        
        settings_layout.addSpacing(20)
        
        # Long Only 체크박스
        self.long_only_check = QCheckBox("Long Only")
        self.long_only_check.setChecked(True)
        self.long_only_check.setStyleSheet("color: white;")
        settings_layout.addWidget(self.long_only_check)
        
        settings_layout.addStretch()
        
        # 버튼들
        self.load_csv_btn = QPushButton("📂 CSV 로드")
        self.load_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        settings_layout.addWidget(self.load_csv_btn)
        
        self.fetch_btn = QPushButton("📥 데이터 가져오기")
        self.fetch_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        settings_layout.addWidget(self.fetch_btn)
        
        self.run_btn = QPushButton("▶️ 시뮬레이션 실행")
        self.run_btn.setEnabled(False)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #00aa55;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #00cc66;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        settings_layout.addWidget(self.run_btn)
        
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
        
        # === 메인 스플리터 (차트 / 결과) ===
        main_splitter = QSplitter(Qt.Vertical)
        
        # 차트 위젯
        self.chart_widget = BacktestChartWidget()
        main_splitter.addWidget(self.chart_widget)
        
        # 하단 스플리터 (테이블 / 통계)
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
        """시그널 연결"""
        self.load_csv_btn.clicked.connect(self._on_load_csv)
        self.fetch_btn.clicked.connect(self._on_fetch_data)
        self.run_btn.clicked.connect(self._on_run_backtest)
        self.trade_table.trade_selected.connect(self._on_trade_selected)
    
    def _on_load_csv(self):
        """CSV 파일 로드"""
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
            
            # 차트에 데이터 표시
            self._update_chart_data()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"CSV 로드 실패:\n{str(e)}")
            self.status_label.setText("CSV 로드 실패")
    
    def _on_fetch_data(self):
        """데이터 가져오기"""
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
        """데이터 수집 진행률"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)
    
    def _on_fetch_finished(self, df):
        """데이터 수집 완료"""
        self.df = df
        self.progress_bar.setVisible(False)
        self.fetch_btn.setEnabled(True)
        self.run_btn.setEnabled(True)
        
        self.status_label.setText(f"데이터 로드 완료: {len(df):,}개 캔들")
        
        # 차트에 데이터 표시
        self._update_chart_data()
    
    def _on_fetch_error(self, error_msg):
        """데이터 수집 오류"""
        self.progress_bar.setVisible(False)
        self.fetch_btn.setEnabled(True)
        self.status_label.setText(f"오류: {error_msg}")
        QMessageBox.critical(self, "오류", f"데이터 가져오기 실패:\n{error_msg}")
    
    def _on_run_backtest(self):
        """백테스트 실행"""
        if self.df is None:
            QMessageBox.warning(self, "경고", "먼저 데이터를 로드하세요.")
            return
        
        # 파라미터 설정
        params = Params(long_only=self.long_only_check.isChecked())
        
        engine = BacktestEngine(
            params=params,
            initial_capital=self.initial_capital.value()
        )
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.run_btn.setEnabled(False)
        self.status_label.setText("백테스트 실행 중...")
        
        self.backtest_worker = BacktestWorker(engine, self.df)
        self.backtest_worker.progress.connect(self._on_backtest_progress)
        self.backtest_worker.finished.connect(self._on_backtest_finished)
        self.backtest_worker.error.connect(self._on_backtest_error)
        self.backtest_worker.start()
    
    def _on_backtest_progress(self, current, total, message):
        """백테스트 진행률"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)
    
    def _on_backtest_finished(self, result: BacktestResult):
        """백테스트 완료"""
        self.result = result
        self.progress_bar.setVisible(False)
        self.run_btn.setEnabled(True)
        
        # 결과 표시
        self._display_results()
        
        self.status_label.setText(
            f"백테스트 완료: {result.total_trades}건 거래, "
            f"REAL ROI: {result.real_roi:+.2f}%"
        )
    
    def _on_backtest_error(self, error_msg):
        """백테스트 오류"""
        self.progress_bar.setVisible(False)
        self.run_btn.setEnabled(True)
        self.status_label.setText(f"오류: {error_msg}")
        QMessageBox.critical(self, "오류", f"백테스트 실패:\n{error_msg}")
    
    def _update_chart_data(self):
        """차트 데이터 업데이트"""
        if self.df is None:
            return
        
        self.chart_widget.set_data(self.df)
    
    def _display_results(self):
        """결과 표시"""
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
        """거래 선택 시 차트 하이라이트"""
        if self.result is None or trade_idx >= len(self.result.trades):
            return
        
        trade = self.result.trades[trade_idx]
        
        # 차트 하이라이트
        self.chart_widget.highlight_trade(
            trade.entry_time,
            trade.exit_time,
            trade.entry_price,
            trade.exit_price,
            trade.side
        )
        
        # 해당 구간으로 줌
        self.chart_widget.zoom_to_range(
            trade.entry_time,
            trade.exit_time,
            padding_ratio=0.5
        )
