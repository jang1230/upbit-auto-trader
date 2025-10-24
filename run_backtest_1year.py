"""
1년치 백테스팅 실행 스크립트
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
    
    logger.info("=" * 80)
    logger.info("📊 1년치 백테스팅 시작")
    logger.info("=" * 80)
    
    # 1. 데이터 수집
    logger.info("\n📊 1단계: 과거 데이터 수집")
    logger.info("-" * 80)
    
    fetcher = HistoricalDataFetcher()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    logger.info(f"심볼: KRW-BTC")
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"간격: 1분봉")
    
    candles = fetcher.fetch_candles(
        symbol='KRW-BTC',
        start_date=start_date,
        end_date=end_date,
        interval='minute1',
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
    logger.info(f"익절 레벨: {len(dca_config.take_profit_levels)}개")
    logger.info(f"손절 레벨: {len(dca_config.stop_loss_levels)}개")
    logger.info("")
    
    # 4. 백테스팅 실행
    logger.info("🔬 4단계: 백테스팅 실행")
    logger.info("-" * 80)
    logger.info("이 작업은 1-2분 정도 소요될 수 있습니다...")
    
    backtester = DcaBacktester(
        strategy=strategy,
        dca_config=dca_config,
        initial_capital=1000000,  # 100만원
        fee_rate=0.0005,  # 0.05%
        slippage=0.001    # 0.1%
    )
    
    result = backtester.run(candles, 'KRW-BTC')
    
    logger.info("")
    
    # 5. 리포트 생성
    logger.info("📝 5단계: 리포트 생성")
    logger.info("-" * 80)
    
    report_generator = BacktestReportGenerator()
    report_generator.print_report(result)
    
    # 6. 월별 성과 분석
    logger.info("\n" + "=" * 80)
    logger.info("📅 월별 성과 분석")
    logger.info("=" * 80)
    
    # 거래 내역을 DataFrame으로 변환
    import pandas as pd
    if result.trades:
        trades_df = pd.DataFrame(result.trades)
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        trades_df.set_index('timestamp', inplace=True)
        
        # 월별 거래 수
        monthly_trades = trades_df.resample('M').size()
        logger.info("\n월별 거래 수:")
        for date, count in monthly_trades.items():
            if count > 0:
                logger.info(f"  {date.strftime('%Y-%m')}: {count}회")
        
        # 월별 매수/매도
        monthly_buy = trades_df[trades_df['side'] == 'buy'].resample('M').size()
        monthly_sell = trades_df[trades_df['side'] == 'sell'].resample('M').size()
        
        logger.info("\n월별 매수/매도:")
        for date in monthly_trades.index:
            if monthly_trades[date] > 0:
                buys = monthly_buy.get(date, 0)
                sells = monthly_sell.get(date, 0)
                logger.info(f"  {date.strftime('%Y-%m')}: 매수 {buys}회, 매도 {sells}회")
    
    # 7. 최종 요약
    logger.info("\n" + "=" * 80)
    logger.info("✅ 1년치 백테스팅 완료!")
    logger.info("=" * 80)
    logger.info(f"\n핵심 지표:")
    logger.info(f"  초기 자본: {result.initial_capital:,.0f}원")
    logger.info(f"  최종 자산: {result.final_capital:,.0f}원")
    logger.info(f"  순수익: {result.final_capital - result.initial_capital:+,.0f}원")
    logger.info(f"  수익률: {result.total_return:+.2f}%")
    logger.info(f"  MDD: {result.max_drawdown:.2f}%")
    logger.info(f"  샤프 비율: {result.sharpe_ratio:.2f}")
    logger.info(f"  총 거래: {result.total_trades}회")
    logger.info(f"  승률: {result.win_rate:.1f}%")
    logger.info("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n중단됨")
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
