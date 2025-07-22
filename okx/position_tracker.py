"""
포지션 상태 추적 및 성과 분석
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd

@dataclass
class PositionRecord:
    """포지션 기록 데이터클래스"""
    position_id: str
    inst_id: str
    strategy_name: str
    side: str
    size: float
    entry_price: float
    exit_price: Optional[float]
    entry_time: datetime
    exit_time: Optional[datetime]
    leverage: float
    realized_pnl: Optional[float]
    unrealized_pnl: float
    max_unrealized_pnl: float
    min_unrealized_pnl: float
    peak_price: float
    trailing_stop_ratio: Optional[float]
    exit_reason: Optional[str]
    fees: float
    is_closed: bool
    duration_seconds: Optional[int]

class PositionTracker:
    """포지션 추적 및 성과 분석 클래스"""
    
    def __init__(self, db_path: str = "trading_history.db"):
        self.db_path = db_path
        self.position_records: Dict[str, PositionRecord] = {}
        self.daily_stats: Dict[str, dict] = {}
        
        # 데이터베이스 초기화
        self._init_database()
        
        # 기존 데이터 로드
        self._load_existing_data()
    
    def _init_database(self):
        """SQLite 데이터베이스 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 포지션 기록 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        position_id TEXT PRIMARY KEY,
                        inst_id TEXT NOT NULL,
                        strategy_name TEXT NOT NULL,
                        side TEXT NOT NULL,
                        size REAL NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        entry_time TEXT NOT NULL,
                        exit_time TEXT,
                        leverage REAL NOT NULL,
                        realized_pnl REAL,
                        unrealized_pnl REAL NOT NULL,
                        max_unrealized_pnl REAL NOT NULL,
                        min_unrealized_pnl REAL NOT NULL,
                        peak_price REAL NOT NULL,
                        trailing_stop_ratio REAL,
                        exit_reason TEXT,
                        fees REAL NOT NULL,
                        is_closed INTEGER NOT NULL,
                        duration_seconds INTEGER,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
                
                # 일일 통계 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        date TEXT PRIMARY KEY,
                        total_pnl REAL NOT NULL,
                        total_trades INTEGER NOT NULL,
                        winning_trades INTEGER NOT NULL,
                        losing_trades INTEGER NOT NULL,
                        win_rate REAL NOT NULL,
                        max_win REAL NOT NULL,
                        max_loss REAL NOT NULL,
                        avg_win REAL NOT NULL,
                        avg_loss REAL NOT NULL,
                        total_fees REAL NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
                
                # 인덱스 생성
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy_name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_date ON positions(entry_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_inst ON positions(inst_id)')
                
                conn.commit()
                print("데이터베이스 초기화 완료")
                
        except Exception as e:
            print(f"데이터베이스 초기화 오류: {e}")
    
    def _load_existing_data(self):
        """기존 데이터 로드"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 최근 30일 포지션 데이터 로드
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute('''
                    SELECT * FROM positions 
                    WHERE entry_time > ?
                    ORDER BY entry_time DESC
                ''', (thirty_days_ago,))
                
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                for row in rows:
                    data = dict(zip(columns, row))
                    position_record = PositionRecord(
                        position_id=data['position_id'],
                        inst_id=data['inst_id'],
                        strategy_name=data['strategy_name'],
                        side=data['side'],
                        size=data['size'],
                        entry_price=data['entry_price'],
                        exit_price=data['exit_price'],
                        entry_time=datetime.fromisoformat(data['entry_time']),
                        exit_time=datetime.fromisoformat(data['exit_time']) if data['exit_time'] else None,
                        leverage=data['leverage'],
                        realized_pnl=data['realized_pnl'],
                        unrealized_pnl=data['unrealized_pnl'],
                        max_unrealized_pnl=data['max_unrealized_pnl'],
                        min_unrealized_pnl=data['min_unrealized_pnl'],
                        peak_price=data['peak_price'],
                        trailing_stop_ratio=data['trailing_stop_ratio'],
                        exit_reason=data['exit_reason'],
                        fees=data['fees'],
                        is_closed=bool(data['is_closed']),
                        duration_seconds=data['duration_seconds']
                    )
                    self.position_records[data['position_id']] = position_record
                
                print(f"기존 포지션 데이터 로드: {len(self.position_records)}개")
                
        except Exception as e:
            print(f"데이터 로드 오류: {e}")
    
    def add_position(self, position_id: str, inst_id: str, strategy_name: str,
                    side: str, size: float, entry_price: float, leverage: float,
                    trailing_stop_ratio: Optional[float] = None):
        """새 포지션 추가"""
        position_record = PositionRecord(
            position_id=position_id,
            inst_id=inst_id,
            strategy_name=strategy_name,
            side=side,
            size=size,
            entry_price=entry_price,
            exit_price=None,
            entry_time=datetime.now(),
            exit_time=None,
            leverage=leverage,
            realized_pnl=None,
            unrealized_pnl=0.0,
            max_unrealized_pnl=0.0,
            min_unrealized_pnl=0.0,
            peak_price=entry_price,
            trailing_stop_ratio=trailing_stop_ratio,
            exit_reason=None,
            fees=0.0,
            is_closed=False,
            duration_seconds=None
        )
        
        self.position_records[position_id] = position_record
        self._save_position(position_record)
        
        print(f"포지션 추적 시작: {position_id}")
    
    def update_position(self, position_id: str, current_price: float, 
                       unrealized_pnl: float, fees: float = 0.0):
        """포지션 상태 업데이트"""
        if position_id not in self.position_records:
            return
        
        record = self.position_records[position_id]
        if record.is_closed:
            return
        
        # 미실현 PnL 업데이트
        record.unrealized_pnl = unrealized_pnl
        record.fees = fees
        
        # 최대/최소 미실현 PnL 추적
        if unrealized_pnl > record.max_unrealized_pnl:
            record.max_unrealized_pnl = unrealized_pnl
        if unrealized_pnl < record.min_unrealized_pnl:
            record.min_unrealized_pnl = unrealized_pnl
        
        # 피크 가격 업데이트
        if record.side == 'long' and current_price > record.peak_price:
            record.peak_price = current_price
        elif record.side == 'short' and current_price < record.peak_price:
            record.peak_price = current_price
        
        # 데이터베이스 업데이트
        self._save_position(record)
    
    def close_position(self, position_id: str, exit_price: float, 
                      realized_pnl: float, exit_reason: str, fees: float = 0.0):
        """포지션 청산"""
        if position_id not in self.position_records:
            return
        
        record = self.position_records[position_id]
        
        record.exit_price = exit_price
        record.exit_time = datetime.now()
        record.realized_pnl = realized_pnl
        record.exit_reason = exit_reason
        record.fees += fees
        record.is_closed = True
        
        # 포지션 지속 시간 계산
        if record.entry_time and record.exit_time:
            duration = record.exit_time - record.entry_time
            record.duration_seconds = int(duration.total_seconds())
        
        # 데이터베이스 업데이트
        self._save_position(record)
        
        # 일일 통계 업데이트
        self._update_daily_stats(record)
        
        print(f"포지션 청산 기록: {position_id} - PnL: {realized_pnl:.2f}")
    
    def _save_position(self, record: PositionRecord):
        """포지션 기록을 데이터베이스에 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO positions (
                        position_id, inst_id, strategy_name, side, size,
                        entry_price, exit_price, entry_time, exit_time,
                        leverage, realized_pnl, unrealized_pnl,
                        max_unrealized_pnl, min_unrealized_pnl, peak_price,
                        trailing_stop_ratio, exit_reason, fees, is_closed,
                        duration_seconds, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.position_id, record.inst_id, record.strategy_name,
                    record.side, record.size, record.entry_price, record.exit_price,
                    record.entry_time.isoformat(), 
                    record.exit_time.isoformat() if record.exit_time else None,
                    record.leverage, record.realized_pnl, record.unrealized_pnl,
                    record.max_unrealized_pnl, record.min_unrealized_pnl, record.peak_price,
                    record.trailing_stop_ratio, record.exit_reason, record.fees,
                    int(record.is_closed), record.duration_seconds,
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            print(f"포지션 저장 오류: {e}")
    
    def _update_daily_stats(self, record: PositionRecord):
        """일일 통계 업데이트"""
        if not record.is_closed or not record.realized_pnl:
            return
        
        date_str = record.exit_time.date().isoformat()
        
        # 해당 날짜 통계 조회/생성
        if date_str not in self.daily_stats:
            self.daily_stats[date_str] = {
                'total_pnl': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'max_win': 0.0,
                'max_loss': 0.0,
                'total_fees': 0.0,
                'wins': [],
                'losses': []
            }
        
        stats = self.daily_stats[date_str]
        stats['total_pnl'] += record.realized_pnl
        stats['total_trades'] += 1
        stats['total_fees'] += record.fees
        
        if record.realized_pnl > 0:
            stats['winning_trades'] += 1
            stats['wins'].append(record.realized_pnl)
            stats['max_win'] = max(stats['max_win'], record.realized_pnl)
        else:
            stats['losing_trades'] += 1
            stats['losses'].append(abs(record.realized_pnl))
            stats['max_loss'] = max(stats['max_loss'], abs(record.realized_pnl))
        
        # 승률 계산
        stats['win_rate'] = stats['winning_trades'] / stats['total_trades'] if stats['total_trades'] > 0 else 0
        stats['avg_win'] = sum(stats['wins']) / len(stats['wins']) if stats['wins'] else 0
        stats['avg_loss'] = sum(stats['losses']) / len(stats['losses']) if stats['losses'] else 0
        
        # 데이터베이스 저장
        self._save_daily_stats(date_str, stats)
    
    def _save_daily_stats(self, date_str: str, stats: dict):
        """일일 통계를 데이터베이스에 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_stats (
                        date, total_pnl, total_trades, winning_trades,
                        losing_trades, win_rate, max_win, max_loss,
                        avg_win, avg_loss, total_fees, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date_str, stats['total_pnl'], stats['total_trades'],
                    stats['winning_trades'], stats['losing_trades'], stats['win_rate'],
                    stats['max_win'], stats['max_loss'], stats['avg_win'],
                    stats['avg_loss'], stats['total_fees'],
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            print(f"일일 통계 저장 오류: {e}")
    
    def get_performance_summary(self, days: int = 30) -> dict:
        """성과 요약 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 기간별 데이터 조회
                start_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                # 전체 통계
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(realized_pnl) as total_pnl,
                        AVG(realized_pnl) as avg_pnl,
                        MAX(realized_pnl) as max_win,
                        MIN(realized_pnl) as max_loss,
                        SUM(fees) as total_fees,
                        AVG(duration_seconds) as avg_duration
                    FROM positions 
                    WHERE is_closed = 1 AND exit_time > ?
                ''', (start_date,))
                
                overall_stats = cursor.fetchone()
                
                # 전략별 통계
                cursor.execute('''
                    SELECT 
                        strategy_name,
                        COUNT(*) as trades,
                        SUM(realized_pnl) as pnl,
                        AVG(realized_pnl) as avg_pnl,
                        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins
                    FROM positions 
                    WHERE is_closed = 1 AND exit_time > ?
                    GROUP BY strategy_name
                ''', (start_date,))
                
                strategy_stats = cursor.fetchall()
                
                # 일별 통계
                cursor.execute('''
                    SELECT date, total_pnl, total_trades, win_rate
                    FROM daily_stats 
                    WHERE date > ?
                    ORDER BY date DESC
                ''', (start_date[:10],))
                
                daily_stats = cursor.fetchall()
                
                return {
                    'period_days': days,
                    'overall': {
                        'total_trades': overall_stats[0] or 0,
                        'winning_trades': overall_stats[1] or 0,
                        'win_rate': (overall_stats[1] or 0) / (overall_stats[0] or 1),
                        'total_pnl': overall_stats[2] or 0.0,
                        'avg_pnl': overall_stats[3] or 0.0,
                        'max_win': overall_stats[4] or 0.0,
                        'max_loss': overall_stats[5] or 0.0,
                        'total_fees': overall_stats[6] or 0.0,
                        'avg_duration_minutes': (overall_stats[7] or 0) / 60
                    },
                    'by_strategy': [
                        {
                            'strategy': row[0],
                            'trades': row[1],
                            'pnl': row[2],
                            'avg_pnl': row[3],
                            'wins': row[4],
                            'win_rate': row[4] / row[1] if row[1] > 0 else 0
                        } for row in strategy_stats
                    ],
                    'daily': [
                        {
                            'date': row[0],
                            'pnl': row[1],
                            'trades': row[2],
                            'win_rate': row[3]
                        } for row in daily_stats
                    ]
                }
                
        except Exception as e:
            print(f"성과 요약 조회 오류: {e}")
            return {}
    
    def export_to_csv(self, filename: str = None, days: int = 30) -> str:
        """CSV 파일로 내보내기"""
        if not filename:
            filename = f"trading_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                start_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                df = pd.read_sql_query('''
                    SELECT * FROM positions 
                    WHERE entry_time > ?
                    ORDER BY entry_time DESC
                ''', conn, params=(start_date,))
                
                df.to_csv(filename, index=False)
                print(f"거래 기록 내보내기 완료: {filename}")
                return filename
                
        except Exception as e:
            print(f"CSV 내보내기 오류: {e}")
            return ""
    
    def print_performance_report(self, days: int = 7):
        """성과 보고서 출력"""
        summary = self.get_performance_summary(days)
        
        if not summary:
            print("성과 데이터가 없습니다.")
            return
        
        overall = summary['overall']
        
        print(f"\n{'='*50}")
        print(f"거래 성과 보고서 (최근 {days}일)")
        print(f"{'='*50}")
        print(f"총 거래수: {overall['total_trades']}")
        print(f"승리 거래: {overall['winning_trades']}")
        print(f"승률: {overall['win_rate']*100:.1f}%")
        print(f"총 PnL: {overall['total_pnl']:.2f} USDT")
        print(f"평균 PnL: {overall['avg_pnl']:.2f} USDT")
        print(f"최대 수익: {overall['max_win']:.2f} USDT")
        print(f"최대 손실: {overall['max_loss']:.2f} USDT")
        print(f"총 수수료: {overall['total_fees']:.2f} USDT")
        print(f"평균 거래 시간: {overall['avg_duration_minutes']:.1f}분")
        
        if summary['by_strategy']:
            print(f"\n전략별 성과:")
            for strategy in summary['by_strategy']:
                print(f"  {strategy['strategy']}: "
                      f"{strategy['trades']}건, "
                      f"PnL {strategy['pnl']:.2f}, "
                      f"승률 {strategy['win_rate']*100:.1f}%")
        
        if summary['daily']:
            print(f"\n일별 성과 (최근 5일):")
            for daily in summary['daily'][:5]:
                print(f"  {daily['date']}: "
                      f"PnL {daily['pnl']:.2f}, "
                      f"{daily['trades']}건, "
                      f"승률 {daily['win_rate']*100:.1f}%")
        
        print(f"{'='*50}")

    def get_active_positions(self) -> List[PositionRecord]:
        """활성 포지션 목록"""
        return [record for record in self.position_records.values() if not record.is_closed]