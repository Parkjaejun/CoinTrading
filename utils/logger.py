# utils/logger.py
"""
로깅 시스템 - 완전한 버전
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import colorlog

def setup_logger(name="trading_bot", level=logging.INFO, log_dir="logs"):
    """
    로거 설정
    
    Args:
        name: 로거 이름
        level: 로그 레벨
        log_dir: 로그 디렉토리
    
    Returns:
        logging.Logger: 설정된 로거
    """
    # 로그 디렉토리 생성
    os.makedirs(log_dir, exist_ok=True)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 핸들러가 이미 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 (컬러 로그)
    console_handler = colorlog.StreamHandler()
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (일반 로그)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, f"{name}.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 거래 전용 파일 핸들러
    trade_handler = RotatingFileHandler(
        os.path.join(log_dir, "trades.log"),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=10
    )
    trade_handler.setFormatter(formatter)
    trade_handler.addFilter(TradeFilter())
    logger.addHandler(trade_handler)
    
    # 에러 전용 파일 핸들러
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "errors.log"),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)
    
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
                pass  # GUI 로그 실패해도 프로그램은 계속 실행

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

def log_trade(action, symbol, amount, price, **kwargs):
    """거래 로그 기록"""
    logger = get_logger()
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    message = f"TRADE: {action} {amount} {symbol} @ {price}"
    if extra_info:
        message += f" | {extra_info}"
    logger.info(message)

def log_error(error, context=""):
    """에러 로그 기록"""
    logger = get_logger()
    message = f"ERROR: {error}"
    if context:
        message += f" | Context: {context}"
    logger.error(message)

def log_performance(metrics):
    """성능 지표 로그"""
    logger = get_logger()
    logger.info(f"PERFORMANCE: {metrics}")

# 데코레이터
def log_function_call(func):
    """함수 호출 로깅 데코레이터"""
    def wrapper(*args, **kwargs):
        logger = get_logger()
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            raise
    return wrapper