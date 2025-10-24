"""
Hybrid Smart Strategy
하이브리드 스마트 전략

Proximity BB의 최고 장점 + Binance의 과매수 필터
- BB 하단 2% 이내 (Proximity BB 강점)
- AND Stochastic < 80 (과매수 회피)
- AND 1시간 시간 필터 (중복 매수 방지)
- 최적화된 조합
"""

from typing import Optional
from datetime import datetime, timedelta
import pandas as pd

from core.strategies.base import BaseStrategy
from core.indicators import calculate_bollinger_bands, calculate_stochastic


class HybridSmartStrategy(BaseStrategy):
    """
    하이브리드 스마트 전략
    
    매수 조건:
    - BB 하단에서 2% 이내 (Proximity BB)
    - AND Stochastic K < 80 (과매수 회피)
    - AND 마지막 거래로부터 1시간 경과 (시간 필터)
    
    특징:
    - 스마트: Proximity BB의 강점 유지하면서 과매수 회피
    - 시간 필터로 중복 매수 방지
    - 최적화된 조합
    """
    
    def __init__(
        self,
        symbol: str,
        bb_period: int = 20,
        bb_std: float = 2.0,
        bb_proximity_pct: float = 2.0,
        stoch_k_period: int = 14,
        stoch_d_period: int = 3,
        stoch_threshold: float = 80.0,
        time_filter_minutes: int = 60
    ):
        """
        초기화
        
        Args:
            symbol: 거래 심볼
            bb_period: 볼린저 밴드 기간 (기본 20)
            bb_std: 볼린저 밴드 표준편차 (기본 2.0)
            bb_proximity_pct: BB 하단 근접 비율 (기본 2%)
            stoch_k_period: Stochastic K 기간 (기본 14)
            stoch_d_period: Stochastic D 기간 (기본 3)
            stoch_threshold: Stochastic 임계값 (기본 80)
            time_filter_minutes: 시간 필터 (분, 기본 60분)
        """
        super().__init__(symbol)
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.bb_proximity_pct = bb_proximity_pct
        self.stoch_k_period = stoch_k_period
        self.stoch_d_period = stoch_d_period
        self.stoch_threshold = stoch_threshold
        self.time_filter_minutes = time_filter_minutes
        self.last_buy_time = None
    
    def generate_signal(
        self,
        candles: pd.DataFrame,
        current_time: Optional[datetime] = None
    ) -> Optional[str]:
        """
        매수/매도 신호 생성
        
        Args:
            candles: OHLCV 데이터
            current_time: 현재 시간 (시간 필터용)
        
        Returns:
            'buy', 'sell', None
        """
        min_length = max(self.bb_period, self.stoch_k_period) + 10
        if len(candles) < min_length:
            return None
        
        # 지표 계산
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            candles['close'], period=self.bb_period, std_dev=self.bb_std
        )
        stoch_k, stoch_d = calculate_stochastic(
            candles['high'], candles['low'], candles['close'],
            k_period=self.stoch_k_period, d_period=self.stoch_d_period
        )
        
        # 현재 값
        current_price = candles['close'].iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_stoch_k = stoch_k.iloc[-1]
        
        # 조건 1: BB 하단 근접 (Proximity BB)
        distance_from_lower = ((current_price - current_bb_lower) / current_bb_lower) * 100
        bb_condition = distance_from_lower <= self.bb_proximity_pct
        
        # 조건 2: Stochastic 과매수 아님 (Binance)
        stoch_condition = current_stoch_k < self.stoch_threshold
        
        # 조건 3: 시간 필터 (Proximity BB)
        time_condition = True
        if current_time and self.last_buy_time:
            time_diff = current_time - self.last_buy_time
            time_condition = time_diff >= timedelta(minutes=self.time_filter_minutes)
        
        # 매수 신호: 세 조건 모두 충족
        if bb_condition and stoch_condition and time_condition:
            if current_time:
                self.last_buy_time = current_time
            return 'buy'
        
        return None
    
    def get_strategy_name(self) -> str:
        return "Hybrid Smart"
    
    def get_parameters(self) -> dict:
        return {
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'bb_proximity_pct': self.bb_proximity_pct,
            'stoch_k_period': self.stoch_k_period,
            'stoch_d_period': self.stoch_d_period,
            'stoch_threshold': self.stoch_threshold,
            'time_filter_minutes': self.time_filter_minutes
        }
