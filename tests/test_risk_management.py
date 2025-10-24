"""
리스크 관리 테스트 스크립트
Risk Management Testing Script

리스크 관리 기능(스톱로스, 타겟 프라이스)을 적용하여 전략을 재테스트합니다.

사용법:
    python tests/test_risk_management.py
"""

import sys
import os
import pandas as pd
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.strategies import BollingerBands_Strategy, MACD_Strategy, RSI_Strategy
from core.backtester import Backtester
from core.risk_manager import RiskManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_real_data(filepath: str = "data/btc_2024.csv") -> pd.DataFrame:
    """실제 업비트 데이터 로드"""
    try:
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        df.columns = df.columns.str.lower()
        logger.info(f"✅ 데이터 로드 완료: {filepath}")
        logger.info(f"   기간: {df.index[0]} ~ {df.index[-1]}")
        logger.info(f"   캔들 수: {len(df):,}개")
        return df
    except FileNotFoundError:
        logger.error(f"❌ 파일을 찾을 수 없습니다: {filepath}")
        sys.exit(1)


def main():
    """메인 실행 함수"""
    print("\n" + "="*100)
    print("리스크 관리 기능 테스트")
    print("Risk Management Testing with Real Data")
    print("="*100 + "\n")

    # 1. 데이터 로드
    print("📊 1단계: 실제 데이터 로드")
    candles = load_real_data("data/btc_2024.csv")

    # 2. 리스크 관리자 설정
    print("\n🛡️  2단계: 리스크 관리자 설정")
    risk_configs = [
        {
            'name': '리스크 관리 없음',
            'manager': None
        },
        {
            'name': '기본 (SL -5%, TP +10%)',
            'manager': RiskManager(stop_loss_pct=5.0, take_profit_pct=10.0)
        },
        {
            'name': '보수적 (SL -3%, TP +8%)',
            'manager': RiskManager(stop_loss_pct=3.0, take_profit_pct=8.0)
        },
        {
            'name': '공격적 (SL -7%, TP +15%)',
            'manager': RiskManager(stop_loss_pct=7.0, take_profit_pct=15.0)
        },
        {
            'name': '트레일링 스톱 (SL -5%, TP +10%, TS -3%)',
            'manager': RiskManager(stop_loss_pct=5.0, take_profit_pct=10.0, trailing_stop_pct=3.0)
        }
    ]

    # 3. 전략 선택 (BB 20, 2.5가 실제 데이터에서 최고 성과)
    print("\n🎯 3단계: 전략 선택")
    strategy = BollingerBands_Strategy(period=20, std_dev=2.5)
    print(f"선택된 전략: BB (20, 2.5) - 실제 데이터 검증 1위")

    # 4. 각 리스크 설정으로 백테스팅
    print("\n⚙️  4단계: 리스크 관리별 백테스팅 실행\n")
    results = []

    for config in risk_configs:
        print(f"\n{'='*70}")
        print(f"설정: {config['name']}")
        print(f"{'='*70}")

        # 백테스터 초기화
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000000,  # 1천만원
            fee_rate=0.0005,  # 0.05%
            risk_manager=config['manager']
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

        # 리스크 관리 통계
        if config['manager'] and hasattr(backtester, 'risk_exits'):
            risk_exits = backtester.risk_exits
            if risk_exits:
                print(f"\n  리스크 관리 청산:")
                stop_loss_count = sum(1 for e in risk_exits if e['reason'] == 'stop_loss')
                take_profit_count = sum(1 for e in risk_exits if e['reason'] == 'take_profit')
                trailing_stop_count = sum(1 for e in risk_exits if e['reason'] == 'trailing_stop')

                print(f"    스톱로스: {stop_loss_count}회")
                print(f"    타겟 달성: {take_profit_count}회")
                if trailing_stop_count > 0:
                    print(f"    트레일링 스톱: {trailing_stop_count}회")

        results.append({
            'name': config['name'],
            'return': result.total_return,
            'sharpe': result.sharpe_ratio,
            'mdd': result.max_drawdown,
            'win_rate': result.win_rate,
            'trades': result.total_trades
        })

    # 5. 비교 분석
    print("\n\n" + "="*100)
    print("📈 5단계: 리스크 관리 설정별 성과 비교")
    print("="*100 + "\n")

    # 테이블 헤더
    header = f"{'설정':<40} {'수익률':>10} {'샤프':>8} {'MDD':>10} {'승률':>8} {'거래수':>8}"
    print(header)
    print("-" * 100)

    # 각 결과
    for r in results:
        row = (
            f"{r['name']:<40} "
            f"{r['return']:>9.2f}% "
            f"{r['sharpe']:>8.2f} "
            f"{r['mdd']:>9.2f}% "
            f"{r['win_rate']:>7.1f}% "
            f"{r['trades']:>8d}"
        )
        print(row)

    print("-" * 100)

    # 최고 성과
    best_return = max(results, key=lambda x: x['return'])
    best_sharpe = max(results, key=lambda x: x['sharpe'])
    lowest_mdd = min(results, key=lambda x: x['mdd'])

    print(f"\n🏆 최고 수익률: {best_return['name']} ({best_return['return']:+.2f}%)")
    print(f"📈 최고 샤프 비율: {best_sharpe['name']} ({best_sharpe['sharpe']:.2f})")
    print(f"🛡️  최저 MDD: {lowest_mdd['name']} ({lowest_mdd['mdd']:.2f}%)")

    # 6. 핵심 인사이트
    print("\n\n" + "="*100)
    print("💡 핵심 인사이트")
    print("="*100 + "\n")

    # 리스크 관리 없음 vs 있음 비교
    no_risk = results[0]
    with_risk = results[1]

    return_diff = with_risk['return'] - no_risk['return']
    mdd_diff = with_risk['mdd'] - no_risk['mdd']

    print(f"1. 리스크 관리 효과:")
    print(f"   수익률 변화: {return_diff:+.2f}%p")
    print(f"   MDD 변화: {mdd_diff:+.2f}%p")

    if mdd_diff < 0:
        print(f"   → MDD 감소로 안정성 향상 ✅")
    if return_diff < 0:
        print(f"   → 수익률 감소는 손실 제한의 트레이드오프 ⚖️")

    print(f"\n2. 최적 리스크 설정:")
    if best_sharpe['name'] == '리스크 관리 없음':
        print(f"   → 현재 시장에서는 리스크 관리 불필요")
    else:
        print(f"   → {best_sharpe['name']}이 위험 대비 수익 최적")

    print(f"\n3. MDD 관리:")
    print(f"   리스크 관리 없음: {no_risk['mdd']:.2f}%")
    print(f"   최저 MDD 설정: {lowest_mdd['mdd']:.2f}%")
    print(f"   → MDD {no_risk['mdd'] - lowest_mdd['mdd']:.2f}%p 개선 가능")

    print("\n" + "="*100)
    print("✅ 리스크 관리 테스트 완료")
    print("="*100 + "\n")

    print("다음 단계:")
    print("  1. 포지션 사이징 구현 (자금 관리)")
    print("  2. 시장 환경별 성과 분석")
    print("  3. Phase 2.5 완료 보고서 작성")
    print()


if __name__ == "__main__":
    main()
