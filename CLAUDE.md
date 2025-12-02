# CLAUDE.md

> Upbit DCA Trader V4 - 업비트 암호화폐 자동 트레이딩 봇 (Python 3.8+ / PySide6 GUI)

## 필수 규칙 ⚠️

### 코드 규칙
- `group_id`는 `None` 대신 `"group_null"` 문자열 사용
- WebSocket 메시지 처리 시 `threading.Lock` 필수
- 중복 방지: TTL 5초 기반 dedup 패턴 사용

### 커밋 메시지
```
fix:      버그 수정
feat:     새 기능
refactor: 리팩토링
docs:     문서
```

### 로그 이모지
```
✅ 성공 | 🎯 이벤트 | 📊 상태 | ⚠️ 경고 | ❌ 에러
```

---

## 핵심 명령어

```bash
# 실행
python main.py

# 테스트
python -m pytest tests/

# 설정/포지션 확인
cat config/trading_config.json
cat data/positions_live.json      # Live
cat data/positions_dryrun.json    # Dry-run
```

---

## Upbit 공식 문서 참조

Upbit API 관련 질문 시 **웹사이트를 fetch하지 말고** 로컬 `upbit_docs/` 폴더의 문서를 참조하세요:

| 폴더 | 내용 |
|------|------|
| `upbit_docs/reference/` | API 레퍼런스 (주문, 잔고, 캔들, WebSocket 등) |
| `upbit_docs/docs/` | 가이드 문서 (개발환경, FAQ, 튜토리얼 등) |
| `upbit_docs/changelog/` | API 변경 이력 |

예시:
- 주문 API → `upbit_docs/reference/new-order.md`
- WebSocket 가이드 → `upbit_docs/reference/websocket-guide.md`
- Rate Limit → `upbit_docs/reference/rate-limits.md`

---

## 하네스 시스템 (세션별 진행 관리)

프로젝트 컨텍스트와 작업 기록은 `.claude/` 폴더에서 관리됩니다:

| 파일 | 용도 | 참조 시점 |
|------|------|----------|
| `.claude/PROJECT_CONTEXT.md` | **아키텍처, GUI 관계도, 설정 파일 구분** | 🔴 코드 분석/수정 전 필수 |
| `.claude/PROGRESS_LOG.md` | 세션별 작업 기록, 최근 커밋 | 이어서 작업 시 |
| `.claude/FEATURE_LIST.json` | 기능 상태 (done/planned), 해결된 이슈 | 기능 추가/버그 수정 시 |
| `.claude/SESSION_START.md` | 세션 시작 템플릿 | 새 세션 시작 시 |
| `.claude/HOW_IT_WORKS.md` | 하네스 시스템 사용 가이드 | 시스템 이해 필요 시 |

### PROJECT_CONTEXT.md 주요 내용
- **아키텍처 다이어그램**: V4TradingEngine 중심 구조
- **GUI 컴포넌트 관계도**: MainWindow → Dialog → Worker 관계
- **설정 파일 구분**: `.env` vs `config.json` 역할 분리
- **핵심 모듈 목록**: 파일별 역할 및 수정 횟수
- **알려진 이슈 패턴**: 해결된 버그와 해결책

---

## 세션 종료 규칙

사용자가 "작업 마무리", "세션 끝", "커밋해줘" 등을 말하면:

1. `.claude/PROGRESS_LOG.md` 맨 위에 아래 양식으로 기록 추가:

```markdown
## YYYY-MM-DD 세션

### 작업 내용
1. **작업 제목** (`커밋해시`)
   - 상세 내용
   - 파일: 변경된 파일 경로

### 변경된 파일
- 파일 목록

### 다음 세션 권장 작업
1. 다음에 할 일
```

2. 커밋 메시지 형식: `fix:`, `feat:`, `refactor:`, `docs:`

---

## 현재 상태 (2025-12 기준)

**Phase**: V4 Phase 4 (통합 테스트 + 안정화)
**다음**: Dry-run 1주일 → Live 소액 배포

### V4 핵심 기능
- **무제한 그룹**: 독립적인 트레이딩 그룹 생성
- **Live/Dry-run 분리**: 포지션 파일 분리
- **프리셋 자동매수**: Conservative/Balanced/Aggressive
- **포지션 손실 한도**: 실시간 모니터링 (24시간 암호화폐 시장에 적합)
- **다단계 DCA/익절/손절**: 그룹별 독립 설정

---

## 핫스팟 파일 🔥

수정 시 주의 필요:

| 파일 | 역할 | 주의사항 |
|------|------|----------|
| `core/v4_trading_engine.py` | 메인 오케스트레이터 | 주문 처리 Phase A-B-C-D |
| `core/upbit_websocket.py` | WebSocket 연결 | Lock, 중복 방지 |
| `core/position_manager.py` | 포지션 관리 | group_null 처리 |
| `gui/main_window.py` | GUI 메인 | Signal 패턴 |

---

## 상세 문서

| 문서 | 내용 |
|------|------|
| `docs/DESIGN_V4_COMPLETE.md` | V4 상세 설계 (172KB, 18개 섹션) |
| `docs/TROUBLESHOOTING.md` | 문제 해결 가이드 |
| `ENVIRONMENT_SETUP.md` | 환경 설정 가이드 |
| `FAQ.md` | 자주 묻는 질문 |
| `README.md` | 전체 프로젝트 문서 |
