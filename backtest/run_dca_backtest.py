"""
DCA Backtest Runner
DCA 백테스트 실행 스크립트

간단한 DCA 전략 백테스트:
- 익절: 평단가 대비 +5%
- 손절: 평단가 대비 -7% (6회 매수 완료 후)
- 추가매수: -10%마다 동일 금액 (최대 5회 추가)
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backtest.data_loader import DataLoader
from backtest.dca_backtest_engine import DCABacktestEngine
from core.strategies.proximity_bb_strategy import ProximityBollingerBandsStrategy

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)


def run_dca_backtest(
    symbol: str = 'KRW-BTC',
    days: int = 90,
    initial_capital: float = 1000000,
    profit_target: float = 5.0,
    stop_loss: float = -7.0,
    max_buys: int = 6,
    buy_interval: float = 10.0
):
    """
    DCA 백테스트 실행

    Args:
        symbol: 심볼 (예: 'KRW-BTC')
        days: 테스트 기간 (일)
        initial_capital: 초기 자본
        profit_target: 익절 목표 % (평단가 대비)
        stop_loss: 손절 % (평단가 대비)
        max_buys: 최대 매수 횟수
        buy_interval: 추가매수 간격 %
    """
    print("=" * 80)
    print("DCA 백테스트 실행")
    print("=" * 80)
    print(f"심볼: {symbol}")
    print(f"기간: 최근 {days}일")
    print(f"초기 자본: {initial_capital:,.0f}원")
    print(f"익절: 평단가 +{profit_target}%")
    print(f"손절: 평단가 {stop_loss}% (6회 매수 완료 후)")
    print(f"분할 매수: {max_buys}회 (-{buy_interval}%마다 추가)")
    print("=" * 80)

    # 1. 데이터 로드
    loader = DataLoader()
    candles = loader.load_ohlcv(symbol, days=days, interval='minute60')

    print(f"\n✅ 데이터 로드 완료: {len(candles)}개 캔들")

    # 2. 전략 설정 (Proximity BB 사용)
    strategy = ProximityBollingerBandsStrategy(symbol=symbol)

    # 3. DCA 백테스트 실행
    engine = DCABacktestEngine(
        strategy=strategy,
        initial_capital=initial_capital,
        profit_target_pct=profit_target,
        stop_loss_pct=stop_loss,
        max_buys=max_buys,
        buy_interval_pct=buy_interval
    )

    result = engine.run(candles)

    # 4. 결과 출력
    result.print_summary()

    # 5. 상세 거래 내역 (최근 5개)
    if result.trades:
        print("\n🔍 최근 5개 거래 상세:")
        for trade in result.trades[-5:]:
            print(f"\n   [{trade.exit_type.upper()}] {trade.exit_timestamp.strftime('%Y-%m-%d %H:%M')}")
            print(f"   분할매수: {len(trade.entry_buys)}회")
            for buy in trade.entry_buys:
                print(f"      {buy.buy_number}차: {buy.price:.0f}원 × {buy.quantity:.4f}")
            print(f"   평단가: {trade.avg_price:.0f}원")
            print(f"   매도가: {trade.exit_price:.0f}원")
            print(f"   손익: {trade.pnl:+,.0f}원 ({trade.pnl_pct:+.2f}%)")

    return result


def compare_dca_strategies(
    symbol: str = 'KRW-BTC',
    days: int = 90,
    initial_capital: float = 1000000
):
    """
    다양한 DCA 파라미터 비교

    Args:
        symbol: 심볼
        days: 테스트 기간
        initial_capital: 초기 자본
    """
    print("\n" + "=" * 80)
    print("DCA 파라미터 비교 분석")
    print("=" * 80)

    # 데이터 로드 (한 번만)
    loader = DataLoader()
    candles = loader.load_ohlcv(symbol, days=days, interval='minute60')

    results = []

    # 테스트 시나리오
    scenarios = [
        {'name': '기본 (익절5%, 손절-7%)', 'profit': 5.0, 'loss': -7.0},
        {'name': '공격적 (익절3%, 손절-10%)', 'profit': 3.0, 'loss': -10.0},
        {'name': '보수적 (익절7%, 손절-5%)', 'profit': 7.0, 'loss': -5.0},
    ]

    for scenario in scenarios:
        print(f"\n{'='*80}")
        print(f"🧪 테스트: {scenario['name']}")
        print(f"{'='*80}")

        strategy = ProximityBollingerBandsStrategy(symbol=symbol)
        engine = DCABacktestEngine(
            strategy=strategy,
            initial_capital=initial_capital,
            profit_target_pct=scenario['profit'],
            stop_loss_pct=scenario['loss']
        )

        result = engine.run(candles)
        results.append((scenario['name'], result))

    # 비교 결과
    print("\n" + "=" * 80)
    print("📊 DCA 파라미터 비교 결과")
    print("=" * 80)

    print(f"\n{'시나리오':<30} {'수익률':>10} {'거래수':>8} {'승률':>8} {'익절':>8} {'손절':>8}")
    print("-" * 80)

    for name, result in results:
        print(
            f"{name:<30} "
            f"{result.total_return:>9.2f}% "
            f"{result.total_trades:>7}회 "
            f"{result.win_rate:>7.1f}% "
            f"{result.avg_profit_trades:>7}회 "
            f"{result.avg_loss_trades:>7}회"
        )

    # 최고 성과 찾기
    best_result = max(results, key=lambda x: x[1].total_return)
    print("\n" + "=" * 80)
    print(f"✅ 최고 성과: {best_result[0]} (수익률 {best_result[1].total_return:+.2f}%)")
    print("=" * 80)


if __name__ == "__main__":
    """테스트 실행"""

    # 1. 기본 DCA 백테스트
    print("\n📊 BTC DCA 백테스트 (90일)")
    run_dca_backtest(symbol='KRW-BTC', days=90)

    print("\n" + "="*80)
    print("\n")

    # 2. ETH DCA 백테스트
    print("📊 ETH DCA 백테스트 (90일)")
    run_dca_backtest(symbol='KRW-ETH', days=90)

    print("\n" + "="*80)
    print("\n")

    # 3. XRP DCA 백테스트
    print("📊 XRP DCA 백테스트 (90일)")
    run_dca_backtest(symbol='KRW-XRP', days=90)

    print("\n" + "="*80)
    print("\n")

    # 4. DCA 파라미터 비교 (BTC)
    print("📊 DCA 파라미터 비교 (BTC, 90일)")
    compare_dca_strategies(symbol='KRW-BTC', days=90)
