# 디지털 자산 출금 취소 요청

출금 UUID로 요청이 완료된 디지털 자산 출금 건의 취소를 요청합니다.

### 출금 취소 접수 가능여부

디지털 자산 출금 취소 요청은 취소 가능한 상태의 출금건에 대해서만 정상적으로 접수됩니다. 출금 취소 요청시 응답의 "is_cancelable" 필드를 통해 해당 출금건의 취소 접수 여부를 확인할 수 있습니다. 출금 취소 접수 가능 여부는 해당 통화의 출금 정책 및 네트워크 지연 여부에 따라 실시간으로 변경될 수 있습니다.

[block:html]
{
  "html": "<div class=\"accordion-changelog\">\n    <input type=\"checkbox\" id=\"api-changelog\">\n    <label for=\"api-changelog\">\n        <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Revision History <i class=\"fa-solid fa-angle-right\"></i> </div>\n    </label>\n\n    <div class=\"accordion-changelog-content\">\n        <table class=\"custom-table\">\n            <thead>\n                <tr>\n                    <th>반영 버전</th>\n                    <th>반영 일자</th>\n                    <th>변경 사항</th>\n                </tr>\n            </thead>\n            <tbody>\n                <tr>\n                    <td class=\"code-col\">v1.5.7</td>\n                    <td>2025-05-19</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/delete_withdraws_coin\"> '디지털 자산 출금 취소 요청' 신규 지원</a></td>\n                </tr>\n            </tbody>\n        </table>\n    </div>\n</div>\n\n<div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Rate Limit</div>\n<div class=\"box-rate-limit\">\n  초당 최대 30회 호출할 수 있습니다. 계정단위로 측정되며 [Exchange 기본 그룹] 내에서 요청 가능 횟수를 공유합니다.\n</div>\n\n  <br>\n  <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">API Key Permission</div>\n  <div class=\"box-rate-limit\">\n    <a href=\"auth\">인증</a>이 필요한 API로, [출금하기] 권한이 설정된 API Key를 사용해야 합니다. <br>\n    권한 오류(out_of_scope) 오류가 발생한다면, <a href=\"https://upbit.com/mypage/open_api_management\">API Key 관리 메뉴</a>에서 권한 설정을 확인해주세요.\n  </div>"
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
    "/withdraws/coin": {
      "delete": {
        "summary": "디지털 자산 출금 취소 요청",
        "operationId": "cancel-withdrawal",
        "tags": [
          "출금(Withdrawal)"
        ],
        "x-readme": {
          "code-samples": [
            {
              "language": "curl",
              "code": "curl --request DELETE \\\n    --url 'https://api.upbit.com/v1/withdraws/coin?uuid=9f432943-54e0-40b7-825f-b6fec8b42b79' \\\n    --header 'Authorization: Bearer {JWT_TOKEN}' \\\n    --header 'Accept: application/json'\n"
            },
            {
              "language": "python",
              "install": "pip install requests pyjwt python-dotenv",
              "code": "import os\nimport uuid\nimport hashlib\nimport jwt\nimport requests\nfrom urllib.parse import unquote, urlencode\nfrom dotenv import load_dotenv\n\nload_dotenv()\n\nBASE_URL = \"https://api.upbit.com\"\nPATH = \"/v1/withdraws/coin\"\n\nACCESS_KEY = os.environ[\"UPBIT_OPEN_API_ACCESS_KEY\"]\nSECRET_KEY = os.environ[\"UPBIT_OPEN_API_SECRET_KEY\"]\n\nparams = {\n  \"uuid\": \"9f432943-54e0-40b7-825f-b6fec8b42b79\",\n}\n\nquery_string = unquote(urlencode(params, doseq=True)).encode(\"utf-8\")\n\nm = hashlib.sha512()\nm.update(query_string)\nquery_hash = m.hexdigest()\n\npayload = {\n  \"access_key\": ACCESS_KEY,\n  \"nonce\": str(uuid.uuid4()),\n  \"query_hash\": query_hash,\n  \"query_hash_alg\": \"SHA512\",\n}\n\njwt_token = jwt.encode(payload, SECRET_KEY, algorithm=\"HS256\")\n\nprint(jwt_token)\n\nheaders = {\n  \"Authorization\": f\"Bearer {jwt_token}\",\n  \"Accept\": \"application/json\",\n}\n\nres = requests.delete(f\"{BASE_URL}{PATH}\", headers=headers, params=params)\nprint(res.json())\n"
            },
            {
              "language": "node",
              "name": "Axios",
              "install": "npm install axios jsonwebtoken uuid",
              "code": "const axios = require(\"axios\");\nconst crypto = require(\"crypto\");\nconst { sign } = require(\"jsonwebtoken\");\nconst { v4: uuidv4 } = require(\"uuid\");\nrequire(\"dotenv\").config();\n\nconst baseURL = \"https://api.upbit.com\";\nconst path = \"/v1/withdraws/coin\";\n\nconst ACCESS_KEY = process.env.UPBIT_OPEN_API_ACCESS_KEY;\nconst SECRET_KEY = process.env.UPBIT_OPEN_API_SECRET_KEY;\n\nconst params = {\n  uuid: \"9f432943-54e0-40b7-825f-b6fec8b42b79\",\n};\n\nconst queryString = new URLSearchParams(params).toString();\n\nconst queryHash = crypto\n  .createHash(\"sha512\")\n  .update(queryString, \"utf-8\")\n  .digest(\"hex\");\n\nconst payload = {\n  access_key: ACCESS_KEY,\n  nonce: uuidv4(),\n  query_hash: queryHash,\n  query_hash_alg: \"SHA512\",\n};\n\nconst jwtToken = sign(payload, SECRET_KEY);\n\nconst options = {\n  method: \"DELETE\",\n  url: `${baseURL}${path}?${queryString}`,\n  headers: {\n    Authorization: `Bearer ${jwtToken}`,\n    Accept: \"application/json\",\n  },\n};\n\naxios\n  .request(options)\n  .then((response) => {\n    console.log(response.data);\n  })\n  .catch((error) => {\n    console.error(error.response ? error.response.data : error.message);\n  });\n"
            },
            {
              "language": "java",
              "code": "package main;\n\nimport com.auth0.jwt.JWT;\nimport com.auth0.jwt.algorithms.Algorithm;\nimport java.io.IOException;\nimport java.nio.charset.StandardCharsets;\nimport java.security.MessageDigest;\nimport java.security.NoSuchAlgorithmException;\nimport java.util.HashMap;\nimport java.util.Map;\nimport java.util.Objects;\nimport java.util.UUID;\nimport java.util.stream.Collectors;\nimport okhttp3.OkHttpClient;\nimport okhttp3.Request;\nimport okhttp3.Response;\n\npublic class CancelWithdraw {\n    private static final String BASE_URL = \"https://api.upbit.com\";\n    private static final String PATH = \"/v1/withdraws/coin\";\n\n    public static void main(String[] args) throws NoSuchAlgorithmException, IOException {\n        String accessKey = System.getenv(\"UPBIT_OPEN_API_ACCESS_KEY\");\n        String secretKey = System.getenv(\"UPBIT_OPEN_API_SECRET_KEY\");\n\n        Map<String, String> params = new HashMap<>();\n        params.put(\"uuid\", \"9f432943-54e0-40b7-825f-b6fec8b42b79\");\n        String queryString = params.entrySet().stream()\n            .map(e -> e.getKey() + \"=\" + String.valueOf(e.getValue()))\n            .collect(Collectors.joining(\"&\"));\n\n        MessageDigest md = MessageDigest.getInstance(\"SHA-512\");\n        md.update(queryString.getBytes(StandardCharsets.UTF_8));\n        StringBuilder sb = new StringBuilder();\n        for (byte b : md.digest()) {\n            sb.append(String.format(\"%02x\", b));\n        }\n        String queryHash = sb.toString();\n\n        Algorithm algorithm = Algorithm.HMAC512(secretKey.getBytes(StandardCharsets.UTF_8));\n        String jwtToken = JWT.create()\n            .withClaim(\"access_key\", accessKey)\n            .withClaim(\"nonce\", UUID.randomUUID().toString())\n            .withClaim(\"query_hash\", queryHash)\n            .withClaim(\"query_hash_alg\", \"SHA512\")\n            .sign(algorithm);\n\n        String authHeader = \"Bearer \" + jwtToken;\n\n        OkHttpClient client = new OkHttpClient();\n        Request request = new Request.Builder()\n            .url(BASE_URL + PATH + \"?\" + queryString)\n            .delete()\n            .addHeader(\"Content-Type\", \"application/json\")\n            .addHeader(\"Authorization\", authHeader)\n            .build();\n\n        try (Response response = client.newCall(request).execute()) {\n            System.out.println(response.code());\n            System.out.println(Objects.requireNonNull(response.body()).string());\n        }\n    }\n}\n"
            }
          ]
        },
        "parameters": [
          {
            "name": "uuid",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "description": "취소하고자 하는 출금의 유일식별자(UUID)",
              "example": "9ca023a5-851b-4fec-9f0a-48cd83c2eaae"
            },
            "allowReserved": true
          }
        ],
        "responses": {
          "200": {
            "description": "Object of canceled withdrawal",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "required": [
                    "type",
                    "uuid",
                    "currency",
                    "net_type",
                    "txid",
                    "state",
                    "created_at",
                    "amount",
                    "fee",
                    "transaction_type",
                    "is_cancelable"
                  ],
                  "properties": {
                    "type": {
                      "type": "string",
                      "description": "입출금 종류",
                      "example": "withdraw",
                      "default": "withdraw"
                    },
                    "uuid": {
                      "type": "string",
                      "description": "출금의 유일 식별자",
                      "example": "9f432943-54e0-40b7-825f-b6fec8b42b79"
                    },
                    "currency": {
                      "type": "string",
                      "description": "조회하고자 하는 통화 코드",
                      "example": "BTC"
                    },
                    "net_type": {
                      "type": "string",
                      "description": "출금 네트워크 유형.\n업비트에서 사용하는 블록체인 네트워크 구분자입니다. 원화(KRW) 출금의 경우 null로 반환됩니다.\n\n[예시] \"ETH\", \"TRX\", \"SOL\"\n",
                      "example": "BTC"
                    },
                    "txid": {
                      "type": "string",
                      "nullable": true,
                      "description": "트랜잭션 ID",
                      "example": 1234567890
                    },
                    "state": {
                      "type": "string",
                      "enum": [
                        "CANCELLED"
                      ],
                      "description": "출금 처리 상태",
                      "example": "CANCELLED",
                      "default": "CANCELLED"
                    },
                    "created_at": {
                      "type": "string",
                      "description": "출금 생성 시간",
                      "example": "2024-01-01T00:00:00"
                    },
                    "done_at": {
                      "type": "string",
                      "nullable": true,
                      "description": "출금 완료 시간. 출금이 완료되지 않은 경우 null로 반환됩니다",
                      "example": "2024-01-01T00:00:00"
                    },
                    "amount": {
                      "type": "string",
                      "description": "출금하고자 하는 자산의 수량\n",
                      "example": "0.01"
                    },
                    "fee": {
                      "type": "string",
                      "description": "출금 수수료",
                      "example": 0
                    },
                    "transaction_type": {
                      "type": "string",
                      "enum": [
                        "default",
                        "internal"
                      ],
                      "description": "출금 유형.\n사용 가능한 값은 다음과 같습니다.\n\n* `default`: 일반출금\n* `internal`: 바로출금\n",
                      "example": "default",
                      "default": "default"
                    },
                    "is_cancelable": {
                      "type": "boolean",
                      "description": "출금 취소 가능 여부",
                      "example": false
                    }
                  }
                },
                "examples": {
                  "Successful Example": {
                    "value": {
                      "type": "withdraw",
                      "uuid": "9f432943-54e0-40b7-825f-b6fec8b42b79",
                      "currency": "BTC",
                      "net_type": "BTC",
                      "txid": null,
                      "state": "CANCELLED",
                      "created_at": "2025-07-01T15:00:00+09:00",
                      "done_at": null,
                      "amount": "0.01",
                      "fee": "0.0",
                      "transaction_type": "default",
                      "is_cancelable": true
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
                  "missing uuid error": {
                    "value": {
                      "error": {
                        "name": "validation_error",
                        "message": "\"field name\" is missing"
                      }
                    }
                  }
                }
              }
            }
          },
          "404": {
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
                  "not found withdraw error": {
                    "value": {
                      "error": {
                        "name": "withdraw_not_found",
                        "message": "출금 정보를 찾지 못했습니다."
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