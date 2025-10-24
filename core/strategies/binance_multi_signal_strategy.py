"""
Binance-Style Multi-Signal Strategy
바이낸스 스타일 멀티 시그널 전략

매수 조건:
1. RSI < 40 (급락 반전)
2. 볼린저 하단 근접 (기회형)
3. Stoch 확인 (선택적)

참고: 바이낸스 롱 포지션 = 현물 매수
"""

import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime
from core.strategies.base import BaseStrategy
from core.indicators import (
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_stochastic
)


class BinanceMultiSignalStrategy(BaseStrategy):
    """
    바이낸스 스타일 멀티 시그널 전략

    여러 기술적 지표를 조합하여 매수 신호 생성
    """

    def __init__(
        self,
        symbol: str = "KRW-BTC",
        # RSI 설정
        rsi_period: int = 14,
        rsi_oversold: float = 40.0,  # RSI < 40 매수
        # 볼린저 밴드 설정
        bb_period: int = 20,
        bb_std: float = 2.0,
        bb_proximity_pct: float = 1.0,  # 하단에서 1% 이내
        # Stochastic 설정
        stoch_k_period: int = 14,
        stoch_d_period: int = 3,
        stoch_overbought: float = 80.0,  # K > 80은 과매수
        # 신호 조합 방식
        require_all_signals: bool = False  # False = OR 조건, True = AND 조건
    ):
        super().__init__(name="BinanceMultiSignal")
        self.symbol = symbol

        # RSI 파라미터
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold

        # 볼린저 밴드 파라미터
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.bb_proximity_pct = bb_proximity_pct

        # Stochastic 파라미터
        self.stoch_k_period = stoch_k_period
        self.stoch_d_period = stoch_d_period
        self.stoch_overbought = stoch_overbought

        # 신호 조합
        self.require_all_signals = require_all_signals

    def generate_signal(
        self, 
        candles: pd.DataFrame,
        current_time: Optional[datetime] = None
    ) -> Optional[str]:
        """
        매수/매도 신호 생성

        Args:
            candles: OHLCV 데이터
            current_time: 현재 시간 (DCA 엔진 호환용, 미사용)

        Returns:
            'buy', 'sell', None
        """
        if len(candles) < max(self.rsi_period, self.bb_period, self.stoch_k_period) + 10:
            return None

        # 지표 계산
        rsi = calculate_rsi(candles['close'], period=self.rsi_period)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            candles['close'], period=self.bb_period, std_dev=self.bb_std
        )
        stoch_k, stoch_d = calculate_stochastic(
            candles['high'],
            candles['low'],
            candles['close'],
            k_period=self.stoch_k_period,
            d_period=self.stoch_d_period
        )

        # 현재 값
        current_price = candles['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_stoch_k = stoch_k.iloc[-1]

        # 신호 체크
        signals = []

        # 1. RSI 급락 반전 신호
        rsi_signal = current_rsi < self.rsi_oversold
        signals.append(rsi_signal)

        # 2. 볼린저 하단 근접 신호
        distance_from_lower = ((current_price - current_bb_lower) / current_bb_lower) * 100
        bb_signal = distance_from_lower <= self.bb_proximity_pct
        signals.append(bb_signal)

        # 3. Stoch 과매수 체크 (부정적 요소)
        stoch_warning = current_stoch_k > self.stoch_overbought

        # 매수 신호 판단
        if self.require_all_signals:
            # AND 조건: 모든 신호 필요
            buy_signal = all(signals) and not stoch_warning
        else:
            # OR 조건: 하나 이상 신호
            buy_signal = any(signals) and not stoch_warning

        if buy_signal:
            return 'buy'

        # 매도는 DCA 익절/손절로 처리
        return None

    def get_signal_details(self, candles: pd.DataFrame) -> dict:
        """
        현재 신호 상태 상세 정보

        Returns:
            dict: 각 지표별 상태
        """
        if len(candles) < max(self.rsi_period, self.bb_period, self.stoch_k_period) + 10:
            return {}

        # 지표 계산
        rsi = calculate_rsi(candles['close'], period=self.rsi_period)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            candles['close'], period=self.bb_period, std_dev=self.bb_std
        )
        stoch_k, stoch_d = calculate_stochastic(
            candles['high'],
            candles['low'],
            candles['close'],
            k_period=self.stoch_k_period,
            d_period=self.stoch_d_period
        )

        # 현재 값
        current_price = candles['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_stoch_k = stoch_k.iloc[-1]

        distance_from_lower = ((current_price - current_bb_lower) / current_bb_lower) * 100

        return {
            'rsi': current_rsi,
            'rsi_oversold': current_rsi < self.rsi_oversold,
            'bb_lower': current_bb_lower,
            'distance_from_bb_lower': distance_from_lower,
            'bb_proximity': distance_from_lower <= self.bb_proximity_pct,
            'stoch_k': current_stoch_k,
            'stoch_warning': current_stoch_k > self.stoch_overbought,
            'price': current_price
        }

    def get_parameters(self) -> dict:
        """
        전략 파라미터 반환

        Returns:
            dict: 전략 파라미터
        """
        return {
            'strategy': 'BinanceMultiSignal',
            'symbol': self.symbol,
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'bb_proximity_pct': self.bb_proximity_pct,
            'stoch_k_period': self.stoch_k_period,
            'stoch_d_period': self.stoch_d_period,
            'stoch_overbought': self.stoch_overbought,
            'require_all_signals': self.require_all_signals
        }
