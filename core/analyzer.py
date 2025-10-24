"""
성과 분석 모듈
백테스팅 결과를 다양한 관점에서 분석

주요 기능:
- 수익률 분석 (총수익률, 연환산 수익률, 월별 수익률)
- 리스크 지표 (MDD, 표준편차, 샤프 비율, 소르티노 비율)
- 거래 분석 (승률, 평균 손익, Profit Factor)
- 시각화 준비 (equity curve, drawdown curve, monthly returns)
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd

from core.backtester import BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class AnalysisReport:
    """분석 보고서 데이터 클래스"""

    # 기본 정보
    backtest_result: BacktestResult

    # 수익률 분석
    total_return_pct: float
    annualized_return_pct: float
    monthly_returns: Dict[str, float]  # 'YYYY-MM': return_pct

    # 리스크 지표
    max_drawdown_pct: float
    volatility_pct: float  # 연환산 변동성
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float  # 수익률 / MDD

    # 거래 분석
    win_rate_pct: float
    profit_factor: float  # 총이익 / 총손실
    avg_win_pct: float
    avg_loss_pct: float
    max_consecutive_wins: int
    max_consecutive_losses: int

    # 시간 분석
    total_days: int
    trading_days: int  # 포지션 보유 일수
    avg_holding_period: float  # 평균 보유 시간 (시간 단위)

    # 시각화 데이터
    equity_curve_df: pd.DataFrame  # timestamp, equity
    drawdown_curve_df: pd.DataFrame  # timestamp, drawdown_pct
    trades_df: pd.DataFrame  # 거래 내역


class PerformanceAnalyzer:
    """
    백테스팅 성과 분석기

    BacktestResult를 입력받아 다양한 성과 지표를 계산합니다.
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Args:
            risk_free_rate: 무위험 수익률 (연율, 기본값 2%)
        """
        self.risk_free_rate = risk_free_rate
        logger.info(f"성과 분석기 초기화: 무위험 수익률 {risk_free_rate:.1%}")

    def analyze(self, result: BacktestResult) -> AnalysisReport:
        """
        백테스팅 결과 종합 분석

        Args:
            result: 백테스팅 결과

        Returns:
            AnalysisReport: 분석 보고서
        """
        logger.info(f"📊 성과 분석 시작: {result.strategy_name}")

        # 1. 수익률 분석
        total_return = result.total_return
        annualized_return = self._calculate_annualized_return(
            result.total_return,
            result.start_date,
            result.end_date
        )
        monthly_returns = self._calculate_monthly_returns(result)

        # 2. 리스크 지표
        volatility = self._calculate_volatility(result.equity_curve)
        sortino_ratio = self._calculate_sortino_ratio(result.equity_curve)
        calmar_ratio = annualized_return / result.max_drawdown if result.max_drawdown > 0 else 0

        # 3. 거래 분석
        profit_factor = self._calculate_profit_factor(result)
        avg_win_pct, avg_loss_pct = self._calculate_avg_win_loss_pct(result)
        max_consecutive_wins, max_consecutive_losses = self._calculate_consecutive_trades(result)

        # 4. 시간 분석
        total_days = (result.end_date - result.start_date).days
        trading_days = self._calculate_trading_days(result)
        avg_holding_period = self._calculate_avg_holding_period(result)

        # 5. 시각화 데이터 생성
        equity_curve_df = self._create_equity_curve_df(result)
        drawdown_curve_df = self._create_drawdown_curve_df(equity_curve_df)
        trades_df = self._create_trades_df(result)

        report = AnalysisReport(
            backtest_result=result,

            # 수익률
            total_return_pct=total_return,
            annualized_return_pct=annualized_return,
            monthly_returns=monthly_returns,

            # 리스크
            max_drawdown_pct=result.max_drawdown,
            volatility_pct=volatility,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,

            # 거래
            win_rate_pct=result.win_rate,
            profit_factor=profit_factor,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,

            # 시간
            total_days=total_days,
            trading_days=trading_days,
            avg_holding_period=avg_holding_period,

            # 시각화
            equity_curve_df=equity_curve_df,
            drawdown_curve_df=drawdown_curve_df,
            trades_df=trades_df
        )

        logger.info(f"✅ 분석 완료")
        return report

    def _calculate_annualized_return(
        self,
        total_return: float,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """
        연환산 수익률 계산

        Args:
            total_return: 총 수익률 (%)
            start_date: 시작일
            end_date: 종료일

        Returns:
            float: 연환산 수익률 (%)
        """
        days = (end_date - start_date).days
        if days == 0:
            return 0.0

        years = days / 365.0

        # (1 + r)^(1/years) - 1
        annualized = (((total_return / 100) + 1) ** (1 / years) - 1) * 100
        return annualized

    def _calculate_monthly_returns(self, result: BacktestResult) -> Dict[str, float]:
        """
        월별 수익률 계산

        Args:
            result: 백테스팅 결과

        Returns:
            Dict[str, float]: {'YYYY-MM': return_pct}
        """
        if not result.equity_curve or not result.trades:
            return {}

        # 거래 내역을 DataFrame으로 변환
        trades_df = pd.DataFrame(result.trades)
        if trades_df.empty:
            return {}

        # 월별 그룹화
        trades_df['month'] = trades_df['timestamp'].apply(lambda x: x.strftime('%Y-%m'))

        # 각 월의 시작/종료 equity 계산
        monthly_returns = {}

        # 월별로 순회
        for month in sorted(trades_df['month'].unique()):
            month_trades = trades_df[trades_df['month'] == month]

            # 해당 월의 첫 거래와 마지막 거래
            first_balance = month_trades.iloc[0]['balance']
            first_position = month_trades.iloc[0]['position']
            first_price = month_trades.iloc[0]['price']

            last_balance = month_trades.iloc[-1]['balance']
            last_position = month_trades.iloc[-1]['position']
            last_price = month_trades.iloc[-1]['price']

            # Equity 계산
            start_equity = first_balance + (first_position * first_price)
            end_equity = last_balance + (last_position * last_price)

            # 수익률 계산
            if start_equity > 0:
                monthly_return = ((end_equity - start_equity) / start_equity) * 100
                monthly_returns[month] = monthly_return

        return monthly_returns

    def _calculate_volatility(self, equity_curve: List[float]) -> float:
        """
        연환산 변동성 (표준편차) 계산

        Args:
            equity_curve: 자산 가치 시계열

        Returns:
            float: 연환산 변동성 (%)
        """
        if len(equity_curve) < 2:
            return 0.0

        # 일일 수익률 계산
        returns = []
        for i in range(1, len(equity_curve)):
            daily_return = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(daily_return)

        if not returns:
            return 0.0

        # 표준편차
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        # 연환산 (252 거래일 기준)
        annual_volatility = std_dev * (252 ** 0.5) * 100
        return annual_volatility

    def _calculate_sortino_ratio(self, equity_curve: List[float]) -> float:
        """
        소르티노 비율 계산
        (샤프 비율과 유사하지만 하방 변동성만 고려)

        Args:
            equity_curve: 자산 가치 시계열

        Returns:
            float: 소르티노 비율 (연환산)
        """
        if len(equity_curve) < 2:
            return 0.0

        # 일일 수익률 계산
        returns = []
        for i in range(1, len(equity_curve)):
            daily_return = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(daily_return)

        if not returns:
            return 0.0

        # 평균 수익률
        mean_return = sum(returns) / len(returns)

        # 하방 변동성 (음수 수익률만 고려)
        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return float('inf')  # 손실이 없으면 무한대

        downside_variance = sum(r ** 2 for r in downside_returns) / len(returns)
        downside_std = downside_variance ** 0.5

        if downside_std == 0:
            return 0.0

        # 소르티노 비율 (연환산)
        daily_rf = (1 + self.risk_free_rate) ** (1/365) - 1
        sortino = (mean_return - daily_rf) / downside_std
        sortino_annualized = sortino * (252 ** 0.5)

        return sortino_annualized

    def _calculate_profit_factor(self, result: BacktestResult) -> float:
        """
        Profit Factor 계산 (총이익 / 총손실)

        Args:
            result: 백테스팅 결과

        Returns:
            float: Profit Factor
        """
        if result.losing_trades == 0:
            return float('inf')  # 손실이 없으면 무한대

        total_profit = result.avg_profit * result.winning_trades
        total_loss = result.avg_loss * result.losing_trades

        if total_loss == 0:
            return float('inf')

        return total_profit / total_loss

    def _calculate_avg_win_loss_pct(self, result: BacktestResult) -> tuple:
        """
        평균 승리/손실 비율 계산 (%)

        Args:
            result: 백테스팅 결과

        Returns:
            tuple: (avg_win_pct, avg_loss_pct)
        """
        # 초기 자본 기준으로 비율 계산
        initial = result.initial_capital

        avg_win_pct = (result.avg_profit / initial) * 100 if initial > 0 else 0
        avg_loss_pct = (result.avg_loss / initial) * 100 if initial > 0 else 0

        return avg_win_pct, avg_loss_pct

    def _calculate_consecutive_trades(self, result: BacktestResult) -> tuple:
        """
        최대 연속 승/패 계산

        Args:
            result: 백테스팅 결과

        Returns:
            tuple: (max_consecutive_wins, max_consecutive_losses)
        """
        if len(result.trades) < 2:
            return 0, 0

        # 매수-매도 쌍 찾아서 수익 계산
        profits = []

        for i in range(1, len(result.trades)):
            prev_trade = result.trades[i-1]
            curr_trade = result.trades[i]

            if prev_trade['side'] == 'buy' and curr_trade['side'] == 'sell':
                buy_value = prev_trade['price'] * prev_trade['amount']
                sell_value = curr_trade['price'] * curr_trade['amount']
                profit = sell_value - buy_value - prev_trade['fee'] - curr_trade['fee']
                profits.append(profit > 0)

        if not profits:
            return 0, 0

        # 연속 승/패 계산
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for is_win in profits:
            if is_win:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return max_wins, max_losses

    def _calculate_trading_days(self, result: BacktestResult) -> int:
        """
        포지션 보유 일수 계산

        Args:
            result: 백테스팅 결과

        Returns:
            int: 포지션 보유 일수
        """
        if not result.trades:
            return 0

        # 매수-매도 쌍의 보유 시간 합산
        total_seconds = 0

        for i in range(1, len(result.trades)):
            prev_trade = result.trades[i-1]
            curr_trade = result.trades[i]

            if prev_trade['side'] == 'buy' and curr_trade['side'] == 'sell':
                hold_time = curr_trade['timestamp'] - prev_trade['timestamp']
                total_seconds += hold_time.total_seconds()

        return int(total_seconds / 86400)  # 초를 일로 변환

    def _calculate_avg_holding_period(self, result: BacktestResult) -> float:
        """
        평균 보유 시간 계산 (시간 단위)

        Args:
            result: 백테스팅 결과

        Returns:
            float: 평균 보유 시간 (시간)
        """
        if not result.trades:
            return 0.0

        # 매수-매도 쌍의 보유 시간 리스트
        holding_times = []

        for i in range(1, len(result.trades)):
            prev_trade = result.trades[i-1]
            curr_trade = result.trades[i]

            if prev_trade['side'] == 'buy' and curr_trade['side'] == 'sell':
                hold_time = curr_trade['timestamp'] - prev_trade['timestamp']
                holding_times.append(hold_time.total_seconds())

        if not holding_times:
            return 0.0

        avg_seconds = sum(holding_times) / len(holding_times)
        return avg_seconds / 3600  # 초를 시간으로 변환

    def _create_equity_curve_df(self, result: BacktestResult) -> pd.DataFrame:
        """
        Equity Curve DataFrame 생성

        Args:
            result: 백테스팅 결과

        Returns:
            pd.DataFrame: columns=['timestamp', 'equity']
        """
        if not result.equity_curve:
            return pd.DataFrame(columns=['timestamp', 'equity'])

        # 시작일부터 종료일까지 타임스탬프 생성
        # (실제로는 캔들 타임스탬프를 사용해야 하지만, 간단히 인덱스 기반)
        data = {
            'equity': result.equity_curve
        }

        df = pd.DataFrame(data)
        return df

    def _create_drawdown_curve_df(self, equity_df: pd.DataFrame) -> pd.DataFrame:
        """
        Drawdown Curve DataFrame 생성

        Args:
            equity_df: Equity Curve DataFrame

        Returns:
            pd.DataFrame: columns=['timestamp', 'drawdown_pct']
        """
        if equity_df.empty:
            return pd.DataFrame(columns=['drawdown_pct'])

        # 각 시점의 낙폭 계산
        drawdowns = []
        max_equity = equity_df['equity'].iloc[0]

        for equity in equity_df['equity']:
            if equity > max_equity:
                max_equity = equity

            drawdown = ((max_equity - equity) / max_equity) * 100 if max_equity > 0 else 0
            drawdowns.append(drawdown)

        df = equity_df.copy()
        df['drawdown_pct'] = drawdowns

        return df[['drawdown_pct']]

    def _create_trades_df(self, result: BacktestResult) -> pd.DataFrame:
        """
        거래 내역 DataFrame 생성

        Args:
            result: 백테스팅 결과

        Returns:
            pd.DataFrame: 거래 내역
        """
        if not result.trades:
            return pd.DataFrame(columns=[
                'timestamp', 'side', 'price', 'amount', 'fee', 'balance', 'position'
            ])

        return pd.DataFrame(result.trades)

    def print_report(self, report: AnalysisReport):
        """
        분석 보고서 출력

        Args:
            report: 분석 보고서
        """
        result = report.backtest_result

        print("\n" + "="*80)
        print(f"📊 백테스팅 성과 분석 보고서")
        print("="*80)

        # 기본 정보
        print(f"\n📋 기본 정보")
        print(f"   전략: {result.strategy_name}")
        print(f"   심볼: {result.symbol}")
        print(f"   기간: {result.start_date} ~ {result.end_date}")
        print(f"   총 일수: {report.total_days}일 (거래 일수: {report.trading_days}일)")

        # 수익률
        print(f"\n💰 수익률")
        print(f"   초기 자본: {result.initial_capital:,.0f}원")
        print(f"   최종 자산: {result.final_capital:,.0f}원")
        print(f"   총 수익률: {report.total_return_pct:+.2f}%")
        print(f"   연환산 수익률: {report.annualized_return_pct:+.2f}%")

        if report.monthly_returns:
            print(f"\n   월별 수익률:")
            for month, ret in sorted(report.monthly_returns.items()):
                print(f"      {month}: {ret:+.2f}%")

        # 리스크 지표
        print(f"\n⚠️ 리스크 지표")
        print(f"   최대 낙폭 (MDD): {report.max_drawdown_pct:.2f}%")
        print(f"   변동성 (연환산): {report.volatility_pct:.2f}%")
        print(f"   샤프 비율: {report.sharpe_ratio:.2f}")
        print(f"   소르티노 비율: {report.sortino_ratio:.2f}")
        print(f"   칼마 비율: {report.calmar_ratio:.2f}")

        # 거래 분석
        print(f"\n📈 거래 분석")
        print(f"   총 거래 수: {result.total_trades}회")
        print(f"   승리 거래: {result.winning_trades}회")
        print(f"   손실 거래: {result.losing_trades}회")
        print(f"   승률: {report.win_rate_pct:.1f}%")
        print(f"   Profit Factor: {report.profit_factor:.2f}")
        print(f"   평균 승리: {report.avg_win_pct:+.2f}%")
        print(f"   평균 손실: {report.avg_loss_pct:.2f}%")
        print(f"   최대 연속 승: {report.max_consecutive_wins}회")
        print(f"   최대 연속 패: {report.max_consecutive_losses}회")
        print(f"   평균 보유 시간: {report.avg_holding_period:.1f}시간")

        print("\n" + "="*80)


if __name__ == "__main__":
    """
    테스트 코드
    """
    print("=== PerformanceAnalyzer 테스트 ===\n")

    # 간단한 더미 전략 (backtester.py에서 가져옴)
    class DummyStrategy:
        name = "Buy & Hold (Test)"

        def __init__(self):
            self.bought = False

        def generate_signal(self, candles):
            if len(candles) == 1 and not self.bought:
                self.bought = True
                return 'buy'
            elif len(candles) >= 10:
                return 'sell'
            return None

    # 더미 캔들 데이터
    import pandas as pd
    dates = pd.date_range('2024-01-01', periods=10, freq='1min')
    candles = pd.DataFrame({
        'open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 110],
        'high': [102, 103, 102, 104, 106, 105, 107, 109, 108, 111],
        'low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 109],
        'close': [101, 102, 101, 103, 105, 104, 106, 108, 107, 110],
        'volume': [1.0] * 10
    }, index=dates)

    # 백테스팅 실행
    from core.backtester import Backtester

    strategy = DummyStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=1000000,
        fee_rate=0.0005,
        slippage=0.001
    )

    result = backtester.run(candles, 'KRW-BTC')

    # 성과 분석
    analyzer = PerformanceAnalyzer(risk_free_rate=0.02)
    report = analyzer.analyze(result)

    # 보고서 출력
    analyzer.print_report(report)

    print("\n=== 테스트 완료 ===")
