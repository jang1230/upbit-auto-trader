"""
기술적 지표 라이브러리
Technical Indicators Module

주요 지표:
- RSI (Relative Strength Index): 과매수/과매도 판단
- MACD (Moving Average Convergence Divergence): 추세 전환 감지
- Bollinger Bands: 변동성 기반 매매 신호
- Moving Averages (SMA, EMA): 추세 파악

사용법:
    from core.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands

    # RSI 계산
    rsi = calculate_rsi(prices, period=14)

    # MACD 계산
    macd_line, signal_line, histogram = calculate_macd(prices)

    # 볼린저 밴드 계산
    upper, middle, lower = calculate_bollinger_bands(prices, period=20, std_dev=2.0)
"""

import pandas as pd
import numpy as np
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """
    단순 이동평균 (Simple Moving Average) 계산

    Args:
        prices: 가격 시계열 (일반적으로 종가)
        period: 이동평균 기간

    Returns:
        pd.Series: SMA 값

    Example:
        >>> sma_20 = calculate_sma(df['close'], period=20)
    """
    if len(prices) < period:
        logger.warning(f"SMA 계산: 데이터 길이({len(prices)})가 기간({period})보다 짧습니다")

    return prices.rolling(window=period, min_periods=1).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    지수 이동평균 (Exponential Moving Average) 계산

    EMA는 최근 데이터에 더 큰 가중치를 부여합니다.

    Args:
        prices: 가격 시계열
        period: 이동평균 기간

    Returns:
        pd.Series: EMA 값

    Example:
        >>> ema_12 = calculate_ema(df['close'], period=12)
    """
    if len(prices) < period:
        logger.warning(f"EMA 계산: 데이터 길이({len(prices)})가 기간({period})보다 짧습니다")

    return prices.ewm(span=period, adjust=False, min_periods=1).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI (Relative Strength Index) 계산

    RSI는 가격의 상승압력과 하락압력의 상대적 강도를 나타내는 모멘텀 지표입니다.

    Args:
        prices: 종가 시계열
        period: RSI 계산 기간 (기본값: 14)

    Returns:
        pd.Series: RSI 값 (0-100 범위)

    해석:
        - RSI > 70: 과매수 구간 (매도 고려)
        - RSI < 30: 과매도 구간 (매수 고려)
        - RSI = 50: 중립

    공식:
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss

    Example:
        >>> rsi = calculate_rsi(df['close'], period=14)
        >>> buy_signal = rsi < 30  # 과매도
        >>> sell_signal = rsi > 70  # 과매수
    """
    if len(prices) < period:
        logger.warning(f"RSI 계산: 데이터 길이({len(prices)})가 기간({period})보다 짧습니다")

    # 가격 변화량 계산
    delta = prices.diff()

    # 상승분과 하락분 분리
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # 평균 상승/하락 계산 (Wilder's smoothing method)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    # RS (Relative Strength) 계산
    rs = avg_gain / avg_loss

    # RSI 계산
    rsi = 100 - (100 / (1 + rs))

    # NaN 처리 (loss가 0일 때)
    rsi = rsi.fillna(100)

    return rsi


