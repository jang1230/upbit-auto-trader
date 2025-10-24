"""
Historical Data Fetcher
Upbit API를 통한 과거 캔들 데이터 수집

주요 기능:
- 과거 1분봉 캔들 데이터 수집
- 데이터 캐싱 (CSV 파일)
- 데이터 검증 및 결측치 처리
"""

import time
import logging
from typing import Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import requests

logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """
    과거 캔들 데이터 수집기

    Upbit API를 통해 과거 데이터를 수집하고 캐싱합니다.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        초기화

        Args:
            cache_dir: 캐시 디렉토리 (None이면 프로젝트 루트/data)
        """
        if cache_dir is None:
            project_root = Path(__file__).parent.parent
            cache_dir = project_root / 'data' / 'historical'

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Upbit API 엔드포인트
        self.base_url = "https://api.upbit.com/v1"

        logger.info(f"Historical Data Fetcher 초기화")
        logger.info(f"  캐시 디렉토리: {self.cache_dir}")

    def fetch_candles(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = 'minute1',
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        캔들 데이터 수집

        Args:
            symbol: 심볼 (예: 'KRW-BTC')
            start_date: 시작 날짜
            end_date: 종료 날짜
            interval: 캔들 간격 ('minute1', 'minute3', 'minute5', 'day')
            use_cache: 캐시 사용 여부

        Returns:
            pd.DataFrame: 캔들 데이터
                index: timestamp (datetime)
                columns: open, high, low, close, volume
        """
        logger.info(f"📊 캔들 데이터 수집 시작")
        logger.info(f"  심볼: {symbol}")
        logger.info(f"  기간: {start_date} ~ {end_date}")
        logger.info(f"  간격: {interval}")

        # 캐시 파일 경로
        cache_file = self._get_cache_path(symbol, start_date, end_date, interval)

        # 캐시 확인
        if use_cache and cache_file.exists():
            logger.info(f"  ✅ 캐시에서 로드: {cache_file.name}")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df

        # API에서 데이터 수집
        logger.info(f"  🌐 Upbit API에서 데이터 수집 중...")
        df = self._fetch_from_api(symbol, start_date, end_date, interval)

        # 캐시 저장
        if use_cache:
            df.to_csv(cache_file)
            logger.info(f"  💾 캐시 저장: {cache_file.name}")

        logger.info(f"  ✅ 수집 완료: {len(df):,}개 캔들")
        return df

    def _fetch_from_api(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> pd.DataFrame:
        """
        Upbit API에서 데이터 수집

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            interval: 캔들 간격

        Returns:
            pd.DataFrame: 캔들 데이터
        """
        all_candles = []
        
        # Upbit API의 'to' 파라미터는 UTC 시간을 사용하므로 KST → UTC 변환 (9시간 차이)
        current_end_utc = end_date - timedelta(hours=9)
        start_date_utc = start_date - timedelta(hours=9)

        # Upbit API는 최대 200개씩만 조회 가능
        while current_end_utc > start_date_utc:
            # API 요청 (UTC 시간 사용)
            candles = self._request_candles(symbol, current_end_utc, interval, count=200)

            if not candles:
                break

            all_candles.extend(candles)

            # 다음 요청을 위한 시간 계산 (역순 정렬 후 candles[0]이 가장 오래된 캔들)
            # 주의: API의 'to' 파라미터는 UTC 시간을 사용!
            oldest_candle = candles[0]
            newest_candle = candles[-1]
            oldest_time_kst = pd.to_datetime(oldest_candle['candle_date_time_kst'])
            newest_time_kst = pd.to_datetime(newest_candle['candle_date_time_kst'])
            oldest_time_utc = pd.to_datetime(oldest_candle['candle_date_time_utc'])

            # API의 'to'는 "이하"이므로, 1분을 빼서 중복 방지 (분봉은 1분 단위)
            current_end_utc = oldest_time_utc - timedelta(minutes=1)

            logger.info(f"    수집: {len(candles)}개 (총 {len(all_candles)}개) | 범위: {oldest_time_kst} ~ {newest_time_kst}")

            # Rate Limit 방지 (초당 10회 제한)
            time.sleep(0.1)

            # 시작 날짜 이전이면 종료 (UTC 기준 비교)
            if current_end_utc <= start_date_utc:
                logger.info(f"    종료: {current_end_utc} <= {start_date_utc}")
                break

        # DataFrame 변환
        df = self._convert_to_dataframe(all_candles)

        # 기간 필터링
        df = df[(df.index >= start_date) & (df.index <= end_date)]

        return df

    def _request_candles(
        self,
        symbol: str,
        to_datetime: datetime,
        interval: str,
        count: int = 200
    ) -> List[dict]:
        """
        Upbit API 캔들 조회 요청

        Args:
            symbol: 심볼
            to_datetime: 마지막 캔들 시각
            interval: 캔들 간격
            count: 조회 개수 (최대 200)

        Returns:
            List[dict]: 캔들 리스트
        """
        # interval 매핑
        interval_map = {
            'minute1': 'minutes/1',
            'minute3': 'minutes/3',
            'minute5': 'minutes/5',
            'minute10': 'minutes/10',
            'minute15': 'minutes/15',
            'minute30': 'minutes/30',
            'minute60': 'minutes/60',
            'minute240': 'minutes/240',
            'day': 'days',
            'week': 'weeks',
            'month': 'months'
        }

        interval_path = interval_map.get(interval, 'minutes/1')

        # API URL
        url = f"{self.base_url}/candles/{interval_path}"

        # 파라미터 (ISO 8601 형식으로 전달, 마이크로초 제거)
        to_param = to_datetime.replace(microsecond=0).isoformat()
        params = {
            'market': symbol,
            'to': to_param,
            'count': count
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Upbit API는 최신→과거 순으로 반환하므로 역순 정렬 (과거→최신)
            if isinstance(data, list):
                return data[::-1]
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 실패: {e}")
            return []

    def _convert_to_dataframe(self, candles: List[dict]) -> pd.DataFrame:
        """
        API 응답을 DataFrame으로 변환

        Args:
            candles: API 응답 캔들 리스트

        Returns:
            pd.DataFrame: 캔들 데이터
        """
        if not candles:
            return pd.DataFrame()

        # 데이터 추출
        data = []
        for candle in candles:
            data.append({
                'timestamp': pd.to_datetime(candle['candle_date_time_kst']),
                'open': candle['opening_price'],
                'high': candle['high_price'],
                'low': candle['low_price'],
                'close': candle['trade_price'],
                'volume': candle['candle_acc_trade_volume']
            })

        # DataFrame 생성
        df = pd.DataFrame(data)
        df = df.set_index('timestamp')
        df = df.sort_index()

        return df

    def _get_cache_path(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> Path:
        """
        캐시 파일 경로 생성

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            interval: 캔들 간격

        Returns:
            Path: 캐시 파일 경로
        """
        # 파일명 생성
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')

        filename = f"{symbol}_{interval}_{start_str}_{end_str}.csv"

        return self.cache_dir / filename

    def clear_cache(self, symbol: Optional[str] = None):
        """
        캐시 삭제

        Args:
            symbol: 특정 심볼만 삭제 (None이면 전체 삭제)
        """
        if symbol:
            # 특정 심볼 캐시만 삭제
            pattern = f"{symbol}_*.csv"
            deleted = 0
            for file in self.cache_dir.glob(pattern):
                file.unlink()
                deleted += 1
            logger.info(f"캐시 삭제: {symbol} ({deleted}개 파일)")
        else:
            # 전체 캐시 삭제
            deleted = 0
            for file in self.cache_dir.glob("*.csv"):
                file.unlink()
                deleted += 1
            logger.info(f"캐시 전체 삭제: {deleted}개 파일")


# 테스트 코드
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Historical Data Fetcher 테스트")
    print("=" * 80)

    # 데이터 수집기 생성
    fetcher = HistoricalDataFetcher()

    # 테스트: 최근 7일 BTC 1분봉 데이터
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    print(f"\n📊 테스트: BTC 1분봉 데이터 수집")
    print(f"  기간: {start_date} ~ {end_date}")

    df = fetcher.fetch_candles(
        symbol='KRW-BTC',
        start_date=start_date,
        end_date=end_date,
        interval='minute1',
        use_cache=True
    )

    print(f"\n✅ 수집 완료: {len(df):,}개 캔들")
    print(f"\n데이터 미리보기:")
    print(df.head())
    print(f"\n데이터 통계:")
    print(df.describe())

    print("\n" + "=" * 80)
