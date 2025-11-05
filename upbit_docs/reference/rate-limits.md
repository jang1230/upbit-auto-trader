# 요청 수 제한(Rate Limits)

업비트 API의 요청 수 제한(Rate Limits) 정책 안내 및 구현 가이드입니다.

## 요청 수 제한 정책

업비트 Open API는 안정적인 서비스 운영을 위해 초 단위의 요청 수 제한(Rate Limit) 정책을 적용하고 있습니다.

<br />

### 기본 정책 안내

- 모든 요청 수 제한은 초(Second) 단위로 적용됩니다.
- API가 속한 Rate Limit 그룹 별  **초당 최대 허용 요청 수**가 정의됩니다. 같은 그룹 API 간 요청 수가 함께 집계됩니다. 본 문서 하단 및 각 API Reference 하단 Rate Limit 영역에서 해당 API의 Rate Limit 그룹과 정책을 확인할 수 있습니다.
- 안정적인 서비스 제공을 위해, **서비스 상황에 따른 추가 초당 최대 허용 요청 수 제한이 발생할 수 있습니다.** 또한 Rate Limit 그룹별 초당 최대 허용 요청 수는 **서비스 정책에 따라 공지 후 변경될 수 있습니다.** 잔여 요청 수 확인 방법을 참고하여 과도한 요청이 발생하지 않도록 유의해주시기 바랍니다.
- **Origin 헤더를 포함한 요청의 경우 별도의 요청 수 제한 정책을 적용**합니다. 시세 조회(Quotation) REST API와 WebSocket 요청에 대해 모두 **10초당 1회**의 요청만을 허용합니다. 자세한 사항은 [관련 공지](https://docs.upbit.com/kr/changelog/origin_rate_limit)를 확인해주시기 바랍니다.

<br />

### 잔여 요청 수 확인 방법

REST API 응답의 `Remaining-Req` 헤더로 아래와 같은 잔여 요청 수 정보가 반환됩니다.

> group=default; min=1800; sec=29

- `group`: 해당 요청이 포함된 Rate Limit Group 입니다.
- `min`: 현재는 Depreated 된 분 단위 요청 제한 정보 필드입니다. 고정 값으로 반환되므로 참조 대상에서 제외하시기 바랍니다.
- `sec`: 현재 잔여 요청 수 입니다. 값이 0으로 반환되는 경우 잔여 요청 수가 없는 상황이므로 일정 시간 이후 요청해야 합니다.

[REST API Best Practice 문서](https://docs.upbit.com/kr/docs/rest-api-best-practice#%EC%9A%94%EC%B2%AD-%EC%88%98-%EC%A0%9C%ED%95%9Crate-limit-%EA%B4%80%EB%A0%A8-%EC%B2%98%EB%A6%AC) 에서는 응답 헤더의 Remaining-Req 값을 활용한 요청 수 제한 관리 방법과 Python 예제 코드(update_from_header)를 제공합니다. 요청 가능 횟수 추적을 통한 제한 정책 구현 시 해당 내용을 참고하시기 바랍니다.

<br />

### 기준 초과 요청에 대한 제한 안내

- 초당 최대 허용 요청 수를 초과한 요청에 대해 응답의 HTTP 상태 코드가 429 Too Many Requests 에러로 반환됩니다. 
- 429 에러 응답에도 지속적으로 요청을 전송하는 경우, **시스템에 의해 동일 IP 또는 계정 단위 요청이 일시적으로 차단됩니다. **IP 및 계정 차단 시 418 HTTP 상태 코드와 함께 차단 시간 정보가 함께 반환되오니 안내된 시간 이후 재시도하시기 바랍니다.
- 정책을 위반한 과도한 요청이 반복되는 경우 IP 차단 시간은 점진적으로 증가할 수 있습니다.

<br />

### 제한 단위

[block:html]
{
  "html": "<style>\nth.feature-col, td.feature-col {\n  width: 150px;\n  min-width: 150px;\n  max-width: 150px;\n  word-break: break-all;\n  }\n</style>\n\n\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th class=\"feature-col\">기능 분류</th>\n      <th class=\"feature-col\">측정 단위</th>\n      <th class=\"feature-col\">설명</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">시세 조회 REST API<br>(Quotation)</td>\n      <td>IP 단위</td>\n      <td>동일한 IP 주소에서 발생한 요청간 초 당 잔여 요청 횟수가 공유/차감되며, IP 단위로 제한이 적용됩니다.</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">거래 및 자산 관리 REST API<br>(Exchange)</td>\n      <td>계정 단위</td>\n      <td>동일한 계정으로 발급된 여러 API Key를 사용 하는 경우에도, 해당 계정 단위로 초 당 잔여 요청 횟수가 공유/차감됩니다.</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">WebSocket 연결 요청 및<br>데이터 요청</td>\n      <td>인증 헤더를 포함한 경우 계정 단위/미포함한 경우 IP 단위</td>\n      <td>시세(Quotation) 정보만 구독하기 위해 인증 없이 요청하는 경우 <b>IP단위</b>, 내 주문 및 체결(My Order), 내 자산(My Asset) 정보 구독을 위해 인증 정보를 포함하여 요청하는 경우 <b>계정 단위</b>로 측정됩니다.</td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


<br />

### Rate Limit 그룹 정책

[block:html]
{
  "html": "<style>\n.category-label {\n  display: inline-block;\n  padding: 2px 8px;\n  border-radius: 9px;\n  font-weight: 500;\n  font-size: 0.65rem;\n  color: #fff;\n  margin-right: 6px;\n  margin-bottom: 2px;\n  letter-spacing: 0.01em;\n  background: #228be6; /* 기본 파란색, 각 라벨에서 덮어씀 */\n  user-select: none;\n  vertical-align: middle;\n  line-height: 1.1;\n  box-shadow: none;\n}\n.quotation {\n  background: #f5f6fa;   /* 연한 회색 */\n  color: #222;\n  border: 1px solid #bdbdbd;\n}\n\n.exchange {\n  background: #444950;   /* 진한 회색 */\n  color: #fff;\n  border: 1px solid #444950;\n}\nth.feature-col, td.feature-col {\n  width: 150px;\n  min-width: 150px;\n  max-width: 150px;\n  word-break: break-all;\n  }\na {\n  color: inherit;\n  font-weight: inherit;\n}\na:visited {\n  color: inherit;\n}\na:hover,\na:active,\na:focus {\n  color: inherit;\n}\n\n\n</style>\n\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>Rate Limit 그룹</th>\n      <th class=\"feature-col\">정책</th>\n      <th>대상 API</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td><span class=\"category-label quotation\">Quotation</span><br><b><code>market</code></b></td>\n      <td class=\"feature-col\">초당 최대 10회</td>\n      <td><li><a href=\"list-trading-pairs\">페어 목록 조회</a></li></td>\n    </tr>\n    <tr>\n      <td><span class=\"category-label quotation\">Quotation</span><br><b><code>candle</code></b></td>\n      <td class=\"feature-col\">초당 최대 10회</td>\n      <td>\n        <li><a href=\"list-candles-seconds\">초(Second) 캔들 조회</a></li>\n        <li><a href=\"list-candles-minutes\">분(Minute) 캔들 조회</a></li>\n        <li><a href=\"list-candles-days\">일(Day) 캔들 조회</a></li>\n        <li><a href=\"list-candles-weeks\">주(Week) 캔들 조회</a></li>\n        <li><a href=\"list-candles-months\">월(Month) 캔들 조회</a></li>\n        <li><a href=\"list-candles-years\">연(Year) 캔들 조회</a></li>\n      </td>\n    </tr>\n    <tr>\n      <td><span class=\"category-label quotation\">Quotation</span><br><b><code>trade</code></b></td>\n      <td class=\"feature-col\">초당 최대 10회</td>\n      <td>\n        <li><a href=\"list-pair-trades\">페어 체결 이력 조회</a></li>\n      </td>\n    </tr>\n    <tr>\n      <td><span class=\"category-label quotation\">Quotation</span><br><b><code>ticker</code></b></td>\n      <td class=\"feature-col\">초당 최대 10회</td>\n      <td>\n        <li><a href=\"list-tickers\">페어 현재가 조회</a></li>\n        <li><a href=\"list-quote-tickers\">마켓 현재가 조회</a></li>\n      </td>\n    </tr>\n    <tr>\n      <td><span class=\"category-label quotation\">Quotation</span><br><b><code>orderbook</code></b></td>\n      <td class=\"feature-col\">초당 최대 10회</td>\n      <td>\n        <li><a href=\"list-orderbooks\">호가 정보 조회</a></li>\n        <li><a href=\"list-orderbook-levels\">호가 모아보기 단위 정보 조회(Deprecated)</a></li>\n      </td>\n    </tr>\n    <tr>\n      <td><span class=\"category-label exchange\">Exchange</span><br><b><code>default<br>(exchange default)</code></b></td>\n      <td class=\"feature-col\">초당 최대 30회</td>\n      <td>\n        <li><a href=\"get-balance\">계정 잔고 조회</a></li>\n        <li><a href=\"available-order-information\">주문 가능정보 조회</a></li>\n        <li><a href=\"cancel-order\">개별 주문 취소</a></li>\n        <li><a href=\"cancel-orders-by-ids\">지정 주문 목록 취소</a></li>\n        <li><a href=\"get-order\">개별 주문 조회</a></li>\n        <li><a href=\"list-orders-by-ids\">id로 주문 목록 조회</a></li>\n        <li><a href=\"list-open-orders\">체결 대기 주문 조회</a></li>\n        <li><a href=\"list-closed-orders\">종료 주문 조회</a></li>\n        <li><a href=\"withdraw\">디지털 자산 출금하기</a></li>\n        <li><a href=\"withdraw-krw\">원화 출금하기</a></li>\n        <li><a href=\"cancel-withdrawal\">디지털 자산 출금 취소 접수</a></li>\n        <li><a href=\"available-withdrawal-information\">출금 가능 정보 조회</a></li>\n        <li><a href=\"list-withdrawal-addresses\">출금 허용 주소 목록 조회</a></li>\n        <li><a href=\"get-withdrawal\">개별 출금 조회</a></li>\n        <li><a href=\"list-withdrawals\">출금 목록 조회</a></li>\n        <li><a href=\"create-deposit-address\">입금 주소 생성 요청</a></li>\n        <li><a href=\"get-deposit-address\">개별 입금 주소 조회</a></li>\n        <li><a href=\"list-deposit-addresses\">입금 주소 목록 조회</a></li>\n        <li><a href=\"available-deposit-information\">입금 가능 통화 조회</a></li>\n        <li><a href=\"get-deposit\">개별 입금 조회</a></li>\n        <li><a href=\"list-deposits\">입금 목록 조회</a></li>\n        <li><a href=\"deposit-krw\">원화 입금</a></li>\n        <li><a href=\"list-travelrule-vasps\">트래블룰 지원 거래소 목록 조회</a></li>\n        <li><a href=\"verify-travelrule-by-uuid\">입금 UUID로 트래블룰 검증 요청<br><span style=\"color: #ff0000;\">(동일 입금 건에 대해 10분당 최대 1회 요청 허용)</span></a></li>\n        <li><a href=\"verify-travelrule-by-txid\">입금 TXID로 트래블룰 검증 요청<br><span style=\"color: #ff0000;\">(동일 입금 건에 대해 10분당 최대 1회 요청 허용)</span></a></li>\n        <li><a href=\"get-service-status\">통화별 입출금 서비스 상태 조회</a></li>\n        <li><a href=\"list-api-keys\">API Key 목록 조회</a></li>\n      </td>\n    </tr>\n    <tr>\n      <td><span class=\"category-label exchange\">Exchange</span><br><b><code>order</code></b></td>\n      <td class=\"feature-col\">초당 최대 8회</td>\n      <td>\n        <li><a href=\"new-order\">주문 생성</a></li>\n        <li><a href=\"cancel-and-new-order\">취소 후 재주문</a></li>\n      </td>\n    </tr>\n\t\t<tr>\n      <td><span class=\"category-label exchange\">Exchange</span><br><b><code>order-test</code></b></td>\n      <td class=\"feature-col\">초당 최대 8회</td>\n      <td>\n        <li><a href=\"order-test\">주문 생성 테스트</a></li>\n      </td>\n    </tr>\n    <tr>\n      <td><span class=\"category-label exchange\">Exchange</span><br><b><code>order-cancel-all</code></b></td>\n      <td class=\"feature-col\">2초당 최대 1회</td>\n      <td>\n        <li><a href=\"batch-cancel-orders\">주문 일괄 취소</a></li>\n      </td>\n    </tr>\n\t\t<tr>\n      <td><b><code>websocket-connect</code></b></td>\n      <td class=\"feature-col\">초당 최대 5회</td>\n      <td>\n        <li>WebSocket 연결 요청</li>\n      </td>\n    </tr>\n    <tr>\n      <td><b><code>websocket-message</code></b></td>\n      <td class=\"feature-col\">초당 최대 5회, 분당 100회</td>\n      <td>\n        <li><a href=\"websocket-guide\">WebSocket 데이터 요청 메시지 전송</a></li>\n      </td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]
