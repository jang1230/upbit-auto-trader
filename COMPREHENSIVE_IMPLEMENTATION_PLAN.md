# 완전한 구현 계획 - 전체 아키텍처 기반

**날짜**: 2025-11-14
**브랜치**: `claude/expert-strategy-clone-01ELiN8eY3EZwEi2gSx4xARg`
**목표**: 테스트 피드백 이슈 해결 (빠짐없는 전체 스택 구현)

---

## 📐 프로그램 아키텍처 분석

### 레이어 구조

```
┌─────────────────────────────────────────────────────────┐
│  Presentation Layer (GUI)                               │
│  - auto_buy_settings_dialog_v2.py                       │
│  - expert_strategy_widget.py                            │
│  - group_management_dialog.py                           │
│  - manual_buy_dialog.py (신규)                          │
│  - v4_custom_settings_dialog.py (신규)                  │
└─────────────────────────────────────────────────────────┘
                          ↓↑ (User Input / Display)
┌─────────────────────────────────────────────────────────┐
│  Business Logic Layer (Core)                            │
│  - v4_trading_engine.py         ← 메인 거래 로직        │
│  - group_manager.py             ← 그룹 관리             │
│  - position_manager.py          ← 포지션 CRUD           │
│  - trade_history_manager.py     ← 거래 내역 기록        │
│  - strategies/                  ← 전략 실행             │
│    - v4_auto_buy_strategy.py                            │
│    - expert_strategy.py                                 │
└─────────────────────────────────────────────────────────┘
                          ↓↑ (Config / Data)
┌─────────────────────────────────────────────────────────┐
│  Data Access Layer (Storage)                            │
│  - config_manager.py            ← Config 로드/저장      │
│  - config/trading_config.json   ← 설정 저장            │
│  - config/schemas/*.json        ← 스키마 검증           │
│  - data/positions_live.json     ← 포지션 데이터         │
│  - data/positions_dryrun.json                           │
│  - data/trade_history.json      ← 거래 내역             │
└─────────────────────────────────────────────────────────┘
                          ↓↑ (Orders / Market Data)
┌─────────────────────────────────────────────────────────┐
│  External Layer (Integration)                           │
│  - upbit_api.py                 ← REST API              │
│  - upbit_websocket.py           ← WebSocket             │
│  - telegram_bot.py              ← 알림                  │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Issue #1: V4 Custom 수치 가시성 (전체 스택)

### 개요
- **문제**: V4 Custom 선택 시 하단 수치가 잘림
- **해결**: 별도 다이얼로그로 분리
- **난이도**: ⭐⭐ Medium
- **예상 시간**: 40분

---

### 1.1 GUI Layer 변경

#### 파일 1: `gui/v4_custom_settings_dialog.py` (신규, 200 lines)

**역할**: V4 Custom 전략의 상세 설정 다이얼로그

**클래스 구조**:
```python
class V4CustomSettingsDialog(QDialog):
    """
    V4 Custom 투자 스타일 상세 설정

    설정 항목:
    - RSI 설정 (기간, 과매도, 과매수)
    - MACD 설정 (Fast, Slow, Signal)
    - Volume 설정 (기간, 임계값)
    """

    def __init__(self, config: dict, parent=None):
        """
        Args:
            config: V4 auto_config 딕셔너리
                {
                    "indicators": {
                        "rsi": {...},
                        "macd": {...},
                        "volume": {...}
                    }
                }
        """

    def _create_rsi_section(self) -> QGroupBox:
        """RSI 설정 그룹박스 생성"""
        # - 기간 (SpinBox, 5~30, 기본 14)
        # - 과매도 (SpinBox, 10~40, 기본 30)
        # - 과매수 (SpinBox, 60~90, 기본 70)

    def _create_macd_section(self) -> QGroupBox:
        """MACD 설정 그룹박스 생성"""
        # - Fast (SpinBox, 5~20, 기본 12)
        # - Slow (SpinBox, 15~40, 기본 26)
        # - Signal (SpinBox, 5~15, 기본 9)

    def _create_volume_section(self) -> QGroupBox:
        """Volume 설정 그룹박스 생성"""
        # - 기간 (SpinBox, 10~50, 기본 20)
        # - 임계값 (DoubleSpinBox, 1.0~5.0, 기본 2.0)

    def get_config(self) -> dict:
        """
        현재 설정 반환

        Returns:
            {
                "indicators": {
                    "rsi": {
                        "enabled": True,
                        "period": 14,
                        "oversold": 30,
                        "overbought": 70
                    },
                    "macd": {...},
                    "volume": {...}
                }
            }
        """

    def _validate_inputs(self) -> bool:
        """입력 검증"""
        # MACD Fast < Slow 확인
        # RSI 과매도 < 과매수 확인
```

**UI 레이아웃**:
```
┌─────────────────────────────────────────┐
│ V4 Custom 전략 고급 설정                 │
├─────────────────────────────────────────┤
│ 📊 RSI 설정                              │
│   기간:       [14]                       │
│   과매도:     [30]                       │
│   과매수:     [70]                       │
├─────────────────────────────────────────┤
│ 📈 MACD 설정                             │
│   Fast:       [12]                       │
│   Slow:       [26]                       │
│   Signal:     [9]                        │
├─────────────────────────────────────────┤
│ 📦 Volume 설정                           │
│   기간:       [20]                       │
│   임계값:     [2.0]                      │
└─────────────────────────────────────────┘
│           [취소]  [확인]                 │
└─────────────────────────────────────────┘
```

---

#### 파일 2: `gui/auto_buy_settings_dialog.py` (수정, +50 lines)

**변경 사항**:

1. Custom 선택 시 고급 설정 버튼 추가
```python
def _create_v4_form(self):
    # ... 기존 코드

    # 투자 스타일 드롭다운
    self.style_combo = QComboBox()
    self.style_combo.addItems([
        "Aggressive", "Balanced", "Conservative", "Custom"
    ])
    self.style_combo.currentTextChanged.connect(
        self._on_investment_style_changed
    )

    # Custom 고급 설정 버튼 (초기 숨김)
    self.custom_advanced_btn = QPushButton("🔧 고급 설정 (Custom 지표 조정)")
    self.custom_advanced_btn.setVisible(False)
    self.custom_advanced_btn.clicked.connect(self._open_custom_dialog)
    layout.addWidget(self.custom_advanced_btn)

