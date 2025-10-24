"""
전략 실제 데이터 테스트 스크립트
Real Data Strategy Testing Script

실제 업비트 BTC 데이터로 전략을 재검증하고 Phase 2 시뮬레이션 결과와 비교합니다.

사용법:
    python tests/test_strategies_real_data.py
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
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


def load_real_data(filepath: str = "data/btc_2024.csv") -> pd.DataFrame:
    """
    실제 업비트 데이터 로드

    Args:
        filepath: CSV 파일 경로

    Returns:
        pd.DataFrame: OHLCV 데이터
    """
    try:
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)

        # 컬럼명 소문자로 통일 (pyupbit format)
        df.columns = df.columns.str.lower()

        logger.info(f"✅ 데이터 로드 완료: {filepath}")
        logger.info(f"   기간: {df.index[0]} ~ {df.index[-1]}")
        logger.info(f"   캔들 수: {len(df):,}개")
        logger.info(f"   가격 범위: {df['close'].min():,.0f}원 ~ {df['close'].max():,.0f}원")

        return df

    except FileNotFoundError:
        logger.error(f"❌ 파일을 찾을 수 없습니다: {filepath}")
        logger.error("   먼저 데이터를 다운로드하세요: python scripts/download_real_data.py")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 데이터 로드 실패: {e}")
        sys.exit(1)


def analyze_market_regime(df: pd.DataFrame) -> dict:
    """
    시장 환경 분석

    Args:
        df: OHLCV 데이터

    Returns:
        dict: 시장 환경별 통계
    """
    # 일일 수익률 계산
    df = df.copy()
    df['returns'] = df['close'].pct_change()
    df['ma_returns'] = df['returns'].rolling(window=20).mean()

    # 시장 환경 분류
    def classify(ret):
        if pd.isna(ret):
            return 'Unknown'
        elif ret > 0.005:  # > 0.5%
            return 'Bull'
        elif ret < -0.005:  # < -0.5%
            return 'Bear'
        else:
            return 'Sideways'

    df['regime'] = df['ma_returns'].apply(classify)

    # 구간별 통계
    regime_stats = {
        'counts': df['regime'].value_counts().to_dict(),
        'percentages': (df['regime'].value_counts() / len(df) * 100).to_dict(),
        'periods': {}
    }

    # 각 환경별 데이터 추출
    for regime in ['Bull', 'Bear', 'Sideways']:
        regime_data = df[df['regime'] == regime]
        if len(regime_data) > 0:
            regime_stats['periods'][regime] = regime_data

    return regime_stats


def compare_with_phase2(real_results: dict, phase2_results: dict) -> pd.DataFrame:
    """
    Phase 2 시뮬레이션 결과와 비교

    Args:
        real_results: 실제 데이터 결과
        phase2_results: Phase 2 시뮬레이션 결과

    Returns:
        pd.DataFrame: 비교 테이블
    """
    comparison = []

    for strategy_name in real_results.keys():
        real = real_results[strategy_name]
        phase2 = phase2_results.get(strategy_name, {})

        comparison.append({
            'Strategy': strategy_name,
            'Real_Return': real.get('return', 0),
            'Sim_Return': phase2.get('return', 0),
            'Return_Diff': real.get('return', 0) - phase2.get('return', 0),
            'Real_Sharpe': real.get('sharpe', 0),
            'Sim_Sharpe': phase2.get('sharpe', 0),
            'Real_MDD': real.get('mdd', 0),
            'Sim_MDD': phase2.get('mdd', 0),
            'Real_WinRate': real.get('win_rate', 0),
            'Sim_WinRate': phase2.get('win_rate', 0),
        })

    return pd.DataFrame(comparison)


def main():
    """메인 실행 함수"""
    print("\n" + "="*100)
    print("실제 업비트 데이터 전략 백테스팅")
    print("Real Upbit Data Strategy Backtesting")
    print("="*100 + "\n")

    # 1. 데이터 로드
    print("📊 1단계: 실제 데이터 로드")
    candles = load_real_data("data/btc_2024.csv")

    # 2. 시장 환경 분석
    print("\n📈 2단계: 시장 환경 분석")
    regime_stats = analyze_market_regime(candles)

    print(f"\n시장 환경 분포:")
    for regime, pct in regime_stats['percentages'].items():
        count = regime_stats['counts'][regime]
        print(f"   {regime}: {count}일 ({pct:.1f}%)")

    # 3. 전략 정의 (Phase 2와 동일)
    print("\n🎯 3단계: 전략 초기화")
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

    # 4. 백테스팅 실행
    print("\n⚙️  4단계: 백테스팅 실행\n")
    results = {}

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
        result = backtester.run(candles, 'KRW-BTC')

        # 결과 출력
        print(f"\n성과:")
        print(f"  초기 자본: {result.initial_capital:,.0f}원")
        print(f"  최종 자본: {result.final_capital:,.0f}원")
        print(f"  총 수익률: {result.total_return:+.2f}%")
        print(f"  샤프 비율: {result.sharpe_ratio:.2f}")
        print(f"  최대 낙폭: {result.max_drawdown:.2f}%")
        print(f"  승률: {result.win_rate:.1f}%")
        print(f"  총 거래: {result.total_trades}회")

        # 결과 저장
        results[name] = {
            'return': result.total_return,
            'sharpe': result.sharpe_ratio,
            'mdd': result.max_drawdown,
            'win_rate': result.win_rate,
            'trades': result.total_trades
        }

    # 5. 성과 비교 테이블
    print("\n\n" + "="*100)
    print("📈 5단계: 전략 성과 비교 (실제 데이터)")
    print("="*100 + "\n")

    # 테이블 헤더
    header = f"{'전략':<25} {'수익률':>10} {'샤프':>8} {'MDD':>10} {'승률':>8} {'거래수':>8}"
    print(header)
    print("-" * 100)

    # 각 전략 결과
    for name, r in results.items():
        row = (
            f"{name:<25} "
            f"{r['return']:>9.2f}% "
            f"{r['sharpe']:>8.2f} "
            f"{r['mdd']:>9.2f}% "
            f"{r['win_rate']:>7.1f}% "
            f"{r['trades']:>8d}"
        )
        print(row)

    print("-" * 100)

    # 최고 성과 전략
    best_return = max(results.items(), key=lambda x: x[1]['return'])
    best_sharpe = max(results.items(), key=lambda x: x[1]['sharpe'])
    best_winrate = max(results.items(), key=lambda x: x[1]['win_rate'])

    print(f"\n🏆 최고 수익률: {best_return[0]} ({best_return[1]['return']:+.2f}%)")
    print(f"📈 최고 샤프 비율: {best_sharpe[0]} ({best_sharpe[1]['sharpe']:.2f})")
    print(f"🎯 최고 승률: {best_winrate[0]} ({best_winrate[1]['win_rate']:.1f}%)")

    # 6. Phase 2 시뮬레이션 결과와 비교
    print("\n\n" + "="*100)
    print("📊 6단계: Phase 2 시뮬레이션 vs 실제 데이터 비교")
    print("="*100 + "\n")

    # Phase 2 결과 (PHASE_2_완료_보고서.md에서)
    phase2_results = {
        'Buy & Hold': {'return': -0.76, 'sharpe': 0.09, 'mdd': 27.29, 'win_rate': 0.0},
        'RSI (30/70)': {'return': 6.82, 'sharpe': 0.25, 'mdd': 18.09, 'win_rate': 66.7},
        'RSI (25/75)': {'return': 5.33, 'sharpe': 0.21, 'mdd': 17.87, 'win_rate': 100.0},
        'MACD (12/26/9)': {'return': 12.92, 'sharpe': 0.44, 'mdd': 19.37, 'win_rate': 55.6},
        'MACD (8/21/5)': {'return': -9.82, 'sharpe': -0.28, 'mdd': 22.17, 'win_rate': 29.2},
        'BB (20, 2.0)': {'return': 27.95, 'sharpe': 0.97, 'mdd': 7.37, 'win_rate': 100.0},
        'BB (20, 2.5)': {'return': 3.89, 'sharpe': 0.29, 'mdd': 3.95, 'win_rate': 0.0},
    }

    print("비교 분석:")
    print(f"{'전략':<25} {'실제':<10} {'시뮬':<10} {'차이':<10} {'평가':<30}")
    print("-" * 100)

    for name in results.keys():
        real_ret = results[name]['return']
        sim_ret = phase2_results[name]['return']
        diff = real_ret - sim_ret

        # 평가
        if abs(diff) < 5:
            evaluation = "✅ 일치"
        elif diff > 0:
            evaluation = "📈 실제가 더 좋음"
        else:
            evaluation = "📉 시뮬이 더 좋음"

        print(f"{name:<25} {real_ret:>9.2f}% {sim_ret:>9.2f}% {diff:>9.2f}% {evaluation}")

    print("\n" + "="*100)
    print("✅ 백테스팅 완료")
    print("="*100 + "\n")

    print("📝 핵심 인사이트:")
    print("  1. 실제 데이터에서도 최고 성과 전략 확인")
    print("  2. 시뮬레이션 vs 실제 데이터 차이 분석")
    print("  3. 시장 환경별 전략 적합성 평가")
    print()

    print("다음 단계:")
    print("  1. 리스크 관리 기능 추가 (스톱로스, 타겟)")
    print("  2. 포지션 사이징 구현")
    print("  3. 시장 환경별 성과 분석")
    print()


if __name__ == "__main__":
    main()
