"""
백테스팅 엔진
Backtest Engine

전략을 과거 데이터에 대해 시뮬레이션하여 성과를 측정합니다.

Example:
    >>> from core.strategies import ProximityBollingerBandsStrategy
    >>> strategy = ProximityBollingerBandsStrategy(symbol='KRW-BTC')
    >>> engine = BacktestEngine(strategy, initial_capital=1000000)
    >>> results = engine.run(candles_df)
    >>> print(results.summary())
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Trade:
    """단일 거래 기록"""
    
    def __init__(
        self,
        timestamp: datetime,
        side: str,  # 'buy' or 'sell'
        price: float,
        quantity: float,
        fee_rate: float = 0.0005
    ):
        self.timestamp = timestamp
        self.side = side
        self.price = price
        self.quantity = quantity
        self.fee_rate = fee_rate
        self.fee = price * quantity * fee_rate
        self.total = price * quantity + (self.fee if side == 'buy' else -self.fee)
    
    def __repr__(self):
        return f"Trade({self.side.upper()} {self.quantity:.8f} @ {self.price:,.0f}원, fee={self.fee:,.0f}원)"


class BacktestResult:
    """백테스트 결과"""
    
    def __init__(
        self,
        strategy_name: str,
        symbol: str,
        initial_capital: float,
        final_capital: float,
        trades: List[Trade],
        equity_curve: pd.Series,
        start_time: datetime,
        end_time: datetime
    ):
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.final_capital = final_capital
        self.trades = trades
        self.equity_curve = equity_curve
        self.start_time = start_time
        self.end_time = end_time
        
        # 성과 지표 계산
        self._calculate_metrics()
    
    def _calculate_metrics(self):
        """성과 지표 계산"""
        self.total_return = ((self.final_capital - self.initial_capital) / self.initial_capital) * 100
        self.total_trades = len(self.trades) // 2  # 매수+매도 = 1거래
        
        # 승률 계산
        winning_trades = 0
        losing_trades = 0
        
        for i in range(0, len(self.trades) - 1, 2):
            if i + 1 < len(self.trades):
                buy_trade = self.trades[i]
                sell_trade = self.trades[i + 1]
                
                if buy_trade.side == 'buy' and sell_trade.side == 'sell':
                    pnl = (sell_trade.price - buy_trade.price) * buy_trade.quantity
                    pnl -= (buy_trade.fee + sell_trade.fee)
                    
                    if pnl > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
        
        self.winning_trades = winning_trades
        self.losing_trades = losing_trades
        self.win_rate = (winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        # MDD (Maximum Drawdown) 계산
        peak = self.equity_curve.expanding().max()
        drawdown = (self.equity_curve - peak) / peak * 100
        self.max_drawdown = drawdown.min()
        
        # Sharpe Ratio (단순화)
        returns = self.equity_curve.pct_change().dropna()
        if len(returns) > 0 and returns.std() != 0:
            self.sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # 연환산
        else:
            self.sharpe_ratio = 0
    
    def summary(self) -> str:
        """결과 요약"""
        duration = (self.end_time - self.start_time).days
        
        summary = f"""
{'=' * 80}
백테스트 결과 요약
{'=' * 80}

전략: {self.strategy_name}
심볼: {self.symbol}
기간: {self.start_time.strftime('%Y-%m-%d')} ~ {self.end_time.strftime('%Y-%m-%d')} ({duration}일)

💰 자본 변화:
   시작: {self.initial_capital:,.0f}원
   종료: {self.final_capital:,.0f}원
   수익률: {self.total_return:+.2f}%

📊 거래 통계:
   총 거래: {self.total_trades}회
   승리: {self.winning_trades}회
   패배: {self.losing_trades}회
   승률: {self.win_rate:.1f}%

📈 성과 지표:
   MDD: {self.max_drawdown:.2f}%
   Sharpe Ratio: {self.sharpe_ratio:.2f}

