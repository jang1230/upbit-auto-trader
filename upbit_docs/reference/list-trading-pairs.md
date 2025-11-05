# 페어 목록 조회

업비트에서 지원하는 모든 페어 목록을 조회합니다.

[block:html]
{
  "html": "\n\n<div class=\"accordion-changelog\">\n    <input type=\"checkbox\" id=\"api-changelog\">\n    <label for=\"api-changelog\">\n        <div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Revision History <i class=\"fa-solid fa-angle-right\"></i> </div>\n    </label>\n\n    <div class=\"accordion-changelog-content\">\n        <table class=\"custom-table\">\n            <thead>\n                <tr>\n                    <th>반영 버전</th>\n                    <th>반영 일자</th>\n                    <th>변경 사항</th>\n                </tr>\n            </thead>\n            <tbody>\n                <tr>\n                    <td class=\"code-col\">-</td>\n                    <td>2024-11-20</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/mytrade_market_warning_deprecated_11_20\"> market_event 필드 신규 지원,<br>market_warning 필드 필수 여부 변경 </a></td>\n              \t</tr>\n\t\t\t\t\t\t\t\t<tr>\n                    <td class=\"code-col\">-</td>\n                    <td>2024-02-22</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/voc_update\"> 페어별 시장경보 조회 지원</a></td>\n                </tr>\n\t\t\t\t\t\t\t\t<tr>\n                    <td class=\"code-col\">-</td>\n                    <td>-</td>\n                    <td><a href=\"https://docs.upbit.com/kr/changelog/open-api-개선사항-안내-투자-유의-종목-필드-추가\"> is_details 파라미터 지원</a></td>\n                </tr>\n            </tbody>\n        </table>\n    </div>\n</div>\n\n<div class=\"APISectionHeader-heading4MUMLbp4_nLs\">Rate Limit</div>\n<div class=\"box-rate-limit\">\n  초당 최대 10회 호출할 수 있습니다. IP 단위로 측정되며 [마켓 그룹] 내에서 요청 가능 횟수를 공유합니다.\n</div>"
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
    "/market/all": {
      "get": {
        "operationId": "list-trading-pairs",
        "summary": "페어 목록 조회",
        "tags": [
          "페어(Trading Pairs)"
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
          ],
          "expanded": true
        },
        "parameters": [
          {
            "name": "is_details",
            "in": "query",
            "required": false,
            "schema": {
              "type": "boolean",
              "description": "상세 정보를 포함한 조회 여부.\ntrue로 지정하여 유의종목 지정 여부, 주의종목 지정 여부와 같은 상세 정보를 응답에 포함할 수 있습니다. 기본값은 false입니다.\n",
              "example": true
            }
          }
        ],
        "responses": {
          "200": {
            "description": "List of trading pairs",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": [
                      "market",
                      "korean_name",
                      "english_name"
                    ],
                    "properties": {
                      "market": {
                        "type": "string",
                        "description": "페어(거래쌍)의 코드\n\n[예시] \"KRW-BTC\"\n",
                        "example": "KRW-BTC"
                      },
                      "korean_name": {
                        "type": "string",
                        "description": "해당 디지털 자산의 한글명",
                        "example": "비트코인"
                      },
                      "english_name": {
                        "type": "string",
                        "description": "해당 디지털 자산의 영문명",
                        "example": "Bitcoin"
                      },
                      "market_event": {
                        "description": "종목 경보 정보",
                        "type": "object",
                        "properties": {
                          "warning": {
                            "type": "boolean",
                            "description": "유의 종목 여부. \n업비트의 시장경보 시스템에 따라 해당 페어가 유의 종목으로 지정되었는지 여부를 나타냅니다.\n※ 자세한 사항은 관련 <a href=\"https://upbit.com/service_center/notice?id=3482\">공지사항</a> 참고 바랍니다.\n",
                            "example": false
                          },
                          "caution": {
                            "description": "주의 종목 여부.\n주의 종목으로 지정된 경우, 아래의 세부 경보 유형 중 하나 이상에 해당될 수 있습니다.\n※ 자세한 사항은 관련 <a href=\"https://upbit.com/service_center/notice?id=3606\">공지사항</a> 참고 바랍니다.\n",
                            "type": "object",
                            "properties": {
                              "PRICE_FLUCTUATIONS": {
                                "type": "boolean",
                                "description": "가격 급등락 경보",
                                "example": false
                              },
                              "TRADING_VOLUME_SOARING": {
                                "type": "boolean",
                                "description": "거래량 급증 경보",
                                "example": false
                              },
                              "DEPOSIT_AMOUNT_SOARING": {
                                "type": "boolean",
                                "description": "입금량 급증 경보",
                                "example": false
                              },
                              "GLOBAL_PRICE_DIFFERENCES": {
                                "type": "boolean",
                                "description": "국내외 가격 차이 경보",
                                "example": false
                              },
                              "CONCENTRATION_OF_SMALL_ACCOUNTS": {
                                "type": "boolean",
                                "description": "소수 계정 집중 거래 경보",
                                "example": false
                              }
                            }
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
                        "market": "KRW-BTC",
                        "korean_name": "비트코인",
                        "english_name": "Bitcoin",
                        "market_event": {
                          "warning": false,
                          "caution": {
                            "PRICE_FLUCTUATIONS": false,
                            "TRADING_VOLUME_SOARING": false,
                            "DEPOSIT_AMOUNT_SOARING": false,
                            "GLOBAL_PRICE_DIFFERENCES": false,
                            "CONCENTRATION_OF_SMALL_ACCOUNTS": false
                          }
                        }
                      },
                      {
                        "market": "KRW-ETH",
                        "korean_name": "이더리움",
                        "english_name": "Ethereum",
                        "market_event": {
                          "warning": true,
                          "caution": {
                            "PRICE_FLUCTUATIONS": false,
                            "TRADING_VOLUME_SOARING": false,
                            "DEPOSIT_AMOUNT_SOARING": false,
                            "GLOBAL_PRICE_DIFFERENCES": false,
                            "CONCENTRATION_OF_SMALL_ACCOUNTS": false
                          }
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
                  "parameter type error": {
                    "value": {
                      "error": {
                        "name": 400,
                        "message": "Type mismatch error. Check the parameters type!"
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