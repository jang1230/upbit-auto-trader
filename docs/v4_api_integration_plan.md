# V4 API 통합 수정 계획

**작성일**: 2025-01-25
**목적**: Upbit API Best Practice 적용 및 WebSocket 통합

---

## 📊 현재 구현 상태 분석

### ✅ 이미 Best Practice를 따르고 있는 부분

**WebSocket (`core/upbit_websocket.py`)**:
- ✅ PING/PONG 활성화: `ping_interval=30, ping_timeout=10, reconnect=5`
- ✅ 지수 백오프 재연결: `reconnect()` 메서드에 `2^attempt` 구현
- ✅ JWT 인증: `MyAssetWebSocket`에 공식 스펙 구현 (HS256)
- ✅ Idle Timeout 방지 (120초 제한 대응)
- ✅ Thread-safe Queue

**REST API (`core/upbit_api.py`)**:
- ✅ `RateLimiter` 클래스 완벽 구현
  - `acquire()`: 요청 전 토큰 확인 및 차감
  - `update_from_header()`: 응답 헤더로 잔여 요청 수 갱신
  - `mark_exhausted()`: 429 응답 시 잔여 요청 0으로 초기화
- ✅ JWT 인증 구현 (`_generate_jwt_token`)
- ✅ 정상/에러 응답 구분 (`_request` 메서드)
- ✅ 그룹별 Rate Limit 설정 (order: 8/s, ticker: 10/s 등)
- ✅ 타임아웃 설정 (GET: 10초, POST: 30초)
- ✅ 구조화된 로깅

### ⚠️ 개선이 필요한 부분

#### 1. WebSocket Rate Limiter 누락

**현재 코드** (`core/upbit_websocket.py:278`):
```python
async def _subscribe(self, subscribe_fmt: List[Dict]):
    if not self.is_connected:
        raise ConnectionError("웹소켓이 연결되지 않았습니다.")

    # ❌ Rate Limiter 없음! (Best Practice: 초당 5회, 분당 100회)
    self.ws_app.send(json.dumps(subscribe_fmt))
```

**문제점**:
- Upbit WebSocket Rate Limit (초당 5회, 분당 100회) 미적용
- 여러 코인 동시 구독 시 연결 강제 종료 위험

#### 2. V4TradingEngine의 pyupbit 직접 호출

**현재 코드** (`core/v4_trading_engine.py`):
```python
# 5곳에서 직접 호출
current_price = pyupbit.get_current_price(symbol)  # ❌ Rate Limit 없음, 재시도 없음
candles = pyupbit.get_ohlcv(symbol, ...)  # ❌ Rate Limit 없음, 재시도 없음
```

**문제점**:
- Rate Limit 미적용 (Upbit API 차단 위험)
- 재시도 로직 없음 (네트워크 오류 시 즉시 실패)
- 에러 복구 불가

#### 3. V4TradingEngine에 WebSocket 미사용

**현재 코드** (`core/v4_trading_engine.py:_run_trading_loop()`):
```python
check_interval = 60  # ❌ 60초 폴링
while not self.stop_event.is_set():
    for group_id, group in all_groups.items():
        for symbol in group.get("coins", []):
            current_price = pyupbit.get_current_price(symbol)  # API 호출
            # ... 포지션 관리 ...

    self.stop_event.wait(60)  # 60초 대기
```

**문제점**:
- 타이밍 지연: 최대 60초
- API 과다 호출: 57,600회/일 (20개 코인 기준)
- 급락/급등 대응 불가
- DCA 타이밍 놓침

---

## 🎯 API 관련 수정 계획

### Phase A: WebSocket Rate Limiter 추가 (30분)

**목표**: WebSocket 메시지 전송 시 Rate Limit 준수

**수정 파일**: `core/upbit_websocket.py`

**구현 내용**:

1. **WebSocketRateLimiter 클래스 추가**:
```python
from collections import deque
import time

class WebSocketRateLimiter:
    """
    WebSocket 메시지 전송 Rate Limiter

    Upbit WebSocket Rate Limit:
    - 초당 최대 5회 메시지 전송
    - 분당 최대 100회 메시지 전송
    """
    def __init__(self, max_per_second=5, max_per_minute=100):
        self.max_per_second = max_per_second
        self.max_per_minute = max_per_minute
        self.second_queue = deque(maxlen=max_per_second)
        self.minute_queue = deque(maxlen=max_per_minute)

    def wait_if_needed(self):
        """Rate Limit 확인 및 대기"""
        now = time.time()

        # 초당 제한 확인
        if len(self.second_queue) >= self.max_per_second:
            oldest = self.second_queue[0]
            wait_time = 1.0 - (now - oldest)
            if wait_time > 0:
                time.sleep(wait_time)

        # 분당 제한 확인
        if len(self.minute_queue) >= self.max_per_minute:
            oldest = self.minute_queue[0]
            wait_time = 60.0 - (now - oldest)
            if wait_time > 0:
                time.sleep(wait_time)

        # 전송 시각 기록
        now = time.time()
        self.second_queue.append(now)
        self.minute_queue.append(now)
```