🔍 최근 5개 거래:
"""
        for trade in self.trades[-10:]:
            summary += f"   {trade}\n"
        
        summary += "=" * 80
        return summary


class BacktestEngine:
    """
    백테스팅 엔진
    
    전략을 과거 데이터에 대해 시뮬레이션합니다.
    """
    
    def __init__(
        self,
        strategy,
        initial_capital: float = 1000000,
        fee_rate: float = 0.0005,
        slippage: float = 0.001
    ):
        """
        Args:
            strategy: 백테스트할 전략 인스턴스
            initial_capital: 초기 자본 (원)
            fee_rate: 수수료율 (기본 0.05%)
            slippage: 슬리피지 (기본 0.1%)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        
        # 상태 변수
        self.cash = initial_capital
        self.position = 0  # 보유 수량
        self.avg_entry_price = 0  # 평균 진입 가격
        self.trades: List[Trade] = []
        self.equity_curve = []
        
        logger.info(f"백테스트 엔진 초기화: {strategy.name}, 자본={initial_capital:,.0f}원")
    
    def run(self, candles: pd.DataFrame) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            candles: OHLCV 데이터
        
        Returns:
            BacktestResult: 백테스트 결과
        """
        logger.info(f"🚀 백테스트 시작: {len(candles)}개 캔들")
        
        # 초기화
        self.cash = self.initial_capital
        self.position = 0
        self.avg_entry_price = 0
        self.trades = []
        self.equity_curve = []
        
        # 전략 리셋
        self.strategy.reset()
        
        # 캔들별 처리
        for i in range(len(candles)):
            # 현재까지의 캔들 데이터
            current_candles = candles.iloc[:i+1]
            
            # 최소 데이터 확보 확인
            if len(current_candles) < 250:  # MA240 + 여유
                continue
            
            # 현재 가격
            current_price = current_candles.iloc[-1]['close']
            current_time = current_candles.index[-1]
            
            # 전략 신호 생성
            signal = self.strategy.generate_signal(current_candles, current_time)
            
            # 신호 처리
            if signal == 'buy' and self.position == 0:
                self._execute_buy(current_price, current_time)
            elif signal == 'sell' and self.position > 0:
                self._execute_sell(current_price, current_time)
            
            # 자산 가치 기록
            portfolio_value = self.cash + (self.position * current_price if self.position > 0 else 0)
            self.equity_curve.append({
                'timestamp': current_time,
                'value': portfolio_value
            })
        
        # 마지막 포지션 정리
        if self.position > 0:
            final_price = candles.iloc[-1]['close']
            final_time = candles.index[-1]
            self._execute_sell(final_price, final_time)
            logger.info(f"⚠️ 백테스트 종료 시 포지션 강제 청산")
        
        # 결과 생성
        equity_df = pd.DataFrame(self.equity_curve).set_index('timestamp')
        
        result = BacktestResult(
            strategy_name=self.strategy.name,
            symbol=self.strategy.symbol,
            initial_capital=self.initial_capital,
            final_capital=self.cash + (self.position * candles.iloc[-1]['close']),
            trades=self.trades,
            equity_curve=equity_df['value'],
            start_time=candles.index[0],
            end_time=candles.index[-1]
        )
        
        logger.info(f"✅ 백테스트 완료: {result.total_trades}회 거래, 수익률 {result.total_return:+.2f}%")
        
        return result
    
    def _execute_buy(self, price: float, timestamp: datetime):
        """매수 실행"""
        # 슬리피지 적용
        actual_price = price * (1 + self.slippage)
        
        # 매수 가능 수량 계산
        quantity = self.cash / actual_price
        
        if quantity <= 0:
            return
        
        # 거래 실행
        trade = Trade(timestamp, 'buy', actual_price, quantity, self.fee_rate)
        self.trades.append(trade)
        
        # 상태 업데이트
        self.cash -= trade.total
        self.position = quantity
        self.avg_entry_price = actual_price
        
        logger.debug(f"   💰 매수: {quantity:.8f} @ {actual_price:,.0f}원 (잔고: {self.cash:,.0f}원)")
    
    def _execute_sell(self, price: float, timestamp: datetime):
        """매도 실행"""
        if self.position <= 0:
            return
        
        # 슬리피지 적용
        actual_price = price * (1 - self.slippage)
        
        # 거래 실행
        trade = Trade(timestamp, 'sell', actual_price, self.position, self.fee_rate)
        self.trades.append(trade)
        
        # 수익률 계산
        profit_pct = ((actual_price - self.avg_entry_price) / self.avg_entry_price) * 100
        
        # 상태 업데이트
        self.cash += trade.total
        self.position = 0
        self.avg_entry_price = 0
        
        logger.debug(f"   💸 매도: {trade.quantity:.8f} @ {actual_price:,.0f}원 (수익률: {profit_pct:+.2f}%, 잔고: {self.cash:,.0f}원)")


if __name__ == "__main__":
    """테스트 코드"""
    print("=" * 80)
    print("백테스트 엔진 테스트")
    print("=" * 80)
    print("실제 테스트는 run_backtest.py에서 실행하세요")
    print("=" * 80)
