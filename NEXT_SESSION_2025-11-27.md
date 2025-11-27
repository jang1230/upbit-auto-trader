# 다음 세션 가이드 (2025-11-27)

## 현재 브랜치
```
claude/duplicate-branch-with-history-01MTwqcDbvrJd9TS6QCofNoF
```

## 최신 코드 받기
```bash
git fetch origin claude/duplicate-branch-with-history-01MTwqcDbvrJd9TS6QCofNoF
git reset --hard origin/claude/duplicate-branch-with-history-01MTwqcDbvrJd9TS6QCofNoF
```

---

## 2025/11/26 ~ 2025/11/27 작업 요약

### 커밋 히스토리 (최신순)

| 커밋 | 내용 |
|------|------|
| `eb87b38` | **feat: 수동 매도 감지 기능 추가 (MyOrder WebSocket)** |
| `daff132` | docs: dca_count → dca_levels_executed 문서 업데이트 |
| `0ec500e` | **refactor: dca_count 변수 제거 - dca_levels_executed 배열로 통합** |
| `8d5d476` | fix: DCA 레벨 리셋 시 dca_count도 함께 초기화 |
| `5189429` | fix: DCA 완료 후 GUI 새로고침 안 되는 문제 수정 (스레드 안전성) |
| `3beab95` | fix: GroupUnifiedSettingsDialog에 레벨 리셋 기능 추가 |
| `703ee64` | fix: DCA state='done' 처리 시 GUI 업데이트 안 되는 버그 수정 |
| `ef00259` | fix: sync_from_myasset에서 total_amount None 처리 추가 |
| `d4b076a` | feat: DCA/익절/손절 설정 변경 시 레벨 실행 기록 리셋 기능 추가 |
| `f2ec8de` | fix: 포지션 저장 시 dictionary iteration 에러 수정 |
| `d49149a` | feat: DCA 불타기(양수) 지원 추가 |
| `8159a2e` | feat: DCA 수량 비율 범위 1~1000%로 확장 |
| `ec6b25e` | fix: DCA/익절 레벨 순서 검증 제거 - 사용자 자유 설정 허용 |
| `a7af6b6` | fix: 익절/손절 후 포지션 에러 및 DCA 최소금액 체크 추가 |
| `273c021` | fix: GUI 포지션 테이블 동기화 문제 수정 |

---

## 주요 변경사항 상세

### 1. dca_count 변수 완전 제거 (`0ec500e`)

**변경 전**: DCA 추적에 두 개의 변수 사용
- `dca_count`: 실행 횟수 카운터
- `dca_levels_executed`: 실행된 레벨 인덱스 배열

**변경 후**: 단일 변수로 통합
- `dca_levels_executed` 배열만 사용
- `len(dca_levels_executed)`로 카운트 계산

**수정 파일**:
- `core/position_manager.py` (3곳)
- `core/v4_trading_engine.py` (4곳)
- `gui/level_settings_dialog.py` (리셋 로직)
- `gui/group_unified_settings_dialog.py` (리셋 로직)

**이점**:
- 동기화 버그 원천 차단
- 익절/손절과 동일한 구조로 일관성 향상

---

### 2. 수동 매도 감지 기능 추가 (`eb87b38`)

**문제점**: Upbit 앱에서 수동으로 매도해도 GUI/로그에 반영 안 됨

**원인**:
- `_on_order_completed` 함수가 `ask_bid == 'BID'`(매수)만 처리
- `ask_bid == 'ASK'`(매도)는 무시됨

**해결**:
`core/v4_trading_engine.py`의 `_on_order_completed` 함수에 수동 매도 처리 로직 추가 (line 2058~2145)

```python
# 수동 매도 처리 (state='done' or 'cancel' and side='ask')
if state in ['done', 'cancel'] and ask_bid == 'ASK':
    # 봇 주문 확인 (processed_bot_order_uuids, pending_order)
    # 부분 매도: update_position()
    # 전체 매도: close_position()
    # _mark_processed_by_myorder() → MyAsset 중복 방지
    # GUI 새로고침 콜백
```

**로그 형식**:
```
[수동매도] 전체: KRW-XXX | 금액 | 수량 | 수익률 | 그룹
[수동매도] 부분: KRW-XXX | 금액 | 수량 | 잔여 수량 | 수익률 | 그룹
```

