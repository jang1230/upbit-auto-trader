# 호가 (Orderbook)

호가 데이터를 WebSocket으로 수신하기 위한 요청 및 구독 데이터 예시를 제공합니다.

## 호가 모아보기 (level)

원화마켓(KRW)에서만 지원하는 기능으로, 지정한 단위로 ask/bid price와 size를 모아(group) 조회할 수 있습니다. 숫자 형식의 String으로 요청합니다. 

[예시]\: KRW-BTC 종목에 대해 level=100000으로 요청시 10만원(KRW) 단위로 ask/bid price가 반환되며, 각 금액대 내에 포진된 매수/매도 주문량의 합산이 size로 반환됩니다.

종목별 호가 단위에 따라 지원하는 모아보기 단위가 다릅니다. 지원하는 모아보기 단위 정보는 [마켓별 주문 정책](doc:faq-market-policy) 문서 또는 [호가 정책 조회](ref:list-orderbook-instruments) API 응답을 참고하여 사용해주시기 바랍니다. 별도로 지정하지 않는 경우 기본 단위인 0으로 지정됩니다. 미지원 단위를 지정하여 요청하는 경우 데이터가 수신되지 않을 수 있으므로 호출 전 지원하는 단위를 반드시 확인해주시기 바랍니다.

<br />

## 호가 조회 단위(개수) 지정

조회할 호가 쌍의 개수 단위(unit)를 지정하고자 하는 경우 기본 요청과 같이 `codes` 필드에 조회할 페어 코드를 입력하되, 페어 코드 뒤에 반점(.)과 조회 단위를 명시하여 지정합니다. 지원하는 호가 조회 단위는 1, 5, 15, 30입니다. 별도의 요청이 없는 경우 기본적으로 30개의 호가 쌍(매수/매도)이 반환됩니다. 

> {pair_code}.{unit}
>
> 예시: KRW-BTC.15

<br />

## Request 메세지 형식

호가 데이터 수신을 요청하기 위해서는 WebSocket 연결 이후 아래 구조의 JSON Object를 생성한 뒤 요청 메세지의 Data Type Object로 포함하여 전송해야 합니다. Ticket, Format 필드를 포함한 전체 WebSocket 데이터 요청 메세지 명세는 [WebSocket 사용 안내](ref:websocket-guide) 문서를 참고해주세요.

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>타입</th>\n      <th>내용</th>\n      <th>필수 여부</th>\n      <th>기본 값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">type</td>\n      <td>String</td>\n      <td><code>orderbook</code></td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">codes</td>\n      <td>List:String</td>\n      <td>수신하고자 하는 페어 목록.<br>반드시 대문자로 요청해야 합니다.</td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n\t\t<tr>\n      <td class=\"code-col\">level</td>\n      <td>Double</td>\n      <td>모아보기 단위</td>\n      <td>Optional</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">is_only_snapshot</td>\n      <td>Boolean</td>\n      <td>스냅샷 시세만 제공</td>\n      <td>Optional</td>\n      <td><code>false</code></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">is_only_realtime</td>\n      <td>Boolean</td>\n      <td>실시간 시세만 제공</td>\n      <td>Optional</td>\n      <td><code>false</code></td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json format - "DEFAULT"
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "orderbook",
    "codes": ["KRW-BTC","KRW-ETH.5"],
    "level": 10000
  },
  {
    "format": "DEFAULT"
  }
]

// 또는 각 페어별로 모아보기 단위를 지정하고자 하는 경우

