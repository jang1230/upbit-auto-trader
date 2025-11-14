# Session Summary: 2025-01-14

## 📋 오늘 완료한 작업

### GUI 개선 작업 (19개 커밋)

#### 1. Dialog 크기 및 레이아웃 조정
- **커밋**: baac79b, a072a8a, 6e9f32a, 8d7a391, b001445
- **변경 내용**:
  - Dialog 크기를 600x525, 800x500 등으로 조정
  - QGroupBox가 제대로 렌더링되도록 spacing 개선
  - Parent dialog 크기 존중하도록 수정
- **영향받은 파일**:
  - `gui/auto_buy_settings_dialog_v2.py`
  - `gui/group_unified_settings_dialog.py`

#### 2. AutoBuySettingsDialogV2 수정
- **커밋**: 25630a1, 4b4a1e5, 3166a11
- **변경 내용**:
  - Parent dialog 크기를 존중하도록 수정 (embedded 모드)
  - `buy_settings` 구조 nesting 문제 수정
  - Full buy_settings 전달하도록 수정
- **버그 수정**: buy_settings 구조가 이중으로 중첩되는 문제 해결

#### 3. Strategy 정보 표시 수정
- **커밋**: 374d0e5
- **변경 내용**: Save confirmation dialog에서 올바른 strategy 정보 표시
- **파일**: `gui/group_unified_settings_dialog.py`

#### 4. V4/Manual 모드 가시성 개선
- **커밋**: 77f0323, 9135ff1
- **변경 내용**:
  - V4/Manual mode 가시성 개선
  - Spacing 조정으로 레이아웃 개선

#### 5. QDialog → QWidget 변경
- **커밋**: 3de6ee7
- **변경 내용**: V4 settings를 QDialog에서 pure QWidget으로 변경
- **이유**: CSS 적용 문제 해결

#### 6. CSS Cascade 문제 수정
- **커밋**: de449d5
- **변경 내용**: QGroupBox styling을 방해하는 CSS cascade 문제 수정

#### 7. Scrollable Area 추가
- **커밋**: 0b25bd3
- **변경 내용**: V4/Expert widgets에 scrollable area 추가 및 spacing 수정

#### 8. GUI 렌더링 전면 개편
- **커밋**: ae17f29
- **변경 내용**: Borders, spacing, layout 전면 개편
- **영향**: 전체 GUI 렌더링 품질 향상

#### 9. 임시 파일 정리
- **커밋**: e62f958
- **변경 내용**: 임시 스크린샷 파일 제거

#### 10. 기타 업로드 커밋
- **커밋**: 1195b26, 7326935, 9805b7c, fd57b2b
- **내용**: 파일 업로드 (웹 인터페이스 사용으로 추정)

---

## 🔍 오늘 발견한 문제 및 분석

### 1. 외부 매수 감지 문제 (BalancePollingManager)

**발견 경위**:
- 사용자가 "group_2에 XRP가 있는데 Upbit 앱에서 수동 매수하면 group_2로 나와야 하는가?" 질문
- 조사 결과: 항상 `group_null`로 생성됨 발견

**원인**:
- `core/balance_polling_manager.py:177-183`
- `group_id="group_null"` 하드코딩됨
- Config를 받지 않아서 그룹 매핑 불가능

**현재 동작**:
```python
self.position_manager.create_position(
    group_id="group_null",  # ← 하드코딩!
    symbol=symbol,
    buy_price=avg_buy_price,
    quantity=total
)
```

**예상 동작**:
1. Upbit 앱에서 XRP 매수
2. BalancePollingManager 감지 (1초 간격)
3. group_2에 XRP 있음 확인
4. group_2로 포지션 생성
5. DCA/익절/손절 즉시 적용 가능

**실제 동작**:
1. Upbit 앱에서 XRP 매수
2. BalancePollingManager 감지
3. **group_null로 포지션 생성** ❌
4. DCA/익절/손절 적용 안 됨
5. 프로그램 재시작 → `sync_with_upbit()` → group_2로 업데이트

---

### 2. DCA 중복 실행 버그 (Critical!)

**발견 경위**:
- 사용자가 실제로 DCA가 중복 실행되는 버그 경험
- "WebSocket 확인까지 하는데도 중복 실행될 수 있나?" 질문
- 코드 분석 결과: Race Condition은 아니었으나, 다른 원인 발견

**초기 분석 (잘못됨)**:
- Race Condition 가능성 제기
- File I/O 지연으로 `pending_order`가 저장되기 전에 다음 루프 실행 가능하다고 분석

**재분석 (정확함)**:
- PositionManager는 **메모리 우선 아키텍처**
- `self.positions` dict에 먼저 저장 → 파일 저장은 나중
- `get_position()`은 메모리에서 읽음 (파일 I/O 없음)
- **Race Condition은 불가능!**

