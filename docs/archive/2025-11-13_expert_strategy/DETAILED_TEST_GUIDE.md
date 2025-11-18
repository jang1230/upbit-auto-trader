# 초상세 테스트 가이드 - Expert Strategy & GUI 개선

**브랜치**: `claude/expert-strategy-clone-01ELiN8eY3EZwEi2gSx4xARg`
**작업일**: 2025-11-13
**테스트 날짜**: __________
**테스터**: __________

---

## 🎯 테스트 목표

11/13일 작업한 다음 기능들이 정상 동작하는지 검증:

1. ✅ **라디오 버튼 구조**: 탭 중첩 제거 → 라디오 버튼으로 전환
2. ✅ **V4/Expert 전략 분리**: 각 전략 저장 시 필드 오염 없음
3. ✅ **공통 매수금액 필드**: V4/Expert 모두 동일한 필드 사용
4. ✅ **스크롤 기능**: 긴 설정 폼 대응
5. ✅ **통합 설정 다이얼로그**: 4번 저장 → 2번 저장
6. ✅ **Expert 10개 프로필**: 전문가 시스템 정상 동작
7. ✅ **Custom 가중치**: 사용자 정의 가중치 저장

---

## 🚀 시작 전 준비

### 1. 브랜치 확인
```bash
cd /home/user/upbit-auto-trader
git branch --show-current
```

**기대 결과**: `claude/expert-strategy-clone-01ELiN8eY3EZwEi2gSx4xARg`

### 2. 최신 커밋 확인
```bash
git log --oneline -5
```

**기대 결과**:
```
d408f6d docs: Add work session documentation and test guides
38dca11 feat: Add common buy amount field above strategy selection
dbbe2ca feat: Add scroll area and reduce dialog height for auto-buy settings
11671d4 refactor: Replace nested tabs with radio button strategy selection
20c5d44 feat: Connect GroupUnifiedSettingsDialog to group management (Step 6)
```

### 3. 백업 (중요!)
```bash
# 기존 설정 백업
cp config/trading_config.json config/trading_config_backup_$(date +%Y%m%d_%H%M%S).json 2>/dev/null || echo "기존 설정 없음"
```

### 4. GUI 실행
```bash
python main.py
```

---

## 📋 Priority 1: 핵심 기능 테스트 (필수)

### ✅ 테스트 1: 라디오 버튼 전환 (10분)

#### 1-1. 다이얼로그 열기
**단계**:
1. GUI 실행
2. 좌측 패널 → **"그룹 관리"** 버튼 클릭
3. 그룹 목록에서 **아무 그룹 선택** (예: v4_example_group)
4. 우측 하단 → **"레벨 설정"** 버튼 클릭
5. 통합 설정 다이얼로그 표시됨

**예상 화면**:
```
┌─────────────────────────────────────────────┐
│ ⚙️ 그룹 설정: V4 전략 예제                   │
├─────────────────────────────────────────────┤
│ [📊 자동매수 전략] [📈 DCA / 익절 / 손절]    │ ← 탭 2개
└─────────────────────────────────────────────┘
```

#### 1-2. 자동매수 탭 확인
**단계**:
1. **"📊 자동매수 전략"** 탭 클릭 (기본 선택됨)
2. 라디오 버튼 2개 확인:
   - `◉ V4 전략 (3개 지표 - RSI, MACD, Volume)`
   - `○ Expert 전략 (5개 지표 - 종합 스코어링)`

**체크 포인트**:
- [ ] 라디오 버튼 2개만 표시됨 (탭 아님!)
- [ ] 라디오 버튼이 명확히 구분됨
- [ ] 둘 중 하나만 선택 가능

**스크린샷 촬영**: `screenshots/test1-2_radio_buttons.png`

#### 1-3. V4 전략 확인
**단계**:
1. **V4 전략 라디오 버튼 클릭**
2. 하단에 V4 설정 폼 표시 확인:
   - 투자 스타일 (Aggressive/Balanced/Conservative)
   - 캔들 단위 (60분/240분/일봉)
   - RSI 설정
   - MACD 설정
   - Volume 설정

**체크 포인트**:
- [ ] 클릭 즉시 폼 전환됨 (딜레이 없음)
- [ ] V4 설정 필드들이 모두 표시됨
- [ ] **하단에 "매수금액" 필드 없음** (공통 필드로 이동됨)

