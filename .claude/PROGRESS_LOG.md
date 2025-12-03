# 진행 로그

> 499개 커밋 분석 기반 세션별 작업 기록
> 새 세션 시작 시 가장 최근 항목을 먼저 확인하세요.

---

## 2025-12-03 세션 (최신)

### 작업 내용
1. **V4 포지션 로드 실패 버그 수정** (`aced284`)
   - 문제: `pos.get("profit_pct", 0)`가 None 반환 시 포맷팅 에러
   - 해결: `.get() or 0` 패턴으로 None 값 방어 처리
   - 파일: `gui/main_window.py`

2. **position_manager.py 읽기 호환성 확보** (`d509444`)
   - `.get("key", 0)` → `.get("key") or 0` 패턴으로 변경
   - None 값과 키 누락 모두 처리
   - 파일: `core/position_manager.py`, `gui/main_window.py`

3. **불필요한 필드 저장 중단** (`eeb25fd`)
   - 저장 제외 필드: `current_price`, `current_value_krw`, `profit_krw`, `profit_pct`, `group_name`
   - 이유: Upbit API에서 조회 가능하거나 계산값
   - `update_price()` 메모리만 업데이트 (파일 저장 안 함)
   - 파일: `core/position_manager.py`

4. **원자적 쓰기 구현** (`d7dfa1b`, `92d72da`)
   - 임시 파일(.tmp) → `os.replace()` 원자적 교체
   - 비정상 종료 시 파일 손상 방지
   - 파일: `core/position_manager.py`, `core/config_manager.py`

5. **리팩토링 테스트 스크립트 추가** (`74ae68a`)
   - 5개 테스트: None 처리, 필드 제외, 원자적 쓰기, update_price()
   - 실행: `python tests/test_refactoring_changes.py`
   - 파일: `tests/test_refactoring_changes.py` (신규)

6. **CLAUDE.md 업데이트** (`8ca9151`)
   - 디버깅 시 .gitignore 파일 요청 가이드라인 추가
   - 파일: `CLAUDE.md`

### 변경된 파일
- `core/position_manager.py` (읽기/쓰기 리팩토링)
- `core/config_manager.py` (원자적 쓰기)
- `gui/main_window.py` (None 값 방어)
- `tests/test_refactoring_changes.py` (신규)
- `CLAUDE.md`

### 기술적 개선 사항
- **데이터 일관성**: Upbit API가 source of truth, 로컬 파일은 관리 데이터만 저장
- **안정성**: 원자적 쓰기로 비정상 종료 시 파일 손상 방지
- **I/O 최적화**: 가격 업데이트마다 저장하지 않음 (이벤트 기반 저장)

### 다음 세션 권장 작업
1. 실제 환경에서 리팩토링 변경사항 테스트
2. WebSocket 통합 구조 구현 (docs/WEBSOCKET_UNIFIED_PROPOSAL.md 참고)
3. Dry-run 테스트 계속

---

## 2025-12-02 세션 3

### 작업 내용
1. **그룹 관리 코인 목록 정렬 기능** (`6fe0fe0`)
   - 선택된 코인 → 다른 그룹 할당 코인 → 미할당 코인 순서로 정렬
   - `_sort_coin_checkboxes()` 메서드 추가
   - 파일: `gui/group_management_dialog.py`

2. **DCA 레벨 기록 버그 수정** (`70a58bb`)
   - 문제: `add_dca()`에서 `dca_levels_executed` 업데이트 누락
   - 해결: DCA 실행 시 레벨 번호를 리스트에 추가
   - 파일: `core/position_manager.py`

3. **포지션 손실 한도 버그 수정 및 기능 확장** (`08f19be`)
   - 필드명 버그 수정: `avg_price` → `avg_buy_price`, `amount` → `total_amount`
   - 옵션 2개 → 3개로 확장:
     - `alert`: 알림만 (매수 계속)
     - `alert_stop`: 알림 + 매수 중단
     - `liquidate`: 전체 청산
   - 파일: `core/v4_trading_engine.py`, `gui/global_settings_dialog.py`

4. **전체 청산 Rate Limit 준수** (`e448844`)
   - 청산 시 매도 주문 간 0.15초 딜레이 추가
   - Upbit 주문 API Rate Limit (8 req/sec) 준수
   - 파일: `core/v4_trading_engine.py`

