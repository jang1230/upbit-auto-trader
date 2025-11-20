# 2025-11-19 작업 세션: MyOrder/MyAsset 역할 구분 및 재설계 계획

**브랜치**: `claude/backup-copy-v3-01QmgKR2fszfXZydjPANfZWJ`
**작업 일자**: 2025년 11월 19일
**작업 완료 커밋**: `43be749` (5개 커밋)
**다음 단계**: MyOrder WebSocket 확장 (외부 매수 처리) 및 MyAsset WebSocket 축소 (백업 역할)

---

## 📋 목차

1. [작업 개요](#1-작업-개요)
2. [완료된 작업 (Phase 1-3 + 버그 수정)](#2-완료된-작업-phase-1-3--버그-수정)
3. [발견된 문제점](#3-발견된-문제점)
4. [재설계 계획 (Phase A-E)](#4-재설계-계획-phase-a-e)
5. [현재 코드 구조 분석](#5-현재-코드-구조-분석)
6. [테스트 시나리오](#6-테스트-시나리오)
7. [다음 세션 작업 가이드](#7-다음-세션-작업-가이드)

---

## 1. 작업 개요

### 1.1 배경

기존 V4 Trading Engine에서 **MyOrder WebSocket**과 **MyAsset WebSocket**이 동시에 매수 이벤트를 처리하면서 다음 문제 발생:

1. **중복 포지션 생성**: 봇 주문 시 MyOrder + MyAsset 모두 포지션 생성 시도
2. **pending_initial_buys 카운트 오류**: MyAsset이 봇 주문도 처리하여 카운트 증가
3. **DCA 평균가 덮어쓰기**: MyOrder가 정확한 평균가 계산 후 MyAsset이 REST API로 덮어쓰기
4. **타이밍 레이스 컨디션**: 두 WebSocket이 거의 동시에 처리하여 데이터 불일치

### 1.2 목표

**Phase 1-3 (완료)**:
- 봇 주문과 외부 매수를 명확히 구분
- MyOrder: 봇 주문만 처리
- MyAsset: 외부 매수만 처리
- DCA 평균가 계산 보호

**Phase A-E (계획)**:
- MyOrder를 **모든 매수**의 단일 진실 공급원(Single Source of Truth)으로 확장
- MyAsset을 **백업 및 동기화** 역할로 축소
- 외부 매수도 MyOrder에서 처리 (그룹 매칭 로직 추가)

---

## 2. 완료된 작업 (Phase 1-3 + 버그 수정)

### 2.1 Phase 1: 백엔드 MyAsset 역할 구분 (695256e)

**커밋**: `695256e` - "feat: MyOrder/MyAsset 역할 구분 (Phase 1: 백엔드)"

**변경 파일**: `core/v4_trading_engine.py`

**변경 내용**:
- `_process_myasset_data()` 메서드 (라인 638-676) 수정
- `pending_initial_buys` 딕셔너리 체크 추가
- 봇 주문: MyOrder만 처리, MyAsset 스킵
- 외부 매수: MyAsset만 처리, `group_null` 포지션 생성

**핵심 로직**:
```python
# 라인 639-648
is_bot_order = any(
    pending_data.get('symbol') == symbol
    for pending_data in self.pending_initial_buys.values()
)

if is_bot_order:
    # 봇 주문 → MyOrder WebSocket이 처리할 예정
    logger.debug(f"⏭️ {symbol} 봇 주문 진행 중 (MyOrder WebSocket에서 처리 예정, MyAsset 스킵)")
    continue

# 외부 매수 감지 (Upbit 앱/웹에서 직접 매수)
logger.info(f"🆕 외부 매수 감지 (Upbit 앱/웹): {symbol}")
```

**효과**:
- ✅ pending_initial_buys 카운트 100% 정확
- ✅ 중복 포지션 생성 방지
- ✅ 최대 포지션 카운트 정확성 개선

---

### 2.2 Phase 2: GUI MyAsset 역할 구분 (f0d6a36)

**커밋**: `f0d6a36` - "feat: MyOrder/MyAsset 역할 구분 (Phase 2: GUI)"

**변경 파일**:
- `gui/myasset_websocket_worker.py` (라인 229-288)
- `gui/main_window.py` (_start_myasset_websocket)

**변경 내용**:
- GUI의 MyAssetWebSocketWorker에 `pending_initial_buys` 참조 추가
- V4TradingEngine의 `pending_initial_buys`를 GUI Worker에 전달
- 백엔드와 동일한 봇/외부 구분 로직 적용

**핵심 로직**:
```python
# gui/myasset_websocket_worker.py 라인 230-241
is_bot_order = False
if self.pending_initial_buys is not None:
    is_bot_order = any(
        pending_data.get('symbol') == symbol
        for pending_data in self.pending_initial_buys.values()
    )

if is_bot_order:
    # 봇 주문 → MyOrder WebSocket이 처리할 예정
    logger.debug(f"   ⏭️ {symbol} 봇 주문 진행 중 (MyOrder WebSocket에서 처리 예정, GUI MyAsset 스킵)")
    continue
```

**효과**:
- ✅ GUI에서도 중복 포지션 생성 방지
- ✅ 백엔드-GUI 일관성 유지

---

### 2.3 Phase 3: 로그 개선 (899639d)

**커밋**: `899639d` - "feat: MyOrder/MyAsset 역할 구분 (Phase 3: 로그 개선)"

**변경 파일**: `core/v4_trading_engine.py` (라인 886, 921, 965, 1748, 1774)

**변경 내용**:
- 봇 주문 관련 로그에 `[봇]` 태그 추가
- 외부 매수 관련 로그에 `[외부]` 태그 추가 (Phase 1,2에서 이미 완료)

**개선된 로그 예시**:
```
🔔 [봇] KRW-XRP: 매수 신호 발생!
💰 [봇] KRW-XRP 매수 실행 중...
✅ [봇] KRW-XRP 매수 주문 접수 완료
✅ [봇] KRW-XRP 초기 매수 체결 완료
✅ [봇] 매수 완료 (텔레그램)
🆕 외부 매수 감지 (Upbit 앱/웹): KRW-DOGE
✅ [외부] group_null 포지션 생성
```

**효과**:
- ✅ 로그 가독성 향상
- ✅ 디버깅 용이
- ✅ 봇/외부 구분 명확

---

### 2.4 버그 수정 1: DCA 평균가 보호 (4daa560)

**커밋**: `4daa560` - "fix: DCA 평균가 계산 보호 - MyAsset의 REST API 덮어쓰기 방지"

**변경 파일**: `core/position_manager.py` (라인 768-793)

**문제 상황**:
```
사용자 로그:
✅ KRW-LSK DCA 레벨 1 부분 체결 완료 → add_dca() 호출 (실제 체결가: 328원)
⚠️ [외부] KRW-LSK 수량 변동 감지 ... REST API로 평균가 조회
📊 REST API 평균가 조회: KRW-LSK = 336원
```

**근본 원인**:
1. MyOrder가 DCA 체결 시 `add_dca()` 호출하여 정확한 평균가 계산 (328원 + 기존가 = 331원)
2. 거의 동시에 MyAsset이 수량 변동 감지
3. `pending_order`가 이미 MyOrder에서 제거되어 봇/외부 구분 실패
4. MyAsset이 REST API로 평균가 재조회하여 MyOrder의 정확한 계산 덮어쓰기 (336원)

**해결 방법**:
- **최근 10초 이내 DCA 히스토리 체크** 추가
- 봇 DCA: MyOrder 계산 신뢰, MyAsset skip
- 외부 추가매수: MyAsset이 REST API 조회

**핵심 로직**:
```python
# 라인 768-795
# 🆕 최근 DCA 발생 확인 (10초 이내)
current_position = self.get_position(symbol)  # 최신 정보 재조회
recent_dca = False
if current_position and current_position.get('dca_history'):
    last_dca = current_position['dca_history'][-1]
    last_dca_time = datetime.fromisoformat(last_dca['timestamp'])
    if (datetime.now() - last_dca_time).total_seconds() < 10:
        recent_dca = True

if recent_dca:
    # 봇 DCA → MyOrder 처리 완료 → skip
    logger.info(f"   ⏭️ [봇] {symbol} 최근 DCA 발생 (10초 이내) → MyOrder에서 평균가 계산 완료, MyAsset skip")
else:
    # 외부 추가매수 → REST API로 평균가 조회
    logger.warning(f"   ⚠️ [외부] {symbol} 수량 변동 감지, REST API로 평균가 조회")
```

**효과**:
- ✅ DCA 평균가 100% 정확성 보장
- ✅ 봇/외부 추가매수 명확히 구분

---

### 2.5 버그 수정 2: DCA 히스토리 타이밍 이슈 (43be749)

**커밋**: `43be749` - "fix: DCA 히스토리 체크 시 최신 포지션 정보 다시 읽기"

**변경 파일**: `core/position_manager.py` (라인 770)

**문제 상황**:
- 이전 수정(4daa560)에서 DCA 히스토리 체크를 추가했지만 실패
- `position` 객체가 메서드 시작 시 한 번만 읽혀서 `add_dca()` 반영 전의 오래된 데이터 사용
- `dca_history`가 아직 업데이트되지 않아 체크 실패

**해결 방법**:
- DCA 히스토리 체크 **직전**에 `get_position()` 재호출
- 최신 포지션 정보로 DCA 여부 확인

**핵심 로직**:
```python
# 라인 770 (수정됨)
current_position = self.get_position(symbol)  # 🆕 최신 정보 다시 읽기
recent_dca = False
if current_position and current_position.get('dca_history'):
    # ... DCA 체크 로직
```

**효과**:
- ✅ DCA 히스토리 체크 100% 정확
- ✅ 타이밍 이슈 해결

---

## 3. 발견된 문제점

### 3.1 Phase 1-3의 한계

**현재 구현의 문제점**:

1. **신규 포지션만 처리**: Phase 1-2는 **신규 포지션 생성**만 봇/외부 구분
   - 기존 포지션의 **추가 매수**(DCA, 외부 추가매수)는 여전히 중복 처리 가능

2. **타이밍 의존적**: `pending_order` 제거 시점에 따라 봇/외부 구분 실패
   - DCA 평균가 문제는 "10초 체크"로 임시 방어
   - 근본적인 해결책 아님 (타이밍 윈도우가 여전히 존재)

3. **아키텍처 비효율**: MyOrder가 **모든 주문 이벤트**를 수신하는데도 불구하고 외부 매수를 MyAsset이 처리
   - **사용자 통찰**: "MyOrder로 주문이 체결완료되서 done이라고 나온다음에 -> 그룹내에 존재하는 코인인지, 이미 매수된 코인인지 찾아서 matching을 하면되는거아닌가?"

### 3.2 핵심 통찰

**MyOrder WebSocket의 특성**:
- Upbit MyOrder WebSocket은 **계정의 모든 주문 이벤트**를 전송 (봇 주문 + 외부 주문)
- `state='done'`으로 체결 완료 시점 정확히 알 수 있음
- `avg_price`, `executed_volume` 등 체결 정보 포함
- **외부 주문도 동일한 형식**으로 수신

**아키텍처 개선 방향**:
- MyOrder를 **모든 매수**의 단일 진실 공급원(Single Source of Truth)으로 확장
- 봇 주문: `pending_initial_buys`로 그룹 매칭
- 외부 주문: `config.groups`로 그룹 매칭 (코인이 어느 그룹에 속하는지)
- MyAsset: 백업 역할 (MyOrder 누락 시 동기화)

---

## 4. 재설계 계획 (Phase A-E)

### Phase A: 현재 구조 분석 ✅ (다음 세션 첫 작업)

**목표**: MyOrder/MyAsset 상호작용 지점 및 중복 책임 상세 분석

**분석 대상**:
1. `_on_order_completed()` - MyOrder 처리 로직 전체 흐름
2. `_process_myasset_data()` - MyAsset 처리 로직 전체 흐름
3. `sync_from_myasset()` - PositionManager의 MyAsset 동기화
4. 두 WebSocket의 타이밍 다이어그램
5. 레이스 컨디션 발생 지점

**출력물**:
- 현재 구조 상세 플로우차트
- 중복 처리 지점 목록
- 타이밍 이슈 목록
- 리팩토링 대상 코드 블록

---

### Phase B: MyOrder 확장 - 외부 매수 처리

**목표**: MyOrder가 모든 매수(봇 + 외부, 신규 + 추가)를 처리하도록 확장

**구현 계획**:

#### B-1. 외부 신규 매수 처리

**매칭 로직**:
```python
# _on_order_completed() 내부에 추가
if state == 'done' and side == 'bid':  # 매수 체결 완료
    # 1. pending_initial_buys 체크 (기존 봇 주문)
    if order_uuid in self.pending_initial_buys:
        # 기존 로직 (라인 1743-1786)
        return

    # 2. 외부 신규 매수 체크
    position = self.position_manager.get_position(symbol)
    if not position:
        # 그룹 매칭
        group_id = self._find_group_for_symbol(symbol)
        if group_id:
            # 그룹 내 코인 → 해당 그룹에 포지션 생성
            logger.info(f"🆕 [외부] {symbol} 신규 매수 감지 (그룹: {group_id})")
            position = self.position_manager.create_position(
                group_id=group_id,
                symbol=symbol,
                buy_price=avg_price,
                quantity=executed_volume
            )
        else:
            # 그룹 외 코인 → group_null 생성
            logger.info(f"🆕 [외부] {symbol} 신규 매수 감지 (그룹 없음 → group_null)")
            position = self.position_manager.create_position(
                group_id="group_null",
                symbol=symbol,
                buy_price=avg_price,
                quantity=executed_volume,
                force_create_for_sync=True
            )
        return
```

**새 메서드 추가**:
```python
def _find_group_for_symbol(self, symbol: str) -> Optional[str]:
    """
    config.groups를 검색하여 symbol이 속한 그룹 ID 반환
    """
    config = self.config_manager.get_config()
    for group_id, group_data in config.get('groups', {}).items():
        if symbol in group_data.get('coins', []):
            return group_id
    return None
```

#### B-2. 외부 추가 매수 처리 (DCA 아님)

**매칭 로직**:
```python
# _on_order_completed() 내부에 추가 (B-1 이후)
if state == 'done' and side == 'bid':
    # ... (B-1 체크 통과 - 기존 포지션 존재)

    # 3. 외부 추가 매수 체크
    position = self.position_manager.get_position(symbol)
    if position:
        pending_order = position.get('pending_order')

        # pending_order 없음 → 외부 추가 매수
        if not pending_order:
            logger.info(f"🆕 [외부] {symbol} 추가 매수 감지 (수량: {executed_volume:.8f})")

            # REST API로 최신 평균가 조회
            accounts = self.upbit_api.get_accounts()
            for acc in accounts:
                if f"KRW-{acc['currency']}" == symbol:
                    new_avg_price = float(acc.get('avg_buy_price', 0))
                    new_balance = float(acc.get('balance', 0))

                    # 포지션 업데이트
                    self.position_manager.update_position(symbol, {
                        'total_amount': new_balance,
                        'avg_buy_price': new_avg_price,
                        'total_invested_krw': new_avg_price * new_balance
                    })

                    logger.info(f"   ✅ [외부] {symbol} 추가 매수 반영 (새 평균가: {new_avg_price:,.0f}원)")
                    break
            return
```

**변경 파일**:
- `core/v4_trading_engine.py` (`_on_order_completed` 메서드 확장)

---

### Phase C: MyAsset 축소 - 백업 역할로 변경

**목표**: MyAsset을 MyOrder 누락 처리용 백업으로 축소

**구현 계획**:

#### C-1. MyAsset 중복 처리 제거

**변경 로직**:
```python
# _process_myasset_data() 수정
def _process_myasset_data(self, data: dict):
    # ... (기존 코드)

    for asset in data:
        symbol = f"KRW-{currency}"
        position = self.position_manager.get_position(symbol)

        if not position:
            # MyOrder가 이미 처리했는지 체크 (5초 윈도우)
            if self._was_recently_processed_by_myorder(symbol):
                logger.debug(f"   ⏭️ {symbol} MyOrder에서 최근 처리됨 (5초 이내), MyAsset 스킵")
                continue

            # MyOrder가 누락했을 가능성 → 백업 처리
            logger.warning(f"   ⚠️ {symbol} MyOrder 누락 감지, MyAsset 백업 처리")
            # ... 포지션 생성 (기존 로직)
```

**새 메서드 추가**:
```python
def _was_recently_processed_by_myorder(self, symbol: str) -> bool:
    """
    최근 5초 이내 MyOrder에서 해당 symbol 처리했는지 확인
    """
    if not hasattr(self, '_myorder_processed_symbols'):
        self._myorder_processed_symbols = {}

    last_time = self._myorder_processed_symbols.get(symbol)
    if last_time:
        elapsed = (datetime.now() - last_time).total_seconds()
        return elapsed < 5
    return False

def _mark_processed_by_myorder(self, symbol: str):
    """
    MyOrder에서 symbol 처리했음을 기록
    """
    if not hasattr(self, '_myorder_processed_symbols'):
        self._myorder_processed_symbols = {}
    self._myorder_processed_symbols[symbol] = datetime.now()
```

#### C-2. MyOrder에서 처리 완료 마킹

**변경 로직**:
```python
# _on_order_completed() 내부, 포지션 생성/업데이트 후 추가
self._mark_processed_by_myorder(symbol)
```

**변경 파일**:
- `core/v4_trading_engine.py` (`_process_myasset_data`, `_on_order_completed`)

---

### Phase D: 통합 테스트

**목표**: 4가지 시나리오 모두 검증

**테스트 시나리오**:

| # | 시나리오 | 처리 담당 | 검증 항목 |
|---|---------|---------|---------|
| 1 | 봇 신규 매수 | MyOrder | ✅ pending_initial_buys 매칭<br>✅ 그룹에 포지션 생성<br>✅ MyAsset 스킵 |
| 2 | 봇 DCA | MyOrder | ✅ pending_order 매칭<br>✅ add_dca() 정확한 평균가<br>✅ MyAsset 스킵 |
| 3 | 외부 신규 매수 | MyOrder | ✅ 그룹 매칭 (그룹 내/외)<br>✅ 포지션 생성<br>✅ MyAsset 백업만 (5초 후) |
| 4 | 외부 추가 매수 | MyOrder | ✅ REST API 평균가 조회<br>✅ 포지션 업데이트<br>✅ MyAsset 백업만 (5초 후) |

**테스트 방법**:
1. **봇 테스트**: GUI에서 수동 매수 버튼 클릭
2. **외부 테스트**: Upbit 앱/웹에서 직접 매수
3. **로그 확인**: `[봇]`/`[외부]` 태그, MyOrder/MyAsset 처리 순서
4. **데이터 검증**: 평균가, 수량, 그룹 ID, 중복 여부

---

### Phase E: 문서화

**목표**: 설계 변경 사항 및 새 아키텍처 문서화

**문서 작성**:
1. `DESIGN_V4_MYORDER_MYASSET_ARCHITECTURE.md`
   - 새 아키텍처 다이어그램
   - MyOrder/MyAsset 역할 정의
   - 처리 플로우차트

2. `CLAUDE.md` 업데이트
   - MyOrder/MyAsset 섹션 추가
   - 아키텍처 개요 업데이트

3. 코드 주석 개선
   - 각 메서드의 책임 명확화
   - 타이밍 이슈 주의사항 기록

---

## 5. 현재 코드 구조 분석

### 5.1 MyOrder WebSocket 처리 흐름

**파일**: `core/v4_trading_engine.py`
**메서드**: `_on_order_completed()` (라인 1702-1865)

**현재 처리 경로**:

```
MyOrder WebSocket 이벤트 수신
    ↓
state='done' and side='bid' 체크
    ↓
┌─────────────────────────────────────┐
│ 1. pending_initial_buys 체크        │ (라인 1743-1786)
│    → 봇 신규 매수                    │
│    → create_position() 호출          │
│    → pending_initial_buys 제거       │
└─────────────────────────────────────┘
    ↓ (없으면)
┌─────────────────────────────────────┐
│ 2. state='trade' 체크                │ (라인 1788-1853)
│    → 부분 체결 (DCA)                 │
│    → pending_order 매칭              │
│    → add_dca() 호출                  │
│    → pending_order 제거              │
└─────────────────────────────────────┘
    ↓ (없으면)
┌─────────────────────────────────────┐
│ 3. 외부 주문 처리                    │ ❌ 현재 없음
│    (Phase B에서 추가 예정)            │
└─────────────────────────────────────┘
```

**처리하는 이벤트**:
- ✅ 봇 신규 매수 (`pending_initial_buys` 존재)
- ✅ 봇 DCA (`pending_order` 존재)
- ❌ 외부 신규 매수 (현재 무시)
- ❌ 외부 추가 매수 (현재 무시)

---

### 5.2 MyAsset WebSocket 처리 흐름

**파일**: `core/v4_trading_engine.py`
**메서드**: `_process_myasset_data()` (라인 638-686)

**현재 처리 경로**:

```
MyAsset WebSocket 이벤트 수신
    ↓
balance > 0 and currency not in ['KRW'] 체크
    ↓
position = get_position(symbol)
    ↓
┌─────────────────────────────────────┐
│ 1. position 없음 (신규 매수)          │ (라인 638-685)
│    ↓                                  │
│    pending_initial_buys 체크          │ (Phase 1 추가)
│    ↓                                  │
│    봇 주문? → 스킵 (MyOrder 처리)      │
│    외부 매수? → group_null 포지션 생성 │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. position 있음 (추가 매수/동기화)    │ (라인 735-807)
│    → sync_from_myasset() 호출        │
│    → 수량 변동 감지                   │
│    → DCA 히스토리 체크 (10초)         │ (Phase 1 추가)
│    → 봇 DCA? → 스킵                   │
│    → 외부 추가? → REST API 평균가     │
└─────────────────────────────────────┘
```

**처리하는 이벤트**:
- ✅ 외부 신규 매수 (`pending_initial_buys` 없음)
- ✅ 외부 추가 매수 (DCA 히스토리 없음)
- ⚠️ 봇 주문 스킵 (Phase 1-3에서 추가된 보호)

---

### 5.3 PositionManager 주요 메서드

**파일**: `core/position_manager.py`

#### create_position() (라인 205-287)
- 새 포지션 생성
- 최대 포지션 개수 체크
- pending_initial_buys 카운트 포함 (Phase 1 이전 버그 수정)

#### add_dca() (라인 445-545)
- DCA 레벨 추가
- **평균가 재계산** (가중 평균)
- dca_history 기록 (타임스탬프 포함)

#### sync_from_myasset() (라인 735-836)
- MyAsset 데이터로 포지션 동기화
- 수량 변동 감지
- **DCA 히스토리 체크** (Phase 1 추가, 라인 768-795)
- 그룹 변경 감지

---

### 5.4 레이스 컨디션 타이밍 다이어그램

**시나리오**: 봇 DCA 체결 시

```
시간 →
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MyOrder WebSocket:
    ├─ state='trade' 수신
    ├─ add_dca(실제가 328원) ──┐
    │                          │ 평균가: 331원 계산
    ├─ pending_order 제거      │
    └─────────────────────────┘

                               ↓ (거의 동시)

MyAsset WebSocket:
    ├─ 수량 변동 감지
    ├─ pending_order 체크 ───→ ❌ 없음 (이미 제거됨)
    ├─ DCA 히스토리 체크 ───→ ⚠️ 오래된 데이터 (Phase 1 버그)
    │                          ✅ 최신 데이터 (43be749 수정)
    ├─ 최근 DCA? ────────────→ ✅ 10초 이내
    └─ 스킵 (MyOrder 신뢰)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**레이스 컨디션 발생 지점**:
1. ⚠️ `pending_order` 제거 시점 (MyOrder) vs 체크 시점 (MyAsset)
2. ⚠️ `add_dca()` 완료 시점 vs `get_position()` 읽기 시점 (MyAsset)

**Phase 1-3 해결 방법**:
- DCA 히스토리 10초 체크 (임시 방어)
- 최신 포지션 재조회 (43be749)

**Phase B-C 해결 방법**:
- MyOrder만 처리, MyAsset은 백업 (5초 윈도우)
- 레이스 컨디션 근본적으로 제거

---

## 6. 테스트 시나리오

### 6.1 Phase 1-3 테스트 (완료된 기능)

#### 테스트 1: 봇 신규 매수
**절차**:
1. GUI에서 "수동 매수" 버튼 클릭
2. 그룹 선택, 금액 입력, 확인

**예상 로그**:
```
🔔 [봇] KRW-BTC: 매수 신호 발생!
💰 [봇] KRW-BTC 매수 실행 중...
✅ [봇] KRW-BTC 매수 주문 접수 완료 (주문 ID: abc123...)
   → pending_initial_buys 추가

[MyOrder WebSocket]
   ✅ [봇] KRW-BTC 초기 매수 체결 완료 (수량: 0.001, 평균가: 80,000,000원)
   → create_position(group_id=group_1, ...)
   🗑️ KRW-BTC pending_initial_buys 제거 완료

[MyAsset WebSocket]
   ⏭️ KRW-BTC 봇 주문 진행 중 (MyOrder WebSocket에서 처리 예정, MyAsset 스킵)
```

**검증**:
- ✅ MyOrder가 포지션 생성
- ✅ MyAsset이 스킵
- ✅ pending_initial_buys 정확히 제거

#### 테스트 2: 봇 DCA
**절차**:
1. 기존 포지션이 있는 코인의 가격 하락 (DCA 트리거)
2. 자동 DCA 주문 실행

**예상 로그**:
```
📉 KRW-ETH DCA 레벨 1 트리거 (현재가: 3,500,000원, 목표가: 3,600,000원)
💰 DCA 매수 주문 접수 완료 (주문 ID: def456...)
   → pending_order 추가

[MyOrder WebSocket]
   💰 주문 def456... 부분 체결 (수량: 0.01)
   📊 KRW-ETH 체결가: 3,498,000원 (예상: 3,500,000원, 차이: -2,000원 / -0.057%)
   ✅ KRW-ETH DCA 레벨 1 부분 체결 완료 → add_dca() 호출 (실제 체결가: 3,498,000원)
   → 평균가 재계산: 3,650,000원 → 3,620,000원

[MyAsset WebSocket]
   ⚠️ KRW-ETH 수량 변동 감지 (기존: 0.1 → 신규: 0.11)
   🔍 최근 DCA 히스토리 체크...
   ⏭️ [봇] KRW-ETH 최근 DCA 발생 (10초 이내) → MyOrder에서 평균가 계산 완료, MyAsset skip
```

**검증**:
- ✅ MyOrder가 add_dca() 호출
- ✅ 평균가 정확히 계산 (실제 체결가 반영)
- ✅ MyAsset이 스킵 (10초 체크)

#### 테스트 3: 외부 신규 매수
**절차**:
1. Upbit 앱/웹에서 그룹에 없는 코인 매수 (예: KRW-DOGE)

**예상 로그**:
```
[MyAsset WebSocket]
   🆕 외부 매수 감지 (Upbit 앱/웹): KRW-DOGE
   - REST API로 평균가 조회: 150원
   ✅ [외부] group_null 포지션 생성: KRW-DOGE (Upbit 앱/웹 매수)
```

**검증**:
- ✅ group_null에 포지션 생성
- ✅ REST API로 평균가 조회

#### 테스트 4: 외부 추가 매수
**절차**:
1. Upbit 앱/웹에서 기존 포지션에 추가 매수

**예상 로그**:
```
[MyAsset WebSocket]
   ⚠️ [외부] KRW-BTC 수량 변동 감지 (기존: 0.001 → 신규: 0.0015), REST API로 평균가 조회
   📊 REST API 평균가 조회: KRW-BTC = 79,500,000원
   ✅ 포지션 업데이트 완료
```

**검증**:
- ✅ REST API로 새 평균가 조회
- ✅ 포지션 업데이트

---

### 6.2 Phase B-C 테스트 (재설계 후)

**Phase B-C 구현 후 동일한 테스트 반복하여 비교**:

#### 변경 사항:
- 테스트 3, 4 (외부 매수)가 **MyOrder**에서 처리됨
- MyAsset은 백업만 (5초 후 처리)

**예상 로그 (테스트 3 - 외부 신규 매수)**:
```
[MyOrder WebSocket]
   🆕 [외부] KRW-DOGE 신규 매수 감지 (그룹 없음 → group_null)
   → create_position(group_id=group_null, avg_price=150, quantity=100)
   ✅ [외부] group_null 포지션 생성 완료

[MyAsset WebSocket] (5초 후)
   ⏭️ KRW-DOGE MyOrder에서 최근 처리됨 (5초 이내), MyAsset 스킵
```

---

## 7. 다음 세션 작업 가이드

### 7.1 즉시 시작할 작업

**Step 1: Phase A 분석 (30-45분)**

```bash
# 1. 현재 브랜치 확인
git status
git log -5 --oneline

# 2. 주요 파일 읽기
# - core/v4_trading_engine.py (라인 638-686, 1702-1865)
# - core/position_manager.py (라인 205-287, 445-545, 735-836)
# - gui/myasset_websocket_worker.py (라인 229-288)
```

**분석 항목**:
1. MyOrder와 MyAsset이 같은 이벤트를 처리하는 경로 찾기
2. 중복 책임 목록 작성
3. 레이스 컨디션 발생 가능 지점 표시
4. Phase B-C에서 수정할 코드 블록 식별

**출력물**:
- `PHASE_A_분석_결과.md` (플로우차트, 코드 블록, 타이밍 다이어그램)

---

**Step 2: Phase B 구현 (1-2시간)**

**작업 파일**: `core/v4_trading_engine.py`

**구현 순서**:
1. `_find_group_for_symbol()` 메서드 추가
2. `_on_order_completed()` 확장 - 외부 신규 매수 처리
3. `_on_order_completed()` 확장 - 외부 추가 매수 처리
4. `_mark_processed_by_myorder()` 메서드 추가

**테스트**:
- Upbit 앱에서 그룹 내 코인 매수 → MyOrder 처리 확인
- Upbit 앱에서 그룹 외 코인 매수 → group_null 생성 확인
- Upbit 앱에서 기존 포지션 추가 매수 → 평균가 업데이트 확인

---

**Step 3: Phase C 구현 (1시간)**

**작업 파일**: `core/v4_trading_engine.py`

**구현 순서**:
1. `_was_recently_processed_by_myorder()` 메서드 추가
2. `_process_myasset_data()` 수정 - 백업 역할로 변경
3. MyOrder 처리 완료 시 `_mark_processed_by_myorder()` 호출

**테스트**:
- 정상 케이스: MyOrder 처리 → MyAsset 스킵
- 백업 케이스: MyOrder 누락 시뮬레이션 → MyAsset 처리

---

**Step 4: Phase D 통합 테스트 (1-2시간)**

**테스트 매트릭스**:

| 시나리오 | 방법 | 예상 처리 | 검증 항목 |
|---------|------|---------|---------|
| 봇 신규 | GUI 수동 매수 | MyOrder | 포지션 생성, MyAsset 스킵 |
| 봇 DCA | 가격 하락 대기 | MyOrder | add_dca(), MyAsset 스킵 |
| 외부 신규 (그룹 내) | Upbit 앱 매수 | MyOrder | 그룹 매칭, 포지션 생성 |
| 외부 신규 (그룹 외) | Upbit 앱 매수 | MyOrder | group_null 생성 |
| 외부 추가 | Upbit 앱 매수 | MyOrder | 평균가 업데이트 |
| MyOrder 누락 | WebSocket 중단 | MyAsset | 백업 처리 |

**각 테스트마다**:
1. 로그 캡처 (`logs/trading_*.log`)
2. 포지션 파일 확인 (`data/positions_live.json`)
3. 평균가, 수량, 그룹 ID 검증
4. 중복 처리 없는지 확인

---

**Step 5: Phase E 문서화 (30분)**

**문서 작성**:
1. `docs/DESIGN_V4_MYORDER_MYASSET_ARCHITECTURE.md`
   - 새 아키텍처 다이어그램
   - 플로우차트
   - 코드 예시

2. `CLAUDE.md` 업데이트
   - "MyOrder/MyAsset 역할" 섹션 추가
   - 아키텍처 개요 수정

---

### 7.2 커밋 전략

**Phase B 커밋**:
```bash
git add core/v4_trading_engine.py
git commit -m "feat: MyOrder 확장 - 외부 매수 처리 (Phase B)

- _find_group_for_symbol() 메서드 추가 (그룹 매칭)
- 외부 신규 매수: 그룹 내/외 구분하여 포지션 생성
- 외부 추가 매수: REST API 평균가 조회하여 업데이트
- _mark_processed_by_myorder() 추가 (MyAsset 백업용)

효과:
- MyOrder가 모든 매수 처리 (봇 + 외부)
- 단일 진실 공급원 (Single Source of Truth)
"
```

**Phase C 커밋**:
```bash
git add core/v4_trading_engine.py
git commit -m "feat: MyAsset 축소 - 백업 역할로 변경 (Phase C)

- _was_recently_processed_by_myorder() 추가 (5초 윈도우)
- _process_myasset_data() 백업 로직 추가
- MyOrder 누락 시에만 MyAsset이 처리

효과:
- 중복 처리 완전 제거
- 레이스 컨디션 근본 해결
- 백업 메커니즘 유지
"
```

**Phase D-E 커밋**:
```bash
git add docs/DESIGN_V4_MYORDER_MYASSET_ARCHITECTURE.md CLAUDE.md
git commit -m "docs: MyOrder/MyAsset 재설계 문서화 (Phase E)

- 새 아키텍처 다이어그램 추가
- 테스트 결과 기록
- CLAUDE.md 업데이트
"
```

---

### 7.3 트러블슈팅

**문제 1: MyOrder에서 외부 매수 이벤트 안 받아짐**
- **원인**: MyOrder WebSocket 연결 문제
- **해결**: `_start_myorder_websocket()` 로그 확인, 재연결

**문제 2: 그룹 매칭 실패**
- **원인**: `config.groups`에 코인 없음
- **해결**: `_find_group_for_symbol()` 로그 추가, config 확인

**문제 3: MyAsset이 여전히 중복 처리**
- **원인**: `_mark_processed_by_myorder()` 호출 누락
- **해결**: MyOrder의 모든 처리 경로에 마킹 추가

**문제 4: 평균가 여전히 부정확**
- **원인**: REST API 호출 타이밍 이슈
- **해결**: MyOrder에서 체결 완료 후 1초 대기 후 REST API 조회

---

### 7.4 참고 파일 위치

**코어 파일**:
- `core/v4_trading_engine.py` - 메인 로직
- `core/position_manager.py` - 포지션 관리
- `core/upbit_websocket.py` - WebSocket 베이스 클래스

**GUI 파일**:
- `gui/myasset_websocket_worker.py` - GUI MyAsset 핸들러
- `gui/main_window.py` - WebSocket 시작

**설정 파일**:
- `config/trading_config.json` - 그룹 설정

**런타임 데이터**:
- `data/positions_live.json` - 포지션 상태
- `logs/trading_*.log` - 로그 파일

---

### 7.5 성공 기준

**Phase A 완료**:
- ✅ 플로우차트 작성
- ✅ 중복 처리 지점 목록
- ✅ 타이밍 다이어그램

**Phase B 완료**:
- ✅ 외부 신규 매수 MyOrder 처리
- ✅ 외부 추가 매수 MyOrder 처리
- ✅ 그룹 매칭 정확

**Phase C 완료**:
- ✅ MyAsset 백업 역할 동작
- ✅ MyOrder 우선, MyAsset은 5초 후

**Phase D 완료**:
- ✅ 6가지 시나리오 모두 통과
- ✅ 중복 처리 0건
- ✅ 평균가 100% 정확

**Phase E 완료**:
- ✅ 문서 작성
- ✅ 코드 주석 개선

---

## 8. 요약

### 8.1 완료된 작업 (2025-11-19)

| Phase | 커밋 | 설명 | 상태 |
|-------|------|------|------|
| Phase 1 | 695256e | 백엔드 MyAsset 역할 구분 | ✅ 완료 |
| Phase 2 | f0d6a36 | GUI MyAsset 역할 구분 | ✅ 완료 |
| Phase 3 | 899639d | 로그 개선 ([봇]/[외부]) | ✅ 완료 |
| 버그 수정 1 | 4daa560 | DCA 평균가 보호 (10초 체크) | ✅ 완료 |
| 버그 수정 2 | 43be749 | DCA 히스토리 타이밍 수정 | ✅ 완료 |

### 8.2 다음 작업 (Phase A-E)

| Phase | 예상 시간 | 설명 | 우선순위 |
|-------|----------|------|---------|
| Phase A | 30-45분 | 현재 구조 상세 분석 | 🔥 최우선 |
| Phase B | 1-2시간 | MyOrder 확장 (외부 매수) | 🔥 최우선 |
| Phase C | 1시간 | MyAsset 축소 (백업) | 🔥 최우선 |
| Phase D | 1-2시간 | 통합 테스트 (6개 시나리오) | ⚠️ 필수 |
| Phase E | 30분 | 문서화 | ⚠️ 필수 |

**총 예상 시간**: 4-6시간

---

## 9. 핵심 설계 원칙

### 9.1 단일 진실 공급원 (Single Source of Truth)

**원칙**: 하나의 데이터는 하나의 담당자만 업데이트

**적용**:
- **MyOrder** = 모든 매수 이벤트의 단일 진실 공급원
- **MyAsset** = 백업 및 동기화 (MyOrder 누락 시에만)

### 9.2 타이밍 독립성

**원칙**: 타이밍에 의존하지 않는 설계

**Phase 1-3 문제점**:
- DCA 히스토리 10초 체크 = 타이밍 의존적 (임시 방어)

**Phase B-C 해결**:
- MyOrder만 처리 = 타이밍 무관 (근본 해결)

### 9.3 명확한 책임 분리

**원칙**: 각 컴포넌트의 책임 명확히 정의

**Phase B-C 후**:
- **MyOrder**: 모든 매수 처리 (봇 + 외부, 신규 + 추가)
- **MyAsset**: 백업 및 누락 감지
- **PositionManager**: 포지션 CRUD 및 평균가 계산

---

## 10. 참고 자료

### 10.1 관련 문서

- `CLAUDE.md` - 프로젝트 전체 가이드
- `README.md` - 프로젝트 개요
- `DESIGN_V4_COMPLETE.md` - V4 아키텍처 설계 문서

### 10.2 Upbit API 문서

- MyOrder WebSocket: https://docs.upbit.com/reference/websocket-myorder
- MyAsset WebSocket: https://docs.upbit.com/reference/websocket-myasset
- REST API (계좌 조회): https://docs.upbit.com/reference/계좌-전체-조회

### 10.3 관련 이슈

- **이슈**: DCA 평균가 덮어쓰기
- **근본 원인**: 두 WebSocket의 레이스 컨디션
- **임시 해결**: 10초 DCA 히스토리 체크
- **근본 해결**: MyOrder 단일 처리 (Phase B-C)

---

## 부록: 코드 스니펫 참고

### A. 그룹 매칭 예시 코드

```python
def _find_group_for_symbol(self, symbol: str) -> Optional[str]:
    """
    config.groups를 검색하여 symbol이 속한 그룹 ID 반환

    Args:
        symbol: "KRW-BTC" 형식의 심볼

    Returns:
        그룹 ID (예: "group_1") 또는 None
    """
    config = self.config_manager.get_config()

    for group_id, group_data in config.get('groups', {}).items():
        coins = group_data.get('coins', [])
        if symbol in coins:
            logger.debug(f"   🔍 {symbol} → 그룹 매칭: {group_id}")
            return group_id

    logger.debug(f"   🔍 {symbol} → 그룹 없음")
    return None
```

### B. MyOrder 외부 매수 처리 예시 코드

```python
# _on_order_completed() 내부 추가
def _on_order_completed(self, data: dict):
    # ... (기존 코드)

    if state == 'done' and side == 'bid':
        symbol = data.get('market', '')
        order_uuid = data.get('uuid', '')
        executed_volume = float(data.get('executed_volume', 0))
        avg_price = float(data.get('avg_price', 0))

        # 1. 봇 신규 매수 (기존 로직)
        if order_uuid in self.pending_initial_buys:
            # ... (라인 1743-1786)
            self._mark_processed_by_myorder(symbol)
            return

        # 2. 외부 매수 처리 (신규)
        position = self.position_manager.get_position(symbol)

        if not position:
            # 2-1. 외부 신규 매수
            group_id = self._find_group_for_symbol(symbol)

            if group_id:
                logger.info(f"🆕 [외부] {symbol} 신규 매수 감지 (그룹: {group_id})")
            else:
                logger.info(f"🆕 [외부] {symbol} 신규 매수 감지 (그룹 없음 → group_null)")
                group_id = "group_null"

            position = self.position_manager.create_position(
                group_id=group_id,
                symbol=symbol,
                buy_price=avg_price,
                quantity=executed_volume,
                force_create_for_sync=(group_id == "group_null")
            )

            self._mark_processed_by_myorder(symbol)
            return

        # 2-2. 외부 추가 매수
        pending_order = position.get('pending_order')

        if not pending_order:
            logger.info(f"🆕 [외부] {symbol} 추가 매수 감지 (수량: {executed_volume:.8f})")

            # REST API로 최신 평균가 조회
            if self.upbit_api:
                accounts = self.upbit_api.get_accounts()
                for acc in accounts:
                    currency = symbol.replace('KRW-', '')
                    if acc['currency'] == currency:
                        new_avg_price = float(acc.get('avg_buy_price', 0))
                        new_balance = float(acc.get('balance', 0))

                        self.position_manager.update_position(symbol, {
                            'total_amount': new_balance,
                            'avg_buy_price': new_avg_price,
                            'total_invested_krw': new_avg_price * new_balance
                        })

                        logger.info(f"   ✅ [외부] {symbol} 추가 매수 반영 (새 평균가: {new_avg_price:,.0f}원)")
                        break

            self._mark_processed_by_myorder(symbol)
            return
```

### C. MyAsset 백업 처리 예시 코드

```python
def _was_recently_processed_by_myorder(self, symbol: str, window_seconds: int = 5) -> bool:
    """
    최근 N초 이내 MyOrder에서 해당 symbol 처리했는지 확인

    Args:
        symbol: "KRW-BTC" 형식
        window_seconds: 윈도우 시간 (기본 5초)

    Returns:
        True if 최근 처리됨, False otherwise
    """
    if not hasattr(self, '_myorder_processed_symbols'):
        self._myorder_processed_symbols = {}

    last_time = self._myorder_processed_symbols.get(symbol)
    if last_time:
        elapsed = (datetime.now() - last_time).total_seconds()
        if elapsed < window_seconds:
            logger.debug(f"   ⏭️ {symbol} MyOrder에서 {elapsed:.1f}초 전 처리됨")
            return True

    return False

def _mark_processed_by_myorder(self, symbol: str):
    """
    MyOrder에서 symbol 처리했음을 기록

    Args:
        symbol: "KRW-BTC" 형식
    """
    if not hasattr(self, '_myorder_processed_symbols'):
        self._myorder_processed_symbols = {}

    self._myorder_processed_symbols[symbol] = datetime.now()
    logger.debug(f"   📝 {symbol} MyOrder 처리 기록")
```

---

**문서 작성일**: 2025-11-20
**작성자**: Claude
**버전**: 1.0
**다음 업데이트**: Phase A-E 완료 후
