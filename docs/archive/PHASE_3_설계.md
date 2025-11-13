# Phase 3 설계 문서
# Phase 3 Design Document

**작성일**: 2025-10-14
**Phase**: Phase 3 - 실전 자동매매 시스템 구축
**상태**: 🚧 설계 중

---

## 📋 목차

1. [개요](#개요)
2. [Phase 2.5 완료 상태](#phase-25-완료-상태)
3. [Phase 3 목표](#phase-3-목표)
4. [시스템 아키텍처](#시스템-아키텍처)
5. [구현 계획](#구현-계획)
6. [페이퍼 트레이딩 계획](#페이퍼-트레이딩-계획)
7. [실전 배포 체크리스트](#실전-배포-체크리스트)

---

## 개요

Phase 3에서는 Phase 2.5에서 검증된 전략을 실제 시장에 배포하기 위한 **실전 자동매매 시스템**을 구축합니다.

### 핵심 원칙
- 🛡️ **안전 제일**: 충분한 페이퍼 트레이딩 후 실전 배포
- 📊 **투명성**: 모든 거래와 결정 과정 기록 및 알림
- 🔄 **자동화**: 사람의 개입 없이 24/7 자동 운영
- ⚡ **신뢰성**: 장애 상황 대비 및 자동 복구

---

## Phase 2.5 완료 상태

### 검증된 전략

**BB (20, 2.5) + 기본 리스크 관리**:
```python
# 전략
strategy = BollingerBands_Strategy(period=20, std_dev=2.5)

# 리스크 관리
risk_manager = RiskManager(
    stop_loss_pct=5.0,      # 스톱로스 -5%
    take_profit_pct=10.0,   # 타겟 프라이스 +10%
    max_daily_loss_pct=10.0 # 일일 최대 손실 -10%
)
```

**예상 성과** (실제 데이터 기준):
- 연간 수익률: +8.22%
- 샤프 비율: 0.50
- 최대 낙폭: 7.95%
- 승률: 66.7%
- 거래 빈도: 연간 6회

### 구현 완료 컴포넌트

✅ **백테스팅 엔진** (`core/backtester.py`)
- 시뮬레이션 및 실제 데이터 테스트
- 리스크 관리 통합
- 성과 지표 계산

✅ **기술적 지표** (`core/indicators.py`)
- RSI, MACD, Bollinger Bands
- SMA, EMA, Stochastic, ATR

✅ **전략 시스템** (`core/strategies/`)
- BaseStrategy 추상 클래스
- RSI, MACD, BB 전략 구현

✅ **리스크 관리** (`core/risk_manager.py`)
- 스톱로스, 타겟 프라이스
- 일일 손실 제한, 트레일링 스톱

---

## Phase 3 목표

### 필수 구현 항목

#### 1. 실시간 데이터 연동
- [ ] 업비트 웹소켓 연결
- [ ] 실시간 캔들 데이터 수신
- [ ] 데이터 버퍼링 및 관리
- [ ] 연결 끊김 자동 재연결

#### 2. 자동 주문 시스템
- [ ] 업비트 REST API 연동
- [ ] 매수/매도 주문 실행
- [ ] 주문 상태 확인
- [ ] 주문 실패 처리 및 재시도

#### 3. 모니터링 및 알림
- [ ] Telegram 봇 연동
- [ ] 매매 신호 알림
- [ ] 거래 실행 알림
- [ ] 일일 수익 리포트

#### 4. 페이퍼 트레이딩
- [ ] 가상 주문 실행 (실제 주문 없이)
- [ ] 실시간 성과 추적
- [ ] 백테스팅 결과와 비교

### 선택 구현 항목

#### 5. 고급 기능
- [ ] 웹 대시보드 (Flask/FastAPI)
- [ ] 전략 파라미터 동적 조정
- [ ] 다중 코인 지원
- [ ] 포지션 사이징 고도화

---

## 시스템 아키텍처

### 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Upbit DCA Trader                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   WebSocket  │      │  REST API    │      │ Telegram  │ │
│  │   (실시간)    │──────│  (주문)      │──────│   Bot     │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│         │                     │                     │        │
│         ▼                     ▼                     ▼        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Trading Engine (Core)                    │  │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────────────┐   │  │
│  │  │ Strategy│  │ Risk Mgr │  │  Order Manager   │   │  │
│  │  └─────────┘  └──────────┘  └──────────────────┘   │  │
│  │  ┌─────────────────────────────────────────────┐   │  │
│  │  │         State Manager & Logger              │   │  │
│  │  └─────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Database (SQLite / JSON)                      │  │
│  │  - 거래 내역                                          │  │
│  │  - 자산 변동                                          │  │
│  │  - 전략 신호                                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 컴포넌트 설명

#### 1. WebSocket Client
**역할**: 업비트로부터 실시간 시장 데이터 수신

**기능**:
- 실시간 캔들 데이터 (1분봉)
- 체결 데이터 (Tick)
- 호가 데이터 (Orderbook)

**구현**:
```python
class UpbitWebSocket:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.callbacks = {}

    async def connect(self):
        """웹소켓 연결"""

    async def subscribe_candles(self, callback):
        """캔들 데이터 구독"""

    async def on_message(self, message):
        """메시지 처리"""
```

#### 2. REST API Client
**역할**: 업비트 주문 및 계좌 정보 조회

**기능**:
- 계좌 잔고 조회
- 시장가/지정가 주문
- 주문 취소
- 주문 내역 조회

**구현**:
```python
class UpbitAPI:
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key

    def get_balance(self) -> Dict:
        """잔고 조회"""

    def buy_market_order(self, symbol: str, amount: float) -> Dict:
        """시장가 매수"""

    def sell_market_order(self, symbol: str, amount: float) -> Dict:
        """시장가 매도"""
```

#### 3. Trading Engine
**역할**: 전략 실행 및 주문 결정

**기능**:
- 실시간 캔들 데이터 버퍼링
- 전략 신호 생성
- 리스크 관리 체크
- 주문 실행 결정

**구현**:
```python
class TradingEngine:
    def __init__(
        self,
        strategy: BaseStrategy,
        risk_manager: RiskManager,
        upbit_api: UpbitAPI
    ):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.upbit_api = upbit_api
        self.candle_buffer = []

    async def on_candle_update(self, candle: Dict):
        """새 캔들 데이터 처리"""
        # 1. 버퍼에 추가
        # 2. 전략 신호 생성
        # 3. 리스크 체크
        # 4. 주문 실행

    async def execute_order(self, side: str):
        """주문 실행"""
```

#### 4. State Manager
**역할**: 시스템 상태 관리 및 영속성

**기능**:
- 현재 포지션 상태
- 거래 내역 기록
- 자산 변동 추적
- 시스템 재시작 시 상태 복원

**구현**:
```python
class StateManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save_state(self, state: Dict):
        """상태 저장"""

    def load_state(self) -> Dict:
        """상태 복원"""

    def log_trade(self, trade: Dict):
        """거래 기록"""
```

#### 5. Telegram Bot
**역할**: 사용자 알림 및 모니터링

**기능**:
- 매매 신호 알림
- 거래 실행 결과 알림
- 일일/주간 수익 리포트
- 수동 명령 (상태 조회, 정지 등)

**구현**:
```python
class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    async def send_message(self, message: str):
        """메시지 전송"""

    async def send_trade_alert(self, trade: Dict):
        """거래 알림"""

    async def send_daily_report(self, report: Dict):
        """일일 리포트"""
```

---

## 구현 계획

### Phase 3.1: 실시간 데이터 연동 (2-3일)

#### 목표
업비트 웹소켓을 통해 실시간 캔들 데이터를 받아 전략 신호를 생성

#### 작업 항목

**1. WebSocket Client 구현** (`core/upbit_websocket.py`)
```python
class UpbitWebSocket:
    """업비트 웹소켓 클라이언트"""

    async def connect(self):
        """웹소켓 연결"""

    async def subscribe_ticker(self, symbols: List[str]):
        """시세 구독"""

    async def subscribe_candle(self, symbols: List[str], unit: str = "1"):
        """캔들 구독 (1분, 3분, 5분 등)"""

    async def on_message(self, message: Dict):
        """메시지 수신 처리"""

    async def reconnect(self):
        """자동 재연결"""
```

**2. 데이터 버퍼 관리** (`core/data_buffer.py`)
```python
class CandleBuffer:
    """캔들 데이터 버퍼"""

    def __init__(self, max_size: int = 500):
        self.candles = pd.DataFrame()
        self.max_size = max_size

    def add_candle(self, candle: Dict):
        """새 캔들 추가"""

    def get_candles(self, count: int) -> pd.DataFrame:
        """최근 N개 캔들 반환"""

    def is_ready(self) -> bool:
        """전략 실행 가능 여부"""
```

**3. 실시간 신호 생성 테스트**
```python
# tests/test_realtime_signal.py

async def test_realtime_signal():
    """실시간 신호 생성 테스트"""

    # 1. 웹소켓 연결
    ws = UpbitWebSocket(["KRW-BTC"])
    await ws.connect()

    # 2. 전략 초기화
    strategy = BollingerBands_Strategy(period=20, std_dev=2.5)
    buffer = CandleBuffer(max_size=100)

    # 3. 캔들 수신 및 신호 생성
    async for candle in ws.subscribe_candle(["KRW-BTC"]):
        buffer.add_candle(candle)

        if buffer.is_ready():
            signal = strategy.generate_signal(buffer.get_candles(100))
            print(f"신호: {signal}")
```

**예상 결과**:
- ✅ 실시간 캔들 데이터 수신 성공
- ✅ 전략 신호 실시간 생성 확인
- ✅ 연결 끊김 시 자동 재연결

---

### Phase 3.2: 자동 주문 시스템 (2-3일)

#### 목표
업비트 REST API를 통해 실제 주문을 자동으로 실행

#### 작업 항목

**1. REST API Client 구현** (`core/upbit_api.py`)
```python
class UpbitAPI:
    """업비트 REST API 클라이언트"""

    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = "https://api.upbit.com/v1"

    def _generate_jwt_token(self, query: Dict) -> str:
        """JWT 토큰 생성 (인증용)"""

    def get_accounts(self) -> List[Dict]:
        """계좌 정보 조회"""

    def get_balance(self, currency: str = "KRW") -> float:
        """특정 화폐 잔고 조회"""

    def buy_market_order(self, symbol: str, price: float) -> Dict:
        """시장가 매수 (원화 금액 기준)"""

    def sell_market_order(self, symbol: str, volume: float) -> Dict:
        """시장가 매도 (코인 수량 기준)"""

    def get_order(self, order_id: str) -> Dict:
        """주문 상태 조회"""

    def cancel_order(self, order_id: str) -> Dict:
        """주문 취소"""
```

**2. Order Manager 구현** (`core/order_manager.py`)
```python
class OrderManager:
    """주문 관리자"""

    def __init__(self, upbit_api: UpbitAPI, min_order_amount: float = 5000):
        self.upbit_api = upbit_api
        self.min_order_amount = min_order_amount  # 최소 주문 금액 (원)

    async def execute_buy(self, symbol: str, amount: float) -> Dict:
        """매수 주문 실행"""
        # 1. 잔고 확인
        # 2. 최소 주문 금액 체크
        # 3. 주문 실행
        # 4. 주문 상태 확인
        # 5. 결과 반환

    async def execute_sell(self, symbol: str, volume: float) -> Dict:
        """매도 주문 실행"""

    async def wait_for_order(self, order_id: str, timeout: int = 30) -> Dict:
        """주문 완료 대기"""
```

**3. 주문 실패 처리**
```python
class OrderRetryHandler:
    """주문 재시도 핸들러"""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    async def execute_with_retry(self, order_func, *args, **kwargs):
        """주문 실행 (재시도 포함)"""
        for attempt in range(self.max_retries):
            try:
                result = await order_func(*args, **kwargs)
                return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 지수 백오프
                    continue
                raise
```

**예상 결과**:
- ✅ 계좌 잔고 조회 성공
- ✅ 매수/매도 주문 실행 성공
- ✅ 주문 실패 시 자동 재시도
- ✅ 최소 주문 금액 검증

---

### Phase 3.3: 모니터링 및 알림 (1-2일)

#### 목표
Telegram을 통한 실시간 알림 및 모니터링

#### 작업 항목

**1. Telegram Bot 구현** (`core/telegram_bot.py`)
```python
class TelegramNotifier:
    """Telegram 알림 시스템"""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.bot_url = f"https://api.telegram.org/bot{token}"

    async def send_message(self, message: str):
        """메시지 전송"""

    async def send_trade_alert(self, trade: Dict):
        """거래 알림"""
        message = f"""
🔔 거래 알림

종목: {trade['symbol']}
방향: {'매수' if trade['side'] == 'buy' else '매도'}
가격: {trade['price']:,.0f}원
수량: {trade['volume']:.8f}
금액: {trade['amount']:,.0f}원
시각: {trade['timestamp']}
        """
        await self.send_message(message)

    async def send_signal_alert(self, signal: Dict):
        """신호 알림"""

    async def send_daily_report(self, report: Dict):
        """일일 리포트"""
        message = f"""
📊 일일 리포트 ({report['date']})

시작 자산: {report['start_capital']:,.0f}원
종료 자산: {report['end_capital']:,.0f}원
수익: {report['profit']:,.0f}원 ({report['profit_pct']:+.2f}%)

거래 횟수: {report['trade_count']}회
승률: {report['win_rate']:.1f}%
        """
        await self.send_message(message)
```

**2. 알림 설정** (`config/notification_config.yaml`)
```yaml
telegram:
  token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"

notifications:
  signals: true          # 전략 신호 알림
  trades: true           # 거래 실행 알림
  daily_report: true     # 일일 리포트
  errors: true           # 에러 알림

alert_levels:
  signal: INFO
  trade: WARNING
  error: ERROR
```

**예상 결과**:
- ✅ Telegram 봇 연동 성공
- ✅ 매매 신호 실시간 알림
- ✅ 거래 실행 결과 알림
- ✅ 일일 수익 리포트 자동 전송

---

### Phase 3.4: Trading Engine 통합 (2-3일)

#### 목표
모든 컴포넌트를 통합하여 완전한 자동매매 시스템 구축

#### 작업 항목

**1. Trading Engine 구현** (`core/trading_engine.py`)
```python
class TradingEngine:
    """통합 트레이딩 엔진"""

    def __init__(
        self,
        strategy: BaseStrategy,
        risk_manager: RiskManager,
        upbit_api: UpbitAPI,
        telegram: TelegramNotifier,
        state_manager: StateManager
    ):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.upbit_api = upbit_api
        self.telegram = telegram
        self.state_manager = state_manager

        self.candle_buffer = CandleBuffer(max_size=200)
        self.order_manager = OrderManager(upbit_api)
        self.position = None  # 현재 포지션

    async def start(self):
        """시스템 시작"""
        logger.info("🚀 Trading Engine 시작")

        # 1. 상태 복원
        state = self.state_manager.load_state()
        self.position = state.get('position')

        # 2. 웹소켓 연결
        ws = UpbitWebSocket(["KRW-BTC"])
        await ws.connect()

        # 3. 캔들 데이터 수신 및 처리
        async for candle in ws.subscribe_candle(["KRW-BTC"], unit="1"):
            await self.on_candle_update(candle)

    async def on_candle_update(self, candle: Dict):
        """새 캔들 데이터 처리"""
        # 1. 버퍼에 추가
        self.candle_buffer.add_candle(candle)

        if not self.candle_buffer.is_ready():
            return

        # 2. 현재 가격 및 자산 확인
        current_price = candle['trade_price']
        balance = await self.upbit_api.get_balance('KRW')

        # 3. 리스크 관리 체크 (포지션 있을 때)
        if self.position:
            should_exit, reason = self.risk_manager.should_exit_position(
                current_price, balance, datetime.now()
            )

            if should_exit:
                await self._execute_sell(reason)
                return

        # 4. 전략 신호 생성
        signal = self.strategy.generate_signal(
            self.candle_buffer.get_candles(200)
        )

        # 5. 신호 처리
        if signal == 'buy' and not self.position:
            await self._execute_buy()
        elif signal == 'sell' and self.position:
            await self._execute_sell('strategy_signal')

    async def _execute_buy(self):
        """매수 실행"""
        # 1. 알림
        await self.telegram.send_signal_alert({
            'type': 'buy',
            'strategy': self.strategy.name
        })

        # 2. 주문 실행
        balance = await self.upbit_api.get_balance('KRW')
        result = await self.order_manager.execute_buy(
            'KRW-BTC',
            balance * 0.99  # 수수료 고려
        )

        # 3. 포지션 설정
        self.position = {
            'entry_price': result['price'],
            'volume': result['volume'],
            'entry_time': datetime.now()
        }

        # 4. 리스크 관리자 설정
        self.risk_manager.set_entry_price(result['price'])

        # 5. 상태 저장
        self.state_manager.save_state({'position': self.position})

        # 6. 알림
        await self.telegram.send_trade_alert(result)

    async def _execute_sell(self, reason: str):
        """매도 실행"""
        # 1. 주문 실행
        result = await self.order_manager.execute_sell(
            'KRW-BTC',
            self.position['volume']
        )

        # 2. 수익 계산
        profit = (result['price'] - self.position['entry_price']) / self.position['entry_price'] * 100

        # 3. 포지션 초기화
        self.position = None
        self.risk_manager.reset_position()

        # 4. 상태 저장
        self.state_manager.save_state({'position': None})
        self.state_manager.log_trade({
            'type': 'sell',
            'reason': reason,
            'profit_pct': profit,
            **result
        })

        # 5. 알림
        await self.telegram.send_trade_alert({
            **result,
            'reason': reason,
            'profit_pct': profit
        })
```

**2. 메인 실행 스크립트** (`main.py`)
```python
import asyncio
import logging
from core.trading_engine import TradingEngine
from core.strategies import BollingerBands_Strategy
from core.risk_manager import RiskManager
from core.upbit_api import UpbitAPI
from core.telegram_bot import TelegramNotifier
from core.state_manager import StateManager
from config import load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """메인 실행 함수"""
    # 1. 설정 로드
    config = load_config('config/config.yaml')

    # 2. 컴포넌트 초기화
    strategy = BollingerBands_Strategy(period=20, std_dev=2.5)
    risk_manager = RiskManager(
        stop_loss_pct=5.0,
        take_profit_pct=10.0
    )
    upbit_api = UpbitAPI(
        access_key=config['upbit']['access_key'],
        secret_key=config['upbit']['secret_key']
    )
    telegram = TelegramNotifier(
        token=config['telegram']['token'],
        chat_id=config['telegram']['chat_id']
    )
    state_manager = StateManager(db_path='data/state.db')

    # 3. Trading Engine 시작
    engine = TradingEngine(
        strategy=strategy,
        risk_manager=risk_manager,
        upbit_api=upbit_api,
        telegram=telegram,
        state_manager=state_manager
    )

    await engine.start()

if __name__ == "__main__":
    asyncio.run(main())
```

**예상 결과**:
- ✅ 실시간 신호 생성 및 주문 실행
- ✅ 리스크 관리 자동 적용
- ✅ 모든 이벤트 Telegram 알림
- ✅ 시스템 재시작 시 상태 복원

---

## 페이퍼 트레이딩 계획

### 목적
실제 자금 투입 전에 시스템 안정성과 성능을 검증

### 구현 방법

**페이퍼 트레이딩 모드** (`core/paper_trading.py`):
```python
class PaperTradingAPI(UpbitAPI):
    """페이퍼 트레이딩용 API (실제 주문 없음)"""

    def __init__(self, initial_capital: float = 10000000):
        self.capital = initial_capital
        self.btc_balance = 0.0
        self.trades = []

    async def buy_market_order(self, symbol: str, price: float) -> Dict:
        """가상 매수 주문"""
        btc_amount = price / current_market_price
        self.capital -= price
        self.btc_balance += btc_amount

        trade = {
            'side': 'buy',
            'price': current_market_price,
            'volume': btc_amount,
            'timestamp': datetime.now()
        }
        self.trades.append(trade)
        return trade

    async def sell_market_order(self, symbol: str, volume: float) -> Dict:
        """가상 매도 주문"""
        price = volume * current_market_price
        self.capital += price
        self.btc_balance -= volume

        trade = {
            'side': 'sell',
            'price': current_market_price,
            'volume': volume,
            'timestamp': datetime.now()
        }
        self.trades.append(trade)
        return trade
```

### 검증 기간
**최소 1주일** (7일) 연속 운영

### 검증 항목

#### 1. 시스템 안정성
- [ ] 24/7 중단 없이 운영
- [ ] 웹소켓 연결 끊김 시 자동 재연결
- [ ] 예외 상황 처리 (네트워크 오류, API 오류 등)

#### 2. 전략 성능
- [ ] 백테스팅 결과와 유사한 수익률
- [ ] 예상 거래 빈도 (연간 6회 → 주간 약 0.12회)
- [ ] 리스크 관리 작동 확인 (스톱로스, 타겟)

#### 3. 주문 실행
- [ ] 신호 발생 시 즉시 주문 실행
- [ ] 주문 실패 시 재시도
- [ ] 슬리피지 측정

#### 4. 알림 시스템
- [ ] 모든 신호 Telegram 알림
- [ ] 거래 실행 결과 알림
- [ ] 일일 리포트 정상 전송

### 페이퍼 트레이딩 결과 분석

**비교 지표**:
```
백테스팅 결과:
- 수익률: +8.22%
- MDD: 7.95%
- 승률: 66.7%
- 거래 빈도: 연 6회

페이퍼 트레이딩 결과 (1주일):
- 수익률: ?
- MDD: ?
- 승률: ?
- 거래 빈도: ?

차이 분석:
- 슬리피지 영향
- 실시간 신호 vs 백테스팅 신호 차이
- 시장 환경 변화
```

---

## 실전 배포 체크리스트

### 사전 준비

#### 1. 설정 파일 점검
- [ ] API 키 안전하게 관리 (환경 변수 또는 암호화)
- [ ] Telegram 봇 토큰 설정
- [ ] 최소 주문 금액 설정 (5,000원)
- [ ] 리스크 관리 파라미터 확인

#### 2. 초기 자금
- [ ] 업비트 계좌에 충분한 KRW 입금
- [ ] 권장 초기 자금: 1,000,000원 이상
- [ ] 최대 손실 가능 금액 확인

#### 3. 시스템 환경
- [ ] 24/7 운영 가능한 서버 (AWS, Azure, 자택 서버 등)
- [ ] 안정적인 인터넷 연결
- [ ] Python 3.9+ 설치
- [ ] 필요한 패키지 설치

### 실전 배포 단계

#### 1. 소액 테스트 (1일)
- [ ] 최소 금액 (10만원)으로 실전 테스트
- [ ] 1회 매매 완료 및 결과 확인
- [ ] 문제 없으면 다음 단계 진행

#### 2. 정상 운영 시작
- [ ] 전체 자금 투입
- [ ] 24/7 모니터링 (첫 주)
- [ ] 일일 결과 확인

#### 3. 지속적 모니터링
- [ ] 주간 성과 분석
- [ ] 백테스팅 결과와 비교
- [ ] 필요시 전략 파라미터 조정

### 비상 대응

#### 문제 상황별 대응

**1. 시스템 장애**
```
상황: 서버 다운, 네트워크 끊김
대응:
- 포지션 있을 경우 → 수동으로 청산
- 시스템 재시작 후 상태 복원
- 알림 시스템으로 장애 감지
```

**2. 예상치 못한 큰 손실**
```
상황: 백테스팅 대비 큰 손실 발생
대응:
- 즉시 시스템 중지
- 원인 분석 (전략 문제? 시장 변화?)
- 필요시 전략 수정 또는 중단
```

**3. API 오류**
```
상황: 업비트 API 응답 없음, 오류
대응:
- 자동 재시도 (최대 3회)
- 포지션 있을 경우 → Telegram 알림
- 수동 개입 필요 시 알림
```

---

## 타임라인

### 전체 일정 (약 2주)

| 주차 | 단계 | 작업 | 소요 시간 |
|------|------|------|-----------|
| 1주차 | Phase 3.1 | 실시간 데이터 연동 | 2-3일 |
| 1주차 | Phase 3.2 | 자동 주문 시스템 | 2-3일 |
| 1주차 | Phase 3.3 | 모니터링 및 알림 | 1-2일 |
| 2주차 | Phase 3.4 | Trading Engine 통합 | 2-3일 |
| 2주차 | Phase 3.5 | 페이퍼 트레이딩 | 7일 (최소) |
| 2주차 | Phase 3.6 | 실전 배포 | 1일 |

### 마일스톤

**Week 1 완료 시**:
- ✅ 모든 컴포넌트 구현 완료
- ✅ 통합 테스트 통과
- ✅ 페이퍼 트레이딩 시작 가능

**Week 2 완료 시**:
- ✅ 페이퍼 트레이딩 검증 완료
- ✅ 실전 배포 준비 완료
- ✅ 자동매매 시스템 운영 시작

---

## 참고 자료

### 업비트 API 문서
- REST API: https://docs.upbit.com/reference
- WebSocket API: https://docs.upbit.com/docs/upbit-quotation-websocket

### 개발 도구
- Python 3.9+
- asyncio (비동기 처리)
- websockets (웹소켓 클라이언트)
- requests (HTTP 클라이언트)
- python-telegram-bot (Telegram 연동)
- SQLite / JSON (상태 저장)

---

**작성자**: Claude (AI Assistant)
**검토일**: 2025-10-14
**버전**: 1.0
**상태**: 설계 완료, 구현 시작
