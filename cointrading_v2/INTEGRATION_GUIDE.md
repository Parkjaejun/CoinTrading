# CoinTrading v2 - Long Only 전략 통합 가이드

## 📋 개요

기존 GUI 프로젝트에 v2 알고리즘(Long Only + SignalPipeline + 이메일 알림)을 통합하기 위한 코드입니다.

### 주요 변경사항

| 항목 | 기존 | v2 |
|------|------|-----|
| **포지션** | Long + Short | **Long Only** |
| **디버깅** | 제한적 | **SignalPipeline** |
| **알림** | 없음 | **이메일 알림** |
| **인터페이스** | 동일 | 동일 (하위 호환) |

---

## 📁 파일 구조

```
cointrading_v2/
├── config.py                    # 설정 파일 (v2)
├── test_strategy.py             # 테스트 스크립트
├── strategy/
│   ├── __init__.py              # 패키지 초기화
│   ├── long_strategy.py         # Long 전략 v2 ⭐
│   ├── strategy_manager.py      # 전략 매니저 (Long Only)
│   ├── signal_pipeline.py       # 시그널 파이프라인 ⭐
│   └── email_notifier.py        # 이메일 알림 ⭐
└── utils/
    ├── __init__.py              # 패키지 초기화
    ├── data_generator.py        # 데이터 생성 유틸
    ├── price_buffer.py          # 가격 버퍼
    └── logger.py                # 로깅 유틸
```

---

## 🔧 기존 프로젝트에 적용하는 방법

### 방법 1: 폴더 복사 (권장)

1. `cointrading_v2/` 폴더 전체를 기존 프로젝트 루트에 복사

2. 기존 코드에서 import 변경:

```python
# 기존
from strategy.long_strategy import LongStrategy
from strategy.dual_manager import DualStrategyManager

# v2
from cointrading_v2.strategy import LongStrategy, StrategyManager
```

### 방법 2: 파일 교체

기존 프로젝트의 파일들을 직접 교체:

```
기존 파일                    →  v2 파일
strategy/long_strategy.py   →  cointrading_v2/strategy/long_strategy.py
strategy/dual_manager.py    →  cointrading_v2/strategy/strategy_manager.py
config.py                   →  cointrading_v2/config.py
```

신규 파일 추가:
```
cointrading_v2/strategy/signal_pipeline.py
cointrading_v2/strategy/email_notifier.py
```

---

## 📊 인터페이스 호환성

### 기존 인터페이스 (100% 호환)

```python
# 전략 초기화
strategy = LongStrategy(symbol="BTC-USDT-SWAP", initial_capital=10000.0)

# 시그널 처리 (동일한 인터페이스)
result = strategy.process_signal(data)

# 상태 조회 (동일한 인터페이스)
status = strategy.get_status()
```

### 데이터 형식 (동일)

```python
data = {
    'timestamp': datetime.now(),
    'close': 50000.0,
    'ema_trend_fast': 50100.0,    # 150 EMA
    'ema_trend_slow': 50000.0,    # 200 EMA
    'curr_entry_fast': 50050.0,   # 현재 20 EMA
    'curr_entry_slow': 50000.0,   # 현재 50 EMA
    'prev_entry_fast': 49950.0,   # 이전 20 EMA
    'prev_entry_slow': 50000.0,   # 이전 50 EMA
    'curr_exit_fast': 50050.0,    # 현재 20 EMA (청산용)
    'curr_exit_slow': 49900.0,    # 현재 100 EMA
    'prev_exit_fast': 49950.0,    # 이전 20 EMA (청산용)
    'prev_exit_slow': 49900.0,    # 이전 100 EMA
}
```

---

## 🆕 v2 추가 기능 사용법

### 1. 시그널 파이프라인

```python
from cointrading_v2.strategy import LongStrategy

strategy = LongStrategy(symbol="BTC", initial_capital=10000.0)

# 시그널 처리 후 파이프라인 확인
result = strategy.process_signal(data)

# 최근 시그널 조회
recent = strategy.pipeline.get_recent_signals(10)

# 차단된 진입 시그널 조회
blocked = strategy.pipeline.get_blocked_entries(10)

# 통계 조회
stats = strategy.pipeline.get_stats()
print(f"총 시그널: {stats['total_signals']}")
print(f"검증 통과: {stats['valid_signals']}")

# 요약 출력
strategy.pipeline.print_summary()
```

### 2. 이메일 알림

```python
from cointrading_v2.strategy import LongStrategy, EmailNotifier, MockEmailNotifier

# 실제 이메일 알림 (환경변수 설정 필요)
notifier = EmailNotifier()

# 테스트용 Mock 알림
notifier = MockEmailNotifier()

# 전략에 연결
strategy = LongStrategy(
    symbol="BTC",
    initial_capital=10000.0,
    email_notifier=notifier
)
```

### 3. 환경변수 설정 (이메일)

```bash
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export ALERT_EMAIL="your-email@gmail.com"
export ALERT_PASSWORD="your-app-password"
export RECIPIENT_EMAIL="recipient@example.com"
```

---

## 🧪 테스트 실행

```bash
cd cointrading_v2
python test_strategy.py
```

예상 출력:
```
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀
CoinTrading v2 전략 테스트
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀

✅ 테스트 1 통과! (기본 초기화)
✅ 테스트 2 통과! (시그널 파이프라인)
✅ 테스트 3 통과! (백테스트)
✅ 테스트 4 통과! (전략 매니저)

📊 테스트 결과: 4/4 통과
✅ 모든 테스트 통과!
```

---

## 📈 알고리즘 요약

### 진입 조건
```
1. 상승장: EMA 150 > EMA 200
2. 골든크로스: EMA 20이 EMA 50을 상향 돌파
```

### 청산 조건
```
1. 데드크로스: EMA 20이 EMA 100을 하향 돌파
2. 트레일링 스탑: 고점 대비 10% 하락
```

### 듀얼 모드
```
REAL → VIRTUAL: 고점 대비 20% 손실
VIRTUAL → REAL: 저점 대비 30% 회복
```

---

## ⚠️ 주의사항

1. **Short 전략 제거됨**: v2는 Long Only입니다.
2. **기존 데이터 호환**: 기존 `generate_strategy_data()` 함수와 호환됩니다.
3. **WebSocket 수정 불필요**: 기존 WebSocket 핸들러 그대로 사용 가능합니다.

---

## 📞 문의

문제가 있으면 테스트 스크립트를 먼저 실행해 보세요:
```bash
python test_strategy.py
```
