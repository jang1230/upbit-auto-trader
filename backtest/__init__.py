"""
Backtest Module

백테스팅 시스템:
- DataLoader: 과거 데이터 로드
- BacktestEngine: 백테스트 실행 엔진
- BacktestResult: 결과 분석

Usage:
    from backtest import DataLoader, BacktestEngine
    from core.strategies import ProximityBollingerBandsStrategy
    
    loader = DataLoader()
    candles = loader.load_ohlcv('KRW-BTC', days=90)
    
    strategy = ProximityBollingerBandsStrategy(symbol='KRW-BTC')
    engine = BacktestEngine(strategy, initial_capital=1000000)
    result = engine.run(candles)
    
    print(result.summary())
"""

from backtest.data_loader import DataLoader
from backtest.backtest_engine import BacktestEngine, BacktestResult, Trade

__all__ = [
    'DataLoader',
    'BacktestEngine',
    'BacktestResult',
    'Trade',
]
