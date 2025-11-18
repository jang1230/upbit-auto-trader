# 수정 계획 - 테스트 피드백 기반

**날짜**: 2025-11-14
**브랜치**: `claude/expert-strategy-clone-01ELiN8eY3EZwEi2gSx4xARg`
**기반**: DETAILED_TEST_GUIDE.md 테스트 결과

---

## 📋 발견된 이슈

### ❌ 이슈 #1: V4 Custom 설정 수치 가시성 문제
**테스트 번호**: 테스트 5 (스크롤 기능)
**심각도**: Medium
**발견 위치**: `gui/auto_buy_settings_dialog.py` (V4 Custom 선택 시)

**문제**:
- V4 전략에서 Custom 투자 스타일 선택 시
- 하단의 RSI/MACD/Volume 값 조정 영역이 너무 작음
- **수치가 아예 보이지 않음**

**재현 방법**:
1. V4 전략 선택
2. 투자 스타일: Custom 선택
3. 스크롤 다운 → 수치 입력 필드가 잘림

---

### ❌ 이슈 #2: Expert Custom 가중치 슬라이더 정밀도 부족
**테스트 번호**: 테스트 8-2 (Custom Profile)
**심각도**: High
**발견 위치**: `gui/expert_strategy_widget.py`

**문제**:
- Expert Custom 프로필에서 가중치를 슬라이더로만 조정
- **0.6, 0.65 같은 정확한 값을 선택할 수 없음**
- 슬라이더 step이 너무 큼

**재현 방법**:
1. Expert 전략 선택
2. Custom 프로필 선택
3. 슬라이더로 0.6 맞추기 시도 → 0.55 또는 0.65로만 이동

---

### ❌ 이슈 #3: 수동매수 기능 누락 (Critical!)
**심각도**: Critical
**발견 위치**: 전체 시스템 아키텍처

**문제**:
- 원래 프로그램은 **3가지 모드** 지원:
  1. **자동매수 + 자동매도** (DCA 익절/손절)
  2. **자동매수 + 수동매도** (신호만 받고 수동 처리)
  3. **수동매수 + 자동매도** (직접 매수, DCA/익절/손절 자동)

- 현재는 **자동매수만** 지원
- **수동매수 모드가 완전히 비활성화됨**

**영향**:
- 사용자가 직접 코인을 선택해서 매수할 수 없음
- DCA/익절/손절만 자동화하고 싶은 사용자 불편
- 기존 V3 기능 대비 **기능 퇴보**

---

## 🎯 수정 계획

---

## 수정 #1: V4 Custom 수치 가시성 개선

### 옵션 A: 스크롤 영역 높이 증가 (빠른 수정)
**난이도**: ⭐ Easy
**예상 시간**: 10분

**변경 사항**:
```python
# gui/auto_buy_settings_dialog_v2.py

# 현재
self.setMinimumHeight(600)
self.setMaximumHeight(650)

# 변경 후
self.setMinimumHeight(700)  # +100px
self.setMaximumHeight(800)  # +150px
```

**장점**:
- 즉시 적용 가능
- 코드 변경 최소

**단점**:
- 해상도 낮은 모니터에서 다이얼로그가 화면 밖으로 나감
- 근본적 해결 아님

---

### 옵션 B: Custom 설정을 접이식(Collapsible) 위젯으로 변경 (권장)
**난이도**: ⭐⭐ Medium
**예상 시간**: 30분

**변경 사항**:

#### 1. V4 설정 구조 변경
```python
# 현재 구조
투자 스타일 드롭다운:
  - Aggressive
  - Balanced
  - Conservative
  - Custom ← 선택 시 하단에 필드 추가 (스크롤 필요)

# 변경 후 구조
투자 스타일 드롭다운:
  - Aggressive
  - Balanced
  - Conservative
  - Custom

[Custom 선택 시]
  → "고급 설정 표시" 버튼 추가
  → 버튼 클릭 시 새 다이얼로그 팝업 (또는 확장 위젯)
```

#### 2. UI 플로우
```
V4 전략 선택
  ↓
투자 스타일: Custom
  ↓
[🔧 고급 설정] 버튼 표시
  ↓
클릭 → "V4 Custom 설정" 다이얼로그
  ↓
RSI/MACD/Volume 상세 조정
  ↓
확인 → 메인 다이얼로그로 돌아옴
```

