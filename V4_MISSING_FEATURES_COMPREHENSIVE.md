# V4 구현 누락 기능 종합 분석 보고서

**작성일**: 2025-11-10
**분석 대상**: V4 GUI 구현 상태
**분석 방법**: V4_IMPLEMENTATION_PLAN.md와 실제 구현 코드 비교

---

## 📋 요약

| 구분 | 계획됨 | 구현됨 | 누락됨 | 완성도 |
|------|--------|--------|--------|--------|
| **Phase 1**: 데이터 구조 | 5개 파일 | 5개 파일 | 0개 | ✅ 100% |
| **Phase 2**: 백엔드 핵심 | 4개 파일 | 4개 파일 | 0개 | ✅ 100% |
| **Phase 3**: GUI 컴포넌트 | 6개 요소 | 3개 요소 | 3개 요소 | ⚠️ 50% |

**결론**: 백엔드는 100% 완성되었으나, **GUI가 50%만 구현**되어 사용자가 핵심 기능에 접근할 수 없음.

---

## 🚨 누락 기능 상세 (우선순위 순)

### 1. 투자 스타일 선택 UI ⭐⭐⭐ (Critical)

**위치**: `gui/group_settings_dialog.py`

**문제**:
- 백엔드에 3가지 투자 스타일 프리셋이 완벽히 구현되어 있음
  - Conservative (4시간봉, 하루 1~5번)
  - Balanced (1시간봉, 하루 5~15번) ⭐ 추천
  - Aggressive (15분봉, 하루 15~30번)
- GUI에서 선택할 수 있는 UI가 **완전히 없음**
- 현재 "balanced" 스타일로 하드코딩됨 (line 357)

**계획된 위치**:
```python
# V4_IMPLEMENTATION_PLAN.md Line 1207-1250
# gui/auto_buy_settings_dialog.py (신규 파일 필요)

class AutoBuySettingsDialog(QDialog):
    """자동매수 설정 다이얼로그"""

    def _setup_ui(self):
        # 투자 스타일 선택
        self.radio_conservative = QRadioButton("보수적 (4시간봉) - 하루 1~5번")
        self.radio_balanced = QRadioButton("균형형 (1시간봉) - 하루 5~15번 ⭐ 추천")
        self.radio_aggressive = QRadioButton("적극적 (15분봉) - 하루 15~30번")
        self.radio_custom = QRadioButton("커스텀 (고급 사용자)")

        # RSI, MACD, Volume 지표 설정 UI
        # ...
```

**실제 상황**:
- `gui/auto_buy_settings_dialog.py` 파일 자체가 **존재하지 않음**
- `gui/group_settings_dialog.py`에 "자동매수 설정..." 버튼도 없음
- 사용자가 투자 스타일을 선택할 방법이 전혀 없음

**영향도**:
- 🔴 **치명적**: 사용자가 자동매수 전략을 커스터마이징할 수 없음
- 🔴 모든 사용자가 동일한 "Balanced" 전략만 사용
- 🔴 보수적/공격적 투자 성향을 반영할 수 없음

**임시 해결책**:
```json
// config/trading_config.json 직접 편집
{
  "groups": {
    "my_group": {
      "buy_settings": {
        "auto_config": {
          "investment_style": "conservative",  // ← 여기를 직접 수정
          "candle_unit": "240"
        }
      }
    }
  }
}
```

**구현 예상 시간**: 2-3시간

**관련 파일**:
- 생성 필요: `gui/auto_buy_settings_dialog.py` (신규, ~350 lines)
- 수정 필요: `gui/group_settings_dialog.py` (버튼 추가)
- 참고: `core/strategies/v4_auto_buy_strategy.py:55-115` (PRESETS 정의)

---

### 2. Auto Buy Settings Dialog 파일 누락 ⭐⭐⭐ (Critical)

**파일**: `gui/auto_buy_settings_dialog.py`

**문제**:
- V4_IMPLEMENTATION_PLAN.md Phase 3.4에 명확히 정의되어 있음 (Line 1207-1441)
- 계획에는 350+ lines의 상세 사양이 있으나 **파일 자체가 없음**

**계획된 기능**:
1. 투자 스타일 선택 (Conservative/Balanced/Aggressive/Custom)
2. 기술적 지표 활성화/비활성화
   - RSI (기간, 과매도/과매수 기준)
   - MACD (Fast, Slow, Signal 파라미터)
   - Volume (기간, 임계값)