5. **WebSocket 통합 구조 제안서 작성** (`e448f75`)
   - 현재 구조 (코인별 개별 WebSocket) vs 개선 구조 (통합 WebSocket) 비교
   - 시작 시간: 13개 코인 기준 16초 → 1-2초 예상
   - 파일: `docs/WEBSOCKET_UNIFIED_PROPOSAL.md`

### 변경된 파일
- `gui/group_management_dialog.py`
- `core/position_manager.py`
- `core/v4_trading_engine.py`
- `gui/global_settings_dialog.py`
- `docs/WEBSOCKET_UNIFIED_PROPOSAL.md` (신규)

### 분석/학습 내용
- WebSocket 시작 시간 병목 원인 분석 (로그 기반)
- Upbit 공식 문서 확인: 하나의 WebSocket에 여러 코인 구독 가능
- GUI WebSocket (`price_websocket_worker.py`)은 이미 통합 방식 사용 중

### 다음 세션 권장 작업
1. **WebSocket 통합 구조 구현** (새 브랜치에서)
   - 참고: `docs/WEBSOCKET_UNIFIED_PROPOSAL.md`
2. Dry-run 테스트 계속
3. 포지션 손실 한도 3가지 옵션 실제 테스트

---

## 2025-12-02 세션 2

### 작업 내용
1. **DailyLossTracker 완전 제거** (`f258baa`)
   - 일일 손실 한도 → 포지션 손실 한도로 변경
   - 24시간 암호화폐 시장에 적합한 실시간 모니터링 방식
   - 파일: core/daily_loss_tracker.py 삭제 (329줄)

2. **문서 업데이트** (`f258baa`)
   - CLAUDE.md, README.md, PROJECT_CONTEXT.md
   - FAQ.md, TROUBLESHOOTING.md, ENVIRONMENT_SETUP.md
   - .claude/FEATURE_LIST.json

3. **CLAUDE.md 최적화**
   - 946줄 → 143줄로 축소 (85% 감소)
   - 중복 내용 제거 (PROJECT_CONTEXT.md와 중복)
   - 2025/12/02 추가 내용 유지 (Upbit 문서 참조, 하네스 시스템)

### 변경된 파일
- `CLAUDE.md` (축소)
- `core/telegram_bot.py`
- `gui/main_window.py`
- `.claude/PROJECT_CONTEXT.md`
- `.claude/FEATURE_LIST.json`

### 다음 세션 권장 작업
1. 통합 테스트 시나리오 작성
2. Dry-run 1주일 테스트 시작

---

## 2025-12-02 (최신)

### 작업 내용
1. **WebSocket 중복 메시지 원인 분석 완료**
   - Upbit 서버에서 동일 메시지 2회 전송 확인 (JSON_LIST 디버그 로그로 증명)
   - `threading.Lock` 으로 Race Condition 해결됨 확인
   - 신규 매수 테스트: 중복 없이 정상 작동 확인

2. **그룹 삭제/코인 제거 시 포지션 관리 버그 수정** (`b85fba1`)
   - 문제: `group_id=None` 설정 시 `sync_with_upbit()`에서 포지션 삭제됨
   - 해결: `group_id="group_null"` 로 변경하여 미할당 포지션 유지
   - 파일: `core/group_manager.py`

3. **설정 로드 메시지 반복 원인 파악**
   - `load_config()` 호출 시마다 `print()` 출력
   - GUI 콜백에서 매번 config 로드 → 한 거래에 8회 이상 출력
   - 해결 필요: `print` → `logger.debug` 변경 권장

### 변경된 파일
- `core/group_manager.py` (group_id: None → "group_null")

### 확인된 정상 동작
- ✅ 신규 매수 WebSocket 메시지 중복 없음
- ✅ wait → trade → cancel 각 1회씩 정상 처리

### 남은 이슈
- ⚠️ `load_config()` print 메시지 반복 (기능 이상 없음, 로그만 지저분)
- ⚠️ 디버그 로그 정리 필요 (JSON_LIST 로그)

### 다음 세션 권장 작업
1. `config_manager.py`: `print` → `logger.debug` 변경
2. `upbit_websocket.py`: JSON_LIST 디버그 로그 제거 또는 `logger.debug`로 변경
3. 그룹 삭제/코인 이동 실제 테스트