**스크린샷 촬영**: `screenshots/test1-3_v4_form.png`

#### 1-4. Expert 전략 확인
**단계**:
1. **Expert 전략 라디오 버튼 클릭**
2. 하단에 Expert 설정 폼 표시 확인:
   - 전문가 프로필 드롭다운 (10개 옵션)
   - 캔들 단위 (10분/15분/60분/240분)
   - (Custom 선택 시) 가중치 조정 슬라이더

**체크 포인트**:
- [ ] 클릭 즉시 폼 전환됨
- [ ] V4 설정이 사라지고 Expert 설정만 표시됨
- [ ] 프로필 드롭다운에 10개 옵션 표시:
  - RSI 전문가
  - 모멘텀 전문가
  - 볼린저 전문가
  - 거래량 전문가
  - 균형형 전문가
  - 보수형 전문가
  - 공격형 전문가
  - 스윙 트레이더
  - 데이 트레이더
  - 스캘퍼

**스크린샷 촬영**: `screenshots/test1-4_expert_form.png`

#### 1-5. 공통 매수금액 필드 확인
**단계**:
1. V4 라디오 선택 → Expert 라디오 선택 반복
2. **라디오 버튼과 스크롤 영역 사이**에 매수금액 필드 확인

**체크 포인트**:
- [ ] 라디오 버튼 바로 아래에 "💰 1회 매수 금액" 그룹박스 표시
- [ ] 전략 전환 시 매수금액 값 유지됨
- [ ] V4 설정 폼 하단에 매수금액 필드 **없음**

**스크린샷 촬영**: `screenshots/test1-5_common_buy_amount.png`

---

### ✅ 테스트 2: Expert 전략 저장 (15분)

#### 2-1. Expert 전략 선택 및 설정
**단계**:
1. **Expert 전략 라디오 버튼 클릭**
2. 프로필 드롭다운에서 **"균형형 전문가"** 선택
3. 캔들 단위: **10분** 선택
4. 매수금액: **100,000원** 입력

**체크 포인트**:
- [ ] 프로필 드롭다운이 정상 동작함
- [ ] 캔들 단위 변경 가능
- [ ] 매수금액 숫자 입력 가능

#### 2-2. 저장 및 알림 확인
**단계**:
1. 하단 **"저장"** 버튼 클릭
2. 알림창 표시 확인

**기대 알림 메시지**:
```
✅ 설정이 저장되었습니다

📊 자동매수: Expert 전략 - balanced_expert
📈 DCA: X개 레벨
💰 익절: X개 레벨
💸 손절: X개 레벨
```

**체크 포인트**:
- [ ] 알림창에 "Expert 전략 - balanced_expert" 표시됨
- [ ] "v4_auto_buy" 표시 **안됨** (버그 수정 확인)
- [ ] 알림창 확인 후 다이얼로그 자동 닫힘

#### 2-3. Config 파일 검증
**단계**:
```bash
cat config/trading_config.json | jq '.groups.v4_example_group.buy_settings.auto_config'
```

**기대 출력**:
```json
{
  "enabled": true,
  "strategy": "expert",                    ← "expert" 확인
  "expert_profile": "balanced_expert",     ← 프로필 확인
  "candle_unit": "10",                     ← 10분 확인
  "buy_amount_krw": 100000                 ← 금액 확인
}
```

**체크 포인트** (중요!):
- [ ] `"strategy": "expert"` ✓
- [ ] `"expert_profile": "balanced_expert"` ✓
- [ ] `"buy_amount_krw": 100000` ✓
- [ ] `"investment_style"` 필드 **없음** ✓ (V4 필드 오염 방지)
- [ ] `"indicators"` 필드 **없음** ✓ (V4 필드 오염 방지)

**스크린샷 촬영**: 터미널 출력 캡처

---

### ✅ 테스트 3: V4 전략 저장 (15분)

#### 3-1. 다이얼로그 다시 열기
**단계**:
1. 그룹 관리 → 같은 그룹 선택 → 레벨 설정 클릭
2. 자동매수 탭 선택

**체크 포인트**:
- [ ] **Expert 라디오가 선택되어 있음** (이전 저장 반영)
- [ ] 프로필이 "균형형 전문가"로 표시됨
- [ ] 매수금액 100,000원 표시됨

