# 🎨 OKX 자동매매 시스템 GUI 설치 및 실행 가이드

## 📁 파일 구조

GUI를 실행하기 위해 다음과 같은 파일 구조가 필요합니다:

```
CoinTrading/
├── gui/
│   ├── __init__.py              # (빈 파일)
│   ├── main_window.py           # 메인 GUI 코드
│   └── config_validator.py      # 설정 검증 모듈
├── run_gui.py                   # GUI 실행 스크립트
├── gui_requirements.txt         # GUI 전용 라이브러리
├── config.py                    # 기존 설정 파일
├── main.py                      # 기존 메인 파일
├── okx/                         # OKX API 모듈들
├── strategy/                    # 전략 모듈들
├── utils/                       # 유틸리티 모듈들
└── logs/                        # 로그 디렉토리 (자동 생성)
```

## 🚀 설치 및 실행 단계

### 1. 필수 라이브러리 설치

#### 방법 1: 자동 설치 (권장)
```bash
python run_gui.py
```
실행하면 누락된 라이브러리를 자동으로 감지하고 설치 여부를 묻습니다.

#### 방법 2: 수동 설치
```bash
# GUI 전용 라이브러리 설치
pip install PyQt5==5.15.9
pip install pyqtgraph==0.13.3
pip install psutil==5.9.6

# 또는 requirements 파일 사용
pip install -r gui_requirements.txt
```

### 2. 기본 파일 생성

#### `gui/__init__.py` 생성
```bash
# Windows
echo. > gui/__init__.py

# macOS/Linux
touch gui/__init__.py
```

#### `config.py` 확인/수정
기존 `config.py` 파일의 API 정보를 올바르게 설정했는지 확인:

```python
# config.py
API_KEY = "your_actual_api_key"
API_SECRET = "your_actual_secret_key"
PASSPHRASE = "your_actual_passphrase"
```

### 3. GUI 실행

```bash
python run_gui.py
```

또는 직접 실행:

```bash
python gui/main_window.py
```

## 🎯 GUI 기능 설명

### 📊 대시보드 탭
- **실시간 상태 모니터링**: 연결 상태, 거래 상태, 운영 시간
- **포지션 현황**: 활성 포지션의 실시간 PnL
- **실시간 차트**: BTC-USDT-SWAP 가격 차트
- **거래 내역**: 최근 거래 기록
- **전략별 성과**: 롱/숏 전략 승률 및 손익

### ⚙️ 설정 탭
- **API 설정**: OKX API 키 입력 및 연결 테스트
- **전략 설정**: 롱/숏 전략별 자본, 레버리지, 트레일링 스탑
- **알림 설정**: 슬랙, 텔레그램, 이메일 알림 활성화

### 📡 모니터링 탭
- **실시간 로그**: 시스템 로그 실시간 표시
- **시스템 상태**: CPU/메모리 사용률
- **네트워크 상태**: API 및 WebSocket 연결 상태
- **오류 카운트**: 경고 및 오류 횟수

### 📈 백테스팅 탭
- **백테스트 설정**: 전략, 기간, 초기자본 설정
- **결과 표시**: 수익률, 승률, 최대낙폭, 샤프비율
- **자본 곡선 차트**: 백테스트 기간 동안의 자본 변화

### 💼 포지션 관리 탭
- **활성 포지션 테이블**: 모든 포지션의 상세 정보
- **포지션 제어**: 전체/롱/숏 청산 버튼
- **긴급 정지**: 모든 거래 즉시 중단
- **거래 이력**: 최근 거래 내역

## 🎨 GUI 특징

### 다크 테마
- 눈의 피로를 줄이는 다크 테마 기본 적용
- 거래 관련 색상: 녹색(수익), 빨간색(손실), 주황색(경고)

### 실시간 업데이트
- 1초마다 시간 업데이트
- 5초마다 포지션 상태 업데이트
- 실시간 로그 스트리밍

### 시스템 트레이
- 최소화 시 시스템 트레이로 이동
- 트레이 아이콘 우클릭으로 메뉴 접근
- 거래 시작/중지 시 알림

## 🔧 주요 단축키

