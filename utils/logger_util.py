# utils/logger.py
"""
통합 로깅 시스템
"""

import logging
import os
from datetime import datetime
from typing import Optional

class TradingLogger:
    def __init__(self, name='trading', log_dir='logs'):
        self.log_dir = log_dir
        self.setup_directories()
        
        # 메인 로거
        self.logger = self.setup_logger(name, f'{log_dir}/trading.log')
        
        # 전용 로거들
        self.trade_logger = self.setup_logger('trades', f'{log_dir}/trades.log')
        self.signal_logger = self.setup_logger('signals', f'{log_dir}/signals.log')
        self.error_logger = self.setup_logger('errors', f'{log_dir}/errors.log')
    
    def setup_directories(self):
        """로그 디렉토리 생성"""
        os.makedirs(self.log_dir, exist_ok=True)
    
    def setup_logger(self, name: str, log_file: str) -> logging.Logger:
        """개별 로거 설정"""
        logger = logging.getLogger(name)
        
        # 기존 핸들러 제거 (중복 방지)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        logger.setLevel(logging.INFO)
        
        # 파일 핸들러
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def info(self, message: str):
        """일반 정보"""
        self.logger.info(message)
        print(f"[INFO] {message}")
    
    def error(self, message: str, exception: Optional[Exception] = None):
        """오류 로깅"""
        if exception:
            error_msg = f"{message}: {str(exception)}"
        else:
            error_msg = message
            
        self.error_logger.error(error_msg)
        self.logger.error(error_msg)
        print(f"[ERROR] {error_msg}")
    
    def trade(self, action: str, symbol: str, side: str, price: float, 
              size: float, pnl: Optional[float] = None):
        """거래 로깅"""
        message = f"{action.upper()} | {symbol} | {side.upper()} | Size: {size:.6f} | Price: ${price:.2f}"
        
        if pnl is not None:
            pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            message += f" | PnL: {pnl_str}"
        
        self.trade_logger.info(message)
        self.logger.info(f"TRADE: {message}")
        print(f"[TRADE] {message}")
    
    def signal(self, symbol: str, signal_type: str, details: str = ""):
        """신호 로깅"""
        message = f"{symbol} | {signal_type}"
        if details:
            message += f" | {details}"
        
        self.signal_logger.info(message)
        self.logger.info(f"SIGNAL: {message}")
        print(f"[SIGNAL] {message}")
    
    def system(self, message: str):
        """시스템 로깅"""
        system_msg = f"SYSTEM: {message}"
        self.logger.info(system_msg)
        print(f"[SYSTEM] {message}")
    
    def position(self, action: str, symbol: str, details: dict):
        """포지션 관련 로깅"""
        message = f"{action.upper()} | {symbol}"
        
        for key, value in details.items():
            if isinstance(value, float):
                if key in ['price', 'avg_price', 'entry_price']:
                    message += f" | {key}: ${value:.2f}"
                elif key in ['size', 'position_size']:
                    message += f" | {key}: {value:.6f}"
                elif key in ['pnl', 'unrealized_pnl']:
                    pnl_str = f"+${value:.2f}" if value >= 0 else f"-${abs(value):.2f}"
                    message += f" | {key}: {pnl_str}"
                else:
                    message += f" | {key}: {value:.4f}"
            else:
                message += f" | {key}: {value}"
        
        self.logger.info(f"POSITION: {message}")
        print(f"[POSITION] {message}")

# 전역 로거 인스턴스
trading_logger = TradingLogger()

# 편의 함수들
def log_info(message: str):
    trading_logger.info(message)

def log_error(message: str, exception: Optional[Exception] = None):
    trading_logger.error(message, exception)

def log_trade(action: str, symbol: str, side: str, price: float, size: float, pnl: Optional[float] = None):
    trading_logger.trade(action, symbol, side, price, size, pnl)

def log_signal(symbol: str, signal_type: str, details: str = ""):
    trading_logger.signal(symbol, signal_type, details)

def log_system(message: str):
    trading_logger.system(message)

def log_position(action: str, symbol: str, details: dict):
    trading_logger.position(action, symbol, details)