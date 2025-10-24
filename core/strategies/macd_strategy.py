"""
MACD 전략 모듈
MACD (Moving Average Convergence Divergence) Strategy

MACD 크로스오버를 이용한 추세 추종 매매 전략입니다.

전략 로직:
- 골든 크로스 (MACD > Signal): 매수
- 데드 크로스 (MACD < Signal): 매도

특징:
- 추세 추종 전략으로 추세장에서 효과적
- 크로스오버 감지로 진입/청산 시점 포착
- 횡보장에서는 잦은 매매로 손실 가능

사용법:
    from core.strategies.macd_strategy import MACD_Strategy

    strategy = MACD_Strategy(fast_period=12, slow_period=26, signal_period=9)
    signal = strategy.generate_signal(candles)
"""

import pandas as pd
from typing import Optional, Dict, Any
import logging

from core.strategies.base import BaseStrategy
from core.indicators import calculate_macd

logger = logging.getLogger(__name__)


class MACD_Strategy(BaseStrategy):
    """
    MACD 크로스오버 전략

    MACD Line과 Signal Line의 크로스오버를 이용한 추세 추종 전략입니다.

    Parameters:
        - fast_period: 빠른 EMA 기간 (기본 12)
        - slow_period: 느린 EMA 기간 (기본 26)
        - signal_period: Signal Line 기간 (기본 9)

    매매 로직:
        1. 골든 크로스 (MACD가 Signal을 상향 돌파):
           - 포지션 없으면 매수
        2. 데드 크로스 (MACD가 Signal을 하향 돌파):
           - 롱 포지션 있으면 매도
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        """
        Args:
            fast_period: 빠른 EMA 기간
            slow_period: 느린 EMA 기간
            signal_period: Signal Line 기간
        """
        # 파라미터 검증
        if fast_period >= slow_period:
            raise ValueError(f"fast_period({fast_period}) must be less than slow_period({slow_period})")

        super().__init__(f"MACD Strategy ({fast_period}/{slow_period}/{signal_period})")

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

        logger.info(f"MACD 전략 초기화: {fast_period}/{slow_period}/{signal_period}")

    def generate_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """
        MACD 기반 매매 신호 생성

        Args:
            candles: 캔들 데이터 (최소 slow_period + signal_period + 2개 필요)

        Returns:
            Optional[str]: 'buy', 'sell', None
        """
        # 최소 데이터 확인 (크로스오버 감지를 위해 2개 필요)
        min_periods = self.slow_period + self.signal_period + 2
        if len(candles) < min_periods:
            logger.debug(f"MACD 전략: 데이터 부족 ({len(candles)} < {min_periods})")
            return None

        # MACD 계산
        macd_line, signal_line, histogram = calculate_macd(
            candles['close'],
            self.fast_period,
            self.slow_period,
            self.signal_period
        )

        # 최근 2개 값 (크로스오버 감지용)
        prev_macd = macd_line.iloc[-2]
        curr_macd = macd_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]
        curr_signal = signal_line.iloc[-1]

        logger.debug(f"MACD 전략: MACD={curr_macd:.4f}, Signal={curr_signal:.4f}, Position={self.position}")

        # 골든 크로스 (MACD가 Signal을 상향 돌파)
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            if self.is_flat():
                logger.info(f"MACD 골든 크로스: MACD={curr_macd:.4f} > Signal={curr_signal:.4f}")
                self.set_position('long')
                return 'buy'

        # 데드 크로스 (MACD가 Signal을 하향 돌파)
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            if self.is_long():
                logger.info(f"MACD 데드 크로스: MACD={curr_macd:.4f} < Signal={curr_signal:.4f}")
                self.set_position(None)
                return 'sell'

        return None

    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            'strategy': 'MACD',
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'signal_period': self.signal_period,
            'position': self.position
        }


if __name__ == "__main__":
    """
    MACD_Strategy 테스트 코드
    """
    import numpy as np

    print("=== MACD_Strategy 테스트 ===\n")

    # 테스트 데이터 생성 (추세 변화 포함)
    dates = pd.date_range('2024-01-01', periods=80, freq='1D')

    # 가격 시뮬레이션
    # 1. 하락 추세
    # 2. 상승 추세로 전환
    # 3. 다시 하락 추세로 전환
    prices = []
    base = 100

    # 하락 추세 (20일)
    for i in range(20):
        base -= np.random.uniform(0.5, 1.5)
        prices.append(max(base, 70))

    # 상승 추세 (30일)
    for i in range(30):
        base += np.random.uniform(0.5, 2.0)
        prices.append(base)

    # 다시 하락 (30일)
    for i in range(30):
        base -= np.random.uniform(0.3, 1.2)
        prices.append(max(base, 70))

    candles = pd.DataFrame({
        'open': prices,
        'high': [p + np.random.uniform(0, 1) for p in prices],
        'low': [p - np.random.uniform(0, 1) for p in prices],
        'close': prices,
        'volume': [1000 + np.random.uniform(-100, 100) for _ in prices]
    }, index=dates)

    # MACD 전략 초기화
    print("1. MACD_Strategy 초기화")
    strategy = MACD_Strategy(fast_period=12, slow_period=26, signal_period=9)
    print(f"   전략: {strategy.name}")
    print(f"   파라미터: {strategy.get_parameters()}\n")

    # 백테스팅 시뮬레이션
    print("2. 매매 신호 생성")
    print(f"   {'날짜':<12} {'종가':>8} {'MACD':>8} {'Signal':>8} {'신호':>6} {'포지션':>8}")
    print("   " + "-" * 65)

    signals = []
    for i in range(len(candles)):
        current_candles = candles.iloc[:i+1]
        signal = strategy.generate_signal(current_candles)

        # MACD 계산 (출력용)
        if len(current_candles) >= 35:
            from core.indicators import calculate_macd
            macd, sig, hist = calculate_macd(current_candles['close'], 12, 26, 9)
            current_macd = macd.iloc[-1]
            current_sig = sig.iloc[-1]
        else:
            current_macd = 0.0
            current_sig = 0.0

        # 신호가 있거나 중요 시점이면 출력
        if signal or i == 0 or i == len(candles) - 1 or (i > 35 and i % 10 == 0):
            date_str = current_candles.index[-1].strftime('%Y-%m-%d')
            close = current_candles['close'].iloc[-1]
            signal_str = signal or '-'
            pos_str = strategy.position or 'None'

            print(f"   {date_str} {close:8.2f} {current_macd:8.4f} {current_sig:8.4f} {signal_str:>6} {pos_str:>8}")

            if signal:
                signals.append({
                    'date': date_str,
                    'price': close,
                    'macd': current_macd,
                    'signal_val': current_sig,
                    'signal': signal
                })

    # 매매 통계
    print(f"\n3. 매매 통계")
    print(f"   총 신호: {len(signals)}개")

    buy_signals = [s for s in signals if s['signal'] == 'buy']
    sell_signals = [s for s in signals if s['signal'] == 'sell']

    print(f"   매수: {len(buy_signals)}회")
    for s in buy_signals:
        print(f"      {s['date']}: {s['price']:.2f}원 (MACD={s['macd']:.4f}, Signal={s['signal_val']:.4f})")

    print(f"   매도: {len(sell_signals)}회")
    for s in sell_signals:
        print(f"      {s['date']}: {s['price']:.2f}원 (MACD={s['macd']:.4f}, Signal={s['signal_val']:.4f})")

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
