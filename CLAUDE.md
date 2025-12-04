# Upbit DCA Trader V4
업비트 암호화폐 자동 트레이딩 봇 (Python 3.8+ / PySide6 GUI)

## 필수 규칙 ⚠️
- `group_id`는 `None` 대신 `"group_null"` 문자열 사용
- WebSocket 메시지 처리 시 `threading.Lock` 필수
- 중복 방지: TTL 5초 기반 dedup 패턴 사용

## 작업 흐름
1. **분석**: 질문/문제 분석 → 원인 설명 → 해결 방안 제시
2. **확인**: "이렇게 수정할까요?" 물어보기
3. **실행**: 사용자 승인 후 코드 수정

❌ 분석 없이 바로 코드 수정 금지

## 정확성 규칙
- 불확실하면 "확실하지 않습니다" 또는 "정보가 부족합니다"라고 말하기
- 제공된 문서/코드 기반으로만 답변, 추측 금지
- 긴 문서 분석 시 원문 인용 후 분석
- 주장에는 근거(파일 경로, 코드 라인) 명시

## 파일 헤더 규칙
`core/`, `gui/`, `utils/` 파일 생성/수정 시 → `.claude/CODING_CONVENTIONS.md` 참조

## 커밋 & 로그
| 커밋 | 용도 | 로그 이모지 |
|------|------|-------------|
| `fix:` | 버그 수정 | ✅ 성공 |
| `feat:` | 새 기능 | 🎯 이벤트 |
| `refactor:` | 리팩토링 | 📊 상태 |
| `docs:` | 문서 | ⚠️ 경고 / ❌ 에러 |

## 핵심 명령어
```bash
python main.py              # 실행
python -m pytest tests/     # 테스트
cat config/trading_config.json
cat data/positions_live.json      # Live
cat data/positions_dryrun.json    # Dry-run
```

## Upbit API 참조
❌ 웹 fetch 금지 → ✅ `upbit_docs/` 폴더 참조

| 내용 | 경로 |
|------|------|
| 주문 API | `upbit_docs/reference/new-order.md` |
| WebSocket | `upbit_docs/reference/websocket-guide.md` |
| Rate Limit | `upbit_docs/reference/rate-limits.md` |

## 세션 관리

### 시작 시
`.claude/PROGRESS_LOG.md` 읽고 최근 작업 및 "다음 세션 권장 작업" 확인

### 종료 시 ("작업 마무리", "오늘 끝" 등)

**1단계: 정보 수집**
- `git log --oneline --since="오늘"` 로 커밋 확인

**2단계: 업데이트 내용 제안** (실행 전 보여주기만)
| 파일 | 업데이트 내용 |
|------|--------------|
| `.claude/PROGRESS_LOG.md` | 오늘 작업, 변경 파일, 다음 권장 작업 |
| `.claude/FEATURE_LIST.json` | feat: → features, fix: → resolved_issues |
| `.claude/PROJECT_CONTEXT.md` | 아키텍처 변경 시만 |

**3단계: 추가 제안**
- 커밋 메시지 제안
- 다음 세션 권장 작업 정리

**4단계: 승인 대기**
❌ 바로 실행 금지 → ✅ 사용자 승인 후 실행

상세 규칙 → `.claude/HOW_IT_WORKS.md` 참조

## 핫스팟 파일 🔥
| 파일 | 주의사항 |
|------|----------|
| `core/v4_trading_engine.py` | 주문 처리 Phase A-B-C-D |
| `core/upbit_websocket.py` | Lock, 중복 방지 |
| `core/position_manager.py` | group_null 처리 |
| `gui/main_window.py` | Signal 패턴 |

## 문제 분석 시 데이터 요청
✅ 요청 가능: `positions_live.json`, `trading_config.json`, 로그
❌ 요청 금지: `.env`, API 키, 비밀번호

## 참조 문서
| 용도 | 경로 |
|------|------|
| 아키텍처, GUI 관계도 | `.claude/PROJECT_CONTEXT.md` 🔴 코드 수정 전 필수 |
| 세션별 작업 기록 | `.claude/PROGRESS_LOG.md` |
| 기능 상태, 해결된 이슈 | `.claude/FEATURE_LIST.json` |
| 하네스 시스템 가이드 | `.claude/HOW_IT_WORKS.md` |
| 코딩 컨벤션, 파일 헤더 | `.claude/CODING_CONVENTIONS.md` |
| V4 상세 설계 | `docs/DESIGN_V4_COMPLETE.md` |

## 현재 상태 (2025-12)
- **Phase**: V4 Phase 4 (통합 테스트 + 안정화)
- **다음**: Dry-run 1주일 → Live 소액 배포
