"""
공격적 테스트 전략
Aggressive Test Strategy

테스트용 전략으로, 포지션이 없을 때마다 매수 신호를 발생시킵니다.
실제 거래에는 사용하지 마세요!

Usage:
    from core.strategies.aggressive_test_strategy import AggressiveTestStrategy

    strategy = AggressiveTestStrategy()
    signal = strategy.generate_signal(candles)
"""

from core.strategies.base import BaseStrategy
import pandas as pd
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AggressiveTestStrategy(BaseStrategy):
    """
    공격적 테스트 전략

    ⚠️ 테스트 전용: 포지션이 없을 때마다 즉시 매수 신호 발생
    - 버퍼가 준비되면 첫 캔들에서 즉시 매수
    - 매도는 리스크 관리자가 처리
    - 실제 거래에는 절대 사용 금지!
    """

    def __init__(self):
        """공격적 테스트 전략 초기화"""
        super().__init__("Aggressive Test")
        self.buy_count = 0  # 매수 신호 발생 횟수

    def generate_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """
        매매 신호 생성: 포지션 없으면 즉시 매수

        Args:
            candles: 캔들 데이터 DataFrame

        Returns:
            'buy' - 포지션이 없을 때
            None - 포지션이 있을 때
        """
        # 데이터 부족 시 신호 없음
        if candles is None or len(candles) < 1:
            return None

        # 포지션 없으면 즉시 매수
        if self.is_flat():
            self.buy_count += 1
            logger.info(f"🚨 [테스트 전략] 매수 신호 발생 (#{self.buy_count})")
            self.set_position('long')
            return 'buy'

        # 포지션 있으면 신호 없음 (매도는 리스크 관리자가 처리)
        return None

    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            'strategy': 'Aggressive Test',
            'description': '⚠️ 테스트 전용 - 포지션 없을 때마다 즉시 매수',
            'buy_count': self.buy_count
        }

    def reset(self):
        """상태 초기화"""
        super().reset()
        self.buy_count = 0


if __name__ == "__main__":
    """테스트 코드"""
    print("=== AggressiveTestStrategy 테스트 ===\n")

    # 테스트 데이터 생성
    dates = pd.date_range('2024-01-01', periods=5, freq='1min')
    candles = pd.DataFrame({
        'open': [100, 102, 101, 103, 105],
        'high': [102, 103, 102, 104, 106],
        'low': [99, 101, 100, 102, 104],
        'close': [101, 102, 101, 103, 105],
        'volume': [1.0] * 5
    }, index=dates)

    strategy = AggressiveTestStrategy()
    print(f"전략 이름: {strategy.name}")
    print(f"파라미터: {strategy.get_parameters()}\n")

    # 캔들 순회
    for i in range(len(candles)):
        current_candles = candles.iloc[:i+1]
        signal = strategy.generate_signal(current_candles)

        print(f"캔들 {i+1}: 신호={signal}, 포지션={strategy.get_position()}")

        # 매도 시뮬레이션 (포지션 있을 때)
        if i == 2 and strategy.is_long():
            strategy.set_position(None)
            print(f"  → [시뮬] 포지션 청산 → 포지션={strategy.get_position()}")

    print(f"\n최종 파라미터: {strategy.get_parameters()}")
    print("\n=== 테스트 완료 ===")