---

## 2025-12-01

### 작업 내용
1. **그룹 삭제/코인 제거 시 포지션 처리 수정** (`b85fba1`)
   - `group_id = None` → `"group_null"` 변경
   - 이유: `sync_with_upbit()`에서 `None`인 포지션이 삭제되는 문제
   - 파일: `core/group_manager.py`

2. **Race Condition 방지** (`2f8a120`)
   - `threading.Lock` 추가 (`_dedup_lock`)
   - Upbit WebSocket이 같은 메시지 2회 전송하는 것 확인됨
   - 파일: `core/upbit_websocket.py`

3. **WebSocket 메시지 중복 제거 개선** (`5a93f34`)
   - TTL 기반 중복 체크 (5초)
   - `(uuid, state, timestamp)` 키 조합
   - 시장가 주문 체결 완료 판단 개선 (`remaining_fee` 추가 체크)
   - 파일: `core/upbit_websocket.py`, `core/v4_trading_engine.py`

4. **거래내역 GUI 중복 제거** (`bccba22`)
5. **close_position KeyError 방지** (`2616323`)
6. **remaining_volume None 값 처리** (`4298c15`)

### 변경된 파일
- `core/group_manager.py`
- `core/upbit_websocket.py`
- `core/v4_trading_engine.py`

### 상태
✅ 안정화 완료 - Live 배포 준비 완료

---

## 2025-11-28

### 작업 내용 (23개 커밋)

#### GUI 사이드바 개선 (6단계)
1. **UI 구조 변경** (`f65ba66`)
2. **업데이트 함수 구현** (`06e4c83`)
3. **실시간 연결** (`96faf20`)
4. **레이아웃 잘림 문제 해결** (`f2fc0ab`)
5. **너비 조정** (220-240px)
6. **'오늘의 거래' 섹션 삭제** (`1c29c7a`)

#### 거래 내역 기능 (4단계)
1. **세션 거래 내역 데이터 구조** (`a47710c`) - `gui/trade_data.py` 신규
2. **GUI 9개 컬럼** (`48f534e`)
3. **V4TradingEngine 콜백 연결** (`f146073`)
4. **CSV 내보내기** (`54559d9`)

#### 기타
- **총평가손익/수익률 실시간 표시** (`2dff0ca`)
- **거래내역 Race Condition 해결** (`454b615`)
- **거래내역 GUI 업데이트 Signal 패턴** (`d3c3aec`)

### 변경된 파일
- `gui/main_window.py` (다수)
- `core/v4_trading_engine.py`
- `gui/trade_data.py` (신규)
- `core/pending_order_manager.py`

---

## 2025-11-27

### 작업 내용 (20개 커밋)

#### 수동 매도 감지
- **수동 매도 감지 기능 추가** (`eb87b38`) - MyOrder WebSocket
- **identifier 기반 봇/수동 주문 구분** (`9b4a7be`)
- **수동 매도 부분/전체 판단 오류 수정** (`40b5d99`)

#### DCA 버그 수정
- **Phase B 조기 return 수정** (`5e62981`)
- **Phase C 도달 버그 수정** (`264277f`)
- **dca_count → dca_levels_executed 리팩토링** (`0ec500e`)
- **DCA 레벨 리셋 시 dca_count 초기화** (`8d5d476`)
- **DCA state='done' 처리 시 GUI 업데이트** (`703ee64`)

#### 텔레그램 중복 알림 수정
- **자동 매수** (`948d303`)
- **DCA** (`7451eaa`)
- **수동 매수/매도 알림 추가** (`4fdeabf`)

### 변경된 파일
- `core/v4_trading_engine.py` (다수)
- `core/upbit_api.py`
- `core/position_manager.py`
- `gui/main_window.py`
- `gui/group_unified_settings_dialog.py`
- `gui/level_settings_dialog.py`

---

## 2025-11-26

### 작업 내용 (10개 커밋)

- **DCA 불타기(양수) 지원** (`d49149a`)
- **DCA 수량 비율 1~1000% 확장** (`8159a2e`)
- **DCA/익절 레벨 순서 검증 제거** (`ec6b25e`) - 사용자 자유 설정
- **Race Condition 수정** (`64eadb5`, `7ad9503`)
- **텔레그램 중복 메시지 수정** (`772f4a5`)
- **GUI 포지션 테이블 동기화** (`273c021`)
- **익절/손절 후 포지션 에러 수정** (`a7af6b6`)
- **포지션 저장 시 dictionary iteration 에러** (`f2ec8de`)

