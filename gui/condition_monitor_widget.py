# gui/condition_monitor_widget.py
"""
진입 조건 실시간 모니터링 위젯

30분봉 EMA 기반 조건 체크:
- 트렌드 방향 표시 (EMA 150 vs 200)
- 진입 신호 근접도 표시 (EMA 20 vs 50)
- 가상/실제 모드 전환 진행률
"""

from datetime import datetime
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QProgressBar, QFrame, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class ConditionMonitorWidget(QWidget):
    """
    진입 조건 실시간 모니터링 위젯
    
    구성:
    1. 트렌드 상태 패널 - EMA 150 vs 200
    2. 진입 신호 패널 - EMA 20/50 크로스오버 근접도
    3. 모드 전환 진행률 패널
    """
    
    condition_updated = pyqtSignal(dict)
    entry_signal_triggered = pyqtSignal(str, dict)  # 'long'/'short', data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data: Dict[str, Any] = {}
        self.is_monitoring = False
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 1. 트렌드 상태 패널
        trend_group = QGroupBox("📊 트렌드 상태 (30분봉)")
        trend_layout = QVBoxLayout(trend_group)
        trend_layout.setSpacing(8)
        
        # EMA 값 표시
        ema_grid = QGridLayout()
        ema_grid.setSpacing(5)
        
        ema150_label = QLabel("EMA 150:")
        ema150_label.setStyleSheet("color: #96CEB4;")
        self.ema150_value = QLabel("$0.00")
        self.ema150_value.setStyleSheet("color: #96CEB4; font-weight: bold; font-size: 13px;")
        self.ema150_value.setAlignment(Qt.AlignRight)
        
        ema200_label = QLabel("EMA 200:")
        ema200_label.setStyleSheet("color: #FFEAA7;")
        self.ema200_value = QLabel("$0.00")
        self.ema200_value.setStyleSheet("color: #FFEAA7; font-weight: bold; font-size: 13px;")
        self.ema200_value.setAlignment(Qt.AlignRight)
        
        ema_grid.addWidget(ema150_label, 0, 0)
        ema_grid.addWidget(self.ema150_value, 0, 1)
        ema_grid.addWidget(ema200_label, 1, 0)
        ema_grid.addWidget(self.ema200_value, 1, 1)
        trend_layout.addLayout(ema_grid)
        
        # 트렌드 상태
        self.trend_status_label = QLabel("📊 데이터 대기 중...")
        self.trend_status_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.trend_status_label.setAlignment(Qt.AlignCenter)
        self.trend_status_label.setMinimumHeight(40)
        self.trend_status_label.setStyleSheet("""
            QLabel { background-color: #3a3a3a; border-radius: 6px; padding: 8px; }
        """)
        trend_layout.addWidget(self.trend_status_label)
        
        # 강도 표시
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("강도:"))
        
        self.trend_strength_bar = QProgressBar()
        self.trend_strength_bar.setRange(0, 100)
        self.trend_strength_bar.setValue(50)
        self.trend_strength_bar.setTextVisible(False)
        self.trend_strength_bar.setMaximumHeight(15)
        self.trend_strength_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #3a3a3a; border-radius: 4px; background-color: #2b2b2b; }
            QProgressBar::chunk { background-color: #888888; border-radius: 3px; }
        """)
        strength_layout.addWidget(self.trend_strength_bar)
        
        self.trend_strength_text = QLabel("+0.00%")
        self.trend_strength_text.setMinimumWidth(70)
        self.trend_strength_text.setAlignment(Qt.AlignRight)
        strength_layout.addWidget(self.trend_strength_text)
        trend_layout.addLayout(strength_layout)
        
        layout.addWidget(trend_group)
        
        # 2. 진입 신호 상태 패널
        signal_group = QGroupBox("🚦 진입 신호 상태")
        signal_layout = QVBoxLayout(signal_group)
        signal_layout.setSpacing(8)
        
        # 롱 진입 패널
        self.long_signal_frame = self._create_signal_frame("롱 진입 (EMA 20/50 골든크로스)", "#28a745")
        signal_layout.addWidget(self.long_signal_frame)
        
        # 숏 진입 패널 (비활성)
        self.short_signal_frame = self._create_disabled_signal_frame("숏 진입 (현재 Long-only 전략)")
        signal_layout.addWidget(self.short_signal_frame)
        
        layout.addWidget(signal_group)
        
        # 3. 모드 전환 진행률 패널
        mode_group = QGroupBox("🔄 모드 전환 진행률")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(10)
        
        # 가상 → 실제
        v2r_label = QLabel("가상 → 실제 전환")
        v2r_label.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(v2r_label)
        
        v2r_desc = QLabel("(저점 대비 +30% 상승 필요)")
        v2r_desc.setStyleSheet("color: #888888; font-size: 11px;")
        mode_layout.addWidget(v2r_desc)
        
        self.v2r_progress = QProgressBar()
        self.v2r_progress.setRange(0, 100)
        self.v2r_progress.setValue(0)
        self.v2r_progress.setFormat("%v%")
        self.v2r_progress.setStyleSheet("""
            QProgressBar { border: 1px solid #28a745; border-radius: 4px; 
                          text-align: center; background-color: #1a3d1a; color: #ffffff; }
            QProgressBar::chunk { background-color: #28a745; }
        """)
        mode_layout.addWidget(self.v2r_progress)
        
        self.v2r_detail = QLabel("현재 수익률: +0.0%")
        self.v2r_detail.setStyleSheet("color: #28a745; font-size: 11px;")
        mode_layout.addWidget(self.v2r_detail)
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #3a3a3a;")
        mode_layout.addWidget(separator)
        
        # 실제 → 가상
        r2v_label = QLabel("실제 → 가상 전환")
        r2v_label.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(r2v_label)
        
        r2v_desc = QLabel("(고점 대비 -20% 하락 시)")
        r2v_desc.setStyleSheet("color: #888888; font-size: 11px;")
        mode_layout.addWidget(r2v_desc)
        
        self.r2v_progress = QProgressBar()
        self.r2v_progress.setRange(0, 100)
        self.r2v_progress.setValue(0)
        self.r2v_progress.setFormat("%v%")
        self.r2v_progress.setStyleSheet("""
            QProgressBar { border: 1px solid #dc3545; border-radius: 4px;
                          text-align: center; background-color: #3d1a1a; color: #ffffff; }
            QProgressBar::chunk { background-color: #dc3545; }
        """)
        mode_layout.addWidget(self.r2v_progress)
        
        self.r2v_detail = QLabel("현재 손실률: -0.0%")
        self.r2v_detail.setStyleSheet("color: #dc3545; font-size: 11px;")
        mode_layout.addWidget(self.r2v_detail)
        
        layout.addWidget(mode_group)
        layout.addStretch()
        
    def _create_signal_frame(self, title: str, color: str) -> QFrame:
        """진입 신호 프레임 생성"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ background-color: #2b2b2b; border: 1px solid {color}; 
                     border-radius: 6px; padding: 5px; }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 8, 10, 8)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 11, QFont.Bold))
        title_label.setStyleSheet(f"color: {color}; border: none;")
        layout.addWidget(title_label)
        
        # EMA 값 그리드
        ema_grid = QGridLayout()
        ema_grid.setSpacing(4)
        
        frame.ema20_label = QLabel("$0.00")
        frame.ema20_label.setStyleSheet("color: #FF6B6B; border: none;")
        frame.ema50_label = QLabel("$0.00")
        frame.ema50_label.setStyleSheet("color: #4ECDC4; border: none;")
        frame.gap_label = QLabel("0.000%")
        frame.gap_label.setStyleSheet("border: none;")
        
        ema20_title = QLabel("EMA 20:")
        ema20_title.setStyleSheet("color: #FF6B6B; border: none;")
        ema50_title = QLabel("EMA 50:")
        ema50_title.setStyleSheet("color: #4ECDC4; border: none;")
        gap_title = QLabel("갭:")
        gap_title.setStyleSheet("border: none;")
        
        ema_grid.addWidget(ema20_title, 0, 0)
        ema_grid.addWidget(frame.ema20_label, 0, 1)
        ema_grid.addWidget(ema50_title, 1, 0)
        ema_grid.addWidget(frame.ema50_label, 1, 1)
        ema_grid.addWidget(gap_title, 2, 0)
        ema_grid.addWidget(frame.gap_label, 2, 1)
        layout.addLayout(ema_grid)
        
        # 진행률 바
        frame.progress_bar = QProgressBar()
        frame.progress_bar.setRange(0, 100)
        frame.progress_bar.setValue(0)
        frame.progress_bar.setFormat("진행률: %v%")
        frame.progress_bar.setMaximumHeight(20)
        frame.progress_bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid {color}; border-radius: 4px;
                           text-align: center; background-color: #1e1e1e; color: #ffffff; }}
            QProgressBar::chunk {{ background-color: {color}; }}
        """)
        layout.addWidget(frame.progress_bar)
        
        frame.status_label = QLabel("⏳ 분석 중...")
        frame.status_label.setStyleSheet("color: #888888; font-size: 11px; border: none;")
        layout.addWidget(frame.status_label)
        
        return frame
    
    def _create_disabled_signal_frame(self, title: str) -> QFrame:
        """비활성화된 신호 프레임"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { background-color: #252525; border: 1px solid #3a3a3a;
                    border-radius: 6px; padding: 5px; }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666666; font-style: italic; border: none;")
        layout.addWidget(title_label)
        
        disabled_label = QLabel("현재 비활성화됨")
        disabled_label.setStyleSheet("color: #555555; font-size: 11px; border: none;")
        layout.addWidget(disabled_label)
        
        return frame
    
    def update_conditions(self, data: Dict[str, Any]):
        """조건 데이터 업데이트"""
        self.current_data = data
        self._update_trend(data)
        self._update_entry_signal(data)
        self._update_mode_progress(data)
        self.condition_updated.emit(data)
    
    def _update_trend(self, data: Dict[str, Any]):
        """트렌드 상태 업데이트"""
        ema150 = data.get('ema_trend_fast', data.get('ema_150', 0))
        ema200 = data.get('ema_trend_slow', data.get('ema_200', 0))
        
        self.ema150_value.setText(f"${ema150:,.2f}" if ema150 else "$0.00")
        self.ema200_value.setText(f"${ema200:,.2f}" if ema200 else "$0.00")
        
        if not ema150 or not ema200:
            self.trend_status_label.setText("📊 데이터 대기 중...")
            self.trend_status_label.setStyleSheet("""
                QLabel { background-color: #3a3a3a; border-radius: 6px; padding: 8px; color: #888888; }
            """)
            return
        
        is_uptrend = ema150 > ema200
        strength = ((ema150 - ema200) / ema200 * 100) if ema200 > 0 else 0
        
        if is_uptrend:
            self.trend_status_label.setText("📈 상승장 (EMA 150 > EMA 200)")
            self.trend_status_label.setStyleSheet("""
                QLabel { background-color: #1a3d1a; border: 1px solid #28a745;
                        border-radius: 6px; padding: 8px; color: #28a745; }
            """)
            bar_color = "#28a745"
        else:
            self.trend_status_label.setText("📉 하락장 (EMA 150 < EMA 200)")
            self.trend_status_label.setStyleSheet("""
                QLabel { background-color: #3d1a1a; border: 1px solid #dc3545;
                        border-radius: 6px; padding: 8px; color: #dc3545; }
            """)
            bar_color = "#dc3545"
        
        normalized = min(100, max(0, (abs(strength) / 2.0) * 100))
        self.trend_strength_bar.setValue(int(normalized))
        self.trend_strength_bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #3a3a3a; border-radius: 4px; background-color: #2b2b2b; }}
            QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 3px; }}
        """)
        
        self.trend_strength_text.setText(f"{strength:+.3f}%")
        self.trend_strength_text.setStyleSheet(f"color: {bar_color};")
    
    def _update_entry_signal(self, data: Dict[str, Any]):
        """진입 신호 상태 업데이트"""
        ema20 = data.get('curr_entry_fast', data.get('ema_20', 0))
        ema50 = data.get('curr_entry_slow', data.get('ema_50', 0))
        prev_ema20 = data.get('prev_entry_fast', 0)
        prev_ema50 = data.get('prev_entry_slow', 0)
        
        self.long_signal_frame.ema20_label.setText(f"${ema20:,.2f}" if ema20 else "$0.00")
        self.long_signal_frame.ema50_label.setText(f"${ema50:,.2f}" if ema50 else "$0.00")
        
        if not ema20 or not ema50:
            self.long_signal_frame.gap_label.setText("계산 중...")
            self.long_signal_frame.progress_bar.setValue(0)
            self.long_signal_frame.status_label.setText("⏳ 데이터 대기 중...")
            return
        
        gap = ((ema20 - ema50) / ema50 * 100) if ema50 > 0 else 0
        
        gap_color = "#28a745" if gap > 0 else "#dc3545" if gap < 0 else "#888888"
        self.long_signal_frame.gap_label.setText(f"{gap:+.4f}%")
        self.long_signal_frame.gap_label.setStyleSheet(f"color: {gap_color}; border: none;")
        
        was_below = prev_ema20 <= prev_ema50 if prev_ema20 and prev_ema50 else False
        is_above = ema20 > ema50
        is_golden_cross = was_below and is_above
        
        if is_golden_cross:
            self.long_signal_frame.progress_bar.setValue(100)
            self.long_signal_frame.status_label.setText("🔥 골든크로스 발생!")
            self.long_signal_frame.status_label.setStyleSheet("color: #28a745; font-weight: bold; border: none;")
            self.entry_signal_triggered.emit('long', data)
        elif is_above:
            progress = min(100, max(0, 50 + gap * 50))
            self.long_signal_frame.progress_bar.setValue(int(progress))
            self.long_signal_frame.status_label.setText("✅ EMA 20 > EMA 50 (진입 가능)")
            self.long_signal_frame.status_label.setStyleSheet("color: #4ECDC4; border: none;")
        else:
            progress = max(0, 50 - abs(gap) * 50)
            self.long_signal_frame.progress_bar.setValue(int(progress))
            
            if gap > -0.1:
                self.long_signal_frame.status_label.setText("⚡ 골든크로스 임박!")
                self.long_signal_frame.status_label.setStyleSheet("color: #ffc107; border: none;")
            else:
                self.long_signal_frame.status_label.setText("⏳ 골든크로스 대기 중...")
                self.long_signal_frame.status_label.setStyleSheet("color: #888888; border: none;")
    
    def _update_mode_progress(self, data: Dict[str, Any]):
        """모드 전환 진행률 업데이트"""
        is_real_mode = data.get('is_real_mode', False)
        
        if is_real_mode:
            real_capital = data.get('real_capital', 0)
            real_peak = data.get('real_peak', 0)
            stop_loss_ratio = data.get('stop_loss_ratio', 0.20)
            
            if real_peak > 0:
                loss_pct = (real_peak - real_capital) / real_peak * 100
                progress = min(100, (loss_pct / (stop_loss_ratio * 100)) * 100)
                self.r2v_progress.setValue(int(max(0, progress)))
                self.r2v_detail.setText(f"현재 손실률: -{loss_pct:.2f}% (/{stop_loss_ratio*100:.0f}%)")
            else:
                self.r2v_progress.setValue(0)
                self.r2v_detail.setText("현재 손실률: -0.0%")
            
            self.v2r_progress.setValue(0)
            self.v2r_detail.setText("(실제 모드 중)")
            self.v2r_detail.setStyleSheet("color: #666666; font-size: 11px;")
        else:
            virtual_capital = data.get('virtual_capital', 0)
            virtual_trough = data.get('virtual_trough', 0)
            reentry_ratio = data.get('reentry_ratio', 0.30)
            
            if virtual_trough > 0:
                gain_pct = (virtual_capital - virtual_trough) / virtual_trough * 100
                progress = min(100, (gain_pct / (reentry_ratio * 100)) * 100)
                self.v2r_progress.setValue(int(max(0, progress)))
                self.v2r_detail.setText(f"현재 수익률: +{gain_pct:.2f}% (/{reentry_ratio*100:.0f}%)")
            else:
                self.v2r_progress.setValue(0)
                self.v2r_detail.setText("현재 수익률: +0.0%")
            
            self.r2v_progress.setValue(0)
            self.r2v_detail.setText("(가상 모드 중)")
            self.r2v_detail.setStyleSheet("color: #666666; font-size: 11px;")
    
    def start_monitoring(self):
        self.is_monitoring = True
    
    def stop_monitoring(self):
        self.is_monitoring = False
    
    def reset(self):
        """초기화"""
        self.current_data = {}
        self.ema150_value.setText("$0.00")
        self.ema200_value.setText("$0.00")
        self.trend_status_label.setText("📊 데이터 대기 중...")
        self.trend_strength_bar.setValue(50)
        self.trend_strength_text.setText("+0.00%")
        self.long_signal_frame.ema20_label.setText("$0.00")
        self.long_signal_frame.ema50_label.setText("$0.00")
        self.long_signal_frame.gap_label.setText("0.000%")
        self.long_signal_frame.progress_bar.setValue(0)
        self.long_signal_frame.status_label.setText("⏳ 분석 중...")
        self.v2r_progress.setValue(0)
        self.v2r_detail.setText("현재 수익률: +0.0%")
        self.r2v_progress.setValue(0)
        self.r2v_detail.setText("현재 손실률: -0.0%")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow, QWidget { background-color: #1e1e1e; color: #ffffff; }
        QGroupBox { font-weight: bold; border: 1px solid #3a3a3a; border-radius: 5px;
                   margin-top: 10px; padding-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
    """)
    
    window = QMainWindow()
    window.setWindowTitle("Condition Monitor Test")
    window.setGeometry(100, 100, 400, 700)
    
    monitor = ConditionMonitorWidget()
    window.setCentralWidget(monitor)
    
    test_data = {
        'ema_trend_fast': 97123.45, 'ema_trend_slow': 96890.12,
        'curr_entry_fast': 97234.56, 'curr_entry_slow': 97180.23,
        'prev_entry_fast': 97100.00, 'prev_entry_slow': 97150.00,
        'is_real_mode': False,
        'virtual_capital': 11500, 'virtual_trough': 10000,
        'real_capital': 10000, 'real_peak': 10000,
    }
    monitor.update_conditions(test_data)
    
    window.show()
    sys.exit(app.exec_())
