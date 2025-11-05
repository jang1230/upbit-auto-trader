# REST API 사용 및 에러 안내

업비트 REST API 사용을 위한 요청, 인증, 에러 및 gzip 지원 관련 안내입니다.

## Endpoint

> <https://api.upbit.com/v1>

[block:html]
{
  "html": "<div class=\"callout-section\" style=\"border: 1px solid #f2b9b9; background: #fff8f8; padding: 1rem 1.25rem; border-radius: 8px;\">\n  <div class=\"callout-title\" style=\"display: flex; align-items: center; font-weight: 700; color: #c62828; margin-bottom: 0.75rem;\">\n    <i class=\"fa-solid fa-circle-exclamation\" style=\"color: #e53935; margin-right: 0.5rem;\"></i>\n    TLS 1.2 이상 업그레이드 필요\n  </div>\n  <div style=\"color: #333; line-height: 1.7; font-size: 0.95rem;\">\n    업비트 <strong>Open API</strong>는 회원님의 정보를 안전하게 보호하기 위해 <strong>TLS 1.2</strong> 이상 버전만 지원합니다.<br>\n    <strong>TLS 1.2</strong> 미만 버전은 더 이상 지원되지 않으므로, 최소 <strong>TLS 1.2</strong> 이상으로 업그레이드해 주시기 바랍니다.\n  </div>\n  <ul style=\"margin-top: 0.75rem; padding-left: 1.25rem; color: #555; font-size: 0.9rem;\">\n    <li><strong>TLS 1.2</strong> (최소 지원 버전)</li>\n    <li><strong>TLS 1.3</strong> (권장 버전)</li>\n  </ul>\n</div>\n"
}
[/block]


<br />

## Content Type

업비트 REST API는 `application/json` Content Type을 지원합니다. 특히 POST 요청의 경우, 본문(Body)을 JSON 형식으로 요청해야 하며 아래 헤더를 함께 지정하여 주시기 바랍니다.

> Content-Type: application/json; charset=utf-8

<FormNotSupported />

<br />

## 인증

인증이 필요한 Exchange API 요청 시 [인증](ref:auth) 가이드를 참고하여 생성한 JWT 토큰을 `Authorization` 헤더에 반드시 포함하여 요청해야 합니다. 업비트 REST API는 Bearer 인증을 지원하며, 아래와 같은 형식으로 입력합니다.

> Authorization: Bearer eyJhb...d8sTw

<br />

## 요청 수 제한

REST API 요청 수 제한 정책은 [요청 수 제한(Rate Limits)](ref:rate-limits)문서를 참조하시기 바랍니다.

<br />

## 응답 상태 코드 및 에러 안내

업비트 REST API 응답으로 반환되는 HTTP 상태 코드 목록과 각 코드의 의미는 아래와 같습니다. 

[block:html]
{
  "html": "<style>\nth.max-width {\n  max-width: 80px;\n  overflow: hidden;\n  text-overflow: ellipsis;\n  }\nth.min-width {\n  min-width: 150px;\n  overflow: hidden;\n  text-overflow: ellipsis;\n  }\n.custom-table {\n  table-layout: fixed;\n  width: 100%;\n}\n\n</style>\n\n<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>HTTP Status Code</th>\n      <th class=\"max-width\">관련 에러 코드</th>\n      <th class=\"min-width\">발생 이유</th>\n      <th>에러 해결 방법</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">200 OK</td>\n      <td>-</td>\n      <td>정상 응답</td>\n      <td>-</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">201 Created</td>\n      <td>-</td>\n      <td>요청으로 인한<br>생성 완료</td>\n      <td>-</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\" rowspan=\"5\">400 Bad Request</td>\n      <td><code>create_ask_error</code>,<br><code>create_bid_error</code></td>\n      <td>주문 요청 정보가 올바르지 않습니다.</td>\n      <td>시장가 주문임에도 가격을 입력하는 경우 발생할 수 있습니다. 주문 생성 문서를 참고해주세요.</td>\n    </tr>\n    <tr>\n      <td><code>insufficient_funds_ask</code>,<br><code>insufficient_funds_bid</code></td>\n      <td>매수/매도 가능<br>잔고가 부족합니다.</td>\n      <td>잔고를 확인해주세요.</td>\n    </tr>\n    <tr>\n      <td><code>under_min_total_ask</code>,<br><code>under_min_total_bid</code></td>\n      <td>최소 주문 금액에<br>미달합니다.</td>\n      <td>페어별 최소 주문 금액 확인 후 재요청해주세요.</td>\n    </tr>\n    <tr>\n      <td><code>withdraw_address<br>_not_registered</code></td>\n      <td>허용되지 않은<br>출금 주소입니다.</td>\n      <td>등록된 출금 주소 목록에 포함되어 있는지 확인해주세요.</td>\n    </tr>\n    <tr>\n      <td><code>validation_error</code></td>\n      <td>잘못된<br>API 요청입니다.</td>\n      <td>필수 파라미터 누락<br>여부를 확인해주세요.</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\" rowspan=\"7\">401 Unauthorized</td>\n      <td><code>invalid_query_payload</code></td>\n      <td>JWT 페이로드가<br>올바르지 않습니다.</td>\n      <td><a href=\"auth\">인증</a> 가이드 문서를 참고하여 서명이 올바르게 생성 되었는지 확인해주세요.</td>\n    </tr>\n    <tr>\n      <td><code>jwt_verification</code></td>\n      <td>JWT 검증에<br>실패했습니다.</td>\n      <td>토큰의 생성 및 서명 상태를 점검해주세요.</td>\n    </tr>\n    <tr>\n      <td><code>expired_access_key</code></td>\n      <td>API 키가<br>만료되었습니다.</td>\n      <td>새로운 키를 발급받아 사용해주세요.</td>\n    </tr>\n    <tr>\n      <td><code>nonce_used</code></td>\n      <td>이미 사용된<br>nonce 값입니다.</td>\n      <td>JWT에는 매 요청마다 새로운 nonce 값을 사용해야 합니다.</td>\n    </tr>\n    <tr>\n      <td><code>no_authorization_ip</code></td>\n      <td>등록되지 않은<br>IP입니다.</td>\n      <td>API 키 발급 시 등록한 IP 환경에서 호출 중인지 점검해주세요.</td>\n    </tr>\n\t\t<tr>\n      <td><code>no_authorization_token</code></td>\n      <td>인증 토큰이<br>누락되었습니다.</td>\n      <td>인증 헤더가 요청에 포함되었는지 확인해주세요.</td>\n    </tr>\n    <tr>\n      <td><code>out_of_scope</code></td>\n      <td>지원 범위를 벗어난<br>기능입니다.</td>\n      <td>API 키 발급 시 해당 기능을 포함했는지 확인해주세요.</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">404 Not Found</td>\n      <td>-</td>\n      <td>존재하지 않는<br>데이터에 접근</td>\n      <td>주문, 출금, 입금, 체결 등 요청 항목이 존재하지 않는 경우</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">418 I'm a teapot</td>\n      <td>-</td>\n      <td>과도한 요청으로<br>인해 거부되었습니다.</td>\n      <td>IP 차단 등으로 요청이 제한됩니다.</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">429 Too Many Requests</td>\n      <td>-</td>\n      <td>요청 제한을<br>초과했습니다.</td>\n      <td>API 호출 한도를 초과했습니다.</td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">500 Internal Server Error</td>\n      <td>-</td>\n      <td>서버 내부 오류</td>\n      <td>서비스 점검 또는 시스템 오류로 인한 처리 불가</td>\n    </tr>\n  </tbody>\n</table>"
}
[/block]


