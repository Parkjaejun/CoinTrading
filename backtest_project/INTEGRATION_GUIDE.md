# 알고리즘 검증 위젯 통합 가이드

## 📁 파일 구조

```
backtest_project/
├── backtest/                    # 백테스트 코어 모듈
│   ├── __init__.py
│   ├── data_fetcher.py          # Binance 데이터 수집
│   ├── backtest_engine.py       # 백테스트 엔진 (scratch_2.py 기반)
│   └── result_analyzer.py       # 결과 분석
│
├── gui/                         # GUI 위젯
│   ├── __init__.py
│   ├── backtest_widget.py       # 메인 백테스트 탭 위젯 ⭐
│   ├── chart_widget.py          # 가격 차트 (matplotlib)
│   ├── trade_table_widget.py    # 거래 내역 테이블
│   └── stats_widget.py          # 통계 요약
│
├── main.py                      # 독립 실행 / 통합용 함수
├── test_backtest.py             # 테스트 스크립트
└── INTEGRATION_GUIDE.md         # 이 파일
```

---

## 🚀 독립 실행

```bash
cd backtest_project
python main.py
```

---

## 🔧 기존 GUI에 통합하는 방법

### 방법 1: 탭으로 추가 (권장)

기존 `MainWindow`의 `setup_ui()` 메서드에 다음 코드 추가:

```python
# 상단에 import 추가
import sys
sys.path.insert(0, '/path/to/backtest_project')  # 경로 조정

from main import create_backtest_tab

# setup_ui() 내부에서 탭 추가
def setup_ui(self):
    # ... 기존 탭 생성 코드 ...
    
    # 알고리즘 검증 탭 추가
    backtest_tab = create_backtest_tab()
    self.tab_widget.addTab(backtest_tab, "🧪 알고리즘 검증")
```

### 방법 2: 직접 위젯 import

```python
from gui.backtest_widget import BacktestWidget

# 탭에 추가
backtest_widget = BacktestWidget()
self.tab_widget.addTab(backtest_widget, "🧪 알고리즘 검증")
```

---

## 📊 주요 기능

### 1. 데이터 로드
- **CSV 로드**: 기존 CSV 파일 직접 로드
- **Binance API**: 지정 기간의 데이터 자동 수집 (캐싱 지원)

### 2. 백테스트 실행
- **Long Only 모드**: 롱 포지션만 진입
- **듀얼 모드**: REAL/VIRTUAL 자동 전환
- **파라미터 설정**: 초기 자본, 레버리지 등

### 3. 결과 시각화
- **가격 차트**: 캔들스틱/라인 차트 + EMA 라인
- **마커 표시**: 진입(🔺) / 청산(⭕) 지점
- **거래 테이블**: 전체 거래 내역
- **통계 요약**: 수익률, MDD, 승률 등

### 4. 인터랙션
- **거래 선택**: 테이블에서 거래 클릭 시 차트 하이라이트
- **줌/팬**: matplotlib 네비게이션 툴바
- **EMA 토글**: 개별 EMA 라인 표시/숨김

---

## 🎯 알고리즘 파라미터 (기본값)

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| trend_fast | 150 | 트렌드 판단용 빠른 EMA |
| trend_slow | 200 | 트렌드 판단용 느린 EMA |
| entry_fast | 20 | 진입 신호용 빠른 EMA |
| entry_slow | 50 | 진입 신호용 느린 EMA |
| long_exit_fast | 20 | 청산 신호용 빠른 EMA |
| long_exit_slow | 100 | 청산 신호용 느린 EMA |
| leverage_long | 10.0 | 롱 레버리지 |
| trailing_stop_long | 0.10 | 트레일링 스탑 (10%) |
| stop_loss_ratio_long | 0.20 | REAL→VIRTUAL 전환 (-20%) |
| reentry_gain_ratio_long | 0.30 | VIRTUAL→REAL 복귀 (+30%) |
| capital_use_ratio | 0.50 | 자본 사용 비율 |
| fee_rate_per_side | 0.0005 | 수수료 (0.05%/편도) |

---

## 📝 검증 체크리스트

### 진입 시점 검증
- [ ] 150 EMA > 200 EMA (상승장) 조건 확인
- [ ] 20 EMA ↗ 50 EMA 골든크로스 감지
- [ ] 마커와 실제 크로스오버 시점 일치

### 청산 시점 검증
- [ ] 20 EMA ↘ 100 EMA 데드크로스 청산
- [ ] 트레일링 스탑 (고점 대비 -10%) 동작
- [ ] 청산 사유 정확히 기록

### 수익률 검증
- [ ] 레버리지 10배 적용 확인
- [ ] 수수료 (0.1% 왕복) 차감 확인
- [ ] 순손익 = PnL - 수수료

### 듀얼 모드 검증
- [ ] REAL → VIRTUAL (피크 대비 -20%)
- [ ] VIRTUAL → REAL (트로프 대비 +30%)
- [ ] 모드별 자본 분리 계산

---

## 🐛 문제 해결

### matplotlib 백엔드 오류
```python
import matplotlib
matplotlib.use('Qt5Agg')  # PyQt5용 백엔드 명시
```

### Import 오류
```python
import sys
sys.path.insert(0, '/path/to/backtest_project')
```

### 차트가 표시되지 않음
- `canvas.draw()` 호출 확인
- `figure.tight_layout()` 호출 확인

---

## 📌 의존성

```
PyQt5>=5.15.0
matplotlib>=3.5.0
pandas>=1.3.0
numpy>=1.20.0
requests>=2.25.0
```

---

## 📞 문의

추가 기능이나 버그 수정이 필요하면 말씀해주세요!
