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


class UpbitAPI:
    """
    업비트 REST API 클라이언트
    
    실거래 주문 및 계좌 관리를 위한 API 클라이언트
    """
    
    def __init__(self, access_key: str, secret_key: str):
        """
        API 클라이언트 초기화
        
        Args:
            access_key: 업비트 Access Key
            secret_key: 업비트 Secret Key
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = "https://api.upbit.com/v1"
        
        logger.info("✅ Upbit API 클라이언트 초기화 완료")
    
    def _generate_jwt_token(self, query: Optional[Dict] = None) -> str:
        """
        JWT 토큰 생성
        
        Args:
            query: API 요청 파라미터
            
        Returns:
            str: JWT 토큰
        """
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
            'timestamp': round(time.time() * 1000)
        }
        
        if query:
            query_string = unquote(urlencode(query, doseq=True)).encode("utf-8")
            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()
            
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'
        
        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return f'Bearer {jwt_token}'
    
    def _request(self, method: str, endpoint: str, query: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict:
        """
        API 요청 실행
        
        Args:
            method: HTTP 메서드 (GET, POST, DELETE)
            endpoint: API 엔드포인트
            query: Query 파라미터
            body: Request Body
            
        Returns:
            Dict: API 응답
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
        
        try:
            # 🔧 timeout 설정 (GET: 10초, POST: 30초)
            timeout = 30 if method == "POST" else 10
            
            if method == "GET":
                response = requests.get(url, headers=headers, params=query, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, params=query, timeout=timeout)
            else:
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ API 요청 시간 초과 ({timeout}초): {method} {endpoint}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ API 요청 실패: {e}")
            logger.error(f"응답 내용: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ 예상치 못한 오류: {e}")
            raise
    
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
        현재가 조회 (시세 조회 API - 인증 불필요)
        
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
        import requests
        
        url = "https://api.upbit.com/v1/ticker"
        params = {'markets': symbol}
        
        try:
            response = requests.get(url, params=params, timeout=10)  # 🔧 10초 timeout
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                return data[0]  # 첫 번째 결과 반환
            else:
                logger.warning(f"현재가 조회 결과 없음: {symbol}")
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
