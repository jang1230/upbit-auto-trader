"""
Upbit WebSocket Client (Official Structure)
업비트 웹소켓 클라이언트 (공식 예제 구조)

실시간 시세 데이터 수신:
- 현재가 (Ticker)
- 체결 (Trade)
- 호가 (Orderbook)
- 분봉 캔들 (Candle)

공식 Upbit 예제 구조 사용:
- websocket-client 라이브러리
- PING/PONG 활성화 (ping_interval=30, ping_timeout=10)
- reconnect=5 (자동 재연결)
- Callback 패턴 (on_message, on_open, on_error, on_close)

NOTE: Upbit WebSocket은 120초 Idle Timeout을 적용하므로
      30초마다 PING을 전송하여 연결을 유지합니다.

Example:
    >>> ws = UpbitWebSocket()
    >>> await ws.connect()
    >>> await ws.subscribe_ticker(['KRW-BTC'])
    >>> async for data in ws.listen():
    >>>     print(data)
"""

import json
import asyncio
import logging
import time
import uuid
import threading
import jwt as pyjwt
from typing import List, Dict, Optional, Callable, AsyncIterator
from queue import Queue
from datetime import datetime
from collections import deque

# websocket-client 라이브러리 (공식 Upbit 예제 호환)
import websocket

logger = logging.getLogger(__name__)


class WebSocketRateLimiter:
    """
    WebSocket 메시지 전송 Rate Limiter

    Upbit WebSocket Rate Limit:
    - 초당 최대 5회
    - 분당 최대 100회

    초과 시 자동으로 대기 후 전송
    """

    def __init__(self):
        """Rate Limiter 초기화"""
        self.second_window = deque(maxlen=5)    # 최근 5회 timestamp
        self.minute_window = deque(maxlen=100)  # 최근 100회 timestamp

    async def acquire(self):
        """
        메시지 전송 전 Rate Limit 체크

        초당 5회 또는 분당 100회 제한을 초과하면 자동으로 대기
        """
        now = time.time()

        # 🔍 초당 5회 제한 체크
        if len(self.second_window) >= 5:
            oldest = self.second_window[0]
            elapsed = now - oldest
            if elapsed < 1.0:
                wait_time = 1.0 - elapsed + 0.01
                logger.debug(f"⏳ WebSocket rate limit (초당 5회): {wait_time:.3f}초 대기")
                await asyncio.sleep(wait_time)
                now = time.time()

        # 🔍 분당 100회 제한 체크
        if len(self.minute_window) >= 100:
            oldest = self.minute_window[0]
            elapsed = now - oldest
            if elapsed < 60.0:
                wait_time = 60.0 - elapsed + 0.01
                logger.warning(f"⏳ WebSocket rate limit (분당 100회): {wait_time:.3f}초 대기")
                await asyncio.sleep(wait_time)
                now = time.time()

        # 타임스탬프 기록
        self.second_window.append(now)
        self.minute_window.append(now)


