# Upbit API 상세 분석 문서

## 1. 기본 정보

- **Base URL**: `https://api.upbit.com`
- **인증 방식**: JWT (JSON Web Token) with HMAC-SHA512
- **API 문서**: https://docs.upbit.com/kr/llms.txt

## 2. 인증 (Authentication)

### JWT 토큰 생성 방법
```python
import jwt
import uuid
import hashlib
from urllib.parse import urlencode

# 쿼리 파라미터가 있는 경우
query = {
    'market': 'KRW-BTC',
    'side': 'bid',
    'volume': '0.01',
    'price': '100000',
    'ord_type': 'limit'
}
query_string = urlencode(query).encode()

# JWT payload 생성
payload = {
    'access_key': access_key,
    'nonce': str(uuid.uuid4()),
    'query_hash': hashlib.sha512(query_string).hexdigest(),
    'query_hash_alg': 'SHA512'
}

# JWT 토큰 생성
jwt_token = jwt.encode(payload, secret_key, algorithm="HS512")

# 헤더에 추가
headers = {
    'Authorization': f'Bearer {jwt_token}'
}
```

### 쿼리 파라미터가 없는 경우
```python
payload = {
    'access_key': access_key,
    'nonce': str(uuid.uuid4())
}
jwt_token = jwt.encode(payload, secret_key, algorithm="HS512")
```

## 3. 계좌 관련 API

### 3.1 전체 계좌 조회
- **Endpoint**: `GET /v1/accounts`
- **Rate Limit**: 30 req/sec
- **인증**: 필요
- **Response**:
```json
[
  {
    "currency": "KRW",
    "balance": "1000000.0",
    "locked": "0.0",
    "avg_buy_price": "0",
    "avg_buy_price_modified": true,
    "unit_currency": "KRW"
  },
  {
    "currency": "BTC",
    "balance": "0.5",
    "locked": "0.0",
    "avg_buy_price": "50000000",
    "avg_buy_price_modified": false,
    "unit_currency": "KRW"
  }
]
```

## 4. 주문 관련 API

### 4.1 주문하기
- **Endpoint**: `POST /v1/orders`
- **Rate Limit**: 8 req/sec
- **인증**: 필요

**Parameters**:
- `market` (required): 마켓 코드 (예: KRW-BTC)
- `side` (required): 주문 종류
  - `bid`: 매수
  - `ask`: 매도
- `ord_type` (required): 주문 타입
  - `limit`: 지정가 주문
  - `market`: 시장가 주문 (매도)
  - `price`: 시장가 주문 (매수)
  - `best`: 최유리 주문
- `volume`: 주문량 (지정가, 시장가 매도 시 필수)
- `price`: 주문 가격 (지정가, 시장가 매수 시 필수)
- `time_in_force` (optional): 주문 유효 조건
  - `ioc`: Immediate or Cancel
  - `fok`: Fill or Kill
  - `post_only`: Post Only
- `smp_type` (optional): 자기매매방지 타입
  - `cn`: Cancel newest
  - `co`: Cancel oldest
  - `cb`: Cancel both
  - `dd`: Decrement and cancel

**Response**:
```json
{
  "uuid": "cdd92199-2897-4e14-9448-f923320408ad",
  "side": "bid",
  "ord_type": "limit",
  "price": "100.0",
  "state": "wait",
  "market": "KRW-BTC",
  "created_at": "2018-04-10T15:42:23+09:00",
  "volume": "0.01",
  "remaining_volume": "0.01",
  "reserved_fee": "0.0015",
  "remaining_fee": "0.0015",
  "paid_fee": "0",
  "locked": "1.0015",
  "executed_volume": "0",
  "trades_count": 0
}
```

### 4.2 개별 주문 조회
- **Endpoint**: `GET /v1/order`
- **인증**: 필요
- **Parameters**: 
  - `uuid` 또는 `identifier` 중 하나 필수

