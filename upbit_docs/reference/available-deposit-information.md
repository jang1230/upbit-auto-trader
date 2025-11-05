# 디지털 자산 입금 가능 정보 조회

지정한 통화에 대한 입금 가능 정보를 조회합니다.

통화 입금 가능 정보는 다음과 같은 주요 항목을 포함합니다

[block:html]
{
  "html": "<table class=\"custom-table\">\n    <thead>\n      <tr>\n        <th>주요 항목</th>\n        <th>관련 주요 응답 필드</th>\n      </tr>\n    </thead>\n    <tbody>\n      <tr>\n        <td class=\"code-col\"><b>입금 가능 여부</b></td>\n        <td><code>is_deposit_possible</code>,\n            <br><code>deposit_impossible_reason</code></td>\n      </tr>\n      <tr>\n        <td class=\"code-col\"><b>최소 입금 수량</b></td>\n        <td><code>minimum_deposit_amount</code></td>\n      </tr>\n      <tr>\n        <td class=\"code-col\"><b>정책</b></td>\n        <td><code>minimum_deposit_confirmations</code>,\n            <br><code>decimal_precision</code></td>\n      </tr>\n    </tbody>\n</table>\n\n  <div class=\"callout-section callout-section--danger\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i> 입금 가능 정보 조회 API는 실시간 상태 조회를 보장하지 않습니다.\n      </div>\n      디지털 자산 입금 가능 정보 조회 API가 반환하는 입금 가능 여부는 서비스 상태를 실시간으로 반영하지 않으며 반영은 수 분 정도 지연될 수 있습니다. \n      따라서 <b>거래 전략 용도가 아닌 참고 용도로의 사용만을 권장</b>하며, 실제 입금을 수행하기 전에는 반드시 <a href=\"https://upbit.com/service_center/notice\">업비트 공지사항</a> 및 <a href=\"https://upbit.com/service_center/wallet_status\">실시간 입출금 현황</a> 페이지를 참고해 주시기를 바랍니다.\n  </div>"
}
[/block]


