"""
Upbit API ISO 형식 테스트 - 응답 확인
"""

import requests
from datetime import datetime, timedelta

print("=" * 80)
print("Upbit API ISO 형식 테스트 - 응답 확인")
print("=" * 80)

url = "https://api.upbit.com/v1/candles/minutes/1"
end_time = datetime.now()

# 테스트 1: 기본 isoformat() (마이크로초 포함)
print(f"\n[테스트 1] 기본 isoformat(): {end_time.isoformat()}")
params_1 = {
    'market': 'KRW-BTC',
    'to': end_time.isoformat(),
    'count': 3
}

response_1 = requests.get(url, params=params_1)
print(f"Status Code: {response_1.status_code}")
print(f"Response Type: {type(response_1.json())}")
print(f"Response: {response_1.json()}")

# 테스트 2: isoformat() 정규화 (초 단위까지만)
normalized_time = end_time.replace(microsecond=0).isoformat()
print(f"\n[테스트 2] 정규화된 isoformat(): {normalized_time}")
params_2 = {
    'market': 'KRW-BTC',
    'to': normalized_time,
    'count': 3
}

response_2 = requests.get(url, params=params_2)
print(f"Status Code: {response_2.status_code}")
print(f"Response Type: {type(response_2.json())}")
data_2 = response_2.json()

if isinstance(data_2, list):
    print(f"✅ 성공! {len(data_2)}개 캔들 수신")
    for candle in data_2:
        print(f"  {candle['candle_date_time_kst']}")
else:
    print(f"❌ 에러: {data_2}")

print("\n" + "=" * 80)