def calculate_macd(
    prices: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence) 계산

    MACD는 두 개의 이동평균선 간의 관계를 이용하여 추세 전환을 감지하는 지표입니다.

    Args:
        prices: 종가 시계열
        fast_period: 빠른 EMA 기간 (기본값: 12)
        slow_period: 느린 EMA 기간 (기본값: 26)
        signal_period: 시그널선(MACD의 EMA) 기간 (기본값: 9)

    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (macd_line, signal_line, histogram)

    해석:
        - MACD Line > Signal Line: 상승 추세 (매수 신호)
        - MACD Line < Signal Line: 하락 추세 (매도 신호)
        - Histogram > 0: 강세 (상승 모멘텀)
        - Histogram < 0: 약세 (하락 모멘텀)
        - 골든 크로스: MACD가 Signal을 상향 돌파
        - 데드 크로스: MACD가 Signal을 하향 돌파

    공식:
        MACD Line = EMA(fast) - EMA(slow)
        Signal Line = EMA(MACD Line, signal_period)
        Histogram = MACD Line - Signal Line

    Example:
        >>> macd, signal, hist = calculate_macd(df['close'])
        >>> # 골든 크로스 감지
        >>> golden_cross = (macd > signal) & (macd.shift(1) <= signal.shift(1))
        >>> # 데드 크로스 감지
        >>> death_cross = (macd < signal) & (macd.shift(1) >= signal.shift(1))
    """
    min_periods = max(fast_period, slow_period)
    if len(prices) < min_periods:
        logger.warning(f"MACD 계산: 데이터 길이({len(prices)})가 최소 기간({min_periods})보다 짧습니다")

    # 빠른 EMA와 느린 EMA 계산
    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)

    # MACD Line 계산
    macd_line = ema_fast - ema_slow

    # Signal Line 계산 (MACD Line의 EMA)
    signal_line = calculate_ema(macd_line, signal_period)

    # Histogram 계산 (MACD - Signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    볼린저 밴드 (Bollinger Bands) 계산

    볼린저 밴드는 가격의 변동성을 기반으로 상단/하단 밴드를 설정하는 지표입니다.

    Args:
        prices: 종가 시계열
        period: 이동평균 기간 (기본값: 20)
        std_dev: 표준편차 배수 (기본값: 2.0)

    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (upper_band, middle_band, lower_band)

    해석:
        - 가격 > Upper Band: 과매수 (매도 고려)
        - 가격 < Lower Band: 과매도 (매수 고려)
        - Band Width 좁아짐: 변동성 감소 → 큰 움직임 예상
        - Band Width 넓어짐: 변동성 증가 → 추세 진행 중

    전략:
        - 밴드 돌파 전략: 상단 돌파 시 매수, 하단 돌파 시 매도
        - 회귀 전략: 상단 터치 시 매도, 하단 터치 시 매수 (중간선 회귀 기대)

    공식:
        Middle Band = SMA(prices, period)
        Upper Band = Middle Band + (std_dev * σ)
        Lower Band = Middle Band - (std_dev * σ)
        σ = Standard Deviation(prices, period)

    Example:
        >>> upper, middle, lower = calculate_bollinger_bands(df['close'], period=20, std_dev=2.0)
        >>> # 하단 밴드 돌파 (매수 신호)
        >>> buy_signal = df['close'] < lower
        >>> # 상단 밴드 돌파 (매도 신호)
        >>> sell_signal = df['close'] > upper
    """
    if len(prices) < period:
        logger.warning(f"볼린저 밴드 계산: 데이터 길이({len(prices)})가 기간({period})보다 짧습니다")

    # 중간선 (SMA)
    middle_band = calculate_sma(prices, period)

    # 표준편차 계산
    std = prices.rolling(window=period, min_periods=1).std()

    # 상단 밴드 = 중간선 + (표준편차 * std_dev)
    upper_band = middle_band + (std_dev * std)

    # 하단 밴드 = 중간선 - (표준편차 * std_dev)
    lower_band = middle_band - (std_dev * std)

    return upper_band, middle_band, lower_band


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    스토캐스틱 (Stochastic Oscillator) 계산

    현재 가격이 일정 기간 동안의 가격 범위에서 어디에 위치하는지를 나타내는 모멘텀 지표입니다.

    Args:
        high: 고가 시계열
        low: 저가 시계열
        close: 종가 시계열
        k_period: %K 계산 기간 (기본값: 14)
        d_period: %D 계산 기간 (%K의 이동평균, 기본값: 3)

    Returns:
        Tuple[pd.Series, pd.Series]: (%K, %D)

    해석:
        - %K, %D > 80: 과매수 (매도 고려)
        - %K, %D < 20: 과매도 (매수 고려)
        - %K가 %D를 상향 돌파: 매수 신호
        - %K가 %D를 하향 돌파: 매도 신호

    공식:
        %K = [(Close - Low(n)) / (High(n) - Low(n))] * 100
        %D = SMA(%K, d_period)
        n = k_period

    Example:
        >>> k, d = calculate_stochastic(df['high'], df['low'], df['close'])
        >>> buy_signal = (k < 20) & (d < 20)  # 과매도
        >>> sell_signal = (k > 80) & (d > 80)  # 과매수
    """
    min_periods = k_period
    if len(close) < min_periods:
        logger.warning(f"스토캐스틱 계산: 데이터 길이({len(close)})가 기간({min_periods})보다 짧습니다")

    # 최고가와 최저가 (k_period 동안)
    highest_high = high.rolling(window=k_period, min_periods=1).max()
    lowest_low = low.rolling(window=k_period, min_periods=1).min()

    # %K 계산
    k = ((close - lowest_low) / (highest_high - lowest_low)) * 100

    # NaN 처리 (분모가 0일 때)
    k = k.fillna(50)

    # %D 계산 (%K의 이동평균)
    d = calculate_sma(k, d_period)

    return k, d


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    ATR (Average True Range) 계산

    ATR은 가격의 변동성을 측정하는 지표로, 스톱로스 설정에 유용합니다.

    Args:
        high: 고가 시계열
        low: 저가 시계열
        close: 종가 시계열
        period: ATR 계산 기간 (기본값: 14)

    Returns:
        pd.Series: ATR 값

    용도:
        - 변동성 측정
        - 스톱로스 레벨 설정: close ± (ATR * multiplier)
        - 포지션 크기 조절: 변동성이 클수록 포지션 축소

    공식:
        True Range = max(H - L, |H - Cp|, |L - Cp|)
        ATR = EMA(True Range, period)
        H = High, L = Low, Cp = Previous Close

    Example:
        >>> atr = calculate_atr(df['high'], df['low'], df['close'], period=14)
        >>> stop_loss = df['close'] - (2 * atr)  # 2 ATR 아래에 스톱로스
    """
    if len(close) < period:
        logger.warning(f"ATR 계산: 데이터 길이({len(close)})가 기간({period})보다 짧습니다")

    # True Range 계산
    tr1 = high - low  # 당일 고가 - 저가
    tr2 = (high - close.shift(1)).abs()  # 당일 고가 - 전일 종가
    tr3 = (low - close.shift(1)).abs()  # 당일 저가 - 전일 종가

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATR = True Range의 EMA
    atr = calculate_ema(true_range, period)

    return atr


