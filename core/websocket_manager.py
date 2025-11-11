"""
WebSocket Manager - 멀티코인 WebSocket 관리자

여러 코인의 WebSocket 연결과 CandleAggregator를 동시에 관리합니다.

주요 기능:
- 코인별 TickerWebSocket 생성 및 관리
- 코인별 CandleAggregator 생성 및 연결
- WebSocket 시작/중지/재연결
- 전체 통계 정보 제공

Example:
    >>> manager = WebSocketManager(upbit_api)
    >>> await manager.add_symbol('KRW-BTC', 15, completed_candles)
    >>> await manager.start_all()
    >>> candles = manager.get_candles('KRW-BTC')
"""

import logging
import asyncio
from typing import Dict, List, Optional
import pandas as pd

from core.candle_aggregator import CandleAggregator
from core.upbit_websocket import TickerWebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    멀티코인 WebSocket 및 CandleAggregator 관리자

    각 코인마다:
    - TickerWebSocket 1개
    - CandleAggregator 1개
    """

    def __init__(self, upbit_api=None):
        """
        WebSocketManager 초기화

        Args:
            upbit_api: UpbitAPI 인스턴스 (초기 캔들 로드용)
        """
        self.upbit_api = upbit_api

        # symbol -> TickerWebSocket
        self.websockets: Dict[str, TickerWebSocket] = {}

        # symbol -> CandleAggregator
        self.aggregators: Dict[str, CandleAggregator] = {}

        # symbol -> candle_unit
        self.candle_units: Dict[str, int] = {}

        # 상태 관리
        self.is_running = False

        logger.info("✅ WebSocketManager 초기화 완료")

    async def add_symbol(
        self,
        symbol: str,
        candle_unit: int,
        completed_candles: Optional[List[Dict]] = None
    ):
        """
        코인 추가 (WebSocket + CandleAggregator 생성)

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')
            candle_unit: 캔들 단위 (분, 15/60/240)
            completed_candles: 과거 완성 캔들 리스트 (Optional)
                               None이면 REST API로 로드
        """
        if symbol in self.websockets:
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

            # TickerWebSocket 생성 (콜백 연결)
            ws = TickerWebSocket(on_tick_callback=aggregator.on_tick)
            self.websockets[symbol] = ws

            logger.info(
                f"✅ {symbol} 추가 완료 "
                f"(캔들 단위: {candle_unit}분, 과거 캔들: {len(completed_candles)}개)"
            )

        except Exception as e:
            logger.error(f"❌ {symbol} 추가 실패: {e}", exc_info=True)
            raise

    async def remove_symbol(self, symbol: str):
        """
        코인 제거 (WebSocket 연결 종료)

        Args:
            symbol: 코인 심볼
        """
        if symbol not in self.websockets:
            logger.warning(f"⚠️ {symbol}: 존재하지 않음 (스킵)")
            return

        try:
            # WebSocket 연결 종료
            ws = self.websockets[symbol]
            await ws.disconnect()

            # 제거
            del self.websockets[symbol]
            del self.aggregators[symbol]
            del self.candle_units[symbol]

            logger.info(f"✅ {symbol} 제거 완료")

        except Exception as e:
            logger.error(f"❌ {symbol} 제거 실패: {e}", exc_info=True)

    async def start_all(self):
        """
        모든 WebSocket 연결 시작
        """
        if self.is_running:
            logger.warning("⚠️ 이미 실행 중입니다")
            return

        logger.info(f"🚀 WebSocket 연결 시작 (총 {len(self.websockets)}개 코인)")

        tasks = []
        for symbol, ws in self.websockets.items():
            tasks.append(self._start_websocket(symbol, ws))

        # 모든 WebSocket 동시 시작
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 확인
        success_count = sum(1 for r in results if r is True)
        fail_count = len(results) - success_count

        if fail_count > 0:
            logger.warning(f"⚠️ WebSocket 연결: 성공 {success_count}개, 실패 {fail_count}개")
        else:
            logger.info(f"✅ 모든 WebSocket 연결 성공 ({success_count}개)")

        self.is_running = True

    async def _start_websocket(self, symbol: str, ws: TickerWebSocket) -> bool:
        """
        개별 WebSocket 연결 시작

        Args:
            symbol: 코인 심볼
            ws: TickerWebSocket 인스턴스

        Returns:
            bool: 성공 여부
        """
        try:
            # 연결
            await ws.connect()

            # Ticker 구독
            await ws.subscribe_ticker([symbol])

            # 리스닝 시작 (백그라운드 태스크)
            asyncio.create_task(ws.start_listening())

            logger.info(f"✅ {symbol}: WebSocket 연결 및 구독 완료")
            return True

        except Exception as e:
            logger.error(f"❌ {symbol}: WebSocket 연결 실패: {e}", exc_info=True)
            return False

    async def stop_all(self):
        """
        모든 WebSocket 연결 종료
        """
        if not self.is_running:
            logger.warning("⚠️ 실행 중이 아닙니다")
            return

        logger.info(f"🛑 WebSocket 연결 종료 중 (총 {len(self.websockets)}개 코인)")

        tasks = []
        for ws in self.websockets.values():
            tasks.append(ws.disconnect())

        await asyncio.gather(*tasks, return_exceptions=True)

        self.is_running = False
        logger.info("✅ 모든 WebSocket 연결 종료 완료")

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
            'total_symbols': len(self.websockets),
            'is_running': self.is_running,
            'symbols': {}
        }

        for symbol, aggregator in self.aggregators.items():
            total_stats['symbols'][symbol] = aggregator.get_stats()

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

    def __repr__(self) -> str:
        return (
            f"WebSocketManager("
            f"symbols={len(self.websockets)}, "
            f"running={self.is_running})"
        )
