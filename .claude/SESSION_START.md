# 세션 시작 가이드

> 매 대화 시작 시 이 파일과 함께 컨텍스트를 제공하세요.

---

## 빠른 시작 (복사용)

```
upbit-auto-trader 프로젝트 작업을 계속하려고 합니다.

브랜치: claude/duplicate-branch-history-0182BCX6kFJuNtc2y14sG1K9

[첨부: .claude/PROJECT_CONTEXT.md]
[첨부: .claude/FEATURE_LIST.json]
[첨부: .claude/PROGRESS_LOG.md]

오늘 작업: [작업 내용 기술]

관련 파일도 함께 첨부합니다:
[첨부: 관련 .py 파일들]
```

---

## 세션 시작 체크리스트

### 1. 컨텍스트 파일 제공
- [ ] `PROJECT_CONTEXT.md` - 프로젝트 개요, 아키텍처
- [ ] `FEATURE_LIST.json` - 기능 상태, 해결된 이슈
- [ ] `PROGRESS_LOG.md` - 최근 진행 상황

### 2. 현재 브랜치 명시
```
브랜치: claude/duplicate-branch-history-0182BCX6kFJuNtc2y14sG1K9
```

### 3. 오늘 작업 명시
```
오늘 작업:
1. [구체적인 작업 내용]
2. [관련 파일 경로]
```

### 4. 관련 코드 파일 첨부
- 작업할 파일 직접 첨부
- 또는 `git diff` 결과 첨부
- 또는 최근 커밋 로그 (`git log -p -10`)

---

## 작업 유형별 템플릿

### 🐛 버그 수정 요청
```
버그 수정이 필요합니다.

증상: [증상 설명]
재현 방법: [재현 단계]
예상 원인: [추측되는 원인]
관련 파일: [파일 경로]

[파일 첨부]
```

### ✨ 새 기능 개발
```
새 기능을 개발하려고 합니다.

기능: [기능 설명]
요구사항:
1. [요구사항 1]
2. [요구사항 2]

관련 기존 코드: [참고할 파일]

[파일 첨부]
```

### 🔧 리팩토링
```
코드 리팩토링이 필요합니다.

대상: [파일/모듈]
목표: [개선 목표]
제약: [변경하면 안 되는 것]

[파일 첨부]
```

### 📊 분석 요청
```
코드 분석이 필요합니다.

분석 대상: [파일/모듈]
알고 싶은 것:
1. [질문 1]
2. [질문 2]

[파일 첨부]
```

---

## 세션 종료 요청

작업 완료 후 항상 요청하세요:

```
작업을 마무리하기 전에:
1. PROGRESS_LOG.md에 추가할 오늘 세션 내용을 작성해주세요
2. FEATURE_LIST.json에서 변경된 항목이 있으면 알려주세요
3. 다음 세션에서 해야 할 일을 정리해주세요
4. git 커밋 메시지를 제안해주세요 (fix:/feat:/refactor: 형식)
```

---

## 자주 사용하는 명령어

### 프로젝트 상태 확인
```bash
# 현재 브랜치
git branch --show-current

# 최근 커밋
git log --oneline -10

# 변경된 파일
git status

# 특정 커밋 상세
git show [commit_hash]
```

### 커밋 diff 추출
```bash
# 최근 10개 커밋 diff (Claude에게 제공용)
git log -p -10 > commits_with_diff.txt

# 특정 파일의 최근 변경
git log -p -5 -- core/v4_trading_engine.py
```

### 테스트 실행
```bash
# GUI 실행
python main.py

# Dry-run 모드 확인
# config/trading_config.json → "mode": "dryrun"
```

### 커밋
```bash
git add .
git commit -m "fix: 커밋 메시지"
git push origin claude/duplicate-branch-history-0182BCX6kFJuNtc2y14sG1K9
```

---

## 현재 우선순위 (2025-12-01 기준)

| 우선순위 | 작업 | 상태 |
|---------|------|------|
| 1 | F25: 통합 테스트 시나리오 작성 | planned |
| 2 | F26: Dry-run 1주일 테스트 | planned |
| 3 | F27: Live 소액 배포 | planned |

---

## 주요 파일 수정 시 주의사항

### `core/v4_trading_engine.py` (134회 수정됨)
- Phase A-B-C-D 흐름 유지
- pending_order 처리 로직 주의
- 텔레그램 알림 중복 체크

### `core/upbit_websocket.py` (27회 수정됨)
- `threading.Lock` 사용 필수 (`_dedup_lock`)
- TTL 기반 중복 제거 패턴
- JWT 알고리즘: HS256 (HS512 아님!)

### `core/position_manager.py` (39회 수정됨)
- `group_id=None` 대신 `"group_null"` 사용
- `recent_bot_sells` 딕셔너리 체크
- dictionary iteration 시 copy() 사용

### `gui/main_window.py` (102회 수정됨)
- Signal 패턴 사용 (스레드 안전)
- GUI 업데이트는 메인 스레드에서만

---

## 코드 패턴 참고

### TTL 기반 중복 제거
```python
self._recent_messages = {}  # {(uuid, state, timestamp): received_time}
self._dedup_ttl_seconds = 5
self._dedup_lock = threading.Lock()

with self._dedup_lock:
    msg_key = (order_uuid, state, timestamp)
    now = time.time()
    
    # TTL 지난 메시지 정리
    expired = [k for k, v in self._recent_messages.items() 
               if now - v > self._dedup_ttl_seconds]
    for k in expired:
        del self._recent_messages[k]
    
    # 중복 체크
    if msg_key in self._recent_messages:
        return  # 스킵
    
    self._recent_messages[msg_key] = now
```

### 봇 매도 추적
```python
# close_position()에서 등록
if close_reason in ['profit', 'loss']:
    self.recent_bot_sells[symbol] = time.time()

# sync_with_myasset()에서 체크
if symbol in self.recent_bot_sells:
    elapsed = time.time() - self.recent_bot_sells[symbol]
    if elapsed < 10:  # 10초 이내면 스킵
        continue
```

### 그룹 없는 포지션 처리
```python
# ❌ 잘못된 방법 (sync_with_upbit에서 삭제됨)
self.position_manager.update_position(symbol, {'group_id': None})

# ✅ 올바른 방법
self.position_manager.update_position(symbol, {'group_id': 'group_null'})
```

---

## 문서 참조

| 문서 | 경로 | 설명 |
|------|------|------|
| V4 상세 설계 | `docs/DESIGN_V4_COMPLETE.md` | 172KB, 18개 섹션 |
| Live 체크리스트 | `docs/LIVE_TRADING_CHECKLIST.md` | 배포 전 확인사항 |
| 트러블슈팅 | `docs/TROUBLESHOOTING.md` | 알려진 이슈 해결 |
| 테스트 시나리오 | `docs/TEST_SCENARIOS.md` | 테스트 케이스 |
