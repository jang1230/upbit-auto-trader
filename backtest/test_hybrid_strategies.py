"""
하이브리드 전략 백테스트
Hybrid Strategies Backtest

4개의 하이브리드 전략 + 기존 2개 전략 비교
- Proximity BB (기존)
- Binance Multi-Signal (기존)
- Hybrid Conservative (신규)
- Hybrid Balanced (신규)
- Hybrid Aggressive (신규)
- Hybrid Smart (신규)
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategies.proximity_bb_strategy import ProximityBBStrategy
from core.strategies.binance_multi_signal_strategy import BinanceMultiSignalStrategy
from core.strategies.hybrid_conservative_strategy import HybridConservativeStrategy
from core.strategies.hybrid_balanced_strategy import HybridBalancedStrategy
from core.strategies.hybrid_aggressive_strategy import HybridAggressiveStrategy
from core.strategies.hybrid_smart_strategy import HybridSmartStrategy
from backtest.dca_backtest_engine import DCABacktestEngine


def load_data(symbol: str, data_dir: str = "data/historical") -> pd.DataFrame:
    """CSV 파일에서 데이터 로드"""
    filepath = Path(project_root) / data_dir / f"{symbol}_minute1_20241020_20251020.csv"
    
    if not filepath.exists():
        raise FileNotFoundError(f"데이터 파일 없음: {filepath}")
    
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    return df


def test_strategy(
    strategy_name: str,
    strategy,
    symbol: str,
    candles: pd.DataFrame,
    dca_config: dict
) -> dict:
    """개별 전략 테스트"""
    
    print(f"\n{'='*80}")
    print(f"📊 {strategy_name} 테스트 중...")
    print(f"{'='*80}")
    
    # 백테스트 엔진 생성
    engine = DCABacktestEngine(
        strategy=strategy,
        initial_capital=dca_config['initial_capital'],
        profit_target_pct=dca_config['profit_target_pct'],
        stop_loss_pct=dca_config['stop_loss_pct'],
        max_buys=dca_config['max_buys'],
        buy_interval_pct=dca_config['buy_interval_pct']
    )
    
    # 실행
    result = engine.run(candles)
    
    # 결과 출력
    print(f"\n✅ 완료!")
    print(f"   수익률: {result.total_return:+.2f}%")
    print(f"   거래 횟수: {result.total_trades}회")
    print(f"   승률: {result.win_rate:.1f}%")
    print(f"   평균 수익: {sum(t.pnl_pct for t in result.trades) / len(result.trades) if result.trades else 0:.2f}%")
    
    return {
        'strategy': strategy_name,
        'symbol': symbol,
        'total_return': result.total_return,
        'total_trades': result.total_trades,
        'win_rate': result.win_rate,
        'avg_profit': sum(t.pnl_pct for t in result.trades) / len(result.trades) if result.trades else 0,
        'final_capital': result.final_capital
    }


def main():
    """메인 실행"""
    
    print("\n" + "="*80)
    print("🚀 하이브리드 전략 백테스트")
    print("="*80)
    print("기간: 2024-10-20 ~ 2025-10-20 (1년)")
    print("코인: BTC, ETH, XRP")
    print("전략: 6개")
    print("="*80)
    
    # DCA 설정 (공격적 설정 사용)
    dca_config = {
        'initial_capital': 1000000,
        'profit_target_pct': 10.0,  # 10% 익절
        'stop_loss_pct': -10.0,     # -10% 손절
        'max_buys': 6,
        'buy_interval_pct': 10.0
    }
    
    print(f"\nDCA 설정:")
    print(f"  초기 자본: {dca_config['initial_capital']:,}원")
    print(f"  익절: {dca_config['profit_target_pct']}%")
    print(f"  손절: {dca_config['stop_loss_pct']}%")
    print(f"  최대 매수: {dca_config['max_buys']}회")
    print(f"  추가 매수 간격: {dca_config['buy_interval_pct']}%")
    
    # 코인 목록
    coins = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
    
    # 전략 목록
    strategies = [
        ('Proximity BB (기존)', lambda s: ProximityBBStrategy(
            symbol=s, bb_period=20, bb_std=2.0, proximity_pct=2.0, 
            time_filter_hours=1
        )),
        ('Binance Multi (기존)', lambda s: BinanceMultiSignalStrategy(
            symbol=s, rsi_period=14, rsi_oversold=40.0,
            bb_period=20, bb_std=2.0, bb_proximity_pct=1.0,
            stoch_k_period=14, stoch_d_period=3, stoch_overbought=80.0,
            require_all_signals=False
        )),
        ('Hybrid Conservative (신규)', lambda s: HybridConservativeStrategy(
            symbol=s, bb_period=20, bb_std=2.0, bb_proximity_pct=2.0,
            rsi_period=14, rsi_threshold=40.0
        )),
        ('Hybrid Balanced (신규)', lambda s: HybridBalancedStrategy(
            symbol=s, bb_period=20, bb_std=2.0, bb_proximity_pct=2.0,
            rsi_period=14, rsi_threshold=40.0,
            stoch_k_period=14, stoch_d_period=3, stoch_threshold=70.0
        )),
        ('Hybrid Aggressive (신규)', lambda s: HybridAggressiveStrategy(
            symbol=s, bb_period=20, bb_std=2.0, bb_proximity_pct=1.5,
            rsi_period=14, rsi_threshold=35.0,
            stoch_k_period=14, stoch_d_period=3, stoch_threshold=60.0
        )),
        ('Hybrid Smart (신규)', lambda s: HybridSmartStrategy(
            symbol=s, bb_period=20, bb_std=2.0, bb_proximity_pct=2.0,
            stoch_k_period=14, stoch_d_period=3, stoch_threshold=80.0,
            time_filter_minutes=60
        ))
    ]
    
    # 결과 저장
    all_results = []
    
    # 코인별 테스트
    for coin in coins:
        print(f"\n{'='*80}")
        print(f"💰 {coin} 데이터 로드 중...")
        print(f"{'='*80}")
        
        try:
            candles = load_data(coin)
            print(f"✅ 데이터 로드 완료: {len(candles):,}개 캔들")
            print(f"   기간: {candles.index[0]} ~ {candles.index[-1]}")
        except FileNotFoundError as e:
            print(f"⚠️ 파일 없음: {e}")
            continue
        
        # 전략별 테스트
        for strategy_name, strategy_factory in strategies:
            strategy = strategy_factory(coin)
            result = test_strategy(strategy_name, strategy, coin, candles, dca_config)
            all_results.append(result)
    
    # 결과 정리
    print(f"\n{'='*80}")
    print("📊 전체 결과 요약")
    print(f"{'='*80}")
    
    results_df = pd.DataFrame(all_results)
    
    # 전략별 평균 수익률
    print(f"\n🏆 전략별 평균 수익률 (BTC/ETH/XRP 평균)")
    avg_by_strategy = results_df.groupby('strategy').agg({
        'total_return': 'mean',
        'total_trades': 'mean',
        'win_rate': 'mean'
    }).round(2)
    avg_by_strategy = avg_by_strategy.sort_values('total_return', ascending=False)
    
    for idx, (strategy, row) in enumerate(avg_by_strategy.iterrows(), 1):
        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "  "
        print(f"{emoji} {strategy:30s}: {row['total_return']:+7.2f}% (거래: {row['total_trades']:4.0f}회, 승률: {row['win_rate']:5.1f}%)")
    
    # CSV 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = project_root / 'backtest_results' / f'hybrid_strategies_comparison_{timestamp}.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n💾 결과 저장: {output_file.name}")
    print(f"\n{'='*80}")
    print("✅ 모든 테스트 완료!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
