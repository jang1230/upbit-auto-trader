# 내 자산 (MyAsset)

내 자산 데이터를 WebSocket으로 수신하기 위한 요청 및 구독 데이터 예시를 제공합니다.

## 내 자산 실시간 스트림 전송 방식 안내

내 자산 데이터의 경우 실제 자산에 변동이 발생할 때만 해당 내용이 실시간 스트림으로 전송됩니다. 따라서 **연결 후 자산 변동이 발생하지 않는 경우 데이터 수신이 이루어지지 않는 것이 정상 동작**입니다. [WebSocket 사용 안내의 연결 유지 항목](ref:websocket-guide)을 참고하여 데이터 미전송시에도 연결이 유지되도록 클라이언트 사양 또는 구현을 확인하시기 바랍니다.

[block:html]
{
  "html": "  <div class=\"callout-section\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i>  내 자산 WebSocket 스트림 최초 이용시 주의사항\n      </div>\n    내 자산 유형의 WebSocket 스트림 최초 구독시 자산 변동 여부와 상관 없이 수분간 데이터 수신이 정상적으로 이루어지지 않을 수 있습니다. \n    계정 최초 1회 연결 이후 재연결 등을 통해 <b>데이터 수신을 반드시 확인하신 후 사용</b>하시기 바랍니다. \n    예를 들어, 2025년 5월 1일 00시 00분 최초 이용 시 자산 변동이 발생하더라도 00시 05분부터 스트림 데이터가 전송될 수 있습니다. 00시 10분에 재접속 시 최초 접속이 아니므로 자산 변동 발생 즉시 스트림을 수신할 수 있습니다.\n  </div>"
}
[/block]


<br />

## Request 메세지 형식

내 자산 데이터 수신을 요청하기 위해서는 WebSocket 연결 이후 아래 구조의 JSON Object를 생성한 뒤 요청 메세지의 Data Type Object로 포함하여 전송해야 합니다. Ticket, Format 필드를 포함한 전체 WebSocket 데이터 요청 메세지 명세는 [WebSocket 사용 안내](ref:websocket-guide) 문서를 참고해주세요.

[block:html]
{
  "html": " <div class=\"callout-section callout-section--danger\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i> 내 자산 타입 데이터 구독 요청은 페어 코드(\"codes\") 파라미터를 지원하지 않습니다.\n      </div>\n    다른 데이터 항목 구독 요청과 달리 내 자산 타입 데이터 구독 요청에 페어 코드 파라미터를 포함하는 경우 \"WRONG_FORMAT\" 에러가 발생하오니 사용에 주의바랍니다.\n  </div>\n\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th>타입</th>\n      <th>내용</th>\n      <th>필수 여부</th>\n      <th>기본 값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">type</td>\n      <td>String</td>\n      <td>데이터 타입<br><code>myAsset</td>\n      <td>Required</td>\n      <td></td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json format - "DEFAULT"
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "myAsset"
  }
]
```
```json format - "JSON_LIST"
[
  {
    "ticket": "0e66c0ac-7e13-43ef-91fb-2a87c2956c49"
  },
  {
    "type": "myAsset"
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
  "html": "\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>필드명</th>\n      <th><div style=\"width:65px\">축약형</div></th>\n      <th><div style=\"width:180px\">내용</div></th>\n      <th>타입</th>\n      <th>값</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td>type</td>\n      <td>ty</td>\n      <td>타입</td>\n      <td>String</td>\n      <td><code>myAsset</code></td>\n    </tr>\n    <tr>\n      <td>asset_uuid</td>\n      <td>astuid</td>\n      <td>자산 고유 식별자</td>\n      <td>String</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>assets</td>\n      <td>ast</td>\n      <td>자산 목록</td>\n      <td>List of Objects</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>assets.currency</td>\n      <td>ast.cu</td>\n      <td>화폐 코드</td>\n      <td>String</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>assets.balance</td>\n      <td>ast.b</td>\n      <td>주문가능 수량</td>\n      <td>Double</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>assets.locked</td>\n      <td>ast.l</td>\n      <td>주문 중 묶여있는 수량</td>\n      <td>Double</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>asset_timestamp</td>\n      <td>asttms</td>\n      <td>자산 타임스탬프 (ms)</td>\n      <td>Long</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>timestamp</td>\n      <td>tms</td>\n      <td>타임스탬프 (ms)</td>\n      <td>Long</td>\n      <td></td>\n    </tr>\n    <tr>\n      <td>stream_type</td>\n      <td>st</td>\n      <td>스트림 타입</td>\n      <td>String</td>\n      <td><code>REALTIME</code> : 실시간</td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


### 예시

```json format - "DEFAULT"
{
    "type": "myAsset",
    "asset_uuid": "e635f223-1609-4969-8fb6-4376937baad6",
    "assets": [
      {
        "currency": "KRW",
        "balance": 1386929.37231066771348207123,
        "locked": 10329.670127489597585685
      }
    ],
    "asset_timestamp": 1710146517259,
    "timestamp": 1710146517267,
    "stream_type": "REALTIME"
  }
```
```json format - "JSON_LIST"
[
  {
    "type": "myAsset",
    "asset_uuid": "e635f223-1609-4969-8fb6-4376937baad6",
    "assets": [
      {
        "currency": "KRW",
        "balance": 1386929.37231066771348207123,
        "locked": 10329.670127489597585685
      }
    ],
    "asset_timestamp": 1710146517259,
    "timestamp": 1710146517267,
    "stream_type": "REALTIME"
  }
]
```
