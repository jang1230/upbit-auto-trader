"""
WebSocket Manager - 통합 WebSocket 관리자 (Unified)

단일 WebSocket으로 여러 코인의 Ticker 데이터를 수신하고
symbol별로 CandleAggregator에 라우팅합니다.

개선 사항 (2025-12-03):
- 코인별 개별 WebSocket → 단일 통합 WebSocket
- 시작 시간 대폭 단축 (13개 코인 기준 16초 → 2초)
- Upbit 공식 권장 방식 적용
- GUI와 V4 엔진에서 공유 가능 (이중 WebSocket 제거)

주요 기능:
- 단일 TickerWebSocket으로 모든 코인 구독
- tick_router로 symbol별 CandleAggregator 라우팅
- GUI 가격 업데이트 콜백 지원
- PositionManager 가격 자동 업데이트
- 자동 재연결 지원
- 런타임 symbol 추가/제거 지원

Example:
    >>> manager = WebSocketManager(upbit_api)
    >>> manager.set_position_manager(position_manager)
    >>> manager.set_price_callback(on_price_updated)
    >>> await manager.add_symbol('KRW-BTC', 15, completed_candles)
    >>> await manager.add_symbol('KRW-ETH', 15)
    >>> await manager.start_all()  # 한 번에 모든 코인 구독
    >>> candles = manager.get_candles('KRW-BTC')
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
import pandas as pd

from core.candle_aggregator import CandleAggregator
from core.upbit_websocket import TickerWebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    통합 WebSocket 및 CandleAggregator 관리자

    구조:
    - TickerWebSocket 1개 (통합)
    - CandleAggregator N개 (코인별)
    - tick_router로 라우팅
    """

    # 재연결 설정
    MAX_RECONNECT_ATTEMPTS = 3
    RECONNECT_DELAY_SECONDS = 2.0

    def __init__(self, upbit_api=None, position_manager=None):
        """
        WebSocketManager 초기화

        Args:
            upbit_api: UpbitAPI 인스턴스 (초기 캔들 로드용)
            position_manager: PositionManager 인스턴스 (가격 업데이트용)
        """
        self.upbit_api = upbit_api

        # 단일 WebSocket (통합)
        self.websocket: Optional[TickerWebSocket] = None

        # symbol -> CandleAggregator
        self.aggregators: Dict[str, CandleAggregator] = {}

        # symbol -> candle_unit
        self.candle_units: Dict[str, int] = {}

        # 상태 관리
        self.is_running = False
        self._listening_task: Optional[asyncio.Task] = None
        self._reconnect_count = 0

        # 🆕 GUI 연동 (이중 WebSocket 제거)
        self.position_manager = position_manager  # 가격 업데이트용
        self.on_price_callback: Optional[Callable[[str, float], None]] = None  # GUI 콜백

        # 🆕 가격 전용 심볼 (CandleAggregator 없이 가격만 수신)
        self.price_only_symbols: set = set()

        logger.info("✅ WebSocketManager 초기화 완료 (통합 WebSocket 모드)")

    def _tick_router(self, tick_data: Dict[str, Any]):
        """
        통합 콜백: symbol별 CandleAggregator로 라우팅 + GUI 가격 업데이트

        Args:
            tick_data: WebSocket에서 수신한 ticker 데이터
                       {'type': 'ticker', 'code': 'KRW-BTC', 'trade_price': ..., ...}
        """
        try:
            symbol = tick_data.get('code')
            trade_price = tick_data.get('trade_price')

            if not symbol:
                return

            # 🆕 1. GUI 가격 업데이트 콜백 호출
            if self.on_price_callback and trade_price:
                try:
                    self.on_price_callback(symbol, trade_price)
                except Exception as e:
                    # GUI 콜백 에러가 WebSocket에 영향 주지 않도록
                    logger.debug(f"GUI 콜백 오류 (무시): {e}")

            # 🆕 2. PositionManager 가격 업데이트
            if self.position_manager and trade_price:
                try:
                    self.position_manager.update_price(symbol, trade_price)
                except Exception as e:
                    logger.debug(f"PositionManager 업데이트 오류 (무시): {e}")

            # 3. CandleAggregator 라우팅 (기존 로직)
            aggregator = self.aggregators.get(symbol)
            if aggregator:
                aggregator.on_tick(tick_data)

        except Exception as e:
            logger.error(f"❌ tick_router 오류: {e}", exc_info=True)

    async def add_symbol(
        self,
        symbol: str,
        candle_unit: int,
        completed_candles: Optional[List[Dict]] = None
    ):
        """
        코인 추가 (CandleAggregator만 생성, WebSocket은 start_all에서 통합 처리)

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')
            candle_unit: 캔들 단위 (분, 15/60/240)
            completed_candles: 과거 완성 캔들 리스트 (Optional)
                               None이면 REST API로 로드
        """
        if symbol in self.aggregators:
            logger.warning(f"⚠️ {symbol}: 이미 추가됨 (스킵)")
            return

        try:
            # 과거 캔들 로드 (없으면 REST API 사용)
            if completed_candles is None:
                completed_candles = await self._load_initial_candles(symbol, candle_unit)

            # CandleAggregator 생성
            aggregator = CandleAggregator(symbol, candle_unit, completed_candles)
            self.aggregators[symbol] = aggregator
            self.candle_units[symbol] = candle_unit

            logger.info(
                f"✅ {symbol} 추가 완료 "
                f"(캔들 단위: {candle_unit}분, 과거 캔들: {len(completed_candles)}개)"
            )

            # 이미 실행 중이면 재구독 필요
            if self.is_running:
                await self._resubscribe()

        except Exception as e:
            logger.error(f"❌ {symbol} 추가 실패: {e}", exc_info=True)
            raise

    async def remove_symbol(self, symbol: str):
        """
        코인 제거 (CandleAggregator 제거 + 재구독)

        Args:
            symbol: 코인 심볼
        """
        if symbol not in self.aggregators:
            logger.warning(f"⚠️ {symbol}: 존재하지 않음 (스킵)")
            return

        try:
            # 제거
            del self.aggregators[symbol]
            del self.candle_units[symbol]

            logger.info(f"✅ {symbol} 제거 완료")

            # 실행 중이면 재구독 (제거된 symbol 제외)
            if self.is_running:
                await self._resubscribe()

        except Exception as e:
            logger.error(f"❌ {symbol} 제거 실패: {e}", exc_info=True)

    async def start_all(self):
        """
        통합 WebSocket 연결 시작 (모든 코인 한 번에 구독)
        """
        if self.is_running:
            logger.warning("⚠️ 이미 실행 중입니다")
            return

        # 🆕 aggregators + price_only_symbols 모두 포함
        all_symbols = self.get_all_symbols()
        symbol_count = len(all_symbols)

        if symbol_count == 0:
            logger.warning("⚠️ 구독할 코인이 없습니다")
            return

        logger.info(f"🚀 통합 WebSocket 연결 시작 ({symbol_count}개 코인)")
        start_time = time.time()

        try:
            # 단일 WebSocket 생성 (tick_router 콜백 연결)
            self.websocket = TickerWebSocket(on_tick_callback=self._tick_router)

            # 연결
            await self.websocket.connect()

            # 모든 코인 한 번에 구독
            await self.websocket.subscribe_ticker(all_symbols)

            # 리스닝 시작 (백그라운드 태스크)
            self._listening_task = asyncio.create_task(
                self._listening_loop()
            )

            self.is_running = True
            self._reconnect_count = 0

            elapsed = time.time() - start_time
            logger.info(
                f"✅ 통합 WebSocket 연결 완료 "
                f"({symbol_count}개 코인, 1개 연결, {elapsed:.2f}초)"
            )

        except Exception as e:
            logger.error(f"❌ WebSocket 연결 실패: {e}", exc_info=True)
            await self._handle_connection_error()

    async def _listening_loop(self):
        """
        WebSocket 리스닝 루프 (연결 유지 + 자동 재연결)
        """
        try:
            if self.websocket:
                await self.websocket.start_listening()

        except Exception as e:
            logger.error(f"❌ WebSocket 리스닝 오류: {e}", exc_info=True)

            # 자동 재연결 시도
            if self.is_running:
                await self._handle_connection_error()

    async def _handle_connection_error(self):
        """
        연결 오류 처리 (자동 재연결)
        """
        if self._reconnect_count >= self.MAX_RECONNECT_ATTEMPTS:
            logger.error(
                f"❌ 재연결 실패: 최대 시도 횟수 초과 ({self.MAX_RECONNECT_ATTEMPTS}회)"
            )
            self.is_running = False
            return

        self._reconnect_count += 1
        logger.warning(
            f"🔄 재연결 시도 중... ({self._reconnect_count}/{self.MAX_RECONNECT_ATTEMPTS})"
        )

        await asyncio.sleep(self.RECONNECT_DELAY_SECONDS)

        try:
            # 기존 연결 정리
            if self.websocket:
                await self.websocket.disconnect()

            # 새로 연결
            self.websocket = TickerWebSocket(on_tick_callback=self._tick_router)
            await self.websocket.connect()

            # 재구독 (aggregators + price_only_symbols)
            all_symbols = self.get_all_symbols()
            await self.websocket.subscribe_ticker(all_symbols)

            # 리스닝 재시작
            self._listening_task = asyncio.create_task(
                self._listening_loop()
            )

            self._reconnect_count = 0
            logger.info("✅ 재연결 성공")

        except Exception as e:
            logger.error(f"❌ 재연결 실패: {e}", exc_info=True)
            await self._handle_connection_error()

    async def _resubscribe(self):
        """
        재구독 (연결 유지한 채로 symbol 리스트 변경)

        런타임에 코인 추가/제거 시 호출
        """
        if not self.websocket or not self.websocket.is_connected:
            logger.warning("⚠️ WebSocket 연결 안 됨 - 재구독 불가")
            return

        try:
            # 🆕 aggregators + price_only_symbols 모두 포함
            all_symbols = self.get_all_symbols()
            await self.websocket.subscribe_ticker(all_symbols)
            logger.info(f"✅ 재구독 완료: {len(all_symbols)}개 심볼")

        except Exception as e:
            logger.error(f"❌ 재구독 실패: {e}", exc_info=True)
            raise

    async def stop_all(self):
        """
        통합 WebSocket 연결 종료
        """
        if not self.is_running:
            logger.warning("⚠️ 실행 중이 아닙니다")
            return

        logger.info(f"🛑 통합 WebSocket 연결 종료 중")

        # 리스닝 태스크 취소
        if self._listening_task:
            self._listening_task.cancel()
            try:
                await self._listening_task
            except asyncio.CancelledError:
                pass
            self._listening_task = None

        # WebSocket 연결 종료
        if self.websocket:
            await self.websocket.disconnect()
            self.websocket = None

        self.is_running = False
        logger.info("✅ 통합 WebSocket 연결 종료 완료")

    def get_candles(self, symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
        """
        특정 코인의 캔들 데이터 가져오기

        Args:
            symbol: 코인 심볼
            count: 캔들 개수 (기본 200)

        Returns:
            pd.DataFrame: 캔들 데이터 (과거 199 + 현재 1)
                          해당 코인이 없으면 None
        """
        aggregator = self.aggregators.get(symbol)

        if aggregator is None:
            logger.warning(f"⚠️ {symbol}: CandleAggregator 없음")
            return None

        return aggregator.get_candles(count)

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        특정 코인의 현재가 가져오기 (진행 중인 캔들의 종가)

        Args:
            symbol: 코인 심볼

        Returns:
            float: 현재가 (없으면 None)
        """
        aggregator = self.aggregators.get(symbol)

        if aggregator is None or aggregator.current_candle is None:
            return None

        return aggregator.current_candle.get('close')

    def get_stats(self, symbol: Optional[str] = None) -> Dict:
        """
        통계 정보 반환

        Args:
            symbol: 특정 코인 심볼 (None이면 전체 통계)

        Returns:
            Dict: 통계 정보
        """
        if symbol:
            # 특정 코인 통계
            aggregator = self.aggregators.get(symbol)
            if aggregator:
                return aggregator.get_stats()
            else:
                return {}

        # 전체 통계
        total_stats = {
            'total_symbols': len(self.aggregators),
            'is_running': self.is_running,
            'websocket_connected': self.websocket.is_connected if self.websocket else False,
            'reconnect_count': self._reconnect_count,
            'symbols': {}
        }

        for sym, aggregator in self.aggregators.items():
            total_stats['symbols'][sym] = aggregator.get_stats()

        return total_stats

    async def _load_initial_candles(self, symbol: str, candle_unit: int) -> List[Dict]:
        """
        REST API로 초기 캔들 로드 (과거 199개)

        Args:
            symbol: 코인 심볼
            candle_unit: 캔들 단위 (분)

        Returns:
            List[Dict]: 과거 캔들 리스트
        """
        if not self.upbit_api:
            logger.warning(f"⚠️ {symbol}: UpbitAPI 없음 (초기 캔들 없이 시작)")
            return []

        try:
            logger.info(f"📊 {symbol}: 초기 캔들 로드 중 ({candle_unit}분봉, 199개)")

            # REST API 호출
            df = self.upbit_api.get_candles(symbol, str(candle_unit), count=199)

            if df is None or df.empty:
                logger.warning(f"⚠️ {symbol}: 캔들 데이터 없음")
                return []

            # DataFrame → Dict 리스트 변환
            candles = df.to_dict('records')

            logger.info(f"✅ {symbol}: 초기 캔들 로드 완료 ({len(candles)}개)")
            return candles

        except Exception as e:
            logger.error(f"❌ {symbol}: 초기 캔들 로드 실패: {e}", exc_info=True)
            return []

    # =========================================================================
    # 🆕 GUI 연동 메서드 (이중 WebSocket 제거용)
    # =========================================================================

    def set_position_manager(self, position_manager):
        """
        PositionManager 설정 (가격 업데이트용)

        Args:
            position_manager: PositionManager 인스턴스
        """
        self.position_manager = position_manager
        logger.info("✅ WebSocketManager: PositionManager 연결 완료")

    def set_price_callback(self, callback: Callable[[str, float], None]):
        """
        GUI 가격 업데이트 콜백 설정

        Args:
            callback: (symbol, price) → None 형태의 콜백 함수
        """
        self.on_price_callback = callback
        logger.info("✅ WebSocketManager: 가격 콜백 등록 완료")

    async def add_price_only_symbol(self, symbol: str):
        """
        가격만 수신할 심볼 추가 (CandleAggregator 없이)

        GUI에서 현재가만 필요한 경우 사용

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')
        """
        if symbol in self.price_only_symbols:
            return  # 이미 추가됨

        if symbol in self.aggregators:
            return  # CandleAggregator로 이미 등록됨

        self.price_only_symbols.add(symbol)
        logger.info(f"✅ {symbol} 가격 전용 심볼 추가")

        # 실행 중이면 재구독
        if self.is_running:
            await self._resubscribe()

    async def remove_price_only_symbol(self, symbol: str):
        """
        가격 전용 심볼 제거

        Args:
            symbol: 코인 심볼
        """
        if symbol not in self.price_only_symbols:
            return

        self.price_only_symbols.discard(symbol)
        logger.info(f"✅ {symbol} 가격 전용 심볼 제거")

        # 실행 중이면 재구독
        if self.is_running:
            await self._resubscribe()

    def get_all_symbols(self) -> List[str]:
        """
        모든 구독 심볼 반환 (aggregators + price_only)

        Returns:
            List[str]: 심볼 리스트
        """
        return list(set(self.aggregators.keys()) | self.price_only_symbols)

    def __repr__(self) -> str:
        return (
            f"WebSocketManager("
            f"symbols={len(self.aggregators)}, "
            f"price_only={len(self.price_only_symbols)}, "
            f"running={self.is_running}, "
            f"unified=True)"
        )
