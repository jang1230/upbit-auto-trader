# 구독 중인 스트림 목록 조회

WebSocket 연결을 통해 구독중인 데이터 스트림 항목을 확인할 수 있습니다.

## Method

"type" 필드를 포함하는 데이터 구독 요청 메세지와 달리, 구독 중인 스트림 목록 조회 요청 메세지는 "method"필드를 포함하며 Operation 메세지의 성격을 가집니다. 데이터 구독 요청 메세지와 동일하게 요청 JSON Array에 Ticket 필드와 Format 필드와 함 Method 필드를 넣어 요청합니다. 

[block:html]
{
  "html": "  <div class=\"callout-section callout-section--danger\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i> Format 필드 지정 시 주의사항\n      </div>\n      구독 중인 스트림 목록 조회 요청시 Format 필드는 실제 각 데이터를 구독 요청할 때 사용한 Format 필드와 동일한 형식으로 요청히시기 바랍니다. \n      다른 형식으로 요청하는 경우, 기존에 구독중이던 데이터 스트림의 요청 형식도 변경되므로 주의하십시오.\n      예를 들어, SIMPLE 형식으로 실시간 스트림을 수신하다가 본 요청을 DEFAULT 형식으로 요청할 경우, 구독중이던 실시간 스트림 또한 DEFAULT 형식으로 수신됩니다.\n  </div>"
}
[/block]


<br />

## 요청 수 제한 안내

구독 중인 스트림 목록 조회 요청도 요청 수 제한 대상에 포함됩니다.

<br />

## Request 메세지 형식

현재 구독 중인 스트림 목록을 조회하기 위해서는 사용중인 WebSocket 연결로 아래 구조의 JSON Object를 생성한 뒤 요청 메세지의 Data Type Object에 포함하여 전송해야 합니다. Ticket, Format 필드를 포함 전체 WebSocket 데이터 요청 메세지 명세는 [WebSocket 사용 안내](ref:websocket-guide) 문서를 참고해주세요.

[block:html]
{
  "html": "\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>타입</th>\n      <th>내용</th>\n      <th>필수 여부</th>\n      <th>기본 값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">method</td>\n      <td>String</td>\n      <td>요청 메서드<br><code>LIST_SUBSCRIPTIONS</code></td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "method": "LIST_SUBSCRIPTIONS"
  }
]
```

***

<br />

## 응답 명세

[block:html]
{
  "html": "\n\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th><div style=\"width:65px\">축약형</div></th>\n      <th><div style=\"width:180px\">내용</div></th>\n      <th>타입</th>\n      <th>값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td>method</td>\n      <td>mthd</td>\n      <td>요청 메서드</td>\n      <td>String</td>\n      <td><code>LIST_SUBSCRIPTIONS</code></td>\n    </tr>\n    <tr>\n      <td>result</td>\n      <td>rslt</td>\n      <td>요청 결과</td>\n      <td>List of Objects</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>result.type</td>\n      <td>rslt.ty</td>\n      <td>데이터 타입</td>\n      <td>String</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>result.codes</td>\n      <td>rslt.cds</td>\n      <td>페어 코드 목록</td>\n      <td>List of String</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>result.level</td>\n      <td>rslt.lv</td>\n      <td>호가 모아보기 단위</td>\n      <td>Double</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>ticket</td>\n      <td>tckt</td>\n      <td>요청자를 식별할 수 있는 값</td>\n      <td>Long</td>\n      <td></td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


<br />

### 예시

```json Quotation 실시간 스트림 내역
{
  "method": "LIST_SUBSCRIPTIONS",
  "result": [
    {
      "type": "ticker",
      "codes": ["KRW-BTC", "KRW-ETH"]
    },
    {
      "type": "orderbook",
      "codes": ["KRW-BTC", "KRW-ETH"],
      "level": 0
    }
  ],
  "ticket": "unique uuid"
}

```
```json Exchange 실시간 스트림 내역
{
  "method": "LIST_SUBSCRIPTIONS",
  "result": [
    {
      "type": "myAsset"
    },
    {
      "type": "myOrder",
      "codes": ["KRW-BTC", "KRW-ETH"]
    }
  ],
  "ticket": "unique uuid"
}

```
