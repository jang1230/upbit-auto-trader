"""
하이브리드 전략 백테스트 결과 시각화 스크립트
Hybrid Strategy Backtest Results Visualization

백테스트 결과를 다양한 차트로 시각화합니다.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
from datetime import datetime
import numpy as np

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# Seaborn 스타일 설정
sns.set_style("whitegrid")
sns.set_palette("husl")

def load_results(results_dir: Path):
    """가장 최근 결과 파일 로드"""
    csv_files = list(results_dir.glob('hybrid_dca_optimization_*.csv'))
    
    if not csv_files:
        print("❌ 결과 파일을 찾을 수 없습니다.")
        return None
    
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"📂 파일: {latest_file.name}")
    
    df = pd.read_csv(latest_file)
    return df

def create_strategy_comparison(df: pd.DataFrame, save_dir: Path):
    """전략별 수익률 비교 차트"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Strategy Performance Comparison', fontsize=16, fontweight='bold')
    
    # 1. 전략별 평균 수익률
    ax1 = axes[0, 0]
    strategy_avg = df.groupby('strategy')['total_return'].agg(['mean', 'std']).sort_values('mean', ascending=False)
    ax1.bar(range(len(strategy_avg)), strategy_avg['mean'])
    ax1.errorbar(range(len(strategy_avg)), strategy_avg['mean'], yerr=strategy_avg['std'], 
                 fmt='none', color='black', capsize=5)
    ax1.set_xticks(range(len(strategy_avg)))
    ax1.set_xticklabels(strategy_avg.index, rotation=45, ha='right')
    ax1.set_ylabel('Return (%)')
    ax1.set_title('Average Return by Strategy')
    ax1.grid(True, alpha=0.3)
    
    # 값 표시
    for i, v in enumerate(strategy_avg['mean']):
        ax1.text(i, v + strategy_avg['std'][i] + 0.5, f'{v:.1f}%', ha='center')
    
    # 2. 전략별 수익률 분포 (박스플롯)
    ax2 = axes[0, 1]
    strategies = df['strategy'].unique()
    data_to_plot = [df[df['strategy'] == s]['total_return'].values for s in strategies]
    bp = ax2.boxplot(data_to_plot, labels=strategies)
    ax2.set_xticklabels(strategies, rotation=45, ha='right')
    ax2.set_ylabel('Return (%)')
    ax2.set_title('Return Distribution by Strategy')
    ax2.grid(True, alpha=0.3)
    
    # 3. 전략별 승률
    ax3 = axes[1, 0]
    strategy_wr = df.groupby('strategy')['win_rate'].mean().sort_values(ascending=False)
    bars = ax3.bar(range(len(strategy_wr)), strategy_wr, color='lightgreen')
    ax3.set_xticks(range(len(strategy_wr)))
    ax3.set_xticklabels(strategy_wr.index, rotation=45, ha='right')
    ax3.set_ylabel('Win Rate (%)')
    ax3.set_title('Average Win Rate by Strategy')
    ax3.grid(True, alpha=0.3)
    
    # 값 표시
    for i, (bar, v) in enumerate(zip(bars, strategy_wr)):
        ax3.text(i, v + 0.5, f'{v:.1f}%', ha='center')
    
    # 4. 전략별 거래 횟수
    ax4 = axes[1, 1]
    strategy_trades = df.groupby('strategy')['total_trades'].mean().sort_values(ascending=False)
    bars = ax4.bar(range(len(strategy_trades)), strategy_trades, color='lightblue')
    ax4.set_xticks(range(len(strategy_trades)))
    ax4.set_xticklabels(strategy_trades.index, rotation=45, ha='right')
    ax4.set_ylabel('Number of Trades')
    ax4.set_title('Average Trade Count by Strategy')
    ax4.grid(True, alpha=0.3)
    
    # 값 표시
    for i, (bar, v) in enumerate(zip(bars, strategy_trades)):
        ax4.text(i, v + 0.5, f'{v:.0f}', ha='center')
    
    plt.tight_layout()
    save_path = save_dir / '01_strategy_comparison.png'
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"✅ 저장: {save_path.name}")

