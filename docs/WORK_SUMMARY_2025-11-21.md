# 작업 요약: 2025-11-21

**브랜치**: `claude/backup-copy-v5-01D7wSJvmTSBJHUXPcTmhaTA`
**작업 시간**: 2025-11-21
**상태**: ✅ 5개 주요 수정 완료, 1개 추가 작업 필요

---

## 📋 목차

1. [완료된 작업 (6개 커밋)](#완료된-작업)
2. [테스트 필요 항목](#테스트-필요-항목)
3. [진행 중 작업 (미완료)](#진행-중-작업)
4. [다음 세션 작업 가이드](#다음-세션-작업-가이드)

---

## ✅ 완료된 작업

### 1️⃣ Critical 버그 3개 수정 (178b956)

**파일**: `core/v4_trading_engine.py`, `core/telegram_bot.py`, `core/position_manager.py`

#### Bug #1: ERA 익절 무한반복 (594회 트리거)
**증상:**
- ERA 익절 레벨 1이 22:16:17부터 계속 반복 트리거
- 포지션이 삭제되었다가 재생성되면서 `profit_levels_executed` 초기화

**원인:**
```python
# Line 1609, 2039, 2177, 2270
self.position_manager.close_position(symbol)  # ❌ 파라미터 누락
```

**수정:**
```python
self.position_manager.close_position(symbol, close_price=avg_price, close_reason=reason)
```

4곳 모두 수정:
- Line 1609: Dry-run 모드
- Line 2039: state=cancel profit/loss
- Line 2177: state=done profit
- Line 2270: state=done loss

---

#### Bug #2: 텔레그램 메시지 50% 발송 실패
**증상:**
- 10건 중 5건 발송 실패
- `RuntimeError('Event loop is closed')`

**원인:**
- asyncio 이벤트 루프가 닫힌 상태에서 메시지 발송 시도

**수정 (1차):**
```python
# core/telegram_bot.py Line 98-105
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    # 새로운 이벤트 루프 생성
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
```

**추가 수정 (2차 - 26ea03e):**
```python
# Line 100-108
try:
    loop = asyncio.get_running_loop()
    # 루프가 닫혀있으면 새로 생성
    if loop.is_closed():
        raise RuntimeError("Loop is closed")
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
```

---

#### Bug #3: 평균가 오차 (+0.4% ~ +1.03%)
**증상:**
- SOL: +2,172원
- XRP: +31.3원
- GRS: +1원

**원인:**
- MyAsset WebSocket이 MyOrder보다 0.01초 빠르게 도착
- REST API로 부정확한 평균가 덮어쓰기

**수정:**
```python
# core/position_manager.py Line 768-815
# recent_dca 윈도우 10초 → 20초로 증가
if (datetime.now() - last_dca_time).total_seconds() < 20:
    recent_dca = True

# 외부 매수 감지 시 3초 대기 후 재체크
logger.warning(f"   ⚠️ [외부] {symbol} 수량 변동 감지, 3초 대기 후 REST API로 평균가 조회")
time.sleep(3)

# 대기 후 MyOrder 완료 여부 재확인
current_position_after_wait = self.get_position(symbol)
```

---

### 2️⃣ 평균 매수가 REST API 조회로 변경 (be983e6)

**배경:**
- 기존: 직접 계산 (수수료 미반영, 0.05~0.1% 오차)
- 변경: REST API 조회 (100% 정확, Upbit 서버 = Single Source of Truth)

**파일**: `core/v4_trading_engine.py`

#### 변경 1: state='trade' 실시간 업데이트
**위치**: Line 1897-1920

```python
# 부분 체결 처리 (state='trade')
if state == 'trade':
    logger.info(f"   💰 주문 {order_uuid[:8]}... 부분 체결 (수량: {executed_volume:.8f}, 가격: {trade_price:,.0f}원)")

    # 🆕 실시간 평균가 업데이트 (REST API 조회)
    position = self.position_manager.get_position(symbol)
    if position and self.upbit_api:
        try:
            accounts = self.upbit_api.get_accounts()
            for acc in accounts:
                currency = symbol.replace('KRW-', '')
                if acc['currency'] == currency:
                    new_avg_price = float(acc.get('avg_buy_price', 0))
                    new_balance = float(acc.get('balance', 0))

                    # 포지션 업데이트 (실시간)
                    self.position_manager.update_position(symbol, {
                        'total_amount': new_balance,
                        'avg_buy_price': new_avg_price,
                        'total_invested_krw': new_avg_price * new_balance
                    })

                    logger.info(f"   📊 [실시간] {symbol} 평균가 업데이트: {new_avg_price:,.0f}원 (수량: {new_balance:.8f}개)")
                    break
        except Exception as e:
            logger.error(f"❌ [실시간] {symbol} 평균가 조회 실패: {e}")

    return  # 최종 처리는 state='done'에서
```

**효과:**
- 부분 체결마다 평균가 실시간 업데이트
- GUI에서 "체결되고 있구나" 느낌 제공 ✨

---

#### 변경 2: 초기 매수 state='done'/'cancel' 최종 조회
**위치**: Line 1789-1804

```python
# 🆕 REST API로 정확한 평균가 조회
final_avg_price = avg_price  # fallback
final_balance = executed_volume  # fallback

if self.upbit_api:
    try:
        accounts = self.upbit_api.get_accounts()
        for acc in accounts:
            currency = symbol.replace('KRW-', '')
            if acc['currency'] == currency:
                final_avg_price = float(acc.get('avg_buy_price', 0))
                final_balance = float(acc.get('balance', 0))
                logger.info(f"   📊 [최종] {symbol} REST API 평균가: {final_avg_price:,.0f}원 (수량: {final_balance:.8f}개)")
                break
    except Exception as e:
        logger.error(f"❌ {symbol} REST API 평균가 조회 실패 (fallback to MyOrder): {e}")

# 포지션 생성
position = self.position_manager.create_position(
    group_id=pending_buy['group_id'],
    symbol=symbol,
    buy_price=final_avg_price,  # ✅ REST API 최종 평균가
    quantity=final_balance,
    buy_amount_krw=pending_buy['buy_amount_krw']
)
```

---

#### 변경 3: DCA state='cancel' 최종 조회
**위치**: Line 1978-2020

```python
# DCA 처리 (done과 동일)
dca_value_krw = pending_order.get('dca_value_krw', 0)
group_id = pending_order.get('group_id', 'unknown')
group_name = pending_order.get('group_name', 'Unknown')

logger.info(f"   ✅ {symbol} DCA 레벨 {level_index+1} 체결 완료 (state=cancel, MyOrder avg: {avg_price:,.0f}원, 수량: {executed_volume:.8f})")

# 🆕 REST API로 정확한 평균가 조회
final_avg_price = avg_price  # fallback
final_balance = 0  # fallback

if self.upbit_api:
    try:
        accounts = self.upbit_api.get_accounts()
        for acc in accounts:
            currency = symbol.replace('KRW-', '')
            if acc['currency'] == currency:
                final_avg_price = float(acc.get('avg_buy_price', 0))
                final_balance = float(acc.get('balance', 0))
                logger.info(f"   📊 [최종] {symbol} REST API 평균가: {final_avg_price:,.0f}원 (수량: {final_balance:.8f}개)")
                break
    except Exception as e:
        logger.error(f"❌ {symbol} REST API 평균가 조회 실패 (fallback to MyOrder): {e}")

# DCA 히스토리 기록
dca_history = position.get('dca_history', [])
dca_record = {
    "level": level_index,
    "price": avg_price,  # 체결가 기록
    "amount": executed_volume,
    "krw": dca_value_krw,
    "timestamp": datetime.now().isoformat()
}
dca_history.append(dca_record)

# 🔧 DCA 레벨 기록 (중복 방지)
dca_levels_executed.append(level_index)

# 포지션 업데이트
self.position_manager.update_position(symbol, {
    'total_amount': final_balance,
    'avg_buy_price': final_avg_price,
    'total_invested_krw': final_avg_price * final_balance,
    'dca_count': position.get('dca_count', 0) + 1,
    'dca_history': dca_history,
    'dca_levels_executed': dca_levels_executed,
    'pending_order': None
})
```

**중요 변경점:**
- `add_dca()` 메서드 사용 중지 ❌
- REST API 조회 + `update_position()` 직접 호출 ✅
- 계산 오차 완전 제거

---

#### 변경 4: DCA state='done' 최종 조회
**위치**: Line 2400-2447

state='cancel'과 동일한 로직 적용

---

### 3️⃣ create_position()에 dca_levels_executed 필드 추가 (53dd184)

**문제:**
- `create_position()`에서 `dca_levels_executed` 필드 누락
- 신규 포지션에 필드가 없어서 DCA 중복 방지 실패

**파일**: `core/position_manager.py`

**수정:**
```python
# Line 222-224
# V4 다중 레벨 익절/손절 추적 (11/12 추가)
"dca_levels_executed": [],     # 실행된 DCA 레벨 인덱스 [0, 1, 2, ...]
"profit_levels_executed": [],  # 실행된 익절 레벨 인덱스 [0, 1, 2, ...]
"loss_levels_executed": [],    # 실행된 손절 레벨 인덱스 [0, 1, ...]
```

**영향:**
- 신규 포지션: 자동으로 필드 포함 ✅
- 기존 포지션: `position.get('dca_levels_executed', [])` 로 자동 처리 ✅

---

### 4️⃣ 프로그램 시작/종료 시 텔레그램 알림 추가 (f5343dd)

**파일**: `core/v4_trading_engine.py`

#### 시작 알림 (Line 303-312)
```python
logger.info("✅ V4 거래 엔진 시작 완료")

# 텔레그램 시작 알림
mode_text = "Live (실거래)" if not self.dry_run else "Dry-run (가상)"

self._send_telegram_alert(
    f"🚀 프로그램 시작\n"
    f"모드: {mode_text}\n"
    f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
```

**메시지 예시:**
```
🚀 프로그램 시작
모드: Live (실거래)
시간: 2025-11-21 11:30:00
```

---

#### 종료 알림 (Line 367-371)
```python
logger.info("✅ V4 거래 엔진 중지 완료")

# 텔레그램 종료 알림
self._send_telegram_alert(
    f"🛑 프로그램 종료\n"
    f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
```

**메시지 예시:**
```
🛑 프로그램 종료
시간: 2025-11-21 15:30:00
```

---

### 5️⃣ 관찰 전용 모드 표시 제거 (e92c4e9)

**이유:**
- 관찰 모드는 그룹별 설정
- 전역 `observation_mode` 표시는 혼란스러움

**파일**: `core/v4_trading_engine.py`

**수정:**
```python
# Line 304-305 제거
# if self.observation_mode:
#     mode_text += " [관찰 전용]"
```

---

### 6️⃣ 텔레그램 Event Loop closed 상태 체크 추가 (26ea03e)

**문제:**
- `get_running_loop()` 성공해도 `loop.is_closed()`일 수 있음
- 닫힌 루프로 `send_message()` 호출 시 RuntimeError 발생

**파일**: `core/telegram_bot.py`

**수정:**
```python
# Line 100-108
try:
    loop = asyncio.get_running_loop()
    # 루프가 닫혀있으면 새로 생성
    if loop.is_closed():
        raise RuntimeError("Loop is closed")
except RuntimeError:
    # 이벤트 루프가 없거나 닫혔으면 새로 생성
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("🔄 텔레그램 봇: 새로운 이벤트 루프 생성")
```

**동작 흐름:**
1. 기존 루프 가져오기 시도
2. 성공 → `is_closed()` 체크
   - 닫혀있음 → 새 루프 생성 ✅
   - 열려있음 → 기존 루프 사용 ✅
3. 실패 → 새 루프 생성 ✅

---

## 🧪 테스트 필요 항목

### 1. 텔레그램 메시지 발송 성공률
**테스트 방법:**
```bash
# 프로그램 실행
python main.py

# 다음 이벤트 발생 시 텔레그램 확인:
1. 프로그램 시작 메시지 ✅
2. DCA 발생 시 메시지 ✅
3. 익절/손절 메시지 ✅
4. 프로그램 종료 메시지 ✅
```

**확인 사항:**
- [ ] 모든 메시지가 100% 발송되는지
- [ ] `RuntimeError('Event loop is closed')` 에러가 없는지

---

### 2. 평균가 정확성
**테스트 방법:**
```bash
# DCA 발생 시 로그 확인
tail -f logs/trading_*.log | grep "📊 \[최종\]"

# positions_live.json 확인
cat data/positions_live.json | jq '.["KRW-ETH"].avg_buy_price'

# Upbit 앱/웹과 비교
# - GUI 평균가
# - positions_live.json 평균가
# - Upbit 앱 평균가
```

**확인 사항:**
- [ ] GUI 평균가 = Upbit 앱 평균가 (100% 일치)
- [ ] positions_live.json 평균가 = Upbit 앱 평균가
- [ ] state='trade' 부분 체결 시 실시간 업데이트 확인

---

### 3. DCA 중복 방지
**테스트 방법:**
```bash
# 1. DCA 발생 전 positions_live.json 확인
cat data/positions_live.json | jq '.["KRW-ETH"].dca_levels_executed'
# 출력: []

# 2. DCA 발생 후 확인
cat data/positions_live.json | jq '.["KRW-ETH"].dca_levels_executed'
# 출력: [0]

# 3. 프로그램 재시작

# 4. 가격이 다시 -2%로 떨어졌을 때
# 로그에서 "이미 실행됨 → 중복 스킵" 메시지 확인
```

**확인 사항:**
- [ ] DCA 실행 시 `dca_levels_executed` 배열 업데이트
- [ ] 프로그램 재시작 후 중복 DCA 방지
- [ ] positions_live.json 즉시 업데이트

---

### 4. ERA 익절 무한반복 해결
**테스트 방법:**
```bash
# ERA 익절 발생 시 로그 확인
tail -f logs/trading_*.log | grep "ERA"

# 1회만 트리거되는지 확인
# "익절 레벨 X 트리거" 로그가 1번만 출력되어야 함
```

**확인 사항:**
- [ ] 익절 시 포지션 정상 종료
- [ ] `close_position()` 파라미터 정상 전달
- [ ] 무한반복 없음

---

## 🚧 진행 중 작업 (미완료)

### GUI 가격 표시 규칙 (Upbit 앱/웹 일치)

**배경:**
- Upbit 앱/웹은 가격대별로 다른 소수점 표시 규칙 사용
- 현재 GUI는 모든 가격을 소수점 2자리로 표시

**관찰된 규칙:**
```
100,000원 이상 → 정수로 표시
  예: 4,268,182.98 → 4,268,183

100,000원 미만 → 소수점 1자리
  예: 236.79 → 236.8
  예: 1,664.65 → 1,664.6  ← 반올림 아님! (미해결)
```

**미해결 문제:**
1. **반올림 규칙이 일관적이지 않음**
   - GRS: 236.79 → 236.8 (반올림 정상)
   - LSK: 290.99 → 291.0 (반올림 정상)
   - 0G: 1,664.65 → 1,664.6 (5인데 올리지 않음!) ❓

2. **가능한 설명:**
   - Banker's Rounding? (5일 때 짝수로 반올림)
   - 호가 단위 기준 버림?
   - Upbit 앱 표시 오류?

3. **추가 데이터 필요:**
   - ".5"로 끝나는 다른 평균가 케이스 확인
   - 1원 미만 가격대 표시 규칙 확인

**현재 상태:**
- 규칙 분석 중 (코드 수정 안함)
- 더 많은 데이터 필요

---

## 📝 다음 세션 작업 가이드

### 🎯 우선순위 1: GUI 가격 표시 규칙 완성

**목표:**
- Upbit 앱/웹과 100% 동일한 가격 표시

**Step 1: 규칙 확인**
```bash
# 다양한 가격대의 코인 확인
# - ".5"로 끝나는 평균가
# - 1원 미만 가격
# - 10원 미만 가격
```

**Step 2: 포맷팅 함수 작성**
```python
# gui/main_window.py 또는 utils.py
def format_price_for_display(price: float) -> str:
    """
    Upbit 웹/앱과 동일한 가격 표시 규칙

    - 100,000원 이상: 정수
    - 100,000원 미만: 소수점 1자리
    - (추가 규칙 확인 필요)
    """
    if price >= 100000:
        return f"{round(price):,}"
    else:
        # TODO: 반올림 규칙 확인 후 수정
        return f"{round(price, 1):,.1f}"
```

**Step 3: GUI 적용**
```python
# gui/main_window.py Line 2370-2371
QTableWidgetItem(self.format_price_for_display(average_price)),  # 평균가
QTableWidgetItem(self.format_price_for_display(current_price)),  # 현재가

# gui/main_window.py Line 2562 (실시간 업데이트)
price_item = QTableWidgetItem(self.format_price_for_display(current_price))
```

**Step 4: 테스트**
- [ ] GUI 평균가가 Upbit 앱과 100% 일치하는지
- [ ] 실시간 업데이트 시에도 포맷 유지되는지

---

### 🎯 우선순위 2: 프로그램 전체 테스트

**테스트 시나리오:**

1. **프로그램 시작**
   - [ ] 텔레그램 시작 메시지 수신
   - [ ] sync_with_upbit() 정상 동작
   - [ ] GUI에 포지션 정상 표시

2. **자동 매수**
   - [ ] state='trade' 실시간 평균가 업데이트 (로그 확인)
   - [ ] state='done' 최종 평균가 REST API 조회
   - [ ] positions_live.json 즉시 업데이트
   - [ ] GUI 평균가 = Upbit 앱 평균가

3. **DCA 실행**
   - [ ] state='trade' 실시간 업데이트
   - [ ] state='done'/'cancel' 최종 조회
   - [ ] `dca_levels_executed` 배열 업데이트
   - [ ] `dca_count` 증가
   - [ ] `dca_history` 기록
   - [ ] 텔레그램 알림 수신

4. **DCA 중복 방지**
   - [ ] 프로그램 재시작
   - [ ] 동일 레벨 중복 트리거 안됨
   - [ ] 로그에 "이미 실행됨 → 중복 스킵" 출력

5. **익절/손절**
   - [ ] 포지션 정상 종료
   - [ ] `close_position()` 파라미터 정상 전달
   - [ ] 무한반복 없음
   - [ ] 텔레그램 알림 수신

6. **프로그램 종료**
   - [ ] 텔레그램 종료 메시지 수신
   - [ ] 모든 포지션 데이터 저장 확인

---

### 📂 파일 위치 참고

**수정된 파일:**
```
core/v4_trading_engine.py        # 평균가 REST API 조회, 텔레그램 알림
core/telegram_bot.py             # Event Loop 수정
core/position_manager.py         # dca_levels_executed 필드 추가
```

**확인할 데이터 파일:**
```
data/positions_live.json         # 포지션 데이터
data/trade_history.json          # 거래 기록
config/trading_config.json       # DCA/익절/손절 설정
```

**로그 파일:**
```
logs/trading_*.log               # 메인 로그
```

---

### 💡 추가 참고 사항

**Rate Limit 상황:**
- state='trade' 부분 체결마다 REST API 조회 추가
- 시장가 주문: 평균 2~5회 부분 체결
- REST API 호출: 3~6회 (trade) + 1회 (done) = 최대 7회
- Rate Limit: 초당 30회 제한 → **충분함** ✅

**데이터 정확성:**
- 내부 저장: float 그대로 (4,268,182.98)
- GUI 표시: 포맷팅 (4,268,183)
- Upbit 앱: 포맷팅 (4,268,183)
- **저장 값 != 표시 값** (정상)

**DCA 동작:**
- 평균가 기준으로 DCA 트리거 계산
- 수동 매수는 평단가만 낮추고 `dca_levels_executed`에 기록 안됨
- 다음 DCA는 새로운 평단가 기준으로 정상 트리거

---

## 📞 문의 사항

다음 세션 시작 시 확인할 사항:
1. GUI 가격 표시 규칙 추가 데이터 수집 완료 여부
2. 전체 테스트 결과
3. 텔레그램 메시지 발송 성공률

---

**작성일**: 2025-11-21
**다음 업데이트**: 테스트 완료 후
