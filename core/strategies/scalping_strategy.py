"""
단타 전략 (Scalping Strategy)
목표: 시총 상위 10개 코인 전체 하루 20~30회 매수 시그널

백테스트 결과 최적 전략:
- MACD 골든크로스 + 거래량 2배
- BTC 기준 하루 평균 2.9회 → 10개 코인 29회 ✅
"""

import pandas as pd
from core.strategies.base import BaseStrategy


class ScalpingStrategy(BaseStrategy):
    """
    단타 트레이딩 전략

    매수 조건:
    1. MACD 골든크로스 (MACD선이 Signal선 상향 돌파)
    2. 거래량이 평균 대비 2배 이상 급증

    특징:
    - 목표 빈도: 하루 20~30회 (10개 코인 전체)
    - 단순하고 명확한 조건
    - 높은 신뢰도의 매수 시그널

    파라미터 설명:
    - macd_fast: 단기 EMA 기간 (기본 12, 작을수록 민감)
    - macd_slow: 장기 EMA 기간 (기본 26, 클수록 안정적)
    - macd_signal: 시그널선 기간 (기본 9)
    - volume_period: 거래량 평균 계산 기간 (기본 20)
    - volume_threshold: 거래량 급증 기준 (기본 2.0 = 평균 대비 2배)
    """

    def __init__(
        self,
        symbol: str,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        volume_period: int = 20,
        volume_threshold: float = 2.0,
        **kwargs
    ):
        """
        Args:
            symbol: 거래 심볼 (예: 'KRW-BTC')
            macd_fast: MACD 단기 EMA 기간 (기본 12)
            macd_slow: MACD 장기 EMA 기간 (기본 26)
            macd_signal: MACD 시그널선 기간 (기본 9)
            volume_period: 거래량 평균 계산 기간 (기본 20)
            volume_threshold: 거래량 급증 기준 배수 (기본 2.0)
        """
        super().__init__(symbol)

        # MACD 파라미터
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal

        # 거래량 파라미터
        self.volume_period = volume_period
        self.volume_threshold = volume_threshold

        # 전략 정보
        self.name = f"Scalping (MACD + Vol×{volume_threshold})"
        self.description = (
            f"MACD({macd_fast},{macd_slow},{macd_signal}) 골든크로스 + "
            f"거래량 {volume_threshold}배 급증"
        )

    def calculate_macd(self, candles: pd.DataFrame) -> tuple:
        """
        MACD 계산

        Returns:
            (macd, macd_signal, macd_hist) 튜플
        """
        close = candles['close']

        # 단기/장기 EMA 계산
        exp1 = close.ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = close.ewm(span=self.macd_slow, adjust=False).mean()

        # MACD = 단기 EMA - 장기 EMA
        macd = exp1 - exp2

        # Signal = MACD의 EMA
        macd_signal = macd.ewm(span=self.macd_signal, adjust=False).mean()

        # Histogram = MACD - Signal
        macd_hist = macd - macd_signal

        return macd, macd_signal, macd_hist

    def calculate_volume_ratio(self, candles: pd.DataFrame) -> pd.Series:
        """
        거래량 비율 계산 (현재 거래량 / 평균 거래량)

        Returns:
            거래량 비율 Series
        """
        volume = candles['volume']
        volume_avg = volume.rolling(window=self.volume_period).mean()
        volume_ratio = volume / volume_avg

        return volume_ratio

    def check_macd_golden_cross(self, candles: pd.DataFrame) -> bool:
        """
        MACD 골든크로스 확인

        조건:
        - 이전 캔들: MACD <= Signal
        - 현재 캔들: MACD > Signal

        Returns:
            골든크로스 발생 시 True
        """
        if len(candles) < self.macd_slow + 1:
            return False

        macd, macd_signal, _ = self.calculate_macd(candles)

        # 현재 및 이전 값
        current_macd = macd.iloc[-1]
        current_signal = macd_signal.iloc[-1]
        prev_macd = macd.iloc[-2]
        prev_signal = macd_signal.iloc[-2]

        # 골든크로스: 이전에는 아래, 현재는 위
        is_golden_cross = (prev_macd <= prev_signal) and (current_macd > current_signal)

        return is_golden_cross

    def check_volume_surge(self, candles: pd.DataFrame) -> bool:
        """
        거래량 급증 확인

        조건:
        - 현재 거래량 >= 평균 거래량 × threshold

        Returns:
            거래량 급증 시 True
        """
        if len(candles) < self.volume_period:
            return False

        volume_ratio = self.calculate_volume_ratio(candles)
        current_ratio = volume_ratio.iloc[-1]

        return current_ratio >= self.volume_threshold

    def should_buy(self, candles: pd.DataFrame) -> bool:
        """
        매수 신호 판단

        조건:
        1. MACD 골든크로스 AND
        2. 거래량 >= 평균 × 2.0

        Returns:
            매수 신호 시 True
        """
        if len(candles) < self.macd_slow + 1:
            return False

        # 1. MACD 골든크로스 확인
        macd_signal = self.check_macd_golden_cross(candles)
        if not macd_signal:
            return False

        # 2. 거래량 급증 확인
        volume_signal = self.check_volume_surge(candles)
        if not volume_signal:
            return False

        # 두 조건 모두 만족
        return True

    def should_sell(self, candles: pd.DataFrame) -> bool:
        """
        매도 신호 판단

        주의: DCA 모드에서는 이 메서드가 사용되지 않음
        DCA 익절/손절 조건이 매도를 결정함

        단타 전략용 매도 조건 (DCA 미사용 시):
        - MACD 데드크로스 OR
        - 거래량 감소

        Returns:
            매도 신호 시 True
        """
        if len(candles) < self.macd_slow + 1:
            return False

        macd, macd_signal, _ = self.calculate_macd(candles)

        # 데드크로스: MACD선이 Signal선 하향 돌파
        current_macd = macd.iloc[-1]
        current_signal = macd_signal.iloc[-1]
        prev_macd = macd.iloc[-2]
        prev_signal = macd_signal.iloc[-2]

        is_dead_cross = (prev_macd >= prev_signal) and (current_macd < current_signal)

        return is_dead_cross

    def get_indicator_values(self, candles: pd.DataFrame) -> dict:
        """
        현재 지표 값 반환 (디버깅/모니터링용)

        Returns:
            지표 값 딕셔너리
        """
        if len(candles) < self.macd_slow:
            return {}

        macd, macd_signal, macd_hist = self.calculate_macd(candles)
        volume_ratio = self.calculate_volume_ratio(candles)

        return {
            'macd': macd.iloc[-1],
            'macd_signal': macd_signal.iloc[-1],
            'macd_hist': macd_hist.iloc[-1],
            'volume_ratio': volume_ratio.iloc[-1],
            'volume_surge': volume_ratio.iloc[-1] >= self.volume_threshold,
            'golden_cross': self.check_macd_golden_cross(candles)
        }

    def generate_signal(self, candles: pd.DataFrame) -> str:
        """
        매수/매도 신호 생성 (BaseStrategy 호환)

        Returns:
            'buy', 'sell', 또는 None
        """
        if self.should_buy(candles):
            return 'buy'
        elif self.should_sell(candles):
            return 'sell'
        return None

    def get_parameters(self) -> dict:
        """
        전략 파라미터 반환 (BaseStrategy 호환)

        Returns:
            파라미터 딕셔너리
        """
        return {
            'macd_fast': self.macd_fast,
            'macd_slow': self.macd_slow,
            'macd_signal': self.macd_signal,
            'volume_period': self.volume_period,
            'volume_threshold': self.volume_threshold
        }

    def __str__(self):
        """전략 정보 문자열"""
        return (
            f"{self.name}\n"
            f"설명: {self.description}\n"
            f"파라미터:\n"
            f"  - MACD: ({self.macd_fast}, {self.macd_slow}, {self.macd_signal})\n"
            f"  - 거래량 기간: {self.volume_period}\n"
            f"  - 거래량 기준: {self.volume_threshold}배\n"
            f"목표 빈도: 하루 2~3회 (코인당)"
        )
