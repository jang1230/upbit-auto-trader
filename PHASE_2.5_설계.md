# Phase 2.5 설계 문서
# Phase 2.5: Strategy Validation & Risk Management

**작성일**: 2025-10-14
**목표**: 실제 업비트 데이터로 전략 검증 및 리스크 관리 기능 추가
**예상 기간**: 1-2일

---

## 📋 목차

1. [Phase 2.5 개요](#phase-25-개요)
2. [왜 Phase 2.5가 필요한가?](#왜-phase-25가-필요한가)
3. [구현 계획](#구현-계획)
4. [리스크 관리 설계](#리스크-관리-설계)
5. [포지션 사이징 설계](#포지션-사이징-설계)
6. [검증 계획](#검증-계획)

---

## Phase 2.5 개요

### 목적
Phase 2에서 구현한 전략들을 **실제 시장 데이터**로 검증하고, **리스크 관리 기능**을 추가하여 실전 투입을 준비합니다.

### 주요 목표
1. ✅ **실제 업비트 데이터 검증**: 시뮬레이션 데이터 → 실제 BTC 데이터
2. ✅ **리스크 관리 추가**: 스톱로스, 타겟 프라이스, 최대 손실 제한
3. ✅ **포지션 사이징**: 자금 관리 전략 구현
4. ✅ **시장 환경별 분석**: 상승장/하락장/횡보장 성과 비교
5. ✅ **파라미터 최적화**: BB 전략 파라미터 미세 조정

### Phase 2와의 차이점

| 항목 | Phase 2 | Phase 2.5 |
|------|---------|-----------|
| **데이터** | 시뮬레이션 (GBM) | 실제 업비트 데이터 |
| **리스크 관리** | ❌ 없음 | ✅ 스톱로스, 타겟 |
| **포지션 사이징** | ❌ 전액 투입 | ✅ 비율 기반 |
| **시장 분석** | ❌ 단일 환경 | ✅ 다양한 환경 |
| **실전 준비도** | 🟡 보통 | 🟢 높음 |

---

## 왜 Phase 2.5가 필요한가?

### Phase 2 검증 결과의 한계

Phase 2에서 BB (20, 2.0) 전략이 +27.95% 수익률을 보였지만:

1. **시뮬레이션 데이터의 한계**
   - Geometric Brownian Motion으로 생성
   - 실제 시장의 급등락, 뉴스 이벤트 미반영
   - 극단적 변동성(Flash Crash) 없음

2. **리스크 관리 부재**
   - 손실 제한 장치 없음
   - 큰 하락에 무방비 노출
   - 포지션 크기 조절 불가

3. **실전 문제 가능성**
   ```
   시뮬레이션: +27.95% ✅
   실제 시장: ???% ❓ (검증 필요!)
   ```

### Phase 2.5의 가치

1. **안전성 확보**
   - 실제 데이터로 전략 신뢰도 확인
   - 리스크 관리로 손실 제한
   - 최악의 시나리오 대비

2. **실전 준비**
   - 다양한 시장 환경에서 성과 확인
   - 파라미터 최적화
   - 포지션 사이징으로 자금 보호

3. **심리적 안정**
   - 충분한 검증으로 확신 확보
   - 손실 제한으로 스트레스 감소
   - 실전 투입 시 불안감 해소

---

## 구현 계획

### 1단계: 실제 데이터 다운로드 (30분)

**목표**: 업비트에서 실제 BTC 거래 데이터 수집

**작업**:
```python
# pyupbit 설치 (venv 또는 --break-system-packages)
pip3 install pyupbit

# 데이터 다운로드 스크립트
import pyupbit

# 2024년 전체 데이터
btc_2024 = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=365)

# 저장
btc_2024.to_csv('data/btc_2024.csv')
```

**검증**:
- [ ] 데이터 수: 365일치 확보
- [ ] 가격 범위: 실제 시장과 일치
- [ ] 결측치: 없음 확인

---

### 2단계: 리스크 관리 기능 구현 (2-3시간)

**목표**: 손실 제한 및 익절 기능 추가

#### 2.1 스톱로스 (Stop Loss)

**개념**: 손실이 일정 수준 이상 발생하면 강제 청산

**구현**:
```python
class RiskManager:
    def __init__(self, stop_loss_pct: float = 5.0):
        """
        Args:
            stop_loss_pct: 스톱로스 비율 (%) - 기본 5%
        """
        self.stop_loss_pct = stop_loss_pct
        self.entry_price = None

    def check_stop_loss(self, current_price: float) -> bool:
        """
        스톱로스 체크

        Returns:
            True: 스톱로스 발동 (매도 필요)
            False: 정상 범위
        """
        if self.entry_price is None:
            return False

        loss_pct = ((current_price - self.entry_price) / self.entry_price) * 100

        if loss_pct <= -self.stop_loss_pct:
            logger.warning(f"🚨 스톱로스 발동: {loss_pct:.2f}% 손실")
            return True

        return False
```

**설정값**:
- 보수적: -3% 스톱로스
- 표준: -5% 스톱로스 (추천)
- 공격적: -10% 스톱로스

#### 2.2 타겟 프라이스 (Take Profit)

**개념**: 목표 수익률 도달 시 자동 익절

**구현**:
```python
class RiskManager:
    def __init__(self, take_profit_pct: float = 10.0):
        """
        Args:
            take_profit_pct: 익절 목표 (%) - 기본 10%
        """
        self.take_profit_pct = take_profit_pct

    def check_take_profit(self, current_price: float) -> bool:
        """
        타겟 프라이스 체크

        Returns:
            True: 목표 달성 (매도 필요)
            False: 목표 미달
        """
        if self.entry_price is None:
            return False

        profit_pct = ((current_price - self.entry_price) / self.entry_price) * 100

        if profit_pct >= self.take_profit_pct:
            logger.info(f"🎯 목표 달성: {profit_pct:.2f}% 수익")
            return True

        return False
```

**설정값**:
- 보수적: +5% 익절
- 표준: +10% 익절 (추천)
- 공격적: +20% 익절

#### 2.3 최대 손실 제한 (Max Loss Limit)

**개념**: 일일/주간 최대 손실 도달 시 거래 중단

**구현**:
```python
class RiskManager:
    def __init__(self, max_daily_loss_pct: float = 10.0):
        """
        Args:
            max_daily_loss_pct: 일일 최대 손실 (%)
        """
        self.max_daily_loss_pct = max_daily_loss_pct
        self.daily_pnl = 0.0
        self.today = datetime.now().date()

    def check_max_loss(self) -> bool:
        """
        최대 손실 제한 체크

        Returns:
            True: 거래 중단 필요
            False: 거래 가능
        """
        # 날짜 변경 시 리셋
        if datetime.now().date() != self.today:
            self.daily_pnl = 0.0
            self.today = datetime.now().date()

        loss_pct = (self.daily_pnl / self.initial_capital) * 100

        if loss_pct <= -self.max_daily_loss_pct:
            logger.error(f"🛑 일일 최대 손실 도달: {loss_pct:.2f}%")
            return True

        return False
```

---

### 3단계: 포지션 사이징 구현 (1-2시간)

**목표**: 자금의 일부만 투입하여 리스크 분산

#### 3.1 Fixed Fraction (고정 비율)

**개념**: 자금의 고정 비율만 투입

**구현**:
```python
class PositionSizer:
    def __init__(self, position_size_pct: float = 30.0):
        """
        Args:
            position_size_pct: 포지션 크기 (%) - 기본 30%
        """
        self.position_size_pct = position_size_pct

    def calculate_position_size(
        self,
        available_capital: float,
        current_price: float
    ) -> float:
        """
        매수 수량 계산

        Returns:
            float: 매수할 BTC 수량
        """
        # 투입 금액 = 가용 자금 * 비율
        position_value = available_capital * (self.position_size_pct / 100)

        # BTC 수량 계산
        btc_amount = position_value / current_price

        return btc_amount
```

**설정값**:
- 보수적: 10-20% 투입
- 표준: 30% 투입 (추천)
- 공격적: 50-70% 투입

#### 3.2 Kelly Criterion (켈리 기준)

**개념**: 승률과 손익비를 고려한 최적 포지션 크기

**공식**:
```
f* = (p * b - q) / b

f*: 최적 포지션 비율
p: 승률
q: 패율 (1 - p)
b: 손익비 (평균 이익 / 평균 손실)
```

**구현**:
```python
class PositionSizer:
    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        켈리 기준 계산

        Returns:
            float: 최적 포지션 비율 (0-1)
        """
        p = win_rate
        q = 1 - p
        b = avg_win / avg_loss

        kelly = (p * b - q) / b

        # 안전 계수 적용 (50% Kelly)
        kelly_adjusted = kelly * 0.5

        return max(0, min(kelly_adjusted, 0.5))  # 최대 50%
```

**예시**:
- 승률 60%, 손익비 2:1 → Kelly = 35%
- 승률 70%, 손익비 1.5:1 → Kelly = 40%
- 승률 50%, 손익비 1:1 → Kelly = 0% (거래 안 함)

---

### 4단계: 시장 환경별 분석 (2-3시간)

**목표**: 다양한 시장 환경에서 전략 성과 확인

#### 4.1 시장 환경 분류

**기준**:
```python
def classify_market_regime(returns: pd.Series, window: int = 20):
    """
    시장 환경 분류

    - 상승장: 평균 수익률 > +1%
    - 하락장: 평균 수익률 < -1%
    - 횡보장: -1% ~ +1%
    """
    rolling_return = returns.rolling(window).mean()

    if rolling_return > 0.01:
        return 'bull'  # 상승장
    elif rolling_return < -0.01:
        return 'bear'  # 하락장
    else:
        return 'sideways'  # 횡보장
```

#### 4.2 환경별 성과 분석

**구간 설정** (2024년 기준):
```
1. 상승장: 1월-3월 (비트코인 ETF 승인)
2. 하락장: 4월-6월 (조정 구간)
3. 횡보장: 7월-9월 (박스권)
4. 상승장: 10월-12월 (대선 랠리)
```

**분석 지표**:
- 구간별 수익률
- 구간별 MDD
- 구간별 승률
- 구간별 샤프 비율

---

### 5단계: 파라미터 최적화 (2-3시간)

**목표**: BB 전략의 최적 파라미터 찾기

#### 5.1 그리드 서치

**테스트 범위**:
```python
parameters = {
    'period': [15, 20, 25],
    'std_dev': [1.5, 2.0, 2.5, 3.0]
}

# 총 12개 조합 테스트
for period in parameters['period']:
    for std_dev in parameters['std_dev']:
        strategy = BollingerBands_Strategy(period, std_dev)
        result = backtest(strategy, data)
        # 성과 기록
```

#### 5.2 최적화 기준

**다중 목표 최적화**:
1. 수익률 최대화 (40%)
2. 샤프 비율 최대화 (30%)
3. MDD 최소화 (20%)
4. 거래 빈도 적정화 (10%)

**점수 계산**:
```python
score = (
    return_pct * 0.4 +
    sharpe_ratio * 10 * 0.3 +
    (1 - mdd/100) * 0.2 +
    (1 - abs(trades - 15)/15) * 0.1
)
```

---

## 리스크 관리 설계

### 전략 통합

**기존 전략 클래스 확장**:

```python
class BollingerBands_Strategy_V2(BollingerBands_Strategy):
    """
    리스크 관리 기능이 추가된 BB 전략
    """

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        stop_loss_pct: float = 5.0,
        take_profit_pct: float = 10.0,
        position_size_pct: float = 30.0
    ):
        super().__init__(period, std_dev)

        # 리스크 관리 추가
        self.risk_manager = RiskManager(stop_loss_pct, take_profit_pct)
        self.position_sizer = PositionSizer(position_size_pct)

    def generate_signal(self, candles: pd.DataFrame) -> Optional[str]:
        # 기존 BB 로직
        base_signal = super().generate_signal(candles)

        # 리스크 관리 체크
        if self.is_long():
            current_price = candles['close'].iloc[-1]

            # 스톱로스 체크
            if self.risk_manager.check_stop_loss(current_price):
                self.set_position(None)
                return 'sell'  # 강제 청산

            # 타겟 프라이스 체크
            if self.risk_manager.check_take_profit(current_price):
                self.set_position(None)
                return 'sell'  # 익절

        return base_signal
```

---

## 포지션 사이징 설계

### 백테스터 통합

**Backtester 클래스 수정**:

```python
class Backtester:
    def __init__(
        self,
        strategy,
        initial_capital: float,
        fee_rate: float = 0.0005,
        position_size_pct: float = 100.0  # 추가
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.position_size_pct = position_size_pct  # 신규

    def _execute_order(self, side: str, price: float, ...):
        if side == 'buy':
            # 기존: 전액 매수
            # amount = self.cash / price

            # 신규: 비율 기반 매수
            position_value = self.cash * (self.position_size_pct / 100)
            amount = position_value / price

            # 나머지 로직 동일
```

---

## 검증 계획

### 테스트 케이스

1. **정상 시나리오**
   - BB 전략으로 매수 → +8% 수익 → 익절 ✅
   - BB 전략으로 매수 → -3% 손실 → 스톱로스 ✅

2. **극단 시나리오**
   - 급등 +30% → 타겟 프라이스 작동 확인
   - 급락 -20% → 스톱로스 작동 확인
   - Flash Crash → 최대 손실 제한 확인

3. **포지션 사이징**
   - 30% 투입 → 나머지 70% 보존 확인
   - 연속 손실 → 자금 고갈 방지 확인

### 성공 기준

| 항목 | 목표 | 측정 방법 |
|------|------|-----------|
| **수익률** | Phase 2 대비 -10% 이내 | 백테스팅 결과 |
| **MDD** | Phase 2 대비 개선 | 최대 낙폭 비교 |
| **스톱로스** | 100% 작동 | 테스트 케이스 |
| **타겟 프라이스** | 100% 작동 | 테스트 케이스 |
| **포지션 사이징** | 설정값 준수 | 거래 내역 확인 |

### 검증 체크리스트

- [ ] 실제 데이터 다운로드 완료
- [ ] 전략 재검증 완료 (Phase 2 결과와 비교)
- [ ] 리스크 관리 기능 구현 완료
- [ ] 리스크 관리 테스트 통과
- [ ] 포지션 사이징 구현 완료
- [ ] 포지션 사이징 테스트 통과
- [ ] 시장 환경별 분석 완료
- [ ] 파라미터 최적화 완료
- [ ] Phase 2.5 완료 보고서 작성

---

## 예상 결과

### Phase 2 vs Phase 2.5 비교

| 지표 | Phase 2 (시뮬레이션) | Phase 2.5 (실제 + 리스크 관리) 예상 |
|------|---------------------|----------------------------------|
| 수익률 | +27.95% | +15-20% (보수적) |
| MDD | 7.37% | 5-6% (개선) |
| 승률 | 100% | 80-90% (현실적) |
| 거래 수 | 11회 | 12-15회 |
| 최대 손실 | 제한 없음 | -5% 제한 |

**예상 개선점**:
- ✅ 실제 시장 데이터로 신뢰도 확보
- ✅ 리스크 관리로 안전성 향상
- ✅ 포지션 사이징으로 자금 보호
- ✅ 다양한 시장 환경 대응 능력 확인

---

## 다음 단계 (Phase 2.75)

Phase 2.5 완료 후:
- 실시간 페이퍼 트레이딩 구현
- 텔레그램 알림 연동
- 버그 및 엣지 케이스 발견

---

**작성자**: Claude (AI Assistant)
**검토일**: 2025-10-14
**버전**: 1.0
