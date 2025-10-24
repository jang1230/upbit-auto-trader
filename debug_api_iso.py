"""
Upbit API ISO 형식 테스트
"""

import requests
from datetime import datetime, timedelta
import pandas as pd

print("=" * 80)
print("Upbit API ISO 형식 테스트")
print("=" * 80)

url = "https://api.upbit.com/v1/candles/minutes/1"

# 첫 번째 조회
end_time = datetime.now()
params_1 = {
    'market': 'KRW-BTC',
    'to': end_time.isoformat(),  # ISO 형식 사용
    'count': 3
}

print(f"\n첫 번째 요청: to={end_time.isoformat()}")
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
    'to': next_end.isoformat(),  # ISO 형식 사용
    'count': 3
}

print(f"\n두 번째 요청: to={next_end.isoformat()}")
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

# 세 번째 조회 (추가로 1분 빼기)
next_end_2 = oldest_time_2 - timedelta(minutes=1)
params_3 = {
    'market': 'KRW-BTC',
    'to': next_end_2.isoformat(),
    'count': 3
}

print(f"\n세 번째 요청: to={next_end_2.isoformat()}")
response_3 = requests.get(url, params=params_3)
data_3 = response_3.json()

print("응답 (원본 순서):")
for candle in data_3:
    print(f"  {candle['candle_date_time_kst']}")

reversed_3 = data_3[::-1]
oldest_time_3 = pd.to_datetime(reversed_3[0]['candle_date_time_kst'])
newest_time_3 = pd.to_datetime(reversed_3[-1]['candle_date_time_kst'])
print(f"\n역순 정렬 후 범위: {oldest_time_3} ~ {newest_time_3}")

print("\n" + "=" * 80)
if oldest_time != oldest_time_2 and oldest_time_2 != oldest_time_3:
    print("✅ 성공: 각 요청마다 다른 데이터를 반환합니다!")
else:
    print("❌ 실패: 여전히 같은 데이터를 반환합니다.")
print("=" * 80)
