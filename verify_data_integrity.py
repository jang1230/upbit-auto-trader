"""
데이터 무결성 검증 스크립트
"""

import logging
from datetime import datetime, timedelta
from core.historical_data import HistoricalDataFetcher

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("📊 데이터 무결성 검증")
print("=" * 80)

fetcher = HistoricalDataFetcher()

# 30일치 1분봉 데이터 수집
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

print(f"\n수집 기간: {start_date} ~ {end_date}")
print(f"예상 캔들 수: {30 * 24 * 60:,}개 (30일 × 24시간 × 60분)")
print()

df = fetcher.fetch_candles(
    symbol='KRW-BTC',
    start_date=start_date,
    end_date=end_date,
    interval='minute1',
    use_cache=True
)

print("\n" + "=" * 80)
print("🔍 데이터 검증 결과")
print("=" * 80)

# 1. 기본 정보
print(f"\n✅ 수집된 캔들 수: {len(df):,}개")
print(f"✅ 실제 기간: {df.index[0]} ~ {df.index[-1]}")
print(f"✅ 예상 대비 비율: {len(df) / (30 * 24 * 60) * 100:.1f}%")

# 2. 시간 간격 검증 (1분 간격이 맞는지)
time_diffs = df.index.to_series().diff()
print(f"\n⏱️ 시간 간격 분석:")
print(f"  - 최소 간격: {time_diffs.min()}")
print(f"  - 최대 간격: {time_diffs.max()}")
print(f"  - 평균 간격: {time_diffs.mean()}")

# 3. 결측치 검증
missing_minutes = time_diffs[time_diffs > timedelta(minutes=1)]
if len(missing_minutes) > 0:
    print(f"\n⚠️ 1분 이상 간격 발생 횟수: {len(missing_minutes)}회")
    print(f"  (거래소 휴장, 거래 중단 등으로 인한 정상적인 현상)")
else:
    print(f"\n✅ 모든 캔들이 1분 간격으로 연속됨")

# 4. 데이터 품질 검증
print(f"\n📊 데이터 품질:")
print(f"  - 결측치: {df.isnull().sum().sum()}개")
print(f"  - 중복 타임스탬프: {df.index.duplicated().sum()}개")

# 5. 가격 데이터 검증
print(f"\n💰 가격 데이터:")
print(f"  - 최저가: {df['low'].min():,.0f}원")
print(f"  - 최고가: {df['high'].max():,.0f}원")
print(f"  - 시작가: {df['open'].iloc[0]:,.0f}원")
print(f"  - 종료가: {df['close'].iloc[-1]:,.0f}원")

# 6. 거래량 검증
print(f"\n📈 거래량 데이터:")
print(f"  - 최소 거래량: {df['volume'].min():.8f} BTC")
print(f"  - 최대 거래량: {df['volume'].max():.8f} BTC")
print(f"  - 평균 거래량: {df['volume'].mean():.8f} BTC")

print("\n" + "=" * 80)
print("✅ 데이터 검증 완료!")
print("=" * 80)