def _on_investment_style_changed(self, style: str):
    """투자 스타일 변경 시 호출"""
    if style == "Custom":
        self.custom_advanced_btn.setVisible(True)
    else:
        self.custom_advanced_btn.setVisible(False)

def _open_custom_dialog(self):
    """V4 Custom 설정 다이얼로그 열기"""
    from gui.v4_custom_settings_dialog import V4CustomSettingsDialog

    # 현재 설정 로드
    current_config = self.config.get("auto_config", {})

    dialog = V4CustomSettingsDialog(current_config, self)
    if dialog.exec():
        # 설정 업데이트
        updated_config = dialog.get_config()
        self.config["auto_config"]["indicators"] = updated_config["indicators"]
        logger.info(f"✅ V4 Custom 설정 업데이트됨: {updated_config}")
```

2. get_config() 수정
```python
def get_config(self) -> dict:
    # ... 기존 코드

    if investment_style == "custom":
        # Custom 지표 설정 포함
        return {
            "strategy": "v4_auto_buy",
            "investment_style": "custom",
            "indicators": self.config.get("auto_config", {}).get("indicators", {
                # 기본값
            }),
            ...
        }
```

---

### 1.2 Data Layer 변경

#### 파일: `config/schemas/trading_config_schema.json` (수정)

**변경 없음** - 기존 스키마가 이미 Custom indicators 지원

---

### 1.3 Business Logic Layer 변경

#### 파일: `core/strategies/v4_auto_buy_strategy.py` (변경 없음)

**이유**: Custom 지표는 이미 구현되어 있음. GUI에서만 입력 방식 개선.

---

### 1.4 데이터 흐름

```
사용자 입력
  ↓
V4 전략 선택 → Custom 선택
  ↓
[고급 설정] 버튼 클릭
  ↓
V4CustomSettingsDialog.exec()
  ↓
사용자가 RSI/MACD/Volume 조정
  ↓
[확인] 클릭 → get_config()
  ↓
auto_buy_settings_dialog.config["auto_config"]["indicators"] 업데이트
  ↓
[저장] 클릭 → GroupUnifiedSettingsDialog.get_config()
  ↓
ConfigManager.save_config(config)
  ↓
trading_config.json 저장
  ↓
V4TradingEngine._load_group_strategies()
  ↓
V4AutoBuyStrategy(indicators=custom_indicators)
```

---

### 1.5 테스트 체크리스트

- [ ] V4 Custom 선택 시 [고급 설정] 버튼 표시
- [ ] 버튼 클릭 시 다이얼로그 팝업
- [ ] RSI/MACD/Volume 값 조정 가능
- [ ] 검증 실패 시 에러 메시지 (Fast >= Slow)
- [ ] [확인] 클릭 시 메인 다이얼로그로 값 전달
- [ ] 저장 후 Config 파일에 반영
- [ ] 재로드 시 Custom 값 유지

---

## 🎯 Issue #2: Expert 슬라이더 정밀도 (전체 스택)

### 개요
- **문제**: 슬라이더로 0.62, 0.68 등 정확한 값 선택 불가
- **해결**: 슬라이더 + DoubleSpinBox 조합
- **난이도**: ⭐⭐ Medium
- **예상 시간**: 30분

---

### 2.1 GUI Layer 변경

#### 파일: `gui/expert_strategy_widget.py` (수정, +100 lines)

**변경 전**:
```python
# 현재 (추정)
rsi_slider = QSlider(Qt.Horizontal)
rsi_slider.setRange(0, 100)
rsi_slider.setValue(int(0.65 * 100))
```

**변경 후**:
```python
def _create_weight_row(
    self,
    label: str,
    default_value: float,
    min_val: float = 0.0,
    max_val: float = 1.0,
    step: float = 0.01
) -> tuple:
    """
    가중치 조정 행 생성 (슬라이더 + SpinBox)

    Args:
        label: 지표 이름 (예: "RSI")
        default_value: 기본 가중치 (예: 0.65)
        min_val: 최소값
        max_val: 최대값
        step: SpinBox 증감 단위

    Returns:
        (layout, slider, spinbox) 튜플
    """
    layout = QHBoxLayout()

    # 레이블
    label_widget = QLabel(f"{label}:")
    label_widget.setMinimumWidth(100)
    label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    layout.addWidget(label_widget)

    # 슬라이더 (0~100 정수)
    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.setSingleStep(5)  # 5% 단위
    slider.setPageStep(10)   # 10% 단위
    slider.setValue(int(default_value * 100))
    slider.setTickPosition(QSlider.TicksBelow)
    slider.setTickInterval(10)
    layout.addWidget(slider, stretch=3)

    # DoubleSpinBox (0.0~1.0, 0.01 단위)
    spinbox = QDoubleSpinBox()
    spinbox.setRange(min_val, max_val)
    spinbox.setSingleStep(step)
    spinbox.setDecimals(2)
    spinbox.setValue(default_value)
    spinbox.setMinimumWidth(80)
    spinbox.setMaximumWidth(100)
    spinbox.setAlignment(Qt.AlignCenter)
    spinbox.setStyleSheet("""
        QDoubleSpinBox {
            font-size: 11pt;
            font-weight: bold;
        }
    """)
    layout.addWidget(spinbox, stretch=1)

    # 양방향 동기화
    slider.valueChanged.connect(
        lambda v: spinbox.blockSignals(True) or
                  spinbox.setValue(v / 100.0) or
                  spinbox.blockSignals(False)
    )
    spinbox.valueChanged.connect(
        lambda v: slider.blockSignals(True) or
                  slider.setValue(int(v * 100)) or
                  slider.blockSignals(False)
    )

    return layout, slider, spinbox


