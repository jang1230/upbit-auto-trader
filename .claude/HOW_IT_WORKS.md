# Claude Code 하네스 시스템 사용 가이드

## 목차
1. [문제: 왜 하네스가 필요한가?](#1-문제-왜-하네스가-필요한가)
2. [해결책: 하네스 시스템의 원리](#2-해결책-하네스-시스템의-원리)
3. [Claude Code에서의 작동 방식](#3-claude-code에서의-작동-방식)
4. [각 파일의 역할](#4-각-파일의-역할)
5. [설치 및 설정](#5-설치-및-설정)
6. [실제 사용 예시](#6-실제-사용-예시)
7. [고급 활용법](#7-고급-활용법)

---

## 1. 문제: 왜 하네스가 필요한가?

### Claude의 근본적 한계

```
┌─────────────────────────────────────────────────────────────┐
│                    세션 1                                    │
│  "DCA 버그를 수정해줘"                                        │
│  → Claude: 코드 분석, 버그 수정, 커밋                         │
│  → 컨텍스트: 프로젝트 구조 파악, 코드 패턴 이해                │
└─────────────────────────────────────────────────────────────┘
                           ⬇️ 세션 종료
                    ❌ 모든 기억 삭제 ❌
                           ⬇️
┌─────────────────────────────────────────────────────────────┐
│                    세션 2                                    │
│  "WebSocket 중복 문제 해결해줘"                               │
│  → Claude: "이 프로젝트가 뭐죠? 구조를 알려주세요..."         │
│  → 처음부터 다시 시작 😫                                      │
└─────────────────────────────────────────────────────────────┘
```

**Claude의 한계:**
1. **세션 간 기억 없음** - 매 대화가 백지 상태에서 시작
2. **컨텍스트 윈도우 제한** - 한 번에 처리할 수 있는 정보량 한계 (~200K 토큰)
3. **프로젝트 히스토리 모름** - 이전에 무슨 작업을 했는지 알 수 없음

### 실제로 겪는 문제들

```
❌ "이 파일 왜 이렇게 수정했어요?" → 이전 세션 기억 없음
❌ "저번에 했던 것처럼 해줘" → 저번이 언제인지 모름
❌ 같은 버그를 여러 번 다르게 수정 → 일관성 없음
❌ 프로젝트 컨벤션 무시 → 코드 스타일 불일치
❌ 이미 해결한 문제 다시 발생 → 학습 효과 없음
```

---

## 2. 해결책: 하네스 시스템의 원리

### 핵심 아이디어: "외부 기억 장치"

```
┌──────────────────────────────────────────────────────────────┐
│                     .claude/ 폴더                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌────────────────┐ │
│  │ PROJECT_CONTEXT │ │  FEATURE_LIST   │ │  PROGRESS_LOG  │ │
│  │     .md         │ │     .json       │ │      .md       │ │
│  │                 │ │                 │ │                │ │
│  │ - 아키텍처      │ │ - 기능 상태     │ │ - 작업 기록    │ │
│  │ - 파일 구조     │ │ - 해결된 이슈   │ │ - 커밋 히스토리│ │
│  │ - 코드 패턴     │ │ - 다음 우선순위 │ │ - 진행 상황    │ │
│  └─────────────────┘ └─────────────────┘ └────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                              ⬇️
                    Claude가 세션 시작 시 읽음
                              ⬇️
┌──────────────────────────────────────────────────────────────┐
│  Claude: "아, 이 프로젝트는 V4 트레이딩 봇이고,               │
│          최근에 WebSocket 중복 문제를 Lock으로 해결했고,      │
│          다음은 통합 테스트를 해야 하는군요!"                 │
└──────────────────────────────────────────────────────────────┘
```

### 비유: 의사의 진료 기록

```
환자(프로젝트)가 병원(Claude)에 올 때마다:

❌ 하네스 없이:
   의사: "처음 뵙겠습니다. 증상이 뭐죠?"
   환자: "아니 저번에 왔었는데..."
   의사: "기록이 없네요. 처음부터 설명해주세요."

✅ 하네스 있을 때:
   의사: (차트를 보며) "아, 지난번 두통으로 오셨고,
         MRI 결과 이상 없었고, 진통제 처방했네요.
         오늘은 어떠세요?"
```

---

## 3. Claude Code에서의 작동 방식

### 3.1 CLAUDE.md - 자동 로딩의 핵심

Claude Code는 프로젝트 루트의 `CLAUDE.md` 파일을 **자동으로** 읽습니다.

```
upbit-auto-trader/
├── CLAUDE.md          ← ⭐ Claude Code가 자동으로 읽는 파일
├── .claude/
│   ├── PROJECT_CONTEXT.md
│   ├── FEATURE_LIST.json
│   ├── PROGRESS_LOG.md
│   └── SESSION_START.md
├── main.py
├── core/
└── gui/
```

**CLAUDE.md 예시:**
```markdown
# Upbit Auto Trader V4

이 프로젝트의 컨텍스트는 `.claude/` 폴더에 있습니다.

작업 시작 전 반드시 읽어야 할 파일:
1. `.claude/PROJECT_CONTEXT.md` - 프로젝트 개요
2. `.claude/FEATURE_LIST.json` - 기능 상태
3. `.claude/PROGRESS_LOG.md` - 최근 작업 기록

## 중요 규칙
- group_id는 None 대신 "group_null" 사용
- WebSocket에서 threading.Lock 필수
- 커밋 메시지: fix:/feat:/refactor: 형식
```

### 3.2 작동 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  1. Claude Code 시작                                        │
│     $ claude                                                │
└─────────────────────────────────────────────────────────────┘
                              ⬇️
┌─────────────────────────────────────────────────────────────┐
│  2. CLAUDE.md 자동 로딩                                     │
│     Claude: (CLAUDE.md 읽음)                                │
│     "아, .claude/ 폴더에 컨텍스트가 있군요"                  │
└─────────────────────────────────────────────────────────────┘
                              ⬇️
┌─────────────────────────────────────────────────────────────┐
│  3. 하네스 파일 참조                                        │
│     Claude: (PROJECT_CONTEXT.md 읽음)                       │
│     "V4 트레이딩 봇, PySide6 GUI, WebSocket 사용..."        │
└─────────────────────────────────────────────────────────────┘
                              ⬇️
┌─────────────────────────────────────────────────────────────┐
│  4. 작업 수행                                               │
│     사용자: "WebSocket 버그 고쳐줘"                          │
│     Claude: (PROGRESS_LOG.md 확인)                          │
│     "이전에 Lock으로 해결했던 패턴을 적용하면 되겠네요"      │
└─────────────────────────────────────────────────────────────┘
                              ⬇️
┌─────────────────────────────────────────────────────────────┐
│  5. 세션 종료 시 업데이트                                   │
│     Claude: PROGRESS_LOG.md에 오늘 작업 기록                │
│     Claude: FEATURE_LIST.json 상태 업데이트                 │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Claude Code의 파일 읽기 우선순위

```
1순위: CLAUDE.md (프로젝트 루트) - 항상 자동 로딩
2순위: .claude/ 폴더 내 파일들 - CLAUDE.md에서 참조 시 로딩
3순위: 사용자가 명시적으로 언급한 파일
4순위: 작업에 필요한 소스 코드 파일
```

---

## 4. 각 파일의 역할

### 4.1 PROJECT_CONTEXT.md - "프로젝트 신분증"

**목적:** Claude가 프로젝트를 빠르게 이해하도록 함

```markdown
포함 내용:
├── 프로젝트 개요 (한 줄 설명)
├── 기술 스택 (Python, PySide6, WebSocket...)
├── 아키텍처 다이어그램
├── 핵심 모듈 목록 (파일별 역할)
├── 파일 구조 트리
├── 코드 컨벤션
│   ├── 커밋 메시지 형식
│   ├── 로깅 패턴 (이모지 규칙)
│   └── 중복 방지 패턴
└── 알려진 이슈 패턴 (해결책 포함)
```

**Claude가 활용하는 방식:**
```
사용자: "새 기능 추가해줘"
Claude: (PROJECT_CONTEXT.md 참조)
        - 어떤 파일에 추가해야 하는지 파악
        - 기존 코드 패턴에 맞춰 작성
        - 커밋 메시지 형식 준수
```

### 4.2 FEATURE_LIST.json - "기능 현황판"

**목적:** 무엇이 완료됐고, 무엇이 남았는지 추적

```json
{
  "features": [
    {
      "id": "F001",
      "description": "무제한 그룹 생성",
      "status": "done",        // done, in_progress, planned
      "files": ["core/group_manager.py"]
    }
  ],
  "resolved_issues": [
    {
      "id": "I001",
      "description": "WebSocket 중복 수신",
      "solution": "threading.Lock + TTL"
    }
  ],
  "next_priorities": ["통합 테스트", "Live 배포"]
}
```

**Claude가 활용하는 방식:**
```
사용자: "다음에 뭐 해야 해?"
Claude: (FEATURE_LIST.json 참조)
        "next_priorities에 따르면 통합 테스트가 우선입니다."

사용자: "이 버그 어떻게 해결해?"
Claude: (resolved_issues 참조)
        "비슷한 이슈 I001을 Lock으로 해결했으니 같은 패턴 적용"
```

### 4.3 PROGRESS_LOG.md - "작업 일지"

**목적:** 이전 세션에서 무슨 작업을 했는지 기록

```markdown
## 2025-12-01 (최신)

### 작업 내용
1. **그룹 삭제 시 포지션 처리 수정** (`b85fba1`)
   - group_id = None → "group_null" 변경
   - 파일: core/group_manager.py

### 변경된 파일
- core/group_manager.py
- core/upbit_websocket.py

### 다음 세션 권장 작업
1. 통합 테스트 시나리오 작성
```

**Claude가 활용하는 방식:**
```
사용자: "어제 뭐 했더라?"
Claude: (PROGRESS_LOG.md 참조)
        "12/1에 group_null 수정, Lock 추가 작업 했습니다."

사용자: "이어서 작업해줘"
Claude: (PROGRESS_LOG.md의 "다음 세션 권장 작업" 참조)
        "통합 테스트 시나리오 작성부터 시작하겠습니다."
```

### 4.4 SESSION_START.md - "작업 매뉴얼"

**목적:** 새 세션 시작 시 참고할 템플릿과 가이드

```markdown
포함 내용:
├── 빠른 시작 템플릿 (복사용)
├── 작업 유형별 템플릿
│   ├── 버그 수정 요청
│   ├── 새 기능 개발
│   └── 리팩토링
├── 자주 사용하는 명령어
├── 주요 파일 수정 시 주의사항
└── 코드 패턴 예시 (복붙용)
```

---

## 5. 설치 및 설정

### 5.1 기본 설치

```bash
# 1. 프로젝트 루트로 이동
cd upbit-auto-trader

# 2. 하네스 파일 압축 해제
unzip claude-harness-v2.zip

# 3. CLAUDE.md 생성 (Claude Code 자동 로딩용)
cat > CLAUDE.md << 'EOF'
# Upbit Auto Trader V4

## 컨텍스트 파일 위치
작업 시작 전 `.claude/` 폴더의 파일들을 참조하세요:

1. `.claude/PROJECT_CONTEXT.md` - 프로젝트 구조, 아키텍처
2. `.claude/FEATURE_LIST.json` - 기능 상태, 해결된 이슈
3. `.claude/PROGRESS_LOG.md` - 최근 작업 기록, 진행 상황

## 필수 규칙
- `group_id`는 `None` 대신 `"group_null"` 문자열 사용
- WebSocket 메시지 처리 시 `threading.Lock` 필수
- 커밋 메시지 형식: `fix:`, `feat:`, `refactor:`, `docs:`
- 로그 이모지: ✅성공, 🎯이벤트, ⚠️경고, ❌에러

## 현재 브랜치
`claude/duplicate-branch-history-0182BCX6kFJuNtc2y14sG1K9`
EOF

# 4. Git에 추가
git add .claude/ CLAUDE.md
git commit -m "docs: Claude Code 하네스 시스템 추가"
```

### 5.2 파일 구조 확인

```
upbit-auto-trader/
├── CLAUDE.md                    ← Claude Code 자동 로딩
├── .claude/
│   ├── PROJECT_CONTEXT.md       ← 프로젝트 개요
│   ├── FEATURE_LIST.json        ← 기능 상태
│   ├── PROGRESS_LOG.md          ← 작업 기록
│   └── SESSION_START.md         ← 사용 가이드
├── main.py
├── core/
├── gui/
└── ...
```

---

## 6. 실제 사용 예시

### 6.1 Claude Code에서 새 세션 시작

```bash
# 터미널에서 Claude Code 실행
$ cd upbit-auto-trader
$ claude

# Claude가 자동으로 CLAUDE.md를 읽고 컨텍스트 파악
```

### 6.2 작업 요청 예시

**버그 수정:**
```
You: WebSocket에서 같은 메시지가 두 번 처리되는 버그가 있어

Claude: (PROGRESS_LOG.md와 resolved_issues 참조)
        "I001에서 비슷한 문제를 Lock + TTL로 해결했습니다.
         core/upbit_websocket.py의 기존 패턴을 확인해볼게요..."
```

**새 기능 개발:**
```
You: 거래 알림을 Discord로도 보내고 싶어

Claude: (PROJECT_CONTEXT.md 참조)
        "현재 텔레그램 알림은 core/v4_trading_engine.py에서 처리하고 있네요.
         같은 패턴으로 Discord 알림을 추가하겠습니다.
         커밋 메시지는 'feat: Discord 알림 기능 추가' 형식으로 할게요."
```

**진행 상황 확인:**
```
You: 지금 어디까지 했어?

Claude: (FEATURE_LIST.json 참조)
        "현재 상태:
         - 완료: 27개 기능 (F001~F024)
         - 다음 우선순위: 통합 테스트, Dry-run 1주일, Live 배포"
```

### 6.3 세션 종료 시

```
You: 오늘 작업 마무리하고 기록 업데이트해줘

Claude: PROGRESS_LOG.md에 추가할 내용:
        
        ## 2025-12-02 세션
        
        ### 작업 내용
        1. **Discord 알림 기능 추가** (`abc1234`)
           - Discord Webhook 연동
           - 파일: core/v4_trading_engine.py, config/trading_config.json
        
        ### 다음 세션 권장 작업
        1. Discord 알림 테스트
        2. 통합 테스트 시나리오 작성
```

---

## 7. 고급 활용법

### 7.1 하네스 파일 자동 업데이트

세션 종료 시 Claude에게 요청:

```
You: 오늘 세션 마무리하면서:
1. PROGRESS_LOG.md 업데이트
2. FEATURE_LIST.json에서 상태 변경된 것 수정
3. 다음 우선순위 정리
```

### 7.2 새 프로젝트에 하네스 적용

```bash
# 1. .claude 폴더 생성
mkdir .claude

# 2. PROJECT_CONTEXT.md 작성 (Claude에게 요청)
# "이 프로젝트 분석해서 PROJECT_CONTEXT.md 만들어줘"

# 3. FEATURE_LIST.json 작성
# "현재 기능 목록 정리해서 FEATURE_LIST.json 만들어줘"

# 4. PROGRESS_LOG.md 초기화
echo "# 진행 로그" > .claude/PROGRESS_LOG.md

# 5. CLAUDE.md 생성
# (위의 예시 참고)
```

### 7.3 팀 협업 시

```
.claude/
├── PROJECT_CONTEXT.md      # 모든 팀원 공유 (Git 추적)
├── FEATURE_LIST.json       # 모든 팀원 공유 (Git 추적)
├── PROGRESS_LOG.md         # 모든 팀원 공유 (Git 추적)
├── SESSION_START.md        # 모든 팀원 공유 (Git 추적)
└── MY_NOTES.md             # 개인용 (gitignore)
```

### 7.4 프로젝트 크기별 권장 구성

**소규모 프로젝트 (< 10개 파일):**
```
CLAUDE.md만으로 충분
```

**중규모 프로젝트 (10~50개 파일):**
```
CLAUDE.md + PROJECT_CONTEXT.md + PROGRESS_LOG.md
```

**대규모 프로젝트 (50개+ 파일):**
```
전체 하네스 시스템 사용
+ 모듈별 컨텍스트 파일 분리 가능
```

---

## 요약: 왜 이 시스템이 효과적인가?

| 문제 | 하네스 해결책 |
|------|--------------|
| 세션 간 기억 없음 | PROGRESS_LOG.md로 작업 이력 유지 |
| 프로젝트 구조 모름 | PROJECT_CONTEXT.md로 즉시 파악 |
| 코드 패턴 불일치 | 컨벤션 문서화 + 예시 제공 |
| 같은 버그 반복 | resolved_issues로 해결책 기록 |
| 우선순위 혼란 | FEATURE_LIST.json으로 상태 관리 |
| 매번 설명 반복 | CLAUDE.md 자동 로딩 |

---

## 참고: Anthropic 블로그 원문

이 하네스 시스템은 Anthropic 엔지니어링 블로그의 
"Effective harnesses for long-running agents" 글을 기반으로 합니다.

핵심 인사이트:
> "The agent's fundamental challenge: context window limitations mean 
> each session starts without memory of previous work."
> 
> 해결책: 외부 파일 시스템을 "기억 장치"로 활용
