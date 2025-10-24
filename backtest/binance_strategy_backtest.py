"""
Binance-Style Strategy Backtest Runner
바이낸스 스타일 전략 백테스트 실행기

5가지 이상의 매도 조건으로 백테스트:
1. 고정 익절 (3%, 5%, 7%)
2. 고정 손절 (-3%, -5%, -7%)
3. 트레일링 스톱
4. 멀티레벨 익절 (DCA 스타일)
5. 시간 기반 매도
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import sys
from typing import Dict, List, Tuple
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategies.binance_multi_signal_strategy import BinanceMultiSignalStrategy


class ExitCondition:
    """매도 조건 베이스 클래스"""
    
    def __init__(self, name: str):
        self.name = name
    
    def should_exit(
        self,
        entry_price: float,
        current_price: float,
        highest_price: float,
        entry_time: datetime,
        current_time: datetime
    ) -> bool:
        """매도 여부 판단"""
        raise NotImplementedError


class FixedProfitTarget(ExitCondition):
    """고정 익절 조건"""
    
    def __init__(self, target_pct: float):
        super().__init__(f"FixedTP_{target_pct}%")
        self.target_pct = target_pct
    
    def should_exit(self, entry_price, current_price, highest_price, entry_time, current_time):
        profit_pct = ((current_price - entry_price) / entry_price) * 100
        return profit_pct >= self.target_pct


class FixedStopLoss(ExitCondition):
    """고정 손절 조건"""
    
    def __init__(self, stop_pct: float):
        super().__init__(f"FixedSL_{abs(stop_pct)}%")
        self.stop_pct = stop_pct
    
    def should_exit(self, entry_price, current_price, highest_price, entry_time, current_time):
        loss_pct = ((current_price - entry_price) / entry_price) * 100
        return loss_pct <= self.stop_pct


class TrailingStop(ExitCondition):
    """트레일링 스톱 조건"""
    
    def __init__(self, trail_pct: float):
        super().__init__(f"Trailing_{trail_pct}%")
        self.trail_pct = trail_pct
    
    def should_exit(self, entry_price, current_price, highest_price, entry_time, current_time):
        if highest_price <= entry_price:
            return False  # 아직 수익 안남
        
        drawdown_from_peak = ((current_price - highest_price) / highest_price) * 100
        return drawdown_from_peak <= -self.trail_pct


class MultiLevelTakeProfit(ExitCondition):
    """멀티레벨 익절 (DCA 스타일)"""
    
    def __init__(self, levels: List[Tuple[float, float]]):
        """
        Args:
            levels: [(익절률, 비중), ...]
            예: [(3, 0.3), (5, 0.5), (7, 1.0)]  # 3%에 30%, 5%에 50%, 7%에 전부
        """
        super().__init__(f"MultiTP_{len(levels)}L")
        self.levels = sorted(levels, key=lambda x: x[0])  # 낮은 익절률부터
        self.current_level = 0
    
    def should_exit(self, entry_price, current_price, highest_price, entry_time, current_time):
        profit_pct = ((current_price - entry_price) / entry_price) * 100
        
        if self.current_level >= len(self.levels):
            return True  # 모두 매도 완료
        
        target_pct, _ = self.levels[self.current_level]
        if profit_pct >= target_pct:
            self.current_level += 1
            return self.current_level >= len(self.levels)  # 마지막 레벨이면 전부 매도
        
        return False
    
    def reset(self):
        """새 포지션 시작 시 레벨 초기화"""
        self.current_level = 0


class TimeBasedExit(ExitCondition):
    """시간 기반 매도"""
    
    def __init__(self, hours: int):
        super().__init__(f"TimeExit_{hours}h")
        self.max_hours = hours
    
    def should_exit(self, entry_price, current_price, highest_price, entry_time, current_time):
        holding_time = (current_time - entry_time).total_seconds() / 3600
        return holding_time >= self.max_hours


class CombinedExit(ExitCondition):
    """조합 매도 조건 (익절 OR 손절)"""
    
    def __init__(self, tp_pct: float, sl_pct: float):
        super().__init__(f"TP{tp_pct}%_SL{abs(sl_pct)}%")
        self.tp = FixedProfitTarget(tp_pct)
        self.sl = FixedStopLoss(sl_pct)
    
    def should_exit(self, entry_price, current_price, highest_price, entry_time, current_time):
        return (
            self.tp.should_exit(entry_price, current_price, highest_price, entry_time, current_time) or
            self.sl.should_exit(entry_price, current_price, highest_price, entry_time, current_time)
        )


class BinanceStrategyBacktest:
    """바이낸스 전략 백테스트 실행기"""
    
    def __init__(
        self,
        data_dir: str = "data/historical",
        results_dir: str = "backtest_results"
    ):
        self.data_dir = Path(data_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 전략 초기화
        self.strategy = BinanceMultiSignalStrategy(
            rsi_oversold=40.0,
            bb_proximity_pct=1.0,
            stoch_overbought=80.0,
            require_all_signals=False  # OR 조건
        )
    
    def load_data(self, symbol: str) -> pd.DataFrame:
        """CSV 데이터 로드"""
        # Find matching CSV file
        csv_files = list(self.data_dir.glob(f"{symbol}_minute1_*.csv"))
        
        if not csv_files:
            raise FileNotFoundError(f"{symbol} 데이터 파일 없음")
        
        csv_file = csv_files[0]  # 첫 번째 파일 사용
        print(f"📂 로드: {csv_file.name}")
        
        df = pd.read_csv(csv_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def run_single_backtest(
        self,
        df: pd.DataFrame,
        exit_condition: ExitCondition,
        initial_capital: float = 1_000_000  # 초기 자본 100만원
    ) -> Dict:
        """단일 매도 조건으로 백테스트"""
        
        capital = initial_capital
        position = 0  # 보유 수량
        entry_price = 0
        entry_time = None
        highest_price = 0
        
        trades = []
        equity_curve = []
        
        for i in range(len(df)):
            current_time = df.index[i]
            current_price = df['close'].iloc[i]
            
            # 포지션 없을 때: 매수 시그널 체크
            if position == 0:
                signal_df = df.iloc[:i+1]  # 현재까지의 데이터
                signal = self.strategy.generate_signal(signal_df)
                
                if signal == 'buy' and capital > 0:
                    # 매수 실행
                    position = capital / current_price
                    entry_price = current_price
                    entry_time = current_time
                    highest_price = current_price
                    capital = 0
                    
                    trades.append({
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'action': 'BUY'
                    })
            
            # 포지션 있을 때: 매도 조건 체크
            elif position > 0:
                highest_price = max(highest_price, current_price)
                
                should_sell = exit_condition.should_exit(
                    entry_price, current_price, highest_price, entry_time, current_time
                )
                
                if should_sell:
                    # 매도 실행
                    capital = position * current_price
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    trades[-1].update({
                        'exit_time': current_time,
                        'exit_price': current_price,
                        'profit_pct': profit_pct,
                        'profit_krw': capital - initial_capital,
                        'action': 'SELL'
                    })
                    
                    position = 0
                    entry_price = 0
                    
                    # MultiLevelTakeProfit의 경우 레벨 리셋
                    if hasattr(exit_condition, 'reset'):
                        exit_condition.reset()
            
            # 자산 가치 추적
            current_equity = capital + (position * current_price if position > 0 else 0)
            equity_curve.append({
                'timestamp': current_time,
                'equity': current_equity
            })
        
        # 최종 포지션 정리 (보유 중이면 마지막 가격에 매도)
        if position > 0:
            final_price = df['close'].iloc[-1]
            capital = position * final_price
            profit_pct = ((final_price - entry_price) / entry_price) * 100
            
            trades[-1].update({
                'exit_time': df.index[-1],
                'exit_price': final_price,
                'profit_pct': profit_pct,
                'profit_krw': capital - initial_capital,
                'action': 'SELL'
            })
        
        # 결과 분석
        trades_df = pd.DataFrame(trades)
        completed_trades = trades_df[trades_df['action'] == 'SELL']
        
        if len(completed_trades) == 0:
            return {
                'exit_condition': exit_condition.name,
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'total_return': 0,
                'final_capital': capital
            }
        
        win_trades = completed_trades[completed_trades['profit_pct'] > 0]
        loss_trades = completed_trades[completed_trades['profit_pct'] <= 0]
        
        result = {
            'exit_condition': exit_condition.name,
            'total_trades': len(completed_trades),
            'win_trades': len(win_trades),
            'loss_trades': len(loss_trades),
            'win_rate': (len(win_trades) / len(completed_trades)) * 100 if len(completed_trades) > 0 else 0,
            'avg_profit': completed_trades['profit_pct'].mean(),
            'avg_win': win_trades['profit_pct'].mean() if len(win_trades) > 0 else 0,
            'avg_loss': loss_trades['profit_pct'].mean() if len(loss_trades) > 0 else 0,
            'max_profit': completed_trades['profit_pct'].max(),
            'max_loss': completed_trades['profit_pct'].min(),
            'total_return': ((capital - initial_capital) / initial_capital) * 100,
            'final_capital': capital,
            'sharpe_ratio': self._calculate_sharpe(equity_curve) if len(equity_curve) > 0 else 0
        }
        
        return result
    
    def _calculate_sharpe(self, equity_curve: List[Dict]) -> float:
        """샤프 비율 계산 (간단 버전)"""
        if len(equity_curve) < 2:
            return 0
        
        equity_df = pd.DataFrame(equity_curve)
        returns = equity_df['equity'].pct_change().dropna()
        
        if len(returns) == 0 or returns.std() == 0:
            return 0
        
        return (returns.mean() / returns.std()) * np.sqrt(365 * 24 * 60)  # 1분봉 기준 연율화
    
    def run_all_backtests(
        self,
        symbols: List[str] = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
    ):
        """모든 코인, 모든 매도 조건으로 백테스트"""
        
        # 매도 조건 정의 (5가지 이상)
        exit_conditions = [
            # 1. 고정 익절/손절 조합
            CombinedExit(tp_pct=3, sl_pct=-3),
            CombinedExit(tp_pct=5, sl_pct=-3),
            CombinedExit(tp_pct=7, sl_pct=-5),
            
            # 2. 트레일링 스톱
            TrailingStop(trail_pct=2),
            TrailingStop(trail_pct=3),
            
            # 3. 시간 기반
            TimeBasedExit(hours=24),
            TimeBasedExit(hours=48),
            
            # 4. 멀티레벨 익절
            MultiLevelTakeProfit(levels=[(3, 0.5), (5, 1.0)]),
            MultiLevelTakeProfit(levels=[(2, 0.3), (5, 0.7), (10, 1.0)]),
        ]
        
        all_results = []
        
        print(f"\n{'='*80}")
        print(f"🎯 바이낸스 전략 백테스트 시작")
        print(f"코인: {', '.join(symbols)}")
        print(f"매도 조건: {len(exit_conditions)}가지")
        print(f"{'='*80}\n")
        
        for symbol in symbols:
            print(f"\n📊 {symbol} 백테스트 시작...")
            
            try:
                df = self.load_data(symbol)
                print(f"   데이터: {len(df):,}개 캔들 ({df.index[0]} ~ {df.index[-1]})")
                
                for idx, exit_cond in enumerate(exit_conditions, 1):
                    print(f"   [{idx}/{len(exit_conditions)}] {exit_cond.name}...", end=' ', flush=True)
                    
                    result = self.run_single_backtest(df, exit_cond)
                    result['symbol'] = symbol
                    all_results.append(result)
                    
                    print(f"✅ 수익률: {result['total_return']:+.2f}%, 승률: {result['win_rate']:.1f}%, 거래: {result['total_trades']}회")
                
                print(f"✅ {symbol} 완료!")
                
            except Exception as e:
                print(f"❌ {symbol} 실패: {e}")
                continue
        
        # 결과 저장
        self._save_results(all_results)
        self._print_summary(all_results)
    
    def _save_results(self, results: List[Dict]):
        """결과 CSV 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"binance_strategy_results_{timestamp}.csv"
        filepath = self.results_dir / filename
        
        df = pd.DataFrame(results)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 결과 저장: {filepath}")
        print(f"   크기: {filepath.stat().st_size / 1024:.1f}KB")
    
    def _print_summary(self, results: List[Dict]):
        """결과 요약 출력"""
        df = pd.DataFrame(results)
        
        print(f"\n{'='*80}")
        print(f"📊 백테스트 결과 요약")
        print(f"{'='*80}\n")
        
        # 코인별 최고 수익률
        print("🏆 코인별 최고 수익률:")
        for symbol in df['symbol'].unique():
            symbol_df = df[df['symbol'] == symbol]
            best = symbol_df.loc[symbol_df['total_return'].idxmax()]
            print(f"   {symbol}: {best['total_return']:.2f}% ({best['exit_condition']})")
        
        print()
        
        # 매도 조건별 평균 수익률
        print("📈 매도 조건별 평균 수익률:")
        avg_by_exit = df.groupby('exit_condition')['total_return'].mean().sort_values(ascending=False)
        for exit_name, avg_return in avg_by_exit.items():
            print(f"   {exit_name}: {avg_return:.2f}%")
        
        print()
        
        # 전체 통계
        print("📊 전체 통계:")
        print(f"   평균 수익률: {df['total_return'].mean():.2f}%")
        print(f"   최고 수익률: {df['total_return'].max():.2f}%")
        print(f"   최저 수익률: {df['total_return'].min():.2f}%")
        print(f"   평균 승률: {df['win_rate'].mean():.1f}%")
        print(f"   평균 거래 횟수: {df['total_trades'].mean():.0f}회")
        
        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    backtest = BinanceStrategyBacktest()
    backtest.run_all_backtests()