# ============================================================================
# 지표 유틸리티 함수
# ============================================================================

def detect_crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    크로스오버 감지 (series1이 series2를 상향 돌파)

    Args:
        series1: 첫 번째 시계열 (예: MACD)
        series2: 두 번째 시계열 (예: Signal)

    Returns:
        pd.Series: 크로스오버 발생 시 True

    Example:
        >>> golden_cross = detect_crossover(macd_line, signal_line)
    """
    return (series1 > series2) & (series1.shift(1) <= series2.shift(1))


def detect_crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    크로스언더 감지 (series1이 series2를 하향 돌파)

    Args:
        series1: 첫 번째 시계열
        series2: 두 번째 시계열

    Returns:
        pd.Series: 크로스언더 발생 시 True

    Example:
        >>> death_cross = detect_crossunder(macd_line, signal_line)
    """
    return (series1 < series2) & (series1.shift(1) >= series2.shift(1))


def calculate_divergence(price: pd.Series, indicator: pd.Series, window: int = 5) -> pd.Series:
    """
    다이버전스 감지 (가격과 지표의 불일치)

    긍정적 다이버전스: 가격은 하락하지만 지표는 상승 → 매수 신호
    부정적 다이버전스: 가격은 상승하지만 지표는 하락 → 매도 신호

    Args:
        price: 가격 시계열
        indicator: 지표 시계열 (RSI, MACD 등)
        window: 비교 기간

    Returns:
        pd.Series: 다이버전스 점수 (양수: 긍정적, 음수: 부정적)

    Example:
        >>> divergence = calculate_divergence(df['close'], rsi, window=5)
        >>> bullish_div = divergence > 0.5  # 긍정적 다이버전스
    """
    # 가격과 지표의 변화율 계산
    price_change = price.pct_change(window)
    indicator_change = indicator.pct_change(window)

    # 다이버전스 = 지표 변화율 - 가격 변화율
    divergence = indicator_change - price_change

    return divergence


if __name__ == "__main__":
    """
    지표 테스트 코드
    """
    print("=== 기술적 지표 테스트 ===\n")

    # 테스트 데이터 생성
    import numpy as np

    dates = pd.date_range('2024-01-01', periods=100, freq='1D')
    np.random.seed(42)

    # 랜덤 워크 가격 데이터
    base_price = 100
    returns = np.random.randn(100) * 2
    prices = pd.Series(base_price + np.cumsum(returns), index=dates, name='close')

    # 고가/저가 생성
    highs = prices + np.random.rand(100) * 3
    lows = prices - np.random.rand(100) * 3

    print("1. RSI 테스트")
    rsi = calculate_rsi(prices, period=14)
    print(f"   최근 RSI: {rsi.iloc[-1]:.2f}")
    print(f"   과매수(>70): {(rsi > 70).sum()}개")
    print(f"   과매도(<30): {(rsi < 30).sum()}개\n")

    print("2. MACD 테스트")
    macd, signal, hist = calculate_macd(prices)
    print(f"   최근 MACD: {macd.iloc[-1]:.2f}")
    print(f"   최근 Signal: {signal.iloc[-1]:.2f}")
    print(f"   최근 Histogram: {hist.iloc[-1]:.2f}\n")

    print("3. 볼린저 밴드 테스트")
    upper, middle, lower = calculate_bollinger_bands(prices, period=20, std_dev=2.0)
    print(f"   최근 가격: {prices.iloc[-1]:.2f}")
    print(f"   상단 밴드: {upper.iloc[-1]:.2f}")
    print(f"   중간선: {middle.iloc[-1]:.2f}")
    print(f"   하단 밴드: {lower.iloc[-1]:.2f}\n")

    print("4. ATR 테스트")
    atr = calculate_atr(highs, lows, prices, period=14)
    print(f"   최근 ATR: {atr.iloc[-1]:.2f}")
    print(f"   스톱로스 레벨 (2 ATR): {prices.iloc[-1] - 2*atr.iloc[-1]:.2f}\n")

    print("=== 테스트 완료 ===")