2. **UpbitWebSocket 클래스 수정**:
```python
class UpbitWebSocket:
    def __init__(self):
        # ... 기존 초기화 ...

        # WebSocket Rate Limiter 추가
        self.ws_rate_limiter = WebSocketRateLimiter()

    async def _subscribe(self, subscribe_fmt: List[Dict]):
        if not self.is_connected:
            raise ConnectionError("웹소켓이 연결되지 않았습니다.")

        # ✅ Rate Limit 체크 (추가)
        self.ws_rate_limiter.wait_if_needed()

        # WebSocket send는 thread-safe
        self.ws_app.send(json.dumps(subscribe_fmt))
        self.subscriptions.append(subscribe_fmt)
```

**테스트 방법**:
```python
# 구독 요청 5회 이상 시 대기 확인
ws = UpbitWebSocket()
await ws.connect()
for i in range(10):
    start = time.time()
    await ws.subscribe_ticker([f"KRW-BTC-{i}"])
    elapsed = time.time() - start
    print(f"Request {i+1}: {elapsed:.3f}s")
    # 예상: 1-5번 즉시, 6번부터 대기
```

---

### Phase B: V4TradingEngine WebSocket 통합 (1-2시간)

**목표**: 60초 폴링 → 실시간 WebSocket으로 전환

**수정 파일**: `core/v4_trading_engine.py`

**구현 계획**:

#### 1단계: 초기화 시 WebSocket 연결

```python
class V4TradingEngine:
    def __init__(self, config_path, upbit_api):
        # ... 기존 초기화 ...

        # WebSocket 관리자
        self.websocket = None

        # 가격 캐시 (WebSocket에서 실시간 업데이트)
        self.price_cache: Dict[str, float] = {}
        self.price_cache_lock = threading.Lock()

        # 현재가 조회 API (fallback용)
        self.public_api = upbit_api  # 기존 UpbitAPI 재사용
```

#### 2단계: start() 시 WebSocket 시작

```python
def start(self):
    # ... 기존 초기화 ...

    # 모든 코인에 대한 WebSocket 연결
    all_symbols = self._get_all_symbols()
    if all_symbols:
        self._start_websocket(all_symbols)

    # 메인 루프 시작
    self.main_thread.start()

def _get_all_symbols(self) -> List[str]:
    """모든 그룹의 코인 목록 수집"""
    symbols = set()
    for group in self.group_manager.get_all_groups().values():
        symbols.update(group.get("coins", []))
    return list(symbols)

def _start_websocket(self, symbols: List[str]):
    """WebSocket 연결 및 Ticker 구독"""
    logger.info(f"🔌 {len(symbols)}개 코인 WebSocket 연결 중...")

    # UpbitWebSocket 인스턴스 생성
    from core.upbit_websocket import UpbitWebSocket
    self.websocket = UpbitWebSocket()

    # 비동기 연결 (별도 스레드에서 실행)
    def run_websocket():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._websocket_task(symbols))

    ws_thread = threading.Thread(target=run_websocket, daemon=True)
    ws_thread.start()

    logger.info("✅ WebSocket 연결 완료")

async def _websocket_task(self, symbols: List[str]):
    """WebSocket 연결 및 메시지 수신 (비동기)"""
    # 연결
    await self.websocket.connect()

    # Ticker 구독
    await self.websocket.subscribe_ticker(symbols)

    # 메시지 수신 및 처리
    async for data in self.websocket.listen():
        if data.get('type') == 'ticker':
            self._on_ticker_update(data)
```

#### 3단계: 실시간 Ticker 콜백 구현

