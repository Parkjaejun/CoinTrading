# gui/debug_condition_monitoring.py
"""
조건 모니터링 시스템 종합 디버깅 도구
GUI의 별도 탭으로 추가하거나 독립 실행 가능
"""

import time
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QGroupBox, QGridLayout,
    QTextEdit, QTabWidget, QProgressBar, QSplitter, QFrame,
    QCheckBox, QSpinBox, QComboBox, QFormLayout, QScrollArea
)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor, QTextCursor

class DebugLevel(Enum):
    """디버그 레벨"""
    INFO = "정보"
    WARNING = "경고"
    ERROR = "오류"
    SUCCESS = "성공"
    DEBUG = "디버그"

class ConditionMonitoringDebugger(QWidget):
    """조건 모니터링 시스템 종합 디버거"""
    
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.debug_logs = []
        self.test_results = {}
        
        # 디버깅 설정
        self.auto_debug_enabled = False
        self.debug_interval = 5  # 5초마다 자동 체크
        
        self.setup_ui()
        self.setup_timers()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 상단 제어 패널
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        # 탭 위젯
        tab_widget = QTabWidget()
        
        # 1. 시스템 상태 탭
        tab_widget.addTab(self.create_system_status_tab(), "🔍 시스템 상태")
        
        # 2. 실시간 테스트 탭
        tab_widget.addTab(self.create_realtime_test_tab(), "🧪 실시간 테스트")
        
        # 3. 데이터 흐름 탭
        tab_widget.addTab(self.create_data_flow_tab(), "📊 데이터 흐름")
        
        # 4. 디버그 로그 탭
        tab_widget.addTab(self.create_debug_log_tab(), "📝 디버그 로그")
        
        layout.addWidget(tab_widget)
        
    def create_control_panel(self) -> QWidget:
        """제어 패널 생성"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMaximumHeight(80)
        
        layout = QHBoxLayout()
        panel.setLayout(layout)
        
        # 전체 시스템 체크
        full_check_btn = QPushButton("🔍 전체 시스템 체크")
        full_check_btn.clicked.connect(self.run_full_system_check)
        full_check_btn.setStyleSheet("background-color: #007bff; font-weight: bold;")
        
        # 조건 모니터링 강제 시작
        force_start_btn = QPushButton("🚀 모니터링 강제 시작")
        force_start_btn.clicked.connect(self.force_start_monitoring)
        force_start_btn.setStyleSheet("background-color: #28a745;")
        
        # 데이터 흐름 테스트
        data_flow_btn = QPushButton("📊 데이터 흐름 테스트")
        data_flow_btn.clicked.connect(self.test_data_flow)
        data_flow_btn.setStyleSheet("background-color: #17a2b8;")
        
        # 위젯 연결 테스트
        widget_test_btn = QPushButton("🔗 위젯 연결 테스트")
        widget_test_btn.clicked.connect(self.test_widget_connections)
        widget_test_btn.setStyleSheet("background-color: #ffc107;")
        
        # 자동 디버깅 토글
        self.auto_debug_checkbox = QCheckBox("자동 디버깅")
        self.auto_debug_checkbox.toggled.connect(self.toggle_auto_debug)
        
        layout.addWidget(full_check_btn)
        layout.addWidget(force_start_btn)
        layout.addWidget(data_flow_btn)
        layout.addWidget(widget_test_btn)
        layout.addStretch()
        layout.addWidget(self.auto_debug_checkbox)
        
        return panel
        
    def create_system_status_tab(self) -> QWidget:
        """시스템 상태 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 상태 표시 그룹
        status_group = QGroupBox("🔧 시스템 컴포넌트 상태")
        status_layout = QGridLayout()
        status_group.setLayout(status_layout)
        
        # 상태 라벨들
        self.main_window_status = QLabel("❓ 확인 중...")
        self.condition_monitor_status = QLabel("❓ 확인 중...")
        self.condition_widget_status = QLabel("❓ 확인 중...")
        self.monitoring_tab_status = QLabel("❓ 확인 중...")
        self.timer_status = QLabel("❓ 확인 중...")
        self.data_source_status = QLabel("❓ 확인 중...")
        
        status_layout.addWidget(QLabel("메인 윈도우:"), 0, 0)
        status_layout.addWidget(self.main_window_status, 0, 1)
        status_layout.addWidget(QLabel("조건 모니터:"), 1, 0)
        status_layout.addWidget(self.condition_monitor_status, 1, 1)
        status_layout.addWidget(QLabel("조건 위젯:"), 2, 0)
        status_layout.addWidget(self.condition_widget_status, 2, 1)
        status_layout.addWidget(QLabel("모니터링 탭:"), 3, 0)
        status_layout.addWidget(self.monitoring_tab_status, 3, 1)
        status_layout.addWidget(QLabel("타이머:"), 4, 0)
        status_layout.addWidget(self.timer_status, 4, 1)
        status_layout.addWidget(QLabel("데이터 소스:"), 5, 0)
        status_layout.addWidget(self.data_source_status, 5, 1)
        
        layout.addWidget(status_group)
        
        # 카운터 상태 그룹
        counter_group = QGroupBox("📊 카운터 및 통계")
        counter_layout = QGridLayout()
        counter_group.setLayout(counter_layout)
        
        self.counter_labels = {}
        counter_names = [
            "총 체크 횟수", "트렌드 상승", "트렌드 하락", 
            "롱 신호", "숏 신호", "실제 모드", "가상 모드"
        ]
        
        for i, name in enumerate(counter_names):
            counter_layout.addWidget(QLabel(f"{name}:"), i, 0)
            label = QLabel("0")
            self.counter_labels[name] = label
            counter_layout.addWidget(label, i, 1)
        
        layout.addWidget(counter_group)
        layout.addStretch()
        
        return widget
        
    def create_realtime_test_tab(self) -> QWidget:
        """실시간 테스트 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 테스트 설정
        test_group = QGroupBox("🧪 테스트 설정")
        test_layout = QFormLayout()
        test_group.setLayout(test_layout)
        
        self.test_symbol_combo = QComboBox()
        self.test_symbol_combo.addItems(["BTC-USDT-SWAP", "ETH-USDT-SWAP", "더미 데이터"])
        
        self.test_interval_spin = QSpinBox()
        self.test_interval_spin.setRange(1, 60)
        self.test_interval_spin.setValue(5)
        self.test_interval_spin.setSuffix("초")
        
        test_layout.addRow("테스트 심볼:", self.test_symbol_combo)
        test_layout.addRow("테스트 간격:", self.test_interval_spin)
        
        # 테스트 버튼들
        test_buttons = QHBoxLayout()
        
        single_test_btn = QPushButton("단일 조건 테스트")
        single_test_btn.clicked.connect(self.run_single_condition_test)
        
        continuous_test_btn = QPushButton("연속 테스트 시작")
        continuous_test_btn.clicked.connect(self.start_continuous_test)
        
        stop_test_btn = QPushButton("테스트 중지")
        stop_test_btn.clicked.connect(self.stop_continuous_test)
        
        test_buttons.addWidget(single_test_btn)
        test_buttons.addWidget(continuous_test_btn)
        test_buttons.addWidget(stop_test_btn)
        
        layout.addWidget(test_group)
        layout.addLayout(test_buttons)
        
        # 테스트 결과 표시
        result_group = QGroupBox("📋 테스트 결과")
        result_layout = QVBoxLayout()
        result_group.setLayout(result_layout)
        
        self.test_result_display = QTextEdit()
        self.test_result_display.setMaximumHeight(200)
        self.test_result_display.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        
        result_layout.addWidget(self.test_result_display)
        layout.addWidget(result_group)
        
        layout.addStretch()
        return widget
        
    def create_data_flow_tab(self) -> QWidget:
        """데이터 흐름 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 데이터 흐름 표시
        flow_group = QGroupBox("📊 데이터 흐름 모니터링")
        flow_layout = QVBoxLayout()
        flow_group.setLayout(flow_layout)
        
        self.data_flow_display = QTextEdit()
        self.data_flow_display.setStyleSheet("background-color: #1e1e1e; color: #00ff00;")
        
        flow_layout.addWidget(self.data_flow_display)
        layout.addWidget(flow_group)
        
        # 데이터 주입 테스트
        inject_group = QGroupBox("💉 테스트 데이터 주입")
        inject_layout = QHBoxLayout()
        inject_group.setLayout(inject_layout)
        
        inject_dummy_btn = QPushButton("더미 데이터 주입")
        inject_dummy_btn.clicked.connect(self.inject_dummy_data)
        
        inject_real_btn = QPushButton("실제 데이터 시뮬레이션")
        inject_real_btn.clicked.connect(self.inject_realistic_data)
        
        inject_extreme_btn = QPushButton("극한 조건 테스트")
        inject_extreme_btn.clicked.connect(self.inject_extreme_data)
        
        inject_layout.addWidget(inject_dummy_btn)
        inject_layout.addWidget(inject_real_btn)
        inject_layout.addWidget(inject_extreme_btn)
        
        layout.addWidget(inject_group)
        return widget
        
    def create_debug_log_tab(self) -> QWidget:
        """디버그 로그 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 로그 필터
        filter_group = QGroupBox("🔍 로그 필터")
        filter_layout = QHBoxLayout()
        filter_group.setLayout(filter_layout)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["전체", "정보", "경고", "오류", "성공", "디버그"])
        
        clear_log_btn = QPushButton("로그 지우기")
        clear_log_btn.clicked.connect(self.clear_debug_logs)
        
        export_log_btn = QPushButton("로그 내보내기")
        export_log_btn.clicked.connect(self.export_debug_logs)
        
        filter_layout.addWidget(QLabel("레벨:"))
        filter_layout.addWidget(self.log_level_combo)
        filter_layout.addStretch()
        filter_layout.addWidget(clear_log_btn)
        filter_layout.addWidget(export_log_btn)
        
        layout.addWidget(filter_group)
        
        # 로그 표시
        self.debug_log_display = QTextEdit()
        self.debug_log_display.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        layout.addWidget(self.debug_log_display)
        
        return widget
        
    def setup_timers(self):
        """타이머 설정"""
        # 상태 업데이트 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_system_status)
        self.status_timer.start(2000)  # 2초마다
        
        # 자동 디버깅 타이머
        self.auto_debug_timer = QTimer()
        self.auto_debug_timer.timeout.connect(self.run_auto_debug_check)
        
        # 연속 테스트 타이머
        self.continuous_test_timer = QTimer()
        self.continuous_test_timer.timeout.connect(self.run_single_condition_test)
        
    # ========== 시스템 체크 메서드들 ==========
    
    def run_full_system_check(self):
        """전체 시스템 종합 체크"""
        self.add_debug_log("🔍 전체 시스템 체크 시작", DebugLevel.INFO)
        
        checks = [
            ("메인 윈도우 체크", self.check_main_window),
            ("조건 모니터 체크", self.check_condition_monitor),
            ("조건 위젯 체크", self.check_condition_widget),
            ("타이머 체크", self.check_timers),
            ("데이터 소스 체크", self.check_data_sources),
            ("GUI 연결 체크", self.check_gui_connections),
            ("메모리 및 성능 체크", self.check_performance)
        ]
        
        results = {}
        for check_name, check_func in checks:
            try:
                self.add_debug_log(f"⏳ {check_name} 실행 중...", DebugLevel.DEBUG)
                result = check_func()
                results[check_name] = result
                
                if result.get('success', False):
                    self.add_debug_log(f"✅ {check_name} 성공", DebugLevel.SUCCESS)
                else:
                    self.add_debug_log(f"❌ {check_name} 실패: {result.get('error', '알 수 없는 오류')}", DebugLevel.ERROR)
                    
            except Exception as e:
                error_msg = f"{check_name} 예외 발생: {e}"
                self.add_debug_log(f"🚨 {error_msg}", DebugLevel.ERROR)
                results[check_name] = {'success': False, 'error': str(e)}
        
        # 결과 요약
        success_count = sum(1 for r in results.values() if r.get('success', False))
        total_count = len(results)
        
        self.add_debug_log(f"📊 전체 시스템 체크 완료: {success_count}/{total_count} 성공", 
                          DebugLevel.SUCCESS if success_count == total_count else DebugLevel.WARNING)
        
        self.test_results['full_system_check'] = results
        
    def check_main_window(self) -> Dict[str, Any]:
        """메인 윈도우 체크"""
        if not self.main_window:
            return {'success': False, 'error': '메인 윈도우 객체 없음'}
        
        checks = {
            'condition_monitor_exists': hasattr(self.main_window, 'condition_monitor'),
            'condition_widget_exists': hasattr(self.main_window, 'condition_widget'),
            'tab_widget_exists': hasattr(self.main_window, 'tab_widget'),
            'condition_monitor_not_none': getattr(self.main_window, 'condition_monitor', None) is not None
        }
        
        all_passed = all(checks.values())
        
        return {
            'success': all_passed,
            'details': checks,
            'error': None if all_passed else '일부 컴포넌트 누락'
        }
        
    def check_condition_monitor(self) -> Dict[str, Any]:
        """조건 모니터 체크"""
        if not self.main_window or not hasattr(self.main_window, 'condition_monitor'):
            return {'success': False, 'error': '조건 모니터 객체 없음'}
        
        monitor = self.main_window.condition_monitor
        if not monitor:
            return {'success': False, 'error': '조건 모니터가 None'}
        
        checks = {
            'has_counters': hasattr(monitor, 'counters'),
            'has_check_method': hasattr(monitor, 'check_conditions'),
            'has_monitoring_active': hasattr(monitor, 'monitoring_active'),
            'monitoring_active_value': getattr(monitor, 'monitoring_active', False)
        }
        
        all_passed = all(checks.values())
        
        return {
            'success': all_passed,
            'details': checks,
            'counters': getattr(monitor, 'counters', {}),
            'error': None if all_passed else '조건 모니터 설정 문제'
        }
        
    def check_condition_widget(self) -> Dict[str, Any]:
        """조건 위젯 체크"""
        if not self.main_window or not hasattr(self.main_window, 'condition_widget'):
            return {'success': False, 'error': '조건 위젯 객체 없음'}
        
        widget = self.main_window.condition_widget
        if not widget:
            return {'success': False, 'error': '조건 위젯이 None'}
        
        checks = {
            'widget_visible': widget.isVisible(),
            'has_update_method': hasattr(widget, 'update_stats'),
            'has_log_method': hasattr(widget, 'add_condition_log'),
            'parent_exists': widget.parent() is not None
        }
        
        all_passed = all(checks.values())
        
        return {
            'success': all_passed,
            'details': checks,
            'error': None if all_passed else '조건 위젯 설정 문제'
        }
    
    def check_timers(self) -> Dict[str, Any]:
        """타이머 체크"""
        if not self.main_window:
            return {'success': False, 'error': '메인 윈도우 없음'}
        
        # 메인 윈도우의 타이머들 체크
        timers_info = {}
        
        # 일반적인 타이머 속성들 체크
        timer_attrs = ['update_timer', 'price_timer', 'position_timer', 'monitor_timer']
        
        for attr in timer_attrs:
            if hasattr(self.main_window, attr):
                timer = getattr(self.main_window, attr)
                if timer:
                    timers_info[attr] = {
                        'exists': True,
                        'active': timer.isActive(),
                        'interval': timer.interval()
                    }
                else:
                    timers_info[attr] = {'exists': False}
            else:
                timers_info[attr] = {'exists': False}
        
        active_timers = sum(1 for info in timers_info.values() 
                           if info.get('exists') and info.get('active'))
        
        return {
            'success': active_timers > 0,
            'details': timers_info,
            'active_count': active_timers,
            'error': None if active_timers > 0 else '활성 타이머 없음'
        }
    
    def check_data_sources(self) -> Dict[str, Any]:
        """데이터 소스 체크"""
        if not self.main_window:
            return {'success': False, 'error': '메인 윈도우 없음'}
        
        data_sources = {}
        
        # 가격 데이터 체크
        if hasattr(self.main_window, 'latest_prices'):
            prices = self.main_window.latest_prices
            data_sources['latest_prices'] = {
                'exists': True,
                'count': len(prices) if prices else 0,
                'symbols': list(prices.keys()) if prices else []
            }
        else:
            data_sources['latest_prices'] = {'exists': False}
        
        # API 클라이언트 체크
        if hasattr(self.main_window, 'okx_client'):
            client = self.main_window.okx_client
            data_sources['okx_client'] = {
                'exists': client is not None,
                'connected': getattr(client, 'connected', False) if client else False
            }
        else:
            data_sources['okx_client'] = {'exists': False}
        
        success = any(source.get('exists', False) for source in data_sources.values())
        
        return {
            'success': success,
            'details': data_sources,
            'error': None if success else '사용 가능한 데이터 소스 없음'
        }
    
    def check_gui_connections(self) -> Dict[str, Any]:
        """GUI 연결 상태 체크"""
        connections = {}
        
        if self.main_window:
            # 탭 연결 체크
            if hasattr(self.main_window, 'tab_widget'):
                tab_widget = self.main_window.tab_widget
                connections['tab_count'] = tab_widget.count()
                connections['current_tab'] = tab_widget.currentIndex()
            
            # 시그널-슬롯 연결 체크 (가능한 것들)
            connections['widget_hierarchy'] = self.check_widget_hierarchy()
        
        return {
            'success': True,  # GUI가 실행 중이면 기본적으로 성공
            'details': connections,
            'error': None
        }
    
    def check_widget_hierarchy(self) -> Dict[str, Any]:
        """위젯 계층 구조 체크"""
        if not self.main_window:
            return {}
        
        hierarchy = {}
        
        # 주요 위젯들의 부모-자식 관계 체크
        widgets_to_check = [
            'condition_widget', 'tab_widget', 'central_widget',
            'position_table', 'log_display'
        ]
        
        for widget_name in widgets_to_check:
            if hasattr(self.main_window, widget_name):
                widget = getattr(self.main_window, widget_name)
                if widget:
                    hierarchy[widget_name] = {
                        'has_parent': widget.parent() is not None,
                        'visible': widget.isVisible(),
                        'enabled': widget.isEnabled()
                    }
        
        return hierarchy
    
    def check_performance(self) -> Dict[str, Any]:
        """메모리 및 성능 체크"""
        import psutil
        import os
        
        try:
            process = psutil.Process(os.getpid())
            
            performance = {
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'thread_count': process.num_threads(),
                'open_files': len(process.open_files())
            }
            
            # 성능 임계값 체크
            memory_ok = performance['memory_mb'] < 500  # 500MB 미만
            cpu_ok = performance['cpu_percent'] < 50    # 50% 미만
            
            return {
                'success': memory_ok and cpu_ok,
                'details': performance,
                'error': None if memory_ok and cpu_ok else '성능 임계값 초과'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'성능 체크 실패: {e}'
            }
    
    # ========== 테스트 메서드들 ==========
    
    def run_single_condition_test(self):
        """단일 조건 테스트"""
        symbol = self.test_symbol_combo.currentText()
        
        self.add_debug_log(f"🧪 단일 조건 테스트 시작: {symbol}", DebugLevel.INFO)
        
        try:
            # 테스트 데이터 생성
            if symbol == "더미 데이터":
                test_data = self.generate_test_data()
            else:
                test_data = self.get_real_test_data(symbol)
            
            # 조건 체크 실행
            if self.main_window and hasattr(self.main_window, 'condition_monitor'):
                monitor = self.main_window.condition_monitor
                if monitor:
                    result = monitor.check_conditions(symbol, test_data, None)
                    
                    self.display_test_result(symbol, test_data, result)
                    self.add_debug_log("✅ 단일 조건 테스트 완료", DebugLevel.SUCCESS)
                else:
                    self.add_debug_log("❌ 조건 모니터 없음", DebugLevel.ERROR)
            else:
                self.add_debug_log("❌ 메인 윈도우 또는 조건 모니터 없음", DebugLevel.ERROR)
                
        except Exception as e:
            self.add_debug_log(f"🚨 단일 조건 테스트 실패: {e}", DebugLevel.ERROR)
    
    def generate_test_data(self) -> Dict[str, Any]:
        """테스트용 더미 데이터 생성"""
        base_price = 45000 + random.uniform(-5000, 5000)
        
        return {
            'close': base_price,
            'ema_trend_fast': base_price * (1 + random.uniform(-0.02, 0.02)),
            'ema_trend_slow': base_price * (1 + random.uniform(-0.03, 0.03)),
            'curr_entry_fast': base_price * (1 + random.uniform(-0.01, 0.01)),
            'curr_entry_slow': base_price * (1 + random.uniform(-0.015, 0.015)),
            'curr_exit_slow': base_price * (1 + random.uniform(-0.02, 0.02)),
            'volume': random.uniform(1000000, 10000000),
            'timestamp': time.time()
        }
    
    def get_real_test_data(self, symbol: str) -> Dict[str, Any]:
        """실제 데이터 기반 테스트 데이터"""
        if (self.main_window and 
            hasattr(self.main_window, 'latest_prices') and 
            symbol in self.main_window.latest_prices):
            
            real_price = self.main_window.latest_prices[symbol]
            return self.main_window._generate_enhanced_price_data(symbol, real_price, {})
        else:
            return self.generate_test_data()
    
    def display_test_result(self, symbol: str, test_data: Dict[str, Any], result: Dict[str, Any]):
        """테스트 결과 표시"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        output = f"[{timestamp}] 테스트 결과 - {symbol}\n"
        output += f"가격: ${test_data.get('close', 0):,.2f}\n"
        
        if result:
            market = result.get('market_conditions', {})
            trend = market.get('trend_direction', 'unknown')
            strength = market.get('trend_strength', 0)
            
            output += f"트렌드: {trend} ({strength:+.2f}%)\n"
            output += f"체크 시간: {result.get('timestamp', 'N/A')}\n"
        else:
            output += "결과 없음 - 조건 체크 실패\n"
        
        output += "-" * 40 + "\n"
        
        self.test_result_display.append(output)
        
        # 스크롤을 맨 아래로
        cursor = self.test_result_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.test_result_display.setTextCursor(cursor)
    
    def start_continuous_test(self):
        """연속 테스트 시작"""
        interval = self.test_interval_spin.value() * 1000  # ms로 변환
        self.continuous_test_timer.start(interval)
        self.add_debug_log(f"🔄 연속 테스트 시작 (간격: {interval/1000}초)", DebugLevel.INFO)
    
    def stop_continuous_test(self):
        """연속 테스트 중지"""
        self.continuous_test_timer.stop()
        self.add_debug_log("⏹️ 연속 테스트 중지", DebugLevel.INFO)
    
    # ========== 데이터 주입 메서드들 ==========
    
    def inject_dummy_data(self):
        """더미 데이터 주입"""
        self.add_debug_log("💉 더미 데이터 주입 중...", DebugLevel.INFO)
        
        try:
            test_data = self.generate_test_data()
            self.force_condition_check_with_data("BTC-USDT-SWAP", test_data)
            
            flow_msg = f"더미 데이터 주입 완료: 가격 ${test_data['close']:,.2f}"
            self.data_flow_display.append(f"[{datetime.now().strftime('%H:%M:%S')}] {flow_msg}")
            
        except Exception as e:
            self.add_debug_log(f"❌ 더미 데이터 주입 실패: {e}", DebugLevel.ERROR)
    
    def inject_realistic_data(self):
        """현실적인 데이터 시뮬레이션"""
        self.add_debug_log("💉 현실적 데이터 시뮬레이션 중...", DebugLevel.INFO)
        
        try:
            # 현실적인 시장 시나리오 생성
            scenarios = [
                self.create_bullish_scenario(),
                self.create_bearish_scenario(),
                self.create_sideways_scenario(),
                self.create_volatile_scenario()
            ]
            
            scenario = random.choice(scenarios)
            self.force_condition_check_with_data("BTC-USDT-SWAP", scenario['data'])
            
            flow_msg = f"시나리오 '{scenario['name']}' 데이터 주입"
            self.data_flow_display.append(f"[{datetime.now().strftime('%H:%M:%S')}] {flow_msg}")
            
        except Exception as e:
            self.add_debug_log(f"❌ 현실적 데이터 주입 실패: {e}", DebugLevel.ERROR)
    
    def inject_extreme_data(self):
        """극한 조건 테스트 데이터"""
        self.add_debug_log("💉 극한 조건 데이터 주입 중...", DebugLevel.WARNING)
        
        try:
            # 극한 시나리오들
            extreme_scenarios = [
                self.create_crash_scenario(),
                self.create_pump_scenario(),
                self.create_flash_crash_scenario(),
                self.create_consolidation_scenario()
            ]
            
            scenario = random.choice(extreme_scenarios)
            self.force_condition_check_with_data("BTC-USDT-SWAP", scenario['data'])
            
            flow_msg = f"극한 시나리오 '{scenario['name']}' 데이터 주입"
            self.data_flow_display.append(f"[{datetime.now().strftime('%H:%M:%S')}] {flow_msg}")
            
        except Exception as e:
            self.add_debug_log(f"❌ 극한 데이터 주입 실패: {e}", DebugLevel.ERROR)
    
    def create_bullish_scenario(self) -> Dict[str, Any]:
        """강세 시나리오"""
        base_price = 45000
        return {
            'name': '강세장',
            'data': {
                'close': base_price,
                'ema_trend_fast': base_price * 1.02,  # 150EMA > 200EMA
                'ema_trend_slow': base_price * 0.98,
                'curr_entry_fast': base_price * 1.01,  # 20EMA > 50EMA (골든크로스)
                'curr_entry_slow': base_price * 0.99,
                'curr_exit_slow': base_price * 0.97,
                'volume': 5000000,
                'timestamp': time.time()
            }
        }
    
    def create_bearish_scenario(self) -> Dict[str, Any]:
        """약세 시나리오"""
        base_price = 43000
        return {
            'name': '약세장',
            'data': {
                'close': base_price,
                'ema_trend_fast': base_price * 0.98,  # 150EMA < 200EMA
                'ema_trend_slow': base_price * 1.02,
                'curr_entry_fast': base_price * 0.99,  # 20EMA < 50EMA (데드크로스)
                'curr_entry_slow': base_price * 1.01,
                'curr_exit_slow': base_price * 1.03,
                'volume': 3000000,
                'timestamp': time.time()
            }
        }
    
    def create_sideways_scenario(self) -> Dict[str, Any]:
        """횡보 시나리오"""
        base_price = 44000
        return {
            'name': '횡보장',
            'data': {
                'close': base_price,
                'ema_trend_fast': base_price * 1.001,  # 거의 동일
                'ema_trend_slow': base_price * 0.999,
                'curr_entry_fast': base_price * 1.0005,
                'curr_entry_slow': base_price * 0.9995,
                'curr_exit_slow': base_price * 0.999,
                'volume': 2000000,
                'timestamp': time.time()
            }
        }
    
    def create_volatile_scenario(self) -> Dict[str, Any]:
        """고변동성 시나리오"""
        base_price = 46000
        return {
            'name': '고변동성',
            'data': {
                'close': base_price,
                'ema_trend_fast': base_price * (1 + random.uniform(-0.05, 0.05)),
                'ema_trend_slow': base_price * (1 + random.uniform(-0.06, 0.06)),
                'curr_entry_fast': base_price * (1 + random.uniform(-0.03, 0.03)),
                'curr_entry_slow': base_price * (1 + random.uniform(-0.04, 0.04)),
                'curr_exit_slow': base_price * (1 + random.uniform(-0.05, 0.05)),
                'volume': random.uniform(8000000, 15000000),
                'timestamp': time.time()
            }
        }
    
    def create_crash_scenario(self) -> Dict[str, Any]:
        """폭락 시나리오"""
        base_price = 35000  # 큰 하락
        return {
            'name': '폭락',
            'data': {
                'close': base_price,
                'ema_trend_fast': base_price * 0.85,
                'ema_trend_slow': base_price * 1.15,
                'curr_entry_fast': base_price * 0.90,
                'curr_entry_slow': base_price * 1.10,
                'curr_exit_slow': base_price * 1.20,
                'volume': 20000000,  # 높은 거래량
                'timestamp': time.time()
            }
        }
    
    def create_pump_scenario(self) -> Dict[str, Any]:
        """급등 시나리오"""
        base_price = 55000  # 큰 상승
        return {
            'name': '급등',
            'data': {
                'close': base_price,
                'ema_trend_fast': base_price * 1.15,
                'ema_trend_slow': base_price * 0.85,
                'curr_entry_fast': base_price * 1.10,
                'curr_entry_slow': base_price * 0.90,
                'curr_exit_slow': base_price * 0.80,
                'volume': 25000000,
                'timestamp': time.time()
            }
        }
    
    def create_flash_crash_scenario(self) -> Dict[str, Any]:
        """플래시 크래시 시나리오"""
        base_price = 42000
        return {
            'name': '플래시크래시',
            'data': {
                'close': base_price,
                'ema_trend_fast': base_price * 0.70,  # 극단적 차이
                'ema_trend_slow': base_price * 1.30,
                'curr_entry_fast': base_price * 0.75,
                'curr_entry_slow': base_price * 1.25,
                'curr_exit_slow': base_price * 1.35,
                'volume': 50000000,  # 극도로 높은 거래량
                'timestamp': time.time()
            }
        }
    
    def create_consolidation_scenario(self) -> Dict[str, Any]:
        """통합 구간 시나리오"""
        base_price = 44500
        return {
            'name': '통합구간',
            'data': {
                'close': base_price,
                'ema_trend_fast': base_price * 1.0001,  # 거의 완전히 동일
                'ema_trend_slow': base_price * 0.9999,
                'curr_entry_fast': base_price * 1.00005,
                'curr_entry_slow': base_price * 0.99995,
                'curr_exit_slow': base_price * 0.9999,
                'volume': 500000,  # 낮은 거래량
                'timestamp': time.time()
            }
        }
    
    def force_condition_check_with_data(self, symbol: str, data: Dict[str, Any]):
        """특정 데이터로 조건 체크 강제 실행"""
        if not self.main_window:
            return
        
        try:
            # 조건 모니터가 있으면 직접 체크
            if hasattr(self.main_window, 'condition_monitor') and self.main_window.condition_monitor:
                monitor = self.main_window.condition_monitor
                result = monitor.check_conditions(symbol, data, None)
                
                # 결과를 위젯에 전달
                if hasattr(self.main_window, 'condition_widget') and self.main_window.condition_widget:
                    widget = self.main_window.condition_widget
                    if hasattr(widget, 'handle_condition_update'):
                        widget.handle_condition_update(result)
                    if hasattr(widget, 'update_stats'):
                        widget.update_stats(monitor.counters)
            
        except Exception as e:
            self.add_debug_log(f"강제 조건 체크 실패: {e}", DebugLevel.ERROR)
    
    # ========== 기타 메서드들 ==========
    
    def force_start_monitoring(self):
        """모니터링 강제 시작"""
        self.add_debug_log("🚀 모니터링 강제 시작 시도", DebugLevel.INFO)
        
        try:
            if self.main_window:
                # 조건 모니터 활성화
                if hasattr(self.main_window, 'condition_monitor'):
                    monitor = self.main_window.condition_monitor
                    if monitor:
                        monitor.monitoring_active = True
                        self.add_debug_log("✅ 조건 모니터 활성화됨", DebugLevel.SUCCESS)
                
                # 강제 활성화 메서드 호출
                if hasattr(self.main_window, 'force_enable_auto_check'):
                    self.main_window.force_enable_auto_check()
                    self.add_debug_log("✅ 자동 체크 강제 활성화됨", DebugLevel.SUCCESS)
                
                # 수동 체크 실행
                if hasattr(self.main_window, 'manual_condition_check'):
                    self.main_window.manual_condition_check()
                    self.add_debug_log("✅ 수동 체크 실행됨", DebugLevel.SUCCESS)
                
            self.add_debug_log("🎯 모니터링 강제 시작 완료", DebugLevel.SUCCESS)
            
        except Exception as e:
            self.add_debug_log(f"❌ 모니터링 강제 시작 실패: {e}", DebugLevel.ERROR)
    
    def test_data_flow(self):
        """데이터 흐름 테스트"""
        self.add_debug_log("📊 데이터 흐름 테스트 시작", DebugLevel.INFO)
        
        try:
            # 1. 더미 데이터 생성
            test_data = self.generate_test_data()
            self.data_flow_display.append(f"1. 데이터 생성: ${test_data['close']:,.2f}")
            
            # 2. 조건 모니터에 데이터 전달
            if (self.main_window and 
                hasattr(self.main_window, 'condition_monitor') and 
                self.main_window.condition_monitor):
                
                monitor = self.main_window.condition_monitor
                result = monitor.check_conditions("BTC-USDT-SWAP", test_data, None)
                self.data_flow_display.append("2. 조건 모니터 처리 완료")
                
                # 3. 위젯 업데이트
                if (hasattr(self.main_window, 'condition_widget') and 
                    self.main_window.condition_widget):
                    
                    widget = self.main_window.condition_widget
                    if hasattr(widget, 'update_stats'):
                        widget.update_stats(monitor.counters)
                        self.data_flow_display.append("3. 위젯 업데이트 완료")
                    
                self.add_debug_log("✅ 데이터 흐름 테스트 성공", DebugLevel.SUCCESS)
            else:
                self.add_debug_log("❌ 조건 모니터 없음", DebugLevel.ERROR)
                
        except Exception as e:
            self.add_debug_log(f"❌ 데이터 흐름 테스트 실패: {e}", DebugLevel.ERROR)
    
    def test_widget_connections(self):
        """위젯 연결 테스트"""
        self.add_debug_log("🔗 위젯 연결 테스트 시작", DebugLevel.INFO)
        
        tests = [
            ("메인 윈도우 → 조건 모니터", self.test_main_to_monitor_connection),
            ("조건 모니터 → 조건 위젯", self.test_monitor_to_widget_connection),
            ("조건 위젯 → GUI 업데이트", self.test_widget_to_gui_connection),
            ("타이머 → 자동 업데이트", self.test_timer_connections)
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                status = "✅ 성공" if result else "❌ 실패"
                self.add_debug_log(f"{status} {test_name}", 
                                 DebugLevel.SUCCESS if result else DebugLevel.ERROR)
            except Exception as e:
                self.add_debug_log(f"🚨 {test_name} 예외: {e}", DebugLevel.ERROR)
    
    def test_main_to_monitor_connection(self) -> bool:
        """메인 윈도우 → 조건 모니터 연결 테스트"""
        if not self.main_window:
            return False
        
        return (hasattr(self.main_window, 'condition_monitor') and 
                self.main_window.condition_monitor is not None)
    
    def test_monitor_to_widget_connection(self) -> bool:
        """조건 모니터 → 조건 위젯 연결 테스트"""
        if not self.main_window:
            return False
        
        has_monitor = (hasattr(self.main_window, 'condition_monitor') and 
                      self.main_window.condition_monitor is not None)
        has_widget = (hasattr(self.main_window, 'condition_widget') and 
                     self.main_window.condition_widget is not None)
        
        return has_monitor and has_widget
    
    def test_widget_to_gui_connection(self) -> bool:
        """조건 위젯 → GUI 업데이트 연결 테스트"""
        if not self.main_window or not hasattr(self.main_window, 'condition_widget'):
            return False
        
        widget = self.main_window.condition_widget
        if not widget:
            return False
        
        # 위젯이 업데이트 메서드를 가지고 있는지 확인
        return (hasattr(widget, 'update_stats') and 
                hasattr(widget, 'add_condition_log'))
    
    def test_timer_connections(self) -> bool:
        """타이머 연결 테스트"""
        if not self.main_window:
            return False
        
        # 활성 타이머가 하나라도 있는지 확인
        timer_attrs = ['update_timer', 'price_timer', 'position_timer', 'monitor_timer']
        
        for attr in timer_attrs:
            if hasattr(self.main_window, attr):
                timer = getattr(self.main_window, attr)
                if timer and timer.isActive():
                    return True
        
        return False
    
    def toggle_auto_debug(self, enabled: bool):
        """자동 디버깅 토글"""
        self.auto_debug_enabled = enabled
        
        if enabled:
            interval = self.debug_interval * 1000  # ms로 변환
            self.auto_debug_timer.start(interval)
            self.add_debug_log(f"🔄 자동 디버깅 시작 (간격: {self.debug_interval}초)", DebugLevel.INFO)
        else:
            self.auto_debug_timer.stop()
            self.add_debug_log("⏹️ 자동 디버깅 중지", DebugLevel.INFO)
    
    def run_auto_debug_check(self):
        """자동 디버깅 체크"""
        try:
            # 간단한 시스템 상태 체크
            if self.main_window:
                monitor_ok = (hasattr(self.main_window, 'condition_monitor') and 
                             self.main_window.condition_monitor is not None)
                widget_ok = (hasattr(self.main_window, 'condition_widget') and 
                            self.main_window.condition_widget is not None)
                
                if not monitor_ok:
                    self.add_debug_log("⚠️ 조건 모니터 비정상", DebugLevel.WARNING)
                if not widget_ok:
                    self.add_debug_log("⚠️ 조건 위젯 비정상", DebugLevel.WARNING)
                    
                # 카운터 체크
                if monitor_ok:
                    monitor = self.main_window.condition_monitor
                    if hasattr(monitor, 'counters'):
                        total_checks = monitor.counters.get('total_checks', 0)
                        if total_checks == 0:
                            self.add_debug_log("⚠️ 체크 카운터가 0 - 모니터링 비활성", DebugLevel.WARNING)
        
        except Exception as e:
            self.add_debug_log(f"🚨 자동 디버깅 오류: {e}", DebugLevel.ERROR)
    
    def update_system_status(self):
        """시스템 상태 업데이트"""
        try:
            if not self.main_window:
                self.main_window_status.setText("❌ 없음")
                return
            
            self.main_window_status.setText("✅ 정상")
            
            # 조건 모니터 상태
            if hasattr(self.main_window, 'condition_monitor') and self.main_window.condition_monitor:
                monitor = self.main_window.condition_monitor
                active = getattr(monitor, 'monitoring_active', False)
                status_text = f"✅ 정상 ({'활성' if active else '비활성'})"
                self.condition_monitor_status.setText(status_text)
                
                # 카운터 업데이트
                if hasattr(monitor, 'counters'):
                    counters = monitor.counters
                    self.counter_labels["총 체크 횟수"].setText(str(counters.get('total_checks', 0)))
                    self.counter_labels["트렌드 상승"].setText(str(counters.get('trend_uptrend', 0)))
                    self.counter_labels["트렌드 하락"].setText(str(counters.get('trend_downtrend', 0)))
                    self.counter_labels["롱 신호"].setText(str(counters.get('long_signals', 0)))
                    self.counter_labels["숏 신호"].setText(str(counters.get('short_signals', 0)))
                    self.counter_labels["실제 모드"].setText(str(counters.get('real_mode_strategies', 0)))
                    self.counter_labels["가상 모드"].setText(str(counters.get('virtual_mode_strategies', 0)))
            else:
                self.condition_monitor_status.setText("❌ 없음")
            
            # 조건 위젯 상태
            if hasattr(self.main_window, 'condition_widget') and self.main_window.condition_widget:
                widget = self.main_window.condition_widget
                visible = widget.isVisible()
                status_text = f"✅ 정상 ({'표시중' if visible else '숨김'})"
                self.condition_widget_status.setText(status_text)
            else:
                self.condition_widget_status.setText("❌ 없음")
            
            # 모니터링 탭 상태 (탭 위젯 확인)
            if hasattr(self.main_window, 'tab_widget'):
                tab_count = self.main_window.tab_widget.count()
                self.monitoring_tab_status.setText(f"✅ 정상 ({tab_count}개 탭)")
            else:
                self.monitoring_tab_status.setText("❌ 없음")
            
            # 타이머 상태
            active_timers = 0
            timer_attrs = ['update_timer', 'price_timer', 'position_timer', 'monitor_timer']
            
            for attr in timer_attrs:
                if hasattr(self.main_window, attr):
                    timer = getattr(self.main_window, attr)
                    if timer and timer.isActive():
                        active_timers += 1
            
            if active_timers > 0:
                self.timer_status.setText(f"✅ 정상 ({active_timers}개 활성)")
            else:
                self.timer_status.setText("⚠️ 활성 타이머 없음")
            
            # 데이터 소스 상태
            if hasattr(self.main_window, 'latest_prices') and self.main_window.latest_prices:
                price_count = len(self.main_window.latest_prices)
                self.data_source_status.setText(f"✅ 정상 ({price_count}개 심볼)")
            else:
                self.data_source_status.setText("⚠️ 가격 데이터 없음")
                
        except Exception as e:
            self.add_debug_log(f"상태 업데이트 오류: {e}", DebugLevel.ERROR)
    
    def add_debug_log(self, message: str, level: DebugLevel):
        """디버그 로그 추가"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # 레벨별 아이콘
        icons = {
            DebugLevel.INFO: 'ℹ️',
            DebugLevel.WARNING: '⚠️',
            DebugLevel.ERROR: '❌',
            DebugLevel.SUCCESS: '✅',
            DebugLevel.DEBUG: '🔍'
        }
        
        icon = icons.get(level, 'ℹ️')
        formatted_message = f"[{timestamp}] {icon} {level.value}: {message}"
        
        # 간단하게 텍스트만 추가
        self.debug_log_display.append(formatted_message)
        
        # 스크롤 맨 아래로
        scrollbar = self.debug_log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # 로그 히스토리에 추가
        self.debug_logs.append({
            'timestamp': datetime.now(),
            'level': level,
            'message': message
        })
        
        # 로그 개수 제한 (최근 1000개만)
        if len(self.debug_logs) > 1000:
            self.debug_logs = self.debug_logs[-1000:]
    
    def clear_debug_logs(self):
        """디버그 로그 지우기"""
        self.debug_log_display.clear()
        self.debug_logs.clear()
        self.test_result_display.clear()
        self.data_flow_display.clear()
        self.add_debug_log("🧹 디버그 로그 초기화됨", DebugLevel.INFO)
    
    def export_debug_logs(self):
        """디버그 로그 내보내기"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"debug_logs_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"조건 모니터링 디버그 로그\n")
                f.write(f"생성 시간: {datetime.now()}\n")
                f.write("=" * 50 + "\n\n")
                
                for log in self.debug_logs:
                    f.write(f"[{log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}] "
                           f"{log['level'].value}: {log['message']}\n")
            
            self.add_debug_log(f"📄 로그 내보내기 완료: {filename}", DebugLevel.SUCCESS)
            
        except Exception as e:
            self.add_debug_log(f"❌ 로그 내보내기 실패: {e}", DebugLevel.ERROR)


# ========== 메인 윈도우에 통합하는 코드 ==========

def add_debugger_to_main_window(main_window):
    """메인 윈도우에 디버거 탭 추가"""
    try:
        debugger = ConditionMonitoringDebugger(main_window)
        
        if hasattr(main_window, 'tab_widget'):
            main_window.tab_widget.addTab(debugger, "🔧 디버깅")
            print("✅ 조건 모니터링 디버거 추가됨")
        else:
            print("❌ 탭 위젯을 찾을 수 없음")
            
    except Exception as e:
        print(f"❌ 디버거 추가 실패: {e}")


# ========== 독립 실행 코드 ==========

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    
    # 독립 실행용 메인 윈도우
    main_window = QMainWindow()
    main_window.setWindowTitle("조건 모니터링 디버거")
    main_window.setGeometry(100, 100, 1200, 800)
    
    debugger = ConditionMonitoringDebugger()
    main_window.setCentralWidget(debugger)
    
    main_window.show()
    sys.exit(app.exec_())