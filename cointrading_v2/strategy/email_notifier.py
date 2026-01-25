# strategy/email_notifier.py
"""
이메일 알림 시스템

거래 이벤트 발생 시 이메일 알림 발송
- 포지션 진입/청산
- 모드 전환 (REAL ↔ VIRTUAL)
- 오류 발생
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import EmailConfig, DEFAULT_EMAIL_CONFIG
except ImportError:
    # 독립 실행 시 기본 설정 사용
    from dataclasses import dataclass
    
    @dataclass
    class EmailConfig:
        smtp_server: str = "smtp.gmail.com"
        smtp_port: int = 587
        sender_email: str = ""
        sender_password: str = ""
        recipient_email: str = ""
        notify_on_entry: bool = True
        notify_on_exit: bool = True
        notify_on_mode_switch: bool = True
        notify_on_error: bool = True
        
        @property
        def is_configured(self) -> bool:
            return bool(self.sender_email and self.sender_password and self.recipient_email)
    
    DEFAULT_EMAIL_CONFIG = EmailConfig()


class EmailNotifier:
    """
    이메일 알림 발송 클래스
    
    SMTP를 통해 거래 알림 이메일 발송
    """
    
    def __init__(self, config: EmailConfig = None):
        """
        Args:
            config: 이메일 설정 (None이면 기본값 사용)
        """
        self.config = config or DEFAULT_EMAIL_CONFIG
        self.enabled = self.config.is_configured
        self.send_count = 0
        self.last_error: Optional[str] = None
        
        if self.enabled:
            print(f"✅ [Email] 알림 활성화: {self.config.recipient_email}")
        else:
            print(f"⚠️ [Email] 설정 미완료 - 알림 비활성화")
    
    def send_entry_alert(self, details: Dict[str, Any]) -> bool:
        """
        진입 알림 발송
        
        Args:
            details: 진입 정보 딕셔너리
                - symbol: 심볼
                - price: 진입가
                - size: 포지션 크기
                - leverage: 레버리지
                - mode: REAL/VIRTUAL
                - capital: 현재 자본
                - reason: 진입 이유
                - timestamp: 시간
        
        Returns:
            발송 성공 여부
        """
        if not self.enabled or not self.config.notify_on_entry:
            return False
        
        subject = f"🟢 LONG 진입 @ ${details.get('price', 0):,.2f}"
        
        body = self._format_entry_body(details)
        
        return self._send(subject, body, details)
    
    def send_exit_alert(self, details: Dict[str, Any]) -> bool:
        """
        청산 알림 발송
        
        Args:
            details: 청산 정보 딕셔너리
                - symbol: 심볼
                - entry_price: 진입가
                - exit_price: 청산가
                - net_pnl: 순손익
                - mode: REAL/VIRTUAL
                - reason: 청산 이유
                - capital_after: 청산 후 자본
                - timestamp: 시간
        
        Returns:
            발송 성공 여부
        """
        if not self.enabled or not self.config.notify_on_exit:
            return False
        
        pnl = details.get('net_pnl', 0)
        emoji = "💰" if pnl > 0 else "📉"
        subject = f"{emoji} LONG 청산 PnL: ${pnl:+,.2f}"
        
        body = self._format_exit_body(details)
        
        return self._send(subject, body, details)
    
    def send_mode_switch_alert(self, details: Dict[str, Any]) -> bool:
        """
        모드 전환 알림 발송
        
        Args:
            details: 모드 전환 정보 딕셔너리
                - symbol: 심볼
                - from_mode: 이전 모드
                - to_mode: 새 모드
                - reason: 전환 이유
                - real_capital: 실제 자본
                - virtual_capital: 가상 자본
        
        Returns:
            발송 성공 여부
        """
        if not self.enabled or not self.config.notify_on_mode_switch:
            return False
        
        to_mode = details.get('to_mode', '')
        emoji = "⚠️" if to_mode == "VIRTUAL" else "✅"
        subject = f"{emoji} 모드 전환: {details.get('from_mode', '')} → {to_mode}"
        
        body = self._format_mode_switch_body(details)
        
        return self._send(subject, body, details)
    
    def send_error_alert(self, details: Dict[str, Any]) -> bool:
        """
        오류 알림 발송
        
        Args:
            details: 오류 정보 딕셔너리
                - error_type: 오류 유형
                - error_message: 오류 메시지
                - symbol: 심볼 (옵션)
                - timestamp: 시간
        
        Returns:
            발송 성공 여부
        """
        if not self.enabled or not self.config.notify_on_error:
            return False
        
        subject = f"🚨 오류 발생: {details.get('error_type', 'Unknown')}"
        
        body = self._format_error_body(details)
        
        return self._send(subject, body, details)
    
    def _format_entry_body(self, details: Dict[str, Any]) -> str:
        """진입 알림 본문 포맷"""
        return f"""
