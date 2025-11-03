# Upbit WebSocket 베스트 프랙티스

## 1. 연결 유지 (Keep-Alive)

### Idle Timeout
업비트 WebSocket 서버는 안정적인 연결 관리와 유지를 위한 PING/PONG Frame을 지원합니다.

**중요:** WebSocket 서버는 기본적으로 아무런 데이터도 수신/발신 되지 않은 채 **120초가 경과하면 Idle Timeout으로 WebSocket 연결을 종료**합니다.

### PING/PONG 설정 (권장)

websocket-client 라이브러리를 사용하는 경우:

```python
import websocket

ws = websocket.WebSocketApp(
    "wss://api.upbit.com/websocket/v1",
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

# 권장 설정
ws.run_forever(
    ping_interval=30,    # 30초마다 PING 전송
    ping_timeout=10,     # PONG 응답 10초 대기
    reconnect=2          # 재연결 대기 2초
)
```

**설정 값:**
- `ping_interval=30`: 30초마다 PING 프레임 전송 (120초 Idle Timeout 방지)
- `ping_timeout=10`: PONG 응답을 10초간 대기
- `reconnect=2`: 연결 끊김 시 2초 후 자동 재연결

## 2. 재연결 로직

### 지수 백오프 (Exponential Backoff)

연결 실패 시 즉시 재연결을 시도하면 서버에 부하가 발생할 수 있습니다. 지수 백오프 패턴을 사용하세요.

```python
import time

def connect_with_retry(max_retries=5):
    """재연결 로직 (지수 백오프)"""
    for attempt in range(max_retries):
        try:
            ws = create_websocket()
            ws.connect()
            return ws
        except Exception as e:
            wait_time = min(2 ** attempt, 32)  # 최대 32초
            print(f"연결 실패 (시도 {attempt + 1}/{max_retries}), {wait_time}초 후 재시도...")
            time.sleep(wait_time)

    raise ConnectionError(f"최대 재시도 횟수 초과 ({max_retries}회)")
```

**권장 설정:**
- 최대 재시도: 3-5회
- 대기 시간: 2^attempt 초 (1초 → 2초 → 4초 → 8초 → 16초)
- 최대 대기: 30-60초

## 3. Rate Limiter

### 메시지 전송 제한

Upbit WebSocket은 다음과 같은 Rate Limit을 적용합니다:

- **초당 최대 5회** 메시지 전송
- **분당 최대 100회** 메시지 전송

Rate Limit 초과 시 연결이 강제 종료될 수 있습니다.

```python
import time
from collections import deque

class RateLimiter:
    """WebSocket 메시지 전송 Rate Limiter"""

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

# 사용 예제
rate_limiter = RateLimiter()

def send_subscribe(ws, symbols):
    """Rate Limit 적용한 구독 요청"""
    rate_limiter.wait_if_needed()
    ws.send(json.dumps([
        {"ticket": "my_ticket"},
        {"type": "ticker", "codes": symbols}
    ]))
```

## 4. JWT 인증 (Private WebSocket)

### /private 엔드포인트 인증

내 자산 조회 등 Private WebSocket은 JWT 토큰 인증이 필요합니다.

```python
import jwt
import uuid
import hashlib

def generate_jwt_token(access_key, secret_key):
    """JWT 토큰 생성 (WebSocket 인증용)"""
    payload = {
        'access_key': access_key,
        'nonce': str(uuid.uuid4())
    }

    # HS256 알고리즘 사용 (Upbit 공식 스펙)
    jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
    return jwt_token

# WebSocket 연결 시 Authorization 헤더 포함
token = generate_jwt_token(access_key, secret_key)

ws = websocket.WebSocketApp(
    "wss://api.upbit.com/websocket/v1/private",
    header={
        "Authorization": f"Bearer {token}"
    },
    on_message=on_message
)
```

**주의사항:**
- JWT 토큰은 **매 연결마다 새로 생성**해야 합니다
- `nonce`는 UUID v4 사용 (중복 방지)
- 알고리즘은 **HS256** 사용 (공식 문서 명시)
- REST API와 달리 `query_hash`, `query_hash_alg` 불필요

## 5. 완전한 예제

### 프로덕션 환경 WebSocket 클래스

