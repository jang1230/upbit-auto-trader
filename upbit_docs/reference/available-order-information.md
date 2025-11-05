# 페어별 주문 가능 정보 조회

지정한 페어의 주문 가능 정보를 조회합니다.

종목 주문 가능 정보는 다음과 같은 주요 항목을 포함합니다.

[block:html]
{
  "html": "<table class=\"custom-table\">\n  <thead>\n    <tr>\n      <th>주요 항목</th>\n      <th>관련 응답 필드</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <td class=\"code-col\">적용 수수료율</td>\n      <td><code>bid_fee</code>,<code>ask_fee</code>,<br><code>maker_bid_fee</code>,<code>maker_ask_fee</code></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">지원 주문 방향 및 주문 유형</td>\n      <td><code>market.order_sides</code>,<code>market.bid_types</code><br><code>market.ask_types</code></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">기준 자산, 호가 자산의 통화 및<br>최소/최대 주문 가능 금액</td>\n      <td><code>market.bid</code>,<code>market.ask</code>,<code>market.max_total</code></td>\n    </tr>\n    <tr>\n      <td class=\"code-col\">기준 자산, 호가 자산의 계정 잔고</td>\n      <td><code>bid_account</code>,<code>ask_account</code></td>\n    </tr>\n  </tbody>\n</table>\n</HTMLBlock>"
}
[/block]


[block:html]
{
  "html": "<div class=\"callout-section callout-section--danger\">\n  <div class=\"callout-title\">\n    <i class=\"fa-solid fa-circle-exclamation\"></i><code>market.order_types</code> 지원 종료 안내 (Deprecated)\n\t</div>\n  종목 지원 주문 유형을 반환하는 order_types 필드는 지원이 종료될 예정입니다. 지원 종료 이후 응답에서 해당 필드가 제거될 예정이오니, 해당 필드를 사용하고 계신 경우 대체 필드인 ask_types, bid_types 필드를 사용해주시기 바랍니다\n</div>"
}
[/block]


