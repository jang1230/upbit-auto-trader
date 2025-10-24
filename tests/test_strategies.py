"""
전략 백테스팅 스크립트
Strategy Backtesting Script

모든 전략을 실제 데이터로 테스트하고 성과를 비교합니다.

성과 지표:
- 총 수익률 (Total Return)
- 샤프 비율 (Sharpe Ratio)
- 최대 낙폭 (Maximum Drawdown)
- 승률 (Win Rate)
- 평균 보유 기간 (Average Holding Period)

사용법:
    python tests/test_strategies.py
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.strategies import RSI_Strategy, MACD_Strategy, BollingerBands_Strategy, SimpleStrategy
from core.backtester import Backtester

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_btc_data(days: int = 365) -> pd.DataFrame:
    """
    업비트에서 BTC 일봉 데이터 다운로드

    Args:
        days: 가져올 데이터 기간 (일)

    Returns:
        pd.DataFrame: 캔들 데이터
    """
    try:
        import pyupbit

        # 종료일 (오늘)
        to_date = datetime.now()

        # 시작일
        from_date = to_date - timedelta(days=days)

        logger.info(f"BTC 데이터 다운로드 중: {from_date.date()} ~ {to_date.date()}")

        # 일봉 데이터 다운로드
        df = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=days)

        if df is None or len(df) == 0:
            raise ValueError("데이터 다운로드 실패")

        # 컬럼명 소문자로 변경
        df.columns = [col.lower() for col in df.columns]

        logger.info(f"데이터 다운로드 완료: {len(df)}개 캔들")
        logger.info(f"기간: {df.index[0]} ~ {df.index[-1]}")
        logger.info(f"가격 범위: {df['close'].min():,.0f}원 ~ {df['close'].max():,.0f}원")

        return df

    except ImportError:
        logger.error("pyupbit 라이브러리가 설치되지 않았습니다.")
        logger.info("설치 명령: pip install pyupbit")
        raise
    except Exception as e:
        logger.error(f"데이터 다운로드 실패: {e}")
        raise


def calculate_performance_metrics(trades: List[Dict]) -> Dict[str, float]:
    """
    거래 내역으로부터 성과 지표 계산

    Args:
        trades: 거래 내역 리스트

    Returns:
        Dict: 성과 지표
    """
    if not trades:
        return {
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'avg_return': 0.0,
            'avg_holding_days': 0.0,
            'total_trades': 0
        }

    # 수익률 계산
    returns = []
    holding_days = []

    for trade in trades:
        if trade['type'] == 'sell':
            buy_price = trade.get('buy_price', 0)
            sell_price = trade.get('sell_price', 0)

            if buy_price > 0:
                ret = (sell_price - buy_price) / buy_price
                returns.append(ret)

                # 보유 기간 계산
                if 'buy_time' in trade and 'sell_time' in trade:
                    holding_period = (trade['sell_time'] - trade['buy_time']).days
                    holding_days.append(holding_period)

    if not returns:
        return {
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'avg_return': 0.0,
            'avg_holding_days': 0.0,
            'total_trades': len(trades)
        }

    # 총 수익률
    total_return = (np.prod([1 + r for r in returns]) - 1) * 100

    # 샤프 비율 (무위험 수익률 0% 가정)
    if len(returns) > 1:
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0

    # 최대 낙폭 (MDD)
    cumulative = np.cumprod([1 + r for r in returns])
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = np.min(drawdown) * 100

    # 승률
    winning_trades = len([r for r in returns if r > 0])
    win_rate = (winning_trades / len(returns)) * 100

    # 평균 수익률
    avg_return = np.mean(returns) * 100

    # 평균 보유 기간
    avg_holding = np.mean(holding_days) if holding_days else 0.0

    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'avg_holding_days': avg_holding,
        'total_trades': len(returns)
    }


def test_strategy(strategy, candles: pd.DataFrame, initial_capital: float = 10000000) -> Dict:
    """
    단일 전략 테스트

    Args:
        strategy: 테스트할 전략
        candles: 캔들 데이터
        initial_capital: 초기 자본 (원)

    Returns:
        Dict: 테스트 결과
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"전략 테스트: {strategy.name}")
    logger.info(f"{'='*70}")

    # 백테스터 초기화
    backtester = Backtester(
        strategy=strategy,
        initial_capital=initial_capital,
        fee_rate=0.0005  # 업비트 수수료 0.05%
    )

    # 백테스팅 실행
    result = backtester.run(candles, 'KRW-BTC')

    # 결과 출력
    logger.info(f"\n전략 파라미터:")
    params = strategy.get_parameters()
    for key, value in params.items():
        logger.info(f"  {key}: {value}")

    logger.info(f"\n성과 지표:")
    logger.info(f"  초기 자본: {result.initial_capital:,.0f}원")
    logger.info(f"  최종 자본: {result.final_capital:,.0f}원")
    logger.info(f"  총 수익률: {result.total_return:+.2f}%")
    logger.info(f"  샤프 비율: {result.sharpe_ratio:.2f}")
    logger.info(f"  최대 낙폭 (MDD): {result.max_drawdown:.2f}%")
    logger.info(f"  승률: {result.win_rate:.1f}%")
    logger.info(f"  평균 수익: {result.avg_profit:,.0f}원")
    logger.info(f"  평균 손실: {result.avg_loss:,.0f}원")
    logger.info(f"  총 거래 횟수: {result.total_trades}회")

    return {
        'strategy_name': strategy.name,
        'parameters': params,
        'result': result
    }


