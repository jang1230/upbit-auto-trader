"""
Expert Strategy - 10개 전문가 프로필 기반 전략

특징:
- 5개 지표 가중치 기반 스코어링 (RSI, MACD, Bollinger Bands, Volume, Trend)
- 10가지 전문가 프로필 선택 가능
- 신뢰도(Confidence) 기반 매수 판단
- 가변 타임프레임 지원 (10분/15분/1시간/4시간)

사용법:
    strategy = ExpertStrategy(
        symbol="KRW-BTC",
        expert_profile="balanced_expert",
        candle_unit="10"  # 10분봉
    )

    if strategy.should_buy(candles):
        # 매수 실행
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ExpertStrategy(BaseStrategy):
    """
    10개 전문가 시스템 기반 전략

    5개 지표를 가중치 기반으로 평가하여 매수 신호를 생성합니다.
    각 전문가 프로필은 지표별로 다른 가중치를 사용합니다.
    """

    # 10개 전문가 프로필 정의 (Funding Rate, Fear & Greed 제외)
    EXPERT_PROFILES = {
        "rsi_specialist": {
            "name": "RSI 전문가",
            "description": "과매수/과매도 포착 중심",
            "weights": {
                "rsi": 0.70,
                "macd": 0.65,
                "bollinger": 0.50,
                "volume": 0.60,
                "trend": 0.40
            },
            "confidence_threshold": 50
        },
        "momentum_expert": {
            "name": "모멘텀 전문가",
            "description": "MACD 골든크로스 중심",
            "weights": {
                "macd": 0.75,
                "volume": 0.70,
                "rsi": 0.50,
                "trend": 0.60,
                "bollinger": 0.40
            },
            "confidence_threshold": 50
        },
        "volatility_expert": {
            "name": "볼린저 전문가",
            "description": "변동성 확장 포착",
            "weights": {
                "bollinger": 0.85,
                "volume": 0.65,
                "rsi": 0.55,
                "macd": 0.60,
                "trend": 0.40
            },
            "confidence_threshold": 50
        },
        "volume_expert": {
            "name": "거래량 전문가",
            "description": "거래량 급증 기반",
            "weights": {
                "volume": 0.85,
                "macd": 0.65,
                "bollinger": 0.50,
                "rsi": 0.50,
                "trend": 0.45
            },
            "confidence_threshold": 50
        },
        "balanced_expert": {
            "name": "균형형 전문가",
            "description": "모든 지표 균등 분석",
            "weights": {
                "rsi": 0.65,
                "macd": 0.65,
                "bollinger": 0.65,
                "volume": 0.65,
                "trend": 0.60
            },
            "confidence_threshold": 45
        },
        "conservative_expert": {
            "name": "보수적 전문가",
            "description": "안전한 진입 우선",
            "weights": {
                "rsi": 0.75,
                "trend": 0.70,
                "bollinger": 0.60,
                "macd": 0.50,
                "volume": 0.55
            },
            "confidence_threshold": 55  # 높은 기준
        },
        "aggressive_expert": {
            "name": "공격적 전문가",
            "description": "빠른 진입",
            "weights": {
                "macd": 0.80,
                "volume": 0.75,
                "rsi": 0.45,
                "bollinger": 0.55,
                "trend": 0.50
            },
            "confidence_threshold": 45  # 낮은 기준
        },
        "trend_follower": {
            "name": "추세 추종가",
            "description": "강한 상승 추세 포착",
            "weights": {
                "trend": 0.80,
                "macd": 0.70,
                "volume": 0.65,
                "rsi": 0.45,
                "bollinger": 0.50
            },
            "confidence_threshold": 50
        },
        "reversal_hunter": {
            "name": "반전 사냥꾼",
            "description": "과매도 반등 노림",
            "weights": {
                "rsi": 0.80,
                "bollinger": 0.70,
                "macd": 0.55,
                "trend": 0.40,
                "volume": 0.60
            },
            "confidence_threshold": 50
        },
        "smart_money": {
            "name": "스마트머니",
            "description": "거래량+추세 종합",
            "weights": {
                "volume": 0.80,
                "trend": 0.75,
                "macd": 0.65,
                "bollinger": 0.55,
                "rsi": 0.50
            },
            "confidence_threshold": 50
        }
    }

    def __init__(
        self,
        symbol: str,
        expert_profile: str = "balanced_expert",
        candle_unit: str = "10",
        **kwargs
    ):
        """
        Args:
            symbol: 거래 심볼 (예: 'KRW-BTC')
            expert_profile: 전문가 프로필 키 (EXPERT_PROFILES 중 하나)
            candle_unit: 캔들 타임프레임 ("10", "15", "60", "240")

        Raises:
            ValueError: 잘못된 expert_profile
        """
        if expert_profile not in self.EXPERT_PROFILES:
            raise ValueError(
                f"Unknown expert profile: {expert_profile}. "
                f"Available: {list(self.EXPERT_PROFILES.keys())}"
            )

        self.profile = self.EXPERT_PROFILES[expert_profile]
        super().__init__(name=f"Expert ({self.profile['name']})")

        self.symbol = symbol
        self.expert_profile = expert_profile
        self.candle_unit = candle_unit

        logger.info(
            f"ExpertStrategy 초기화: {self.profile['name']}, "
            f"Symbol={symbol}, Candle={candle_unit}min"
        )

    def should_buy(self, candles: pd.DataFrame) -> bool:
        """
        매수 신호 판단

        5개 지표를 계산하고, 가중치 기반 신뢰도를 계산하여
        threshold 이상이면 매수 신호를 반환합니다.

        Args:
            candles: 캔들 데이터 DataFrame (최소 100개 권장)

        Returns:
            매수 신호 여부
        """
        # 최소 데이터 체크
        if len(candles) < 60:  # MA50 계산을 위해 최소 60개 필요
            logger.debug(f"데이터 부족: {len(candles)}개 (최소 60개 필요)")
            return False

        # 포지션 보유 중이면 매수 안 함
        if self.position == 'long':
            return False

        try:
            # 5개 지표 신호 계산
            signals = self.calculate_indicator_signals(candles)

            # 신뢰도 계산
            confidence = self.calculate_confidence(signals)

            # Threshold 확인
            threshold = self.profile['confidence_threshold']

            if confidence >= threshold:
                logger.info(
                    f"[{self.profile['name']}] 매수 신호! "
                    f"Confidence: {confidence:.2f}% (Threshold: {threshold}%)"
                )
                return True
            else:
                logger.debug(
                    f"[{self.profile['name']}] 매수 보류 "
                    f"Confidence: {confidence:.2f}% < {threshold}%"
                )
                return False

        except Exception as e:
            logger.error(f"매수 신호 계산 중 오류: {e}", exc_info=True)
            return False

    def should_sell(self, candles: pd.DataFrame) -> bool:
        """
        매도 신호 판단

        주의: V4에서는 DCA 모드 사용으로 전략 매도 신호를 사용하지 않음
             익절/손절은 profit_loss_settings가 처리

        Returns:
            항상 False (DCA 시스템 사용)
        """
        return False

    def calculate_indicator_signals(self, candles: pd.DataFrame) -> Dict[str, Dict]:
        """
        5개 지표의 신호와 강도를 계산

        Returns:
            {
                'rsi': {'signal': 'long'|'neutral', 'strength': 0-100},
                'macd': {...},
                'bollinger': {...},
                'volume': {...},
                'trend': {...}
            }
        """
        signals = {}

        signals['rsi'] = self._calculate_rsi_signal(candles)
        signals['macd'] = self._calculate_macd_signal(candles)
        signals['bollinger'] = self._calculate_bb_signal(candles)
        signals['volume'] = self._calculate_volume_signal(candles)
        signals['trend'] = self._calculate_trend_signal(candles)

        return signals

    def calculate_confidence(self, signals: Dict[str, Dict]) -> float:
        """
        가중치 기반 신뢰도 계산

        Args:
            signals: calculate_indicator_signals() 결과

        Returns:
            0~100 사이의 신뢰도 퍼센트
        """
        long_score = 0.0
        max_possible_score = 0.0

        weights = self.profile['weights']

        for indicator, signal_data in signals.items():
            weight = weights.get(indicator, 0.0)
            strength = signal_data['strength']  # 0~100

            if signal_data['signal'] == 'long':
                long_score += strength * weight

            max_possible_score += 100 * weight

        if max_possible_score == 0:
            return 0.0

        confidence = (long_score / max_possible_score) * 100
        return round(confidence, 2)

    def get_signal_details(self, candles: pd.DataFrame) -> Dict:
        """
        상세 신호 정보 반환 (디버깅/로깅용)

        Returns:
            {
                'expert': 전문가 이름,
                'confidence': 신뢰도,
                'threshold': 임계값,
                'signals': 각 지표별 신호,
                'should_buy': 매수 여부
            }
        """
        try:
            signals = self.calculate_indicator_signals(candles)
            confidence = self.calculate_confidence(signals)

            return {
                'expert': self.profile['name'],
                'confidence': confidence,
                'threshold': self.profile['confidence_threshold'],
                'signals': signals,
                'should_buy': confidence >= self.profile['confidence_threshold']
            }
        except Exception as e:
            logger.error(f"신호 상세 정보 계산 중 오류: {e}")
            return {
                'expert': self.profile['name'],
                'error': str(e)
            }

    # ========== 지표 계산 함수 ==========

    def _calculate_rsi_signal(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """
        RSI 신호 계산

        문서 기준:
        - RSI < 30: LONG, 강도 = (30 - RSI) / 30 * 100
        - RSI 30-40: 약한 LONG
        - RSI 40-60: NEUTRAL

        Returns:
            {'signal': 'long'|'neutral', 'strength': 0-100}
        """
        period = 14
        delta = candles['close'].diff()

        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]

        if current_rsi < 30:
            # 강한 LONG 신호
            strength = ((30 - current_rsi) / 30) * 100
            strength = min(100, max(0, strength))
            return {'signal': 'long', 'strength': round(strength, 2), 'rsi': round(current_rsi, 2)}
        elif current_rsi < 40:
            # 약한 LONG 신호
            strength = ((40 - current_rsi) / 10) * 50  # 30~40 → 50~0
            strength = min(100, max(0, strength))
            return {'signal': 'long', 'strength': round(strength, 2), 'rsi': round(current_rsi, 2)}
        else:
            # NEUTRAL
            return {'signal': 'neutral', 'strength': 40, 'rsi': round(current_rsi, 2)}

    def _calculate_macd_signal(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """
        MACD 신호 계산

        문서 기준:
        - MACD > Signal: LONG, 강도 = |Histogram| × 10
        - MACD 골든크로스: 강한 LONG 신호

        Returns:
            {'signal': 'long'|'neutral', 'strength': 0-100}
        """
        fast = 12
        slow = 26
        signal_period = 9

        ema_fast = candles['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = candles['close'].ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        prev_histogram = histogram.iloc[-2] if len(histogram) > 1 else 0

        # 골든크로스 확인 (이전: 음수, 현재: 양수)
        golden_cross = (prev_histogram < 0) and (current_histogram > 0)

        if current_macd > current_signal:
            # LONG 신호
            strength = abs(current_histogram) * 10
            strength = min(100, max(0, strength))

            if golden_cross:
                # 골든크로스 발생 시 강도 증가
                strength = min(100, strength * 1.5)

            return {
                'signal': 'long',
                'strength': round(strength, 2),
                'macd': round(current_macd, 2),
                'signal_line': round(current_signal, 2),
                'histogram': round(current_histogram, 2),
                'golden_cross': golden_cross
            }
        else:
            return {
                'signal': 'neutral',
                'strength': 40,
                'macd': round(current_macd, 2),
                'signal_line': round(current_signal, 2)
            }

    def _calculate_bb_signal(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Bollinger Bands 신호 계산

        문서 기준:
        - 위치 < 0.2 (하단 근처): LONG, 강도 = (0.2 - 위치) / 0.2 * 100
        - 하단 밴드 터치 후 반등: 강한 LONG 신호

        Returns:
            {'signal': 'long'|'neutral', 'strength': 0-100}
        """
        period = 20
        std_dev = 2

        ma20 = candles['close'].rolling(window=period).mean()
        std = candles['close'].rolling(window=period).std()

        upper_band = ma20 + (std_dev * std)
        lower_band = ma20 - (std_dev * std)

        current_price = candles['close'].iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_ma = ma20.iloc[-1]

        # 현재 가격 위치 계산 (0~1)
        band_width = current_upper - current_lower
        if band_width == 0:
            position = 0.5
        else:
            position = (current_price - current_lower) / band_width

        if position < 0.2:
            # 하단 근처 - LONG 신호
            strength = ((0.2 - position) / 0.2) * 100
            strength = min(100, max(0, strength))
            return {
                'signal': 'long',
                'strength': round(strength, 2),
                'position': round(position, 3),
                'lower_band': round(current_lower, 2),
                'upper_band': round(current_upper, 2)
            }
        else:
            return {
                'signal': 'neutral',
                'strength': 40,
                'position': round(position, 3)
            }

    def _calculate_volume_signal(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Volume 신호 계산

        문서 기준:
        - 비율 > 1.5 (거래량 급증) + 상승 추세: LONG, 강도 = (비율 - 1) * 50

        Returns:
            {'signal': 'long'|'neutral', 'strength': 0-100}
        """
        volume_period = 20

        avg_volume = candles['volume'].rolling(window=volume_period).mean()
        current_volume = candles['volume'].iloc[-1]
        avg_vol = avg_volume.iloc[-1]

        if avg_vol == 0:
            ratio = 1.0
        else:
            ratio = current_volume / avg_vol

        # 추세 확인 (현재가 vs 이전가)
        current_price = candles['close'].iloc[-1]
        prev_price = candles['close'].iloc[-2] if len(candles) > 1 else current_price
        is_uptrend = current_price > prev_price

        if ratio > 1.5 and is_uptrend:
            # 거래량 급증 + 상승 추세 - LONG 신호
            strength = (ratio - 1) * 50
            strength = min(100, max(0, strength))
            return {
                'signal': 'long',
                'strength': round(strength, 2),
                'ratio': round(ratio, 2),
                'uptrend': True
            }
        elif ratio > 1.5:
            # 거래량 급증만 있음 - 약한 신호
            strength = (ratio - 1) * 30
            strength = min(100, max(0, strength))
            return {
                'signal': 'long',
                'strength': round(strength, 2),
                'ratio': round(ratio, 2),
                'uptrend': False
            }
        else:
            return {
                'signal': 'neutral',
                'strength': 40,
                'ratio': round(ratio, 2)
            }

    def _calculate_trend_signal(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Trend 신호 계산

        문서 기준:
        - 현재가 > MA20 > MA50: LONG (강한 상승 추세)
          강도 = ((현재가-MA20)/MA20 + (MA20-MA50)/MA50) × 1000

        Returns:
            {'signal': 'long'|'neutral', 'strength': 0-100}
        """
        ma20 = candles['close'].rolling(window=20).mean()
        ma50 = candles['close'].rolling(window=50).mean()

        current_price = candles['close'].iloc[-1]
        current_ma20 = ma20.iloc[-1]
        current_ma50 = ma50.iloc[-1]

        # 강한 상승 추세: 현재가 > MA20 > MA50
        if current_price > current_ma20 > current_ma50:
            # 강도 계산
            price_to_ma20_pct = (current_price - current_ma20) / current_ma20
            ma20_to_ma50_pct = (current_ma20 - current_ma50) / current_ma50

            strength = (price_to_ma20_pct + ma20_to_ma50_pct) * 1000
            strength = min(100, max(0, strength))

            return {
                'signal': 'long',
                'strength': round(strength, 2),
                'ma20': round(current_ma20, 2),
                'ma50': round(current_ma50, 2),
                'trend': 'strong_uptrend'
            }
        elif current_price > current_ma20:
            # 약한 상승 추세
            price_to_ma20_pct = (current_price - current_ma20) / current_ma20
            strength = price_to_ma20_pct * 500
            strength = min(100, max(0, strength))

            return {
                'signal': 'long',
                'strength': round(strength, 2),
                'ma20': round(current_ma20, 2),
                'ma50': round(current_ma50, 2),
                'trend': 'weak_uptrend'
            }
        else:
            return {
                'signal': 'neutral',
                'strength': 40,
                'ma20': round(current_ma20, 2),
                'ma50': round(current_ma50, 2),
                'trend': 'downtrend_or_sideways'
            }

    def generate_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """
        BaseStrategy 인터페이스 구현

        Returns:
            'buy', 'sell', None
        """
        if self.should_buy(candles):
            return 'buy'
        elif self.should_sell(candles):
            return 'sell'
        else:
            return None

    def get_parameters(self) -> Dict[str, Any]:
        """
        전략 파라미터 반환

        Returns:
            전략 설정 정보
        """
        return {
            'strategy': 'ExpertStrategy',
            'symbol': self.symbol,
            'expert_profile': self.expert_profile,
            'expert_name': self.profile['name'],
            'candle_unit': self.candle_unit,
            'confidence_threshold': self.profile['confidence_threshold'],
            'weights': self.profile['weights']
        }