---

### 3. 레벨 설정 변경 시 리셋 기능 (`d4b076a`, `3beab95`)

DCA/익절/손절 설정 변경 시 해당 레벨 실행 기록 초기화:
- `dca_levels_executed = []`
- `profit_levels_executed = []`
- `loss_levels_executed = []`

**적용 위치**:
- `gui/level_settings_dialog.py`
- `gui/group_unified_settings_dialog.py`

---

### 4. DCA 불타기/물타기 통합 (`d49149a`)

- **물타기** (기존): 가격 하락 시 추가 매수 (음수 price_ratio: -3%, -6%)
- **불타기** (신규): 가격 상승 시 추가 매수 (양수 price_ratio: +3%, +5%)

---

## 테스트 필요 항목

### 1. 수동 매도 감지 테스트 (최우선)

**테스트 방법**:
1. 프로그램 실행 (V4 Trading Engine 시작)
2. Upbit 앱/웹에서 포지션 중 하나를 수동 매도
3. 확인 사항:
   - CLI 로그에 `[수동매도]` 출력 여부
   - GUI 활성 포지션에서 제거/업데이트 여부
   - `📊 수량 변동` 로그 대신 `[수동매도]` 로그 출력 여부

**예상 로그**:
```
[11:05:16] 🔔 [KRW-TRUST] 수동 매도 감지! (실시간) (order_id=abc123...)
[11:05:16] [수동매도] 전체: KRW-TRUST | 5,612원 | 46.33개 | -2.69% | 4번 그룹
```

**실패 시 확인**:
- MyOrder WebSocket이 연결되어 있는지
- `ask_bid == 'ASK'` 조건이 제대로 동작하는지

### 2. DCA 리셋 테스트

**테스트 방법**:
1. DCA가 이미 실행된 포지션 확인
2. 그룹 설정 → DCA 설정 변경 → 저장
3. 확인 사항:
   - 확인 다이얼로그 표시 여부
   - `dca_levels_executed` 배열이 `[]`로 초기화되는지
   - 변경된 조건에서 DCA가 다시 트리거되는지

### 3. 익절/손절 리셋 테스트

DCA와 동일한 방식으로 테스트

---

## 알려진 이슈

### 1. 문서 업데이트 미완료

`dca_count` 관련 히스토리/설계 문서는 의도적으로 수정하지 않음 (당시 기록 보존)

**수정된 활성 문서**:
- README.md
- TROUBLESHOOTING.md
- NEXT_SESSION_GUIDE.md
- docs/LIVE_TRADING_CHECKLIST.md
- docs/TEST_SCENARIOS.md

**수정 안 한 문서** (히스토리):
- WORK_SUMMARY_*.md
- docs/work_sessions/*.md
- docs/design/*.md
- docs/archive/*.md

---

## 코드 구조 참고

### 주문 처리 흐름

| 시나리오 | 함수 | pending_order | 콜백 등록 |
|----------|------|---------------|----------|
| 자동매수 | `_execute_buy()` | pending_buy | ✅ |
| 수동매수 | - | ❌ | ❌ |
| DCA | `_execute_dca()` | type='dca' | ✅ |
| 익절 | `_execute_sell(reason='profit')` | type='profit' | ✅ |
| 손절 | `_execute_sell(reason='loss')` | type='loss' | ✅ |
| 수동매도 | - | ❌ | ❌ |
| 즉시매도 | `_execute_immediate_sell()` | ❌ (동기처리) | ❌ |

### 핵심 파일

- `core/v4_trading_engine.py`: 메인 트레이딩 로직, `_on_order_completed`
- `core/position_manager.py`: 포지션 CRUD
- `gui/main_window.py`: GUI, 즉시매도
- `gui/level_settings_dialog.py`: 레벨 설정 다이얼로그
- `gui/group_unified_settings_dialog.py`: 그룹 통합 설정 다이얼로그

---

## 다음 작업 제안

1. **수동 매도 테스트** - 가장 중요, 새로 추가된 기능
2. **DCA 리셋 테스트** - 설정 변경 시 제대로 리셋되는지
3. **전체 시나리오 테스트** - 7가지 시나리오 모두 정상 동작 확인
4. **안정화 후 main 브랜치 병합**
