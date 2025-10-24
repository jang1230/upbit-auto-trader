"""
순수 전략 백테스터 (DCA 없이)
전략 신호만 따라 매매하여 전략 성능을 정확히 비교
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
from core.historical_data import HistoricalDataFetcher
from core.strategies import (
    BollingerBands_Strategy,
    RSI_Strategy,
    MACD_Strategy
)

# 로깅 설정
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)


class PureStrategyBacktester:
    """순수 전략 백테스터 (DCA 없이 신호만 따름)"""
    
    def __init__(self, initial_capital: float = 1000000, fee_rate: float = 0.0005):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        
    def run(self, strategy, candles: pd.DataFrame, symbol: str) -> Dict:
        """백테스팅 실행"""
        cash = self.initial_capital
        position = 0.0
        trades = []
        equity_curve = []
        
        # 캔들 순회
        for i in range(len(candles)):
            current_candles = candles.iloc[:i+1]
            current_price = candles.iloc[i]['close']
            
            # 최소 데이터 확인
            if len(current_candles) < 50:
                equity = cash + (position * current_price)
                equity_curve.append(equity)
                continue
            
            # 전략 신호 생성
            signal = strategy.generate_signal(current_candles)
            
            # 매수 신호
            if signal == 'buy' and position == 0 and cash > 0:
                # 전액 매수
                amount = (cash * 0.99) / current_price  # 99% 사용 (수수료 여유)
                fee = (current_price * amount) * self.fee_rate
                
                cash -= (current_price * amount + fee)
                position = amount
                
                trades.append({
                    'timestamp': candles.index[i],
                    'side': 'buy',
                    'price': current_price,
                    'amount': amount,
                    'fee': fee
                })
            
            # 매도 신호
            elif signal == 'sell' and position > 0:
                # 전량 매도
                amount = position
                fee = (current_price * amount) * self.fee_rate
                
                cash += (current_price * amount - fee)
                position = 0
                
                trades.append({
                    'timestamp': candles.index[i],
                    'side': 'sell',
                    'price': current_price,
                    'amount': amount,
                    'fee': fee
                })
            
            # 자산 가치 기록
            equity = cash + (position * current_price)
            equity_curve.append(equity)
        
        # 최종 청산 (포지션 남아있으면)
        if position > 0:
            final_price = candles.iloc[-1]['close']
            fee = (final_price * position) * self.fee_rate
            cash += (final_price * position - fee)
            
            trades.append({
                'timestamp': candles.index[-1],
                'side': 'sell',
                'price': final_price,
                'amount': position,
                'fee': fee
            })
            
            position = 0
        
        # 최종 자산
        final_capital = cash + (position * candles.iloc[-1]['close'])
        
        # 결과 계산
        return self._calculate_results(
            strategy.name,
            symbol,
            candles,
            final_capital,
            trades,
            equity_curve
        )
    
    def _calculate_results(
        self,
        strategy_name: str,
        symbol: str,
        candles: pd.DataFrame,
        final_capital: float,
        trades: List[Dict],
        equity_curve: List[float]
    ) -> Dict:
        """결과 계산"""
        
        total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100
        
        # 거래 통계
        buy_trades = [t for t in trades if t['side'] == 'buy']
        sell_trades = [t for t in trades if t['side'] == 'sell']
        
        # 승/패 계산
        winning_trades = 0
        losing_trades = 0
        profits = []
        losses = []
        
        for i in range(min(len(buy_trades), len(sell_trades))):
            buy_price = buy_trades[i]['price']
            sell_price = sell_trades[i]['price']
            profit = (sell_price - buy_price) * buy_trades[i]['amount']
            
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
        max_drawdown = self._calculate_mdd(equity_curve)
        
        # 샤프 비율
        sharpe_ratio = self._calculate_sharpe(equity_curve)
        
        return {
            'strategy_name': strategy_name,
            'symbol': symbol,
            'start_date': candles.index[0],
            'end_date': candles.index[-1],
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'trades': trades,
            'equity_curve': equity_curve
        }
    
    def _calculate_mdd(self, equity_curve: List[float]) -> float:
        """최대 낙폭 계산"""
        if not equity_curve:
            return 0.0
        
        max_equity = equity_curve[0]
        max_dd = 0.0
        
        for equity in equity_curve:
            if equity > max_equity:
                max_equity = equity
            
            dd = ((max_equity - equity) / max_equity) * 100
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_sharpe(self, equity_curve: List[float], rf_rate: float = 0.02) -> float:
        """샤프 비율 계산"""
        if len(equity_curve) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        daily_rf = (1 + rf_rate) ** (1/365) - 1
        sharpe = (avg_return - daily_rf) / std_dev
        sharpe_annualized = sharpe * (252 ** 0.5)
        
        return sharpe_annualized


# 메인 실행
if __name__ == "__main__":
    print("=" * 80)
    print("📊 순수 전략 비교 백테스팅 (DCA 없이)")
    print("=" * 80)
    
    # 데이터 로딩
    print("\n📊 데이터 로딩 중...")
    fetcher = HistoricalDataFetcher()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    candles = fetcher.fetch_candles(
        symbol='KRW-BTC',
        start_date=start_date,
        end_date=end_date,
        interval='minute1',
        use_cache=True
    )
    
    print(f"✅ {len(candles):,}개 캔들 로드 완료")
    print(f"   기간: {candles.index[0]} ~ {candles.index[-1]}")
    
    # 전략 정의
    strategies = [
        ('BB (std=2.5)', BollingerBands_Strategy(period=20, std_dev=2.5)),
        ('BB (std=2.0)', BollingerBands_Strategy(period=20, std_dev=2.0)),
        ('BB (std=1.5)', BollingerBands_Strategy(period=20, std_dev=1.5)),
        ('RSI (30/70)', RSI_Strategy(period=14, oversold=30, overbought=70)),
        ('RSI (40/60)', RSI_Strategy(period=14, oversold=40, overbought=60)),
        ('MACD (12/26/9)', MACD_Strategy(fast_period=12, slow_period=26, signal_period=9))
    ]
    
    # 백테스팅 실행
    print("\n" + "=" * 80)
    print("🔬 전략별 백테스팅 실행 중...")
    print("=" * 80)
    
    backtester = PureStrategyBacktester(initial_capital=1000000)
    results = []
    
    for i, (name, strategy) in enumerate(strategies, 1):
        print(f"\n[{i}/{len(strategies)}] {name}")
        print("-" * 80)
        
        result = backtester.run(strategy, candles, 'KRW-BTC')
        results.append((name, result))
        
        print(f"  수익률: {result['total_return']:+.2f}%")
        print(f"  MDD: {result['max_drawdown']:.2f}%")
        print(f"  총 거래: {result['total_trades']}회 (매수 {result['buy_trades']}회, 매도 {result['sell_trades']}회)")
        print(f"  승률: {result['win_rate']:.1f}% ({result['winning_trades']}승 {result['losing_trades']}패)")
    
    # 결과 비교
    print("\n" + "=" * 80)
    print("📊 전략 비교 결과")
    print("=" * 80)
    
    print(f"\n{'전략':<20} {'수익률':>10} {'MDD':>8} {'거래':>8} {'승률':>8} {'샤프':>8}")
    print("-" * 80)
    
    for name, r in results:
        print(f"{name:<20} {r['total_return']:>9.2f}% {r['max_drawdown']:>7.2f}% "
              f"{r['total_trades']:>7}회 {r['win_rate']:>7.1f}% {r['sharpe_ratio']:>8.2f}")
    
    # 최고 성과
    print("\n" + "=" * 80)
    print("🏆 최고 성과 전략")
    print("=" * 80)
    
    best_return = max(results, key=lambda x: x[1]['total_return'])
    most_trades = max(results, key=lambda x: x[1]['total_trades'])
    best_winrate = max(results, key=lambda x: x[1]['win_rate'])
    
    print(f"\n최고 수익률: {best_return[0]}")
    print(f"  수익률: {best_return[1]['total_return']:+.2f}%")
    print(f"  거래 수: {best_return[1]['total_trades']}회")
    
    print(f"\n가장 활발한 거래: {most_trades[0]}")
    print(f"  총 거래: {most_trades[1]['total_trades']}회")
    print(f"  수익률: {most_trades[1]['total_return']:+.2f}%")
    
    print(f"\n최고 승률: {best_winrate[0]}")
    print(f"  승률: {best_winrate[1]['win_rate']:.1f}%")
    print(f"  수익률: {best_winrate[1]['total_return']:+.2f}%")
    
    print("\n" + "=" * 80)
    print("✅ 순수 전략 비교 완료!")
    print("=" * 80)