### 4.3 주문 리스트 조회
- **Endpoint**: `GET /v1/orders`
- **인증**: 필요
- **Types**:
  - **체결 대기 주문 조회**: 현재 진행 중인 주문
  - **종료 주문 조회**: 완료/취소된 주문
  
**Parameters**:
- `market`: 마켓 코드 (선택)
- `state`: 주문 상태 (wait, watch, done, cancel)
- `page`: 페이지 번호
- `limit`: 조회 개수 (default: 100, max: 100)
- `order_by`: 정렬 방식 (asc, desc)

### 4.4 주문 취소
- **Endpoint**: `DELETE /v1/order`
- **인증**: 필요
- **Parameters**:
  - `uuid` 또는 `identifier` 중 하나 필수

**일괄 취소 옵션**:
1. **id로 주문 목록 취소**: 최대 20개
2. **주문 일괄 취소**: 최대 300개
3. **취소 후 재주문**: 기존 주문 취소 후 새 주문 생성

## 5. 시세 정보 API

### 5.1 캔들 조회
- **Endpoint**: `GET /v1/candles/minutes/{unit}`
- **Rate Limit**: 600 req/min (분/일/주/월 캔들 통합)
- **인증**: 불필요

**Unit Options**: 1, 3, 5, 10, 15, 30, 60, 240 (분)

**Parameters**:
- `market` (required): 마켓 코드 (예: KRW-BTC)
- `to` (optional): 마지막 캔들 시각 (exclusive, ISO 8601 format)
- `count` (optional): 캔들 개수 (default: 1, max: 200)

**Response**:
```json
[
  {
    "market": "KRW-BTC",
    "candle_date_time_utc": "2023-01-01T00:01:00",
    "candle_date_time_kst": "2023-01-01T09:01:00",
    "opening_price": 19554000.0,
    "high_price": 19555000.0,
    "low_price": 19553000.0,
    "trade_price": 19554000.0,
    "timestamp": 1672531260000,
    "candle_acc_trade_price": 48388845.0,
    "candle_acc_trade_volume": 2.47652447,
    "unit": 1
  }
]
```

**추가 캔들 타입**:
- **일 캔들**: `GET /v1/candles/days`
- **주 캔들**: `GET /v1/candles/weeks`
- **월 캔들**: `GET /v1/candles/months`

### 5.2 현재가 정보 (Ticker)
- **Endpoint**: `GET /v1/ticker`
- **Rate Limit**: 600 req/min
- **인증**: 불필요

**Parameters**:
- `markets` (required): 마켓 코드 리스트 (comma-separated, 예: KRW-BTC,KRW-ETH)

**Response**:
```json
[
  {
    "market": "KRW-BTC",
    "trade_date": "20230101",
    "trade_time": "091530",
    "trade_date_kst": "20230101",
    "trade_time_kst": "181530",
    "trade_timestamp": 1672561530000,
    "opening_price": 19554000.0,
    "high_price": 19640000.0,
    "low_price": 19500000.0,
    "trade_price": 19620000.0,
    "prev_closing_price": 19550000.0,
    "change": "RISE",
    "change_price": 70000.0,
    "change_rate": 0.0035795489,
    "signed_change_price": 70000.0,
    "signed_change_rate": 0.0035795489,
    "trade_volume": 0.02,
    "acc_trade_price": 385488450.0,
    "acc_trade_price_24h": 9852648750.0,
    "acc_trade_volume": 19.65847,
    "acc_trade_volume_24h": 502.1547,
    "highest_52_week_price": 50000000.0,
    "highest_52_week_date": "2022-04-01",
    "lowest_52_week_price": 15000000.0,
    "lowest_52_week_date": "2022-12-01",
    "timestamp": 1672561530123
  }
]
```

### 5.3 마켓 코드 조회
- **Endpoint**: `GET /v1/market/all`
- **Rate Limit**: N/A (public endpoint)
- **인증**: 불필요

