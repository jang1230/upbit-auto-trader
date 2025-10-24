# Phase 1.5: 백테스팅 시스템 설계 문서

**목표**: 과거 데이터를 활용한 전략 검증 시스템 구축

---

## 📋 개요

### 목적
- 실거래 전 전략의 유효성 검증
- 과거 데이터 기반 수익률 시뮬레이션
- 리스크 분석 및 최적화 근거 제공

### 예상 소요 시간
- **2~3일** (Phase 1 완료 기준)

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    백테스팅 시스템                        │
└─────────────────────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
    ┌─────▼──────┐   ┌──────▼──────┐   ┌─────▼──────┐
    │ Data Loader│   │  Backtester  │   │  Analyzer  │
    │ (다운로드)  │   │ (시뮬레이션) │   │  (분석)    │
    └─────┬──────┘   └──────┬──────┘   └─────┬──────┘
          │                 │                 │
    ┌─────▼──────┐   ┌──────▼──────┐   ┌─────▼──────┐
    │  Database  │   │   Strategy   │   │   Report   │
    │  (SQLite)  │   │  (전략 엔진) │   │  (리포트)  │
    └────────────┘   └──────────────┘   └────────────┘
```

---

## 📦 모듈 설계

### 1. **데이터 로더** (`core/data_loader.py`)

#### 책임
- Upbit API에서 과거 캔들 데이터 다운로드
- 데이터 정규화 및 검증
- 데이터베이스에 저장

#### 주요 클래스: `UpbitDataLoader`

```python
class UpbitDataLoader:
    def __init__(self, api_client: UpbitAPI):
        """UpbitAPI 클라이언트 주입"""

    def download_candles(
        self,
        market: str,
        interval: str,  # '1m', '5m', '1h', '1d'
        start_date: datetime,
        end_date: datetime,
        count: int = 200
    ) -> List[Dict]:
        """
        과거 캔들 데이터 다운로드

        Upbit API 제약:
        - 한 번에 최대 200개 캔들
        - Rate Limit: 600 req/min (시세 API)

        Returns:
            List[Dict]: 캔들 데이터 리스트
                [{
                    'timestamp': datetime,
                    'open': float,
                    'high': float,
                    'low': float,
                    'close': float,
                    'volume': float
                }]
        """

    def batch_download(
        self,
        market: str,
        interval: str,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """
        전체 기간 데이터를 배치로 다운로드

        Returns:
            int: 다운로드된 캔들 개수
        """

    def validate_data(self, candles: List[Dict]) -> bool:
        """
        데이터 무결성 검증
        - 타임스탬프 연속성
        - 가격 유효성 (OHLC 관계)
        - 볼륨 양수
        """
```

#### API 제약 처리
```python
# Upbit API 제약:
# - 최대 200개 캔들/요청
# - Rate Limit: 600 req/min

# 해결 방법:
# 1. 200개씩 나눠서 요청
# 2. Rate Limit 자동 대기 (UpbitAPI 클래스에 구현됨)
# 3. 진행률 표시

# 예: 2024년 전체 1분봉
# - 365일 * 24시간 * 60분 = 525,600개
# - 525,600 / 200 = 2,628회 요청
# - 2,628 / 600 = 약 4.4분 소요
```

---

### 2. **데이터베이스** (`core/database.py`)

#### 책임
- SQLite 데이터베이스 관리
- 캔들 데이터 CRUD
- 인덱싱 및 쿼리 최적화

#### 스키마 설계

```sql
-- 캔들 데이터 테이블
CREATE TABLE candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL,           -- 'KRW-BTC'
    interval TEXT NOT NULL,         -- '1m', '5m', '1h', '1d'
    timestamp INTEGER NOT NULL,     -- Unix timestamp (ms)
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    created_at INTEGER NOT NULL,    -- 데이터 다운로드 시각

    UNIQUE(market, interval, timestamp)
);

-- 인덱스 (쿼리 속도 향상)
CREATE INDEX idx_market_interval_timestamp
    ON candles(market, interval, timestamp);

-- 백테스팅 결과 테이블
CREATE TABLE backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,           -- UUID
    market TEXT NOT NULL,
    strategy TEXT NOT NULL,
    start_date INTEGER NOT NULL,
    end_date INTEGER NOT NULL,
    initial_capital REAL NOT NULL,
    final_capital REAL NOT NULL,
    total_return REAL NOT NULL,     -- 수익률 (%)
    max_drawdown REAL NOT NULL,     -- 최대 낙폭 (%)
    win_rate REAL NOT NULL,         -- 승률 (%)
    sharpe_ratio REAL,              -- 샤프 비율
    total_trades INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

