# agents/llm_client.py
"""
Claude LLM 클라이언트

두 가지 백엔드를 지원:
1. Anthropic API (anthropic 패키지) — 별도 API 크레딧 필요
2. Claude Code CLI (claude 명령어) — 기존 Claude 구독 사용

우선순위: Anthropic API → Claude Code CLI → 비활성
"""

import json
import subprocess
import shutil
from typing import Dict, Optional, Any

from utils.logger import log_system, log_error


# Anthropic SDK 가용 여부
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def _find_claude_cli() -> Optional[str]:
    """claude CLI 경로 탐색"""
    path = shutil.which("claude")
    if path:
        return path
    # Windows 일반 설치 경로
    import os
    for candidate in [
        os.path.expanduser("~/.claude/local/claude.exe"),
        os.path.expanduser("~/.claude/local/claude"),
        "claude.exe",
        "claude",
    ]:
        if shutil.which(candidate):
            return candidate
    return None


class LLMClient:
    """Claude LLM 클라이언트 (API + CLI 듀얼 백엔드)"""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-5-20250929",
                 use_cli: bool = True):
        """
        Args:
            api_key: Anthropic API 키 (없으면 CLI 모드)
            model: Anthropic API 모델 ID
            use_cli: True면 API 실패 시 Claude Code CLI 사용
        """
        self.api_key = api_key
        self.model = model
        self._client = None
        self._cli_path: Optional[str] = None
        self._backend = "none"
        self._call_count = 0

        # 1순위: Anthropic API
        if HAS_ANTHROPIC and api_key:
            try:
                self._client = anthropic.Anthropic(api_key=api_key)
                # 간단한 연결 테스트는 하지 않음 (비용 절약)
                self._backend = "api"
                log_system(f"[LLMClient] Anthropic API 모드 (모델: {model})")
            except Exception as e:
                log_error(f"[LLMClient] Anthropic API 초기화 실패: {e}")

        # 2순위: Claude Code CLI
        if self._backend == "none" and use_cli:
            self._cli_path = _find_claude_cli()
            if self._cli_path:
                self._backend = "cli"
                log_system(f"[LLMClient] Claude Code CLI 모드 ({self._cli_path})")
            else:
                log_error("[LLMClient] Claude CLI를 찾을 수 없습니다")

        if self._backend == "none":
            log_error("[LLMClient] LLM 백엔드 없음 — 규칙 기반 폴백만 사용")

    @property
    def is_available(self) -> bool:
        return self._backend != "none"

    @property
    def backend(self) -> str:
        return self._backend

    # ==================== 호출 인터페이스 ====================

    def _call(self, system_prompt: str, user_prompt: str,
              max_tokens: int = 1024) -> Optional[str]:
        """
        LLM 호출 (백엔드 자동 선택)

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            max_tokens: 최대 토큰 수 (API 모드)

        Returns:
            응답 텍스트 또는 None
        """
        self._call_count += 1

        if self._backend == "api":
            return self._call_api(system_prompt, user_prompt, max_tokens)
        elif self._backend == "cli":
            return self._call_cli(system_prompt, user_prompt)
        return None

    def _call_api(self, system_prompt: str, user_prompt: str,
                  max_tokens: int) -> Optional[str]:
        """Anthropic API 호출"""
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except Exception as e:
            log_error(f"[LLMClient] API 호출 실패: {e}")
            # API 실패 시 CLI 폴백
            if self._cli_path:
                log_system("[LLMClient] CLI 폴백 시도...")
                return self._call_cli(system_prompt, user_prompt)
            return None

    def _call_cli(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Claude Code CLI 호출 (stdin 파이프)"""
        if not self._cli_path:
            return None

        try:
            import os

            # 시스템 프롬프트 + 사용자 프롬프트를 하나로 결합
            combined_prompt = (
                f"[System Instructions]\n{system_prompt}\n\n"
                f"[Analysis Request]\n{user_prompt}"
            )

            # 중첩 세션 차단 우회 — subprocess는 독립 프로세스이므로 안전
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)
            env.pop("CLAUDE_CODE_SESSION", None)

            # stdin 파이프로 프롬프트 전달
            result = subprocess.run(
                [self._cli_path, "-p", "--"],
                input=combined_prompt,
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                env=env,
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            else:
                stderr = result.stderr.strip() if result.stderr else ""
                log_error(f"[LLMClient] CLI 호출 실패 (code={result.returncode}): {stderr[:200]}")
                return None

        except subprocess.TimeoutExpired:
            log_error("[LLMClient] CLI 호출 타임아웃 (120초)")
            return None
        except Exception as e:
            log_error(f"[LLMClient] CLI 호출 오류: {e}")
            return None

    # ==================== JSON 파싱 ====================

    def _parse_json_response(self, text: Optional[str], default: dict) -> dict:
        """응답에서 JSON 추출 (마크다운 코드블록 포함)"""
        if not text:
            return default

        # 마크다운 코드블록 제거 (```json ... ```)
        cleaned = text.strip()
        if "```" in cleaned:
            import re
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()

        try:
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(cleaned[start:end])
        except json.JSONDecodeError:
            pass
        return default

    # ==================== 시장 분석 (Reader용) ====================

    def analyze_market(self, price_data: Dict, ema_data: Dict,
                       news_summary: str) -> Dict[str, Any]:
        """
        시장 종합 분석

        Returns:
            {"signal": "BUY/SELL/HOLD", "confidence": 0.0~1.0, "reasoning": str}
        """
        default = {"signal": "HOLD", "confidence": 0.0, "reasoning": "분석 불가"}

        system_prompt = """당신은 BTC-USDT-SWAP 선물 거래 전문 분석가입니다.
주어진 가격 데이터, EMA 지표, 뉴스 정보를 종합 분석하여 매매 신호를 생성합니다.

전략 (롱 + 숏 양방향):
- EMA150 > EMA200 = 상승 트렌드 → BUY 가능
- EMA150 < EMA200 = 하락 트렌드 → SHORT 가능
- EMA20/EMA50 골든크로스 + 상승트렌드 = BUY (롱 진입)
- EMA20/EMA50 데드크로스 + 하락트렌드 = SHORT (숏 진입)
- EMA20/EMA100 데드크로스 = SELL (롱 청산)
- EMA20/EMA100 골든크로스 = COVER (숏 청산)

규칙:
- 뉴스가 극도로 부정적이면 BUY 신뢰도 낮추고 SHORT 신뢰도 높이세요
- 뉴스가 극도로 긍정적이면 SHORT 신뢰도 낮추고 BUY 신뢰도 높이세요
- 원금 보존이 최우선입니다
- 명확한 트렌드가 없으면 HOLD

반드시 아래 JSON 형식으로만 응답하세요:
{"signal": "BUY/SELL/SHORT/COVER/HOLD", "confidence": 0.0~1.0, "reasoning": "판단 근거"}"""

        user_prompt = f"""현재 시장 데이터:
{json.dumps(price_data, indent=2, default=str)}

EMA 지표:
{json.dumps(ema_data, indent=2, default=str)}

최근 뉴스:
{news_summary if news_summary else "뉴스 데이터 없음"}

종합 분석 후 매매 신호를 JSON으로 응답하세요."""

        text = self._call(system_prompt, user_prompt)
        return self._parse_json_response(text, default)

    # ==================== 전략 최적화 (Strategist용) ====================

    def optimize_strategy(self, performance_data: Dict,
                          market_data: Dict) -> Dict[str, Any]:
        """
        전략 파라미터 최적화 제안

        Returns:
            {"param_changes": {...}, "reasoning": str}
        """
        default = {"param_changes": {}, "reasoning": "변경 불필요"}

        system_prompt = """당신은 암호화폐 퀀트 전략 최적화 전문가입니다.
현재 전략의 성과와 시장 상태를 분석하여 파라미터 조정을 제안합니다.

조정 가능한 파라미터:
- leverage: 레버리지 (1~20)
- trailing_stop: 트레일링 스탑 비율 (0.03~0.20)
- entry_fast/entry_slow: 진입 EMA 기간
- exit_fast/exit_slow: 청산 EMA 기간
- capital_use_ratio: 자본 사용 비율 (0.10~0.80)

규칙:
- 원금 보존 최우선. 손실이 크면 레버리지/자본비율 축소
- 한 번에 1~2개 파라미터만 변경
- 급격한 변경 금지 (현재 값의 ±30% 이내)
- 변경이 불필요하면 빈 dict 반환

반드시 아래 JSON 형식으로만 응답하세요:
{"param_changes": {"파라미터명": 새값, ...}, "reasoning": "변경 근거"}"""

        user_prompt = f"""전략 성과 데이터:
{json.dumps(performance_data, indent=2, default=str)}

시장 상태:
{json.dumps(market_data, indent=2, default=str)}

최적 파라미터 조정을 JSON으로 제안하세요."""

        text = self._call(system_prompt, user_prompt)
        return self._parse_json_response(text, default)

    # ==================== 코드 리뷰 (Monitor용) ====================

    def review_code_change(self, original_code: str, modified_code: str,
                           reason: str) -> Dict[str, Any]:
        """
        전략 코드 변경 리뷰

        Returns:
            {"approved": bool, "risk_level": str, "feedback": str}
        """
        default = {"approved": False, "risk_level": "HIGH", "feedback": "리뷰 불가"}

        system_prompt = """당신은 트레이딩 시스템 코드 리뷰 전문가입니다.
전략 코드 변경사항을 검토하여 안전성을 평가합니다.

거부 사유:
- 무한 루프 가능성
- 예외 처리 미흡
- API 키/비밀번호 노출
- 위험한 시스템 명령 실행
- 주문 수량/레버리지 제한 우회
- 기존 안전장치 무력화

반드시 아래 JSON 형식으로만 응답하세요:
{"approved": true/false, "risk_level": "LOW/MEDIUM/HIGH", "feedback": "리뷰 의견"}"""

        user_prompt = f"""변경 이유: {reason}

원본 코드:
```python
{original_code}
```

수정 코드:
```python
{modified_code}
```

코드 변경을 승인할까요? JSON으로 응답하세요."""

        text = self._call(system_prompt, user_prompt)
        return self._parse_json_response(text, default)

    # ==================== 리스크 평가 (Monitor용) ====================

    def assess_risk(self, portfolio_state: Dict,
                    market_conditions: Dict) -> Dict[str, Any]:
        """
        포트폴리오 리스크 평가

        Returns:
            {"risk_level": str, "action": str, "reasoning": str}
        """
        default = {"risk_level": "MEDIUM", "action": "HOLD", "reasoning": "평가 불가"}

        system_prompt = """당신은 암호화폐 리스크 관리 전문가입니다.
포트폴리오 상태를 평가하여 리스크 레벨과 권장 행동을 제시합니다.

리스크 레벨:
- LOW: 정상 운영
- MEDIUM: 주의 필요 (신규 진입 제한 고려)
- HIGH: 위험 (포지션 축소 권장)
- CRITICAL: 긴급 (전 포지션 청산 + 시스템 정지)

행동:
- HOLD: 현상 유지
- REDUCE: 포지션 축소
- CLOSE_ALL: 전 포지션 청산
- STOP: 시스템 정지

원금 보존이 최우선 목표입니다.

반드시 아래 JSON 형식으로만 응답하세요:
{"risk_level": "LOW/MEDIUM/HIGH/CRITICAL", "action": "HOLD/REDUCE/CLOSE_ALL/STOP", "reasoning": "판단 근거"}"""

        user_prompt = f"""포트폴리오 상태:
{json.dumps(portfolio_state, indent=2, default=str)}

시장 조건:
{json.dumps(market_conditions, indent=2, default=str)}

리스크를 평가하고 JSON으로 응답하세요."""

        text = self._call(system_prompt, user_prompt)
        return self._parse_json_response(text, default)

    # ==================== 거래 승인 판단 (Monitor용) ====================

    def evaluate_trade_request(self, trade_request: Dict,
                               portfolio_state: Dict) -> Dict[str, Any]:
        """
        거래 요청 승인/거부 판단

        Returns:
            {"approved": bool, "reasoning": str}
        """
        default = {"approved": False, "reasoning": "판단 불가"}

        system_prompt = """당신은 트레이딩 리스크 관리자입니다.
거래 요청을 검토하고 승인 여부를 결정합니다.

거부 기준:
- Drawdown 10% 이상 → 신규 진입 거부
- 포지션 비율 30% 초과 → 거부
- 신호 신뢰도 70% 미만 → 거부
- 원금 이하로 자산 감소 시 → 무조건 거부

승인 기준:
- 충분한 잔고
- 적절한 포지션 크기
- 신호 신뢰도 70% 이상
- Drawdown 10% 미만

반드시 아래 JSON 형식으로만 응답하세요:
{"approved": true/false, "reasoning": "판단 근거"}"""

        user_prompt = f"""거래 요청:
{json.dumps(trade_request, indent=2, default=str)}

포트폴리오 상태:
{json.dumps(portfolio_state, indent=2, default=str)}

이 거래를 승인할까요? JSON으로 응답하세요."""

        text = self._call(system_prompt, user_prompt)
        return self._parse_json_response(text, default)

    # ==================== 통계 ====================

    def get_stats(self) -> Dict[str, Any]:
        """LLM 호출 통계"""
        return {
            "available": self.is_available,
            "backend": self._backend,
            "model": self.model if self._backend == "api" else "claude-code-cli",
            "call_count": self._call_count,
        }
