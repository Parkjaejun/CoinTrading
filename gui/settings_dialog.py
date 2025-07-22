# gui/settings_dialog.py
"""
고급 설정 대화상자
API, 전략, 알림 등의 상세 설정을 위한 별도 창
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QPushButton, QTextEdit, QLabel, QFileDialog,
    QMessageBox, QProgressBar, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QSlider, QColorDialog, QFontDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QPalette

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

from gui.config_validator import config_manager, config_validator

class APITestThread(QThread):
    """API 연결 테스트 스레드"""
    
    test_completed = pyqtSignal(bool, str)
    
    def __init__(self, api_key: str, api_secret: str, passphrase: str):
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
    
    def run(self):
        try:
            # 임시로 API 정보 설정하여 테스트
            from okx.account_manager import AccountManager
            
            # 테스트용 AccountManager 생성
            test_account = AccountManager()
            test_account.api_key = self.api_key
            test_account.secret_key = self.api_secret
            test_account.passphrase = self.passphrase
            
            # 간단한 API 호출
            balances = test_account.get_account_balance()
            
            if balances:
                self.test_completed.emit(True, "API 연결 성공!")
            else:
                self.test_completed.emit(False, "API 응답 없음")
                
        except Exception as e:
            self.test_completed.emit(False, f"연결 실패: {str(e)}")

class NotificationTestDialog(QDialog):
    """알림 테스트 대화상자"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("알림 테스트")
        self.setFixedSize(400, 300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 테스트 메시지 입력
        message_group = QGroupBox("테스트 메시지")
        message_layout = QFormLayout()
        
        self.title_edit = QLineEdit("GUI 테스트")
        self.message_edit = QTextEdit("알림 시스템 테스트 메시지입니다.")
        self.message_edit.setMaximumHeight(100)
        
        message_layout.addRow("제목:", self.title_edit)
        message_layout.addRow("내용:", self.message_edit)
        message_group.setLayout(message_layout)
        layout.addWidget(message_group)
        
        # 알림 채널 선택
        channel_group = QGroupBox("테스트할 채널")
        channel_layout = QVBoxLayout()
        
        self.slack_check = QCheckBox("슬랙")
        self.telegram_check = QCheckBox("텔레그램")
        self.email_check = QCheckBox("이메일")
        
        channel_layout.addWidget(self.slack_check)
        channel_layout.addWidget(self.telegram_check)
        channel_layout.addWidget(self.email_check)
        channel_group.setLayout(channel_layout)
        layout.addWidget(channel_group)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("테스트 전송")
        self.test_btn.clicked.connect(self.send_test_notification)
        
        self.close_btn = QPushButton("닫기")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.test_btn)
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def send_test_notification(self):
        """테스트 알림 전송"""
        title = self.title_edit.text()
        message = self.message_edit.toPlainText()
        
        channels = []
        if self.slack_check.isChecked():
            channels.append("slack")
        if self.telegram_check.isChecked():
            channels.append("telegram")
        if self.email_check.isChecked():
            channels.append("email")
        
        if not channels:
            QMessageBox.warning(self, "알림 테스트", "테스트할 채널을 선택해주세요.")
            return
        
        try:
            # 실제 알림 전송 (utils.notifications 사용)
            from utils.notifications import send_system_alert
            send_system_alert(title, message, "info")
            
            QMessageBox.information(self, "알림 테스트", 
                                  f"테스트 알림을 전송했습니다.\n채널: {', '.join(channels)}")
        except Exception as e:
            QMessageBox.critical(self, "알림 테스트", f"알림 전송 실패: {str(e)}")

