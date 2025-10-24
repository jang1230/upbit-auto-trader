"""
모든 전략 비교 백테스팅
1년치 데이터로 4가지 전략 성과 비교
"""

import logging
from datetime import datetime, timedelta
from core.historical_data import HistoricalDataFetcher
from core.dca_backtester import DcaBacktester
from core.strategies import (
    BollingerBands_Strategy,
    RSI_Strategy,
    MACD_Strategy
)
from gui.dca_config import DcaConfigManager

# 로깅 설정
logging.basicConfig(
    level=logging.WARNING,  # INFO 로그 숨김 (결과만 보기)
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("📊 전략 비교 백테스팅 (1년)")
print("=" * 80)

# 1. 데이터 수집
print("\n📊 데이터 로딩 중...")
fetcher = HistoricalDataFetcher()

end_date = datetime.now()
start_date = end_date - timedelta(days=365)

candles = fetcher.fetch_candles(
    symbol='KRW-BTC',
    start_date=start_date,
    end_date=end_date,
    interval='minute1',
    use_cache=True
)

print(f"✅ {len(candles):,}개 캔들 로드 완료")
print(f"   기간: {candles.index[0]} ~ {candles.index[-1]}")

# 2. DCA 설정 로드
dca_manager = DcaConfigManager()
dca_config = dca_manager.load()

# 3. 전략 정의
strategies = [
    {
        'name': 'Bollinger Bands',
        'instance': BollingerBands_Strategy(period=20, std_dev=2.5),
        'description': '볼린저 밴드 (보수적)'
    },
    {
        'name': 'Bollinger Bands (Aggressive)',
        'instance': BollingerBands_Strategy(period=20, std_dev=2.0),
        'description': '볼린저 밴드 (공격적)'
    },
    {
        'name': 'RSI',
        'instance': RSI_Strategy(period=14, oversold=30, overbought=70),
        'description': 'RSI 과매수/과매도'
    },
    {
        'name': 'RSI (Aggressive)',
        'instance': RSI_Strategy(period=14, oversold=40, overbought=60),
        'description': 'RSI 과매수/과매도 (공격적)'
    },
    {
        'name': 'MACD',
        'instance': MACD_Strategy(fast_period=12, slow_period=26, signal_period=9),
        'description': 'MACD 크로스오버'
    }
]

# 4. 백테스팅 실행
print("\n" + "=" * 80)
print("🔬 전략별 백테스팅 실행 중...")
print("=" * 80)

results = []

for i, strategy_info in enumerate(strategies, 1):
    print(f"\n[{i}/{len(strategies)}] {strategy_info['name']} - {strategy_info['description']}")
    print("-" * 80)
    
    backtester = DcaBacktester(
        strategy=strategy_info['instance'],
        dca_config=dca_config,
        initial_capital=1000000,
        fee_rate=0.0005,
        slippage=0.001
    )
    
    result = backtester.run(candles, 'KRW-BTC')
    
    results.append({
        'name': strategy_info['name'],
        'description': strategy_info['description'],
        'result': result
    })
    
    # 간단한 결과 출력
    print(f"  수익률: {result.total_return:+.2f}%")
    print(f"  MDD: {result.max_drawdown:.2f}%")
    print(f"  총 거래: {result.total_trades}회")
    print(f"  승률: {result.win_rate:.1f}%")

# 5. 결과 비교
print("\n" + "=" * 80)
print("📊 전략 비교 결과")
print("=" * 80)

# 테이블 헤더
print(f"\n{'전략':<30} {'수익률':>10} {'MDD':>8} {'거래수':>8} {'승률':>8} {'샤프':>8}")
print("-" * 80)

# 각 전략 결과
for res in results:
    r = res['result']
    print(f"{res['name']:<30} {r.total_return:>9.2f}% {r.max_drawdown:>7.2f}% "
          f"{r.total_trades:>7}회 {r.win_rate:>7.1f}% {r.sharpe_ratio:>8.2f}")

# 6. 최고 성과 전략
print("\n" + "=" * 80)
print("🏆 최고 성과 전략")
print("=" * 80)

best_return = max(results, key=lambda x: x['result'].total_return)
best_sharpe = max(results, key=lambda x: x['result'].sharpe_ratio if x['result'].sharpe_ratio > -100 else -999)
best_winrate = max(results, key=lambda x: x['result'].win_rate)
lowest_mdd = min(results, key=lambda x: x['result'].max_drawdown)
most_trades = max(results, key=lambda x: x['result'].total_trades)

print(f"\n최고 수익률: {best_return['name']}")
print(f"  수익률: {best_return['result'].total_return:+.2f}%")
print(f"  설명: {best_return['description']}")

print(f"\n최고 샤프 비율: {best_sharpe['name']}")
print(f"  샤프 비율: {best_sharpe['result'].sharpe_ratio:.2f}")

print(f"\n최고 승률: {best_winrate['name']}")
print(f"  승률: {best_winrate['result'].win_rate:.1f}%")

print(f"\n최저 MDD: {lowest_mdd['name']}")
print(f"  MDD: {lowest_mdd['result'].max_drawdown:.2f}%")

print(f"\n가장 활발한 거래: {most_trades['name']}")
print(f"  총 거래: {most_trades['result'].total_trades}회")

# 7. 종합 평가
print("\n" + "=" * 80)
print("💡 종합 평가")
print("=" * 80)

print("\n1. 거래 빈도 분석:")
for res in sorted(results, key=lambda x: x['result'].total_trades, reverse=True):
    r = res['result']
    days_per_trade = 365 / r.total_trades if r.total_trades > 0 else 365
    print(f"   {res['name']:<30} {r.total_trades:>3}회 (평균 {days_per_trade:.1f}일/거래)")

print("\n2. 위험 대비 수익:")
for res in results:
    r = res['result']
    if r.max_drawdown > 0:
        risk_reward = r.total_return / r.max_drawdown
        print(f"   {res['name']:<30} {risk_reward:>6.2f} (수익률/MDD)")

print("\n" + "=" * 80)
print("✅ 전략 비교 완료!")
print("=" * 80)