#### 3. 구현 계획
**파일**: `gui/v4_custom_settings_dialog.py` (신규)

```python
class V4CustomSettingsDialog(QDialog):
    """V4 Custom 투자 스타일 상세 설정 다이얼로그"""

    def __init__(self, config: dict, parent=None):
        # RSI 설정
        # - 기간
        # - 과매도
        # - 과매수

        # MACD 설정
        # - Fast
        # - Slow
        # - Signal

        # Volume 설정
        # - 기간
        # - 임계값
```

**파일**: `gui/auto_buy_settings_dialog.py` (수정)

```python
def _create_v4_form(self):
    # ...

    # Custom 선택 시
    if investment_style == "custom":
        advanced_btn = QPushButton("🔧 고급 설정 (Custom 지표 조정)")
        advanced_btn.clicked.connect(self._open_custom_dialog)
        layout.addWidget(advanced_btn)

def _open_custom_dialog(self):
    dialog = V4CustomSettingsDialog(self.config, self)
    if dialog.exec():
        self.custom_config = dialog.get_config()
```

**장점**:
- 스크롤 문제 완전 해결
- 메인 다이얼로그 깔끔 유지
- Custom 설정에 충분한 공간

**단점**:
- 다이얼로그 2개 열어야 함 (UX 복잡도 증가)

---

### 옵션 C: QTabWidget으로 분리 (미권장)
**난이도**: ⭐⭐⭐ Hard
**예상 시간**: 60분

V4 기본 설정 / V4 Custom 설정을 탭으로 분리

**단점**:
- 탭 중첩 문제 재발 (라디오 버튼 → 탭 전환의 의미 퇴색)
- UX 혼란

---

### ✅ 권장 방안: **옵션 B (접이식 위젯)**

**이유**:
1. 스크롤 문제 완전 해결
2. Custom 설정 사용자는 소수 → 별도 다이얼로그 허용 가능
3. 메인 UI 깔끔 유지

---

## 수정 #2: Expert Custom 가중치 슬라이더 정밀도 개선

### 현재 구현 (추정)
```python
# gui/expert_strategy_widget.py

# RSI 가중치 슬라이더
rsi_slider = QSlider(Qt.Horizontal)
rsi_slider.setRange(0, 100)  # 0 ~ 100 정수
rsi_slider.setValue(int(weight * 100))  # 0.70 → 70
```

**문제**:
- 슬라이더 값은 정수 (0~100)
- 0.60, 0.65, 0.70은 가능하지만 **0.62, 0.68은 불가능**
- step=5로 설정된 경우 0.60 선택 불가

---

### 해결 방안: 슬라이더 + SpinBox 조합 (권장)

**난이도**: ⭐⭐ Medium
**예상 시간**: 20분

#### UI 레이아웃
```
┌─────────────────────────────────────────┐
│ RSI 가중치                              │
│ [슬라이더━━━━━●━━━━━] [0.65 ▼]        │
│                        ↑ DoubleSpinBox  │
├─────────────────────────────────────────┤
│ MACD 가중치                             │
│ [슬라이더━━━━●━━━━━━] [0.60 ▼]        │
└─────────────────────────────────────────┘
```

#### 구현 계획
**파일**: `gui/expert_strategy_widget.py`

```python
def _create_weight_row(self, label: str, default_value: float) -> QHBoxLayout:
    """
    가중치 조정 행 생성 (슬라이더 + SpinBox)

    Args:
        label: 지표 이름 (예: "RSI")
        default_value: 기본 가중치 (예: 0.65)

    Returns:
        QHBoxLayout: [Label] [Slider] [SpinBox]
    """
    layout = QHBoxLayout()

    # 레이블
    label_widget = QLabel(f"{label} 가중치:")
    label_widget.setMinimumWidth(120)
    layout.addWidget(label_widget)

    # 슬라이더 (0~100)
    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.setSingleStep(5)  # 5% 단위
    slider.setValue(int(default_value * 100))
    layout.addWidget(slider, stretch=3)

    # SpinBox (0.0~1.0, step=0.01)
    spinbox = QDoubleSpinBox()
    spinbox.setRange(0.0, 1.0)
    spinbox.setSingleStep(0.01)  # 0.01 단위로 정밀 조정
    spinbox.setDecimals(2)  # 소수점 2자리
    spinbox.setValue(default_value)
    spinbox.setMinimumWidth(80)
    layout.addWidget(spinbox, stretch=1)

    # 슬라이더 ↔ SpinBox 동기화
    slider.valueChanged.connect(
        lambda v: spinbox.setValue(v / 100.0)
    )
    spinbox.valueChanged.connect(
        lambda v: slider.setValue(int(v * 100))
    )

    # 반환 시 참조 저장
    return layout, slider, spinbox
```

