"""
가격 WebSocket Worker

포지션 심볼들의 실시간 가격을 WebSocket으로 수신하여
PositionManager를 업데이트하고 GUI에 시그널을 전송합니다.
"""

import asyncio
import logging
from typing import List
from PySide6.QtCore import QThread, Signal

from core.upbit_websocket import UpbitWebSocket
from core.position_manager import PositionManager

logger = logging.getLogger(__name__)


class PriceWebSocketWorker(QThread):
    """
    가격 WebSocket Worker (QThread)

    실시간 가격 데이터를 수신하여 PositionManager 업데이트
    """

    # 시그널 정의
    price_updated = Signal(str, float)  # (symbol, current_price)
    connected = Signal()                # 연결 성공
    disconnected = Signal()             # 연결 끊김
    error_occurred = Signal(str)        # 에러 발생

    def __init__(self, position_manager: PositionManager, parent=None):
        super().__init__(parent)
        self.position_manager = position_manager
        self.websocket = None
        self.symbols = []
        self.is_running = False
        self.loop = None  # asyncio 이벤트 루프 저장

    def set_symbols(self, symbols: List[str]):
        """
        구독할 심볼 설정

        Args:
            symbols: 심볼 리스트 (예: ['KRW-BTC', 'KRW-ETH'])
        """
        self.symbols = symbols
        logger.info(f"📊 구독 심볼 설정: {symbols}")

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
            logger.error(f"❌ WebSocket Worker 오류: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            self.is_running = False
            if self.loop:
                self.loop.close()
            self.loop = None

    async def _run_websocket(self):
        """WebSocket 연결 및 메시지 수신"""
        try:
            # WebSocket 생성 및 연결
            self.websocket = UpbitWebSocket()

            logger.info("🔌 WebSocket 연결 시도...")
            connected = await self.websocket.connect()

            if not connected:
                self.error_occurred.emit("WebSocket 연결 실패")
                return

            self.connected.emit()
            logger.info("✅ WebSocket 연결 성공")

            # 심볼이 없으면 종료
            if not self.symbols:
                logger.warning("⚠️ 구독할 심볼이 없습니다")
                return

            # Ticker 구독
            await self.websocket.subscribe_ticker(self.symbols)
            logger.info(f"📊 Ticker 구독 완료: {len(self.symbols)}개 심볼")

            # 메시지 수신 루프 (async generator를 제대로 닫기 위해 try-finally 사용)
            listener = self.websocket.listen()
            try:
                async for data in listener:
                    if not self.is_running:
                        break

                    await self._process_ticker_data(data)
            finally:
                # async generator 명시적 종료
                await listener.aclose()

        except Exception as e:
            logger.error(f"❌ WebSocket 실행 오류: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            # 연결 종료
            if self.websocket:
                await self.websocket.disconnect()
            self.disconnected.emit()
            logger.info("🔌 WebSocket 연결 종료")

    async def _process_ticker_data(self, data: dict):
        """
        Ticker 데이터 처리

        Args:
            data: WebSocket에서 수신한 데이터
        """
        try:
            # Ticker 데이터 확인
            if data.get('type') != 'ticker':
                return

            symbol = data.get('code')  # 예: 'KRW-BTC'
            trade_price = data.get('trade_price')  # 현재가

            if not symbol or not trade_price:
                return

            # PositionManager 업데이트
            position = self.position_manager.update_price(symbol, trade_price)

            if position:
                # GUI 업데이트 시그널 발생
                self.price_updated.emit(symbol, trade_price)

                logger.debug(
                    f"💹 가격 업데이트: {symbol} = {trade_price:,.0f}원 "
                    f"({position['profit_pct']:+.2f}%)"
                )

        except Exception as e:
            logger.error(f"❌ Ticker 데이터 처리 오류: {e}", exc_info=True)

    def update_symbols(self, new_symbols: List[str]):
        """
        Symbol 리스트 업데이트 (연결 유지한 채 재구독)

        공식 Best Practice: "새로운 구독 메시지를 전송하여 이전 구독을 중단하고
                            새로운 데이터 스트림 구독을 시작할 수 있습니다."

        Args:
            new_symbols: 새로운 심볼 리스트 (예: ['KRW-BTC', 'KRW-ETH'])
        """
        # Symbol 리스트 동일 여부 체크
        if set(self.symbols) == set(new_symbols):
            logger.debug(f"📊 Symbol 리스트 동일 ({len(new_symbols)}개) - 재구독 불필요")
            return

        logger.info(
            f"📊 Symbol 리스트 변경 감지\n"
            f"   - 이전: {self.symbols}\n"
            f"   - 신규: {new_symbols}\n"
            f"   - 재구독 메시지 전송 중..."
        )

        self.symbols = new_symbols

        # asyncio 이벤트 루프에서 재구독 실행 (연결은 유지)
        if self.loop and self.loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._resubscribe(),
                    self.loop
                )
                # 재구독 완료 대기 (최대 3초)
                future.result(timeout=3.0)
            except Exception as e:
                logger.error(f"❌ 재구독 실패: {e}", exc_info=True)
        else:
            logger.warning("⚠️ 이벤트 루프가 실행 중이 아님 - 재구독 불가")

    async def _resubscribe(self):
        """
        재구독 (연결 유지)

        WebSocket 연결을 유지한 채로 새로운 Symbol 리스트로 재구독합니다.
        Upbit 공식 문서: 연결 재생성 없이 메시지만 전송하면 구독 변경 가능
        """
        try:
            if not self.websocket or not self.websocket.is_connected:
                logger.warning("⚠️ WebSocket 연결 안 됨 - 재구독 불가")
                return

            # 새로운 Symbol 리스트로 재구독 (기존 연결 유지)
            await self.websocket.subscribe_ticker(self.symbols)
            logger.info(f"✅ 재구독 완료: {len(self.symbols)}개 심볼 (연결 유지)")

        except Exception as e:
            logger.error(f"❌ 재구독 오류: {e}", exc_info=True)
            raise

    def stop(self):
        """WebSocket Worker 중지"""
        logger.info("🛑 WebSocket Worker 중지 요청")
        self.is_running = False

        # WebSocket 연결 종료 (올바른 이벤트 루프 사용)
        if self.websocket and self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.disconnect(),
                    self.loop
                )
            except Exception as e:
                logger.warning(f"⚠️ WebSocket 종료 중 오류: {e}")
