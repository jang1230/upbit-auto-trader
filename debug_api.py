"""
Upbit API 직접 테스트 - 실제 응답 형식 확인
"""

import requests
from datetime import datetime, timedelta
import pandas as pd

print("=" * 80)
print("Upbit API 직접 테스트")
print("=" * 80)

# 테스트 1: 최근 5개 캔들 조회
print("\n[테스트 1] 최근 5개 1분봉 조회")
print("-" * 80)

url = "https://api.upbit.com/v1/candles/minutes/1"
params = {
    'market': 'KRW-BTC',
    'count': 5
}

response = requests.get(url, params=params)
data = response.json()

print(f"\n응답 개수: {len(data)}개")
print("\n📊 API 원본 응답 순서:")
for i, candle in enumerate(data):
    kst_time = candle['candle_date_time_kst']
    print(f"  [{i}] {kst_time} (가격: {candle['trade_price']:,}원)")

print("\n🔄 역순 정렬 후 (data[::-1]):")
reversed_data = data[::-1]
for i, candle in enumerate(reversed_data):
    kst_time = candle['candle_date_time_kst']
    print(f"  [{i}] {kst_time} (가격: {candle['trade_price']:,}원)")

# 테스트 2: to 파라미터로 과거 데이터 조회
print("\n" + "=" * 80)
print("[테스트 2] 'to' 파라미터로 과거 데이터 조회")
print("-" * 80)

# 첫 번째 조회
end_time = datetime.now()
params_1 = {
    'market': 'KRW-BTC',
    'to': end_time.strftime('%Y-%m-%d %H:%M:%S'),
    'count': 3
}

print(f"\n첫 번째 요청: to={end_time.strftime('%Y-%m-%d %H:%M:%S')}")
response_1 = requests.get(url, params=params_1)
data_1 = response_1.json()

print("응답 (원본 순서):")
for candle in data_1:
    print(f"  {candle['candle_date_time_kst']}")

# 역순 정렬
reversed_1 = data_1[::-1]
oldest_time = pd.to_datetime(reversed_1[0]['candle_date_time_kst'])
newest_time = pd.to_datetime(reversed_1[-1]['candle_date_time_kst'])
print(f"\n역순 정렬 후 범위: {oldest_time} ~ {newest_time}")
print(f"가장 오래된 캔들 (reversed[0]): {oldest_time}")

# 두 번째 조회 (1분 빼기)
next_end = oldest_time - timedelta(minutes=1)
params_2 = {
    'market': 'KRW-BTC',
    'to': next_end.strftime('%Y-%m-%d %H:%M:%S'),
    'count': 3
}

print(f"\n두 번째 요청: to={next_end.strftime('%Y-%m-%d %H:%M:%S')}")
response_2 = requests.get(url, params=params_2)
data_2 = response_2.json()

print("응답 (원본 순서):")
for candle in data_2:
    print(f"  {candle['candle_date_time_kst']}")

# 역순 정렬
reversed_2 = data_2[::-1]
oldest_time_2 = pd.to_datetime(reversed_2[0]['candle_date_time_kst'])
newest_time_2 = pd.to_datetime(reversed_2[-1]['candle_date_time_kst'])
print(f"\n역순 정렬 후 범위: {oldest_time_2} ~ {newest_time_2}")

print("\n" + "=" * 80)
print("✅ 테스트 완료")
print("=" * 80)
