"""
전략 베이스 클래스
Base Strategy Abstract Class

모든 트레이딩 전략은 이 추상 클래스를 상속받아 구현합니다.

주요 메서드:
- generate_signal(): 매매 신호 생성 (buy, sell, None)
- get_parameters(): 전략 파라미터 반환
- reset(): 전략 상태 초기화

사용법:
    from core.strategies.base import BaseStrategy

    class MyStrategy(BaseStrategy):
        def generate_signal(self, candles):
            # 매매 로직 구현
            return 'buy' if condition else None
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    트레이딩 전략 추상 클래스

    모든 전략은 이 클래스를 상속받아 generate_signal() 메서드를 구현해야 합니다.

    Attributes:
        name (str): 전략 이름
        position (str): 현재 포지션 상태 ('long', 'short', None)
    """

    def __init__(self, name: str):
        """
        Args:
            name: 전략 이름
        """
        self.name = name
        self.position: Optional[str] = None  # 'long', 'short', None

        logger.info(f"전략 초기화: {self.name}")

    @abstractmethod
    def generate_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """
        매매 신호 생성 (서브클래스에서 반드시 구현)

        Args:
            candles: 캔들 데이터 DataFrame
                     index: timestamp (datetime)
                     columns: open, high, low, close, volume

        Returns:
            Optional[str]: 매매 신호
                - 'buy': 매수 신호
                - 'sell': 매도 신호
                - None: 신호 없음

        Example:
            >>> signal = strategy.generate_signal(candles)
            >>> if signal == 'buy':
            >>>     # 매수 실행
            >>> elif signal == 'sell':
            >>>     # 매도 실행
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        전략 파라미터 반환 (서브클래스에서 반드시 구현)

        Returns:
            Dict[str, Any]: 전략 파라미터 딕셔너리

        Example:
            >>> params = strategy.get_parameters()
            >>> print(f"RSI Period: {params['period']}")
        """
        pass

    def reset(self):
        """
        전략 상태 초기화

        백테스팅 시작 전이나 새로운 심볼로 전환할 때 호출합니다.
        """
        self.position = None
        logger.debug(f"{self.name} 상태 초기화")

    def set_position(self, position: Optional[str]):
        """
        포지션 설정

        Args:
            position: 'long', 'short', None
        """
        if position not in ['long', 'short', None]:
            raise ValueError(f"Invalid position: {position}. Must be 'long', 'short', or None")

        self.position = position
        logger.debug(f"{self.name} 포지션 변경: {position}")

    def get_position(self) -> Optional[str]:
        """
        현재 포지션 반환

        Returns:
            Optional[str]: 'long', 'short', None
        """
        return self.position

    def is_long(self) -> bool:
        """롱 포지션 여부"""
        return self.position == 'long'

    def is_short(self) -> bool:
        """숏 포지션 여부 (현물 거래에서는 사용 안 함)"""
        return self.position == 'short'

    def is_flat(self) -> bool:
        """포지션 없음 여부"""
        return self.position is None

    def __str__(self) -> str:
        """전략 정보 문자열 반환"""
        return f"{self.name} (Position: {self.position or 'None'})"

    def __repr__(self) -> str:
        """전략 객체 표현"""
        return f"<{self.__class__.__name__}: {self.name}>"


class SimpleStrategy(BaseStrategy):
    """
    간단한 Buy & Hold 전략 (테스트용)

    초기에 매수하고 마지막에 매도하는 단순 전략입니다.
    백테스팅 시스템 테스트 및 비교 기준으로 사용됩니다.
    """

    def __init__(self, hold_periods: Optional[int] = None):
        """
        Args:
            hold_periods: 보유 기간 (None이면 전체 기간 보유)
        """
        super().__init__("Buy & Hold")
        self.hold_periods = hold_periods
        self.bought = False
        self.hold_count = 0

    def generate_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """
        Buy & Hold 신호 생성

        첫 캔들에서 매수, 마지막 또는 지정 기간 후 매도
        """
        # 첫 캔들에서 매수
        if len(candles) == 1 and not self.bought:
            self.bought = True
            self.hold_count = 0
            self.set_position('long')
            return 'buy'

        # 보유 기간 설정된 경우
        if self.hold_periods is not None and self.is_long():
            self.hold_count += 1
            if self.hold_count >= self.hold_periods:
                self.set_position(None)
                self.bought = False
                self.hold_count = 0
                return 'sell'

        return None

    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            'strategy': 'Buy & Hold',
            'hold_periods': self.hold_periods or 'unlimited'
        }

    def reset(self):
        """상태 초기화"""
        super().reset()
        self.bought = False
        self.hold_count = 0


if __name__ == "__main__":
    """
    BaseStrategy 테스트 코드
    """
    print("=== BaseStrategy 테스트 ===\n")

    # 테스트 데이터 생성
    dates = pd.date_range('2024-01-01', periods=10, freq='1D')
    candles = pd.DataFrame({
        'open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 110],
        'high': [102, 103, 102, 104, 106, 105, 107, 109, 108, 111],
        'low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 109],
        'close': [101, 102, 101, 103, 105, 104, 106, 108, 107, 110],
        'volume': [1.0] * 10
    }, index=dates)

    # SimpleStrategy 테스트
    print("1. SimpleStrategy (Buy & Hold) 테스트")
    strategy = SimpleStrategy()
    print(f"   전략 이름: {strategy.name}")
    print(f"   초기 포지션: {strategy.get_position()}")

    # 캔들 순회
    signals = []
    for i in range(len(candles)):
        current_candles = candles.iloc[:i+1]
        signal = strategy.generate_signal(current_candles)

        if signal:
            signals.append((i, signal, strategy.get_position()))
            print(f"   캔들 {i+1}: {signal} → 포지션: {strategy.get_position()}")

    print(f"\n   총 신호 수: {len(signals)}개")
    print(f"   파라미터: {strategy.get_parameters()}")

    # 기간 제한 테스트
    print("\n2. SimpleStrategy (5일 보유) 테스트")
    strategy2 = SimpleStrategy(hold_periods=5)
    strategy2.reset()

    signals2 = []
    for i in range(len(candles)):
        current_candles = candles.iloc[:i+1]
        signal = strategy2.generate_signal(current_candles)

        if signal:
            signals2.append((i, signal))
            print(f"   캔들 {i+1}: {signal}")

    print(f"\n   총 신호 수: {len(signals2)}개")

    # 상태 메서드 테스트
    print("\n3. 상태 메서드 테스트")
    strategy3 = SimpleStrategy()
    print(f"   is_flat(): {strategy3.is_flat()}")

    strategy3.set_position('long')
    print(f"   set_position('long')")
    print(f"   is_long(): {strategy3.is_long()}")
    print(f"   is_flat(): {strategy3.is_flat()}")

    strategy3.reset()
    print(f"   reset()")
    print(f"   is_flat(): {strategy3.is_flat()}")

    print("\n=== 테스트 완료 ===")