-- 거래 내역 테이블 (백테스팅)
CREATE TABLE backtest_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    side TEXT NOT NULL,             -- 'buy', 'sell'
    price REAL NOT NULL,
    amount REAL NOT NULL,
    fee REAL NOT NULL,
    balance REAL NOT NULL,          -- 거래 후 잔액
    position REAL NOT NULL,         -- 거래 후 포지션

    FOREIGN KEY(run_id) REFERENCES backtest_results(run_id)
);
```

#### 주요 클래스: `CandleDatabase`

```python
class CandleDatabase:
    def __init__(self, db_path: str = 'data/candles.db'):
        """SQLite 데이터베이스 연결"""

    def create_tables(self):
        """테이블 생성 (없으면)"""

    def insert_candles(self, candles: List[Dict], market: str, interval: str):
        """캔들 데이터 삽입 (중복 무시)"""

    def get_candles(
        self,
        market: str,
        interval: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """기간별 캔들 데이터 조회"""

    def get_date_range(self, market: str, interval: str) -> Tuple[datetime, datetime]:
        """저장된 데이터의 시작/종료 날짜"""

    def count_candles(self, market: str, interval: str) -> int:
        """저장된 캔들 개수"""
```

---

### 3. **백테스팅 엔진** (`core/backtester.py`)

#### 책임
- 과거 데이터로 전략 시뮬레이션
- 가상 주문 실행
- 포지션 및 자금 관리

#### 주요 클래스: `Backtester`

```python
class Backtester:
    def __init__(
        self,
        strategy,                   # 전략 객체 (Phase 2에서 구현)
        initial_capital: float,     # 초기 자금
        fee_rate: float = 0.0005,   # 수수료율 (0.05%)
        slippage: float = 0.001     # 슬리피지 (0.1%)
    ):
        """백테스터 초기화"""

    def run(
        self,
        candles: pd.DataFrame,
        symbol: str
    ) -> BacktestResult:
        """
        백테스팅 실행

        프로세스:
        1. 캔들을 순회하며 전략 신호 확인
        2. 매수/매도 신호 시 가상 주문 실행
        3. 포지션 및 자금 업데이트
        4. 성과 기록

        Returns:
            BacktestResult: 백테스팅 결과
        """

    def _execute_order(
        self,
        side: str,      # 'buy' or 'sell'
        price: float,
        amount: float
    ):
        """가상 주문 실행"""
        # 1. 수수료 계산
        # 2. 슬리피지 적용
        # 3. 잔액 업데이트
        # 4. 포지션 업데이트

    def get_equity_curve(self) -> List[float]:
        """시간별 자산 곡선"""

    def get_trades(self) -> List[Dict]:
        """모든 거래 내역"""
```

#### BacktestResult 데이터 클래스

```python
@dataclass
class BacktestResult:
    run_id: str                     # UUID
    symbol: str
    strategy_name: str
    start_date: datetime
    end_date: datetime

    # 자금 정보
    initial_capital: float
    final_capital: float
    total_return: float             # %

    # 성과 지표
    max_drawdown: float             # %
    sharpe_ratio: float
    win_rate: float                 # %

    # 거래 통계
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_profit: float
    avg_loss: float

    # 시계열 데이터
    equity_curve: List[float]
    trades: List[Dict]
```

---

### 4. **성과 분석기** (`core/analyzer.py`)

#### 책임
- 백테스팅 결과 분석
- 성과 지표 계산
- 리포트 생성

#### 주요 클래스: `PerformanceAnalyzer`

```python
class PerformanceAnalyzer:
    @staticmethod
    def calculate_metrics(result: BacktestResult) -> Dict:
        """
        성과 지표 계산

        Returns:
            {
                'total_return': float,      # 총 수익률 (%)
                'cagr': float,              # 연평균 수익률 (%)
                'max_drawdown': float,      # 최대 낙폭 (%)
                'sharpe_ratio': float,      # 샤프 비율
                'sortino_ratio': float,     # 소르티노 비율
                'win_rate': float,          # 승률 (%)
                'profit_factor': float,     # 수익 팩터
                'avg_win': float,           # 평균 수익
                'avg_loss': float,          # 평균 손실
                'max_consecutive_wins': int,
                'max_consecutive_losses': int
            }
        """

    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> Tuple[float, int, int]:
        """
        최대 낙폭 계산

        Returns:
            (mdd_pct, start_idx, end_idx)
        """

    @staticmethod
    def calculate_sharpe_ratio(
        equity_curve: List[float],
        risk_free_rate: float = 0.02  # 무위험 수익률 2%
    ) -> float:
        """샤프 비율 계산"""

    @staticmethod
    def generate_report(result: BacktestResult) -> str:
        """
        텍스트 리포트 생성

        Returns:
            Markdown 형식의 리포트
        """
```

---

## 🔄 데이터 흐름

### 백테스팅 실행 흐름

```
1. 사용자 입력
   ↓
   python main.py --backtest \
       --symbol KRW-BTC \
       --start 2024-01-01 \
       --end 2024-12-31 \
       --strategy dca_rsi

2. 데이터 준비
   ↓
   CandleDatabase.get_candles()
   → 데이터 없으면 UpbitDataLoader.download_candles()
   → CandleDatabase.insert_candles()

3. 백테스팅 실행
   ↓
   Backtester.run(candles, strategy)
   → 캔들 순회
   → 전략 신호 확인 (Phase 2에서 구현)
   → 가상 주문 실행
   → 포지션 업데이트

4. 결과 분석
   ↓
   PerformanceAnalyzer.calculate_metrics()
   → 성과 지표 계산
   → 리포트 생성

5. 결과 저장
   ↓
   CandleDatabase.save_backtest_result()
   → backtest_results 테이블에 저장
   → backtest_trades 테이블에 거래 내역 저장

6. 결과 출력
   ↓
   콘솔에 리포트 출력
```

---

## 📊 성과 지표 정의

### 1. **총 수익률 (Total Return)**
```
총 수익률 (%) = (최종 자산 - 초기 자산) / 초기 자산 * 100
```

### 2. **연평균 수익률 (CAGR)**
```
CAGR = (최종 자산 / 초기 자산)^(1/연수) - 1
```

### 3. **최대 낙폭 (Maximum Drawdown, MDD)**
```
MDD = (최고점 - 최저점) / 최고점 * 100

낙폭이 클수록 위험이 큼
```

### 4. **샤프 비율 (Sharpe Ratio)**
```
Sharpe Ratio = (포트폴리오 수익률 - 무위험 수익률) / 표준편차

높을수록 위험 대비 수익이 좋음
> 1.0: 우수
> 2.0: 매우 우수
```

### 5. **승률 (Win Rate)**
```
승률 (%) = 이익 거래 수 / 전체 거래 수 * 100
```

### 6. **수익 팩터 (Profit Factor)**
```
Profit Factor = 총 이익 / 총 손실

> 1.0: 수익
> 2.0: 우수
```

---

## 🧪 테스트 시나리오

### 시나리오 1: 단순 매수-보유 (Buy & Hold)

```python
# 전략: 시작 시 100% 매수, 끝까지 보유
# 목적: 백테스팅 엔진 검증

start_date = 2024-01-01
end_date = 2024-12-31
initial_capital = 1,000,000원

예상 결과:
- BTC 2024년 실제 수익률과 일치해야 함
- 거래 횟수: 2회 (매수 1회, 매도 1회)
```

### 시나리오 2: 정기 적립식 (DCA)

```python
# 전략: 매일 10,000원씩 매수
# 목적: 분할 매수 로직 검증

start_date = 2024-01-01
end_date = 2024-12-31
daily_amount = 10,000원

예상 결과:
- 거래 횟수: 365회 (매일 매수)
- 평균 단가 계산 정확성 검증
```

### 시나리오 3: RSI 기반 전략 (Phase 2 구현 후)

```python
# 전략: RSI < 30 매수, RSI > 70 매도
# 목적: 지표 기반 전략 검증

예상 결과:
- 승률 및 수익률 확인
- 최대 낙폭 확인
```

---

## 📝 구현 순서

### Day 1: 데이터 인프라

1. **`core/database.py`** (2시간)
   - SQLite 스키마 생성
   - CRUD 메서드 구현
   - 테스트

2. **`core/data_loader.py`** (3시간)
   - Upbit API 과거 데이터 다운로드
   - 배치 다운로드 로직
   - Rate Limit 처리
   - 테스트

3. **CLI 통합** (1시간)
   - `main.py --download-data` 추가
   - 진행률 표시

### Day 2: 백테스팅 엔진

1. **`core/backtester.py`** (4시간)
   - Backtester 클래스 구현
   - 가상 주문 시스템
   - 포지션 관리
   - 테스트

2. **간단한 전략 구현** (2시간)
   - Buy & Hold 전략 (검증용)
   - DCA 전략 (검증용)

### Day 3: 분석 및 리포트

1. **`core/analyzer.py`** (3시간)
   - 성과 지표 계산
   - 리포트 생성
   - 테스트

2. **CLI 통합** (2시간)
   - `main.py --backtest` 추가
   - 결과 출력 포맷팅

3. **문서화** (1시간)
   - 사용 가이드 작성
   - 예제 추가

---

## 🎯 완성 후 사용 예시

### 1. 데이터 다운로드

```bash
# BTC 2024년 전체 1분봉 다운로드
python main.py --download-data \
    --symbol KRW-BTC \
    --interval 1m \
    --start 2024-01-01 \
    --end 2024-12-31

# 진행률:
# [████████████████████░░░░] 75% (1,971 / 2,628 requests)
# 예상 남은 시간: 1분 12초
```

### 2. 백테스팅 실행

```bash
# Buy & Hold 전략 백테스팅
python main.py --backtest \
    --symbol KRW-BTC \
    --strategy buy_hold \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --capital 1000000

# 출력:
# ════════════════════════════════════════════
#  백테스팅 결과
# ════════════════════════════════════════════
#  심볼: KRW-BTC
#  전략: Buy & Hold
#  기간: 2024-01-01 ~ 2024-12-31 (365일)
# ────────────────────────────────────────────
#  초기 자산:     1,000,000원
#  최종 자산:     1,452,000원
#  총 수익률:     +45.2%
#  연평균 수익률: +45.2%
# ────────────────────────────────────────────
#  최대 낙폭:     -18.3%
#  샤프 비율:     1.85
#  승률:          100.0%
# ────────────────────────────────────────────
#  총 거래:       2회
#  수수료 합계:   1,452원
# ════════════════════════════════════════════
```

### 3. 결과 비교

```bash
# 여러 전략 비교
python main.py --backtest-compare \
    --symbol KRW-BTC \
    --strategies buy_hold,dca,dca_rsi \
    --start 2024-01-01 \
    --end 2024-12-31

# 출력:
# ┌──────────┬──────────┬─────────┬──────────┐
# │ 전략     │ 수익률   │  MDD    │  샤프    │
# ├──────────┼──────────┼─────────┼──────────┤
# │ buy_hold │ +45.2%   │ -18.3%  │  1.85    │
# │ dca      │ +38.7%   │ -12.1%  │  2.14    │
# │ dca_rsi  │ +52.3%   │ -15.8%  │  2.35    │ ⭐
# └──────────┴──────────┴─────────┴──────────┘
```

---

## ⚠️ 주의사항 및 제약

### Upbit API 제약
- 최대 200개 캔들/요청
- Rate Limit: 600 req/min
- 과거 데이터 제공 범위 제한 있을 수 있음

### 백테스팅 한계
- **슬리피지**: 실제 체결가와 차이 발생 가능
- **유동성**: 대량 주문 시 가격 영향 미반영
- **수수료**: 고정 수수료율 가정 (실제는 변동 가능)
- **미래 편향**: 미래 정보 사용 금지 (Look-ahead bias)

### 데이터 품질
- API 오류로 일부 캔들 누락 가능
- 거래소 점검 시간 데이터 없음
- 초기 상장 코인은 데이터 부족

---

## 📚 참고 자료

### 백테스팅 관련
- **Backtrader**: Python 백테스팅 라이브러리
- **Zipline**: Quantopian 백테스팅 엔진
- **VectorBT**: 빠른 백테스팅 라이브러리

### 성과 지표
- **Sharpe Ratio**: 위험 조정 수익률
- **Sortino Ratio**: 하방 위험만 고려
- **Calmar Ratio**: MDD 대비 수익률

---

**작성일**: 2025-01-15
**Phase**: 1.5 백테스팅 시스템
**예상 완료**: 2025-01-18 (3일)
