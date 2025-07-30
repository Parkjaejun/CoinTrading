# gui/condition_widgets.py
"""
조건 모니터링 GUI 위젯들
실시간 조건 상태 표시 및 로그 출력
"""

import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QTextEdit, QTableWidget, QTableWidgetItem, QProgressBar,
    QFrame, QSplitter, QPushButton, QComboBox, QCheckBox, QSpinBox,
    QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

class ConditionStatusWidget(QWidget):
    """조건 상태 표시 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 시장 조건 그룹
        market_group = QGroupBox("📊 시장 조건")
        market_layout = QGridLayout()
        market_group.setLayout(market_layout)
        
        # 시장 조건 라벨들
        self.trend_label = QLabel("트렌드: --")
        self.trend_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.strength_label = QLabel("강도: --%")
        self.strength_progress = QProgressBar()
        self.strength_progress.setRange(0, 100)
        self.strength_progress.setValue(0)
        
        self.price_label = QLabel("현재가: $--")
        self.price_label.setFont(QFont("Arial", 11))
        
        market_layout.addWidget(QLabel("트렌드:"), 0, 0)
        market_layout.addWidget(self.trend_label, 0, 1)
        market_layout.addWidget(QLabel("강도:"), 1, 0)
        market_layout.addWidget(self.strength_progress, 1, 1)
        market_layout.addWidget(self.strength_label, 1, 2)
        market_layout.addWidget(self.price_label, 2, 0, 1, 3)
        
        # 신호 조건 그룹
        signal_group = QGroupBox("⚡ 신호 조건")
        signal_layout = QVBoxLayout()
        signal_group.setLayout(signal_layout)
        
        self.signal_table = QTableWidget()
        self.signal_table.setColumnCount(4)
        self.signal_table.setHorizontalHeaderLabels([
            "신호 유형", "상태", "거리(%)", "예상 시간"
        ])
        self.signal_table.setMaximumHeight(120)
        self.signal_table.horizontalHeader().setStretchLastSection(True)
        self.signal_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        signal_layout.addWidget(self.signal_table)
        
        # 전략 조건 그룹
        strategy_group = QGroupBox("🎯 전략 조건")
        strategy_layout = QVBoxLayout()
        strategy_group.setLayout(strategy_layout)
        
        self.strategy_table = QTableWidget()
        self.strategy_table.setColumnCount(5)
        self.strategy_table.setHorizontalHeaderLabels([
            "전략", "모드", "수익률(%)", "전환 목표", "거리"
        ])
        self.strategy_table.setMaximumHeight(120)
        self.strategy_table.horizontalHeader().setStretchLastSection(True)
        self.strategy_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        strategy_layout.addWidget(self.strategy_table)
        
        # 레이아웃 추가
        layout.addWidget(market_group)
        layout.addWidget(signal_group)
        layout.addWidget(strategy_group)
        
        # 스타일 적용
        self.apply_dark_style()
    
    def apply_dark_style(self):
        """다크 테마 스타일 적용"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin: 5px;
                padding-top: 10px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                color: #ffffff;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #3a3a3a;
                border: 1px solid #555555;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #2b2b2b;
            }
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
    
    def update_market_condition(self, market_condition):
        """시장 조건 업데이트"""
        if not market_condition:
            return
        
        # 트렌드 방향 표시
        trend_text = market_condition.trend_direction.value
        if market_condition.trend_direction.name == "UPTREND":
            self.trend_label.setText(f"📈 {trend_text}")
            self.trend_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        elif market_condition.trend_direction.name == "DOWNTREND":
            self.trend_label.setText(f"📉 {trend_text}")
            self.trend_label.setStyleSheet("color: #ff6666; font-weight: bold;")
        else:
            self.trend_label.setText(f"➡️ {trend_text}")
            self.trend_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        
        # 트렌드 강도
        strength = min(100, abs(market_condition.trend_strength))
        self.strength_progress.setValue(int(strength))
        self.strength_label.setText(f"{market_condition.trend_strength:.2f}%")
        
        # 현재가
        self.price_label.setText(f"현재가: ${market_condition.current_price:,.2f}")
    
    def update_signal_conditions(self, signal_conditions: List):
        """신호 조건 업데이트"""
        self.signal_table.setRowCount(len(signal_conditions))
        
        for i, signal in enumerate(signal_conditions):
            # 신호 유형
            type_item = QTableWidgetItem(signal.signal_type)
            self.signal_table.setItem(i, 0, type_item)
            
            # 상태
            status_item = QTableWidgetItem(signal.status.value)
            if signal.status.name == "TRIGGERED":
                status_item.setForeground(QColor("#ff0000"))
                status_item.setText("🚨 " + status_item.text())
            elif signal.status.name == "APPROACHING":
                status_item.setForeground(QColor("#ffaa00"))
                status_item.setText("⚡ " + status_item.text())
            else:
                status_item.setForeground(QColor("#00ff00"))
                status_item.setText("⏳ " + status_item.text())
            
            self.signal_table.setItem(i, 1, status_item)
            
            # 거리
            distance_item = QTableWidgetItem(f"{signal.distance_pct:.3f}%")
            self.signal_table.setItem(i, 2, distance_item)
            
            # 예상 시간
            time_item = QTableWidgetItem(signal.estimated_time or "--")
            self.signal_table.setItem(i, 3, time_item)
    
    def update_strategy_conditions(self, strategy_conditions: List):
        """전략 조건 업데이트"""
        self.strategy_table.setRowCount(len(strategy_conditions))
        
        for i, strategy in enumerate(strategy_conditions):
            # 전략명
            name_item = QTableWidgetItem(strategy.strategy_name)
            self.strategy_table.setItem(i, 0, name_item)
            
            # 모드
            mode_text = "🔴 실제" if strategy.is_real_mode else "🟡 가상"
            mode_item = QTableWidgetItem(mode_text)
            if strategy.is_real_mode:
                mode_item.setForeground(QColor("#ff6666"))
            else:
                mode_item.setForeground(QColor("#ffaa00"))
            self.strategy_table.setItem(i, 1, mode_item)
            
            # 수익률
            return_item = QTableWidgetItem(f"{strategy.return_pct:+.2f}%")
            if strategy.return_pct > 0:
                return_item.setForeground(QColor("#00ff00"))
            elif strategy.return_pct < 0:
                return_item.setForeground(QColor("#ff6666"))
            self.strategy_table.setItem(i, 2, return_item)
            
            # 전환 목표
            target_item = QTableWidgetItem(f"+{strategy.switch_threshold}%")
            self.strategy_table.setItem(i, 3, target_item)
            
            # 거리
            if strategy.is_real_mode:
                distance_text = "활성화됨"
                distance_item = QTableWidgetItem(distance_text)
                distance_item.setForeground(QColor("#00ff00"))
            else:
                distance_text = f"{strategy.distance_to_switch:.1f}%p"
                distance_item = QTableWidgetItem(distance_text)
                if strategy.distance_to_switch < 5:
                    distance_item.setForeground(QColor("#ffaa00"))
            
            self.strategy_table.setItem(i, 4, distance_item)


