# 취소 후 재주문

한 번의 요청으로 기존 주문을 취소하고 신규 주문을 생성합니다.

### 재주문 시 변경 가능 항목 및 제한 사항

- 신규 주문은 기존 주문과 **동일한 페어, 동일한 주문 방향에 대해서만 생성 가능**하며 변경 불가합니다. 
- 선택적으로 신규 identifer(`new_identifier`)를 설정할 수 있으나, 취소하고자 하는 기존 주문에 사용한 identifier 값은 **재사용할 수 없습니다. **
- 주문 유형(`new_ord_type`), 수량(`new_volume`), 금액(`new_price`), 자전거래 체결 방지 모드(`new_smp_type`), 주문 체결 옵션(`new_time_in_force`)은 변경할 수 있습니다.
- 기존 주문이 부분 체결 주문인 경우 수량(new_volume) 파라미터에 **"remain_only"**를 요청하여 신규 주문 수량을 기존 주문 잔량으로 쉽게 지정할 수 있습니다.

<br />

### 신규 주문 유형에 따른 필수 파라미터

신규 주문 유형(new_ord_type)에 따른 필수 파라미터는 다음과 같습니다. 

[block:html]
{
  "html": "<table class=\"custom-table\">\n    <thead>\n      <tr>\n        <th>주문 유형</th>\n        <th>필수 필드</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td class=\"code-col\">지정가(limit)</td>\n        <td><code>new_volume</code>, <code>new_price</code><td>\n      </tr>\n      <tr>\n        <td class=\"code-col\">시장가 매수(price)</td>\n        <td><code>new_price</code></td>\n      </tr>\n      <tr>\n        <td class=\"code-col\">시장가 매도(market)</td>\n        <td><code>new_volume</code></td>\n      </tr>\n      <tr>\n        <td class=\"code-col\">최유리 지정가(best) 매수</td>\n        <td><code>new_price</code>, <code>new_time_in_force</code></td>\n      </tr>\n      <tr>\n        <td class=\"code-col\">최유리 지정가(best) 매도</td>\n        <td><code>new_volume</code>, <code>new_time_in_force</code></td>\n      </tr>\n    </tbody>\n  </table>"
}
[/block]


자세한 주문 유형 별 파라미터 예시는 [주문 생성](ref:new-order) 문서를 참고해주시기 바랍니다.

<br />

### 신규 주문 생성 조건

본 API 요청시 신규 주문은 반드시 이전 주문의 취소가 완료된 이후 생성됩니다. API가 성공적으로 요청되더라도, 기존 주문의 취소 처리가 완료되기 전에 전량 체결되어 취소가 불가능한 경우 신규 주문은 생성되지 않습니다.

[block:html]
{
  "html": "\n<div class=\"callout-section\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i>  취소 요청 시 prev_order_uuid 또는 prev_order_identifier를 반드시 포함해야 합니다.\n      </div>\n    두 파라미터 모두 선택(Optional) 파라미터이지만, 취소 대상 주문 지정을 위해 반드시 하나의 파라미터를 포함해야 합니다. \n  </div>\n"
}
[/block]


[block:html]
{
  "html": "<div class=\"callout-section callout-section--danger\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i> POST API에 대한 Form 방식 요청은 2022년 3월 1일부로 지원이 종료되었습니다.\n      </div>\n    Form 방식 지원 종료에 따라 Urlencoded Form 방식으로 전송하는 POST 요청에 대한 정상적인 동작을 보장하지 않습니다. <b>반드시 JSON 형식으로 요청 본문(Body)을 전송</b>해주시기 바랍니다.\n  </div>"
}
[/block]


