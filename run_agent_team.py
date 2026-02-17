# run_agent_team.py
"""
자율 매매 에이전트 팀 CLI 진입점

4개 에이전트 (Reader, Trader, Strategist, Monitor)를 시작하고
터미널 대시보드로 상태를 표시한다.

사용법:
    python run_agent_team.py                  # 실거래 모드
    python run_agent_team.py --dry-run        # 주문 없이 테스트
    python run_agent_team.py --capital 200    # 초기 자본 지정
"""

import sys
import os
import time
import signal
import argparse
from datetime import datetime

# 프로젝트 루트를 PATH에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import validate_config, test_api_connection, TRADING_CONFIG
from utils.logger import log_system, log_error, log_info

from agents.agent_config import AGENT_TEAM_CONFIG
from agents.message_bus import MessageBus
from agents.state_manager import StateManager
from agents.llm_client import LLMClient
from agents.news_fetcher import NewsFetcher
from agents.strategy_modifier import StrategyModifier
from agents.reader_agent import ReaderAgent
from agents.trader_agent import TraderAgent
from agents.strategist_agent import StrategistAgent
from agents.monitor_agent import MonitorAgent

from okx.order_manager import OrderManager


def parse_args():
    parser = argparse.ArgumentParser(description="자율 매매 에이전트 팀")
    parser.add_argument("--dry-run", action="store_true",
                        help="실제 주문 없이 테스트 모드 실행")
    parser.add_argument("--capital", type=float, default=None,
                        help="초기 자본 (USDT). 미지정 시 config.py 값 사용")
    parser.add_argument("--no-llm", action="store_true",
                        help="Claude API 미사용 (기술적 분석만)")
    parser.add_argument("--symbol", type=str, default="BTC-USDT-SWAP",
                        help="거래 심볼 (기본: BTC-USDT-SWAP)")
    return parser.parse_args()


def print_banner():
    print("=" * 60)
    print("🤖 자율 매매 에이전트 팀 v1.0")
    print("=" * 60)
    print("  📊 Reader   — 시세 & 뉴스 분석")
    print("  💰 Trader   — 자율 매매 집행")
    print("  🧠 Strategist — 전략 최적화")
    print("  🛡️ Monitor  — 리스크 관리 & 승인")
    print("=" * 60)


def print_status(state_manager, agents, message_bus):
    """터미널 대시보드 출력"""
    status = state_manager.get_team_status()
    bus_stats = message_bus.get_stats()

    print("\n" + "─" * 60)
    print(f"  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  💵 자산: ${status['current_equity']:,.2f}  |  "
          f"PnL: ${status['current_pnl']:+,.2f}  |  "
          f"누적: ${status['cumulative_profit']:+,.2f}")
    print(f"  📉 Drawdown: {status['drawdown_pct']:.1%}  |  "
          f"포지션: {status['open_positions']}개  |  "
          f"거래: {status['total_trades']}건")
    print(f"  💲 BTC: ${status['current_price']:,.0f}  |  "
          f"메시지: {bus_stats['total_messages']}건")
    params = status.get("strategy_params", {})
    print(f"  ⚙️ 레버리지: {params.get('leverage', '?')}x  |  "
          f"자본사용: {params.get('capital_use_ratio', '?')}  |  "
          f"트레일링: {params.get('trailing_stop', '?')}")

    # 긴급 상태
    if status["emergency_stop"]:
        print(f"  🚨 긴급 정지: {status['emergency_reason']}")
    elif status["entry_blocked"]:
        print(f"  ⚠️ 신규 진입 차단 중")

    # 에이전트 상태
    agent_status = []
    for agent in agents:
        s = agent.get_status()
        emoji = "🟢" if s["running"] else "🔴"
        err = f" ⚠️{s['last_error'][:20]}" if s["last_error"] else ""
        agent_status.append(f"{emoji}{s['name']}(#{s['cycle_count']}{err})")
    print(f"  에이전트: {' | '.join(agent_status)}")
    print("─" * 60)