class ConditionLogWidget(QWidget):
    """조건 로그 표시 위젯"""
    
    def __init__(self):
        super().__init__()
        self.max_log_lines = 500
        self.setup_ui()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 제어 패널
        control_layout = QHBoxLayout()
        
        self.auto_scroll_check = QCheckBox("자동 스크롤")
        self.auto_scroll_check.setChecked(True)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "전체", "시장 조건", "신호 조건", "전략 조건", "경고", "오류"
        ])
        
        self.clear_btn = QPushButton("로그 지우기")
        self.clear_btn.clicked.connect(self.clear_logs)
        
        control_layout.addWidget(QLabel("필터:"))
        control_layout.addWidget(self.filter_combo)
        control_layout.addWidget(self.auto_scroll_check)
        control_layout.addStretch()
        control_layout.addWidget(self.clear_btn)
        
        # 로그 표시 영역
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        
        layout.addLayout(control_layout)
        layout.addWidget(self.log_text)
        
        # 스타일 적용
        self.apply_dark_style()
    
    def apply_dark_style(self):
        """다크 테마 스타일 적용"""
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #555555;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QCheckBox {
                color: #ffffff;
            }
            QComboBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 4px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QLabel {
                color: #ffffff;
            }
        """)
    
    def add_log(self, message: str, log_type: str = "정보"):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 로그 타입별 색상 및 아이콘
        if log_type == "시장 조건":
            color = "#00aaff"
            icon = "📊"
        elif log_type == "신호 조건":
            color = "#ffaa00"
            icon = "⚡"
        elif log_type == "전략 조건":
            color = "#00ff00"
            icon = "🎯"
        elif log_type == "경고":
            color = "#ff6666"
            icon = "⚠️"
        elif log_type == "오류":
            color = "#ff0000"
            icon = "❌"
        else:
            color = "#ffffff"
            icon = "ℹ️"
        
        # HTML 포맷으로 로그 추가
        log_entry = f"""
        <span style="color: #888888;">[{timestamp}]</span> 
        <span style="color: {color};">{icon} {message}</span>
        """
        
        self.log_text.append(log_entry)
        
        # 자동 스크롤
        if self.auto_scroll_check.isChecked():
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.End)
            self.log_text.setTextCursor(cursor)
        
        # 최대 라인 수 제한
        document = self.log_text.document()
        if document.blockCount() > self.max_log_lines:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 
                              document.blockCount() - self.max_log_lines)
            cursor.removeSelectedText()
    
    def clear_logs(self):
        """로그 지우기"""
        self.log_text.clear()
        self.add_log("로그가 지워졌습니다.", "정보")


class ConditionStatsWidget(QWidget):
    """조건 통계 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QGridLayout()
        self.setLayout(layout)
        
        # 통계 라벨들
        self.total_checks_label = QLabel("총 체크: 0회")
        self.uptime_label = QLabel("가동 시간: 0분")
        self.trend_stats_label = QLabel("트렌드: 상승 0 | 하락 0 | 횡보 0")
        self.signal_stats_label = QLabel("신호: 골든크로스 0 | 데드크로스 0")
        self.mode_stats_label = QLabel("모드: 가상 0 | 실제 0")
        self.switch_label = QLabel("전환 기회: 0회")
        
        # 폰트 설정
        font = QFont("Arial", 10)
        for label in [self.total_checks_label, self.uptime_label, 
                     self.trend_stats_label, self.signal_stats_label,
                     self.mode_stats_label, self.switch_label]:
            label.setFont(font)
        
        # 레이아웃 배치
        layout.addWidget(self.total_checks_label, 0, 0)
        layout.addWidget(self.uptime_label, 0, 1)
        layout.addWidget(self.trend_stats_label, 1, 0, 1, 2)
        layout.addWidget(self.signal_stats_label, 2, 0, 1, 2)
        layout.addWidget(self.mode_stats_label, 3, 0)
        layout.addWidget(self.switch_label, 3, 1)
        
        # 스타일 적용
        self.setStyleSheet("QLabel { color: #ffffff; }")
    
    def update_stats(self, stats: Dict[str, Any]):
        """통계 업데이트"""
        if not stats:
            return
        
        # 기본 통계
        self.total_checks_label.setText(f"총 체크: {stats.get('total_checks', 0):,}회")
        self.uptime_label.setText(f"가동 시간: {stats.get('uptime_minutes', 0):.1f}분")
        
        # 트렌드 분포
        trend_dist = stats.get('trend_distribution', {})
        self.trend_stats_label.setText(
            f"트렌드: 상승 {trend_dist.get('uptrend', 0)} | "
            f"하락 {trend_dist.get('downtrend', 0)} | "
            f"횡보 {trend_dist.get('sideways', 0)}"
        )
        
        # 신호 카운트
        signal_counts = stats.get('signal_counts', {})
        self.signal_stats_label.setText(
            f"신호: 골든크로스 {signal_counts.get('golden_cross', 0)} | "
            f"데드크로스 {signal_counts.get('dead_cross', 0)}"
        )
        
        # 모드 분포
        mode_dist = stats.get('mode_distribution', {})
        self.mode_stats_label.setText(
            f"모드: 가상 {mode_dist.get('virtual', 0)} | "
            f"실제 {mode_dist.get('real', 0)}"
        )
        
        # 전환 기회
        self.switch_label.setText(f"전환 기회: {stats.get('switch_opportunities', 0)}회")