[block:html]
{
  "html": "<div class=\"accordion-changelog\">\n    <input type=\"checkbox\" id=\"api-changelog\">\n    <label for=\"api-changelog\">\n        <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Revision History <i class=\"fa-solid fa-angle-right\"></i> </div>\n    </label>\n\n    <div class=\"accordion-changelog-content\">\n        <table class=\"custom-table\">\n            <thead>\n                <tr>\n                    <th>반영 버전</th>\n                    <th>반영 일자</th>\n                    <th>변경 사항</th>\n                </tr>\n            </thead>\n         \t\t <tbody>\n\t\t\t\t\t\t\t\t<tr>\n                    <td class=\"code-col\">v1.5.8</td>\n                    <td class=\"code-col\">2025-07-02</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/post_only\"><code>Post Only</code> 주문 옵션 신규 지원</a></td>\n              \t</tr>\n                <tr>\n                    <td class=\"code-col\">v1.5.8</td>\n                    <td>2025-07-02</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/smp\"> 자전거래 체결 방지(SMP) 기능<br>신규 지원에 따른 필드 추가<br><code>smp_type</code>,<code>prevented_volume</code>,<code>prevented_locked</code></a></td>\n               \t</tr>\n\t\t\t\t\t\t\t\t<tr>\n                    <td>-</td>\n                    <td>2025-02-05 </td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/cancel_and_new_oreder\"> \"취소 후 재주문\" API 신규 지원</a></td>\n                </tr>\n\n            </tbody>\n        </table>\n    </div>\n</div>\n\n<div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Rate Limit</div>\n<div class=\"box-rate-limit\">\n  초당 최대 8회 호출할 수 있습니다. 계정단위로 측정되며 [주문 생성 그룹] 내에서 요청 가능 횟수를 공유합니다.\n</div>\n  <br>\n  <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">API Key Permission</div>\n  <div class=\"box-rate-limit\">\n    <a href=\"auth\">인증</a>이 필요한 API로, [주문하기] 권한이 설정된 API Key를 사용해야 합니다. <br>\n    권한 오류(out_of_scope) 오류가 발생한다면, <a href=\"https://upbit.com/mypage/open_api_management\">API Key 관리 메뉴</a>에서 권한 설정을 확인해주세요.\n  </div>"
}
[/block]