**실제 원인 발견**:
```python
# 현재 흐름 (v4_trading_engine.py:1026-1073)

Line 938: if pending_order: return  # ← 체크
         ↓ (없으면 통과)

Line 1028: order_result = self.upbit_api.buy_market_order(...)  # ← REST API 호출 (500ms~2초)
         ↓
         ↓ ⚠️ GAP! 이 사이에 프로그램 크래시 가능!
         ↓

Line 1047: self.position_manager.update_position(symbol, {
               "pending_order": {...}  # ← 이제야 저장
           })
```

**중복 실행 시나리오**:
1. DCA 레벨 0 조건 만족 → 체크 통과
2. REST API 호출 시작 (500ms~2초 소요)
3. **프로그램 크래시** ❌ (Ctrl+C, 시스템 오류 등)
4. `pending_order` 저장 안 됨
5. 주문은 Upbit에서 체결됨
6. 프로그램 재시작
7. `pending_order` 없음 → 레벨 0 조건 다시 체크 → 만족
8. **중복 실행!**

**또 다른 시나리오 (60초 루프)**:
```
00:00:00 - 레벨 0 조건 만족, pending_order 체크 (None)
00:00:01 - REST API 호출 시작 (2초 소요 예정)
00:01:00 - 다음 루프 시작, pending_order 체크 (아직 None!)
00:01:01 - 중복 실행!
00:00:03 - pending_order 저장 완료 (너무 늦음)
```

---

### 3. pending_order 영구 블록 문제

**발견 경위**:
- DCA 중복 방지 메커니즘 분석 중 발견
- WebSocket 콜백 실패 시 영구 블록 가능성 확인

**시나리오 A: WebSocket 콜백 등록 실패**
```python
# v4_trading_engine.py:1063-1067

# pending_order 저장 완료
self.position_manager.update_position(symbol, {
    "pending_order": {...}
})

# MyOrderWebSocket 연결 끊김
if self.myorder_ws:
    self.myorder_ws.register_order_callback(...)  # ← 실패!
else:
    logger.warning("⚠️ MyOrderWebSocket 없음")  # ← Warning만 출력
```

**결과**:
- 주문은 Upbit에서 체결됨
- 콜백을 못 받음
- `pending_order`는 영구히 남아 있음
- 다음 DCA/익절/손절이 모두 블록됨 (Line 938-941)
- **해당 코인의 모든 자동 실행 중단!**

**시나리오 B: 주문 취소/방지 이벤트 누락**
```python
# DCA 주문 생성 (state='wait')
order_uuid = "abc-123"
pending_order = {...}

# Upbit에서 주문 자동 취소 (잔고 부족 발생)
# WebSocket 이벤트 누락 (네트워크 문제 등)

# pending_order 영구 보존 → 모든 실행 중단!
```

**현재 문제**:
- `pending_order`에 `timestamp` 저장은 하지만 확인 안 함 (Line 1052)
- 5분, 10분 지나도 계속 대기
- Timeout 메커니즘 없음

---

### 4. 프로그램 재시작 시 pending_order 미처리

**발견 경위**:
- DCA 중복 실행 원인 분석 중 발견
- `sync_with_upbit()` 코드 검토

**현재 로직**:
```python
# position_manager.py:546-551

def sync_with_upbit(self, config, accounts):
    # 그룹 변경은 감지
    if current_group_id != old_group_id:
        updates['group_id'] = current_group_id

    # pending_order 체크 없음!
```

**시나리오**:
1. DCA 레벨 0 주문 실행 → `pending_order` 저장
2. 프로그램 강제 종료 (Ctrl+C)
3. 주문은 Upbit에서 체결 완료
4. 프로그램 재시작 → `sync_with_upbit()` 호출
5. 보유 수량은 업데이트됨 (1.0 → 1.5 BTC)
6. **하지만 `pending_order`는 그대로!**
7. **`dca_count` 증가 안 됨! (여전히 0)**
8. 다음 루프에서 레벨 0 조건 다시 체크
9. 조건 만족 → **중복 실행!**

**영향**:
- 사용자가 경험한 DCA 중복 실행 버그의 **가장 유력한 원인**
- 프로그램 재시작 시마다 발생 가능

---

### 5. Dry-run 모드 버그 (level 파라미터 누락)

**발견 경위**:
- DCA 실행 코드 분석 중 발견
- Live 모드와 Dry-run 모드 비교

**위치**: `v4_trading_engine.py:1002-1007`

**현재 코드**:
```python
# Dry-run 모드
self.position_manager.add_dca(
    symbol=symbol,
    dca_price=current_price,
    dca_amount=dca_quantity,
    dca_value_krw=dca_amount  # ← level 파라미터 없음!
)

# Live 모드 (Line 1443-1449)
self.position_manager.add_dca(
    symbol=symbol,
    dca_price=dca_price,
    dca_amount=dca_amount,
    dca_krw=dca_value_krw,
    level=level_index  # ← 있음!
)
```

