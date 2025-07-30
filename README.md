# 🎨 OKX 자동매매 시스템 README

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![GUI](https://img.shields.io/badge/GUI-PyQt5-green.svg)
![Trading](https://img.shields.io/badge/Trading-OKX-orange.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

**전문적인 GUI 기반 OKX 암호화폐 자동매매 시스템**

EMA 기반의 듀얼 트레이딩 전략(롱/숏)을 직관적인 GUI로 실시간 관리하며, 포지션 모니터링, 백테스팅, 설정 관리 등 모든 기능을 시각적으로 제공합니다.

---

## 📋 목차

- [🚀 프로젝트 개요](#-프로젝트-개요)
- [⚙️ 환경 설정](#-환경-설정)
- [🤖 트레이딩 전략 및 알고리즘](#-트레이딩-전략-및-알고리즘)
- [🖥️ GUI 기능 구성](#-gui-기능-구성)
- [🔧 신규 트레이딩 전략 추가 방법](#-신규-트레이딩-전략-추가-방법)
- [📊 백테스팅 및 성과 분석](#-백테스팅-및-성과-분석)
- [🔧 문제해결](#-문제해결)

---

## 🚀 프로젝트 개요

### 🎯 주요 기능
- **듀얼 전략 자동매매**: EMA 기반 롱/숏 전략을 동시 운영
- **GUI 기반 제어**: 직관적인 인터페이스로 모든 기능 관리
- **실시간 모니터링**: 포지션, 차트, 잔고 실시간 추적
- **가상/실제 거래**: 손실 시 자동으로 가상 거래로 전환
- **백테스팅**: 과거 데이터를 이용한 전략 검증
- **위험 관리**: 트레일링 스탑, 손절매 자동 실행

### 🏗️ 프로젝트 구조
```
CoinTrading/
├── gui/                    # GUI 관련 모듈
│   ├── __init__.py
│   ├── main_window.py      # 메인 윈도우
│   ├── widgets.py          # GUI 위젯들
│   └── settings_dialog.py  # 설정 다이얼로그
├── strategy/               # 트레이딩 전략
│   ├── long_strategy.py    # 롱 전략
│   ├── short_strategy.py   # 숏 전략
│   └── dual_manager.py     # 듀얼 전략 관리
├── okx/                    # OKX API 관련
│   ├── api_client.py       # API 클라이언트
│   └── account_manager.py  # 계좌 관리
├── simulation/             # 백테스팅 시뮬레이션
│   ├── virtual_order.py    # 가상 주문 관리
│   └── strategy_adapter.py # 전략 어댑터
├── run_gui.py             # GUI 런처
└── config.py              # 설정 파일
```

---

## ⚙️ 환경 설정

### 1. 시스템 요구사항
```bash
# Python 버전
Python 3.8 이상

# 운영체제
Windows 10/11, macOS 10.14+, Ubuntu 18.04+

# 메모리
최소 4GB RAM (8GB 권장)
```

### 2. 라이브러리 설치
```bash
# 필수 라이브러리
pip install PyQt5==5.15.9
pip install pyqtgraph==0.13.3
pip install psutil==5.9.6

# 추가 라이브러리 (선택사항)
pip install colorlog  # 컬러 로깅
pip install requests  # HTTP 요청
pip install pandas    # 데이터 분석
```

### 3. 프로젝트 설정
```bash
# 1. 프로젝트 클론/다운로드
git clone <repository-url>
cd CoinTrading

# 2. 빈 __init__.py 파일 생성 (중요!)
touch gui/__init__.py

# 3. config.py 파일 설정
cp config.example.py config.py
nano config.py  # API 키 입력
```

### 4. OKX API 설정
```python
# config.py 파일 내용
OKX_CONFIG = {
    "API_KEY": "your_api_key_here",
    "API_SECRET": "your_secret_here",
    "PASSPHRASE": "your_passphrase_here",
    "sandbox": False,  # True: 테스트넷, False: 실거래
    "flag": "0"  # 0: 실거래, 1: 포트폴리오 마진
}

# 거래 설정
TRADING_CONFIG = {
    "paper_trading": True,      # True: 가상거래, False: 실거래
    "initial_capital": 1000,    # 초기 자본 ($)
    "symbols": ["BTC-USDT-SWAP"],  # 거래할 심볼
    "leverage": 5               # 레버리지 (안전한 값으로 시작)
}
```

### 5. GUI 실행
```bash
# 방법 1: 런처 사용 (권장)
python run_gui.py

# 방법 2: 직접 실행
python gui/main_window.py
```

---

## 🤖 트레이딩 전략 및 알고리즘

### 📈 알고리즘 1번 - 롱 전략

#### 전략 개요
- **시간프레임**: 30분봉
- **기본 조건**: 상승장 (150EMA > 200EMA)
- **레버리지**: 10배
- **트레일링 스탑**: 고점 대비 10%

#### 진입/청산 로직
```python
# 진입 조건 (골든크로스)
상승장 확인: 150EMA > 200EMA
진입 신호: 20EMA가 50EMA를 상향 돌파

# 청산 조건 (데드크로스)
청산 신호: 20EMA가 100EMA를 하향 돌파
트레일링 스탑: 고점 대비 10% 하락
```

#### 위험 관리
- **손실 한계**: 고점 대비 20% 하락 시 거래 중단
- **자산 전환**: 실제 자산 → 가상 자산으로 자동 전환
- **재진입**: 가상자산으로 30% 회복 시 실제 거래 재개

### 📉 알고리즘 2번 - 숏 전략

#### 전략 개요
- **시간프레임**: 30분봉
- **기본 조건**: 하락장 (150EMA < 200EMA)
- **레버리지**: 3배
- **트레일링 스탑**: 고점 대비 2%

#### 진입/청산 로직
```python
# 진입 조건 (데드크로스)
하락장 확인: 150EMA < 200EMA
진입 신호: 20EMA가 50EMA를 하향 돌파

# 청산 조건 (골든크로스)
청산 신호: 100EMA가 200EMA를 상향 돌파
트레일링 스탑: 고점 대비 2% 하락
```

#### 위험 관리
- **손실 한계**: 고점 대비 10% 하락 시 거래 중단
- **자산 전환**: 실제 자산 → 가상 자산으로 자동 전환
- **재진입**: 가상자산으로 20% 회복 시 실제 거래 재개

### 🔄 듀얼 전략 관리

#### 전략 병렬 실행
```python
# 자본 분배 방식
total_capital = 1000
strategies_count = len(symbols) * 2  # 롱/숏 각각
capital_per_strategy = total_capital / strategies_count

# 예: BTC-USDT-SWAP 거래 시
long_strategy_capital = 500   # 롱 전략에 50%
short_strategy_capital = 500  # 숏 전략에 50%
```

#### 우선순위 관리
1. **시장 트렌드 우선**: 강한 상승장에서는 롱 전략 비중 증가
2. **리스크 관리 우선**: 높은 변동성에서는 레버리지 감소
3. **성과 기반 조정**: 성과가 좋은 전략의 자본 비중 증가

---

## 🖥️ GUI 기능 구성

### 📊 대시보드 탭
```
┌─────────────────────────────────────────────────────────────┐
│ 🎯 실시간 대시보드                                           │
│ ┌─────────────────┬─────────────────────────────────────────┐ │
│ │ 📡 연결 상태     │ 🟢 API 연결됨                           │ │
│ │ 💰 총 잔고      │ $1,234.56                              │ │
│ │ 📈 활성 포지션   │ 2개 (롱 1개, 숏 1개)                   │ │
│ │ 📊 일일 PnL     │ +$45.67 (+3.7%)                       │ │
│ └─────────────────┴─────────────────────────────────────────┘ │
│                                                             │
│ 📈 실시간 가격 차트 (최근 100개 데이터 포인트)                │
│ [차트 영역 - PyQtGraph 기반]                                │
│                                                             │
│ 🚨 시스템 상태                                               │
│ [로그 표시 영역 - 실시간 업데이트]                           │
└─────────────────────────────────────────────────────────────┘
```

### 📈 포지션 관리 탭
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 활성 포지션                                               │
│ ┌─────────┬────────┬──────────┬──────────┬──────────┬──────┐ │
│ │ 심볼    │ 방향   │ 크기     │ 진입가   │ 현재가   │ PnL  │ │
│ ├─────────┼────────┼──────────┼──────────┼──────────┼──────┤ │
│ │ BTC-USD │ LONG   │ 0.0100   │ $45,600  │ $45,780  │ +$18 │ │
│ │ ETH-USD │ SHORT  │ 0.0500   │ $3,200   │ $3,180   │ +$10 │ │
│ └─────────┴────────┴──────────┴──────────┴──────────┴──────┘ │
├─────────────────────────────────────────────────────────────┤
│ 🎮 포지션 제어                                               │
│ [전체 청산] [롱 청산] [숏 청산] [🚨 긴급 정지]                │
└─────────────────────────────────────────────────────────────┘
```

### ⚙️ 설정 탭
```
┌─────────────────────────────────────────────────────────────┐
│ 🔧 거래 설정                                                 │
│ ┌─────────────────┬─────────────────────────────────────────┐ │
│ │ Paper Trading:  │ ☑ 활성화 (실거래 시 체크 해제)           │ │
│ │ 초기 자본:      │ $1000                                  │ │
│ │ 거래 심볼:      │ BTC-USDT-SWAP                          │ │
│ │ 롱 레버리지:    │ 10배                                   │ │
│ │ 숏 레버리지:    │ 3배                                    │ │
│ └─────────────────┴─────────────────────────────────────────┘ │
│                                                             │
│ 🔑 API 설정                                                 │
│ ┌─────────────────┬─────────────────────────────────────────┐ │
│ │ API Key:        │ ******************** [편집]            │ │
│ │ Secret Key:     │ ******************** [편집]            │ │
│ │ Passphrase:     │ ******************** [편집]            │ │
│ │ 연결 상태:      │ 🟢 연결됨                               │ │
│ └─────────────────┴─────────────────────────────────────────┘ │
│ [연결 테스트] [설정 저장] [백업 생성]                         │
└─────────────────────────────────────────────────────────────┘
```

### 🎯 조건 모니터링 탭
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 실시간 조건 체크                                          │
│ ┌─────────────────┬─────────────────────────────────────────┐ │
│ │ 총 체크 횟수:   │ 1,234회                                │ │
│ │ 조건 만족:      │ 45회                                   │ │
│ │ 마지막 신호:    │ 12:34:56 - 롱 진입                     │ │
│ │ 모니터링 상태:  │ 🟢 활성                                │ │
│ └─────────────────┴─────────────────────────────────────────┘ │
│                                                             │
│ 🎮 제어 패널                                                 │
│ [모니터링 시작/중지] [수동 체크] [로그 내보내기]               │
│                                                             │
│ 📝 조건 체크 로그                                            │
│ [실시간 로그 표시 영역]                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 신규 트레이딩 전략 추가 방법

### 1. 전략 클래스 생성

#### 기본 전략 템플릿
```python
# strategy/my_new_strategy.py
from typing import Dict, Any, Optional

class MyNewStrategy:
    """새로운 트레이딩 전략"""
    
    def __init__(self, symbol: str, initial_capital: float):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # 전략 파라미터
        self.leverage = 5
        self.stop_loss = 0.05  # 5% 손절매
        
        # 포지션 상태
        self.is_position_open = False
        self.entry_price = 0
        self.position_side = None  # 'long' or 'short'
        
        # 성과 추적
        self.total_pnl = 0
        self.trade_count = 0
        self.win_count = 0
    
    def check_entry_condition(self, data: Dict[str, Any]) -> Optional[str]:
        """진입 조건 체크
        
        Args:
            data: 시장 데이터 (가격, 지표 등)
            
        Returns:
            'long', 'short', 또는 None
        """
        # 여기에 진입 로직 구현
        current_price = data.get('close')
        rsi = data.get('rsi_14')
        
        # 예시: RSI 기반 전략
        if rsi and rsi < 30:  # 과매도
            return 'long'
        elif rsi and rsi > 70:  # 과매수
            return 'short'
        
        return None
    
    def check_exit_condition(self, data: Dict[str, Any]) -> bool:
        """청산 조건 체크"""
        if not self.is_position_open:
            return False
        
        current_price = data.get('close')
        if not current_price:
            return False
        
        # 손절매 체크
        if self.position_side == 'long':
            loss_pct = (self.entry_price - current_price) / self.entry_price
            if loss_pct >= self.stop_loss:
                return True
        elif self.position_side == 'short':
            loss_pct = (current_price - self.entry_price) / self.entry_price
            if loss_pct >= self.stop_loss:
                return True
        
        # 추가 청산 조건들...
        
        return False
    
    def process_signal(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """메인 신호 처리 로직"""
        
        if not self.is_position_open:
            # 진입 신호 체크
            entry_signal = self.check_entry_condition(data)
            if entry_signal:
                return self.enter_position(data, entry_signal)
        else:
            # 청산 신호 체크
            if self.check_exit_condition(data):
                return self.exit_position(data)
        
        return None
    
    def enter_position(self, data: Dict[str, Any], side: str) -> Dict[str, Any]:
        """포지션 진입"""
        current_price = data.get('close')
        
        # 포지션 크기 계산
        position_value = self.current_capital * self.leverage
        size = position_value / current_price
        
        # 포지션 상태 업데이트
        self.is_position_open = True
        self.entry_price = current_price
        self.position_side = side
        
        return {
            'action': 'enter',
            'side': side,
            'symbol': self.symbol,
            'price': current_price,
            'size': size,
            'leverage': self.leverage
        }
    
    def exit_position(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """포지션 청산"""
        current_price = data.get('close')
        
        # PnL 계산
        if self.position_side == 'long':
            pnl = (current_price - self.entry_price) / self.entry_price
        else:  # short
            pnl = (self.entry_price - current_price) / self.entry_price
        
        pnl *= self.leverage
        pnl_amount = self.current_capital * pnl
        
        # 자본 업데이트
        self.current_capital += pnl_amount
        self.total_pnl += pnl_amount
        self.trade_count += 1
        
        if pnl_amount > 0:
            self.win_count += 1
        
        # 포지션 상태 리셋
        self.is_position_open = False
        self.entry_price = 0
        self.position_side = None
        
        return {
            'action': 'exit',
            'symbol': self.symbol,
            'price': current_price,
            'pnl': pnl_amount,
            'pnl_percentage': pnl * 100
        }
```

### 2. 전략 매니저에 통합

#### 전략 매니저 수정
```python
# strategy/enhanced_dual_manager.py 수정
from strategy.my_new_strategy import MyNewStrategy

class EnhancedMultiStrategyManager:
    """다중 전략 매니저"""
    
    def __init__(self, total_capital: float, symbols: List[str]):
        self.total_capital = total_capital
        self.symbols = symbols
        self.strategies = {}
        
        # 전략별 자본 분배
        strategy_count = len(symbols) * 3  # 롱, 숏, 새 전략
        capital_per_strategy = total_capital / strategy_count
        
        for symbol in symbols:
            # 기존 전략들
            self.strategies[f"long_{symbol}"] = EnhancedMonitoringLongStrategy(
                symbol, capital_per_strategy
            )
            self.strategies[f"short_{symbol}"] = EnhancedMonitoringShortStrategy(
                symbol, capital_per_strategy
            )
            
            # 새로운 전략 추가
            self.strategies[f"mynew_{symbol}"] = MyNewStrategy(
                symbol, capital_per_strategy
            )
```

### 3. GUI에 전략 추가

#### 설정 탭에 전략 선택 추가
```python
# gui/widgets.py 수정
class SettingsWidget(QWidget):
    def create_strategy_settings(self):
        """전략 설정 UI"""
        strategy_group = QGroupBox("📊 전략 설정")
        layout = QVBoxLayout()
        
        # 전략 활성화 체크박스
        self.long_strategy_cb = QCheckBox("롱 전략 활성화")
        self.short_strategy_cb = QCheckBox("숏 전략 활성화")
        self.mynew_strategy_cb = QCheckBox("새 전략 활성화")  # 추가
        
        layout.addWidget(self.long_strategy_cb)
        layout.addWidget(self.short_strategy_cb)
        layout.addWidget(self.mynew_strategy_cb)  # 추가
        
        strategy_group.setLayout(layout)
        return strategy_group
```

### 4. 백테스팅에 전략 추가

#### 시뮬레이션 어댑터 생성
```python
# simulation/strategy_adapter.py에 추가
from strategy.my_new_strategy import MyNewStrategy

# 새 전략용 어댑터 생성
mynew_adapter = SimulationStrategyAdapter(MyNewStrategy, symbol)
```

### 5. 전략 검증 및 테스트

#### 단위 테스트 작성
```python
# tests/test_my_new_strategy.py
import unittest
from strategy.my_new_strategy import MyNewStrategy

class TestMyNewStrategy(unittest.TestCase):
    
    def setUp(self):
        self.strategy = MyNewStrategy("BTC-USDT-SWAP", 1000)
    
    def test_entry_condition(self):
        """진입 조건 테스트"""
        # RSI 30 미만 테스트 (롱 진입)
        data = {'close': 50000, 'rsi_14': 25}
        result = self.strategy.check_entry_condition(data)
        self.assertEqual(result, 'long')
        
        # RSI 70 초과 테스트 (숏 진입)
        data = {'close': 50000, 'rsi_14': 75}
        result = self.strategy.check_entry_condition(data)
        self.assertEqual(result, 'short')
    
    def test_position_management(self):
        """포지션 관리 테스트"""
        data = {'close': 50000}
        
        # 롱 포지션 진입
        entry_result = self.strategy.enter_position(data, 'long')
        self.assertTrue(self.strategy.is_position_open)
        self.assertEqual(self.strategy.position_side, 'long')
        
        # 청산
        data['close'] = 52000  # 4% 수익
        exit_result = self.strategy.exit_position(data)
        self.assertFalse(self.strategy.is_position_open)
        self.assertGreater(exit_result['pnl'], 0)

if __name__ == '__main__':
    unittest.main()
```

### 6. 전략 성능 모니터링

#### 성능 지표 추가
```python
# strategy/my_new_strategy.py에 추가
class MyNewStrategy:
    def get_performance_metrics(self) -> Dict[str, float]:
        """성능 지표 계산"""
        if self.trade_count == 0:
            return {'win_rate': 0, 'avg_return': 0, 'total_return': 0}
        
        win_rate = (self.win_count / self.trade_count) * 100
        total_return = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        avg_return = total_return / self.trade_count if self.trade_count > 0 else 0
        
        return {
            'win_rate': win_rate,
            'total_return': total_return,
            'avg_return': avg_return,
            'trade_count': self.trade_count,
            'current_capital': self.current_capital
        }
```

---

## 📊 백테스팅 및 성과 분석

### 🧪 백테스팅 실행 방법

#### 1. GUI에서 백테스팅
```
설정 단계:
1. GUI 실행 → 백테스팅 탭 이동
2. 전략 선택 (롱/숏/듀얼)
3. 테스트 기간 설정 (예: 2024-01-01 ~ 2024-12-31)
4. 초기 자본 설정 (예: $10,000)
5. 거래 심볼 선택 (예: BTC-USDT-SWAP)
6. [백테스트 시작] 버튼 클릭
```

#### 2. 백테스팅 결과 해석
```python
# 주요 성능 지표
총 수익률: +24.5% ($12,450)     # 목표: 연 20-30%
승률: 68.2% (75승 35패)         # 목표: 60% 이상
최대 낙폭(MDD): -8.3%          # 허용 한계: -15% 이내
샤프 비율: 1.85                # 목표: 1.5 이상
평균 거래시간: 2시간 15분        # 효율성 지표
```

### 📈 성과 최적화 가이드

#### 1. 파라미터 튜닝
```python
# 롱 전략 최적화 예시
LONG_STRATEGY_PARAMS = {
    "trend_ema": [140, 180],        # 150, 200에서 조정
    "entry_ema": [21, 55],          # 20, 50에서 조정
    "exit_ema": [20, 90],           # 20, 100에서 조정
    "leverage": 5,                  # 10에서 보수적으로 조정
    "trailing_stop": 0.08,          # 10%에서 8%로 조정
}

# 백테스팅으로 최적 조합 찾기
for trend_fast in range(140, 160, 5):
    for trend_slow in range(180, 220, 10):
        # 파라미터 조합 테스트
        result = backtest_strategy(trend_fast, trend_slow)
        if result['sharpe_ratio'] > best_sharpe:
            best_params = (trend_fast, trend_slow)
```

#### 2. 시장 조건별 전략 조정
```python
# 변동성 기반 자동 조정
def adjust_strategy_by_volatility(volatility: float):
    if volatility > 5%:
        # 고변동성: 보수적 접근
        leverage *= 0.8
        trailing_stop *= 1.5
        position_size *= 0.7
    elif volatility < 2%:
        # 저변동성: 적극적 접근
        leverage *= 1.2
        trailing_stop *= 0.8
        position_size *= 1.3

# 트렌드 강도 기반 조정
def adjust_by_trend_strength(trend_strength: float):
    if trend_strength > 3%:
        # 강한 트렌드: 트렌드 추종 강화
        entry_threshold *= 0.8  # 더 빨리 진입
        exit_threshold *= 1.2   # 더 늦게 청산
    else:
        # 약한 트렌드: 신중한 접근
        entry_threshold *= 1.2
        exit_threshold *= 0.8
```

### 📊 실시간 성과 모니터링

#### 포트폴리오 대시보드
```
┌─────────────────────────────────────────────────────────────┐
│ 💼 포트폴리오 성과 (실시간)                                  │
│ ┌─────────────┬──────────┬──────────┬──────────┬──────────┐ │
│ │ 전략        │ 자본     │ 승률     │ 일일PnL  │ 총PnL    │ │
│ ├─────────────┼──────────┼──────────┼──────────┼──────────┤ │
│ │ 롱 전략     │ $1,234   │ 68.9%    │ +$45.67  │ +$234.56 │ │
│ │ 숏 전략     │ $1,123   │ 62.5%    │ +$23.45  │ +$123.45 │ │
│ │ 전체        │ $2,357   │ 66.2%    │ +$69.12  │ +$357.01 │ │
│ └─────────────┴──────────┴──────────┴──────────┴──────────┘ │
│                                                             │
│ 📈 핵심 지표                                                 │
│ • 총 수익률: +35.7%                                         │
│ • 최대 낙폭: -6.8%                                          │
│ • 샤프 비율: 1.92                                           │
│ • 활성 포지션: 3개                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 문제해결

### ❌ 일반적인 오류 및 해결방법

#### 1. GUI 실행 오류
```bash
# 문제: "ModuleNotFoundError: No module named 'PyQt5'"
해결책:
pip install PyQt5==5.15.9

# 문제: "gui/__init__.py not found"
해결책:
touch gui/__init__.py  # Linux/Mac
echo. > gui/__init__.py  # Windows

# 문제: "ImportError: cannot import name 'main_window'"
해결책:
cd /path/to/CoinTrading  # 올바른 디렉토리에서 실행
python run_gui.py
```

#### 2. API 연결 문제
```bash
# 문제: "🔴 API 연결 실패"
해결책:
1. config.py에서 API 키 확인
2. OKX API 권한 설정 확인 (읽기 + 거래)
3. 인터넷 연결 상태 확인
4. 방화벽 설정 확인

# 문제: "🚨 SIGNAL LOST" 빈번 발생
해결책:
1. API 호출 한도 확인 (분당 요청 수 제한)
2. 네트워크 안정성 점검
3. OKX 서버 상태 확인
4. update_interval 값 증가 (3초 → 5초)
```

#### 3. 거래 실행 문제
```bash
# 문제: "거래가 실행되지 않음"
해결책:
1. Paper Trading 모드 확인 (실거래 원하면 False로 설정)
2. 충분한 잔고 보유 확인
3. 레버리지 설정 확인
4. 전략 조건 만족 여부 확인
5. API 거래 권한 활성화 확인

# 문제: "Position size too small" 오류
해결책:
1. 최소 주문 크기 확인 (보통 $5-10)
2. 초기 자본 증가
3. 레버리지 조정
4. 심볼별 최소 주문량 확인
```

#### 4. 성능 최적화
```python
# 메모리 사용량 최적화
# gui/widgets.py에서
MAX_CHART_POINTS = 50      # 기본값: 100
MAX_LOG_LINES = 500        # 기본값: 1000

# CPU 사용량 최적화
PRICE_UPDATE_INTERVAL = 5   # 기본값: 3초
BALANCE_UPDATE_INTERVAL = 15 # 기본값: 10초
```

### 🛡️ 안전 운영 가이드

#### 1. 초기 설정 체크리스트
```bash
✅ Paper Trading 모드로 시작
✅ 소액 자본으로 테스트 ($100 이하)
✅ 레버리지 보수적 설정 (2-5배)
✅ 손절매 설정 확인
✅ 알림 설정 테스트
✅ 백테스팅 결과 검토
```

#### 2. 위험 관리 원칙
```python
# 자본 관리 규칙
MAX_POSITION_SIZE = 0.1     # 한 포지션 최대 10%
MAX_DAILY_LOSS = 0.05       # 일일 최대 손실 5%
MAX_TOTAL_LEVERAGE = 3      # 전체 레버리지 3배 이하

# 모니터링 필수 요소
- 실시간 PnL 추적
- API 연결 상태 확인
- 포지션 크기 모니터링
- 일일/주간 손익 검토
```

#### 3. 비상 대응 절차
```python
# 긴급 상황 시 대응
1. GUI에서 [🚨 긴급 정지] 버튼 클릭
2. 모든 활성 포지션 수동 확인
3. [전체 청산] 실행
4. 시스템 로그 검토
5. 문제 원인 파악 후 재시작
```

---

## 🚀 고급 활용 및 확장

### 🔔 알림 시스템 고도화

#### 1. 다중 채널 알림 설정
```python
# config.py에 알림 설정 추가
NOTIFICATION_CONFIG = {
    "telegram": {
        "enabled": True,
        "bot_token": "your_bot_token",
        "chat_id": "your_chat_id"
    },
    "slack": {
        "enabled": True,
        "webhook_url": "your_webhook_url",
        "channel": "#trading-alerts"
    },
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your_email",
        "password": "your_app_password",
        "to_email": "alerts@yourdomain.com"
    },
    "priority_levels": {
        "critical": ["telegram", "slack", "email"],
        "warning": ["telegram", "slack"],
        "info": ["telegram"]
    }
}
```

#### 2. 조건부 알림 로직
```python
# utils/notification_manager.py
class SmartNotificationManager:
    def send_trade_alert(self, trade_data):
        """거래 알림 - 중요도별 채널 분배"""
        pnl = trade_data.get('pnl', 0)
        
        if abs(pnl) > 100:  # $100 이상 손익
            self.send_priority_alert("critical", trade_data)
        elif abs(pnl) > 50:   # $50 이상 손익
            self.send_priority_alert("warning", trade_data)
        else:
            self.send_priority_alert("info", trade_data)
    
    def send_system_alert(self, level, message):
        """시스템 알림"""
        if "API 연결 실패" in message:
            self.send_priority_alert("critical", message)
        elif "Signal Lost" in message:
            self.send_priority_alert("warning", message)
```

### 📊 고급 분석 도구

#### 1. 커스텀 지표 추가
```python
# utils/technical_indicators.py
import numpy as np
import pandas as pd

class AdvancedIndicators:
    @staticmethod
    def calculate_rsi(prices, period=14):
        """RSI 계산"""
        delta = pd.Series(prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    @staticmethod
    def calculate_macd(prices, fast=12, slow=26, signal=9):
        """MACD 계산"""
        prices = pd.Series(prices)
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        
        return {
            'macd': macd.iloc[-1],
            'signal': signal_line.iloc[-1],
            'histogram': histogram.iloc[-1]
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices, period=20, std_dev=2):
        """볼린저 밴드 계산"""
        prices = pd.Series(prices)
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band.iloc[-1],
            'middle': sma.iloc[-1],
            'lower': lower_band.iloc[-1],
            'current_price': prices.iloc[-1]
        }
```

#### 2. 다중 시간프레임 분석
```python
# strategy/multi_timeframe_strategy.py
class MultiTimeframeStrategy:
    def __init__(self, symbol, timeframes=['15m', '30m', '1h', '4h']):
        self.symbol = symbol
        self.timeframes = timeframes
        self.signals = {}
        
    def analyze_all_timeframes(self, market_data):
        """모든 시간프레임 분석"""
        combined_signal = 0
        signal_weights = {
            '15m': 0.1,  # 단기: 낮은 가중치
            '30m': 0.3,  # 기본: 중간 가중치
            '1h': 0.4,   # 중기: 높은 가중치
            '4h': 0.2    # 장기: 중간 가중치
        }
        
        for tf in self.timeframes:
            tf_data = market_data.get(tf, {})
            signal = self.analyze_timeframe(tf_data, tf)
            self.signals[tf] = signal
            
            # 가중 평균 계산
            combined_signal += signal * signal_weights.get(tf, 0.25)
        
        return self.interpret_combined_signal(combined_signal)
    
    def analyze_timeframe(self, data, timeframe):
        """개별 시간프레임 분석"""
        # EMA 기반 신호
        ema_signal = self.get_ema_signal(data)
        
        # RSI 기반 신호
        rsi_signal = self.get_rsi_signal(data)
        
        # MACD 기반 신호
        macd_signal = self.get_macd_signal(data)
        
        # 신호 결합 (각 지표별 가중치)
        combined = (ema_signal * 0.5) + (rsi_signal * 0.3) + (macd_signal * 0.2)
        
        return combined
```

### 🤖 AI 기반 최적화

#### 1. 머신러닝 파라미터 튜닝
```python
# ml/parameter_optimizer.py
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
import numpy as np

class MLParameterOptimizer:
    def __init__(self, historical_data):
        self.historical_data = historical_data
        self.model = RandomForestRegressor(n_estimators=100)
        
    def optimize_strategy_parameters(self, strategy_class):
        """ML을 이용한 전략 파라미터 최적화"""
        
        # 파라미터 범위 정의
        param_ranges = {
            'leverage': [3, 5, 7, 10],
            'trailing_stop': [0.05, 0.08, 0.10, 0.12],
            'entry_ema_fast': [18, 20, 22, 25],
            'entry_ema_slow': [45, 50, 55, 60]
        }
        
        # 백테스팅 결과 수집
        results = []
        for params in self.generate_param_combinations(param_ranges):
            strategy = strategy_class(**params)
            backtest_result = self.run_backtest(strategy)
            
            features = list(params.values())
            target = backtest_result['sharpe_ratio']
            
            results.append((features, target))
        
        # ML 모델 훈련
        X = np.array([r[0] for r in results])
        y = np.array([r[1] for r in results])
        
        self.model.fit(X, y)
        
        # 최적 파라미터 예측
        best_params = self.find_optimal_parameters(param_ranges)
        return best_params
    
    def predict_strategy_performance(self, params):
        """주어진 파라미터로 성과 예측"""
        features = np.array([list(params.values())]).reshape(1, -1)
        predicted_sharpe = self.model.predict(features)[0]
        
        return {
            'predicted_sharpe_ratio': predicted_sharpe,
            'confidence': self.model.score(features, [predicted_sharpe])
        }
```

#### 2. 시장 센티먼트 분석 통합
```python
# sentiment/market_sentiment.py
import requests
import json
from textblob import TextBlob

class MarketSentimentAnalyzer:
    def __init__(self):
        self.fear_greed_api = "https://api.alternative.me/fng/"
        self.news_sources = [
            "https://newsapi.org/v2/everything?q=bitcoin",
            "https://newsapi.org/v2/everything?q=cryptocurrency"
        ]
    
    def get_fear_greed_index(self):
        """공포&탐욕 지수 수집"""
        try:
            response = requests.get(self.fear_greed_api)
            data = response.json()
            
            current_index = int(data['data'][0]['value'])
            classification = data['data'][0]['value_classification']
            
            return {
                'index': current_index,
                'classification': classification,
                'interpretation': self.interpret_fear_greed(current_index)
            }
        except Exception as e:
            return {'index': 50, 'classification': 'Neutral', 'interpretation': 'neutral'}
    
    def analyze_news_sentiment(self):
        """뉴스 감정 분석"""
        positive_count = 0
        negative_count = 0
        total_sentiment = 0
        
        for source in self.news_sources:
            try:
                news_data = self.fetch_news(source)
                for article in news_data.get('articles', [])[:10]:  # 최근 10개 기사
                    title = article.get('title', '')
                    description = article.get('description', '')
                    
                    text = f"{title} {description}"
                    sentiment = TextBlob(text).sentiment.polarity
                    
                    total_sentiment += sentiment
                    if sentiment > 0.1:
                        positive_count += 1
                    elif sentiment < -0.1:
                        negative_count += 1
                        
            except Exception as e:
                continue
        
        avg_sentiment = total_sentiment / 20 if total_sentiment else 0
        
        return {
            'average_sentiment': avg_sentiment,
            'positive_articles': positive_count,
            'negative_articles': negative_count,
            'sentiment_score': self.normalize_sentiment(avg_sentiment)
        }
    
    def get_combined_sentiment(self):
        """종합 시장 감정 점수"""
        fear_greed = self.get_fear_greed_index()
        news_sentiment = self.analyze_news_sentiment()
        
        # 가중 평균 (공포탐욕 60%, 뉴스 40%)
        fg_normalized = fear_greed['index'] / 100
        combined_score = (fg_normalized * 0.6) + (news_sentiment['sentiment_score'] * 0.4)
        
        return {
            'combined_score': combined_score,
            'fear_greed_index': fear_greed,
            'news_sentiment': news_sentiment,
            'recommendation': self.get_strategy_recommendation(combined_score)
        }
    
    def get_strategy_recommendation(self, sentiment_score):
        """감정 점수 기반 전략 추천"""
        if sentiment_score > 0.7:
            return "bullish_aggressive"  # 강세장 공격적 전략
        elif sentiment_score > 0.5:
            return "bullish_moderate"    # 강세장 보통 전략
        elif sentiment_score < 0.3:
            return "bearish_aggressive"  # 약세장 공격적 전략
        elif sentiment_score < 0.5:
            return "bearish_moderate"    # 약세장 보통 전략
        else:
            return "neutral"             # 중립 전략
```

---

## 🔮 향후 개발 계획

### 🆕 계획된 기능 (v2.0)

#### 1. 고급 차트 기능
- **다중 시간프레임 차트**: 15분, 30분, 1시간, 4시간 동시 표시
- **기술적 지표 오버레이**: RSI, MACD, 볼린저 밴드 실시간 표시
- **거래 마킹**: 진입/청산 포인트 자동 마킹
- **패턴 인식**: 캔들스틱 패턴 자동 인식 및 알림

#### 2. AI 기반 기능
- **자동 파라미터 최적화**: 시장 조건에 따른 실시간 파라미터 조정
- **위험도 자동 조절**: AI 기반 포지션 크기 및 레버리지 동적 조정
- **가격 예측 모델**: LSTM 기반 단기 가격 예측
- **시장 체제 인식**: 트렌드/레인지 시장 자동 구분

#### 3. 모바일 및 원격 기능
- **모바일 앱**: iOS/Android 앱으로 원격 모니터링
- **웹 대시보드**: 브라우저 기반 실시간 모니터링
- **원격 제어**: 모바일에서 긴급 정지 및 포지션 제어
- **QR 코드 연동**: 간편한 모바일-PC 연동

### 🔧 시스템 개선 사항

#### 1. 성능 최적화
- **멀티스레딩**: 병렬 처리로 응답성 향상
- **데이터베이스 통합**: SQLite 기반 거래 이력 관리
- **메모리 최적화**: 대용량 데이터 효율적 처리
- **캐싱 시스템**: 중복 API 호출 최소화

#### 2. 안정성 강화
- **자동 복구**: 연결 끊김 시 자동 재연결
- **백업 시스템**: 설정 및 거래 데이터 자동 백업
- **로그 관리**: 로테이션 기반 로그 관리
- **오류 처리**: 포괄적 예외 처리 및 복구

---

## 📞 지원 및 커뮤니티

### 🤝 커뮤니티 리소스

#### 공식 채널
- **GitHub Repository**: 소스 코드 및 이슈 트래킹
- **Discord 서버**: 실시간 질문 및 토론
- **텔레그램 그룹**: 한국어 사용자 커뮤니티
- **YouTube 채널**: 사용법 튜토리얼 및 전략 설명

#### 학습 자료
- **공식 문서**: 상세한 API 및 설정 가이드
- **비디오 튜토리얼**: 초보자를 위한 단계별 가이드
- **전략 가이드**: 수익성 있는 전략 개발 방법
- **FAQ 섹션**: 자주 묻는 질문과 답변

### 🆘 기술 지원

#### 문제 신고 시 포함할 정보
```bash
# 시스템 환경
Python 버전: python --version
설치된 패키지: pip list | grep -E "(PyQt5|pyqtgraph|psutil)"

# 설정 정보 (API 키 제외)
cat config.py | grep -v "API_"

# 로그 파일
logs/gui.log (최근 100줄)
logs/trading.log (최근 100줄)
logs/errors.log (전체)

# 에러 메시지
정확한 에러 메시지 복사/붙여넣기
```

#### 자주 묻는 질문 (FAQ)

**Q: GUI가 시작되지 않습니다.**
```
A: 다음 순서로 확인:
1. Python 3.8+ 설치 확인
2. PyQt5 설치: pip install PyQt5
3. gui/__init__.py 파일 생성
4. 올바른 디렉토리에서 실행
```

**Q: API 연결이 자주 끊어집니다.**
```
A: 다음 사항 점검:
1. 안정적인 인터넷 연결
2. API 호출 한도 확인 (분당 제한)
3. 방화벽 설정 확인
4. update_interval 값 증가
```

**Q: 실제 거래가 실행되지 않습니다.**
```
A: 다음 설정 확인:
1. paper_trading = False 설정
2. 충분한 잔고 보유
3. API 거래 권한 활성화
4. 최소 주문 크기 충족
```

---

## ⚠️ 면책 조항 및 주의사항

### 📝 중요 고지사항

#### 투자 위험 고지
- **높은 위험성**: 암호화폐 거래는 높은 위험을 수반하며 원금 손실 가능성이 있습니다
- **레버리지 위험**: 레버리지 거래는 수익과 손실을 모두 증폭시킵니다
- **시장 변동성**: 암호화폐 시장은 24시간 운영되며 극심한 변동성을 보입니다
- **기술적 위험**: 소프트웨어 오류, 네트워크 문제 등으로 인한 손실 가능성

#### 사용자 책임
- **충분한 테스트**: 실제 자금 투입 전 충분한 백테스팅과 페이퍼 트레이딩 필수
- **리스크 관리**: 투자 가능한 손실 범위 내에서만 거래
- **지속적 모니터링**: 자동매매 시스템도 지속적인 감시와 관리 필요
- **규정 준수**: 거주 지역의 암호화폐 거래 관련 법규 준수

#### 시스템 한계
- **과거 성과**: 백테스팅 결과가 미래 수익을 보장하지 않음
- **시장 환경**: 급격한 시장 변화 시 전략 효과 제한 가능
- **기술적 한계**: API 장애, 네트워크 문제 등 기술적 리스크 존재

---

## 📄 라이선스 및 저작권

### MIT License

```
MIT License

Copyright (c) 2024 OKX Auto Trading System

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

**🎯 성공적인 자동매매를 위한 핵심 원칙**

1. **점진적 시작**: Paper Trading → 소액 실거래 → 점진적 확대
2. **철저한 백테스팅**: 충분한 과거 데이터로 전략 검증
3. **리스크 우선**: 수익보다 손실 방지를 우선시
4. **지속적 학습**: 시장 변화에 따른 전략 개선
5. **감정 배제**: 자동화된 규칙 기반 거래 고수

**행운을 빕니다! 🚀📈**