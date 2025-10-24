"""
하이브리드 전략 백테스트 결과 자동 분석 스크립트
Hybrid Strategy Backtest Results Auto-Analyzer

백테스트 완료 후 결과를 자동으로 분석하고 최적 전략을 추출합니다.
"""

import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

def load_latest_result(results_dir: Path):
    """가장 최근 결과 파일 로드"""
    csv_files = list(results_dir.glob('hybrid_dca_optimization_*.csv'))
    
    if not csv_files:
        print("❌ 결과 파일을 찾을 수 없습니다.")
        return None
    
    # 가장 최근 파일 선택
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"📂 결과 파일: {latest_file.name}")
    print(f"📅 생성 시간: {datetime.fromtimestamp(latest_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    df = pd.read_csv(latest_file)
    return df

def analyze_results(df: pd.DataFrame):
    """결과 종합 분석"""
    print("=" * 80)
    print("📊 백테스트 결과 종합 분석")
    print("=" * 80)
    
    # 기본 통계
    print(f"\n✅ 총 테스트 수: {len(df)}개")
    print(f"📈 전략 종류: {df['전략명'].nunique()}개 - {', '.join(df['전략명'].unique())}")
    print(f"💰 코인 종류: {df['코인'].nunique()}개 - {', '.join(df['코인'].unique())}")
    print(f"⚙️  DCA 설정: {df['DCA설정'].nunique()}개")
    
    # 수익률 통계
    print(f"\n💵 수익률 통계:")
    print(f"  - 평균: {df['총_수익률(%)'].mean():.2f}%")
    print(f"  - 중앙값: {df['총_수익률(%)'].median():.2f}%")
    print(f"  - 최대: {df['총_수익률(%)'].max():.2f}%")
    print(f"  - 최소: {df['총_수익률(%)'].min():.2f}%")
    print(f"  - 표준편차: {df['총_수익률(%)'].std():.2f}%")

def top_strategies(df: pd.DataFrame, n: int = 10):
    """상위 N개 전략 추출"""
    print("\n" + "=" * 80)
    print(f"🏆 상위 {n}개 전략")
    print("=" * 80)
    
    top_n = df.nlargest(n, '총_수익률(%)')
    
    for idx, row in enumerate(top_n.itertuples(), 1):
        print(f"\n{idx}위:")
        print(f"  전략: {row.전략명}")
        print(f"  코인: {row.코인}")
        print(f"  DCA설정: {row.DCA설정}")
        print(f"  💰 총 수익률: {row.총_수익률:.2f}%")
        print(f"  📊 거래 횟수: {row.총_거래횟수}회")
        print(f"  ✅ 승률: {row.승률:.1f}%")
        print(f"  📈 평균 수익: {row.평균_수익:.2f}%")
        print(f"  📉 평균 손실: {row.평균_손실:.2f}%")
        print(f"  🎯 수익/손실 비율: {row.수익손실비율:.2f}")

def strategy_comparison(df: pd.DataFrame):
    """전략별 비교"""
    print("\n" + "=" * 80)
    print("🔍 전략별 성과 비교")
    print("=" * 80)
    
    strategy_stats = df.groupby('전략명').agg({
        '총_수익률(%)': ['mean', 'median', 'max', 'min', 'std'],
        '총_거래횟수': 'mean',
        '승률': 'mean'
    }).round(2)
    
    print(strategy_stats.to_string())
    
    # 전략별 평균 순위
    print(f"\n📊 전략별 평균 수익률 순위:")
    avg_returns = df.groupby('전략명')['총_수익률(%)'].mean().sort_values(ascending=False)
    for idx, (strategy, ret) in enumerate(avg_returns.items(), 1):
        print(f"  {idx}. {strategy}: {ret:.2f}%")

def coin_comparison(df: pd.DataFrame):
    """코인별 비교"""
    print("\n" + "=" * 80)
    print("💰 코인별 성과 비교")
    print("=" * 80)
    
    coin_stats = df.groupby('코인').agg({
        '총_수익률(%)': ['mean', 'median', 'max', 'min'],
        '총_거래횟수': 'mean',
        '승률': 'mean'
    }).round(2)
    
    print(coin_stats.to_string())

def dca_comparison(df: pd.DataFrame):
    """DCA 설정별 비교"""
    print("\n" + "=" * 80)
    print("⚙️  DCA 설정별 성과 비교")
    print("=" * 80)
    
    dca_stats = df.groupby('DCA설정').agg({
        '총_수익률(%)': ['mean', 'median', 'max'],
        '총_거래횟수': 'mean',
        '승률': 'mean'
    }).round(2)
    
    # 평균 수익률 순으로 정렬
    dca_stats = dca_stats.sort_values(('총_수익률(%)', 'mean'), ascending=False)
    print(dca_stats.to_string())

def best_combinations(df: pd.DataFrame):
    """최고 조합 찾기"""
    print("\n" + "=" * 80)
    print("🎯 전략별 최적 조합")
    print("=" * 80)
    
    for strategy in df['전략명'].unique():
        strategy_df = df[df['전략명'] == strategy]
        best = strategy_df.nlargest(1, '총_수익률(%)').iloc[0]
        
        print(f"\n📌 {strategy}")
        print(f"  최고 수익률: {best['총_수익률(%)']:.2f}%")
        print(f"  코인: {best['코인']}")
        print(f"  DCA설정: {best['DCA설정']}")
        print(f"  거래 횟수: {best['총_거래횟수']}회")
        print(f"  승률: {best['승률']:.1f}%")

def save_summary(df: pd.DataFrame, output_dir: Path):
    """분석 요약 저장"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = output_dir / f'analysis_summary_{timestamp}.txt'
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        # 상위 10개 전략
        f.write("=" * 80 + "\n")
        f.write("상위 10개 전략\n")
        f.write("=" * 80 + "\n\n")
        
        top_n = df.nlargest(10, '총_수익률(%)')
        for idx, row in enumerate(top_n.itertuples(), 1):
            f.write(f"{idx}위: {row.전략명} | {row.코인} | {row.DCA설정} | {row.총_수익률:.2f}%\n")
        
        # 전략별 평균
        f.write("\n" + "=" * 80 + "\n")
        f.write("전략별 평균 수익률\n")
        f.write("=" * 80 + "\n\n")
        
        avg_returns = df.groupby('전략명')['총_수익률(%)'].mean().sort_values(ascending=False)
        for strategy, ret in avg_returns.items():
            f.write(f"{strategy}: {ret:.2f}%\n")
    
    print(f"\n💾 분석 요약 저장: {summary_file.name}")

def main():
    # 프로젝트 루트 찾기
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    results_dir = project_root / 'backtest_results'
    
    print("🔍 백테스트 결과 분석 시작\n")
    
    # 결과 파일 로드
    df = load_latest_result(results_dir)
    if df is None:
        return
    
    # 분석 실행
    analyze_results(df)
    top_strategies(df, n=10)
    strategy_comparison(df)
    coin_comparison(df)
    dca_comparison(df)
    best_combinations(df)
    
    # 요약 저장
    save_summary(df, results_dir)
    
    print("\n" + "=" * 80)
    print("✅ 분석 완료!")
    print("=" * 80)

if __name__ == "__main__":
    main()