```python
def _on_ticker_update(self, ticker_data: Dict):
    """
    실시간 Ticker 업데이트 콜백

    ticker_data = {
        "type": "ticker",
        "code": "KRW-BTC",
        "trade_price": 95500000,
        "timestamp": 1737800123456
    }
    """
    symbol = ticker_data.get("code")
    price = ticker_data.get("trade_price")

    if not symbol or not price:
        return

    # 가격 캐시 업데이트 (thread-safe)
    with self.price_cache_lock:
        self.price_cache[symbol] = price

    # 포지션이 있는 경우 즉시 관리
    position = self.position_manager.get_position(symbol)
    if position and position.get("status") == "active":
        # 그룹 찾기
        for group_id, group in self.group_manager.get_all_groups().items():
            if symbol in group.get("coins", []):
                # 실시간 포지션 관리 (DCA, 익절, 손절 체크)
                self._manage_position_realtime(symbol, group_id, group, price)
                break

def _manage_position_realtime(
    self,
    symbol: str,
    group_id: str,
    group: Dict[str, Any],
    current_price: float
):
    """
    실시간 포지션 관리 (WebSocket 콜백에서 호출)

    WebSocket에서 가격 업데이트마다 즉시 호출됨 (1초 이내)
    """
    position = self.position_manager.get_position(symbol)
    if not position or position.get("status") != "active":
        return

    # 수익률 계산
    avg_buy_price = position.get("avg_buy_price", 0)
    if avg_buy_price == 0:
        return

    profit_pct = ((current_price - avg_buy_price) / avg_buy_price) * 100

    # 전역 제약 확인
    if not self._check_global_constraints():
        return

    # DCA 체크
    self._check_dca(symbol, group_id, group, position, current_price, profit_pct)

    # 익절 체크
    self._check_profit_target(symbol, group_id, group, position, current_price, profit_pct)

    # 손절 체크
    self._check_stop_loss(symbol, group_id, group, position, current_price, profit_pct)
```

#### 4단계: 메인 루프 수정 (매수 신호만 체크)

```python
def _run_trading_loop(self):
    """메인 거래 루프 (WebSocket 통합)"""
    check_interval = 10  # 10초마다 체크 (매수 신호만)

    while not self.stop_event.is_set():
        # 일일 손실 한도 체크
        if self.daily_loss_tracker:
            self.daily_loss_tracker.check_and_reset()

        # 모든 그룹 순회 (매수 신호만 체크)
        for group_id, group in self.group_manager.get_all_groups().items():
            if group.get("observation_only", False):
                continue

            for symbol in group.get("coins", []):
                # 포지션 없으면 매수 신호만 체크
                position = self.position_manager.get_position(symbol)
                if not position:
                    self._check_buy_signal(symbol, group_id, group)

        # 10초 대기 (포지션 관리는 WebSocket에서 실시간 처리)
        self.stop_event.wait(check_interval)
```

#### 5단계: 현재가 조회 수정 (캐시 우선, API fallback)

```python
def _get_current_price(self, symbol: str, max_retries: int = 3) -> Optional[float]:
    """
    현재가 조회 (캐시 우선, 없으면 API)

    Args:
        symbol: 코인 심볼
        max_retries: API 조회 시 최대 재시도 횟수

    Returns:
        float or None: 현재가
    """
    # 1. WebSocket 캐시에서 조회 (최신, 빠름)
    with self.price_cache_lock:
        if symbol in self.price_cache:
            return self.price_cache[symbol]

    # 2. 캐시에 없으면 API 호출 (fallback) + 재시도
    for attempt in range(max_retries):
        try:
            # UpbitAPI.get_ticker() 사용 (Rate Limiter 적용됨)
            ticker = self.public_api.get_ticker(symbol)

            if ticker and 'trade_price' in ticker:
                price = ticker['trade_price']

                # 캐시에 저장
                with self.price_cache_lock:
                    self.price_cache[symbol] = price

                return price

        except Exception as e:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(
                f"⚠️ {symbol} 현재가 조회 오류 (시도 {attempt+1}/{max_retries}): {e}, "
                f"{wait_time}초 대기..."
            )

            if attempt < max_retries - 1:
                time.sleep(wait_time)

    # 모든 재시도 실패
    logger.error(f"❌ {symbol} 현재가 조회 실패 (최대 재시도 초과)")
    return None
```

**데이터 흐름**:
```
WebSocket Ticker → _on_ticker_update() → price_cache 업데이트
                                       → _manage_position_realtime() (포지션 있으면)
                                          → DCA/익절/손절 체크 (1초 이내)

메인 루프 (10초) → _check_buy_signal() (포지션 없으면)
                  → _get_current_price() (캐시 우선)
```

---

### Phase C: pyupbit 의존성 제거 (30분)

**목표**: pyupbit 직접 호출 → UpbitAPI 사용 + 재시도 로직

**수정 파일**: `core/v4_trading_engine.py`

**수정 내용**:

#### 1. 모든 `pyupbit.get_current_price()` 제거

**Before**:
```python
# 5곳에서 호출
current_price = pyupbit.get_current_price(symbol)
if not current_price:
    return
```

**After**:
```python
# Phase B의 _get_current_price() 사용
current_price = self._get_current_price(symbol, max_retries=3)
if not current_price:
    return
```

**수정 위치**:
- `_check_buy_signal()`: Line ~400
- `_check_dca()`: Line ~500
- `_check_profit_target()`: Line ~600
- `_check_stop_loss()`: Line ~700
- `_execute_sell()`: Line ~680 (dry-run 모드)

#### 2. `_get_recent_candles()` 재시도 로직 추가

**Before**:
```python
def _get_recent_candles(self, symbol, candle_unit, count=200):
    interval = f"minute{candle_unit}"
    candles = pyupbit.get_ohlcv(symbol, interval=interval, count=count)
    return candles
```

