"""
V4 자동매수 전략

특징:
- Preset 타임프레임 시스템 (4H/1H/15min)
- TradingView 표준 지표 (RSI, MACD, Volume)
- 선택적 지표 활성화
- 투자 스타일 선택 (conservative/balanced/aggressive)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy
from typing import Dict, Any, Optional


class V4AutoBuyStrategy(BaseStrategy):
    """
    V4 자동매수 전략

    Preset 기반 자동매수 전략으로, 투자 스타일에 따라
    타임프레임과 지표 파라미터가 자동 설정됩니다.

    투자 스타일:
    - conservative: 4시간봉, 보수적 진입
    - balanced: 1시간봉, 균형잡힌 진입 (기본값)
    - aggressive: 15분봉, 공격적 진입
    - custom: 사용자 정의 설정

    매수 조건:
    - RSI: 과매도 구간 (기본 30 이하)
    - MACD: 골든크로스 (MACD선이 Signal선 상향 돌파)
    - Volume: 평균 대비 급증 (기본 2배 이상)
    """

    # Preset 정의
    PRESETS = {
        "conservative": {
            "candle_unit": "240",  # 4시간
            "indicators": {
                "rsi": {
                    "enabled": True,
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70
                },
                "macd": {
                    "enabled": True,
                    "fast": 12,
                    "slow": 26,
                    "signal": 9
                },
                "volume": {
                    "enabled": True,
                    "period": 20,
                    "threshold": 2.0
                }
            }
        },
        "balanced": {
            "candle_unit": "60",  # 1시간
            "indicators": {
                "rsi": {
                    "enabled": True,
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70
                },
                "macd": {
                    "enabled": True,
                    "fast": 12,
                    "slow": 26,
                    "signal": 9
                },
                "volume": {
                    "enabled": True,
                    "period": 20,
                    "threshold": 2.0
                }
            }
        },
        "aggressive": {
            "candle_unit": "15",  # 15분
            "indicators": {
                "rsi": {
                    "enabled": True,
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70
                },
                "macd": {
                    "enabled": True,
                    "fast": 10,  # 더 빠른 반응
                    "slow": 20,
                    "signal": 7
                },
                "volume": {
                    "enabled": True,
                    "period": 20,
                    "threshold": 3.0  # 더 높은 기준
                }
            }
        }
    }

    def __init__(
        self,
        symbol: str,
        investment_style: str = "balanced",
        candle_unit: str = None,
        indicators_config: Dict[str, Any] = None,
        **kwargs
    ):
        """
        Args:
            symbol: 거래 심볼 (예: 'KRW-BTC')
            investment_style: 투자 스타일 (conservative/balanced/aggressive/custom)
            candle_unit: 캔들 단위 (분) - custom 스타일일 때만 사용
            indicators_config: 지표 설정 - custom 스타일일 때만 사용
                {
                    "rsi": {"enabled": True, "period": 14, ...},
                    "macd": {"enabled": True, "fast": 12, ...},
                    "volume": {"enabled": True, "threshold": 2.0, ...}
                }
        """
        super().__init__(name=f"V4 Auto-buy ({investment_style})")

        self.symbol = symbol
        self.investment_style = investment_style

        # Preset 적용
        if investment_style in self.PRESETS:
            preset = self.PRESETS[investment_style]
            self.candle_unit = preset["candle_unit"]
            self.indicators_config = preset["indicators"]
        elif investment_style == "custom":
            if not candle_unit or not indicators_config:
                raise ValueError("custom 스타일은 candle_unit과 indicators_config가 필요합니다.")
            self.candle_unit = candle_unit
            self.indicators_config = indicators_config
        else:
            raise ValueError(f"알 수 없는 투자 스타일: {investment_style}")

    def should_buy(self, candles: pd.DataFrame) -> bool:
        """
        매수 신호 판단

        ⚠️ 중요: 미래 데이터 사용 금지!
        백테스트 시 candles.iloc[:i+1]만 전달됨

        Args:
            candles: 캔들 데이터 DataFrame

        Returns:
            매수 신호 여부
        """
        if len(candles) < 30:  # 최소 데이터 필요
            return False

        # 포지션 보유 중이면 매수 안 함
        if self.position == 'long':
            return False

        buy_signals = []

        # 1. RSI 체크
        if self.indicators_config["rsi"]["enabled"]:
            rsi = self._calculate_rsi(candles)
            if rsi.iloc[-1] <= self.indicators_config["rsi"]["oversold"]:
                buy_signals.append(True)
            else:
                buy_signals.append(False)

        # 2. MACD 골든크로스 체크
        if self.indicators_config["macd"]["enabled"]:
            if self._check_macd_golden_cross(candles):
                buy_signals.append(True)
            else:
                buy_signals.append(False)

        # 3. Volume surge 체크
        if self.indicators_config["volume"]["enabled"]:
            if self._check_volume_surge(candles):
                buy_signals.append(True)
            else:
                buy_signals.append(False)

        # 모든 활성화된 조건 만족 시 매수
        if len(buy_signals) > 0 and all(buy_signals):
            return True

        return False

    def should_sell(self, candles: pd.DataFrame) -> bool:
        """
        매도 신호 판단

        주의: V4에서는 DCA 모드 사용으로 전략 매도 신호를 사용하지 않음
             익절/손절은 GroupManager가 처리

        Returns:
            항상 False (V4에서는 사용 안 함)
        """
        return False

    def generate_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """
        매매 신호 생성 (BaseStrategy 인터페이스)

        Args:
            candles: 캔들 데이터 DataFrame

        Returns:
            'buy', 'sell', 또는 None
        """
        if self.should_buy(candles):
            return 'buy'
        elif self.should_sell(candles):
            return 'sell'
        return None

    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'investment_style': self.investment_style,
            'candle_unit': self.candle_unit,
            'indicators_config': self.indicators_config
        }

    # ===== 지표 계산 메서드 =====

    def _calculate_rsi(self, candles: pd.DataFrame) -> pd.Series:
        """
        RSI 계산

        Args:
            candles: 캔들 데이터

        Returns:
            RSI 시리즈
        """
        period = self.indicators_config["rsi"]["period"]
        close = candles['close']

        # 가격 변화
        delta = close.diff()

        # 상승/하락 분리
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # RS (Relative Strength)
        rs = gain / loss

        # RSI
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _check_macd_golden_cross(self, candles: pd.DataFrame) -> bool:
        """
        MACD 골든크로스 확인

        골든크로스: MACD선이 Signal선을 상향 돌파

        Args:
            candles: 캔들 데이터

        Returns:
            골든크로스 발생 여부
        """
        config = self.indicators_config["macd"]
        close = candles['close']

        # EMA 계산
        exp1 = close.ewm(span=config["fast"], adjust=False).mean()
        exp2 = close.ewm(span=config["slow"], adjust=False).mean()

        # MACD 및 Signal 계산
        macd = exp1 - exp2
        signal = macd.ewm(span=config["signal"], adjust=False).mean()

        # 골든크로스 확인: 이전에는 아래, 현재는 위
        if len(candles) < 2:
            return False

        prev_macd = macd.iloc[-2]
        prev_signal = signal.iloc[-2]
        curr_macd = macd.iloc[-1]
        curr_signal = signal.iloc[-1]

        # 이전: MACD <= Signal, 현재: MACD > Signal
        is_golden_cross = (prev_macd <= prev_signal) and (curr_macd > curr_signal)

        return is_golden_cross

    def _check_volume_surge(self, candles: pd.DataFrame) -> bool:
        """
        거래량 급증 확인

        Args:
            candles: 캔들 데이터

        Returns:
            거래량 급증 여부
        """
        config = self.indicators_config["volume"]
        volume = candles['volume']

        # 평균 거래량
        avg_volume = volume.rolling(window=config["period"]).mean()

        # 현재 거래량
        current_volume = volume.iloc[-1]
        avg_current = avg_volume.iloc[-1]

        # 임계값 이상인지 확인
        if pd.isna(avg_current) or avg_current == 0:
            return False

        return current_volume >= (avg_current * config["threshold"])

    def get_indicator_values(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """
        현재 지표 값 반환 (모니터링/디버깅용)

        Args:
            candles: 캔들 데이터

        Returns:
            지표 값 딕셔너리
        """
        indicators = {}

        if self.indicators_config["rsi"]["enabled"]:
            rsi = self._calculate_rsi(candles)
            indicators['rsi'] = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

        if self.indicators_config["macd"]["enabled"]:
            indicators['macd_cross'] = self._check_macd_golden_cross(candles)

        if self.indicators_config["volume"]["enabled"]:
            indicators['volume_surge'] = self._check_volume_surge(candles)

        return indicators


if __name__ == "__main__":
    # 테스트 코드
    print("=== V4AutoBuyStrategy 테스트 ===\n")

    # 테스트 데이터 생성
    import numpy as np

    dates = pd.date_range('2025-01-01', periods=100, freq='h')
    test_candles = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + np.random.randn(100) * 1000,
        'high': 51000 + np.random.randn(100) * 1000,
        'low': 49000 + np.random.randn(100) * 1000,
        'close': 50000 + np.random.randn(100) * 1000,
        'volume': 1000000 + np.random.randn(100) * 100000
    })

    # 1. Balanced 스타일 (기본)
    print("1. Balanced 스타일 전략 생성")
    strategy_balanced = V4AutoBuyStrategy(
        symbol="KRW-BTC",
        investment_style="balanced"
    )
    print(f"   - 전략명: {strategy_balanced.name}")
    print(f"   - 캔들 단위: {strategy_balanced.candle_unit}분")
    print()

    # 2. Conservative 스타일
    print("2. Conservative 스타일 전략 생성")
    strategy_conservative = V4AutoBuyStrategy(
        symbol="KRW-ETH",
        investment_style="conservative"
    )
    print(f"   - 전략명: {strategy_conservative.name}")
    print(f"   - 캔들 단위: {strategy_conservative.candle_unit}분")
    print()

    # 3. Aggressive 스타일
    print("3. Aggressive 스타일 전략 생성")
    strategy_aggressive = V4AutoBuyStrategy(
        symbol="KRW-XRP",
        investment_style="aggressive"
    )
    print(f"   - 전략명: {strategy_aggressive.name}")
    print(f"   - 캔들 단위: {strategy_aggressive.candle_unit}분")
    print(f"   - MACD Fast: {strategy_aggressive.indicators_config['macd']['fast']}")
    print()

    # 4. 매수 신호 테스트
    print("4. 매수 신호 테스트 (Balanced)")
    signal = strategy_balanced.generate_signal(test_candles)
    print(f"   - 신호: {signal}")

    # 5. 지표 값 확인
    print("\n5. 지표 값 확인")
    indicators = strategy_balanced.get_indicator_values(test_candles)
    print(f"   - RSI: {indicators.get('rsi', 'N/A')}")
    print(f"   - MACD 골든크로스: {indicators.get('macd_cross', False)}")
    print(f"   - Volume 급증: {indicators.get('volume_surge', False)}")
    print()

    # 6. 파라미터 조회
    print("6. 전략 파라미터 조회")
    params = strategy_balanced.get_parameters()
    print(f"   - 심볼: {params['symbol']}")
    print(f"   - 스타일: {params['investment_style']}")
    print(f"   - RSI Period: {params['indicators_config']['rsi']['period']}")
    print()

    # 7. Custom 스타일 테스트
    print("7. Custom 스타일 테스트")
    try:
        strategy_custom = V4AutoBuyStrategy(
            symbol="KRW-DOGE",
            investment_style="custom",
            candle_unit="30",
            indicators_config={
                "rsi": {"enabled": True, "period": 10, "oversold": 25, "overbought": 75},
                "macd": {"enabled": True, "fast": 8, "slow": 17, "signal": 7},
                "volume": {"enabled": True, "period": 15, "threshold": 2.5}
            }
        )
        print(f"   ✅ Custom 스타일 생성 성공")
        print(f"   - 캔들 단위: {strategy_custom.candle_unit}분")
        print(f"   - RSI Period: {strategy_custom.indicators_config['rsi']['period']}")
    except Exception as e:
        print(f"   ⚠️ 오류: {e}")
    print()

    print("✅ 테스트 완료!")
