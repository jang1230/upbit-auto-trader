# V4 자동매수 미구현 기능 분석

**작성일**: 2025-11-10
**발견 경위**: 사용자 질문 - "분봉이나 이런거에따라서 옵션3개가있어야하지않니?"
**결론**: ✅ 정확한 지적 - **GUI 미구현**

---

## 📋 계획된 기능 vs 실제 구현

### 1. 계획 문서 (TOPIC_9_AUTO_BUY_LOGIC.md)

#### 3가지 투자 스타일 프리셋 (line 510-600)

| 스타일 | 타임프레임 | RSI | MACD | Volume | 예상 거래 빈도 |
|--------|-----------|-----|------|--------|----------------|
| **보수적 (Conservative)** | 4시간봉 (240) | (14, 30/70) | (12, 26, 9) | 2.0x | 하루 1~5번 |
| **균형형 (Balanced)** ⭐ | 1시간봉 (60) | (14, 30/70) | (12, 26, 9) | 2.0x | 하루 5~15번 |
| **적극적 (Aggressive)** | 15분봉 (15) | (14, 30/70) | (10, 20, 7) | 3.0x | 하루 15~30번 |

#### GUI 설계 (line 707-857)

```
┌─ 자동매수 설정 ────────────────────────────────────┐
│                                                  │
│ 투자 스타일 선택                                  │
│                                                  │
│ ○ 보수적 (4시간봉)                                │
│   └ 직장인, 하루 1번 확인, 안정 최우선            │
│   └ 예상: 하루 1~5번 매수 (50개 전체)             │
│                                                  │
│ ● 균형형 (1시간봉) ⭐ 추천                        │
│   └ 안전+수익 균형, 하루 2~3번 확인               │
│   └ 예상: 하루 5~15번 매수 (50개 전체)            │
│                                                  │
│ ○ 적극적 (15분봉)                                 │
│   └ 빠른 수익, 수시 확인 가능                     │
│   └ 예상: 하루 15~30번 매수 (50개 전체)           │
│                                                  │
│ [프리셋]  [초기화]  [고급 설정]  [저장]          │
└──────────────────────────────────────────────────┘
```

**설계된 UI 요소**:
- ✅ 라디오 버튼 3개 (보수적/균형형/적극적)
- ✅ 각 스타일별 설명 문구
- ✅ 예상 거래 빈도 안내
- ✅ 기본값: 균형형 (1시간봉)

---

## 2. 실제 구현 상태

### ✅ 백엔드 코드 (100% 완성)

#### V4AutoBuyStrategy.py (line 36-104)

```python
class V4AutoBuyStrategy(BaseStrategy):
    # Preset 정의
    PRESETS = {
        "conservative": {
            "candle_unit": "240",  # 4시간
            "indicators": {
                "rsi": {
                    "enabled": True,
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70
                },
                "macd": {
                    "enabled": True,
                    "fast": 12,
                    "slow": 26,
                    "signal": 9
                },
                "volume": {
                    "enabled": True,
                    "period": 20,
                    "threshold": 2.0
                }
            }
        },
        "balanced": {
            "candle_unit": "60",  # 1시간
            "indicators": {
                "rsi": {
                    "enabled": True,
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70
                },
                "macd": {
                    "enabled": True,
                    "fast": 12,
                    "slow": 26,
                    "signal": 9
                },
                "volume": {
                    "enabled": True,
                    "period": 20,
                    "threshold": 2.0
                }
            }
        },
        "aggressive": {
            "candle_unit": "15",  # 15분
            "indicators": {
                "rsi": {
                    "enabled": True,
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70
                },
                "macd": {
                    "enabled": True,
                    "fast": 10,  # 더 빠른 반응
                    "slow": 20,
                    "signal": 7
                },
                "volume": {
                    "enabled": True,
                    "period": 20,
                    "threshold": 3.0  # 더 높은 기준
                }
            }
        }
    }

    def __init__(
        self,
        symbol: str,
        investment_style: str = "balanced",  # ← 파라미터 있음
        candle_unit: str = None,
        indicators_config: Dict[str, Any] = None,
        **kwargs
    ):
        # Preset 적용
        if investment_style in self.PRESETS:
            preset = self.PRESETS[investment_style]
            self.candle_unit = preset["candle_unit"]
            self.indicators_config = preset["indicators"]
        # ...
```