**시그니처**:
```python
# position_manager.py:294
def add_dca(self, symbol, dca_price, dca_amount, dca_krw, level):
    #                                                      ↑ 필수!
```

**영향**:
- Dry-run 모드에서 TypeError 발생 가능
- 또는 level=None으로 저장되어 DCA 레벨 추적 불가능

---

### 6. Config 리로드 비효율성

**발견 경위**:
- "config 파일을 60초마다 읽기보다는 필요할 때 읽는 방법은 없을까?" 질문
- 조사 결과: 60초 폴링 자체가 없었고, `sync_with_upbit()`는 startup 시 1회만 호출됨

**현재 상황**:
```python
# v4_trading_engine.py:219-223

# startup 시 1회만 호출
sync_result = self.position_manager.sync_with_upbit(
    self.config,
    accounts=accounts
)

# 이후 호출 없음!
```

**문제**:
- 설정에서 그룹 변경 (BTC: group_1 → group_2)
- `sync_with_upbit()`가 호출되지 않음
- 그룹 변경 감지 안 됨
- **프로그램 재시작 전까지 업데이트 안 됨**

**기존 인프라**:
```python
# gui/main_window.py:2212
dialog.groups_changed.connect(self._on_groups_changed)

# gui/main_window.py:2224-2229
def _on_groups_changed(self):
    logger.info("📊 그룹 변경됨, 메인 윈도우 업데이트")
    self._load_v4_positions()
    self._add_log("✅ 그룹 설정이 업데이트되었습니다.")
    # ⚠️ V4TradingEngine에 알리지 않음!
```

**Signal 인프라는 있지만 연결 안 됨**:
- Qt Signal: `groups_changed` ✅ 있음
- MainWindow: `_on_groups_changed()` ✅ 있음
- V4TradingEngine: config reload 메서드 ❌ 없음
- PositionManager: group update 메서드 ❌ 없음

---

## 🔧 다음 세션에서 수정할 항목

### 🔴 필수 수정 (Critical Priority)

#### 1. pending_order 먼저 저장 (DCA 중복 실행 방지)

**목적**: 프로그램 크래시 시 중복 실행 방지

**적용 위치**:
1. `core/v4_trading_engine.py` - `_execute_dca()` (Line 1026-1073)
2. `core/v4_trading_engine.py` - `_execute_sell()` (Line 1228-1269)

**변경 내용**:

**Before (현재)**:
```python
# _execute_dca() Line 1027-1060
order_result = self.upbit_api.buy_market_order(symbol, dca_amount)  # ← REST API 먼저

if not order_result or 'error' in order_result:
    logger.error(f"❌ {symbol} DCA 실패: {order_result}")
    return

order_uuid = order_result.get('uuid')

# pending_order 저장 (나중)
self.position_manager.update_position(symbol, {
    "pending_order": {
        "order_id": order_uuid,
        "type": "dca",
        "level": dca_level_index,
        "timestamp": datetime.now().isoformat(),
        ...
    }
})
```

**After (개선)**:
```python
# _execute_dca() - 새 구조

# 1. pending_order 먼저 저장 (주문 전)
from datetime import datetime
self.position_manager.update_position(symbol, {
    "pending_order": {
        "type": "dca",
        "level": dca_level_index,
        "timestamp": datetime.now().isoformat(),
        "status": "preparing",  # 주문 준비 중
        "group_id": group_id,
        "group_name": group.get("name", "Unknown")
    }
})

logger.info(f"   📝 {symbol} DCA 레벨 {dca_level_num} pending_order 사전 저장 완료")

# 2. REST API 호출
try:
    order_result = self.upbit_api.buy_market_order(symbol, dca_amount)

    if not order_result or 'error' in order_result:
        logger.error(f"❌ {symbol} DCA 실패: {order_result}")
        # 실패 시 pending_order 제거
        self.position_manager.update_position(symbol, {
            "pending_order": None
        })
        return

    order_uuid = order_result.get('uuid')
    if not order_uuid:
        logger.error(f"❌ {symbol} 주문 UUID 없음: {order_result}")
        # 실패 시 pending_order 제거
        self.position_manager.update_position(symbol, {
            "pending_order": None
        })
        return

    executed_volume = float(order_result.get('executed_volume', 0))
    avg_price = float(order_result.get('avg_price', 0))

    logger.info(f"   📝 {symbol} DCA 주문 생성: {order_uuid[:8]}... (수량: {executed_volume:.8f})")

    # 3. pending_order 업데이트 (order_id 추가)
    self.position_manager.update_position(symbol, {
        "pending_order": {
            "order_id": order_uuid,
            "type": "dca",
            "level": dca_level_index,
            "timestamp": datetime.now().isoformat(),
            "status": "waiting",  # 체결 대기
            "dca_price": avg_price,
            "dca_amount": executed_volume,
            "dca_value_krw": dca_amount,
            "group_id": group_id,
            "group_name": group.get("name", "Unknown")
        }
    })

    # 4. WebSocket 콜백 등록
    if self.myorder_ws:
        self.myorder_ws.register_order_callback(order_uuid, self._on_order_completed)
        logger.info(f"   📡 {symbol} DCA 주문 {order_uuid[:8]}... 콜백 등록 완료")
    else:
        logger.warning(f"   ⚠️ {symbol} MyOrderWebSocket 없음 (콜백 등록 불가)")

    logger.info(f"   ⏳ {symbol} DCA 레벨 {dca_level_num} 주문 대기 중...")

except Exception as e:
    logger.error(f"❌ {symbol} DCA 실행 오류: {e}", exc_info=True)
    # 예외 발생 시 pending_order 제거
    self.position_manager.update_position(symbol, {
        "pending_order": None
    })
```