[  
    {  
        "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"  
    },  
    {  
        "type": "orderbook",  
        "codes": ["KRW-BTC"],  
        "level": 10000  
    },  
    {  
        "type": "orderbook",  
        "codes": ["KRW-BTT"],  
        "level": 0  
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

***

## 구독 데이터 명세

현재가 스냅샷 또는 실시간 스트림 데이터는 아래와 같이 반환됩니다. 

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>축약형</th>\n      <th>내용</th>\n      <th>타입</th>\n      <th>값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr><td class=\"code-col\">type</td><td>ty</td><td>타입</td><td>String</td><td><code>orderbook</code></td></tr>\n    <tr><td class=\"code-col\">code</td><td>cd</td><td>페어 코드</td><td>String</td><td><code>KRW-BTC</code></td></tr>\n    <tr><td class=\"code-col\">total_ask_size</td><td>tas</td><td>호가 매도 총 잔량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">total_bid_size</td><td>tbs</td><td>호가 매수 총 잔량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">orderbook_units</td><td>obu</td><td>호가</td><td>List of Objects</td><td></td></tr>\n    <tr><td class=\"code-col\">orderbook_units.ask_price</td><td>obu.ap</td><td>매도 호가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">orderbook_units.bid_price</td><td>obu.bp</td><td>매수 호가</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">orderbook_units.ask_size</td><td>obu.as</td><td>매도 잔량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">orderbook_units.bid_size</td><td>obu.bs</td><td>매수 잔량</td><td>Double</td><td></td></tr>\n    <tr><td class=\"code-col\">timestamp</td><td>tms</td><td>타임스탬프 (ms)</td><td>Long</td><td></td></tr>\n    <tr><td class=\"code-col\">level</td><td>lv</td><td>호가 모아보기 단위 (default: 0, 기본 호가단위)<br>*호가 모아보기 기능은 원화마켓(KRW)에서만 지원하므로 BTC, USDT 마켓의 경우 0만 존재합니다.<br></td><td>Double</td><td>모아보기 단위</td></tr>\n    <tr><td class=\"code-col\">stream_type</td><td>st</td><td>스트림 타입</td><td>String</td><td><code>SNAPSHOT</code><br>: 스냅샷<br><code>REALTIME</code><br>: 실시간</td></tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json format - "DEFAULT"
{
  "type": "orderbook",
  "code": "KRW-BTC",
  "timestamp": 1746601573804,
  "total_ask_size": 4.79158413,
  "total_bid_size": 2.65609625,
  "orderbook_units": [
    {
      "ask_price": 137002000,
      "bid_price": 137001000,
      "ask_size": 0.10623869,
      "bid_size": 0.03656812
    },
    {
      "ask_price": 137023000,
      "bid_price": 137000000,
      "ask_size": 0.06144079,
      "bid_size": 0.33543284
    },
    {
      "ask_price": 137050000,
      "bid_price": 136999000,
      "ask_size": 0.0055433,
      "bid_size": 0.00104379
    },
    {
      "ask_price": 137052000,
      "bid_price": 136980000,
      "ask_size": 0.00452071,
      "bid_size": 0.32709281
    },
    {
      "ask_price": 137053000,
      "bid_price": 136978000,
      "ask_size": 0.12781487,
      "bid_size": 0.00875219
    },
    {
      "ask_price": 137054000,
      "bid_price": 136976000,
      "ask_size": 0.03777519,
      "bid_size": 0.01867952
    },
    {
      "ask_price": 137055000,
      "bid_price": 136975000,
      "ask_size": 0.06073315,
      "bid_size": 0.04379996
    },
    {
      "ask_price": 137056000,
      "bid_price": 136971000,
      "ask_size": 0.00372511,
      "bid_size": 0.00036504
    },
    {
      "ask_price": 137060000,
      "bid_price": 136970000,
      "ask_size": 0.00308733,
      "bid_size": 0.15547631
    },
    {
      "ask_price": 137065000,
      "bid_price": 136969000,
      "ask_size": 0.04218546,
      "bid_size": 0.00036504
    },
    {
      "ask_price": 137070000,
      "bid_price": 136942000,
      "ask_size": 0.01172394,
      "bid_size": 0.00021907
    },
    {
      "ask_price": 137071000,
      "bid_price": 136931000,
      "ask_size": 0.001,
      "bid_size": 0.00260654
    },
    {
      "ask_price": 137076000,
      "bid_price": 136930000,
      "ask_size": 0.00120371,
      "bid_size": 0.00014606
    },
    {
      "ask_price": 137079000,
      "bid_price": 136924000,
      "ask_size": 0.00007303,
      "bid_size": 0.00004381
    },
    {
      "ask_price": 137080000,
      "bid_price": 136911000,
      "ask_size": 0.01051428,
      "bid_size": 0.09531
    },
    {
      "ask_price": 137084000,
      "bid_price": 136910000,
      "ask_size": 0.00004,
      "bid_size": 0.01354743
    },
    {
      "ask_price": 137086000,
      "bid_price": 136906000,
      "ask_size": 0.00643152,
      "bid_size": 0.00519774
    },
    {
      "ask_price": 137091000,
      "bid_price": 136902000,
      "ask_size": 0.0105,
      "bid_size": 0.00485
    },
    {
      "ask_price": 137098000,
      "bid_price": 136898000,
      "ask_size": 4.0534502,
      "bid_size": 0.01017513
    },
    {
      "ask_price": 137099000,
      "bid_price": 136897000,
      "ask_size": 0.00995,
      "bid_size": 0.0002599
    },
    {
      "ask_price": 137100000,
      "bid_price": 136895000,
      "ask_size": 0.14272057,
      "bid_size": 0.01245
    },
    {
      "ask_price": 137104000,
      "bid_price": 136893000,
      "ask_size": 0.0012294,
      "bid_size": 0.01468299
    },
    {
      "ask_price": 137109000,
      "bid_price": 136892000,
      "ask_size": 0.009,
      "bid_size": 0.0042
    },
    {
      "ask_price": 137112000,
      "bid_price": 136890000,
      "ask_size": 0.03154608,
      "bid_size": 0.00385
    },
    {
      "ask_price": 137113000,
      "bid_price": 136881000,
      "ask_size": 0.00136546,
      "bid_size": 0.00080361
    },
    {
      "ask_price": 137120000,
      "bid_price": 136880000,
      "ask_size": 0.00325241,
      "bid_size": 0.01460539
    },
    {
      "ask_price": 137123000,
      "bid_price": 136879000,
      "ask_size": 0.02020901,
      "bid_size": 1.203
    },
    {
      "ask_price": 137124000,
      "bid_price": 136874000,
      "ask_size": 0.00734507,
      "bid_size": 0.00791911
    },
    {
      "ask_price": 137135000,
      "bid_price": 136868000,
      "ask_size": 0.0002192,
      "bid_size": 0.01735219
    },
    {
      "ask_price": 137137000,
      "bid_price": 136861000,
      "ask_size": 0.01674565,
      "bid_size": 0.31730166
    }
  ],
  "stream_type": "SNAPSHOT",
  "level": 0
}
```
```json format  "SIMPLE_LIST"
[
  {
    "ty": "orderbook",
    "cd": "KRW-BTC",
    "tms": 1751855921432,
    "tas": 17.12835169,
    "tbs": 4.81969018,
    "obu": [
      {
        "ap": 148880000,
        "bp": 148830000,
        "as": 0.37765316,
        "bs": 0.34809059
      },
      {
        "ap": 148890000,
        "bp": 148820000,
        "as": 0.64120607,
        "bs": 0.02744065
      },
      {
        "ap": 148900000,
        "bp": 148810000,
        "as": 0.70085443,
        "bs": 0.04667566
...
    "lv": 10000
  }
]
```
