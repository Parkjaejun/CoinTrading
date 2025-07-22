"""
간단한 로깅 시스템
"""

import logging
import os
from datetime import datetime

def setup_logger(name='trading', log_file='logs/trading.log'):
    """로거 설정"""
    # logs 디렉토리 생성
    os.makedirs('logs', exist_ok=True)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 전역 로거 인스턴스
trading_logger = setup_logger()

def log_trade(action, symbol, side, price, size, pnl=None):
    """거래 로그"""
    message = f"거래 {action}: {symbol} {side.upper()} {size} @ ${price:.2f}"
    if pnl is not None:
        message += f" | PnL: {pnl:+.2f}"
    
    trading_logger.info(message)

def log_signal(symbol, signal_type, details=""):
    """신호 로그"""
    message = f"신호: {symbol} {signal_type}"
    if details:
        message += f" | {details}"
    
    trading_logger.info(message)

def log_error(error_msg, exception=None):
    """오류 로그"""
    if exception:
        trading_logger.error(f"{error_msg}: {exception}")
    else:
        trading_logger.error(error_msg)

def log_system(message):
    """시스템 로그"""
    trading_logger.info(f"시스템: {message}")