**동일한 패턴을 _execute_sell()에도 적용**:
```python
# _execute_sell() Line 1228-1269

# 1. pending_order 먼저 저장
self.position_manager.update_position(symbol, {
    "pending_order": {
        "type": reason,  # "profit" or "loss"
        "level": level_index,
        "timestamp": datetime.now().isoformat(),
        "status": "preparing"
    }
})

# 2. REST API 호출
try:
    order_result = self.upbit_api.sell_market_order(symbol, sell_amount)

    if not order_result or 'error' in order_result:
        # 실패 시 pending_order 제거
        self.position_manager.update_position(symbol, {"pending_order": None})
        return

    # 3. pending_order 업데이트
    # 4. WebSocket 콜백 등록

except Exception as e:
    # 예외 시 pending_order 제거
    self.position_manager.update_position(symbol, {"pending_order": None})
```

**효과**:
- ✅ 프로그램 크래시 시 중복 실행 방지
- ✅ 60초 루프 중복 실행 방지
- ✅ 주문 실패 시 자동 정리

**테스트 시나리오**:
1. DCA 트리거 → pending_order 저장 → 프로그램 강제 종료 (Ctrl+C)
2. 재시작 → pending_order 발견 → 스킵 확인
3. REST API 실패 → pending_order 제거 확인

---

#### 2. pending_order Timeout 메커니즘 추가

**목적**: WebSocket 콜백 실패 시 영구 블록 방지

**적용 위치**:
1. `core/v4_trading_engine.py` - `_check_dca_trigger()` (Line 938-941)
2. `core/v4_trading_engine.py` - `_check_profit_target()` (Line 1089-1093)
3. `core/v4_trading_engine.py` - `_check_stop_loss()` (Line 1138-1142)

**변경 내용**:

**Before (현재)**:
```python
# Line 938-941
pending_order = position.get("pending_order")
if pending_order:
    logger.debug(f"   ⏳ {symbol}: DCA 스킵 (진행 중인 주문: {pending_order.get('type')} 레벨 {pending_order.get('level')})")
    return
```

**After (개선)**:
```python
from datetime import datetime

# pending_order 체크 및 Timeout 확인
pending_order = position.get("pending_order")
if pending_order:
    timestamp_str = pending_order.get('timestamp')

    if timestamp_str:
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            elapsed = (datetime.now() - timestamp).total_seconds()

            # 5분(300초) 이상 대기 중이면 자동 제거
            if elapsed > 300:
                logger.warning(
                    f"⚠️ {symbol} pending_order timeout "
                    f"(경과: {elapsed:.0f}초, 타입: {pending_order.get('type')}, "
                    f"레벨: {pending_order.get('level')}) → 제거 및 재시도"
                )
                self.position_manager.update_position(symbol, {
                    "pending_order": None
                })

                # Telegram 알림
                self._send_telegram_alert(
                    f"⚠️ pending_order Timeout\n"
                    f"코인: {symbol}\n"
                    f"타입: {pending_order.get('type')}\n"
                    f"레벨: {pending_order.get('level')}\n"
                    f"경과 시간: {elapsed:.0f}초\n"
                    f"자동 제거 후 재시도합니다."
                )

                # 계속 진행 (재시도)
            else:
                # 정상 대기 중
                logger.debug(
                    f"   ⏳ {symbol}: DCA 스킵 "
                    f"(진행 중인 주문: {pending_order.get('type')} 레벨 {pending_order.get('level')}, "
                    f"경과: {elapsed:.0f}초)"
                )
                return  # 스킵

        except ValueError as e:
            # timestamp parsing 실패
            logger.error(f"⚠️ {symbol} pending_order timestamp 파싱 실패: {e}")
            # timestamp가 잘못되었으면 제거
            self.position_manager.update_position(symbol, {
                "pending_order": None
            })
            # 계속 진행 (재시도)
    else:
        # timestamp 없음 (오래된 데이터)
        logger.warning(f"⚠️ {symbol} pending_order에 timestamp 없음 → 제거")
        self.position_manager.update_position(symbol, {
            "pending_order": None
        })
        # 계속 진행 (재시도)
```