class ConditionMonitoringWidget(QWidget):
    """통합 조건 모니터링 위젯"""
    
    # 시그널 정의
    condition_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.condition_monitor = None  # 나중에 설정
        self.setup_ui()
        self.setup_timer()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 스플리터로 영역 분할
        main_splitter = QSplitter(Qt.Vertical)
        
        # 상단: 조건 상태 표시
        status_frame = QFrame()
        status_layout = QVBoxLayout()
        status_frame.setLayout(status_layout)
        
        self.status_widget = ConditionStatusWidget()
        self.stats_widget = ConditionStatsWidget()
        
        status_layout.addWidget(self.status_widget)
        status_layout.addWidget(self.stats_widget)
        
        # 하단: 로그 표시
        self.log_widget = ConditionLogWidget()
        
        # 스플리터에 추가
        main_splitter.addWidget(status_frame)
        main_splitter.addWidget(self.log_widget)
        main_splitter.setSizes([300, 200])  # 상단:하단 비율
        
        layout.addWidget(main_splitter)
        
        # 초기 로그 메시지
        self.log_widget.add_log("조건 모니터링 시스템 초기화됨", "정보")
    
    def setup_timer(self):
        """업데이트 타이머 설정"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # 1초마다 업데이트
    
    def set_condition_monitor(self, condition_monitor):
        """조건 모니터 설정"""
        self.condition_monitor = condition_monitor
        self.log_widget.add_log("조건 모니터링 연결됨", "정보")
    
    def update_display(self):
        """화면 업데이트"""
        if not self.condition_monitor:
            return
        
        try:
            # 통계 업데이트
            stats = self.condition_monitor.get_summary_stats()
            self.stats_widget.update_stats(stats)
            
            # 최근 히스토리에서 최신 조건 상태 가져오기
            recent_history = self.condition_monitor.get_recent_history(5)  # 최근 5분
            if recent_history:
                latest_status = recent_history[-1]
                
                # 조건 상태 업데이트
                market_condition = latest_status.get('market_condition')
                signal_conditions = latest_status.get('signal_conditions', [])
                strategy_conditions = latest_status.get('strategy_conditions', [])
                
                self.status_widget.update_market_condition(market_condition)
                self.status_widget.update_signal_conditions(signal_conditions)
                self.status_widget.update_strategy_conditions(strategy_conditions)
                
        except Exception as e:
            self.log_widget.add_log(f"화면 업데이트 오류: {e}", "오류")
    
    def add_condition_log(self, message: str, log_type: str = "정보"):
        """조건 로그 추가 (외부에서 호출)"""
        self.log_widget.add_log(message, log_type)
    
    def handle_condition_change(self, condition_data: Dict[str, Any]):
        """조건 변화 처리"""
        if not condition_data:
            return
        
        # 중요한 변화 감지 및 로깅
        market = condition_data.get('market_condition')
        if market:
            trend_name = market.trend_direction.name
            if trend_name in ['UPTREND', 'DOWNTREND']:
                self.add_condition_log(
                    f"{market.symbol}: {market.trend_direction.value} "
                    f"(강도: {market.trend_strength:.2f}%)",
                    "시장 조건"
                )
        
        # 신호 상태 로깅
        signals = condition_data.get('signal_conditions', [])
        for signal in signals:
            if signal.status.name == "TRIGGERED":
                self.add_condition_log(
                    f"{signal.signal_type} 신호 발생!",
                    "신호 조건"
                )
            elif signal.status.name == "APPROACHING":
                self.add_condition_log(
                    f"{signal.signal_type} 접근 중 "
                    f"(거리: {signal.distance_pct:.3f}%)",
                    "신호 조건"
                )
        
        # 전략 상태 로깅
        strategies = condition_data.get('strategy_conditions', [])
        for strategy in strategies:
            if not strategy.is_real_mode and strategy.distance_to_switch < 5:
                self.add_condition_log(
                    f"{strategy.strategy_name}: 실제거래 전환 임박 "
                    f"(현재 수익률: {strategy.return_pct:+.1f}%)",
                    "전략 조건"
                )
        
        # 시그널 발송
        self.condition_updated.emit(condition_data)