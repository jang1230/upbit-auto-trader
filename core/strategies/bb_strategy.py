"""
Bollinger Bands 전략 모듈
Bollinger Bands Strategy

볼린저 밴드 돌파를 이용한 변동성 기반 매매 전략입니다.

전략 로직:
- 가격 < Lower Band: 과매도 → 매수
- 가격 > Upper Band: 과매수 → 매도

특징:
- 변동성 기반 전략으로 횡보장에서 효과적
- 밴드 터치 후 중간선 회귀 특성 활용
- 강한 추세장에서는 밴드를 벗어나 손실 가능

사용법:
    from core.strategies.bb_strategy import BollingerBands_Strategy

    strategy = BollingerBands_Strategy(period=20, std_dev=2.0)
    signal = strategy.generate_signal(candles)
"""

import pandas as pd
from typing import Optional, Dict, Any
import logging

from core.strategies.base import BaseStrategy
from core.indicators import calculate_bollinger_bands

logger = logging.getLogger(__name__)


class BollingerBands_Strategy(BaseStrategy):
    """
    볼린저 밴드 돌파 전략

    가격이 볼린저 밴드 하단/상단을 돌파할 때 진입/청산하는 회귀 전략입니다.

    Parameters:
        - period: 이동평균 기간 (기본 20)
        - std_dev: 표준편차 배수 (기본 2.0)

    매매 로직:
        1. 포지션 없을 때:
           - 가격 < Lower Band → 매수 (중간선 회귀 기대)
        2. 롱 포지션 있을 때:
           - 가격 > Upper Band → 매도 (중간선 회귀 기대)

    참고:
        - 밴드 폭이 좁을수록 변동성 감소 → 큰 움직임 예상
        - 밴드 폭이 넓을수록 변동성 증가 → 추세 진행 중
    """

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0
    ):
        """
        Args:
            period: 볼린저 밴드 기간
            std_dev: 표준편차 배수
        """
        if period < 2:
            raise ValueError(f"period({period}) must be >= 2")
        if std_dev <= 0:
            raise ValueError(f"std_dev({std_dev}) must be > 0")

        super().__init__(f"BB Strategy (period={period}, std={std_dev})")

        self.period = period
        self.std_dev = std_dev

        logger.info(f"볼린저 밴드 전략 초기화: period={period}, std_dev={std_dev}")

    def generate_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """
        볼린저 밴드 기반 매매 신호 생성

        Args:
            candles: 캔들 데이터 (최소 period+1개 필요)

        Returns:
            Optional[str]: 'buy', 'sell', None
        """
        # 최소 데이터 확인
        if len(candles) < self.period + 1:
            logger.debug(f"BB 전략: 데이터 부족 ({len(candles)} < {self.period + 1})")
            return None

        # 볼린저 밴드 계산
        upper_band, middle_band, lower_band = calculate_bollinger_bands(
            candles['close'],
            self.period,
            self.std_dev
        )

        # 현재 값
        current_price = candles['close'].iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_middle = middle_band.iloc[-1]

        # 밴드 폭 (변동성 지표)
        band_width = (current_upper - current_lower) / current_middle * 100

        logger.debug(f"BB 전략: Price={current_price:.2f}, "
                    f"Lower={current_lower:.2f}, Upper={current_upper:.2f}, "
                    f"Width={band_width:.2f}%, Position={self.position}")

        # 포지션 없을 때 - 하단 밴드 돌파 시 매수
        if self.is_flat():
            if current_price < current_lower:
                logger.info(f"BB 매수 신호: Price={current_price:.2f} < Lower={current_lower:.2f}")
                self.set_position('long')
                return 'buy'

        # 롱 포지션 있을 때 - 상단 밴드 돌파 시 매도
        elif self.is_long():
            if current_price > current_upper:
                logger.info(f"BB 매도 신호: Price={current_price:.2f} > Upper={current_upper:.2f}")
                self.set_position(None)
                return 'sell'

        return None

    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            'strategy': 'Bollinger Bands',
            'period': self.period,
            'std_dev': self.std_dev,
            'position': self.position
        }