[block:html]
{
  "html": "<div class=\"accordion-changelog\">\n    <input type=\"checkbox\" id=\"api-changelog\">\n    <label for=\"api-changelog\">\n        <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Revision History <i class=\"fa-solid fa-angle-right\"></i> </div>\n    </label>\n\n    <div class=\"accordion-changelog-content\">\n        <table class=\"custom-table\">\n            <thead>\n                <tr>\n                    <th>반영 버전</th>\n                    <th>반영 일자</th>\n                    <th>변경 사항</th>\n                </tr>\n            </thead>\n            <tbody>\n                <tr>\n                    <td class=\"code-col\">-</td>\n                    <td>2024-04-22</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/new_ord_type_expand\"> 최유리지정가 주문 유형 신규 지원<br>주문 옵션(time_in_force) 추가 지원</a></td>\n              \t</tr>\n\t\t\t\t\t\t\t\t<tr>\n                    <td class=\"code-col\">-</td>\n                    <td>2022-10-14</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/open-api-변경-사항-안내-적용-일자-1014\"><code>market.order_types</code> 필드 Deprected,<code>ask_types</code>, <code>bid_types</code> 필드 추가<br></a></td>\n                </tr>\n            </tbody>\n        </table>\n    </div>\n</div>\n\n<div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Rate Limit</div>\n<div class=\"box-rate-limit\">\n  초당 최대 30회 호출할 수 있습니다. 계정단위로 측정되며 [Exchange 기본 그룹] 내에서 요청 가능 횟수를 공유합니다.\n</div>\n<br>\n  <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">API Key Permission</div>\n  <div class=\"box-rate-limit\">\n    <a href=\"auth\">인증</a>이 필요한 API로, [주문조회] 권한이 설정된 API Key를 사용해야 합니다. <br>\n    권한 오류(out_of_scope) 오류가 발생한다면, <a href=\"https://upbit.com/mypage/open_api_management\">API Key 관리 메뉴</a>에서 권한 설정을 확인해주세요.\n  </div>"
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
    "/orders/chance": {
      "get": {
        "summary": "페어별 주문 가능 정보 조회",
        "operationId": "available-order-information",
        "tags": [
          "주문(Order)"
        ],
        "x-readme": {
          "code-samples": [
            {
              "language": "curl",
              "code": "curl --request GET \\\n    --url 'https://api.upbit.com/v1/orders/chance?market=KRW-BTC' \\\n    --header 'Authorization: Bearer {JWT_TOKEN}' \\\n    --header 'accept: application/json'\n"
            },
            {
              "language": "python",
              "install": "pip install requests pyjwt python-dotenv",
              "code": "import os\nfrom dotenv import load_dotenv\nimport uuid\nimport hashlib\nimport jwt\nimport requests\n\nload_dotenv()\n\nBASE_URL = \"https://api.upbit.com\"\nPATH = \"/v1/orders/chance\"\n\nACCESS_KEY = os.environ[\"UPBIT_OPEN_API_ACCESS_KEY\"]\nSECRET_KEY = os.environ[\"UPBIT_OPEN_API_SECRET_KEY\"]\n\nparams = {\"market\": \"KRW-BTC\"}\nquery_string = unquote(urlencode(params, doseq=True)).encode(\"utf-8\")\n\nm = hashlib.sha512()\nm.update(query_string.encode(\"utf-8\"))\nquery_hash = m.hexdigest()\n\npayload = {\n  \"access_key\": ACCESS_KEY,\n  \"nonce\": str(uuid.uuid4()),\n  \"query_hash\": query_hash,\n  \"query_hash_alg\": \"SHA512\",\n}\n\njwt_token = jwt.encode(payload, SECRET_KEY, algorithm=\"HS256\")\n\nheaders = {\n  \"Authorization\": f\"Bearer {jwt_token}\",\n  \"Accept\": \"application/json\",\n}\n\nres = requests.get(f\"{BASE_URL}{PATH}?{query_string}\", headers=headers)\nprint(res.json())\n"
            },
            {
              "language": "node",
              "name": "Axios",
              "install": "npm install axios jsonwebtoken uuid",
              "code": "const axios = require(\"axios\");\nconst crypto = require(\"crypto\");\nconst { sign } = require(\"jsonwebtoken\");\nconst { v4: uuidv4 } = require(\"uuid\");\nrequire(\"dotenv\").config();\n\nconst baseURL = \"https://api.upbit.com\";\nconst path = \"/v1/orders/chance\";\n\nconst ACCESS_KEY = process.env.UPBIT_OPEN_API_ACCESS_KEY;\nconst SECRET_KEY = process.env.UPBIT_OPEN_API_SECRET_KEY;\n\nconst queryParams = {\n  market: \"KRW-BTC\",\n};\n\nconst queryString = new URLSearchParams(queryParams).toString();\n\nconst queryHash = crypto\n  .createHash(\"sha512\")\n  .update(queryString, \"utf-8\")\n  .digest(\"hex\");\n\nconst payload = {\n  access_key: ACCESS_KEY,\n  nonce: uuidv4(),\n  query_hash: queryHash,\n  query_hash_alg: \"SHA512\",\n};\n\nconst jwtToken = sign(payload, SECRET_KEY);\n\nconst options = {\n  method: \"GET\",\n  url: `${baseURL}${path}?${queryString}`,\n  headers: {\n    Authorization: `Bearer ${jwtToken}`,\n    Accept: \"application/json\",\n  },\n};\n\naxios\n  .request(options)\n  .then((response) => {\n    console.log(response.data);\n  })\n  .catch((error) => {\n    console.error(error.response ? error.response.data : error.message);\n  });\n"
            },
            {
              "language": "java",
              "code": "package main;\n\nimport com.auth0.jwt.JWT;\nimport com.auth0.jwt.algorithms.Algorithm;\nimport java.io.IOException;\nimport java.nio.charset.StandardCharsets;\nimport java.security.MessageDigest;\nimport java.security.NoSuchAlgorithmException;\nimport java.util.HashMap;\nimport java.util.Map;\nimport java.util.Objects;\nimport java.util.UUID;\nimport java.util.stream.Collectors;\nimport okhttp3.OkHttpClient;\nimport okhttp3.Request;\nimport okhttp3.Response;\n\npublic class AvailableOrderInformation {\n    private static final String BASE_URL = \"https://api.upbit.com\";\n    private static final String PATH = \"/v1/orders/chance\";\n\n\n    public static void main(String[] args) throws NoSuchAlgorithmException, IOException {\n        String accessKey = System.getenv(\"UPBIT_OPEN_API_ACCESS_KEY\");\n        String secretKey = System.getenv(\"UPBIT_OPEN_API_SECRET_KEY\");\n\n        Map<String, String> params = new HashMap<>();\n        params.put(\"market\", \"KRW-BTC\");\n        String queryString = params.entrySet().stream()\n            .map(e -> e.getKey() + \"=\" + String.valueOf(e.getValue()))\n            .collect(Collectors.joining(\"&\"));\n\n        MessageDigest md = MessageDigest.getInstance(\"SHA-512\");\n        md.update(queryString.getBytes(StandardCharsets.UTF_8));\n        StringBuilder sb = new StringBuilder();\n        for (byte b : md.digest()) {\n            sb.append(String.format(\"%02x\", b));\n        }\n        String queryHash = sb.toString();\n\n        Algorithm algorithm = Algorithm.HMAC512(secretKey.getBytes(StandardCharsets.UTF_8));\n        String jwtToken = JWT.create()\n            .withClaim(\"access_key\", accessKey)\n            .withClaim(\"nonce\", UUID.randomUUID().toString())\n            .withClaim(\"query_hash\", queryHash)\n            .withClaim(\"query_hash_alg\", \"SHA512\")\n            .sign(algorithm);\n\n        String authHeader = \"Bearer \" + jwtToken;\n\n        OkHttpClient client = new OkHttpClient();\n        Request request = new Request.Builder()\n            .url(BASE_URL + PATH + \"?\" + queryString)\n            .get()\n            .addHeader(\"Content-Type\", \"application/json\")\n            .addHeader(\"Authorization\", authHeader)\n            .build();\n\n        try (Response response = client.newCall(request).execute()) {\n            System.out.println(response.code());\n            System.out.println(Objects.requireNonNull(response.body()).string());\n        }\n    }\n}\n"
            }
          ]
        },
        "parameters": [
          {
            "name": "market",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "description": "조회하고자 하는 페어(거래쌍)",
              "example": "KRW-BTC"
            },
            "allowReserved": true
          }
        ],
        "responses": {
          "200": {
            "description": "Object of order policy",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": [
                      "bid_fee",
                      "ask_fee",
                      "maker_bid_fee",
                      "maker_ask_fee",
                      "market",
                      "bid_account",
                      "ask_account"
                    ],
                    "properties": {
                      "bid_fee": {
                        "type": "string",
                        "description": "매수 시 적용되는 수수료율",
                        "example": 0.0005
                      },
                      "ask_fee": {
                        "type": "string",
                        "description": "매도 시 적용되는 수수료율",
                        "example": 0.0005
                      },
                      "maker_bid_fee": {
                        "type": "string",
                        "description": "매수 maker 주문 수수료 비율",
                        "example": 0.0005
                      },
                      "maker_ask_fee": {
                        "type": "string",
                        "description": "매도 maker 주문 수수료 비율",
                        "example": 0.0005
                      },
                      "market": {
                        "type": "object",
                        "required": [
                          "id",
                          "name",
                          "order_types",
                          "order_sides",
                          "bid_types",
                          "ask_types",
                          "bid",
                          "ask",
                          "max_total",
                          "state"
                        ],
                        "properties": {
                          "id": {
                            "type": "string",
                            "description": "페어(거래쌍)의 코드\n\n[예시] \"KRW-BTC\"\n",
                            "example": "KRW-BTC"
                          },
                          "name": {
                            "type": "string",
                            "description": "페어 코드((기준 자산)/(디지털 자산 구매에 사용되는 통화 - KRW,BTC,USDT))\n\n[예시] \"BTC/KRW\"\n",
                            "example": "BTC/KRW"
                          },
                          "order_types": {
                            "type": "array",
                            "description": "지원하는 주문 유형 (deprecated)",
                            "enum": [
                              "limit",
                              "price",
                              "market",
                              "best"
                            ],
                            "items": {
                              "type": "string"
                            },
                            "example": [
                              "limit",
                              "market"
                            ]
                          },
                          "order_sides": {
                            "type": "array",
                            "description": "지원하는 주문 방향(매수/매도)",
                            "enum": [
                              "ask",
                              "bid"
                            ],
                            "items": {
                              "type": "string"
                            },
                            "example": [
                              "ask",
                              "bid"
                            ]
                          },
                          "bid_types": {
                            "type": "array",
                            "description": "지원하는 매수 주문 유형\n\n[예시] [\"limit\", \"price\", \"best_fok\", ...]\n",
                            "enum": [
                              "best_fok",
                              "best_ioc",
                              "limit",
                              "limit_fok",
                              "limit_ioc",
                              "price"
                            ],
                            "items": {
                              "type": "string"
                            },
                            "example": [
                              "best_fok",
                              "limit"
                            ]
                          },
                          "ask_types": {
                            "description": "지원하는 매도 주문 유형\n\n[예시] [\"market\", \"limit\", \"best_fok\", ...]\n",
                            "type": "array",
                            "enum": [
                              "best_fok",
                              "best_ioc",
                              "limit",
                              "limit_fok",
                              "limit_ioc",
                              "market"
                            ],
                            "items": {
                              "type": "string"
                            },
                            "example": [
                              "market",
                              "limit_ioc"
                            ]
                          },
                          "bid": {
                            "description": "매수 제약 조건",
                            "type": "object",
                            "required": [
                              "currency",
                              "min_total"
                            ],
                            "properties": {
                              "currency": {
                                "type": "string",
                                "description": "디지털 자산 구매에 사용되는 통화(KRW,BTC,USDT)\n",
                                "example": "KRW"
                              },
                              "price_unit": {
                                "type": "number",
                                "format": "double",
                                "description": "주문 금액 단위.\n해당 필드는 더 이상 사용되지 않으며, 참조하지 않을 것을 권장합니다.  \n(deprecated)\n",
                                "example": 1e-8
                              },
                              "min_total": {
                                "type": "string",
                                "format": "number",
                                "description": "매수 시 최소 주문 금액(결제 화폐 기준)\n\n[예시]  \"min_total\": \"5000\"일 경우, 5000 KRW를 의미합니다.\n",
                                "example": "5000"
                              }
                            }
                          },
                          "ask": {
                            "description": "매도 제약 조건",
                            "type": "object",
                            "required": [
                              "currency",
                              "min_total"
                            ],
                            "properties": {
                              "currency": {
                                "type": "string",
                                "description": "매도 자산 통화\n\n[예시] \"BTC\", \"ETH\"\n",
                                "example": "BTC"
                              },
                              "price_unit": {
                                "type": "number",
                                "format": "double",
                                "description": "주문 금액 단위.\n해당 필드는 더 이상 사용되지 않으며, 참조하지 않을 것을 권장합니다.  \n(deprecated)\n",
                                "example": 1e-8
                              },
                              "min_total": {
                                "type": "string",
                                "format": "number",
                                "description": "매도 시 최소 주문 금액(결제 화폐 기준)\n\n[예시]  \"min_total\": \"5000\"일 경우, 5000 KRW를 의미합니다.\n",
                                "example": "5000"
                              }
                            }
                          },
                          "max_total": {
                            "type": "string",
                            "description": "최대 주문 가능 금액",
                            "example": "1000000000"
                          },
                          "state": {
                            "type": "string",
                            "enum": [
                              "active"
                            ],
                            "description": "페어 운영 상태",
                            "example": "active",
                            "default": "active"
                          }
                        }
                      },
                      "bid_account": {
                        "description": "호가 자산(Quote Asset) 계좌 정보",
                        "type": "object",
                        "required": [
                          "currency",
                          "balance",
                          "locked",
                          "avg_buy_price",
                          "avg_buy_price_modified"
                        ],
                        "properties": {
                          "currency": {
                            "type": "string",
                            "description": "조회하고자 하는 통화 코드",
                            "example": "BTC"
                          },
                          "balance": {
                            "type": "string",
                            "description": "주문 가능 수량 또는 금액.\n디지털 자산의 경우 수량, 법정 통화(KRW)의 경우 금액입니다.\n",
                            "example": 1000000
                          },
                          "locked": {
                            "type": "string",
                            "description": "출금이나 주문 등에 잠겨 있는 잔액",
                            "example": 0
                          },
                          "avg_buy_price": {
                            "type": "string",
                            "description": "매수 평균가",
                            "example": 0
                          },
                          "avg_buy_price_modified": {
                            "type": "boolean",
                            "description": "매수 평균가 수정 여부",
                            "example": false
                          },
                          "unit_currency": {
                            "type": "string",
                            "description": "평균가 기준 통화.\n\"avg_buy_price\"가 기준하는 단위입니다.\n\n[예시] KRW, BTC, USDT\n",
                            "example": "KRW"
                          }
                        }
                      },
                      "ask_account": {
                        "description": "기준 자산(Base Asset) 계좌 정보",
                        "type": "object",
                        "required": [
                          "currency",
                          "balance",
                          "locked",
                          "avg_buy_price",
                          "avg_buy_price_modified"
                        ],
                        "properties": {
                          "currency": {
                            "type": "string",
                            "description": "조회하고자 하는 통화 코드",
                            "example": "BTC"
                          },
                          "balance": {
                            "type": "string",
                            "description": "주문 가능 수량 또는 금액.\n디지털 자산의 경우 수량, 법정 통화(KRW)의 경우 금액입니다.\n",
                            "example": 1000000
                          },
                          "locked": {
                            "type": "string",
                            "description": "출금이나 주문 등에 잠겨 있는 잔액",
                            "example": 0
                          },
                          "avg_buy_price": {
                            "type": "string",
                            "description": "매수 평균가",
                            "example": 0
                          },
                          "avg_buy_price_modified": {
                            "type": "boolean",
                            "description": "매수 평균가 수정 여부",
                            "example": false
                          },
                          "unit_currency": {
                            "type": "string",
                            "description": "평균가 기준 통화.\n\"avg_buy_price\"가 기준하는 단위입니다.\n\n[예시] KRW, BTC, USDT\n",
                            "example": "KRW"
                          }
                        }
                      }
                    }
                  }
                },
                "examples": {
                  "Successful Example": {
                    "value": [
                      {
                        "bid_fee": "0.0005",
                        "ask_fee": "0.0005",
                        "maker_bid_fee": "0.0005",
                        "maker_ask_fee": "0.0005",
                        "market": {
                          "id": "KRW-BTC",
                          "name": "BTC/KRW",
                          "order_types": [
                            "limit"
                          ],
                          "order_sides": [
                            "ask",
                            "bid"
                          ],
                          "bid_types": [
                            "best_fok",
                            "best_ioc",
                            "limit",
                            "limit_fok",
                            "limit_ioc",
                            "price"
                          ],
                          "ask_types": [
                            "best_fok",
                            "best_ioc",
                            "limit",
                            "limit_fok",
                            "limit_ioc",
                            "market"
                          ],
                          "bid": {
                            "currency": "KRW",
                            "min_total": "5000"
                          },
                          "ask": {
                            "currency": "BTC",
                            "min_total": "5000"
                          },
                          "max_total": "1000000000",
                          "state": "active"
                        },
                        "bid_account": {
                          "currency": "KRW",
                          "balance": "10000",
                          "locked": "0",
                          "avg_buy_price": "0",
                          "avg_buy_price_modified": true,
                          "unit_currency": "KRW"
                        },
                        "ask_account": {
                          "currency": "BTC",
                          "balance": "0.001",
                          "locked": "0",
                          "avg_buy_price": "140000000",
                          "avg_buy_price_modified": false,
                          "unit_currency": "KRW"
                        }
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
                  },
                  "not found market error": {
                    "value": {
                      "error": {
                        "name": "notfoundmarket",
                        "message": "다음 마켓에 없는 종목입니다: KRW-BTCs"
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