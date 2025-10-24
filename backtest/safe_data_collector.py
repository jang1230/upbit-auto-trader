"""
간단 과거 데이터 수집기
Simple Historical Data Collector

목표: 2022-01-01 ~ 2024-10-19 BTC 분봉 데이터 수집
"""

import pandas as pd
import pyupbit
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def collect_historical_data(
    symbol: str,
    start_date: str,  # 'YYYY-MM-DD'
    end_date: str,    # 'YYYY-MM-DD'
    delay_seconds: float = 0.15  # 초당 6.7회
) -> pd.DataFrame:
    """
    과거 데이터 수집

    Args:
        symbol: 심볼 (예: 'KRW-BTC')
        start_date: 시작일 ('2022-01-01')
        end_date: 종료일 ('2024-10-19')
        delay_seconds: API 대기 시간 (초, 기본 0.15초)

    Returns:
        pd.DataFrame: 수집된 데이터
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 {symbol} 데이터 수집 시작")
    logger.info(f"기간: {start_date} ~ {end_date}")
    logger.info(f"API 대기: {delay_seconds}초 (초당 {1/delay_seconds:.1f}회)")
    logger.info(f"{'='*80}\n")

    # 날짜 파싱
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)  # 23:59:59

    all_data = []
    current_time = start_dt  # ✅ 2022-01-01부터 시작!
    request_count = 0
    start_time = time.time()

    logger.info(f"시작 시점: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    while current_time < end_dt:
        request_count += 1

        # API 호출
        logger.info(f"🔄 요청 #{request_count}: {current_time.strftime('%Y-%m-%d %H:%M')} 이전 200개")

        df = pyupbit.get_ohlcv(
            ticker=symbol,
            interval='minute1',
            to=current_time.strftime('%Y%m%d%H%M%S'),
            count=200
        )

        if df is None or len(df) == 0:
            logger.warning(f"⚠️ 데이터 없음, 중단")
            break

        # 데이터 추가
        all_data.append(df)
        total_candles = sum(len(d) for d in all_data)

        # 진행상황 표시
        elapsed = time.time() - start_time
        oldest_time = df.index[0].strftime('%Y-%m-%d %H:%M')
        newest_time = df.index[-1].strftime('%Y-%m-%d %H:%M')

        logger.info(f"✅ {len(df)}개 수집 (총 {total_candles:,}개, 경과 {elapsed/60:.1f}분)")
        logger.info(f"   📅 범위: {oldest_time} ~ {newest_time}")

        # 다음 구간 설정 (최신 시간 + 1분)
        current_time = df.index[-1] + timedelta(minutes=1)

        # 종료일 도달 확인
        if df.index[-1] >= end_dt:
            logger.info(f"\n✅ 종료일 도달! 수집 완료")
            break

        # API 대기
        time.sleep(delay_seconds)

    # 데이터 병합
    if not all_data:
        logger.error("❌ 수집된 데이터 없음")
        return pd.DataFrame()

    logger.info(f"\n📦 데이터 병합 중...")
    final_df = pd.concat(all_data)
    final_df = final_df.sort_index()
    final_df = final_df[~final_df.index.duplicated(keep='first')]

    # 날짜 범위 필터링
    final_df = final_df[(final_df.index >= start_dt) & (final_df.index <= end_dt)]

    total_time = time.time() - start_time
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ {symbol} 수집 완료!")
    logger.info(f"총 캔들: {len(final_df):,}개")

    if len(final_df) > 0:
        logger.info(f"기간: {final_df.index[0]} ~ {final_df.index[-1]}")
    else:
        logger.warning(f"⚠️ 날짜 범위 내 데이터 없음")

    logger.info(f"소요 시간: {total_time/60:.1f}분")
    logger.info(f"API 호출: {request_count}회")
    logger.info(f"{'='*80}\n")

    return final_df


def save_to_csv(
    df: pd.DataFrame,
    symbol: str,
    start_date: str,
    end_date: str,
    output_dir: str = "data/historical"
) -> str:
    """CSV 저장"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    start = start_date.replace('-', '')
    end = end_date.replace('-', '')
    filename = f"{symbol}_minute1_{start}_{end}.csv"
    filepath = output_path / filename

    df.reset_index(inplace=True)
    df.rename(columns={'index': 'timestamp'}, inplace=True)
    df.to_csv(filepath, index=False)

    logger.info(f"💾 저장: {filepath}")
    logger.info(f"📊 크기: {filepath.stat().st_size / 1024 / 1024:.1f}MB\n")

    return str(filepath)


def collect_and_save(
    symbol: str,
    start_date: str,
    end_date: str,
    delay_seconds: float = 0.15
) -> str:
    """수집 + 저장"""
    df = collect_historical_data(symbol, start_date, end_date, delay_seconds)

    if df.empty:
        logger.error("❌ 수집 실패")
        return None

    filepath = save_to_csv(df, symbol, start_date, end_date)
    return filepath


if __name__ == "__main__":
    # BTC 수집
    collect_and_save(
        symbol='KRW-BTC',
        start_date='2022-01-01',
        end_date='2024-10-19',
        delay_seconds=0.15  # 초당 6.7회
    )
