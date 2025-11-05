# WebSocket 사용 및 에러 안내

업비트 WebSocket 연결 및 데이터 수신을 위한 사용 안내입니다.

## Endpoint

업비트 WebSocket Endpoint는 아래와 같습니다. 조회하고자 하는 데이터의 분류에 따라 세부 Endpoint가 구분됩니다.

> **시세(Quotation)**: wss://api.upbit.com/websocket/v1 
>
> **자산 및 주문(Exchange)**: wss://api.upbit.com/websocket/v1/private 

[block:html]
{
  "html": "<div class=\"callout-section\" style=\"border: 1px solid #f2b9b9; background: #fff8f8; padding: 1rem 1.25rem; border-radius: 8px;\">\n  <div class=\"callout-title\" style=\"display: flex; align-items: center; font-weight: 700; color: #c62828; margin-bottom: 0.75rem;\">\n    <i class=\"fa-solid fa-circle-exclamation\" style=\"color: #e53935; margin-right: 0.5rem;\"></i>\n    TLS 1.2 이상 업그레이드 필요\n  </div>\n  <div style=\"color: #333; line-height: 1.7; font-size: 0.95rem;\">\n    업비트 <strong>Open API</strong>는 회원님의 정보를 안전하게 보호하기 위해 <strong>TLS 1.2</strong> 이상 버전만 지원합니다.<br>\n    <strong>TLS 1.2</strong> 미만 버전은 더 이상 지원되지 않으므로, 최소 <strong>TLS 1.2</strong> 이상으로 업그레이드해 주시기 바랍니다.\n  </div>\n  <ul style=\"margin-top: 0.75rem; padding-left: 1.25rem; color: #555; font-size: 0.9rem;\">\n    <li><strong>TLS 1.2</strong> (최소 지원 버전)</li>\n    <li><strong>TLS 1.3</strong> (권장 버전)</li>\n  </ul>\n</div>\n"
}
[/block]


<br />

## 인증

Exchange 데이터를 수신하기 위해 WebSocket을 `wss://api.upbit.com/websocket/v1/private` 도메인으로 연결하는 경우 인증이 필요합니다. [인증](ref:auth) 가이드를 참고하여 생성한 JWT 토큰을 Authorization 헤더에 반드시 포함하여 요청해야 합니다. Bearer 인증을 지원하며, 아래와 같은 형식으로 입력합니다.

> Authorization: Bearer eyJhb...d8sTw

[block:html]
{
  "html": "<div class=\"callout-section\">\n  <div class=\"callout-title\">\n    <i class=\"fa-solid fa-circle-exclamation\"></i>  WebSocket 클라이언트 사용 시 헤더 설정을 지원하지 않을 수 있습니다.</div>\n    wscat과 같은 일부 WebSocket 클라이언트들은 커스텀 헤더 설정을 지원하지 않으므로 Exchange 데이터 수신 확인이 어려울 수 있습니다. 클라이언트 선택 전 헤더 지원 여부를 확인하시고, 필요한 경우 아래 구현 가이드를 참고하여 구현 후 사용하시기를 권장드립니다. \n</div>"
}
[/block]


<br />

## 요청 수 제한

WebSocket 요청 수 제한 정책은 [요청 수 제한(Rate Limits)](ref:rate-limits)문서를 참조하시기 바랍니다.

<br />

## 에러 안내

WebSocket 연결 후 요청에 대한 에러 발생 시, 응답은 다음과 같은 JSON 형식으로 반환됩니다. 

```json Error Response
{
  "error": {
    "name": "ERRPR_CODE",
    "message": "ERROR_MESSAGE"
  }
}
```
```json Example - INVALID_AUTH
{
  "error": {
    "name": "INVALID_AUTH",
    "message": "인증 정보가 올바르지 않습니다."
  }
}
```

반환될 수 있는 주요 에러 코드 목록은 아래와 같습니다.

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th class=\"feature-col\"><code>error.name</code></th>\n      <th class=\"feature-col\">발생 이유</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\"><code>INVALID_AUTH</code></td>\n      <td>인증 정보 누락 또는 인증 토큰 검증 실패</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><code>WRONG_FORMAT</code></td>\n      <td>요청 형식 위반</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><code>NO_TICKET</code></td>\n      <td>티켓 필드 누락</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><code>NO_TYPE</code></td>\n      <td>타입 필드 누락</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><code>NO_CODES</code></td>\n      <td>코드 필드 누락</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><code>INVALID_PARAM</code></td>\n      <td>필수 요청 파라미터 누락 또는 지원하지 않는 값 요청</td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