```python
import websocket
import json
import time
import logging
from typing import Callable, List
from collections import deque

logger = logging.getLogger(__name__)

class UpbitWebSocket:
    """
    Upbit WebSocket 클라이언트 (베스트 프랙티스 적용)

    특징:
    - PING/PONG 활성화 (Idle Timeout 방지)
    - 지수 백오프 재연결
    - Rate Limiter 적용
    - 에러 핸들링
    """

    def __init__(self, url="wss://api.upbit.com/websocket/v1"):
        self.url = url
        self.ws = None
        self.is_connected = False
        self.rate_limiter = RateLimiter()

    def connect(self, max_retries=3):
        """연결 (재시도 로직 포함)"""
        for attempt in range(max_retries):
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )

                # 베스트 프랙티스 설정
                self.ws.run_forever(
                    ping_interval=30,
                    ping_timeout=10,
                    reconnect=2
                )

                return True

            except Exception as e:
                wait_time = min(2 ** attempt, 32)
                logger.error(f"연결 실패 (시도 {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    logger.info(f"{wait_time}초 후 재시도...")
                    time.sleep(wait_time)

        logger.error(f"최대 재시도 횟수 초과 ({max_retries}회)")
        return False

    def subscribe(self, type: str, codes: List[str]):
        """구독 요청 (Rate Limiter 적용)"""
        if not self.is_connected:
            raise ConnectionError("WebSocket이 연결되지 않았습니다")

        # Rate Limit 체크
        self.rate_limiter.wait_if_needed()

        # 구독 요청 전송
        subscribe_fmt = [
            {"ticket": "upbit_ticker"},
            {"type": type, "codes": codes, "isOnlyRealtime": True}
        ]

        self.ws.send(json.dumps(subscribe_fmt))
        logger.info(f"구독 완료: {type}, {len(codes)}개 코인")

    def _on_open(self, ws):
        """연결 성공 콜백"""
        self.is_connected = True
        logger.info("✅ WebSocket 연결 성공")

    def _on_message(self, ws, message):
        """메시지 수신 콜백"""
        try:
            data = json.loads(message)
            # 메시지 처리 로직
            print(f"수신: {data.get('type')}")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")

    def _on_error(self, ws, error):
        """에러 발생 콜백"""
        logger.error(f"WebSocket 에러: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """연결 종료 콜백"""
        self.is_connected = False
        logger.warning(f"WebSocket 연결 종료 (code={close_status_code})")

    def disconnect(self):
        """연결 종료"""
        if self.ws:
            self.ws.close()
            logger.info("WebSocket 연결 종료")

class RateLimiter:
    """Rate Limiter (초당 5회, 분당 100회)"""

    def __init__(self, max_per_second=5, max_per_minute=100):
        self.max_per_second = max_per_second
        self.max_per_minute = max_per_minute
        self.second_queue = deque(maxlen=max_per_second)
        self.minute_queue = deque(maxlen=max_per_minute)

    def wait_if_needed(self):
        """Rate Limit 확인 및 대기"""
        now = time.time()

        # 초당 제한
        if len(self.second_queue) >= self.max_per_second:
            oldest = self.second_queue[0]
            wait_time = 1.0 - (now - oldest)
            if wait_time > 0:
                time.sleep(wait_time)

        # 분당 제한
        if len(self.minute_queue) >= self.max_per_minute:
            oldest = self.minute_queue[0]
            wait_time = 60.0 - (now - oldest)
            if wait_time > 0:
                time.sleep(wait_time)

        now = time.time()
        self.second_queue.append(now)
        self.minute_queue.append(now)

# 사용 예제
if __name__ == "__main__":
    ws = UpbitWebSocket()
    ws.connect()
    ws.subscribe("ticker", ["KRW-BTC", "KRW-ETH"])
```

## 6. 체크리스트

프로덕션 환경에서 Upbit WebSocket을 사용하기 전 다음 항목을 확인하세요:

- [ ] **PING/PONG 활성화**: `ping_interval=30`, `ping_timeout=10` 설정
- [ ] **재연결 로직**: 지수 백오프 패턴 적용 (최대 3-5회 재시도)
- [ ] **Rate Limiter**: 초당 5회, 분당 100회 제한 준수
- [ ] **JWT 인증**: Private WebSocket 사용 시 올바른 JWT 토큰 생성
- [ ] **에러 핸들링**: on_error, on_close 콜백 구현
- [ ] **로깅**: 연결 상태, 에러, 재연결 시도 등 로깅
- [ ] **Graceful Shutdown**: 프로그램 종료 시 WebSocket 정리

## 7. 추가 참고사항

### Idle Timeout 디버깅

120초 Idle Timeout으로 인한 연결 종료 여부를 확인하려면:

```python
import time

last_message_time = time.time()

def _on_message(self, ws, message):
    global last_message_time
    now = time.time()
    elapsed = now - last_message_time

    if elapsed > 60:
        logger.warning(f"⚠️ 메시지 수신 간격: {elapsed:.1f}초")

    last_message_time = now
    # 메시지 처리...
```

메시지 수신 간격이 120초를 넘으면 Idle Timeout으로 연결이 종료됩니다.

### 구독 코인 수 제한

한 번에 너무 많은 코인을 구독하면 메시지 처리가 지연될 수 있습니다.

**권장 사항:**
- Ticker: 최대 20-30개 코인
- Orderbook: 최대 5-10개 코인 (데이터 양이 많음)
- 필요시 여러 WebSocket 연결 사용

### 메모리 관리

WebSocket 메시지를 큐에 저장할 때 메모리 누수를 방지하세요:

```python
from collections import deque

# 최대 크기 제한 (오래된 메시지 자동 삭제)
message_queue = deque(maxlen=1000)
```

---

**작성일**: 2025-01-24
**참고**: [Upbit 공식 API 문서](https://docs.upbit.com/docs/upbit-quotation-websocket)
