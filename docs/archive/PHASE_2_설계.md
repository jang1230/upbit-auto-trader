# Phase 2: 기술적 지표 및 전략 구현

**목표**: 백테스팅 가능한 실전 트레이딩 전략 구현

**기간**: 3일 예상

**우선순위**: Phase 1.5 완료 후 핵심 기능

---

## 📋 Phase 2 개요

### 목표
- 주요 기술적 지표 라이브러리 구축 (RSI, MACD, Bollinger Bands)
- 지표 기반 트레이딩 전략 구현
- 백테스팅으로 전략 검증
- 실전 투입 가능한 전략 선정

### 핵심 가치
- **검증된 전략**: 백테스팅으로 성과 확인된 전략만 사용
- **유연한 구조**: 새로운 전략 추가 용이
- **파라미터 최적화**: 전략별 최적 파라미터 탐색

---

## 🏗️ 시스템 아키텍처

```
Phase 2: 지표 + 전략
├── core/indicators.py          # 기술적 지표 라이브러리
├── core/strategies/
│   ├── __init__.py
│   ├── base.py                 # 전략 추상 클래스
│   ├── rsi_strategy.py         # RSI 과매수/과매도 전략
│   ├── macd_strategy.py        # MACD 크로스오버 전략
│   └── bb_strategy.py          # Bollinger Bands 돌파 전략
└── test_strategies.py          # 전략 백테스팅 스크립트
```

---

## 📊 Day 1: 기술적 지표 구현

### 1.1 indicators.py 모듈

**위치**: `core/indicators.py`

**구현할 지표**:

#### 1. RSI (Relative Strength Index)
```python
def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI 계산

    Args:
        prices: 종가 시계열
        period: 계산 기간 (기본 14)

    Returns:
        pd.Series: RSI 값 (0-100)

    해석:
        - RSI > 70: 과매수 (매도 시그널)
        - RSI < 30: 과매도 (매수 시그널)
    """
```

**알고리즘**:
1. 가격 변화량 계산: `delta = prices.diff()`
2. 상승/하락 분리: `gain = delta.where(delta > 0, 0)`, `loss = -delta.where(delta < 0, 0)`
3. 평균 계산: `avg_gain = gain.rolling(window=period).mean()`, `avg_loss = loss.rolling(window=period).mean()`
4. RS 계산: `rs = avg_gain / avg_loss`
5. RSI 계산: `rsi = 100 - (100 / (1 + rs))`

#### 2. MACD (Moving Average Convergence Divergence)
```python
def calculate_macd(
    prices: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD 계산

    Args:
        prices: 종가 시계열
        fast_period: 빠른 EMA 기간 (기본 12)
        slow_period: 느린 EMA 기간 (기본 26)
        signal_period: 시그널선 기간 (기본 9)

    Returns:
        tuple: (macd_line, signal_line, histogram)

    해석:
        - MACD > Signal: 상승 추세 (매수)
        - MACD < Signal: 하락 추세 (매도)
        - Histogram > 0: 강세
        - Histogram < 0: 약세
    """
```

**알고리즘**:
1. 빠른 EMA: `ema_fast = prices.ewm(span=fast_period, adjust=False).mean()`
2. 느린 EMA: `ema_slow = prices.ewm(span=slow_period, adjust=False).mean()`
3. MACD Line: `macd_line = ema_fast - ema_slow`
4. Signal Line: `signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()`
5. Histogram: `histogram = macd_line - signal_line`

#### 3. Bollinger Bands
```python
def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    볼린저 밴드 계산

    Args:
        prices: 종가 시계열
        period: 이동평균 기간 (기본 20)
        std_dev: 표준편차 배수 (기본 2.0)

    Returns:
        tuple: (upper_band, middle_band, lower_band)

    해석:
        - 가격 > Upper Band: 과매수 (매도)
        - 가격 < Lower Band: 과매도 (매수)
        - Band Width 좁아짐: 변동성 증가 예상
    """
```

**알고리즘**:
1. 중간선 (SMA): `middle_band = prices.rolling(window=period).mean()`
2. 표준편차: `std = prices.rolling(window=period).std()`
3. 상단 밴드: `upper_band = middle_band + (std_dev * std)`
4. 하단 밴드: `lower_band = middle_band - (std_dev * std)`