def create_coin_analysis(df: pd.DataFrame, save_dir: Path):
    """코인별 분석 차트"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Performance Analysis by Coin', fontsize=16, fontweight='bold')
    
    # 1. 코인별 평균 수익률
    ax1 = axes[0, 0]
    coin_avg = df.groupby('symbol')['total_return'].agg(['mean', 'std']).sort_values('mean', ascending=False)
    ax1.bar(range(len(coin_avg)), coin_avg['mean'])
    ax1.errorbar(range(len(coin_avg)), coin_avg['mean'], yerr=coin_avg['std'], 
                 fmt='none', color='black', capsize=5)
    ax1.set_xticks(range(len(coin_avg)))
    ax1.set_xticklabels(coin_avg.index)
    ax1.set_ylabel('Return (%)')
    ax1.set_title('Average Return by Coin')
    ax1.grid(True, alpha=0.3)
    
    for i, v in enumerate(coin_avg['mean']):
        ax1.text(i, v + coin_avg['std'][i] + 0.5, f'{v:.1f}%', ha='center')
    
    # 2. 코인-전략 히트맵
    ax2 = axes[0, 1]
    pivot = df.pivot_table(values='total_return', index='strategy', columns='symbol', aggfunc='mean')
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', center=0, ax=ax2)
    ax2.set_title('Strategy-Coin Return Heatmap')
    
    # 3. 코인별 수익률 분포
    ax3 = axes[1, 0]
    df.boxplot(column='total_return', by='symbol', ax=ax3)
    ax3.set_xlabel('Coin')
    ax3.set_ylabel('Return (%)')
    ax3.set_title('Return Distribution by Coin')
    plt.sca(ax3)
    plt.xticks(rotation=0)
    
    # 4. 코인별 최고/최저 수익률
    ax4 = axes[1, 1]
    coin_stats = df.groupby('symbol')['total_return'].agg(['max', 'min'])
    x = np.arange(len(coin_stats))
    width = 0.35
    
    bars1 = ax4.bar(x - width/2, coin_stats['max'], width, label='Max', color='green')
    bars2 = ax4.bar(x + width/2, coin_stats['min'], width, label='Min', color='red')
    
    ax4.set_xticks(x)
    ax4.set_xticklabels(coin_stats.index)
    ax4.set_ylabel('Return (%)')
    ax4.set_title('Max/Min Returns by Coin')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # 값 표시
    for bar in bars1:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{height:.1f}%', ha='center', va='bottom')
    for bar in bars2:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height - 1.5,
                f'{height:.1f}%', ha='center', va='top')
    
    plt.tight_layout()
    save_path = save_dir / '02_coin_analysis.png'
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"✅ 저장: {save_path.name}")

def create_dca_analysis(df: pd.DataFrame, save_dir: Path):
    """DCA 설정별 분석"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('DCA Configuration Analysis', fontsize=16, fontweight='bold')
    
    # 1. DCA 설정별 평균 수익률
    ax1 = axes[0, 0]
    dca_avg = df.groupby('config')['total_return'].mean().sort_values(ascending=False)
    bars = ax1.barh(range(len(dca_avg)), dca_avg)
    ax1.set_yticks(range(len(dca_avg)))
    ax1.set_yticklabels(dca_avg.index)
    ax1.set_xlabel('Return (%)')
    ax1.set_title('Average Return by DCA Config')
    ax1.grid(True, alpha=0.3)
    
    # 색상 설정
    colors = ['green' if x > 0 else 'red' for x in dca_avg]
    for bar, color in zip(bars, colors):
        bar.set_color(color)
    
    # 값 표시
    for i, v in enumerate(dca_avg):
        ax1.text(v + 0.5 if v > 0 else v - 0.5, i, f'{v:.1f}%', 
                va='center', ha='left' if v > 0 else 'right')
    
    # 2. DCA 설정별 승률
    ax2 = axes[0, 1]
    dca_wr = df.groupby('config')['win_rate'].mean().sort_values(ascending=False)
    bars = ax2.barh(range(len(dca_wr)), dca_wr, color='lightblue')
    ax2.set_yticks(range(len(dca_wr)))
    ax2.set_yticklabels(dca_wr.index)
    ax2.set_xlabel('Win Rate (%)')
    ax2.set_title('Average Win Rate by DCA Config')
    ax2.grid(True, alpha=0.3)
    
    for i, v in enumerate(dca_wr):
        ax2.text(v + 0.5, i, f'{v:.1f}%', va='center')
    
    # 3. 익절/손절 vs 수익률 산점도
    ax3 = axes[1, 0]
    scatter = ax3.scatter(df['profit_target'], df['stop_loss'], 
                         c=df['total_return'], cmap='RdYlGn', s=50, alpha=0.6)
    ax3.set_xlabel('Profit Target (%)')
    ax3.set_ylabel('Stop Loss (%)')
    ax3.set_title('Profit/Stop vs Return')
    plt.colorbar(scatter, ax=ax3, label='Return (%)')
    ax3.grid(True, alpha=0.3)
    
    # 4. DCA 설정별 거래횟수 vs 수익률
    ax4 = axes[1, 1]
    dca_stats = df.groupby('config').agg({
        'total_return': 'mean',
        'total_trades': 'mean'
    })
    ax4.scatter(dca_stats['total_trades'], dca_stats['total_return'], s=100)
    
    # 라벨 추가
    for idx, row in dca_stats.iterrows():
        ax4.annotate(idx[:10], (row['total_trades'], row['total_return']),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    ax4.set_xlabel('Average Trade Count')
    ax4.set_ylabel('Average Return (%)')
    ax4.set_title('Trade Count vs Return')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='red', linestyle='--', linewidth=0.5)
    
    plt.tight_layout()
    save_path = save_dir / '03_dca_analysis.png'
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"✅ 저장: {save_path.name}")