<br />

## 데이터 항목

업비트 WebSocket을 통해 조회 및 구독할 수 있는 데이터 항목은 다음과 같습니다. 

[block:html]
{
  "html": "<style>\n.category-label {\n  display: inline-block;\n  padding: 2px 8px;\n  border-radius: 9px;\n  font-weight: 500;\n  font-size: 0.65rem;\n  color: #fff;\n  margin-right: 6px;\n  margin-bottom: 2px;\n  letter-spacing: 0.01em;\n  background: #228be6; /* 기본 파란색, 각 라벨에서 덮어씀 */\n  user-select: none;\n  vertical-align: middle;\n  line-height: 1.1;\n  box-shadow: none;\n}\n.quotation {\n  background: #f5f6fa;   /* 연한 회색 */\n  color: #222;\n  border: 1px solid #bdbdbd;\n}\n\n.exchange {\n  background: #444950;   /* 진한 회색 */\n  color: #fff;\n  border: 1px solid #444950;\n}\n</style>\n\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>데이터 항목(type)</th>\n      <th>설명</th>\n      <th>지원 형식</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\"><span class=\"category-label quotation\">Quotation</span><br><b><code>ticker</code></b></td>\n      <td>현재가 데이터 수신</td>\n      <td>스냅샷, 실시간 스트림</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><span class=\"category-label quotation\">Quotation</span><br><b><code>trade</code></b></td>\n      <td>체결 데이터 수신</td>\n      <td>스냅샷, 실시간 스트림</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><span class=\"category-label quotation\">Quotation</span><br><b><code>orderbook</code></b></td>\n      <td>호가 데이터 수신</td>\n      <td>스냅샷, 실시간 스트림</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><span class=\"category-label quotation\">Quotation</span><br><b><code>candle.{unit}</code></b></td>\n      <td>캔들(초봉, 분봉) 데이터 수신</td>\n      <td>스냅샷, 실시간 스트림</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><span class=\"category-label exchange\">Exchange</span><br><b><code>myAsset</code></b></td>\n      <td>내 자산 데이터 수신</td>\n      <td>실시간 스트림</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\"><span class=\"category-label exchange\">Exchange</span><br><b><code>myOrder</code></b></td>\n      <td>내 주문 데이터 수신</td>\n      <td>실시간 스트림</td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


<br />

## 데이터 유형

WebSocket을 통해 수신할 수 있는 데이터는 스냅샷 데이터와 실시간 스트림의 두가지 유형으로 구분됩니다. 

- **스냅샷** 데이터란, 요청 시점의 정보를 1회 수신하는 방식입니다. 
- **실시간 스트림**은 WebSocket 연결이 유지되는 동안 지속적으로 정보가 수신되는 방식으로, 데이터 항목에 따라 일정한 갱신 주기마다 또는 이벤트가 발생하는 시점에 정보를 수신할 수 있습니다. 

사용자는 WebSocket 채널을 통해 서버로 스냅샷 데이터와 실시간 스트림 데이터 전송을 요청하는 메세지를 송신할 수 있으며, 특정 유형의 데이터만을 요청할 수도 있습니다. 항목 별로 지원하는 데이터 유형을 확인하고 용도에 맞게 조회하여 사용하시기 바랍니다. 

<br />

## 요청 메세지의 구조와 형식

데이터 전송 요청 메세지는 JSON Array형식으로, 아래와 같은 JSON Object들을 포함해야 합니다.

<br />

### Ticket Object

배열의 첫번째 요소로 Ticket Object를 입력합니다. Ticket Object 명세는 아래와 같습니다.

[block:html]
{
  "html": "<div style=\"margin-left: 20px;\">\n  <table class=\"custom-table\">\n    <thead>\n      <tr>\n        <th class=\"feature-col\">필드명</th>\n        <th class=\"feature-col\">형식</th>\n        <th class=\"feature-col\">필수 여부</th>\n        <th class=\"feature-col\">설명</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td class=\"code-col\">ticket</td>\n        <td>String</td>\n        <td>Required</td>\n        <td>요청 티켓의 고유 식별자. UUID 등 고유성을 보장하는 문자열을 사용합니다.</td>\n      </tr>\n    </tbody>\n  </table>\n</div>"
}
[/block]


<br />

### Data Type Object

배열의 두번째 요소 부터 조회하고자 하는 데이터 요청 Object를 입력합니다. 2개 이상의 Object를 입력하여 동시에 여러 데이터를 요청 및 수신할 수 있습니다. 데이터 구독 요청의 공통 필드인 `type` 필드를 제외한 **항목별 요청 Object 명세와 응답 명세는 항목별 Reference 문서를 참고해주시기 바랍니다. **

[block:html]
{
  "html": "<div style=\"margin-left: 20px;\">\n  <table class=\"custom-table\">\n    <thead>\n      <tr>\n        <th class=\"feature-col\">필드명</th>\n        <th class=\"feature-col\">형식</th>\n        <th class=\"feature-col\">필수 여부</th>\n        <th class=\"feature-col\">설명</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td class=\"code-col\">type</td>\n        <td>String</td>\n        <td>Required</td>\n        <td>수신하고자 하는 데이터 항목. <code>ticker</code>, <code>trade</code>, <code>orderbook</code>, <code>candle.{unit}</code>, <code>myAsset</code>, <code>myOrder</code> 중 하나를 입력할 수 있습니다.</td>\n      </tr>\n      <tr>\n\t\t\t\t<td class=\"code-col\">codes</td>\n        <td>String</td>\n        <td>Conditional</td>\n        <td>조회하고자 하는 페어 목록. type 필드가 <code>ticker</code>, <code>trade</code>, <code>orderbook</code>, <code>candle.{unit}</code> 인 경우 필수(Required), <code>myOrder</code>인 경우 선택적으로 사용할 수 있습니다.</td>\n      </tr>\n      <tr>\n\t\t\t\t<td class=\"code-col\">level</td>\n        <td>String</td>\n        <td>Optional</td>\n        <td>호가 모아보기 단위. type 필드가 <code>orderbook</code>인 경우에만 선택적으로 사용할 수 있습니다.</td>\n\t\t\t</tr>\n      <tr>\n        <td class=\"code-col\">is_only_snapshot</td>\n        <td>String</td>\n        <td>Optional</td>\n\t\t\t\t<td>스냅샷만 요청. type 필드가 <code>ticker</code>, <code>trade</code>, <code>orderbook</code>, <code>candle.{unit}</code> 인 경우에만 선택적으로 사용할 수 있습니다.</td>\n      </tr>\n      <tr>\n        <td class=\"code-col\">is_only_realtime</td>\n        <td>String</td>\n        <td>Optional</td>\n        <td>실시간 스트림만 요청. type 필드가 <code>ticker</code>, <code>trade</code>, <code>orderbook</code>, <code>candle.{unit}</code> 인 경우에만 선택적으로 사용할 수 있습니다.</td>\n      </tr>\n    </tbody>\n  </table>\n</div>\n"
}
[/block]


### Format Object

배열의 마지막 요소로 Format Object를 입력합니다. 설정에 따라 일반 포맷, SIMPLE 포맷, 또는 배열 포맷으로 데이터를 수신할 수 있습니다. SIMPLE 포맷은 각 필드의 key 값이 축약어 형태로 반환되는 포맷입니다. 예를 들어 `market` 필드는 `mk`으로 표기됩니다. 많은 데이터를 수신하여 데이터 사이즈를 줄이고자 하는 경우 유용하게 사용할 수 있습니다. Format Object 명세는 아래와 같습니다.

[block:html]
{
  "html": "<div style=\"margin-left: 20px;\">\n  <table class=\"custom-table\">\n    <thead>\n      <tr>\n        <th class=\"feature-col\">필드명</th>\n        <th class=\"feature-col\">형식</th>\n        <th class=\"feature-col\">필수 여부</th>\n        <th class=\"feature-col\">설명</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td class=\"code-col\">format</td>\n        <td>String</td>\n        <td>Required</td>\n        <td>\n          수신하고자 하는 데이터 포맷입니다. <code>DEFAULT</code>,<code>SIMPLE</code>,<code>JSON_LIST</code>,<code>SIMPLE_LIST</code> 중 하나를 입력할 수 있습니다.<br><br>\n          <li><code>DEFAULT</code> : 기본 포맷. </li>\n          <li><code>SIMPLE</code> : 간략한 포맷. 각 필드가 축약어 형태로 반환됩니다.</li>\n          <li><code>JSON_LIST</code> : 리스트 포맷.</li>\n          <li><code>SIMPLE_LIST</code> : 축약어 형태의 리스트 포맷.</li>\n        </td>\n      </tr>\n    </tbody>\n  </table>\n</div>"
}
[/block]


### 요청 예제

```json 단일 Ticker 스냅샷/실시간 스트림 조회 요청
[
  {"ticket":"3e2c4a9f-f0a7-457f-945e-4b57bde9f1ec"},	
  {"type":"ticker","codes":["KRW-BTC"]}
]
```
```json Trade, Orderbook 스냅샷/실시간 스트림 SIMPLE 포맷 조회 요청
[
  {"ticket":"9a65cd93-8786-4202-9b13-bd90e0c8b64b"},
  {"type":"trade","codes":["KRW-BTC","BTC-BCH"]},
	{"type":"orderbook","codes":["KRW-BTC","BTC-BCH"]},
  {"format":"SIMPLE"}
]
```

<br />

## 연결 관리

업비트 WebSocket 서버는 안정적인 연결 관리와 유지를 위한 [PING/PONG Frame](https://tools.ietf.org/html/rfc6455#section-5.5.2)을 지원합니다. 

- WebSocket 서버는 기본적으로 아무런 데이터도 수신/발신 되지 않은 채 120초가 경과하면 Idle Timeout으로 WebSocket 연결을 종료합니다.
- 클라이언트는 서버로 주기적으로 PING Frame을 보내 자동 연결 종료를 방지하고 연결 상태를 확인할 수 있습니다. 
- 대부분의 WebSocket 클라이언트 또는 라이브러리는 연결 유지를 위한 PING 함수 전송 기능이 내장되어 있으므로 사용중인 클라이언트의 사양을 확인하시기 바랍니다.
- PING Frame 요청을 보내는 별도의 구현이 어려운 경우, "PING" 메세지를 송신하여 연결을 유지할 수 있습니다. 연결이 정상적으로 유지되고 있는 경우, 아래와 같이 서버는 클라이언트에게 10초 간격으로  `UP` 상태 메시지를 전송합니다.

```shell
$ telsocket -url wss://api.upbit.com/websocket/v1
Connected!
PING
{"status":"UP"}
{"status":"UP"}
{"status":"UP"}
...
```

<br />

## 압축

업비트 WebSocket 서버는 더 빠르고 효율적인 데이터 전송을 위해 [압축(Compression)](https://tools.ietf.org/html/rfc7692)  기능을 제공합니다. 

- 사용중인 WebSocket 클라이언트 또는 라이브러리에서 압축 옵션을 지원하는 경우, 해당 옵션을 활성화하여 압축 형식으로 데이터를 주고 받을 수 있습니다. 
- 전송 구간이 종료되면 압축 데이터는 클라이언트 또는 라이브러리에 의해 압축 해제되어 제공되므로, 사용자는 옵션의 사용 여부와 상관 없이 Raw 데이터를 수신하여 사용할 수 있습니다. 따라서 별도의 압축 관련 구현은 요구되지 않습니다.

<br />

## 연결 및 요청 테스트

WebSocket 클라이언트를 활용하여 간단히 업비트 WebSocket 데이터 수신을 테스트해볼 수 있습니다. 널리 알려진 wscat과 telsocket 클라이언트를 활용한 예제를 제공합니다. 둘 중 하나의 클라이언트를 설치한 뒤, 연결 명령어를 아래와 같이 실행할 수 있습니다.

[block:html]
{
  "html": "<div class=\"callout-section\">\n  <div class=\"callout-title\">\n    <i class=\"fa-solid fa-circle-exclamation\"></i> Node.js 설치 안내\n    </div>\n    이 예제는 macOS, Linux뿐 아니라 Windows 환경(명령 프롬프트 또는 PowerShell)에서도 사용 가능합니다. 단, Node.js가 설치되어 있어야 하며, npm 명령이 정상적으로 동작해야 합니다.\n</div>"
}
[/block]


<br />

```shell Shell - wscat 사용 예제
$ npm install -g wscat
$ wscat -c wss://api.upbit.com/websocket/v1
connected (press CTRL+C to quit)
```
```shell Shell - telsocket 사용 예제
$ telsocket -url wss://api.upbit.com/websocket/v1
Connected!
```

<br />

연결이 성공적으로 완료되었다면, 아래와 같이 요청 메세지를 전송하여 KRW-BTC 페어의 현재가 실시간 스트림을 구독할 수 있습니다.

```shell
$ telsocket -url wss://api.upbit.com/websocket/v1
Connected!
[{"ticket":"test"},{"type":"ticker","codes":["KRW-BTC"]}]
{"market":"KRW-BTC","opening_price":8450000.00000000,"high_price":8679000.00000000,"low_price":8445000.00000000,"trade_price":8629000.0,"prev_closing_price":8450000.00000000,"acc_trade_price":105514711074.18726000,"change":"RISE","change_price":179000.00000000,"signed_change_price":179000.00000000,"change_rate":0.0211834320,"signed_change_rate":0.0211834320,"ask_bid":"ASK","trade_volume":0.0105675,"acc_trade_volume":12312.36058857,"trade_date":"20180418","trade_time":"100729","trade_timestamp":1524046049000,"acc_ask_volume":5703.42273172,"acc_bid_volume":6608.93785685,"highest_52_week_price":28885000.00000000,"highest_52_week_date":"2018-01-06","lowest_52_week_price":3286000.00000000,"lowest_52_week_date":"2017-09-15","trade_status":"ACTIVE","market_state":"ACTIVE","market_state_for_ios":"ACTIVE","is_trading_suspended":false,"delisting_date":null,"market_warning":"NONE","timestamp":1524046049766,"acc_trade_price_24h":55330325803.78210000,"acc_trade_volume_24h":6448.96200341}
 {"market":"KRW-BTC","opening_price":8450000.00000000,"high_price":8679000.00000000,"low_price":8445000.00000000,"trade_price":8629000.0,"prev_closing_price":8450000.00000000,"acc_trade_price":105515441503.850220000,"change":"RISE","change_price":179000.00000000,"signed_change_price":179000.00000000,"change_rate":0.0211834320,"signed_change_rate":0.0211834320,"ask_bid":"ASK","trade_volume":0.08464824,"acc_trade_volume":12312.44523681,"trade_date":"20180418","trade_time":"100730","trade_timestamp":1524046050000,"acc_ask_volume":5703.50737996,"acc_bid_volume":6608.93785685,"highest_52_week_price":28885000.00000000,"highest_52_week_date":"2018-01-06","lowest_52_week_price":3286000.00000000,"lowest_52_week_date":"2017-09-15","trade_status":"ACTIVE","market_state":"ACTIVE","market_state_for_ios":"ACTIVE","is_trading_suspended":false,"delisting_date":null,"market_warning":"NONE","timestamp":1524046050758,"acc_trade_price_24h":55330325803.78210000,"acc_trade_volume_24h":6448.96200341}
...
```

<br />

특별히 스냅샷만, 혹은 실시간 정보만 받겠다고 명시하지 않았기 때문에 맨 처음 스냅샷 정보가 내려오고 뒤를 이어 실시간 정보를 계속해서 수신할 수 있습니다. 만약 여러 페어의 정보를 동시에 수신하고 싶은 경우 codes 필드에 페어 코드들을 쉼표(,)으로 구분하여 명시합니다.

<br />

## 요청 예시

원화-비트코인(KRW-BTC) 마켓과 비트코인-비트코인캐시(KRW-BCH) 마켓의 실시간 체결정보만을 간소화된 포맷(SIMPLE)으로 수신하고 싶은 경우 다음과 같이 요청할 수 있습니다.

```text SIMPLE
$ telsocket -url wss://api.upbit.com/websocket/v1
Connected!

[{"ticket":"test"},{"type":"trade","codes":["KRW-BTC","BTC-BCH"]},{"format":"SIMPLE"}]
{"mk":"KRW-BTC","tms":1523531768829,"td":"2018-04-12","ttm":"11:16:03","ttms":1523531763000,"tp":7691000.0,"tv":0.00996719,"ab":"BID","pcp":7429000.00000000,"c":"RISE","cp":262000.00000000,"sid":1523531768829000,"st":"SNAPSHOT"}
 {"mk":"BTC-BCH","tms":1523531745481,"td":"2018-04-12","ttm":"11:15:48","ttms":1523531748370,"tp":0.09601999,"tv":0.18711789,"ab":"BID","pcp":0.09618000,"c":"FALL","cp":0.00016001,"sid":15235317454810000,"st":"SNAPSHOT"}
 {"mk":"KRW-BTC","tms":1523531769250,"td":"2018-04-12","ttm":"11:16:04","ttms":1523531764000,"tp":7691000.0,"tv":0.07580113,"ab":"BID","pcp":7429000.00000000,"c":"RISE","cp":262000.00000000,"sid":1523531769250000,"st":"REALTIME"}
 ...
```
```Text JSON_LIST
$ telsocket -url wss://api.upbit.com/websocket/v1
Connected!

[{"ticket":"test"}, {"type": "orderbook", "codes": ["KRW-BTC", "KRW-ETH", "KRW-XRP"], {"format":"JSON_LIST"}]

[
  {
    "type": "orderbook",
    "code": "KRW-BTC",
    "timestamp": 1751854223422,
    "total_ask_size": 5.62766605,
    "total_bid_size": 2.05887046,
    "orderbook_units": [
      {
        "ask_price": 148961000.0,
        "bid_price": 148960000.0,
        "ask_size": 0.07029618,
        "bid_size": 0.03754714
      },
      ...
      {
        "ask_price": 3123.0,
        "bid_price": 3064.0,
        "ask_size": 27866.74745758,
        "bid_size": 74293.14839192
      }
    ],
    "stream_type": "SNAPSHOT",
    "level": 0
  }
]
```
```Text SIMPLE_LIST
$ telsocket -url wss://api.upbit.com/websocket/v1
Connected!

[{"ticket":"test"}, {"type": "orderbook", "codes": ["KRW-BTC", "KRW-ETH", "KRW-XRP"], {"format":"SIMPLE_LIST"}]

[
  {
    "ty": "orderbook",
    "cd": "KRW-BTC",
    "tms": 1751854413122,
    "tas": 6.24428096,
    "tbs": 1.87774193,
    "obu": [
      {
        "ap": 149061000,
        "bp": 149054000,
        "as": 0.02035833,
        "bs": 0.03354488
      },
      {
        "ap": 149062000,
        "bp": 149018000,
        "as": 0.01108025,
        "bs": 0.01176719
      },
      {
        "ap": 149063000,
        "bp": 149017000,
        "as": 0.00409224,
        "bs": 0.00670897
...
    "lv": 0
  }
]
```

이 외에도 아래와 같은 요청 예시를 소개하오니, 요청 형식 확인 및 사용에 참고하시기 바랍니다. 

- KRW-BTC, BTC-XRP 페어의 실시간 체결 스트림 구독  
  \[{"ticket":"UNIQUE_TICKET"},{"type":"trade","codes":["KRW-BTC","BTC-XRP"]}]
- KRW-BTC, BTC-XRP 페어의 실시간 호가 스트림 구독  
  \[{"ticket":"UNIQUE_TICKET"},{"type":"orderbook","codes":["KRW-BTC","BTC-XRP"]}]
- KRW-BTC 페어의 1~3호가, BTC-XRP 페어의 실시간 1~5호가 스트림 구독  
  \[{"ticket":"UNIQUE_TICKET"},{"type":"orderbook","codes":["KRW-BTC.3","BTC-XRP.5"]}]
- KRW-BTC 페어의 체결 정보, KRW-ETH 페어의 실시간 호가 스트림 구독  
  \[{"ticket":"UNIQUE_TICKET"},{"type":"trade","codes":["KRW-BTC"]},{"type":"orderbook","codes":["KRW-ETH"]}]
- KRW-BTC 페어의 체결, KRW-ETH 페어의 호가, KRW-EOS 페어의 현재가 스트림 구독  
  \[{"ticket":"UNIQUE_TICKET"},{"type":"trade","codes":["KRW-BTC"]},{"type":"orderbook","codes":["KRW-ETH"]},{"type":"ticker", "codes":["KRW-EOS"]}]
