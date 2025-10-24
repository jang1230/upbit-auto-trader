"""
백테스팅 실행 스크립트

사용법:
    python run_backtest.py --symbol KRW-BTC --days 30

옵션:
    --symbol: 코인 심볼 (기본값: KRW-BTC)
    --days: 백테스팅 기간 (일, 기본값: 30)
    --interval: 캔들 간격 (기본값: minute1)
    --capital: 초기 자본 (기본값: 1000000원)
"""

import argparse
import logging
from datetime import datetime, timedelta
from core.historical_data import HistoricalDataFetcher
from core.dca_backtester import DcaBacktester
from core.backtest_report import BacktestReportGenerator
from core.strategies import BollingerBands_Strategy
from gui.dca_config import DcaConfigManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """메인 실행 함수"""
    # 인자 파싱
    parser = argparse.ArgumentParser(description='백테스팅 실행')
    parser.add_argument('--symbol', type=str, default='KRW-BTC', help='코인 심볼')
    parser.add_argument('--days', type=int, default=30, help='백테스팅 기간 (일)')
    parser.add_argument('--interval', type=str, default='minute1', help='캔들 간격')
    parser.add_argument('--capital', type=float, default=1000000, help='초기 자본 (원)')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("백테스팅 시작")
    logger.info("=" * 80)
    logger.info(f"심볼: {args.symbol}")
    logger.info(f"기간: 최근 {args.days}일")
    logger.info(f"간격: {args.interval}")
    logger.info(f"초기 자본: {args.capital:,.0f}원")
    logger.info("")

    # 1. 데이터 수집
    logger.info("📊 1단계: 과거 데이터 수집")
    logger.info("-" * 80)

    fetcher = HistoricalDataFetcher()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)

    candles = fetcher.fetch_candles(
        symbol=args.symbol,
        start_date=start_date,
        end_date=end_date,
        interval=args.interval,
        use_cache=True
    )

    logger.info(f"✅ 데이터 수집 완료: {len(candles):,}개 캔들")
    logger.info("")

    # 2. 전략 초기화
    logger.info("🎯 2단계: 전략 초기화")
    logger.info("-" * 80)

    strategy = BollingerBands_Strategy(
        period=20,
        std_dev=2.5
    )

    logger.info(f"전략: {strategy.name}")
    logger.info(f"  볼린저 밴드 기간: 20")
    logger.info(f"  표준편차 배수: 2.5")
    logger.info("")

    # 3. DCA 설정 로드
    logger.info("⚙️ 3단계: DCA 설정 로드")
    logger.info("-" * 80)

    dca_manager = DcaConfigManager()
    dca_config = dca_manager.load()

    logger.info(f"DCA 레벨: {len(dca_config.levels)}개")
    logger.info(f"익절 레벨: {len(dca_config.take_profit_levels) if dca_config.take_profit_levels else 1}개")
    logger.info(f"손절 레벨: {len(dca_config.stop_loss_levels) if dca_config.stop_loss_levels else 1}개")
    logger.info("")

    # 4. 백테스팅 실행
    logger.info("🔬 4단계: 백테스팅 실행")
    logger.info("-" * 80)

    backtester = DcaBacktester(
        strategy=strategy,
        dca_config=dca_config,
        initial_capital=args.capital,
        fee_rate=0.0005,  # 0.05%
        slippage=0.001    # 0.1%
    )

    result = backtester.run(candles, args.symbol)

    logger.info("")

    # 5. 리포트 생성
    logger.info("📝 5단계: 리포트 생성")
    logger.info("-" * 80)

    report_generator = BacktestReportGenerator()
    report_generator.print_report(result)

    logger.info("")
    logger.info("=" * 80)
    logger.info("백테스팅 완료!")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n중단됨")
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
