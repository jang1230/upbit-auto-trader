"""
실제 업비트 데이터 다운로드 스크립트
Download Real Upbit Market Data

업비트에서 실제 BTC 거래 데이터를 다운로드합니다.

사용법:
    python scripts/download_real_data.py
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import pyupbit
except ImportError:
    print("❌ pyupbit가 설치되지 않았습니다.")
    print("설치 명령: pip3 install pyupbit")
    print("또는: pip3 install --break-system-packages pyupbit")
    sys.exit(1)


def download_btc_data(days: int = 365, interval: str = "day") -> pd.DataFrame:
    """
    업비트에서 BTC 데이터 다운로드

    Args:
        days: 가져올 일수
        interval: 캔들 간격 (day, minute1, minute3, minute5, minute10, minute15, minute30, minute60, minute240, week, month)

    Returns:
        pd.DataFrame: OHLCV 데이터
    """
    print(f"\n📊 업비트 데이터 다운로드 시작")
    print(f"   심볼: KRW-BTC")
    print(f"   기간: {days}일")
    print(f"   간격: {interval}")
    print()

    try:
        # 데이터 다운로드
        print("다운로드 중...", end=" ")
        df = pyupbit.get_ohlcv("KRW-BTC", interval=interval, count=days)

        if df is None or len(df) == 0:
            raise ValueError("데이터를 가져올 수 없습니다.")

        print("✅ 완료!")

        # 데이터 정보
        print(f"\n📈 데이터 정보:")
        print(f"   기간: {df.index[0]} ~ {df.index[-1]}")
        print(f"   캔들 수: {len(df):,}개")
        print(f"   가격 범위: {df['close'].min():,.0f}원 ~ {df['close'].max():,.0f}원")
        print(f"   평균 가격: {df['close'].mean():,.0f}원")
        print(f"   총 거래량: {df['volume'].sum():,.2f} BTC")

        # 결측치 확인
        missing = df.isnull().sum().sum()
        if missing > 0:
            print(f"\n⚠️  결측치: {missing}개 발견")
        else:
            print(f"\n✅ 결측치: 없음")

        return df

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise


def save_data(df: pd.DataFrame, filename: str = None):
    """
    데이터를 CSV 파일로 저장

    Args:
        df: 저장할 데이터
        filename: 파일명 (None이면 자동 생성)
    """
    # data 디렉토리 생성
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"\n📁 '{data_dir}' 디렉토리 생성")

    # 파일명 생성
    if filename is None:
        today = datetime.now().strftime("%Y%m%d")
        filename = f"btc_{today}.csv"

    filepath = os.path.join(data_dir, filename)

    # 저장
    df.to_csv(filepath)
    print(f"\n💾 저장 완료: {filepath}")
    print(f"   파일 크기: {os.path.getsize(filepath) / 1024:.1f} KB")


def download_multiple_periods():
    """
    여러 기간의 데이터 다운로드

    - 2024년 전체 (365일)
    - 최근 6개월 (180일)
    - 최근 3개월 (90일)
    - 최근 1개월 (30일)
    """
    periods = [
        (365, "btc_1year.csv", "2024년 전체"),
        (180, "btc_6months.csv", "최근 6개월"),
        (90, "btc_3months.csv", "최근 3개월"),
        (30, "btc_1month.csv", "최근 1개월"),
    ]

    print("\n" + "="*70)
    print("📊 여러 기간 데이터 다운로드")
    print("="*70)

    for days, filename, description in periods:
        print(f"\n[{description}]")
        try:
            df = download_btc_data(days=days)
            save_data(df, filename)
        except Exception as e:
            print(f"❌ {description} 다운로드 실패: {e}")

    print("\n" + "="*70)
    print("✅ 모든 데이터 다운로드 완료")
    print("="*70)


def analyze_market_regime(df: pd.DataFrame):
    """
    시장 환경 분석

    상승장/하락장/횡보장 구간 식별

    Args:
        df: OHLCV 데이터
    """
    print("\n" + "="*70)
    print("📈 시장 환경 분석")
    print("="*70)

    # 일일 수익률 계산
    df['returns'] = df['close'].pct_change()

    # 20일 이동평균 수익률
    df['ma_returns'] = df['returns'].rolling(window=20).mean()

    # 시장 환경 분류
    def classify(ret):
        if pd.isna(ret):
            return 'Unknown'
        elif ret > 0.005:  # > 0.5%
            return 'Bull'  # 상승장
        elif ret < -0.005:  # < -0.5%
            return 'Bear'  # 하락장
        else:
            return 'Sideways'  # 횡보장

    df['regime'] = df['ma_returns'].apply(classify)

    # 통계 계산
    regime_stats = df.groupby('regime').agg({
        'close': ['count', 'mean'],
        'returns': ['mean', 'std']
    }).round(4)

    print(f"\n시장 환경별 통계:")
    print(regime_stats)

    # 구간별 비율
    regime_pct = (df['regime'].value_counts() / len(df) * 100).round(1)
    print(f"\n시장 환경 비율:")
    for regime, pct in regime_pct.items():
        print(f"   {regime}: {pct}%")

    # 최근 환경
    recent_regime = df['regime'].iloc[-1]
    print(f"\n현재 시장 환경: {recent_regime}")


def main():
    """메인 실행 함수"""
    print("\n" + "="*70)
    print("업비트 실제 데이터 다운로드 스크립트")
    print("Upbit Real Market Data Downloader")
    print("="*70)

    # 1. 기본 데이터 다운로드 (1년)
    print("\n[1] 기본 데이터 다운로드 (1년)")
    try:
        df = download_btc_data(days=365)
        save_data(df, "btc_2024.csv")

        # 시장 환경 분석
        analyze_market_regime(df)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        return

    # 2. 추가 옵션
    print("\n" + "="*70)
    print("추가 옵션:")
    print("  1. 여러 기간 데이터 다운로드")
    print("  2. 종료")
    print("="*70)

    choice = input("\n선택 (1-2): ").strip()

    if choice == "1":
        download_multiple_periods()
    else:
        print("\n프로그램을 종료합니다.")

    print("\n" + "="*70)
    print("✅ 완료!")
    print("="*70)
    print("\n다음 단계:")
    print("  1. 전략 재검증: python tests/test_strategies_real_data.py")
    print("  2. 리스크 관리 테스트: python tests/test_risk_management.py")
    print()


if __name__ == "__main__":
    main()
