# 현재가 (Ticker)

현재가 데이터를 WebSocket으로 수신하기 위한 요청 및 구독 데이터 예시를 제공합니다.

## Request 메세지 형식

현재가 데이터 수신을 요청하기 위해서는 WebSocket 연결 이후 아래 구조의 JSON Object를 생성한 뒤 요청 메세지의 Data Type Object로 포함하여 전송해야 합니다. Ticket, Format 필드를 포함한 전체 WebSocket 데이터 요청 메세지 명세는 [WebSocket 사용 안내](ref:websocket-guide) 문서를 참고해주세요.

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>타입</th>\n      <th>내용</th>\n      <th>필수 여부</th>\n      <th>기본 값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">type</td>\n      <td>String</td>\n      <td><code>ticker</code></td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">codes</td>\n      <td>List:String</td>\n      <td>수신하고자 하는 페어 목록.<br>반드시 대문자로 요청해야 합니다.</td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">is_only_snapshot</td>\n      <td>Boolean</td>\n      <td>스냅샷 시세만 제공</td>\n      <td>Optional</td>\n      <td><code>false</code></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">is_only_realtime</td>\n      <td>Boolean</td>\n      <td>실시간 시세만 제공</td>\n      <td>Optional</td>\n      <td><code>false</code></td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


<br />

### 예시

```json format - "DEFAULT"
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "ticker",
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
    "type": "ticker",
    "codes": ["KRW-BTC","KRW-ETH"]
  },
  {
    "format": "SIMPLE_LIST"
  }
]
```

<br />

<br />

***

## 구독 데이터 명세

현재가 스냅샷 또는 실시간 스트림 데이터는 아래와 같이 반환됩니다. 

