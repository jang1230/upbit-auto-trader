"""
데이터 로더 모듈
Upbit API에서 과거 캔들 데이터 다운로드

주요 기능:
- 지정 기간의 캔들 데이터 다운로드
- 배치 다운로드 (200개씩 자동 분할)
- Rate Limit 자동 관리
- 진행률 표시
"""

import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from api.upbit_api import UpbitAPI
from core.database import CandleDatabase

# 한국 시간대 (KST = UTC+9)
KST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)


class UpbitDataLoader:
    """
    Upbit API 과거 데이터 다운로더

    Upbit API 제약:
    - 최대 200개 캔들/요청
    - Rate Limit: 600 req/min (시세 API)
    """

    # 지원하는 캔들 간격
    SUPPORTED_INTERVALS = {
        '1m': {'unit': 1, 'minutes': 1},
        '3m': {'unit': 3, 'minutes': 3},
        '5m': {'unit': 5, 'minutes': 5},
        '10m': {'unit': 10, 'minutes': 10},
        '15m': {'unit': 15, 'minutes': 15},
        '30m': {'unit': 30, 'minutes': 30},
        '1h': {'unit': 60, 'minutes': 60},
        '4h': {'unit': 240, 'minutes': 240},
        '1d': {'unit': 'days', 'minutes': 1440},
        '1w': {'unit': 'weeks', 'minutes': 10080},
        '1M': {'unit': 'months', 'minutes': 43200},
    }

    def __init__(self, api: UpbitAPI, database: CandleDatabase):
        """
        Args:
            api: UpbitAPI 인스턴스
            database: CandleDatabase 인스턴스
        """
        self.api = api
        self.db = database

    def download_candles(
        self,
        market: str,
        interval: str,
        to_datetime: Optional[datetime] = None,
        count: int = 200
    ) -> List[Dict]:
        """
        캔들 데이터 다운로드 (단일 요청)

        Args:
            market: 마켓 코드 (예: 'KRW-BTC')
            interval: 캔들 간격 (예: '1m', '5m', '1h', '1d')
            to_datetime: 마지막 캔들 시각 (None이면 현재)
            count: 캔들 개수 (최대 200)

        Returns:
            List[Dict]: 캔들 데이터 리스트 (시간 내림차순)
        """
        if interval not in self.SUPPORTED_INTERVALS:
            raise ValueError(f"지원하지 않는 간격: {interval}")

        if count > 200:
            logger.warning(f"count가 200을 초과하여 200으로 제한됨: {count}")
            count = 200

        try:
            # Upbit API 호출
            # to 파라미터에 KST 시간대 정보를 포함해서 전달
            to_param = None
            if to_datetime:
                # Naive datetime을 KST timezone-aware datetime으로 변환
                if to_datetime.tzinfo is None:
                    to_datetime_kst = to_datetime.replace(tzinfo=KST)
                else:
                    to_datetime_kst = to_datetime.astimezone(KST)

                to_param = to_datetime_kst.isoformat()

            candles = self.api.get_candles(
                market=market,
                unit=self._get_unit(interval),
                to=to_param,
                count=count
            )

            # 데이터 정규화
            normalized = []
            for candle in candles:
                normalized.append({
                    'timestamp': self._parse_timestamp(candle['candle_date_time_kst']),
                    'open': float(candle['opening_price']),
                    'high': float(candle['high_price']),
                    'low': float(candle['low_price']),
                    'close': float(candle['trade_price']),
                    'volume': float(candle['candle_acc_trade_volume'])
                })

            return normalized

        except Exception as e:
            logger.error(f"캔들 다운로드 실패: {e}")
            return []

    def batch_download(
        self,
        market: str,
        interval: str,
        start_date: datetime,
        end_date: datetime,
        show_progress: bool = True
    ) -> int:
        """
        기간별 캔들 데이터 배치 다운로드

        Args:
            market: 마켓 코드
            interval: 캔들 간격
            start_date: 시작 날짜 (포함)
            end_date: 종료 날짜 (포함)
            show_progress: 진행률 표시 여부

        Returns:
            int: 다운로드된 캔들 개수
        """
        logger.info(f"📥 배치 다운로드 시작: {market} {interval} ({start_date} ~ {end_date})")

        # 필요한 요청 횟수 계산
        total_minutes = self._calculate_total_minutes(start_date, end_date, interval)
        total_requests = (total_minutes // 200) + 1

        logger.info(f"   예상 캔들 수: {total_minutes:,}개")
        logger.info(f"   예상 요청 수: {total_requests:,}회")
        logger.info(f"   예상 소요 시간: {self._estimate_time(total_requests)}")

        # 배치 다운로드
        current_time = end_date
        downloaded_count = 0
        request_count = 0
        batch_size = 200

        while True:
            request_count += 1

            # 캔들 다운로드
            candles = self.download_candles(
                market=market,
                interval=interval,
                to_datetime=current_time,
                count=batch_size
            )

            if not candles:
                logger.warning("더 이상 다운로드할 데이터가 없습니다")
                break

            # 다음 요청을 위한 시간 업데이트 (가장 오래된 캔들 기준)
            oldest_candle = min(candles, key=lambda x: x['timestamp'])

            # 디버그 로그 (첫 10회만)
            if request_count <= 10:
                logger.info(f"요청 #{request_count}: oldest={oldest_candle['timestamp']}, start={start_date}")

            # 시작 날짜보다 오래된 캔들이 나타나면 필터링 후 종료
            if oldest_candle['timestamp'] < start_date:
                # 시작 날짜 이후 캔들만 필터링해서 저장
                filtered = [c for c in candles if c['timestamp'] >= start_date]
                if filtered:
                    inserted = self.db.insert_candles(filtered, market, interval)
                    downloaded_count += inserted
                logger.info(f"시작 날짜에 도달했습니다 (oldest={oldest_candle['timestamp']} < start={start_date})")
                break

            # 데이터베이스 저장 (모든 캔들이 범위 내)
            inserted = self.db.insert_candles(candles, market, interval)
            downloaded_count += inserted

            # 진행률 표시
            if show_progress and request_count % 10 == 0:
                progress = min((downloaded_count / max(total_minutes, 1)) * 100, 100)
                self._print_progress(progress, downloaded_count, total_minutes)

            # 다음 요청 시간 설정
            current_time = oldest_candle['timestamp'] - timedelta(seconds=1)

            # Rate Limit 여유 대기 (안전하게)
            time.sleep(0.11)  # 600 req/min = 0.1초/req + 여유

        # 최종 진행률 표시
        if show_progress:
            progress = min((downloaded_count / max(total_minutes, 1)) * 100, 100)
            self._print_progress(progress, downloaded_count, total_minutes)
            print()  # 줄바꿈

        logger.info(f"✅ 배치 다운로드 완료: {downloaded_count:,}개 다운로드")
        return downloaded_count

    def validate_data(self, candles: List[Dict]) -> bool:
        """
        캔들 데이터 무결성 검증

        검증 항목:
        - OHLC 관계 (High >= Open, Close, Low)
        - 볼륨 양수
        - 타임스탬프 순서

        Args:
            candles: 캔들 데이터 리스트

        Returns:
            bool: 유효하면 True
        """
        if not candles:
            return True

        try:
            for i, candle in enumerate(candles):
                # OHLC 관계 검증
                if not (
                    candle['high'] >= candle['open'] and
                    candle['high'] >= candle['close'] and
                    candle['high'] >= candle['low'] and
                    candle['low'] <= candle['open'] and
                    candle['low'] <= candle['close']
                ):
                    logger.warning(f"OHLC 관계 오류: index {i}, {candle}")
                    return False

                # 볼륨 양수 검증
                if candle['volume'] < 0:
                    logger.warning(f"음수 볼륨: index {i}, {candle}")
                    return False

                # 타임스탬프 순서 검증 (i > 0일 때)
                if i > 0:
                    prev_time = candles[i - 1]['timestamp']
                    curr_time = candle['timestamp']

                    if curr_time >= prev_time:
                        logger.warning(f"타임스탬프 순서 오류: index {i}")
                        return False

            return True

        except Exception as e:
            logger.error(f"데이터 검증 실패: {e}")
            return False

    def get_missing_ranges(
        self,
        market: str,
        interval: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Tuple[datetime, datetime]]:
        """
        데이터베이스에 없는 기간 찾기

        Args:
            market: 마켓 코드
            interval: 캔들 간격
            start_date: 확인할 시작 날짜
            end_date: 확인할 종료 날짜

        Returns:
            List[Tuple[datetime, datetime]]: 누락된 기간 리스트
        """
        # 데이터베이스의 날짜 범위 확인
        db_range = self.db.get_date_range(market, interval)

        if db_range is None:
            # 데이터가 전혀 없음
            return [(start_date, end_date)]

        db_start, db_end = db_range
        missing_ranges = []

        # 앞쪽 누락 확인
        if start_date < db_start:
            missing_ranges.append((start_date, db_start - timedelta(seconds=1)))

        # 뒤쪽 누락 확인
        if end_date > db_end:
            missing_ranges.append((db_end + timedelta(seconds=1), end_date))

        # TODO: 중간 누락 구간 찾기 (복잡하므로 추후 구현)

        return missing_ranges

    def _get_unit(self, interval: str) -> int:
        """
        간격을 Upbit API unit으로 변환

        Args:
            interval: 간격 문자열

        Returns:
            int or str: API unit 값
        """
        interval_info = self.SUPPORTED_INTERVALS.get(interval)
        if not interval_info:
            raise ValueError(f"지원하지 않는 간격: {interval}")

        return interval_info['unit']

    def _calculate_total_minutes(
        self,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> int:
        """
        기간 내 캔들 개수 계산

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            interval: 캔들 간격

        Returns:
            int: 캔들 개수
        """
        interval_info = self.SUPPORTED_INTERVALS.get(interval)
        if not interval_info:
            return 0

        total_seconds = (end_date - start_date).total_seconds()
        interval_minutes = interval_info['minutes']
        total_candles = int(total_seconds / 60 / interval_minutes)

        return total_candles

    def _estimate_time(self, total_requests: int) -> str:
        """
        예상 소요 시간 계산

        Args:
            total_requests: 총 요청 횟수

        Returns:
            str: 예상 시간 (예: "1분 30초", "5분")
        """
        # 600 req/min + 여유 = 약 500 req/min
        estimated_minutes = total_requests / 500

        if estimated_minutes < 1:
            seconds = int(estimated_minutes * 60)
            return f"{seconds}초"
        elif estimated_minutes < 60:
            minutes = int(estimated_minutes)
            seconds = int((estimated_minutes - minutes) * 60)
            if seconds > 0:
                return f"{minutes}분 {seconds}초"
            else:
                return f"{minutes}분"
        else:
            hours = int(estimated_minutes / 60)
            minutes = int(estimated_minutes % 60)
            return f"{hours}시간 {minutes}분"

    def _print_progress(
        self,
        progress: float,
        current: int,
        total: int
    ):
        """
        진행률 출력 (프로그레스 바)

        Args:
            progress: 진행률 (0~100)
            current: 현재 요청 수
            total: 총 요청 수
        """
        bar_length = 40
        filled_length = int(bar_length * progress / 100)

        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        print(f'\r[{bar}] {progress:.1f}% ({current:,} / {total:,})', end='', flush=True)

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Upbit 타임스탬프 문자열을 datetime으로 변환

        Args:
            timestamp_str: Upbit API timestamp (KST 시간)
                예: "2024-01-01T12:34:56"

        Returns:
            datetime: 변환된 naive datetime (KST 기준)
        """
        # ISO 8601 형식 파싱 (KST 시간이므로 timezone 정보 제거)
        # "2024-01-01T12:34:56" → naive datetime
        if 'T' in timestamp_str:
            return datetime.fromisoformat(timestamp_str.split('+')[0].replace('Z', ''))
        return datetime.fromisoformat(timestamp_str)


if __name__ == "__main__":
    """
    테스트 코드
    """
    import os
    from dotenv import load_dotenv

    print("=== UpbitDataLoader 테스트 ===\n")

    # 환경 변수 로드 (API 키)
    load_dotenv()
    access_key = os.getenv('UPBIT_ACCESS_KEY', '')
    secret_key = os.getenv('UPBIT_SECRET_KEY', '')

    if not access_key or not secret_key:
        print("⚠️ API 키가 설정되지 않았습니다")
        print("   .env 파일에 UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY 설정")
        print("   또는 테스트를 건너뜁니다\n")

        # API 키 없이도 공개 API 테스트 가능
        print("📝 API 키 없이 공개 데이터 테스트 진행\n")
        access_key = None
        secret_key = None

    # API 및 데이터베이스 초기화
    api = UpbitAPI(access_key, secret_key) if access_key else UpbitAPI('', '')
    db = CandleDatabase()

    # 데이터 로더 생성
    loader = UpbitDataLoader(api, db)

    # 1. 단일 요청 테스트
    print("1️⃣ 단일 요청 테스트 (최근 10개 1분봉)")
    candles = loader.download_candles(
        market='KRW-BTC',
        interval='1m',
        count=10
    )
    print(f"   다운로드된 캔들: {len(candles)}개")
    if candles:
        latest = candles[0]
        print(f"   최근 캔들: {latest['timestamp']} - Close: {latest['close']:,.0f}원")
    print()

    # 2. 데이터 검증 테스트
    print("2️⃣ 데이터 검증 테스트")
    is_valid = loader.validate_data(candles)
    print(f"   검증 결과: {'✅ 유효' if is_valid else '❌ 오류'}\n")

    # 3. 배치 다운로드 테스트 (소량)
    print("3️⃣ 배치 다운로드 테스트 (2024-01-01 00:00 ~ 00:10, 1분봉)")
    start = datetime(2024, 1, 1, 0, 0)
    end = datetime(2024, 1, 1, 0, 10)

    downloaded = loader.batch_download(
        market='KRW-BTC',
        interval='1m',
        start_date=start,
        end_date=end,
        show_progress=True
    )
    print(f"   다운로드 완료: {downloaded}개\n")

    # 4. 데이터베이스 조회
    print("4️⃣ 데이터베이스 조회")
    stored_candles = db.get_candles('KRW-BTC', '1m', start, end)
    print(f"   저장된 캔들: {len(stored_candles)}개")
    if not stored_candles.empty:
        print(stored_candles.head())
    print()

    # 5. 날짜 범위 확인
    print("5️⃣ 저장된 데이터 범위")
    date_range = db.get_date_range('KRW-BTC', '1m')
    if date_range:
        print(f"   시작: {date_range[0]}")
        print(f"   종료: {date_range[1]}")
    else:
        print("   데이터 없음")
    print()

    # 정리
    api.close()
    db.close()

    print("=== 테스트 완료 ===")