def _create_custom_weights_section(self):
    """Custom 가중치 조정 섹션 생성"""
    group = QGroupBox("🎯 가중치 조정")
    main_layout = QVBoxLayout()

    # 5개 지표 생성
    indicators = [
        ("RSI 가중치", "rsi", 0.65),
        ("MACD 가중치", "macd", 0.60),
        ("Bollinger Bands 가중치", "bollinger", 0.55),
        ("Volume 가중치", "volume", 0.65),
        ("Trend 가중치", "trend", 0.50)
    ]

    self.weight_widgets = {}  # {indicator_id: (slider, spinbox)}

    for display_name, indicator_id, default_val in indicators:
        layout, slider, spinbox = self._create_weight_row(
            display_name, default_val
        )
        main_layout.addLayout(layout)
        self.weight_widgets[indicator_id] = (slider, spinbox)

    # 안내 문구
    info_label = QLabel(
        "💡 슬라이더로 빠르게 조정하거나, 숫자를 직접 입력하세요.\n"
        "   가중치 범위: 0.0 (사용 안 함) ~ 1.0 (최대 중요도)"
    )
    info_label.setWordWrap(True)
    info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 10px;")
    main_layout.addWidget(info_label)

    # 신뢰도 임계값
    threshold_layout = QHBoxLayout()
    threshold_label = QLabel("신뢰도 임계값:")
    threshold_label.setMinimumWidth(100)
    threshold_layout.addWidget(threshold_label)

    self.threshold_spin = QSpinBox()
    self.threshold_spin.setRange(0, 100)
    self.threshold_spin.setSingleStep(5)
    self.threshold_spin.setValue(50)
    self.threshold_spin.setSuffix(" %")
    threshold_layout.addWidget(self.threshold_spin, stretch=3)
    threshold_layout.addStretch(1)

    main_layout.addLayout(threshold_layout)

    group.setLayout(main_layout)
    return group


def get_custom_weights(self) -> dict:
    """Custom 가중치 반환"""
    return {
        indicator_id: spinbox.value()  # SpinBox에서 정확한 값
        for indicator_id, (slider, spinbox) in self.weight_widgets.items()
    }


def get_config(self) -> dict:
    """설정 반환"""
    if self.profile_combo.currentText() == "Custom":
        return {
            "expert_profile": "custom",
            "custom_weights": self.get_custom_weights(),
            "custom_threshold": self.threshold_spin.value(),
            "candle_unit": self.candle_combo.currentText(),
            ...
        }
```

---

### 2.2 Data Layer 변경

#### 파일: `config/schemas/trading_config_schema.json` (변경 없음)

**이유**: Custom weights 스키마 이미 존재

---

### 2.3 Business Logic Layer 변경

#### 파일: `core/strategies/expert_strategy.py` (변경 없음)

**이유**: Custom weights 로직 이미 구현됨

---

### 2.4 데이터 흐름

```
사용자 입력
  ↓
Expert 전략 선택 → Custom 프로필 선택
  ↓
슬라이더 드래그 또는 SpinBox 직접 입력
  ↓
slider.valueChanged → spinbox.setValue() (양방향 동기화)
  ↓
[저장] 클릭 → get_custom_weights()
  ↓
{
  "rsi": 0.62,  ← SpinBox 값 (정확함!)
  "macd": 0.68,
  ...
}
  ↓
ConfigManager.save_config()
  ↓
trading_config.json 저장
  ↓
V4TradingEngine._load_group_strategies()
  ↓
ExpertStrategy(custom_weights={...})
```

---

### 2.5 테스트 체크리스트

- [ ] 슬라이더 드래그 시 SpinBox 값 동기화
- [ ] SpinBox 직접 입력 시 슬라이더 위치 동기화
- [ ] 0.62, 0.68 등 모든 값 입력 가능
- [ ] 저장 후 Config에 정확한 값 저장 (0.62 그대로)
- [ ] 재로드 시 슬라이더와 SpinBox 모두 정확한 위치

---

## 🎯 Issue #3: 수동매수 기능 복원 (전체 스택) ⭐ Critical

### 개요
- **문제**: 자동매수만 지원, 수동매수 불가능
- **영향**: 원래 3가지 모드 → 1가지 (기능 퇴보)
- **해결**: 매수 모드 선택 추가 (자동 vs 수동)
- **난이도**: ⭐⭐⭐⭐ High
- **예상 시간**: 3시간

---

### 3.1 Config Schema 변경 (최우선)

#### 파일: `config/schemas/trading_config_schema.json` (수정, +30 lines)

**buy_settings 스키마 확장**:

```json
{
  "buy_settings": {
    "type": "object",
    "required": ["mode"],
    "properties": {
      "mode": {
        "type": "string",
        "enum": ["auto", "manual", "disabled"],
        "description": "Buy mode: auto (strategy-based), manual (direct buy), disabled"
      },
      "auto_config": {
        "type": "object",
        "description": "Auto buy configuration (required when mode=auto)",
        "required": ["enabled", "strategy"],
        "properties": {
          "enabled": {
            "type": "boolean"
          },
          "strategy": {
            "type": "string",
            "enum": ["v4_auto_buy", "expert"]
          },
          // ... (기존 V4/Expert 필드)
        }
      },
      "buy_amount_krw": {
        "type": "number",
        "minimum": 5000,
        "description": "Buy amount in KRW (used in both auto and manual mode)"
      }
    },
    "allOf": [
      {
        "if": {
          "properties": {"mode": {"const": "auto"}}
        },
        "then": {
          "required": ["auto_config"]
        }
      },
      {
        "if": {
          "properties": {"mode": {"const": "manual"}}
        },
        "then": {
          "required": ["buy_amount_krw"]
        }
      }
    ]
  }
}
```

**변경 포인트**:
1. `mode` 필드 필수화 (`auto` / `manual` / `disabled`)
2. `auto_config`는 `mode=auto`일 때만 필수
3. `buy_amount_krw`는 모든 모드에서 사용 (공통 필드)
4. Conditional validation (if-then 사용)

---

### 3.2 Config Manager 변경

#### 파일: `core/config_manager.py` (수정, +60 lines)

**마이그레이션 로직 추가**:

```python
def _migrate_buy_settings(self, config: Dict[str, Any]) -> bool:
    """
    buy_settings에 'mode' 필드 추가 (V4 내부 마이그레이션)

    기존 설정:
        {
            "buy_settings": {
                "auto_config": {...}
            }
        }

    마이그레이션 후:
        {
            "buy_settings": {
                "mode": "auto",  ← 추가
                "auto_config": {...}
            }
        }
    """
    migrated = False

    groups = config.get("groups", {})
    for group_id, group in groups.items():
        buy_settings = group.get("buy_settings", {})

        # 'mode' 필드 없음 → 자동 추가
        if "mode" not in buy_settings:
            # auto_config 존재 → mode=auto
            if "auto_config" in buy_settings:
                buy_settings["mode"] = "auto"
            else:
                # auto_config 없음 → mode=disabled
                buy_settings["mode"] = "disabled"

            migrated = True
            print(f"🔄 그룹 '{group_id}': mode='{buy_settings['mode']}' 추가됨")

    return migrated


