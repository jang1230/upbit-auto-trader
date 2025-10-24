"""
전략별 실제 신호 발생 시점 디버깅
"""

import logging
from datetime import datetime, timedelta
from core.historical_data import HistoricalDataFetcher
from core.strategies import (
    BollingerBands_Strategy,
    RSI_Strategy,
    MACD_Strategy
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

print("=" * 80)
print("🔍 전략별 신호 발생 시점 분석")
print("=" * 80)

# 데이터 로딩
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

print(f"\n데이터: {len(candles):,}개 캔들")
print(f"기간: {candles.index[0]} ~ {candles.index[-1]}")

# 전략 정의
strategies = [
    ('BB (std=2.5)', BollingerBands_Strategy(period=20, std_dev=2.5)),
    ('BB (std=2.0)', BollingerBands_Strategy(period=20, std_dev=2.0)),
    ('RSI (30/70)', RSI_Strategy(period=14, oversold=30, overbought=70)),
    ('RSI (40/60)', RSI_Strategy(period=14, oversold=40, overbought=60)),
    ('MACD', MACD_Strategy(fast_period=12, slow_period=26, signal_period=9))
]

# 각 전략의 신호 수집
for name, strategy in strategies:
    print(f"\n{'=' * 80}")
    print(f"전략: {name}")
    print(f"{'=' * 80}")
    
    signals = []
    
    # 캔들 데이터를 순회하면서 신호 확인
    for i in range(len(candles)):
        current_candles = candles.iloc[:i+1]
        
        # 최소 데이터 확인 (MACD는 26+9=35개 필요)
        if len(current_candles) < 50:
            continue
        
        signal = strategy.generate_signal(current_candles)
        
        if signal:
            signals.append({
                'timestamp': current_candles.index[-1],
                'signal': signal,
                'price': current_candles['close'].iloc[-1]
            })
    
    # 신호 출력
    print(f"\n총 신호 수: {len(signals)}개")
    
    if signals:
        buy_signals = [s for s in signals if s['signal'] == 'buy']
        sell_signals = [s for s in signals if s['signal'] == 'sell']
        
        print(f"\n매수 신호: {len(buy_signals)}개")
        for s in buy_signals[:10]:  # 처음 10개만
            print(f"  {s['timestamp']}: {s['price']:,.0f}원")
        if len(buy_signals) > 10:
            print(f"  ... 외 {len(buy_signals) - 10}개")
        
        print(f"\n매도 신호: {len(sell_signals)}개")
        for s in sell_signals[:10]:
            print(f"  {s['timestamp']}: {s['price']:,.0f}원")
        if len(sell_signals) > 10:
            print(f"  ... 외 {len(sell_signals) - 10}개")
    else:
        print("  ⚠️ 신호 없음!")

print("\n" + "=" * 80)
print("✅ 분석 완료")
print("=" * 80)
