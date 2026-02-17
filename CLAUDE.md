# CLAUDE.md - OKX 비트코인 자동매매 시스템

## 프로젝트 개요

OKX 거래소 API를 이용한 비트코인(BTC-USDT-SWAP) 자동매매 봇.
Python + PyQt5 기반이며, EMA 크로스 전략과 듀얼 모드(Real/Virtual) 자본 관리를 사용한다.

## 실행 방법

```bash
# GUI 모드 (메인)
python run_gui.py

# CLI 모드 (실제 거래)
python main.py

# 페이퍼 트레이딩 (가상 자금)
python main.py --paper-trading --virtual-balance 10000

# 잔액 확인만
python main.py --check-balance

# 백테스트
python main.py --backtest long --start-date 2025-01-01 --end-date 2025-12-31
```

## 프로젝트 구조

```
CoinTrading/
├── main.py                  # CLI 진입점 (TradingSystem)
├── run_gui.py               # GUI 진입점 (PyQt5)
├── config.py                # 통합 설정 + API 유틸리티 함수
├── trading_engine.py        # 멀티 타임프레임 매매 엔진
├── quiet_logger.py          # 포지션 조회 로그 숨김
├── terminal_dashboard.py    # 터미널 대시보드
│
├── gui/                     # PyQt5 GUI 컴포넌트
│   ├── main_window.py       #   메인 윈도우
│   ├── auto_trading_widget.py #  자동매매 위젯
│   ├── dashboard_chart_widget.py # 차트 위젯
│   ├── settings_dialog.py   #   설정 다이얼로그
│   ├── balance_manager.py   #   잔고 관리
│   ├── v2_strategy_widget.py #  v2 전략 위젯
│   ├── v2_strategy_bridge.py #  v2 전략 브릿지
│   └── ...
│
├── okx/                     # OKX 거래소 연동
│   ├── account_manager.py   #   계정 관리
│   ├── order_manager.py     #   주문 관리
│   ├── real_order_manager.py #  실주문 관리
│   ├── websocket_handler.py #   WebSocket 실시간 데이터
│   ├── historical_data_loader.py # 과거 데이터 로딩
│   ├── connection_manager.py #  연결 관리
│   └── ...
│
├── strategy/                # 매매 전략
│   ├── dual_manager.py      #   듀얼(Real/Virtual) 전략 매니저
│   ├── real_only_strategy_manager.py # 실거래 전용
│   └── short_strategy.py    #   숏 전략 (DEPRECATED)
│
├── cointrading_v2/          # v2 트레이딩 엔진 (Long Only)
│   ├── trading_engine_v2.py #   v2 엔진
│   ├── realtime_trader_v2.py #  실시간 트레이더
│   ├── signal_pipeline.py   #   신호 파이프라인
│   ├── backtest_v2.py       #   v2 백테스트
│   ├── email_notifier.py    #   이메일 알림
│   └── debug_logger.py      #   디버그 로거
│
├── simulation/              # 시뮬레이션 모듈
│   ├── simulation_main.py
│   ├── strategy_adapter.py
│   └── virtual_order_manager.py
│
├── simulation_gui/          # 시뮬레이션 GUI
│   └── sim_main_window.py
│
├── backtest_project/        # 독립 백테스트 프로젝트
│   ├── main.py
│   ├── backtest/
│   └── backtest_gui/
│
├── utils/                   # 유틸리티
│   ├── logger.py            #   로깅 (log_system, log_error, log_info)
│   ├── notifications.py     #   알림 (이메일 등)
│   ├── data_loader.py       #   데이터 로더
│   ├── indicators.py        #   기술적 지표
│   ├── balance_util.py      #   잔액 유틸리티
│   └── price_buffer.py      #   가격 버퍼
│
├── data/                    # 시장 데이터 저장소
├── logs/                    # 로그 파일
├── cache/                   # 캐시
└── temp/                    # 임시 파일
```

## 핵심 아키텍처

### 매매 전략 (EMA 크로스)
- **트렌드 판단**: 30분봉 EMA150 vs EMA200
- **진입 신호**: 1분봉 EMA20 vs EMA50 크로스
- **청산 신호**: 트레일링 스탑 또는 1분봉 EMA20 vs EMA100 역크로스
- **기본 전략**: Long Only (숏 전략은 DEPRECATED)

### 듀얼 모드 자본 관리
- **Real 모드**: 실제 거래 실행
- **Virtual 모드**: 시뮬레이션만 (실주문 없음)
- 자동 전환: 손실 20% → Virtual, 회복 30% → Real

### 데이터 플로우
```
OKX WebSocket → websocket_handler → strategy_manager → order_manager → OKX API
                    ↓
              price_buffer (30m/1m)
                    ↓
              EMA 계산 → 신호 생성 → 주문 실행
```

## 설정 (config.py)

모든 설정은 `config.py`에 중앙 관리된다:
- `TRADING_CONFIG`: 거래 기본 설정 (심볼, 레버리지, 자본 등)
- `EMA_PERIODS`: EMA 기간 설정
- `LONG_STRATEGY_CONFIG`: Long 전략 상세 설정
- `WEBSOCKET_CONFIG`: WebSocket 연결 설정
- `NOTIFICATION_CONFIG`: 알림 설정 (이메일)
- `GUI_CONFIG`: GUI 윈도우 설정

API 키는 환경변수 또는 config.py 직접 설정:
- `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_PASSPHRASE`

## 코딩 컨벤션

- **언어**: 코드는 Python, 주석/docstring/로그 메시지는 한국어
- **GUI**: PyQt5 사용, 다크 테마 기본
- **로깅**: `utils/logger.py`의 `log_system`, `log_error`, `log_info` 사용
- **API 호출**: `config.py`의 `make_api_request()` 함수를 통해 통일
- **에러 처리**: try/except로 감싸고, `log_error`로 기록
- **타입 힌트**: `typing` 모듈 사용 (Dict, Optional, List 등)
- **이모지**: 로그 메시지에 이모지 사용 관례 있음 (✅ ❌ 🚀 📊 등)

## 주의사항

- `config.py`에 API 키와 이메일 비밀번호가 하드코딩되어 있음. 변경 시 주의
- Short 전략(`short_strategy.py`, `SHORT_STRATEGY_CONFIG`)은 DEPRECATED
- `cointrading_v2/`는 v2 엔진으로, 기존 `trading_engine.py`와 별도 동작
- `install.cmd`는 Claude Code 설치 스크립트로 프로젝트와 무관
- WebSocket 연결은 `wss://ws.okx.com:8443/ws/v5/` 사용
- 거래 대상: `BTC-USDT-SWAP` (비트코인 무기한 선물)
- 기본 레버리지: 10배 (Long)