def compare_strategies(results: List[Dict]):
    """
    전략 성과 비교 테이블 출력

    Args:
        results: 전략 테스트 결과 리스트
    """
    logger.info(f"\n\n{'='*100}")
    logger.info(f"전략 성과 비교")
    logger.info(f"{'='*100}\n")

    # 테이블 헤더
    header = f"{'전략':<30} {'수익률':>10} {'샤프':>8} {'MDD':>10} {'승률':>8} {'거래수':>8}"
    logger.info(header)
    logger.info("-" * 100)

    # 각 전략 결과
    for result in results:
        name = result['strategy_name'][:28]
        r = result['result']

        row = (
            f"{name:<30} "
            f"{r.total_return:>9.2f}% "
            f"{r.sharpe_ratio:>8.2f} "
            f"{r.max_drawdown:>9.2f}% "
            f"{r.win_rate:>7.1f}% "
            f"{r.total_trades:>8d}"
        )
        logger.info(row)

    logger.info("-" * 100)

    # 최고 성과 전략
    best_return = max(results, key=lambda x: x['result'].total_return)
    best_sharpe = max(results, key=lambda x: x['result'].sharpe_ratio)
    best_winrate = max(results, key=lambda x: x['result'].win_rate)

    logger.info(f"\n🏆 최고 수익률: {best_return['strategy_name']} ({best_return['result'].total_return:+.2f}%)")
    logger.info(f"📈 최고 샤프 비율: {best_sharpe['strategy_name']} ({best_sharpe['result'].sharpe_ratio:.2f})")
    logger.info(f"🎯 최고 승률: {best_winrate['strategy_name']} ({best_winrate['result'].win_rate:.1f}%)")


def main():
    """메인 실행 함수"""
    print("\n" + "="*100)
    print("전략 백테스팅 시스템")
    print("Strategy Backtesting System")
    print("="*100 + "\n")

    try:
        # 1. 데이터 다운로드
        print("📊 1단계: 데이터 다운로드")
        candles = download_btc_data(days=365)  # 1년 데이터

        # 2. 전략 정의
        print("\n🎯 2단계: 전략 초기화")
        strategies = [
            SimpleStrategy(),  # 벤치마크
            RSI_Strategy(period=14, oversold=30, overbought=70),
            RSI_Strategy(period=14, oversold=25, overbought=75),  # 변형
            MACD_Strategy(fast_period=12, slow_period=26, signal_period=9),
            MACD_Strategy(fast_period=8, slow_period=21, signal_period=5),  # 변형
            BollingerBands_Strategy(period=20, std_dev=2.0),
            BollingerBands_Strategy(period=20, std_dev=2.5),  # 변형
        ]

        print(f"테스트할 전략: {len(strategies)}개")
        for strategy in strategies:
            print(f"  - {strategy.name}")

        # 3. 각 전략 테스트
        print("\n⚙️  3단계: 백테스팅 실행")
        results = []

        for strategy in strategies:
            result = test_strategy(strategy, candles)
            results.append(result)

        # 4. 성과 비교
        print("\n📈 4단계: 성과 비교")
        compare_strategies(results)

        print("\n" + "="*100)
        print("✅ 백테스팅 완료")
        print("="*100 + "\n")

    except Exception as e:
        logger.error(f"백테스팅 실패: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
