# utils/logger.py
"""
로깅 시스템 - 완전 수정 버전 (Windows 호환)
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Windows 인코딩 문제 완전 해결
if sys.platform.startswith('win'):
    # stdout/stderr 재지정 없이 기본 설정만 변경
    pass

def setup_logger(name="trading_bot", level=logging.INFO, log_dir="logs"):
    """
    로거 설정 - 안전한 버전
    """
    # 로그 디렉토리 생성
    os.makedirs(log_dir, exist_ok=True)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 핸들러가 이미 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()
    
    # 기본 포맷터 (이모지 없음)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 (기본 설정)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (UTF-8 인코딩)
    try:
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, f"{name}.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ 파일 핸들러 생성 실패: {e}")
    
    # 거래 전용 파일 핸들러
    try:
        trade_handler = RotatingFileHandler(
            os.path.join(log_dir, "trades.log"),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10,
            encoding='utf-8'
        )
        trade_handler.setFormatter(formatter)
        trade_handler.addFilter(TradeFilter())
        logger.addHandler(trade_handler)
    except Exception as e:
        print(f"⚠️ 거래 핸들러 생성 실패: {e}")
    
    # 에러 전용 파일 핸들러
    try:
        error_handler = RotatingFileHandler(
            os.path.join(log_dir, "errors.log"),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
    except Exception as e:
        print(f"⚠️ 에러 핸들러 생성 실패: {e}")
    
    return logger

class TradeFilter(logging.Filter):
    """거래 관련 로그만 필터링"""
    
    def filter(self, record):
        trade_keywords = ['TRADE', 'ORDER', 'POSITION', 'BUY', 'SELL']
        return any(keyword in record.getMessage().upper() for keyword in trade_keywords)

class GUILogHandler(logging.Handler):
    """GUI 로그 위젯으로 로그 전송"""
    
    def __init__(self, log_widget=None):
        super().__init__()
        self.log_widget = log_widget
    
    def emit(self, record):
        if self.log_widget:
            try:
                msg = self.format(record)
                level = record.levelname
                self.log_widget.add_log(msg, level)
            except Exception:
                pass

def get_logger(name="trading_bot"):
    """기본 로거 반환"""
    return logging.getLogger(name)

# 전역 로거 인스턴스
default_logger = None

def init_logging(name="trading_bot", level=logging.INFO, log_dir="logs"):
    """전역 로깅 초기화"""
    global default_logger
    default_logger = setup_logger(name, level, log_dir)
    return default_logger

def _safe_log_message(message):
    """안전한 로그 메시지 생성 (이모지 제거)"""
    # 이모지 및 특수 문자를 안전한 텍스트로 변환
    emoji_map = {
        '✅': '[OK]',
        '❌': '[ERROR]',
        '🚀': '[ROCKET]',
        '💰': '[MONEY]',
        '📊': '[CHART]',
        '🎯': '[TARGET]',
        '💼': '[BRIEFCASE]',
        '🛑': '[STOP]',
        '📈': '[UP]',
        '📉': '[DOWN]',
        '🔗': '[LINK]',
        '💡': '[IDEA]',
        '⚠️': '[WARNING]',
        '🎮': '[GAME]',
        '📱': '[PHONE]',
        '🔧': '[TOOL]',
        '📖': '[BOOK]',
        '💳': '[CARD]',
        '🌟': '[STAR]',
        '🔥': '[FIRE]',
        '⭐': '[STAR]',
        '💻': '[COMPUTER]',
        '🎵': '[MUSIC]'
    }
    
    # 이모지 변환
    for emoji, replacement in emoji_map.items():
        message = message.replace(emoji, replacement)
    
    # Windows cp949 인코딩 문제 해결
    try:
        # ASCII로 안전하게 변환 시도
        message.encode('ascii')
        return message
    except UnicodeEncodeError:
        # 인코딩 불가능한 문자들을 제거
        safe_message = message.encode('ascii', 'ignore').decode('ascii')
        return safe_message

# 로깅 함수들 - 안전한 메시지 처리
def log_trade(action, symbol, amount, price, **kwargs):
    """거래 로그 기록"""
    try:
        logger = get_logger()
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"TRADE: {action} {amount} {symbol} @ {price}"
        if extra_info:
            message += f" | {extra_info}"
        logger.info(_safe_log_message(message))
    except Exception as e:
        print(f"로그 기록 실패: {e}")

def log_error(error, context=""):
    """에러 로그 기록"""
    try:
        logger = get_logger()
        message = f"ERROR: {error}"
        if context:
            message += f" | Context: {context}"
        logger.error(_safe_log_message(message))
    except Exception as e:
        print(f"에러 로그 기록 실패: {e}")

def log_performance(metrics):
    """성능 지표 로그"""
    try:
        logger = get_logger()
        logger.info(_safe_log_message(f"PERFORMANCE: {metrics}"))
    except Exception as e:
        print(f"성능 로그 기록 실패: {e}")

def log_system(message, context=""):
    """시스템 로그 기록"""
    try:
        logger = get_logger()
        full_message = f"SYSTEM: {message}"
        if context:
            full_message += f" | Context: {context}"
        logger.info(_safe_log_message(full_message))
    except Exception as e:
        print(f"시스템 로그 기록 실패: {e}")

def log_info(message, context=""):
    """일반 정보 로그 기록"""
    try:
        logger = get_logger()
        full_message = f"INFO: {message}"
        if context:
            full_message += f" | Context: {context}"
        logger.info(_safe_log_message(full_message))
    except Exception as e:
        print(f"정보 로그 기록 실패: {e}")

def log_warning(message, context=""):
    """경고 로그 기록"""
    try:
        logger = get_logger()
        full_message = f"WARNING: {message}"
        if context:
            full_message += f" | Context: {context}"
        logger.warning(_safe_log_message(full_message))
    except Exception as e:
        print(f"경고 로그 기록 실패: {e}")

def log_debug(message, context=""):
    """디버그 로그 기록"""
    try:
        logger = get_logger()
        full_message = f"DEBUG: {message}"
        if context:
            full_message += f" | Context: {context}"
        logger.debug(_safe_log_message(full_message))
    except Exception as e:
        print(f"디버그 로그 기록 실패: {e}")

# 데코레이터
def log_function_call(func):
    """함수 호출 로깅 데코레이터"""
    def wrapper(*args, **kwargs):
        try:
            logger = get_logger()
            logger.debug(_safe_log_message(f"Calling {func.__name__}"))
            result = func(*args, **kwargs)
            logger.debug(_safe_log_message(f"{func.__name__} completed successfully"))
            return result
        except Exception as e:
            logger.error(_safe_log_message(f"{func.__name__} failed: {e}"))
            raise
    return wrapper

# 로깅 시스템 자동 초기화
try:
    default_logger = setup_logger()
    print("[OK] 로깅 시스템 초기화 완료")
except Exception as e:
    print(f"[WARNING] 로깅 시스템 초기화 실패: {e}")
    # 기본 로깅으로 폴백
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('trading.log', encoding='utf-8')
        ]
    )