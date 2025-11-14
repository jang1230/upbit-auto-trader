# 📊 테스트 요약 - Expert Strategy 통합

**브랜치**: `claude/expert-strategy-clone-01ELiN8eY3EZwEi2gSx4xARg`
**작업 날짜**: 2025-11-13
**테스트 대상**: 33개 커밋 (새벽 00:06 ~ 23:45)

---

## 🎯 테스트해야 할 핵심 기능

### 1. 라디오 버튼 구조 (커밋: 11671d4)
- **변경 전**: 탭 중첩 (GroupUnified → Tab1 → V4/Expert 탭)
- **변경 후**: 라디오 버튼 2개 (V4 / Expert)
- **목적**: UI 단순화, 사용자 혼란 방지

**테스트 포인트**:
- 라디오 버튼 2개만 표시되는가?
- 클릭 시 즉시 전환되는가?
- 선택된 버튼이 명확히 표시되는가?

---

### 2. V4/Expert 필드 분리 (커밋: 89d56c3, f310af5)
- **문제**: V4로 저장했는데 Expert 필드가 남아있음
- **해결**: get_config()에서 전략별로 필드 분리

**테스트 포인트**:
- V4 저장 시: `investment_style`, `indicators` 있음, `expert_profile` **없음**
- Expert 저장 시: `expert_profile` 있음, `investment_style`, `indicators` **없음**

---

### 3. 공통 매수금액 필드 (커밋: 38dca11)
- **변경 전**: V4에만 매수금액, Expert는 없음
- **변경 후**: 라디오 버튼 바로 아래 공통 필드

**테스트 포인트**:
- V4 폼 하단에 매수금액 필드 **없음**
- 공통 필드가 라디오 버튼과 스크롤 사이에 위치
- 전략 전환 시 값 유지됨

---

### 4. 스크롤 영역 (커밋: dbbe2ca)
- **문제**: V4 설정이 길어서 화면 밖으로 넘침
- **해결**: 높이 제한 + 스크롤 영역 추가

**테스트 포인트**:
- 다이얼로그 높이 600-650px
- 세로 스크롤 가능
- 가로 스크롤 없음

---

### 5. 통합 설정 다이얼로그 (커밋: 5958909~20c5d44)
- **변경 전**: 자동매수, DCA, 익절, 손절 각각 저장 (4번)
- **변경 후**: 통합 다이얼로그 → 1번 저장 (+ 그룹 관리 1번 = 총 2번)

**테스트 포인트**:
- 자동매수 + DCA/익절/손절 탭이 하나의 다이얼로그에 통합됨
- 저장 버튼 1번 클릭으로 모든 설정 반영
- 그룹 관리에서 1번 더 저장하면 완료 (총 2번)

---

### 6. Expert 10개 프로필 (커밋: d307ccb)
- RSI 전문가, 모멘텀 전문가, 볼린저 전문가, 거래량 전문가
- 균형형, 보수형, 공격형
- 스윙 트레이더, 데이 트레이더, 스캘퍼

**테스트 포인트**:
- 프로필 드롭다운에 10개 옵션 표시
- 각 프로필 선택 가능
- Custom 선택 시 가중치 슬라이더 5개 표시

---

### 7. Custom 가중치 (커밋: 2dfef06, 58ffaee)
- **기능**: 사용자가 5개 지표 가중치 직접 조정
- **지표**: RSI, MACD, Bollinger Bands, Volume, Trend
- **범위**: 0.0 ~ 1.0

**테스트 포인트**:
- Custom 프로필 선택 시 슬라이더 표시
- 가중치 조정 가능
- 저장 시 `custom_weights` 객체 생성
- `custom_threshold` 필드 저장

---

## 📝 테스트 우선순위

### Priority 1: 필수 (배포 전 반드시 테스트)
1. ✅ 라디오 버튼 전환
2. ✅ Expert 전략 저장
3. ✅ V4 전략 저장
4. ✅ 재로드 테스트

