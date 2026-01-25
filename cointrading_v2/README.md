# CoinTrading v2

Long Only 암호화폐 자동 트레이딩 시스템

## 🎯 주요 변경사항 (v1 → v2)

| 항목 | v1 | v2 |
|------|----|----|
| 포지션 | Long + Short | **Long Only** |
| 시그널 처리 | 단일 함수 | **파이프라인 기반** |
| 디버깅 | 제한적 | **상세 로깅 + 추적** |
| 알림 | 없음 | **이메일 알림** |

## 📁 파일 구조

```
cointrading_v2/
├── __init__.py           # 패키지 초기화
├── config_v2.py          # 설정 (파라미터, 이메일)
├── models.py             # 데이터 모델 (Trade, Position, Signal 등)
├── signal_pipeline.py    # 시그널 파이프라인
├── trading_engine_v2.py  # 트레이딩 엔진
├── backtest_v2.py        # 백테스트 모듈
├── realtime_trader_v2.py # 실시간 트레이딩
├── email_notifier.py     # 이메일 알림
├── debug_logger.py       # 디버그 로거
└── run_test.py           # 테스트 스크립트
```

## 🚀 빠른 시작

### 1. 백테스트 실행

```python
from cointrading_v2 import run_backtest, ParamsV2

# 기본 설정으로 백테스트
results = run_backtest("BTCUSDT_30m.csv", initial_capital=10000)

# 커스텀 파라미터
params = ParamsV2(
    leverage=10.0,
    trailing_stop=0.10,
    stop_loss_ratio=0.20,
    reentry_gain_ratio=0.30,
)
results = run_backtest("BTCUSDT_30m.csv", params=params)
```

### 2. 상세 백테스트

```python
from cointrading_v2 import BacktestV2, ParamsV2

bt = BacktestV2(
    params=ParamsV2(enable_debug_logging=True),
    initial_capital=10000.0,
)

results = bt.run(csv_path="data.csv", print_trades=True)

# Equity curve
equity_df = bt.get_equity_dataframe()

# 거래 내역
trades_df = bt.get_trades_dataframe()
```

### 3. 실시간 시뮬레이션

```python
from cointrading_v2 import RealtimeTraderV2, RealtimeSimulator

trader = RealtimeTraderV2(
    symbol="BTC-USDT-SWAP",
    initial_capital=10000.0,
    dry_run=True,  # 실제 주문 없음
)

simulator = RealtimeSimulator(trader)
simulator.run_from_csv("data.csv", speed=0)  # 즉시 실행
```

## ⚙️ 파라미터 설명

```python
@dataclass
class ParamsV2:
    # EMA 기간
    trend_fast: int = 150       # 트렌드 빠른 EMA
    trend_slow: int = 200       # 트렌드 느린 EMA
    entry_fast: int = 20        # 진입 빠른 EMA
    entry_slow: int = 50        # 진입 느린 EMA
    exit_fast: int = 20         # 청산 빠른 EMA
    exit_slow: int = 100        # 청산 느린 EMA
    
    # 거래 설정
    leverage: float = 10.0      # 레버리지
    trailing_stop: float = 0.10 # 트레일링 스탑 (10%)
    
    # 듀얼 모드 설정
    stop_loss_ratio: float = 0.20    # REAL→VIRTUAL (고점 -20%)
    reentry_gain_ratio: float = 0.30 # VIRTUAL→REAL (저점 +30%)
    
    # 자본 설정
    capital_use_ratio: float = 0.50  # 자본 사용 비율
    fee_rate_per_side: float = 0.0005 # 수수료 (편도)
```

## 📧 이메일 알림 설정

### 환경변수 (.env)

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
ALERT_EMAIL=your_email@gmail.com
ALERT_PASSWORD=your_app_password  # Gmail 앱 비밀번호
RECIPIENT_EMAIL=recipient@example.com
```

### 코드에서 설정

```python
from cointrading_v2 import EmailConfig, EmailNotifier

config = EmailConfig(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    sender_email="your@gmail.com",
    sender_password="app_password",
    recipient_email="recipient@email.com",
    notify_on_entry=True,
    notify_on_exit=True,
    notify_on_mode_switch=True,
)

notifier = EmailNotifier(config)
notifier.test_connection()  # 연결 테스트
```

## 🔍 디버깅 기능

### 시그널 파이프라인 상태

```python
# 파이프라인 상태 확인
status = engine.pipeline.get_status()
print(status['stats'])  # 시그널 통계
print(status['rejection_reasons'])  # 거부 이유

# 최근 시그널
signals = engine.pipeline.get_recent_signals(10)

# 차단된 진입 시그널
blocked = engine.pipeline.get_blocked_entries(10)
```

### 디버그 로거

```python
from cointrading_v2 import DebugLogger

logger = DebugLogger(
    name="MyTrader",
    log_to_file=True,
    log_dir="logs",
)

logger.log_signal(signal.to_dict())
logger.log_trade(trade.to_dict())
logger.log_mode_switch("REAL", "VIRTUAL", "stop_loss")
```

## 📊 듀얼 모드 로직

```
[REAL 모드]
├── 실제 자본으로 거래
├── real_peak 대비 -20% 하락 → VIRTUAL 전환
└── 전환 시 virtual_capital = 10000 리셋

[VIRTUAL 모드]
├── 가상 자본으로 모의 거래 (시장 적합도 평가)
├── virtual_trough 대비 +30% 상승 → REAL 복귀
└── 복귀 시 virtual_capital = 10000 리셋
```

## 📈 진입/청산 조건

### 진입 조건 (LONG)
1. **트렌드**: EMA 150 > EMA 200 (상승장)
2. **진입 신호**: EMA 20이 EMA 50 상향 돌파 (골든크로스)

### 청산 조건
1. **EMA 청산**: EMA 20이 EMA 100 하향 돌파 (데드크로스)
2. **트레일링 스탑**: 고점 대비 -10% 하락

## 🧪 테스트 실행

```bash
# 기본 테스트
python run_test.py

# CSV 파일로 테스트
python run_test.py /path/to/BTCUSDT_30m.csv

# 백테스트만 실행
python backtest_v2.py /path/to/data.csv
```

## 📝 CSV 파일 형식

```csv
timestamp,open,high,low,close
2024-01-01 00:00:00,42000,42500,41800,42300
2024-01-01 00:30:00,42300,42800,42100,42600
...
```

지원 타임스탬프 형식:
- ISO 8601: `2024-01-01T00:00:00Z`
- Unix (초): `1704067200`
- Unix (밀리초): `1704067200000`

## 🔧 의존성

```
pandas>=1.3.0
numpy>=1.21.0
```

선택적:
```
websocket-client>=1.3.0  # 실시간 트레이딩
```

## 📄 라이센스

MIT License