**동일한 로직을 3곳에 모두 적용**:
- `_check_dca_trigger()` Line 938-941
- `_check_profit_target()` Line 1089-1093
- `_check_stop_loss()` Line 1138-1142

**효과**:
- ✅ WebSocket 콜백 실패 시 5분 후 자동 복구
- ✅ 주문 취소/방지 이벤트 누락 시 자동 복구
- ✅ Telegram 알림으로 사용자에게 이상 상황 통보

**테스트 시나리오**:
1. DCA 주문 생성 → MyOrderWebSocket 강제 종료
2. 5분 대기 → Timeout 발생 확인
3. pending_order 제거 및 재시도 확인
4. Telegram 알림 수신 확인

---

#### 3. Dry-run 모드 level 파라미터 추가

**목적**: Dry-run 모드에서 DCA 레벨 정상 추적

**적용 위치**: `core/v4_trading_engine.py` - `_execute_dca()` (Line 1002-1007)

**변경 내용**:

**Before (현재)**:
```python
# Line 1002-1007 (Dry-run 모드)
self.position_manager.add_dca(
    symbol=symbol,
    dca_price=current_price,
    dca_amount=dca_quantity,
    dca_value_krw=dca_amount
    # level 파라미터 없음!
)
```

**After (개선)**:
```python
# Line 1002-1007 (Dry-run 모드)
self.position_manager.add_dca(
    symbol=symbol,
    dca_price=current_price,
    dca_amount=dca_quantity,
    dca_krw=dca_amount,  # dca_value_krw → dca_krw (파라미터명 일치)
    level=dca_level_index  # ← 추가!
)
```

**효과**:
- ✅ Dry-run 모드에서 TypeError 방지
- ✅ DCA 레벨 정상 추적
- ✅ Live 모드와 동일한 동작

**테스트 시나리오**:
1. Dry-run 모드로 실행
2. DCA 트리거 → 정상 실행 확인
3. `dca_history`에 level 정보 저장 확인

---

### 🟠 권장 수정 (High Priority)

#### 4. BalancePollingManager 그룹 매핑

**목적**: 외부 매수 시 올바른 그룹에 포지션 생성

**적용 위치**: `core/balance_polling_manager.py` (Line 177-183, __init__)

**변경 내용**:

**Step 1: __init__에 config 파라미터 추가**

**Before (현재)**:
```python
# balance_polling_manager.py

class BalancePollingManager:
    def __init__(self, upbit_api, position_manager):
        self.upbit_api = upbit_api
        self.position_manager = position_manager
        # config 없음!
```

**After (개선)**:
```python
class BalancePollingManager:
    def __init__(self, upbit_api, position_manager, config):
        self.upbit_api = upbit_api
        self.position_manager = position_manager
        self.config = config  # ← 추가!
```

**Step 2: create_position 호출 시 그룹 동적 결정**

**Before (현재)**:
```python
# Line 177-183
self.position_manager.create_position(
    group_id="group_null",  # ← 하드코딩!
    symbol=symbol,
    buy_price=avg_buy_price,
    quantity=total
)
```

**After (개선)**:
```python
# Line 177-183
# 1. 그룹 찾기 (PositionManager의 _find_group_for_coin 사용)
group_id = self.position_manager._find_group_for_coin(symbol, self.config)

# 2. 그룹이 없으면 group_null 사용
if not group_id:
    group_id = "group_null"
    logger.info(f"   📝 {symbol} 그룹 없음 → group_null로 설정")
else:
    logger.info(f"   📝 {symbol} 외부 매수 감지 → {group_id}로 포지션 생성")

# 3. 포지션 생성
self.position_manager.create_position(
    group_id=group_id,  # ← 동적으로 결정!
    symbol=symbol,
    buy_price=avg_buy_price,
    quantity=total
)
```

**Step 3: V4TradingEngine에서 config 전달**

**호출 위치 찾기**:
```bash
# 검색 필요
grep -n "BalancePollingManager(" core/v4_trading_engine.py
```

**예상 위치**: `core/v4_trading_engine.py`의 `__init__` 또는 `start()`

**Before**:
```python
self.balance_polling_manager = BalancePollingManager(
    upbit_api=self.upbit_api,
    position_manager=self.position_manager
)
```

**After**:
```python
self.balance_polling_manager = BalancePollingManager(
    upbit_api=self.upbit_api,
    position_manager=self.position_manager,
    config=self.config  # ← 추가!
)
```

**Step 4: Config 변경 시 BalancePollingManager 업데이트**

