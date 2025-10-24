"""
ETH 파라미터 최적화 백테스팅

목표: ETH의 거래 횟수를 줄이고 승률을 높여 손실을 수익으로 전환
현재 문제: 72회 거래, 50% 승률, -1.14% 손실
"""

import logging
from datetime import datetime, timedelta
from core.historical_data import HistoricalDataFetcher
import pandas as pd
import numpy as np

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_bollinger_bands(candles, period=20, std_dev=2.0):
    """볼린저 밴드 계산"""
    close = candles['close']
    ma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return ma, upper, lower


def calculate_ma(candles, period=240):
    """이동평균선 계산"""
    return candles['close'].rolling(window=period).mean()


def calculate_atr(candles, period=14):
    """ATR (Average True Range) 계산"""
    high = candles['high']
    low = candles['low']
    close = candles['close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()

    return atr


def backtest_eth_config(
    candles: pd.DataFrame,
    std_dev: float,
    min_hours_between_trades: int,
    atr_multiplier: float,
    initial_capital: float = 2000000
):
    """
    ETH 백테스팅 (단일 설정)
    """
    # 지표 계산
    ma20, upper, lower = calculate_bollinger_bands(candles, period=20, std_dev=std_dev)
    ma240 = calculate_ma(candles, period=240)
    atr = calculate_atr(candles, period=14)

    # 상태 변수
    balance = initial_capital
    position = 0
    trades = []
    last_trade_time = None
    min_minutes_between_trades = min_hours_between_trades * 60

    # 백테스팅 루프
    for i in range(300, len(candles)):
        current_time = candles.index[i]
        price = candles['close'].iloc[i]

        # 시간 필터
        if last_trade_time is not None:
            time_diff = (current_time - last_trade_time).total_seconds() / 60
            if time_diff < min_minutes_between_trades:
                continue

        # 변동성 필터
        if np.isnan(atr.iloc[i]) or atr.iloc[i] < (price * atr_multiplier / 100):
            continue

        # 매수 신호
        if position == 0 and price < lower.iloc[i] and price < ma240.iloc[i]:
            if not np.isnan(lower.iloc[i]) and not np.isnan(ma240.iloc[i]):
                buy_amount = balance * 0.99 / price
                fee = balance * 0.99 * 0.0005

                position = buy_amount
                balance = balance * 0.01
                last_trade_time = current_time

                trades.append({
                    'time': current_time,
                    'type': 'buy',
                    'price': price,
                    'amount': buy_amount,
                    'balance': balance,
                    'position': position
                })

        # 매도 신호
        elif position > 0 and price > upper.iloc[i] and price > ma240.iloc[i]:
            if not np.isnan(upper.iloc[i]) and not np.isnan(ma240.iloc[i]):
                sell_value = position * price
                fee = sell_value * 0.0005

                balance = balance + sell_value - fee
                position = 0
                last_trade_time = current_time

                trades.append({
                    'time': current_time,
                    'type': 'sell',
                    'price': price,
                    'amount': 0,
                    'balance': balance,
                    'position': position
                })

    # 최종 청산
    if position > 0:
        final_price = candles['close'].iloc[-1]
        sell_value = position * final_price
        fee = sell_value * 0.0005
        balance = balance + sell_value - fee
        position = 0

    # 결과 계산
    final_capital = balance
    total_return = ((final_capital - initial_capital) / initial_capital) * 100

    # 승률 계산
    wins = 0
    losses = 0
    for i in range(1, len(trades), 2):
        if i < len(trades):
            buy_price = trades[i-1]['price']
            sell_price = trades[i]['price']
            if sell_price > buy_price:
                wins += 1
            else:
                losses += 1

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    return {
        'std_dev': std_dev,
        'wait_hours': min_hours_between_trades,
        'atr_mult': atr_multiplier,
        'return': total_return,
        'final_capital': final_capital,
        'trades': len(trades),
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate
    }


def main():
    """메인 실행"""
    print("=" * 80)
    print("ETH 파라미터 최적화 백테스팅")
    print("=" * 80)
    print()

    # 1. 데이터 로드
    print("📊 ETH 데이터 로드 중...")
    fetcher = HistoricalDataFetcher()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    candles = fetcher.fetch_candles(
        symbol='KRW-ETH',
        start_date=start_date,
        end_date=end_date,
        interval='minute1',
        use_cache=True
    )

    print(f"✅ {len(candles):,}개 캔들 로드 완료\n")

    # 2. 테스트할 파라미터 조합
    configs = [
        # (std_dev, wait_hours, atr_multiplier, 설명)
        (2.0, 6, 0.3, "현재 설정 (기준선)"),
        (2.0, 12, 0.4, "대기 2배 + 변동성↑"),
        (2.5, 10, 0.4, "밴드 확장 + 대기↑"),
        (2.5, 12, 0.5, "보수적 (추천 1)"),
        (3.0, 12, 0.5, "매우 보수적 (추천 2)"),
        (2.5, 8, 0.3, "밴드만 확장"),
        (2.0, 10, 0.5, "대기↑ + 변동성↑↑"),
    ]

    print("🔬 테스트 시작...\n")
    print("-" * 80)

    # 3. 각 설정 테스트
    results = []

    for std_dev, wait_hours, atr_mult, desc in configs:
        print(f"\n테스트: {desc}")
        print(f"  파라미터: std={std_dev}, wait={wait_hours}h, atr={atr_mult}")

        result = backtest_eth_config(
            candles=candles,
            std_dev=std_dev,
            min_hours_between_trades=wait_hours,
            atr_multiplier=atr_mult,
            initial_capital=2000000
        )

        result['description'] = desc
        results.append(result)

        print(f"  결과: {result['return']:+.2f}% | "
              f"거래 {result['trades']}회 | "
              f"승률 {result['win_rate']:.1f}%")

    print("\n" + "=" * 80)
    print("📊 결과 요약")
    print("=" * 80)
    print()

    # 4. 결과 정렬 및 출력
    results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)

    print(f"{'순위':<4} {'설명':<25} {'수익률':<10} {'거래수':<8} {'승률':<8} {'최종자본':<12}")
    print("-" * 80)

    for rank, r in enumerate(results_sorted, 1):
        emoji = "🏆" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "

        print(f"{emoji}{rank:<3} {r['description']:<25} "
              f"{r['return']:>+7.2f}% "
              f"{r['trades']:>6}회 "
              f"{r['win_rate']:>6.1f}% "
              f"{r['final_capital']:>10,.0f}원")

    # 5. 최적 설정 추출
    best = results_sorted[0]

    print("\n" + "=" * 80)
    print("🎯 최적 설정")
    print("=" * 80)
    print()
    print(f"설명: {best['description']}")
    print(f"파라미터:")
    print(f"  - std_dev: {best['std_dev']}")
    print(f"  - wait_hours: {best['wait_hours']}")
    print(f"  - atr_multiplier: {best['atr_mult']}")
    print()
    print(f"성과:")
    print(f"  - 수익률: {best['return']:+.2f}%")
    print(f"  - 거래 횟수: {best['trades']}회")
    print(f"  - 승률: {best['win_rate']:.1f}%")
    print(f"  - 최종 자본: {best['final_capital']:,.0f}원")
    print()

    # 6. 현재 vs 최적 비교
    current = [r for r in results if "현재 설정" in r['description']][0]

    print("=" * 80)
    print("📈 개선 효과")
    print("=" * 80)
    print()
    print(f"{'항목':<15} {'현재':<15} {'최적':<15} {'개선':<15}")
    print("-" * 80)
    print(f"{'수익률':<15} {current['return']:>+7.2f}% {best['return']:>+10.2f}% "
          f"{best['return']-current['return']:>+10.2f}%p")
    print(f"{'거래 횟수':<15} {current['trades']:>7}회 {best['trades']:>10}회 "
          f"{best['trades']-current['trades']:>+10}회")
    print(f"{'승률':<15} {current['win_rate']:>7.1f}% {best['win_rate']:>10.1f}% "
          f"{best['win_rate']-current['win_rate']:>+10.1f}%p")
    print(f"{'최종 자본':<15} {current['final_capital']:>10,.0f}원 {best['final_capital']:>13,.0f}원 "
          f"{best['final_capital']-current['final_capital']:>+10,.0f}원")

    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n중단됨")
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
