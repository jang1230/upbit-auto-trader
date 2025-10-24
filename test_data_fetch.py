"""
데이터 수집 테스트 스크립트
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
print("데이터 수집 테스트")
print("=" * 80)

# 데이터 수집기 생성
fetcher = HistoricalDataFetcher()

# 테스트 1: 일봉 데이터 (빠름)
print("\n[테스트 1] 일봉 데이터 수집 (30일)")
print("-" * 80)

end_date = datetime.now()
start_date = end_date - timedelta(days=30)

try:
    df_day = fetcher.fetch_candles(
        symbol='KRW-BTC',
        start_date=start_date,
        end_date=end_date,
        interval='day',
        use_cache=False  # 캐시 사용 안 함 (실제 API 테스트)
    )

    print(f"\n✅ 일봉 데이터 수집 성공!")
    print(f"   수집된 캔들 수: {len(df_day):,}개")
    print(f"   기간: {df_day.index[0]} ~ {df_day.index[-1]}")
    print(f"\n데이터 미리보기:")
    print(df_day.head())

except Exception as e:
    print(f"\n❌ 일봉 데이터 수집 실패: {e}")
    import traceback
    traceback.print_exc()

# 테스트 2: 1분봉 데이터 (적은 양)
print("\n" + "=" * 80)
print("[테스트 2] 1분봉 데이터 수집 (최근 500개)")
print("-" * 80)

# 500개 캔들 = 약 8시간 정도
end_date = datetime.now()
start_date = end_date - timedelta(hours=10)

try:
    df_minute = fetcher.fetch_candles(
        symbol='KRW-BTC',
        start_date=start_date,
        end_date=end_date,
        interval='minute1',
        use_cache=False
    )

    print(f"\n✅ 1분봉 데이터 수집 성공!")
    print(f"   수집된 캔들 수: {len(df_minute):,}개")
    print(f"   기간: {df_minute.index[0]} ~ {df_minute.index[-1]}")
    print(f"\n데이터 미리보기:")
    print(df_minute.head())

except Exception as e:
    print(f"\n❌ 1분봉 데이터 수집 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("데이터 수집 테스트 완료")
print("=" * 80)
