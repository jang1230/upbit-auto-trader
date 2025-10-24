"""
하이브리드 전략 DCA 파라미터 최적화
Hybrid Strategies DCA Parameter Optimization

4개 하이브리드 전략 × 9개 DCA 설정 = 36개 조합
3개 코인 (BTC, ETH, XRP) = 총 108개 백테스트
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import time

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategies.hybrid_conservative_strategy import HybridConservativeStrategy
from core.strategies.hybrid_balanced_strategy import HybridBalancedStrategy
from core.strategies.hybrid_aggressive_strategy import HybridAggressiveStrategy
from core.strategies.hybrid_smart_strategy import HybridSmartStrategy
from backtest.dca_backtest_engine import DCABacktestEngine


def load_data(symbol: str) -> pd.DataFrame:
    """CSV 파일에서 데이터 로드"""
    filepath = Path(project_root) / "data" / "historical" / f"{symbol}_minute1_20241020_20251020.csv"
    
    if not filepath.exists():
        raise FileNotFoundError(f"파일 없음: {filepath}")
    
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    return df


def test_parameter_combination(
    strategy_name: str,
    strategy,
    symbol: str,
    candles: pd.DataFrame,
    profit_target: float,
    stop_loss: float,
    buy_interval: float,
    max_buys: int,
    config_name: str
) -> dict:
    """하나의 파라미터 조합 테스트"""
    
    engine = DCABacktestEngine(
        strategy=strategy,
        initial_capital=1000000,
        profit_target_pct=profit_target,
        stop_loss_pct=stop_loss,
        max_buys=max_buys,
        buy_interval_pct=buy_interval
    )
    
    result = engine.run(candles)
    
    avg_profit = sum(t.pnl_pct for t in result.trades) / len(result.trades) if result.trades else 0
    
    return {
        'strategy': strategy_name,
        'config': config_name,
        'symbol': symbol,
        'profit_target': profit_target,
        'stop_loss': stop_loss,
        'buy_interval': buy_interval,
        'max_buys': max_buys,
        'total_return': result.total_return,
        'total_trades': result.total_trades,
        'win_rate': result.win_rate,
        'avg_profit': avg_profit,
        'profit_trades': result.avg_profit_trades,
        'loss_trades': result.avg_loss_trades,
        'final_capital': result.final_capital
    }


def main():
    """메인 실행"""
    
    print("\n" + "="*80)
    print("🚀 하이브리드 전략 DCA 파라미터 최적화")
    print("="*80)
    print("전략: 4개 (Conservative, Balanced, Aggressive, Smart)")
    print("DCA 설정: 9가지")
    print("코인: 3개 (BTC, ETH, XRP)")
    print("총 테스트: 108개 (4 × 9 × 3)")
    print("="*80)
    
    # 9개 DCA 설정
    dca_configs = [
        ("현재 설정 (기준)", 5.0, -7.0, 10.0, 6),
        ("보수적 (빠른 회전)", 3.0, -5.0, 10.0, 6),
        ("공격적 (큰 수익)", 10.0, -10.0, 10.0, 6),
        ("타이트 (스캘핑)", 3.0, -3.0, 10.0, 6),
        ("넓은 간격 (느린 평단)", 5.0, -7.0, 15.0, 6),
        ("좁은 간격 (빠른 평단)", 5.0, -7.0, 5.0, 6),
        ("적은 매수 (4회)", 5.0, -7.0, 10.0, 4),
        ("많은 매수 (8회)", 5.0, -7.0, 10.0, 8),
        ("균형 (중도)", 7.0, -8.0, 12.0, 6)
    ]
    
    # 4개 하이브리드 전략
    strategies = [
        ("Hybrid Conservative", lambda s: HybridConservativeStrategy(
            symbol=s, bb_period=20, bb_std=2.0, bb_proximity_pct=2.0,
            rsi_period=14, rsi_threshold=40.0
        )),
        ("Hybrid Balanced", lambda s: HybridBalancedStrategy(
            symbol=s, bb_period=20, bb_std=2.0, bb_proximity_pct=2.0,
            rsi_period=14, rsi_threshold=40.0,
            stoch_k_period=14, stoch_d_period=3, stoch_threshold=70.0
        )),
        ("Hybrid Aggressive", lambda s: HybridAggressiveStrategy(
            symbol=s, bb_period=20, bb_std=2.0, bb_proximity_pct=1.5,
            rsi_period=14, rsi_threshold=35.0,
            stoch_k_period=14, stoch_d_period=3, stoch_threshold=60.0
        )),
        ("Hybrid Smart", lambda s: HybridSmartStrategy(
            symbol=s, bb_period=20, bb_std=2.0, bb_proximity_pct=2.0,
            stoch_k_period=14, stoch_d_period=3, stoch_threshold=80.0,
            time_filter_minutes=60
        ))
    ]
    
    # 코인 목록
    coins = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
    
    # 결과 저장
    all_results = []
    
    # 전략별 테스트
    total_tests = len(strategies) * len(dca_configs) * len(coins)
    current_test = 0
    
    for strategy_name, strategy_factory in strategies:
        print(f"\n{'='*80}")
        print(f"📊 {strategy_name} 테스트")
        print(f"{'='*80}")
        
        for coin in coins:
            print(f"\n💰 {coin} 데이터 로드 중...")
            
            try:
                candles = load_data(coin)
                print(f"✅ 로드 완료: {len(candles):,}개 캔들")
                print(f"   기간: {candles.index[0]} ~ {candles.index[-1]}")
            except FileNotFoundError as e:
                print(f"⚠️ 파일 없음, 스킵: {coin}")
                continue
            
            # 9개 DCA 설정 테스트
            for config_name, profit_target, stop_loss, buy_interval, max_buys in dca_configs:
                current_test += 1
                
                print(f"  [{current_test}/{total_tests}] 테스트: {config_name}", end=" ")
                
                strategy = strategy_factory(coin)
                
                result = test_parameter_combination(
                    strategy_name=strategy_name,
                    strategy=strategy,
                    symbol=coin,
                    candles=candles,
                    profit_target=profit_target,
                    stop_loss=stop_loss,
                    buy_interval=buy_interval,
                    max_buys=max_buys,
                    config_name=config_name
                )
                
                all_results.append(result)
                
                print(f"✅ 수익률: {result['total_return']:+.2f}% | 거래: {result['total_trades']}회 | 승률: {result['win_rate']:.1f}%")
    
    # 결과 분석
    print(f"\n{'='*80}")
    print("📊 결과 분석")
    print(f"{'='*80}")
    
    results_df = pd.DataFrame(all_results)
    
    # 1. 전략별 평균 (모든 코인, 모든 DCA 설정)
    print(f"\n🏆 전략별 평균 성과")
    strategy_avg = results_df.groupby('strategy').agg({
        'total_return': 'mean',
        'total_trades': 'mean',
        'win_rate': 'mean'
    }).round(2).sort_values('total_return', ascending=False)
    
    for idx, (strategy, row) in enumerate(strategy_avg.iterrows(), 1):
        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "  "
        print(f"{emoji} {strategy:25s}: {row['total_return']:+7.2f}% (거래: {row['total_trades']:4.0f}회, 승률: {row['win_rate']:5.1f}%)")
    
    # 2. 전략별 최고 DCA 설정
    print(f"\n🎯 전략별 최고 DCA 설정 (3개 코인 평균)")
    for strategy_name, _ in strategies:
        strategy_data = results_df[results_df['strategy'] == strategy_name]
        config_avg = strategy_data.groupby('config').agg({
            'total_return': 'mean'
        }).round(2).sort_values('total_return', ascending=False)
        
        best_config = config_avg.index[0]
        best_return = config_avg.iloc[0]['total_return']
        
        print(f"  {strategy_name:25s}: {best_config:30s} ({best_return:+.2f}%)")
    
    # 3. 코인별 최고 조합
    print(f"\n💎 코인별 최고 전략+DCA 조합")
    for coin in coins:
        coin_data = results_df[results_df['symbol'] == coin]
        if len(coin_data) == 0:
            continue
        
        best = coin_data.loc[coin_data['total_return'].idxmax()]
        print(f"  {coin}: {best['strategy']} + {best['config']}")
        print(f"         수익률: {best['total_return']:+.2f}% | 거래: {best['total_trades']:.0f}회 | 승률: {best['win_rate']:.1f}%")
    
    # CSV 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = project_root / 'backtest_results' / f'hybrid_dca_optimization_{timestamp}.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n💾 결과 저장: {output_file.name}")
    print(f"\n{'='*80}")
    print("✅ 모든 테스트 완료!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
