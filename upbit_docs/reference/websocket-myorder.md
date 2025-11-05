# 내 주문 및 체결 (MyOrder)

내 주문 및 체결 데이터를 WebSocket으로 수신하기 위한 요청 및 구독 데이터 예시를 제공합니다.

## 내 주문 및 체결 실시간 스트림 전송 방식 안내

내 주문 및 체결 데이터의 경우 실제 주문 또는 체결이 발생할 때만 해당 내용이 실시간 스트림으로 전송됩니다. 따라서 **연결 후 주문 또는 체결이 발생하지 않는 경우 데이터 수신이 이루어지지 않는 것이 정상 동작**입니다. [WebSocket 사용 안내의 연결 유지 항목](ref:websocket-guide)을 참고하여 데이터 미전송시에도 연결이 유지되도록 클라이언트 사양 또는 구현을 확인하시기 바랍니다.

## Request 메세지 형식

내 주문 및 체결 데이터 수신을 요청하기 위해서는 WebSocket 연결 이후 아래 구조의 JSON Object를 생성한 뒤 요청 메세지의 Data Type Object로 포함하여 전송해야 합니다. Ticket, Format 필드를 포함한 전체 WebSocket 데이터 요청 메세지 명세는 [WebSocket 사용 안내](ref:websocket-guide) 문서를 참고해주세요.

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>타입</th>\n      <th>내용</th>\n      <th>필수 여부</th>\n      <th>기본 값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">type</td>\n      <td>String</td>\n      <td><code>myOrder</code></td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">codes</td>\n      <td>List</td>\n      <td>수신하고자 하는 페어 목록.<br>반드시 대문자로 요청해야 합니다.</td>\n      <td>Optional</td>\n      <td>생략하거나 빈 배열로 요청할 경우 모든 마켓에 대한 정보를 수신합니다.</td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json format - "DEFAULT" / 모든 페어 구독
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "myOrder"
  }
]

// 또는

