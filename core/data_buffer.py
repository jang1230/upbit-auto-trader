"""
Candle Data Buffer
캔들 데이터 버퍼

실시간 캔들 데이터를 버퍼링하여 전략에 전달합니다.

Example:
    >>> buffer = CandleBuffer(max_size=200)
    >>> buffer.add_candle({...})
    >>> if buffer.is_ready():
    >>>     candles = buffer.get_candles(100)
    >>>     signal = strategy.generate_signal(candles)
"""

import pandas as pd
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CandleBuffer:
    """
    캔들 데이터 버퍼

    실시간으로 수신되는 캔들 데이터를 DataFrame으로 관리합니다.
    """

    def __init__(self, max_size: int = 500, required_count: int = 100):
        """
        캔들 버퍼 초기화

        Args:
            max_size: 최대 버퍼 크기
            required_count: 전략 실행에 필요한 최소 캔들 수
        """
        self.max_size = max_size
        self.required_count = required_count

        # 캔들 데이터 (DataFrame)
        self.candles = pd.DataFrame(columns=[
            'timestamp',
            'open',
            'high',
            'low',
            'close',
            'volume'
        ])

        # 🔧 실시간 캔들 추적 (과거 데이터 로드 후 실시간 대기용)
        self.realtime_candle_count = 0  # WebSocket으로 받은 실시간 캔들 수
        self.historical_loaded = False  # 과거 데이터 로드 완료 여부

        logger.info(f"캔들 버퍼 초기화: max_size={max_size}, required={required_count}")

    def add_candle(self, candle: Dict, is_realtime: bool = True):
        """
        새 캔들 추가

        Args:
            candle: 캔들 데이터
                {
                    'timestamp': datetime,
                    'opening_price': float,
                    'high_price': float,
                    'low_price': float,
                    'trade_price': float,
                    'candle_acc_trade_volume': float
                }
            is_realtime: 실시간 캔들 여부 (False면 과거 데이터)
        """
        # 캔들 데이터 변환
        new_candle = pd.DataFrame([{
            'timestamp': candle.get('timestamp', datetime.now()),
            'open': candle.get('opening_price', candle.get('open')),
            'high': candle.get('high_price', candle.get('high')),
            'low': candle.get('low_price', candle.get('low')),
            'close': candle.get('trade_price', candle.get('close')),
            'volume': candle.get('candle_acc_trade_volume', candle.get('volume'))
        }])

        # 타임스탬프를 인덱스로 설정
        new_candle.set_index('timestamp', inplace=True)

        # 기존 데이터와 병합
        self.candles = pd.concat([self.candles, new_candle])

        # 중복 제거 (같은 시각의 캔들은 최신 것만 유지)
        was_duplicate = self.candles.index.duplicated(keep='last').any()
        self.candles = self.candles[~self.candles.index.duplicated(keep='last')]

        # 시간 순 정렬
        self.candles.sort_index(inplace=True)

        # 최대 크기 초과 시 오래된 데이터 제거
        if len(self.candles) > self.max_size:
            self.candles = self.candles.iloc[-self.max_size:]

        # 🔧 실시간 캔들 카운트 증가 (중복이 아닌 경우만)
        if is_realtime and not was_duplicate:
            self.realtime_candle_count += 1
            logger.debug(f"📊 실시간 캔들 추가: {candle.get('timestamp')} | 실시간={self.realtime_candle_count}/{self.required_count}")
        elif not is_realtime:
            logger.debug(f"📚 과거 캔들 추가: {candle.get('timestamp')} | 버퍼={len(self.candles)}")
        else:
            logger.debug(f"🔄 캔들 업데이트 (중복): {candle.get('timestamp')}")

    def get_candles(self, count: Optional[int] = None) -> pd.DataFrame:
        """
        최근 N개 캔들 반환

        Args:
            count: 반환할 캔들 수 (None이면 전체)

        Returns:
            pd.DataFrame: 캔들 데이터 (timestamp가 인덱스)
        """
        if count is None:
            return self.candles.copy()

        return self.candles.iloc[-count:].copy()

    def is_ready(self) -> bool:
        """
        전략 실행 가능 여부 확인

        Returns:
            bool: 필요한 캔들 수가 충족되었는지 여부
        """
        # 🔧 과거 데이터 로드 여부와 무관하게 총 버퍼 크기로 판단
        # 200개 과거 데이터 로드 시 즉시 전략 실행 가능 (20분 대기 불필요)
        # - BB 계산: 20개 필요 ✅
        # - MA240: 240개 필요 → 200개로 최선
        return len(self.candles) >= self.required_count

    def mark_historical_loaded(self):
        """
        과거 데이터 로드 완료 표시
        
        Note: is_ready()는 총 버퍼 크기로 판단하므로 과거 데이터만으로 즉시 준비 완료
        """
        self.historical_loaded = True
        self.realtime_candle_count = 0  # 실시간 카운터 초기화
        logger.info(f"✅ 과거 데이터 로드 완료 → 버퍼 준비됨 (총 {len(self.candles)}개 캔들)")

    def get_latest_candle(self) -> Optional[Dict]:
        """
        최신 캔들 반환

        Returns:
            Dict: 최신 캔들 데이터
        """
        if len(self.candles) == 0:
            return None

        latest = self.candles.iloc[-1]

        return {
            'timestamp': self.candles.index[-1],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'volume': latest['volume']
        }

    def get_latest_price(self) -> Optional[float]:
        """
        최신 가격 반환

        Returns:
            float: 최신 종가
        """
        if len(self.candles) == 0:
            return None

        return self.candles.iloc[-1]['close']

    def clear(self):
        """버퍼 초기화"""
        self.candles = pd.DataFrame(columns=[
            'timestamp',
            'open',
            'high',
            'low',
            'close',
            'volume'
        ])
        logger.info("캔들 버퍼 초기화됨")

    def get_info(self) -> Dict:
        """
        버퍼 정보 반환

        Returns:
            Dict: 버퍼 상태 정보
        """
        if len(self.candles) == 0:
            return {
                'size': 0,
                'is_ready': False,
                'latest_price': None
            }

        return {
            'size': len(self.candles),
            'max_size': self.max_size,
            'required_count': self.required_count,
            'is_ready': self.is_ready(),
            'latest_timestamp': self.candles.index[-1],
            'latest_price': self.get_latest_price(),
            'price_range': {
                'min': self.candles['close'].min(),
                'max': self.candles['close'].max(),
                'avg': self.candles['close'].mean()
            }
        }

    def __len__(self) -> int:
        """버퍼 크기 반환"""
        return len(self.candles)

    def __repr__(self) -> str:
        return f"CandleBuffer(size={len(self)}, ready={self.is_ready()})"


