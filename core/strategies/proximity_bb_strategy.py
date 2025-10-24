"""
근접 볼린저 밴드 전략 (DCA 최적화)
Proximity Bollinger Bands Strategy (DCA Optimized)

DCA 철학에 맞춘 "자주 사는" 전략입니다.
엄격한 돌파 대신 볼린저 밴드 하단 근접(2% 이내)을 감지하여
실제 거래 기회를 증가시킵니다.

💡 핵심 철학:
"정확한 바닥을 맞추려 하지 말고, 통계적으로 저평가된 구간에서 자주 매수"

전략 특징:
✅ 근접 모드: 볼린저 밴드 하단 2% 이내 진입 시 매수
✅ 완화된 필터: MA240/ATR 필터 최소화 (선택적 사용)
✅ 빈번한 기회: 시간 필터 1시간 (하루 최대 24회)
✅ DCA 친화적: 월 1-2회 → 일 1-3회로 기회 증가

매수 조건:
1. 가격 <= 볼린저 밴드 하단 * 1.02 (2% 근접)
2. (선택) MA240 필터 (기본 OFF)
3. (완화) ATR >= 0.05% (거의 항상 통과)
4. 마지막 거래 후 1시간 경과

매도 조건:
⚠️ DCA 시스템에서는 전략의 매도 신호를 사용하지 않습니다.
매도는 "고급 DCA 설정"의 다단계 익절/손절로 처리됩니다.

적합한 사용자:
- DCA 방식으로 평균 단가를 낮추고 싶은 투자자
- 거래 빈도를 높여 심리적 안정감을 원하는 투자자
- 볼린저 밴드 신뢰도를 유지하되 엄격함은 완화하고 싶은 투자자
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from core.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class ProximityBollingerBandsStrategy(BaseStrategy):
    """
    근접 볼린저 밴드 전략 (DCA 최적화)
    
    Parameters:
        bb_period: 볼린저 밴드 기간 (기본 20)
        bb_std_dev: 볼린저 밴드 표준편차 배수 (기본 2.0)
        bb_proximity_pct: 하단 근접 퍼센트 (기본 2.0%)
        use_ma240_filter: MA240 추세 필터 사용 여부 (기본 False)
        atr_period: ATR 계산 기간 (기본 14)
        atr_multiplier: ATR 최소 기준 (기본 0.05%, 거의 통과)
        min_hours_between_trades: 최소 거래 대기 시간 (기본 1시간)
    """
    
    def __init__(
        self,
        bb_period: int = 20,
        bb_std_dev: float = 2.0,
        bb_proximity_pct: float = 2.0,
        use_ma240_filter: bool = False,
        ma_period: int = 240,
        atr_period: int = 14,
        atr_multiplier: float = 0.05,
        min_hours_between_trades: int = 1,
        symbol: str = "DEFAULT"
    ):
        """
        Args:
            bb_period: 볼린저 밴드 기간
            bb_std_dev: 볼린저 밴드 표준편차 배수
            bb_proximity_pct: 볼린저밴드 하단 근접 % (기본 2.0%)
            use_ma240_filter: MA240 추세 필터 사용 여부 (기본 False)
            ma_period: 추세 필터 이동평균 기간 (기본 240)
            atr_period: ATR 계산 기간
            atr_multiplier: ATR 최소 기준 (가격의 %, 기본 0.05%)
            min_hours_between_trades: 최소 거래 대기 시간 (시간, 기본 1)
            symbol: 코인 심볼 (로깅용)
        """
        super().__init__(f"Proximity BB Strategy ({symbol})")

        self.bb_period = bb_period
        self.bb_std_dev = bb_std_dev
        self.bb_proximity_pct = bb_proximity_pct
        self.use_ma240_filter = use_ma240_filter
        self.ma_period = ma_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.min_hours_between_trades = min_hours_between_trades
        self.symbol = symbol
        
        # 마지막 거래 시간 추적
        self.last_trade_time: Optional[datetime] = None

        logger.info(
            f"{symbol} 근접 BB 전략 초기화: "
            f"bb_std={bb_std_dev}, proximity={bb_proximity_pct}%, "
            f"ma240_filter={'ON' if use_ma240_filter else 'OFF'}, "
            f"atr={atr_multiplier}%, wait={min_hours_between_trades}h"
        )
    
    def calculate_bollinger_bands(self, closes: pd.Series) -> tuple:
        """볼린저 밴드 계산"""
        ma = closes.rolling(window=self.bb_period).mean()
        std = closes.rolling(window=self.bb_period).std()
        upper = ma + (std * self.bb_std_dev)
        lower = ma - (std * self.bb_std_dev)
        return ma, upper, lower
    
    def calculate_ma(self, closes: pd.Series) -> pd.Series:
        """이동평균 계산"""
        return closes.rolling(window=self.ma_period).mean()
    
    def calculate_atr(self, candles: pd.DataFrame) -> pd.Series:
        """ATR (Average True Range) 계산"""
        high = candles['high']
        low = candles['low']
        close = candles['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean()
        
        return atr
    
    def check_time_filter(self, current_time: datetime) -> bool:
        """
        시간 필터 확인
        
        Args:
            current_time: 현재 시간
        
        Returns:
            bool: True면 거래 가능, False면 대기 필요
        """
        if self.last_trade_time is None:
            return True
        
        time_diff = current_time - self.last_trade_time
        min_time_delta = timedelta(hours=self.min_hours_between_trades)
        
        return time_diff >= min_time_delta
    
    def generate_signal(
        self, 
        candles: pd.DataFrame,
        current_time: Optional[datetime] = None
    ) -> Optional[str]:
        """
        근접 볼린저 밴드 매매 신호 생성
        
        Args:
            candles: 캔들 데이터
            current_time: 현재 시간 (None이면 candles의 마지막 인덱스 사용)
        
        Returns:
            Optional[str]: 'buy', 'sell', None
        """
        # 최소 데이터 확인
        min_required = max(self.bb_period, self.ma_period, self.atr_period) + 1
        if len(candles) < min_required:
            logger.debug(
                f"{self.symbol} 근접 BB: 데이터 부족 "
                f"({len(candles)} < {min_required})"
            )
            return None
        
        # 현재 시간 설정
        if current_time is None:
            if isinstance(candles.index, pd.DatetimeIndex):
                current_time = candles.index[-1]
            else:
                current_time = datetime.now()
        
        # 시간 필터 확인
        if not self.check_time_filter(current_time):
            time_left = (
                self.last_trade_time + 
                timedelta(hours=self.min_hours_between_trades) - 
                current_time
            )
            logger.debug(
                f"{self.symbol} 시간 필터: {time_left.total_seconds()/3600:.1f}시간 대기 필요"
            )
            return None
        
        # 지표 계산
        closes = candles['close']
        ma20, upper_band, lower_band = self.calculate_bollinger_bands(closes)
        ma240 = self.calculate_ma(closes)
        atr = self.calculate_atr(candles)
        
        # 현재 값
        current_price = closes.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_ma240 = ma240.iloc[-1]
        current_atr = atr.iloc[-1]
        
        # NaN 체크
        if pd.isna(current_upper) or pd.isna(current_lower) or \
           pd.isna(current_ma240) or pd.isna(current_atr):
            logger.debug(f"{self.symbol} 근접 BB: 지표 계산 불가 (NaN)")
            return None
        
        # ATR 변동성 필터 (완화됨: 0.05%)
        min_atr = current_price * (self.atr_multiplier / 100)
        if current_atr < min_atr:
            logger.debug(
                f"{self.symbol} 변동성 필터: "
                f"ATR {current_atr:.2f} < {min_atr:.2f}"
            )
            return None
        
        # 매수 신호: 하단 밴드 근접 (근접 % 이내)
        if self.is_flat():
            # 볼린저밴드 하단 근접 체크 (핵심 로직)
            lower_threshold = current_lower * (1 + self.bb_proximity_pct / 100)
            bb_condition = current_price <= lower_threshold

            # MA240 필터 체크 (선택적)
            ma240_condition = True
            if self.use_ma240_filter:
                ma240_condition = current_price < current_ma240

            # 최종 조건: BB 근접 AND (MA240 필터 OFF 또는 MA240 조건 만족)
            if bb_condition and ma240_condition:
                proximity_pct_actual = ((current_price - current_lower) / current_lower) * 100
                logger.info(
                    f"{self.symbol} 매수 신호: "
                    f"Price={current_price:.0f}, "
                    f"Lower={current_lower:.0f} (근접도: {proximity_pct_actual:+.2f}%)"
                    + (f", MA240={current_ma240:.0f}" if self.use_ma240_filter else "")
                )
                self.set_position('long')
                self.last_trade_time = current_time
                return 'buy'
        
        # 매도 신호: 상단 밴드 위 + MA240 위 (상승 추세)
        # ⚠️ DCA 시스템에서는 다단계 익절/손절 사용, 전략 매도 신호는 참고용
        elif self.is_long():
            if current_price > current_upper and current_price > current_ma240:
                logger.info(
                    f"{self.symbol} 매도 신호 (참고용): "
                    f"Price={current_price:.0f} > "
                    f"Upper={current_upper:.0f}, "
                    f"MA240={current_ma240:.0f}"
                )
                self.set_position(None)
                self.last_trade_time = current_time
                return 'sell'
        
        return None
    
    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            'strategy': 'Proximity Bollinger Bands (DCA Optimized)',
            'symbol': self.symbol,
            'bb_period': self.bb_period,
            'bb_std_dev': self.bb_std_dev,
            'bb_proximity_pct': self.bb_proximity_pct,
            'use_ma240_filter': self.use_ma240_filter,
            'ma_period': self.ma_period,
            'atr_period': self.atr_period,
            'atr_multiplier': self.atr_multiplier,
            'min_hours_between_trades': self.min_hours_between_trades,
            'position': self.position,
            'last_trade_time': self.last_trade_time
        }
    
    def reset(self):
        """전략 상태 초기화"""
        super().reset()
        self.last_trade_time = None
        logger.info(f"{self.symbol} 전략 상태 초기화")


if __name__ == "__main__":
    """테스트 코드"""
    print("=" * 80)
    print("근접 볼린저 밴드 전략 테스트 (DCA 최적화)")
    print("=" * 80)
    
    # 기본 전략 생성
    print("\n1. 기본 전략 (DCA 친화 파라미터):")
    strategy = ProximityBollingerBandsStrategy(symbol='KRW-BTC')
    print(f"   전략: {strategy.get_parameters()}")
    
    # 파라미터 설명
    print("\n2. 핵심 파라미터:")
    print("   - bb_proximity_pct: 2.0% (근접 모드)")
    print("   - use_ma240_filter: False (MA240 OFF)")
    print("   - atr_multiplier: 0.05% (거의 통과)")
    print("   - min_hours_between_trades: 1시간 (빈번한 기회)")
    
    print("\n3. 예상 거래 빈도:")
    print("   - 기존 Filtered 전략: 월 1-2회")
    print("   - Proximity 전략: 일 1-3회")
    
    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)
