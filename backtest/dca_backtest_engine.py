"""
DCA (Dollar Cost Averaging) Backtest Engine
DCA 백테스트 엔진

단순화된 DCA 전략:
- 매수 신호 시 초기 매수 (자본의 1/6)
- 추가매수: -10%마다 동일 금액 (최대 5회 추가, 총 6회)
- 익절: 평단가 대비 +5%
- 손절: 평단가 대비 -7% (6회 모두 매수 완료 후)
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DCABuy:
    """DCA 매수 기록"""
    price: float
    quantity: float
    timestamp: datetime
    buy_number: int  # 1차, 2차, 3차...


@dataclass
class DCATrade:
    """DCA 거래 완료 기록"""
    entry_buys: List[DCABuy]
    exit_price: float
    exit_timestamp: datetime
    exit_type: str  # 'profit' or 'loss'
    pnl: float
    pnl_pct: float

    @property
    def avg_price(self) -> float:
        """평단가 계산"""
        total_cost = sum(buy.price * buy.quantity for buy in self.entry_buys)
        total_quantity = sum(buy.quantity for buy in self.entry_buys)
        return total_cost / total_quantity if total_quantity > 0 else 0


class DCAPosition:
    """DCA 포지션 관리"""

    def __init__(
        self,
        initial_buy_price: float,
        initial_quantity: float,
        initial_timestamp: datetime,
        max_buys: int = 6,
        buy_interval_pct: float = 10.0
    ):
        """
        DCA 포지션 초기화

        Args:
            initial_buy_price: 첫 매수가
            initial_quantity: 첫 매수량
            initial_timestamp: 첫 매수 시각
            max_buys: 최대 매수 횟수 (기본 6회)
            buy_interval_pct: 추가매수 간격 % (기본 -10%)
        """
        self.first_buy_price = initial_buy_price
        self.max_buys = max_buys
        self.buy_interval_pct = buy_interval_pct

        # 매수 기록
        self.buys: List[DCABuy] = [
            DCABuy(
                price=initial_buy_price,
                quantity=initial_quantity,
                timestamp=initial_timestamp,
                buy_number=1
            )
        ]

    @property
    def avg_price(self) -> float:
        """평단가 계산"""
        total_cost = sum(buy.price * buy.quantity for buy in self.buys)
        total_quantity = sum(buy.quantity for buy in self.buys)
        return total_cost / total_quantity if total_quantity > 0 else 0

    @property
    def total_quantity(self) -> float:
        """총 보유량"""
        return sum(buy.quantity for buy in self.buys)

    @property
    def total_cost(self) -> float:
        """총 투자금"""
        return sum(buy.price * buy.quantity for buy in self.buys)

    @property
    def buy_count(self) -> int:
        """매수 횟수"""
        return len(self.buys)

    def should_add_buy(self, current_price: float) -> bool:
        """추가매수 필요 여부 확인"""
        if self.buy_count >= self.max_buys:
            return False

        # 다음 추가매수 가격 계산
        next_buy_level = self.buy_count + 1  # 2, 3, 4, 5, 6
        target_drop_pct = (next_buy_level - 1) * self.buy_interval_pct
        target_price = self.first_buy_price * (1 - target_drop_pct / 100)

        return current_price <= target_price

    def add_buy(self, price: float, quantity: float, timestamp: datetime):
        """추가매수 실행"""
        self.buys.append(
            DCABuy(
                price=price,
                quantity=quantity,
                timestamp=timestamp,
                buy_number=self.buy_count + 1
            )
        )
        logger.debug(
            f"   추가매수 {self.buy_count}차: "
            f"가격={price:.0f}, 수량={quantity:.4f}, "
            f"평단가={self.avg_price:.0f}"
        )


class DCABacktestResult:
    """DCA 백테스트 결과"""

    def __init__(
        self,
        strategy_name: str,
        symbol: str,
        initial_capital: float,
        final_capital: float,
        trades: List[DCATrade],
        start_time: datetime,
        end_time: datetime
    ):
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.final_capital = final_capital
        self.trades = trades
        self.start_time = start_time
        self.end_time = end_time

    @property
    def total_return(self) -> float:
        """총 수익률 (%)"""
        return ((self.final_capital - self.initial_capital) / self.initial_capital) * 100

    @property
    def total_trades(self) -> int:
        """총 거래 횟수"""
        return len(self.trades)

    @property
    def winning_trades(self) -> int:
        """승리 거래 수"""
        return sum(1 for t in self.trades if t.pnl > 0)

    @property
    def losing_trades(self) -> int:
        """손실 거래 수"""
        return sum(1 for t in self.trades if t.pnl < 0)

    @property
    def win_rate(self) -> float:
        """승률 (%)"""
        return (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

    @property
    def avg_profit_trades(self) -> int:
        """익절 거래 수"""
        return sum(1 for t in self.trades if t.exit_type == 'profit')

    @property
    def avg_loss_trades(self) -> int:
        """손절 거래 수"""
        return sum(1 for t in self.trades if t.exit_type == 'loss')

    def print_summary(self):
        """결과 요약 출력"""
        print("\n" + "=" * 80)
        print("DCA 백테스트 결과 요약")
        print("=" * 80)
        print(f"\n전략: {self.strategy_name}")
        print(f"심볼: {self.symbol}")
        print(f"기간: {self.start_time.strftime('%Y-%m-%d')} ~ {self.end_time.strftime('%Y-%m-%d')} ({(self.end_time - self.start_time).days}일)")

        print(f"\n💰 자본 변화:")
        print(f"   시작: {self.initial_capital:,.0f}원")
        print(f"   종료: {self.final_capital:,.0f}원")
        print(f"   수익률: {self.total_return:+.2f}%")

        print(f"\n📊 거래 통계:")
        print(f"   총 거래: {self.total_trades}회")
        print(f"   익절: {self.avg_profit_trades}회")
        print(f"   손절: {self.avg_loss_trades}회")
        print(f"   승률: {self.win_rate:.1f}%")

        if self.trades:
            avg_buys = sum(len(t.entry_buys) for t in self.trades) / len(self.trades)
            print(f"   평균 분할매수 횟수: {avg_buys:.1f}회")

        print("\n" + "=" * 80)


class DCABacktestEngine:
    """DCA 백테스트 엔진"""

    def __init__(
        self,
        strategy,
        initial_capital: float = 1000000,
        profit_target_pct: float = 5.0,
        stop_loss_pct: float = -7.0,
        max_buys: int = 6,
        buy_interval_pct: float = 10.0,
        slippage: float = 0.001,  # 0.1%
        fee_rate: float = 0.0005  # 0.05%
    ):
        """
        DCA 백테스트 엔진 초기화

        Args:
            strategy: 매수 신호 생성 전략
            initial_capital: 초기 자본금
            profit_target_pct: 익절 목표 % (평단가 대비, 기본 +5%)
            stop_loss_pct: 손절 % (평단가 대비, 기본 -7%)
            max_buys: 최대 매수 횟수 (기본 6회)
            buy_interval_pct: 추가매수 간격 % (기본 -10%)
            slippage: 슬리피지 (기본 0.1%)
            fee_rate: 수수료율 (기본 0.05%)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_buys = max_buys
        self.buy_interval_pct = buy_interval_pct
        self.slippage = slippage
        self.fee_rate = fee_rate

        # 백테스트 상태
        self.cash = initial_capital
        self.position: Optional[DCAPosition] = None
        self.trades: List[DCATrade] = []

        logger.info(
            f"DCA 백테스트 엔진 초기화: "
            f"익절={profit_target_pct}%, 손절={stop_loss_pct}%, "
            f"분할={max_buys}회 (-{buy_interval_pct}%마다)"
        )

    def _execute_initial_buy(self, price: float, timestamp: datetime):
        """초기 매수 실행"""
        # 자본을 max_buys로 나눔 (6분할)
        buy_amount = self.initial_capital / self.max_buys

        # 슬리피지 적용
        actual_price = price * (1 + self.slippage)

        # 수수료 차감 후 매수 가능 수량
        fee = buy_amount * self.fee_rate
        quantity = (buy_amount - fee) / actual_price

        # 포지션 생성
        self.position = DCAPosition(
            initial_buy_price=actual_price,
            initial_quantity=quantity,
            initial_timestamp=timestamp,
            max_buys=self.max_buys,
            buy_interval_pct=self.buy_interval_pct
        )

        self.cash -= buy_amount

        logger.info(
            f"   💵 1차 매수: 가격={actual_price:.0f}, "
            f"수량={quantity:.4f}, 투자={buy_amount:,.0f}원"
        )

    def _execute_additional_buy(self, price: float, timestamp: datetime):
        """추가매수 실행"""
        if not self.position:
            return

        # 동일 금액으로 추가매수
        buy_amount = self.initial_capital / self.max_buys

        # 슬리피지 적용
        actual_price = price * (1 + self.slippage)

        # 수수료 차감 후 매수 가능 수량
        fee = buy_amount * self.fee_rate
        quantity = (buy_amount - fee) / actual_price

        self.position.add_buy(actual_price, quantity, timestamp)
        self.cash -= buy_amount

    def _execute_sell(self, price: float, timestamp: datetime, exit_type: str):
        """매도 실행"""
        if not self.position:
            return

        # 슬리피지 적용
        actual_price = price * (1 - self.slippage)

        # 전량 매도
        sell_amount = self.position.total_quantity * actual_price
        fee = sell_amount * self.fee_rate
        proceeds = sell_amount - fee

        # 손익 계산
        pnl = proceeds - self.position.total_cost
        pnl_pct = (pnl / self.position.total_cost) * 100

        # 거래 기록
        trade = DCATrade(
            entry_buys=self.position.buys.copy(),
            exit_price=actual_price,
            exit_timestamp=timestamp,
            exit_type=exit_type,
            pnl=pnl,
            pnl_pct=pnl_pct
        )
        self.trades.append(trade)

        self.cash += proceeds

        logger.info(
            f"   {'💰 익절' if exit_type == 'profit' else '🛑 손절'}: "
            f"평단가={self.position.avg_price:.0f}, "
            f"매도가={actual_price:.0f}, "
            f"손익={pnl:+,.0f}원 ({pnl_pct:+.2f}%)"
        )

        # 포지션 종료
        self.position = None

    def run(self, candles: pd.DataFrame) -> DCABacktestResult:
        """백테스트 실행"""
        logger.info(f"🚀 DCA 백테스트 시작: {len(candles)}개 캔들")

        # 전략 초기화
        self.strategy.reset()

        for i in range(len(candles)):
            current_candles = candles.iloc[:i+1]
            current_time = candles.index[i]
            current_price = candles['close'].iloc[i]

            # 포지션 없음 → 매수 신호 대기
            if self.position is None:
                signal = self.strategy.generate_signal(current_candles, current_time)

                if signal == 'buy':
                    self._execute_initial_buy(current_price, current_time)

            # 포지션 있음 → 추가매수/익절/손절 체크
            else:
                # 1. 추가매수 체크 (먼저 실행)
                if self.position.should_add_buy(current_price):
                    self._execute_additional_buy(current_price, current_time)

                # 2. 익절 체크 (평단가 대비 +5%)
                avg_price = self.position.avg_price
                profit_pct = ((current_price - avg_price) / avg_price) * 100

                if profit_pct >= self.profit_target_pct:
                    self._execute_sell(current_price, current_time, 'profit')
                    continue

                # 3. 손절 체크 (6회 모두 매수 완료 후, 평단가 대비 -7%)
                if self.position.buy_count >= self.max_buys:
                    if profit_pct <= self.stop_loss_pct:
                        self._execute_sell(current_price, current_time, 'loss')

        # 백테스트 종료 시 포지션 강제 청산
        if self.position is not None:
            logger.warning("⚠️ 백테스트 종료 시 포지션 강제 청산")
            self._execute_sell(candles['close'].iloc[-1], candles.index[-1], 'loss')

        final_capital = self.cash

        logger.info(
            f"✅ DCA 백테스트 완료: {len(self.trades)}회 거래, "
            f"수익률 {((final_capital - self.initial_capital) / self.initial_capital * 100):+.2f}%"
        )

        return DCABacktestResult(
            strategy_name=self.strategy.name,
            symbol=getattr(self.strategy, 'symbol', 'UNKNOWN'),
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            trades=self.trades,
            start_time=candles.index[0],
            end_time=candles.index[-1]
        )
