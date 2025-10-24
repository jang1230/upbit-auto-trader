"""
데이터 수집 페이지네이션 테스트
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
print("페이지네이션 테스트 - 600개 캔들 수집 (약 10시간)")
print("=" * 80)

# 데이터 수집기 생성
fetcher = HistoricalDataFetcher()

# 테스트: 최근 10시간 1분봉 데이터 (약 600개)
end_date = datetime.now()
start_date = end_date - timedelta(hours=10)

print(f"\n요청 기간: {start_date} ~ {end_date}")
print(f"예상 캔들 수: ~600개 (10시간 × 60분)")
print("")

try:
    df = fetcher.fetch_candles(
        symbol='KRW-BTC',
        start_date=start_date,
        end_date=end_date,
        interval='minute1',
        use_cache=False  # 캐시 사용 안 함 (실제 API 테스트)
    )

    print(f"\n✅ 수집 성공!")
    print(f"   총 캔들 수: {len(df):,}개")
    print(f"   실제 기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"\n처음 5개 캔들:")
    print(df.head())
    print(f"\n마지막 5개 캔들:")
    print(df.tail())

except Exception as e:
    print(f"\n❌ 수집 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
