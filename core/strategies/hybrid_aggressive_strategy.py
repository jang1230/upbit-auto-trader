"""
Hybrid Aggressive Strategy
하이브리드 공격적 전략

더 많은 매수 기회 포착
- BB 하단 1.5% 이내 OR (RSI < 35 AND Stochastic < 60)
- 여러 루트로 매수 신호 생성
- 거래 기회 많음, 적극적 진입
"""

from typing import Optional
from datetime import datetime
import pandas as pd

from core.strategies.base import BaseStrategy
from core.indicators import calculate_rsi, calculate_bollinger_bands, calculate_stochastic


class HybridAggressiveStrategy(BaseStrategy):
    """
    하이브리드 공격적 전략
    
    매수 조건:
    - BB 하단 1.5% 이내 (Binance보다 완화)
    - OR (RSI < 35 AND Stochastic K < 60) (강한 과매도)
    
    특징:
    - 공격적: OR 조건으로 많은 기회 포착
    - 거래 기회 많음
    - 변동성 활용
    """
    
    def __init__(
        self,
        symbol: str,
        bb_period: int = 20,
        bb_std: float = 2.0,
        bb_proximity_pct: float = 1.5,
        rsi_period: int = 14,
        rsi_threshold: float = 35.0,
        stoch_k_period: int = 14,
        stoch_d_period: int = 3,
        stoch_threshold: float = 60.0
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
        
        # 루트 1: BB 하단 근접 (1.5% 이내)
        distance_from_lower = ((current_price - current_bb_lower) / current_bb_lower) * 100
        route_bb = distance_from_lower <= self.bb_proximity_pct
        
        # 루트 2: 강한 과매도 (RSI < 35 AND Stoch < 60)
        route_oversold = (current_rsi < self.rsi_threshold) and (current_stoch_k < self.stoch_threshold)
        
        # 매수 신호: 루트 1 OR 루트 2
        if route_bb or route_oversold:
            return 'buy'
        
        return None
    
    def get_strategy_name(self) -> str:
        return "Hybrid Aggressive"
    
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