[block:html]
{
  "html": "<style>\n .custom-table .deprecated {\n  color: #AFAFAF; \n}\n</style>\n\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>축약형</th>\n      <th>내용</th>\n      <th>타입</th>\n      <th>값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr><td class=\"code-col\">type</td><td>ty</td><td>데이터 항목</td><td>String</td><td><code>ticker</code></td></tr>\n    <tr><td class=\"code-col\">code</td><td>cd</td><td>페어 코드</td><td>String</td><td><code>KRW-BTC</code></td></tr>\n    <tr><td class=\"code-col\">opening_price</td><td>op</td><td>시가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">high_price</td><td>hp</td><td>고가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">low_price</td><td>lp</td><td>저가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">trade_price</td><td>tp</td><td>현재가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">prev_closing_price</td><td>pcp</td><td>전일 종가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">change</td><td>c</td><td>전일 종가 대비<br>가격 변동 방향</td><td>String</td><td><code>RISE</code><br>: 상승<br><code>EVEN</code><br>: 보합<br><code>FALL</code><br>: 하락</td></tr>\n    <tr><td class=\"code-col\">change_price</td><td>cp</td><td>전일 대비 가격 변동의 절대값</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">signed_change_price</td><td>scp</td><td>전일 대비 가격 변동 값</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">change_rate</td><td>cr</td><td>전일 대비 등락율의 절대값</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">signed_change_rate</td><td>scr</td><td>전일 대비 등락율</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">trade_volume</td><td>tv</td><td>가장 최근 거래량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">acc_trade_volume</td><td>atv</td><td>누적 거래량(UTC 0시 기준)</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">acc_trade_volume_24h</td><td>atv24h</td><td>24시간 누적 거래량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">acc_trade_price</td><td>atp</td><td>누적 거래대금(UTC 0시 기준)</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">acc_trade_price_24h</td><td>atp24h</td><td>24시간 누적 거래대금</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">trade_date</td><td>tdt</td><td>최근 거래 일자(UTC)</td><td>String</td><td><code>yyyyMMdd</code></td></tr>\n    <tr><td class=\"code-col\">trade_time</td><td>ttm</td><td>최근 거래 시각(UTC)</td><td>String</td><td><code>HHmmss</code></td></tr>\n    <tr><td class=\"code-col\">trade_timestamp</td><td>ttms</td><td>체결 타임스탬프(ms)</td><td>Long</td><td></td></tr>\n    <tr><td class=\"code-col\">ask_bid</td><td>ab</td><td>매수/매도 구분</td><td>String</td><td><code>ASK</code><br>: 매도<br><code>BID</code><br>: 매수</td></tr>\n    <tr><td class=\"code-col\">acc_ask_volume</td><td>aav</td><td>누적 매도량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">acc_bid_volume</td><td>abv</td><td>누적 매수량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">highest_52_week_price</td><td>h52wp</td><td>52주 최고가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">highest_52_week_date</td><td>h52wdt</td><td>52주 최고가 달성일</td><td>String</td><td><code>yyyy-MM-dd</code></td></tr>\n    <tr><td class=\"code-col\">lowest_52_week_price</td><td>l52wp</td><td>52주 최저가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">lowest_52_week_date</td><td>l52wdt</td><td>52주 최저가 달성일</td><td>String</td><td><code>yyyy-MM-dd</code></td></tr>\n    <tr><td class=\"code-col\">market_state</td><td>ms</td><td>거래상태</td><td>String</td><td><code>PREVIEW</code><br>: 입금지원<br><code>ACTIVE</code><br>: 거래지원가능<br><code>DELISTED</code><br>: 거래지원종료</td></tr>\n    <tr><td class=\"code-col deprecated\">is_trading_suspended</td><td class=\"deprecated\">its</td><td class=\"deprecated\">거래 정지 여부. <br> Deprecated 필드로 참조 대상에서 제외하는 것을 권장합니다.</td><td class=\"deprecated\">Boolean</td><td></td></tr>\n    <tr><td class=\"code-col\">delisting_date</td><td>dd</td><td>거래지원 종료일</td><td>Date</td><td></td></tr>\n    <tr><td class=\"code-col deprecated\">market_warning</td><td class=\"deprecated\">mw</td><td class=\"deprecated\">유의 종목 여부 <br> Deprecated 필드로 참조 대상에서 제외하는 것을 권장합니다.</td><td class=\"deprecated\">String</td><td class=\"deprecated\"><code>NONE</code><br>: 해당없음<br><code>CAUTION</code><br>: 투자유의</td></tr>\n    <tr><td class=\"code-col\">timestamp</td><td>tms</td><td>타임스탬프 (ms)</td><td>Long</td><td></td></tr>\n    <tr><td class=\"code-col\">stream_type</td><td>st</td><td>스트림 타입</td><td>String</td><td><code>SNAPSHOT</code><br>: 스냅샷<br><code>REALTIME</code><br>: 실시간</td></tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json format - "DEFAULT"
{
  "type": "ticker",
  "code": "KRW-BTC",
  "opening_price": 31883000,
  "high_price": 32310000,
  "low_price": 31855000,
  "trade_price": 32287000,
  "prev_closing_price": 31883000.00000000,
  "acc_trade_price": 78039261076.51241000,
  "change": "RISE",
  "change_price": 404000.00000000,
  "signed_change_price": 404000.00000000,
  "change_rate": 0.0126713295,
  "signed_change_rate": 0.0126713295,
  "ask_bid": "ASK",
  "trade_volume": 0.03103806,
  "acc_trade_volume": 2429.58834336,
  "trade_date": "20230221",
  "trade_time": "074102",
  "trade_timestamp": 1676965262139,
  "acc_ask_volume": 1146.25573608,
  "acc_bid_volume": 1283.33260728,
  "highest_52_week_price": 57678000.00000000,
  "highest_52_week_date": "2022-03-28",
  "lowest_52_week_price": 20700000.00000000,
  "lowest_52_week_date": "2022-12-30",
  "market_state": "ACTIVE",
  "is_trading_suspended": false,
  "delisting_date": null,
  "market_warning": "NONE",
  "timestamp": 1676965262177,
  "acc_trade_price_24h": 228827082483.70729000,
  "acc_trade_volume_24h": 7158.80283560,
  "stream_type": "REALTIME"
}
```
```json format - "SIMPLE_LIST"
[
  {
    "ty": "ticker",
    "cd": "KRW-BTC",
    "op": 148500000.0,
    "hp": 149064000.0,
    "lp": 148050000.0,
    "tp": 148956000.0,
    "pcp": 148500000.0,
    "atp": 16115868486.03173,
    "c": "RISE",
    "cp": 456000.0,
    "scp": 456000.0,
    "cr": 0.0030707071,
    "scr": 0.0030707071,
    "ab": "BID",
    "tv": 0.0602652,
    "atv": 108.51228784,
    "tdt": "20250707",
    "ttm": "022055",
    "ttms": 1751854855934,
    "aav": 36.9943567,
    "abv": 71.51793114,
    "h52wp": 163325000.0,
    "h52wdt": "2025-01-20",
...
    "st": "SNAPSHOT"
  }
]
```
