"""
백테스트 실행 스크립트
Run Backtest Script

Proximity vs Filtered 전략을 비교 테스트합니다.

Usage:
    python -m backtest.run_backtest
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.data_loader import DataLoader
from backtest.backtest_engine import BacktestEngine
from core.strategies.proximity_bb_strategy import ProximityBollingerBandsStrategy
from core.strategies.filtered_bb_strategy import FilteredBollingerBandsStrategy
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def compare_strategies(
    symbol: str = 'KRW-BTC',
    days: int = 90,
    initial_capital: float = 1000000
):
    """
    Proximity vs Filtered 전략 비교
    
    Args:
        symbol: 테스트할 심볼
        days: 테스트 기간 (일)
        initial_capital: 초기 자본
    """
    print("=" * 80)
    print(f"백테스트: Proximity vs Filtered 전략 비교")
    print("=" * 80)
    print(f"심볼: {symbol}")
    print(f"기간: 최근 {days}일")
    print(f"초기 자본: {initial_capital:,.0f}원")
    print("=" * 80)
    
    # 1. 데이터 로드
    loader = DataLoader()
    candles = loader.load_ohlcv(symbol, days=days, interval='minute60')
    
    if candles.empty:
        logger.error("❌ 데이터 로드 실패")
        return
    
    print(f"\n✅ 데이터 로드 완료: {len(candles)}개 캔들")
    
    # 2. Proximity 전략 테스트
    print("\n" + "=" * 80)
    print("1️⃣  Proximity BB 전략 (DCA 최적화)")
    print("=" * 80)
    
    proximity_strategy = ProximityBollingerBandsStrategy(
        symbol=symbol,
        bb_proximity_pct=2.0,
        use_ma240_filter=False,
        atr_multiplier=0.05,
        min_hours_between_trades=1
    )
    
    proximity_engine = BacktestEngine(
        strategy=proximity_strategy,
        initial_capital=initial_capital
    )
    
    proximity_result = proximity_engine.run(candles)
    print(proximity_result.summary())
    
    # 3. Filtered 전략 테스트 (엄격한 파라미터)
    print("\n" + "=" * 80)
    print("2️⃣  Filtered BB 전략 (보수적 - 백테스팅 최적 파라미터)")
    print("=" * 80)
    
    filtered_strategy = FilteredBollingerBandsStrategy.create_for_coin(symbol)
    
    filtered_engine = BacktestEngine(
        strategy=filtered_strategy,
        initial_capital=initial_capital
    )
    
    filtered_result = filtered_engine.run(candles)
    print(filtered_result.summary())
    
    # 4. 비교 분석
    print("\n" + "=" * 80)
    print("📊 전략 비교 분석")
    print("=" * 80)
    
    comparison = f"""
{'지표':<20} {'Proximity':<20} {'Filtered':<20} {'차이':<20}
{'-' * 80}
수익률              {proximity_result.total_return:>+6.2f}%            {filtered_result.total_return:>+6.2f}%            {proximity_result.total_return - filtered_result.total_return:>+6.2f}%p
총 거래 횟수        {proximity_result.total_trades:>6}회             {filtered_result.total_trades:>6}회             {proximity_result.total_trades - filtered_result.total_trades:>+6}회
승률                {proximity_result.win_rate:>6.1f}%            {filtered_result.win_rate:>6.1f}%            {proximity_result.win_rate - filtered_result.win_rate:>+6.1f}%p
MDD                 {proximity_result.max_drawdown:>6.2f}%            {filtered_result.max_drawdown:>6.2f}%            {proximity_result.max_drawdown - filtered_result.max_drawdown:>+6.2f}%p
Sharpe Ratio        {proximity_result.sharpe_ratio:>6.2f}             {filtered_result.sharpe_ratio:>6.2f}             {proximity_result.sharpe_ratio - filtered_result.sharpe_ratio:>+6.2f}
"""
    
    print(comparison)
    
    # 5. 결론
    print("=" * 80)
    print("💡 결론")
    print("=" * 80)
    
    if proximity_result.total_return > filtered_result.total_return:
        winner = "Proximity"
        winner_return = proximity_result.total_return
    else:
        winner = "Filtered"
        winner_return = filtered_result.total_return
    
    print(f"""
✅ {winner} 전략이 {winner_return:+.2f}% 수익률로 우세

📌 Proximity 전략 특징:
   - 거래 빈도: {proximity_result.total_trades}회 ({proximity_result.total_trades / (days / 30):.1f}회/월)
   - DCA 철학에 부합: {'✅' if proximity_result.total_trades > filtered_result.total_trades else '❌'}
   - 심리적 안정감: {'높음 (빈번한 거래)' if proximity_result.total_trades > 10 else '낮음'}

📌 Filtered 전략 특징:
   - 거래 빈도: {filtered_result.total_trades}회 ({filtered_result.total_trades / (days / 30):.1f}회/월)
   - 보수적 접근: {'✅' if filtered_result.total_trades < proximity_result.total_trades else '❌'}
   - 엄격한 필터: ✅
""")
    
    print("=" * 80)
    print("백테스트 완료!")
    print("=" * 80)
    
    return proximity_result, filtered_result


def test_single_strategy(
    strategy_name: str = 'proximity',
    symbol: str = 'KRW-BTC',
    days: int = 90
):
    """
    단일 전략 테스트
    
    Args:
        strategy_name: 'proximity' or 'filtered'
        symbol: 테스트할 심볼
        days: 테스트 기간
    """
    print("=" * 80)
    print(f"백테스트: {strategy_name.upper()} 전략")
    print("=" * 80)
    
    # 데이터 로드
    loader = DataLoader()
    candles = loader.load_ohlcv(symbol, days=days, interval='minute60')
    
    if candles.empty:
        logger.error("❌ 데이터 로드 실패")
        return
    
    # 전략 선택
    if strategy_name.lower() == 'proximity':
        strategy = ProximityBollingerBandsStrategy(symbol=symbol)
    else:
        strategy = FilteredBollingerBandsStrategy.create_for_coin(symbol)
    
    # 백테스트 실행
    engine = BacktestEngine(strategy=strategy, initial_capital=1000000)
    result = engine.run(candles)
    
    print(result.summary())
    
    return result


if __name__ == "__main__":
    """메인 실행"""
    
    # 전략 비교 테스트
    compare_strategies(
        symbol='KRW-BTC',
        days=90,  # 최근 3개월
        initial_capital=1000000
    )
    
    # 다른 코인 테스트
    # compare_strategies(symbol='KRW-ETH', days=90)
    # compare_strategies(symbol='KRW-XRP', days=90)
