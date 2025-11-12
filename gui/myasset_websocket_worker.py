"""
MyAsset WebSocket Worker

계좌 잔고 변동을 실시간으로 감지하여
PositionManager를 업데이트하고 GUI에 시그널을 전송합니다.

Adaptive Polling 전략:
- WebSocket 미수신 → REST API Polling ON (1초 간격)
- WebSocket 정상 → REST API Polling OFF
- WebSocket 끊김 → REST API Polling ON (Fallback)
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from PySide6.QtCore import QThread, Signal

from core.upbit_websocket import MyAssetWebSocket
from core.position_manager import PositionManager

logger = logging.getLogger(__name__)


class MyAssetState:
    """MyAsset WebSocket 상태 정의"""
    NOT_RECEIVING = "not_receiving"  # 🔴 미수신 (Polling ON)
    RECEIVING = "receiving"          # 🟢 정상 (Polling OFF)
    DISCONNECTED = "disconnected"    # 🟠 끊김 (Polling ON)


class MyAssetWebSocketWorker(QThread):
    """
    MyAsset WebSocket Worker (QThread)

    실시간 잔고 변동 데이터를 수신하여 PositionManager 업데이트

    Adaptive Polling 전략:
    - WebSocket 미수신 시 BalancePollingManager가 백업으로 작동
    - WebSocket 첫 수신 시 polling 자동 중지
    - WebSocket 끊김 시 polling 자동 재시작
    """

    # 시그널 정의
    balance_updated = Signal(list)      # (assets) 잔고 업데이트
    connected = Signal()                # 연결 성공
    disconnected = Signal()             # 연결 끊김
    error_occurred = Signal(str)        # 에러 발생
    state_changed = Signal(str)         # 상태 변경 (MyAssetState)

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        position_manager: PositionManager,
        config: Dict[str, Any],
        balance_polling_manager=None,  # BalancePollingManager (optional)
        upbit_api=None,  # UpbitAPI (avg_buy_price 조회용, optional)
        parent=None
    ):
        super().__init__(parent)
        self.access_key = access_key
        self.secret_key = secret_key
        self.position_manager = position_manager
        self.config = config  # trading_config.json
        self.balance_polling_manager = balance_polling_manager
        self.upbit_api = upbit_api
        self.websocket: Optional[MyAssetWebSocket] = None
        self.is_running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None  # asyncio 이벤트 루프 저장

        # 상태 관리
        self.state = MyAssetState.NOT_RECEIVING  # 초기 상태: 미수신
        self.first_message_received = False  # 첫 메시지 수신 플래그

    def run(self):
        """QThread 실행 (별도 스레드에서 asyncio 이벤트 루프 실행)"""
        try:
            # Polling 시작 (초기 상태: NOT_RECEIVING)
            if self.balance_polling_manager:
                self.balance_polling_manager.start_polling()
                self.state_changed.emit(MyAssetState.NOT_RECEIVING)
                logger.info("🔴 상태: NOT_RECEIVING - REST API Polling 활성화")

            # 새로운 asyncio 이벤트 루프 생성
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # WebSocket 연결 및 구독
            self.is_running = True
            self.loop.run_until_complete(self._run_websocket())

        except Exception as e:
            logger.error(f"❌ MyAsset WebSocket Worker 오류: {e}", exc_info=True)
            self.error_occurred.emit(str(e))

            # 에러 발생 시 Polling 재시작 (WebSocket 정상이었다면)
            if self.balance_polling_manager and self.state == MyAssetState.RECEIVING:
                self.balance_polling_manager.start_polling()
                self.state = MyAssetState.DISCONNECTED
                self.state_changed.emit(MyAssetState.DISCONNECTED)
                logger.warning("🟠 상태: DISCONNECTED - 오류로 인해 REST API Polling 재활성화")

        finally:
            self.is_running = False

            # 종료 시 Polling 중지
            if self.balance_polling_manager:
                self.balance_polling_manager.stop_polling()

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

            # 연결 끊김 시 Polling 재시작 (WebSocket 정상이었다면)
            if self.balance_polling_manager and self.state == MyAssetState.RECEIVING:
                self.balance_polling_manager.start_polling()
                self.state = MyAssetState.DISCONNECTED
                self.state_changed.emit(MyAssetState.DISCONNECTED)
                logger.warning("🟠 상태: DISCONNECTED - 연결 끊김으로 인해 REST API Polling 재활성화")

        finally:
            # 연결 종료
            if self.websocket:
                await self.websocket.disconnect()
            self.disconnected.emit()
            logger.info("🔌 MyAsset WebSocket 연결 종료")

    async def _process_myasset_data(self, data: dict):
        """
        MyAsset 데이터 처리 + 상태 전환 + 새 자산 감지

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

            # 🆕 첫 메시지 수신 시 상태 전환
            if not self.first_message_received:
                self.first_message_received = True

                # Polling 중지
                if self.balance_polling_manager:
                    self.balance_polling_manager.stop_polling()

                # 상태 전환: NOT_RECEIVING → RECEIVING
                self.state = MyAssetState.RECEIVING
                self.state_changed.emit(MyAssetState.RECEIVING)

                logger.info("🟢 상태: RECEIVING - MyAsset WebSocket 정상 수신 확인, REST API Polling 비활성화")

            # 🆕 새 자산 감지 시 처리
            for asset in assets:
                currency = asset.get('currency')

                # 🐛 디버깅: WebSocket 데이터 전체 확인
                logger.debug(f"📊 [DEBUG] WebSocket asset 데이터: {asset}")

                # KRW는 제외
                if currency == 'KRW':
                    continue

                balance = float(asset.get('balance', 0))
                locked = float(asset.get('locked', 0))
                total = balance + locked

                # 잔고가 0이면 스킵
                if total <= 0:
                    continue

                symbol = f"KRW-{currency}"

                # 포지션 확인
                position = self.position_manager.get_position_by_symbol(symbol)

                if not position:
                    # 새 자산 발견!
                    logger.info(f"🆕 신규 보유 코인 감지 (WebSocket): {symbol}")

                    # 🐛 디버깅: WebSocket에 avg_buy_price가 있는지 확인
                    ws_avg_buy_price = float(asset.get('avg_buy_price', 0))
                    logger.info(f"   📊 [DEBUG] WebSocket avg_buy_price: {ws_avg_buy_price:,.0f}원")

                    # WebSocket 데이터에서 먼저 avg_buy_price 확인
                    avg_buy_price = ws_avg_buy_price

                    if self.upbit_api:
                        try:
                            # REST API로 계좌 정보 조회 (avg_buy_price 획득)
                            accounts = await asyncio.get_event_loop().run_in_executor(
                                None,
                                self.upbit_api.get_accounts
                            )

                            for acc in accounts:
                                if acc['currency'] == currency:
                                    avg_buy_price = float(acc.get('avg_buy_price', 0))
                                    break

                            logger.debug(f"   - REST API로 평균가 조회: {avg_buy_price:,.0f}원")

                        except Exception as e:
                            logger.error(f"❌ avg_buy_price 조회 실패 ({symbol}): {e}")

                    # avg_buy_price > 0인 경우에만 포지션 생성
                    if avg_buy_price > 0:
                        try:
                            self.position_manager.create_position(
                                group_id="group_null",
                                symbol=symbol,
                                buy_price=avg_buy_price,
                                quantity=total,
                                force_create_for_sync=True
                            )

                            logger.info(f"✅ group_null 포지션 생성: {symbol}")

                            # BalancePollingManager의 known_symbols에도 추가
                            if self.balance_polling_manager:
                                self.balance_polling_manager.add_known_symbol(symbol)

                        except Exception as e:
                            logger.error(f"❌ 포지션 생성 실패 ({symbol}): {e}", exc_info=True)
                    else:
                        logger.warning(f"⚠️ {symbol} avg_buy_price가 0이라 포지션 생성 생략")

            # PositionManager 업데이트 (메인 스레드에서 실행하도록 시그널로 전달)
            self.balance_updated.emit(assets)

            # 로그 출력
            for asset in assets:
                currency = asset.get('currency')
                balance = float(asset.get('balance', 0))
                locked = float(asset.get('locked', 0))
                avg_buy_price = float(asset.get('avg_buy_price', 0))

                if currency == 'KRW':
                    logger.debug(f"💰 잔고 변동: {currency} - 잔액: {balance:,.0f}원, 주문중: {locked:,.0f}원")
                elif balance > 0 or locked > 0:
                    logger.debug(f"💰 잔고 변동: {currency} - 잔액: {balance:.8f}, 주문중: {locked:.8f}")

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