#### 사용 예시
```python
def _create_custom_weights_section(self):
    group = QGroupBox("🎯 가중치 조정 (0.0 ~ 1.0)")
    layout = QVBoxLayout()

    # 5개 지표
    self.rsi_layout, self.rsi_slider, self.rsi_spin = \
        self._create_weight_row("RSI", 0.65)
    layout.addLayout(self.rsi_layout)

    self.macd_layout, self.macd_slider, self.macd_spin = \
        self._create_weight_row("MACD", 0.60)
    layout.addLayout(self.macd_layout)

    # ... (Bollinger, Volume, Trend)

    group.setLayout(layout)
    return group

def get_custom_weights(self) -> dict:
    """현재 가중치 값 반환"""
    return {
        "rsi": self.rsi_spin.value(),       # SpinBox에서 정확한 값
        "macd": self.macd_spin.value(),
        "bollinger": self.bb_spin.value(),
        "volume": self.volume_spin.value(),
        "trend": self.trend_spin.value()
    }
```

#### 장점
- ✅ 슬라이더로 빠른 조정 (마우스 드래그)
- ✅ SpinBox로 정밀 입력 (키보드 입력)
- ✅ 0.62, 0.68 등 모든 값 입력 가능
- ✅ 양방향 동기화로 일관성 유지

#### 단점
- UI가 약간 복잡해짐 (하지만 Custom 사용자는 고급 사용자)

---

### ✅ 권장 방안: **슬라이더 + DoubleSpinBox 조합**

**이유**:
1. 정밀도 문제 완전 해결
2. 빠른 조정 + 정확한 입력 모두 가능
3. 업계 표준 UI 패턴 (많은 프로그램에서 사용)

---

## 수정 #3: 수동매수 기능 복원 (Critical!)

### 현재 아키텍처 분석

#### V3 시스템 (과거)
```json
{
  "mode": "semi_auto",  // 또는 "full_auto"
  "trading_settings": {
    "buy_mode": "auto",      // "auto" or "manual"
    "sell_mode": "auto",     // "auto" or "manual"
    ...
  }
}
```

**3가지 조합**:
1. `buy_mode: auto`, `sell_mode: auto` → 완전 자동
2. `buy_mode: auto`, `sell_mode: manual` → 자동매수, 수동매도
3. `buy_mode: manual`, `sell_mode: auto` → 수동매수, 자동매도

---

#### V4 시스템 (현재)
```json
{
  "groups": {
    "group_1": {
      "buy_settings": {
        "mode": "auto",  // "auto", "manual", "disabled"
        "auto_config": {
          "strategy": "v4_auto_buy",  // 또는 "expert"
          ...
        }
      },
      "dca_settings": {...},      // 자동매도 (추가매수)
      "profit_settings": {...},   // 자동매도 (익절)
      "loss_settings": {...}      // 자동매도 (손절)
    }
  }
}
```

**현재 문제**:
- `buy_settings.mode`가 `"auto"`만 지원
- `"manual"` 모드가 GUI에서 선택 불가
- DCA/익절/손절은 항상 자동 (좋음!)
- **수동매수 → 자동매도 조합이 불가능**

---

### 해결 방안: 매수 모드 선택 추가

#### 옵션 A: 라디오 버튼 2단계 구조 (권장)

**난이도**: ⭐⭐⭐ Medium-High
**예상 시간**: 60분

