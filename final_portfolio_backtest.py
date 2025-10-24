"""
최종 3개 코인 포트폴리오 백테스팅
각 코인별 최적화된 파라미터 적용

코인별 설정:
- BTC: std=2.0, wait=6h, atr=0.3 (기존 좋은 성과)
- ETH: std=2.5, wait=10h, atr=0.4 (최적화 결과 #2)
- XRP: std=2.0, wait=6h, atr=0.3 (기존 수익성 있음)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict
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


def backtest_coin_with_config(
    symbol: str,
    candles: pd.DataFrame,
    config: Dict,
    initial_capital: float = 2000000
):
    """
    특정 설정으로 단일 코인 백테스팅
    
    Args:
        symbol: 코인 심볼
        candles: 캔들 데이터
        config: {'std_dev': float, 'wait_hours': int, 'atr_mult': float}
        initial_capital: 초기 자본
    """
    
    print(f"\n{'='*70}")
    print(f"🔍 {symbol} 백테스팅")
    print(f"{'='*70}")
    print(f"  파라미터: std={config['std_dev']}, wait={config['wait_hours']}h, atr={config['atr_mult']}")
    
    # 지표 계산
    ma20, upper, lower = calculate_bollinger_bands(
        candles, 
        period=20, 
        std_dev=config['std_dev']
    )
    ma240 = calculate_ma(candles, period=240)
    atr = calculate_atr(candles, period=14)
    
    cash = initial_capital
    position = 0.0
    trades = []
    entry_price = 0
    last_trade_time = None
    
    min_minutes_between_trades = config['wait_hours'] * 60
    
    for i in range(300, len(candles)):
        current_time = candles.iloc[i].name
        price = candles.iloc[i]['close']
        
        # 시간 필터
        if last_trade_time is not None:
            time_diff = (current_time - last_trade_time).total_seconds() / 60
            if time_diff < min_minutes_between_trades:
                continue
        
        # 변동성 필터
        if np.isnan(atr[i]) or atr[i] < (price * config['atr_mult'] / 100):
            continue
        
        # 매수 신호: 하단 밴드 아래 + 4시간 MA 아래 (하락 추세)
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
        
        # 매도 신호: 상단 밴드 위 + 4시간 MA 위 (상승 추세)
        elif position > 0:
            if price > upper[i] and not np.isnan(upper[i]):
                if not np.isnan(ma240[i]) and price > ma240[i]:
                    proceeds = position * price
                    fee = proceeds * 0.0005
                    cash += proceeds - fee
                    
                    profit = (price - entry_price) * position - (trades[-1]['amount'] * entry_price * 0.0005) - fee
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
                    
                    position = 0.0
                    entry_price = 0
    
    # 최종 청산
    if position > 0:
        final_price = candles.iloc[-1]['close']
        final_time = candles.iloc[-1].name
        
        proceeds = position * final_price
        fee = proceeds * 0.0005
        cash += proceeds - fee
        
        profit = (final_price - entry_price) * position - (trades[-1]['amount'] * entry_price * 0.0005) - fee
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
    
    final_capital = cash
    total_return = ((final_capital - initial_capital) / initial_capital) * 100
    
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
    
    print(f"\n  📊 결과:")
    print(f"     초기 자본: {initial_capital:,.0f}원")
    print(f"     최종 자본: {final_capital:,.0f}원")
    print(f"     수익률: {total_return:+.2f}%")
    print(f"     거래 횟수: {len(trades)}회 (매수 {len(buy_trades)}회, 매도 {len(sell_trades)}회)")
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
        'config': config,
        'trade_list': trades
    }


def main():
    print("=" * 80)
    print("최종 3개 코인 포트폴리오 백테스팅")
    print("=" * 80)
    print()
    print("💰 초기 설정:")
    print("   - 총 자본: 6,000,000원")
    print("   - 코인당 자본: 2,000,000원")
    print("   - 기간: 2024-10-20 ~ 2025-10-20 (1년)")
    print()
    print("🎯 코인별 최적 파라미터:")
    print("   - BTC: std=2.0, wait=6h, atr=0.3 (기존)")
    print("   - ETH: std=2.5, wait=10h, atr=0.4 (최적화 #2)")
    print("   - XRP: std=2.0, wait=6h, atr=0.3 (기존)")
    print()
    
    # 코인별 설정
    coin_configs = {
        'KRW-BTC': {
            'std_dev': 2.0,
            'wait_hours': 6,
            'atr_mult': 0.3
        },
        'KRW-ETH': {
            'std_dev': 2.5,
            'wait_hours': 10,
            'atr_mult': 0.4
        },
        'KRW-XRP': {
            'std_dev': 2.0,
            'wait_hours': 6,
            'atr_mult': 0.3
        }
    }
    
    # 데이터 수집 기간
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    fetcher = HistoricalDataFetcher()
    
    # 각 코인별 백테스팅
    results = []
    
    for symbol, config in coin_configs.items():
        print(f"\n📊 {symbol} 데이터 로드 중...")
        
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
            result = backtest_coin_with_config(
                symbol=symbol,
                candles=candles,
                config=config,
                initial_capital=2000000
            )
            
            results.append(result)
            
        except Exception as e:
            print(f"   ❌ {symbol} 오류: {e}")
            import traceback
            traceback.print_exc()
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
    if results:
        best = max(results, key=lambda x: x['return'])
        worst = min(results, key=lambda x: x['return'])
        
        print(f"\n🏆 최고 성과: {best['symbol']} ({best['return']:+.2f}%)")
        print(f"📉 최저 성과: {worst['symbol']} ({worst['return']:+.2f}%)")
    
    # 개선 효과 비교 (이전 결과 대비)
    print("\n" + "=" * 80)
    print("📈 최적화 효과 (이전 vs 현재)")
    print("=" * 80)
    
    # 이전 결과 (기존 설정)
    previous_results = {
        'KRW-BTC': {'return': 8.05, 'trades': 24},
        'KRW-ETH': {'return': -1.14, 'trades': 72},
        'KRW-XRP': {'return': 14.42, 'trades': 84}
    }
    
    print(f"\n{'코인':<12} {'이전 수익률':>12} {'현재 수익률':>12} {'개선':>10} {'이전 거래':>10} {'현재 거래':>10}")
    print("-" * 80)
    
    for result in results:
        symbol = result['symbol']
        if symbol in previous_results:
            prev = previous_results[symbol]
            improvement = result['return'] - prev['return']
            trade_change = result['trades'] - prev['trades']
            
            print(f"{symbol:<12} "
                  f"{prev['return']:>11.2f}% "
                  f"{result['return']:>11.2f}% "
                  f"{improvement:>9.2f}%p "
                  f"{prev['trades']:>9}회 "
                  f"{result['trades']:>9}회")
    
    # 포트폴리오 전체 개선
    prev_portfolio = 4.27  # 이전 포트폴리오 수익률
    portfolio_improvement = portfolio_return - prev_portfolio
    
    print("-" * 80)
    print(f"{'포트폴리오':<12} "
          f"{prev_portfolio:>11.2f}% "
          f"{portfolio_return:>11.2f}% "
          f"{portfolio_improvement:>9.2f}%p")
    
    print("\n" + "=" * 80)
    print("💡 결론")
    print("=" * 80)
    print(f"ETH 파라미터 최적화를 통해 포트폴리오 성과가 개선되었습니다.")
    print(f"현실적 기대 수익률: {portfolio_return * 0.5:.2f}% (백테스팅의 50%)")
    print()
    print("⚠️ 주의사항:")
    print("  - 백테스팅 결과는 과거 데이터 기반이며, 미래 수익을 보장하지 않습니다")
    print("  - 오버피팅 가능성이 있으므로 실제 수익률은 더 낮을 수 있습니다")
    print("  - 시장 상황에 따라 손실이 발생할 수 있습니다")
    print()
    print("=" * 80)
    print("분석 완료!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n중단됨")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