- **Ctrl+S**: 설정 저장
- **Ctrl+Q**: 프로그램 종료
- **F5**: 새로고침
- **Ctrl+1~5**: 탭 전환

## ⚠️ 주의사항

### 1. Paper Trading 모드
- 처음 실행 시 Paper Trading 모드로 설정됨
- 실제 거래 전 반드시 테스트 권장

### 2. API 키 보안
- API 키는 GUI 내에서 마스킹 처리됨
- 설정 파일은 암호화되지 않으므로 주의

### 3. 시스템 리소스
- GUI는 추가 메모리(약 100-200MB) 사용
- 장시간 실행 시 로그 파일 크기 주의

## 🐛 문제해결

### PyQt5 설치 오류
```bash
# Windows에서 C++ 컴파일러 오류 시
pip install PyQt5 --only-binary=all

# 또는 conda 사용
conda install pyqt
```

### 모듈 임포트 오류
```bash
# Python 경로 확인
python -c "import sys; print(sys.path)"

# 현재 디렉토리에서 실행하는지 확인
cd /path/to/CoinTrading
python run_gui.py
```

### GUI 응답 없음
- 백테스팅 등 무거운 작업 중일 수 있음
- 강제 종료: Ctrl+C (터미널) 또는 작업 관리자

### 차트 표시 안됨
- pyqtgraph 라이브러리 확인
- OpenGL 드라이버 업데이트 (선택사항)

## 📊 성능 최적화

### 메모리 사용량 감소
- 로그 최대 라인 수 조정 (기본: 1000줄)
- 차트 데이터 포인트 수 조정 (기본: 100개)

### CPU 사용량 감소
- 업데이트 간격 늘리기 (기본: 1초)
- 불필요한 탭 비활성화

## 🔄 업데이트

새로운 기능이나 버그 수정이 있을 때:

1. `gui/main_window.py` 파일 교체
2. 기존 설정 백업 (자동으로 수행됨)
3. GUI 재시작

```bash
# 백업 확인
ls config_backups/

# GUI 재시작
python run_gui.py
```

## 📱 추가 기능 (향후 계획)

### 모바일 연동
- QR 코드로 모바일 알림 설정
- 원격 제어 기능

### 고급 차트
- 다중 시간프레임 차트
- 기술적 지표 추가 (RSI, MACD 등)
- 진입/청산 포인트 마킹

### 자동화 기능
- 예약 거래 시작/중지
- 조건부 알림
- 자동 설정 백업

## 🎯 사용 팁

### 효율적인 모니터링
1. **대시보드**에서 전체 상황 파악
2. **모니터링**에서 상세 로그 확인
3. **포지션 관리**에서 즉시 대응

### 안전한 거래
1. 작은 자본으로 시작
2. Paper Trading으로 충분한 테스트
3. 손실 한계 설정 준수
4. 정기적인 수익 실현

### 설정 관리
1. 중요한 설정 변경 전 백업
2. 여러 전략 설정 파일 관리
3. 정기적인 성과 분석

## 🆘 지원 및 문의

### 로그 파일 위치
- GUI 로그: `logs/gui.log`
- 거래 로그: `logs/trading.log`
- 오류 로그: `logs/errors.log`

### 설정 파일 위치
- GUI 설정: `gui_trading_config.json`
- 설정 백업: `config_backups/`

### 문제 신고 시 포함할 정보
1. 운영체제 및 Python 버전
2. 오류 메시지 전문
3. 관련 로그 파일
4. 재현 단계

---

## 🚀 빠른 시작 체크리스트

- [ ] Python 3.8+ 설치 확인
- [ ] 프로젝트 파일 다운로드
- [ ] `gui/__init__.py` 파일 생성
- [ ] `config.py`에 API 정보 입력
- [ ] `python run_gui.py` 실행
- [ ] API 연결 테스트 수행
- [ ] Paper Trading 모드로 테스트
- [ ] 알림 설정 (선택사항)
- [ ] 실제 거래 시작 (신중하게!)

**성공적인 자동매매를 위해 충분한 테스트와 모니터링을 권장합니다! 📈**