**상태**: ✅ **100% 구현 완료**

---

#### V4TradingEngine.py (line 194-199)

```python
strategy = V4AutoBuyStrategy(
    symbol=symbol,
    investment_style=auto_config.get("investment_style", "balanced"),  # ← 읽어옴
    candle_unit=auto_config.get("candle_unit", "60"),
    indicators_config=auto_config.get("indicators", {})
)
```

**상태**: ✅ **100% 구현 완료**

---

#### config_manager.py (line 312-318)

```python
"buy_settings": {
    "mode": "auto",
    "auto_config": {
        "enabled": True,
        "investment_style": "balanced",  # ← 기본값 하드코딩
        "candle_unit": "60",
        "indicators": {
            # ...
        }
    }
}
```

**상태**: ✅ **기본값 설정 완료**

---

### ❌ GUI 코드 (0% 미구현)

#### group_settings_dialog.py 현재 상태

**있는 것** (line 72-90):
```python
# 3가지 프리셋 버튼
presets = [
    ("자동매수 + 자동매도", "auto_auto"),
    ("자동매수 + 수동매도", "auto_manual"),
    ("수동매수 + 자동매도", "manual_auto"),
]
```

→ 이것은 **거래 방식 프리셋** (매수/매도 자동화 여부)

**없는 것**:
```python
# ❌ 투자 스타일 선택 UI가 없음!
# ❌ 보수적/균형형/적극적 라디오 버튼 없음!
# ❌ 4시간봉/1시간봉/15분봉 선택 불가!
```

---

## 3. 문제 분석

### 현재 동작 방식

```python
# config_manager.py:315
"investment_style": "balanced"  # ← 항상 균형형으로 고정
```

→ **사용자가 선택할 수 없음!**

### 예상했던 동작 방식

```
[GUI] 사용자가 라디오 버튼 선택
  ○ 보수적
  ● 균형형  ← 사용자 선택
  ○ 적극적
       ↓
[설정] investment_style = "balanced"
       ↓
[엔진] V4AutoBuyStrategy(..., investment_style="balanced")
       ↓
[전략] PRESETS["balanced"] 적용
       → candle_unit="60" (1시간봉)
       → MACD(12, 26, 9)
       → Volume(2.0x)
```

### 실제 동작 방식

```
[설정] investment_style = "balanced" (하드코딩)
       ↓
[엔진] V4AutoBuyStrategy(..., investment_style="balanced")
       ↓
[전략] PRESETS["balanced"] 적용
       → 항상 1시간봉으로 고정
```

---

## 4. 미구현 UI 요소 상세

### 4.1 필요한 위젯

```python
# group_settings_dialog.py에 추가 필요

# 1. 투자 스타일 선택 그룹박스
investment_style_group = QGroupBox("📊 투자 스타일")
investment_style_layout = QVBoxLayout()

# 2. 라디오 버튼 3개
self.conservative_radio = QRadioButton("○ 보수적 (4시간봉)")
self.balanced_radio = QRadioButton("● 균형형 (1시간봉) ⭐ 추천")
self.aggressive_radio = QRadioButton("○ 적극적 (15분봉)")

# 3. 설명 라벨
conservative_label = QLabel(
    "   └ 직장인, 하루 1번 확인, 안정 최우선\n"
    "   └ 예상: 하루 1~5번 매수 (50개 전체)"
)
balanced_label = QLabel(
    "   └ 안전+수익 균형, 하루 2~3번 확인\n"
    "   └ 예상: 하루 5~15번 매수 (50개 전체)"
)
aggressive_label = QLabel(
    "   └ 빠른 수익, 수시 확인 가능\n"
    "   └ 예상: 하루 15~30번 매수 (50개 전체)"
)

# 4. 시그널 연결
self.conservative_radio.toggled.connect(self._on_investment_style_changed)
self.balanced_radio.toggled.connect(self._on_investment_style_changed)
self.aggressive_radio.toggled.connect(self._on_investment_style_changed)
```

