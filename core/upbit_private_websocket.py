"""
Upbit Private WebSocket

실시간 내 주문 및 자산 데이터 수신 (myOrder, myAsset 채널)

프로그램 실행 중 외부 매수를 실시간으로 감지하여
사용자에게 즉시 알림을 보냅니다 (< 1초 지연).

Author: Claude
Created: 2025-01-26
"""

import json
import jwt
import uuid
import asyncio
import logging
import websockets
from typing import Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UpbitPrivateWebSocket:
    """
    Upbit Private WebSocket 클라이언트

    myOrder 채널을 구독하여 내 주문 체결을 실시간으로 수신합니다.

    Features:
        - JWT 인증 (Authorization 헤더)
        - myOrder 채널 구독
        - 체결 이벤트 실시간 수신 (< 1초)
        - 자동 재연결
        - 외부 매수 감지

    Attributes:
        access_key (str): Upbit API Access Key
        secret_key (str): Upbit API Secret Key
        on_order_callback (Callable): 주문 체결 시 호출할 콜백 함수

    Example:
        >>> async def handle_order(order_data):
        ...     print(f"체결: {order_data['code']}")
        >>> ws = UpbitPrivateWebSocket(
        ...     access_key="your_access_key",
        ...     secret_key="your_secret_key",
        ...     on_order_callback=handle_order
        ... )
        >>> await ws.connect()
    """

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        on_order_callback: Callable,
        on_asset_callback: Optional[Callable] = None
    ):
        """
        UpbitPrivateWebSocket 초기화

        Args:
            access_key: Upbit API Access Key
            secret_key: Upbit API Secret Key
            on_order_callback: 주문 체결 시 호출할 콜백 (async 함수)
            on_asset_callback: 자산 변동 시 호출할 콜백 (optional)
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.on_order = on_order_callback
        self.on_asset = on_asset_callback

        self.ws = None
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10

        logger.info("✅ UpbitPrivateWebSocket 초기화 완료")

    def _generate_jwt(self) -> str:
        """
        JWT 토큰 생성 (WebSocket 인증용)

        Returns:
            str: JWT 토큰 문자열

        Note:
            Upbit WebSocket Private 채널은 JWT 인증이 필요합니다.
            Authorization 헤더에 "Bearer {jwt_token}" 형식으로 전달합니다.
        """
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }

        # HS256 알고리즘으로 JWT 토큰 생성
        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')

        logger.debug(f"JWT 토큰 생성: {jwt_token[:20]}...")
        return jwt_token

    async def connect(self):
        """
        WebSocket 연결 및 구독

        myOrder 채널을 구독하여 실시간으로 내 주문 체결을 수신합니다.

        Raises:
            websockets.exceptions.WebSocketException: WebSocket 연결 실패

        Note:
            연결이 끊기면 자동으로 재연결을 시도합니다.
        """
        uri = "wss://api.upbit.com/websocket/v1/private"

        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                # JWT 토큰 생성
                jwt_token = self._generate_jwt()

                # Authorization 헤더 추가
                headers = {
                    "Authorization": f"Bearer {jwt_token}"
                }

                logger.info(f"🔌 Private WebSocket 연결 시도: {uri}")

                # WebSocket 연결 (버전 호환성을 위한 파라미터 처리)
                # websockets >= 10.0: extra_headers
                # websockets < 10.0: additional_headers
                connect_params = {
                    "ping_interval": 120,  # 120초마다 PING 전송
                    "ping_timeout": 10
                }

                # websockets 버전 확인
                try:
                    ws_version = tuple(map(int, websockets.__version__.split('.')[:2]))
                    use_extra_headers = ws_version >= (10, 0)
                except (ValueError, AttributeError):
                    # 버전 파싱 실패 시 기본값 (최신 버전 가정)
                    use_extra_headers = True

                if use_extra_headers:
                    connect_params["extra_headers"] = headers
                else:
                    connect_params["additional_headers"] = headers

                async with websockets.connect(uri, **connect_params) as ws:
                    self.ws = ws
                    self.reconnect_attempts = 0  # 연결 성공 시 재시도 횟수 초기화

                    # myOrder 채널 구독
                    subscribe_msg = [
                        {"ticket": str(uuid.uuid4())},
                        {"type": "myOrder"}  # 모든 코인의 내 주문
                    ]

                    await ws.send(json.dumps(subscribe_msg))
                    logger.info("✅ Private WebSocket 연결 완료 (myOrder 채널 구독)")

                    # 메시지 수신 루프
                    async for message in ws:
                        if not self.running:
                            logger.info("🛑 Private WebSocket 중지 요청")
                            break

                        try:
                            # 메시지 파싱
                            if isinstance(message, bytes):
                                data = json.loads(message.decode('utf-8'))
                            else:
                                data = json.loads(message)

                            # 메시지 타입별 처리
                            if data.get('type') == 'myOrder':
                                # myOrder 이벤트
                                await self._handle_my_order(data)

                            elif data.get('type') == 'myAsset':
                                # myAsset 이벤트
                                if self.on_asset:
                                    await self.on_asset(data)

                            elif 'status' in data:
                                # 상태 메시지 ("UP")
                                logger.debug(f"WebSocket 상태: {data['status']}")

                            elif 'error' in data:
                                # 에러 메시지
                                logger.error(f"❌ WebSocket 에러: {data['error']}")

                        except json.JSONDecodeError as e:
                            logger.error(f"❌ JSON 파싱 실패: {e}")

                        except Exception as e:
                            logger.error(f"❌ 메시지 처리 실패: {e}", exc_info=True)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"⚠️ Private WebSocket 연결 끊김: {e}")
                await self._handle_reconnect()

            except Exception as e:
                logger.error(f"❌ Private WebSocket 에러: {e}", exc_info=True)
                await self._handle_reconnect()

        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"❌ Private WebSocket 재연결 최대 시도 횟수 초과 ({self.max_reconnect_attempts}회)")

    async def _handle_my_order(self, order_data: dict):
        """
        myOrder 이벤트 처리

        Args:
            order_data: myOrder 데이터
                {
                    "type": "myOrder",
                    "code": "KRW-BTC",
                    "uuid": "order-id",
                    "ask_bid": "BID" or "ASK",
                    "state": "done" or "wait" or "cancel",
                    "price": 50000000.0,
                    "executed_volume": 0.001,
                    "trade_timestamp": 1234567890
                }
        """
        try:
            # 매수만 처리 (매도는 무시)
            if order_data.get('ask_bid') != 'BID':
                logger.debug(f"매도 주문 무시: {order_data.get('code')}")
                return

            # 체결 완료만 처리 (대기 중, 취소는 무시)
            if order_data.get('state') != 'done':
                logger.debug(
                    f"미체결 주문 무시: {order_data.get('code')} "
                    f"(state={order_data.get('state')})"
                )
                return

            # 콜백 호출
            if self.on_order:
                logger.info(
                    f"📱 myOrder 이벤트: {order_data.get('code')} "
                    f"매수 체결 (uuid={order_data.get('uuid')[:8]}...)"
                )
                await self.on_order(order_data)

        except Exception as e:
            logger.error(f"❌ myOrder 처리 실패: {e}", exc_info=True)

    async def _handle_reconnect(self):
        """재연결 처리"""
        self.reconnect_attempts += 1

        if self.reconnect_attempts < self.max_reconnect_attempts:
            # Exponential backoff (1s, 2s, 4s, 8s, ...)
            delay = min(2 ** (self.reconnect_attempts - 1), 60)
            logger.info(
                f"🔄 {delay}초 후 재연결 시도 "
                f"({self.reconnect_attempts}/{self.max_reconnect_attempts})"
            )
            await asyncio.sleep(delay)

    def start(self):
        """
        WebSocket 시작

        Note:
            비동기 함수이므로 asyncio.create_task()로 호출하세요.

        Example:
            >>> ws = UpbitPrivateWebSocket(...)
            >>> ws.start()
            >>> task = asyncio.create_task(ws.connect())
        """
        self.running = True
        logger.info("✅ Private WebSocket 시작")

    def stop(self):
        """WebSocket 중지"""
        self.running = False
        logger.info("🛑 Private WebSocket 중지")

    async def close(self):
        """WebSocket 연결 종료"""
        self.stop()
        if self.ws:
            await self.ws.close()
            logger.info("✅ Private WebSocket 연결 종료")

    def is_connected(self) -> bool:
        """
        연결 상태 확인

        Returns:
            bool: 연결 여부
        """
        return self.ws is not None and self.ws.open

    def __repr__(self) -> str:
        status = "connected" if self.is_connected() else "disconnected"
        return f"<UpbitPrivateWebSocket status={status}>"


# 테스트 코드
if __name__ == "__main__":
    """테스트: Private WebSocket 연결 및 myOrder 수신"""
    import os
    from dotenv import load_dotenv

    print("=== Upbit Private WebSocket 테스트 ===\n")

    # .env 파일에서 API 키 로드
    load_dotenv()
    access_key = os.getenv('UPBIT_ACCESS_KEY')
    secret_key = os.getenv('UPBIT_SECRET_KEY')

    if not access_key or not secret_key:
        print("❌ API 키가 설정되지 않았습니다.")
        print("   .env 파일에 UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY를 설정하세요.")
        exit(1)

    async def handle_order(order_data):
        """주문 체결 콜백"""
        print(f"\n📱 myOrder 이벤트 수신:")
        print(f"   코인: {order_data.get('code')}")
        print(f"   UUID: {order_data.get('uuid')}")
        print(f"   매수/매도: {order_data.get('ask_bid')}")
        print(f"   상태: {order_data.get('state')}")
        print(f"   가격: {order_data.get('price'):,.0f}원")
        print(f"   수량: {order_data.get('executed_volume')}")

    async def test_private_websocket():
        # Private WebSocket 초기화
        ws = UpbitPrivateWebSocket(
            access_key=access_key,
            secret_key=secret_key,
            on_order_callback=handle_order
        )

        # 시작
        ws.start()

        # 연결 (60초 동안 테스트)
        print("📡 Private WebSocket 연결 중...")
        print("⏳ 60초 동안 myOrder 이벤트를 기다립니다...\n")
        print("   (Upbit 앱에서 매수 주문을 테스트해보세요!)\n")

        # 연결 태스크 실행
        connection_task = asyncio.create_task(ws.connect())

        # 60초 대기
        try:
            await asyncio.wait_for(connection_task, timeout=60.0)
        except asyncio.TimeoutError:
            print("\n⏰ 60초 타임아웃")

        # 종료
        ws.stop()
        await ws.close()
        print("\n✅ 테스트 완료")

    # 비동기 테스트 실행
    asyncio.run(test_private_websocket())