#### 3-2. V4 전략으로 변경
**단계**:
1. **V4 전략 라디오 버튼 클릭**
2. 투자 스타일: **Aggressive** 선택
3. 캔들 단위: **240분** 선택
4. RSI 설정:
   - 기간: 14
   - 과매도: 25 (기본 30에서 변경)
   - 과매수: 75 (기본 70에서 변경)
5. 매수금액: **200,000원**으로 변경

**체크 포인트**:
- [ ] V4 폼으로 즉시 전환됨
- [ ] 모든 필드 수정 가능
- [ ] 매수금액 값이 공통 필드에 반영됨

#### 3-3. 저장 및 알림 확인
**단계**:
1. 저장 버튼 클릭
2. 알림창 확인

**기대 알림 메시지**:
```
✅ 설정이 저장되었습니다

📊 자동매수: V4 전략 - aggressive
...
```

**체크 포인트**:
- [ ] 알림창에 "V4 전략 - aggressive" 표시됨
- [ ] "Expert" 표시 **안됨**

#### 3-4. Config 파일 검증
```bash
cat config/trading_config.json | jq '.groups.v4_example_group.buy_settings.auto_config'
```

**기대 출력**:
```json
{
  "enabled": true,
  "strategy": "v4_auto_buy",              ← "v4_auto_buy" 확인
  "investment_style": "aggressive",       ← aggressive 확인
  "candle_unit": "240",                   ← 240분 확인
  "indicators": {
    "rsi": {
      "enabled": true,
      "period": 14,
      "oversold": 25,                     ← 변경 반영
      "overbought": 75                    ← 변경 반영
    },
    ...
  },
  "buy_amount_krw": 200000                ← 금액 변경 확인
}
```

**체크 포인트** (중요!):
- [ ] `"strategy": "v4_auto_buy"` ✓
- [ ] `"investment_style": "aggressive"` ✓
- [ ] `"indicators"` 객체 존재 ✓
- [ ] `"expert_profile"` 필드 **없음** ✓ (Expert 필드 오염 방지)
- [ ] `"custom_weights"` 필드 **없음** ✓ (Expert 필드 오염 방지)

---

### ✅ 테스트 4: 재로드 테스트 (5분)

#### 4-1. 다이얼로그 재오픈
**단계**:
1. 다이얼로그 닫기
2. 그룹 관리 → 레벨 설정 다시 클릭

**체크 포인트**:
- [ ] **V4 라디오가 선택되어 있음** (마지막 저장 반영)
- [ ] 투자 스타일: Aggressive 표시
- [ ] 매수금액: 200,000원 표시
- [ ] RSI 과매도: 25, 과매수: 75 표시

#### 4-2. GUI 재시작 후 확인
**단계**:
1. GUI 완전히 종료 (Ctrl+C 또는 창 닫기)
2. `python main.py` 재실행
3. 그룹 관리 → 레벨 설정 클릭

**체크 포인트**:
- [ ] 설정이 유지됨
- [ ] V4 라디오 선택됨
- [ ] 모든 값 동일하게 표시됨

---

## 📋 Priority 2: UI/UX 테스트 (중요)

### ✅ 테스트 5: 스크롤 기능 (5분)

#### 5-1. V4 설정 폼 스크롤
**단계**:
1. V4 라디오 선택
2. 설정 폼이 긴지 확인
3. 마우스 휠로 스크롤

**체크 포인트**:
- [ ] 다이얼로그 높이가 화면을 넘지 않음 (600-650px)
- [ ] 세로 스크롤바가 표시됨
- [ ] 마우스 휠로 스크롤 가능
- [ ] 가로 스크롤바 **없음**
- [ ] 스크롤이 부드럽게 작동함

**스크린샷 촬영**: `screenshots/test5_scroll.png`

#### 5-2. Expert 설정 폼 스크롤
**단계**:
1. Expert 라디오 선택
2. Custom 프로필 선택 (슬라이더 5개 표시)
3. 스크롤 동작 확인

**체크 포인트**:
- [ ] 스크롤이 정상 동작함
- [ ] 슬라이더가 잘림 없이 표시됨

---

### ✅ 테스트 6: 공통 매수금액 필드 위치 (5분)

#### 6-1. 위치 확인
**단계**:
1. 자동매수 탭 열기
2. UI 레이아웃 확인