### 변경된 파일
- `core/v4_trading_engine.py`
- `core/position_manager.py`
- `gui/main_window.py`
- `gui/level_settings_dialog.py`

---

## 2025-11-25

### 작업 내용 (35개 커밋)

#### 핵심 수정
- **GUI-Engine PositionManager 인스턴스 공유** (`b3de9b4`)
- **DCA/익절/손절 처리 시작 시 UUID 즉시 등록** (`f053d7f`)
- **봇 매도 후 수동매도 중복 알림 방지** (`b6890a7`) - `recent_bot_sells`

#### GUI 로그 개선
- **로그 필터링 강화** (`876f817`)
- **이모지 정리** (`fb3664a`) - INFO는 제거, WARNING/ERROR 유지
- **'포지션 관리 시작' 반복 로그 제외** (`bd27a64`)

#### 기타
- **DCA 완료 후 REST API 조회 전 1.5초 대기** (`c3f23d5`)
- **종료된 포지션이 신규 매수 차단 버그** (`d29b7dd`)
- **수동매도 감지 기능 구현** (GUI 연동)

### 변경된 파일
- `core/v4_trading_engine.py`
- `core/position_manager.py`
- `gui/main_window.py`
- `gui/logging_handler.py`

---

## 2025-11-24

### 작업 내용 (26개 커밋)

- **pending_order 복구 + Private WebSocket 통합** - Phase 3 완료
- **MyOrder/MyAsset 역할 구분** (Phase 1-2-3)
- **Adaptive Polling 시스템 통합** (Phase 4)
- **REST API 호출 최소화** (Rate Limit 해결)
- **실시간 캔들 집계 시스템**

### 주요 Phase 작업
```
Phase 1: BalancePollingManager 추가
Phase 2: MyAssetWebSocketWorker 상태 관리
Phase 3: PositionManager에 force_create_for_sync 추가
Phase 4: V4TradingEngine에 Adaptive Polling 통합
```

---

## 2025-11-17 ~ 2025-11-21

### V4 Phase 3 작업

- **WebSocket 개선**
  - 실시간 캔들 집계
  - 메인 루프 60초 → 1초 실시간 체크
  - WebSocketManager 초기화

- **Rate Limit 해결**
  - Phase 3-1 ~ 3-4 완료
  - WebSocket 캔들 사용 (REST 대체)

---

## 2025-11-10 ~ 2025-11-14

### V4 Phase 1-2 작업 (~80개 커밋)

#### Phase 1: 데이터 구조
- ConfigManager
- PositionManager  
- TradeHistoryManager

#### Phase 2: 백엔드 핵심
- GroupManager
- V4AutoBuyStrategy (DailyLossTracker는 제거됨)
- V4TradingEngine

---

## 2025-11-03 ~ 2025-11-07

### V4 설계 문서 작성 (~40개 커밋)

- **DESIGN_V4_COMPLETE.md** (172KB, 18개 섹션)
- Topic 1-9 완료
- JSON Schema 정의
- V4 Implementation Plan (5 Phases, 32-42h)

---

## 2025-10-27 ~ 2025-10-31

### V3 개선 및 Live 배포 (~50개 커밋)

- **Live 트레이딩 모드 활성화** (`3e70453`)
- **multi-level take-profit/stop-loss** (`2d2b8fe`)
- **GUI freeze 해결** (batch updates)
- **WebSocket 개선** (MyAsset 실시간 감지)
- **DCA config 실시간 업데이트**

---

## 2025-10-24

### Initial Commit

- Upbit DCA Trading Bot with Phase 4 features
- 기존 V3 코드 기반

---

## 세션 기록 템플릿

```markdown
## YYYY-MM-DD 세션

### 작업 내용
1. **작업 제목** (`커밋해시`)
   - 상세 내용
   - 파일: `path/to/file.py`

### 변경된 파일
- `path/to/file.py`

### 남은 이슈
- 이슈 설명

### 다음 세션 권장 작업
1. 작업 1
2. 작업 2
```
