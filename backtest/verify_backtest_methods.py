"""
백테스트 방식 검증 스크립트
30일 데이터로 느린 방식 vs 빠른 방식 비교

목적: 벡터화된 빠른 방식이 기존 방식과 동일한 결과를 내는지 검증
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import sys
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategies.binance_multi_signal_strategy import BinanceMultiSignalStrategy
from core.indicators import calculate_rsi, calculate_bollinger_bands, calculate_stochastic


def slow_backtest(df: pd.DataFrame, strategy, exit_tp=5, exit_sl=-3):
    """느린 방식: 매 캔들마다 전체 데이터로 지표 재계산"""
    print(f"\n🐌 느린 방식 백테스트 시작...")
    start_time = time.time()
    
    capital = 1_000_000
    position = 0
    entry_price = 0
    trades = []
    
    for i in range(len(df)):
        current_time = df.index[i]
        current_price = df['close'].iloc[i]
        
        # 매수 시그널 체크 (현재까지의 전체 데이터 사용)
        if position == 0:
            signal_df = df.iloc[:i+1]  # ← 매번 슬라이싱
            signal = strategy.generate_signal(signal_df)  # ← 매번 지표 재계산
            
            if signal == 'buy' and capital > 0:
                position = capital / current_price
                entry_price = current_price
                capital = 0
                trades.append({
                    'entry_time': current_time,
                    'entry_price': entry_price,
                    'entry_index': i
                })
        
        # 매도 체크
        elif position > 0:
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            
            if profit_pct >= exit_tp or profit_pct <= exit_sl:
                capital = position * current_price
                trades[-1]['exit_time'] = current_time
                trades[-1]['exit_price'] = current_price
                trades[-1]['exit_index'] = i
                trades[-1]['profit_pct'] = profit_pct
                position = 0
    
    # 마지막 포지션 정리
    if position > 0:
        final_price = df['close'].iloc[-1]
        capital = position * final_price
        profit_pct = ((final_price - entry_price) / entry_price) * 100
        trades[-1]['exit_time'] = df.index[-1]
        trades[-1]['exit_price'] = final_price
        trades[-1]['exit_index'] = len(df) - 1
        trades[-1]['profit_pct'] = profit_pct
    
    elapsed = time.time() - start_time
    print(f"   ⏱️  소요 시간: {elapsed:.2f}초")
    print(f"   📊 거래 횟수: {len(trades)}회")
    print(f"   💰 최종 자산: {capital:,.0f}원")
    
    return trades, capital, elapsed


def fast_backtest(df: pd.DataFrame, strategy, exit_tp=5, exit_sl=-3):
    """빠른 방식: 전체 지표 한 번 계산 후 시그널만 찾기"""
    print(f"\n🚀 빠른 방식 백테스트 시작...")
    start_time = time.time()
    
    # 1️⃣ 전체 데이터에 대해 지표를 한 번만 계산
    print(f"   📊 지표 계산 중...")
    rsi = calculate_rsi(df['close'], period=14)
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df['close'], period=20, std_dev=2.0)
    stoch_k, stoch_d = calculate_stochastic(df['high'], df['low'], df['close'], k_period=14, d_period=3)
    
    # 2️⃣ 매수 시그널 생성 (벡터 연산)
    rsi_signal = rsi < 40.0
    distance_from_lower = ((df['close'] - bb_lower) / bb_lower) * 100
    bb_signal = distance_from_lower <= 1.0
    stoch_warning = stoch_k > 80.0
    
    # OR 조건: 하나라도 True이고 Stoch 경고 없으면 매수
    buy_signals = (rsi_signal | bb_signal) & ~stoch_warning
    
    # 3️⃣ 시그널 기반 매매 시뮬레이션
    print(f"   🔄 매매 시뮬레이션 중...")
    capital = 1_000_000
    position = 0
    entry_price = 0
    trades = []
    
    for i in range(len(df)):
        current_time = df.index[i]
        current_price = df['close'].iloc[i]
        
        # 매수
        if position == 0 and buy_signals.iloc[i] and capital > 0:
            position = capital / current_price
            entry_price = current_price
            capital = 0
            trades.append({
                'entry_time': current_time,
                'entry_price': entry_price,
                'entry_index': i
            })
        
        # 매도
        elif position > 0:
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            
            if profit_pct >= exit_tp or profit_pct <= exit_sl:
                capital = position * current_price
                trades[-1]['exit_time'] = current_time
                trades[-1]['exit_price'] = current_price
                trades[-1]['exit_index'] = i
                trades[-1]['profit_pct'] = profit_pct
                position = 0
    
    # 마지막 포지션 정리
    if position > 0:
        final_price = df['close'].iloc[-1]
        capital = position * final_price
        profit_pct = ((final_price - entry_price) / entry_price) * 100
        trades[-1]['exit_time'] = df.index[-1]
        trades[-1]['exit_price'] = final_price
        trades[-1]['exit_index'] = len(df) - 1
        trades[-1]['profit_pct'] = profit_pct
    
    elapsed = time.time() - start_time
    print(f"   ⏱️  소요 시간: {elapsed:.2f}초")
    print(f"   📊 거래 횟수: {len(trades)}회")
    print(f"   💰 최종 자산: {capital:,.0f}원")
    
    return trades, capital, elapsed


def compare_results(slow_trades, slow_capital, slow_time, fast_trades, fast_capital, fast_time):
    """두 방식의 결과 비교"""
    print(f"\n{'='*80}")
    print(f"📊 결과 비교")
    print(f"{'='*80}\n")
    
    # 거래 횟수 비교
    print(f"1️⃣  거래 횟수:")
    print(f"   느린 방식: {len(slow_trades)}회")
    print(f"   빠른 방식: {len(fast_trades)}회")
    print(f"   {'✅ 동일' if len(slow_trades) == len(fast_trades) else '❌ 불일치'}\n")
    
    # 최종 자산 비교
    print(f"2️⃣  최종 자산:")
    print(f"   느린 방식: {slow_capital:,.0f}원")
    print(f"   빠른 방식: {fast_capital:,.0f}원")
    diff = abs(slow_capital - fast_capital)
    print(f"   차이: {diff:,.0f}원")
    print(f"   {'✅ 동일' if diff < 1 else '❌ 불일치'}\n")
    
    # 소요 시간 비교
    print(f"3️⃣  소요 시간:")
    print(f"   느린 방식: {slow_time:.2f}초")
    print(f"   빠른 방식: {fast_time:.2f}초")
    speedup = slow_time / fast_time if fast_time > 0 else 0
    print(f"   속도 향상: {speedup:.1f}배 빠름\n")
    
    # 거래 상세 비교 (첫 5개)
    if len(slow_trades) == len(fast_trades):
        print(f"4️⃣  거래 상세 비교 (처음 5개):")
        
        all_match = True
        for i in range(min(5, len(slow_trades))):
            slow = slow_trades[i]
            fast = fast_trades[i]
            
            entry_match = slow['entry_index'] == fast['entry_index']
            exit_match = slow.get('exit_index') == fast.get('exit_index')
            
            if entry_match and exit_match:
                print(f"   거래 #{i+1}: ✅ 매수={slow['entry_index']}, 매도={slow.get('exit_index', 'N/A')}")
            else:
                print(f"   거래 #{i+1}: ❌ 불일치")
                print(f"      느린: 매수={slow['entry_index']}, 매도={slow.get('exit_index', 'N/A')}")
                print(f"      빠른: 매수={fast['entry_index']}, 매도={fast.get('exit_index', 'N/A')}")
                all_match = False
        
        print(f"\n   {'✅ 모든 거래 일치' if all_match else '❌ 일부 거래 불일치'}")
    
    print(f"\n{'='*80}")
    
    # 최종 판정
    is_identical = (
        len(slow_trades) == len(fast_trades) and
        abs(slow_capital - fast_capital) < 1
    )
    
    if is_identical:
        print(f"✅ 검증 성공: 두 방식의 결과가 동일합니다!")
        print(f"💡 빠른 방식 사용 가능 (속도 {speedup:.1f}배 향상)")
    else:
        print(f"❌ 검증 실패: 두 방식의 결과가 다릅니다!")
        print(f"⚠️  느린 방식만 사용해야 합니다")
    
    print(f"{'='*80}\n")


if __name__ == "__main__":
    print(f"\n{'='*80}")
    print(f"🔬 백테스트 방식 검증")
    print(f"{'='*80}\n")
    
    # 데이터 로드
    data_dir = Path("data/historical")
    csv_file = list(data_dir.glob("KRW-BTC_minute1_*.csv"))[0]
    
    print(f"📂 데이터 로드: {csv_file.name}")
    df_full = pd.read_csv(csv_file)
    df_full['timestamp'] = pd.to_datetime(df_full['timestamp'])
    df_full.set_index('timestamp', inplace=True)
    
    # 30일 데이터만 추출
    end_date = df_full.index[-1]
    start_date = end_date - timedelta(days=30)
    df = df_full[df_full.index >= start_date].copy()
    
    print(f"   전체: {len(df_full):,}개 캔들")
    print(f"   30일: {len(df):,}개 캔들 ({df.index[0]} ~ {df.index[-1]})")
    
    # 전략 초기화
    strategy = BinanceMultiSignalStrategy(
        rsi_oversold=40.0,
        bb_proximity_pct=1.0,
        stoch_overbought=80.0,
        require_all_signals=False
    )
    
    # 두 방식 실행
    slow_trades, slow_capital, slow_time = slow_backtest(df, strategy, exit_tp=5, exit_sl=-3)
    fast_trades, fast_capital, fast_time = fast_backtest(df, strategy, exit_tp=5, exit_sl=-3)
    
    # 결과 비교
    compare_results(slow_trades, slow_capital, slow_time, fast_trades, fast_capital, fast_time)
