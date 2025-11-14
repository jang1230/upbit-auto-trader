# 수정 계획 요약 - 테스트 피드백

**날짜**: 2025-11-14
**상세 문서**: `FIX_PLAN_TEST_FEEDBACK.md` (23KB)

---

## 🐛 발견된 이슈 (3개)

### 1. V4 Custom 수치 안 보임 ⚠️ Medium
- **문제**: Custom 선택 시 하단 수치 입력 필드가 잘림
- **해결**: V4 Custom을 별도 다이얼로그로 분리
- **시간**: 30분

### 2. Expert 슬라이더 정밀도 부족 🔴 High
- **문제**: 0.6, 0.65만 가능, 0.62 불가능
- **해결**: 슬라이더 + SpinBox 조합
- **시간**: 20분

### 3. 수동매수 기능 누락 🔴 Critical!
- **문제**: 자동매수만 지원, 수동매수 불가능
- **영향**: 원래 3가지 모드 → 1가지만 지원 (기능 퇴보)
- **해결**: 매수 모드 선택 라디오 버튼 추가
- **시간**: 2시간

---

## 🎯 수정 방안 (권장)

### 수정 #1: V4 Custom → 별도 다이얼로그
```
V4 전략 → Custom 선택
  ↓
[🔧 고급 설정] 버튼 표시
  ↓
클릭 → "V4 Custom 설정" 다이얼로그
  ↓
RSI/MACD/Volume 상세 조정
```

**파일**: `gui/v4_custom_settings_dialog.py` (신규)

---

### 수정 #2: Expert 슬라이더 + SpinBox
```
현재:  [슬라이더━━━━━●━━━━━]

변경:  [슬라이더━━━━━●━━━━━] [0.65 ▼]
                            ↑ DoubleSpinBox
```

**파일**: `gui/expert_strategy_widget.py` (수정)

**기능**:
- 슬라이더: 빠른 조정
- SpinBox: 정밀 입력 (0.01 단위)
- 양방향 동기화

---

### 수정 #3: 수동매수 기능 복원
```
현재 구조:
  ◉ V4 전략
  ○ Expert 전략

새 구조:
  [1단계] 매수 모드
    ◉ 자동매수 (전략 기반)
    ○ 수동매수 (직접 선택)

  [2단계] 전략 선택 (자동일 때만)
    ◉ V4 전략
    ○ Expert 전략
```

**파일**:
- `gui/auto_buy_settings_dialog_v2.py` (대폭 수정)
- `gui/manual_buy_dialog.py` (신규)
- `gui/group_management_dialog.py` (수정)

**Config 변경**:
```json
// 자동매수
{
  "buy_settings": {
    "mode": "auto",
    "auto_config": {...}
  }
}

// 수동매수
{
  "buy_settings": {
    "mode": "manual",
    "buy_amount_krw": 50000
  }
}
```

---

## 📅 구현 로드맵

### Phase 1: UI 개선 (1시간)
- [x] Expert 슬라이더 → 슬라이더+SpinBox (20분)
- [x] V4 Custom → 별도 다이얼로그 (30분)
- [x] 다이얼로그 높이 증가 임시 조치 (10분)

### Phase 2: 수동매수 복원 (2시간)
- [x] 매수 모드 라디오 버튼 (40분)
- [x] 수동매수 페이지 UI (20분)
- [x] Config 저장/로드 (20분)
- [x] 그룹 관리 수동 매수 버튼 (20분)
- [x] 수동 매수 다이얼로그 (40분)

### Phase 3: 통합 테스트 (1시간)
- [ ] 자동매수 V4/Expert 테스트
- [ ] 수동매수 테스트
- [ ] DCA/익절/손절 자동 실행 (수동매수 후)

**총 예상 시간**: 4시간

---

## 🎯 우선순위

1. 🔴 **Critical**: 수동매수 기능 복원 (Phase 2)
2. 🟠 **High**: Expert 슬라이더 (Phase 1 - 20분)
3. 🟡 **Medium**: V4 Custom 다이얼로그 (Phase 1 - 30분)

---

## ✅ 권장 순서

```bash
# 1. Phase 1 먼저 (빠른 개선)
git checkout -b fix/ui-improvements-sliders-custom
# Expert 슬라이더 (20분)
# V4 Custom (30분)
# 테스트 → 커밋 → 푸시

# 2. Phase 2 이어서 (기능 복원)
git checkout -b feat/restore-manual-buy-mode
# 수동매수 UI (2시간)
# 테스트 → 커밋 → 푸시

# 3. Phase 3 (통합 테스트)
# 전체 시나리오 검증 (1시간)
```

---

## 📁 파일 변경 내역

### 신규 (3개)
- `gui/v4_custom_settings_dialog.py`
- `gui/manual_buy_dialog.py`
- `FIX_PLAN_TEST_FEEDBACK.md`

### 수정 (3개)
- `gui/auto_buy_settings_dialog_v2.py` ← 대폭 수정
- `gui/expert_strategy_widget.py`
- `gui/group_management_dialog.py`

---

## 💡 핵심 결정 사항

### Q1: V4 Custom 수치 문제?
**A**: 별도 다이얼로그로 분리 (고급 설정 버튼)

### Q2: Expert 슬라이더 문제?
**A**: 슬라이더 + DoubleSpinBox 조합

### Q3: 수동매수 복원 방법?
**A**: 매수 모드 선택 라디오 버튼 (자동 vs 수동)

---

## ⏱️ 다음 단계

1. **이 계획 검토** (5분)
   - 옵션 확정
   - 우선순위 조정

2. **Phase 1 구현** (1시간)
   - Expert 슬라이더
   - V4 Custom
   - 테스트

3. **Phase 2 구현** (2시간)
   - 수동매수 기능
   - 테스트

---

**상세 내용**: `FIX_PLAN_TEST_FEEDBACK.md` 참고