#### UI 플로우
```
┌────────────────────────────────────────┐
│ 📊 자동매수 전략 설정                   │
├────────────────────────────────────────┤
│ [1단계] 매수 모드 선택                  │
│   ◉ 자동매수 (전략 기반)                │
│   ○ 수동매수 (직접 선택)                │
├────────────────────────────────────────┤
│ [2단계] 전략 선택 (자동매수일 때만)     │
│   ◉ V4 전략                             │
│   ○ Expert 전략                         │
├────────────────────────────────────────┤
│ 💰 1회 매수 금액                        │
│   [50,000] 원                           │
├────────────────────────────────────────┤
│ [스크롤 영역]                           │
│ (자동) V4/Expert 설정 폼                │
│ (수동) 안내 메시지                      │
└────────────────────────────────────────┘
```

#### 상세 설계

**파일**: `gui/auto_buy_settings_dialog_v2.py` (대폭 수정)

```python
class AutoBuySettingsDialogV2(QDialog):
    """
    자동매수 설정 다이얼로그 V2.1

    구조:
    1. 매수 모드 선택 (자동 vs 수동)
    2. 자동매수 → V4/Expert 선택
    3. 수동매수 → 안내 메시지만 표시
    """

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # === 1단계: 매수 모드 선택 ===
        mode_group = QGroupBox("🎯 매수 모드 선택")
        mode_layout = QVBoxLayout()

        self.auto_buy_radio = QRadioButton(
            "🤖 자동매수 (전략 기반 - V4/Expert)"
        )
        self.manual_buy_radio = QRadioButton(
            "✋ 수동매수 (직접 선택 - DCA/익절/손절만 자동)"
        )

        mode_layout.addWidget(self.auto_buy_radio)
        mode_layout.addWidget(self.manual_buy_radio)
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)

        # === 2단계: 스택 위젯 (자동 vs 수동) ===
        self.mode_stack = QStackedWidget()

        # 2-1. 자동매수 페이지
        auto_page = self._create_auto_buy_page()
        self.mode_stack.addWidget(auto_page)  # index 0

        # 2-2. 수동매수 페이지
        manual_page = self._create_manual_buy_page()
        self.mode_stack.addWidget(manual_page)  # index 1

        main_layout.addWidget(self.mode_stack)

        # 이벤트 연결
        self.auto_buy_radio.toggled.connect(self._on_mode_changed)

    def _create_auto_buy_page(self) -> QWidget:
        """
        자동매수 페이지 (기존 구조)
        - V4/Expert 라디오 버튼
        - 공통 매수금액
        - V4/Expert 설정 폼
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # === V4/Expert 선택 (기존 코드) ===
        strategy_group = QGroupBox("📊 자동매수 전략 선택")
        strategy_layout = QVBoxLayout()

        self.v4_radio = QRadioButton("📊 V4 전략 (3개 지표)")
        self.expert_radio = QRadioButton("🎯 Expert 전략 (5개 지표)")

        strategy_layout.addWidget(self.v4_radio)
        strategy_layout.addWidget(self.expert_radio)
        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # === 공통 매수금액 ===
        buy_amount_group = self._create_buy_amount_group()
        layout.addWidget(buy_amount_group)

        # === V4/Expert 폼 스택 ===
        scroll_area = QScrollArea()
        self.strategy_stack = QStackedWidget()
        # ... (기존 V4/Expert 위젯)
        scroll_area.setWidget(self.strategy_stack)
        layout.addWidget(scroll_area)

        return widget

    def _create_manual_buy_page(self) -> QWidget:
        """
        수동매수 페이지
        - 안내 메시지만 표시
        - 매수금액은 공통 필드 사용
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 안내 메시지
        info_group = QGroupBox("ℹ️ 수동매수 모드")
        info_layout = QVBoxLayout()

        info_label = QLabel(
            "수동매수 모드에서는:\n\n"
            "✅ DCA (추가매수) 자동 실행\n"
            "✅ 익절 자동 실행\n"
            "✅ 손절 자동 실행\n"
            "❌ 최초 매수는 수동 (그룹 관리 → 직접 매수)\n\n"
            "사용 방법:\n"
            "1. 이 설정 저장\n"
            "2. 그룹 관리 → 코인 선택\n"
            "3. '수동 매수' 버튼 클릭\n"
            "4. DCA/익절/손절은 자동 처리됨"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                padding: 15px;
                background-color: #E8F5E9;
                border-radius: 5px;
                font-size: 11pt;
                line-height: 1.6;
            }
        """)
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 매수금액 (수동매수 시에도 사용)
        buy_amount_group = self._create_buy_amount_group()
        layout.addWidget(buy_amount_group)

        layout.addStretch()
        return widget

    def _on_mode_changed(self):
        """매수 모드 변경 시 스택 전환"""
        if self.auto_buy_radio.isChecked():
            self.mode_stack.setCurrentIndex(0)  # 자동매수 페이지
        else:
            self.mode_stack.setCurrentIndex(1)  # 수동매수 페이지

    def get_config(self) -> dict:
        """현재 설정 반환"""

        # 매수 모드 확인
        if self.manual_buy_radio.isChecked():
            # 수동매수
            return {
                "mode": "manual",
                "buy_amount_krw": self.buy_amount_spin.value()
                # auto_config 없음
            }
        else:
            # 자동매수 (기존 로직)
            buy_amount = self.buy_amount_spin.value()

            if self.v4_radio.isChecked():
                return {
                    "mode": "auto",
                    "auto_config": {
                        "strategy": "v4_auto_buy",
                        "buy_amount_krw": buy_amount,
                        # ... V4 설정
                    }
                }
            else:
                return {
                    "mode": "auto",
                    "auto_config": {
                        "strategy": "expert",
                        "buy_amount_krw": buy_amount,
                        # ... Expert 설정
                    }
                }
```