**새 메서드 추가** (`balance_polling_manager.py`):
```python
def update_config(self, config):
    """Config 업데이트 (설정 변경 시 호출)"""
    self.config = config
    logger.info("✅ BalancePollingManager config 업데이트 완료")
```

**호출** (`v4_trading_engine.py`의 `reload_config_and_update_groups()`):
```python
def reload_config_and_update_groups(self):
    """설정 변경 시 config 리로드 및 그룹 업데이트"""
    logger.info("🔄 Config 리로드 중...")
    self.config = self.config_manager.load_config()

    # 포지션 그룹 업데이트
    self.position_manager.update_position_groups_from_config(self.config)

    # BalancePollingManager 업데이트
    if self.balance_polling_manager:
        self.balance_polling_manager.update_config(self.config)

    logger.info("✅ Config 리로드 완료")
```

**효과**:
- ✅ Upbit 앱/웹에서 매수 → 올바른 그룹에 포지션 생성
- ✅ DCA/익절/손절 즉시 적용 가능
- ✅ 프로그램 재시작 불필요

**테스트 시나리오**:
1. group_2에 XRP 설정 (수동 매수 모드)
2. Upbit 앱에서 XRP 매수
3. 1초 후 BalancePollingManager 감지
4. group_2로 포지션 생성 확인
5. DCA/익절/손절 적용 확인

---

#### 5. Config 리로드 메커니즘 (Signal 기반)

**목적**: 설정 변경 즉시 반영 (프로그램 재시작 불필요)

**적용 위치**:
1. `core/v4_trading_engine.py` - 새 메서드 추가
2. `core/position_manager.py` - 새 메서드 추가
3. `gui/main_window.py` - Signal 연결

**변경 내용**:

**Step 1: V4TradingEngine.reload_config_and_update_groups() 추가**

**위치**: `core/v4_trading_engine.py` (새 메서드)

```python
def reload_config_and_update_groups(self):
    """
    설정 변경 시 config 리로드 및 그룹 업데이트

    MainWindow의 groups_changed Signal에서 호출됨
    API 호출 없이 메모리 기반 업데이트만 수행
    """
    logger.info("🔄 Config 리로드 중...")

    try:
        # 1. Config 파일 다시 로드
        self.config = self.config_manager.load_config()
        logger.info("   📄 Config 파일 로드 완료")

        # 2. 포지션 그룹 업데이트 (API 호출 없음)
        self.position_manager.update_position_groups_from_config(self.config)
        logger.info("   📊 포지션 그룹 업데이트 완료")

        # 3. BalancePollingManager 업데이트
        if hasattr(self, 'balance_polling_manager') and self.balance_polling_manager:
            self.balance_polling_manager.update_config(self.config)
            logger.info("   🔄 BalancePollingManager config 업데이트 완료")

        logger.info("✅ Config 리로드 완료 (재시작 불필요)")

        # 4. Telegram 알림
        self._send_telegram_alert(
            "✅ 설정 변경 적용 완료\n"
            "그룹 설정이 즉시 반영되었습니다."
        )

    except Exception as e:
        logger.error(f"❌ Config 리로드 실패: {e}", exc_info=True)
        self._send_telegram_alert(
            f"⚠️ 설정 변경 적용 실패\n"
            f"오류: {e}\n"
            f"프로그램을 재시작해주세요."
        )
```

**Step 2: PositionManager.update_position_groups_from_config() 추가**

**위치**: `core/position_manager.py` (새 메서드)

```python
def update_position_groups_from_config(self, config):
    """
    Config 기반으로 포지션 그룹 업데이트

    API 호출 없이 메모리 내 포지션의 group_id만 업데이트
    설정 변경 시 즉시 반영용

    Args:
        config: 새로운 config dict
    """
    logger.info("🔄 Config 기반 포지션 그룹 업데이트 시작")

    updated_count = 0

    for symbol, position in self.positions.items():
        # active 포지션만 대상
        if position.get('status') != 'active':
            continue

        # 현재 config에서 그룹 찾기
        current_group_id = self._find_group_for_coin(symbol, config)
        old_group_id = position.get('group_id')

        # 그룹 변경 감지
        if current_group_id and current_group_id != old_group_id:
            self.update_position(symbol, {'group_id': current_group_id})
            logger.info(f"   🔄 {symbol} 그룹 변경: {old_group_id} → {current_group_id}")
            updated_count += 1

        # 그룹에서 제거됨 (config에 없음)
        elif not current_group_id and old_group_id != "group_null":
            self.update_position(symbol, {'group_id': "group_null"})
            logger.info(f"   ⚠️ {symbol} 그룹 제거됨: {old_group_id} → group_null")
            updated_count += 1

    if updated_count > 0:
        logger.info(f"✅ {updated_count}개 포지션 그룹 업데이트 완료")
    else:
        logger.info("✅ 그룹 변경 없음")

    return updated_count
```

