"""
Hybrid Conservative Strategy
하이브리드 보수적 전략

Proximity BB의 장점 + Binance의 RSI 필터
- BB 하단 2% 이내 (Proximity BB의 강점)
- AND RSI < 40 (Binance의 과매도 필터)
- 가장 확실한 타이밍만 포착
- 거래 횟수 적음, 높은 승률 예상
"""

from typing import Optional
from datetime import datetime
import pandas as pd

from core.strategies.base import BaseStrategy
from core.indicators import calculate_rsi, calculate_bollinger_bands


class HybridConservativeStrategy(BaseStrategy):
    """
    하이브리드 보수적 전략
    
    매수 조건:
    - BB 하단에서 2% 이내 (Proximity BB)
    - AND RSI < 40 (Binance 필터)
    
    특징:
    - 보수적: 두 조건 모두 충족해야 매수
    - 높은 승률 예상
    - 거래 기회 적음
    """
    
    def __init__(
        self,
        symbol: str,
        bb_period: int = 20,
        bb_std: float = 2.0,
        bb_proximity_pct: float = 2.0,
        rsi_period: int = 14,
        rsi_threshold: float = 40.0
    ):
        """
        초기화
        
        Args:
            symbol: 거래 심볼
            bb_period: 볼린저 밴드 기간 (기본 20)
            bb_std: 볼린저 밴드 표준편차 (기본 2.0)
            bb_proximity_pct: BB 하단 근접 비율 (기본 2%)
            rsi_period: RSI 기간 (기본 14)
            rsi_threshold: RSI 임계값 (기본 40)
        """
        super().__init__(symbol)
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.bb_proximity_pct = bb_proximity_pct
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
    
    def generate_signal(
        self,
        candles: pd.DataFrame,
        current_time: Optional[datetime] = None
    ) -> Optional[str]:
        """
        매수/매도 신호 생성
        
        Args:
            candles: OHLCV 데이터
            current_time: 현재 시간 (미사용)
        
        Returns:
            'buy', 'sell', None
        """
        if len(candles) < max(self.bb_period, self.rsi_period) + 10:
            return None
        
        # 지표 계산
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            candles['close'],
            period=self.bb_period,
            std_dev=self.bb_std
        )
        rsi = calculate_rsi(candles['close'], period=self.rsi_period)
        
        # 현재 값
        current_price = candles['close'].iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # 조건 1: BB 하단 근접 (Proximity BB)
        distance_from_lower = ((current_price - current_bb_lower) / current_bb_lower) * 100
        bb_condition = distance_from_lower <= self.bb_proximity_pct
        
        # 조건 2: RSI 과매도 (Binance)
        rsi_condition = current_rsi < self.rsi_threshold
        
        # 매수 신호: 두 조건 모두 충족 (AND)
        if bb_condition and rsi_condition:
            return 'buy'
        
        return None
    
    def get_strategy_name(self) -> str:
        """전략 이름 반환"""
        return "Hybrid Conservative"
    
    def get_parameters(self) -> dict:
        """전략 파라미터 반환"""
        return {
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'bb_proximity_pct': self.bb_proximity_pct,
            'rsi_period': self.rsi_period,
            'rsi_threshold': self.rsi_threshold
        }
