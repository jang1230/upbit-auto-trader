# Phase A: MyOrder/MyAsset 상세 구조 분석 결과

**분석 일자**: 2025-11-20
**브랜치**: `claude/backup-copy-v4-01D6qnKRJSHFVEK1WJQRYzEH`
**분석자**: Claude
**분석 범위**: MyOrder WebSocket과 MyAsset WebSocket의 모든 상호작용 지점

---

## 📋 목차

1. [전체 아키텍처 개요](#1-전체-아키텍처-개요)
2. [MyOrder WebSocket 처리 흐름](#2-myorder-websocket-처리-흐름)
3. [MyAsset WebSocket 처리 흐름](#3-myasset-websocket-처리-흐름)
4. [pending_initial_buys 메커니즘](#4-pending_initial_buys-메커니즘)
5. [중복 처리 지점 목록](#5-중복-처리-지점-목록)
6. [레이스 컨디션 발생 지점](#6-레이스-컨디션-발생-지점)
7. [타이밍 다이어그램](#7-타이밍-다이어그램)
8. [리팩토링 대상 코드 블록](#8-리팩토링-대상-코드-블록)

---

## 1. 전체 아키텍처 개요

### 1.1 현재 구조 플로우차트

```
사용자 매수 신호 발생
    ↓
┌─────────────────────────────────────────────────────────┐
│ V4TradingEngine._execute_buy()                          │
│ - Dry-run: 즉시 포지션 생성                              │
│ - Live: upbit_api.buy_market_order() 호출               │
│         pending_initial_buys에 order_uuid 등록          │
│         (포지션 생성 안 함)                              │
└─────────────────────────────────────────────────────────┘
    ↓ (Live 모드)
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│ MyOrder WebSocket                    │  │ MyAsset WebSocket                    │
│ (core/upbit_websocket.py)            │  │ (core/upbit_websocket.py)            │
│                                      │  │                                      │
│ 수신: state='done' and side='bid'    │  │ 수신: balance > 0 (신규 잔고)         │
│   ↓                                  │  │   ↓                                  │
│ _on_order_completed()                │  │ _process_myasset_data()              │
│ (v4_trading_engine.py:1713-1900)     │  │ (v4_trading_engine.py:638-688)       │
│                                      │  │                                      │
│ ✅ pending_initial_buys 체크          │  │ ⚠️ pending_initial_buys 체크          │
│    order_uuid in pending?            │  │    symbol in pending values?         │
│      ↓ YES                           │  │      ↓ YES                           │
│    포지션 생성                         │  │    스킵 (MyOrder가 처리)              │
│    거래 기록                          │  │      ↓ NO                            │
│    텔레그램 알림                       │  │    외부 매수 → group_null 생성        │
│    pending_initial_buys 제거          │  │                                      │
└──────────────────────────────────────┘  └──────────────────────────────────────┘
         |                                           |
         +----- 거의 동시 처리 (100-500ms 차이) ------+
                        |
                        ↓
                PositionManager
                  positions.json
```

### 1.2 컴포넌트별 역할

| 컴포넌트 | 현재 역할 | 처리 이벤트 | 문제점 |
|---------|----------|-----------|-------|
| **MyOrder WebSocket** | 봇 주문 체결 처리 | 봇 신규 매수, 봇 DCA | 외부 주문 무시 |
| **MyAsset WebSocket (백엔드)** | 외부 매수 감지 | 외부 신규 매수 | 타이밍 의존적 |
| **MyAsset WebSocket (GUI)** | 외부 매수 감지 (중복) | 외부 신규 매수 | 백엔드와 중복 |
| **PositionManager.sync_from_myasset** | 포지션 동기화 | 수량 변동, 추가 매수 | DCA 평균가 덮어쓰기 위험 |
| **pending_initial_buys** | 초기 매수 추적 | 봇 신규 매수만 | 외부 매수 추적 안 함 |

---

## 2. MyOrder WebSocket 처리 흐름

### 2.1 메서드 위치

**파일**: `core/v4_trading_engine.py`
**메서드**: `_on_order_completed()` (라인 1713-1900)

### 2.2 상세 처리 플로우

```
MyOrder WebSocket 이벤트 수신
    ↓
order_data 파싱
  - uuid: 주문 ID
  - code: 심볼 (KRW-BTC)
  - state: 주문 상태 (wait, trade, done, cancel, prevented)
  - ask_bid: BID(매수) / ASK(매도)
  - executed_volume: 체결 수량
  - avg_price: 평균 체결가
  - price: 실제 체결가 (state='trade'일 때)
    ↓
state 체크
    ↓
┌────────────────────────────────────────────────────────────┐
│ 1. state == 'wait': 무시                                    │
│    - 아직 체결 안 됨                                         │
└────────────────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────────────────┐
│ 2. 초기 매수 체결 (pending_initial_buys 체크)               │
│    if order_uuid in self.pending_initial_buys:             │
│      ↓                                                      │
│    state == 'done'?                                        │
│      ↓ YES                                                 │
│    포지션 생성 (create_position)                            │
│      - group_id: pending에서 가져옴                         │
│      - symbol                                              │
│      - buy_price: avg_price (실제 체결가)                   │
│      - quantity: executed_volume (실제 수량)                │
│    거래 기록 (trade_history)                                │
│    텔레그램 알림 ("[봇] 매수 완료")                          │
│    pending_initial_buys 제거 (del)                         │
│    return                                                  │
└────────────────────────────────────────────────────────────┘
    ↓ (pending_initial_buys에 없으면)
┌────────────────────────────────────────────────────────────┐
│ 3. 부분 체결 (state == 'trade')                             │
│    - DCA 주문 체결 처리                                      │
│    포지션 확인                                               │
│    pending_order 매칭 (order_uuid == pending.order_id)      │
│      ↓ 매칭 성공                                            │
│    order_type == 'dca'?                                    │
│      ↓ YES                                                 │
│    add_dca() 호출                                          │
│      - dca_price: trade_price (실제 체결가)                 │
│      - dca_amount: executed_volume (실제 수량)              │
│    거래 기록                                                 │
│    pending_order 제거 (update_position)                    │
│    return                                                  │
└────────────────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────────────────┐
│ 4. 취소/방지 (state == 'cancel' or 'prevented')             │
│    pending_order 정리                                       │
│    return                                                  │
└────────────────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────────────────┐
│ 5. 전체 체결 완료 (state == 'done')                         │
│    - 익절/손절 주문 체결 처리                                │
│    pending_order 매칭                                       │
│    order_type 확인 ('profit', 'loss')                      │
│    executed_levels 업데이트                                 │
│    pending_order 제거                                       │
└────────────────────────────────────────────────────────────┘
```

### 2.3 처리하는 이벤트

| 이벤트 | 조건 | 처리 | 코드 위치 |
|-------|-----|------|---------|
| **봇 신규 매수** | `order_uuid in pending_initial_buys` | ✅ create_position | 1743-1786 |
| **봇 DCA** | `pending_order.type == 'dca'` | ✅ add_dca | 1788-1853 |
| **봇 익절/손절** | `pending_order.type == 'profit/loss'` | ✅ executed_levels 업데이트 | 1869-1900 |
| **외부 신규 매수** | - | ❌ 무시 (처리 안 함) | - |
| **외부 추가 매수** | - | ❌ 무시 (처리 안 함) | - |

### 2.4 핵심 변수

#### pending_initial_buys
**위치**: `v4_trading_engine.py:163`
```python
self.pending_initial_buys: Dict[str, Dict[str, Any]] = {}
# {order_uuid: {symbol, group_id, group_name, buy_amount_krw}}
```

**추가 시점**: `_execute_buy()` Live 모드 (라인 958-963)
```python
self.pending_initial_buys[order_uuid] = {
    'symbol': symbol,
    'group_id': group_id,
    'group_name': group.get('name', 'Unknown'),
    'buy_amount_krw': buy_amount
}
```

**제거 시점**: `_on_order_completed()` state='done' (라인 1783)
```python
del self.pending_initial_buys[order_uuid]
```

**사용 지점**:
1. MyOrder WebSocket: 봇 주문 체결 확인 (라인 1743)
2. MyAsset WebSocket (백엔드): 봇/외부 구분 (라인 640-643)
3. MyAsset WebSocket (GUI): 봇/외부 구분 (라인 232-236)
4. 중복 매수 방지: pending 체크 (라인 790-795)

---

## 3. MyAsset WebSocket 처리 흐름

### 3.1 백엔드 처리

**파일**: `core/v4_trading_engine.py`
**메서드**: `_process_myasset_data()` (라인 638-688)

```
MyAsset WebSocket 이벤트 수신
    ↓
assets 배열 순회
    ↓
for asset in data:
  currency = asset.get('currency')
  balance = float(asset.get('balance', 0))
  locked = float(asset.get('locked', 0))
  total = balance + locked
    ↓
  KRW 제외, balance > 0 체크
    ↓
  symbol = f"KRW-{currency}"
  position = get_position(symbol)
    ↓
┌──────────────────────────────────────────────────────────┐
│ position 없음 (신규 매수 감지)                             │
│   ↓                                                       │
│ 🆕 봇 주문인지 확인 (Phase 1-2에서 추가)                   │
│   is_bot_order = any(                                    │
│     pending['symbol'] == symbol                          │
│     for pending in pending_initial_buys.values()         │
│   )                                                      │
│   ↓                                                       │
│ if is_bot_order:                                         │
│   logger.debug("⏭️ 봇 주문 진행 중 (MyOrder 처리, skip)")  │
│   continue                                               │
│   ↓                                                       │
│ 외부 매수 감지                                             │
│   logger.info("🆕 외부 매수 감지 (Upbit 앱/웹)")           │
│   ↓                                                       │
│ REST API로 avg_buy_price 조회                            │
│   accounts = upbit_api.get_accounts()                    │
│   avg_buy_price = acc.get('avg_buy_price', 0)           │
│   ↓                                                       │
│ avg_buy_price > 0?                                       │
│   ↓ YES                                                  │
│ create_position(                                         │
│   group_id="group_null",                                 │
│   symbol=symbol,                                         │
│   buy_price=avg_buy_price,                               │
│   quantity=total,                                        │
│   force_create_for_sync=True                             │
│ )                                                        │
│   ↓                                                       │
│ logger.info("✅ [외부] group_null 포지션 생성")            │
└──────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────┐
│ position 있음 (sync_from_myasset 호출)                    │
│   - PositionManager.sync_from_myasset()에서 처리          │
│   - 수량 변동 감지                                         │
│   - 평균가 업데이트 (DCA 히스토리 체크)                    │
└──────────────────────────────────────────────────────────┘
```

### 3.2 GUI 처리

**파일**: `gui/myasset_websocket_worker.py`
**메서드**: `_handle_myasset_data()` (라인 229-288)

**차이점**:
- 백엔드와 거의 동일한 로직
- `pending_initial_buys` 참조 전달받음 (main_window에서)
- `balance_updated.emit(assets)` 시그널 발생

**중복 처리 위험**:
- 백엔드와 GUI가 **같은 외부 매수 이벤트**를 동시에 처리
- `group_null` 포지션 2번 생성 가능성 (Phase 1-2에서 방어 추가)

### 3.3 PositionManager.sync_from_myasset()

**파일**: `core/position_manager.py`
**메서드**: `sync_from_myasset()` (라인 735-850)

```
MyAsset 데이터로 포지션 동기화
    ↓
for asset in assets:
  symbol = f"KRW-{currency}"
  balance, locked, avg_buy_price 추출
    ↓
  position = get_position(symbol)
    ↓
┌──────────────────────────────────────────────────────────┐
│ position 있음 (기존 포지션 업데이트)                       │
│   ↓                                                       │
│ updates = {                                              │
│   'total_amount': balance,                               │
│   'locked_amount': locked                                │
│ }                                                        │
│   ↓                                                       │
│ avg_buy_price 처리                                        │
│   ↓                                                       │
│ if avg_buy_price > 0:  (MyAsset 제공)                    │
│   updates['avg_buy_price'] = avg_buy_price               │
│   ↓                                                       │
│ else:  (MyAsset에 없음)                                  │
│   수량 변동 감지?                                          │
│     ↓ YES                                                │
│   pending_order 체크                                      │
│     ↓ 있음 (봇 DCA 진행 중)                               │
│     ⏭️ REST API 조회 skip (MyOrder 계산 신뢰)             │
│     ↓ 없음                                                │
│     🆕 최근 DCA 히스토리 체크 (10초)                       │
│       current_position = get_position(symbol)  # 재조회    │
│       last_dca_time < 10초?                               │
│         ↓ YES (봇 DCA)                                   │
│         ⏭️ REST API skip (MyOrder 계산 신뢰)              │
│         ↓ NO (외부 추가매수)                              │
│         ⚠️ REST API로 평균가 조회                         │
│         accounts = upbit_api.get_accounts()              │
│         updates['avg_buy_price'] = fetched_avg_price     │
│   ↓                                                       │
│ update_position(symbol, updates)                         │
└──────────────────────────────────────────────────────────┘
```

**핵심 로직** (라인 768-795):
- **pending_order 체크**: DCA 진행 중이면 skip (라인 754-766)
- **10초 DCA 히스토리 체크**: 최근 DCA면 skip (라인 768-783) ⭐ Phase 1 추가
- **외부 추가매수**: REST API 조회 (라인 785-795)

---

## 4. pending_initial_buys 메커니즘

### 4.1 생명 주기

```
매수 신호 발생
    ↓
_execute_buy() 호출
    ↓
Live 모드?
  ↓ YES
upbit_api.buy_market_order(symbol, amount)
    ↓
order_result.uuid 받음
    ↓
pending_initial_buys[uuid] = {
  'symbol': symbol,
  'group_id': group_id,
  'group_name': group_name,
  'buy_amount_krw': amount
}
    ↓
[대기 시간: 100-500ms]
    ↓
┌──────────────────────┐  ┌──────────────────────┐
│ MyOrder WebSocket    │  │ MyAsset WebSocket    │
│ state='done' 수신     │  │ balance > 0 수신      │
│   ↓                  │  │   ↓                  │
│ uuid in pending?     │  │ symbol in pending?   │
│   ↓ YES              │  │   ↓ YES              │
│ 포지션 생성           │  │ 스킵 (MyOrder 처리)   │
│ pending에서 제거      │  │                      │
└──────────────────────┘  └──────────────────────┘
         |                        |
         +------- 레이스 윈도우 ----+
              (100-500ms)
```

### 4.2 사용 지점 (총 4곳)

| # | 위치 | 목적 | 동작 |
|---|-----|------|-----|
| 1 | `v4_trading_engine.py:1743` | MyOrder 체결 확인 | uuid로 체크 → 포지션 생성 |
| 2 | `v4_trading_engine.py:640-643` | MyAsset 봇/외부 구분 | symbol로 체크 → 봇이면 skip |
| 3 | `myasset_websocket_worker.py:232-236` | GUI MyAsset 봇/외부 구분 | symbol로 체크 → 봇이면 skip |
| 4 | `v4_trading_engine.py:790-795` | 중복 매수 방지 | symbol로 체크 → pending이면 skip |

### 4.3 체크 방식의 차이

**MyOrder (uuid 체크)**:
```python
if order_uuid in self.pending_initial_buys:
    # uuid 정확히 매칭
```

**MyAsset (symbol 체크)**:
```python
is_bot_order = any(
    pending_data.get('symbol') == symbol
    for pending_data in self.pending_initial_buys.values()
)
# symbol만 비교 (uuid 모름)
```

**장점**: symbol만으로 봇/외부 구분 가능
**단점**: 같은 코인 여러 주문 시 구분 어려움 (현재는 중복 방지로 해결)

---

## 5. 중복 처리 지점 목록

### 5.1 신규 포지션 생성 중복

| # | 처리 위치 | 조건 | 동작 | 중복 방지 |
|---|---------|-----|------|---------|
| 1 | MyOrder WebSocket (백엔드) | 봇 주문 체결 | ✅ create_position | pending_initial_buys (uuid) |
| 2 | MyAsset WebSocket (백엔드) | 외부 매수 감지 | ✅ create_position (group_null) | pending_initial_buys 체크 (Phase 1) ⭐ |
| 3 | MyAsset WebSocket (GUI) | 외부 매수 감지 | ✅ create_position (group_null) | pending_initial_buys 체크 (Phase 2) ⭐ |

**현재 상태**:
- ✅ 백엔드 MyAsset과 GUI MyAsset의 중복 생성 방지 완료 (Phase 1-2)
- ✅ MyOrder와 MyAsset의 중복 생성 방지 완료 (Phase 1-2)

### 5.2 평균가 업데이트 중복

| # | 처리 위치 | 트리거 | 동작 | 중복 방지 |
|---|---------|-------|------|---------|
| 1 | MyOrder WebSocket | DCA 체결 (state='trade') | ✅ add_dca() (정확한 평균가) | - |
| 2 | PositionManager.sync_from_myasset | 수량 변동 감지 | ⚠️ REST API 조회 (덮어쓰기 위험) | pending_order 체크 + 10초 DCA 히스토리 (Phase 1 버그 수정) ⭐ |

**문제 상황** (Phase 1 이전):
```
시간: 15:38:45.123
MyOrder: DCA 체결 → add_dca(실제가 328원) → 평균가 331원 계산 완료

시간: 15:38:45.234 (111ms 후)
MyAsset: 수량 변동 감지 → pending_order 없음 (이미 제거) → REST API 조회 (336원) → 덮어쓰기
```

**해결 방법** (Phase 1):
- **pending_order 체크**: 진행 중이면 skip (라인 754-766)
- **10초 DCA 히스토리 체크**: 최근 DCA면 skip (라인 768-783) ⭐
- **최신 포지션 재조회**: add_dca() 반영 확인 (라인 770) ⭐ Phase 1 버그 수정

### 5.3 외부 매수 중복 처리

| # | 처리 위치 | 동작 | 중복 방지 | 상태 |
|---|---------|------|---------|-----|
| 1 | MyAsset (백엔드) | group_null 생성 | pending_initial_buys 체크 | ✅ Phase 1 |
| 2 | MyAsset (GUI) | group_null 생성 | pending_initial_buys 체크 | ✅ Phase 2 |

**현재 상태**: ✅ 중복 생성 방지 완료

---

## 6. 레이스 컨디션 발생 지점

### 6.1 봇 신규 매수 시 (MyOrder vs MyAsset)

```
시간축 →
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

T+0ms:   _execute_buy() → buy_market_order() 호출
T+10ms:  order_result 수신 → pending_initial_buys[uuid] 추가
T+50ms:  MyOrder WebSocket 연결 대기 중...
         MyAsset WebSocket 연결 대기 중...

T+150ms: MyOrder 이벤트 수신 (state='done')
         → uuid in pending? ✅ YES
         → create_position() 호출 시작

T+180ms: MyAsset 이벤트 수신 (balance > 0)
         → symbol in pending? ✅ YES (Phase 1 추가)
         → ⏭️ 스킵 (MyOrder 처리 대기)

T+200ms: MyOrder create_position() 완료
         → pending_initial_buys 제거 (del uuid)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Phase 1-2 해결: MyAsset이 pending 체크하여 스킵
```

**레이스 윈도우**: T+150ms ~ T+200ms (약 50ms)
**해결 상태**: ✅ Phase 1-2에서 해결 (pending_initial_buys 체크)

### 6.2 봇 DCA 시 (MyOrder vs MyAsset)

```
시간축 →
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

T+0ms:   DCA 주문 실행 → pending_order 추가
T+100ms: MyOrder 이벤트 수신 (state='trade')

T+120ms: MyOrder add_dca() 시작
         - dca_price: 328원 (실제 체결가)
         - 평균가 재계산: 331원
         - dca_history 추가 (timestamp 기록)

T+150ms: MyOrder add_dca() 완료
         - 평균가: 331원 저장
         - pending_order 제거 (= None)

T+160ms: MyAsset 이벤트 수신 (수량 변동)
         - 수량 변동 감지 (0.1 → 0.11)
         - pending_order 체크 → ❌ 없음 (이미 제거)
         - 🆕 최신 포지션 재조회 (get_position)
         - 🆕 DCA 히스토리 체크 (last_dca < 10초?)
           → ✅ YES (10ms 전)
         - ⏭️ REST API skip (MyOrder 계산 신뢰)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Phase 1 해결: 10초 DCA 히스토리 체크
⚠️ 타이밍 의존적: 10초 윈도우 (임시 방어책)
```

**레이스 윈도우**: T+150ms ~ T+10초 (약 10초)
**해결 상태**: ⚠️ Phase 1에서 임시 해결 (10초 체크)
**근본 해결**: Phase B-C에서 MyOrder만 처리 (타이밍 무관)

### 6.3 외부 추가 매수 시

```
시간축 →
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

T+0ms:   사용자가 Upbit 앱에서 추가 매수 (0.001 BTC)

T+50ms:  MyOrder WebSocket 이벤트 수신 (state='done')
         → uuid in pending? ❌ NO (외부 주문)
         → position 확인 → 있음
         → pending_order 확인 → 없음
         → ❌ 현재: 무시 (처리 안 함)
         → 🔧 Phase B: 외부 추가 매수 처리 추가 예정

T+100ms: MyAsset WebSocket 이벤트 수신 (수량 변동)
         → 수량 변동 감지 (0.005 → 0.006)
         → pending_order 없음
         → DCA 히스토리 없음
         → ✅ REST API로 평균가 조회
         → update_position(avg_price=...)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ 현재 문제: MyOrder가 외부 매수 무시
✅ Phase B: MyOrder가 외부 매수도 처리하도록 확장
```

**현재 상태**: ❌ MyAsset만 처리 (비효율)
**Phase B 목표**: MyOrder가 모든 매수 처리

---

## 7. 타이밍 다이어그램

### 7.1 봇 신규 매수 (정상 케이스)

```
시간 →   0ms    50ms   100ms  150ms  200ms  250ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

거래
엔진      [매수]
          |
          ↓
Upbit     [주문]
API         |
          ↓
pending   [uuid 추가]
          |
          ├────────────────────────┐
          ↓                        ↓
MyOrder                      [state=done]
WebSocket                      ↓
                             [포지션 생성]
                               ↓
                             [pending 제거]

MyAsset                            [balance>0]
WebSocket                            ↓
                                   [pending 체크]
                                     ↓
                                   [✅ 스킵]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 7.2 봇 DCA (평균가 레이스)

```
시간 →   0ms    50ms   100ms  150ms  200ms  250ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

거래
엔진      [DCA 주문]
          |
          ↓
pending   [pending_order 추가]
order     |
          ├────────────────────────┐
          ↓                        ↓
MyOrder                      [state=trade]
WebSocket                      ↓
                             [add_dca(328원)]
                               ↓
                             [평균가: 331원]
                               ↓
                             [dca_history 추가]
                               ↓
                             [pending_order 제거]

MyAsset                            [수량 변동]
WebSocket                            ↓
                                   [pending_order? ❌]
                                     ↓
                                   [🆕 position 재조회]
                                     ↓
                                   [🆕 DCA history?]
                                     ↓
                                   [✅ 10초 이내]
                                     ↓
                                   [⏭️ REST skip]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**타이밍 의존성**:
- ⚠️ 10초 윈도우 (임시 방어)
- ⚠️ position 재조회 타이밍 중요 (Phase 1 버그 수정)

### 7.3 외부 신규 매수 (현재 vs Phase B)

**현재 (MyAsset 처리)**:
```
시간 →   0ms    50ms   100ms  150ms  200ms  250ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Upbit    [사용자 매수]
앱         |
          ↓
MyOrder                      [state=done]
WebSocket                      ↓
                             [pending? ❌]
                               ↓
                             [position? ❌]
                               ↓
                             [❌ 무시]

MyAsset                            [balance>0]
WebSocket                            ↓
                                   [pending? ❌]
                                     ↓
                                   [REST API]
                                     ↓
                                   [✅ group_null 생성]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Phase B (MyOrder 처리)**:
```
시간 →   0ms    50ms   100ms  150ms  200ms  250ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Upbit    [사용자 매수]
앱         |
          ↓
MyOrder                      [state=done]
WebSocket                      ↓
                             [pending? ❌]
                               ↓
                             [position? ❌]
                               ↓
                             [🔧 그룹 매칭]
                               ↓
                             [✅ 포지션 생성]
                               ↓
                             [🆕 처리 마킹]

MyAsset                            [balance>0]
WebSocket                            ↓
                                   [🆕 최근 처리? ✅]
                                     ↓
                                   [⏭️ 백업 스킵]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 8. 리팩토링 대상 코드 블록

### 8.1 MyOrder 확장 (Phase B)

**파일**: `core/v4_trading_engine.py`
**메서드**: `_on_order_completed()` (라인 1713-1900)

#### 추가 위치 1: 외부 신규 매수 처리

**현재 코드** (라인 1786 이후):
```python
return  # 초기 매수는 여기서 종료
```

**추가할 코드**:
```python
# 🔧 Phase B: 외부 신규 매수 처리
if state == 'done' and side == 'bid':
    position = self.position_manager.get_position(symbol)

    if not position:
        # 외부 신규 매수 감지
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
```

#### 추가 위치 2: 외부 추가 매수 처리

**추가할 코드** (외부 신규 매수 이후):
```python
    # 외부 추가 매수 처리
    if position:
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

#### 새 메서드 추가

**메서드 1: _find_group_for_symbol**
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

**메서드 2: _mark_processed_by_myorder**
```python
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

### 8.2 MyAsset 축소 (Phase C)

**파일**: `core/v4_trading_engine.py`
**메서드**: `_process_myasset_data()` (라인 638-688)

#### 수정할 코드

**현재** (라인 638-648):
```python
if not position:
    # 🆕 봇 주문인지 확인 (pending_initial_buys)
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

**Phase C 수정**:
```python
if not position:
    # 🆕 봇 주문인지 확인 (pending_initial_buys)
    is_bot_order = any(
        pending_data.get('symbol') == symbol
        for pending_data in self.pending_initial_buys.values()
    )

    if is_bot_order:
        # 봇 주문 → MyOrder WebSocket이 처리할 예정
        logger.debug(f"⏭️ {symbol} 봇 주문 진행 중 (MyOrder WebSocket에서 처리 예정, MyAsset 스킵)")
        continue

    # 🔧 Phase C: MyOrder가 이미 처리했는지 확인 (5초 윈도우)
    if self._was_recently_processed_by_myorder(symbol):
        logger.debug(f"   ⏭️ {symbol} MyOrder에서 최근 처리됨 (5초 이내), MyAsset 스킵")
        continue

    # MyOrder가 누락했을 가능성 → 백업 처리
    logger.warning(f"   ⚠️ {symbol} MyOrder 누락 감지, MyAsset 백업 처리")

    # 외부 매수 감지 (Upbit 앱/웹에서 직접 매수)
    logger.info(f"🆕 외부 매수 감지 (Upbit 앱/웹): {symbol}")
```

#### 새 메서드 추가

**메서드: _was_recently_processed_by_myorder**
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
```

### 8.3 초기화 코드 추가

**파일**: `core/v4_trading_engine.py`
**위치**: `__init__` 메서드 (라인 163 이후)

**추가할 코드**:
```python
# 초기 매수 주문 추적 (MyOrder WebSocket에서 포지션 생성용)
self.pending_initial_buys: Dict[str, Dict[str, Any]] = {}

# 🆕 Phase B-C: MyOrder 처리 완료 추적 (MyAsset 백업용)
self._myorder_processed_symbols: Dict[str, datetime] = {}  # {symbol: timestamp}
```

---

## 9. 핵심 통찰 및 결론

### 9.1 현재 아키텍처의 한계

| 한계 | 설명 | 영향 |
|-----|------|-----|
| **타이밍 의존적** | 10초 DCA 체크, 5초 백업 윈도우 | 레이스 컨디션 위험 |
| **역할 불명확** | MyOrder와 MyAsset이 같은 이벤트 처리 가능성 | 중복 처리 위험 |
| **비효율적** | MyOrder가 모든 이벤트 수신하는데 외부 매수는 MyAsset 처리 | 리소스 낭비 |
| **신규 포지션만 구분** | 기존 포지션 추가 매수는 여전히 중복 위험 | 외부 추가 매수 문제 |

### 9.2 Phase B-C 개선 효과

| 개선 항목 | 현재 (Phase 1-3) | Phase B-C 이후 |
|---------|----------------|--------------|
| **외부 신규 매수** | MyAsset 처리 | MyOrder 처리 → MyAsset 백업 |
| **외부 추가 매수** | MyAsset REST API | MyOrder 처리 → MyAsset 백업 |
| **평균가 정확성** | 10초 체크 (타이밍 의존) | MyOrder만 처리 (타이밍 무관) |
| **중복 방지** | pending 체크 + 10초 체크 | MyOrder 단일 처리 + 5초 백업 |
| **레이스 윈도우** | 10초 | 5초 |
| **아키텍처 명확성** | 모호 (둘 다 처리) | 명확 (MyOrder 우선, MyAsset 백업) |

### 9.3 Phase A 완료 체크리스트

- [x] MyOrder WebSocket 처리 흐름 분석
- [x] MyAsset WebSocket 처리 흐름 분석 (백엔드 + GUI)
- [x] pending_initial_buys 메커니즘 분석
- [x] 중복 처리 지점 5개 식별
- [x] 레이스 컨디션 3개 시나리오 분석
- [x] 타이밍 다이어그램 3개 작성
- [x] 리팩토링 대상 코드 블록 상세 작성
- [x] Phase B-C 구현 가이드 제공

---

## 10. 다음 단계 (Phase B)

### Phase B-1: MyOrder 확장 - 외부 신규 매수

**작업 항목**:
1. `_find_group_for_symbol()` 메서드 추가
2. `_on_order_completed()`에 외부 신규 매수 처리 추가
3. `_mark_processed_by_myorder()` 메서드 추가

**예상 시간**: 30분

### Phase B-2: MyOrder 확장 - 외부 추가 매수

**작업 항목**:
1. `_on_order_completed()`에 외부 추가 매수 처리 추가
2. REST API 평균가 조회 로직

**예상 시간**: 30분

### Phase B-3: 테스트

**작업 항목**:
1. Upbit 앱에서 그룹 내 코인 매수 → MyOrder 처리 확인
2. Upbit 앱에서 그룹 외 코인 매수 → group_null 생성 확인
3. Upbit 앱에서 기존 포지션 추가 매수 → 평균가 업데이트 확인

**예상 시간**: 30분

---

**Phase A 완료 상태**: ✅
**다음 작업**: Phase B-1 시작 (MyOrder 확장)
**총 분석 시간**: 45분

