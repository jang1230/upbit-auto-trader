# 계정주 확인 서비스 지원 거래소 목록 조회

계정주 확인 서비스를 지원하는 거래소 목록을 조회합니다.

[block:html]
{
  "html": "<div class=\"callout-section\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i>  계정주 확인 서비스 제공 거래소 목록 확인\n      </div>\n    계정주 확인 서비스를 제공하는 전체 거래소 목록은 <a href=\"https://support.upbit.com/hc/ko/articles/5048002559897-%EC%9E%85%EC%B6%9C%EA%B8%88-%EA%B0%80%EB%8A%A5-%EA%B0%80%EC%83%81%EC%9E%90%EC%82%B0%EC%82%AC%EC%97%85%EC%9E%90-%EB%A6%AC%EC%8A%A4%ED%8A%B8\">업비트 고객 센터 > 이용 가이드 > 트래블룰</a>에서도 확인할 수 있습니다.\n  </div>"
}
[/block]


[block:html]
{
  "html": "<div class=\"accordion-changelog\">\n    <input type=\"checkbox\" id=\"api-changelog\">\n    <label for=\"api-changelog\">\n        <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Revision History <i class=\"fa-solid fa-angle-right\"></i> </div>\n    </label>\n\n    <div class=\"accordion-changelog-content\">\n        <table class=\"custom-table\">\n            <thead>\n                <tr>\n                    <th>반영 버전</th>\n                    <th>반영 일자</th>\n                    <th>변경 사항</th>\n                </tr>\n            </thead>\n            <tbody>\n                <tr>\n                    <td class=\"code-col\">-</td>\n                    <td>2024-04-24</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/travelrule_verification\"> '트래블룰 지원 거래소 목록 조회' 기능 신규 지원</a></td>\n                </tr>\n            </tbody>\n        </table>\n    </div>\n</div>\n\n<div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Rate Limit</div>\n<div class=\"box-rate-limit\">\n  초당 최대 30회 호출할 수 있습니다. 계정단위로 측정되며 [Exchange 기본 그룹] 내에서 요청 가능 횟수를 공유합니다.\n</div>\n\n  <br>\n  <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">API Key Permission</div>\n  <div class=\"box-rate-limit\">\n    <a href=\"auth\">인증</a>이 필요한 API로, [입금조회] 권한이 설정된 API Key를 사용해야 합니다. <br>\n    권한 오류(out_of_scope) 오류가 발생한다면, <a href=\"https://upbit.com/mypage/open_api_management\">API Key 관리 메뉴</a>에서 권한 설정을 확인해주세요.\n  </div>"
}
[/block]

