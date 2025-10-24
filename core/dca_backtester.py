"""
DCA Backtester
DCA + 분할 익절/손절을 지원하는 백테스팅 엔진

기존 Backtester를 확장하여 다음 기능 추가:
- 신호가 기반 DCA 추가매수
- 다단계 익절 (Take Profit)
- 다단계 손절 (Stop Loss)
- 평균 단가 계산
"""

import uuid
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
from core.backtester import BacktestResult
from gui.dca_config import AdvancedDcaConfig

logger = logging.getLogger(__name__)


class DcaBacktester:
    """
    DCA 백테스팅 엔진

    DCA 전략과 분할 익절/손절을 시뮬레이션합니다.
    """

    def __init__(
        self,
        strategy,
        dca_config: AdvancedDcaConfig,
        initial_capital: float,
        fee_rate: float = 0.0005,  # 0.05%
        slippage: float = 0.001     # 0.1%
    ):
        """
        Args:
            strategy: 매수/매도 신호 전략
            dca_config: DCA 설정
            initial_capital: 초기 자금
            fee_rate: 거래 수수료율
            slippage: 슬리피지
        """
        self.strategy = strategy
        self.dca_config = dca_config
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage

        # 상태 변수
        self.cash = initial_capital
        self.position = 0.0  # 보유 수량
        self.avg_entry_price = None  # 평균 단가
        self.total_invested = 0.0  # 총 투자 금액
        self.signal_price = None  # DCA 기준 신호가

        # 실행 상태 추적
        self.executed_dca_levels = set()  # 실행된 DCA 레벨
        self.executed_tp_levels = set()   # 실행된 익절 레벨
        self.executed_sl_levels = set()   # 실행된 손절 레벨

        # 기록
        self.equity_curve = []
        self.trades = []

        logger.info(f"DCA 백테스터 초기화")
        logger.info(f"  초기 자금: {initial_capital:,.0f}원")
        logger.info(f"  DCA 레벨: {len(dca_config.levels)}개")
        logger.info(f"  익절 레벨: {len(dca_config.take_profit_levels) if dca_config.take_profit_levels else 1}개")
        logger.info(f"  손절 레벨: {len(dca_config.stop_loss_levels) if dca_config.stop_loss_levels else 1}개")

    def run(
        self,
        candles: pd.DataFrame,
        symbol: str
    ) -> BacktestResult:
        """
        백테스팅 실행

        Args:
            candles: 캔들 데이터 (pandas DataFrame)
            symbol: 심볼

        Returns:
            BacktestResult: 백테스팅 결과
        """
        logger.info(f"📊 DCA 백테스팅 시작: {symbol}")
        logger.info(f"   기간: {candles.index[0]} ~ {candles.index[-1]}")
        logger.info(f"   캔들 수: {len(candles):,}개")

        # 초기화
        self.cash = self.initial_capital
        self.position = 0.0
        self.avg_entry_price = None
        self.total_invested = 0.0
        self.signal_price = None
        self.executed_dca_levels.clear()
        self.executed_tp_levels.clear()
        self.executed_sl_levels.clear()
        self.equity_curve = []
        self.trades = []

        run_id = str(uuid.uuid4())

        # 캔들 순회
        for i in range(len(candles)):
            current_candle = candles.iloc[i]
            timestamp = candles.index[i]
            close_price = current_candle['close']

            # 현재 자산 가치 계산
            equity = self.cash + (self.position * close_price)
            self.equity_curve.append(equity)

            # 1. 매수 신호 체크 (포지션 없을 때만)
            if self.position == 0:
                signal = self._get_signal(candles.iloc[:i+1])
                if signal == 'buy' and self.cash >= self.dca_config.levels[0].order_amount:
                    # 초기 진입 (DCA Level 1)
                    self._execute_initial_entry(close_price, timestamp)
                    continue

            # 포지션이 있을 때 체크
            if self.position > 0 and self.avg_entry_price:
                # 2. 분할 익절 체크
                self._check_take_profit(close_price, timestamp)

                # 3. 분할 손절 체크
                self._check_stop_loss(close_price, timestamp)

                # 4. DCA 추가매수 체크
                self._check_dca_levels(close_price, timestamp)

        # 최종 청산 (포지션이 남아있으면)
        if self.position > 0:
            final_price = candles.iloc[-1]['close']
            final_timestamp = candles.index[-1]
            self._execute_order('sell', final_price, self.position, final_timestamp, "최종 청산")

        # 결과 생성
        result = self._generate_result(run_id, symbol, candles)

        logger.info(f"✅ DCA 백테스팅 완료")
        logger.info(f"   최종 자산: {result.final_capital:,.0f}원")
        logger.info(f"   수익률: {result.total_return:+.2f}%")
        logger.info(f"   총 거래: {result.total_trades}회")
        logger.info(f"   MDD: {result.max_drawdown:.2f}%")
        logger.info(f"   승률: {result.win_rate:.1f}%")

        return result

    def _get_signal(self, candles: pd.DataFrame) -> Optional[str]:
        """전략으로부터 매수/매도 신호 받기"""
        if hasattr(self.strategy, 'generate_signal'):
            return self.strategy.generate_signal(candles)
        return None

    def _execute_initial_entry(self, price: float, timestamp: datetime):
        """초기 진입 (DCA Level 1)"""
        level_1 = self.dca_config.levels[0]
        quantity = level_1.order_amount / price

        self._execute_order('buy', price, quantity, timestamp, "초기 진입")

        # 신호가 저장
        self.signal_price = price
        self.executed_dca_levels.add(1)

        logger.info(f"  🎯 초기 진입: {price:,.0f}원, 신호가 설정")

    def _check_dca_levels(self, current_price: float, timestamp: datetime):
        """DCA 추가매수 레벨 체크"""
        if not self.signal_price:
            return

        for level_config in self.dca_config.levels[1:]:  # Level 2부터
            level = level_config.level

            # 이미 실행된 레벨은 스킵
            if level in self.executed_dca_levels:
                continue

            # 목표 하락률 달성 확인
            target_price = self.signal_price * (1 - level_config.drop_pct / 100)

            if current_price <= target_price and self.cash >= level_config.order_amount:
                # DCA 추가매수 실행
                quantity = level_config.order_amount / current_price
                self._execute_order('buy', current_price, quantity, timestamp, f"DCA Level {level}")
                self.executed_dca_levels.add(level)

                logger.info(f"  📈 DCA Level {level} 실행: {level_config.drop_pct:.1f}% 하락, {level_config.order_amount:,}원 추가매수")

    def _check_take_profit(self, current_price: float, timestamp: datetime):
        """분할 익절 체크"""
        if not self.dca_config.is_multi_level_tp_enabled():
            # 단일 익절
            if 1 not in self.executed_tp_levels:
                target_price = self.avg_entry_price * (1 + self.dca_config.take_profit_pct / 100)
                if current_price >= target_price:
                    # 전량 익절
                    self._execute_order('sell', current_price, self.position, timestamp, "익절")
                    self.executed_tp_levels.add(1)
                    logger.info(f"  ✅ 익절 실행: +{self.dca_config.take_profit_pct:.1f}% 달성")
            return

        # 다단계 익절
        for tp in self.dca_config.take_profit_levels:
            level = tp.level

            if level in self.executed_tp_levels:
                continue

            target_price = self.avg_entry_price * (1 + tp.profit_pct / 100)

            if current_price >= target_price:
                # 부분 익절
                sell_quantity = self.position * (tp.sell_ratio / 100)
                self._execute_order('sell', current_price, sell_quantity, timestamp, f"익절 Level {level}")
                self.executed_tp_levels.add(level)

                logger.info(f"  ✅ 익절 Level {level} 실행: +{tp.profit_pct:.1f}% 달성, {tp.sell_ratio:.0f}% 매도")

    def _check_stop_loss(self, current_price: float, timestamp: datetime):
        """분할 손절 체크"""
        if not self.dca_config.is_multi_level_sl_enabled():
            # 단일 손절
            if 1 not in self.executed_sl_levels:
                target_price = self.avg_entry_price * (1 - self.dca_config.stop_loss_pct / 100)
                if current_price <= target_price:
                    # 전량 손절
                    self._execute_order('sell', current_price, self.position, timestamp, "손절")
                    self.executed_sl_levels.add(1)
                    logger.warning(f"  ⚠️ 손절 실행: -{self.dca_config.stop_loss_pct:.1f}% 하락")
            return

        # 다단계 손절
        for sl in self.dca_config.stop_loss_levels:
            level = sl.level

            if level in self.executed_sl_levels:
                continue

            target_price = self.avg_entry_price * (1 - sl.loss_pct / 100)

            if current_price <= target_price:
                # 부분 손절
                sell_quantity = self.position * (sl.sell_ratio / 100)
                self._execute_order('sell', current_price, sell_quantity, timestamp, f"손절 Level {level}")
                self.executed_sl_levels.add(level)

                logger.warning(f"  ⚠️ 손절 Level {level} 실행: -{sl.loss_pct:.1f}% 하락, {sl.sell_ratio:.0f}% 매도")

    def _execute_order(
        self,
        side: str,
        price: float,
        amount: float,
        timestamp: datetime,
        reason: str = ""
    ):
        """주문 실행"""
        # 슬리피지 적용
        if side == 'buy':
            execution_price = price * (1 + self.slippage)
        else:
            execution_price = price * (1 - self.slippage)

        # 거래 금액
        total_value = execution_price * amount

        # 수수료
        fee = total_value * self.fee_rate

        if side == 'buy':
            # 매수
            self.cash -= (total_value + fee)
            self.position += amount

            # 평균 단가 업데이트
            if self.avg_entry_price is None:
                self.avg_entry_price = execution_price
                self.total_invested = total_value
            else:
                new_invested = total_value
                new_avg_price = (self.total_invested + new_invested) / (self.position)
                self.avg_entry_price = new_avg_price
                self.total_invested += new_invested

            logger.debug(f"    매수: {amount:.8f} @ {execution_price:,.0f}원 ({reason})")

        else:
            # 매도
            self.cash += (total_value - fee)
            self.position -= amount

            # 전량 청산 시 초기화
            if self.position <= 0:
                self.avg_entry_price = None
                self.total_invested = 0
                self.signal_price = None
                self.executed_dca_levels.clear()
                self.executed_tp_levels.clear()
                self.executed_sl_levels.clear()

            logger.debug(f"    매도: {amount:.8f} @ {execution_price:,.0f}원 ({reason})")

        # 거래 기록
        trade = {
            'timestamp': timestamp,
            'side': side,
            'price': execution_price,
            'amount': amount,
            'fee': fee,
            'balance': self.cash,
            'position': self.position,
            'reason': reason
        }
        self.trades.append(trade)

    def _generate_result(
        self,
        run_id: str,
        symbol: str,
        candles: pd.DataFrame
    ) -> BacktestResult:
        """백테스팅 결과 생성"""
        final_capital = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        # 거래 통계 계산
        winning_trades = 0
        losing_trades = 0
        profits = []
        losses = []

        # 매수-매도 쌍 찾기
        buy_value = 0
        buy_amount = 0

        for trade in self.trades:
            if trade['side'] == 'buy':
                buy_value += trade['price'] * trade['amount']
                buy_amount += trade['amount']

            elif trade['side'] == 'sell' and buy_amount > 0:
                # 평균 매수가 계산
                avg_buy_price = buy_value / buy_amount if buy_amount > 0 else 0

                # 손익 계산
                profit = (trade['price'] - avg_buy_price) * trade['amount'] - trade['fee']

                if profit > 0:
                    winning_trades += 1
                    profits.append(profit)
                else:
                    losing_trades += 1
                    losses.append(abs(profit))

                # 부분 매도인 경우 비례 차감
                buy_amount -= trade['amount']
                if buy_amount > 0:
                    buy_value = avg_buy_price * buy_amount
                else:
                    buy_value = 0

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
        """최대 낙폭 (MDD) 계산"""
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
        """샤프 비율 계산"""
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
        daily_rf = (1 + risk_free_rate) ** (1/365) - 1
        sharpe = (avg_return - daily_rf) / std_dev
        sharpe_annualized = sharpe * (252 ** 0.5)

        return sharpe_annualized
