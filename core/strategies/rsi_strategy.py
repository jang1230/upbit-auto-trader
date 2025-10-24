"""
RSI 전략 모듈
RSI (Relative Strength Index) Strategy

RSI 과매수/과매도 구간을 이용한 역추세 매매 전략입니다.

전략 로직:
- RSI < oversold (기본 30): 과매도 → 매수
- RSI > overbought (기본 70): 과매수 → 매도

특징:
- 단순하고 효과적인 역추세 전략
- 횡보장에서 좋은 성과
- 강한 추세장에서는 손실 가능

사용법:
    from core.strategies.rsi_strategy import RSI_Strategy

    strategy = RSI_Strategy(period=14, oversold=30, overbought=70)
    signal = strategy.generate_signal(candles)
"""

import pandas as pd
from typing import Optional, Dict, Any
import logging

from core.strategies.base import BaseStrategy
from core.indicators import calculate_rsi

logger = logging.getLogger(__name__)


class RSI_Strategy(BaseStrategy):
    """
    RSI 과매수/과매도 전략

    RSI 지표를 사용하여 과매수/과매도 구간에서 역추세 매매를 수행합니다.

    Parameters:
        - period: RSI 계산 기간 (기본 14)
        - oversold: 과매도 기준 (기본 30, 이하면 매수)
        - overbought: 과매수 기준 (기본 70, 이상이면 매도)

    매매 로직:
        1. 포지션 없을 때:
           - RSI < oversold → 매수
        2. 롱 포지션 있을 때:
           - RSI > overbought → 매도
    """

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30,
        overbought: float = 70
    ):
        """
        Args:
            period: RSI 계산 기간
            oversold: 과매도 기준 (0-100)
            overbought: 과매수 기준 (0-100)
        """
        # 파라미터 검증
        if not (0 < oversold < overbought < 100):
            raise ValueError(f"Invalid parameters: 0 < oversold({oversold}) < overbought({overbought}) < 100")

        super().__init__(f"RSI Strategy (period={period}, OS={oversold}, OB={overbought})")

        self.period = period
        self.oversold = oversold
        self.overbought = overbought

        logger.info(f"RSI 전략 초기화: period={period}, oversold={oversold}, overbought={overbought}")

    def generate_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """
        RSI 기반 매매 신호 생성

        Args:
            candles: 캔들 데이터 (최소 period+1개 필요)

        Returns:
            Optional[str]: 'buy', 'sell', None
        """
        # 최소 데이터 확인
        if len(candles) < self.period + 1:
            logger.debug(f"RSI 전략: 데이터 부족 ({len(candles)} < {self.period + 1})")
            return None

        # RSI 계산
        rsi = calculate_rsi(candles['close'], self.period)
        current_rsi = rsi.iloc[-1]

        logger.debug(f"RSI 전략: RSI={current_rsi:.2f}, Position={self.position}")

        # 포지션 없을 때 - 매수 신호 확인
        if self.is_flat():
            if current_rsi < self.oversold:
                logger.info(f"RSI 매수 신호: RSI={current_rsi:.2f} < {self.oversold} (과매도)")
                self.set_position('long')
                return 'buy'

        # 롱 포지션 있을 때 - 매도 신호 확인
        elif self.is_long():
            if current_rsi > self.overbought:
                logger.info(f"RSI 매도 신호: RSI={current_rsi:.2f} > {self.overbought} (과매수)")
                self.set_position(None)
                return 'sell'

        return None

    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            'strategy': 'RSI',
            'period': self.period,
            'oversold': self.oversold,
            'overbought': self.overbought,
            'position': self.position
        }


if __name__ == "__main__":
    """
    RSI_Strategy 테스트 코드
    """
    import numpy as np

    print("=== RSI_Strategy 테스트 ===\n")

    # 테스트 데이터 생성 (과매수/과매도 구간 포함)
    dates = pd.date_range('2024-01-01', periods=50, freq='1D')

    # 가격 시뮬레이션
    # 1. 상승 → 과매수
    # 2. 하락 → 과매도
    # 3. 다시 상승
    prices = []
    base = 100

    # 상승 구간 (15일)
    for i in range(15):
        base += np.random.uniform(1, 3)
        prices.append(base)

    # 하락 구간 (15일)
    for i in range(15):
        base -= np.random.uniform(1, 3)
        prices.append(base)

    # 다시 상승 (20일)
    for i in range(20):
        base += np.random.uniform(0.5, 2)
        prices.append(base)

    candles = pd.DataFrame({
        'open': prices,
        'high': [p + np.random.uniform(0, 2) for p in prices],
        'low': [p - np.random.uniform(0, 2) for p in prices],
        'close': prices,
        'volume': [1000 + np.random.uniform(-200, 200) for _ in prices]
    }, index=dates)

    # RSI 전략 초기화
    print("1. RSI_Strategy 초기화")
    strategy = RSI_Strategy(period=14, oversold=30, overbought=70)
    print(f"   전략: {strategy.name}")
    print(f"   파라미터: {strategy.get_parameters()}\n")

    # 백테스팅 시뮬레이션
    print("2. 매매 신호 생성")
    print(f"   {'날짜':<12} {'종가':>8} {'RSI':>6} {'신호':>6} {'포지션':>8}")
    print("   " + "-" * 50)

    signals = []
    for i in range(len(candles)):
        current_candles = candles.iloc[:i+1]
        signal = strategy.generate_signal(current_candles)

        # RSI 계산 (출력용)
        if len(current_candles) >= 15:
            from core.indicators import calculate_rsi
            rsi = calculate_rsi(current_candles['close'], 14)
            current_rsi = rsi.iloc[-1]
        else:
            current_rsi = 50.0

        # 신호가 있거나 처음/마지막이면 출력
        if signal or i == 0 or i == len(candles) - 1 or (i > 15 and i % 5 == 0):
            date_str = current_candles.index[-1].strftime('%Y-%m-%d')
            close = current_candles['close'].iloc[-1]
            signal_str = signal or '-'
            pos_str = strategy.position or 'None'

            print(f"   {date_str} {close:8.2f} {current_rsi:6.2f} {signal_str:>6} {pos_str:>8}")

            if signal:
                signals.append({
                    'date': date_str,
                    'price': close,
                    'rsi': current_rsi,
                    'signal': signal
                })

    # 매매 통계
    print(f"\n3. 매매 통계")
    print(f"   총 신호: {len(signals)}개")

    buy_signals = [s for s in signals if s['signal'] == 'buy']
    sell_signals = [s for s in signals if s['signal'] == 'sell']

    print(f"   매수: {len(buy_signals)}회")
    for s in buy_signals:
        print(f"      {s['date']}: {s['price']:.2f}원 (RSI={s['rsi']:.2f})")

    print(f"   매도: {len(sell_signals)}회")
    for s in sell_signals:
        print(f"      {s['date']}: {s['price']:.2f}원 (RSI={s['rsi']:.2f})")

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