if __name__ == "__main__":
    """
    BollingerBands_Strategy 테스트 코드
    """
    import numpy as np

    print("=== BollingerBands_Strategy 테스트 ===\n")

    # 테스트 데이터 생성 (변동성 변화 포함)
    dates = pd.date_range('2024-01-01', periods=60, freq='1D')

    # 가격 시뮬레이션
    # 1. 안정적 횡보 (밴드 폭 좁음)
    # 2. 급등 (하단 → 상단)
    # 3. 다시 횡보
    prices = []
    base = 100

    # 안정적 횡보 (20일)
    for i in range(20):
        base += np.random.uniform(-0.5, 0.5)
        prices.append(base)

    # 급등 (15일)
    for i in range(15):
        base += np.random.uniform(1, 3)
        prices.append(base)

    # 다시 횡보 (25일)
    peak = base
    for i in range(25):
        base = peak + np.random.uniform(-2, 2)
        prices.append(base)

    candles = pd.DataFrame({
        'open': prices,
        'high': [p + np.random.uniform(0, 1) for p in prices],
        'low': [p - np.random.uniform(0, 1) for p in prices],
        'close': prices,
        'volume': [1000 + np.random.uniform(-100, 100) for _ in prices]
    }, index=dates)

    # BB 전략 초기화
    print("1. BollingerBands_Strategy 초기화")
    strategy = BollingerBands_Strategy(period=20, std_dev=2.0)
    print(f"   전략: {strategy.name}")
    print(f"   파라미터: {strategy.get_parameters()}\n")

    # 백테스팅 시뮬레이션
    print("2. 매매 신호 생성")
    print(f"   {'날짜':<12} {'종가':>8} {'하단':>8} {'중간':>8} {'상단':>8} {'신호':>6} {'포지션':>8}")
    print("   " + "-" * 75)

    signals = []
    for i in range(len(candles)):
        current_candles = candles.iloc[:i+1]
        signal = strategy.generate_signal(current_candles)

        # BB 계산 (출력용)
        if len(current_candles) >= 21:
            from core.indicators import calculate_bollinger_bands
            upper, middle, lower = calculate_bollinger_bands(current_candles['close'], 20, 2.0)
            current_lower = lower.iloc[-1]
            current_middle = middle.iloc[-1]
            current_upper = upper.iloc[-1]
        else:
            current_lower = current_middle = current_upper = 100.0

        # 신호가 있거나 중요 시점이면 출력
        if signal or i == 0 or i == len(candles) - 1 or (i > 20 and i % 8 == 0):
            date_str = current_candles.index[-1].strftime('%Y-%m-%d')
            close = current_candles['close'].iloc[-1]
            signal_str = signal or '-'
            pos_str = strategy.position or 'None'

            print(f"   {date_str} {close:8.2f} {current_lower:8.2f} {current_middle:8.2f} "
                  f"{current_upper:8.2f} {signal_str:>6} {pos_str:>8}")

            if signal:
                signals.append({
                    'date': date_str,
                    'price': close,
                    'lower': current_lower,
                    'upper': current_upper,
                    'signal': signal
                })

    # 매매 통계
    print(f"\n3. 매매 통계")
    print(f"   총 신호: {len(signals)}개")

    buy_signals = [s for s in signals if s['signal'] == 'buy']
    sell_signals = [s for s in signals if s['signal'] == 'sell']

    print(f"   매수: {len(buy_signals)}회")
    for s in buy_signals:
        print(f"      {s['date']}: {s['price']:.2f}원 (Lower={s['lower']:.2f})")

    print(f"   매도: {len(sell_signals)}회")
    for s in sell_signals:
        print(f"      {s['date']}: {s['price']:.2f}원 (Upper={s['upper']:.2f})")

    # 간단한 수익률 계산
    if len(buy_signals) > 0 and len(sell_signals) > 0:
        total_return = 0
        for i in range(min(len(buy_signals), len(sell_signals))):
            buy_price = buy_signals[i]['price']
            sell_price = sell_signals[i]['price']
            ret = ((sell_price - buy_price) / buy_price) * 100
            total_return += ret
            print(f"\n   거래 {i+1}: {ret:+.2f}% ({buy_price:.2f} → {sell_price:.2f})")

        print(f"\n   평균 수익률: {total_return / min(len(buy_signals), len(sell_signals)):+.2f}%")

    print("\n=== 테스트 완료 ===")