[block:html]
{
  "html": "<div class=\"accordion-changelog\">\n    <input type=\"checkbox\" id=\"api-changelog\">\n    <label for=\"api-changelog\">\n        <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Revision History <i class=\"fa-solid fa-angle-right\"></i> </div>\n    </label>\n\n    <div class=\"accordion-changelog-content\">\n        <table class=\"custom-table\">\n            <thead>\n                <tr>\n                    <th>반영 버전</th>\n                    <th>반영 일자</th>\n                    <th>변경 사항</th>\n                </tr>\n            </thead>\n          \t<tbody>\n                <tr>\n                    <td class=\"code-col\">-</td>\n                    <td>2024-11-14</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/available_deposit_information\"> '입금 가능 정보 조회' 기능 신규 추가</a></td>\n            \t  </tr>\n            </tbody>\n        </table>\n    </div>\n</div>\n\n<div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Rate Limit</div>\n<div class=\"box-rate-limit\">\n  초당 최대 30회 호출할 수 있습니다. 계정단위로 측정되며 [Exchange 기본 그룹] 내에서 요청 가능 횟수를 공유합니다.\n</div>\n\n  <br>\n  <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">API Key Permission</div>\n  <div class=\"box-rate-limit\">\n    <a href=\"auth\">인증</a>이 필요한 API로, [입금조회] 권한이 설정된 API Key를 사용해야 합니다. <br>\n    권한 오류(out_of_scope) 오류가 발생한다면, <a href=\"https://upbit.com/mypage/open_api_management\">API Key 관리 메뉴</a>에서 권한 설정을 확인해주세요.\n  </div>"
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
    "/deposits/chance/coin": {
      "get": {
        "operationId": "available-deposit-information",
        "summary": "디지털 자산 입금 가능 정보 조회",
        "tags": [
          "입금(Deposit)"
        ],
        "x-readme": {
          "code-samples": [
            {
              "language": "curl",
              "code": "curl --request GET \\\n  --url 'https://api.upbit.com/v1/deposits/chance/coin?currency=BTC&net_type=BTC' \\\n  --header 'Authorization: Bearer {JWT_TOKEN}' \\\n  --header 'Accept: application/json'\n"
            },
            {
              "language": "python",
              "install": "pip install requests pyjwt python-dotenv",
              "code": "import os\nimport uuid\nimport hashlib\nimport jwt\nimport requests\nfrom urllib.parse import unquote, urlencode\nfrom dotenv import load_dotenv\n\nload_dotenv()\n\nBASE_URL = \"https://api.upbit.com\"\nPATH = \"/v1/deposits/chance/coin\"\n\nACCESS_KEY = os.environ[\"UPBIT_OPEN_API_ACCESS_KEY\"]\nSECRET_KEY = os.environ[\"UPBIT_OPEN_API_SECRET_KEY\"]\n\nparams = {\n  \"currency\": \"BTC\",\n  \"net_type\": \"BTC\",\n}\n\nquery_string = unquote(urlencode(params, doseq=True)).encode(\"utf-8\")\n\nm = hashlib.sha512()\nm.update(query_string)\nquery_hash = m.hexdigest()\n\npayload = {\n  \"access_key\": ACCESS_KEY,\n  \"nonce\": str(uuid.uuid4()),\n  \"query_hash\": query_hash,\n  \"query_hash_alg\": \"SHA512\",\n}\n\njwt_token = jwt.encode(payload, SECRET_KEY, algorithm=\"HS256\")\n\nheaders = {\n  \"Authorization\": f\"Bearer {jwt_token}\",\n  \"Accept\": \"application/json\",\n}\n\nres = requests.get(f\"{BASE_URL}{PATH}\", headers=headers, params=params)\nprint(res.json())\n"
            },
            {
              "language": "node",
              "name": "Axios",
              "install": "npm install axios jsonwebtoken uuid",
              "code": "const axios = require(\"axios\");\nconst crypto = require(\"crypto\");\nconst { sign } = require(\"jsonwebtoken\");\nconst { v4: uuidv4 } = require(\"uuid\");\nrequire(\"dotenv\").config();\n\nconst baseURL = \"https://api.upbit.com\";\nconst path = \"/v1/deposits/chance/coin\";\n\nconst ACCESS_KEY = process.env.UPBIT_OPEN_API_ACCESS_KEY;\nconst SECRET_KEY = process.env.UPBIT_OPEN_API_SECRET_KEY;\n\nconst params = {\n  currency: \"BTC\",\n  net_type: \"BTC\",\n};\n\nconst queryString = new URLSearchParams(params).toString();\n\nconst queryHash = crypto\n  .createHash(\"sha512\")\n  .update(queryString, \"utf-8\")\n  .digest(\"hex\");\n\nconst payload = {\n  access_key: ACCESS_KEY,\n  nonce: uuidv4(),\n  query_hash: queryHash,\n  query_hash_alg: \"SHA512\",\n};\n\nconst jwtToken = sign(payload, SECRET_KEY);\n\nconst options = {\n  method: \"GET\",\n  url: `${baseURL}${path}?${queryString}`,\n  headers: {\n    Authorization: `Bearer ${jwtToken}`,\n    Accept: \"application/json\",\n  },\n};\n\naxios\n  .request(options)\n  .then((response) => {\n    console.log(response.data);\n  })\n  .catch((error) => {\n    console.error(error.response ? error.response.data : error.message);\n  });\n"
            },
            {
              "language": "java",
              "code": "package main;\n\nimport com.auth0.jwt.JWT;\nimport com.auth0.jwt.algorithms.Algorithm;\nimport java.io.IOException;\nimport java.nio.charset.StandardCharsets;\nimport java.security.MessageDigest;\nimport java.security.NoSuchAlgorithmException;\nimport java.util.HashMap;\nimport java.util.Map;\nimport java.util.Objects;\nimport java.util.UUID;\nimport java.util.stream.Collectors;\nimport okhttp3.OkHttpClient;\nimport okhttp3.Request;\nimport okhttp3.Response;\n\npublic class AvailableDeposit {\n    private static final String BASE_URL = \"https://api.upbit.com\";\n    private static final String PATH = \"/v1/deposits/chance/coin\";\n\n    public static void main(String[] args) throws NoSuchAlgorithmException, IOException {\n        String accessKey = System.getenv(\"UPBIT_OPEN_API_ACCESS_KEY\");\n        String secretKey = System.getenv(\"UPBIT_OPEN_API_SECRET_KEY\");\n\n        Map<String, String> params = new HashMap<>();\n        params.put(\"currency\", \"BTC\");\n        params.put(\"net_type\", \"BTC\");\n        String queryString = params.entrySet().stream()\n            .map(e -> e.getKey() + \"=\" + String.valueOf(e.getValue()))\n            .collect(Collectors.joining(\"&\"));\n\n        MessageDigest md = MessageDigest.getInstance(\"SHA-512\");\n        md.update(queryString.getBytes(StandardCharsets.UTF_8));\n        StringBuilder sb = new StringBuilder();\n        for (byte b : md.digest()) {\n            sb.append(String.format(\"%02x\", b));\n        }\n        String queryHash = sb.toString();\n\n        Algorithm algorithm = Algorithm.HMAC512(secretKey.getBytes(StandardCharsets.UTF_8));\n        String jwtToken = JWT.create()\n            .withClaim(\"access_key\", accessKey)\n            .withClaim(\"nonce\", UUID.randomUUID().toString())\n            .withClaim(\"query_hash\", queryHash)\n            .withClaim(\"query_hash_alg\", \"SHA512\")\n            .sign(algorithm);\n\n        String authHeader = \"Bearer \" + jwtToken;\n\n        OkHttpClient client = new OkHttpClient();\n        Request request = new Request.Builder()\n            .url(BASE_URL + PATH + \"?\" + queryString)\n            .get()\n            .addHeader(\"Content-Type\", \"application/json\")\n            .addHeader(\"Authorization\", authHeader)\n            .build();\n\n        try (Response response = client.newCall(request).execute()) {\n            System.out.println(response.code());\n            System.out.println(Objects.requireNonNull(response.body()).string());\n        }\n    }\n}\n"
            }
          ]
        },
        "parameters": [
          {
            "name": "currency",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "description": "조회하고자 하는 통화 코드. \n통화 코드로 조회 대상을 한정하기 위한 필터 파라미터입니다.\n",
              "example": "BTC"
            },
            "allowReserved": true
          },
          {
            "name": "net_type",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "description": "디지털 자산 입출금에 사용되는 블록체인 네트워크 식별자.\n조회 대상을 네트워크 식별자로 한정하기 위한 필터 파라미터입니다.\n"
            },
            "example": "BTC"
          }
        ],
        "responses": {
          "200": {
            "description": "Object of deposit availability",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "required": [
                    "currency",
                    "net_type",
                    "is_deposit_possible",
                    "deposit_impossible_reason",
                    "minimum_deposit_amount",
                    "minimum_deposit_confirmations",
                    "decimal_precision"
                  ],
                  "properties": {
                    "currency": {
                      "type": "string",
                      "description": "조회하고자 하는 통화 코드",
                      "example": "BTC"
                    },
                    "net_type": {
                      "type": "string",
                      "nullable": true,
                      "description": "입금 네트워크 유형.\n업비트에서 사용하는 블록체인 네트워크 구분자입니다.\n\n[예시] ETH, TRX, SOL\n",
                      "example": "BTC"
                    },
                    "is_deposit_possible": {
                      "type": "boolean",
                      "description": "입금 가능 여부",
                      "example": true
                    },
                    "deposit_impossible_reason": {
                      "type": "string",
                      "description": "입금 불가 이유\n※ \"is_deposit_possible\"가 \"false\"일 경우, 메시지가 제공됩니다.\n",
                      "example": "네트워크 업그레이드로 인한 입출금 일시 중단"
                    },
                    "minimum_deposit_amount": {
                      "type": "string",
                      "format": "decimal",
                      "description": "최소 입금 수량",
                      "example": 0
                    },
                    "minimum_deposit_confirmations": {
                      "type": "integer",
                      "description": "최소 입금 컨펌 수.\n업비트에서 해당 자산이 입금으로 인정되기까지 요구되는 블록체인 네트워크 상의 컨펌 수입니다.\n",
                      "example": 1
                    },
                    "decimal_precision": {
                      "type": "integer",
                      "description": "입금 시 적용되는 소수점 자릿수",
                      "example": 6
                    }
                  }
                },
                "examples": {
                  "Successful Example": {
                    "value": {
                      "currency": "BTC",
                      "net_type": "BTC",
                      "is_deposit_possible": false,
                      "deposit_impossible_reason": "네트워크 업그레이드로 인한 입출금 일시 중단",
                      "minimum_deposit_amount": "0",
                      "minimum_deposit_confirmations": 1,
                      "decimal_precision": 8
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
                  "invalid enum error": {
                    "value": {
                      "error": {
                        "name": "validation_error",
                        "message": "\"field name\" does not have a valid value"
                      }
                    }
                  },
                  "missing field error": {
                    "value": {
                      "error": {
                        "name": "validation_error",
                        "message": "net_type is missing, net_type does not have a valid value, net_type is empty"
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