#### 4. 보조 지표
```python
def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """단순 이동평균 (Simple Moving Average)"""

def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """지수 이동평균 (Exponential Moving Average)"""
```

---

## 🎯 Day 2: 전략 구현

### 2.1 BaseStrategy (추상 클래스)

**위치**: `core/strategies/base.py`

```python
from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """
    트레이딩 전략 추상 클래스

    모든 전략은 이 클래스를 상속받아 구현합니다.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signal(self, candles: pd.DataFrame) -> str:
        """
        매매 신호 생성

        Args:
            candles: 캔들 데이터 (index: timestamp, columns: open, high, low, close, volume)

        Returns:
            str: 'buy', 'sell', None
        """
        pass

    @abstractmethod
    def get_parameters(self) -> dict:
        """전략 파라미터 반환"""
        pass
```

### 2.2 RSI Strategy

**위치**: `core/strategies/rsi_strategy.py`

**전략 로직**:
- **매수 조건**: RSI < 30 (과매도)
- **매도 조건**: RSI > 70 (과매수)
- **포지션 있을 때**: 반대 신호 대기

```python
class RSI_Strategy(BaseStrategy):
    """
    RSI 과매수/과매도 전략

    Parameters:
        - period: RSI 계산 기간 (기본 14)
        - oversold: 과매도 기준 (기본 30)
        - overbought: 과매수 기준 (기본 70)
    """

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__(f"RSI Strategy (period={period}, OS={oversold}, OB={overbought})")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.position = None  # 'long', 'short', None

    def generate_signal(self, candles: pd.DataFrame) -> str:
        # RSI 계산
        rsi = calculate_rsi(candles['close'], self.period)
        current_rsi = rsi.iloc[-1]

        # 포지션 없을 때
        if self.position is None:
            if current_rsi < self.oversold:
                self.position = 'long'
                return 'buy'

        # 롱 포지션 있을 때
        elif self.position == 'long':
            if current_rsi > self.overbought:
                self.position = None
                return 'sell'

        return None
```

### 2.3 MACD Strategy

**위치**: `core/strategies/macd_strategy.py`

**전략 로직**:
- **매수 조건**: MACD > Signal (골든 크로스)
- **매도 조건**: MACD < Signal (데드 크로스)
- **크로스오버 감지**: 이전 캔들과 현재 캔들 비교

```python
class MACD_Strategy(BaseStrategy):
    """
    MACD 크로스오버 전략

    Parameters:
        - fast_period: 빠른 EMA 기간 (기본 12)
        - slow_period: 느린 EMA 기간 (기본 26)
        - signal_period: 시그널선 기간 (기본 9)
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(f"MACD Strategy ({fast_period}/{slow_period}/{signal_period})")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.position = None

    def generate_signal(self, candles: pd.DataFrame) -> str:
        # MACD 계산
        macd_line, signal_line, _ = calculate_macd(
            candles['close'],
            self.fast_period,
            self.slow_period,
            self.signal_period
        )

        # 최근 2개 값
        prev_macd = macd_line.iloc[-2]
        curr_macd = macd_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]
        curr_signal = signal_line.iloc[-1]

        # 골든 크로스 (MACD가 Signal을 상향 돌파)
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            if self.position != 'long':
                self.position = 'long'
                return 'buy'

        # 데드 크로스 (MACD가 Signal을 하향 돌파)
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            if self.position == 'long':
                self.position = None
                return 'sell'

        return None
```

### 2.4 Bollinger Bands Strategy

**위치**: `core/strategies/bb_strategy.py`

**전략 로직**:
- **매수 조건**: 가격 < Lower Band (밴드 하단 돌파)
- **매도 조건**: 가격 > Upper Band (밴드 상단 돌파)
- **중간선 회귀 전략**: 밴드 터치 후 중간선 복귀 예상

