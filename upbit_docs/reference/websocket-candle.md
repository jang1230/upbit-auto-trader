# 캔들 (Candle)

캔들 데이터를 WebSocket으로 수신하기 위한 요청 및 구독 데이터 예시를 제공합니다.

## 캔들 실시간 스트림 전송 방식 안내

### 데이터 전송 주기

캔들 데이터의 실시간 스트림 전송 주기는 1초 입니다. 

### 데이터 생성 안내

캔들은 해당 시간대에 체결이 발생하여 직전 캔들 대비 캔들 데이터가 변경될 때에만 생성됩니다. 전송 주기인 1초가 지나더라도 체결이 발생하지 않은 경우 실시간 캔들 데이터 스트림이 발생하지 않습니다. 또한 요청 시점에 요청한 단위의 캔들 데이터가 생성되지 않은 경우 이전 시간 단위의 데이터가 최초 전송됩니다.

3분 봉 요청 상황을 예로 들어, 12:00:00 3분 봉은 존재하고, 12:03:00 ~ 12:04:00 사이는 아직 체결이 없는 상태라고 가정합니다. 이때 12:04:00 에 `candle.3m` 요청을 보내면, 서버는 12:00:00 ~ 12:03:00 3분 봉 데이터를 스냅샷 데이터로 반환합니다. 이후 12:04:05 에 첫 체결이 발생하면 서버는 즉시 12:03:00 3분봉을 생성하고, 다음 1초 interval 인 12:04:06 에 해당 12:03:00 3분 봉 데이터를 전송하게 됩니다. 

[block:html]
{
  "html": "<div class=\"callout-section callout-section--danger\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i> 같은 candle_date_time 데이터가 여러 번 전송될 수 있습니다.\n      </div>\n    다양한 시간 단위의 요청을 처리하는 캔들 실시간 스트림의 특성상, 데이터의 전송 주기를 완벽하게 보장하기 어려우며 체결 타이밍에 따라 같은 시간대의 캔들 데이터가 여러번 전송될 수 있습니다. 가장 마지막으로 수신한 데이터가 최신 데이터이며, 사용 전 candle_date_time 필드를 참조하여 값을 업데이트 하시기 바랍니다.\n  </div>"
}
[/block]


<br />

## Request 메세지 형식

캔들 데이터 수신을 요청하기 위해서는 WebSocket 연결 이후 아래 구조의 JSON Object를 생성한 뒤 요청 메세지의 Data Type Object로 포함하여 전송해야 합니다. Ticket, Format 필드를 포함한 전체 WebSocket 데이터 요청 메세지 명세는 [WebSocket 사용 안내](ref:websocket-guide) 문서를 참고해주세요.

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>타입</th>\n      <th>내용</th>\n      <th>필수 여부</th>\n      <th>기본 값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">type</td>\n      <td>String</td>\n      <td>\n        캔들 형식<br>\n        - <code>candle.1s</code>: 초봉<br>\n        - <code>candle.1m</code>: 1분봉<br>\n        - <code>candle.3m</code>: 3분봉<br>\n        - <code>candle.5m</code>: 5분봉<br>\n        - <code>candle.10m</code>: 10분봉<br>\n        - <code>candle.15m</code>: 15분봉<br>\n        - <code>candle.30m</code>: 30분봉<br>\n        - <code>candle.60m</code>: 60분봉<br>\n        - <code>candle.240m</code>: 240분봉\n      </td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">codes</td>\n      <td>List</td>\n      <td>수신하고자 하는 페어 목록.<br>반드시 대문자로 요청해야 합니다.</td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">is_only_snapshot</td>\n      <td>Boolean</td>\n      <td>스냅샷 시세만 제공</td>\n      <td>Optional</td>\n      <td><code>false</code></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">is_only_realtime</td>\n      <td>Boolean</td>\n      <td>실시간 시세만 제공</td>\n      <td>Optional</td>\n      <td><code>false</code></td>\n    </tr>\n  </tbody>\n</table>\n"
}
[/block]


### 예시

```json format - "DEFAULT"
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "candle.1s",
    "codes": [
      "KRW-BTC",
      "KRW-ETH"
    ]
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
    "type": "candle.1s",
    "codes": [
      "KRW-BTC",
      "KRW-ETH"
    ]
  },
  {
    "format": "SIMPLE_LIST"
  }
]
```

***

<br />

