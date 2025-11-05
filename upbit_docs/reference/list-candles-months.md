# 월(Month) 캔들 조회

월 단위 캔들 목록을 조회합니다.

[block:html]
{
  "html": "<div class=\"accordion-changelog\">\n    <input type=\"checkbox\" id=\"api-changelog\">\n    <label for=\"api-changelog\">\n        <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Revision History <i class=\"fa-solid fa-angle-right\"></i> </div>\n    </label>\n\n    <div class=\"accordion-changelog-content\">\n        <table class=\"custom-table\">\n            <thead>\n                <tr>\n                    <th>반영 버전</th>\n                    <th>반영 일자</th>\n                    <th>변경 사항</th>\n                </tr>\n            </thead>\n            <tbody>\n                <tr>\n                    <td class=\"code-col\">-</td>\n                    <td>2018-06-21</td>\n                    <td>API 신규 지원</td>\n                </tr>\n            </tbody>\n        </table>\n    </div>\n</div>\n\n<div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Rate Limit</div>\n<div class=\"box-rate-limit\">\n  초당 최대 10회 호출할 수 있습니다. IP 단위로 측정되며 [캔들 그룹] 내에서 요청 가능 횟수를 공유합니다.\n</div>"
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
    "/candles/months": {
      "get": {
        "operationId": "list-candles-months",
        "summary": "월(Month) 캔들 조회",
        "tags": [
          "캔들(OHLCV)"
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
            "name": "market",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "description": "조회하고자 하는 페어(거래쌍)",
              "example": "KRW-BTC"
            },
            "allowReserved": true
          },
          {
            "name": "to",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string",
              "description": "조회 기간의 종료 시각. \n지정한 시각 이전 캔들을 조회합니다. 미지정시 요청 시각을 기준으로 최근 캔들이 조회됩니다.\n\nISO 8601 형식의 datetime으로 아래와 같이 요청 할 수 있습니다. 실제 요청 시에는 공백 및 특수문자가 정상적으로 처리되도록 URL 인코딩을 수행해야 합니다.\n\n[예시] \n2025-06-24T04:56:53Z\n2025-06-24 04:56:53\n2025-06-24T13:56:53+09:00\n",
              "example": "2024-01-01T00:00:00"
            }
          },
          {
            "name": "count",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "description": "조회하고자 하는 캔들의 개수.\n최대 200개의 캔들 조회를 지원하며, 기본값은 1입니다.\n",
              "example": 200,
              "default": 1
            },
            "allowReserved": true
          }
        ],
        "responses": {
          "200": {
            "description": "List of candles",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": [
                      "market",
                      "candle_date_time_utc",
                      "candle_date_time_kst",
                      "opening_price",
                      "high_price",
                      "low_price",
                      "trade_price",
                      "timestamp",
                      "candle_acc_trade_price",
                      "candle_acc_trade_volume",
                      "first_day_of_period"
                    ],
                    "properties": {
                      "market": {
                        "type": "string",
                        "description": "페어(거래쌍)의 코드\n\n[예시] \"KRW-BTC\"\n",
                        "example": "KRW-BTC"
                      },
                      "candle_date_time_utc": {
                        "type": "string",
                        "description": "캔들 구간의 시작 시각 (UTC 기준)\n\n[형식] yyyy-MM-dd'T'HH:mm:ss\n",
                        "example": "2025-06-23T14:29:59"
                      },
                      "candle_date_time_kst": {
                        "type": "string",
                        "description": "캔들 구간의 시작 시각 (KST 기준)\n\n[형식] yyyy-MM-dd'T'HH:mm:ss\n",
                        "example": "2025-06-23T23:29:59"
                      },
                      "opening_price": {
                        "type": "number",
                        "format": "double",
                        "description": "시가.\n해당 캔들의 첫 거래 가격입니다.\n",
                        "example": 142340000
                      },
                      "high_price": {
                        "type": "number",
                        "format": "double",
                        "description": "고가.\n해당 캔들의 최고 거래 가격입니다.\n",
                        "example": 142340000
                      },
                      "low_price": {
                        "type": "number",
                        "format": "double",
                        "description": "저가.\n해당 캔들의 최저 거래 가격입니다.\n",
                        "example": 142340000
                      },
                      "trade_price": {
                        "type": "number",
                        "format": "double",
                        "description": "종가.\n해당 페어의 현재 가격입니다.\n",
                        "example": 142340000
                      },
                      "timestamp": {
                        "type": "integer",
                        "format": "int64",
                        "description": "해당 캔들의 마지막 틱이 저장된 시각의 타임스탬프 (ms)\n",
                        "example": 1750688999123
                      },
                      "candle_acc_trade_price": {
                        "type": "number",
                        "format": "double",
                        "description": "해당 캔들 동안의 누적 거래 금액\n",
                        "example": 185042
                      },
                      "candle_acc_trade_volume": {
                        "type": "number",
                        "format": "double",
                        "description": "해당 캔들 동안의 누적 거래된 디지털 자산의 수량\n",
                        "example": 0.0013
                      },
                      "first_day_of_period": {
                        "type": "string",
                        "description": "캔들 집계 시작일자\n\n[형식] yyyy-MM-dd\n",
                        "example": "2025-06-23"
                      }
                    }
                  }
                },
                "examples": {
                  "Successful Example": {
                    "value": [
                      {
                        "market": "KRW-BTC",
                        "candle_date_time_utc": "2025-06-30T00:00:00",
                        "candle_date_time_kst": "2025-06-30T09:00:00",
                        "opening_price": 147996000,
                        "high_price": 149755000,
                        "low_price": 144265000,
                        "trade_price": 148336000,
                        "timestamp": 1751605274309,
                        "candle_acc_trade_price": 677950313447.2709,
                        "candle_acc_trade_volume": 4603.1776237,
                        "first_day_of_period": "2025-06-30"
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
                  "parameter range error": {
                    "value": {
                      "error": {
                        "name": 400,
                        "message": "Invalid parameter. Check the given value!"
                      }
                    }
                  },
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