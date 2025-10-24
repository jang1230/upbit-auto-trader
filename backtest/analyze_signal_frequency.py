"""
매수 시그널 발생 빈도 분석 스크립트
Analyze Buy Signal Frequency

목표: 기술적 지표 조합별 매수 시그널 발생 빈도 측정
목표 범위: 하루 20~30회 (10개 코인 전체)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SignalFrequencyAnalyzer:
    """매수 시그널 빈도 분석기"""

    def __init__(self, df: pd.DataFrame, symbol: str):
        """
        Args:
            df: OHLCV 데이터프레임 (timestamp, open, high, low, close, volume)
            symbol: 심볼 (예: 'KRW-BTC')
        """
        self.df = df.copy()
        self.symbol = symbol
        self.df['date'] = pd.to_datetime(self.df['timestamp']).dt.date

    def calculate_bollinger_bands(self, period=20, std=2.0):
        """볼린저 밴드 계산"""
        self.df['bb_middle'] = self.df['close'].rolling(period).mean()
        rolling_std = self.df['close'].rolling(period).std()
        self.df['bb_upper'] = self.df['bb_middle'] + (rolling_std * std)
        self.df['bb_lower'] = self.df['bb_middle'] - (rolling_std * std)

    def calculate_macd(self, fast=12, slow=26, signal=9):
        """MACD 계산"""
        exp1 = self.df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = self.df['close'].ewm(span=slow, adjust=False).mean()
        self.df['macd'] = exp1 - exp2
        self.df['macd_signal'] = self.df['macd'].ewm(span=signal, adjust=False).mean()
        self.df['macd_hist'] = self.df['macd'] - self.df['macd_signal']

    def calculate_rsi(self, period=14):
        """RSI 계산"""
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

    def calculate_disparity(self, period=20):
        """이격도 계산"""
        ma = self.df['close'].rolling(period).mean()
        self.df[f'disparity_{period}'] = (self.df['close'] / ma) * 100

    def calculate_volume_ratio(self, period=20):
        """거래량 비율 계산"""
        self.df['volume_avg'] = self.df['volume'].rolling(period).mean()
        self.df['volume_ratio'] = self.df['volume'] / self.df['volume_avg']

    def calculate_all_indicators(self):
        """모든 지표 계산"""
        logger.info(f"📊 {self.symbol} 기술적 지표 계산 중...")

        self.calculate_bollinger_bands(period=20, std=2.0)
        self.calculate_macd(fast=12, slow=26, signal=9)
        self.calculate_rsi(period=14)
        self.calculate_disparity(period=5)
        self.calculate_disparity(period=20)
        self.calculate_volume_ratio(period=20)

        # NaN 제거
        self.df = self.df.dropna()

        logger.info(f"✅ 지표 계산 완료 ({len(self.df):,}개 캔들)")

    def check_bb_lower_touch(self):
        """볼린저밴드 하단선 터치"""
        return (self.df['low'] <= self.df['bb_lower']) & \
               (self.df['close'] >= self.df['bb_lower'])

    def check_macd_golden_cross(self):
        """MACD 골든크로스"""
        prev_macd = self.df['macd'].shift(1)
        prev_signal = self.df['macd_signal'].shift(1)

        return (prev_macd <= prev_signal) & \
               (self.df['macd'] > self.df['macd_signal'])

    def check_rsi_oversold(self, threshold=30):
        """RSI 과매도"""
        return self.df['rsi'] < threshold

    def check_disparity_low(self, period=20, threshold=95):
        """이격도 저점"""
        return self.df[f'disparity_{period}'] < threshold

    def check_volume_surge(self, ratio=2.0):
        """거래량 급증"""
        return self.df['volume_ratio'] >= ratio

    def strategy_conservative(self):
        """
        보수적 전략 (AND 조건)
        - BB 하단선 터치 AND
        - RSI < 30 AND
        - MACD 골든크로스 AND
        - 거래량 2배 이상
        """
        signal = (
            self.check_bb_lower_touch() &
            self.check_rsi_oversold(30) &
            self.check_macd_golden_cross() &
            self.check_volume_surge(2.0)
        )
        return signal

    def strategy_balanced(self):
        """
        균형 전략 (Mixed 조건) - 목표
        - (BB 하단선 터치 OR RSI < 30) AND
        - MACD 골든크로스 AND
        - 거래량 1.5배 이상
        """
        signal = (
            (self.check_bb_lower_touch() | self.check_rsi_oversold(30)) &
            self.check_macd_golden_cross() &
            self.check_volume_surge(1.5)
        )
        return signal

    def strategy_aggressive(self):
        """
        공격적 전략 (OR 조건)
        - BB 하단선 터치 OR
        - RSI < 30 OR
        - MACD 골든크로스 OR
        - 이격도 < 95
        """
        signal = (
            self.check_bb_lower_touch() |
            self.check_rsi_oversold(30) |
            self.check_macd_golden_cross() |
            self.check_disparity_low(20, 95)
        )
        return signal

    def strategy_rsi_only(self, threshold=20):
        """RSI만 사용 (단순 비교용)"""
        return self.check_rsi_oversold(threshold)

    def strategy_bb_only(self):
        """BB만 사용 (단순 비교용)"""
        return self.check_bb_lower_touch()

    def strategy_macd_volume(self):
        """
        MACD + 거래량 전략
        - MACD 골든크로스 AND
        - 거래량 1.5배 이상
        """
        signal = (
            self.check_macd_golden_cross() &
            self.check_volume_surge(1.5)
        )
        return signal

    def strategy_macd_volume_strict(self):
        """
        MACD + 거래량 엄격 (거래량 2배)
        - MACD 골든크로스 AND
        - 거래량 2배 이상
        """
        signal = (
            self.check_macd_golden_cross() &
            self.check_volume_surge(2.0)
        )
        return signal

    def strategy_macd_volume_rsi(self):
        """
        MACD + 거래량 + RSI 필터
        - MACD 골든크로스 AND
        - 거래량 1.5배 이상 AND
        - RSI < 50 (약한 필터)
        """
        signal = (
            self.check_macd_golden_cross() &
            self.check_volume_surge(1.5) &
            (self.df['rsi'] < 50)
        )
        return signal

    def strategy_bb_rsi_volume(self):
        """
        BB 또는 RSI + 거래량
        - (BB 하단선 터치 OR RSI < 30) AND
        - 거래량 2배 이상
        """
        signal = (
            (self.check_bb_lower_touch() | self.check_rsi_oversold(30)) &
            self.check_volume_surge(2.0)
        )
        return signal

    def strategy_disparity_macd_volume(self):
        """
        이격도 + MACD + 거래량
        - 20일 이격도 < 95 AND
        - MACD 골든크로스 AND
        - 거래량 1.5배 이상
        """
        signal = (
            self.check_disparity_low(20, 95) &
            self.check_macd_golden_cross() &
            self.check_volume_surge(1.5)
        )
        return signal

    def strategy_bb_macd(self):
        """
        BB + MACD (거래량 제외)
        - BB 하단선 터치 AND
        - MACD 골든크로스
        """
        signal = (
            self.check_bb_lower_touch() &
            self.check_macd_golden_cross()
        )
        return signal

    def analyze_daily_frequency(self, strategy_name: str, signals: pd.Series):
        """일별 매수 시그널 빈도 분석"""
        # 시그널이 있는 캔들만 필터링
        signal_df = self.df[signals].copy()

        if len(signal_df) == 0:
            logger.warning(f"⚠️ {strategy_name}: 시그널 없음")
            return None

        # 일별 그룹화
        daily_counts = signal_df.groupby('date').size()

        stats = {
            'strategy': strategy_name,
            'total_signals': len(signal_df),
            'total_days': len(self.df['date'].unique()),
            'signal_days': len(daily_counts),
            'avg_per_day': daily_counts.mean(),
            'min_per_day': daily_counts.min(),
            'max_per_day': daily_counts.max(),
            'median_per_day': daily_counts.median(),
            'std_per_day': daily_counts.std(),
            # 목표 범위 (20~30회) 달성 비율 (1개 코인 기준 2~3회)
            'in_target_range': ((daily_counts >= 2) & (daily_counts <= 3)).sum() / len(daily_counts) * 100
        }

        return stats, daily_counts

    def run_all_strategies(self):
        """모든 전략 실행 및 분석"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 매수 시그널 빈도 분석 시작: {self.symbol}")
        logger.info(f"기간: {self.df['date'].iloc[0]} ~ {self.df['date'].iloc[-1]}")
        logger.info(f"총 캔들: {len(self.df):,}개")
        logger.info(f"{'='*80}\n")

        strategies = {
            '1. 보수적 (Conservative)': self.strategy_conservative(),
            '2. 균형 (Balanced)': self.strategy_balanced(),
            '3. 공격적 (Aggressive)': self.strategy_aggressive(),
            '4. RSI 단독 (20)': self.strategy_rsi_only(20),
            '5. RSI 단독 (30)': self.strategy_rsi_only(30),
            '6. BB 단독': self.strategy_bb_only(),
            '7. MACD + 거래량 (1.5배)': self.strategy_macd_volume(),
            '8. MACD + 거래량 (2배) ⭐': self.strategy_macd_volume_strict(),
            '9. MACD + 거래량 + RSI ⭐': self.strategy_macd_volume_rsi(),
            '10. BB/RSI + 거래량2배 ⭐': self.strategy_bb_rsi_volume(),
            '11. 이격도 + MACD + 거래량': self.strategy_disparity_macd_volume(),
            '12. BB + MACD': self.strategy_bb_macd(),
        }

        all_stats = []
        all_daily_counts = {}

        for name, signals in strategies.items():
            result = self.analyze_daily_frequency(name, signals)
            if result is None:
                continue

            stats, daily_counts = result
            all_stats.append(stats)
            all_daily_counts[name] = daily_counts

            # 출력
            logger.info(f"📈 {name}")
            logger.info(f"   총 시그널: {stats['total_signals']:,}개")
            logger.info(f"   평균/일: {stats['avg_per_day']:.1f}회")
            logger.info(f"   범위: {stats['min_per_day']:.0f} ~ {stats['max_per_day']:.0f}회/일")
            logger.info(f"   중간값: {stats['median_per_day']:.1f}회/일")
            logger.info(f"   목표 범위(2~3회/일) 달성률: {stats['in_target_range']:.1f}%")

            # 10개 코인 추정
            estimated_total = stats['avg_per_day'] * 10
            logger.info(f"   💡 10개 코인 추정: 하루 {estimated_total:.0f}회")

            if 20 <= estimated_total <= 30:
                logger.info(f"   ✅ 목표 범위(20~30회) 달성!")
            elif estimated_total < 20:
                logger.info(f"   ⚠️ 시그널 부족 ({estimated_total:.0f}회 < 20회)")
            else:
                logger.info(f"   ⚠️ 시그널 과다 ({estimated_total:.0f}회 > 30회)")

            logger.info("")

        return pd.DataFrame(all_stats), all_daily_counts


