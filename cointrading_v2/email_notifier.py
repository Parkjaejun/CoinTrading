# email_notifier.py
"""
CoinTrading v2 이메일 알림 시스템
- 포지션 진입/청산 알림
- 모드 전환 알림
- 오류 알림
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional
import traceback

from config_v2 import EmailConfig


class EmailNotifier:
    """이메일 알림 발송기"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.enabled = config.is_configured
        self.send_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
        
        if self.enabled:
            print(f"✅ [EmailNotifier] 초기화 완료 - 수신자: {config.recipient_email}")
        else:
            print(f"⚠️ [EmailNotifier] 설정 미완료 - 알림 비활성화")
    
    def send_entry_alert(self, details: Dict[str, Any]) -> bool:
        """포지션 진입 알림"""
        if not self.config.notify_on_entry:
            return False
        
        subject = f"🟢 [CoinTrading] LONG 진입 - {details.get('symbol', 'BTC')}"
        html_body = self._format_entry_message(details)
        return self._send_email(subject, html_body)
    
    def send_exit_alert(self, details: Dict[str, Any]) -> bool:
        """포지션 청산 알림"""
        if not self.config.notify_on_exit:
            return False
        
        pnl = details.get('net_pnl', 0)
        emoji = "💰" if pnl > 0 else "📉"
        subject = f"{emoji} [CoinTrading] LONG 청산 - PnL: ${pnl:+,.2f}"
        html_body = self._format_exit_message(details)
        return self._send_email(subject, html_body)
    
    def send_mode_switch_alert(self, details: Dict[str, Any]) -> bool:
        """모드 전환 알림"""
        if not self.config.notify_on_mode_switch:
            return False
        
        from_mode = details.get('from_mode', '')
        to_mode = details.get('to_mode', '')
        
        if to_mode == "VIRTUAL":
            emoji = "⚠️"
            status = "거래 중지"
        else:
            emoji = "✅"
            status = "거래 재개"
        
        subject = f"{emoji} [CoinTrading] {status} - {from_mode} → {to_mode}"
        html_body = self._format_mode_switch_message(details)
        return self._send_email(subject, html_body)
    
    def send_error_alert(self, error_type: str, error_message: str, details: Optional[Dict] = None) -> bool:
        """오류 알림"""
        if not self.config.notify_on_error:
            return False
        
        subject = f"🚨 [CoinTrading] 오류 발생 - {error_type}"
        html_body = self._format_error_message(error_type, error_message, details)
        return self._send_email(subject, html_body)
    
    def _format_entry_message(self, details: Dict[str, Any]) -> str:
        """진입 알림 HTML 포맷"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #1a5f1a, #2d8a2d); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">🟢 포지션 진입</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">{details.get('timestamp', datetime.now())}</p>
            </div>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 0 0 10px 10px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">심볼</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{details.get('symbol', 'BTC-USDT-SWAP')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">방향</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; color: #2d8a2d; font-weight: bold;">LONG</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">진입가</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-size: 18px;">${details.get('entry_price', 0):,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">레버리지</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{details.get('leverage', 10)}x</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">모드</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                            <span style="background: {'#2d8a2d' if details.get('mode') == 'REAL' else '#ff9800'}; color: white; padding: 3px 8px; border-radius: 3px;">
                                {details.get('mode', 'REAL')}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">사용 자본</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">${details.get('capital_used', 0):,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">포지션 크기</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{details.get('size', 0):.6f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">진입 이유</td>
                        <td style="padding: 10px;">{details.get('reason', 'EMA 골든크로스')}</td>
                    </tr>
                </table>
            </div>
            
            <div style="text-align: center; padding: 15px; color: #666; font-size: 12px;">
                CoinTrading v2 자동 알림
            </div>
        </body>
        </html>
        """
    
    def _format_exit_message(self, details: Dict[str, Any]) -> str:
        """청산 알림 HTML 포맷"""
        net_pnl = details.get('net_pnl', 0)
        pnl_color = "#2d8a2d" if net_pnl > 0 else "#d32f2f"
        pnl_emoji = "💰" if net_pnl > 0 else "📉"
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #8b0000, #d32f2f); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">🔴 포지션 청산</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">{details.get('timestamp', datetime.now())}</p>
            </div>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 0 0 10px 10px;">
                <div style="background: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                    <p style="margin: 0; color: #666;">순손익 (Net PnL)</p>
                    <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; color: {pnl_color};">
                        {pnl_emoji} ${net_pnl:+,.2f}
                    </p>
                </div>
                
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">심볼</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{details.get('symbol', 'BTC-USDT-SWAP')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">진입가</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">${details.get('entry_price', 0):,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">청산가</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">${details.get('exit_price', 0):,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">모드</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                            <span style="background: {'#2d8a2d' if details.get('mode') == 'REAL' else '#ff9800'}; color: white; padding: 3px 8px; border-radius: 3px;">
                                {details.get('mode', 'REAL')}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">청산 이유</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{details.get('reason', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">수수료</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">${details.get('fee', 0):.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">청산 후 자본</td>
                        <td style="padding: 10px; font-size: 18px;">${details.get('capital_after', 0):,.2f}</td>
                    </tr>
                </table>
            </div>
            
            <div style="text-align: center; padding: 15px; color: #666; font-size: 12px;">
                CoinTrading v2 자동 알림
            </div>
        </body>
        </html>
        """
    
    def _format_mode_switch_message(self, details: Dict[str, Any]) -> str:
        """모드 전환 알림 HTML 포맷"""
        to_mode = details.get('to_mode', '')
        
        if to_mode == "VIRTUAL":
            header_bg = "linear-gradient(135deg, #e65100, #ff9800)"
            status_text = "⚠️ 거래 중지 - 모의 투자 전환"
            status_desc = "손실이 기준치를 초과하여 실제 거래를 중지하고 모의 투자로 전환합니다."
        else:
            header_bg = "linear-gradient(135deg, #1b5e20, #4caf50)"
            status_text = "✅ 거래 재개 - 실제 거래 전환"
            status_desc = "모의 투자에서 수익이 확인되어 실제 거래를 재개합니다."
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {header_bg}; color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">{status_text}</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">{details.get('timestamp', datetime.now())}</p>
            </div>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 0 0 10px 10px;">
                <div style="background: white; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                    <p style="margin: 0; color: #666;">{status_desc}</p>
                </div>
                
                <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 20px;">
                    <span style="background: {'#2d8a2d' if details.get('from_mode') == 'REAL' else '#ff9800'}; color: white; padding: 8px 16px; border-radius: 5px; font-weight: bold;">
                        {details.get('from_mode', '')}
                    </span>
                    <span style="margin: 0 15px; font-size: 24px;">→</span>
                    <span style="background: {'#2d8a2d' if details.get('to_mode') == 'REAL' else '#ff9800'}; color: white; padding: 8px 16px; border-radius: 5px; font-weight: bold;">
                        {details.get('to_mode', '')}
                    </span>
                </div>
                
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">전환 이유</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{details.get('reason', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">REAL 자본</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">${details.get('real_capital', 0):,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">REAL Peak</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">${details.get('real_peak', 0):,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold;">VIRTUAL 자본</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">${details.get('virtual_capital', 0):,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">VIRTUAL Trough</td>
                        <td style="padding: 10px;">${details.get('virtual_trough', 0):,.2f}</td>
                    </tr>
                </table>
            </div>
            
            <div style="text-align: center; padding: 15px; color: #666; font-size: 12px;">
                CoinTrading v2 자동 알림
            </div>
        </body>
        </html>
        """
    
    def _format_error_message(self, error_type: str, error_message: str, details: Optional[Dict] = None) -> str:
        """오류 알림 HTML 포맷"""
        details_html = ""
        if details:
            details_rows = "".join([
                f"<tr><td style='padding: 8px; border-bottom: 1px solid #ddd;'>{k}</td>"
                f"<td style='padding: 8px; border-bottom: 1px solid #ddd;'>{v}</td></tr>"
                for k, v in details.items()
            ])
            details_html = f"""
            <h3 style="margin-top: 20px;">추가 정보</h3>
            <table style="width: 100%; border-collapse: collapse;">
                {details_rows}
            </table>
            """
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #b71c1c, #d32f2f); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">🚨 오류 발생</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">{datetime.now()}</p>
            </div>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 0 0 10px 10px;">
                <div style="background: #ffebee; padding: 15px; border-radius: 10px; border-left: 4px solid #d32f2f;">
                    <p style="margin: 0; font-weight: bold; color: #d32f2f;">{error_type}</p>
                    <p style="margin: 10px 0 0 0; color: #666;">{error_message}</p>
                </div>
                
                {details_html}
            </div>
            
            <div style="text-align: center; padding: 15px; color: #666; font-size: 12px;">
                CoinTrading v2 자동 알림
            </div>
        </body>
        </html>
        """
    
    def _send_email(self, subject: str, html_body: str) -> bool:
        """실제 이메일 발송"""
        if not self.enabled:
            print(f"[EmailNotifier] 비활성화 - 스킵: {subject}")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.sender_email
            msg['To'] = self.config.recipient_email
            
            # HTML 본문 첨부
            msg.attach(MIMEText(html_body, 'html'))
            
            # SMTP 연결 및 발송
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.sender_email, self.config.sender_password)
                server.send_message(msg)
            
            self.send_count += 1
            print(f"✅ [EmailNotifier] 발송 완료 ({self.send_count}): {subject}")
            return True
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            print(f"❌ [EmailNotifier] 발송 실패: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """알림 시스템 상태"""
        return {
            'enabled': self.enabled,
            'configured': self.config.is_configured,
            'recipient': self.config.recipient_email if self.enabled else None,
            'send_count': self.send_count,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'notify_settings': {
                'entry': self.config.notify_on_entry,
                'exit': self.config.notify_on_exit,
                'mode_switch': self.config.notify_on_mode_switch,
                'error': self.config.notify_on_error,
            }
        }
    
    def test_connection(self) -> bool:
        """이메일 연결 테스트"""
        if not self.enabled:
            print("[EmailNotifier] 설정 미완료 - 테스트 불가")
            return False
        
        try:
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.sender_email, self.config.sender_password)
            print("✅ [EmailNotifier] SMTP 연결 테스트 성공")
            return True
        except Exception as e:
            print(f"❌ [EmailNotifier] SMTP 연결 테스트 실패: {e}")
            return False


# 테스트용 Mock Notifier
class MockEmailNotifier(EmailNotifier):
    """테스트용 Mock 알림기 (실제 발송 없음)"""
    
    def __init__(self):
        self.config = EmailConfig()
        self.enabled = True
        self.send_count = 0
        self.error_count = 0
        self.last_error = None
        self.sent_messages = []
        print("[MockEmailNotifier] 테스트 모드 - 실제 발송 없음")
    
    def _send_email(self, subject: str, html_body: str) -> bool:
        """실제 발송 대신 로그만 남김"""
        self.send_count += 1
        self.sent_messages.append({
            'timestamp': datetime.now(),
            'subject': subject,
            'body_length': len(html_body),
        })
        print(f"📧 [MockEmail #{self.send_count}] {subject}")
        return True
