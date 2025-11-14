# ⚡ 빠른 테스트 체크리스트

**브랜치**: `claude/expert-strategy-clone-01ELiN8eY3EZwEi2gSx4xARg`
**테스트 날짜**: __________

---

## 🚀 5분 퀵 체크

### 1. 라디오 버튼 ✓
```
python main.py
→ 그룹 관리 → 레벨 설정
→ 라디오 버튼 2개 확인
→ 클릭 시 즉시 전환
```
- [ ] ◉ V4 전략
- [ ] ○ Expert 전략
- [ ] 즉시 전환됨

### 2. Expert 저장 ✓
```
→ Expert 선택
→ 균형형 전문가
→ 100,000원
→ 저장
```
- [ ] 알림: "Expert 전략 - balanced_expert"
- [ ] Config: `"strategy": "expert"`
- [ ] V4 필드 없음

### 3. V4 저장 ✓
```
→ 다시 열기
→ V4 선택
→ Aggressive
→ 200,000원
→ 저장
```
- [ ] 알림: "V4 전략 - aggressive"
- [ ] Config: `"strategy": "v4_auto_buy"`
- [ ] Expert 필드 없음

### 4. 재로드 ✓
```
→ 다이얼로그 다시 열기
```
- [ ] V4 선택됨
- [ ] Aggressive 표시
- [ ] 200,000원 표시

### 5. 스크롤 ✓
```
→ V4 선택
→ 마우스 휠
```
- [ ] 세로 스크롤 가능
- [ ] 가로 스크롤 없음
- [ ] 높이 600-650px

---

## 📋 Config 검증 명령어

### Expert 저장 후
```bash
cat config/trading_config.json | jq '.groups.v4_example_group.buy_settings.auto_config' | grep -E "strategy|expert_profile|buy_amount"
```

**기대 결과**:
```json
"strategy": "expert",
"expert_profile": "balanced_expert",
"buy_amount_krw": 100000
```

**체크**:
- [ ] `"strategy": "expert"`
- [ ] `"expert_profile"` 존재
- [ ] `"investment_style"` **없음**
- [ ] `"indicators"` **없음**

---

### V4 저장 후
```bash
cat config/trading_config.json | jq '.groups.v4_example_group.buy_settings.auto_config' | grep -E "strategy|investment_style|buy_amount"
```

**기대 결과**:
```json
"strategy": "v4_auto_buy",
"investment_style": "aggressive",
"buy_amount_krw": 200000
```

**체크**:
- [ ] `"strategy": "v4_auto_buy"`
- [ ] `"investment_style"` 존재
- [ ] `"indicators"` 존재
- [ ] `"expert_profile"` **없음**
- [ ] `"custom_weights"` **없음**

---

## 🎯 최종 판정

### ✅ 모든 체크 통과
→ **배포 가능**, 다음 단계 진행

### ⚠️ 일부 실패
→ `DETAILED_TEST_GUIDE.md` 참고하여 상세 테스트

### ❌ 심각한 버그 발견
→ 버그 리포트 작성 후 수정 요청

---

**테스트 시간**: 약 5분
**테스터**: __________
**결과**: ✅ / ⚠️ / ❌