**Step 3: MainWindow._on_groups_changed() 연결**

**위치**: `gui/main_window.py:2224-2229`

**Before (현재)**:
```python
def _on_groups_changed(self):
    logger.info("📊 그룹 변경됨, 메인 윈도우 업데이트")
    self._load_v4_positions()
    self._add_log("✅ 그룹 설정이 업데이트되었습니다.")
    # V4TradingEngine에 알리지 않음!
```

**After (개선)**:
```python
def _on_groups_changed(self):
    logger.info("📊 그룹 변경됨, 메인 윈도우 업데이트")

    # 1. GUI 업데이트
    self._load_v4_positions()
    self._add_log("✅ 그룹 설정이 업데이트되었습니다.")

    # 2. V4TradingEngine 리로드 (거래 중인 경우)
    if hasattr(self, 'v4_engine') and self.v4_engine:
        try:
            self.v4_engine.reload_config_and_update_groups()
            logger.info("   ✅ V4TradingEngine config 리로드 완료")
        except Exception as e:
            logger.error(f"   ❌ V4TradingEngine config 리로드 실패: {e}")
            self._add_log(f"⚠️ 설정 적용 실패: {e}")
    else:
        logger.info("   ℹ️ V4TradingEngine 없음 (거래 중지 상태)")
```

**효과**:
- ✅ 설정 변경 즉시 반영 (재시작 불필요)
- ✅ 거래 중에도 그룹 변경 가능
- ✅ API 호출 없음 (메모리만 업데이트)
- ✅ Telegram 알림으로 확인 가능

**테스트 시나리오**:
1. 거래 시작 (BTC: group_1, XRP: group_2)
2. 설정에서 BTC를 group_2로 변경
3. 저장 → groups_changed Signal 발생
4. V4TradingEngine 리로드 확인
5. 포지션 그룹 변경 확인 (group_1 → group_2)
6. Telegram 알림 수신 확인
7. 다음 루프에서 group_2 설정 적용 확인

---

### 🟡 선택 수정 (Medium Priority)

#### 6. 프로그램 재시작 시 pending_order 정리

**목적**: 재시작 시 오래된 pending_order 자동 정리

**적용 위치**: `core/position_manager.py` - `sync_with_upbit()` (Line 546-651)

**변경 내용**:

**위치**: `sync_with_upbit()` 끝 부분 (Line 640 이후)

**추가 코드**:
```python
# sync_with_upbit() 끝 부분에 추가

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 오래된 pending_order 정리 (프로그램 재시작 시)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from datetime import datetime

cleaned_pending_orders = []

for symbol, position in self.positions.items():
    if position.get('status') != 'active':
        continue

    pending_order = position.get('pending_order')
    if not pending_order:
        continue

    timestamp_str = pending_order.get('timestamp')
    if not timestamp_str:
        # timestamp 없음 (오래된 데이터)
        self.update_position(symbol, {'pending_order': None})
        cleaned_pending_orders.append(f"{symbol} (timestamp 없음)")
        logger.warning(f"   🗑️ {symbol} pending_order 제거 (timestamp 없음)")
        continue

    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        elapsed = (datetime.now() - timestamp).total_seconds()

        # 5분(300초) 이상 경과
        if elapsed > 300:
            order_type = pending_order.get('type', 'unknown')
            level = pending_order.get('level', '?')

            self.update_position(symbol, {'pending_order': None})
            cleaned_pending_orders.append(
                f"{symbol} ({order_type} 레벨 {level}, {elapsed:.0f}초)"
            )
            logger.warning(
                f"   🗑️ {symbol} 오래된 pending_order 제거 "
                f"(타입: {order_type}, 레벨: {level}, 경과: {elapsed:.0f}초)"
            )

    except ValueError as e:
        # timestamp parsing 실패
        self.update_position(symbol, {'pending_order': None})
        cleaned_pending_orders.append(f"{symbol} (timestamp 파싱 실패)")
        logger.error(f"   🗑️ {symbol} pending_order 제거 (timestamp 파싱 실패: {e})")

if cleaned_pending_orders:
    print(f"\n   🗑️ 오래된 pending_order {len(cleaned_pending_orders)}개 정리:")
    for item in cleaned_pending_orders:
        print(f"      - {item}")

# return 문 (기존 코드)
return {
    "synced": synced_positions,
    "new": new_positions,
    "removed": removed_positions,
    "skipped": skipped_positions,
    "krw_balance": krw_balance,
    "cleaned_pending_orders": cleaned_pending_orders  # ← 추가
}
```

**효과**:
- ✅ 프로그램 재시작 시 오래된 pending_order 자동 정리
- ✅ 5분 이상 경과한 pending_order 제거
- ✅ timestamp 없거나 잘못된 경우 제거
- ✅ 로그로 정리 내역 확인 가능

