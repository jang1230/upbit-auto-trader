"""
Candle Aggregator - 실시간 캔들 누적 엔진

WebSocket tick 데이터를 실시간으로 받아서 진행 중인 캔들을 계산합니다.

주요 기능:
- 과거 완성 캔들 199개 관리
- 현재 진행 중 캔들 1개 실시간 업데이트 (open, high, low, close, volume)
- 캔들 완성 시점 자동 감지 (15분/60분/240분)
- 완성 캔들 자동 저장 및 과거 캔들 리스트 관리
- 전략 계산용 200개 캔들 제공 (과거 199 + 현재 1)

Example:
    >>> aggregator = CandleAggregator('KRW-BTC', 15, completed_candles)
    >>> aggregator.on_tick({'trade_price': 95000000, 'timestamp': 1699677661000})
    >>> candles = aggregator.get_candles()  # 200개 캔들 반환
"""

import logging
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class CandleAggregator:
    """
    실시간 WebSocket tick 데이터로 진행 중인 캔들 계산

    캔들 구조:
    {
        'timestamp': '2025-11-11 11:00:00',  # 캔들 시작 시각
        'open': 95000000.0,                   # 시가
        'high': 95500000.0,                   # 고가
        'low': 94800000.0,                    # 저가
        'close': 95200000.0,                  # 종가 (현재가)
        'volume': 12.5,                       # 거래량
        'is_complete': False                  # 완성 여부
    }
    """

    def __init__(
        self,
        symbol: str,
        candle_unit: int,
        completed_candles: List[Dict]
    ):
        """
        CandleAggregator 초기화

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')
            candle_unit: 캔들 단위 (분, 15/60/240)
            completed_candles: 과거 완성 캔들 리스트 (최대 199개)
        """
        self.symbol = symbol
        self.candle_unit = int(candle_unit)

        # 과거 완성 캔들 (최대 199개 유지)
        self.completed_candles = deque(
            completed_candles[-199:] if completed_candles else [],
            maxlen=199
        )

        # 현재 진행 중인 캔들
        self.current_candle: Optional[Dict] = None

        # 통계
        self.tick_count = 0
        self.candles_completed = 0

        logger.info(
            f"✅ CandleAggregator 초기화: {symbol} "
            f"(단위: {candle_unit}분, 과거 캔들: {len(self.completed_candles)}개)"
        )

    def on_tick(self, tick_data: Dict):
        """
        WebSocket tick 수신 시 호출되는 콜백 메서드

        Args:
            tick_data: WebSocket tick 데이터
                {
                    'code': 'KRW-BTC',
                    'trade_price': 95000000.0,
                    'trade_volume': 0.5,
                    'acc_trade_volume_24h': 1500.0,
                    'timestamp': 1699677661000  # milliseconds
                }
        """
        self.tick_count += 1

        try:
            # 현재가 및 타임스탬프 추출
            current_price = float(tick_data.get('trade_price', 0))
            timestamp_ms = tick_data.get('timestamp', 0)

            if current_price == 0 or timestamp_ms == 0:
                logger.warning(f"⚠️ {self.symbol}: 잘못된 tick 데이터 (price={current_price}, ts={timestamp_ms})")
                return

            # 현재 캔들이 없으면 새로 시작
            if self.current_candle is None:
                self._start_new_candle(tick_data)
                return

            # 캔들 완성 시점 체크
            if self._is_candle_complete(timestamp_ms):
                self._finalize_current_candle()
                self._start_new_candle(tick_data)

            # 진행 중인 캔들 업데이트
            self._update_current_candle(tick_data)

        except Exception as e:
            logger.error(f"❌ {self.symbol} on_tick 오류: {e}", exc_info=True)

    def _start_new_candle(self, tick_data: Dict):
        """
        새로운 캔들 시작

        Args:
            tick_data: WebSocket tick 데이터
        """
        timestamp_ms = tick_data.get('timestamp', 0)
        current_price = float(tick_data.get('trade_price', 0))

        # 캔들 시작 시각 계산 (분 단위로 정렬)
        candle_start = self._get_candle_start_time(timestamp_ms)

        self.current_candle = {
            'timestamp': candle_start.strftime('%Y-%m-%d %H:%M:%S'),
            'open': current_price,
            'high': current_price,
            'low': current_price,
            'close': current_price,
            'volume': 0.0,
            'is_complete': False,
            '_start_ms': int(candle_start.timestamp() * 1000)  # 내부용
        }

        logger.debug(
            f"🕐 {self.symbol}: 새 캔들 시작 "
            f"({candle_start.strftime('%H:%M')}, 단위: {self.candle_unit}분)"
        )

    def _update_current_candle(self, tick_data: Dict):
        """
        진행 중인 캔들 업데이트

        Args:
            tick_data: WebSocket tick 데이터
        """
        if self.current_candle is None:
            return

        current_price = float(tick_data.get('trade_price', 0))
        trade_volume = float(tick_data.get('trade_volume', 0))

        # 고가/저가 업데이트
        self.current_candle['high'] = max(self.current_candle['high'], current_price)
        self.current_candle['low'] = min(self.current_candle['low'], current_price)

        # 종가 업데이트 (현재가)
        self.current_candle['close'] = current_price

        # 거래량 누적
        self.current_candle['volume'] += trade_volume

    def _is_candle_complete(self, current_timestamp_ms: int) -> bool:
        """
        캔들 완성 여부 확인

        Args:
            current_timestamp_ms: 현재 타임스탬프 (밀리초)

        Returns:
            bool: 캔들이 완성되었으면 True
        """
        if self.current_candle is None:
            return False

        candle_start_ms = self.current_candle.get('_start_ms', 0)
        elapsed_minutes = (current_timestamp_ms - candle_start_ms) / 60000

        # 캔들 단위만큼 시간이 지났으면 완성
        return elapsed_minutes >= self.candle_unit

    def _finalize_current_candle(self):
        """
        현재 캔들을 완성하고 과거 캔들 리스트에 추가
        """
        if self.current_candle is None:
            return

        # 완성 플래그 설정
        self.current_candle['is_complete'] = True

        # 내부 필드 제거
        if '_start_ms' in self.current_candle:
            del self.current_candle['_start_ms']

        # 과거 캔들 리스트에 추가 (deque가 자동으로 maxlen=199 유지)
        self.completed_candles.append(self.current_candle.copy())
        self.candles_completed += 1

        logger.info(
            f"✅ {self.symbol}: 캔들 완성 "
            f"({self.current_candle['timestamp']}, "
            f"종가: {self.current_candle['close']:,.0f}, "
            f"거래량: {self.current_candle['volume']:.2f})"
        )

        # 현재 캔들 초기화
        self.current_candle = None

    def _get_candle_start_time(self, timestamp_ms: int) -> datetime:
        """
        주어진 타임스탬프에서 캔들 시작 시각 계산

        Args:
            timestamp_ms: 타임스탬프 (밀리초)

        Returns:
            datetime: 캔들 시작 시각

        Examples:
            15분봉:
            - 11:07 → 11:00
            - 11:23 → 11:15
            - 11:45 → 11:45

            60분봉:
            - 11:30 → 11:00
            - 12:15 → 12:00

            240분봉:
            - 05:30 → 04:00
            - 10:00 → 08:00
        """
        dt = datetime.fromtimestamp(timestamp_ms / 1000)

        # 분 단위로 정렬
        minutes = (dt.minute // self.candle_unit) * self.candle_unit

        return dt.replace(minute=minutes, second=0, microsecond=0)

    def get_candles(self, count: int = 200) -> pd.DataFrame:
        """
        전략 계산용 캔들 데이터 반환 (과거 완성 + 현재 진행 중)

        Args:
            count: 반환할 캔들 개수 (기본 200)

        Returns:
            pd.DataFrame: 캔들 데이터 (과거 199개 + 현재 1개)
                columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
        all_candles = []

        # 과거 완성 캔들 추가
        all_candles.extend(list(self.completed_candles))

        # 현재 진행 중 캔들 추가 (있으면)
        if self.current_candle:
            all_candles.append(self.current_candle.copy())

        # 요청 개수만큼만 반환 (최신 데이터)
        if len(all_candles) > count:
            all_candles = all_candles[-count:]

        # DataFrame 변환
        if not all_candles:
            return pd.DataFrame()

        df = pd.DataFrame(all_candles)

        # is_complete 컬럼 제거 (전략에서 불필요)
        if 'is_complete' in df.columns:
            df = df.drop(columns=['is_complete'])

        # _start_ms 제거 (내부용)
        if '_start_ms' in df.columns:
            df = df.drop(columns=['_start_ms'])

        return df

    def get_stats(self) -> Dict:
        """
        통계 정보 반환

        Returns:
            Dict: 통계 정보
                {
                    'symbol': 'KRW-BTC',
                    'candle_unit': 15,
                    'completed_count': 199,
                    'tick_count': 1500,
                    'candles_completed': 5,
                    'current_candle': {...}
                }
        """
        return {
            'symbol': self.symbol,
            'candle_unit': self.candle_unit,
            'completed_count': len(self.completed_candles),
            'tick_count': self.tick_count,
            'candles_completed': self.candles_completed,
            'current_candle': self.current_candle.copy() if self.current_candle else None
        }

    def reset(self):
        """
        Aggregator 리셋 (테스트용)
        """
        self.current_candle = None
        self.tick_count = 0
        self.candles_completed = 0
        logger.info(f"🔄 {self.symbol}: CandleAggregator 리셋")