def main():
    """메인 실행 함수"""
    # BTC 데이터 로드
    data_path = Path("data/historical/KRW-BTC_minute1_20220101_20241019.csv")

    if not data_path.exists():
        logger.error(f"❌ 데이터 파일 없음: {data_path}")
        logger.error(f"   먼저 safe_data_collector.py로 데이터를 수집하세요")
        return

    logger.info(f"📂 데이터 로드 중: {data_path}")
    df = pd.read_csv(data_path)
    logger.info(f"✅ 로드 완료: {len(df):,}개 캔들\n")

    # 분석기 생성 및 실행
    analyzer = SignalFrequencyAnalyzer(df, 'KRW-BTC')
    analyzer.calculate_all_indicators()

    stats_df, daily_counts = analyzer.run_all_strategies()

    # 결과 저장
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stats_file = output_dir / f"signal_frequency_stats_{timestamp}.csv"

    stats_df.to_csv(stats_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n💾 통계 저장: {stats_file}")

    # 일별 빈도 저장
    for strategy_name, daily_count in daily_counts.items():
        safe_name = strategy_name.replace(' ', '_').replace('(', '').replace(')', '').replace(',', '').replace('/', '_').replace('⭐', '')
        daily_file = output_dir / f"daily_frequency_{safe_name}_{timestamp}.csv"
        daily_count.to_csv(daily_file, header=['count'], encoding='utf-8-sig')

    logger.info(f"💾 일별 빈도 저장: {len(daily_counts)}개 전략")

    # 요약 출력
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 분석 완료 요약")
    logger.info(f"{'='*80}")
    logger.info(f"\n최적 전략 추천 (10개 코인 기준 20~30회):")

    stats_df['estimated_10_coins'] = stats_df['avg_per_day'] * 10
    target_strategies = stats_df[
        (stats_df['estimated_10_coins'] >= 20) &
        (stats_df['estimated_10_coins'] <= 30)
    ]

    if len(target_strategies) > 0:
        logger.info(f"\n✅ 목표 범위 달성 전략:")
        for idx, row in target_strategies.iterrows():
            logger.info(f"   - {row['strategy']}: 하루 {row['estimated_10_coins']:.0f}회")
    else:
        logger.info(f"\n⚠️ 목표 범위 달성 전략 없음")
        logger.info(f"   가장 가까운 전략:")
        stats_df['distance'] = abs(stats_df['estimated_10_coins'] - 25)
        closest = stats_df.nsmallest(3, 'distance')
        for idx, row in closest.iterrows():
            logger.info(f"   - {row['strategy']}: 하루 {row['estimated_10_coins']:.0f}회")

    logger.info(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
