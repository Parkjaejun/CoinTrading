# agents/reader_agent.py
"""
Agent 1: Reader (시세 & 뉴스 분석)

역할:
- 1분봉/30분봉 데이터 수집 (OKX REST API)
- EMA 지표 계산
- 뉴스 수집 (NewsFetcher)
- Claude API로 종합 분석
- 매매 신호 생성 및 Message Bus 발행
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List

import pandas as pd

from agents.base_agent import BaseAgent
from agents.message_bus import MSG_SIGNAL
from agents.agent_config import AGENT_TEAM_CONFIG
from config import make_api_request, EMA_PERIODS
from utils.logger import log_system, log_error


class ReaderAgent(BaseAgent):
    """시세 & 뉴스 분석 에이전트"""

    def __init__(self, message_bus, state_manager, llm_client, news_fetcher):
        """
        Args:
            message_bus: MessageBus 인스턴스
            state_manager: StateManager 인스턴스
            llm_client: LLMClient 인스턴스
            news_fetcher: NewsFetcher 인스턴스
        """
        interval = AGENT_TEAM_CONFIG.get("reader_interval", 60)
        super().__init__("reader", message_bus, state_manager, llm_client, interval)

        self._news_fetcher = news_fetcher
        self._symbol = AGENT_TEAM_CONFIG.get("symbol", "BTC-USDT-SWAP")
        self._min_confidence = AGENT_TEAM_CONFIG.get("min_signal_confidence", 0.7)

        # EMA 기간
        self._ema_periods = {
            "trend_fast": EMA_PERIODS.get("trend_fast", 150),
            "trend_slow": EMA_PERIODS.get("trend_slow", 200),
            "entry_fast": EMA_PERIODS.get("entry_fast", 20),
            "entry_slow": EMA_PERIODS.get("entry_slow", 50),
            "exit_fast": EMA_PERIODS.get("exit_fast", 20),
            "exit_slow": EMA_PERIODS.get("exit_slow", 100),
        }

        # 메시지 구독 (Reader는 주로 발행만 하지만 STATUS 수신)
        self.message_bus.subscribe("reader", ["STATUS", "EMERGENCY_STOP"])

    def run_cycle(self) -> None:
        """Reader 사이클: 데이터 수집 → EMA 계산 → 분석 → 신호 발행"""
        # 1. 현재가 갱신
        self.state_manager.refresh_price()
        price = self.state_manager.get_current_price()
        if price <= 0:
            self.log("⚠️ 가격 데이터 없음 — 사이클 건너뜀")
            return

        # 2. 캔들 데이터 수집
        candles_30m = self._fetch_candles("30m", limit=210)
        candles_1m = self._fetch_candles("1m", limit=110)

        if not candles_30m or not candles_1m:
            self.log("⚠️ 캔들 데이터 수집 실패")
            return

        # 3. EMA 계산
        ema_data = self._calculate_emas(candles_30m, candles_1m)

        # 4. 가격 데이터 정리
        price_data = self._build_price_data(price, candles_1m, candles_30m)

        # 5. 뉴스 수집
        news_summary = ""
        try:
            news_summary = self._news_fetcher.get_sentiment_summary()
        except Exception as e:
            self.log(f"뉴스 수집 실패 (계속 진행): {e}")

        # 6. 기술적 신호 판단 (코드 기반)
        technical_signal = self._evaluate_technical_signal(ema_data)

        # 7. LLM 종합 분석
        llm_signal = None
        if self.llm_client and self.llm_client.is_available:
            llm_signal = self.llm_client.analyze_market(price_data, ema_data, news_summary)

        # 8. 최종 신호 결합
        final_signal = self._combine_signals(technical_signal, llm_signal)

        # 9. 신호 발행
        if final_signal["signal"] != "HOLD":
            self.log(
                f"📊 신호 발행: {final_signal['signal']} "
                f"(신뢰도: {final_signal['confidence']:.2f}) "
                f"— {final_signal['reasoning']}"
            )
            self.send_message(MSG_SIGNAL, {
                "signal": final_signal["signal"],
                "confidence": final_signal["confidence"],
                "reasoning": final_signal["reasoning"],
                "price": price,
                "ema_data": ema_data,
                "timestamp": datetime.now().isoformat(),
            })
        else:
            if self._cycle_count % 5 == 0:  # 5사이클마다 HOLD 로그
                self.log(f"📊 HOLD (신뢰도: {final_signal['confidence']:.2f})")

    # ==================== 캔들 데이터 수집 ====================

    def _fetch_candles(self, timeframe: str, limit: int = 200) -> Optional[List[Dict]]:
        """OKX REST API에서 캔들 데이터 조회"""
        try:
            bar_map = {"1m": "1m", "30m": "30m", "1H": "1H", "4H": "4H"}
            bar = bar_map.get(timeframe, timeframe)

            result = make_api_request(
                "GET", "/api/v5/market/candles",
                params={
                    "instId": self._symbol,
                    "bar": bar,
                    "limit": str(limit),
                }
            )
            if result and result.get("code") == "0":
                candles = []
                for item in reversed(result.get("data", [])):
                    # [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                    candles.append({
                        "timestamp": int(item[0]),
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    })
                return candles
        except Exception as e:
            log_error(f"[Reader] 캔들 조회 실패 ({timeframe}): {e}")
        return None

    # ==================== EMA 계산 ====================

    def _calculate_emas(self, candles_30m: List[Dict],
                        candles_1m: List[Dict]) -> Dict[str, Any]:
        """EMA 지표 계산"""
        result = {}

        # 30분봉 EMA (트렌드 판단)
        df_30m = pd.DataFrame(candles_30m)
        if len(df_30m) >= self._ema_periods["trend_slow"]:
            for key in ["trend_fast", "trend_slow"]:
                period = self._ema_periods[key]
                ema = df_30m["close"].ewm(span=period, adjust=False).mean()
                result[f"ema_{key}"] = ema.iloc[-1]
                if len(ema) >= 2:
                    result[f"ema_{key}_prev"] = ema.iloc[-2]

        # 1분봉 EMA (진입/청산 판단)
        df_1m = pd.DataFrame(candles_1m)
        if len(df_1m) >= self._ema_periods["exit_slow"]:
            for key in ["entry_fast", "entry_slow", "exit_fast", "exit_slow"]:
                period = self._ema_periods[key]
                ema = df_1m["close"].ewm(span=period, adjust=False).mean()
                result[f"ema_{key}"] = ema.iloc[-1]
                if len(ema) >= 2:
                    result[f"ema_{key}_prev"] = ema.iloc[-2]

        return result

    # ==================== 기술적 신호 판단 ====================

    def _evaluate_technical_signal(self, ema_data: Dict) -> Dict[str, Any]:
        """EMA 기반 기술적 신호 판단 (롱 + 숏)"""
        signal = {"signal": "HOLD", "confidence": 0.0, "reasoning": ""}
        reasons = []

        # 필수 데이터 확인
        trend_fast = ema_data.get("ema_trend_fast")
        trend_slow = ema_data.get("ema_trend_slow")
        entry_fast = ema_data.get("ema_entry_fast")
        entry_slow = ema_data.get("ema_entry_slow")
        exit_fast = ema_data.get("ema_exit_fast")
        exit_slow = ema_data.get("ema_exit_slow")

        if None in (trend_fast, trend_slow):
            signal["reasoning"] = "트렌드 EMA 데이터 부족"
            return signal

        # 트렌드 판단
        is_uptrend = trend_fast > trend_slow
        is_downtrend = trend_fast < trend_slow
        reasons.append(f"트렌드: {'상승' if is_uptrend else '하락'} (EMA150={trend_fast:.0f} vs EMA200={trend_slow:.0f})")

        # 현재 포지션 방향
        pos_dir = self.state_manager.get_position_direction()

        # EMA 크로스 상태 계산
        golden_cross = False
        dead_cross_entry = False
        dead_cross_exit = False
        is_above = False
        is_below = False

        if entry_fast is not None and entry_slow is not None:
            entry_fast_prev = ema_data.get("ema_entry_fast_prev", entry_fast)
            entry_slow_prev = ema_data.get("ema_entry_slow_prev", entry_slow)
            golden_cross = (entry_fast_prev <= entry_slow_prev * 1.001) and (entry_fast >= entry_slow * 0.999)
            dead_cross_entry = (entry_fast_prev >= entry_slow_prev * 0.999) and (entry_fast <= entry_slow * 1.001)
            is_above = entry_fast > entry_slow
            is_below = entry_fast < entry_slow

        if exit_fast is not None and exit_slow is not None:
            exit_fast_prev = ema_data.get("ema_exit_fast_prev", exit_fast)
            exit_slow_prev = ema_data.get("ema_exit_slow_prev", exit_slow)
            dead_cross_exit = (exit_fast_prev >= exit_slow_prev) and (exit_fast < exit_slow)
            golden_cross_exit = (exit_fast_prev <= exit_slow_prev) and (exit_fast > exit_slow)
        else:
            golden_cross_exit = False

        # ==================== 롱 포지션 청산 ====================
        if pos_dir == "long":
            if dead_cross_exit:
                signal["signal"] = "SELL"
                signal["confidence"] = 0.85
                reasons.append(f"롱 청산: 데드크로스 (EMA20={exit_fast:.0f} < EMA100={exit_slow:.0f})")
            elif is_downtrend:
                signal["signal"] = "SELL"
                signal["confidence"] = 0.75
                reasons.append("롱 청산: 트렌드 하락 전환")

        # ==================== 숏 포지션 청산 ====================
        elif pos_dir == "short":
            if golden_cross_exit:
                signal["signal"] = "COVER"
                signal["confidence"] = 0.85
                reasons.append(f"숏 청산: 골든크로스 (EMA20={exit_fast:.0f} > EMA100={exit_slow:.0f})")
            elif is_uptrend:
                signal["signal"] = "COVER"
                signal["confidence"] = 0.75
                reasons.append("숏 청산: 트렌드 상승 전환")

        # ==================== 신규 진입 ====================
        elif pos_dir == "none":
            # 롱 진입: 상승 트렌드 + 골든크로스
            if is_uptrend and golden_cross:
                signal["signal"] = "BUY"
                signal["confidence"] = 0.85
                reasons.append(f"롱 진입: 골든크로스 (EMA20={entry_fast:.0f} > EMA50={entry_slow:.0f})")
            # 숏 진입: 하락 트렌드 + 데드크로스
            elif is_downtrend and dead_cross_entry:
                signal["signal"] = "SHORT"
                signal["confidence"] = 0.85
                reasons.append(f"숏 진입: 데드크로스 (EMA20={entry_fast:.0f} < EMA50={entry_slow:.0f})")
            # 정보성 로그
            elif is_uptrend and is_above:
                signal["confidence"] = 0.5
                reasons.append("매수 대기 (EMA20 > EMA50, 크로스 대기)")
            elif is_downtrend and is_below:
                signal["confidence"] = 0.5
                reasons.append("숏 대기 (EMA20 < EMA50, 크로스 대기)")

        signal["reasoning"] = " | ".join(reasons)
        return signal

    # ==================== 신호 결합 ====================

    def _combine_signals(self, technical: Dict, llm: Optional[Dict]) -> Dict[str, Any]:
        """기술적 신호와 LLM 분석 결합"""
        if not llm:
            return technical

        tech_signal = technical.get("signal", "HOLD")
        llm_signal = llm.get("signal", "HOLD")
        tech_conf = technical.get("confidence", 0.0)
        llm_conf = llm.get("confidence", 0.0)

        # 청산 신호 (SELL/COVER)는 기술적 분석이 최우선
        # 포지션 보호가 LLM 판단보다 중요
        if tech_signal in ("SELL", "COVER"):
            return technical

        # 둘 다 같은 신호 → 신뢰도 상승
        if tech_signal == llm_signal:
            combined_conf = min(1.0, (tech_conf + llm_conf) / 2 + 0.1)
            return {
                "signal": tech_signal,
                "confidence": combined_conf,
                "reasoning": f"[기술] {technical['reasoning']} | [LLM] {llm.get('reasoning', '')}",
            }

        # LLM이 청산 신호 → LLM 우선 (리스크 관리)
        if llm_signal in ("SELL", "COVER"):
            return {
                "signal": llm_signal,
                "confidence": llm_conf * 0.9,
                "reasoning": f"[LLM] 청산 신호 우선 적용",
            }

        # 그 외: 높은 신뢰도 선택
        if tech_conf >= llm_conf:
            return technical
        return llm

    # ==================== 유틸리티 ====================

    def _build_price_data(self, current_price: float,
                          candles_1m: List[Dict],
                          candles_30m: List[Dict]) -> Dict[str, Any]:
        """가격 데이터 정리"""
        data = {
            "current_price": current_price,
            "symbol": self._symbol,
            "timestamp": datetime.now().isoformat(),
        }

        # 1분봉 변동률
        if candles_1m and len(candles_1m) >= 2:
            prev_close = candles_1m[-2]["close"]
            data["change_1m_pct"] = (current_price - prev_close) / prev_close * 100

        # 30분봉 변동률
        if candles_30m and len(candles_30m) >= 2:
            prev_close_30m = candles_30m[-2]["close"]
            data["change_30m_pct"] = (current_price - prev_close_30m) / prev_close_30m * 100

        # 24시간 고저
        if candles_30m and len(candles_30m) >= 48:
            recent_48 = candles_30m[-48:]
            data["high_24h"] = max(c["high"] for c in recent_48)
            data["low_24h"] = min(c["low"] for c in recent_48)

        return data