**예상 시간**: 30분

---

### Priority 2: 중요 (UX 개선 검증)
5. ✅ 스크롤 기능
6. ✅ 공통 매수금액 필드
7. ✅ 통합 저장 (2번 저장)

**예상 시간**: 20분

---

### Priority 3: 선택 (Edge Case)
8. ✅ Custom Profile 테스트
9. ✅ 에러 처리

**예상 시간**: 15분

---

## 🔍 검증 방법

### GUI 테스트
```bash
python main.py
```

### Config 파일 검증
```bash
# 전체 보기
cat config/trading_config.json | jq '.groups.v4_example_group.buy_settings.auto_config'

# 필드 검증
cat config/trading_config.json | jq '.groups.v4_example_group.buy_settings.auto_config | keys'
```

### 코드 레벨 검증 (자동화)
```bash
python test_expert_strategy_integration.py
```

---

## 📂 테스트 문서

### 1. DETAILED_TEST_GUIDE.md (30페이지)
- **대상**: 처음 테스트하는 사람
- **내용**: 스크린샷, 체크리스트, 단계별 가이드
- **시간**: 60분 (전체 테스트)

### 2. QUICK_TEST_CHECKLIST.md (2페이지)
- **대상**: 빠른 검증
- **내용**: 핵심 5가지 체크
- **시간**: 5분

### 3. TEST_CHECKLIST.md (기존)
- **대상**: 체크박스 형식
- **내용**: 9개 테스트 항목
- **시간**: 45분

---

## ✅ 성공 기준

### 모든 테스트 통과 조건

1. **라디오 버튼 동작**
   - [ ] 2개만 표시
   - [ ] 즉시 전환
   - [ ] 명확한 선택 표시

2. **V4 저장 후 Config**
   ```json
   {
     "strategy": "v4_auto_buy",
     "investment_style": "...",
     "indicators": {...}
     // expert_profile 없음
     // custom_weights 없음
   }
   ```

3. **Expert 저장 후 Config**
   ```json
   {
     "strategy": "expert",
     "expert_profile": "...",
     // investment_style 없음
     // indicators 없음
   }
   ```

4. **UI/UX**
   - [ ] 스크롤 정상 동작
   - [ ] 공통 매수금액 필드 위치 정확
   - [ ] 2번 저장으로 완료

---

## 🐛 예상 이슈

### 1. PySide6 import 에러
**원인**: GUI 라이브러리 미설치
**해결**: `pip install PySide6`

### 2. Config 파일 손상
**원인**: 잘못된 JSON 형식
**해결**: 백업에서 복원 또는 템플릿 복사

### 3. 설정이 저장 안됨
**원인**: 파일 권한 문제
**해결**: `chmod 644 config/trading_config.json`

---

## 📊 테스트 결과 양식

```markdown
## 테스트 결과 보고

**테스터**: __________
**날짜**: 2025-__-__
**소요 시간**: ____ 분

### 통과 (✅)
- 테스트 1: 라디오 버튼 전환
- 테스트 2: Expert 저장
- ...

### 실패 (❌)
- 테스트 X: [문제 설명]
  - 재현 방법: ...
  - 스크린샷: ...

### 최종 판정
- [ ] ✅ 배포 가능
- [ ] ⚠️ 일부 수정 필요
- [ ] ❌ 재작업 필요
```

---

## 🎯 다음 단계

### 모든 테스트 통과 시
1. 커밋 메시지 작성
   ```bash
   git add -A
   git commit -m "test: Verify Expert Strategy integration - all tests passed"
   ```

2. PR 생성 또는 메인 브랜치 병합

3. 배포 준비
   - BUILD_GUIDE.md 확인
   - exe 빌드 테스트

### 일부 테스트 실패 시
1. 버그 리포트 작성 (DETAILED_TEST_GUIDE.md 참고)
2. 이슈 생성
3. 수정 작업

---

**작성일**: 2025-11-13
**작성자**: Claude AI
**문서 버전**: 1.0
