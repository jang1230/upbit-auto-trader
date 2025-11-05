# 호가 모아보기 단위 조회

종목별로 지원하는 모아보기 단위 목록을 조회합니다. 반환된 지원 단위를 호가 조회 API 사용 시 지정하여 호가를 원하는 단위로 조회할 수 있습니다.

[block:html]
{
  "html": "<div class=\"callout-section\">\n    <div class=\"callout-title\">\n      <i class=\"fa-solid fa-circle-exclamation\"></i> 호가 모아보기 기능은 현재 원화마켓만 지원합니다.\n      </div>\n      지원 대상이 아닌 종목으로 모아보기 단위 조회를 요청하는 경우 모아보기 기본값인 0만 지원 단위로 반환되니 사용에 참고해주시기 바랍니다.\n  </div>"
}
[/block]


[block:html]
{
  "html": "<div class=\"accordion-changelog\">\n    <input type=\"checkbox\" id=\"api-changelog\">\n    <label for=\"api-changelog\">\n        <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Revision History <i class=\"fa-solid fa-angle-right\"></i> </div>\n    </label>\n\n    <div class=\"accordion-changelog-content\">\n        <table class=\"custom-table\">\n            <thead>\n                <tr>\n                    <th>반영 버전</th>\n                    <th>반영 일자</th>\n                    <th>변경 사항</th>\n                </tr>\n            </thead>\n            <tbody>\n                <tr>\n                    <td class=\"code-col\">v1.4.4</td>\n                    <td>2024-01-22</td>\n                  <td><a href=\"https://docs.upbit.com/kr/changelog/tick_unit_change\">호가 모아보기 기능 신규 지원(원화 마켓)</a></td>\n                </tr>\n            </tbody>\n        </table>\n    </div>\n</div>\n\n<div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Rate Limit</div>\n<div class=\"box-rate-limit\">\n  초당 최대 10회 호출할 수 있습니다. IP 단위로 측정되며 [호가 그룹] 내에서 요청 가능 횟수를 공유합니다.\n</div>"
}
[/block]

# OpenAPI definition
```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "QUOTATION API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://api.upbit.com/v1"
    }
  ],
  "paths": {
    "/orderbook/supported_levels": {
      "get": {
        "operationId": "list-orderbook-levels",
        "summary": "호가 모아보기 단위 조회 (Deprecated)",
        "tags": [
          "호가(Orderbook)"
        ],
        "security": [
          {
            "BearerAuth": []
          }
        ],
        "x-readme": {
          "explorer-enabled": false,
          "samples-languages": [
            "shell",
            "python",
            "java",
            "node"
          ]
        },
        "parameters": [
          {
            "name": "markets",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "description": "조회하고자 하는 페어(거래쌍) 목록.\n2개 이상의 페어에 대해 조회하고자 하는 경우 쉼표(,)로 구분된 문자열 형식으로 요청합니다.\n\n[예시] KRW-BTC,KRW-ETH,BTC-ETH,BTC-XRP\n",
              "example": "KRW-BTC,KRW-ETH"
            },
            "allowReserved": true
          }
        ],
        "responses": {
          "200": {
            "description": "List of orderbook levels",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": [
                      "market",
                      "supported_levels"
                    ],
                    "properties": {
                      "market": {
                        "type": "string",
                        "description": "페어(거래쌍)의 코드\n\n[예시] \"KRW-BTC\"\n",
                        "example": "KRW-BTC"
                      },
                      "supported_levels": {
                        "type": "array",
                        "description": "해당 페어에서 지원하는 호가 모아보기 단위.\n- 0: 기본 호가단위\n- 호가 모아보기 기능은 원화마켓(KRW)에서만 지원합니다.\n  (BTC, USDT 마켓의 경우 0만 존재)\n",
                        "example": [
                          0,
                          10000,
                          100000,
                          1000000,
                          10000000,
                          100000000
                        ]
                      }
                    }
                  }
                },
                "examples": {
                  "Successful Example": {
                    "value": [
                      {
                        "market": "KRW-BTC",
                        "supported_levels": [
                          0,
                          10000,
                          100000,
                          1000000,
                          10000000,
                          100000000
                        ]
                      },
                      {
                        "market": "KRW-ETH",
                        "supported_levels": [
                          0,
                          10000,
                          100000,
                          1000000
                        ]
                      },
                      {
                        "market": "KRW-TRX",
                        "supported_levels": [
                          0,
                          1,
                          10,
                          100
                        ]
                      },
                      {
                        "market": "KRW-XRP",
                        "supported_levels": [
                          0,
                          10,
                          100,
                          1000
                        ]
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
                  "parameter type error": {
                    "value": {
                      "error": {
                        "name": 400,
                        "message": "Type mismatch error. Check the parameters type!"
                      }
                    }
                  },
                  "missing required parameter error": {
                    "value": {
                      "error": {
                        "name": 400,
                        "message": "Missing request parameter error. Check the required parameters!"
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
                  "not found error": {
                    "value": {
                      "error": {
                        "name": 404,
                        "message": "Code not found"
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
  "x-readme": {
    "explorer-enabled": true,
    "proxy-enabled": true
  },
  "_id": "68ef7ce9a70441b77323902e"
}
```