# backtest/result_analyzer.py
"""
백테스트 결과 분석 모듈
- 통계 계산
- 보고서 생성
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import pandas as pd

from .backtest_engine import BacktestResult, Trade


@dataclass
class TradeStats:
    """거래 통계"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    total_pnl: float
    total_fees: float
    net_pnl: float
    
    avg_profit: float
    avg_loss: float
    profit_factor: float
    
    max_profit: float
    max_loss: float
    
    avg_holding_bars: float
    max_consecutive_wins: int
    max_consecutive_losses: int


class ResultAnalyzer:
    """백테스트 결과 분석기"""
    
    def __init__(self, result: BacktestResult):
        self.result = result
    
    def calculate_trade_stats(self, mode: str = "ALL") -> TradeStats:
        """
        거래 통계 계산
        
        Args:
            mode: "ALL", "REAL", "VIRTUAL"
        """
        trades = self.result.trades
        
        if mode != "ALL":
            trades = [t for t in trades if t.mode == mode]
        
        if not trades:
            return TradeStats(
                total_trades=0, winning_trades=0, losing_trades=0, win_rate=0,
                total_pnl=0, total_fees=0, net_pnl=0,
                avg_profit=0, avg_loss=0, profit_factor=0,
                max_profit=0, max_loss=0,
                avg_holding_bars=0, max_consecutive_wins=0, max_consecutive_losses=0
            )
        
        winning = [t for t in trades if t.net_pnl > 0]
        losing = [t for t in trades if t.net_pnl <= 0]
        
        total_pnl = sum(t.pnl for t in trades)
        total_fees = sum(t.fee for t in trades)
        net_pnl = sum(t.net_pnl for t in trades)
        
        avg_profit = sum(t.net_pnl for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.net_pnl for t in losing) / len(losing) if losing else 0
        
        gross_profit = sum(t.net_pnl for t in winning)
        gross_loss = abs(sum(t.net_pnl for t in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        max_profit = max((t.net_pnl for t in trades), default=0)
        max_loss = min((t.net_pnl for t in trades), default=0)
        
        # 연속 승/패
        max_cons_wins, max_cons_losses = self._calculate_consecutive(trades)
        
        # 평균 보유 기간
        avg_holding = sum(t.holding_bars for t in trades) / len(trades)
        
        return TradeStats(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(trades) * 100 if trades else 0,
            total_pnl=total_pnl,
            total_fees=total_fees,
            net_pnl=net_pnl,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_profit=max_profit,
            max_loss=max_loss,
            avg_holding_bars=avg_holding,
            max_consecutive_wins=max_cons_wins,
            max_consecutive_losses=max_cons_losses,
        )
    
    def _calculate_consecutive(self, trades: List[Trade]) -> tuple:
        """연속 승/패 계산"""
        if not trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        curr_wins = 0
        curr_losses = 0
        
        for t in trades:
            if t.net_pnl > 0:
                curr_wins += 1
                curr_losses = 0
                max_wins = max(max_wins, curr_wins)
            else:
                curr_losses += 1
                curr_wins = 0
                max_losses = max(max_losses, curr_losses)
        
        return max_wins, max_losses
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """거래 내역을 DataFrame으로 반환"""
        if not self.result.trades:
            return pd.DataFrame()
        
        data = []
        for i, t in enumerate(self.result.trades, 1):
            data.append({
                "#": i,
                "방향": t.side,
                "모드": t.mode,
                "진입시간": t.entry_time,
                "청산시간": t.exit_time,
                "진입가": t.entry_price,
                "청산가": t.exit_price,
                "수익률(%)": t.pnl_percentage,
                "순손익": t.net_pnl,
                "수수료": t.fee,
                "청산사유": t.reason_exit,
            })
        
        return pd.DataFrame(data)
    
    def get_equity_dataframe(self) -> pd.DataFrame:
        """자산곡선을 DataFrame으로 반환"""
        data = []
        for (t_r, v_r), (t_v, v_v) in zip(
            self.result.equity_curve_real, 
            self.result.equity_curve_virtual
        ):
            data.append({
                "time": t_r,
                "real_capital": v_r,
                "virtual_capital": v_v,
            })
        return pd.DataFrame(data)
    
    def generate_summary_text(self) -> str:
        """요약 텍스트 생성"""
        r = self.result
        stats_all = self.calculate_trade_stats("ALL")
        stats_real = self.calculate_trade_stats("REAL")
        stats_virtual = self.calculate_trade_stats("VIRTUAL")
        
        lines = [
            "=" * 60,
            "백테스트 결과 요약",
            "=" * 60,
            "",
            f"초기 자본: ${r.initial_capital:,.2f}",
            f"최종 REAL 자본: ${r.final_real_capital:,.2f}",
            f"최종 VIRTUAL 자본: ${r.final_virtual_capital:,.2f}",
            "",
            "--- 수익률 ---",
            f"REAL ROI: {r.real_roi:+.2f}%",
            f"VIRTUAL ROI: {r.virtual_roi:+.2f}%",
            f"REAL MDD: -{r.mdd_real:.2f}%",
            f"VIRTUAL MDD: -{r.mdd_virtual:.2f}%",
            "",
            "--- 거래 통계 ---",
            f"총 거래 수: {stats_all.total_trades} (REAL: {stats_real.total_trades}, VIRTUAL: {stats_virtual.total_trades})",
            f"승률: {stats_all.win_rate:.1f}%",
            f"승: {stats_all.winning_trades}, 패: {stats_all.losing_trades}",
            f"손익비: {stats_all.profit_factor:.2f}",
            "",
            f"평균 수익: ${stats_all.avg_profit:+.2f}",
            f"평균 손실: ${stats_all.avg_loss:+.2f}",
            f"최대 수익: ${stats_all.max_profit:+.2f}",
            f"최대 손실: ${stats_all.max_loss:+.2f}",
            "",
            f"총 수수료: ${stats_all.total_fees:.2f}",
            f"순손익: ${stats_all.net_pnl:+.2f}",
            "",
            "--- 모드 전환 ---",
            f"REAL→VIRTUAL: {r.r2v_switches}회",
            f"VIRTUAL→REAL: {r.v2r_switches}회",
            "",
            f"연속 최대 승: {stats_all.max_consecutive_wins}",
            f"연속 최대 패: {stats_all.max_consecutive_losses}",
            "",
            f"진행중 포지션: {'있음' if r.has_open_position else '없음'}",
            "=" * 60,
        ]
        
        return "\n".join(lines)
    
    def get_summary_dict(self) -> Dict[str, Any]:
        """요약 정보를 딕셔너리로 반환 (GUI용)"""
        r = self.result
        stats = self.calculate_trade_stats("ALL")
        
        return {
            "initial_capital": r.initial_capital,
            "final_real_capital": r.final_real_capital,
            "final_virtual_capital": r.final_virtual_capital,
            "real_roi": r.real_roi,
            "virtual_roi": r.virtual_roi,
            "mdd_real": r.mdd_real,
            "mdd_virtual": r.mdd_virtual,
            "total_trades": stats.total_trades,
            "real_trades": r.real_trades,
            "virtual_trades": r.virtual_trades,
            "win_rate": stats.win_rate,
            "winning_trades": stats.winning_trades,
            "losing_trades": stats.losing_trades,
            "profit_factor": stats.profit_factor,
            "avg_profit": stats.avg_profit,
            "avg_loss": stats.avg_loss,
            "max_profit": stats.max_profit,
            "max_loss": stats.max_loss,
            "total_fees": stats.total_fees,
            "net_pnl": stats.net_pnl,
            "r2v_switches": r.r2v_switches,
            "v2r_switches": r.v2r_switches,
            "max_consecutive_wins": stats.max_consecutive_wins,
            "max_consecutive_losses": stats.max_consecutive_losses,
            "has_open_position": r.has_open_position,
        }
