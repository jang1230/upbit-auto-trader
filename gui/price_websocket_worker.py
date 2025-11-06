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
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # WebSocket 연결 및 구독
            self.is_running = True
            loop.run_until_complete(self._run_websocket())

        except Exception as e:
            logger.error(f"❌ WebSocket Worker 오류: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            self.is_running = False

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

            # 메시지 수신 루프
            async for data in self.websocket.listen():
                if not self.is_running:
                    break

                await self._process_ticker_data(data)

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

    def stop(self):
        """WebSocket Worker 중지"""
        logger.info("🛑 WebSocket Worker 중지 요청")
        self.is_running = False

        # WebSocket 연결 종료
        if self.websocket:
            asyncio.run_coroutine_threadsafe(
                self.websocket.disconnect(),
                asyncio.get_event_loop()
            )