### 4.2 이벤트 핸들러

```python
def _on_investment_style_changed(self):
    """투자 스타일 변경 시"""
    if self.conservative_radio.isChecked():
        investment_style = "conservative"
        candle_unit = "240"  # 4시간봉
        macd_config = {"fast": 12, "slow": 26, "signal": 9}
        volume_threshold = 2.0

    elif self.balanced_radio.isChecked():
        investment_style = "balanced"
        candle_unit = "60"  # 1시간봉
        macd_config = {"fast": 12, "slow": 26, "signal": 9}
        volume_threshold = 2.0

    elif self.aggressive_radio.isChecked():
        investment_style = "aggressive"
        candle_unit = "15"  # 15분봉
        macd_config = {"fast": 10, "slow": 20, "signal": 7}  # 파라미터 변경
        volume_threshold = 3.0  # Threshold 상향

        # 경고 메시지
        QMessageBox.warning(
            self,
            "⚠️ 적극적 투자 스타일 선택",
            "하루 15~30번의 매수 신호가 발생할 수 있으며,\n"
            "많은 포지션 관리가 필요합니다.\n\n"
            "초보자의 경우 매도 타점을 놓쳐 수익을\n"
            "실현하지 못할 수 있습니다.\n\n"
            "권장: '균형형' 스타일로 시작 후\n"
            "      익숙해지면 변경하세요."
        )

    # 설정 업데이트
    self.current_investment_style = investment_style
    self.current_candle_unit = candle_unit
    # ...
```

### 4.3 설정 저장

```python
def _save_settings(self):
    """설정 저장"""
    group_settings = {
        "buy_settings": {
            "mode": "auto" if self.auto_buy_radio.isChecked() else "manual",
            "auto_config": {
                "enabled": True,
                "investment_style": self.current_investment_style,  # ← 저장
                "candle_unit": self.current_candle_unit,
                "indicators": {
                    # ...
                }
            }
        },
        # ...
    }
```

---

## 5. 구현 우선순위

### 긴급 (P0)
- [ ] GUI에 투자 스타일 선택 라디오 버튼 추가
- [ ] 이벤트 핸들러 구현
- [ ] 설정 저장/로드 로직 수정

### 중요 (P1)
- [ ] 적극적 스타일 선택 시 경고 메시지
- [ ] 기본값 "균형형" 프리셋 적용
- [ ] 설명 문구 표시

### 선택 (P2)
- [ ] 프리셋 미리보기 기능
- [ ] 투자 스타일별 백테스트 결과 표시
- [ ] 실시간 매수 빈도 모니터링

---

## 6. 임시 해결 방법

### 방법 1: 설정 파일 직접 수정

```json
// config/trading_config.json
{
  "groups": {
    "group_1": {
      "buy_settings": {
        "mode": "auto",
        "auto_config": {
          "investment_style": "conservative",  // ← 직접 변경
          "candle_unit": "240"                 // ← 4시간봉
        }
      }
    }
  }
}
```

**단점**: 사용자가 JSON 직접 편집 필요 (불편함)

---

### 방법 2: 코드 기본값 변경

```python
# config_manager.py:315
"investment_style": "conservative",  # balanced → conservative 변경
"candle_unit": "240",                 # 60 → 240 변경
```

**단점**: 모든 그룹에 일괄 적용, GUI 없으면 변경 불가

---

## 7. 정확한 구현 범위

### ✅ 이미 구현된 것

| 항목 | 파일 | 상태 |
|------|------|------|
| **Preset 정의** | `v4_auto_buy_strategy.py:36-104` | ✅ 100% |
| **Preset 적용 로직** | `v4_auto_buy_strategy.py:132-142` | ✅ 100% |
| **설정 읽기** | `v4_trading_engine.py:196` | ✅ 100% |
| **기본값 설정** | `config_manager.py:315` | ✅ 100% |

