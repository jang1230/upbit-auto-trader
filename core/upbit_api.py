"""
Upbit REST API Client
업비트 REST API 클라이언트

실거래 주문 실행:
- 시장가 매수/매도
- 잔고 조회
- 주문 상태 확인
- JWT 인증

Example:
    >>> api = UpbitAPI(access_key, secret_key)
    >>> balance = api.get_balance('KRW')
    >>> order = api.buy_market_order('KRW-BTC', 10000)
"""

import time
import uuid
import hashlib
import jwt
import requests
import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode, unquote

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Upbit API Rate Limit 관리 클래스

    Upbit REST API는 그룹별로 초당 최대 요청 수 제한 적용:
    - order: 8 requests/1s
    - order-cancel-all: 1 request/2s
    - default: 30 requests/1s
    - market, ticker, candles, orderbook: 10 requests/1s
    """

    def __init__(self):
        # group -> (capacity, window_sec)
        self.cfg = {
            "market": (10, 1),
            "ticker": (10, 1),
            "trades": (10, 1),
            "candles": (10, 1),
            "orderbook": (10, 1),
            "default": (30, 1),
            "order": (8, 1),
            "order-cancel-all": (1, 2),
        }
        # group -> (remaining, window_start_epoch)
        self.state = {}

    def _win_start(self, now_sec: int, win: int) -> int:
        """현재 window 시작 시각 계산"""
        return now_sec - (now_sec % win)

    def acquire(self, group: str):
        """
        API 요청 전 잔여 토큰 확인 및 차감

        토큰이 부족한 경우 다음 window까지 대기

        Args:
            group: Rate Limit 그룹 (order, ticker, default 등)
        """
        cap, win = self.cfg.get(group, (10, 1))
        now = time.time()
        now_sec = int(now)
        win_start = self._win_start(now_sec, win)

        remaining, cur_win_start = self.state.get(group, (cap, win_start))
        if cur_win_start != win_start:
            remaining, cur_win_start = cap, win_start

        if remaining <= 0:
            sleep_for = (cur_win_start + win) - now + 0.01
            logger.debug(f"RateLimiter: group={group} exhausted, sleeping {sleep_for:.3f}s")
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.time()
            now_sec = int(now)
            cur_win_start = self._win_start(now_sec, win)
            remaining = cap

        self.state[group] = (remaining - 1, cur_win_start)

    def update_from_header(self, header_value: str):
        """
        응답 헤더의 'Remaining-Req'로 잔여 요청 수 갱신

        Args:
            header_value: 'Remaining-Req' 헤더 값
                예: "group=default; min=1800; sec=29"
        """
        if not header_value:
            return

        g, sec = "default", None
        try:
            for p in [s.strip() for s in header_value.split(";")]:
                if p.startswith("group="):
                    g = p.split("=", 1)[1].strip()
                elif p.startswith("sec="):
                    sec = int(p.split("=", 1)[1].strip())
        except Exception:
            return

        if g in self.cfg and sec is not None:
            cap, win = self.cfg[g]
            now_sec = int(time.time())
            win_start = self._win_start(now_sec, win)
            logger.debug(f"RateLimiter: update group={g} remaining={sec}")
            self.state[g] = (min(cap, sec), win_start)

    def mark_exhausted(self, group: str):
        """
        429 Too Many Requests 응답 시 잔여 요청 수를 0으로 초기화

        Args:
            group: Rate Limit 그룹
        """
        cap, win = self.cfg.get(group, (10, 1))
        now_sec = int(time.time())
        win_start = self._win_start(now_sec, win)
        logger.warning(f"RateLimiter: mark exhausted for group={group}")
        self.state[group] = (0, win_start)


class UpbitAPI:
    """
    업비트 REST API 클라이언트
    
    실거래 주문 및 계좌 관리를 위한 API 클라이언트
    """
    
    def __init__(self, access_key: str, secret_key: str, limiter: Optional[RateLimiter] = None):
        """
        API 클라이언트 초기화

        Args:
            access_key: 업비트 Access Key
            secret_key: 업비트 Secret Key
            limiter: Rate Limiter (기본값: 새 인스턴스 생성)
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = "https://api.upbit.com/v1"
        self.limiter = limiter or RateLimiter()

        logger.info("✅ Upbit API 클라이언트 초기화 완료")
    
    def _generate_jwt_token(self, query: Optional[Dict] = None) -> str:
        """
        JWT 토큰 생성 (Upbit 공식 스펙)

        공식 Upbit JWT 스펙:
        - 기본 payload: access_key, nonce (timestamp 없음)
        - 파라미터 있을 때: query_hash, query_hash_alg 추가
        - algorithm: HS512

        Args:
            query: API 요청 파라미터

        Returns:
            str: JWT 토큰 (Bearer 포함)
        """
        # 🔧 공식 Upbit JWT 스펙에 맞춤 (timestamp 제거)
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4())
        }

        if query:
            query_string = unquote(urlencode(query, doseq=True)).encode("utf-8")
            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()

            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'

        # 🔧 공식 Upbit 스펙: HS256 사용 (공식 문서 명시)
        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return f'Bearer {jwt_token}'

    def _group_for(self, method: str, endpoint: str) -> str:
        """
        API endpoint에서 Rate Limit 그룹 결정

        Args:
            method: HTTP 메서드
            endpoint: API endpoint

        Returns:
            str: Rate Limit 그룹명
        """
        if endpoint.startswith("/market"):
            return "market"
        if endpoint.startswith("/ticker"):
            return "ticker"
        if endpoint.startswith("/trades"):
            return "trades"
        if endpoint.startswith("/candles"):
            return "candles"
        if endpoint.startswith("/orderbook"):
            return "orderbook"
        if endpoint.startswith("/orders/open") and method.upper() == "DELETE":
            return "order-cancel-all"
        if endpoint.startswith("/orders") and method.upper() == "POST":
            return "order"
        return "default"

    def _request(self, method: str, endpoint: str, query: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict:
        """
        API 요청 실행 (Rate Limit 및 에러 처리 포함)

        Args:
            method: HTTP 메서드 (GET, POST, DELETE)
            endpoint: API 엔드포인트
            query: Query 파라미터
            body: Request Body

        Returns:
            Dict: API 응답 또는 에러 정보
                정상: API 응답 데이터
                에러: {"status_code": int, "name": str, "message": str}
        """
        url = f"{self.base_url}{endpoint}"

        # JWT 토큰 생성
        if body:
            auth_token = self._generate_jwt_token(body)
        elif query:
            auth_token = self._generate_jwt_token(query)
        else:
            auth_token = self._generate_jwt_token()

        headers = {"Authorization": auth_token}

        # Rate Limit 그룹 결정 및 토큰 획득
        group = self._group_for(method, endpoint)
        self.limiter.acquire(group)

        try:
            # 🔧 timeout 설정 (GET: 10초, POST: 30초)
            timeout = 30 if method == "POST" else 10

            # HTTP 요청 실행
            start_time = time.time()

            if method == "GET":
                response = requests.get(url, headers=headers, params=query, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, params=query, timeout=timeout)
            else:
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")

            elapsed = time.time() - start_time

            # 429 Too Many Requests 처리
            if response.status_code == 429:
                logger.warning(f"Rate limit exceeded for group={group}")
                self.limiter.mark_exhausted(group)

            # 응답 헤더에서 Rate Limit 정보 갱신
            self.limiter.update_from_header(response.headers.get("Remaining-Req"))

            # HTTP 상태 코드 기반 정상/에러 구분
            if 200 <= response.status_code < 300:
                # 정상 응답
                logger.debug(f"HTTP {response.status_code} | {method} {endpoint} | {elapsed:.3f}s")
                try:
                    return response.json()
                except ValueError:
                    return response.text

            # 에러 응답 파싱
            logger.warning(f"HTTP {response.status_code} | {method} {endpoint} | {elapsed:.3f}s")
            try:
                ej = response.json()
                if isinstance(ej, dict) and "error" in ej:
                    e = ej["error"]
                    error_dict = {
                        "status_code": response.status_code,
                        "name": e.get("name"),
                        "message": e.get("message")
                    }
                    logger.error(f"API Error: {error_dict['name']} - {error_dict['message']}")
                    return error_dict
                return {
                    "status_code": response.status_code,
                    "name": None,
                    "message": ej
                }
            except ValueError:
                return {
                    "status_code": response.status_code,
                    "name": None,
                    "message": response.text
                }

        except requests.exceptions.Timeout:
            logger.error(f"❌ API 요청 시간 초과 ({timeout}초): {method} {endpoint}")
            return {
                "status_code": 0,
                "name": "Timeout",
                "message": f"API 요청 시간 초과 ({timeout}초)"
            }
        except Exception as e:
            logger.error(f"❌ 예상치 못한 오류: {e}")
            return {
                "status_code": 0,
                "name": "Exception",
                "message": str(e)
            }
    
    def get_accounts(self) -> List[Dict]:
        """
        계좌 정보 조회
        
        Returns:
            List[Dict]: 계좌 정보 리스트
                [
                    {
                        'currency': 'KRW',
                        'balance': '1000000.0',
                        'locked': '0.0',
                        'avg_buy_price': '0',
                        ...
                    },
                    ...
                ]
        """
        logger.info("📊 계좌 정보 조회 중...")
        accounts = self._request("GET", "/accounts")
        logger.info(f"✅ 계좌 정보 조회 완료: {len(accounts)}개 자산")
        return accounts
    
    def get_balance(self, currency: str = "KRW") -> float:
        """
        특정 화폐 잔고 조회
        
        Args:
            currency: 화폐 코드 (KRW, BTC, ETH, ...)
            
        Returns:
            float: 잔고 (사용 가능 금액)
        """
        accounts = self.get_accounts()
        
        for account in accounts:
            if account['currency'] == currency:
                balance = float(account['balance'])
                logger.info(f"💰 {currency} 잔고: {balance:,.2f}")
                return balance
        
        logger.warning(f"⚠️ {currency} 잔고를 찾을 수 없음")
        return 0.0
    
    def buy_market_order(self, symbol: str, price: float) -> Dict:
        """
        시장가 매수 주문
        
        Args:
            symbol: 마켓 코드 (예: 'KRW-BTC')
            price: 매수 금액 (KRW)
            
        Returns:
            Dict: 주문 정보
                {
                    'uuid': '주문 ID',
                    'side': 'bid',
                    'ord_type': 'price',
                    'price': '10000.0',
                    'market': 'KRW-BTC',
                    'created_at': '2024-01-01T00:00:00+09:00',
                    ...
                }
        """
        logger.info(f"🛒 시장가 매수 주문: {symbol}, {price:,.0f}원")
        
        body = {
            'market': symbol,
            'side': 'bid',
            'ord_type': 'price',
            'price': str(price)
        }
        
        order = self._request("POST", "/orders", body=body)
        
        logger.info(f"✅ 매수 주문 완료: {order['uuid']}")
        return order
    
    def sell_market_order(self, symbol: str, volume: float) -> Dict:
        """
        시장가 매도 주문
        
        Args:
            symbol: 마켓 코드 (예: 'KRW-BTC')
            volume: 매도 수량 (코인 수량)
            
        Returns:
            Dict: 주문 정보
        """
        logger.info(f"💵 시장가 매도 주문: {symbol}, {volume:.8f}개")
        
        body = {
            'market': symbol,
            'side': 'ask',
            'ord_type': 'market',
            'volume': str(volume)
        }
        
        order = self._request("POST", "/orders", body=body)
        
        logger.info(f"✅ 매도 주문 완료: {order['uuid']}")
        return order
    
    def get_order(self, order_id: str) -> Dict:
        """
        주문 상태 조회
        
        Args:
            order_id: 주문 UUID
            
        Returns:
            Dict: 주문 상태 정보
                {
                    'uuid': '주문 ID',
                    'state': 'done' or 'wait' or 'cancel',
                    'trades': [거래 내역],
                    ...
                }
        """
        query = {'uuid': order_id}
        order = self._request("GET", "/order", query=query)
        
        logger.info(f"📋 주문 상태: {order['state']} ({order_id})")
        return order
    
    def cancel_order(self, order_id: str) -> Dict:
        """
        주문 취소
        
        Args:
            order_id: 주문 UUID
            
        Returns:
            Dict: 취소된 주문 정보
        """
        logger.info(f"🚫 주문 취소 요청: {order_id}")
        
        query = {'uuid': order_id}
        order = self._request("DELETE", "/order", query=query)
        
        logger.info(f"✅ 주문 취소 완료: {order_id}")
        return order
    
    def get_order_chance(self, symbol: str) -> Dict:
        """
        주문 가능 정보 조회
        
        Args:
            symbol: 마켓 코드
            
        Returns:
            Dict: 주문 가능 정보
                {
                    'bid_fee': '0.0005',  # 매수 수수료율
                    'ask_fee': '0.0005',  # 매도 수수료율
                    'market': {...},      # 마켓 정보
                    'bid_account': {...}, # 매수 가능 계좌
                    'ask_account': {...}  # 매도 가능 계좌
                }
        """
        query = {'market': symbol}
        return self._request("GET", "/orders/chance", query=query)
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        현재가 조회 (시세 조회 API - 인증 불필요, Rate Limit 적용)

        Args:
            symbol: 마켓 코드 (예: 'KRW-BTC')

        Returns:
            Dict: 현재가 정보
                {
                    'market': 'KRW-BTC',
                    'trade_price': 95000000.0,  # 현재가
                    'signed_change_price': 500000.0,  # 전일 대비 가격
                    'signed_change_rate': 0.0053,  # 전일 대비 등락률
                    ...
                }
        """
        # Rate Limit 적용 (ticker: 10 requests/1s)
        self.limiter.acquire("ticker")

        url = "https://api.upbit.com/v1/ticker"
        params = {'markets': symbol}

        try:
            start_time = time.time()
            response = requests.get(url, params=params, timeout=10)
            elapsed = time.time() - start_time

            # 응답 헤더에서 Rate Limit 정보 갱신
            self.limiter.update_from_header(response.headers.get("Remaining-Req"))

            if 200 <= response.status_code < 300:
                logger.debug(f"HTTP {response.status_code} | GET /ticker | {elapsed:.3f}s")
                data = response.json()
                if data and len(data) > 0:
                    return data[0]  # 첫 번째 결과 반환
                else:
                    logger.warning(f"현재가 조회 결과 없음: {symbol}")
                    return {}
            else:
                logger.warning(f"HTTP {response.status_code} | GET /ticker | {elapsed:.3f}s")
                logger.error(f"현재가 조회 실패 ({symbol}): {response.text}")
                return {}

        except requests.exceptions.Timeout:
            logger.error(f"현재가 조회 시간 초과 ({symbol}): 10초")
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"현재가 조회 실패 ({symbol}): {e}")
            return {}


# 테스트 코드
if __name__ == "__main__":
    """테스트: API 연결 및 계좌 조회"""
    import os
    from dotenv import load_dotenv
    
    print("=== Upbit API 테스트 ===\n")
    
    # .env 파일에서 API 키 로드
    load_dotenv()
    access_key = os.getenv('UPBIT_ACCESS_KEY')
    secret_key = os.getenv('UPBIT_SECRET_KEY')
    
    if not access_key or not secret_key:
        print("❌ API 키가 설정되지 않았습니다.")
        print("   .env 파일에 UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY를 설정하세요.")
        exit(1)
    
    # API 클라이언트 초기화
    api = UpbitAPI(access_key, secret_key)
    
    # 1. 계좌 정보 조회
    print("1. 계좌 정보 조회")
    accounts = api.get_accounts()
    for account in accounts:
        currency = account['currency']
        balance = float(account['balance'])
        if balance > 0:
            print(f"   {currency}: {balance:,.8f}")
    print()
    
    # 2. KRW 잔고 조회
    print("2. KRW 잔고 조회")
    krw_balance = api.get_balance('KRW')
    print(f"   KRW: {krw_balance:,.0f}원")
    print()
    
    # 3. 주문 가능 정보 조회
    print("3. 주문 가능 정보 조회 (KRW-BTC)")
    order_chance = api.get_order_chance('KRW-BTC')
    print(f"   매수 수수료: {float(order_chance['bid_fee']) * 100:.2f}%")
    print(f"   매도 수수료: {float(order_chance['ask_fee']) * 100:.2f}%")
    print()
    
    print("✅ 테스트 완료")
    print("\n⚠️ 주의: 실제 주문 테스트는 Phase 3.5 페이퍼 트레이딩에서 진행합니다.")
