# CoinTrading - OKX 자동매매 시스템

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Development-orange.svg)

**OKX 거래소를 위한 전문적인 암호화폐 자동매매 시스템**

EMA 기반의 듀얼 트레이딩 전략(롱/숏)을 실시간으로 실행하며, 포지션 관리, 트레일링 스탑, 위험 관리 등 완전한 자동매매 기능을 제공합니다.

## 📋 목차

- [주요 기능](#-주요-기능)
- [시스템 구조](#-시스템-구조)
- [설치 및 설정](#-설치-및-설정)
- [API 설정](#-api-설정)
- [사용법](#-사용법)
- [전략 설명](#-전략-설명)
- [모니터링](#-모니터링)
- [백테스팅](#-백테스팅)
- [보안 및 위험관리](#-보안-및-위험관리)
- [문제해결](#-문제해결)
- [기여하기](#-기여하기)

## 🚀 주요 기능

### 🔄 자동매매 전략
- **듀얼 전략 시스템**: 롱 전략 + 숏 전략 병렬 실행
- **EMA 기반 신호**: 150/200/20/50/100 EMA 조합으로 정교한 진입/청산
- **트레일링 스탑**: 수익 보호를 위한 동적 손절매
- **위험 관리**: MDD 제한, 자동 거래 중단/재개

### 📊 포지션 관리
- **실시간 포지션 추적**: 모든 포지션의 실시간 PnL 모니터링
- **자동 청산**: 손절/익절/트레일링 스탑 자동 실행
- **레버리지 관리**: 전략별 차별화된 레버리지 적용
- **다중 포지션**: 여러 전략과 심볼의 동시 관리

### 🔔 알림 시스템
- **실시간 알림**: 매수/매도/청산 시 즉시 알림
- **다중 채널**: 텔레그램, 슬랙, 이메일 지원
- **상세 정보**: 진입가, 청산가, PnL, 청산 사유 포함

### 📈 성과 분석
- **거래 기록**: 모든 거래의 상세 기록 저장
- **성과 지표**: 승률, 평균 수익, MDD, 샤프 비율
- **일별/전략별 분석**: 세분화된 성과 분석
- **CSV 내보내기**: 외부 분석 도구 연동

## 🏗️ 시스템 구조

```
CoinTrading/
├── main.py                     # 메인 실행 파일
├── config.py                   # 설정 파일
├── requirements.txt            # 필수 라이브러리
├── test_connection.py          # API 연결 테스트
├── README.md                   # 이 파일
│
├── okx/                        # OKX API 연동
│   ├── account.py             # 계좌 관리
│   ├── order_manager.py       # 주문 실행
│   ├── websocket_handler.py   # 실시간 데이터
│   ├── position_manager.py    # 포지션 관리
│   └── position_tracker.py    # 거래 기록 추적
│
├── strategy/                   # 트레이딩 전략
│   └── my_strategy.py         # 듀얼 자산 전략
│
├── utils/                      # 유틸리티
│   ├── indicators.py          # 기술적 지표
│   ├── price_buffer.py        # 가격 데이터 버퍼
│   └── generate_latest_data.py # 데이터 생성
│
└── logs/                       # 로그 파일 (자동 생성)
    └── trading.log
```

## 💻 설치 및 설정

### 1. 시스템 요구사항
- **Python 3.8+**
- **인터넷 연결** (실시간 데이터 수신)
- **OKX 계정** (API 키 필요)
- **최소 메모리**: 4GB RAM

### 2. 프로젝트 클론 및 설정

```bash
# 저장소 클론
git clone https://github.com/your-username/CoinTrading.git
cd CoinTrading

# 가상환경 생성 (권장)
python -m venv trading_env

# 가상환경 활성화
# Windows:
trading_env\Scripts\activate
# macOS/Linux:
source trading_env/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt
```

### 3. 디렉토리 생성

```bash
# 로그 디렉토리 생성
mkdir logs

# 데이터베이스 디렉토리 생성 (선택사항)
mkdir data
```

## 🔑 API 설정

### 1. OKX API 키 발급

1. [OKX 거래소](https://www.okx.com) 가입 및 본인인증
2. 2단계 인증(2FA) 설정 필수
3. **계정 → API 관리 → API 키 생성**
4. 권한 설정:
   - ✅ **읽기**: 계좌 조회, 포지션 조회
   - ✅ **거래**: 주문 생성, 취소, 포지션 관리
   - ❌ **출금**: 보안상 비활성화 권장
5. **IP 화이트리스트** 설정 (보안 강화)

### 2. config.py 설정

```python
# config.py 파일 수정
API_KEY = "your_actual_api_key"
API_SECRET = "your_actual_secret_key" 
PASSPHRASE = "your_actual_passphrase"

# 보안 강화 (환경변수 사용 권장)
import os
API_KEY = os.getenv('OKX_API_KEY')
API_SECRET = os.getenv('OKX_API_SECRET')
PASSPHRASE = os.getenv('OKX_PASSPHRASE')
```

### 3. 환경변수 설정 (권장)

```bash
# Windows
set OKX_API_KEY=your_api_key
set OKX_API_SECRET=your_secret_key
set OKX_PASSPHRASE=your_passphrase

# macOS/Linux
export OKX_API_KEY=your_api_key
export OKX_API_SECRET=your_secret_key
export OKX_PASSPHRASE=your_passphrase
```

## 🧪 연결 테스트

시스템 사용 전 반드시 API 연결을 테스트하세요.

```bash
python test_connection.py
```

**예상 출력:**
```
==================================================
OKX API 연결 테스트 시작
==================================================

[1] 계좌 정보 조회 테스트
✅ 계좌 조회 성공
   USDT: 1000.0000 (사용가능: 1000.0000)

[2] 계좌 설정 조회 테스트
✅ 계좌 설정 조회 성공
   계좌 레벨: 1
   포지션 모드: net_mode

[3] 포지션 조회 테스트
✅ 현재 포지션 수: 0

[4] 수수료율 조회 테스트
✅ Maker: 0.020%, Taker: 0.050%

🎉 API 연결 테스트 완료 - 모든 기능 정상 작동
```

## 🎯 사용법

### 1. 기본 실행

```bash
# 메인 시스템 시작
python main.py
```

### 2. 개별 기능 테스트

#### 계좌 정보 확인
```python
from okx.account import AccountManager

account = AccountManager()
status = account.check_account_status()
print(status)
```

#### 수동 포지션 관리
```python
from okx.position_manager import PositionManager

pm = PositionManager()

# 롱 포지션 오픈
position_id = pm.open_position(
    inst_id="BTC-USDT-SWAP",
    side="long",
    size=0.01,                    # 0.01 BTC
    leverage=10,                  # 10배 레버리지
    strategy_name="manual_long",
    trailing_stop_ratio=0.10      # 10% 트레일링 스탑
)

# 포지션 상태 확인
pm.print_position_status()

# 포지션 청산
pm.close_position(position_id, "manual_close")
```

#### 실시간 데이터 모니터링
```python
from okx.websocket_handler import WebSocketHandler

ws = WebSocketHandler()
ws.start_ws(["BTC-USDT-SWAP", "ETH-USDT-SWAP"])

# 30초 후 중지
import time
time.sleep(30)
ws.stop_ws()
```

### 3. 전략 시스템 실행

```python
from strategy.strategy_manager import StrategyManager

# 전략 매니저 초기화
strategy_manager = StrategyManager()

# 전략 등록
strategy_manager.add_strategy("long_strategy", symbols=["BTC-USDT-SWAP"])
strategy_manager.add_strategy("short_strategy", symbols=["ETH-USDT-SWAP"])

# 전략 실행 시작
strategy_manager.start()
```

## 📊 전략 설명

### 알고리즘 1번 - 롱 전략 📈

**진입 조건:**
- 30분봉 기준
- 150EMA > 200EMA (상승장 확인)
- 20EMA가 50EMA를 상향 돌파 (골든크로스)

**청산 조건:**
- 20EMA가 100EMA를 하향 돌파 (데드크로스)
- 또는 트레일링 스탑 (고점 대비 10% 하락)

**위험 관리:**
- 레버리지: 10배
- 손실 한계: 고점 대비 20% 하락 시 거래 중단
- 재진입: 가상자산으로 30% 상승 시 거래 재개

### 알고리즘 2번 - 숏 전략 📉

**진입 조건:**
- 30분봉 기준  
- 150EMA < 200EMA (하락장 확인)
- 20EMA가 50EMA를 하향 돌파 (데드크로스)

**청산 조건:**
- 100EMA가 200EMA를 상향 돌파 (골든크로스)
- 또는 트레일링 스탑 (저점 대비 2% 상승)

**위험 관리:**
- 레버리지: 3배
- 손실 한계: 고점 대비 10% 하락 시 거래 중단
- 재진입: 가상자산으로 20% 상승 시 거래 재개

### 듀얼 자산 시스템

```
실제 자산 (A) ←→ 가상 자산 (B)
     ↓              ↓
  실제 거래      가상 거래 (검증)
     ↓              ↓
 손실 한계 도달 → 가상으로 전환
     ↓              ↓
 가상에서 회복 → 실제로 복귀
```

## 📱 모니터링

### 1. 실시간 콘솔 출력
```
=== 포지션 현황 ===
활성 포지션 수: 2
미실현 PnL: +125.50 USDT
실현 PnL: +89.20 USDT
최대 낙폭: 3.2%

전략별 현황:
  long_strategy: 1개 포지션, PnL: +78.30 USDT
  short_strategy: 1개 포지션, PnL: +47.20 USDT

개별 포지션:
  BTC-USDT-SWAP LONG: 크기 0.0100, 진입가 45000.00, 현재가 45780.00, PnL +78.00 (+1.73%)
```

### 2. 알림 설정

#### 텔레그램 알림 설정
```python
# config.py
NOTIFICATION_CONFIG = {
    "telegram": {
        "enabled": True,
        "bot_token": "your_bot_token",
        "chat_id": "your_chat_id"
    }
}
```

#### 슬랙 알림 설정
```python
# config.py
NOTIFICATION_CONFIG = {
    "slack": {
        "enabled": True,
        "webhook_url": "your_webhook_url",
        "channel": "#trading-alerts"
    }
}
```

### 3. 성과 분석

```python
from okx.position_tracker import PositionTracker

tracker = PositionTracker()
tracker.print_performance_report(days=7)
```

**출력 예시:**
```
==================================================
거래 성과 보고서 (최근 7일)
==================================================
총 거래수: 24
승리 거래: 18
승률: 75.0%
총 PnL: +456.70 USDT
평균 PnL: +19.03 USDT
최대 수익: +89.50 USDT
최대 손실: -23.10 USDT
총 수수료: 12.34 USDT
평균 거래 시간: 45.2분
```

## 🔍 백테스팅

### 1. 기본 백테스트
```python
from backtest.backtester import Backtester

backtester = Backtester()
results = backtester.run_backtest(
    strategy="long_strategy",
    symbol="BTC-USDT-SWAP",
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=10000
)

print(f"총 수익률: {results['total_return']:.2%}")
print(f"샤프 비율: {results['sharpe_ratio']:.2f}")
print(f"최대 낙폭: {results['max_drawdown']:.2%}")
```

### 2. 파라미터 최적화
```python
# 다양한 EMA 기간 조합 테스트
ema_combinations = [
    {"fast": 20, "slow": 50, "trend": 200},
    {"fast": 12, "slow": 26, "trend": 200},
    {"fast": 21, "slow": 55, "trend": 200}
]

best_params = backtester.optimize_parameters(
    strategy="long_strategy",
    parameter_sets=ema_combinations
)
```

## 🛡️ 보안 및 위험관리

### ⚠️ 중요한 보안 수칙

1. **API 키 보안**
   - 절대 코드에 직접 입력하지 않기
   - 환경변수 또는 별도 설정 파일 사용
   - GitHub 등에 업로드 시 `.gitignore`에 추가

2. **권한 최소화**
   - 출금 권한은 절대 활성화하지 않기
   - IP 화이트리스트 설정
   - 정기적인 API 키 재발급

3. **자금 관리**
   - 초기에는 소액으로 테스트
   - 총 자산의 5-10% 이내에서 시작
   - 손실 한계 명확히 설정

### 🚨 위험 관리 체크리스트

- [ ] API 키가 안전하게 관리되고 있는가?
- [ ] IP 화이트리스트가 설정되었는가?
- [ ] 초기 자본이 적절한가? (전체 자산의 10% 이하)
- [ ] 손실 한계가 설정되었는가?
- [ ] 백테스팅 결과를 충분히 검토했는가?
- [ ] Paper Trading으로 검증했는가?
- [ ] 비상 시 수동 개입 방법을 알고 있는가?

### 📋 운영 단계별 권장사항

#### 1단계: 개발 및 테스트
```python
# config.py
ENVIRONMENT = {
    "mode": "development",
    "paper_trading": True,
    "debug": True
}
```

#### 2단계: 소액 실전 테스트
```python
TRADING_CONFIG = {
    "initial_capital": 100,      # $100로 시작
    "max_position_size": 0.1,    # 자본의 10%만 사용
    "risk_per_trade": 0.01       # 거래당 1% 위험
}
```

#### 3단계: 본격 운영
```python
TRADING_CONFIG = {
    "initial_capital": 10000,    # $10,000
    "max_position_size": 0.5,    # 자본의 50%까지
    "risk_per_trade": 0.02       # 거래당 2% 위험
}
```

## 🔧 문제해결

### 자주 발생하는 오류

#### 1. API 연결 오류
```
❌ API 연결 테스트 실패: 401 Unauthorized
```
**해결책:**
- API 키, 시크릿, 패스프레이즈 확인
- IP 화이트리스트에 현재 IP 추가
- API 권한 설정 재확인

#### 2. 주문 실행 오류
```
❌ 주문 실패: Insufficient balance
```
**해결책:**
- 계좌 잔고 확인
- 포지션 크기 조정
- 레버리지 설정 확인

#### 3. WebSocket 연결 오류
```
❌ WebSocket 테스트 실패: Connection timeout
```
**해결책:**
- 인터넷 연결 확인
- 방화벽 설정 확인
- VPN 사용 시 해제 후 재시도

#### 4. 데이터 수신 오류
```
⚠️ WebSocket 연결은 되었으나 데이터 수신 실패
```
**해결책:**
- 심볼명 정확성 확인 (예: BTC-USDT-SWAP)
- 시장 개장 시간 확인
- 구독 채널 재설정

### 로그 분석

```bash
# 실시간 로그 모니터링
tail -f logs/trading.log

# 오류만 필터링
grep "ERROR" logs/trading.log

# 특정 시간대 로그 확인
grep "2024-01-01 14:" logs/trading.log
```

### 디버깅 모드

```python
# config.py
ENVIRONMENT = {
    "debug": True
}

# 상세 로깅 활성화
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 성능 최적화

### 1. 메모리 사용량 최적화
```python
# utils/price_buffer.py
class PriceBuffer:
    def __init__(self, maxlen=200):  # 기본값을 줄여서 메모리 절약
        self.buffer = deque(maxlen=maxlen)
```

### 2. API 호출 최적화
```python
# API 호출 간격 조정 (rate limit 고려)
import time
time.sleep(0.1)  # 100ms 간격
```

### 3. 데이터베이스 성능
```python
# position_tracker.py에서 배치 처리
def batch_update_positions(self, positions):
    # 여러 포지션을 한 번에 업데이트
    pass
```

## 🤝 기여하기

프로젝트 개선에 기여해주세요!

### 개발 환경 설정
```bash
# 개발용 의존성 설치
pip install -r requirements-dev.txt

# 테스트 실행
pytest tests/

# 코드 품질 검사
flake8 .
black .
```

### 이슈 제기
- **버그 리포트**: 상세한 오류 메시지와 재현 단계 포함
- **기능 요청**: 구체적인 사용 사례와 기대 효과 설명
- **문서 개선**: 불명확한 부분이나 누락된 정보 지적

### Pull Request
1. Fork 후 feature branch 생성
2. 코드 작성 및 테스트 추가
3. 문서 업데이트
4. PR 제출 시 변경사항 상세 설명

## ⚖️ 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

## ⚠️ 면책 조항

**이 소프트웨어는 교육 및 연구 목적으로 제공됩니다.**

- 자동매매는 높은 위험을 수반합니다
- 투자 손실에 대한 책임은 사용자에게 있습니다
- 충분한 테스트 없이 실제 자금을 사용하지 마세요
- 본인의 위험 허용도 범위 내에서만 사용하세요

## 📞 지원 및 커뮤니티

- **이슈 트래커**: [GitHub Issues](https://github.com/your-username/CoinTrading/issues)
- **토론**: [GitHub Discussions](https://github.com/your-username/CoinTrading/discussions)
- **이메일**: trading-support@your-domain.com

---

## 🎯 빠른 시작 요약

```bash
# 1. 프로젝트 설정
git clone https://github.com/your-username/CoinTrading.git
cd CoinTrading
pip install -r requirements.txt

# 2. API 키 설정
# config.py에서 API 정보 입력

# 3. 연결 테스트
python test_connection.py

# 4. 시스템 시작
python main.py
```

**성공적인 자동매매를 위한 황금률:**
1. 🧪 **충분한 테스트**
2. 💰 **적절한 자금 관리** 
3. 📊 **지속적인 모니터링**
4. 🛡️ **철저한 위험 관리**

---

*마지막 업데이트: 2024-01-01*