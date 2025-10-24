"""
백테스팅 엔진 모듈
과거 데이터로 전략 시뮬레이션

주요 기능:
- 캔들 데이터 순회 및 전략 실행
- 가상 주문 실행 (수수료, 슬리피지 포함)
- 포지션 및 자금 관리
- 성과 기록 및 분석
"""

import uuid
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
from core.risk_manager import RiskManager

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """백테스팅 결과 데이터 클래스"""

    # 기본 정보
    run_id: str
    symbol: str
    strategy_name: str
    start_date: datetime
    end_date: datetime

    # 자금 정보
    initial_capital: float
    final_capital: float
    total_return: float  # %

    # 성과 지표
    max_drawdown: float  # %
    sharpe_ratio: float
    win_rate: float  # %

    # 거래 통계
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_profit: float
    avg_loss: float

    # 시계열 데이터
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)


class Backtester:
    """
    백테스팅 엔진

    과거 캔들 데이터를 순회하며 전략을 시뮬레이션합니다.
    """

    def __init__(
        self,
        strategy,
        initial_capital: float,
        fee_rate: float = 0.0005,  # 0.05%
        slippage: float = 0.001,    # 0.1%
        risk_manager: Optional[RiskManager] = None
    ):
        """
        Args:
            strategy: 전략 객체 (Phase 2에서 구현)
                      .generate_signal(candles) 메서드 필요
            initial_capital: 초기 자금
            fee_rate: 거래 수수료율 (0.0005 = 0.05%)
            slippage: 슬리피지 (0.001 = 0.1%)
            risk_manager: 리스크 관리자 (Optional)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.risk_manager = risk_manager

        # 상태 변수
        self.cash = initial_capital  # 현금 잔액
        self.position = 0.0           # 보유 수량 (BTC)
        self.equity_curve = []        # 자산 가치 시계열
        self.trades = []              # 거래 내역
        self.risk_exits = []          # 리스크 관리로 인한 청산 기록

        logger.info(f"백테스터 초기화: 초기 자금 {initial_capital:,.0f}원")
        if risk_manager:
            logger.info(f"  리스크 관리: 활성화 (SL: -{risk_manager.stop_loss_pct}%, TP: +{risk_manager.take_profit_pct}%)")

    def run(
        self,
        candles: pd.DataFrame,
        symbol: str
    ) -> BacktestResult:
        """
        백테스팅 실행

        Args:
            candles: 캔들 데이터 (pandas DataFrame)
                     index: timestamp
                     columns: open, high, low, close, volume
            symbol: 심볼 (예: 'KRW-BTC')

        Returns:
            BacktestResult: 백테스팅 결과
        """
        logger.info(f"📊 백테스팅 시작: {symbol}")
        logger.info(f"   기간: {candles.index[0]} ~ {candles.index[-1]}")
        logger.info(f"   캔들 수: {len(candles):,}개")

        # 초기화
        self.cash = self.initial_capital
        self.position = 0.0
        self.equity_curve = []
        self.trades = []
        self.risk_exits = []

        run_id = str(uuid.uuid4())

        # 캔들 순회
        for i in range(len(candles)):
            current_candle = candles.iloc[i]
            timestamp = candles.index[i]
            close_price = current_candle['close']

            # 현재 자산 가치 계산
            equity = self.cash + (self.position * close_price)

            # 리스크 관리 체크 (포지션이 있을 때만)
            if self.risk_manager and self.position > 0:
                should_exit, exit_reason = self.risk_manager.should_exit_position(
                    close_price, equity, timestamp
                )

                if should_exit:
                    # 리스크 관리로 인한 강제 청산
                    self._execute_order('sell', close_price, self.position, timestamp)
                    self.risk_exits.append({
                        'timestamp': timestamp,
                        'reason': exit_reason,
                        'price': close_price
                    })
                    logger.info(f"  리스크 관리 청산: {exit_reason}")
                    continue

            # 전략 신호 생성
            signal = self._get_signal(candles.iloc[:i+1])

            # 신호에 따라 주문 실행
            if signal == 'buy' and self.cash > 0:
                # 전액 매수
                amount = self.cash / close_price
                self._execute_order('buy', close_price, amount, timestamp)

                # 리스크 관리자에 진입 가격 설정
                if self.risk_manager:
                    self.risk_manager.set_entry_price(close_price)

            elif signal == 'sell' and self.position > 0:
                # 전량 매도
                self._execute_order('sell', close_price, self.position, timestamp)

                # 리스크 관리자 포지션 초기화
                if self.risk_manager:
                    self.risk_manager.reset_position()

            # 현재 자산 가치 기록
            self.equity_curve.append(equity)

        # 결과 생성
        result = self._generate_result(run_id, symbol, candles)

        logger.info(f"✅ 백테스팅 완료")
        logger.info(f"   최종 자산: {result.final_capital:,.0f}원")
        logger.info(f"   수익률: {result.total_return:+.2f}%")
        logger.info(f"   총 거래: {result.total_trades}회")

        return result

    def _get_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """
        전략으로부터 매수/매도 신호 받기

        Args:
            candles: 현재까지의 캔들 데이터

        Returns:
            'buy', 'sell', None
        """
        # Phase 2에서 전략 객체 구현 후 연동
        # 현재는 None 반환 (신호 없음)

        if hasattr(self.strategy, 'generate_signal'):
            return self.strategy.generate_signal(candles)

        return None

    def _execute_order(
        self,
        side: str,
        price: float,
        amount: float,
        timestamp: datetime
    ):
        """
        가상 주문 실행

        Args:
            side: 'buy' or 'sell'
            price: 주문 가격
            amount: 주문 수량
            timestamp: 주문 시각
        """
        # 슬리피지 적용
        if side == 'buy':
            execution_price = price * (1 + self.slippage)
        else:
            execution_price = price * (1 - self.slippage)

        # 거래 금액
        total_value = execution_price * amount

        # 수수료 계산
        fee = total_value * self.fee_rate

        if side == 'buy':
            # 매수
            self.cash -= (total_value + fee)
            self.position += amount

            logger.debug(f"매수: {amount:.8f} @ {execution_price:,.0f}원 (수수료: {fee:,.0f}원)")

        else:
            # 매도
            self.cash += (total_value - fee)
            self.position -= amount

            logger.debug(f"매도: {amount:.8f} @ {execution_price:,.0f}원 (수수료: {fee:,.0f}원)")

        # 거래 내역 기록
        trade = {
            'timestamp': timestamp,
            'side': side,
            'price': execution_price,
            'amount': amount,
            'fee': fee,
            'balance': self.cash,
            'position': self.position
        }
        self.trades.append(trade)

    def _generate_result(
        self,
        run_id: str,
        symbol: str,
        candles: pd.DataFrame
    ) -> BacktestResult:
        """
        백테스팅 결과 생성

        Args:
            run_id: 백테스팅 실행 ID
            symbol: 심볼
            candles: 캔들 데이터

        Returns:
            BacktestResult
        """
        final_capital = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        # 거래 통계 계산
        winning_trades = 0
        losing_trades = 0
        profits = []
        losses = []

        for i in range(1, len(self.trades)):
            prev_trade = self.trades[i-1]
            curr_trade = self.trades[i]

            # 매수 → 매도 쌍 찾기
            if prev_trade['side'] == 'buy' and curr_trade['side'] == 'sell':
                buy_value = prev_trade['price'] * prev_trade['amount']
                sell_value = curr_trade['price'] * curr_trade['amount']
                profit = sell_value - buy_value - prev_trade['fee'] - curr_trade['fee']

                if profit > 0:
                    winning_trades += 1
                    profits.append(profit)
                else:
                    losing_trades += 1
                    losses.append(abs(profit))

        win_rate = (winning_trades / max(winning_trades + losing_trades, 1)) * 100
        avg_profit = sum(profits) / max(len(profits), 1) if profits else 0
        avg_loss = sum(losses) / max(len(losses), 1) if losses else 0

        # MDD 계산
        max_drawdown = self._calculate_max_drawdown(self.equity_curve)

        # 샤프 비율 계산
        sharpe_ratio = self._calculate_sharpe_ratio(self.equity_curve)

        return BacktestResult(
            run_id=run_id,
            symbol=symbol,
            strategy_name=getattr(self.strategy, 'name', 'Unknown'),
            start_date=candles.index[0],
            end_date=candles.index[-1],
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=len(self.trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            equity_curve=self.equity_curve,
            trades=self.trades
        )

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        최대 낙폭 (MDD) 계산

        Args:
            equity_curve: 자산 가치 시계열

        Returns:
            float: MDD (%)
        """
        if not equity_curve:
            return 0.0

        max_equity = equity_curve[0]
        max_dd = 0.0

        for equity in equity_curve:
            if equity > max_equity:
                max_equity = equity

            drawdown = ((max_equity - equity) / max_equity) * 100
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_sharpe_ratio(
        self,
        equity_curve: List[float],
        risk_free_rate: float = 0.02
    ) -> float:
        """
        샤프 비율 계산

        Args:
            equity_curve: 자산 가치 시계열
            risk_free_rate: 무위험 수익률 (연율)

        Returns:
            float: 샤프 비율
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
        avg_return = sum(returns) / len(returns)

        # 표준편차
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        # 샤프 비율 (연율화)
        # 일일 무위험 수익률
        daily_rf = (1 + risk_free_rate) ** (1/365) - 1

        sharpe = (avg_return - daily_rf) / std_dev

        # 연율화 (252 거래일 기준)
        sharpe_annualized = sharpe * (252 ** 0.5)

        return sharpe_annualized


if __name__ == "__main__":
    """
    테스트 코드
    """
    print("=== Backtester 테스트 ===\n")

    # 간단한 더미 전략 (Phase 2에서 실제 전략 구현)
    class DummyStrategy:
        name = "Buy & Hold (Test)"

        def __init__(self):
            self.bought = False

        def generate_signal(self, candles):
            # 첫 캔들에서 매수, 마지막 캔들에서 매도
            if len(candles) == 1 and not self.bought:
                self.bought = True
                return 'buy'
            elif len(candles) >= 10:  # 10번째 캔들에서 매도
                return 'sell'
            return None

    # 더미 캔들 데이터 생성
    dates = pd.date_range('2024-01-01', periods=10, freq='1min')
    candles = pd.DataFrame({
        'open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 110],
        'high': [102, 103, 102, 104, 106, 105, 107, 109, 108, 111],
        'low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 109],
        'close': [101, 102, 101, 103, 105, 104, 106, 108, 107, 110],
        'volume': [1.0] * 10
    }, index=dates)

    # 백테스팅 실행
    strategy = DummyStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=1000000,
        fee_rate=0.0005,
        slippage=0.001
    )

    result = backtester.run(candles, 'KRW-BTC')

    # 결과 출력
    print("\n=== 백테스팅 결과 ===")
    print(f"전략: {result.strategy_name}")
    print(f"기간: {result.start_date} ~ {result.end_date}")
    print(f"\n초기 자산: {result.initial_capital:,.0f}원")
    print(f"최종 자산: {result.final_capital:,.0f}원")
    print(f"수익률: {result.total_return:+.2f}%")
    print(f"\nMDD: {result.max_drawdown:.2f}%")
    print(f"샤프 비율: {result.sharpe_ratio:.2f}")
    print(f"승률: {result.win_rate:.1f}%")
    print(f"\n총 거래: {result.total_trades}회")
    print(f"승리 거래: {result.winning_trades}회")
    print(f"손실 거래: {result.losing_trades}회")

    print("\n=== 테스트 완료 ===")
