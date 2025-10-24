#!/usr/bin/env python3
"""
데이터 로더 테스트 스크립트
실제 Upbit API로 소량의 과거 데이터 다운로드 테스트
"""

import sys
from datetime import datetime
from api.upbit_api import UpbitAPI
from core.database import CandleDatabase
from core.data_loader import UpbitDataLoader

print("=== UpbitDataLoader 테스트 ===\n")

# API 초기화 (API 키 없이 공개 데이터만 사용)
print("1️⃣ API 초기화")
api = UpbitAPI('', '')  # 공개 API는 키 없이도 사용 가능
print("   ✅ API 초기화 완료\n")

# 데이터베이스 초기화
print("2️⃣ 데이터베이스 초기화")
db = CandleDatabase()
print(f"   📁 DB 경로: {db.db_path}\n")

# 데이터 로더 생성
print("3️⃣ 데이터 로더 생성")
loader = UpbitDataLoader(api, db)
print("   ✅ 데이터 로더 준비 완료\n")

# 테스트 1: 최근 10개 캔들 다운로드
print("4️⃣ 최근 10개 1분봉 다운로드 테스트")
try:
    candles = loader.download_candles(
        market='KRW-BTC',
        interval='1m',
        count=10
    )
    print(f"   ✅ 다운로드 성공: {len(candles)}개")

    if candles:
        latest = candles[0]
        print(f"   📊 최근 캔들:")
        print(f"      시각: {latest['timestamp']}")
        print(f"      종가: {latest['close']:,.0f}원")
        print(f"      거래량: {latest['volume']:.4f}")
    print()

except Exception as e:
    print(f"   ❌ 오류: {e}\n")
    sys.exit(1)

# 테스트 2: 데이터 검증
print("5️⃣ 데이터 무결성 검증")
is_valid = loader.validate_data(candles)
print(f"   {'✅ 유효' if is_valid else '❌ 오류'}\n")

# 테스트 3: 배치 다운로드 (2024-01-01 00:00 ~ 01:00, 약 60개)
print("6️⃣ 배치 다운로드 테스트")
print("   기간: 2024-01-01 00:00 ~ 01:00 (1분봉)")

start = datetime(2024, 1, 1, 0, 0)
end = datetime(2024, 1, 1, 1, 0)

try:
    downloaded = loader.batch_download(
        market='KRW-BTC',
        interval='1m',
        start_date=start,
        end_date=end,
        show_progress=True
    )
    print(f"\n   ✅ 다운로드 완료: {downloaded}개\n")

except Exception as e:
    print(f"\n   ❌ 오류: {e}\n")
    sys.exit(1)

# 테스트 4: 데이터베이스 조회
print("7️⃣ 데이터베이스 조회")
stored = db.get_candles('KRW-BTC', '1m', start, end)
print(f"   저장된 캔들: {len(stored)}개")

if not stored.empty:
    print("\n   📊 저장된 데이터 샘플:")
    print(stored.head().to_string())
print()

# 테스트 5: 날짜 범위 확인
print("8️⃣ 저장된 데이터 날짜 범위")
date_range = db.get_date_range('KRW-BTC', '1m')
if date_range:
    print(f"   시작: {date_range[0]}")
    print(f"   종료: {date_range[1]}")

    # 총 캔들 수
    total = db.count_candles('KRW-BTC', '1m')
    print(f"   총 캔들: {total:,}개")
else:
    print("   데이터 없음")
print()

# 정리
api.close()
db.close()

print("=== ✅ 모든 테스트 통과! ===")
