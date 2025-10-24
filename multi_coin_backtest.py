"""
다중 코인 백테스팅
- 여러 코인에 분산 투자 시뮬레이션
- 포트폴리오 전체 성과 분석
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
    """ATR 계산"""
    high = candles['high'].values
    low = candles['low'].values
    close = candles['close'].values
    
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]
    
    atr = pd.Series(tr).rolling(window=period).mean().values
    return atr


def calculate_bollinger_bands(candles: pd.DataFrame, period: int = 20, std_dev: float = 2.0):
    """볼린저 밴드 계산"""
    closes = candles['close'].values
    ma = pd.Series(closes).rolling(window=period).mean().values
    std = pd.Series(closes).rolling(window=period).std().values
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return ma, upper, lower


def calculate_ma(candles: pd.DataFrame, period: int = 240):
    """이동평균 계산"""
    closes = candles['close'].values
    ma = pd.Series(closes).rolling(window=period).mean().values
    return ma


def backtest_single_coin(
    symbol: str,
    candles: pd.DataFrame,
    std_dev: float = 2.0,
    min_hours_between_trades: int = 6,
    atr_multiplier: float = 0.3,
    initial_capital: float = 2000000
):
    """단일 코인 백테스팅"""
    
    print(f"\n{'='*60}")
    print(f"🔍 {symbol} 백테스팅")
    print(f"{'='*60}")
    
    # 지표 계산
    ma20, upper, lower = calculate_bollinger_bands(candles, period=20, std_dev=std_dev)
    ma240 = calculate_ma(candles, period=240)
    atr = calculate_atr(candles, period=14)
    
    cash = initial_capital
    position = 0.0
    trades = []
    entry_price = 0
    last_trade_time = None
    
    min_minutes_between_trades = min_hours_between_trades * 60
    
    for i in range(300, len(candles)):
        current_time = candles.iloc[i].name
        price = candles.iloc[i]['close']
        
        # 시간 필터
        if last_trade_time is not None:
            time_diff = (current_time - last_trade_time).total_seconds() / 60
            if time_diff < min_minutes_between_trades:
                continue
        
        # 변동성 필터
        if np.isnan(atr[i]) or atr[i] < (price * atr_multiplier / 100):
            continue
        
        # 매수 신호
        if position == 0:
            if price < lower[i] and not np.isnan(lower[i]):
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
                            'timestamp': current_time
                        })
                        
                        print(f"  ✅ 매수: {current_time.strftime('%Y-%m-%d %H:%M')} | {price:,.0f}원")
        
        # 매도 신호
        elif position > 0:
            if price > upper[i] and not np.isnan(upper[i]):
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
                        'timestamp': current_time
                    })
                    
                    print(f"  ✅ 매도: {current_time.strftime('%Y-%m-%d %H:%M')} | {price:,.0f}원 | {profit_pct:+.2f}%")
                    
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
            'final_liquidation': True
        })
        
        print(f"  🔵 최종 청산: {final_time.strftime('%Y-%m-%d %H:%M')} | {final_price:,.0f}원 | {profit_pct:+.2f}%")
    
    final_capital = cash
    total_return = ((final_capital - initial_capital) / initial_capital) * 100
    
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
    
    print(f"\n  📊 결과:")
    print(f"     수익률: {total_return:+.2f}%")
    print(f"     최종 자본: {final_capital:,.0f}원")
    print(f"     거래: {len(trades)}회 (매수 {len(buy_trades)}회, 매도 {len(sell_trades)}회)")
    if sell_trades:
        print(f"     승률: {len(winning_trades)/len(sell_trades)*100:.1f}%")
    
    return {
        'symbol': symbol,
        'initial_capital': initial_capital,
        'final_capital': final_capital,
        'return': total_return,
        'trades': len(trades),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'win_rate': (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0,
        'trade_list': trades
    }


def main():
    print("=" * 80)
    print("다중 코인 포트폴리오 백테스팅")
    print("=" * 80)
    print()
    print("💰 초기 설정:")
    print("   - 총 자본: 10,000,000원")
    print("   - 코인당 자본: 2,000,000원")
    print("   - 전략: 필터링된 볼린저 밴드 (std=2.0, wait=6h)")
    print()
    
    # 테스트할 코인
    symbols = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL', 'KRW-ADA']
    
    # 데이터 수집 기간
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    fetcher = HistoricalDataFetcher()
    
    # 각 코인별 백테스팅
    results = []
    
    for symbol in symbols:
        print(f"\n📊 {symbol} 데이터 수집 중...")
        
        try:
            candles = fetcher.fetch_candles(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval='minute1',
                use_cache=True
            )
            
            print(f"   ✅ {len(candles):,}개 캔들 로드 완료")
            
            # 백테스팅 실행
            result = backtest_single_coin(
                symbol=symbol,
                candles=candles,
                std_dev=2.0,
                min_hours_between_trades=6,
                atr_multiplier=0.3,
                initial_capital=2000000
            )
            
            results.append(result)
            
        except Exception as e:
            print(f"   ❌ {symbol} 오류: {e}")
            continue
    
    # 포트폴리오 전체 분석
    print("\n" + "=" * 80)
    print("📊 포트폴리오 전체 분석")
    print("=" * 80)
    
    # 개별 코인 성과
    print(f"\n{'코인':<12} {'초기자본':>15} {'최종자본':>15} {'수익률':>10} {'거래수':>8} {'승률':>8}")
    print("-" * 80)
    
    total_initial = 0
    total_final = 0
    total_trades = 0
    
    for result in results:
        total_initial += result['initial_capital']
        total_final += result['final_capital']
        total_trades += result['trades']
        
        print(f"{result['symbol']:<12} "
              f"{result['initial_capital']:>14,}원 "
              f"{result['final_capital']:>14,}원 "
              f"{result['return']:>9.2f}% "
              f"{result['trades']:>7}회 "
              f"{result['win_rate']:>7.1f}%")
    
    # 전체 포트폴리오 성과
    portfolio_return = ((total_final - total_initial) / total_initial) * 100
    
    print("-" * 80)
    print(f"{'포트폴리오':<12} "
          f"{total_initial:>14,}원 "
          f"{total_final:>14,}원 "
          f"{portfolio_return:>9.2f}% "
          f"{total_trades:>7}회")
    
    print("\n" + "=" * 80)
    print("🎯 종합 평가")
    print("=" * 80)
    print(f"총 투자금: {total_initial:,}원")
    print(f"최종 자산: {total_final:,}원")
    print(f"순이익: {total_final - total_initial:+,}원")
    print(f"포트폴리오 수익률: {portfolio_return:+.2f}%")
    print(f"총 거래 수: {total_trades}회")
    
    # 월 평균 거래 빈도
    days = 365
    monthly_trades = (total_trades / days) * 30
    print(f"월 평균 거래: {monthly_trades:.1f}회")
    
    # 최고/최저 성과 코인
    best = max(results, key=lambda x: x['return'])
    worst = min(results, key=lambda x: x['return'])
    
    print(f"\n🏆 최고 성과: {best['symbol']} ({best['return']:+.2f}%)")
    print(f"📉 최저 성과: {worst['symbol']} ({worst['return']:+.2f}%)")
    
    print("\n" + "=" * 80)
    print("분석 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