**기대 레이아웃**:
```
┌─────────────────────────────────────┐
│ 📊 자동매수 전략 선택               │
│ ◉ V4 전략                           │
│ ○ Expert 전략                       │
├─────────────────────────────────────┤
│ 💰 1회 매수 금액                    │  ← 이 위치!
│ [100,000] 원                        │
├─────────────────────────────────────┤
│ [스크롤 영역]                       │
│ V4 설정 폼 또는 Expert 설정 폼      │
└─────────────────────────────────────┘
```

**체크 포인트**:
- [ ] 라디오 버튼 바로 아래 위치
- [ ] 스크롤 영역 위에 고정됨
- [ ] 전략 전환 시 항상 보임

#### 6-2. 값 유지 확인
**단계**:
1. 매수금액 150,000원 입력
2. V4 ↔ Expert 라디오 버튼 여러 번 클릭
3. 매수금액 값 확인

**체크 포인트**:
- [ ] 전략 전환 시 값이 유지됨
- [ ] 저장 시 양쪽 전략 모두 동일한 값 사용

---

### ✅ 테스트 7: 통합 저장 (2번 저장) (10분)

#### 7-1. 모든 설정 변경
**단계**:
1. **자동매수 탭**:
   - V4 전략 선택
   - Conservative 선택
   - 매수금액 50,000원

2. **DCA/익절/손절 탭**:
   - DCA 탭 클릭 → 레벨 1개 추가 (예: -5%, 100%)
   - 익절 탭 클릭 → 레벨 1개 추가 (예: +10%, 100%)
   - 손절 탭 클릭 → 레벨 1개 추가 (예: -15%, 100%)

#### 7-2. 1차 저장 (통합 다이얼로그)
**단계**:
1. 하단 **"저장"** 버튼 클릭 (1번째 저장)
2. 알림창 확인

**기대 알림**:
```
✅ 설정이 저장되었습니다

📊 자동매수: V4 전략 - conservative
📈 DCA: 1개 레벨
💰 익절: 1개 레벨
💸 손절: 1개 레벨
```

**체크 포인트**:
- [ ] 4가지 설정 모두 알림에 표시됨
- [ ] 다이얼로그 자동 닫힘

#### 7-3. 2차 저장 (그룹 관리)
**단계**:
1. 그룹 관리 다이얼로그로 돌아옴
2. 하단 **"저장"** 버튼 클릭 (2번째 저장)
3. 알림창 확인

**체크 포인트**:
- [ ] 총 2번 저장으로 완료됨 (기존 4번에서 개선)
- [ ] 모든 설정이 config 파일에 반영됨

#### 7-4. Config 검증
```bash
cat config/trading_config.json | jq '.groups.v4_example_group' | grep -A 5 "dca_settings\|profit_settings\|loss_settings"
```

**체크 포인트**:
- [ ] DCA 레벨이 저장되어 있음
- [ ] 익절 레벨이 저장되어 있음
- [ ] 손절 레벨이 저장되어 있음

---

## 📋 Priority 3: Edge Cases (선택)

### ✅ 테스트 8: Custom Profile (Expert) (10분)

#### 8-1. Custom 프로필 선택
**단계**:
1. Expert 라디오 선택
2. 프로필 드롭다운에서 **"Custom (사용자 정의)"** 선택
3. 가중치 슬라이더 5개 표시 확인:
   - RSI 가중치
   - MACD 가중치
   - Bollinger Bands 가중치
   - Volume 가중치
   - Trend 가중치
4. 신뢰도 임계값 스핀박스 표시 확인

**체크 포인트**:
- [ ] Custom 선택 시 슬라이더 5개 표시됨
- [ ] 다른 프로필 선택 시 슬라이더 숨겨짐
- [ ] 슬라이더 범위: 0.0 ~ 1.0
- [ ] 임계값 범위: 0 ~ 100

**스크린샷 촬영**: `screenshots/test8_custom_profile.png`

#### 8-2. Custom 가중치 저장
**단계**:
1. 가중치 조정:
   - RSI: 0.75
   - MACD: 0.60
   - BB: 0.55
   - Volume: 0.70
   - Trend: 0.50
2. 임계값: 55
3. 저장 클릭

#### 8-3. Config 검증
```bash
cat config/trading_config.json | jq '.groups.v4_example_group.buy_settings.auto_config'
```

