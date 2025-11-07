"""
MyAsset WebSocket Worker

계좌 잔고 변동을 실시간으로 감지하여
PositionManager를 업데이트하고 GUI에 시그널을 전송합니다.
"""

import asyncio
import logging
from typing import Dict, Any, List
from PySide6.QtCore import QThread, Signal

from core.upbit_websocket import MyAssetWebSocket
from core.position_manager import PositionManager

logger = logging.getLogger(__name__)


class MyAssetWebSocketWorker(QThread):
    """
    MyAsset WebSocket Worker (QThread)

    실시간 잔고 변동 데이터를 수신하여 PositionManager 업데이트
    """

    # 시그널 정의
    balance_updated = Signal(list)      # (assets) 잔고 업데이트
    connected = Signal()                # 연결 성공
    disconnected = Signal()             # 연결 끊김
    error_occurred = Signal(str)        # 에러 발생

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        position_manager: PositionManager,
        config: Dict[str, Any],
        parent=None
    ):
        super().__init__(parent)
        self.access_key = access_key
        self.secret_key = secret_key
        self.position_manager = position_manager
        self.config = config  # trading_config.json
        self.websocket = None
        self.is_running = False
        self.loop = None  # asyncio 이벤트 루프 저장

    def run(self):
        """QThread 실행 (별도 스레드에서 asyncio 이벤트 루프 실행)"""
        try:
            # 새로운 asyncio 이벤트 루프 생성
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # WebSocket 연결 및 구독
            self.is_running = True
            self.loop.run_until_complete(self._run_websocket())

        except Exception as e:
            logger.error(f"❌ MyAsset WebSocket Worker 오류: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            self.is_running = False
            if self.loop:
                self.loop.close()
            self.loop = None

    async def _run_websocket(self):
        """WebSocket 연결 및 메시지 수신"""
        try:
            # MyAsset WebSocket 생성 및 연결
            self.websocket = MyAssetWebSocket(self.access_key, self.secret_key)

            logger.info("🔌 MyAsset WebSocket 연결 시도...")
            await self.websocket.connect()

            self.connected.emit()
            logger.info("✅ MyAsset WebSocket 연결 성공")

            # MyAsset 구독
            await self.websocket.subscribe_myasset()
            logger.info("💰 MyAsset 구독 완료 - 잔고 변동 실시간 감지 시작")

            # 메시지 수신 루프
            listener = self.websocket.listen()
            try:
                async for data in listener:
                    if not self.is_running:
                        break

                    await self._process_myasset_data(data)
            finally:
                # async generator 명시적 종료
                await listener.aclose()

        except Exception as e:
            logger.error(f"❌ MyAsset WebSocket 실행 오류: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            # 연결 종료
            if self.websocket:
                await self.websocket.disconnect()
            self.disconnected.emit()
            logger.info("🔌 MyAsset WebSocket 연결 종료")

    async def _process_myasset_data(self, data: dict):
        """
        MyAsset 데이터 처리

        Args:
            data: WebSocket에서 수신한 데이터
            {
                "type": "myAsset",
                "assets": [
                    {"currency": "KRW", "balance": "1000000", "locked": "0"},
                    {"currency": "BTC", "balance": "0.001", "locked": "0"},
                    ...
                ]
            }
        """
        try:
            # MyAsset 데이터 확인
            if data.get('type') != 'myAsset':
                return

            assets = data.get('assets', [])
            if not assets:
                return

            logger.debug(f"💰 MyAsset 메시지 수신: {len(assets)}개 자산")

            # PositionManager 업데이트 (메인 스레드에서 실행하도록 시그널로 전달)
            self.balance_updated.emit(assets)

            # 로그 출력
            for asset in assets:
                currency = asset.get('currency')
                balance = float(asset.get('balance', 0))
                locked = float(asset.get('locked', 0))
                avg_buy_price = float(asset.get('avg_buy_price', 0))

                if currency == 'KRW':
                    logger.info(f"💰 잔고 변동: {currency} - 잔액: {balance:,.0f}원, 주문중: {locked:,.0f}원")
                elif balance > 0 or locked > 0:
                    logger.info(f"💰 잔고 변동: {currency} - 잔액: {balance:.8f}, 주문중: {locked:.8f}, 평균가: {avg_buy_price:,.0f}원")

        except Exception as e:
            logger.error(f"❌ MyAsset 데이터 처리 오류: {e}", exc_info=True)

    def stop(self):
        """WebSocket Worker 중지"""
        logger.info("🛑 MyAsset WebSocket Worker 중지 요청")
        self.is_running = False

        # WebSocket 연결 종료 (올바른 이벤트 루프 사용)
        if self.websocket and self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.disconnect(),
                    self.loop
                )
            except Exception as e:
                logger.warning(f"⚠️ MyAsset WebSocket 종료 중 오류: {e}")
