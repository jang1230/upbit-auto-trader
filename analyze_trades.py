"""
거래 내역 상세 분석 스크립트
"""

import logging
from datetime import datetime, timedelta
from core.historical_data import HistoricalDataFetcher
from core.dca_backtester import DcaBacktester
from core.strategies import BollingerBands_Strategy
from gui.dca_config import DcaConfigManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("🔍 거래 내역 상세 분석")
print("=" * 80)

# 데이터 수집
fetcher = HistoricalDataFetcher()
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

candles = fetcher.fetch_candles(
    symbol='KRW-BTC',
    start_date=start_date,
    end_date=end_date,
    interval='minute1',
    use_cache=True
)

# 전략 초기화
strategy = BollingerBands_Strategy(period=20, std_dev=2.5)

# DCA 설정
dca_manager = DcaConfigManager()
dca_config = dca_manager.load()

# 백테스팅 실행
backtester = DcaBacktester(
    strategy=strategy,
    dca_config=dca_config,
    initial_capital=1000000,
    fee_rate=0.0005,
    slippage=0.001
)

result = backtester.run(candles, 'KRW-BTC')

print("\n" + "=" * 80)
print("📊 거래 통계")
print("=" * 80)
print(f"총 거래 수: {result.total_trades}회")
print(f"승리 거래: {result.winning_trades}회")
print(f"손실 거래: {result.losing_trades}회")
print(f"승률: {result.win_rate:.1f}%")

print("\n" + "=" * 80)
print("📝 전체 거래 내역 (상세)")
print("=" * 80)

for i, trade in enumerate(result.trades, 1):
    print(f"\n{'='*60}")
    print(f"거래 #{i}")
    print(f"{'='*60}")
    print(f"시간: {trade['timestamp']}")
    print(f"유형: {'🔴 매수' if trade['side'] == 'buy' else '🔵 매도'}")
    print(f"가격: {trade['price']:,.0f}원")
    print(f"수량: {trade['amount']:.8f} BTC")
    print(f"금액: {trade['price'] * trade['amount']:,.0f}원")
    print(f"수수료: {trade['fee']:,.0f}원")
    print(f"잔고: {trade['balance']:,.0f}원")
    print(f"포지션: {trade['position']:.8f} BTC")
    print(f"사유: {trade.get('reason', 'N/A')}")

# 매수/매도 거래 분리 분석
buy_trades = [t for t in result.trades if t['side'] == 'buy']
sell_trades = [t for t in result.trades if t['side'] == 'sell']

print("\n" + "=" * 80)
print("🔍 거래 유형별 분석")
print("=" * 80)
print(f"매수 거래: {len(buy_trades)}회")
print(f"매도 거래: {len(sell_trades)}회")
print(f"총 거래: {len(result.trades)}회")

print("\n" + "=" * 80)
print("❓ 승/패 집계 검증")
print("=" * 80)

# 매수-매도 쌍 분석
if len(buy_trades) > 0 and len(sell_trades) > 0:
    print(f"\n매수 평균가: {sum(t['price'] for t in buy_trades) / len(buy_trades):,.0f}원")
    print(f"매도 평균가: {sum(t['price'] for t in sell_trades) / len(sell_trades):,.0f}원")
    
    # 각 매도 거래의 손익 계산 (추정)
    print("\n매도 거래별 예상 손익:")
    for i, sell_trade in enumerate(sell_trades, 1):
        # 직전 매수 거래 찾기
        prev_buys = [t for t in buy_trades if t['timestamp'] < sell_trade['timestamp']]
        if prev_buys:
            last_buy = prev_buys[-1]
            profit = (sell_trade['price'] - last_buy['price']) * sell_trade['amount']
            print(f"  매도 #{i}: {profit:+,.0f}원 "
                  f"(매수가 {last_buy['price']:,.0f} → 매도가 {sell_trade['price']:,.0f})")

print("\n" + "=" * 80)
