"""
Upbit WebSocket Client
업비트 웹소켓 클라이언트

실시간 시세 데이터 수신:
- 현재가 (Ticker)
- 체결 (Trade)
- 호가 (Orderbook)
- 분봉 캔들 (Candle)

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
import hashlib
import jwt as pyjwt
from typing import List, Dict, Optional, Callable, AsyncIterator
from datetime import datetime
from urllib.parse import urlencode, unquote
import websockets

logger = logging.getLogger(__name__)


class UpbitWebSocket:
    """
    업비트 웹소켓 클라이언트

    실시간 시장 데이터를 수신합니다.
    """

    def __init__(self):
        """웹소켓 클라이언트 초기화"""
        self.url = "wss://api.upbit.com/websocket/v1"
        self.websocket = None
        self.is_connected = False
        self.subscriptions = []
        self.callbacks = {}

    async def connect(self) -> bool:
        """
        웹소켓 연결

        Returns:
            bool: 연결 성공 여부
        """
        try:
            self.websocket = await websockets.connect(self.url)
            self.is_connected = True
            logger.info("✅ 업비트 웹소켓 연결 성공")
            return True
        except Exception as e:
            logger.error(f"❌ 웹소켓 연결 실패: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """웹소켓 연결 종료"""
        self.is_connected = False
        if self.websocket:
            try:
                # 1초 타임아웃으로 graceful shutdown 시도
                await asyncio.wait_for(self.websocket.close(), timeout=1.0)
                logger.info("웹소켓 연결 종료")
            except asyncio.TimeoutError:
                # 타임아웃 시 강제 종료
                logger.warning("⚠️ 웹소켓 graceful shutdown 타임아웃, 강제 종료")
                # websocket close_timeout을 0으로 설정하여 즉시 종료
                try:
                    await asyncio.wait_for(self.websocket.close(), timeout=0.1)
                except:
                    pass
            except Exception as e:
                logger.warning(f"⚠️ 웹소켓 종료 중 에러: {e}")

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
            # 🔧 타임아웃 5초 설정 (네트워크 문제 시 무한 대기 방지)
            await asyncio.wait_for(
                self.websocket.send(json.dumps(subscribe_fmt)),
                timeout=5.0
            )
            self.subscriptions.append(subscribe_fmt)
        except asyncio.TimeoutError:
            logger.error("❌ WebSocket 구독 타임아웃 (5초) - 연결 불안정")
            self.is_connected = False
            raise
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

        try:
            while self.is_connected:
                message = await self.websocket.recv()

                # 바이너리 데이터 디코딩
                if isinstance(message, bytes):
                    message = message.decode('utf-8')

                # JSON 파싱
                data = json.loads(message)

                yield data

        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ 웹소켓 연결 끊김")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ 메시지 수신 오류: {e}")
            self.is_connected = False

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

    def __init__(self, interval_seconds: int = 60):
        """
        캔들 웹소켓 초기화

        Args:
            interval_seconds: 캔들 갱신 주기 (초)
        """
        super().__init__()
        self.interval_seconds = interval_seconds
        self.last_candle_time = None
        self.is_running = True  # 종료 flag

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
        import pyupbit

        logger.info(f"🕯️ Candle 구독 시작: {symbols} ({unit}분봉)")

        consecutive_errors = 0  # 연속 에러 카운터
        max_consecutive_errors = 3  # 최대 연속 에러 허용

        while self.is_running:
            try:
                for symbol in symbols:
                    # 최신 캔들 가져오기
                    df = pyupbit.get_ohlcv(
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

                # 🔧 다음 캔들까지 대기 (취소 가능하도록 작은 단위로 체크)
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

                # 🔧 에러 재시도 대기 (취소 가능하도록 작은 단위로 체크)
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
        # 🔧 MyAsset은 Private 엔드포인트 사용 (공식 문서 명시)
        self.url = "wss://api.upbit.com/websocket/v1/private"
        self.websocket = None
        self.is_connected = False

    def _generate_jwt_token(self) -> str:
        """
        JWT 토큰 생성 (WebSocket 인증용)

        Returns:
            str: JWT 토큰 (Bearer 제외)
        """
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
            'timestamp': round(time.time() * 1000)
        }

        jwt_token = pyjwt.encode(payload, self.secret_key, algorithm='HS256')
        return jwt_token

    async def connect(self) -> bool:
        """
        WebSocket 연결 (JWT 인증 포함)

        Returns:
            bool: 연결 성공 여부
        """
        try:
            # JWT 토큰 생성
            token = self._generate_jwt_token()

            # Authorization 헤더와 함께 연결
            # 🔧 additional_headers 사용 (websockets 10.0+)
            self.websocket = await websockets.connect(
                self.url,
                additional_headers={
                    "Authorization": f"Bearer {token}"
                }
            )

            self.is_connected = True
            logger.info("✅ MyAsset WebSocket 연결 성공 (인증 완료)")
            return True

        except Exception as e:
            logger.error(f"❌ MyAsset WebSocket 연결 실패: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """WebSocket 연결 종료"""
        self.is_connected = False
        if self.websocket:
            try:
                await asyncio.wait_for(self.websocket.close(), timeout=1.0)
                logger.info("MyAsset WebSocket 연결 종료")
            except asyncio.TimeoutError:
                logger.warning("⚠️ MyAsset WebSocket graceful shutdown 타임아웃")
                try:
                    await asyncio.wait_for(self.websocket.close(), timeout=0.1)
                except:
                    pass
            except Exception as e:
                logger.warning(f"⚠️ MyAsset WebSocket 종료 중 에러: {e}")

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
            {"format": "JSON_LIST"}  # 🔧 공식 문서 권장 (효율적인 리스트 형식)
        ]

        try:
            # 🔧 타임아웃 5초 설정 (네트워크 문제 시 무한 대기 방지)
            await asyncio.wait_for(
                self.websocket.send(json.dumps(subscribe_fmt)),
                timeout=5.0
            )
            logger.info("💰 MyAsset 구독 완료 - 자산 변동 실시간 감지 시작")
        except asyncio.TimeoutError:
            logger.error("❌ MyAsset 구독 타임아웃 (5초) - WebSocket 연결 불안정")
            self.is_connected = False
            raise
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

        try:
            message_count = 0
            while self.is_connected:
                message = await self.websocket.recv()

                # 🔍 디버깅: 처음 3개 메시지 로깅
                message_count += 1
                if message_count <= 3:
                    logger.info(f"🔍 MyAsset 메시지 #{message_count} 수신 (길이: {len(message) if isinstance(message, (str, bytes)) else 0})")
                    if isinstance(message, bytes):
                        logger.info(f"🔍 원본 (bytes): {message[:200]}")
                    else:
                        logger.info(f"🔍 원본 (str): {message[:200]}")

                # 바이너리 데이터 디코딩
                if isinstance(message, bytes):
                    message = message.decode('utf-8')

                # JSON 파싱
                try:
                    data = json.loads(message)
                    if message_count <= 3:
                        if isinstance(data, list):
                            logger.info(f"🔍 파싱 성공 (JSON_LIST): length={len(data)}, first_type={data[0].get('type') if data else None}")
                        else:
                            logger.info(f"🔍 파싱 성공: type={data.get('type')}, keys={list(data.keys())}")
                except json.JSONDecodeError as je:
                    logger.error(f"❌ JSON 파싱 실패: {je}, 원본: {message[:100]}")
                    continue

                # JSON_LIST 형식 처리 (배열의 모든 요소를 순회)
                if isinstance(data, list):
                    for item in data:
                        if item.get('type') == 'myAsset':
                            yield item
                else:
                    # DEFAULT 형식 (단일 객체)
                    if data.get('type') == 'myAsset':
                        yield data

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"⚠️ MyAsset WebSocket 연결 끊김 (close_code={e.code if hasattr(e, 'code') else 'unknown'}, reason={e.reason if hasattr(e, 'reason') else 'unknown'})")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ MyAsset 메시지 수신 오류: {e}", exc_info=True)
            self.is_connected = False

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
