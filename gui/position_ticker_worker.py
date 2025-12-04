"""
PositionTickerWorker - GUI 전용 현재가 수신 Worker

프로그램 시작부터 종료까지 항상 실행되며,
활성 포지션 심볼의 현재가를 수신하여 PositionManager에 업데이트합니다.

핵심 특징:
- V4TradingEngine 상태와 무관하게 독립 동작
- 프로그램 시작 시 자동 시작, 종료 시 자동 정리
- 포지션 추가/제거 시 구독 심볼 동적 업데이트
- PositionManager.update_price()로 실시간 가격 업데이트

사용법:
    worker = PositionTickerWorker(position_manager)
    worker.start()  # 프로그램 시작 시
    ...
    worker.add_symbol('KRW-BTC')  # 포지션 추가 시
    worker.remove_symbol('KRW-ETH')  # 포지션 종료 시
    ...
    worker.stop()  # 프로그램 종료 시
    worker.wait()
"""

import asyncio
import logging
import threading
from typing import Dict, Any, List, Optional, Set

from PySide6.QtCore import QThread, Signal

from core.upbit_websocket import TickerWebSocket
from core.position_manager import PositionManager

logger = logging.getLogger(__name__)


class PositionTickerWorker(QThread):
    """
    GUI 전용 Ticker WebSocket Worker (QThread)

    활성 포지션 심볼만 구독하여 현재가를 수신하고
    PositionManager에 업데이트합니다.

    V4 엔진 상태와 무관하게 독립적으로 동작합니다.
    """

    # 시그널 정의
    price_updated = Signal(str, float)      # (symbol, price) 가격 업데이트
    connected = Signal()                     # WebSocket 연결 성공
    disconnected = Signal()                  # WebSocket 연결 끊김
    error_occurred = Signal(str)             # 에러 발생
    subscription_updated = Signal(int)       # 구독 심볼 수 변경

    def __init__(
        self,
        position_manager: PositionManager,
        parent=None
    ):
        """
        PositionTickerWorker 초기화

        Args:
            position_manager: PositionManager 인스턴스 (가격 업데이트 대상)
            parent: 부모 QObject (선택)
        """
        super().__init__(parent)
        self.position_manager = position_manager
        self.websocket: Optional[TickerWebSocket] = None
        self.is_running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        # 구독 심볼 관리
        self._subscribed_symbols: Set[str] = set()
        self._pending_add: Set[str] = set()      # 추가 대기 중인 심볼
        self._pending_remove: Set[str] = set()   # 제거 대기 중인 심볼
        self._subscription_lock = threading.Lock()

        # 재연결 설정
        self._reconnect_count = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 2.0  # 초

        logger.info("✅ PositionTickerWorker 초기화 완료 (GUI 전용)")

    def run(self):
        """QThread 실행 (별도 스레드에서 asyncio 이벤트 루프 실행)"""
        try:
            # 새로운 asyncio 이벤트 루프 생성
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            self.is_running = True
            logger.info("🚀 PositionTickerWorker 시작")

            # WebSocket 연결 및 메시지 수신
            self.loop.run_until_complete(self._run_websocket())

        except Exception as e:
            logger.error(f"❌ PositionTickerWorker 오류: {e}", exc_info=True)
            self.error_occurred.emit(str(e))

        finally:
            self.is_running = False
            if self.loop:
                self.loop.close()
            self.loop = None
            logger.info("🛑 PositionTickerWorker 종료")

    async def _run_websocket(self):
        """WebSocket 연결 및 메시지 수신 루프"""
        while self.is_running:
            try:
                # 1. 초기 심볼 로드 (PositionManager에서)
                await self._load_initial_symbols()

                # 구독할 심볼이 없으면 대기 후 재시도
                if not self._subscribed_symbols:
                    logger.info("⏳ 구독할 심볼 없음 - 5초 후 재확인...")
                    await asyncio.sleep(5)
                    continue

                # 2. WebSocket 생성 및 연결
                self.websocket = TickerWebSocket(on_tick_callback=self._on_tick)

                logger.info(f"🔌 PositionTickerWorker WebSocket 연결 시도... ({len(self._subscribed_symbols)}개 심볼)")
                await self.websocket.connect()

                self.connected.emit()
                self._reconnect_count = 0
                logger.info("✅ PositionTickerWorker WebSocket 연결 성공")

                # 3. 심볼 구독
                await self._subscribe_current_symbols()

                # 4. 메시지 수신 루프 (+ 동적 구독 업데이트)
                await self._message_loop()

            except Exception as e:
                logger.error(f"❌ WebSocket 오류: {e}", exc_info=True)
                self.error_occurred.emit(str(e))

                # 재연결 시도
                if self.is_running and self._reconnect_count < self._max_reconnect_attempts:
                    self._reconnect_count += 1
                    delay = self._reconnect_delay * self._reconnect_count
                    logger.warning(f"🔄 재연결 시도 {self._reconnect_count}/{self._max_reconnect_attempts} ({delay:.1f}초 후)")
                    await asyncio.sleep(delay)
                else:
                    logger.error("❌ 최대 재연결 시도 초과")
                    break

            finally:
                # WebSocket 정리
                if self.websocket:
                    try:
                        await self.websocket.disconnect()
                    except Exception as e:
                        logger.debug(f"WebSocket 종료 중 오류 (무시): {e}")
                    self.websocket = None
                self.disconnected.emit()

    async def _message_loop(self):
        """메시지 수신 루프 (동적 구독 업데이트 포함)"""
        while self.is_running and self.websocket and self.websocket.is_connected:
            # 대기 중인 구독 변경 처리
            await self._process_pending_subscriptions()

            # 짧은 대기 (CPU 부하 방지)
            await asyncio.sleep(0.1)

    async def _load_initial_symbols(self):
        """PositionManager에서 초기 심볼 로드"""
        try:
            positions = self.position_manager.get_all_positions()

            with self._subscription_lock:
                self._subscribed_symbols = set()
                # positions는 dict: {symbol: position_data}
                for symbol in positions.keys():
                    if symbol and symbol.startswith('KRW-'):
                        self._subscribed_symbols.add(symbol)

            count = len(self._subscribed_symbols)
            logger.info(f"📊 초기 구독 심볼 로드: {count}개")

            if count > 0:
                symbols_str = ", ".join(sorted(self._subscribed_symbols)[:5])
                if count > 5:
                    symbols_str += f" ... (+{count - 5}개)"
                logger.debug(f"   심볼: {symbols_str}")

        except Exception as e:
            logger.error(f"❌ 초기 심볼 로드 실패: {e}", exc_info=True)

    async def _subscribe_current_symbols(self):
        """현재 심볼 목록 구독"""
        with self._subscription_lock:
            symbols = list(self._subscribed_symbols)

        if not symbols:
            logger.warning("⚠️ 구독할 심볼 없음")
            return

        try:
            await self.websocket.subscribe_ticker(symbols)
            self.subscription_updated.emit(len(symbols))
            logger.info(f"📊 Ticker 구독 완료: {len(symbols)}개 심볼")
        except Exception as e:
            logger.error(f"❌ 구독 실패: {e}", exc_info=True)
            raise

    async def _process_pending_subscriptions(self):
        """대기 중인 구독 변경 처리"""
        with self._subscription_lock:
            has_changes = bool(self._pending_add or self._pending_remove)
            if not has_changes:
                return

            # 심볼 추가
            for symbol in self._pending_add:
                self._subscribed_symbols.add(symbol)

            # 심볼 제거
            for symbol in self._pending_remove:
                self._subscribed_symbols.discard(symbol)

            # 대기 목록 초기화
            self._pending_add.clear()
            self._pending_remove.clear()

        # 재구독 (새 메시지 전송으로 기존 구독 대체)
        if self.websocket and self.websocket.is_connected:
            try:
                await self._subscribe_current_symbols()
                logger.info("✅ 구독 업데이트 완료")
            except Exception as e:
                logger.error(f"❌ 구독 업데이트 실패: {e}", exc_info=True)

    def _on_tick(self, tick_data: Dict[str, Any]):
        """
        Tick 데이터 수신 콜백 (TickerWebSocket에서 호출)

        Args:
            tick_data: WebSocket에서 수신한 ticker 데이터
                       {'type': 'ticker', 'code': 'KRW-BTC', 'trade_price': 50000000, ...}
        """
        try:
            symbol = tick_data.get('code')
            trade_price = tick_data.get('trade_price')

            if not symbol or not trade_price:
                return

            # PositionManager 가격 업데이트
            if self.position_manager:
                self.position_manager.update_price(symbol, trade_price)

            # 시그널 발생 (GUI 업데이트용)
            self.price_updated.emit(symbol, trade_price)

        except Exception as e:
            logger.debug(f"Tick 처리 오류 (무시): {e}")

    def add_symbol(self, symbol: str):
        """
        구독 심볼 추가 (스레드 안전)

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')
        """
        if not symbol or not symbol.startswith('KRW-'):
            return

        with self._subscription_lock:
            if symbol not in self._subscribed_symbols and symbol not in self._pending_add:
                self._pending_add.add(symbol)
                self._pending_remove.discard(symbol)  # 제거 대기에서 제외
                logger.info(f"➕ 구독 추가 예약: {symbol}")

    def remove_symbol(self, symbol: str):
        """
        구독 심볼 제거 (스레드 안전)

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')
        """
        if not symbol:
            return

        with self._subscription_lock:
            if symbol in self._subscribed_symbols or symbol in self._pending_add:
                self._pending_remove.add(symbol)
                self._pending_add.discard(symbol)  # 추가 대기에서 제외
                logger.info(f"➖ 구독 제거 예약: {symbol}")

    def get_subscribed_symbols(self) -> List[str]:
        """
        현재 구독 중인 심볼 목록 반환

        Returns:
            List[str]: 심볼 리스트
        """
        with self._subscription_lock:
            return list(self._subscribed_symbols)

    def stop(self):
        """Worker 중지 요청"""
        logger.info("🛑 PositionTickerWorker 중지 요청")
        self.is_running = False

        # WebSocket 연결 종료 (이벤트 루프에서 실행)
        if self.websocket and self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.disconnect(),
                    self.loop
                )
            except Exception as e:
                logger.debug(f"WebSocket 종료 요청 중 오류 (무시): {e}")

    def __repr__(self) -> str:
        with self._subscription_lock:
            count = len(self._subscribed_symbols)
        return f"PositionTickerWorker(symbols={count}, running={self.is_running})"