def load_config(self, auto_migrate: bool = True) -> Dict[str, Any]:
    # ... 기존 코드

    # V4 내부 마이그레이션
    migrated1 = self._migrate_strategy_field(self.config)
    migrated2 = self._migrate_buy_settings(self.config)  # ← 추가

    if migrated1 or migrated2:
        print("🔄 설정 업데이트됨")
        self.save_config(self.config)
```

---

### 3.3 GUI Layer 변경 (핵심)

#### 파일 1: `gui/auto_buy_settings_dialog_v2.py` (대폭 수정, +250 lines)

**구조 변경**:

```python
class AutoBuySettingsDialogV2(QDialog):
    """
    자동매수 설정 다이얼로그 V2.1

    구조:
    1. 매수 모드 선택 (자동 vs 수동)
    2. 자동매수 → V4/Expert 선택
    3. 수동매수 → 안내 메시지
    """

    def __init__(self, config: dict = None, parent=None):
        self.config = config or self._get_default_config()

        # 매수 모드 (기본값: auto)
        self.current_buy_mode = self.config.get("mode", "auto")

        self._init_ui()
        self._load_config()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # === 1단계: 매수 모드 선택 ===
        mode_group = self._create_buy_mode_selection()
        main_layout.addWidget(mode_group)

        # === 공통 매수금액 (모든 모드에서 사용) ===
        buy_amount_group = self._create_buy_amount_group()
        main_layout.addWidget(buy_amount_group)

        # === 2단계: 모드별 컨텐츠 스택 ===
        self.mode_stack = QStackedWidget()

        # 자동매수 페이지
        auto_page = self._create_auto_buy_page()
        self.mode_stack.addWidget(auto_page)  # index 0

        # 수동매수 페이지
        manual_page = self._create_manual_buy_page()
        self.mode_stack.addWidget(manual_page)  # index 1

        main_layout.addWidget(self.mode_stack)

    def _create_buy_mode_selection(self) -> QGroupBox:
        """매수 모드 선택 그룹"""
        group = QGroupBox("🎯 매수 모드 선택")
        layout = QVBoxLayout()

        # 자동매수 라디오
        self.auto_buy_radio = QRadioButton(
            "🤖 자동매수 (전략 기반 - V4/Expert)"
        )
        self.auto_buy_radio.setStyleSheet("QRadioButton { padding: 8px; }")

        auto_desc = QLabel(
            "   └─ V4 또는 Expert 전략이 매수 시점을 자동 판단합니다.\n"
            "      DCA/익절/손절도 자동 실행됩니다."
        )
        auto_desc.setStyleSheet("color: #666; font-size: 9pt;")

        # 수동매수 라디오
        self.manual_buy_radio = QRadioButton(
            "✋ 수동매수 (직접 선택 - DCA/익절/손절만 자동)"
        )
        self.manual_buy_radio.setStyleSheet("QRadioButton { padding: 8px; }")

        manual_desc = QLabel(
            "   └─ 최초 매수는 수동으로 진행합니다.\n"
            "      이후 DCA/익절/손절은 자동 실행됩니다."
        )
        manual_desc.setStyleSheet("color: #666; font-size: 9pt;")

        layout.addWidget(self.auto_buy_radio)
        layout.addWidget(auto_desc)
        layout.addSpacing(10)
        layout.addWidget(self.manual_buy_radio)
        layout.addWidget(manual_desc)

        group.setLayout(layout)

        # 이벤트 연결
        self.auto_buy_radio.toggled.connect(self._on_buy_mode_changed)

        return group

    def _create_auto_buy_page(self) -> QWidget:
        """자동매수 페이지 (기존 구조)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # V4/Expert 선택 (기존 코드)
        strategy_group = QGroupBox("📊 자동매수 전략 선택")
        strategy_layout = QVBoxLayout()

        self.v4_radio = QRadioButton("📊 V4 전략 (3개 지표)")
        self.expert_radio = QRadioButton("🎯 Expert 전략 (5개 지표)")

        strategy_layout.addWidget(self.v4_radio)
        strategy_layout.addWidget(self.expert_radio)
        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # V4/Expert 폼 스택 (기존 코드)
        scroll_area = QScrollArea()
        self.strategy_stack = QStackedWidget()

        # V4 위젯
        self.v4_widget = self._create_v4_widget()
        self.strategy_stack.addWidget(self.v4_widget)

        # Expert 위젯
        self.expert_widget = self._create_expert_widget()
        self.strategy_stack.addWidget(self.expert_widget)

        scroll_area.setWidget(self.strategy_stack)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # 라디오 이벤트
        self.v4_radio.toggled.connect(self._on_strategy_changed)

        return widget

    def _create_manual_buy_page(self) -> QWidget:
        """수동매수 페이지"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 안내 메시지
        info_group = QGroupBox("ℹ️ 수동매수 모드 안내")
        info_layout = QVBoxLayout()

        info_label = QLabel(
            "<b>수동매수 모드란?</b><br><br>"

            "최초 매수는 사용자가 직접 선택하지만, "
            "이후 DCA/익절/손절은 자동으로 실행되는 모드입니다.<br><br>"

            "<b>✅ 자동 실행:</b><br>"
            "• DCA (추가매수): 설정된 비율만큼 하락 시 자동 매수<br>"
            "• 익절: 설정된 수익률 도달 시 자동 매도<br>"
            "• 손절: 설정된 손실률 도달 시 자동 매도<br><br>"

            "<b>❌ 수동 실행:</b><br>"
            "• 최초 매수: 그룹 관리 → '수동 매수' 버튼 클릭<br><br>"

            "<b>사용 방법:</b><br>"
            "1. 이 설정 저장<br>"
            "2. DCA/익절/손절 레벨 설정 (다음 탭)<br>"
            "3. 그룹 관리 → 코인 선택 → '수동 매수' 버튼 클릭<br>"
            "4. 매수 후 DCA/익절/손절은 자동 처리됨"
        )
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.RichText)
        info_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                background-color: #E3F2FD;
                border: 2px solid #2196F3;
                border-radius: 8px;
                font-size: 10pt;
                line-height: 1.6;
            }
        """)
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()
        return widget

    def _on_buy_mode_changed(self):
        """매수 모드 변경 시"""
        if self.auto_buy_radio.isChecked():
            self.current_buy_mode = "auto"
            self.mode_stack.setCurrentIndex(0)  # 자동매수 페이지
        else:
            self.current_buy_mode = "manual"
            self.mode_stack.setCurrentIndex(1)  # 수동매수 페이지

    def _load_config(self):
        """설정 로드"""
        buy_mode = self.config.get("mode", "auto")

        # 매수 모드 라디오 선택
        if buy_mode == "manual":
            self.manual_buy_radio.setChecked(True)
            self.mode_stack.setCurrentIndex(1)
        else:
            self.auto_buy_radio.setChecked(True)
            self.mode_stack.setCurrentIndex(0)

            # 자동매수: V4/Expert 선택
            auto_config = self.config.get("auto_config", {})
            strategy = auto_config.get("strategy", "v4_auto_buy")

            if strategy == "expert":
                self.expert_radio.setChecked(True)
                self.strategy_stack.setCurrentIndex(1)
            else:
                self.v4_radio.setChecked(True)
                self.strategy_stack.setCurrentIndex(0)

        # 매수금액
        buy_amount = self.config.get("buy_amount_krw", 50000)
        self.buy_amount_spin.setValue(buy_amount)

    def get_config(self) -> dict:
        """현재 설정 반환"""
        buy_amount = self.buy_amount_spin.value()

        if self.current_buy_mode == "manual":
            # 수동매수
            return {
                "mode": "manual",
                "buy_amount_krw": buy_amount
                # auto_config 없음
            }
        else:
            # 자동매수
            if self.v4_radio.isChecked():
                return {
                    "mode": "auto",
                    "auto_config": {
                        "strategy": "v4_auto_buy",
                        "investment_style": ...,
                        "buy_amount_krw": buy_amount,
                        ...
                    }
                }
            else:
                return {
                    "mode": "auto",
                    "auto_config": {
                        "strategy": "expert",
                        "expert_profile": ...,
                        "buy_amount_krw": buy_amount,
                        ...
                    }
                }
```

---

#### 파일 2: `gui/manual_buy_dialog.py` (신규, 250 lines)

**역할**: 수동 매수 실행 다이얼로그

```python
class ManualBuyDialog(QDialog):
    """
    수동 매수 다이얼로그

    기능:
    - 그룹 내 코인 선택
    - 매수 금액 입력 (기본값: buy_amount_krw)
    - 시장가 매수 실행
    - Position 생성
    """

    buy_executed = Signal(str, str, float, float)  # (group_id, symbol, price, amount)

    def __init__(
        self,
        group_id: str,
        config_manager: ConfigManager,
        position_manager: PositionManager,
        upbit_api: UpbitAPI,
        parent=None
    ):
        """
        Args:
            group_id: 그룹 ID
            config_manager: ConfigManager 인스턴스
            position_manager: PositionManager 인스턴스
            upbit_api: UpbitAPI 인스턴스
        """
        super().__init__(parent)

        self.group_id = group_id
        self.config_manager = config_manager
        self.position_manager = position_manager
        self.upbit_api = upbit_api

        # 그룹 설정 로드
        config = self.config_manager.load_config()
        self.group_config = config["groups"][group_id]
        self.buy_settings = self.group_config["buy_settings"]

        # 기본 매수금액
        self.default_buy_amount = self.buy_settings.get("buy_amount_krw", 50000)

        self.setWindowTitle(f"💰 수동 매수 - {self.group_config['name']}")
        self.setMinimumWidth(500)

        self._init_ui()
        self._load_current_prices()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 코인 선택
        coin_group = QGroupBox("📊 코인 선택")
        coin_layout = QFormLayout()

        self.coin_combo = QComboBox()
        self.coin_combo.addItems(self.group_config["coins"])
        self.coin_combo.currentTextChanged.connect(self._on_coin_changed)

        coin_layout.addRow("코인:", self.coin_combo)

        # 현재가 표시
        self.price_label = QLabel("로딩 중...")
        self.price_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        coin_layout.addRow("현재가:", self.price_label)

        coin_group.setLayout(coin_layout)
        layout.addWidget(coin_group)

        # 매수 설정
        buy_group = QGroupBox("💰 매수 설정")
        buy_layout = QFormLayout()

        # 매수 금액
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(5000, 10000000)
        self.amount_spin.setSingleStep(5000)
        self.amount_spin.setValue(self.default_buy_amount)
        self.amount_spin.setSuffix(" 원")
        self.amount_spin.valueChanged.connect(self._update_quantity_preview)

        buy_layout.addRow("매수 금액:", self.amount_spin)

        # 수량 미리보기
        self.quantity_label = QLabel("계산 중...")
        buy_layout.addRow("예상 수량:", self.quantity_label)

        buy_group.setLayout(buy_layout)
        layout.addWidget(buy_group)

        # 안내 메시지
        info_label = QLabel(
            "ℹ️ 시장가 매수가 실행됩니다.\n"
            "   매수 후 DCA/익절/손절은 자동으로 처리됩니다."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #FFF3E0;
                border-radius: 5px;
            }
        """)
        layout.addWidget(info_label)

        # 버튼
        button_layout = QHBoxLayout()

        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.buy_btn = QPushButton("💰 시장가 매수")
        self.buy_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.buy_btn.clicked.connect(self._execute_buy)
        button_layout.addWidget(self.buy_btn)

        layout.addLayout(button_layout)

    def _load_current_prices(self):
        """현재가 로드 (첫 코인)"""
        if self.coin_combo.count() > 0:
            symbol = self.coin_combo.currentText()
            self._on_coin_changed(symbol)

    def _on_coin_changed(self, symbol: str):
        """코인 변경 시 현재가 업데이트"""
        try:
            ticker = self.upbit_api.get_ticker(symbol)
            self.current_price = ticker["trade_price"]
            self.price_label.setText(f"{self.current_price:,.0f} 원")
            self._update_quantity_preview()
        except Exception as e:
            logger.error(f"❌ 현재가 조회 실패: {e}")
            self.price_label.setText("조회 실패")

    def _update_quantity_preview(self):
        """수량 미리보기 업데이트"""
        if hasattr(self, "current_price") and self.current_price > 0:
            amount = self.amount_spin.value()
            quantity = amount / self.current_price
            self.quantity_label.setText(f"{quantity:.8f} (약 {quantity:.4f})")

    def _execute_buy(self):
        """매수 실행"""
        symbol = self.coin_combo.currentText()
        amount = self.amount_spin.value()

        # 확인 다이얼로그
        reply = QMessageBox.question(
            self,
            "매수 확인",
            f"<b>{symbol}</b>을(를) <b>{amount:,}원</b>에 시장가 매수하시겠습니까?<br><br>"
            f"현재가: {self.current_price:,.0f} 원<br>"
            f"예상 수량: {amount / self.current_price:.8f}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # 매수 실행
            logger.info(f"🛒 수동 매수 실행: {symbol} {amount}원")

            # Upbit API 호출
            order_result = self.upbit_api.buy_market_order(
                symbol=symbol,
                price=amount
            )

            # Position 생성
            position = self.position_manager.create_position(
                group_id=self.group_id,
                symbol=symbol,
                buy_price=order_result["avg_price"],
                quantity=order_result["executed_volume"],
                buy_amount_krw=amount,
                order_id=order_result["uuid"]
            )

            # 성공 메시지
            QMessageBox.information(
                self,
                "매수 완료",
                f"✅ 매수가 완료되었습니다!<br><br>"
                f"코인: {symbol}<br>"
                f"평균 가격: {order_result['avg_price']:,.2f} 원<br>"
                f"수량: {order_result['executed_volume']:.8f}<br><br>"
                f"이제 DCA/익절/손절이 자동으로 처리됩니다."
            )

            # Signal 발생
            self.buy_executed.emit(
                self.group_id,
                symbol,
                order_result["avg_price"],
                order_result["executed_volume"]
            )

            self.accept()

        except Exception as e:
            logger.error(f"❌ 수동 매수 실패: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "매수 실패",
                f"❌ 매수에 실패했습니다.<br><br>"
                f"오류: {str(e)}<br><br>"
                f"잔고 또는 API 키를 확인해주세요."
            )
```

---

#### 파일 3: `gui/group_management_dialog.py` (수정, +80 lines)

**수동 매수 버튼 추가**:

```python
def _update_group_info_panel(self, group_id: str):
    """
    그룹 정보 패널 업데이트

    수동매수 모드일 때 '수동 매수' 버튼 표시
    """
    # ... 기존 코드

    # 그룹 설정 로드
    config = self.config_manager.load_config()
    group = config["groups"][group_id]
    buy_settings = group.get("buy_settings", {})
    buy_mode = buy_settings.get("mode", "auto")

    # 매수 모드 표시
    mode_text = {
        "auto": "🤖 자동매수",
        "manual": "✋ 수동매수",
        "disabled": "❌ 비활성화"
    }.get(buy_mode, buy_mode)

    mode_label = QLabel(f"매수 모드: {mode_text}")
    self.info_layout.addWidget(mode_label)

    # 수동 매수 버튼 (수동매수 모드일 때만)
    if buy_mode == "manual":
        manual_buy_btn = QPushButton("💰 수동 매수")
        manual_buy_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                margin: 10px 0;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        manual_buy_btn.clicked.connect(
            lambda: self._open_manual_buy_dialog(group_id)
        )
        self.info_layout.addWidget(manual_buy_btn)


def _open_manual_buy_dialog(self, group_id: str):
    """수동 매수 다이얼로그 열기"""
    from gui.manual_buy_dialog import ManualBuyDialog

    # Upbit API 확인
    if not self.upbit_api:
        QMessageBox.warning(
            self,
            "API 키 필요",
            "수동 매수를 하려면 Upbit API 키가 필요합니다.\n"
            "설정에서 API 키를 등록해주세요."
        )
        return

    # Dry-run 모드 확인
    config = self.config_manager.load_config()
    if config["global_settings"]["dry_run"]:
        QMessageBox.warning(
            self,
            "Dry-run 모드",
            "현재 Dry-run (모의투자) 모드입니다.\n"
            "실제 매수는 실행되지 않습니다."
        )

    # 다이얼로그 열기
    dialog = ManualBuyDialog(
        group_id=group_id,
        config_manager=self.config_manager,
        position_manager=self.position_manager,
        upbit_api=self.upbit_api,
        parent=self
    )

    # 매수 완료 시 포지션 목록 새로고침
    dialog.buy_executed.connect(self._on_manual_buy_executed)

    dialog.exec()


def _on_manual_buy_executed(
    self,
    group_id: str,
    symbol: str,
    price: float,
    amount: float
):
    """수동 매수 완료 시 호출"""
    logger.info(f"✅ 수동 매수 완료: {group_id} / {symbol} / {price} / {amount}")

    # 그룹 정보 패널 새로고침
    self._update_group_info_panel(group_id)

    # Telegram 알림 (선택)
    if self.telegram_bot:
        self.telegram_bot.send_message(
            f"✅ 수동 매수 완료\n\n"
            f"그룹: {group_id}\n"
            f"코인: {symbol}\n"
            f"가격: {price:,.2f} 원\n"
            f"수량: {amount:.8f}"
        )
```

---

### 3.4 Business Logic Layer 변경

#### 파일: `core/v4_trading_engine.py` (수정, +50 lines)

**수동매수 모드 처리**:

```python
def _load_group_strategies(self):
    """그룹별 전략 로드"""
    groups = self.config.get("groups", {})

    for group_id, group in groups.items():
        buy_settings = group.get("buy_settings", {})
        buy_mode = buy_settings.get("mode", "auto")

        # 수동매수 모드는 전략 로드 안 함
        if buy_mode == "manual":
            logger.info(f"ℹ️ 그룹 '{group_id}': 수동매수 모드 (전략 없음)")
            continue

        # 자동매수 모드만 전략 로드
        if buy_mode == "auto":
            auto_config = buy_settings.get("auto_config", {})
            strategy = auto_config.get("strategy")

            if strategy == "v4_auto_buy":
                # V4 전략 생성
                ...
            elif strategy == "expert":
                # Expert 전략 생성
                ...


def _check_auto_buy_signals(self):
    """자동매수 신호 확인 (메인 루프)"""
    groups = self.config.get("groups", {})

    for group_id, group in groups.items():
        buy_settings = group.get("buy_settings", {})
        buy_mode = buy_settings.get("mode", "auto")

        # 수동매수 모드는 자동매수 스킵
        if buy_mode != "auto":
            continue

        # 자동매수 로직 실행
        ...


def _monitor_positions(self):
    """포지션 모니터링 (DCA/익절/손절)"""
    # 모든 포지션에 대해 DCA/익절/손절 체크
    # 수동매수로 생성된 포지션도 포함됨!

    positions = self.position_manager.get_all_positions()

    for position_id, position in positions.items():
        group_id = position["group_id"]
        group = self.config["groups"][group_id]

        # DCA 체크
        self._check_dca_trigger(position, group)

        # 익절 체크
        self._check_profit_trigger(position, group)

        # 손절 체크
        self._check_loss_trigger(position, group)
```

**핵심 포인트**:
- `mode=manual` 그룹은 자동매수 스킵
- DCA/익절/손절은 **모든 포지션**에 대해 실행 (수동매수 포지션 포함)

---

### 3.5 데이터 흐름 (전체)

#### 자동매수 흐름
```
GUI: 자동매수 선택 → V4/Expert 선택
  ↓
[저장] → ConfigManager.save_config()
  ↓
{
  "buy_settings": {
    "mode": "auto",
    "auto_config": {
      "strategy": "v4_auto_buy",
      ...
    }
  }
}
  ↓
V4TradingEngine.start()
  ↓
_load_group_strategies()
  ↓
V4AutoBuyStrategy 생성
  ↓
메인 루프: _check_auto_buy_signals()
  ↓
should_buy() == True
  ↓
OrderManager.buy()
  ↓
PositionManager.create_position()
  ↓
DCA/익절/손절 자동 모니터링
```

#### 수동매수 흐름
```
GUI: 수동매수 선택
  ↓
[저장] → ConfigManager.save_config()
  ↓
{
  "buy_settings": {
    "mode": "manual",
    "buy_amount_krw": 50000
  }
}
  ↓
V4TradingEngine.start()
  ↓
_load_group_strategies() → 전략 로드 스킵 (mode=manual)
  ↓
메인 루프: _check_auto_buy_signals() → 스킵 (mode != auto)
  ↓
(사용자 액션 대기)
  ↓
GUI: 그룹 관리 → [수동 매수] 버튼 클릭
  ↓
ManualBuyDialog.exec()
  ↓
사용자: 코인 선택, 금액 입력
  ↓
[시장가 매수] 클릭
  ↓
UpbitAPI.buy_market_order()
  ↓
PositionManager.create_position()
  ↓
V4TradingEngine._monitor_positions()
  ↓
DCA/익절/손절 자동 모니터링 ✅
```

---

### 3.6 Config 예시

#### 자동매수 (V4)
```json
{
  "groups": {
    "auto_group": {
      "name": "자동매수 그룹",
      "coins": ["KRW-BTC", "KRW-ETH"],
      "buy_settings": {
        "mode": "auto",
        "auto_config": {
          "enabled": true,
          "strategy": "v4_auto_buy",
          "investment_style": "balanced",
          "candle_unit": "60",
          "indicators": {...},
          "buy_amount_krw": 50000
        }
      },
      "dca_settings": {...},
      "profit_settings": {...},
      "loss_settings": {...}
    }
  }
}
```

#### 수동매수
```json
{
  "groups": {
    "manual_group": {
      "name": "수동매수 그룹",
      "coins": ["KRW-XRP", "KRW-ADA"],
      "buy_settings": {
        "mode": "manual",
        "buy_amount_krw": 30000
      },
      "dca_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": -5.0, "quantity_ratio": 100}
        ]
      },
      "profit_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": 5.0, "quantity_ratio": 100}
        ]
      },
      "loss_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": -10.0, "quantity_ratio": 100}
        ]
      }
    }
  }
}
```

**핵심 차이**:
- 자동매수: `auto_config` 존재
- 수동매수: `auto_config` 없음, `buy_amount_krw`만 존재

---

### 3.7 테스트 체크리스트

#### GUI 테스트
- [ ] 자동매수 라디오 선택 → V4/Expert 폼 표시
- [ ] 수동매수 라디오 선택 → 안내 메시지 표시
- [ ] 자동매수 저장 → Config `mode: auto`, `auto_config` 존재
- [ ] 수동매수 저장 → Config `mode: manual`, `auto_config` 없음
- [ ] 재로드 시 저장된 모드로 라디오 선택됨

#### 그룹 관리 테스트
- [ ] 수동매수 그룹 → [수동 매수] 버튼 표시
- [ ] 자동매수 그룹 → [수동 매수] 버튼 없음
- [ ] 버튼 클릭 시 ManualBuyDialog 팝업

#### 수동 매수 다이얼로그 테스트
- [ ] 그룹 코인 목록 드롭다운 표시
- [ ] 코인 선택 시 현재가 표시
- [ ] 매수 금액 입력 시 수량 미리보기 업데이트
- [ ] [시장가 매수] 클릭 시 확인 다이얼로그
- [ ] 매수 성공 시 Position 생성
- [ ] 매수 성공 메시지 표시

#### Backend 테스트
- [ ] V4TradingEngine 시작 시 수동매수 그룹 전략 로드 안 함
- [ ] 자동매수 시그널 체크 시 수동매수 그룹 스킵
- [ ] 수동매수로 생성된 Position에 대해 DCA 자동 실행
- [ ] 수동매수로 생성된 Position에 대해 익절/손절 자동 실행

---

## 📊 전체 구현 로드맵 (Phase별)

### Phase 1: UI 개선 (1.5시간)

| 작업 | 파일 | 레이어 | 시간 |
|------|------|--------|------|
| Expert 슬라이더+SpinBox | `gui/expert_strategy_widget.py` | GUI | 30분 |
| V4 Custom 다이얼로그 | `gui/v4_custom_settings_dialog.py` (신규) | GUI | 40분 |
| V4 Custom 버튼 연결 | `gui/auto_buy_settings_dialog.py` | GUI | 20분 |

**테스트**: 슬라이더 정밀도, Custom 다이얼로그 동작

---

### Phase 2: 수동매수 기능 (3시간)

#### Step 1: Config 기반 (30분)
| 작업 | 파일 | 레이어 | 시간 |
|------|------|--------|------|
| Schema 확장 | `config/schemas/trading_config_schema.json` | Data | 15분 |
| Migration 로직 | `core/config_manager.py` | Data | 15분 |

#### Step 2: GUI 구현 (1.5시간)
| 작업 | 파일 | 레이어 | 시간 |
|------|------|--------|------|
| 매수 모드 선택 UI | `gui/auto_buy_settings_dialog_v2.py` | GUI | 40분 |
| 수동매수 페이지 | `gui/auto_buy_settings_dialog_v2.py` | GUI | 20분 |
| 수동 매수 다이얼로그 | `gui/manual_buy_dialog.py` (신규) | GUI | 30분 |

#### Step 3: Backend 연동 (40분)
| 작업 | 파일 | 레이어 | 시간 |
|------|------|--------|------|
| Trading Engine 수정 | `core/v4_trading_engine.py` | Business Logic | 20분 |
| 그룹 관리 버튼 추가 | `gui/group_management_dialog.py` | GUI | 20분 |

#### Step 4: 통합 테스트 (20분)
- 자동매수 → 수동매수 전환 테스트
- 수동매수 실행 → Position 생성 확인
- DCA/익절/손절 자동 실행 확인

---

### Phase 3: 통합 테스트 (1시간)

| 테스트 시나리오 | 체크 포인트 | 시간 |
|----------------|------------|------|
| V4 Custom 전체 플로우 | 버튼 → 다이얼로그 → 저장 → 재로드 | 15분 |
| Expert Custom 슬라이더 | 0.62 입력 → 저장 → 재로드 | 10분 |
| 자동매수 V4 | 전략 → 매수 신호 → Position | 10분 |
| 자동매수 Expert | 전략 → 매수 신호 → Position | 10분 |
| 수동매수 | 다이얼로그 → 매수 → Position | 10분 |
| 수동매수 + DCA | 수동매수 → 가격 하락 → DCA 실행 | 15분 |

---

## 📁 전체 파일 변경 요약

### 신규 파일 (3개)
1. `gui/v4_custom_settings_dialog.py` (200 lines)
2. `gui/manual_buy_dialog.py` (250 lines)
3. `COMPREHENSIVE_IMPLEMENTATION_PLAN.md` (이 문서)

### 수정 파일 (6개)
1. `gui/auto_buy_settings_dialog_v2.py` (+250 lines)
2. `gui/expert_strategy_widget.py` (+100 lines)
3. `gui/group_management_dialog.py` (+80 lines)
4. `config/schemas/trading_config_schema.json` (+30 lines)
5. `core/config_manager.py` (+60 lines)
6. `core/v4_trading_engine.py` (+50 lines)

---

## 🔄 데이터 레이어 전체 흐름

```
┌─────────────────────────────────────────────────────┐
│ User Input (GUI)                                    │
│ - 자동매수 vs 수동매수 선택                          │
│ - V4/Expert 설정                                    │
│ - Custom 지표 조정                                   │
└─────────────────────────────────────────────────────┘
                         ↓ (Save)