```python
class BollingerBands_Strategy(BaseStrategy):
    """
    볼린저 밴드 돌파 전략

    Parameters:
        - period: 이동평균 기간 (기본 20)
        - std_dev: 표준편차 배수 (기본 2.0)
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(f"BB Strategy (period={period}, std={std_dev})")
        self.period = period
        self.std_dev = std_dev
        self.position = None

    def generate_signal(self, candles: pd.DataFrame) -> str:
        # 볼린저 밴드 계산
        upper_band, middle_band, lower_band = calculate_bollinger_bands(
            candles['close'],
            self.period,
            self.std_dev
        )

        current_price = candles['close'].iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_upper = upper_band.iloc[-1]

        # 하단 밴드 돌파 (매수)
        if current_price < current_lower:
            if self.position != 'long':
                self.position = 'long'
                return 'buy'

        # 상단 밴드 돌파 (매도)
        elif current_price > current_upper:
            if self.position == 'long':
                self.position = None
                return 'sell'

        return None
```

---

## 🧪 Day 3: 전략 테스트 및 최적화

### 3.1 test_strategies.py

**위치**: `test_strategies.py`

**테스트 시나리오**:
1. 각 전략별 백테스팅 실행 (2024-01-01 ~ 2024-12-31)
2. 다양한 파라미터 조합 테스트
3. 성과 비교 및 순위 매기기
4. 최적 파라미터 선정

```python
#!/usr/bin/env python3
"""
전략 백테스팅 스크립트

전략별로 백테스팅을 실행하고 성과를 비교합니다.
"""

from datetime import datetime
from core.database import CandleDatabase
from core.data_loader import UpbitDataLoader
from core.backtester import Backtester
from core.analyzer import PerformanceAnalyzer
from core.strategies.rsi_strategy import RSI_Strategy
from core.strategies.macd_strategy import MACD_Strategy
from core.strategies.bb_strategy import BollingerBands_Strategy
from api.upbit_api import UpbitAPI

# 테스트 기간
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 12, 31)
SYMBOL = 'KRW-BTC'
INTERVAL = '1d'
INITIAL_CAPITAL = 10000000  # 1000만원

# 데이터 준비
db = CandleDatabase()
api = UpbitAPI('', '')
loader = UpbitDataLoader(api, db)

# 데이터 다운로드 (필요 시)
candles = db.get_candles(SYMBOL, INTERVAL, START_DATE, END_DATE)
if candles.empty:
    print("📥 과거 데이터 다운로드 중...")
    loader.batch_download(SYMBOL, INTERVAL, START_DATE, END_DATE, show_progress=True)
    candles = db.get_candles(SYMBOL, INTERVAL, START_DATE, END_DATE)

# 전략 리스트
strategies = [
    RSI_Strategy(period=14, oversold=30, overbought=70),
    RSI_Strategy(period=14, oversold=25, overbought=75),  # 파라미터 변형
    MACD_Strategy(fast_period=12, slow_period=26, signal_period=9),
    MACD_Strategy(fast_period=10, slow_period=20, signal_period=9),  # 파라미터 변형
    BollingerBands_Strategy(period=20, std_dev=2.0),
    BollingerBands_Strategy(period=20, std_dev=2.5),  # 파라미터 변형
]

# 백테스팅 실행
results = []
for strategy in strategies:
    print(f"\n{'='*80}")
    print(f"📊 {strategy.name}")
    print('='*80)

    backtester = Backtester(
        strategy=strategy,
        initial_capital=INITIAL_CAPITAL,
        fee_rate=0.0005,
        slippage=0.001
    )

    result = backtester.run(candles, SYMBOL)

    # 성과 분석
    analyzer = PerformanceAnalyzer(risk_free_rate=0.02)
    report = analyzer.analyze(result)

    # 결과 저장
    results.append({
        'strategy': strategy.name,
        'total_return': report.total_return_pct,
        'sharpe_ratio': report.sharpe_ratio,
        'max_drawdown': report.max_drawdown_pct,
        'win_rate': report.win_rate_pct,
        'total_trades': result.total_trades
    })

    # 간단한 결과 출력
    print(f"   수익률: {report.total_return_pct:+.2f}%")
    print(f"   샤프 비율: {report.sharpe_ratio:.2f}")
    print(f"   MDD: {report.max_drawdown_pct:.2f}%")
    print(f"   승률: {report.win_rate_pct:.1f}%")
    print(f"   거래 횟수: {result.total_trades}회")

# 최종 비교
print(f"\n{'='*80}")
print("📈 전략 성과 비교")
print('='*80)

# 수익률 순으로 정렬
results_sorted = sorted(results, key=lambda x: x['total_return'], reverse=True)

for i, res in enumerate(results_sorted, 1):
    print(f"\n{i}. {res['strategy']}")
    print(f"   수익률: {res['total_return']:+.2f}% | "
          f"샤프: {res['sharpe_ratio']:.2f} | "
          f"MDD: {res['max_drawdown']:.2f}% | "
          f"승률: {res['win_rate']:.1f}%")

# 정리
api.close()
db.close()
```

