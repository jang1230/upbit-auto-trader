"""
순수 전략 백테스터 (최적화 버전)
- 전략 신호만 따라 매매
- 성능 최적화: 지표를 미리 계산하여 속도 향상
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
import numpy as np
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


def calculate_bollinger_bands(candles: pd.DataFrame, period: int = 20, std_dev: float = 2.0):
    """볼린저 밴드 계산 (전체 데이터에 대해 한번에)"""
    closes = candles['close'].values
    
    # 이동평균
    ma = pd.Series(closes).rolling(window=period).mean().values
    
    # 표준편차
    std = pd.Series(closes).rolling(window=period).std().values
    
    # 상단/하단 밴드
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    
    return ma, upper, lower


def calculate_rsi(candles: pd.DataFrame, period: int = 14):
    """RSI 계산 (전체 데이터에 대해 한번에)"""
    closes = pd.Series(candles['close'].values)
    
    # 가격 변화
    delta = closes.diff()
    
    # 상승/하락 분리
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # 평균 계산
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # RSI 계산
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.values


def calculate_macd(candles: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD 계산 (전체 데이터에 대해 한번에)"""
    closes = pd.Series(candles['close'].values)
    
    # EMA 계산
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    
    # MACD 라인
    macd_line = ema_fast - ema_slow
    
    # 시그널 라인
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    
    # 히스토그램
    histogram = macd_line - signal_line
    
    return macd_line.values, signal_line.values, histogram.values


