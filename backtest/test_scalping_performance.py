"""
ScalpingStrategy 성능 검증 백테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime
import logging

from core.strategies.scalping_strategy import ScalpingStrategy

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimpleBacktester:
    """단순 백테스터 (DCA 없이 단순 매수/매도)"""

    def __init__(self, strategy, initial_capital=1_000_000, fee_rate=0.0005):
        """
        Args:
            strategy: 거래 전략
            initial_capital: 초기 자금 (기본 100만원)
            fee_rate: 거래 수수료율 (기본 0.05%)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate

        # 상태
        self.cash = initial_capital
        self.position = 0  # 보유 수량
        self.entry_price = 0  # 진입 가격

        # 거래 기록
        self.trades = []
        self.balance_history = []

    def run(self, candles: pd.DataFrame) -> dict:
        """
        백테스트 실행

        Args:
            candles: OHLCV 데이터

        Returns:
            결과 딕셔너리
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 백테스트 시작: {self.strategy.name}")
        logger.info(f"기간: {candles['timestamp'].iloc[0]} ~ {candles['timestamp'].iloc[-1]}")
        logger.info(f"총 캔들: {len(candles):,}개")
        logger.info(f"초기 자금: {self.initial_capital:,}원")
        logger.info(f"{'='*80}\n")

        for i in range(len(candles)):
            current_candles = candles.iloc[:i+1].copy()

            if len(current_candles) < 30:  # 최소 데이터 필요
                continue

            current_price = current_candles['close'].iloc[-1]
            current_time = current_candles['timestamp'].iloc[-1]

            # 현재 자산 가치
            current_value = self.cash + (self.position * current_price)
            self.balance_history.append({
                'timestamp': current_time,
                'value': current_value
            })

            # 포지션 없음 → 매수 신호 확인
            if self.position == 0:
                if self.strategy.should_buy(current_candles):
                    self._buy(current_price, current_time)

            # 포지션 있음 → 매도 신호 확인
            else:
                if self.strategy.should_sell(current_candles):
                    self._sell(current_price, current_time)

        # 마지막 포지션 청산
        if self.position > 0:
            final_price = candles['close'].iloc[-1]
            final_time = candles['timestamp'].iloc[-1]
            self._sell(final_price, final_time, forced=True)

        # 결과 계산
        return self._calculate_results()

    def _buy(self, price: float, timestamp):
        """매수 실행"""
        # 수수료 제외 후 매수 가능 금액
        available = self.cash * (1 - self.fee_rate)
        quantity = available / price

        self.position = quantity
        self.entry_price = price
        self.cash = 0

        self.trades.append({
            'timestamp': timestamp,
            'type': 'buy',
            'price': price,
            'quantity': quantity,
            'value': price * quantity
        })

        # logger.info(f"💰 매수: {timestamp} | 가격: {price:,.0f}원 | 수량: {quantity:.6f}")

    def _sell(self, price: float, timestamp, forced=False):
        """매도 실행"""
        # 수수료 제외 후 매도 대금
        proceeds = self.position * price * (1 - self.fee_rate)

        # 수익률 계산
        profit_pct = ((price - self.entry_price) / self.entry_price) * 100

        self.trades.append({
            'timestamp': timestamp,
            'type': 'sell',
            'price': price,
            'quantity': self.position,
            'value': proceeds,
            'profit_pct': profit_pct
        })

        # logger.info(
        #     f"💸 매도: {timestamp} | 가격: {price:,.0f}원 | "
        #     f"수익률: {profit_pct:+.2f}% {'(강제청산)' if forced else ''}"
        # )

        self.cash = proceeds
        self.position = 0
        self.entry_price = 0

    def _calculate_results(self) -> dict:
        """결과 계산"""
        final_value = self.cash

        # 총 수익률
        total_return = ((final_value - self.initial_capital) / self.initial_capital) * 100

        # 거래 통계
        sell_trades = [t for t in self.trades if t['type'] == 'sell']
        num_trades = len(sell_trades)

        if num_trades == 0:
            return {
                'total_return': 0,
                'num_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'final_value': final_value
            }

        # 승률
        wins = [t for t in sell_trades if t['profit_pct'] > 0]
        losses = [t for t in sell_trades if t['profit_pct'] <= 0]
        win_rate = (len(wins) / num_trades) * 100 if num_trades > 0 else 0

        # 평균 수익/손실
        avg_profit = np.mean([t['profit_pct'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['profit_pct'] for t in losses]) if losses else 0

        # Profit Factor
        total_profit = sum([t['profit_pct'] for t in wins])
        total_loss = abs(sum([t['profit_pct'] for t in losses]))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        # MDD 계산
        balance_df = pd.DataFrame(self.balance_history)
        if len(balance_df) > 0:
            peak = balance_df['value'].expanding().max()
            drawdown = (balance_df['value'] - peak) / peak * 100
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0

        return {
            'total_return': total_return,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'final_value': final_value,
            'num_wins': len(wins),
            'num_losses': len(losses)
        }


def main():
    """메인 실행"""
    # BTC 데이터 로드
    data_path = Path("data/historical/KRW-BTC_minute1_20220101_20241019.csv")

    if not data_path.exists():
        logger.error(f"❌ 데이터 파일 없음: {data_path}")
        return

    logger.info(f"📂 데이터 로드 중: {data_path}")
    df = pd.read_csv(data_path)
    logger.info(f"✅ 로드 완료: {len(df):,}개 캔들\n")

    # 전략 생성
    strategy = ScalpingStrategy(symbol='KRW-BTC')

    logger.info(f"📈 전략 정보:")
    logger.info(strategy)
    logger.info("")

    # 백테스트 실행
    backtester = SimpleBacktester(
        strategy=strategy,
        initial_capital=1_000_000,
        fee_rate=0.0005
    )

    results = backtester.run(df)

    # 결과 출력
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 백테스트 결과")
    logger.info(f"{'='*80}\n")

    logger.info(f"💰 수익 지표:")
    logger.info(f"   총 수익률: {results['total_return']:+.2f}%")
    logger.info(f"   최종 자산: {results['final_value']:,.0f}원")
    logger.info(f"   초기 자산: 1,000,000원")
    logger.info("")

    logger.info(f"📈 거래 통계:")
    logger.info(f"   총 거래: {results['num_trades']}회")
    logger.info(f"   승리: {results['num_wins']}회")
    logger.info(f"   패배: {results['num_losses']}회")
    logger.info(f"   승률: {results['win_rate']:.1f}%")
    logger.info("")

    logger.info(f"💹 수익/손실:")
    logger.info(f"   평균 수익: {results['avg_profit']:+.2f}%")
    logger.info(f"   평균 손실: {results['avg_loss']:+.2f}%")
    logger.info(f"   Profit Factor: {results['profit_factor']:.2f}")
    logger.info("")

    logger.info(f"📉 리스크:")
    logger.info(f"   최대 낙폭 (MDD): {results['max_drawdown']:.2f}%")
    logger.info("")

    # 평가
    logger.info(f"✅ 종합 평가:")
    if results['total_return'] > 0:
        logger.info(f"   ✅ 수익 달성!")
    else:
        logger.info(f"   ⚠️ 손실 발생")

    if results['win_rate'] > 50:
        logger.info(f"   ✅ 승률 양호 ({results['win_rate']:.1f}%)")
    else:
        logger.info(f"   ⚠️ 승률 개선 필요 ({results['win_rate']:.1f}%)")

    if results['max_drawdown'] > -15:
        logger.info(f"   ✅ MDD 양호 ({results['max_drawdown']:.1f}%)")
    else:
        logger.info(f"   ⚠️ MDD 높음 ({results['max_drawdown']:.1f}%)")

    logger.info(f"\n{'='*80}\n")

    # 결과 저장
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_file = output_dir / f"scalping_backtest_result_{timestamp}.txt"

    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(f"ScalpingStrategy 백테스트 결과\n")
        f.write(f"={'='*60}\n\n")
        f.write(f"전략: {strategy.name}\n")
        f.write(f"설명: {strategy.description}\n\n")
        f.write(f"총 수익률: {results['total_return']:+.2f}%\n")
        f.write(f"총 거래: {results['num_trades']}회\n")
        f.write(f"승률: {results['win_rate']:.1f}%\n")
        f.write(f"평균 수익: {results['avg_profit']:+.2f}%\n")
        f.write(f"평균 손실: {results['avg_loss']:+.2f}%\n")
        f.write(f"Profit Factor: {results['profit_factor']:.2f}\n")
        f.write(f"MDD: {results['max_drawdown']:.2f}%\n")

    logger.info(f"💾 결과 저장: {result_file}\n")


if __name__ == "__main__":
    main()
