"""
Hybrid Balanced Strategy
하이브리드 균형 전략

Proximity BB + RSI OR Stochastic 조합
- BB 하단 2% 이내 (필수)
- AND (RSI < 40 OR Stochastic < 70) (필터)
- 중도적 접근: 확실한 바닥 + 유연한 필터
"""

from typing import Optional
from datetime import datetime
import pandas as pd

from core.strategies.base import BaseStrategy
from core.indicators import calculate_rsi, calculate_bollinger_bands, calculate_stochastic


class HybridBalancedStrategy(BaseStrategy):
    """
    하이브리드 균형 전략
    
    매수 조건:
    - BB 하단에서 2% 이내 (필수)
    - AND (RSI < 40 OR Stochastic K < 70)
    
    특징:
    - 중도적: BB는 확실하게, 필터는 유연하게
    - 적당한 거래 기회
    - 균형잡힌 승률과 거래 횟수
    """
    
    def __init__(
        self,
        symbol: str,
        bb_period: int = 20,
        bb_std: float = 2.0,
        bb_proximity_pct: float = 2.0,
        rsi_period: int = 14,
        rsi_threshold: float = 40.0,
        stoch_k_period: int = 14,
        stoch_d_period: int = 3,
        stoch_threshold: float = 70.0
    ):
        """초기화"""
        super().__init__(symbol)
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.bb_proximity_pct = bb_proximity_pct
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
        self.stoch_k_period = stoch_k_period
        self.stoch_d_period = stoch_d_period
        self.stoch_threshold = stoch_threshold
    
    def generate_signal(
        self,
        candles: pd.DataFrame,
        current_time: Optional[datetime] = None
    ) -> Optional[str]:
        """매수/매도 신호 생성"""
        min_length = max(self.bb_period, self.rsi_period, self.stoch_k_period) + 10
        if len(candles) < min_length:
            return None
        
        # 지표 계산
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            candles['close'], period=self.bb_period, std_dev=self.bb_std
        )
        rsi = calculate_rsi(candles['close'], period=self.rsi_period)
        stoch_k, stoch_d = calculate_stochastic(
            candles['high'], candles['low'], candles['close'],
            k_period=self.stoch_k_period, d_period=self.stoch_d_period
        )
        
        # 현재 값
        current_price = candles['close'].iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_stoch_k = stoch_k.iloc[-1]
        
        # 조건 1: BB 하단 근접 (필수)
        distance_from_lower = ((current_price - current_bb_lower) / current_bb_lower) * 100
        bb_condition = distance_from_lower <= self.bb_proximity_pct
        
        # 조건 2: RSI 또는 Stochastic 과매도 (유연한 필터)
        rsi_condition = current_rsi < self.rsi_threshold
        stoch_condition = current_stoch_k < self.stoch_threshold
        filter_condition = rsi_condition or stoch_condition
        
        # 매수 신호: BB 필수 + (RSI OR Stoch)
        if bb_condition and filter_condition:
            return 'buy'
        
        return None
    
    def get_strategy_name(self) -> str:
        return "Hybrid Balanced"
    
    def get_parameters(self) -> dict:
        return {
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'bb_proximity_pct': self.bb_proximity_pct,
            'rsi_period': self.rsi_period,
            'rsi_threshold': self.rsi_threshold,
            'stoch_k_period': self.stoch_k_period,
            'stoch_d_period': self.stoch_d_period,
            'stoch_threshold': self.stoch_threshold
        }
