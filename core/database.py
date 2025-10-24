"""
데이터베이스 관리 모듈
SQLite를 사용한 캔들 데이터 및 백테스팅 결과 저장

PyInstaller 호환성:
- sys.frozen 체크로 DB 경로 자동 설정
- 상대 경로 사용
"""

import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class CandleDatabase:
    """
    캔들 데이터 및 백테스팅 결과 저장 관리

    데이터베이스 구조:
    - candles: 캔들 데이터
    - backtest_results: 백테스팅 결과
    - backtest_trades: 백테스팅 거래 내역
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Args:
            db_path: 데이터베이스 파일 경로 (None이면 자동 설정)
        """
        # PyInstaller 환경 감지
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent

        # DB 경로 설정
        if db_path is None:
            data_dir = base_path / 'data'
            data_dir.mkdir(exist_ok=True)
            self.db_path = data_dir / 'candles.db'
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 데이터베이스 연결
        self.conn = None
        self._connect()

        # 테이블 생성
        self.create_tables()

        logger.info(f"📁 데이터베이스 연결: {self.db_path}")

    def _connect(self):
        """데이터베이스 연결"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능

    def create_tables(self):
        """테이블 생성 (없으면)"""
        cursor = self.conn.cursor()

        # 캔들 데이터 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL,
                interval TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                created_at INTEGER NOT NULL,

                UNIQUE(market, interval, timestamp)
            )
        ''')

        # 인덱스 생성 (쿼리 속도 향상)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_market_interval_timestamp
            ON candles(market, interval, timestamp)
        ''')

        # 백테스팅 결과 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                market TEXT NOT NULL,
                strategy TEXT NOT NULL,
                start_date INTEGER NOT NULL,
                end_date INTEGER NOT NULL,
                initial_capital REAL NOT NULL,
                final_capital REAL NOT NULL,
                total_return REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                win_rate REAL NOT NULL,
                sharpe_ratio REAL,
                total_trades INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        ''')

        # 백테스팅 거래 내역 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                fee REAL NOT NULL,
                balance REAL NOT NULL,
                position REAL NOT NULL,

                FOREIGN KEY(run_id) REFERENCES backtest_results(run_id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_run_id
            ON backtest_trades(run_id)
        ''')

        self.conn.commit()

    def insert_candles(
        self,
        candles: List[Dict],
        market: str,
        interval: str
    ) -> int:
        """
        캔들 데이터 삽입 (중복 무시)

        Args:
            candles: 캔들 데이터 리스트
                [{
                    'timestamp': datetime 또는 int (ms),
                    'open': float,
                    'high': float,
                    'low': float,
                    'close': float,
                    'volume': float
                }]
            market: 마켓 코드 (예: 'KRW-BTC')
            interval: 간격 (예: '1m', '5m', '1h', '1d')

        Returns:
            int: 삽입된 개수
        """
        if not candles:
            return 0

        cursor = self.conn.cursor()
        created_at = int(datetime.now().timestamp() * 1000)
        inserted_count = 0

        for candle in candles:
            try:
                # Timestamp 변환
                if isinstance(candle['timestamp'], datetime):
                    timestamp = int(candle['timestamp'].timestamp() * 1000)
                else:
                    timestamp = candle['timestamp']

                cursor.execute('''
                    INSERT OR IGNORE INTO candles
                    (market, interval, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    market,
                    interval,
                    timestamp,
                    float(candle['open']),
                    float(candle['high']),
                    float(candle['low']),
                    float(candle['close']),
                    float(candle['volume']),
                    created_at
                ))

                if cursor.rowcount > 0:
                    inserted_count += 1

            except Exception as e:
                logger.error(f"캔들 삽입 실패: {e}, candle: {candle}")
                continue

        self.conn.commit()
        logger.info(f"✅ 캔들 삽입 완료: {inserted_count}개 (시장: {market}, 간격: {interval})")
        return inserted_count

    def get_candles(
        self,
        market: str,
        interval: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        캔들 데이터 조회

        Args:
            market: 마켓 코드
            interval: 간격
            start_date: 시작 날짜 (포함)
            end_date: 종료 날짜 (포함)
            limit: 최대 개수

        Returns:
            pd.DataFrame: 캔들 데이터
                Columns: timestamp, open, high, low, close, volume
                Index: timestamp (datetime)
        """
        query = '''
            SELECT timestamp, open, high, low, close, volume
            FROM candles
            WHERE market = ? AND interval = ?
        '''
        params = [market, interval]

        if start_date:
            query += ' AND timestamp >= ?'
            params.append(int(start_date.timestamp() * 1000))

        if end_date:
            query += ' AND timestamp <= ?'
            params.append(int(end_date.timestamp() * 1000))

        query += ' ORDER BY timestamp ASC'

        if limit:
            query += f' LIMIT {limit}'

        # 데이터 조회
        df = pd.read_sql_query(query, self.conn, params=params)

        if df.empty:
            return df

        # Timestamp를 datetime으로 변환
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        return df

    def get_date_range(
        self,
        market: str,
        interval: str
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        저장된 데이터의 시작/종료 날짜

        Args:
            market: 마켓 코드
            interval: 간격

        Returns:
            (start_date, end_date) 또는 None
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT MIN(timestamp), MAX(timestamp)
            FROM candles
            WHERE market = ? AND interval = ?
        ''', (market, interval))

        result = cursor.fetchone()

        if result and result[0] and result[1]:
            start_ts = result[0]
            end_ts = result[1]

            start_date = datetime.fromtimestamp(start_ts / 1000)
            end_date = datetime.fromtimestamp(end_ts / 1000)

            return (start_date, end_date)

        return None

    def count_candles(
        self,
        market: str,
        interval: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        캔들 개수 조회

        Args:
            market: 마켓 코드
            interval: 간격
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            int: 캔들 개수
        """
        query = '''
            SELECT COUNT(*)
            FROM candles
            WHERE market = ? AND interval = ?
        '''
        params = [market, interval]

        if start_date:
            query += ' AND timestamp >= ?'
            params.append(int(start_date.timestamp() * 1000))

        if end_date:
            query += ' AND timestamp <= ?'
            params.append(int(end_date.timestamp() * 1000))

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()

        return result[0] if result else 0

    def delete_candles(
        self,
        market: str,
        interval: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        캔들 데이터 삭제

        Args:
            market: 마켓 코드
            interval: 간격
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            int: 삭제된 개수
        """
        query = 'DELETE FROM candles WHERE market = ? AND interval = ?'
        params = [market, interval]

        if start_date:
            query += ' AND timestamp >= ?'
            params.append(int(start_date.timestamp() * 1000))

        if end_date:
            query += ' AND timestamp <= ?'
            params.append(int(end_date.timestamp() * 1000))

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        deleted_count = cursor.rowcount

        self.conn.commit()
        logger.info(f"🗑️ 캔들 삭제 완료: {deleted_count}개")

        return deleted_count

    def save_backtest_result(
        self,
        run_id: str,
        market: str,
        strategy: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
        final_capital: float,
        total_return: float,
        max_drawdown: float,
        win_rate: float,
        sharpe_ratio: Optional[float],
        total_trades: int
    ):
        """
        백테스팅 결과 저장

        Args:
            run_id: 실행 ID (UUID)
            market: 마켓 코드
            strategy: 전략 이름
            ... (기타 성과 지표)
        """
        cursor = self.conn.cursor()
        created_at = int(datetime.now().timestamp() * 1000)

        cursor.execute('''
            INSERT INTO backtest_results
            (run_id, market, strategy, start_date, end_date,
             initial_capital, final_capital, total_return,
             max_drawdown, win_rate, sharpe_ratio, total_trades, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            run_id,
            market,
            strategy,
            int(start_date.timestamp() * 1000),
            int(end_date.timestamp() * 1000),
            initial_capital,
            final_capital,
            total_return,
            max_drawdown,
            win_rate,
            sharpe_ratio,
            total_trades,
            created_at
        ))

        self.conn.commit()
        logger.info(f"💾 백테스팅 결과 저장 완료: {run_id}")

    def save_backtest_trades(
        self,
        run_id: str,
        trades: List[Dict]
    ):
        """
        백테스팅 거래 내역 저장

        Args:
            run_id: 실행 ID
            trades: 거래 내역 리스트
                [{
                    'timestamp': datetime,
                    'side': 'buy' or 'sell',
                    'price': float,
                    'amount': float,
                    'fee': float,
                    'balance': float,
                    'position': float
                }]
        """
        if not trades:
            return

        cursor = self.conn.cursor()

        for trade in trades:
            timestamp = int(trade['timestamp'].timestamp() * 1000) \
                if isinstance(trade['timestamp'], datetime) \
                else trade['timestamp']

            cursor.execute('''
                INSERT INTO backtest_trades
                (run_id, timestamp, side, price, amount, fee, balance, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run_id,
                timestamp,
                trade['side'],
                trade['price'],
                trade['amount'],
                trade['fee'],
                trade['balance'],
                trade['position']
            ))

        self.conn.commit()
        logger.info(f"💾 거래 내역 저장 완료: {len(trades)}개 (run_id: {run_id})")

    def get_backtest_results(
        self,
        market: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 10
    ) -> pd.DataFrame:
        """
        백테스팅 결과 조회

        Args:
            market: 마켓 코드 (필터)
            strategy: 전략 이름 (필터)
            limit: 최대 개수

        Returns:
            pd.DataFrame: 백테스팅 결과
        """
        query = 'SELECT * FROM backtest_results WHERE 1=1'
        params = []

        if market:
            query += ' AND market = ?'
            params.append(market)

        if strategy:
            query += ' AND strategy = ?'
            params.append(strategy)

        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        df = pd.read_sql_query(query, self.conn, params=params)

        # Timestamp 변환
        if not df.empty:
            df['start_date'] = pd.to_datetime(df['start_date'], unit='ms')
            df['end_date'] = pd.to_datetime(df['end_date'], unit='ms')
            df['created_at'] = pd.to_datetime(df['created_at'], unit='ms')

        return df

    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()
            logger.info("📁 데이터베이스 연결 종료")

    def __enter__(self):
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.close()


if __name__ == "__main__":
    """
    테스트 코드
    """
    print("=== CandleDatabase 테스트 ===\n")

    # 데이터베이스 생성
    with CandleDatabase() as db:
        print(f"📁 데이터베이스 경로: {db.db_path}\n")

        # 1. 테스트 캔들 데이터 삽입
        print("1️⃣ 캔들 데이터 삽입 테스트")
        test_candles = [
            {
                'timestamp': datetime(2024, 1, 1, 0, 0),
                'open': 50000000,
                'high': 51000000,
                'low': 49000000,
                'close': 50500000,
                'volume': 100.5
            },
            {
                'timestamp': datetime(2024, 1, 1, 0, 1),
                'open': 50500000,
                'high': 52000000,
                'low': 50000000,
                'close': 51000000,
                'volume': 120.3
            },
            {
                'timestamp': datetime(2024, 1, 1, 0, 2),
                'open': 51000000,
                'high': 51500000,
                'low': 50500000,
                'close': 51200000,
                'volume': 95.7
            }
        ]

        inserted = db.insert_candles(test_candles, 'KRW-BTC', '1m')
        print(f"   삽입된 캔들: {inserted}개\n")

        # 2. 캔들 개수 확인
        print("2️⃣ 캔들 개수 확인")
        count = db.count_candles('KRW-BTC', '1m')
        print(f"   총 캔들 수: {count}개\n")

        # 3. 날짜 범위 확인
        print("3️⃣ 날짜 범위 확인")
        date_range = db.get_date_range('KRW-BTC', '1m')
        if date_range:
            print(f"   시작: {date_range[0]}")
            print(f"   종료: {date_range[1]}\n")

        # 4. 캔들 데이터 조회
        print("4️⃣ 캔들 데이터 조회")
        candles_df = db.get_candles('KRW-BTC', '1m')
        print(f"   조회된 캔들: {len(candles_df)}개")
        print(candles_df)
        print()

        # 5. 백테스팅 결과 저장 (테스트)
        print("5️⃣ 백테스팅 결과 저장 테스트")
        import uuid
        run_id = str(uuid.uuid4())

        db.save_backtest_result(
            run_id=run_id,
            market='KRW-BTC',
            strategy='test_strategy',
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=1000000,
            final_capital=1450000,
            total_return=45.0,
            max_drawdown=-18.3,
            win_rate=65.5,
            sharpe_ratio=1.85,
            total_trades=120
        )
        print(f"   실행 ID: {run_id}\n")

        # 6. 백테스팅 결과 조회
        print("6️⃣ 백테스팅 결과 조회")
        results_df = db.get_backtest_results(limit=5)
        print(f"   조회된 결과: {len(results_df)}개")
        if not results_df.empty:
            print(results_df[['run_id', 'market', 'strategy', 'total_return', 'sharpe_ratio']])
        print()

    print("=== 테스트 완료 ===")