def create_top10_chart(df: pd.DataFrame, save_dir: Path):
    """상위 10개 전략 상세 차트"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Top 10 Strategies Analysis', fontsize=16, fontweight='bold')
    
    # 상위 10개 선택
    top10 = df.nlargest(10, 'total_return')
    
    # 1. 상위 10개 수익률
    ax1 = axes[0, 0]
    x_labels = [f"{row['strategy'][:8]}\n{row['symbol'][-3:]}\n{row['config'][:5]}" 
                for _, row in top10.iterrows()]
    bars = ax1.bar(range(len(top10)), top10['total_return'].values, color='green')
    ax1.set_xticks(range(len(top10)))
    ax1.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=8)
    ax1.set_ylabel('Return (%)')
    ax1.set_title('Top 10 Returns')
    ax1.grid(True, alpha=0.3)
    
    # 값 표시
    for i, v in enumerate(top10['total_return'].values):
        ax1.text(i, v + 0.5, f'{v:.1f}%', ha='center', fontsize=9)
    
    # 2. 상위 10개 승률
    ax2 = axes[0, 1]
    bars = ax2.bar(range(len(top10)), top10['win_rate'].values, color='lightblue')
    ax2.set_xticks(range(len(top10)))
    ax2.set_xticklabels(range(1, 11))
    ax2.set_xlabel('Rank')
    ax2.set_ylabel('Win Rate (%)')
    ax2.set_title('Top 10 Win Rates')
    ax2.grid(True, alpha=0.3)
    
    for i, v in enumerate(top10['win_rate'].values):
        ax2.text(i, v + 0.5, f'{v:.1f}%', ha='center', fontsize=9)
    
    # 3. 거래횟수
    ax3 = axes[1, 0]
    bars = ax3.bar(range(len(top10)), top10['total_trades'].values, color='orange')
    ax3.set_xticks(range(len(top10)))
    ax3.set_xticklabels(range(1, 11))
    ax3.set_xlabel('Rank')
    ax3.set_ylabel('Trade Count')
    ax3.set_title('Top 10 Trade Counts')
    ax3.grid(True, alpha=0.3)
    
    for i, v in enumerate(top10['total_trades'].values):
        ax3.text(i, v + 0.5, f'{int(v)}', ha='center', fontsize=9)
    
    # 4. 전략 구성 파이차트
    ax4 = axes[1, 1]
    strategy_counts = top10['strategy'].value_counts()
    colors = plt.cm.Set3(np.linspace(0, 1, len(strategy_counts)))
    wedges, texts, autotexts = ax4.pie(strategy_counts.values, 
                                        labels=strategy_counts.index,
                                        autopct='%1.0f%%',
                                        colors=colors)
    ax4.set_title('Top 10 Strategy Distribution')
    
    # 폰트 크기 조정
    for text in texts:
        text.set_fontsize(9)
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(9)
        autotext.set_weight('bold')
    
    plt.tight_layout()
    save_path = save_dir / '04_top10_analysis.png'
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"✅ 저장: {save_path.name}")

def create_comprehensive_dashboard(df: pd.DataFrame, save_dir: Path):
    """종합 대시보드"""
    fig = plt.figure(figsize=(20, 12))
    
    # 제목
    fig.suptitle('Hybrid Strategy DCA Backtest - Comprehensive Dashboard', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    # 1. 전략별 평균 수익률 (왼쪽 상단)
    ax1 = plt.subplot(3, 4, 1)
    strategy_avg = df.groupby('strategy')['total_return'].mean().sort_values(ascending=False)
    bars = ax1.bar(range(len(strategy_avg)), strategy_avg.values)
    ax1.set_xticks(range(len(strategy_avg)))
    ax1.set_xticklabels([s[:8] for s in strategy_avg.index], rotation=45, ha='right')
    ax1.set_ylabel('Return (%)')
    ax1.set_title('Avg Return by Strategy', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 색상 설정
    colors = ['green' if x > 0 else 'red' for x in strategy_avg.values]
    for bar, color in zip(bars, colors):
        bar.set_color(color)
    
    # 2. 코인별 평균 수익률
    ax2 = plt.subplot(3, 4, 2)
    coin_avg = df.groupby('symbol')['total_return'].mean().sort_values(ascending=False)
    bars = ax2.bar(range(len(coin_avg)), coin_avg.values)
    ax2.set_xticks(range(len(coin_avg)))
    ax2.set_xticklabels(coin_avg.index)
    ax2.set_ylabel('Return (%)')
    ax2.set_title('Avg Return by Coin', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    colors = ['green' if x > 0 else 'red' for x in coin_avg.values]
    for bar, color in zip(bars, colors):
        bar.set_color(color)
    
    # 3. 상위 5개 전략
    ax3 = plt.subplot(3, 4, 3)
    top5 = df.nlargest(5, 'total_return')
    labels = [f"{row['strategy'][:4]}\n{row['symbol'][-3:]}" for _, row in top5.iterrows()]
    bars = ax3.bar(range(len(top5)), top5['total_return'].values, color='darkgreen')
    ax3.set_xticks(range(len(top5)))
    ax3.set_xticklabels(labels, fontsize=8)
    ax3.set_ylabel('Return (%)')
    ax3.set_title('Top 5 Strategies', fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # 4. 최악 5개 전략
    ax4 = plt.subplot(3, 4, 4)
    bottom5 = df.nsmallest(5, 'total_return')
    labels = [f"{row['strategy'][:4]}\n{row['symbol'][-3:]}" for _, row in bottom5.iterrows()]
    bars = ax4.bar(range(len(bottom5)), bottom5['total_return'].values, color='darkred')
    ax4.set_xticks(range(len(bottom5)))
    ax4.set_xticklabels(labels, fontsize=8)
    ax4.set_ylabel('Return (%)')
    ax4.set_title('Bottom 5 Strategies', fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    # 5. 전략-코인 히트맵
    ax5 = plt.subplot(3, 4, (5, 6))
    pivot = df.pivot_table(values='total_return', index='strategy', columns='symbol', aggfunc='mean')
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', center=0, ax=ax5, cbar_kws={'label': 'Return (%)'})
    ax5.set_title('Strategy-Coin Heatmap', fontsize=10)
    ax5.set_xlabel('')
    ax5.set_ylabel('')
    
    # 6. DCA 설정별 수익률 분포
    ax6 = plt.subplot(3, 4, (7, 8))
    dca_configs = df['config'].unique()[:5]  # 상위 5개만
    data_to_plot = [df[df['config'] == c]['total_return'].values for c in dca_configs]
    bp = ax6.boxplot(data_to_plot, labels=[c[:10] for c in dca_configs])
    ax6.set_xticklabels([c[:10] for c in dca_configs], rotation=45, ha='right', fontsize=8)
    ax6.set_ylabel('Return (%)')
    ax6.set_title('Return Distribution by DCA Config', fontsize=10)
    ax6.grid(True, alpha=0.3)
    ax6.axhline(y=0, color='red', linestyle='--', linewidth=0.5)
    
    # 7. 승률 vs 수익률 산점도
    ax7 = plt.subplot(3, 4, 9)
    scatter = ax7.scatter(df['win_rate'], df['total_return'], 
                         c=df['total_trades'], cmap='viridis', alpha=0.6, s=30)
    ax7.set_xlabel('Win Rate (%)')
    ax7.set_ylabel('Return (%)')
    ax7.set_title('Win Rate vs Return', fontsize=10)
    ax7.grid(True, alpha=0.3)
    ax7.axhline(y=0, color='red', linestyle='--', linewidth=0.5)
    ax7.axvline(x=50, color='gray', linestyle='--', linewidth=0.5)
    
    # 8. 거래횟수 vs 수익률
    ax8 = plt.subplot(3, 4, 10)
    ax8.scatter(df['total_trades'], df['total_return'], alpha=0.6, s=30)
    ax8.set_xlabel('Trade Count')
    ax8.set_ylabel('Return (%)')
    ax8.set_title('Trade Count vs Return', fontsize=10)
    ax8.grid(True, alpha=0.3)
    ax8.axhline(y=0, color='red', linestyle='--', linewidth=0.5)
    
    # 9. 전략별 승률
    ax9 = plt.subplot(3, 4, 11)
    strategy_wr = df.groupby('strategy')['win_rate'].mean().sort_values(ascending=False)
    bars = ax9.bar(range(len(strategy_wr)), strategy_wr.values, color='skyblue')
    ax9.set_xticks(range(len(strategy_wr)))
    ax9.set_xticklabels([s[:8] for s in strategy_wr.index], rotation=45, ha='right')
    ax9.set_ylabel('Win Rate (%)')
    ax9.set_title('Avg Win Rate by Strategy', fontsize=10)
    ax9.grid(True, alpha=0.3)
    
    # 10. 통계 요약 테이블
    ax10 = plt.subplot(3, 4, 12)
    ax10.axis('tight')
    ax10.axis('off')
    
    # 통계 계산
    stats_data = [
        ['Total Tests', str(len(df))],
        ['Avg Return', f"{df['total_return'].mean():.2f}%"],
        ['Max Return', f"{df['total_return'].max():.2f}%"],
        ['Min Return', f"{df['total_return'].min():.2f}%"],
        ['Avg Win Rate', f"{df['win_rate'].mean():.1f}%"],
        ['Avg Trades', f"{df['total_trades'].mean():.0f}"]
    ]
    
    table = ax10.table(cellText=stats_data, 
                      colLabels=['Metric', 'Value'],
                      cellLoc='left',
                      loc='center',
                      colWidths=[0.5, 0.5])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    
    # 헤더 색상
    for i in range(2):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    plt.tight_layout()
    save_path = save_dir / '05_comprehensive_dashboard.png'
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"✅ 저장: {save_path.name}")

def main():
    """메인 실행 함수"""
    # 프로젝트 루트 찾기
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    results_dir = project_root / 'backtest_results'
    
    print("\n" + "="*80)
    print("📊 백테스트 결과 시각화 시작")
    print("="*80)
    
    # 결과 파일 로드
    df = load_results(results_dir)
    if df is None:
        return
    
    # 차트 저장 디렉토리
    charts_dir = results_dir / 'charts'
    charts_dir.mkdir(exist_ok=True)
    
    print(f"\n📁 차트 저장 위치: {charts_dir}")
    print("\n차트 생성 중...")
    print("-"*40)
    
    # 각 차트 생성
    create_strategy_comparison(df, charts_dir)
    create_coin_analysis(df, charts_dir)
    create_dca_analysis(df, charts_dir)
    create_top10_chart(df, charts_dir)
    create_comprehensive_dashboard(df, charts_dir)
    
    print("-"*40)
    print(f"\n✅ 모든 차트 생성 완료!")
    print(f"📁 저장 위치: {charts_dir}")
    print("\n생성된 차트:")
    print("  1. 01_strategy_comparison.png - 전략별 비교")
    print("  2. 02_coin_analysis.png - 코인별 분석")
    print("  3. 03_dca_analysis.png - DCA 설정 분석")
    print("  4. 04_top10_analysis.png - 상위 10개 전략")
    print("  5. 05_comprehensive_dashboard.png - 종합 대시보드")
    print("\n" + "="*80)

if __name__ == "__main__":
    main()