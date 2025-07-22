# utils/notifications.py
"""
알림 시스템 - 슬랙, 텔레그램, 이메일 지원
"""

import requests
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional, List
from utils.logger import log_system, log_error
import threading
import queue
import time

class NotificationManager:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 알림 큐 (비동기 처리)
        self.notification_queue = queue.Queue()
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # 알림 채널별 활성화 상태
        self.channels = {
            'slack': self.config.get('slack', {}).get('enabled', False),
            'telegram': self.config.get('telegram', {}).get('enabled', False),
            'email': self.config.get('email', {}).get('enabled', False)
        }
        
        # 알림 제한 (스팸 방지)
        self.rate_limits = {
            'max_per_minute': 30,
            'max_per_hour': 200
        }
        self.notification_history: List[datetime] = []
        
        log_system(f"알림 시스템 초기화: {[k for k, v in self.channels.items() if v]}")
    
    def start_notification_service(self):
        """알림 서비스 시작 (백그라운드 처리)"""
        if self.is_running:
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(
            target=self._notification_worker,
            name="NotificationWorker",
            daemon=True
        )
        self.worker_thread.start()
        
        log_system("알림 서비스 시작")
    
    def stop_notification_service(self):
        """알림 서비스 중지"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 남은 알림들 처리
        self.notification_queue.put(None)  # 종료 신호
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        
        log_system("알림 서비스 중지")
    
    def _notification_worker(self):
        """백그라운드 알림 처리"""
        while self.is_running:
            try:
                # 큐에서 알림 가져오기 (1초 타임아웃)
                notification = self.notification_queue.get(timeout=1)
                
                # 종료 신호 확인
                if notification is None:
                    break
                
                # 속도 제한 확인
                if not self._check_rate_limit():
                    continue
                
                # 알림 전송
                self._process_notification(notification)
                
                # 처리 완료 표시
                self.notification_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                log_error("알림 처리 오류", e)
    
    def _check_rate_limit(self) -> bool:
        """알림 속도 제한 확인"""
        current_time = datetime.now()
        
        # 1분/1시간 이내 알림 수 확인
        minute_ago = current_time.timestamp() - 60
        hour_ago = current_time.timestamp() - 3600
        
        recent_notifications = [
            dt for dt in self.notification_history
            if dt.timestamp() > hour_ago
        ]
        
        minute_count = len([dt for dt in recent_notifications if dt.timestamp() > minute_ago])
        hour_count = len(recent_notifications)
        
        if minute_count >= self.rate_limits['max_per_minute']:
            log_error("알림 속도 제한: 분당 한도 초과")
            return False
        
        if hour_count >= self.rate_limits['max_per_hour']:
            log_error("알림 속도 제한: 시간당 한도 초과")
            return False
        
        # 기록 업데이트
        self.notification_history.append(current_time)
        
        # 오래된 기록 정리
        self.notification_history = recent_notifications + [current_time]
        
        return True
    
    def _process_notification(self, notification: Dict[str, Any]):
        """개별 알림 처리"""
        message_type = notification.get('type', 'info')
        title = notification.get('title', 'Trading Alert')
        message = notification.get('message', '')
        details = notification.get('details', {})
        
        # 채널별 전송
        if self.channels['slack']:
            self._send_slack_message(title, message, details, message_type)
        
        if self.channels['telegram']:
            self._send_telegram_message(title, message, details)
        
        if self.channels['email']:
            self._send_email_message(title, message, details, message_type)
    
    def _send_slack_message(self, title: str, message: str, details: Dict, msg_type: str):
        """슬랙 메시지 전송"""
        try:
            slack_config = self.config.get('slack', {})
            webhook_url = slack_config.get('webhook_url')
            
            if not webhook_url:
                log_error("슬랙 웹훅 URL이 설정되지 않음")
                return
            
            # 메시지 색상 (타입별)
            colors = {
                'trade': '#36a64f',      # 녹색 (거래)
                'entry': '#2eb886',      # 청록색 (진입)
                'exit': '#ff9500',       # 주황색 (청산)
                'profit': '#36a64f',     # 녹색 (수익)
                'loss': '#ff0000',       # 빨간색 (손실)
                'warning': '#ffcc00',    # 노란색 (경고)
                'error': '#ff0000',      # 빨간색 (오류)
                'info': '#36a64f'        # 기본 녹색
            }
            
            # 슬랙 첨부 구성
            attachment = {
                "color": colors.get(msg_type, colors['info']),
                "title": title,
                "text": message,
                "timestamp": int(datetime.now().timestamp()),
                "fields": []
            }
            
            # 상세 정보 추가
            for key, value in details.items():
                field_title = key.replace('_', ' ').title()
                
                if isinstance(value, float):
                    if key in ['price', 'entry_price', 'exit_price']:
                        field_value = f"${value:.2f}"
                    elif key in ['pnl', 'profit', 'loss']:
                        field_value = f"${value:+.2f}"
                    elif key in ['percentage', 'win_rate']:
                        field_value = f"{value:.1f}%"
                    else:
                        field_value = f"{value:.4f}"
                else:
                    field_value = str(value)
                
                attachment["fields"].append({
                    "title": field_title,
                    "value": field_value,
                    "short": True
                })
            
            # 슬랙 페이로드
            payload = {
                "username": "Trading Bot",
                "icon_emoji": ":robot_face:",
                "attachments": [attachment]
            }
            
            # HTTP 요청
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_system("슬랙 알림 전송 성공")
            else:
                log_error(f"슬랙 알림 전송 실패: {response.status_code}")
                
        except Exception as e:
            log_error("슬랙 알림 전송 오류", e)
    
    def _send_telegram_message(self, title: str, message: str, details: Dict):
        """텔레그램 메시지 전송"""
        try:
            telegram_config = self.config.get('telegram', {})
            bot_token = telegram_config.get('bot_token')
            chat_id = telegram_config.get('chat_id')
            
            if not bot_token or not chat_id:
                log_error("텔레그램 설정 불완전")
                return
            
            # 메시지 구성
            full_message = f"🤖 *{title}*\n\n{message}\n"
            
            if details:
                full_message += "\n📊 *상세 정보:*\n"
                for key, value in details.items():
                    field_name = key.replace('_', ' ').title()
                    if isinstance(value, float):
                        if key in ['price', 'entry_price', 'exit_price']:
                            field_value = f"${value:.2f}"
                        elif key in ['pnl', 'profit', 'loss']:
                            field_value = f"${value:+.2f}"
                        else:
                            field_value = f"{value:.4f}"
                    else:
                        field_value = str(value)
                    
                    full_message += f"• {field_name}: `{field_value}`\n"
            
            # API 요청
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': full_message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                log_system("텔레그램 알림 전송 성공")
            else:
                log_error(f"텔레그램 알림 전송 실패: {response.status_code}")
                
        except Exception as e:
            log_error("텔레그램 알림 전송 오류", e)
    
    def _send_email_message(self, title: str, message: str, details: Dict, msg_type: str):
        """이메일 메시지 전송"""
        try:
            email_config = self.config.get('email', {})
            smtp_server = email_config.get('smtp_server')
            smtp_port = email_config.get('smtp_port', 587)
            sender_email = email_config.get('sender_email')
            sender_password = email_config.get('sender_password')
            recipient_email = email_config.get('recipient_email')
            
            if not all([smtp_server, sender_email, sender_password, recipient_email]):
                log_error("이메일 설정 불완전")
                return
            
            # 이메일 구성
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"Trading Alert: {title}"
            
            # 본문 작성
            body = f"""
            <html>
            <head></head>
            <body>
                <h2 style="color: {'green' if msg_type == 'profit' else 'red' if msg_type == 'loss' else 'blue'};">
                    {title}
                </h2>
                <p><strong>메시지:</strong> {message}</p>
                
                <h3>상세 정보:</h3>
                <table border="1" style="border-collapse: collapse;">
                    <tr style="background-color: #f2f2f2;">
                        <th>항목</th>
                        <th>값</th>
                    </tr>
            """
            
            for key, value in details.items():
                field_name = key.replace('_', ' ').title()
                if isinstance(value, float):
                    if key in ['price', 'entry_price', 'exit_price']:
                        field_value = f"${value:.2f}"
                    elif key in ['pnl', 'profit', 'loss']:
                        field_value = f"${value:+.2f}"
                    else:
                        field_value = f"{value:.4f}"
                else:
                    field_value = str(value)
                
                body += f"""
                    <tr>
                        <td>{field_name}</td>
                        <td>{field_value}</td>
                    </tr>
                """
            
            body += """
                </table>
                <br>
                <p><em>자동매매 봇에서 전송된 메시지입니다.</em></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # SMTP 서버 연결 및 전송
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            log_system("이메일 알림 전송 성공")
            
        except Exception as e:
            log_error("이메일 알림 전송 오류", e)
    
    # 편의 메서드들
    def send_trade_notification(self, action: str, symbol: str, side: str, 
                              price: float, size: float, pnl: float = None):
        """거래 알림"""
        title = f"{action.upper()} - {symbol}"
        message = f"{side.upper()} 포지션 {action}"
        
        details = {
            'symbol': symbol,
            'side': side.upper(),
            'price': price,
            'size': size,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        if pnl is not None:
            details['pnl'] = pnl
            message += f" (PnL: ${pnl:+.2f})"
        
        msg_type = 'profit' if pnl and pnl > 0 else 'loss' if pnl and pnl < 0 else 'trade'
        
        self.send_notification(title, message, details, msg_type)
    
    def send_system_notification(self, title: str, message: str, level: str = 'info'):
        """시스템 알림"""
        details = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': level.upper()
        }
        
        self.send_notification(title, message, details, level)
    
    def send_error_notification(self, error_message: str, exception: Exception = None):
        """오류 알림"""
        title = "System Error"
        message = error_message
        
        details = {
            'error_type': type(exception).__name__ if exception else 'Unknown',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if exception:
            details['exception_message'] = str(exception)
        
        self.send_notification(title, message, details, 'error')
    
    def send_notification(self, title: str, message: str, details: Dict = None, 
                         msg_type: str = 'info'):
        """일반 알림 전송 (큐에 추가)"""
        if not any(self.channels.values()):
            return  # 활성화된 채널이 없음
        
        notification = {
            'type': msg_type,
            'title': title,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now()
        }
        
        try:
            self.notification_queue.put(notification, timeout=1)
        except queue.Full:
            log_error("알림 큐 가득 찬 상태 - 알림 누락")
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """알림 통계"""
        current_time = datetime.now()
        hour_ago = current_time.timestamp() - 3600
        
        recent_count = len([
            dt for dt in self.notification_history
            if dt.timestamp() > hour_ago
        ])
        
        return {
            'active_channels': [k for k, v in self.channels.items() if v],
            'queue_size': self.notification_queue.qsize(),
            'notifications_last_hour': recent_count,
            'is_service_running': self.is_running
        }

# 기본 설정 (config.py에서 오버라이드 가능)
DEFAULT_NOTIFICATION_CONFIG = {
    'slack': {
        'enabled': False,
        'webhook_url': None
    },
    'telegram': {
        'enabled': False,
        'bot_token': None,
        'chat_id': None
    },
    'email': {
        'enabled': False,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender_email': None,
        'sender_password': None,
        'recipient_email': None
    }
}

# 전역 알림 매니저
notification_manager: Optional[NotificationManager] = None

def initialize_notifications(config: Dict[str, Any] = None):
    """알림 시스템 초기화"""
    global notification_manager
    
    if notification_manager is None:
        final_config = DEFAULT_NOTIFICATION_CONFIG.copy()
        if config:
            final_config.update(config)
        
        notification_manager = NotificationManager(final_config)
        notification_manager.start_notification_service()

def send_trade_alert(action: str, symbol: str, side: str, price: float, size: float, pnl: float = None):
    """거래 알림 전송"""
    if notification_manager:
        notification_manager.send_trade_notification(action, symbol, side, price, size, pnl)

def send_system_alert(title: str, message: str, level: str = 'info'):
    """시스템 알림 전송"""
    if notification_manager:
        notification_manager.send_system_notification(title, message, level)

def send_error_alert(error_message: str, exception: Exception = None):
    """오류 알림 전송"""
    if notification_manager:
        notification_manager.send_error_notification(error_message, exception)