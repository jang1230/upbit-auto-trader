"""
DCA 파라미터 최적화 백테스트
여러 조합을 테스트하여 최적 설정 찾기
"""

import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backtest.dca_backtest_engine import DCABacktestEngine, DCABacktestResult
from core.strategies.proximity_bb_strategy import ProximityBollingerBandsStrategy


def load_csv_data(symbol: str) -> pd.DataFrame:
    """CSV 파일에서 데이터 로드"""
    csv_path = Path(__file__).parent.parent / "data" / "historical"
    
    # 파일 찾기
    files = list(csv_path.glob(f"{symbol}_minute1_*.csv"))
    if not files:
        raise FileNotFoundError(f"{symbol} CSV 파일을 찾을 수 없습니다")
    
    filepath = files[0]
    print(f"📂 로드: {filepath.name}")
    
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    return df


def test_parameter_combination(
    symbol: str,
    candles: pd.DataFrame,
    profit_target: float,
    stop_loss: float,
    buy_interval: float,
    max_buys: int,
    config_name: str
) -> dict:
    """하나의 파라미터 조합 테스트"""
    
    strategy = ProximityBollingerBandsStrategy(symbol=symbol)
    engine = DCABacktestEngine(
        strategy=strategy,
        initial_capital=1000000,
        profit_target_pct=profit_target,
        stop_loss_pct=stop_loss,
        max_buys=max_buys,
        buy_interval_pct=buy_interval
    )
    
    result = engine.run(candles)
    
    # 평균 수익/거래 계산
    avg_profit = sum(t.pnl_pct for t in result.trades) / len(result.trades) if result.trades else 0
    
    return {
        'config': config_name,
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
    """메인 최적화 실행"""
    
    print("=" * 80)
    print("🎯 DCA 파라미터 최적화 백테스트")
    print("=" * 80)
    print()
    
    # 테스트할 파라미터 조합들
    configs = [
        # 기준 설정
        {
            'name': '현재 설정 (기준)',
            'profit': 5.0,
            'loss': -7.0,
            'interval': 10.0,
            'buys': 6
        },
        # 보수적 (빠른 익절/손절)
        {
            'name': '보수적 (빠른 회전)',
            'profit': 3.0,
            'loss': -5.0,
            'interval': 10.0,
            'buys': 6
        },
        # 공격적 (높은 익절, 깊은 손절)
        {
            'name': '공격적 (큰 수익)',
            'profit': 10.0,
            'loss': -10.0,
            'interval': 10.0,
            'buys': 6
        },
        # 타이트 (익절/손절 모두 빠름)
        {
            'name': '타이트 (스캘핑)',
            'profit': 3.0,
            'loss': -3.0,
            'interval': 10.0,
            'buys': 6
        },
        # 넓은 간격 (추가매수 느리게)
        {
            'name': '넓은 간격 (느린 평단)',
            'profit': 5.0,
            'loss': -7.0,
            'interval': 15.0,
            'buys': 6
        },
        # 좁은 간격 (추가매수 빠르게)
        {
            'name': '좁은 간격 (빠른 평단)',
            'profit': 5.0,
            'loss': -7.0,
            'interval': 5.0,
            'buys': 6
        },
        # 적은 매수 횟수
        {
            'name': '적은 매수 (4회)',
            'profit': 5.0,
            'loss': -7.0,
            'interval': 10.0,
            'buys': 4
        },
        # 많은 매수 횟수
        {
            'name': '많은 매수 (8회)',
            'profit': 5.0,
            'loss': -7.0,
            'interval': 10.0,
            'buys': 8
        },
        # 균형잡힌 중간 설정
        {
            'name': '균형 (중도)',
            'profit': 7.0,
            'loss': -8.0,
            'interval': 12.0,
            'buys': 6
        }
    ]
    
    coins = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
    
    all_results = []
    
    for symbol in coins:
        print(f"\n{'='*80}")
        print(f"📊 {symbol} 데이터 로드 및 테스트")
        print(f"{'='*80}\n")
        
        # 데이터 로드
        candles = load_csv_data(symbol)
        print(f"✅ 총 {len(candles):,}개 캔들 로드")
        print(f"   기간: {candles.index[0]} ~ {candles.index[-1]}")
        print()
        
        # 각 설정 테스트
        for config in configs:
            print(f"🔄 테스트: {config['name']}")
            
            result = test_parameter_combination(
                symbol=symbol,
                candles=candles,
                profit_target=config['profit'],
                stop_loss=config['loss'],
                buy_interval=config['interval'],
                max_buys=config['buys'],
                config_name=config['name']
            )
            
            result['symbol'] = symbol
            all_results.append(result)
            
            print(f"   → 수익률: {result['total_return']:+.2f}% | "
                  f"거래: {result['total_trades']}회 | "
                  f"승률: {result['win_rate']:.1f}%")
    
    # 결과 DataFrame 생성
    results_df = pd.DataFrame(all_results)
    
    # 코인별 최고 성과 출력
    print(f"\n\n{'='*80}")
    print("🏆 코인별 최고 성과 설정")
    print(f"{'='*80}\n")
    
    for symbol in coins:
        coin_results = results_df[results_df['symbol'] == symbol]
        best = coin_results.loc[coin_results['total_return'].idxmax()]
        
        print(f"📊 {symbol}")
        print(f"   최고 설정: {best['config']}")
        print(f"   수익률: {best['total_return']:+.2f}%")
        print(f"   거래 횟수: {int(best['total_trades'])}회")
        print(f"   승률: {best['win_rate']:.1f}%")
        print(f"   평균 수익: {best['avg_profit']:+.2f}%")
        print(f"   최대 낙폭: {best['max_drawdown']:.2f}%")
        print(f"   파라미터: 익절 {best['profit_target']}% | "
              f"손절 {best['stop_loss']}% | "
              f"간격 {best['buy_interval']}% | "
              f"횟수 {int(best['max_buys'])}회")
        print()
    
    # 전체 평균 최고 성과
    print(f"{'='*80}")
    print("🎯 전체 평균 최고 성과 설정")
    print(f"{'='*80}\n")
    
    avg_by_config = results_df.groupby('config').agg({
        'total_return': 'mean',
        'total_trades': 'mean',
        'win_rate': 'mean',
        'avg_profit': 'mean',
        'max_drawdown': 'mean'
    }).round(2)
    
    avg_by_config = avg_by_config.sort_values('total_return', ascending=False)
    
    print(avg_by_config.to_string())
    
    # 상위 3개 설정 자세히
    print(f"\n\n{'='*80}")
    print("🥇 상위 3개 설정 상세")
    print(f"{'='*80}\n")
    
    for i, (config_name, row) in enumerate(avg_by_config.head(3).iterrows(), 1):
        print(f"{i}. {config_name}")
        print(f"   평균 수익률: {row['total_return']:+.2f}%")
        print(f"   평균 거래 횟수: {row['total_trades']:.1f}회")
        print(f"   평균 승률: {row['win_rate']:.1f}%")
        print(f"   평균 수익/거래: {row['avg_profit']:+.2f}%")
        print(f"   평균 최대 낙폭: {row['max_drawdown']:.2f}%")
        
        # 해당 설정의 파라미터 찾기
        config_detail = results_df[results_df['config'] == config_name].iloc[0]
        print(f"   📌 파라미터: 익절 {config_detail['profit_target']}% | "
              f"손절 {config_detail['stop_loss']}% | "
              f"간격 {config_detail['buy_interval']}% | "
              f"횟수 {int(config_detail['max_buys'])}회")
        print()
    
    # CSV 저장
    output_path = Path(__file__).parent.parent / "backtest_results" / f"parameter_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    output_path.parent.mkdir(exist_ok=True)
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"💾 결과 저장: {output_path}")
    print()


if __name__ == "__main__":
    main()
