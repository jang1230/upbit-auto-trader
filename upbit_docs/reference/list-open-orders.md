# 체결 대기 주문 목록 조회

체결 대기 중인 주문(Open Orders) 목록을 조회합니다.

계정의 체결 대기 주문 목록을 조회할 수 있습니다. 필터 파라미터인 페어와 주문 상태(체결 대기 또는 예약 주문 대기)를 선택적으로 입력하여 해당 조건을 만족하는 체결 대기 주문들을 조회할 수 있습니다.

[block:html]
{
  "html": "  <div class=\"callout-section\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i>  state와 states[]는 동시에 사용할 수 없습니다.\n      </div>\n      주문 상태 필터링 시 조건에 따라 적절한 파라미터를 하나만 사용해주세요.\n  </div>"
}
[/block]


[block:html]
{
  "html": "<div class=\"accordion-changelog\">\n    <input type=\"checkbox\" id=\"api-changelog\">\n    <label for=\"api-changelog\">\n        <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Revision History <i class=\"fa-solid fa-angle-right\"></i> </div>\n    </label>\n\n    <div class=\"accordion-changelog-content\">\n        <table class=\"custom-table\">\n            <thead>\n                <tr>\n                    <th>반영 버전</th>\n                    <th>반영 일자</th>\n                    <th>변경 사항</th>\n                </tr>\n            </thead>\n            <tbody>\n                <tr>\n                    <td class=\"code-col\">v1.5.8</td>\n                    <td>2025-07-02</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/smp\"> 자전거래 체결 방지(SMP) 기능<br>신규 지원에 따른 필드 추가<br><code>smp_type</code>,<code>prevented_volume</code>,<code>prevented_locked</code></a></td>\n              \t </tr>\n\t\t\t\t\t\t\t\t<tr>\n                    <td class=\"code-col\">-</td>\n                    <td>2024-12-04</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/myorder_identifier\"> <code>identifier</code> 필드 신규 지원</a></td>\n                </tr>\n\t\t\t\t\t\t\t\t<tr>\n                    <td class=\"code-col\">-</td>\n                    <td>2024-06-27</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/new_get_orders\"> '체결 대기 주문 목록 조회' 신규 기능 지원</a></td>\n                </tr>\n            </tbody>\n        </table>\n    </div>\n</div>\n\n<div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Rate Limit</div>\n<div class=\"box-rate-limit\">\n  초당 최대 30회 호출할 수 있습니다. 계정단위로 측정되며 [Exchange 기본 그룹] 내에서 요청 가능 횟수를 공유합니다.\n</div>\n<br>\n  <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">API Key Permission</div>\n  <div class=\"box-rate-limit\">\n    <a href=\"auth\">인증</a>이 필요한 API로, [주문조회] 권한이 설정된 API Key를 사용해야 합니다. <br>\n    권한 오류(out_of_scope) 오류가 발생한다면, <a href=\"https://upbit.com/mypage/open_api_management\">API Key 관리 메뉴</a>에서 권한 설정을 확인해주세요.\n  </div>"
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
    "/orders/open": {
      "get": {
        "summary": "체결 대기 주문 목록 조회",
        "operationId": "list-open-orders",
        "tags": [
          "주문(Order)"
        ],
        "x-readme": {
          "code-samples": [
            {
              "language": "curl",
              "code": "curl --request GET \\\n    --url 'https://api.upbit.com/v1/orders/open?market=KRW-BTC&states[]=wait&states[]=watch' \\\n    --header 'Authorization: Bearer {JWT_TOKEN}' \\\n    --header 'Accept: application/json'\n"
            },
            {
              "language": "python",
              "install": "pip install requests pyjwt python-dotenv",
              "code": "import os\nimport uuid\nimport hashlib\nimport jwt\nimport requests\nfrom urllib.parse import unquote, urlencode\nfrom dotenv import load_dotenv\n\nload_dotenv()\n\nBASE_URL = \"https://api.upbit.com\"\nPATH = \"/v1/orders/open\"\n\nACCESS_KEY = os.environ[\"UPBIT_OPEN_API_ACCESS_KEY\"]\nSECRET_KEY = os.environ[\"UPBIT_OPEN_API_SECRET_KEY\"]\n\nparams = {\n  \"market\": \"KRW-BTC\",\n  \"states[]\": [\"wait\", \"watch\"],\n}\n\nquery_string = unquote(urlencode(params, doseq=True)).encode(\"utf-8\")\n\nm = hashlib.sha512()\nm.update(query_string)\nquery_hash = m.hexdigest()\n\npayload = {\n  \"access_key\": ACCESS_KEY,\n  \"nonce\": str(uuid.uuid4()),\n  \"query_hash\": query_hash,\n  \"query_hash_alg\": \"SHA512\",\n}\n\njwt_token = jwt.encode(payload, SECRET_KEY, algorithm=\"HS256\")\n\nheaders = {\n  \"Authorization\": f\"Bearer {jwt_token}\",\n  \"Accept\": \"application/json\",\n}\n\nres = requests.get(f\"{BASE_URL}{PATH}\", headers=headers, params=params)\nprint(res.json())\n"
            },
            {
              "language": "node",
              "name": "Axios",
              "install": "npm install axios jsonwebtoken uuid",
              "code": "const axios = require(\"axios\");\nconst crypto = require(\"crypto\");\nconst { sign } = require(\"jsonwebtoken\");\nconst { v4: uuidv4 } = require(\"uuid\");\nrequire(\"dotenv\").config();\n\nconst BASE_URL = \"https://api.upbit.com\";\nconst PATH = \"/v1/orders/open\";\n\nconst ACCESS_KEY = process.env.UPBIT_OPEN_API_ACCESS_KEY;\nconst SECRET_KEY = process.env.UPBIT_OPEN_API_SECRET_KEY;\n\nconst params = {\n  market: \"KRW-BTC\",\n  \"states[]\": [\"wait\", \"watch\"],\n};\n\nconst encodedQueryString = new URLSearchParams(\n  Object.entries(params).flatMap(([key, value]) =>\n    Array.isArray(value) ? value.map((v) => [key, v]) : [[key, value]]\n  )\n).toString();\n\nconst queryString = decodeURIComponent(encodedQueryString);\n\nconst queryHash = crypto\n  .createHash(\"sha512\")\n  .update(queryString, \"utf-8\")\n  .digest(\"hex\");\n\nconst payload = {\n  access_key: ACCESS_KEY,\n  nonce: uuidv4(),\n  query_hash: queryHash,\n  query_hash_alg: \"SHA512\",\n};\n\nconst jwtToken = sign(payload, SECRET_KEY);\nconsole.log(jwtToken);\n\nconst options = {\n  method: \"GET\",\n  url: `${BASE_URL}${PATH}?${encodedQueryString}`,\n  headers: {\n    Authorization: `Bearer ${jwtToken}`,\n    Accept: \"application/json\",\n  },\n};\n\naxios\n  .request(options)\n  .then((response) => {\n    console.log(response.data);\n  })\n  .catch((error) => {\n    console.error(error.response ? error.response.data : error.message);\n  });\n"
            },
            {
              "language": "java",
              "code": "package main;\n\nimport com.auth0.jwt.JWT;\nimport com.auth0.jwt.algorithms.Algorithm;\nimport java.io.IOException;\nimport java.nio.charset.StandardCharsets;\nimport java.security.MessageDigest;\nimport java.security.NoSuchAlgorithmException;\nimport java.util.HashMap;\nimport java.util.List;\nimport java.util.Map;\nimport java.util.Objects;\nimport java.util.UUID;\nimport java.util.stream.Collectors;\nimport okhttp3.OkHttpClient;\nimport okhttp3.Request;\nimport okhttp3.Response;\n\npublic class OpenOrders {\n    private static final String BASE_URL = \"https://api.upbit.com\";\n    private static final String PATH = \"/v1/orders/open\";\n\n    public static void main(String[] args) throws NoSuchAlgorithmException, IOException {\n        String accessKey = System.getenv(\"UPBIT_OPEN_API_ACCESS_KEY\");\n        String secretKey = System.getenv(\"UPBIT_OPEN_API_SECRET_KEY\");\n\n        Map<String, List<String>> params = new HashMap<>();\n        params.put(\"market\", \"KRW-BTC\");\n        params.put(\"states[]\", List.of(\"wait\", \"watch\"));\n        String queryString = params.entrySet().stream()\n            .flatMap(e -> e.getValue().stream().map(v -> e.getKey() + \"=\" + v))\n            .collect(Collectors.joining(\"&\")); \n\n        MessageDigest md = MessageDigest.getInstance(\"SHA-512\");\n        md.update(queryString.getBytes(StandardCharsets.UTF_8));\n        StringBuilder sb = new StringBuilder();\n        for (byte b : md.digest()) {\n            sb.append(String.format(\"%02x\", b));\n        }\n        String queryHash = sb.toString();\n\n        Algorithm algorithm = Algorithm.HMAC512(secretKey.getBytes(StandardCharsets.UTF_8));\n        String jwtToken = JWT.create()\n            .withClaim(\"access_key\", accessKey)\n            .withClaim(\"nonce\", UUID.randomUUID().toString())\n            .withClaim(\"query_hash\", queryHash)\n            .withClaim(\"query_hash_alg\", \"SHA512\")\n            .sign(algorithm);\n\n        String authHeader = \"Bearer \" + jwtToken;\n\n        OkHttpClient client = new OkHttpClient();\n        Request request = new Request.Builder()\n            .url(BASE_URL + PATH + \"?\" + queryString)\n            .get()\n            .addHeader(\"Content-Type\", \"application/json\")\n            .addHeader(\"Authorization\", authHeader)\n            .build();\n\n        try (Response response = client.newCall(request).execute()) {\n            System.out.println(response.code());\n            System.out.println(Objects.requireNonNull(response.body()).string());\n        }\n    }\n}\n"
            }
          ]
        },
        "parameters": [
          {
            "name": "market",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string",
              "description": "조회하고자 하는 페어(거래쌍)",
              "example": "KRW-BTC"
            },
            "allowReserved": true
          },
          {
            "name": "state",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string",
              "description": "주문의 상태. \n지정한 상태의 주문만을 조회하기 위한 필터 파라미터입니다. 사용 가능한 값은 “wait”(체결 대기), “watch”(예약 주문 대기)입니다. 미지정시 기본값은 “wait”입니다.\n",
              "enum": [
                "wait",
                "watch"
              ],
              "default": "wait"
            },
            "allowReserved": true
          },
          {
            "name": "states[]",
            "in": "query",
            "required": false,
            "schema": {
              "type": "array",
              "description": "주문의 상태. \n지정한 상태의 주문만을 조회하기 위한 필터 파라미터입니다. 배열 형식이며 사용 가능한 값은 “wait”(체결 대기), “watch”(예약 주문 대기)입니다. 미지정시 기본값은 “wait”입니다.\n\n[예시] states[]=wait&states[]=watch\n",
              "items": {
                "type": "string",
                "enum": [
                  "wait",
                  "watch"
                ]
              },
              "default": "wait"
            },
            "allowReserved": true
          },
          {
            "name": "page",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "description": "조회할 페이지 번호.\nPagination을 위한 파라미터로, 조회하고자 하는 페이지를 지정할 수 있습니다. 미지정시 기본값은 1입니다.\n",
              "example": 1,
              "default": 1
            },
            "allowReserved": true
          },
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "description": "페이지당 항목 수. \nPagination을 위한 파라미터로, 조회하고자 하는 페이지당 항목 수를 지정할 수 있습니다. 한번에 최대 100개의 항목을 조회할 수 있으며, 미지정시 기본값은 100입니다.\n",
              "example": 100,
              "default": 100
            },
            "allowReserved": true
          },
          {
            "name": "order_by",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string",
              "enum": [
                "asc",
                "desc"
              ],
              "description": "결과 정렬 방식. \n주문 생성 시각을 기준으로 설정한 방식에 따라 정렬된 주문 목록이 반환됩니다. 사용 가능한 값은 “desc”(내림차순, 최신 주문 순) 또는 “asc”(오름차순, 오래된 주문 순)입니다. 기본값은 “desc”입니다.\n",
              "example": "desc",
              "default": "desc"
            },
            "allowReserved": true
          }
        ],
        "responses": {
          "200": {
            "description": "List of open orders",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
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
                      "executed_funds",
                      "reserved_fee",
                      "remaining_fee",
                      "paid_fee",
                      "locked",
                      "prevented_volume",
                      "prevented_locked",
                      "trades_count"
                    ],
                    "properties": {
                      "market": {
                        "type": "string",
                        "description": "페어(거래쌍)의 코드\n\n[예시] \"KRW-BTC\"\n",
                        "example": "KRW-BTC"
                      },
                      "uuid": {
                        "type": "string",
                        "description": "주문의 유일 식별자",
                        "example": "9ca023a5-851b-4fec-9f0a-48cd83c2eaae"
                      },
                      "side": {
                        "type": "string",
                        "enum": [
                          "ask",
                          "bid"
                        ],
                        "description": "주문 방향(매수/매도)",
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
                        "description": "주문 유형. \n\n- `limit`: 지정가 매수/매도 주문\n- `price`: 시장가 매수 주문\n- `market`: 시장가 매도 주문\n- `best`: 최유리 지정가 매수/매도 주문 (time_in_force 필드 설정 필수)\n",
                        "example": "limit"
                      },
                      "price": {
                        "type": "string",
                        "description": "주문 단가 또는 총액\n지정가 주문의 경우 단가, 시장가 매수 주문의 경우 매수 총액입니다.\n",
                        "example": 1000
                      },
                      "state": {
                        "type": "string",
                        "enum": [
                          "wait",
                          "watch"
                        ],
                        "description": "주문 상태\n\n- `wait`: 체결 대기\n- `watch`: 예약 주문 대기\n",
                        "example": "wait"
                      },
                      "created_at": {
                        "type": "string",
                        "description": "주문 생성 시각 (KST 기준)\n\n[형식] yyyy-MM-ddTHH:mm:ss+09:00\n",
                        "example": "2025-06-25T15:42:25+09:00"
                      },
                      "volume": {
                        "type": "string",
                        "description": "주문 요청 수량",
                        "example": 10
                      },
                      "remaining_volume": {
                        "type": "string",
                        "description": "체결 후 남은 주문 양",
                        "example": 8
                      },
                      "executed_volume": {
                        "type": "string",
                        "description": "체결된 양",
                        "example": 2
                      },
                      "executed_funds": {
                        "type": "string",
                        "description": "현재까지 체결된 금액",
                        "example": 2000
                      },
                      "reserved_fee": {
                        "type": "string",
                        "description": "수수료로 예약된 비용",
                        "example": 5
                      },
                      "remaining_fee": {
                        "type": "string",
                        "description": "남은 수수료",
                        "example": 5
                      },
                      "paid_fee": {
                        "type": "string",
                        "description": "사용된 수수료",
                        "example": 0
                      },
                      "locked": {
                        "type": "string",
                        "description": "거래에 사용 중인 비용",
                        "example": 0
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
                      "identifier": {
                        "type": "string",
                        "description": "주문 생성시 클라이언트가 지정한 주문 식별자. \n* identifier 필드는 2024년 10월 18일 이후 생성된 주문에 대해서만 제공됩니다.\n",
                        "example": "9ca023a5-851b-4fec-9f0a-48cd83c2eaae"
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
                      "prevented_volume": {
                        "type": "string",
                        "description": "자전거래 방지로 인해 취소된 수량.\n동일 사용자의 주문 간 체결이 발생하지 않도록 설정(SMP)에 따라 취소된 주문 수량입니다.\n",
                        "example": 2
                      },
                      "prevented_locked": {
                        "type": "string",
                        "description": "자전거래 방지로 인해 해제된 자산.\n자전거래 체결 방지 설정으로 인해 취소된 주문의 잔여 자산입니다.\n  - 매수 주문의 경우: 취소된 금액\n  - 매도 주문의 경우: 취소된 수량\n",
                        "example": 2000
                      },
                      "trades_count": {
                        "type": "integer",
                        "description": "해당 주문에 대한 체결 건수",
                        "example": 1
                      }
                    }
                  }
                },
                "examples": {
                  "Successful Example": {
                    "value": [
                      {
                        "uuid": "d098ceaf-6811-4df8-97f2-b7e01aefc03f",
                        "side": "bid",
                        "ord_type": "limit",
                        "price": "140000000",
                        "state": "wait",
                        "market": "KRW-BTC",
                        "created_at": "2025-07-04T15:00:00+09:00",
                        "volume": "1.0",
                        "remaining_volume": "1.0",
                        "executed_volume": "0.0",
                        "executed_funds": "140000000.0",
                        "reserved_fee": "70000.0",
                        "remaining_fee": "70000.0",
                        "paid_fee": "0.0",
                        "locked": "140070000.0",
                        "prevented_volume": "0",
                        "prevented_locked": "0",
                        "trades_count": 0
                      }
                    ]
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
          }
        }
      }
    }
  },
  "_id": "68ef7ce9a70441b77323902d"
}
```