**기대 출력**:
```json
{
  "strategy": "expert",
  "expert_profile": "custom",
  "custom_weights": {
    "rsi": 0.75,
    "macd": 0.60,
    "bollinger": 0.55,
    "volume": 0.70,
    "trend": 0.50
  },
  "custom_threshold": 55,
  ...
}
```

**체크 포인트**:
- [ ] `"expert_profile": "custom"` ✓
- [ ] `"custom_weights"` 객체 존재 ✓
- [ ] 5개 가중치 모두 저장됨 ✓
- [ ] `"custom_threshold": 55` ✓

---

### ✅ 테스트 9: 에러 처리 (5분)

#### 9-1. 잘못된 입력 테스트
**단계**:
1. DCA 탭 → 가격 비율에 **0** 입력
2. 저장 시도

**체크 포인트**:
- [ ] 에러 메시지 표시됨
- [ ] 저장이 방지됨
- [ ] 적절한 안내 메시지 표시

#### 9-2. 빈 설정 테스트
**단계**:
1. 모든 DCA 레벨 삭제
2. 저장 시도

**체크 포인트**:
- [ ] 경고 또는 확인 메시지 표시 (레벨 없음 허용 여부)
- [ ] 적절히 처리됨

---

## 📊 테스트 결과 기록

### 통과/실패 체크리스트

| 테스트 번호 | 테스트 이름 | 결과 | 비고 |
|----------|----------|------|------|
| 1 | 라디오 버튼 전환 | ⬜ PASS / ⬜ FAIL | |
| 2 | Expert 전략 저장 | ⬜ PASS / ⬜ FAIL | |
| 3 | V4 전략 저장 | ⬜ PASS / ⬜ FAIL | |
| 4 | 재로드 테스트 | ⬜ PASS / ⬜ FAIL | |
| 5 | 스크롤 기능 | ⬜ PASS / ⬜ FAIL | |
| 6 | 공통 매수금액 필드 | ⬜ PASS / ⬜ FAIL | |
| 7 | 통합 저장 (2번) | ⬜ PASS / ⬜ FAIL | |
| 8 | Custom Profile | ⬜ PASS / ⬜ FAIL | |
| 9 | 에러 처리 | ⬜ PASS / ⬜ FAIL | |

**총 통과**: _____ / 9
**총 실패**: _____ / 9

---

## 🐛 버그 발견 시

### 버그 리포트 템플릿

```markdown
## 버그 #X

**테스트 번호**: [테스트 X]
**심각도**: Critical / High / Medium / Low
**발견 시각**: YYYY-MM-DD HH:MM

**재현 방법**:
1. 단계 1
2. 단계 2
3. 단계 3

**기대 결과**:


**실제 결과**:


**에러 메시지** (있다면):
```
[에러 메시지 붙여넣기]
```

**스크린샷**: screenshots/bug_X.png

**Config 파일 상태** (관련 있다면):
```bash
cat config/trading_config.json | jq '.groups.그룹명.buy_settings.auto_config'
```

**임시 해결책** (있다면):


**추가 정보**:

```

---

## 🎯 테스트 완료 후

### 1. 모든 테스트 통과 시 (9/9)
```bash
# 커밋 준비
git status
git add -A
git commit -m "test: Verify all 9 test cases passed for Expert Strategy integration"
```

### 2. 일부 실패 시
- 발견된 버그를 `BUG_REPORT.md`에 기록
- 스크린샷 첨부
- Config 파일 백업본과 비교

### 3. 테스트 결과 공유
- TEST_CHECKLIST.md 업데이트
- 스크린샷을 `docs/screenshots/testing/` 폴더에 저장

---

## 📞 도움이 필요할 때

### 자주 발생하는 문제

**Q1: 다이얼로그가 열리지 않아요**
```bash
# 로그 확인
tail -f logs/$(ls -t logs/ | head -1)
```

**Q2: 설정이 저장 안 돼요**
```bash
# Config 파일 권한 확인
ls -la config/trading_config.json

# 백업에서 복원
cp config/trading_config_backup_*.json config/trading_config.json
```

**Q3: GUI가 느려요**
- 스크롤 영역 크기 확인
- 다른 프로그램 종료 후 재시도

---

**테스트 완료 시각**: __________
**총 소요 시간**: __________
**최종 판정**: ✅ 배포 가능 / ⚠️ 수정 필요 / ❌ 재작업 필요
