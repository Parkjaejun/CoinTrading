# strategy/dual_manager_improved.py
"""
실시간 데이터 연동을 위한 개선된 듀얼 전략 관리자
- WebSocket으로부터 실시간 데이터 수신
- EMA 기반 신호 생성 및 처리
- 롱/숏 전략 병렬 실행
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque
import pandas as pd

from strategy.long_strategy import LongStrategy
from strategy.short_strategy import ShortStrategy
from okx.position import SimplePositionManager
from utils.data_generator import convert_to_strategy_data, generate_strategy_data
from utils.indicators import calculate_ema
from utils.logger import log_system, log_error, log_info
from config import EMA_PERIODS

class RealTimeDataBuffer:
    """실시간 데이터 버퍼 (EMA 계산용)"""
    
    def __init__(self, symbol: str, max_candles: int = 300):
        self.symbol = symbol
        self.max_candles = max_candles
        
        # 실시간 가격 데이터 저장
        self.price_buffer = deque(maxlen=max_candles)
        self.last_candle_time = None
        self.current_candle = None
        
        # EMA 계산을 위한 DataFrame
        self._df_cache = None
        self._last_ema_calculation = None
        
        log_info(f"📊 실시간 데이터 버퍼 초기화: {symbol}")
    
    def add_price_data(self, price_data: Dict[str, Any]):
        """실시간 가격 데이터 추가 - 안전한 타입 변환"""
        try:
            timestamp = datetime.now()
            
            # 🔧 안전한 가격 추출 및 변환
            price_raw = price_data.get('close', price_data.get('last', 0))
            
            # 문자열인 경우 float으로 변환
            try:
                if isinstance(price_raw, str):
                    price = float(price_raw) if price_raw.strip() else 0.0
                else:
                    price = float(price_raw)
            except (ValueError, TypeError):
                log_error(f"가격 변환 실패 ({self.symbol}): {price_raw}")
                return
            
            # 유효하지 않은 가격 체크
            if price <= 0:
                log_error(f"유효하지 않은 가격 ({self.symbol}): {price}")
                return
            
            # 🔧 안전한 볼륨 추출 및 변환
            volume_raw = price_data.get('volume', price_data.get('vol24h', 0))
            try:
                if isinstance(volume_raw, str):
                    volume = float(volume_raw) if volume_raw.strip() else 0.0
                else:
                    volume = float(volume_raw)
            except (ValueError, TypeError):
                volume = 0.0
            
            # 30분 캔들 생성/업데이트
            candle_time = self._get_candle_time(timestamp)
            
            if self.last_candle_time != candle_time:
                # 새로운 캔들 시작
                if self.current_candle:
                    # 이전 캔들 완료
                    self.price_buffer.append(self.current_candle.copy())
                    self._invalidate_cache()
                
                # 새 캔들 시작
                self.current_candle = {
                    'timestamp': candle_time,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                }
                self.last_candle_time = candle_time
            else:
                # 기존 캔들 업데이트
                if self.current_candle:
                    self.current_candle['high'] = max(self.current_candle['high'], price)
                    self.current_candle['low'] = min(self.current_candle['low'], price)
                    self.current_candle['close'] = price
                    # 볼륨은 최신 값 사용 (또는 누적 가능)
                    self.current_candle['volume'] = volume
            
        except Exception as e:
            log_error(f"가격 데이터 추가 오류 ({self.symbol})", e)

    def _get_candle_time(self, timestamp: datetime) -> datetime:
        """30분 캔들 시간 계산"""
        # 30분 단위로 반올림
        minute = (timestamp.minute // 30) * 30
        return timestamp.replace(minute=minute, second=0, microsecond=0)
    
    def _invalidate_cache(self):
        """캐시 무효화"""
        self._df_cache = None
        self._last_ema_calculation = None
    
    def get_dataframe(self) -> Optional[pd.DataFrame]:
        """DataFrame 반환 (EMA 계산용)"""
        if len(self.price_buffer) < 10:
            return None
        
        # 캐시된 DataFrame 사용
        if self._df_cache is not None and len(self._df_cache) == len(self.price_buffer):
            return self._df_cache
        
        try:
            # DataFrame 생성
            df = pd.DataFrame(list(self.price_buffer))
            
            if len(df) < 10:
                return None
            
            # 시간순 정렬
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 캐시 저장
            self._df_cache = df
            return df
            
        except Exception as e:
            log_error(f"DataFrame 생성 오류 ({self.symbol})", e)
            return None
    
    def get_ema_data(self) -> Optional[Dict[str, Any]]:
        """EMA 계산된 전략 데이터 반환"""
        df = self.get_dataframe()
        if df is None or len(df) < max(EMA_PERIODS.values()) + 2:
            return None
        
        try:
            # EMA 계산
            for ema_name, period in EMA_PERIODS.items():
                if len(df) >= period:
                    df[f'ema_{ema_name}'] = calculate_ema(df['close'], period)
            
            # 전략용 데이터 생성
            strategy_data = generate_strategy_data(df, EMA_PERIODS)
            return strategy_data
            
        except Exception as e:
            log_error(f"EMA 데이터 생성 오류 ({self.symbol})", e)
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """버퍼 상태 정보"""
        return {
            'symbol': self.symbol,
            'candle_count': len(self.price_buffer),
            'current_candle': self.current_candle,
            'last_candle_time': self.last_candle_time,
            'has_enough_data': len(self.price_buffer) >= max(EMA_PERIODS.values()) + 2,
            'latest_price': self.current_candle['close'] if self.current_candle else None
        }

class ImprovedDualStrategyManager:
    """실시간 데이터 연동 듀얼 전략 관리자"""
    
    def __init__(self, total_capital: float = 10000, symbols: List[str] = None):
        self.total_capital = total_capital
        self.symbols = symbols or ['BTC-USDT-SWAP']
        
        # 자본 분배 (50:50)
        capital_per_strategy = total_capital * 0.5
        
        # 전략 인스턴스 생성
        self.strategies = {}
        for symbol in self.symbols:
            self.strategies[f"long_{symbol}"] = LongStrategy(symbol, capital_per_strategy)
            self.strategies[f"short_{symbol}"] = ShortStrategy(symbol, capital_per_strategy)
        
        # 실시간 데이터 버퍼
        self.data_buffers = {symbol: RealTimeDataBuffer(symbol) for symbol in self.symbols}
        
        # 포지션 관리자
        self.position_manager = SimplePositionManager()
        
        # 상태 추적
        self.start_time = datetime.now()
        self.total_signals_received = 0
        self.total_signals_processed = 0
        self.executed_trades = 0
        self.last_status_update = datetime.now()
        
        # 성능 통계
        self.performance_stats = {
            'ticker_updates': 0,
            'candle_updates': 0,
            'ema_calculations': 0,
            'strategy_signals': 0,
            'successful_trades': 0,
            'failed_trades': 0
        }
        
        log_system(f"🚀 실시간 듀얼 전략 관리자 초기화")
        log_system(f"총 자본: ${total_capital:,.0f} | 전략별: ${capital_per_strategy:,.0f}")
        log_system(f"대상 심볼: {', '.join(self.symbols)} | 활성 전략: {len(self.strategies)}개")
    
    def process_signal(self, symbol: str, raw_data: Dict[str, Any]) -> bool:
        """실시간 신호 처리 - 개선된 버전"""
        try:
            self.total_signals_received += 1
            
            # 데이터 타입 확인
            if 'close' in raw_data or 'last' in raw_data:
                # 실시간 가격 데이터 (Ticker)
                self._process_ticker_data(symbol, raw_data)
                return True
            
            elif all(k in raw_data for k in ['ema_trend_fast', 'ema_trend_slow']):
                # EMA 계산된 전략 데이터 (Candle 기반)
                return self._process_strategy_data(symbol, raw_data)
            
            else:
                # 기타 데이터 - 실시간 데이터 버퍼 업데이트
                if symbol in self.data_buffers:
                    self.data_buffers[symbol].add_price_data(raw_data)
                    
                    # EMA 기반 전략 신호 시도
                    return self._try_ema_strategy_signal(symbol)
            
            return False
            
        except Exception as e:
            log_error(f"신호 처리 오류 ({symbol})", e)
            self.performance_stats['failed_trades'] += 1
            return False
    
    def _process_ticker_data(self, symbol: str, ticker_data: Dict[str, Any]):
        """실시간 Ticker 데이터 처리 - 안전한 타입 변환"""
        try:
            self.performance_stats['ticker_updates'] += 1
            
            # 데이터 버퍼 업데이트
            if symbol in self.data_buffers:
                self.data_buffers[symbol].add_price_data(ticker_data)
            
            # 🔧 안전한 가격 추출 및 변환
            price_raw = ticker_data.get('close', ticker_data.get('last', 0))
            
            try:
                if isinstance(price_raw, str):
                    current_price = float(price_raw) if price_raw.strip() else 0.0
                else:
                    current_price = float(price_raw)
            except (ValueError, TypeError):
                log_error(f"Ticker 가격 변환 실패 ({symbol}): {price_raw}")
                return
            
            # 포지션 가격 업데이트
            if current_price > 0:
                self.position_manager.update_position_prices({symbol: current_price})
            
            # 주기적 로깅 (1000개마다)
            if self.performance_stats['ticker_updates'] % 1000 == 0:
                log_info(f"📊 {symbol} Ticker 업데이트: ${current_price:,.2f} ({self.performance_stats['ticker_updates']:,}건)")
            
        except Exception as e:
            log_error(f"Ticker 데이터 처리 오류 ({symbol})", e)


    def _process_strategy_data(self, symbol: str, strategy_data: Dict[str, Any]) -> bool:
        """EMA 계산된 전략 데이터 처리"""
        try:
            self.total_signals_processed += 1
            signals_generated = 0
            
            # 롱 전략 처리
            long_strategy_key = f"long_{symbol}"
            if long_strategy_key in self.strategies:
                long_data = convert_to_strategy_data(strategy_data, 'long')
                long_signal = self.strategies[long_strategy_key].process_signal(long_data)
                
                if long_signal:
                    self._execute_signal(long_signal)
                    signals_generated += 1
            
            # 숏 전략 처리
            short_strategy_key = f"short_{symbol}"
            if short_strategy_key in self.strategies:
                short_data = convert_to_strategy_data(strategy_data, 'short')
                short_signal = self.strategies[short_strategy_key].process_signal(short_data)
                
                if short_signal:
                    self._execute_signal(short_signal)
                    signals_generated += 1
            
            if signals_generated > 0:
                self.performance_stats['strategy_signals'] += signals_generated
                log_info(f"🎯 {symbol} 전략 신호 생성: {signals_generated}개")
            
            return signals_generated > 0
            
        except Exception as e:
            log_error(f"전략 데이터 처리 오류 ({symbol})", e)
            return False
    
    def _try_ema_strategy_signal(self, symbol: str) -> bool:
        """EMA 기반 전략 신호 시도"""
        try:
            if symbol not in self.data_buffers:
                return False
            
            # EMA 데이터 생성 시도
            ema_data = self.data_buffers[symbol].get_ema_data()
            if ema_data is None:
                return False
            
            self.performance_stats['ema_calculations'] += 1
            
            # 전략 신호 처리
            return self._process_strategy_data(symbol, ema_data)
            
        except Exception as e:
            log_error(f"EMA 전략 신호 시도 오류 ({symbol})", e)
            return False
    
    def _execute_signal(self, signal: Dict[str, Any]):
        """신호 실행 - 개선된 버전"""
        try:
            action = signal['action']
            symbol = signal['symbol']
            strategy_name = signal['strategy_name']
            
            if action.startswith('enter'):
                # 진입 신호
                is_real_mode = signal.get('is_real_mode', True)
                
                if is_real_mode:
                    # 실제 거래 모드
                    position_id = self.position_manager.open_position(
                        symbol=symbol,
                        side=signal['side'],
                        size=signal['size'],
                        leverage=signal['leverage'],
                        strategy_name=strategy_name,
                        trailing_stop_ratio=signal.get('trailing_stop_ratio')
                    )
                    
                    if position_id:
                        self.executed_trades += 1
                        self.performance_stats['successful_trades'] += 1
                        self._notify_signal(f"📈 실제 거래 진입", signal)
                    else:
                        self.performance_stats['failed_trades'] += 1
                        log_error(f"포지션 오픈 실패: {symbol}")
                else:
                    # 가상 거래 모드
                    log_info(f"🔄 {strategy_name} 가상 모드 진입: {symbol} {signal['side'].upper()}")
                    
            elif action.startswith('exit'):
                # 청산 신호
                is_real_mode = signal.get('is_real_mode', True)
                
                if is_real_mode:
                    # 실제 거래 청산
                    success = self.position_manager.close_position(
                        symbol, 
                        signal.get('reason', 'strategy')
                    )
                    
                    if success:
                        self.executed_trades += 1
                        self.performance_stats['successful_trades'] += 1
                        self._notify_signal(f"📉 실제 거래 청산", signal)
                    else:
                        self.performance_stats['failed_trades'] += 1
                        log_error(f"포지션 청산 실패: {symbol}")
                else:
                    # 가상 거래 청산
                    log_info(f"🔄 {strategy_name} 가상 모드 청산: {symbol} (사유: {signal.get('reason', 'strategy')})")
            
        except Exception as e:
            log_error("신호 실행 오류", e)
            self.performance_stats['failed_trades'] += 1
    
    def _notify_signal(self, title: str, signal: Dict[str, Any]):
        """신호 알림"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            symbol = signal.get('symbol', 'N/A')
            side = signal.get('side', 'N/A').upper()
            price = signal.get('price', signal.get('exit_price', 0))
            strategy = signal.get('strategy_name', 'Unknown')
            
            log_info(f"[{timestamp}] {title}")
            log_info(f"  📊 {symbol} {side} @ ${price:.2f} ({strategy})")
            
            if 'pnl' in signal:
                pnl = signal['pnl']
                pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
                log_info(f"  💰 PnL: {pnl_str}")
            
            if 'reason' in signal:
                log_info(f"  📝 사유: {signal['reason']}")
            
            # 실제 알림 시스템 연동 (있는 경우)
            try:
                from utils.notifications import send_trade_alert
                send_trade_alert(
                    action=signal.get('action', 'unknown'),
                    symbol=symbol,
                    side=side,
                    price=price,
                    size=signal.get('size', 0),
                    pnl=signal.get('pnl')
                )
            except ImportError:
                pass  # 알림 시스템 없음
            
        except Exception as e:
            log_error("신호 알림 오류", e)
    
    def get_strategy_status(self, strategy_key: str) -> Dict[str, Any]:
        """개별 전략 상태"""
        if strategy_key not in self.strategies:
            return {}
        
        return self.strategies[strategy_key].get_status()
    
    def get_data_buffer_status(self) -> Dict[str, Any]:
        """데이터 버퍼 상태"""
        status = {}
        
        for symbol, buffer in self.data_buffers.items():
            status[symbol] = buffer.get_status()
        
        return status
    
    def close_all_positions(self):
        """모든 포지션 강제 청산"""
        log_system("🛑 모든 포지션 청산 중...")
        self.position_manager.close_all_positions()
    
    def print_status(self):
        """현재 상태 출력 - 실시간 통계 포함"""
        current_time = datetime.now()
        runtime = current_time - self.start_time
        
        print(f"\n{'='*70}")
        print(f"🤖 실시간 듀얼 전략 시스템 상태")
        print(f"{'='*70}")
        print(f"실행 시간: {runtime}")
        print(f"수신 신호: {self.total_signals_received:,}개")
        print(f"처리 신호: {self.total_signals_processed:,}개")
        print(f"실행 거래: {self.executed_trades}건")
        
        # 성능 통계
        print(f"\n📊 처리 통계:")
        print(f"  Ticker 업데이트: {self.performance_stats['ticker_updates']:,}건")
        print(f"  캔들 업데이트: {self.performance_stats['candle_updates']:,}건")
        print(f"  EMA 계산: {self.performance_stats['ema_calculations']:,}회")
        print(f"  전략 신호: {self.performance_stats['strategy_signals']:,}개")
        print(f"  성공 거래: {self.performance_stats['successful_trades']:,}건")
        print(f"  실패 거래: {self.performance_stats['failed_trades']:,}건")
        
        # 데이터 버퍼 상태
        print(f"\n📈 데이터 버퍼 상태:")
        for symbol, status in self.get_data_buffer_status().items():
            candle_count = status['candle_count']
            latest_price = status['latest_price']
            has_data = "✅" if status['has_enough_data'] else "❌"
            
            price_str = f"${latest_price:.2f}" if latest_price else "N/A"
            print(f"  {symbol}: {candle_count}개 캔들, 최신가: {price_str} {has_data}")
        
        # 포지션 상태
        self.position_manager.print_status()
        
        # 전략별 상태
        print(f"\n📋 전략별 상태:")
        for strategy_key, strategy in self.strategies.items():
            status = strategy.get_status()
            mode = "🟢 실제" if status.get('is_real_mode', True) else "🔵 가상"
            capital = status.get('current_capital', 0)
            trades = status.get('trade_count', 0)
            win_rate = status.get('win_rate', 0)
            
            print(f"  {strategy_key}: {mode} | 자본: ${capital:.0f} | 거래: {trades}회 | 승률: {win_rate:.1f}%")
        
        self.last_status_update = current_time
        print(f"{'='*70}")
    
    def print_final_summary(self):
        """최종 요약 - 성능 통계 포함"""
        runtime = datetime.now() - self.start_time
        
        print(f"\n🏁 최종 실시간 거래 요약")
        print(f"=" * 50)
        print(f"총 실행 시간: {runtime}")
        print(f"수신된 신호: {self.total_signals_received:,}개")
        print(f"처리된 신호: {self.total_signals_processed:,}개")
        print(f"실행된 거래: {self.executed_trades}건")
        
        # 처리 효율성
        if self.total_signals_received > 0:
            processing_rate = (self.total_signals_processed / self.total_signals_received) * 100
            print(f"신호 처리율: {processing_rate:.1f}%")
        
        # 거래 성공률
        total_attempts = self.performance_stats['successful_trades'] + self.performance_stats['failed_trades']
        if total_attempts > 0:
            success_rate = (self.performance_stats['successful_trades'] / total_attempts) * 100
            print(f"거래 성공률: {success_rate:.1f}%")
        
        # 전략별 최종 자본
        total_final_capital = 0
        print(f"\n💰 전략별 최종 결과:")
        
        for strategy_key, strategy in self.strategies.items():
            status = strategy.get_status()
            final_capital = status.get('current_capital', 0)
            total_final_capital += final_capital
            
            initial_capital = self.total_capital * 0.5
            pnl = final_capital - initial_capital
            pnl_pct = (pnl / initial_capital) * 100 if initial_capital > 0 else 0
            
            print(f"  {strategy_key}: ${final_capital:.0f} ({pnl:+.0f}, {pnl_pct:+.1f}%)")
        
        total_pnl = total_final_capital - self.total_capital
        total_pnl_pct = (total_pnl / self.total_capital) * 100 if self.total_capital > 0 else 0
        
        print(f"=" * 50)
        print(f"초기 자본: ${self.total_capital:,.0f}")
        print(f"최종 자본: ${total_final_capital:,.0f}")
        print(f"총 손익: {total_pnl:+,.0f} ({total_pnl_pct:+.2f}%)")
        print(f"=" * 50)
    
    def is_healthy(self) -> bool:
        """시스템 건강 상태 확인"""
        try:
            # 기본 체크
            if not self.strategies:
                return False
            
            # 각 전략이 정상 작동하는지 확인
            for strategy in self.strategies.values():
                if not hasattr(strategy, 'get_status'):
                    return False
            
            # 데이터 버퍼 상태 확인
            for buffer in self.data_buffers.values():
                if buffer is None:
                    return False
            
            # 최근 신호 수신 확인 (5분 이내)
            if self.total_signals_received == 0:
                return True  # 시작 단계는 정상
            
            time_since_last_update = (datetime.now() - self.last_status_update).total_seconds()
            if time_since_last_update > 300:  # 5분
                return False
            
            return True
            
        except Exception:
            return False


# 기존 코드와의 호환성을 위한 래퍼
class DualStrategyManager(ImprovedDualStrategyManager):
    """기존 코드와의 호환성을 위한 래퍼"""
    pass