#### Config 구조 변경
```json
// 자동매수
{
  "buy_settings": {
    "mode": "auto",
    "auto_config": {
      "strategy": "v4_auto_buy",
      "investment_style": "balanced",
      ...
    }
  }
}

// 수동매수
{
  "buy_settings": {
    "mode": "manual",
    "buy_amount_krw": 50000
    // auto_config 없음
  }
}
```

#### 그룹 관리 UI 수정
**파일**: `gui/group_management_dialog.py`

```python
def _update_group_info_panel(self, group_id: str):
    """
    그룹 정보 패널 업데이트

    수동매수일 때 '수동 매수' 버튼 표시
    """
    # ... 기존 코드

    buy_mode = group.get("buy_settings", {}).get("mode", "auto")

    if buy_mode == "manual":
        # 수동 매수 버튼 추가
        manual_buy_btn = QPushButton("💰 수동 매수 (코인 선택)")
        manual_buy_btn.clicked.connect(
            lambda: self._open_manual_buy_dialog(group_id)
        )
        self.info_layout.addWidget(manual_buy_btn)

def _open_manual_buy_dialog(self, group_id: str):
    """
    수동 매수 다이얼로그
    - 코인 드롭다운 (그룹의 코인 목록)
    - 매수 금액 (기본값: buy_amount_krw)
    - 시장가 매수 버튼
    """
    # 새 다이얼로그 구현 필요
    pass
```

---

#### 옵션 B: 별도 메뉴 추가 (미권장)
그룹 관리에 "수동 매수" 전용 메뉴 추가

**단점**:
- 설정과 실행이 분리됨
- UX 일관성 떨어짐

---

### ✅ 권장 방안: **옵션 A (라디오 버튼 2단계 구조)**

**이유**:
1. 기존 라디오 버튼 구조와 일관성 유지
2. 자동/수동 모드가 명확히 구분됨
3. Config 구조가 깔끔함 (mode: auto/manual)
4. 기능 완전 복원 (V3 수준)

---

## 📊 전체 구현 로드맵

### Phase 1: UI 개선 (Quick Wins)
**예상 시간**: 1시간
**우선순위**: High

| 작업 | 파일 | 난이도 | 시간 |
|------|------|--------|------|
| Expert 슬라이더 → 슬라이더+SpinBox | `gui/expert_strategy_widget.py` | ⭐⭐ | 20분 |
| V4 Custom → 별도 다이얼로그 | `gui/v4_custom_settings_dialog.py` (신규) | ⭐⭐ | 30분 |
| 다이얼로그 높이 증가 (임시) | `gui/auto_buy_settings_dialog_v2.py` | ⭐ | 10분 |

