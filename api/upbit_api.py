"""
Upbit API 클라이언트
JWT 인증 및 REST API 통신 담당
"""
import time
import uuid
import hashlib
import jwt
import requests
from urllib.parse import urlencode
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Rate Limit 초과 에러"""
    pass


class UpbitAPIError(Exception):
    """Upbit API 에러"""
    pass


class UpbitAPI:
    """Upbit REST API 클라이언트"""
    
    BASE_URL = "https://api.upbit.com"
    
    # Rate Limits (요청/초 또는 요청/분)
    RATE_LIMITS = {
        'order': {'limit': 8, 'period': 1},          # 8 req/sec
        'account': {'limit': 30, 'period': 1},       # 30 req/sec
        'market': {'limit': 600, 'period': 60},      # 600 req/min
    }
    
    def __init__(self, access_key: str, secret_key: str):
        """
        Args:
            access_key: Upbit API Access Key
            secret_key: Upbit API Secret Key
        """
        self.access_key = access_key
        self.secret_key = secret_key
        
        # Rate Limit 추적
        self._request_times = {
            'order': [],
            'account': [],
            'market': []
        }
        
        # 세션 생성
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        logger.info("UpbitAPI 초기화 완료")
    
    def _generate_jwt_token(self, query_params: Optional[Dict] = None) -> str:
        """
        JWT 토큰 생성
        
        Args:
            query_params: 쿼리 파라미터 (주문 등에 필요)
            
        Returns:
            JWT 토큰 문자열
        """
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4())
        }
        
        if query_params:
            # 쿼리 파라미터가 있는 경우 query_hash 추가
            query_string = urlencode(query_params).encode()
            
            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()
            
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'
        
        # JWT 토큰 생성
        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS512')
        
        return f"Bearer {jwt_token}"
    
    def _check_rate_limit(self, category: str) -> None:
        """
        Rate Limit 체크
        
        Args:
            category: 'order', 'account', 'market'
            
        Raises:
            RateLimitError: Rate Limit 초과 시
        """
        now = time.time()
        limit_info = self.RATE_LIMITS[category]
        period = limit_info['period']
        limit = limit_info['limit']
        
        # 오래된 요청 제거
        self._request_times[category] = [
            t for t in self._request_times[category]
            if now - t < period
        ]
        
        # Rate Limit 체크
        if len(self._request_times[category]) >= limit:
            wait_time = period - (now - self._request_times[category][0])
            raise RateLimitError(
                f"Rate Limit 초과 ({category}): {wait_time:.2f}초 후 재시도"
            )
        
        # 요청 시간 기록
        self._request_times[category].append(now)
    
    def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        category: str,
        auth_required: bool = False,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        재시도 로직이 포함된 API 요청
        
        Args:
            method: HTTP 메서드 (GET, POST, DELETE)
            endpoint: API 엔드포인트
            category: Rate Limit 카테고리
            auth_required: 인증 필요 여부
            params: URL 파라미터
            json_data: JSON 바디
            max_retries: 최대 재시도 횟수
            
        Returns:
            API 응답 JSON
            
        Raises:
            UpbitAPIError: API 오류
            RateLimitError: Rate Limit 초과
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                # Rate Limit 체크
                self._check_rate_limit(category)
                
                # 헤더 설정
                headers = {}
                if auth_required:
                    query_params = params or json_data
                    headers['Authorization'] = self._generate_jwt_token(query_params)
                
                # 요청 실행
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                    timeout=10
                )
                
                # 에러 처리
                if response.status_code == 429:
                    raise RateLimitError("Rate Limit 초과")
                
                if response.status_code >= 400:
                    error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                    raise UpbitAPIError(
                        f"API 오류 ({response.status_code}): {error_msg}"
                    )
                
                return response.json()
                
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt == max_retries - 1:
                    raise UpbitAPIError(f"네트워크 오류: {e}")
                
                wait_time = 2 ** attempt  # 지수 백오프
                logger.warning(f"네트워크 오류, {wait_time}초 후 재시도 ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
                
            except RateLimitError:
                if attempt == max_retries - 1:
                    raise
                
                logger.warning("Rate Limit 초과, 60초 대기")
                time.sleep(60)
    
    # ========== 계좌 관련 API ==========
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """
        전체 계좌 조회
        
        Returns:
            계좌 정보 리스트
            [{
                'currency': 'KRW',
                'balance': '1000000.0',
                'locked': '0.0',
                'avg_buy_price': '0',
                ...
            }]
        """
        return self._request_with_retry(
            method='GET',
            endpoint='/v1/accounts',
            category='account',
            auth_required=True
        )
    
    def get_balance(self, currency: str = 'KRW') -> Dict[str, float]:
        """
        특정 화폐 잔고 조회
        
        Args:
            currency: 화폐 코드 (KRW, BTC 등)
            
        Returns:
            {'balance': 1000000.0, 'locked': 0.0}
        """
        accounts = self.get_accounts()
        
        for account in accounts:
            if account['currency'] == currency:
                return {
                    'balance': float(account['balance']),
                    'locked': float(account['locked'])
                }
        
        return {'balance': 0.0, 'locked': 0.0}
    
    # ========== 주문 관련 API ==========
    
    def place_order(
        self,
        market: str,
        side: str,
        ord_type: str,
        volume: Optional[float] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        주문하기
        
        Args:
            market: 마켓 코드 (예: KRW-BTC)
            side: 주문 종류 ('bid': 매수, 'ask': 매도)
            ord_type: 주문 타입
                - 'limit': 지정가 (volume, price 필수)
                - 'market': 시장가 매도 (volume 필수)
                - 'price': 시장가 매수 (price 필수)
            volume: 주문 수량
            price: 주문 가격
            
        Returns:
            주문 결과
            {
                'uuid': '...',
                'side': 'bid',
                'ord_type': 'limit',
                'price': '100.0',
                'state': 'wait',
                ...
            }
        """
        params = {
            'market': market,
            'side': side,
            'ord_type': ord_type
        }
        
        if volume is not None:
            params['volume'] = str(volume)
        
        if price is not None:
            params['price'] = str(price)
        
        return self._request_with_retry(
            method='POST',
            endpoint='/v1/orders',
            category='order',
            auth_required=True,
            json_data=params
        )
    
    def get_order(self, uuid: str) -> Dict[str, Any]:
        """
        개별 주문 조회
        
        Args:
            uuid: 주문 UUID
            
        Returns:
            주문 정보
        """
        params = {'uuid': uuid}
        
        return self._request_with_retry(
            method='GET',
            endpoint='/v1/order',
            category='account',
            auth_required=True,
            params=params
        )
    
    def get_orders(
        self,
        market: Optional[str] = None,
        state: str = 'wait',
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        주문 리스트 조회
        
        Args:
            market: 마켓 코드 (선택)
            state: 주문 상태 ('wait', 'done', 'cancel')
            limit: 조회 개수 (최대 100)
            
        Returns:
            주문 리스트
        """
        params = {
            'state': state,
            'limit': limit
        }
        
        if market:
            params['market'] = market
        
        return self._request_with_retry(
            method='GET',
            endpoint='/v1/orders',
            category='account',
            auth_required=True,
            params=params
        )
    
    def cancel_order(self, uuid: str) -> Dict[str, Any]:
        """
        주문 취소
        
        Args:
            uuid: 주문 UUID
            
        Returns:
            취소 결과
        """
        params = {'uuid': uuid}
        
        return self._request_with_retry(
            method='DELETE',
            endpoint='/v1/order',
            category='order',
            auth_required=True,
            params=params
        )
    
    # ========== 시세 정보 API ==========
    
    def get_candles(
        self,
        market: str,
        unit: int = 1,
        count: int = 200,
        to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        분봉 캔들 조회
        
        Args:
            market: 마켓 코드 (예: KRW-BTC)
            unit: 분 단위 (1, 3, 5, 10, 15, 30, 60, 240)
            count: 캔들 개수 (최대 200)
            to: 마지막 캔들 시각 (ISO 8601 format, 선택)
            
        Returns:
            캔들 데이터 리스트
            [{
                'market': 'KRW-BTC',
                'candle_date_time_kst': '2023-01-01T09:01:00',
                'opening_price': 19554000.0,
                'high_price': 19555000.0,
                'low_price': 19553000.0,
                'trade_price': 19554000.0,
                'candle_acc_trade_volume': 2.47652447,
                ...
            }]
        """
        params = {
            'market': market,
            'count': min(count, 200)  # 최대 200개
        }
        
        if to:
            params['to'] = to
        
        endpoint = f'/v1/candles/minutes/{unit}'
        
        return self._request_with_retry(
            method='GET',
            endpoint=endpoint,
            category='market',
            params=params
        )
    
    def get_current_price(self, markets: List[str]) -> List[Dict[str, Any]]:
        """
        현재가 정보 조회 (Ticker)
        
        Args:
            markets: 마켓 코드 리스트 (예: ['KRW-BTC', 'KRW-ETH'])
            
        Returns:
            현재가 정보 리스트
            [{
                'market': 'KRW-BTC',
                'trade_price': 19620000.0,
                'change': 'RISE',
                'change_rate': 0.0035795489,
                'acc_trade_volume_24h': 502.1547,
                ...
            }]
        """
        params = {
            'markets': ','.join(markets)
        }
        
        return self._request_with_retry(
            method='GET',
            endpoint='/v1/ticker',
            category='market',
            params=params
        )
    
    def get_market_all(self) -> List[Dict[str, str]]:
        """
        마켓 코드 조회
        
        Returns:
            마켓 정보 리스트
            [{
                'market': 'KRW-BTC',
                'korean_name': '비트코인',
                'english_name': 'Bitcoin'
            }]
        """
        return self._request_with_retry(
            method='GET',
            endpoint='/v1/market/all',
            category='market'
        )
    
    # ========== 유틸리티 메서드 ==========
    
    def test_connection(self) -> bool:
        """
        API 연결 테스트
        
        Returns:
            연결 성공 여부
        """
        try:
            self.get_accounts()
            logger.info("✅ API 연결 테스트 성공")
            return True
        except Exception as e:
            logger.error(f"❌ API 연결 테스트 실패: {e}")
            return False
    
    def close(self):
        """세션 종료"""
        self.session.close()
        logger.info("UpbitAPI 세션 종료")
