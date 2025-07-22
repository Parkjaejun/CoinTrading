# 🚀 OKX 자동매매 시스템 완전 설치 가이드

## 📋 목차
1. [시스템 요구사항](#시스템-요구사항)
2. [설치 과정](#설치-과정)
3. [API 설정](#api-설정)
4. [알림 설정](#알림-설정)
5. [설정 검증](#설정-검증)
6. [실행 방법](#실행-방법)
7. [백테스팅](#백테스팅)
8. [문제해결](#문제해결)

## 🖥️ 시스템 요구사항

### 필수 요구사항
- **Python 3.8 이상**
- **최소 4GB RAM**
- **안정적인 인터넷 연결**
- **OKX 거래소 계정** (API 키 필요)

### 권장 사항
- Python 3.9-3.11 (최적 성능)
- 8GB RAM 이상
- SSD 저장장치
- VPS 또는 전용 서버 (24시간 운영시)

## 🔧 설치 과정

### 1. 프로젝트 다운로드
```bash
# Git 클론 (또는 ZIP 다운로드)
git clone https://github.com/your-repo/okx-trading-bot.git
cd okx-trading-bot
```

### 2. 가상환경 생성 (권장)
```bash
# Windows
python -m venv trading_env
trading_env\Scripts\activate

# macOS/Linux
python3 -m venv trading_env
source trading_env/bin/activate
```

### 3. 필수 라이브러리 설치
```bash
# 업데이트된 requirements 설치
pip install -r requirements_updated.txt

# 또는 개별 설치
pip install requests==2.31.0 websocket-client==1.6.4 pandas==2.1.4 numpy==1.24.3 python-dateutil==2.8.2
```

### 4. 디렉토리 구조 확인
```
okx-trading-bot/
├── main_updated.py          # 메인 실행 파일
├── config_updated.py        # 설정 파일
├── requirements_updated.txt # 라이브러리 목록
├── logs/                    # 로그 파일 (자동 생성)
├── okx/                     # OKX API 관련
├── strategy/                # 트레이딩 전략
├── utils/                   # 유틸리티
└── backtest/               # 백테스팅
```

### 5. 누락된 파일 생성
프로젝트에서 제공한 아티팩트들을 다음 위치에 저장:

```bash
# 1. 기본 인프라
okx/account.py
utils/logger.py

# 2. 연결 관리
okx/connection_manager.py

# 3. 데이터 로딩
utils/data_loader.py

# 4. 주문 검증
okx/order_validator.py

# 5. 백테스팅
backtest/backtester.py

# 6. 알림 시스템
utils/notifications.py

# 7. 업데이트된 설정
config_updated.py

# 8. 업데이트된 메인
main_updated.py

# 9. 업데이트된 requirements
requirements_updated.txt
```

## 🔑 API 설정

### 1. OKX API 키 발급
1. [OKX 거래소](https://www.okx.com) 로그인
2. **계정 → API 관리** 이동
3. **API 키 생성** 클릭
4. 권한 설정:
   - ✅ **읽기** (계좌 조회)
   - ✅ **거래** (주문 실행)
   - ❌ **출금** (보안상 비활성화)
5. **IP 화이트리스트** 설정 (보안 강화)
6. **2FA 인증** 완료

### 2. API 정보 설정
`config_updated.py` 파일을 열고 다음 정보를 입력:

```python
# API 인증 정보
API_KEY = "your_actual_api_key_here"
API_SECRET = "your_actual_secret_key_here"
PASSPHRASE = "your_actual_passphrase_here"
```

### 3. 환경변수 설정 (더 안전한 방법)
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

## 🔔 알림 설정

### 슬랙 알림 (권장)
1. 슬랙 워크스페이스에서 앱 추가
2. **Incoming Webhooks** 검색 및 설치
3. 채널 선택 및 웹훅 URL 복사
4. `config_updated.py`에서 설정:

```python
NOTIFICATION_CONFIG = {
    "slack": {
        "enabled": True,
        "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
        "channel": "#trading-alerts"
    }
}
```

### 텔레그램 알림
1. @BotFather에게 `/newbot` 명령으로 봇 생성
2. 봇 토큰 복사
3. 봇과 대화 시작 후 Chat ID 확인
4. 설정 업데이트:

```python
"telegram": {
    "enabled": True,
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
}
```

### 이메일 알림
Gmail 사용 시:
1. Gmail에서 2단계 인증 활성화
2. 앱 비밀번호 생성
3. 설정 업데이트:

```python
"email": {
    "enabled": True,
    "sender_email": "your_email@gmail.com",
    "sender_password": "your_app_password",
    "recipient_email": "recipient@gmail.com"
}
```

## ✅ 설정 검증

### 1. 설정 테스트
```bash
python main_updated.py --config-test
```

예상 출력:
```
✅ 설정 검증 완료
🔔 활성 알림 채널: slack
🛡️  안전 설정 정상
✅ 설정 테스트 통과
```

### 2. API 연결 테스트
```bash
python simple_test.py
```

예상 출력:
```
✅ API 연결 성공
   USDT: 1000.0000
   Maker: 0.020%, Taker: 0.050%
🎉 테스트 완료 - API 정상 작동
```

## 🚀 실행 방법

### 1. 개발 모드 (Paper Trading)
```bash
python main_updated.py --env development
```
- 실제 주문 없음
- 시뮬레이션만 실행
- 안전한 테스트

### 2. 실제 거래 모드
```bash
python main_updated.py --env production
```
- 실제 자금으로 거래
- 신중하게 시작

### 3. 백그라운드 실행 (Linux/macOS)
```bash
nohup python main_updated.py --env production > trading.log 2>&1 &
```

### 4. 서비스로 등록 (systemd)
`/etc/systemd/system/trading-bot.service` 생성:

```ini
[Unit]
Description=OKX Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/your/bot
ExecStart=/path/to/your/venv/bin/python main_updated.py --env production
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

활성화:
```bash
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

## 📊 백테스팅

### 기본 백테스트
```bash
# 롱 전략 백테스트
python main_updated.py --backtest long --start-date 2024-01-01 --end-date 2024-06-30

# 숏 전략 백테스트  
python main_updated.py --backtest short --start-date 2024-01-01 --end-date 2024-06-30
```

### Python 스크립트로 백테스트
```python
from backtest.backtester import run_strategy_backtest

# 롱 전략 테스트
result = run_strategy_backtest(
    strategy_type='long',
    symbol='BTC-USDT-SWAP', 
    start_date='2024-01-01',
    end_date='2024-06-30',
    initial_capital=10000
)

print(f"총 수익률: {result.metrics['total_return']*100:.2f}%")
print(f"승률: {result.metrics['win_rate']*100:.1f}%")
```

## 🚨 중요한 안전 수칙

### 1. 시작 전 체크리스트
- [ ] Paper Trading으로 충분히 테스트
- [ ] 소액 자본으로 실전 테스트
- [ ] API 키 권한 재확인 (출금 권한 비활성화)
- [ ] 알림 시스템 작동 확인
- [ ] 손실 한계 설정 확인

### 2. 운영 중 모니터링
- [ ] 로그 파일 정기 확인
- [ ] 포지션 상태 모니터링
- [ ] 알림 메시지 확인
- [ ] 시스템 리소스 확인

### 3. 긴급 상황 대응
```bash
# 즉시 중단
Ctrl + C

# 모든 포지션 강제 청산 (별도 스크립트)
python emergency_close.py

# 서비스 중지
sudo systemctl stop trading-bot
```

## 🔧 문제해결

### 자주 발생하는 오류

#### 1. API 연결 오류
```
❌ API 연결 테스트 실패: 401 Unauthorized
```
**해결책:**
- API 키, 시크릿, 패스프레이즈 재확인
- IP 화이트리스트 설정 확인
- 시간 동기화 확인

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
❌ WebSocket 연결 실패
```
**해결책:**
- 인터넷 연결 확인
- 방화벽 설정 확인
- VPN 사용시 해제

#### 4. 모듈 임포트 오류
```
ModuleNotFoundError: No module named 'xxx'
```
**해결책:**
```bash
pip install -r requirements_updated.txt
```

### 로그 확인
```bash
# 실시간 로그 모니터링
tail -f logs/trading.log

# 오류만 필터링
grep "ERROR" logs/trading.log

# 거래 내역만 확인
grep "TRADE" logs/trades.log
```

### 성능 모니터링
```bash
# CPU/메모리 사용량
top -p $(pgrep -f "main_updated.py")

# 디스크 사용량
du -sh logs/

# 네트워크 연결 상태
netstat -an | grep :8443
```

## 📞 지원 및 도움

### 로그 수집 (문제 신고시)
```bash
# 필요한 정보 수집
echo "=== 시스템 정보 ===" > debug_info.txt
python --version >> debug_info.txt
pip list >> debug_info.txt
echo "=== 최근 로그 ===" >> debug_info.txt
tail -100 logs/trading.log >> debug_info.txt
echo "=== 오류 로그 ===" >> debug_info.txt
grep "ERROR" logs/trading.log | tail -20 >> debug_info.txt
```

### 커뮤니티
- GitHub Issues
- 텔레그램 그룹
- 이메일 지원

---

## 🎯 성공적인 운영을 위한 팁

1. **점진적 확장**: 소액 → 중간 → 본격 운영
2. **지속적 모니터링**: 알림 시스템 적극 활용
3. **정기적 백테스트**: 전략 성능 검증
4. **위험 관리**: 손실 한계 엄격히 준수
5. **로그 분석**: 패턴 파악 및 개선점 도출

**행운을 빕니다! 📈**