**테스트**:
- [ ] Expert Custom에서 0.62 입력 가능
- [ ] V4 Custom 고급 설정 버튼 표시
- [ ] 수치 모두 보임

---

### Phase 2: 수동매수 기능 복원
**예상 시간**: 2시간
**우선순위**: Critical

| 작업 | 파일 | 난이도 | 시간 |
|------|------|--------|------|
| 매수 모드 라디오 버튼 추가 | `gui/auto_buy_settings_dialog_v2.py` | ⭐⭐⭐ | 40분 |
| 수동매수 페이지 UI | `gui/auto_buy_settings_dialog_v2.py` | ⭐⭐ | 20분 |
| Config 저장/로드 로직 | `gui/auto_buy_settings_dialog_v2.py` | ⭐⭐ | 20분 |
| 그룹 관리 - 수동 매수 버튼 | `gui/group_management_dialog.py` | ⭐⭐ | 20분 |
| 수동 매수 다이얼로그 | `gui/manual_buy_dialog.py` (신규) | ⭐⭐⭐ | 40분 |

**테스트**:
- [ ] 자동매수 선택 → V4/Expert 선택 가능
- [ ] 수동매수 선택 → 안내 메시지 표시
- [ ] 수동매수 저장 → Config `mode: manual`
- [ ] 그룹 관리에서 수동 매수 버튼 표시
- [ ] 수동 매수 실행 → Position 생성

---

### Phase 3: 통합 테스트
**예상 시간**: 1시간

| 테스트 | 체크 |
|--------|------|
| 자동매수 V4 | [ ] |
| 자동매수 Expert | [ ] |
| 수동매수 | [ ] |
| DCA 자동 실행 (수동매수 후) | [ ] |
| 익절/손절 자동 실행 | [ ] |
| Config 재로드 | [ ] |

---

## 📁 생성/수정될 파일 목록

### 신규 파일 (3개)
1. `gui/v4_custom_settings_dialog.py` - V4 Custom 고급 설정
2. `gui/manual_buy_dialog.py` - 수동 매수 실행
3. `FIX_PLAN_TEST_FEEDBACK.md` - 이 문서

### 수정 파일 (3개)
1. `gui/auto_buy_settings_dialog_v2.py` - 매수 모드 선택 추가
2. `gui/expert_strategy_widget.py` - 슬라이더 + SpinBox
3. `gui/group_management_dialog.py` - 수동 매수 버튼

---

## 🎯 우선순위 결정

### Critical (즉시 수정 필요)
- ✅ **수정 #3**: 수동매수 기능 복원
  - 기능 퇴보, 사용자 불편
  - Phase 2 전체

### High (빠른 시일 내 수정)
- ✅ **수정 #2**: Expert 슬라이더 정밀도
  - Custom 사용자 불편
  - Phase 1 - 20분

### Medium (여유 있을 때)
- ✅ **수정 #1**: V4 Custom 가시성
  - Custom 사용자 소수
  - Phase 1 - 30분

---

## ✅ 다음 단계

### 1. 계획 검토 및 승인
- [ ] 이 문서 검토
- [ ] 옵션 선택 확정
- [ ] 우선순위 조정 (필요 시)

### 2. 구현 시작
```bash
# Phase 1 브랜치 생성
git checkout -b fix/ui-improvements-sliders-custom

# Phase 2 브랜치 생성 (Phase 1 완료 후)
git checkout -b feat/restore-manual-buy-mode
```

### 3. 구현 순서 (권장)
1. **Phase 1** 먼저 완료 (1시간)
   - Expert 슬라이더 개선
   - V4 Custom 다이얼로그
   - 테스트 → 커밋 → 푸시

2. **Phase 2** 이어서 진행 (2시간)
   - 수동매수 기능 복원
   - 테스트 → 커밋 → 푸시

3. **Phase 3** 통합 테스트 (1시간)
   - 전체 시나리오 검증
   - 문서 업데이트

---

**작성일**: 2025-11-14
**작성자**: Claude AI
**검토 대기**: 사용자 승인 필요
**예상 총 작업 시간**: 4시간
