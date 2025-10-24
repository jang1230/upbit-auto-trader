"""
필터링된 전략 백테스터
- 시간 필터: 최소 대기 시간
- 변동성 필터: ATR 기반
- 추세 필터: 이동평균 기반
- 목표: 적정 거래 빈도 (연 10-30회)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
import numpy as np
from core.historical_data import HistoricalDataFetcher

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)


def calculate_atr(candles: pd.DataFrame, period: int = 14):
    """ATR (Average True Range) 계산"""
    high = candles['high'].values
    low = candles['low'].values
    close = candles['close'].values
    
    # True Range 계산
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]  # 첫 번째 값은 high-low
    
    # ATR = TR의 이동평균
    atr = pd.Series(tr).rolling(window=period).mean().values
    
    return atr


def calculate_bollinger_bands(candles: pd.DataFrame, period: int = 20, std_dev: float = 3.0):
    """볼린저 밴드 계산"""
    closes = candles['close'].values
    
    ma = pd.Series(closes).rolling(window=period).mean().values
    std = pd.Series(closes).rolling(window=period).std().values
    
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    
    return ma, upper, lower


def calculate_ma(candles: pd.DataFrame, period: int = 240):
    """이동평균 계산 (240분 = 4시간)"""
    closes = candles['close'].values
    ma = pd.Series(closes).rolling(window=period).mean().values
    return ma


def backtest_filtered_bb(
    candles: pd.DataFrame,
    std_dev: float = 3.0,
    min_hours_between_trades: int = 12,
    atr_multiplier: float = 0.5,
    initial_capital: float = 1000000
):
    """필터링된 볼린저 밴드 전략"""
    
    print(f"\n🔍 필터링된 볼린저 밴드 전략 백테스팅")
    print(f"   - std_dev: {std_dev}")
    print(f"   - 최소 대기 시간: {min_hours_between_trades}시간")
    print(f"   - ATR 승수: {atr_multiplier}")
    print()
    
    # 지표 계산
    ma20, upper, lower = calculate_bollinger_bands(candles, period=20, std_dev=std_dev)
    ma240 = calculate_ma(candles, period=240)  # 4시간 이동평균
    atr = calculate_atr(candles, period=14)
    
    cash = initial_capital
    position = 0.0
    trades = []
    entry_price = 0
    last_trade_time = None
    
    min_minutes_between_trades = min_hours_between_trades * 60
    
    for i in range(300, len(candles)):  # 충분한 데이터 이후부터
        current_time = candles.iloc[i].name
        price = candles.iloc[i]['close']
        
        # 시간 필터: 마지막 거래 후 충분한 시간 경과 확인
        if last_trade_time is not None:
            time_diff = (current_time - last_trade_time).total_seconds() / 60
            if time_diff < min_minutes_between_trades:
                continue
        
        # 변동성 필터: ATR이 충분히 높은지 확인
        # (가격의 일정 비율 이상의 변동성)
        if np.isnan(atr[i]) or atr[i] < (price * atr_multiplier / 100):
            continue
        
        # 매수 신호
        if position == 0:
            # 볼린저 밴드 하단 돌파
            if price < lower[i] and not np.isnan(lower[i]):
                # 추세 필터: 4시간 MA 아래에 있어야 함 (하락 추세)
                if not np.isnan(ma240[i]) and price < ma240[i]:
                    if cash > 0:
                        amount = (cash * 0.99) / price
                        fee = amount * price * 0.0005
                        cost = amount * price + fee
                        
                        position = amount
                        cash -= cost
                        entry_price = price
                        last_trade_time = current_time
                        
                        trades.append({
                            'type': 'buy',
                            'price': price,
                            'amount': amount,
                            'timestamp': current_time,
                            'atr': atr[i],
                            'atr_pct': (atr[i] / price) * 100
                        })
                        
                        print(f"✅ 매수: {current_time} | "
                              f"가격: {price:,.0f}원 | "
                              f"ATR: {atr[i]:,.0f} ({(atr[i]/price)*100:.2f}%)")
        
        # 매도 신호
        elif position > 0:
            # 볼린저 밴드 상단 돌파
            if price > upper[i] and not np.isnan(upper[i]):
                # 추세 필터: 4시간 MA 위에 있어야 함 (상승 추세)
                if not np.isnan(ma240[i]) and price > ma240[i]:
                    proceeds = position * price
                    fee = proceeds * 0.0005
                    cash += proceeds - fee
                    
                    profit = (price - entry_price) * position - (amount * entry_price * 0.0005) - fee
                    profit_pct = ((price - entry_price) / entry_price) * 100
                    
                    last_trade_time = current_time
                    
                    trades.append({
                        'type': 'sell',
                        'price': price,
                        'amount': position,
                        'profit': profit,
                        'profit_pct': profit_pct,
                        'timestamp': current_time,
                        'holding_time': (current_time - trades[-1]['timestamp']).total_seconds() / 3600
                    })
                    
                    print(f"✅ 매도: {current_time} | "
                          f"가격: {price:,.0f}원 | "
                          f"수익: {profit:,.0f}원 ({profit_pct:+.2f}%) | "
                          f"보유: {trades[-1]['holding_time']:.1f}시간")
                    
                    position = 0.0
                    entry_price = 0
    
    # 최종 청산
    if position > 0:
        final_price = candles.iloc[-1]['close']
        final_time = candles.iloc[-1].name
        
        proceeds = position * final_price
        fee = proceeds * 0.0005
        cash += proceeds - fee
        
        profit = (final_price - entry_price) * position - (amount * entry_price * 0.0005) - fee
        profit_pct = ((final_price - entry_price) / entry_price) * 100
        
        trades.append({
            'type': 'sell',
            'price': final_price,
            'amount': position,
            'profit': profit,
            'profit_pct': profit_pct,
            'timestamp': final_time,
            'holding_time': (final_time - trades[-1]['timestamp']).total_seconds() / 3600,
            'final_liquidation': True
        })
        
        print(f"🔵 최종 청산: {final_time} | "
              f"가격: {final_price:,.0f}원 | "
              f"수익: {profit:,.0f}원 ({profit_pct:+.2f}%)")
    
    final_capital = cash
    total_return = ((final_capital - initial_capital) / initial_capital) * 100
    
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
    
    # 평균 보유 시간
    avg_holding_time = np.mean([t['holding_time'] for t in sell_trades if 'holding_time' in t])
    
    return {
        'strategy': f'Filtered BB (std={std_dev}, wait={min_hours_between_trades}h)',
        'return': total_return,
        'trades': len(trades),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'win_rate': (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0,
        'final_capital': final_capital,
        'avg_holding_hours': avg_holding_time,
        'trade_list': trades
    }


def test_multiple_configs(candles: pd.DataFrame):
    """여러 설정 테스트"""
    
    configs = [
        # (std_dev, min_hours, atr_multiplier)
        (3.0, 12, 0.5),   # 보수적
        (2.5, 8, 0.4),    # 중간
        (2.0, 6, 0.3),    # 공격적
        (3.5, 24, 0.6),   # 매우 보수적
    ]
    
    results = []
    
    for std_dev, min_hours, atr_mult in configs:
        result = backtest_filtered_bb(
            candles,
            std_dev=std_dev,
            min_hours_between_trades=min_hours,
            atr_multiplier=atr_mult
        )
        results.append(result)
    
    return results


def main():
    print("=" * 80)
    print("필터링된 전략 백테스팅")
    print("=" * 80)
    
    # 데이터 로드
    print("\n📊 1년치 데이터 로딩 중...")
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
    
    print(f"✅ 데이터 로드 완료: {len(candles):,}개 캔들")
    print(f"   기간: {candles.index[0]} ~ {candles.index[-1]}")
    
    # 여러 설정 테스트
    results = test_multiple_configs(candles)
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 전략 성능 비교")
    print("=" * 80)
    print(f"{'전략':<40} {'수익률':>10} {'거래수':>8} {'승률':>8} {'평균보유':>10}")
    print("-" * 80)
    
    for result in sorted(results, key=lambda x: x['return'], reverse=True):
        print(f"{result['strategy']:<40} {result['return']:>9.2f}% "
              f"{result['trades']:>7}회 "
              f"{result['win_rate']:>7.1f}% "
              f"{result['avg_holding_hours']:>9.1f}h")
    
    # 최고 성과 전략의 거래 내역
    best = max(results, key=lambda x: x['return'])
    print("\n" + "=" * 80)
    print(f"🏆 최고 성과: {best['strategy']}")
    print(f"   수익률: {best['return']:.2f}%")
    print(f"   총 거래: {best['trades']}회 (매수 {best['buy_count']}회, 매도 {best['sell_count']}회)")
    print(f"   승률: {best['win_rate']:.1f}%")
    print(f"   평균 보유: {best['avg_holding_hours']:.1f}시간")
    
    # 거래 빈도 분석
    if best['buy_count'] > 0:
        days = (candles.index[-1] - candles.index[0]).days
        trades_per_month = (best['buy_count'] / days) * 30
        print(f"   거래 빈도: 월 {trades_per_month:.1f}회")
    
    print("\n" + "=" * 80)
    print("분석 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
