"""
1년치 비트코인 데이터 수집 스크립트
JSON과 Excel 형식으로 저장
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from core.historical_data import HistoricalDataFetcher

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("📊 1년치 비트코인 데이터 수집")
print("=" * 80)

# 데이터 수집기 생성
fetcher = HistoricalDataFetcher()

# 1년치 기간 설정
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

print(f"\n수집 설정:")
print(f"  심볼: KRW-BTC")
print(f"  기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
print(f"  간격: 1분봉")
print(f"  예상 캔들 수: {365 * 24 * 60:,}개")
print(f"  예상 API 요청: {(365 * 24 * 60) // 200:,}회")
print(f"  예상 소요 시간: 약 4-5분")
print()

input("계속하려면 Enter를 누르세요...")

print("\n데이터 수집 시작...")
print("-" * 80)

# 데이터 수집
df = fetcher.fetch_candles(
    symbol='KRW-BTC',
    start_date=start_date,
    end_date=end_date,
    interval='minute1',
    use_cache=True  # 캐시 사용 (이미 수집된 부분은 재사용)
)

print("\n" + "=" * 80)
print("✅ 데이터 수집 완료!")
print("=" * 80)
print(f"수집된 캔들 수: {len(df):,}개")
print(f"실제 기간: {df.index[0]} ~ {df.index[-1]}")
print(f"데이터 크기: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

# 출력 디렉토리 생성
output_dir = Path(__file__).parent / 'data' / 'exports'
output_dir.mkdir(parents=True, exist_ok=True)

# 파일명 생성
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
base_filename = f"BTC_1year_{timestamp}"

# 1. CSV 저장 (가장 범용적)
csv_path = output_dir / f"{base_filename}.csv"
df.to_csv(csv_path, encoding='utf-8-sig')
print(f"\n💾 CSV 저장: {csv_path.name}")
print(f"   크기: {csv_path.stat().st_size / 1024 / 1024:.2f} MB")

# 2. JSON 저장
json_path = output_dir / f"{base_filename}.json"
df.to_json(json_path, orient='index', date_format='iso', indent=2)
print(f"\n💾 JSON 저장: {json_path.name}")
print(f"   크기: {json_path.stat().st_size / 1024 / 1024:.2f} MB")

# 3. Excel 저장 (시각적 확인에 좋음)
try:
    excel_path = output_dir / f"{base_filename}.xlsx"
    
    # Excel은 1,048,576행 제한이 있으므로 확인
    if len(df) > 1_000_000:
        print(f"\n⚠️ Excel 저장 생략: 데이터가 너무 큼 ({len(df):,}행 > 1,000,000행)")
        print(f"   Excel은 최대 1,048,576행까지만 지원합니다.")
    else:
        df.to_excel(excel_path, engine='openpyxl')
        print(f"\n💾 Excel 저장: {excel_path.name}")
        print(f"   크기: {excel_path.stat().st_size / 1024 / 1024:.2f} MB")
except ImportError:
    print(f"\n⚠️ Excel 저장 생략: openpyxl 패키지가 설치되지 않았습니다.")
    print(f"   설치: pip install openpyxl")

# 데이터 통계
print("\n" + "=" * 80)
print("📊 데이터 통계")
print("=" * 80)
print(f"\n가격 범위:")
print(f"  최저가: {df['low'].min():,.0f}원")
print(f"  최고가: {df['high'].max():,.0f}원")
print(f"  시작가: {df['open'].iloc[0]:,.0f}원")
print(f"  종료가: {df['close'].iloc[-1]:,.0f}원")
print(f"  변동폭: {(df['high'].max() - df['low'].min()):,.0f}원")

print(f"\n거래량:")
print(f"  최소: {df['volume'].min():.8f} BTC")
print(f"  최대: {df['volume'].max():.8f} BTC")
print(f"  평균: {df['volume'].mean():.8f} BTC")
print(f"  총 거래량: {df['volume'].sum():.2f} BTC")

# 월별 통계
print(f"\n월별 데이터 분포:")
monthly = df.resample('M').size()
for date, count in monthly.items():
    print(f"  {date.strftime('%Y-%m')}: {count:,}개 캔들")

print("\n" + "=" * 80)
print("✅ 모든 작업 완료!")
print("=" * 80)
print(f"\n저장된 파일:")
print(f"  📁 위치: {output_dir}")
print(f"  📄 CSV: {csv_path.name}")
print(f"  📄 JSON: {json_path.name}")
if excel_path.exists():
    print(f"  📄 Excel: {excel_path.name}")
print()