class UpbitWebSocket:
    """
    업비트 웹소켓 클라이언트 (공식 예제 구조)

    실시간 시장 데이터를 수신합니다.

    특징:
    - websocket-client 라이브러리 사용 (Upbit 공식 예제)
    - 자동 재연결 (reconnect=5)
    - PING/PONG 활성화 (ping_interval=30, ping_timeout=10)
    - Thread 기반 (asyncio 통합)
    """

    def __init__(self):
        """웹소켓 클라이언트 초기화"""
        self.url = "wss://api.upbit.com/websocket/v1"
        self.ws_app = None
        self.ws_thread = None
        self.is_connected = False
        self.subscriptions = []

        # 메시지 큐 (thread-safe)
        self.message_queue = Queue()

        # 종료 이벤트
        self.stop_event = threading.Event()

        # Rate Limiter (초당 5회, 분당 100회)
        self.rate_limiter = WebSocketRateLimiter()

    def _on_message(self, ws, message):
        """
        메시지 수신 콜백

        Args:
            ws: WebSocketApp 인스턴스
            message: 수신 메시지 (bytes or str)
        """
        try:
            # 바이너리 데이터 디코딩
            if isinstance(message, bytes):
                message = message.decode('utf-8')

            # JSON 파싱
            data = json.loads(message)

            # 메시지 큐에 추가 (asyncio에서 소비)
            self.message_queue.put(data)

        except Exception as e:
            logger.error(f"❌ 메시지 처리 오류: {e}", exc_info=True)

    def _on_error(self, ws, error):
        """
        에러 발생 콜백

        Args:
            ws: WebSocketApp 인스턴스
            error: 에러 객체
        """
        logger.error(f"❌ WebSocket 에러: {error}", exc_info=True)
        logger.error(f"🔍 [DEBUG] 에러 타입: {type(error)}, 내용: {str(error)}")

    def _on_close(self, ws, close_status_code, close_msg):
        """
        연결 종료 콜백

        Args:
            ws: WebSocketApp 인스턴스
            close_status_code: 종료 상태 코드
            close_msg: 종료 메시지
        """
        self.is_connected = False
        logger.warning(
            f"⚠️ WebSocket 연결 종료\n"
            f"   - 상태 코드: {close_status_code}\n"
            f"   - 메시지: {close_msg}\n"
            f"   - 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _on_open(self, ws):
        """
        연결 성공 콜백

        Args:
            ws: WebSocketApp 인스턴스
        """
        self.is_connected = True
        logger.info("✅ 업비트 WebSocket 연결 성공")

    def _run_websocket(self):
        """
        WebSocket 실행 (별도 스레드에서 실행)

        Upbit WebSocket 설정:
        - ping_interval=30: 30초마다 PING 전송 (120초 Idle Timeout 방지)
        - ping_timeout=10: PONG 응답 10초 대기
        - reconnect=5: 연결 끊김 시 5초 후 재연결

        NOTE: Upbit WebSocket은 120초간 데이터가 없으면 연결을 종료합니다.
              PING을 주기적으로 전송하여 연결을 유지합니다.
        """
        try:
            self.ws_app.run_forever(
                ping_interval=30,    # ✅ 30초마다 PING (Idle Timeout 방지)
                ping_timeout=10,     # ✅ PONG 응답 10초 대기
                reconnect=5          # ✅ 재연결 대기 시간
            )
        except Exception as e:
            logger.error(f"❌ WebSocket 실행 오류: {e}")
        finally:
            self.is_connected = False

    async def connect(self) -> bool:
        """
        웹소켓 연결

        Returns:
            bool: 연결 성공 여부
        """
        try:
            # WebSocketApp 생성
            self.ws_app = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )

            # 별도 스레드에서 WebSocket 실행
            self.ws_thread = threading.Thread(
                target=self._run_websocket,
                daemon=True
            )
            self.ws_thread.start()

            # 연결 대기 (최대 5초)
            for _ in range(50):
                if self.is_connected:
                    return True
                await asyncio.sleep(0.1)

            logger.error("❌ WebSocket 연결 타임아웃 (5초)")
            return False

        except Exception as e:
            logger.error(f"❌ WebSocket 연결 실패: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """웹소켓 연결 종료"""
        self.is_connected = False
        self.stop_event.set()

        if self.ws_app:
            try:
                self.ws_app.close()
                logger.info("WebSocket 연결 종료")
            except Exception as e:
                logger.warning(f"⚠️ WebSocket 종료 중 에러: {e}")

        # 스레드 종료 대기 (최대 2초)
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2.0)

    async def subscribe_ticker(self, symbols: List[str]):
        """
        현재가 구독

        Args:
            symbols: 심볼 리스트 (예: ['KRW-BTC', 'KRW-ETH'])
        """
        subscribe_fmt = [
            {"ticket": "upbit_ticker"},
            {
                "type": "ticker",
                "codes": symbols,
                "isOnlyRealtime": True
            }
        ]

        await self._subscribe(subscribe_fmt)
        logger.info(f"📊 Ticker 구독: {symbols}")

    async def subscribe_trade(self, symbols: List[str]):
        """
        체결 데이터 구독

        Args:
            symbols: 심볼 리스트
        """
        subscribe_fmt = [
            {"ticket": "upbit_trade"},
            {
                "type": "trade",
                "codes": symbols,
                "isOnlyRealtime": True
            }
        ]

        await self._subscribe(subscribe_fmt)
        logger.info(f"💱 Trade 구독: {symbols}")

    async def subscribe_orderbook(self, symbols: List[str]):
        """
        호가 데이터 구독

        Args:
            symbols: 심볼 리스트
        """
        subscribe_fmt = [
            {"ticket": "upbit_orderbook"},
            {
                "type": "orderbook",
                "codes": symbols,
                "isOnlyRealtime": True
            }
        ]

        await self._subscribe(subscribe_fmt)
        logger.info(f"📈 Orderbook 구독: {symbols}")

    async def _subscribe(self, subscribe_fmt: List[Dict]):
        """
        구독 요청 전송

        Args:
            subscribe_fmt: 구독 포맷
        """
        if not self.is_connected:
            raise ConnectionError("웹소켓이 연결되지 않았습니다.")

        try:
            # Rate Limit 체크 (초당 5회, 분당 100회)
            await self.rate_limiter.acquire()

            # WebSocket send는 thread-safe
            self.ws_app.send(json.dumps(subscribe_fmt))
            self.subscriptions.append(subscribe_fmt)
        except Exception as e:
            logger.error(f"❌ WebSocket 구독 실패: {e}")
            self.is_connected = False
            raise

    async def listen(self) -> AsyncIterator[Dict]:
        """
        웹소켓 메시지 수신 (Generator)

        Yields:
            Dict: 수신된 데이터
        """
        if not self.is_connected:
            raise ConnectionError("웹소켓이 연결되지 않았습니다.")

        # 🔍 디버깅: 주기적 상태 로깅
        last_status_log = time.time()
        status_log_interval = 30  # 30초마다 상태 로깅
        empty_queue_count = 0

        while self.is_connected:
            try:
                # 큐에서 메시지 가져오기 (non-blocking)
                if not self.message_queue.empty():
                    data = self.message_queue.get_nowait()
                    empty_queue_count = 0  # 메시지 받으면 카운터 리셋
                    yield data
                else:
                    # 큐가 비어있으면 잠시 대기
                    empty_queue_count += 1
                    await asyncio.sleep(0.01)

                    # 🔍 주기적 상태 로깅 (30초마다)
                    now = time.time()
                    if now - last_status_log >= status_log_interval:
                        thread_alive = self.ws_thread.is_alive() if self.ws_thread else False
                        logger.warning(
                            f"🔍 [DEBUG] WebSocket 상태 체크:\n"
                            f"   - 연결 상태: {self.is_connected}\n"
                            f"   - 스레드 살아있음: {thread_alive}\n"
                            f"   - 큐 크기: {self.message_queue.qsize()}\n"
                            f"   - 빈 큐 체크 횟수: {empty_queue_count} (30초간)\n"
                            f"   - 구독 목록: {len(self.subscriptions)}개"
                        )
                        last_status_log = now
                        empty_queue_count = 0  # 카운터 리셋

            except Exception as e:
                logger.error(f"❌ 메시지 수신 오류: {e}", exc_info=True)
                self.is_connected = False
                break

    async def listen_with_callback(self, callback: Callable):
        """
        웹소켓 메시지 수신 (Callback)

        Args:
            callback: 메시지 처리 콜백 함수
        """
        async for data in self.listen():
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"❌ 콜백 처리 오류: {e}")

    async def reconnect(self, max_retries: int = 5):
        """
        웹소켓 자동 재연결

        Note: websocket-client의 reconnect=2 설정으로 자동 재연결됨
        이 메서드는 수동 재연결이 필요한 경우에만 사용

        Args:
            max_retries: 최대 재시도 횟수
        """
        for attempt in range(max_retries):
            logger.info(f"🔄 재연결 시도 {attempt + 1}/{max_retries}")

            if await self.connect():
                # 기존 구독 복원
                for sub in self.subscriptions:
                    await self._subscribe(sub)
                logger.info("✅ 재연결 및 구독 복원 완료")
                return True

            # 지수 백오프
            await asyncio.sleep(2 ** attempt)

        logger.error(f"❌ 재연결 실패 (최대 {max_retries}회 시도)")
        return False


class CandleWebSocket(UpbitWebSocket):
    """
    캔들 데이터 전용 웹소켓 (업비트는 캔들 웹소켓 미지원)

    REST API를 통해 주기적으로 최신 캔들을 가져옵니다.
    """

    def __init__(self, interval_seconds: int = 60, upbit_api=None):
        """
        캔들 웹소켓 초기화

        Args:
            interval_seconds: 캔들 갱신 주기 (초)
            upbit_api: UpbitAPI 인스턴스 (캔들 조회용)
        """
        super().__init__()
        self.interval_seconds = interval_seconds
        self.last_candle_time = None
        self.is_running = True  # 종료 flag
        self.upbit_api = upbit_api

    async def disconnect(self):
        """캔들 웹소켓 종료"""
        self.is_running = False  # 루프 종료 flag 설정
        await super().disconnect()  # 부모 클래스의 disconnect 호출

    async def subscribe_candle(
        self,
        symbols: List[str],
        unit: str = "1"
    ) -> AsyncIterator[Dict]:
        """
        분봉 캔들 구독 (유사 구현)

        Args:
            symbols: 심볼 리스트
            unit: 분 단위 (1, 3, 5, 10, 15, 30, 60, 240)

        Yields:
            Dict: 캔들 데이터
        """
        if not self.upbit_api:
            logger.error("❌ CandleWebSocket에 UpbitAPI가 설정되지 않았습니다")
            return

        logger.info(f"🕯️ Candle 구독 시작: {symbols} ({unit}분봉)")

        consecutive_errors = 0  # 연속 에러 카운터
        max_consecutive_errors = 3  # 최대 연속 에러 허용

        while self.is_running:
            try:
                for symbol in symbols:
                    # 최신 캔들 가져오기 (UpbitAPI 사용)
                    df = self.upbit_api.get_candles(
                        symbol,
                        interval=f"minute{unit}",
                        count=1
                    )

                    if df is not None and len(df) > 0:
                        candle_time = df.index[0]

                        # 새로운 캔들인 경우에만 반환
                        if self.last_candle_time is None or candle_time > self.last_candle_time:
                            self.last_candle_time = candle_time

                            candle_data = {
                                'type': 'candle',
                                'code': symbol,
                                'timestamp': candle_time,
                                'opening_price': df['open'].iloc[0],
                                'high_price': df['high'].iloc[0],
                                'low_price': df['low'].iloc[0],
                                'trade_price': df['close'].iloc[0],
                                'candle_acc_trade_volume': df['volume'].iloc[0],
                            }

                            yield candle_data
                            consecutive_errors = 0  # 성공 시 에러 카운터 리셋

                # 다음 캔들까지 대기 (취소 가능하도록 작은 단위로 체크)
                elapsed = 0
                sleep_interval = 0.5  # 0.5초마다 체크
                while elapsed < self.interval_seconds and self.is_running:
                    await asyncio.sleep(sleep_interval)
                    elapsed += sleep_interval

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"❌ 캔들 데이터 가져오기 실패 ({consecutive_errors}/{max_consecutive_errors}): {e}")

                # 연속 에러 시 대기 시간 증가
                if consecutive_errors >= max_consecutive_errors:
                    wait_time = 10
                    logger.warning(f"⚠️ 연속 {max_consecutive_errors}회 실패, {wait_time}초 대기 후 재시도")
                else:
                    wait_time = 2

                # 에러 재시도 대기 (취소 가능하도록 작은 단위로 체크)
                elapsed = 0
                sleep_interval = 0.5
                while elapsed < wait_time and self.is_running:
                    await asyncio.sleep(sleep_interval)
                    elapsed += sleep_interval

                if self.is_running:  # 종료되지 않은 경우에만 재시도 로그
                    logger.info(f"🔄 재시도 중... (시도 {consecutive_errors}회)")


class MyAssetWebSocket:
    """
    내 자산 변동 실시간 알림 WebSocket (인증 필요)

    사용자의 계좌에서 자산 변동(매수/매도)이 발생할 때 실시간으로 알림을 받습니다.
    - 10초 polling 대신 즉시 감지
    - API 호출 불필요
    - JWT 인증 필요

    공식 Upbit 예제 구조 사용:
    - websocket-client 라이브러리
    - PING/PONG 활성화 (ping_interval=30, ping_timeout=10)
    - reconnect=5 (자동 재연결)

    Example:
        >>> ws = MyAssetWebSocket(access_key, secret_key)
        >>> await ws.connect()
        >>> await ws.subscribe_myasset()
        >>> async for data in ws.listen():
        >>>     print(f"자산 변동: {data}")
    """

    def __init__(self, access_key: str, secret_key: str):
        """
        내 자산 WebSocket 초기화

        Args:
            access_key: Upbit Access Key
            secret_key: Upbit Secret Key
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.url = "wss://api.upbit.com/websocket/v1/private"
        self.ws_app = None
        self.ws_thread = None
        self.is_connected = False

        # 메시지 큐 (thread-safe)
        self.message_queue = Queue()

        # 종료 이벤트
        self.stop_event = threading.Event()

        # Rate Limiter (초당 5회, 분당 100회)
        self.rate_limiter = WebSocketRateLimiter()

    def _generate_jwt_token(self) -> str:
        """
        JWT 토큰 생성 (WebSocket 인증용)

        공식 Upbit JWT 스펙:
        - payload: access_key, nonce (timestamp 없음)
        - algorithm: HS256 (공식 문서 명시)

        Returns:
            str: JWT 토큰 (Bearer 제외)
        """
        # 🔧 공식 Upbit JWT 스펙에 맞춤 (HS256 사용)
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4())
        }

        jwt_token = pyjwt.encode(payload, self.secret_key, algorithm='HS256')
        return jwt_token

    def _on_message(self, ws, message):
        """
        메시지 수신 콜백

        Args:
            ws: WebSocketApp 인스턴스
            message: 수신 메시지 (bytes or str)
        """
        try:
            # 바이너리 데이터 디코딩
            if isinstance(message, bytes):
                message = message.decode('utf-8')

            # JSON 파싱
            try:
                data = json.loads(message)
            except json.JSONDecodeError as je:
                logger.error(f"❌ JSON 파싱 실패: {je}, 원본: {message[:100]}")
                return

            # JSON_LIST 형식 처리 (배열의 모든 요소를 순회)
            if isinstance(data, list):
                for item in data:
                    if item.get('type') == 'myAsset':
                        self.message_queue.put(item)
            else:
                # DEFAULT 형식 (단일 객체)
                if data.get('type') == 'myAsset':
                    self.message_queue.put(data)

        except Exception as e:
            logger.error(f"❌ MyAsset 메시지 처리 오류: {e}")

    def _on_error(self, ws, error):
        """
        에러 발생 콜백

        Args:
            ws: WebSocketApp 인스턴스
            error: 에러 객체
        """
        logger.error(f"❌ MyAsset WebSocket 에러: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """
        연결 종료 콜백

        Args:
            ws: WebSocketApp 인스턴스
            close_status_code: 종료 상태 코드
            close_msg: 종료 메시지
        """
        self.is_connected = False
        logger.warning(f"⚠️ MyAsset WebSocket 연결 종료 (code={close_status_code}, msg={close_msg})")

    def _on_open(self, ws):
        """
        연결 성공 콜백

        Args:
            ws: WebSocketApp 인스턴스
        """
        self.is_connected = True
        logger.info("✅ MyAsset WebSocket 연결 성공 (인증 완료)")

    def _run_websocket(self):
        """
        WebSocket 실행 (별도 스레드에서 실행)

        Upbit WebSocket 설정:
        - ping_interval=30: 30초마다 PING 전송 (120초 Idle Timeout 방지)
        - ping_timeout=10: PONG 응답 10초 대기
        - reconnect=5: 연결 끊김 시 5초 후 재연결

        NOTE: Upbit WebSocket은 120초간 데이터가 없으면 연결을 종료합니다.
              PING을 주기적으로 전송하여 연결을 유지합니다.
        """
        try:
            self.ws_app.run_forever(
                ping_interval=30,    # ✅ 30초마다 PING (Idle Timeout 방지)
                ping_timeout=10,     # ✅ PONG 응답 10초 대기
                reconnect=5          # ✅ 재연결 대기 시간
            )
        except Exception as e:
            logger.error(f"❌ MyAsset WebSocket 실행 오류: {e}")
        finally:
            self.is_connected = False

    async def connect(self) -> bool:
        """
        WebSocket 연결 (JWT 인증 포함)

        Returns:
            bool: 연결 성공 여부
        """
        try:
            # JWT 토큰 생성
            token = self._generate_jwt_token()

            # WebSocketApp 생성 (Authorization 헤더 포함)
            self.ws_app = websocket.WebSocketApp(
                self.url,
                header={
                    "Authorization": f"Bearer {token}"
                },
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )

            # 별도 스레드에서 WebSocket 실행
            self.ws_thread = threading.Thread(
                target=self._run_websocket,
                daemon=True
            )
            self.ws_thread.start()

            # 연결 대기 (최대 5초)
            for _ in range(50):
                if self.is_connected:
                    return True
                await asyncio.sleep(0.1)

            logger.error("❌ MyAsset WebSocket 연결 타임아웃 (5초)")
            return False

        except Exception as e:
            logger.error(f"❌ MyAsset WebSocket 연결 실패: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """WebSocket 연결 종료"""
        self.is_connected = False
        self.stop_event.set()

        if self.ws_app:
            try:
                self.ws_app.close()
                logger.info("MyAsset WebSocket 연결 종료")
            except Exception as e:
                logger.warning(f"⚠️ MyAsset WebSocket 종료 중 에러: {e}")

        # 스레드 종료 대기 (최대 2초)
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2.0)

    async def subscribe_myasset(self):
        """
        내 자산 구독

        자산 변동(매수/매도) 발생 시 실시간 알림 수신

        주의:
        - codes 파라미터 없음 (전체 자산 자동 구독)
        - 최초 연결 시 수분간 데이터 수신 안 될 수 있음 (Upbit 정책)
        - 자산 변동 없으면 데이터 수신 없음 (정상)
        """
        if not self.is_connected:
            raise ConnectionError("WebSocket이 연결되지 않았습니다.")

        # myAsset 구독 요청 (codes 파라미터 없음!)
        subscribe_fmt = [
            {"ticket": str(uuid.uuid4())},
            {"type": "myAsset"},
            {"format": "JSON_LIST"}  # 공식 문서 권장 (효율적인 리스트 형식)
        ]

        try:
            # Rate Limit 체크 (초당 5회, 분당 100회)
            await self.rate_limiter.acquire()

            # WebSocket send는 thread-safe
            self.ws_app.send(json.dumps(subscribe_fmt))
            logger.info("💰 MyAsset 구독 완료 - 자산 변동 실시간 감지 시작")
        except Exception as e:
            logger.error(f"❌ MyAsset 구독 실패: {e}")
            self.is_connected = False
            raise

    async def listen(self) -> AsyncIterator[Dict]:
        """
        자산 변동 메시지 수신 (Generator)

        Yields:
            Dict: 자산 변동 데이터
                - type: 'myAsset'
                - asset: 자산 코드 (예: 'KRW', 'BTC')
                - balance: 보유 수량
                - locked: 주문 중 수량
                - avg_buy_price: 평균 매수가
                - modified: 변동 여부
        """
        if not self.is_connected:
            raise ConnectionError("WebSocket이 연결되지 않았습니다.")

        message_count = 0

        while self.is_connected:
            try:
                # 큐에서 메시지 가져오기 (non-blocking)
                if not self.message_queue.empty():
                    data = self.message_queue.get_nowait()

                    # 디버깅: 처음 3개 메시지만 로깅 (logger.debug)
                    message_count += 1
                    if message_count <= 3:
                        logger.debug(f"🔍 MyAsset 메시지 #{message_count} 수신")
                        logger.debug(f"🔍 파싱 성공: type={data.get('type')}, keys={list(data.keys())}")

                    yield data
                else:
                    # 큐가 비어있으면 잠시 대기
                    await asyncio.sleep(0.01)

            except Exception as e:
                logger.error(f"❌ MyAsset 메시지 수신 오류: {e}", exc_info=True)
                self.is_connected = False
                break

    async def listen_with_callback(self, callback: Callable):
        """
        자산 변동 메시지 수신 (Callback)

        Args:
            callback: 메시지 처리 콜백 함수
        """
        async for data in self.listen():
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"❌ MyAsset 콜백 처리 오류: {e}")


# 편의 함수
async def create_ticker_stream(symbols: List[str]) -> AsyncIterator[Dict]:
    """
    Ticker 스트림 생성 (편의 함수)

    Args:
        symbols: 심볼 리스트

    Yields:
        Dict: Ticker 데이터
    """
    ws = UpbitWebSocket()
    await ws.connect()
    await ws.subscribe_ticker(symbols)

    async for data in ws.listen():
        yield data


async def create_candle_stream(
    symbols: List[str],
    unit: str = "1"
) -> AsyncIterator[Dict]:
    """
    Candle 스트림 생성 (편의 함수)

    Args:
        symbols: 심볼 리스트
        unit: 분 단위

    Yields:
        Dict: Candle 데이터
    """
    ws = CandleWebSocket()

    async for candle in ws.subscribe_candle(symbols, unit):
        yield candle


# 테스트 코드
if __name__ == "__main__":
    """테스트: 실시간 Ticker 수신"""

    async def test_ticker():
        print("=== Upbit WebSocket Ticker 테스트 ===\n")

        ws = UpbitWebSocket()
        await ws.connect()
        await ws.subscribe_ticker(['KRW-BTC'])

        print("📊 BTC Ticker 수신 중... (10개만 출력)\n")

        count = 0
        async for data in ws.listen():
            if data.get('type') == 'ticker':
                print(f"[{count + 1}] BTC 현재가: {data['trade_price']:,.0f}원")
                count += 1

                if count >= 10:
                    break

        await ws.disconnect()
        print("\n✅ 테스트 완료")

    async def test_candle():
        print("\n=== Upbit Candle 테스트 ===\n")

        ws = CandleWebSocket(interval_seconds=10)

        print("🕯️ BTC 1분봉 수신 중... (3개만 출력)\n")

        count = 0
        async for candle in ws.subscribe_candle(['KRW-BTC'], unit="1"):
            print(f"[{count + 1}] 시각: {candle['timestamp']}")
            print(f"    종가: {candle['trade_price']:,.0f}원")
            print(f"    거래량: {candle['candle_acc_trade_volume']:.4f}\n")
            count += 1

            if count >= 3:
                break

        print("✅ 테스트 완료")

    # 실행
    asyncio.run(test_ticker())
    asyncio.run(test_candle())