## 구독 데이터 명세

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>축약형</th>\n      <th>내용</th>\n      <th>타입</th>\n      <th>값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">type</td>\n      <td>ty</td>\n      <td>타입</td>\n      <td>String</td>\n      <td>\n        <code>candle.1s</code>: 초봉<br>\n        <code>candle.1m</code>: 1분봉<br>\n        <code>candle.3m</code>: 3분봉<br>\n        <code>candle.5m</code>: 5분봉<br>\n        <code>candle.10m</code>: 10분봉<br>\n        <code>candle.15m</code>: 15분봉<br>\n        <code>candle.30m</code>: 30분봉<br>\n        <code>candle.60m</code>: 60분봉<br>\n        <code>candle.240m</code>: 240분봉\n      </td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">code</td>\n      <td>cd</td>\n      <td>마켓 코드 (ex. KRW-BTC)</td>\n      <td>String</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">candle_date_time_utc</td>\n      <td>cdttmu</td>\n      <td>캔들 기준 시각(UTC 기준)<br>포맷: <code>yyyy-MM-dd'T'HH:mm:ss</code></td>\n      <td>String</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">candle_date_time_kst</td>\n      <td>cdttmk</td>\n      <td>캔들 기준 시각(KST 기준)<br>포맷: <code>yyyy-MM-dd'T'HH:mm:ss</code></td>\n      <td>String</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">opening_price</td>\n      <td>op</td>\n      <td>시가</td>\n      <td>Double</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">high_price</td>\n      <td>hp</td>\n      <td>고가</td>\n      <td>Double</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">low_price</td>\n      <td>lp</td>\n      <td>저가</td>\n      <td>Double</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">trade_price</td>\n      <td>tp</td>\n      <td>종가</td>\n      <td>Double</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">candle_acc_trade_volume</td>\n      <td>catv</td>\n      <td>누적 거래량</td>\n      <td>Double</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">candle_acc_trade_price</td>\n      <td>catp</td>\n      <td>누적 거래 금액</td>\n      <td>Double</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">timestamp</td>\n      <td>tms</td>\n      <td>타임스탬프 (ms)</td>\n      <td>Long</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">stream_type</td>\n      <td>st</td>\n      <td>스트림 타입</td>\n      <td>String</td>\n      <td><code>SNAPSHOT</code>: 스냅샷<br><code>REALTIME</code>: 실시간</td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json format - "DEFAULT"
{
  "type": "candle.1s",
  "code": "KRW-BTC",
  "candle_date_time_utc": "2025-01-02T04:28:05",
  "candle_date_time_kst": "2025-01-02T13:28:05",
  "opening_price": 142009000.00000000,
  "high_price": 142009000.00000000,
  "low_price": 142009000.00000000,
  "trade_price": 142009000.00000000,
  "candle_acc_trade_volume": 0.00606119,
  "candle_acc_trade_price": 860743.5307100000000000,
  "timestamp": 1735792085824,
  "stream_type": "REALTIME"
}
{
  "type": "candle.1s",
  "code": "KRW-ETH",
  "candle_date_time_utc": "2025-01-02T04:28:05",
  "candle_date_time_kst": "2025-01-02T13:28:05",
  "opening_price": 5059000.00000000,
  "high_price": 5059000.00000000,
  "low_price": 5059000.00000000,
  "trade_price": 5059000.00000000,
  "candle_acc_trade_volume": 0.08158869,
  "candle_acc_trade_price": 412757.1827100000000000,
  "timestamp": 1735792085749,
  "stream_type": "REALTIME"
}
```
```json format - "SIMPLE_LIST"
[
  {
    "ty": "candle.1s",
    "cd": "KRW-BTC",
    "cdttmu": "2025-07-07T02:29:24",
    "cdttmk": "2025-07-07T11:29:24",
    "op": 149000000.0,
    "hp": 149000000.0,
    "lp": 149000000.0,
    "tp": 149000000.0,
    "catv": 0.00033557,
    "catp": 49999.93,
    "tms": 1751855364161,
    "st": "SNAPSHOT"
  },
  {
    "ty": "candle.1s",
    "cd": "KRW-ETH",
    "cdttmu": "2025-07-07T02:29:12",
    "cdttmk": "2025-07-07T11:29:12",
    "op": 3515000.0,
    "hp": 3515000.0,
    "lp": 3515000.0,
    "tp": 3515000.0,
    "catv": 0.01,
...
    "st": "SNAPSHOT"
  }
]
```
