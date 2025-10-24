"""
전략 간단 테스트 스크립트
Simple Strategy Testing Script

시뮬레이션 데이터로 전략을 테스트하고 성과를 비교합니다.

사용법:
    python tests/test_strategies_simple.py
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.strategies import RSI_Strategy, MACD_Strategy, BollingerBands_Strategy, SimpleStrategy
from core.backtester import Backtester

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_test_data(days: int = 365, initial_price: float = 100000000) -> pd.DataFrame:
    """
    시뮬레이션 캔들 데이터 생성

    Args:
        days: 생성할 일수
        initial_price: 초기 가격

    Returns:
        pd.DataFrame: 캔들 데이터
    """
    dates = pd.date_range(end=datetime.now(), periods=days, freq='1D')

    # 가격 시뮬레이션 (Geometric Brownian Motion + 추세)
    np.random.seed(42)  # 재현성을 위한 시드

    prices = [initial_price]
    current_price = initial_price

    for i in range(1, days):
        # 추세 + 랜덤 워크
        # 전반부는 상승, 중반은 하락, 후반은 횡보
        if i < days * 0.3:
            trend = 0.001  # 상승 추세
        elif i < days * 0.6:
            trend = -0.001  # 하락 추세
        else:
            trend = 0.0  # 횡보

        # 일일 변동 = 추세 + 랜덤 노이즈
        daily_return = trend + np.random.normal(0, 0.02)
        current_price = current_price * (1 + daily_return)

        prices.append(current_price)

    # OHLCV 생성
    df = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': [1000000 + np.random.uniform(-200000, 200000) for _ in prices]
    }, index=dates)

    logger.info(f"테스트 데이터 생성: {len(df)}일")
    logger.info(f"기간: {df.index[0].date()} ~ {df.index[-1].date()}")
    logger.info(f"가격 범위: {df['close'].min():,.0f}원 ~ {df['close'].max():,.0f}원")

    return df


def main():
    """메인 실행 함수"""
    print("\n" + "="*100)
    print("전략 백테스팅 시스템 (Simple Test)")
    print("Strategy Backtesting System (With Simulated Data)")
    print("="*100 + "\n")

    # 1. 데이터 생성
    print("📊 1단계: 시뮬레이션 데이터 생성")
    candles = generate_test_data(days=365, initial_price=100000000)

    # 2. 전략 정의
    print("\n🎯 2단계: 전략 초기화")
    strategies = [
        ('Buy & Hold', SimpleStrategy()),
        ('RSI (30/70)', RSI_Strategy(period=14, oversold=30, overbought=70)),
        ('RSI (25/75)', RSI_Strategy(period=14, oversold=25, overbought=75)),
        ('MACD (12/26/9)', MACD_Strategy(fast_period=12, slow_period=26, signal_period=9)),
        ('MACD (8/21/5)', MACD_Strategy(fast_period=8, slow_period=21, signal_period=5)),
        ('BB (20, 2.0)', BollingerBands_Strategy(period=20, std_dev=2.0)),
        ('BB (20, 2.5)', BollingerBands_Strategy(period=20, std_dev=2.5)),
    ]

    print(f"테스트할 전략: {len(strategies)}개")
    for name, _ in strategies:
        print(f"  - {name}")

    # 3. 각 전략 테스트
    print("\n⚙️  3단계: 백테스팅 실행\n")
    results = []

    for name, strategy in strategies:
        print(f"\n{'='*70}")
        print(f"전략: {name}")
        print(f"{'='*70}")

        # 백테스터 초기화
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000000,  # 1천만원
            fee_rate=0.0005  # 0.05%
        )

        # 백테스팅 실행
        result = backtester.run(candles, 'SIMULATED')

        # 결과 출력
        print(f"\n성과:")
        print(f"  초기 자본: {result.initial_capital:,.0f}원")
        print(f"  최종 자본: {result.final_capital:,.0f}원")
        print(f"  총 수익률: {result.total_return:+.2f}%")
        print(f"  샤프 비율: {result.sharpe_ratio:.2f}")
        print(f"  최대 낙폭: {result.max_drawdown:.2f}%")
        print(f"  승률: {result.win_rate:.1f}%")
        print(f"  총 거래: {result.total_trades}회")

        results.append({
            'name': name,
            'result': result
        })

    # 4. 성과 비교
    print("\n\n" + "="*100)
    print("📈 4단계: 전략 성과 비교")
    print("="*100 + "\n")

    # 테이블 헤더
    header = f"{'전략':<25} {'수익률':>10} {'샤프':>8} {'MDD':>10} {'승률':>8} {'거래수':>8}"
    print(header)
    print("-" * 100)

    # 각 전략 결과
    for item in results:
        name = item['name'][:23]
        r = item['result']

        row = (
            f"{name:<25} "
            f"{r.total_return:>9.2f}% "
            f"{r.sharpe_ratio:>8.2f} "
            f"{r.max_drawdown:>9.2f}% "
            f"{r.win_rate:>7.1f}% "
            f"{r.total_trades:>8d}"
        )
        print(row)

    print("-" * 100)

    # 최고 성과 전략
    best_return = max(results, key=lambda x: x['result'].total_return)
    best_sharpe = max(results, key=lambda x: x['result'].sharpe_ratio)
    best_winrate = max(results, key=lambda x: x['result'].win_rate)

    print(f"\n🏆 최고 수익률: {best_return['name']} ({best_return['result'].total_return:+.2f}%)")
    print(f"📈 최고 샤프 비율: {best_sharpe['name']} ({best_sharpe['result'].sharpe_ratio:.2f})")
    print(f"🎯 최고 승률: {best_winrate['name']} ({best_winrate['result'].win_rate:.1f}%)")

    print("\n" + "="*100)
    print("✅ 백테스팅 완료")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