### 3.2 파라미터 최적화

각 전략별로 최적 파라미터를 찾기 위한 그리드 서치:

```python
# RSI 파라미터 최적화
rsi_params = [
    {'period': 10, 'oversold': 25, 'overbought': 75},
    {'period': 14, 'oversold': 30, 'overbought': 70},
    {'period': 20, 'oversold': 35, 'overbought': 65},
]

# MACD 파라미터 최적화
macd_params = [
    {'fast': 8, 'slow': 17, 'signal': 9},
    {'fast': 12, 'slow': 26, 'signal': 9},
    {'fast': 16, 'slow': 32, 'signal': 9},
]

# BB 파라미터 최적화
bb_params = [
    {'period': 15, 'std_dev': 1.5},
    {'period': 20, 'std_dev': 2.0},
    {'period': 25, 'std_dev': 2.5},
]
```

---

## 📊 성과 평가 기준

### 주요 지표
1. **총 수익률**: 높을수록 좋음
2. **샤프 비율**: 위험 대비 수익 (>1.0 양호, >2.0 우수)
3. **MDD**: 최대 낙폭 (낮을수록 좋음, <20% 권장)
4. **승률**: 승리 거래 비율 (>50% 권장)
5. **거래 횟수**: 적절한 거래 빈도 (너무 많거나 적으면 문제)

### 종합 평가
```
점수 = (수익률 * 0.3) + (샤프비율 * 20 * 0.3) + ((100 - MDD) * 0.2) + (승률 * 0.2)
```

---

## 🔄 main.py 통합

백테스팅 모드에서 전략 선택 가능하도록 수정:

```python
# main.py --backtest 옵션에 전략 선택 추가
parser.add_argument(
    '--strategy',
    type=str,
    default='buy_hold',
    choices=['buy_hold', 'rsi', 'macd', 'bb'],
    help='백테스팅 전략 (기본: buy_hold)'
)

# 전략 로드 로직
if args.strategy == 'rsi':
    strategy = RSI_Strategy()
elif args.strategy == 'macd':
    strategy = MACD_Strategy()
elif args.strategy == 'bb':
    strategy = BollingerBands_Strategy()
else:
    strategy = SimpleStrategy()  # Buy & Hold
```

---

## ✅ 완료 기준

### Day 1
- [x] indicators.py 모듈 생성
- [x] RSI, MACD, BB 지표 구현
- [x] 지표 단위 테스트 통과

### Day 2
- [x] BaseStrategy 추상 클래스 구현
- [x] RSI_Strategy 구현
- [x] MACD_Strategy 구현
- [x] BollingerBands_Strategy 구현
- [x] 각 전략별 단위 테스트

### Day 3
- [x] test_strategies.py 작성
- [x] 2024년 전체 백테스팅 실행
- [x] 파라미터 최적화 완료
- [x] 성과 비교 보고서 생성
- [x] main.py 전략 통합

---

## 📚 참고 자료

### 기술적 지표 이론
- **RSI**: Wilder, J. W. (1978). New Concepts in Technical Trading Systems
- **MACD**: Appel, G. (1979). The Moving Average Convergence Divergence Trading Method
- **Bollinger Bands**: Bollinger, J. (1992). Using Bollinger Bands

### 구현 참고
- pandas-ta: Technical Analysis Library
- TA-Lib: Technical Analysis Library (C/Python)

---

## 🎯 Phase 2 완료 후

### Phase 3 준비사항
- 포지션 크기 조절 (Position Sizing)
- 리스크 관리 (Stop Loss, Take Profit)
- 자금 관리 (Money Management)
- 다중 전략 조합

### 실전 투입 체크리스트
- [ ] 최소 3개월 백테스팅 통과
- [ ] 샤프 비율 > 1.5
- [ ] MDD < 20%
- [ ] 승률 > 50%
- [ ] 실제 시장 테스트 (소액)

---

**Phase 2 설계 완료**
**다음**: Day 1 - 기술적 지표 구현 시작
