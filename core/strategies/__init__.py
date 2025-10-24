"""
Trading Strategies Module

Available strategies:
- BaseStrategy: Abstract base class
- SimpleStrategy: Buy & Hold strategy (for testing)
- AggressiveTestStrategy: Aggressive test strategy (for testing UI)
- RSI_Strategy: RSI overbought/oversold strategy
- MACD_Strategy: MACD crossover strategy
- BollingerBands_Strategy: Bollinger Bands breakout strategy
- FilteredBollingerBandsStrategy: Optimized BB strategy with filters
- ProximityBollingerBandsStrategy: DCA-optimized proximity BB strategy
- ScalpingStrategy: 단타 트레이딩 전략 (MACD + 거래량, 하루 20~30회) ⭐ RECOMMENDED

Usage:
    from core.strategies import RSI_Strategy, MACD_Strategy, BollingerBands_Strategy
    from core.strategies import FilteredBollingerBandsStrategy, ProximityBollingerBandsStrategy
    from core.strategies import ScalpingStrategy

    # ⭐ 단타 전략 (권장) - 하루 20~30회 매수 타점 (10개 코인 전체)
    scalping = ScalpingStrategy(symbol='KRW-BTC')
    scalping_custom = ScalpingStrategy(
        symbol='KRW-ETH',
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        volume_threshold=2.0  # 거래량 2배 기준
    )

    # 기본 전략들
    rsi_strategy = RSI_Strategy(period=14, oversold=30, overbought=70)
    macd_strategy = MACD_Strategy(fast_period=12, slow_period=26, signal_period=9)
    bb_strategy = BollingerBands_Strategy(period=20, std_dev=2.0)

    # DCA 최적화 전략 - 근접 모드로 거래 기회 증가
    btc_strategy = ProximityBollingerBandsStrategy(symbol='KRW-BTC')
    eth_strategy = ProximityBollingerBandsStrategy(symbol='KRW-ETH')
    xrp_strategy = ProximityBollingerBandsStrategy(symbol='KRW-XRP')

    # 엄격한 필터링 전략 (보수적)
    btc_strict = FilteredBollingerBandsStrategy.create_for_coin('KRW-BTC')

    test_strategy = AggressiveTestStrategy()  # For UI testing only!
"""

from core.strategies.base import BaseStrategy, SimpleStrategy
from core.strategies.rsi_strategy import RSI_Strategy
from core.strategies.macd_strategy import MACD_Strategy
from core.strategies.bb_strategy import BollingerBands_Strategy
from core.strategies.aggressive_test_strategy import AggressiveTestStrategy
from core.strategies.filtered_bb_strategy import FilteredBollingerBandsStrategy
from core.strategies.proximity_bb_strategy import ProximityBollingerBandsStrategy
from core.strategies.scalping_strategy import ScalpingStrategy

__all__ = [
    'BaseStrategy',
    'SimpleStrategy',
    'AggressiveTestStrategy',
    'RSI_Strategy',
    'MACD_Strategy',
    'BollingerBands_Strategy',
    'FilteredBollingerBandsStrategy',
    'ProximityBollingerBandsStrategy',
    'ScalpingStrategy',
]
