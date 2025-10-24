"""
백테스팅 데이터 로더
Backtest Data Loader

Upbit API를 통해 과거 캔들 데이터를 가져옵니다.

Example:
    >>> loader = DataLoader()
    >>> df = loader.load_ohlcv('KRW-BTC', days=365, interval='minute1')
    >>> print(df.head())
"""

import pandas as pd
import pyupbit
import time
from datetime import datetime, timedelta
from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """
    백테스팅용 과거 데이터 로더
    
    Upbit API를 사용하여 과거 캔들 데이터를 가져옵니다.
    """
    
    def __init__(self):
        """데이터 로더 초기화"""
        pass
    
    def load_ohlcv(
        self,
        symbol: str,
        days: int = 365,
        interval: Literal['minute1', 'minute3', 'minute5', 'minute10', 
                         'minute15', 'minute30', 'minute60', 'minute240',
                         'day', 'week', 'month'] = 'minute1'
    ) -> pd.DataFrame:
        """
        OHLCV 데이터 로드
        
        Args:
            symbol: 심볼 (예: 'KRW-BTC')
            days: 불러올 일수 (기본 365일)
            interval: 캔들 간격
        
        Returns:
            pd.DataFrame: OHLCV 데이터
                columns: ['open', 'high', 'low', 'close', 'volume']
                index: DatetimeIndex
        """
        logger.info(f"📊 {symbol} 데이터 로드 시작: {days}일, {interval}")
        
        # 시작/종료 시간 계산
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # 간격별 최대 캔들 수
        count_map = {
            'minute1': 200,
            'minute3': 200,
            'minute5': 200,
            'minute10': 200,
            'minute15': 200,
            'minute30': 200,
            'minute60': 200,
            'minute240': 200,
            'day': 200,
            'week': 200,
            'month': 200
        }
        
        max_count = count_map.get(interval, 200)
        
        # 필요한 총 캔들 수 계산
        if 'minute' in interval:
            minutes_per_candle = int(interval.replace('minute', ''))
            total_candles = (days * 24 * 60) // minutes_per_candle
        elif interval == 'day':
            total_candles = days
        elif interval == 'week':
            total_candles = days // 7
        elif interval == 'month':
            total_candles = days // 30
        else:
            total_candles = days
        
        # 데이터 수집
        all_data = []
        current_end = end_time
        
        iterations_needed = (total_candles // max_count) + 1
        logger.info(f"   예상 반복: {iterations_needed}회 (총 {total_candles}개 캔들)")
        
        for i in range(iterations_needed):
            try:
                # pyupbit를 사용하여 데이터 가져오기
                df = pyupbit.get_ohlcv(
                    symbol,
                    interval=interval,
                    to=current_end,
                    count=max_count
                )
                
                if df is None or len(df) == 0:
                    logger.warning(f"   데이터 없음 (반복 {i+1})")
                    break
                
                all_data.append(df)
                
                # 다음 반복을 위한 시간 조정
                current_end = df.index[0] - timedelta(seconds=1)
                
                # 시작 시간보다 이전이면 중단
                if current_end < start_time:
                    break
                
                # API Rate Limit 방지
                time.sleep(0.1)
                
                logger.debug(f"   반복 {i+1}/{iterations_needed}: {len(df)}개 캔들 로드")
                
            except Exception as e:
                logger.error(f"   ❌ 데이터 로드 실패 (반복 {i+1}): {e}")
                break
        
        if not all_data:
            logger.error(f"❌ {symbol} 데이터 로드 실패")
            return pd.DataFrame()
        
        # 모든 데이터 병합
        result = pd.concat(all_data)
        
        # 중복 제거 및 정렬
        result = result[~result.index.duplicated(keep='first')]
        result = result.sort_index()
        
        # 시작 시간 이후 데이터만 필터링
        result = result[result.index >= start_time]
        
        logger.info(f"✅ {symbol} 데이터 로드 완료: {len(result)}개 캔들 ({result.index[0]} ~ {result.index[-1]})")
        
        return result
    
    def load_multiple_symbols(
        self,
        symbols: list[str],
        days: int = 365,
        interval: str = 'minute1'
    ) -> dict[str, pd.DataFrame]:
        """
        여러 심볼의 데이터 한번에 로드
        
        Args:
            symbols: 심볼 리스트
            days: 불러올 일수
            interval: 캔들 간격
        
        Returns:
            dict: {symbol: DataFrame} 형태의 딕셔너리
        """
        logger.info(f"📊 다중 심볼 데이터 로드: {len(symbols)}개")
        
        result = {}
        for symbol in symbols:
            df = self.load_ohlcv(symbol, days=days, interval=interval)
            if not df.empty:
                result[symbol] = df
            
            # API Rate Limit 방지
            time.sleep(0.2)
        
        logger.info(f"✅ 다중 심볼 데이터 로드 완료: {len(result)}/{len(symbols)}개 성공")
        return result


if __name__ == "__main__":
    """테스트 코드"""
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 80)
    print("데이터 로더 테스트")
    print("=" * 80)
    
    loader = DataLoader()
    
    # 1. 단일 심볼 테스트
    print("\n1. BTC 1분봉 데이터 (최근 7일)")
    df = loader.load_ohlcv('KRW-BTC', days=7, interval='minute1')
    print(f"   데이터 크기: {len(df)} 캔들")
    print(f"   기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"\n   샘플 데이터:")
    print(df.head(3))
    
    # 2. 다중 심볼 테스트
    print("\n2. BTC, ETH, XRP 데이터 (최근 30일)")
    data_dict = loader.load_multiple_symbols(
        ['KRW-BTC', 'KRW-ETH', 'KRW-XRP'],
        days=30,
        interval='minute60'
    )
    
    for symbol, df in data_dict.items():
        print(f"   {symbol}: {len(df)} 캔들")
    
    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)