[
  {
    "ticket": "test-myOrder"
  },
  {
    "type": "myOrder",
    "codes": []
  }
]
```
```json format - "DEFAULT" / 특정 페어 구독
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "myOrder",
    "codes": ["KRW-BTC"]
  }
]
```
```json format - "JSON LIST"
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "myOrder",
    "codes": ["KRW-BTC"]
  },
  {
    "format": "JSON_LIST"
  }
]
```

***

<br />

## 구독 데이터 명세

[block:html]
{
  "html": "  <div class=\"callout-section\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i>  신규 필드 추가 안내 (2025.07.02)\n      </div>\n      자전거래 체결 방지 (Self-Match Prevention) 기능 추가로 인해 주문 데이터 필드가 아래와 같이 추가됩니다. 자세한 사항은 관련 <a href=\"https://docs.upbit.com/kr/changelog/smp\">공지</a> 참고 부탁드립니다. <a href=\"/kr/docs/smp\">[SMP 상세 설명 바로가기]</a><br><br>\n      <li><code>smp_type</code> : <code>reduce</code>, <code>cancel_maker</code>, <code>cancel_taker</code></li >\n      <li>주문 상태 state 필드에 <code>prevented</code> (체결 방지) 타입이 신규로 추가됩니다.</li>\n      <li>신규 주문 조건 <code>post_only</code>가 추가되어 time_in_force 필드에 <code>post_only</code> 타입이 신규로 추가됩니다.</li>\n</div>\n\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>축약형</th>\n      <th>내용</th>\n      <th>타입</th>\n      <th>값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr><td>type</td><td>ty</td><td>타입</td><td>String</td><td><code>myOrder</code></td></tr>\n    <tr><td>code</td><td>cd</td><td>페어 코드(예시:KRW-BTC)</td><td>String</td><td></td></tr>\n    <tr><td>uuid</td><td>uid</td><td>주문의 유일 식별자</td><td>String</td><td></td></tr>\n    <tr><td>ask_bid</td><td>ab</td><td>매수/매도 구분</td><td>String</td><td><code>ASK</code><br>매도<br/><code>BID</code><br>매수</td></tr>\n    <tr><td>order_type</td><td>ot</td><td>주문 타입</td><td>String</td><td><code>limit</code><br>지정가 주문<br/><code>price</code><br>시장가 매수 주문<br/><code>market</code><br>시장가 매도 주문<br/><code>best</code><br>최유리 지정가 주문</td></tr>\n    <tr><td>state</td><td>s</td><td>주문 상태</td><td>String</td><td><code>wait</code><br>체결 대기<br/><code>watch</code><br>예약 주문 대기<br/><code>trade</code><br>체결 발생<br/><code>done</code><br>전체 체결 완료<br/><code>cancel</code><br>주문 취소<br/><code>prevented</code><br>체결 방지</td></tr>\n    <tr><td>trade_uuid</td><td>tuid</td><td>체결의 유일 식별자</td><td>String</td><td></td></tr>\n    <tr><td>price</td><td>p</td><td>주문 가격 또는<br/>체결 가격(state: trade 일 때)</td><td>Double</td><td></td></tr>\n    <tr><td>avg_price</td><td>ap</td><td>평균 체결 가격</td><td>Double</td><td></td></tr>\n    <tr><td>volume</td><td>v</td><td>주문량 또는<br/>체결량 (state: trade 일 때)</td><td>Double</td><td></td></tr>\n    <tr><td>remaining_volume</td><td>rv</td><td>체결 후 주문 잔량</td><td>Double</td><td></td></tr>\n    <tr><td>executed_volume</td><td>ev</td><td>체결된 수량</td><td>Double</td><td></td></tr>\n    <tr><td>trades_count</td><td>tc</td><td>해당 주문에 걸린 체결 수</td><td>Integer</td><td></td></tr>\n    <tr><td>reserved_fee</td><td>rsf</td><td>수수료로 예약된 비용</td><td>Double</td><td></td></tr>\n    <tr><td>remaining_fee</td><td>rmf</td><td>남은 수수료</td><td>Double</td><td></td></tr>\n    <tr><td>paid_fee</td><td>pf</td><td>사용된 수수료</td><td>Double</td><td></td></tr>\n    <tr><td>locked</td><td>l</td><td>거래에 사용중인 비용</td><td>Double</td><td></td></tr>\n    <tr><td>executed_funds</td><td>ef</td><td>체결된 금액</td><td>Double</td><td></td></tr>\n    <tr><td>time_in_force</td><td>tif</td><td>IOC, FOK, POST ONLY 설정</td><td>String</td><td><code>ioc</code><br/><code>fok</code><br/><code>post_only</code></td></tr>\n    <tr><td>trade_fee</td><td>tf</td><td>체결 시 발생한 수수료<br/>(state:<code>trade</code>가 아닐 경우 null)</td><td>Double</td><td></td></tr>\n    <tr><td>is_maker</td><td>im</td><td>체결이 발생한 주문의 메이커/테이커 여부<br/>(state:<code>trade</code>가 아닐 경우 null)</td><td>Boolean</td><td><code>true</code> : 메이커 주문<br/><code>false</code> : 테이커 주문</td></tr>\n    <tr><td>identifier</td><td>id</td><td>클라이언트 지정 주문 식별자</span></td><td>String</td><td></td></tr>\n    <tr><td>smp_type</td><td>smpt</td><td>자전거래 체결 방지 타입<br/>(동일 회원의 메이커/테이커 주문 간 체결 방지)</td><td>String</td><td><code>reduce</code><br>주문 줄이고 진행<br/><code>cancel_maker</code><br>메이커 주문 취소<br/><code>cancel_taker</code><br>테이커 주문 취소</td></tr>\n    <tr><td>prevented_volume</td><td>pv</td><td>자전거래 체결 방지로 인해 취소된 주문 수량</td><td>Double</td><td></td></tr>\n    <tr><td>prevented_locked</td><td>pl</td><td>(매수 시)자전거래 체결 방지 설정으로 인해 취소된 금액<br/>(매도 시)자전거래 체결 방지 설정으로 인해 취소된 수량</td><td>Double</td><td></td></tr>\n    <tr><td>trade_timestamp</td><td>ttms</td><td>체결 타임스탬프 (ms)</td><td>Long</td><td></td></tr>\n    <tr><td>order_timestamp</td><td>otms</td><td>주문 타임스탬프 (ms)</td><td>Long</td><td></td></tr>\n    <tr><td>timestamp</td><td>tms</td><td>타임스탬프 (ms)</td><td>Long</td><td></td></tr>\n    <tr><td>stream_type</td><td>st</td><td>스트림 타입</td><td>String</td><td><code>REALTIME</code><br>실시간 스트림<br><code>SNAPSHOT</code><br>스냅샷</td></tr>\n  </tbody>\n</table>\n"
}
[/block]


### 예시

```json format - "DEFAULT"
{
  "type": "myOrder",
  "code": "KRW-BTC",
  "uuid": "ac2dc2a3-fce9-40a2-a4f6-5987c25c438f",
  "ask_bid": "BID",
  "order_type": "limit",
  "state": "trade",
  "trade_uuid": "68315169-fba4-4175-ade3-aff14a616657",
  "price": 0.001453,
  "avg_price": 0.00145372,
  "volume": 30925891.29839369,
  "remaining_volume": 29968038.09235948,
  "executed_volume": 30925891.29839369,
  "trades_count": 1,
  "reserved_fee": 44.23943970238218,
  "remaining_fee": 21.77177967409916,
  "paid_fee": 22.467660028283017,
  "locked": 43565.33112787242,
  "executed_funds": 44935.32005656603,
  "time_in_force": null,
  "trade_fee": 22.467660028283017,
  "is_maker": true,
  "identifier": "test-1",
  "smp_type": "cancel_maker",
  "prevented_volume": 1.174291929,
  "prevented_locked": 0.001706246173,
  "trade_timestamp": 1710751590421,
  "order_timestamp": 1710751590000,
  "timestamp": 1710751597500,
  "stream_type": "REALTIME"
}
```
```json format - "JSON_LIST"
[
 {
    "type": "myOrder",
    "code": "KRW-BTC",
    "uuid": "ac2dc2a3-fce9-40a2-a4f6-5987c25c438f",
    "ask_bid": "BID",
    "order_type": "limit",
    "state": "trade",
    "trade_uuid": "68315169-fba4-4175-ade3-aff14a616657",
    "price": 0.001453,
    "avg_price": 0.00145372,
    "volume": 30925891.29839369,
    "remaining_volume": 29968038.09235948,
    "executed_volume": 30925891.29839369,
    "trades_count": 1,
    "reserved_fee": 44.23943970238218,
    "remaining_fee": 21.77177967409916,
    "paid_fee": 22.467660028283017,
    "locked": 43565.33112787242,
    "executed_funds": 44935.32005656603,
    "time_in_force": null,
    "trade_fee": 22.467660028283017,
    "is_maker": true,
    "identifier": "test-1",
    "smp_type": "cancel_maker",
    "prevented_volume": 1.174291929,
    "prevented_locked": 0.001706246173,
    "trade_timestamp": 1710751590421,
    "order_timestamp": 1710751590000,
    "timestamp": 1710751597500,
    "stream_type": "REALTIME"
  }
]
```
