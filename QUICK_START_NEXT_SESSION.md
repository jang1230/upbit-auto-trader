# 🚀 다음 세션 빠른 시작 가이드

**작업일**: 2025-11-13  
**브랜치**: `claude/expert-strategy-011CV4sNxreGsXF9WYeAamPb`  
**상태**: ✅ 구현 완료, 테스트 대기

---

## ⚡ 30초 빠른 시작

```bash
cd /home/user/upbit-auto-trader
git checkout claude/expert-strategy-011CV4sNxreGsXF9WYeAamPb
git log --oneline -3
python main.py
```

---

## 📚 컨텍스트 복원 (5분)

### 1. 작업 요약 읽기
```bash
cat WORK_SESSION_2025-11-13.md | head -100
```

**핵심 변경 사항**:
- ✅ Expert Strategy 버그 수정
- ✅ 설정 다이얼로그 통합 (4번 → 2번 저장)
- ✅ **탭 → 라디오 버튼** 구조 변경 ⭐
- ✅ 스크롤 영역 추가
- ✅ 공통 매수금액 필드

### 2. 최근 커밋 확인
```bash
git log --oneline -10
```

**기대 출력**:
```
38dca11 feat: Add common buy amount field above strategy selection
dbbe2ca feat: Add scroll area and reduce dialog height
11671d4 refactor: Replace nested tabs with radio button strategy selection
...
```

### 3. 변경된 파일 확인
```bash
git diff main..HEAD --name-only
```

**핵심 파일**:
- `gui/auto_buy_settings_dialog_v2.py` (완전 재작성)
- `gui/group_unified_settings_dialog.py` (신규)
- `gui/group_management_dialog.py`
- `core/v4_trading_engine.py`

---

## 🧪 테스트 시작 (10분)

### 간단 테스트 (2분)
```bash
python main.py
# → 그룹 관리
# → 레벨 설정
# → 자동매수 탭
# → 라디오 버튼 2개 확인 ✓
```

### 전체 테스트 (10분)
```bash
# 체크리스트 열기
cat TEST_CHECKLIST.md

# 하나씩 체크하며 테스트
python main.py
```

---

## 🔍 현재 상태 파악 (1분)

```bash
# 브랜치 확인
git branch

# 원격 동기화 상태
git status

# 마지막 작업 확인
git log -1 --format="%h %s%n%b"
```

---

## 📖 상세 문서 위치

| 문서 | 용도 | 명령어 |
|------|------|--------|
| `WORK_SESSION_2025-11-13.md` | 전체 작업 내용 | `cat WORK_SESSION_2025-11-13.md` |
| `TEST_CHECKLIST.md` | 테스트 체크리스트 | `cat TEST_CHECKLIST.md` |
| `QUICK_START_NEXT_SESSION.md` | 이 문서 | `cat QUICK_START_NEXT_SESSION.md` |

---

## 🎯 다음 작업 (우선순위)

### Priority 1: 테스트
- [ ] TEST_CHECKLIST.md의 Priority 1 항목 (4개)
- [ ] 버그 발견 시 즉시 수정

### Priority 2: 버그 수정 (발견 시)
```bash
# 버그 수정 브랜치 생성
git checkout -b fix/[버그-설명]

# 수정 후
git add .
git commit -m "fix: [버그 설명]"
git push -u origin fix/[버그-설명]

# 원래 브랜치로 복귀
git checkout claude/expert-strategy-011CV4sNxreGsXF9WYeAamPb
```

### Priority 3: 배포 준비 (테스트 통과 시)
```bash
# 변경 사항 확인
git diff main..HEAD --stat

# PR 생성 준비
git log --oneline main..HEAD
```

---

## 🐛 버그 발견 시 절차

### 1. 버그 기록
```bash
# TEST_CHECKLIST.md의 "발견된 버그" 섹션에 작성
vim TEST_CHECKLIST.md
```

### 2. 재현 가능성 확인
- 단계별로 정확히 재현 가능한지 확인
- 에러 메시지 복사

### 3. 긴급도 판단
- **Critical**: 프로그램 크래시, 데이터 손실
- **High**: 핵심 기능 동작 안 함
- **Medium**: 일부 기능 오작동
- **Low**: UI 불편, 사소한 버그

### 4. 수정 여부 결정
- Critical/High → 즉시 수정
- Medium/Low → 이슈로 기록 후 나중에 수정

---

## 💡 자주 사용하는 명령어

```bash
# 현재 브랜치 상태
git status

# 최근 커밋 5개
git log --oneline -5

# 특정 파일 변경 내역
git diff gui/auto_buy_settings_dialog_v2.py

# 변경사항 되돌리기 (주의!)
git checkout -- [파일명]

# 최신 코드 가져오기
git pull origin claude/expert-strategy-011CV4sNxreGsXF9WYeAamPb

# GUI 실행
python main.py

# 로그 확인 (실시간)
tail -f logs/trading_*.log
```

---

## 🆘 문제 해결

### GUI가 안 열릴 때
```bash
# 의존성 확인
pip list | grep PySide6

# 재설치
pip install --upgrade PySide6

# Python 버전 확인
python --version  # 3.8+ 필요
```

### Import 에러
```bash
# 프로젝트 루트인지 확인
pwd  # /home/user/upbit-auto-trader 이어야 함

# PYTHONPATH 설정
export PYTHONPATH=/home/user/upbit-auto-trader:$PYTHONPATH
```

### Config 파일 에러
```bash
# 템플릿으로 초기화
cp config/trading_config_template.json config/trading_config.json

# 권한 확인
ls -la config/
```

---

## 📞 도움이 필요할 때

### 이전 대화 컨텍스트 공유
```
1. "오늘(11/13) 작업한 내용 요약해줘"
2. WORK_SESSION_2025-11-13.md 내용 참조
3. 특정 커밋 코드 확인: git show [커밋해시]
```

### 버그 리포트 형식
```
버그 발견:
- 위치: gui/auto_buy_settings_dialog_v2.py
- 증상: Expert 선택 후 저장하면 에러
- 에러: [에러 메시지 붙여넣기]
- 재현: 1) ... 2) ... 3) ...
```

---

## ✅ 체크리스트 (시작 전)

- [ ] 올바른 브랜치에 있는가?
  ```bash
  git branch  # * claude/expert-strategy-011CV4sNxreGsXF9WYeAamPb
  ```

- [ ] 최신 코드를 받았는가?
  ```bash
  git pull origin claude/expert-strategy-011CV4sNxreGsXF9WYeAamPb
  ```

- [ ] 작업 요약을 읽었는가?
  ```bash
  cat WORK_SESSION_2025-11-13.md | head -50
  ```

- [ ] 테스트 체크리스트를 확인했는가?
  ```bash
  cat TEST_CHECKLIST.md
  ```

---

## 🎉 모든 테스트 통과 시

### 1. 축하 메시지 작성
```bash
echo "✅ 모든 테스트 통과! $(date)" >> TEST_RESULTS.txt
```

### 2. 브랜치 병합 준비
```bash
# 1. 변경 사항 정리
git log --oneline main..HEAD > commits_summary.txt

# 2. 통계
git diff main..HEAD --stat

# 3. PR 제목 초안
echo "feat: Expert Strategy + GUI Improvements (Radio Button, Unified Dialog)" > PR_TITLE.txt
```

### 3. 다음 단계 논의
- 메인 브랜치 병합?
- 추가 기능 구현?
- 배포 준비?

---

**생성일**: 2025-11-13  
**다음 업데이트**: 테스트 완료 후