**총 백엔드 코드**: ✅ **100% 완성**

---

### ❌ 미구현된 것

| 항목 | 파일 | 상태 |
|------|------|------|
| **투자 스타일 라디오 버튼** | `group_settings_dialog.py` | ❌ 0% |
| **설명 문구 라벨** | `group_settings_dialog.py` | ❌ 0% |
| **스타일 변경 핸들러** | `group_settings_dialog.py` | ❌ 0% |
| **경고 메시지** | `group_settings_dialog.py` | ❌ 0% |
| **설정 저장/로드** | `group_settings_dialog.py` | ❌ 0% |

**총 GUI 코드**: ❌ **0% 미구현**

---

## 8. 설계 문서 vs 구현 비교

### TOPIC_9_AUTO_BUY_LOGIC.md (2025-01-24)

**문서 내용**:
- ✅ 3가지 프리셋 상세 설명 (line 510-600)
- ✅ GUI 모형도 (line 707-857)
- ✅ 웹서치 근거 (line 85-380)
- ✅ 타임프레임별 지표 파라미터 (line 85-380)

**실제 구현**:
- ✅ 백엔드: 문서대로 100% 구현
- ❌ GUI: 0% 미구현

---

## 9. 예상 작업 시간

### GUI 구현

| 작업 | 예상 시간 |
|------|----------|
| 라디오 버튼 + 레이아웃 | 30분 |
| 이벤트 핸들러 | 20분 |
| 설정 저장/로드 | 15분 |
| 경고 메시지 | 10분 |
| 테스트 | 15분 |
| **합계** | **1.5시간** |

**난이도**: ⭐⭐ (낮음)
**이유**: 백엔드 완성, GUI 위젯 추가만 필요

---

## 10. 테스트 시나리오

### 시나리오 1: 보수적 스타일 선택

```
1. "그룹 관리" → "자동매수 설정"
2. ○ 보수적 (4시간봉) 선택
3. 저장
4. V4 엔진 시작

예상 동작:
- candle_unit = "240"
- 4시간마다 신호 체크
- 하루 1~5번 매수 신호
```

### 시나리오 2: 적극적 스타일 선택 + 경고

```
1. "그룹 관리" → "자동매수 설정"
2. ○ 적극적 (15분봉) 선택
   → ⚠️ 경고 메시지 표시
3. "계속하기" 클릭
4. 저장

예상 동작:
- candle_unit = "15"
- MACD(10, 20, 7) 적용
- Volume 3.0x 적용
- 15분마다 신호 체크
- 하루 15~30번 매수 신호
```

### 시나리오 3: 설정 변경 후 재시작

```
1. 균형형 → 보수적으로 변경
2. 저장
3. V4 엔진 재시작

예상 동작:
- 기존 포지션 유지
- 새 매수 신호: 4시간봉 기준
```

---

## 11. 결론

### 사용자 지적 내용

> "분봉이나 이런거에따라서 옵션3개가있어야하지않니? 그건 제대로 아직 구현이안된거같은데"

### 검증 결과

**✅ 정확한 지적입니다!**

**이유**:
1. 설계 문서에 3가지 프리셋 명시됨
2. 백엔드 코드는 100% 구현됨
3. **GUI만 0% 미구현**
4. 현재는 "균형형"으로 하드코딩 상태

### 구현 필요 사항

**필수**:
- GUI에 투자 스타일 선택 라디오 버튼 추가
- 이벤트 핸들러 및 설정 저장

**선택**:
- 경고 메시지
- 프리셋 미리보기

### 현재 사용 방법

**임시 해결책**:
```json
// config/trading_config.json 직접 수정
"investment_style": "conservative"  // balanced, aggressive
"candle_unit": "240"                 // 60, 15
```

**정식 해결책**:
- GUI 구현 후 라디오 버튼으로 선택

---

**마지막 업데이트**: 2025-11-10
**작성자**: Claude (Sonnet 4.5)
**상태**: 미구현 기능 확인 완료, GUI 구현 필요