**Response**:
```json
[
  {
    "market": "KRW-BTC",
    "korean_name": "비트코인",
    "english_name": "Bitcoin"
  },
  {
    "market": "KRW-ETH",
    "korean_name": "이더리움",
    "english_name": "Ethereum"
  }
]
```

## 6. Rate Limits 요약

| API 카테고리 | Rate Limit | 비고 |
|------------|-----------|------|
| 계좌 조회 | 30 req/sec | |
| 주문하기 | 8 req/sec | 주의 필요 |
| 주문 조회/취소 | 30 req/sec | |
| 캔들 조회 (전체) | 600 req/min | 분/일/주/월 통합 |
| 현재가 조회 | 600 req/min | |
| 마켓 조드 | 제한 없음 | Public API |

**Rate Limit 처리 권장 사항**:
- 주문 API는 8 req/sec로 매우 제한적이므로 주의
- 캔들 데이터는 캐싱 필수 (600 req/min을 여러 종목이 공유)
- WebSocket 사용 고려 (실시간 데이터용)

## 7. 에러 처리

### 일반적인 에러 코드
- `400`: Bad Request (잘못된 파라미터)
- `401`: Unauthorized (인증 실패)
- `403`: Forbidden (권한 없음)
- `404`: Not Found (존재하지 않는 리소스)
- `429`: Too Many Requests (Rate Limit 초과)
- `500`: Internal Server Error (서버 오류)

### Rate Limit 초과 시 처리
```python
import time
from requests.exceptions import HTTPError

def api_call_with_retry(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** i  # exponential backoff
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

## 8. Binance vs Upbit 주요 차이점

| 항목 | Binance Futures | Upbit Spot |
|-----|----------------|-----------|
| 마켓 형식 | BTCUSDT | KRW-BTC |
| 레버리지 | 지원 (최대 125x) | 미지원 |
| 주문 타입 | LIMIT, MARKET, STOP 등 | limit, market, price, best |
| 포지션 | 롱/숏 | 매수/매도만 |
| 수수료 | Maker/Taker | 단일 수수료 |
| API 인증 | HMAC SHA256 | JWT with HMAC SHA512 |
| Rate Limit | 가중치 기반 | 고정 req/sec 또는 req/min |

## 9. 자동매매 구현 시 주의사항

1. **Rate Limit 관리**
   - 주문 API 8 req/sec 제한 엄격
   - 캔들 API 600 req/min 공유 제한
   - 에러 429 처리 필수

2. **인증 보안**
   - API 키는 환경 변수 또는 암호화된 설정 파일에 저장
   - JWT nonce는 매번 새로운 UUID 사용
   - query_hash는 정확한 순서로 생성

3. **주문 실행**
   - 시장가 매수는 `ord_type="price"`로 금액 지정
   - 시장가 매도는 `ord_type="market"`으로 수량 지정
   - 지정가 주문은 `ord_type="limit"`으로 가격과 수량 모두 지정

4. **데이터 캐싱**
   - 마켓 코드 리스트는 세션당 1회만 조회
   - 캔들 데이터는 로컬 캐싱 후 최신 데이터만 갱신
   - 계좌 잔고는 필요 시에만 조회

5. **에러 복구**
   - 네트워크 오류 시 재시도 로직
   - 주문 실패 시 상태 확인 후 처리
   - 일일 손실 한도 설정 권장

## 10. 추천 구현 순서

1. **Phase 1**: 기본 인증 및 계좌 조회
2. **Phase 2**: 시세 데이터 조회 (캔들, 현재가)
3. **Phase 3**: 간단한 주문 실행 (시장가)
4. **Phase 4**: 지정가 주문 및 주문 관리
5. **Phase 5**: DCA 로직 통합
6. **Phase 6**: 기술적 지표 계산 및 자동 진입
7. **Phase 7**: UI 통합 및 실시간 모니터링