3. 매수 금액 설정
4. Preset 적용 시 자동 파라미터 설정

**실제 상황**:
- 파일 없음
- `group_settings_dialog.py`에서 이 다이얼로그를 여는 버튼도 없음

**영향도**:
- 🔴 **치명적**: 투자 스타일 선택 불가 (위 1번과 동일)
- 🔴 지표 파라미터 조정 불가
- 🔴 매수 금액도 조정 불가 (현재 하드코딩됨)

**구현 예상 시간**: 3-4시간

**참고 구현**:
- `gui/advanced_dca_dialog.py` (36KB) - 유사한 프리셋 시스템 참고 가능
- `gui/auto_trading_config_dialog.py` (8.6KB) - V3 자동매매 설정 참고

---

### 3. 통계 탭 누락 ⭐⭐ (High)

**위치**: `gui/main_window.py`

**문제**:
- 계획: 3개 탭 (활성 포지션, 거래 내역, **통계**)
- 실제: 2개 탭만 구현 (활성 포지션, 거래 내역)
- **통계 탭이 완전히 없음**

**계획된 통계 탭 기능** (V4_IMPLEMENTATION_PLAN.md Line 904-939):
```python
# Tab 3: 통계
def _create_statistics_tab(self):
    # 전체 통계
    - 총 수익 (원, %)
    - 승률 (%)
    - 총 거래 횟수

    # 그룹별 통계 테이블
    - 그룹명
    - 코인 수
    - 총 수익
    - 승률
    - 거래 횟수
    - 평균 보유 시간
```

**실제 코드**:
```python
# gui/main_window.py Line 437-508
tab_widget = QTabWidget()
tab_widget.addTab(position_widget, "📊 활성 포지션")     # ✅ 존재
tab_widget.addTab(trade_history_widget, "📋 거래 내역")  # ✅ 존재
# tab_widget.addTab(statistics_widget, "📈 통계")         # ❌ 없음!
```

**영향도**:
- 🟡 **중간**: 거래 성과를 한눈에 파악하기 어려움
- 🟡 그룹별 성과 비교 불가
- 🟡 승률, 평균 보유 시간 등 통계 확인 불가

**대안**:
- "📋 거래 내역" 탭에 요약 통계가 일부 있음 (Line 472)
- `core/trade_history_manager.py`에 `calculate_statistics()` 메서드 완성되어 있음

**구현 예상 시간**: 2-3시간

**관련 파일**:
- 수정: `gui/main_window.py` (탭 추가)
- 활용: `core/trade_history_manager.py:calculate_statistics()` (이미 완성됨)

---

### 4. Dry-run 모드 토글 UI 누락 ⭐⭐ (High)

**위치**: `gui/global_settings_dialog.py`

**문제**:
- `config/trading_config_template.json` Line 24에 `"dry_run": true` 필드 존재
- JSON Schema에서 **필수 필드**로 정의됨 (Line 14: `"required": ["dry_run"]`)
- GUI에서 이 값을 변경할 수 있는 UI가 **없음**

**현재 구현된 탭**:
```python
# gui/global_settings_dialog.py Line 38-50
Tab 1: 거래 제한 (Trading Limits)         ✅ 존재
Tab 2: 일일 손실 한도 (Daily Loss Limit)  ✅ 존재
Tab 3: 텔레그램 알림 (Telegram)           ✅ 존재
Tab 4: Dry-run 모드                       ❌ 없음!
```

**계획에는 없지만 필수인 기능**:
```python
# 추가 필요 (V4_IMPLEMENTATION_PLAN에는 명시 안 되어 있음)
dry_run_group = QGroupBox("거래 모드")
dry_run_layout = QVBoxLayout()

self.dry_run_checkbox = QCheckBox("Dry-run 모드 (모의 거래)")
dry_run_info = QLabel("활성화 시 실제 주문 없이 가상 잔고로 거래 시뮬레이션")

dry_run_layout.addWidget(self.dry_run_checkbox)
dry_run_layout.addWidget(dry_run_info)
```

**실제 상황**:
- JSON 파일에서만 변경 가능
- GUI로 Live ↔ Dry-run 전환 불가

**영향도**:
- 🟡 **중간**: 테스트 시 JSON 파일 직접 편집해야 함
- 🟡 사용자가 실수로 Live 모드에서 거래할 위험
- 🟡 모드 전환이 번거로움

