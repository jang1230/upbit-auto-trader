# 체결 (Trade)

체결 데이터를 WebSocket으로 수신하기 위한 요청 및 구독 데이터 예시를 제공합니다.

## Request 메세지 형식

체결 데이터 수신을 요청하기 위해서는 WebSocket 연결 이후 아래 구조의 JSON Object를 생성한 뒤 요청 메세지의 Data Type Object로 포함하여 전송해야 합니다. Ticket, Format 필드를 포함한 전체 WebSocket 데이터 요청 메세지 명세는 [WebSocket 사용 안내](ref:websocket-guide) 문서를 참고해주세요.

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>타입</th>\n      <th>내용</th>\n      <th>필수 여부</th>\n      <th>기본 값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">type</td>\n      <td>String</td>\n      <td><code>trade</code></td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">codes</td>\n      <td>List:String</td>\n      <td>수신하고자 하는 페어 목록.<br>반드시 대문자로 요청해야 합니다.</td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">is_only_snapshot</td>\n      <td>Boolean</td>\n      <td>스냅샷 시세만 제공</td>\n      <td>Optional</td>\n      <td><code>false</code></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">is_only_realtime</td>\n      <td>Boolean</td>\n      <td>실시간 시세만 제공</td>\n      <td>Optional</td>\n      <td><code>false</code></td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json format - "DEFAULT"
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "trade",
    "codes": ["KRW-BTC","KRW-ETH"]
  },
  {
    "format": "DEFAULT"
  }
]
```
```json format - "SIMPLE_LIST"
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "trade",
    "codes": ["KRW-BTC","KRW-ETH"]
  },
  {
    "format": "SIMPLE_LIST"
  }
]
```

<br />

***

## 구독 데이터 명세

현재가 스냅샷 또는 실시간 스트림 데이터는 아래와 같이 반환됩니다. 

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>축약형</th>\n      <th>내용</th>\n      <th>타입</th>\n      <th>값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr><td class=\"code-col\">type</td><td>ty</td><td>데이터 항목</td><td>String</td><td><code>trade</code></td></tr>\n    <tr><td class=\"code-col\">code</td><td>cd</td><td>페어 코드</td><td>String</td><td><code>KRW-BTC</code></td></tr>\n    <tr><td class=\"code-col\">trade_price</td><td>tp</td><td>체결 가격</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">trade_volume</td><td>tv</td><td>체결량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">ask_bid</td><td>ab</td><td>매수/매도 구분</td><td>String</td><td><code>ASK</code><br>: 매도<br><code>BID</code><br>: 매수</td></tr>\n    <tr><td class=\"code-col\">prev_closing_price</td><td>pcp</td><td>전일 종가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">change</td><td>c</td><td>전일 종가 대비 가격 변동 방향</td><td>String</td><td><code>RISE</code><br>: 상승<br><code>EVEN</code><br>: 보합<br><code>FALL</code><br>: 하락</td></tr>\n    <tr><td class=\"code-col\">change_price</td><td>cp</td><td>전일 대비 가격 변동의 절대값</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">trade_date</td><td>td</td><td>체결 일자(UTC 기준)</td><td>String</td><td><code>yyyy-MM-dd</code></td></tr>\n    <tr><td class=\"code-col\">trade_time</td><td>ttm</td><td>체결 시각(UTC 기준)</td><td>String</td><td><code>HH:mm:ss</code></td></tr>\n    <tr><td class=\"code-col\">trade_timestamp</td><td>ttms</td><td>체결 타임스탬프(ms)</td><td>Long</td><td></td></tr>\n    <tr><td class=\"code-col\">timestamp</td><td>tms</td><td>타임스탬프(ms)</td><td>Long</td><td></td></tr>\n    <tr><td class=\"code-col\">sequential_id</td><td>sid</td><td>체결 번호(Unique)</td><td>Long</td><td></td></tr>\n    <tr><td class=\"code-col\">best_ask_price</td><td>bap</td><td>최우선 매도 호가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">best_ask_size</td><td>bas</td><td>최우선 매도 잔량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">best_bid_price</td><td>bbp</td><td>최우선 매수 호가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">best_bid_size</td><td>bbs</td><td>최우선 매수 잔량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">stream_type</td><td>st</td><td>스트림 타입</td><td>String</td><td><code>SNAPSHOT</code><br>: 스냅샷<br><code>REALTIME</code><br>: 실시간</td></tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json format - "DEFAULT"
{
  "type": "trade",
  "code": "KRW-BTC",
  "timestamp": 1730336862082,
  "trade_date": "2024-10-31",
  "trade_time": "01:07:42",
  "trade_timestamp": 1730336862047,
  "trade_price": 100473000.00000000,
  "trade_volume": 0.00014208,
  "ask_bid": "BID",
  "prev_closing_price": 100571000.00000000,
  "change": "FALL",
  "change_price": 98000.00000000,
  "sequential_id": 17303368620470000,
  "best_ask_price": 100473000,
  "best_ask_size": 0.43139478,
  "best_bid_price": 100465000,
  "best_bid_size": 0.01990656,
  "stream_type": "SNAPSHOT"
}
{
  "type": "trade",
  "code": "KRW-ETH",
  "timestamp": 1730336862120,
  "trade_date": "2024-10-31",
  "trade_time": "01:07:42",
  "trade_timestamp": 1730336862080,
  "trade_price": 3700000.00000000,
  "trade_volume": 0.02207517,
  "ask_bid": "BID",
  "prev_closing_price": 3695000.00000000,
  "change": "RISE",
  "change_price": 5000.00000000,
  "sequential_id": 17303368620800006,
  "best_ask_price": 3700000,
  "best_ask_size": 0.39101775,
  "best_bid_price": 3699000,
  "best_bid_size": 0.13499454,
  "stream_type": "SNAPSHOT"
}
```
```json format - "JSON_LIST"
[
  {
    "type": "trade",
    "code": "KRW-BTC",
    "timestamp": 1730336862082,
    "trade_date": "2024-10-31",
    "trade_time": "01:07:42",
    "trade_timestamp": 1730336862047,
    "trade_price": 100473000.00000000,
    "trade_volume": 0.00014208,
    "ask_bid": "BID",
    "prev_closing_price": 100571000.00000000,
    "change": "FALL",
    "change_price": 98000.00000000,
    "sequential_id": 17303368620470000,
    "best_ask_price": 100473000,
    "best_ask_size": 0.43139478,
    "best_bid_price": 100465000,
    "best_bid_size": 0.01990656,
    "stream_type": "SNAPSHOT"
  }
  {
    "type": "trade",
    "code": "KRW-ETH",
    "timestamp": 1730336862120,
    "trade_date": "2024-10-31",
    "trade_time": "01:07:42",
    "trade_timestamp": 1730336862080,
    "trade_price": 3700000.00000000,
    "trade_volume": 0.02207517,
    "ask_bid": "BID",
    "prev_closing_price": 3695000.00000000,
    "change": "RISE",
    "change_price": 5000.00000000,
    "sequential_id": 17303368620800006,
    "best_ask_price": 3700000,
    "best_ask_size": 0.39101775,
    "best_bid_price": 3699000,
    "best_bid_size": 0.13499454,
    "stream_type": "SNAPSHOT"
  }
]
```