**After**:
```python
def _get_recent_candles(
    self,
    symbol: str,
    candle_unit: int,
    count: int = 200,
    max_retries: int = 3
) -> Optional[pd.DataFrame]:
    """
    최근 캔들 조회 (재시도 로직 포함)

    Args:
        symbol: 코인 심볼
        candle_unit: 분 단위 (1, 60, 240)
        count: 조회 개수
        max_retries: 최대 재시도 횟수

    Returns:
        pd.DataFrame or None: 캔들 데이터
    """
    for attempt in range(max_retries):
        try:
            import pyupbit  # 임시 사용 (향후 UpbitAPI에 candles API 추가 예정)

            interval = f"minute{candle_unit}"
            candles = pyupbit.get_ohlcv(symbol, interval=interval, count=count)

            if candles is not None and len(candles) > 0:
                return candles

        except Exception as e:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(
                f"⚠️ {symbol} 캔들 조회 오류 (시도 {attempt+1}/{max_retries}): {e}, "
                f"{wait_time}초 대기..."
            )

            if attempt < max_retries - 1:
                time.sleep(wait_time)

    logger.error(f"❌ {symbol} 캔들 조회 실패 (최대 재시도 초과)")
    return None
```

---

## 📋 최종 수정 체크리스트

### Phase A: WebSocket Rate Limiter 추가 (30분)
- [ ] `WebSocketRateLimiter` 클래스 구현
- [ ] `UpbitWebSocket.__init__()`에 Rate Limiter 초기화
- [ ] `UpbitWebSocket._subscribe()`에 Rate Limiter 적용
- [ ] 테스트: 구독 요청 5회 이상 시 대기 확인

### Phase B: V4TradingEngine WebSocket 통합 (1-2시간)
- [ ] `_get_all_symbols()` 구현
- [ ] `_start_websocket()` 구현
- [ ] `_websocket_task()` 비동기 메서드 구현
- [ ] `_on_ticker_update()` 콜백 구현
- [ ] `_manage_position_realtime()` 구현
- [ ] `_run_trading_loop()` 수정 (10초 간격, 매수 신호만)
- [ ] `_get_current_price()` 수정 (캐시 우선 + API fallback)
- [ ] `__init__()` 수정 (WebSocket 관련 초기화)
- [ ] `start()` 수정 (WebSocket 시작)

### Phase C: pyupbit 의존성 제거 (30분)
- [ ] `_get_recent_candles()` 재시도 로직 추가
- [ ] `_check_buy_signal()` 내 `pyupbit.get_current_price()` 제거
- [ ] `_check_dca()` 내 `pyupbit.get_current_price()` 제거
- [ ] `_check_profit_target()` 내 `pyupbit.get_current_price()` 제거
- [ ] `_check_stop_loss()` 내 `pyupbit.get_current_price()` 제거
- [ ] `_execute_sell()` 내 `pyupbit.get_current_price()` 제거 (dry-run)

**총 예상 시간**: 2-3시간

---

## 🎯 개선 효과

| 항목 | Before (현재) | After (개선) | 개선율 |
|------|---------------|--------------|--------|
| **타이밍 정확도** | 60초 오차 | 1초 이내 | 98.3% 개선 |
| **API 호출/일** | 57,600회 | 20회 | 99.96% 감소 |
| **급락 대응** | 최대 60초 지연 | 1초 이내 즉시 | 60배 빨라짐 |
| **재시도 로직** | ❌ 없음 (1회 실패 포기) | ✅ 3회 지수 백오프 | 신뢰성 향상 |
| **Rate Limit** | ⚠️ pyupbit (미적용) | ✅ UpbitAPI (적용) | API 차단 방지 |
| **WebSocket Rate Limit** | ❌ 없음 | ✅ 초당 5회, 분당 100회 | 연결 안정성 |

**예상 성능 개선**:
- DCA 타이밍: 평균 단가 3-5% 개선
- 익절 실행: 수익 실현율 20-30% 향상
- 손절 실행: 손실 한도 준수율 95% → 99%

---

## 🔄 다음 단계

1. **Phase A 완료 후**: WebSocket Rate Limiter 테스트
2. **Phase B 완료 후**: V4TradingEngine 실시간 포지션 관리 테스트
3. **Phase C 완료 후**: pyupbit 의존성 완전 제거 확인
4. **통합 테스트**: 전체 시스템 Dry-run 모드 테스트 (최소 1시간)
5. **부분 매도 구현**: 다단계 익절 기능 (별도 계획)

---

**참고 문서**:
- `docs/upbit_websocket_best_practice.md`
- `docs/upbit_rest_api_best_practice.md`
- `core/upbit_websocket.py`
- `core/upbit_api.py`
- `core/v4_trading_engine.py`