**임시 해결책**:
```bash
# config/trading_config.json 직접 편집
{
  "global_settings": {
    "dry_run": true  // ← 여기를 true/false로 변경
  }
}
```

**구현 예상 시간**: 30분

**관련 파일**:
- 수정: `gui/global_settings_dialog.py` (체크박스 추가)

---

### 5. Observation 모드 토글 UI 누락 ⭐ (Medium)

**위치**: `gui/group_settings_dialog.py`

**문제**:
- `config/trading_config_template.json` Line 29에 `"observation_only": false` 필드 존재
- 그룹별로 "관찰 전용" 모드를 설정할 수 있어야 함
- GUI에서 이 값을 변경할 수 있는 UI가 **없음**

**계획된 위치**:
```python
# V4_IMPLEMENTATION_PLAN.md에는 명시 안 되어 있으나
# config 파일 구조상 그룹 설정 다이얼로그에 있어야 함

# gui/group_settings_dialog.py에 추가 필요
observation_group = QGroupBox("관찰 모드")
self.observation_checkbox = QCheckBox("관찰 전용 (매매 없이 모니터링만)")
observation_info = QLabel("활성화 시 이 그룹은 매매하지 않고 신호만 확인합니다.")
```

**실제 상황**:
- `group_settings_dialog.py`에 관찰 모드 UI 없음
- JSON 파일에서만 변경 가능

**영향도**:
- 🟢 **낮음**: 주요 기능은 아니지만 편의 기능
- 🟢 특정 코인을 매매 없이 모니터링하고 싶을 때 유용
- 🟢 JSON 편집으로 가능하므로 Workaround 있음

**임시 해결책**:
```json
// config/trading_config.json 직접 편집
{
  "groups": {
    "watch_only_group": {
      "observation_only": true,  // ← 여기를 true로 설정
      "coins": ["KRW-BTC"]
    }
  }
}
```

**구현 예상 시간**: 20분

**관련 파일**:
- 수정: `gui/group_settings_dialog.py` (체크박스 추가)

---

## 📊 Phase 3 GUI 체크리스트 비교

### V4_IMPLEMENTATION_PLAN.md Phase 3 체크리스트 (Line 1895-1900)

```markdown
### Phase 3 체크리스트
- [ ] `gui/main_window.py` V4 재설계
- [ ] `gui/group_management_dialog.py` 구현
- [ ] `gui/group_settings_dialog.py` 구현
- [ ] `gui/auto_buy_settings_dialog.py` 구현  ← 🔴 파일 자체가 없음
- [ ] `gui/global_settings_dialog.py` 구현
- [ ] GUI 통합 테스트
```

### 실제 구현 상태

| 항목 | 계획 | 실제 | 상태 | 비고 |
|------|------|------|------|------|
| **main_window.py 재설계** | 3-tab 구조 | 2-tab만 구현 | ⚠️ 67% | 통계 탭 없음 |
| **group_management_dialog.py** | CRUD 기능 | CRUD 완성 | ✅ 100% | 완벽 구현 |
| **group_settings_dialog.py** | 매수/DCA/익절/손절 | 4가지 모두 있음 | ⚠️ 80% | 투자 스타일 선택 UI 없음, observation 체크박스 없음 |
| **auto_buy_settings_dialog.py** | 투자 스타일 + 지표 설정 | **파일 없음** | ❌ 0% | 완전히 누락 |
| **global_settings_dialog.py** | 거래 제한 + 손실 한도 + 텔레그램 | 3-tab 구현 | ⚠️ 90% | dry_run 토글 없음 |
| **GUI 통합 테스트** | 종합 테스트 | 미실시 | ❌ 0% | 자동매매 테스트 안 함 |

**Phase 3 전체 완성도**: **약 56%**

---

## 🎯 구현 우선순위 및 예상 작업량

### 우선순위 1: 투자 스타일 선택 UI (필수) ⏱️ 3-4시간

**작업 내용**:
1. `gui/auto_buy_settings_dialog.py` 신규 생성 (~350 lines)
   - 투자 스타일 라디오 버튼 (Conservative/Balanced/Aggressive/Custom)
   - RSI/MACD/Volume 지표 설정 UI
   - Preset 선택 시 자동 파라미터 적용
   - 설정 저장/로드 로직