def backtest_bollinger(candles: pd.DataFrame, std_dev: float = 2.0, initial_capital: float = 1000000):
    """볼린저 밴드 전략 백테스팅"""
    print(f"\n🔍 볼린저 밴드 전략 (std_dev={std_dev}) 백테스팅 중...")
    
    # 지표 계산
    ma, upper, lower = calculate_bollinger_bands(candles, period=20, std_dev=std_dev)
    
    cash = initial_capital
    position = 0.0
    trades = []
    entry_price = 0
    
    for i in range(50, len(candles)):  # 최소 50개 캔들 이후부터
        price = candles.iloc[i]['close']
        
        # 매수 신호: 가격이 하단 밴드 아래
        if position == 0 and price < lower[i] and not np.isnan(lower[i]):
            if cash > 0:
                amount = (cash * 0.99) / price
                fee = amount * price * 0.0005
                cost = amount * price + fee
                
                position = amount
                cash -= cost
                entry_price = price
                
                trades.append({
                    'type': 'buy',
                    'price': price,
                    'amount': amount,
                    'timestamp': candles.iloc[i].name
                })
        
        # 매도 신호: 가격이 상단 밴드 위
        elif position > 0 and price > upper[i] and not np.isnan(upper[i]):
            proceeds = position * price
            fee = proceeds * 0.0005
            cash += proceeds - fee
            
            profit = (price - entry_price) * position - fee
            
            trades.append({
                'type': 'sell',
                'price': price,
                'amount': position,
                'profit': profit,
                'timestamp': candles.iloc[i].name
            })
            
            position = 0.0
            entry_price = 0
    
    # 최종 청산
    if position > 0:
        final_price = candles.iloc[-1]['close']
        proceeds = position * final_price
        fee = proceeds * 0.0005
        cash += proceeds - fee
        
        profit = (final_price - entry_price) * position - fee
        
        trades.append({
            'type': 'sell',
            'price': final_price,
            'amount': position,
            'profit': profit,
            'timestamp': candles.iloc[-1].name
        })
    
    final_capital = cash
    total_return = ((final_capital - initial_capital) / initial_capital) * 100
    
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
    
    return {
        'strategy': f'BB (std={std_dev})',
        'return': total_return,
        'trades': len(trades),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'win_rate': (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0,
        'final_capital': final_capital
    }


def backtest_rsi(candles: pd.DataFrame, oversold: int = 30, overbought: int = 70, initial_capital: float = 1000000):
    """RSI 전략 백테스팅"""
    print(f"\n🔍 RSI 전략 (oversold={oversold}, overbought={overbought}) 백테스팅 중...")
    
    # RSI 계산
    rsi = calculate_rsi(candles, period=14)
    
    cash = initial_capital
    position = 0.0
    trades = []
    entry_price = 0
    
    for i in range(50, len(candles)):
        price = candles.iloc[i]['close']
        
        # 매수 신호: RSI < oversold
        if position == 0 and rsi[i] < oversold and not np.isnan(rsi[i]):
            if cash > 0:
                amount = (cash * 0.99) / price
                fee = amount * price * 0.0005
                cost = amount * price + fee
                
                position = amount
                cash -= cost
                entry_price = price
                
                trades.append({
                    'type': 'buy',
                    'price': price,
                    'amount': amount,
                    'timestamp': candles.iloc[i].name
                })
        
        # 매도 신호: RSI > overbought
        elif position > 0 and rsi[i] > overbought and not np.isnan(rsi[i]):
            proceeds = position * price
            fee = proceeds * 0.0005
            cash += proceeds - fee
            
            profit = (price - entry_price) * position - fee
            
            trades.append({
                'type': 'sell',
                'price': price,
                'amount': position,
                'profit': profit,
                'timestamp': candles.iloc[i].name
            })
            
            position = 0.0
            entry_price = 0
    
    # 최종 청산
    if position > 0:
        final_price = candles.iloc[-1]['close']
        proceeds = position * final_price
        fee = proceeds * 0.0005
        cash += proceeds - fee
        
        profit = (final_price - entry_price) * position - fee
        
        trades.append({
            'type': 'sell',
            'price': final_price,
            'amount': position,
            'profit': profit,
            'timestamp': candles.iloc[-1].name
        })
    
    final_capital = cash
    total_return = ((final_capital - initial_capital) / initial_capital) * 100
    
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
    
    return {
        'strategy': f'RSI ({oversold}/{overbought})',
        'return': total_return,
        'trades': len(trades),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'win_rate': (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0,
        'final_capital': final_capital
    }


def backtest_macd(candles: pd.DataFrame, initial_capital: float = 1000000):
    """MACD 전략 백테스팅"""
    print(f"\n🔍 MACD 전략 백테스팅 중...")
    
    # MACD 계산
    macd_line, signal_line, histogram = calculate_macd(candles)
    
    cash = initial_capital
    position = 0.0
    trades = []
    entry_price = 0
    
    for i in range(50, len(candles)):
        price = candles.iloc[i]['close']
        
        # 매수 신호: MACD가 시그널선 상향 돌파
        if position == 0 and i > 0:
            if macd_line[i-1] <= signal_line[i-1] and macd_line[i] > signal_line[i]:
                if not np.isnan(macd_line[i]) and cash > 0:
                    amount = (cash * 0.99) / price
                    fee = amount * price * 0.0005
                    cost = amount * price + fee
                    
                    position = amount
                    cash -= cost
                    entry_price = price
                    
                    trades.append({
                        'type': 'buy',
                        'price': price,
                        'amount': amount,
                        'timestamp': candles.iloc[i].name
                    })
        
        # 매도 신호: MACD가 시그널선 하향 돌파
        elif position > 0 and i > 0:
            if macd_line[i-1] >= signal_line[i-1] and macd_line[i] < signal_line[i]:
                if not np.isnan(macd_line[i]):
                    proceeds = position * price
                    fee = proceeds * 0.0005
                    cash += proceeds - fee
                    
                    profit = (price - entry_price) * position - fee
                    
                    trades.append({
                        'type': 'sell',
                        'price': price,
                        'amount': position,
                        'profit': profit,
                        'timestamp': candles.iloc[i].name
                    })
                    
                    position = 0.0
                    entry_price = 0
    
    # 최종 청산
    if position > 0:
        final_price = candles.iloc[-1]['close']
        proceeds = position * final_price
        fee = proceeds * 0.0005
        cash += proceeds - fee
        
        profit = (final_price - entry_price) * position - fee
        
        trades.append({
            'type': 'sell',
            'price': final_price,
            'amount': position,
            'profit': profit,
            'timestamp': candles.iloc[-1].name
        })
    
    final_capital = cash
    total_return = ((final_capital - initial_capital) / initial_capital) * 100
    
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
    
    return {
        'strategy': 'MACD (12/26/9)',
        'return': total_return,
        'trades': len(trades),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'win_rate': (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0,
        'final_capital': final_capital
    }


def main():
    print("=" * 80)
    print("순수 전략 백테스팅 (DCA 없이)")
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
    
    # 전략별 백테스팅
    results = []
    
    # 1. 볼린저 밴드 (3가지 설정)
    results.append(backtest_bollinger(candles, std_dev=2.5))
    results.append(backtest_bollinger(candles, std_dev=2.0))
    results.append(backtest_bollinger(candles, std_dev=1.5))
    
    # 2. RSI (2가지 설정)
    results.append(backtest_rsi(candles, oversold=30, overbought=70))
    results.append(backtest_rsi(candles, oversold=40, overbought=60))
    
    # 3. MACD
    results.append(backtest_macd(candles))
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 전략 성능 비교")
    print("=" * 80)
    print(f"{'전략':<25} {'수익률':>10} {'거래수':>8} {'매수':>6} {'매도':>6} {'승률':>8}")
    print("-" * 80)
    
    for result in sorted(results, key=lambda x: x['return'], reverse=True):
        print(f"{result['strategy']:<25} {result['return']:>9.2f}% "
              f"{result['trades']:>7}회 "
              f"{result['buy_count']:>5}회 "
              f"{result['sell_count']:>5}회 "
              f"{result['win_rate']:>7.1f}%")
    
    print("\n" + "=" * 80)
    print("분석 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