def main():
    args = parse_args()
    print_banner()

    # 설정 적용
    if args.dry_run:
        AGENT_TEAM_CONFIG["dry_run"] = True
        print("🏷️  DRY-RUN 모드 (실제 주문 없음)")

    if args.symbol:
        AGENT_TEAM_CONFIG["symbol"] = args.symbol

    initial_capital = args.capital or 70.0  # 현재 계좌 자산 기준

    # ==================== 1. 설정 검증 ====================
    print("\n📋 설정 검증 중...")

    if not validate_config():
        print("❌ API 설정 검증 실패")
        sys.exit(1)

    if not args.dry_run:
        print("🔌 OKX API 연결 테스트...")
        if not test_api_connection():
            print("❌ API 연결 실패. --dry-run으로 테스트해보세요.")
            sys.exit(1)

    # Claude LLM 확인 (API 키 또는 CLI)
    use_llm = not args.no_llm
    api_key = AGENT_TEAM_CONFIG.get("claude_api_key", "")
    if use_llm:
        if api_key:
            print(f"🧠 Claude API 키 확인 (모델: {AGENT_TEAM_CONFIG['claude_model']})")
        else:
            print("🧠 Claude Code CLI 모드로 LLM 사용")
    else:
        print("⚠️ LLM 미사용 (--no-llm) — 기술적 분석만")

    # ==================== 2. 컴포넌트 초기화 ====================
    print("\n🔧 컴포넌트 초기화...")

    message_bus = MessageBus()
    log_system("MessageBus 초기화 완료")

    state_manager = StateManager(
        initial_capital=initial_capital,
        symbol=args.symbol,
        dry_run=args.dry_run,
    )
    log_system(f"StateManager 초기화 완료 (초기 자본: ${initial_capital:,.2f})")

    # 초기 잔고/포지션 갱신
    if not args.dry_run:
        state_manager.refresh_balance()
        state_manager.refresh_positions()
        state_manager.refresh_price()
        equity = state_manager.get_current_equity()
        price = state_manager.get_current_price()
        positions = state_manager.get_positions()
        print(f"  💵 현재 자산: ${equity:,.2f}")
        print(f"  💲 BTC 가격: ${price:,.0f}")
        if positions:
            print(f"  ⚠️ 기존 포지션 {len(positions)}개 발견:")
            for pos in positions:
                print(f"     {pos['inst_id']} {pos['pos_side']} "
                      f"{pos['position']}계약 (UPL: ${pos['upl']:+,.2f})")

    llm_client = LLMClient(
        api_key=api_key if use_llm else "",
        model=AGENT_TEAM_CONFIG.get("claude_model", "claude-sonnet-4-5-20250929"),
        use_cli=use_llm,
    )

    news_fetcher = NewsFetcher()

    strategy_modifier = StrategyModifier(
        state_manager=state_manager,
        backup_dir="agents/backups",
        allowed_paths=AGENT_TEAM_CONFIG.get("allowed_code_paths", []),
    )

    order_manager = OrderManager(verbose=False) if not args.dry_run else None

    # ==================== 3. 에이전트 생성 ====================
    print("\n🤖 에이전트 생성...")

    monitor = MonitorAgent(
        message_bus=message_bus,
        state_manager=state_manager,
        llm_client=llm_client,
        strategy_modifier=strategy_modifier,
        order_manager=order_manager,
    )

    reader = ReaderAgent(
        message_bus=message_bus,
        state_manager=state_manager,
        llm_client=llm_client,
        news_fetcher=news_fetcher,
    )

    trader = TraderAgent(
        message_bus=message_bus,
        state_manager=state_manager,
        llm_client=llm_client,
        order_manager=order_manager,
    )

    strategist = StrategistAgent(
        message_bus=message_bus,
        state_manager=state_manager,
        llm_client=llm_client,
        strategy_modifier=strategy_modifier,
    )

    agents = [monitor, reader, trader, strategist]
    print(f"  ✅ {len(agents)}개 에이전트 생성 완료")

    # ==================== 4. 에이전트 시작 ====================
    print("\n🚀 에이전트 팀 시작!\n")

    # Monitor 먼저 시작 (안전장치 우선)
    monitor.start()
    time.sleep(0.5)

    reader.start()
    trader.start()
    strategist.start()

    # ==================== 5. 메인 루프 ====================
    # 종료 시그널 핸들러
    shutdown_flag = False

    def signal_handler(sig, frame):
        nonlocal shutdown_flag
        shutdown_flag = True
        print("\n\n🛑 종료 신호 수신...")

    signal.signal(signal.SIGINT, signal_handler)

    status_interval = 30  # 30초마다 상태 출력
    last_status = 0

    try:
        while not shutdown_flag:
            now = time.time()
            if now - last_status >= status_interval:
                # 잔고/가격 갱신
                if not args.dry_run:
                    state_manager.refresh_balance()
                    state_manager.refresh_price()

                print_status(state_manager, agents, message_bus)
                last_status = now

                # 목표 달성 확인
                profit = state_manager.get_cumulative_profit()
                if profit >= AGENT_TEAM_CONFIG.get("target_profit", 1000):
                    print(f"\n🎯🎯🎯 목표 수익 달성! ${profit:,.2f} 🎯🎯🎯")

            time.sleep(1)

    except KeyboardInterrupt:
        pass

    # ==================== 6. 안전 종료 ====================
    print("\n🛑 에이전트 팀 종료 중...")

    for agent in agents:
        agent.stop()

    # 포지션 확인
    if not args.dry_run:
        positions = state_manager.get_positions()
        if positions:
            print(f"\n⚠️ 보유 포지션 {len(positions)}개 — 수동 확인 필요:")
            for pos in positions:
                print(f"  {pos['inst_id']} {pos['pos_side']} "
                      f"{pos['position']}계약 (PnL: ${pos['upl']:+,.2f})")

    # 최종 상태
    status = state_manager.get_team_status()
    print(f"\n📊 최종 상태:")
    print(f"  자산: ${status['current_equity']:,.2f}")
    print(f"  PnL: ${status['current_pnl']:+,.2f}")
    print(f"  누적 수익: ${status['cumulative_profit']:+,.2f}")
    print(f"  총 거래: {status['total_trades']}건")
    print(f"  Drawdown: {status['drawdown_pct']:.1%}")

    bus_stats = message_bus.get_stats()
    print(f"  메시지: {bus_stats['total_messages']}건")

    print("\n✅ 종료 완료")


if __name__ == "__main__":
    main()