2. `gui/group_settings_dialog.py` 수정 (~20 lines 추가)
   - "자동매수 설정..." 버튼 추가
   - 버튼 클릭 시 AutoBuySettingsDialog 열기
   - 자동매수 모드일 때만 버튼 활성화

**완료 조건**:
- [ ] Conservative/Balanced/Aggressive 프리셋 선택 가능
- [ ] 선택한 스타일이 config.json에 저장됨
- [ ] GUI 재시작 시 설정 유지
- [ ] Custom 모드에서 지표 파라미터 직접 조정 가능

**테스트 방법**:
```python
# 1. GUI에서 "📁 그룹 관리" → 그룹 생성
# 2. 매수 설정: "자동" 선택
# 3. "자동매수 설정..." 버튼 클릭
# 4. "적극적" 스타일 선택 → 저장
# 5. config/trading_config.json 확인
assert config["groups"]["xxx"]["buy_settings"]["auto_config"]["investment_style"] == "aggressive"
assert config["groups"]["xxx"]["buy_settings"]["auto_config"]["candle_unit"] == "15"
```

---

### 우선순위 2: 통계 탭 추가 (권장) ⏱️ 2-3시간

**작업 내용**:
1. `gui/main_window.py` 수정
   - `_create_statistics_tab()` 메서드 추가 (~100 lines)
   - 전체 통계 그룹 (총 수익, 승률, 총 거래)
   - 그룹별 통계 테이블
   - 탭 위젯에 통계 탭 추가

2. `core/trade_history_manager.py` 활용
   - 이미 구현된 `calculate_statistics()` 메서드 사용
   - 그룹별 통계 계산 로직 완성되어 있음

**완료 조건**:
- [ ] "📈 통계" 탭이 메인 윈도우에 표시됨
- [ ] 전체 통계 (총 수익, 승률, 거래 횟수) 표시
- [ ] 그룹별 통계 테이블 표시
- [ ] 실시간 업데이트 (거래 발생 시 자동 갱신)

---

### 우선순위 3: Dry-run 모드 토글 (권장) ⏱️ 30분

**작업 내용**:
1. `gui/global_settings_dialog.py` 수정 (~30 lines 추가)
   - Dry-run 모드 그룹박스 추가
   - 체크박스 + 설명 라벨
   - 저장/로드 로직 추가

**완료 조건**:
- [ ] "⚙️ 전역 설정"에서 Dry-run 모드 토글 가능
- [ ] 설정 변경 시 config.json 업데이트
- [ ] 모드 변경 시 경고 메시지 표시 (Live 모드 전환 시)

---

### 우선순위 4: Observation 모드 토글 (선택) ⏱️ 20분

**작업 내용**:
1. `gui/group_settings_dialog.py` 수정 (~20 lines 추가)
   - 관찰 모드 체크박스 추가
   - 저장/로드 로직 추가

**완료 조건**:
- [ ] 그룹 설정에서 "관찰 전용" 체크박스 표시
- [ ] 활성화 시 해당 그룹은 매매하지 않음

---

## 📝 구현 로드맵 제안

### Option A: 최소 기능 (1일 작업)
- ✅ 투자 스타일 선택 UI (3-4시간)
- ✅ Dry-run 모드 토글 (30분)
- **총 소요 시간**: 약 4-5시간 (1일)

### Option B: 권장 기능 (2일 작업)
- ✅ 투자 스타일 선택 UI (3-4시간)
- ✅ 통계 탭 추가 (2-3시간)
- ✅ Dry-run 모드 토글 (30분)
- ✅ Observation 모드 토글 (20분)
- **총 소요 시간**: 약 6-8시간 (2일)

### Option C: 완전 구현 (3일 작업)
- ✅ Option B 모든 기능
- ✅ GUI 통합 테스트 (4시간)
- ✅ 문서 업데이트 (2시간)
- **총 소요 시간**: 약 12-14시간 (3일)

---

## 🔍 기타 발견 사항

### 1. V3 vs V4 코드 중복

**발견**:
- `gui/auto_trading_config_dialog.py` (V3 전용, 8.6KB)
- 이 파일은 V3 Auto Trading Manager용이며 V4와는 별개

**권장 조치**:
- 파일 상단에 주석 추가: `# V3 ONLY - 레거시 코드, V4에서는 사용 안 함`
- 또는 `gui/legacy/` 폴더로 이동