<br />

에러 발생 시, 응답은 다음과 같은 JSON 형식으로 반환됩니다. `name` 필드는 해당 에러의 코드를, `message` 필드는 오류와 관련된 메세지를 반환합니다. Quotation API는 정수 형식의 `name` 필드를, Exchange API는 문자열 형식의 `name` 필드를 반환합니다. 각 API 별 오류 예시는 API Reference 문서 우측 하단 응답 예시 영역을 참고하시기 바랍니다. 

```json Quotation API Error Response
{
  "error": {
    "name": 400,
    "message": "ERROR_MESSAGE"
  }
}
```
```json Exchange API Error Response
{
  "error": {
    "name": "ERRPR_CODE",
    "message": "ERROR_MESSAGE"
  }
}
```

<br />

## 인코딩

GET 또는 DELETE API에 대해 쿼리 파라미터를 포함한 요청을 전송하는 경우 모든 쿼리 파라미터를 URL 인코딩 한 후 요청해야 합니다. 인코딩이 정상적으로 이루어지지 않은 요청에 대해 응답으로 400 `Invalid parameter` 에러가 발생할 수 있습니다. 단, Exchange API의 파라미터 중 배열 형식의 파라미터가 이름에 \[]를 포함하고 있는 경우, '[',']' 문자는 인코딩 대상에서 제외합니다. 

<URLEncoding />

<br />

## gzip 응답 지원

인코딩 옵션을 `gzip`으로 요청하여 REST API 응답을 gzip 압축된 형태로 수신할 수 있습니다. gzip 형식으로 요청 시 API를 통해 주고 받는 데이터 크기를 줄여 트래픽 비용 및 응답 시간을 절감할 수 있습니다. gzip 인코딩은 **시세(Quotation) API만 지원**합니다. gzip 옵션 사용 시 아래와 같이 헤더를 지정합니다.

> Accept-Encoding: gzip

<br />

## API Reference 예제 코드 안내

보다 쉬운 API 사용을 위해 각 API Reference 우측 상단에서 해당 API 호출을 위한 예제 코드를 제공합니다. Shell(cURL), Python, Java, Node.js의 네가지 도구/언어 예시를 제공하며 Java와 Node.js는 사용하는 HTTP 클라이언트 라이브러리에 따라 아래와 같이 세분화하여 제공합니다. (코드 박스 상단 아래 화살표를 클릭하여 라이브러리별 예제를 변경할 수 있습니다.)

- **Java** - AsyncHttp, java.net.http, OkHttp, Unirest
- **Node.js** - Axios, fetch, https

문서의 요청 쿼리 파라미터 및 본문(Body) 영역에서 각 파라미터의 값을 예시값 또는 임의의 값으로 입력할 수 있습니다. 입력된 값에 따라 우측 예제 코드 또한 실시간으로 변경됩니다. 

거래 및 자산 관리(Exchange) API의 경우 인증 토큰을 생성하는 부분은 예제 코드에서 제외되어 있습니다. [인증](ref:auth)문서의 인증 토큰 생성 예제 코드를 참고하여 실제 연동 시에는 반드시 인증 토큰을 요청에 포함하도록 구현해주시기 바랍니다.