class AdvancedSettingsDialog(QDialog):
    """고급 설정 대화상자"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("고급 설정")
        self.setFixedSize(800, 600)
        self.current_config = config_manager.load_config()
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        
        # 각 탭 생성
        self.setup_api_tab()
        self.setup_trading_tab()
        self.setup_strategy_tab()
        self.setup_notification_tab()
        self.setup_gui_tab()
        self.setup_backup_tab()
        
        layout.addWidget(self.tab_widget)
        
        # 하단 버튼
        button_layout = QHBoxLayout()
        
        self.test_api_btn = QPushButton("API 테스트")
        self.test_api_btn.clicked.connect(self.test_api_connection)
        
        self.test_notification_btn = QPushButton("알림 테스트")
        self.test_notification_btn.clicked.connect(self.test_notifications)
        
        self.reset_btn = QPushButton("초기화")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        
        self.save_btn = QPushButton("저장")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.test_api_btn)
        button_layout.addWidget(self.test_notification_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def setup_api_tab(self):
        """API 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # API 인증 정보
        auth_group = QGroupBox("API 인증 정보")
        auth_layout = QFormLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        
        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setEchoMode(QLineEdit.Password)
        
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.Password)
        
        self.show_api_btn = QPushButton("표시")
        self.show_api_btn.setCheckable(True)
        self.show_api_btn.clicked.connect(self.toggle_api_visibility)
        
        auth_layout.addRow("API Key:", self.api_key_edit)
        auth_layout.addRow("Secret:", self.api_secret_edit)
        auth_layout.addRow("Passphrase:", self.passphrase_edit)
        auth_layout.addRow("비밀번호 표시:", self.show_api_btn)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        # 거래 모드
        mode_group = QGroupBox("거래 모드")
        mode_layout = QVBoxLayout()
        
        self.paper_trading_check = QCheckBox("Paper Trading 모드 (실제 주문 없음)")
        self.paper_trading_check.setChecked(True)
        
        mode_layout.addWidget(self.paper_trading_check)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 연결 설정
        connection_group = QGroupBox("연결 설정")
        connection_layout = QFormLayout()
        
        self.request_timeout_spin = QSpinBox()
        self.request_timeout_spin.setRange(5, 60)
        self.request_timeout_spin.setValue(10)
        self.request_timeout_spin.setSuffix("초")
        
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(1, 10)
        self.max_retries_spin.setValue(5)
        
        connection_layout.addRow("요청 타임아웃:", self.request_timeout_spin)
        connection_layout.addRow("최대 재시도:", self.max_retries_spin)
        
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "🔑 API 설정")
    
    def setup_trading_tab(self):
        """거래 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 기본 거래 설정
        basic_group = QGroupBox("기본 거래 설정")
        basic_layout = QFormLayout()
        
        self.initial_capital_spin = QDoubleSpinBox()
        self.initial_capital_spin.setRange(100, 1000000)
        self.initial_capital_spin.setValue(10000)
        self.initial_capital_spin.setPrefix("$")
        
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 20)
        self.max_positions_spin.setValue(5)
        
        self.symbol_edit = QLineEdit()
        self.symbol_edit.setText("BTC-USDT-SWAP")
        self.symbol_edit.setPlaceholderText("심볼을 쉼표로 구분하여 입력")
        
        basic_layout.addRow("초기 자본:", self.initial_capital_spin)
        basic_layout.addRow("최대 포지션 수:", self.max_positions_spin)
        basic_layout.addRow("거래 심볼:", self.symbol_edit)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 위험 관리
        risk_group = QGroupBox("위험 관리")
        risk_layout = QFormLayout()
        
        self.max_capital_per_trade_spin = QDoubleSpinBox()
        self.max_capital_per_trade_spin.setRange(0.01, 1.0)
        self.max_capital_per_trade_spin.setSingleStep(0.01)
        self.max_capital_per_trade_spin.setValue(0.20)
        self.max_capital_per_trade_spin.setSuffix("%")
        
        self.daily_loss_limit_spin = QDoubleSpinBox()
        self.daily_loss_limit_spin.setRange(0.01, 0.50)
        self.daily_loss_limit_spin.setSingleStep(0.01)
        self.daily_loss_limit_spin.setValue(0.10)
        self.daily_loss_limit_spin.setSuffix("%")
        
        risk_layout.addRow("거래당 최대 자본:", self.max_capital_per_trade_spin)
        risk_layout.addRow("일일 손실 한계:", self.daily_loss_limit_spin)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "💰 거래 설정")
    
    def setup_strategy_tab(self):
        """전략 설정 탭"""
        tab = QWidget()
        layout = QHBoxLayout()
        
        # 롱 전략
        long_group = QGroupBox("롱 전략")
        long_layout = QFormLayout()
        
        self.long_leverage_spin = QSpinBox()
        self.long_leverage_spin.setRange(1, 100)
        self.long_leverage_spin.setValue(10)
        
        self.long_trailing_spin = QDoubleSpinBox()
        self.long_trailing_spin.setRange(0.01, 0.50)
        self.long_trailing_spin.setSingleStep(0.01)
        self.long_trailing_spin.setValue(0.10)
        self.long_trailing_spin.setSuffix("%")
        
        self.long_stop_loss_spin = QDoubleSpinBox()
        self.long_stop_loss_spin.setRange(0.05, 0.50)
        self.long_stop_loss_spin.setSingleStep(0.01)
        self.long_stop_loss_spin.setValue(0.20)
        self.long_stop_loss_spin.setSuffix("%")
        
        self.long_reentry_spin = QDoubleSpinBox()
        self.long_reentry_spin.setRange(0.10, 1.00)
        self.long_reentry_spin.setSingleStep(0.01)
        self.long_reentry_spin.setValue(0.30)
        self.long_reentry_spin.setSuffix("%")
        
        long_layout.addRow("레버리지:", self.long_leverage_spin)
        long_layout.addRow("트레일링 스탑:", self.long_trailing_spin)
        long_layout.addRow("손절선:", self.long_stop_loss_spin)
        long_layout.addRow("재진입 기준:", self.long_reentry_spin)
        
        long_group.setLayout(long_layout)
        layout.addWidget(long_group)
        
        # 숏 전략
        short_group = QGroupBox("숏 전략")
        short_layout = QFormLayout()
        
        self.short_leverage_spin = QSpinBox()
        self.short_leverage_spin.setRange(1, 100)
        self.short_leverage_spin.setValue(3)
        
        self.short_trailing_spin = QDoubleSpinBox()
        self.short_trailing_spin.setRange(0.01, 0.50)
        self.short_trailing_spin.setSingleStep(0.01)
        self.short_trailing_spin.setValue(0.02)
        self.short_trailing_spin.setSuffix("%")
        
        self.short_stop_loss_spin = QDoubleSpinBox()
        self.short_stop_loss_spin.setRange(0.05, 0.50)
        self.short_stop_loss_spin.setSingleStep(0.01)
        self.short_stop_loss_spin.setValue(0.10)
        self.short_stop_loss_spin.setSuffix("%")
        
        self.short_reentry_spin = QDoubleSpinBox()
        self.short_reentry_spin.setRange(0.10, 1.00)
        self.short_reentry_spin.setSingleStep(0.01)
        self.short_reentry_spin.setValue(0.20)
        self.short_reentry_spin.setSuffix("%")
        
        short_layout.addRow("레버리지:", self.short_leverage_spin)
        short_layout.addRow("트레일링 스탑:", self.short_trailing_spin)
        short_layout.addRow("손절선:", self.short_stop_loss_spin)
        short_layout.addRow("재진입 기준:", self.short_reentry_spin)
        
        short_group.setLayout(short_layout)
        layout.addWidget(short_group)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "📈 전략 설정")
    
    def setup_notification_tab(self):
        """알림 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 슬랙 설정
        slack_group = QGroupBox("슬랙 알림")
        slack_layout = QFormLayout()
        
        self.slack_enabled_check = QCheckBox("슬랙 알림 활성화")
        self.slack_webhook_edit = QLineEdit()
        self.slack_webhook_edit.setPlaceholderText("https://hooks.slack.com/services/...")
        self.slack_channel_edit = QLineEdit()
        self.slack_channel_edit.setText("#trading-alerts")
        
        slack_layout.addRow("", self.slack_enabled_check)
        slack_layout.addRow("웹훅 URL:", self.slack_webhook_edit)
        slack_layout.addRow("채널:", self.slack_channel_edit)
        
        slack_group.setLayout(slack_layout)
        layout.addWidget(slack_group)
        
        # 텔레그램 설정
        telegram_group = QGroupBox("텔레그램 알림")
        telegram_layout = QFormLayout()
        
        self.telegram_enabled_check = QCheckBox("텔레그램 알림 활성화")
        self.telegram_token_edit = QLineEdit()
        self.telegram_token_edit.setPlaceholderText("봇 토큰")
        self.telegram_chat_edit = QLineEdit()
        self.telegram_chat_edit.setPlaceholderText("채팅 ID")
        
        telegram_layout.addRow("", self.telegram_enabled_check)
        telegram_layout.addRow("봇 토큰:", self.telegram_token_edit)
        telegram_layout.addRow("채팅 ID:", self.telegram_chat_edit)
        
        telegram_group.setLayout(telegram_layout)
        layout.addWidget(telegram_group)
        
        # 이메일 설정
        email_group = QGroupBox("이메일 알림")
        email_layout = QFormLayout()
        
        self.email_enabled_check = QCheckBox("이메일 알림 활성화")
        self.email_sender_edit = QLineEdit()
        self.email_password_edit = QLineEdit()
        self.email_password_edit.setEchoMode(QLineEdit.Password)
        self.email_recipient_edit = QLineEdit()
        
        email_layout.addRow("", self.email_enabled_check)
        email_layout.addRow("발신자 이메일:", self.email_sender_edit)
        email_layout.addRow("앱 비밀번호:", self.email_password_edit)
        email_layout.addRow("수신자 이메일:", self.email_recipient_edit)
        
        email_group.setLayout(email_layout)
        layout.addWidget(email_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "🔔 알림 설정")
    
    def setup_gui_tab(self):
        """GUI 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 테마 설정
        theme_group = QGroupBox("테마 설정")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "Auto"])
        
        self.font_btn = QPushButton("폰트 선택")
        self.font_btn.clicked.connect(self.select_font)
        
        theme_layout.addRow("테마:", self.theme_combo)
        theme_layout.addRow("폰트:", self.font_btn)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # 업데이트 간격
        update_group = QGroupBox("업데이트 간격")
        update_layout = QFormLayout()
        
        self.chart_update_spin = QSpinBox()
        self.chart_update_spin.setRange(100, 10000)
        self.chart_update_spin.setValue(1000)
        self.chart_update_spin.setSuffix("ms")
        
        self.position_update_spin = QSpinBox()
        self.position_update_spin.setRange(1000, 60000)
        self.position_update_spin.setValue(5000)
        self.position_update_spin.setSuffix("ms")
        
        update_layout.addRow("차트 업데이트:", self.chart_update_spin)
        update_layout.addRow("포지션 업데이트:", self.position_update_spin)
        
        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
        
        # 기타 설정
        misc_group = QGroupBox("기타 설정")
        misc_layout = QVBoxLayout()
        
        self.auto_scroll_check = QCheckBox("로그 자동 스크롤")
        self.auto_scroll_check.setChecked(True)
        
        self.minimize_to_tray_check = QCheckBox("최소화 시 시스템 트레이로")
        self.minimize_to_tray_check.setChecked(True)
        
        self.start_minimized_check = QCheckBox("시작 시 최소화")
        
        misc_layout.addWidget(self.auto_scroll_check)
        misc_layout.addWidget(self.minimize_to_tray_check)
        misc_layout.addWidget(self.start_minimized_check)
        
        misc_group.setLayout(misc_layout)
        layout.addWidget(misc_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "🎨 GUI 설정")
    
    def setup_backup_tab(self):
        """백업 관리 탭"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 자동 백업 설정
        auto_backup_group = QGroupBox("자동 백업")
        auto_backup_layout = QFormLayout()
        
        self.auto_backup_check = QCheckBox("자동 백업 활성화")
        self.auto_backup_check.setChecked(True)
        
        self.backup_interval_spin = QSpinBox()
        self.backup_interval_spin.setRange(1, 24)
        self.backup_interval_spin.setValue(6)
        self.backup_interval_spin.setSuffix("시간")
        
        self.max_backups_spin = QSpinBox()
        self.max_backups_spin.setRange(5, 100)
        self.max_backups_spin.setValue(30)
        
        auto_backup_layout.addRow("", self.auto_backup_check)
        auto_backup_layout.addRow("백업 간격:", self.backup_interval_spin)
        auto_backup_layout.addRow("최대 백업 수:", self.max_backups_spin)
        
        auto_backup_group.setLayout(auto_backup_layout)
        layout.addWidget(auto_backup_group)
        
        # 백업 관리
        backup_group = QGroupBox("백업 관리")
        backup_layout = QVBoxLayout()
        
        # 백업 리스트
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(3)
        self.backup_table.setHorizontalHeaderLabels(["날짜", "시간", "크기"])
        self.backup_table.horizontalHeader().setStretchLastSection(True)
        
        backup_layout.addWidget(self.backup_table)
        
        # 백업 버튼들
        backup_btn_layout = QHBoxLayout()
        
        self.create_backup_btn = QPushButton("백업 생성")
        self.create_backup_btn.clicked.connect(self.create_backup)
        
        self.restore_backup_btn = QPushButton("복원")
        self.restore_backup_btn.clicked.connect(self.restore_backup)
        
        self.delete_backup_btn = QPushButton("삭제")
        self.delete_backup_btn.clicked.connect(self.delete_backup)
        
        self.export_btn = QPushButton("내보내기")
        self.export_btn.clicked.connect(self.export_settings)
        
        self.import_btn = QPushButton("가져오기")
        self.import_btn.clicked.connect(self.import_settings)
        
        backup_btn_layout.addWidget(self.create_backup_btn)
        backup_btn_layout.addWidget(self.restore_backup_btn)
        backup_btn_layout.addWidget(self.delete_backup_btn)
        backup_btn_layout.addStretch()
        backup_btn_layout.addWidget(self.export_btn)
        backup_btn_layout.addWidget(self.import_btn)
        
        backup_layout.addLayout(backup_btn_layout)
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "💾 백업 관리")
        
        # 백업 목록 로드
        self.load_backup_list()
    
    def toggle_api_visibility(self):
        """API 키 표시/숨김 토글"""
        if self.show_api_btn.isChecked():
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
            self.api_secret_edit.setEchoMode(QLineEdit.Normal)
            self.passphrase_edit.setEchoMode(QLineEdit.Normal)
            self.show_api_btn.setText("숨김")
        else:
            self.api_key_edit.setEchoMode(QLineEdit.Password)
            self.api_secret_edit.setEchoMode(QLineEdit.Password)
            self.passphrase_edit.setEchoMode(QLineEdit.Password)
            self.show_api_btn.setText("표시")
    
    def select_font(self):
        """폰트 선택"""
        font, ok = QFontDialog.getFont()
        if ok:
            self.font_btn.setText(f"{font.family()} {font.pointSize()}pt")
            self.selected_font = font
    
    def load_current_settings(self):
        """현재 설정 로드"""
        config = self.current_config
        
        # API 설정
        api_config = config.get('api', {})
        self.api_key_edit.setText(api_config.get('api_key', ''))
        self.api_secret_edit.setText(api_config.get('api_secret', ''))
        self.passphrase_edit.setText(api_config.get('passphrase', ''))
        self.paper_trading_check.setChecked(api_config.get('paper_trading', True))
        
        # 거래 설정
        trading_config = config.get('trading', {})
        self.initial_capital_spin.setValue(trading_config.get('initial_capital', 10000))
        self.max_positions_spin.setValue(trading_config.get('max_positions', 5))
        
        symbols = trading_config.get('symbols', ['BTC-USDT-SWAP'])
        self.symbol_edit.setText(', '.join(symbols))
        
        # 전략 설정
        long_config = config.get('long_strategy', {})
        self.long_leverage_spin.setValue(long_config.get('leverage', 10))
        self.long_trailing_spin.setValue(long_config.get('trailing_stop', 0.10))
        self.long_stop_loss_spin.setValue(long_config.get('stop_loss', 0.20))
        self.long_reentry_spin.setValue(long_config.get('reentry_gain', 0.30))
        
        short_config = config.get('short_strategy', {})
        self.short_leverage_spin.setValue(short_config.get('leverage', 3))
        self.short_trailing_spin.setValue(short_config.get('trailing_stop', 0.02))
        self.short_stop_loss_spin.setValue(short_config.get('stop_loss', 0.10))
        self.short_reentry_spin.setValue(short_config.get('reentry_gain', 0.20))
        
        # 알림 설정
        notifications = config.get('notifications', {})
        
        slack_config = notifications.get('slack', {})
        self.slack_enabled_check.setChecked(slack_config.get('enabled', False))
        self.slack_webhook_edit.setText(slack_config.get('webhook_url', ''))
        self.slack_channel_edit.setText(slack_config.get('channel', '#trading-alerts'))
        
        telegram_config = notifications.get('telegram', {})
        self.telegram_enabled_check.setChecked(telegram_config.get('enabled', False))
        self.telegram_token_edit.setText(telegram_config.get('bot_token', ''))
        self.telegram_chat_edit.setText(telegram_config.get('chat_id', ''))
        
        email_config = notifications.get('email', {})
        self.email_enabled_check.setChecked(email_config.get('enabled', False))
        self.email_sender_edit.setText(email_config.get('sender_email', ''))
        self.email_password_edit.setText(email_config.get('sender_password', ''))
        self.email_recipient_edit.setText(email_config.get('recipient_email', ''))
        
        # GUI 설정
        gui_config = config.get('gui', {})
        theme = gui_config.get('theme', 'dark')
        theme_index = {'dark': 0, 'light': 1, 'auto': 2}.get(theme.lower(), 0)
        self.theme_combo.setCurrentIndex(theme_index)
        
        self.chart_update_spin.setValue(gui_config.get('chart_update_interval', 1000))
        self.position_update_spin.setValue(gui_config.get('position_update_interval', 5000))
        self.auto_scroll_check.setChecked(gui_config.get('auto_scroll_logs', True))
        self.minimize_to_tray_check.setChecked(gui_config.get('minimize_to_tray', True))
        self.start_minimized_check.setChecked(gui_config.get('start_minimized', False))
    
    def collect_settings(self) -> Dict[str, Any]:
        """현재 GUI 설정 수집"""
        return {
            'api': {
                'api_key': self.api_key_edit.text(),
                'api_secret': self.api_secret_edit.text(),
                'passphrase': self.passphrase_edit.text(),
                'paper_trading': self.paper_trading_check.isChecked(),
                'request_timeout': self.request_timeout_spin.value(),
                'max_retries': self.max_retries_spin.value()
            },
            'trading': {
                'initial_capital': self.initial_capital_spin.value(),
                'max_positions': self.max_positions_spin.value(),
                'symbols': [s.strip() for s in self.symbol_edit.text().split(',')],
                'max_capital_per_trade': self.max_capital_per_trade_spin.value(),
                'daily_loss_limit': self.daily_loss_limit_spin.value()
            },
            'long_strategy': {
                'leverage': self.long_leverage_spin.value(),
                'trailing_stop': self.long_trailing_spin.value(),
                'stop_loss': self.long_stop_loss_spin.value(),
                'reentry_gain': self.long_reentry_spin.value()
            },
            'short_strategy': {
                'leverage': self.short_leverage_spin.value(),
                'trailing_stop': self.short_trailing_spin.value(),
                'stop_loss': self.short_stop_loss_spin.value(),
                'reentry_gain': self.short_reentry_spin.value()
            },
            'notifications': {
                'slack': {
                    'enabled': self.slack_enabled_check.isChecked(),
                    'webhook_url': self.slack_webhook_edit.text(),
                    'channel': self.slack_channel_edit.text()
                },
                'telegram': {
                    'enabled': self.telegram_enabled_check.isChecked(),
                    'bot_token': self.telegram_token_edit.text(),
                    'chat_id': self.telegram_chat_edit.text()
                },
                'email': {
                    'enabled': self.email_enabled_check.isChecked(),
                    'sender_email': self.email_sender_edit.text(),
                    'sender_password': self.email_password_edit.text(),
                    'recipient_email': self.email_recipient_edit.text()
                }
            },
            'gui': {
                'theme': ['dark', 'light', 'auto'][self.theme_combo.currentIndex()],
                'chart_update_interval': self.chart_update_spin.value(),
                'position_update_interval': self.position_update_spin.value(),
                'auto_scroll_logs': self.auto_scroll_check.isChecked(),
                'minimize_to_tray': self.minimize_to_tray_check.isChecked(),
                'start_minimized': self.start_minimized_check.isChecked()
            }
        }
    
    def test_api_connection(self):
        """API 연결 테스트"""
        api_key = self.api_key_edit.text()
        api_secret = self.api_secret_edit.text()
        passphrase = self.passphrase_edit.text()
        
        if not all([api_key, api_secret, passphrase]):
            QMessageBox.warning(self, "API 테스트", "모든 API 정보를 입력해주세요.")
            return
        
        # 테스트 스레드 시작
        self.test_thread = APITestThread(api_key, api_secret, passphrase)
        self.test_thread.test_completed.connect(self.on_api_test_completed)
        
        # 버튼 비활성화 및 프로그레스 표시
        self.test_api_btn.setText("테스트 중...")
        self.test_api_btn.setEnabled(False)
        
        self.test_thread.start()
    
    def on_api_test_completed(self, success: bool, message: str):
        """API 테스트 완료"""
        self.test_api_btn.setText("API 테스트")
        self.test_api_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "API 테스트", f"✅ {message}")
        else:
            QMessageBox.warning(self, "API 테스트", f"❌ {message}")
    
    def test_notifications(self):
        """알림 테스트"""
        dialog = NotificationTestDialog(self)
        dialog.exec_()
    
    def reset_to_defaults(self):
        """기본값으로 초기화"""
        reply = QMessageBox.question(self, "설정 초기화", 
                                   "모든 설정을 기본값으로 초기화하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            default_config = config_manager.get_default_config()
            self.current_config = default_config
            self.load_current_settings()
    
    def save_settings(self):
        """설정 저장"""
        try:
            new_config = self.collect_settings()
            
            # 설정 검증
            from gui.config_validator import config_integrator
            is_valid, errors = config_integrator.validate_and_save_gui_config(new_config)
            
            if is_valid:
                QMessageBox.information(self, "설정 저장", "✅ 설정이 저장되었습니다.")
                self.settings_changed.emit(new_config)
                self.close()
            else:
                error_message = "설정 검증 실패:\n\n" + "\n".join(errors)
                QMessageBox.warning(self, "설정 오류", error_message)
                
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"설정 저장 중 오류: {str(e)}")
    
    def load_backup_list(self):
        """백업 목록 로드"""
        try:
            backups = config_manager.list_backups()
            
            self.backup_table.setRowCount(len(backups))
            
            for i, backup_file in enumerate(backups):
                # 파일명에서 날짜/시간 추출
                parts = backup_file.replace('config_backup_', '').replace('.json', '')
                if '_' in parts:
                    date_part, time_part = parts.split('_')
                    date_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                    time_str = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                else:
                    date_str = "알 수 없음"
                    time_str = "알 수 없음"
                
                # 파일 크기
                try:
                    file_path = os.path.join(config_manager.backup_dir, backup_file)
                    size = os.path.getsize(file_path)
                    size_str = f"{size} bytes"
                except:
                    size_str = "알 수 없음"
                
                self.backup_table.setItem(i, 0, QTableWidgetItem(date_str))
                self.backup_table.setItem(i, 1, QTableWidgetItem(time_str))
                self.backup_table.setItem(i, 2, QTableWidgetItem(size_str))
                
        except Exception as e:
            QMessageBox.warning(self, "백업 목록", f"백업 목록 로드 실패: {str(e)}")
    
    def create_backup(self):
        """수동 백업 생성"""
        try:
            backup_file = config_manager.create_backup()
            if backup_file:
                QMessageBox.information(self, "백업 생성", f"✅ 백업이 생성되었습니다:\n{backup_file}")
                self.load_backup_list()
            else:
                QMessageBox.warning(self, "백업 생성", "❌ 백업 생성에 실패했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "백업 오류", f"백업 생성 중 오류: {str(e)}")
    
    def restore_backup(self):
        """백업 복원"""
        current_row = self.backup_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "백업 복원", "복원할 백업을 선택해주세요.")
            return
        
        backups = config_manager.list_backups()
        if current_row >= len(backups):
            QMessageBox.warning(self, "백업 복원", "잘못된 백업 선택입니다.")
            return
        
        backup_file = backups[current_row]
        backup_path = os.path.join(config_manager.backup_dir, backup_file)
        
        reply = QMessageBox.question(self, "백업 복원", 
                                   f"선택한 백업으로 복원하시겠습니까?\n\n{backup_file}\n\n"
                                   "현재 설정이 손실될 수 있습니다.",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                if config_manager.restore_backup(backup_path):
                    QMessageBox.information(self, "백업 복원", "✅ 백업이 복원되었습니다.")
                    # 설정 다시 로드
                    self.current_config = config_manager.load_config()
                    self.load_current_settings()
                else:
                    QMessageBox.warning(self, "백업 복원", "❌ 백업 복원에 실패했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "복원 오류", f"백업 복원 중 오류: {str(e)}")
    
    def delete_backup(self):
        """백업 삭제"""
        current_row = self.backup_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "백업 삭제", "삭제할 백업을 선택해주세요.")
            return
        
        backups = config_manager.list_backups()
        if current_row >= len(backups):
            QMessageBox.warning(self, "백업 삭제", "잘못된 백업 선택입니다.")
            return
        
        backup_file = backups[current_row]
        
        reply = QMessageBox.question(self, "백업 삭제", 
                                   f"선택한 백업을 삭제하시겠습니까?\n\n{backup_file}",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                backup_path = os.path.join(config_manager.backup_dir, backup_file)
                os.remove(backup_path)
                QMessageBox.information(self, "백업 삭제", "✅ 백업이 삭제되었습니다.")
                self.load_backup_list()
            except Exception as e:
                QMessageBox.critical(self, "삭제 오류", f"백업 삭제 중 오류: {str(e)}")
    
    def export_settings(self):
        """설정 내보내기"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "설정 내보내기", 
            f"trading_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                if config_manager.export_config(file_path):
                    QMessageBox.information(self, "설정 내보내기", f"✅ 설정이 내보내기되었습니다:\n{file_path}")
                else:
                    QMessageBox.warning(self, "설정 내보내기", "❌ 설정 내보내기에 실패했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "내보내기 오류", f"설정 내보내기 중 오류: {str(e)}")
    
    def import_settings(self):
        """설정 가져오기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "설정 가져오기", "",
            "JSON Files (*.json)"
        )
        
        if file_path:
            reply = QMessageBox.question(self, "설정 가져오기", 
                                       f"선택한 파일에서 설정을 가져오시겠습니까?\n\n{file_path}\n\n"
                                       "현재 설정이 덮어써질 수 있습니다.",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                try:
                    if config_manager.import_config(file_path):
                        QMessageBox.information(self, "설정 가져오기", "✅ 설정이 가져와졌습니다.")
                        # 설정 다시 로드
                        self.current_config = config_manager.load_config()
                        self.load_current_settings()
                    else:
                        QMessageBox.warning(self, "설정 가져오기", "❌ 설정 가져오기에 실패했습니다.")
                except Exception as e:
                    QMessageBox.critical(self, "가져오기 오류", f"설정 가져오기 중 오류: {str(e)}")

# 메인 실행 (테스트용)
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    dialog = AdvancedSettingsDialog()
    dialog.show()
    
    sys.exit(app.exec_())
        