📈 LONG 포지션 진입

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ 심볼: {details.get('symbol', 'N/A')}
💵 진입가: ${details.get('price', 0):,.2f}
📊 포지션 크기: {details.get('size', 0):.6f}
⚡ 레버리지: {details.get('leverage', 0)}x
🎯 모드: {details.get('mode', 'N/A')}
💰 사용 자본: ${details.get('capital', 0):,.2f}
📝 이유: {details.get('reason', 'N/A')}
⏰ 시간: {details.get('timestamp', datetime.now())}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    def _format_exit_body(self, details: Dict[str, Any]) -> str:
        """청산 알림 본문 포맷"""
        pnl = details.get('net_pnl', 0)
        pnl_emoji = "🟢" if pnl > 0 else "🔴"
        
        return f"""
📉 LONG 포지션 청산

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ 심볼: {details.get('symbol', 'N/A')}
💵 진입가: ${details.get('entry_price', 0):,.2f}
💵 청산가: ${details.get('exit_price', 0):,.2f}
{pnl_emoji} 손익: ${pnl:+,.2f}
🎯 모드: {details.get('mode', 'N/A')}
📝 청산 이유: {details.get('reason', 'N/A')}
💰 청산 후 자본: ${details.get('capital_after', 0):,.2f}
⏰ 시간: {details.get('timestamp', datetime.now())}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    def _format_mode_switch_body(self, details: Dict[str, Any]) -> str:
        """모드 전환 알림 본문 포맷"""
        to_mode = details.get('to_mode', '')
        warning = "⚠️ 손실로 인한 가상 모드 전환" if to_mode == "VIRTUAL" else "✅ 회복으로 인한 실제 모드 복귀"
        
        return f"""
🔄 거래 모드 전환

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ 심볼: {details.get('symbol', 'N/A')}
📌 상태: {warning}
🔀 전환: {details.get('from_mode', '')} → {to_mode}
📝 이유: {details.get('reason', 'N/A')}
💰 실제 자본: ${details.get('real_capital', 0):,.2f}
🎮 가상 자본: ${details.get('virtual_capital', 0):,.2f}
⏰ 시간: {datetime.now()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    def _format_error_body(self, details: Dict[str, Any]) -> str:
        """오류 알림 본문 포맷"""
        return f"""
🚨 시스템 오류 발생

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 오류 유형: {details.get('error_type', 'Unknown')}
📝 오류 메시지: {details.get('error_message', 'N/A')}
🏷️ 심볼: {details.get('symbol', 'N/A')}
⏰ 시간: {details.get('timestamp', datetime.now())}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

즉시 확인이 필요합니다.
"""
    
    def _send(self, subject: str, body: str, details: Dict = None) -> bool:
        """
        실제 이메일 발송
        
        Args:
            subject: 제목
            body: 본문
            details: 추가 정보 (로깅용)
        
        Returns:
            발송 성공 여부
        """
        try:
            msg = MIMEMultipart()
            msg['Subject'] = f"[CoinTrading] {subject}"
            msg['From'] = self.config.sender_email
            msg['To'] = self.config.recipient_email
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.sender_email, self.config.sender_password)
                server.send_message(msg)
            
            self.send_count += 1
            self.last_error = None
            print(f"📧 [Email #{self.send_count}] {subject}")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            print(f"❌ [Email] 발송 실패: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        알림 시스템 상태 조회
        
        Returns:
            상태 딕셔너리
        """
        return {
            'enabled': self.enabled,
            'send_count': self.send_count,
            'last_error': self.last_error,
            'recipient': self.config.recipient_email if self.enabled else None,
        }


class MockEmailNotifier(EmailNotifier):
    """
    테스트용 Mock 이메일 알림
    
    실제 이메일 발송 없이 콘솔에 로그만 출력
    """
    
    def __init__(self):
        """Mock 초기화 - 항상 활성화"""
        self.config = EmailConfig()
        self.config.notify_on_entry = True
        self.config.notify_on_exit = True
        self.config.notify_on_mode_switch = True
        self.config.notify_on_error = True
        
        self.enabled = True
        self.send_count = 0
        self.last_error = None
        self.sent_messages: list = []  # 발송된 메시지 저장
        
        print(f"📧 [MockEmail] 테스트 모드 활성화")
    
    def _send(self, subject: str, body: str, details: Dict = None) -> bool:
        """
        Mock 발송 - 콘솔 출력만
        
        Args:
            subject: 제목
            body: 본문
            details: 추가 정보
        
        Returns:
            항상 True
        """
        self.send_count += 1
        
        # 발송 기록 저장
        self.sent_messages.append({
            'subject': subject,
            'body': body,
            'details': details,
            'timestamp': datetime.now(),
        })
        
        print(f"📧 [MockEmail #{self.send_count}] {subject}")
        return True
    
    def get_sent_messages(self, n: int = 10) -> list:
        """
        발송된 메시지 조회
        
        Args:
            n: 조회할 개수
        
        Returns:
            최근 발송된 메시지 리스트
        """
        return self.sent_messages[-n:]
    
    def clear_messages(self):
        """발송 기록 초기화"""
        self.sent_messages.clear()
        self.send_count = 0