# 테스트 코드
if __name__ == "__main__":
    """테스트: 캔들 버퍼 동작 확인"""
    print("=== Candle Buffer 테스트 ===\n")

    # 1. 버퍼 생성
    buffer = CandleBuffer(max_size=10, required_count=5)
    print(f"버퍼 생성: {buffer}\n")

    # 2. 캔들 추가
    print("캔들 추가 중...")
    for i in range(7):
        candle = {
            'timestamp': datetime.now(),
            'opening_price': 100000000 + i * 1000000,
            'high_price': 100100000 + i * 1000000,
            'low_price': 99900000 + i * 1000000,
            'trade_price': 100000000 + i * 1000000,
            'candle_acc_trade_volume': 10.5 + i
        }
        buffer.add_candle(candle)
        print(f"  [{i+1}] 추가 완료 | 버퍼 크기: {len(buffer)} | Ready: {buffer.is_ready()}")

    print()

    # 3. 최신 캔들 조회
    latest = buffer.get_latest_candle()
    print(f"최신 캔들:")
    print(f"  시각: {latest['timestamp']}")
    print(f"  종가: {latest['close']:,.0f}원")
    print(f"  거래량: {latest['volume']:.2f}\n")

    # 4. 최근 3개 캔들 조회
    recent_3 = buffer.get_candles(3)
    print(f"최근 3개 캔들:")
    print(recent_3)
    print()

    # 5. 버퍼 정보
    info = buffer.get_info()
    print(f"버퍼 정보:")
    for key, value in info.items():
        print(f"  {key}: {value}")

    print("\n✅ 테스트 완료")