**테스트 시나리오**:
1. DCA 주문 생성 → pending_order 저장
2. 프로그램 강제 종료
3. 6분 후 재시작
4. sync_with_upbit() 호출
5. pending_order 자동 제거 확인
6. 로그에 정리 메시지 확인

---

## 🎯 수정 우선순위 요약

| 번호 | 항목 | 우선순위 | 파일 | 라인 | 영향 |
|------|------|---------|------|------|------|
| 1 | pending_order 먼저 저장 | 🔴 필수 | v4_trading_engine.py | 1026-1073, 1228-1269 | DCA 중복 실행 방지 |
| 2 | Timeout 메커니즘 | 🔴 필수 | v4_trading_engine.py | 938-941, 1089-1093, 1138-1142 | 영구 블록 방지 |
| 3 | Dry-run level 파라미터 | 🔴 필수 | v4_trading_engine.py | 1002-1007 | Dry-run 정상화 |
| 4 | BalancePollingManager 그룹 매핑 | 🟠 권장 | balance_polling_manager.py | 177-183, __init__ | 외부 매수 그룹 매핑 |
| 5 | Config 리로드 Signal | 🟠 권장 | v4_trading_engine.py, position_manager.py, main_window.py | 새 메서드 | 설정 즉시 반영 |
| 6 | 재시작 시 pending 정리 | 🟡 선택 | position_manager.py | 640 이후 | 안정성 향상 |

---

## 📝 중요 개념 정리 (다음 세션 참고)

### DCA 순차 실행의 의미

**사용자가 원하는 "순차 실행"**:
```
레벨 0 주문 → 체결 완료 대기 → 레벨 1 주문 → 체결 완료 대기 → 레벨 2 주문
```

**예시 (급락 -50%)**:
```
초기:
- 평단가: 100,000원
- 가격: 50,000원 (급락!)
- 수익률: -50%

DCA 레벨:
- 레벨 0: -2% (98,000원)
- 레벨 1: -3% (97,000원)
- 레벨 2: -4% (96,000원)

실행:
1. 레벨 0 실행 → 체결 → 평단가: 75,000원, 수익률: -33%
2. 레벨 1 실행 → 체결 → 평단가: 65,000원, 수익률: -23%
3. 레벨 2 실행 → 체결 → 평단가: 58,000원, 수익률: -14%
   ↑ 평단가가 개선되어도 급락이 워낙 커서 조건 계속 만족
```

**현재 구현은 정확히 이 방식으로 동작함** ✅

**중요**:
- 평단가를 무시하는 게 아님
- 매 루프마다 조건을 다시 체크함
- 급락이 충분히 크면 평단가 개선되어도 모든 레벨 실행됨

### 레벨별 플래그 vs 전체 락

**전체 락 방식 (현재 구현)**:
- `pending_order` 하나로 모든 레벨 블록
- 순차 실행 보장
- 잔고 관리 안전
- 평단가 계산 단순

**레벨별 플래그 방식 (사용자 초기 제안)**:
- 각 레벨마다 개별 플래그
- 병렬 실행 가능
- 급락 시 빠른 대응
- 하지만 잔고/평단가 문제 발생 가능

**결론**: 전체 락 방식 + Timeout으로 충분

---

## 🚀 다음 세션 작업 순서

1. **🔴 필수 수정 (1-3번)** 먼저 완료
   - pending_order 먼저 저장
   - Timeout 메커니즘
   - Dry-run level 파라미터

2. **테스트** (각 수정마다)
   - Dry-run 모드 테스트
   - 프로그램 강제 종료 테스트
   - Timeout 테스트

3. **🟠 권장 수정 (4-5번)** 진행
   - BalancePollingManager 그룹 매핑
   - Config 리로드 Signal

4. **통합 테스트**
   - 전체 시나리오 테스트
   - 사용자 환경에서 검증

5. **🟡 선택 수정 (6번)** (시간 있으면)
   - 재시작 시 pending 정리

---

## 📌 중요 참고 사항

### 파일 위치
- V4TradingEngine: `core/v4_trading_engine.py`
- PositionManager: `core/position_manager.py`
- BalancePollingManager: `core/balance_polling_manager.py`
- MainWindow: `gui/main_window.py`

### 현재 브랜치
- `claude/expert-strategy-clone-01ELiN8eY3EZwEi2gSx4xARg`

### 테스트 환경
- 반드시 Dry-run 모드로 먼저 테스트
- 프로그램 강제 종료 시나리오 필수 테스트
- WebSocket 연결 끊김 시나리오 테스트

### 안전 조치
- 모든 수정에 try-except 추가
- Telegram 알림으로 이상 상황 통보
- 로그 레벨 DEBUG로 상세 기록

---

**작성일**: 2025-01-14
**세션**: GUI 개선 및 DCA 버그 분석
**다음 세션**: DCA 버그 수정 및 Config 리로드 구현