┌─────────────────────────────────────────────────────┐
│ ConfigManager.save_config()                         │
│ - JSON 검증 (Schema)                                │
│ - 파일 쓰기                                          │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ trading_config.json                                 │
│ {                                                   │
│   "groups": {                                       │
│     "group_1": {                                    │
│       "buy_settings": {                             │
│         "mode": "auto" | "manual",                  │
│         "auto_config": {...}  // mode=auto일 때만   │
│       }                                             │
│     }                                               │
│   }                                                 │
│ }                                                   │
└─────────────────────────────────────────────────────┘
                         ↓ (Load)
┌─────────────────────────────────────────────────────┐
│ V4TradingEngine.start()                             │
│ - ConfigManager.load_config()                       │
│ - Migration (if needed)                             │
│ - Schema validation                                 │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ Business Logic                                      │
│ - _load_group_strategies()                          │
│   - mode=auto → Strategy 생성                       │
│   - mode=manual → 스킵                               │
│ - _check_auto_buy_signals()                         │
│   - mode=auto → 시그널 체크                          │
│   - mode=manual → 스킵                               │
│ - _monitor_positions()                              │
│   - 모든 포지션 DCA/익절/손절 체크                   │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ PositionManager                                     │
│ - create_position() (자동/수동 모두)                 │
│ - add_dca()                                         │
│ - update_position()                                 │
│ - close_position()                                  │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ positions_live.json / positions_dryrun.json         │
│ {                                                   │
│   "pos_1": {                                        │
│     "group_id": "manual_group",  // 수동매수 포지션  │
│     "symbol": "KRW-BTC",                            │
│     "buy_price": 85000000,                          │
│     ...                                             │
│   }                                                 │
│ }                                                   │
└─────────────────────────────────────────────────────┘
```

---

## ✅ 완료 조건 (Definition of Done)

### Issue #1: V4 Custom
- [ ] [고급 설정] 버튼 클릭 시 다이얼로그 팝업
- [ ] RSI/MACD/Volume 모든 값 조정 가능
- [ ] 검증 실패 시 에러 메시지
- [ ] 저장 후 Config 파일 반영
- [ ] 재로드 시 값 유지

### Issue #2: Expert 슬라이더
- [ ] 슬라이더 + SpinBox 동기화
- [ ] 0.62, 0.68 등 정확한 값 입력 가능
- [ ] 저장 후 Config 정확한 값 저장
- [ ] 재로드 시 슬라이더/SpinBox 정확한 위치

### Issue #3: 수동매수
- [ ] 자동/수동 모드 선택 가능
- [ ] 자동 저장 → `mode: auto`, `auto_config` 존재
- [ ] 수동 저장 → `mode: manual`, `auto_config` 없음
- [ ] 수동매수 그룹 → [수동 매수] 버튼 표시
- [ ] 수동 매수 실행 → Position 생성
- [ ] 수동매수 Position → DCA 자동 실행
- [ ] 수동매수 Position → 익절/손절 자동 실행
- [ ] V3 Config 자동 마이그레이션 (mode 필드 추가)

---

## 📅 예상 일정

- **Phase 1**: 1.5시간
- **Phase 2**: 3시간
- **Phase 3**: 1시간
- **총 예상 시간**: **5.5시간**

---

## 🎯 우선순위 (재확인)

1. **🔴 Critical**: Issue #3 수동매수 (3시간)
2. **🟠 High**: Issue #2 Expert 슬라이더 (30분)
3. **🟡 Medium**: Issue #1 V4 Custom (40분)

---

**작성일**: 2025-11-14
**작성자**: Claude AI
**문서 버전**: 1.0 (Complete Architecture Coverage)
**예상 총 작업 시간**: 5.5시간