### 2. DCA 프리셋 혼동 가능성

**발견**:
- `gui/advanced_dca_dialog.py`에 "보수적/균형형/공격적" 프리셋 있음 (Line 167-180)
- 이것은 **DCA 레벨 프리셋**이며, 투자 스타일 프리셋과는 다름

**명확화 필요**:
- DCA 프리셋: 하락률과 매수 비중 조정
- 투자 스타일 프리셋: 캔들봉 주기와 지표 파라미터 조정

### 3. JSON 스키마 검증 누락

**발견**:
- `config/schemas/trading_config_schema.json` 존재
- `core/config_manager.py`에 `validate_config()` 메서드 있음 (Line 250-280)
- 하지만 GUI에서 저장 시 스키마 검증을 호출하지 않음

**권장 조치**:
```python
# gui/group_settings_dialog.py, global_settings_dialog.py 수정
def _save_settings(self):
    # 설정 업데이트
    # ...

    # 스키마 검증 추가
    is_valid, error_msg = self.config_manager.validate_config(self.config)
    if not is_valid:
        QMessageBox.critical(self, "설정 오류", f"유효하지 않은 설정입니다:\n{error_msg}")
        return

    # 저장
    self.config_manager.save_config(self.config)
```

---

## ✅ 결론

### 현재 상황
- **백엔드**: 100% 완성 (Phase 1-2 완료)
- **GUI**: 56% 완성 (Phase 3 부분 완료)
- **자동매매 테스트**: 0% (실행해본 적 없음)

### 핵심 문제
1. 🔴 투자 스타일을 선택할 GUI가 없음 (가장 중요!)
2. 🔴 `auto_buy_settings_dialog.py` 파일이 완전히 누락됨
3. 🟡 통계 탭이 없어서 성과 파악이 어려움
4. 🟡 Dry-run 모드를 GUI에서 전환할 수 없음

### 다음 단계 권장 사항

**Option 1: 빠른 테스트 (현재 상태 유지)**
- JSON 파일 직접 편집으로 투자 스타일 설정
- Dry-run 모드에서 자동매매 테스트 진행
- GUI 개선은 나중에

**Option 2: GUI 완성 후 테스트 (권장)**
1. 투자 스타일 선택 UI 구현 (3-4시간)
2. Dry-run 토글 구현 (30분)
3. Dry-run 모드에서 자동매매 테스트 (1-3일)
4. 통계 탭 구현 (2-3시간)
5. 1주일 프로덕션 모니터링
6. PR 생성

**Option 3: 완전 구현 (이상적)**
- Option 2 + Observation 모드 + GUI 테스트 + 문서 업데이트
- 총 소요 기간: 5-7일

---

**마지막 업데이트**: 2025-11-10
**작성자**: Claude (Sonnet 4.5)
**상태**: 분석 완료, 구현 대기

## 📎 참고 파일

**계획 문서**:
- `docs/V4_IMPLEMENTATION_PLAN.md` (1,932 lines)
- `docs/DESIGN_V4_COMPLETE.md` (4,700+ lines)
- `docs/V4_STATUS.md` (461 lines)

**설정 파일**:
- `config/trading_config_template.json` (100 lines)
- `config/schemas/trading_config_schema.json` (JSON Schema)

**백엔드 완성 파일**:
- `core/config_manager.py` (512 lines) ✅ 100%
- `core/position_manager.py` (656 lines) ✅ 100%
- `core/group_manager.py` (578 lines) ✅ 100%
- `core/daily_loss_tracker.py` (329 lines) ✅ 100%
- `core/strategies/v4_auto_buy_strategy.py` (456 lines) ✅ 100%
- `core/v4_trading_engine.py` (930 lines) ✅ 100%

**GUI 부분 완성 파일**:
- `gui/group_management_dialog.py` (24KB) ✅ 100%
- `gui/group_settings_dialog.py` (19KB) ⚠️ 80% (투자 스타일 UI 없음)
- `gui/global_settings_dialog.py` (14KB) ⚠️ 90% (dry_run 토글 없음)
- `gui/main_window.py` (3000+ lines) ⚠️ 67% (통계 탭 없음)

**GUI 완전 누락 파일**:
- `gui/auto_buy_settings_dialog.py` ❌ 0% (파일 자체가 없음)