# OpenAPI definition
```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "Travelrule API",
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
    "/travel_rule/vasps": {
      "get": {
        "operationId": "list-travelrule-vasps",
        "summary": "계정주 확인 서비스 지원 거래소 목록 조회",
        "tags": [
          "트래블룰 검증"
        ],
        "security": [
          {
            "BearerAuth": []
          }
        ],
        "x-readme": {
          "code-samples": [
            {
              "language": "curl",
              "code": "curl --request GET \\\n    --url 'https://api.upbit.com/v1/travel_rule/vasps' \\\n    --header 'Authorization: Bearer {JWT_TOKEN}' \\\n    --header 'Accept: application/json'\n"
            },
            {
              "language": "python",
              "install": "pip install requests pyjwt python-dotenv",
              "code": "import os\nimport uuid\nimport jwt\nimport requests\nfrom dotenv import load_dotenv\n\nload_dotenv()\n\nBASE_URL = \"https://api.upbit.com\"\nPATH = \"/v1/travel_rule/vasps\"\n\nACCESS_KEY = os.environ[\"UPBIT_OPEN_API_ACCESS_KEY\"]\nSECRET_KEY = os.environ[\"UPBIT_OPEN_API_SECRET_KEY\"]\n\npayload = {\n  \"access_key\": ACCESS_KEY,\n  \"nonce\": str(uuid.uuid4()),\n}\n\njwt_token = jwt.encode(payload, SECRET_KEY, algorithm=\"HS256\")\n\nres = requests.get(f\"{BASE_URL}{PATH}\", headers={\"Authorization\": f\"Bearer {jwt_token}\", \"Accept\": \"application/json\"})\nprint(res.json())\n"
            },
            {
              "language": "node",
              "name": "Axios",
              "install": "npm install axios jsonwebtoken uuid",
              "code": "const axios = require(\"axios\");\nconst { sign } = require(\"jsonwebtoken\");\nconst { v4: uuidv4 } = require(\"uuid\");\nrequire(\"dotenv\").config();\n\nconst baseURL = \"https://api.upbit.com\";\nconst path = \"/v1/travel_rule/vasps\";\n\nconst ACCESS_KEY = process.env.UPBIT_OPEN_API_ACCESS_KEY;\nconst SECRET_KEY = process.env.UPBIT_OPEN_API_SECRET_KEY;\n\nconst payload = {\n  access_key: ACCESS_KEY,\n  nonce: uuidv4(),\n};\n\nconst jwtToken = sign(payload, SECRET_KEY);\n\nconst options = {\n  method: \"GET\",\n  url: `${baseURL}${path}`,\n  headers: {\n    Authorization: `Bearer ${jwtToken}`,\n    Accept: \"application/json\",\n  },\n};\n\naxios\n  .request(options)\n  .then((response) => console.log(response.data))\n  .catch((error) => console.error(error));\n"
            },
            {
              "language": "java",
              "code": "package main;\n\nimport com.auth0.jwt.JWT;\nimport com.auth0.jwt.algorithms.Algorithm;\nimport java.io.IOException;\nimport java.nio.charset.StandardCharsets;\nimport java.security.MessageDigest;\nimport java.security.NoSuchAlgorithmException;\nimport java.util.HashMap;\nimport java.util.Map;\nimport java.util.Objects;\nimport java.util.UUID;\nimport java.util.stream.Collectors;\nimport okhttp3.OkHttpClient;\nimport okhttp3.Request;\nimport okhttp3.Response;\n\npublic class StatusService {\n    private static final String BASE_URL = \"https://api.upbit.com\";\n    private static final String PATH = \"/v1/travel_rule/vasps\";\n\n    public static void main(String[] args) throws NoSuchAlgorithmException, IOException {\n        String accessKey = System.getenv(\"UPBIT_OPEN_API_ACCESS_KEY\");\n        String secretKey = System.getenv(\"UPBIT_OPEN_API_SECRET_KEY\");\n\n        Map<String, String> params = new HashMap<>();\n        params.put(\"access_key\", accessKey);\n        params.put(\"nonce\", UUID.randomUUID().toString());\n        String queryString = params.entrySet().stream()\n            .map(e -> e.getKey() + \"=\" + String.valueOf(e.getValue()))\n            .collect(Collectors.joining(\"&\"));\n\n        MessageDigest md = MessageDigest.getInstance(\"SHA-512\");\n        md.update(queryString.getBytes(StandardCharsets.UTF_8));\n        StringBuilder sb = new StringBuilder();\n        for (byte b : md.digest()) {\n            sb.append(String.format(\"%02x\", b));\n        }\n        String queryHash = sb.toString();\n\n        Algorithm algorithm = Algorithm.HMAC512(secretKey.getBytes(StandardCharsets.UTF_8));\n        String jwtToken = JWT.create()\n            .withClaim(\"access_key\", accessKey)\n            .withClaim(\"nonce\", UUID.randomUUID().toString())\n            .withClaim(\"query_hash\", queryHash)\n            .withClaim(\"query_hash_alg\", \"SHA512\")\n            .sign(algorithm);\n\n        String authHeader = \"Bearer \" + jwtToken;\n\n        OkHttpClient client = new OkHttpClient();\n        Request request = new Request.Builder()\n            .url(BASE_URL + PATH + \"?\" + queryString)\n            .get()\n            .addHeader(\"Content-Type\", \"application/json\")\n            .addHeader(\"Authorization\", authHeader)\n            .build();\n\n        try (Response response = client.newCall(request).execute()) {\n            System.out.println(response.code());\n            System.out.println(Objects.requireNonNull(response.body()).string());\n        }\n    }\n}\n"
            }
          ]
        },
        "responses": {
          "200": {
            "description": "List of exchanges",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": [
                      "vasp_name",
                      "vasp_uuid",
                      "depositable",
                      "withdrawable"
                    ],
                    "properties": {
                      "vasp_name": {
                        "type": "string",
                        "description": "거래소 이름\nVASP(가상자산사업자)의 이름입니다.\n",
                        "example": "업비트"
                      },
                      "vasp_uuid": {
                        "type": "string",
                        "description": "거래소의 유일식별자 (UUID).\n전송을 위해 고유하게 부여된 VASP 식별자입니다.\n",
                        "example": "8d4fe968-82b2-42e5-822f-3840a245f802"
                      },
                      "depositable": {
                        "type": "boolean",
                        "description": "해당 VASP로부터 업비트로의 입금 반영 가능 여부",
                        "example": true
                      },
                      "withdrawable": {
                        "type": "boolean",
                        "description": "해당 VASP로의 출금 가능 여부",
                        "example": true
                      }
                    }
                  }
                },
                "examples": {
                  "Successful Example": {
                    "value": [
                      {
                        "vasp_name": "업비트",
                        "vasp_uuid": "00000000-0000-0000-0000-000000000000",
                        "depositable": true,
                        "withdrawable": true
                      },
                      {
                        "vasp_name": "업비트 인도네시아",
                        "vasp_uuid": "00000000-0000-0000-0000-000000000000",
                        "depositable": true,
                        "withdrawable": true
                      }
                    ]
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  "_id": "68ef7ce9a70441b77323902f"
}
```