# OpenAPI definition
```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "EXCHANGE API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://api.upbit.com/v1"
    }
  ],
  "x-readme": {
    "explorer-enabled": false,
    "samples-languages": [
      "shell",
      "python",
      "java",
      "node"
    ],
    "proxy-enabled": true
  },
  "paths": {
    "/orders/cancel_and_new": {
      "post": {
        "operationId": "cancel-and-new-order",
        "summary": "취소 후 재주문",
        "tags": [
          "주문(Order)"
        ],
        "x-readme": {
          "code-samples": [
            {
              "language": "curl",
              "code": "curl --request POST \\\n  --url 'https://api.upbit.com/v1/orders/cancel_and_new' \\\n  --header 'Authorization: Bearer {JWT_TOKEN}' \\\n  --header 'Accept: application/json' \\\n  --header 'Content-Type: application/json' \\\n  --data '\n{\n\"prev_order_uuid\": \"ad217e24-ed02-469c-9b30-c08dbbda6908\",\n\"new_ord_type\": \"limit\",\n\"new_price\": \"100000000\",\n\"new_volume\": \"1\"\n}\n'\n"
            },
            {
              "language": "python",
              "install": "pip install requests pyjwt python-dotenv",
              "code": "import os\nimport uuid\nimport hashlib\nimport jwt\nimport requests\nfrom urllib.parse import unquote, urlencode\nfrom dotenv import load_dotenv\n\nload_dotenv()\n\nBASE_URL = \"https://api.upbit.com\"\nPATH = \"/v1/orders/cancel_and_new\"\n\nACCESS_KEY = os.environ[\"UPBIT_OPEN_API_ACCESS_KEY\"]\nSECRET_KEY = os.environ[\"UPBIT_OPEN_API_SECRET_KEY\"]\n\nparams = {\n  \"prev_order_uuid\": \"ad217e24-ed02-469c-9b30-c08dbbda6908\",\n  \"new_ord_type\": \"limit\",\n  \"new_price\": \"100000000\",\n  \"new_volume\": \"1\",\n}\nquery_string = unquote(urlencode(params, doseq=True)).encode(\"utf-8\")\n\nm = hashlib.sha512()\nm.update(query_string)\nquery_hash = m.hexdigest()\n\npayload = {\n  \"access_key\": ACCESS_KEY,\n  \"nonce\": str(uuid.uuid4()),\n  \"query_hash\": query_hash,\n  \"query_hash_alg\": \"SHA512\",\n}\n\njwt_token = jwt.encode(payload, SECRET_KEY, algorithm=\"HS256\")\n\nheaders = {\n  \"Authorization\": f\"Bearer {jwt_token}\",\n  \"Accept\": \"application/json\",\n}\n\nres = requests.post(f\"{BASE_URL}{PATH}\", headers=headers, json=params)\nprint(res.json())\n"
            },
            {
              "language": "node",
              "name": "Axios",
              "install": "npm install axios jsonwebtoken uuid",
              "code": "const axios = require(\"axios\");\nconst crypto = require(\"crypto\");\nconst { sign } = require(\"jsonwebtoken\");\nconst { v4: uuidv4 } = require(\"uuid\");\nrequire(\"dotenv\").config();\n\nconst baseURL = \"https://api.upbit.com\";\nconst path = \"/v1/orders/cancel_and_new\";\n\nconst ACCESS_KEY = process.env.UPBIT_OPEN_API_ACCESS_KEY;\nconst SECRET_KEY = process.env.UPBIT_OPEN_API_SECRET_KEY;\n\nconst params = {\n  prev_order_uuid: \"ad217e24-ed02-469c-9b30-c08dbbda6908\",\n  new_ord_type: \"limit\",\n  new_price: \"100000000\",\n  new_volume: \"1\",\n};\n\nconst queryString = new URLSearchParams(params).toString();\n\nconst queryHash = crypto\n  .createHash(\"sha512\")\n  .update(queryString, \"utf-8\")\n  .digest(\"hex\");\n\nconst payload = {\n  access_key: ACCESS_KEY,\n  nonce: uuidv4(),\n  query_hash: queryHash,\n  query_hash_alg: \"SHA512\",\n};\n\nconst jwtToken = sign(payload, SECRET_KEY);\n\nconst options = {\n  method: \"POST\",\n  url: `${baseURL}${path}`,\n  headers: {\n    Authorization: `Bearer ${jwtToken}`,\n    Accept: \"application/json\",\n  },\n  data: params,\n};\n\naxios\n  .request(options)\n  .then((response) => {\n    console.log(response.data);\n  })\n  .catch((error) => {\n    console.error(error.response ? error.response.data : error.message);\n  });\n"
            },
            {
              "language": "java",
              "code": "package main;\n\nimport com.auth0.jwt.JWT;\nimport com.auth0.jwt.algorithms.Algorithm;\nimport java.io.IOException;\nimport java.nio.charset.StandardCharsets;\nimport java.security.MessageDigest;\nimport java.security.NoSuchAlgorithmException;\nimport java.util.HashMap;\nimport java.util.Map;\nimport java.util.Objects;\nimport java.util.UUID;\nimport java.util.stream.Collectors;\nimport okhttp3.OkHttpClient;\nimport okhttp3.Request;\nimport okhttp3.RequestBody;\nimport okhttp3.Response;\nimport com.google.gson.Gson;\n\npublic class CancelAndNew {\n    private static final String BASE_URL = \"https://api.upbit.com\";\n    private static final String PATH = \"/v1/orders/cancel_and_new\";\n\n\n    public static void main(String[] args) throws NoSuchAlgorithmException, IOException {\n        String accessKey = System.getenv(\"UPBIT_OPEN_API_ACCESS_KEY\");\n        String secretKey = System.getenv(\"UPBIT_OPEN_API_SECRET_KEY\");\n\n        Map<String, String> params = new HashMap<>();\n        params.put(\"prev_order_uuid\", \"ad217e24-ed02-469c-9b30-c08dbbda6908\");\n        params.put(\"new_ord_type\", \"limit\");\n        params.put(\"new_price\", \"100000000\");\n        params.put(\"new_volume\", \"1\");\n        String queryString = params.entrySet().stream()\n            .map(e -> e.getKey() + \"=\" + String.valueOf(e.getValue()))\n            .collect(Collectors.joining(\"&\"));\n\n        MessageDigest md = MessageDigest.getInstance(\"SHA-512\");\n        md.update(queryString.getBytes(StandardCharsets.UTF_8));\n        StringBuilder sb = new StringBuilder();\n        for (byte b : md.digest()) {\n            sb.append(String.format(\"%02x\", b));\n        }\n        String queryHash = sb.toString();\n\n        Algorithm algorithm = Algorithm.HMAC512(secretKey.getBytes(StandardCharsets.UTF_8));\n        String jwtToken = JWT.create()\n            .withClaim(\"access_key\", accessKey)\n            .withClaim(\"nonce\", UUID.randomUUID().toString())\n            .withClaim(\"query_hash\", queryHash)\n            .withClaim(\"query_hash_alg\", \"SHA512\")\n            .sign(algorithm);\n\n        String authHeader = \"Bearer \" + jwtToken;\n\n        String jsonBody = new Gson().toJson(params);\n        OkHttpClient client = new OkHttpClient();\n        Request request = new Request.Builder()\n            .url(BASE_URL + PATH)\n            .post(RequestBody.create(jsonBody, okhttp3.MediaType.parse(\"application/json; charset=utf-8\")))\n            .addHeader(\"Content-Type\", \"application/json\")\n            .addHeader(\"Authorization\", authHeader)\n            .build();\n\n        try (Response response = client.newCall(request).execute()) {\n            System.out.println(response.code());\n            System.out.println(Objects.requireNonNull(response.body()).string());\n        }\n    }\n}\n"
            }
          ]
        },
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "required": [
                  "new_ord_type"
                ],
                "properties": {
                  "prev_order_uuid": {
                    "type": "string",
                    "description": "취소하고자 하는 주문의 유일식별자(UUID)",
                    "example": "9ca023a5-851b-4fec-9f0a-48cd83c2eaae"
                  },
                  "prev_order_identifier": {
                    "type": "string",
                    "description": "취소하고자 하는 주문의 클라이언트 지정 식별자",
                    "example": "9ca023a5-851b-4fec-9f0a-48cd83c2eaae"
                  },
                  "new_ord_type": {
                    "type": "string",
                    "description": "신규 주문의 주문 유형. \n생성하고자 하는 주문 유형에 따라 아래 값 중 하나를 입력합니다. \n\n* `limit`: 지정가 매수/매도 주문\n* `price`: 시장가 매수 주문\n* `market`: 시장가 매도 주문\n* `best`: 최유리 지정가 매수/매도 주문 (time_in_force 필드 설정 필수)\n",
                    "example": "limit"
                  },
                  "new_volume": {
                    "type": "string",
                    "description": "신규 주문 수량.\n매수 또는 매도하고자 하는 수량을 숫자 형식의 String으로 입력합니다. “remain_only”로 설정하는 경우 이전 주문 잔량을 신규 주문 수량으로 설정할 수 있습니다. \n\n다음 주문 유형에 대해 필수로 입력되어야 합니다.\n- 지정가 매수/매도(new_ord_type 필드가 “limit”인 경우)\n- 시장가 매도(new_ord_type 필드가 “market”인 경우)\n- 최유리 지정가 매도(이전 주문의 side 필드가 “ask”, new_ord_type 필드가 “best”인 경우)\n",
                    "example": "remain_only"
                  },
                  "new_price": {
                    "type": "string",
                    "description": "신규 주문 단가 또는 총액.\n디지털 자산 구매에 사용되는 통화(KRW,BTC,USDT)를 기준으로, 숫자 형식의 String으로 입력합니다.\n\n다음 주문 조건에 대해 필수로 입력합니다.\n- 지정가 매수/매도(new_ord_type 필드가 “limit”인 경우)\n- 시장가 매수(new_ord_type 필드가 “price”인 경우)\n- 최유리 지정가 매수(이전 주문의 side필드가 “bid”, new_ord_type 필드가 “best”인 경우)\n\nprice 필드는 주문 유형에 따라 다른 용도로 사용됩니다.\n- 지정가 주문시 매수/매도 호가로 사용됩니다.\n- 시장가 매수, 최유리 지정가 매수시 매수 총액을 설정하는 용도로 사용됩니다. 주문 시점의 시장가 또는 최유리 지정가로 price 총액을 채우는 수량만큼 매수 주문이 체결됩니다.\n",
                    "example": "1000"
                  },
                  "new_identifier": {
                    "type": "string",
                    "description": "신규 주문의 클라이언트 지정 식별자.\n\n사용자 계정의 전체 주문 내에서 유일하게 식별되는 값을 할당해야 하며, prev_order_identifier를 포함하여 한번 사용한 identifier 값은 해당 주문의 생성,체결 여부와 상관 없이 재사용할 수 없습니다.\n",
                    "example": "9ca023a5-851b-4fec-9f0a-48cd83c2eaae"
                  },
                  "new_time_in_force": {
                    "type": "string",
                    "enum": [
                      "ioc",
                      "fok",
                      "post_only"
                    ],
                    "description": "주문 체결 조건.\nIOC(Immediate or Cancel), FOK(Fill or Kill), Post Only와 같은 주문 체결 조건을 설정할 수 있습니다. \n\n시장가 주문(ord_type 필드가 \"limit\")인 경우 모든 옵션을 선택적으로 사용할 수 있습니다. 최유리 지정가 주문(ord_type 필드가 “best”)인 경우 대해 \"ioc\" 또는 \"fok\" 중 하나를 필수로 입력합니다. 사용 가능한 값은 다음과 같습니다.\n\n* `ioc`: 지정가 조건으로 체결 가능한 수량만 즉시 부분 체결하고, 잔여 수량은 취소됩니다.\n* `fok`: 지정가 조건으로 주문량 전량 체결 가능할 때만 주문을 실행하고, 아닌 경우 전량 주문 취소합니다.\n* `post_only`: 지정가 조건으로 부분 또는 전체에 대해 즉시 체결 가능한 상황인 경우 주문을 실행하지 않고 취소합니다. 즉, 메이커(maker)주문으로 생성될 수 있는 상황에서만 주문이 생성되며 테이커(taker) 주문으로 체결되는 것을 방지합니다.\n",
                    "example": "ioc"
                  },
                  "new_smp_type": {
                    "type": "string",
                    "enum": [
                      "reduce",
                      "cancel_maker",
                      "cancel_taker"
                    ],
                    "description": "신규 주문의 자전거래 체결 방지(Self-Match Prevention) 모드.\n자동 매매 시 동일 계정으로부터 생성된 매수 주문과 매도 주문이 체결(자전거래)되는 것을 방지하기 위해 SMP 모드를 선택적으로 설정할 수 있습니다. 메이커(maker) 주문과 테이커(taker) 주문에 설정된 SMP 모드가 서로 상이한 경우 테이커 주문 모드에 따라 동작합니다. \n\n사용 가능한 값은 다음과 같습니다.\n\n* `cancel_maker`: 메이커 주문을 취소합니다. 즉, 새로운 주문 생성 시 자전 거래 조건이 성립하는 경우 이전에 생성한 주문을 취소하여 체결을 방지합니다.\n* `cancel_taker`: 테이커 주문을 취소합니다. 즉, 새로운 주문 생성 시 자전 거래 조건이 성립하는 경우 새롭게 생성한 주문을 취소하여 체결을 방지합니다.\n* `reduce`: 새로운 주문 생성 시 자전 거래 조건이 성립하는 경우 기존 주문과 신규 주문의 주문 수량을 줄여 체결을 방지합니다. 잔량이 0인 경우 주문을 취소합니다.\n",
                    "example": "cancel_maker"
                  }
                }
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Object of cancel-and-new order result",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "required": [
                    "market",
                    "uuid",
                    "side",
                    "ord_type",
                    "state",
                    "created_at",
                    "remaining_volume",
                    "executed_volume",
                    "reserved_fee",
                    "remaining_fee",
                    "paid_fee",
                    "locked",
                    "prevented_volume",
                    "prevented_locked",
                    "trades_count",
                    "new_order_uuid"
                  ],
                  "properties": {
                    "market": {
                      "type": "string",
                      "description": "취소할 페어(거래쌍)의 코드\n\n[예시] \"KRW-BTC\"\n",
                      "example": "KRW-BTC"
                    },
                    "uuid": {
                      "type": "string",
                      "description": "취소할 주문의 유일 식별자",
                      "example": "9ca023a5-851b-4fec-9f0a-48cd83c2eaae"
                    },
                    "identifier": {
                      "type": "string",
                      "description": "주문 생성시 클라이언트가 지정한 주문 식별자. \n* identifier 필드는 2024년 10월 18일 이후 생성된 주문에 대해서만 제공됩니다.\n",
                      "example": "9ca023a5-851b-4fec-9f0a-48cd83c2eaae"
                    },
                    "side": {
                      "type": "string",
                      "enum": [
                        "ask",
                        "bid"
                      ],
                      "description": "취소할 주문의 방향(매수/매도)",
                      "example": "ask"
                    },
                    "ord_type": {
                      "type": "string",
                      "enum": [
                        "limit",
                        "price",
                        "market",
                        "best"
                      ],
                      "description": "취소할 주문의 유형.\n",
                      "example": "limit"
                    },
                    "price": {
                      "type": "string",
                      "description": "취소할 주문의 단가 또는 총액",
                      "example": 1000
                    },
                    "state": {
                      "type": "string",
                      "enum": [
                        "wait",
                        "watch",
                        "done",
                        "cancel"
                      ],
                      "description": "취소할 주문의 상태\n\n- `wait`: 체결 대기\n- `watch`: 예약 주문 대기\n- `done`: 체결 완료\n- `cancel`: 주문 취소\n",
                      "example": "wait"
                    },
                    "created_at": {
                      "type": "string",
                      "description": "취소할 주문의 생성 시각 (KST 기준)\n\n[형식] yyyy-MM-ddTHH:mm:ss+09:00\n",
                      "example": "2025-06-25T15:42:25+09:00"
                    },
                    "volume": {
                      "type": "string",
                      "description": "취소할 주문의 수량",
                      "example": 10
                    },
                    "remaining_volume": {
                      "type": "string",
                      "description": "취소할 주문의 남은 주문 양",
                      "example": 8
                    },
                    "executed_volume": {
                      "type": "string",
                      "description": "취소할 주문의 체결된 양",
                      "example": 2
                    },
                    "reserved_fee": {
                      "type": "string",
                      "description": "취소할 주문의 수수료로 예약된 비용",
                      "example": 5
                    },
                    "remaining_fee": {
                      "type": "string",
                      "description": "취소할 주문의 남은 수수료",
                      "example": 5
                    },
                    "paid_fee": {
                      "type": "string",
                      "description": "취소할 주문의 사용된 수수료",
                      "example": 0
                    },
                    "locked": {
                      "type": "string",
                      "description": "취소할 주문의 거래에 사용 중인 비용",
                      "example": 0
                    },
                    "prevented_volume": {
                      "type": "string",
                      "description": "취소할 주문의 자전거래 방지로 인해 취소된 수량",
                      "example": 2
                    },
                    "prevented_locked": {
                      "type": "string",
                      "description": "취소할 주문의 자전거래 방지로 인해 해제된 자산.\n자전거래 체결 방지 설정으로 인해 취소된 주문의 잔여 자산입니다.\n  - 매수 주문의 경우: 취소된 금액\n  - 매도 주문의 경우: 취소된 수량\n",
                      "example": 2000
                    },
                    "smp_type": {
                      "type": "string",
                      "enum": [
                        "reduce",
                        "cancel_maker",
                        "cancel_taker"
                      ],
                      "description": "자전거래 체결 방지(Self-Match Prevention) 모드",
                      "example": "cancel_maker"
                    },
                    "trades_count": {
                      "type": "integer",
                      "description": "취소할 주문에 대한 체결 건수",
                      "example": 1
                    },
                    "time_in_force": {
                      "type": "string",
                      "enum": [
                        "fok",
                        "ioc",
                        "post_only"
                      ],
                      "description": "주문 체결 옵션",
                      "example": "ioc"
                    },
                    "new_order_uuid": {
                      "type": "string",
                      "description": "신규 생성된 주문의 유일 식별자",
                      "example": "55538b02-8828-4e31-8737-8f2f22690dbc"
                    },
                    "new_order_identifier": {
                      "type": "string",
                      "description": "신규 생성된 주문의 클라이언트 지정 식별자",
                      "example": 1234
                    }
                  }
                },
                "examples": {
                  "Successful Example": {
                    "value": {
                      "uuid": "ad217e24-ed02-469c-9b30-c08dbbda6908",
                      "side": "bid",
                      "ord_type": "limit",
                      "price": "100000000",
                      "state": "wait",
                      "market": "KRW-BTC",
                      "created_at": "2025-07-04T15:00:00+09:00",
                      "volume": "1",
                      "remaining_volume": "1",
                      "executed_volume": "0.0",
                      "reserved_fee": "70000.0",
                      "remaining_fee": "70000.0",
                      "paid_fee": "0.0",
                      "locked": "100070000.0",
                      "prevented_volume": "0",
                      "prevented_locked": "0",
                      "trades_count": 0,
                      "new_order_uuid": "4b07aa31-4747-485c-8bce-ac5495e4a639"
                    }
                  }
                }
              }
            }
          },
          "400": {
            "description": "error object",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "error": {
                      "type": "object",
                      "required": [
                        "name",
                        "message"
                      ],
                      "properties": {
                        "name": {
                          "type": "string",
                          "description": "에러명"
                        },
                        "message": {
                          "type": "string",
                          "description": "에러 메세지"
                        }
                      }
                    }
                  }
                },
                "examples": {
                  "invalid parameter error": {
                    "value": {
                      "error": {
                        "name": "invalid_parameter",
                        "message": "잘못된 파라미터"
                      }
                    }
                  }
                }
              }
            }
          },
          "401": {
            "description": "error object",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "error": {
                      "type": "object",
                      "required": [
                        "name",
                        "message"
                      ],
                      "properties": {
                        "name": {
                          "type": "string",
                          "description": "에러명"
                        },
                        "message": {
                          "type": "string",
                          "description": "에러 메세지"
                        }
                      }
                    }
                  }
                },
                "examples": {
                  "unauthorized jwt error": {
                    "value": {
                      "error": {
                        "name": "invalid_query_payload",
                        "message": "Failed to verify the query of Jwt."
                      }
                    }
                  }
                }
              }
            }
          },
          "500": {
            "description": "error object",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "error": {
                      "type": "object",
                      "required": [
                        "name",
                        "message"
                      ],
                      "properties": {
                        "name": {
                          "type": "string",
                          "description": "에러명"
                        },
                        "message": {
                          "type": "string",
                          "description": "에러 메세지"
                        }
                      }
                    }
                  }
                },
                "examples": {
                  "internal server error": {
                    "value": {
                      "error": {
                        "name": "internal_server_error",
                        "message": "Internal Server Error"
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  "_id": "68ef7ce9a70441b77323902d"
}
```