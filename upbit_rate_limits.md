# 업비트 Open API 요청 수 제한(Rate Limits) 정책

## 1. 요청 수 제한 정책 개요

업비트 Open API는 안정적인 서비스 운영을 위해 초 단위의 요청 수 제한(Rate Limit) 정책을 적용합니다.

### 1.1 기본 정책 안내

- **시간 단위**: 모든 요청 수 제한은 초(Second) 단위로 적용됩니다.

- **Rate Limit 그룹**: API가 속한 Rate Limit 그룹별로 초당 최대 허용 요청 수가 정의됩니다. 같은 그룹 API 간 요청 수가 함께 집계됩니다. 각 API Reference 하단 Rate Limit 영역에서 해당 API의 Rate Limit 그룹과 정책을 확인할 수 있습니다.

- **동적 제한**: 안정적인 서비스 제공을 위해 서비스 상황에 따른 추가 초당 최대 허용 요청 수 제한이 발생할 수 있습니다. Rate Limit 그룹별 초당 최대 허용 요청 수는 서비스 정책에 따라 공지 후 변경될 수 있습니다.

- **Origin 헤더 포함 요청 특별 정책**: Origin 헤더를 포함한 요청의 경우 별도의 요청 수 제한 정책을 적용합니다. 시세 조회(Quotation) REST API와 WebSocket 요청에 대해 모두 **10초당 1회의 요청만 허용**합니다. 자세한 사항은 [관련 공지](https://docs.upbit.com/kr/changelog/origin_rate_limit)를 확인하시기 바랍니다.

### 1.2 기준 초과 요청에 대한 제한

- **429 Too Many Requests 에러**: 초당 최대 허용 요청 수를 초과한 요청에 대해 응답의 HTTP 상태 코드가 429 Too Many Requests 에러로 반환됩니다.

- **지속적인 초과 요청 차단**: 429 에러 응답에도 지속적으로 요청을 전송하는 경우, 시스템에 의해 동일 IP 또는 계정 단위 요청이 일시적으로 차단됩니다.

- **418 HTTP 상태 코드**: IP 및 계정 차단 시 418 HTTP 상태 코드와 함께 차단 시간 정보가 함께 반환되오니 안내된 시간 이후 재시도하시기 바랍니다.

- **점진적 차단 시간 증가**: 정책을 위반한 과도한 요청이 반복되는 경우 IP 차단 시간은 점진적으로 증가할 수 있습니다.

## 2. 제한 단위

| 기능 분류 | 측정 단위 | 설명 |
|---|---|---|
| 시세 조회 REST API (Quotation) | IP 단위 | 동일한 IP 주소에서 발생한 요청간 초당 잔여 요청 횟수가 공유/차감되며, IP 단위로 제한이 적용됩니다. |
| 거래 및 자산 관리 REST API (Exchange) | 계정 단위 | 동일한 계정으로 발급된 여러 API Key를 사용하는 경우에도, 해당 계정 단위로 초당 잔여 요청 횟수가 공유/차감됩니다. |
| WebSocket 연결 요청 및 데이터 요청 | 인증 헤더를 포함한 경우 계정 단위 / 미포함한 경우 IP 단위 | 시세(Quotation) 정보만 구독하기 위해 인증 없이 요청하는 경우 IP 단위, 내 주문 및 체결(My Order), 내 자산(My Asset) 정보 구독을 위해 인증 정보를 포함하여 요청하는 경우 계정 단위로 측정됩니다. |

## 3. Rate Limit 그룹 정책

| Rate Limit 그룹 | 정책 | 대상 API |
|---|---|---|
| **Quotation/market** | 초당 최대 10회 | • 마켓 코드 조회 |
| **Quotation/candle** | 초당 최대 10회 | • 분(Minute) 캔들<br>• 일(Day) 캔들<br>• 주(Week) 캔들<br>• 월(Month) 캔들 |
| **Quotation/trade** | 초당 최대 10회 | • 최근 체결 내역 |
| **Quotation/ticker** | 초당 최대 10회 | • 현재가 정보 |
| **Quotation/orderbook** | 초당 최대 10회 | • 호가 정보 조회 |
| **Exchange/default** | 초당 최대 30회 | • 전체 계좌 조회<br>• 주문 가능 정보<br>• 개별 주문 조회<br>• 주문 리스트 조회<br>• 주문 취소 접수<br>• 출금 리스트 조회<br>• 개별 출금 조회<br>• 출금 가능 정보<br>• 원화 출금하기<br>• 코인 출금하기<br>• 입금 리스트 조회<br>• 개별 입금 조회 **(동일 입금 건에 대해 10분당 최대 1회 요청 허용)**<br>• 입금 주소 생성 요청<br>• 전체 입금 주소 조회<br>• 개별 입금 주소 조회<br>• 코인 입금하기<br>• 요청 당시 종목 시세 조회<br>• API 키 리스트 조회 |
| **Exchange/order** | 초당 최대 8회 | • 주문하기 |
| **Exchange/order-cancel-all** | 2초당 최대 1회 | • 전체 주문 취소 (신규) |
| **websocket-connect** | 초당 최대 5회 | • WebSocket 연결 요청 |
| **websocket-message** | 초당 최대 5회, 분당 100회 | • WebSocket 데이터 수신 |

## 4. 잔여 요청 수 확인 방법

REST API 응답의 `Remaining-Req` 헤더로 잔여 요청 수 정보가 반환됩니다.

### 4.1 헤더 형식 예시
```
group=default; min=1800; sec=29
```

### 4.2 필드 설명

- **`group`**: 해당 요청이 포함된 Rate Limit Group입니다.

- **`min`**: 현재는 Deprecated된 분 단위 요청 제한 정보 필드입니다. 고정 값으로 반환되므로 참조 대상에서 제외하시기 바랍니다.

- **`sec`**: 현재 잔여 요청 수입니다. 값이 0으로 반환되는 경우 잔여 요청 수가 없는 상황이므로 일정 시간 이후 요청해야 합니다.

---

## 주요 유의사항 요약

1. 모든 제한은 초 단위로 적용됩니다.
2. 같은 Rate Limit 그룹의 API는 요청 수가 함께 집계됩니다.
3. Origin 헤더를 포함하면 10초당 1회만 허용됩니다.
4. 429 에러 후 지속 요청 시 418 코드로 일시 차단됩니다.
5. 시세 조회는 IP 단위, 거래/자산 관리는 계정 단위로 제한됩니다.
6. `Remaining-Req` 헤더의 `sec` 값으로 잔여 요청 수를 확인할 수 있습니다.
7. 개별 입금 조회는 동일 입금 건에 대해 10분당 최대 1회만 허용됩니다.

---

## 참고 링크

- [업비트 개발자 센터 - Rate Limits 공식 문서](https://docs.upbit.com/kr/reference/rate-limits)
- [Origin 헤더 Rate Limit 정책 공지](https://docs.upbit.com/kr/changelog/origin_rate_limit)
