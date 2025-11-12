# 작업 세션 요약 (2025-11-12)

## 📋 오늘 완료한 작업

### 1. GUI 응답없음 문제 해결 ✅
**커밋**: `e703323 - fix: Resolve GUI freeze and enable profit-taking by fixing thread blocking`

**문제**:
- 시작 버튼 클릭 시 GUI 응답없음 발생
- 1초마다 REST API 호출하는 blocking 동작이 메인 스레드 차단

**해결**:
- `core/v4_trading_engine.py`의 blocking 호출을 background thread로 이동
- GUI 반응성 복구

---

### 2. 익절(Profit-taking) 동작 안 함 문제 해결 ✅
**커밋**: `ee55a10 - fix: Standardize field name to avg_buy_price across all modules`

**문제**:
- XRP 수익률 0.7%, 익절 설정 0.5%인데 매도 주문 안 나감
- 필드명 불일치: `position_manager.py`는 "average_price", `v4_trading_engine.py`는 "avg_buy_price" 읽음
- 결과: avg_buy_price = 0 → profit_pct = 100% (잘못된 계산)

**해결**:
- Upbit API 공식 문서 기준으로 "avg_buy_price"로 통일
- `core/position_manager.py`: 9군데 필드명 수정
  - Lines: 196, 217, 341, 540, 701, 716, 722, 941, 961

**테스트 결과** (유저 확인):
- ETH 0.68% 수익, 0.5% 익절 설정 → ✅ 정상 매도
- SOL 0.78% 수익, 0.5% 익절 설정 → ✅ 정상 매도
- "일단 1차매도로 해도 정상적으로 매도가 나가는건 확인했어"

---

### 3. 레벨 설정 소수점 표시 문제 해결 ✅
**커밋**: `f4b1ef4 - fix: Display decimal places in level settings dialog`

**문제**:
- 레벨 설정에서 0.5% 입력해도 0으로 표시됨
- 원인: `str(int(0.5))` = "0" (정수 변환으로 소수점 소실)

**해결**:
- `gui/level_settings_dialog.py` Lines 245, 268, 291
- `str(int(value))` → `f"{value:.1f}"` 변경
- 0.5 → "0.5" 정상 표시

---

### 4. DCA 필드명 불일치 문제 해결 ✅
**커밋**: `4001d21 - fix: Correct DCA field names to match level settings configuration`

**문제**:
- 0G 코인 -2.2% 손익, DCA 설정 -2% 100%인데 전혀 작동 안 함
- 코드는 "drop_pct", "buy_ratio" 읽음
- 설정 파일은 "price_ratio", "quantity_ratio" 저장

**해결**:
- `core/v4_trading_engine.py` Line 909, 934
  ```python
  # Before
  drop_pct = level.get("drop_pct", -5.0)
  buy_ratio = level.get("buy_ratio", 100) / 100.0

  # After
  price_ratio = level.get("price_ratio", -5.0)
  quantity_ratio = level.get("quantity_ratio", 100) / 100.0
  ```

---

### 5. DCA 계산 로직 변경 (최초 금액 → 현재 보유 금액 기준) ✅
**커밋**: `53069b5 - fix: Change DCA calculation to use current total investment instead of initial amount`

**유저 요청**:
- "내 생각에는 dca의 %는 현재 보유금액에 비례해서 설정하는게 맞는거같고"
- 수동 매수 6,000원 → DCA 100% = 6,000원 추가 (50,000원 아님)

**변경 사항**:

1. **DCA 계산 로직** (`core/v4_trading_engine.py` Lines 932-936):
```python
# Before: 고정된 초기 금액 기준
base_amount = auto_config["buy_amount_krw"]  # 항상 50,000원
dca_amount = int(base_amount * quantity_ratio)

# After: 현재 총 투자 금액 기준
total_invested = position.get("total_invested_krw", 50000)
quantity_ratio = level.get("quantity_ratio", 100) / 100.0
quantity_ratio = min(quantity_ratio, 1.0)  # 최대 100% 제한
dca_amount = int(total_invested * quantity_ratio)
```

2. **Auto-buy 파라미터명 수정** (Lines 775, 800):
```python
# Before
position = self.position_manager.create_position(
    buy_amount=executed_volume,      # 잘못된 파라미터명
    buy_value_krw=total_paid          # 잘못된 파라미터명
)

# After
position = self.position_manager.create_position(
    quantity=executed_volume,         # 올바른 파라미터명
    buy_amount_krw=total_paid         # 올바른 파라미터명
)
```

3. **GUI 설명 업데이트** (`gui/level_settings_dialog.py` Lines 83-86):
```python
desc_label = QLabel("💡 DCA (Dollar Cost Averaging): 가격이 하락할 때 추가 매수하여 평균 단가를 낮춥니다.\n"
                   "• 하락률: 최초 매수가 대비 하락 퍼센트 (예: -3, -5, -7)\n"
                   "• 수량 비율: 현재 보유 금액 대비 비율 (100 = 100%, 최대 100%)\n"
                   "  예) 2만원 보유 → 100% = 2만원 추가 → 총 4만원")
```

**시나리오 예시**:

**공격적 전략 (모두 100%)**:
- 초기: 20,000원
- DCA1 (-2%, 100%): 20,000 × 100% = +20,000원 → 총 40,000원
- DCA2 (-5%, 100%): 40,000 × 100% = +40,000원 → 총 80,000원
- DCA3 (-7%, 100%): 80,000 × 100% = +80,000원 → 총 160,000원

**보수적 전략 (감소하는 %)**:
- 초기: 20,000원
- DCA1 (-2%, 100%): 20,000 × 100% = +20,000원 → 총 40,000원
- DCA2 (-5%, 50%):  40,000 × 50%  = +20,000원 → 총 60,000원
- DCA3 (-7%, 33%):  60,000 × 33%  = +20,000원 → 총 80,000원

---

## ❌ 현재 남은 문제: DCA 순차 실행 안 됨

### 문제 상황

**유저 설정**:
- DCA 레벨 1: -1.0% / 100%
- DCA 레벨 2: -1.5% / 50%

**실제 상황**:
- 0G 코인 현재 손익률: -2.2%
- 보유 금액: 5,999원

**기대 동작**:
1. -2.2% → DCA1 실행 (-1.0% 트리거) → 5,999원 추가 → 총 11,998원
2. 평균 단가 개선 → 손익률 -1.1%로 회복
3. 가격 추가 하락 → -1.5% 도달
4. DCA2 실행 (-1.5% 트리거) → 5,999원 추가 (50% of 11,998) → 총 17,997원

**실제 동작**:
1. -2.2% → DCA1 실행 10번 이상 반복
2. DCA2 한 번도 실행 안 됨
3. `dca_count` = 0으로 계속 유지
4. `total_invested_krw` = 5,999원으로 계속 유지
5. 손익률 -2.2% 고정

### 로그 분석

```
🔔 KRW-0G: DCA 레벨 1 트리거 (현재: -2.52%, 기준: -1.00%)
💰 KRW-0G DCA 레벨 1 실행 중... (금액: 5,999원, 비율: 100% of 5,999원)
📬 주문 체결 이벤트 수신: KRW-0G 1d3f6fdc... state=wait
📬 주문 체결 이벤트 수신: KRW-0G 1d3f6fdc... state=trade  ← 부분 체결!
📬 주문 체결 이벤트 수신: KRW-0G 1d3f6fdc... state=cancel ← 나머지 취소
⚠️ 주문 1d3f6fdc... 취소됨 (state=cancel)
(10번 이상 반복...)
```

### 근본 원인

**Upbit 시장가 주문 동작**:
1. 시장가 주문 전송 → `state=wait`
2. 일부 체결됨 → `state=trade` (executed_volume > 0)
3. 미체결 부분 자동 취소 → `state=cancel`

**코드 문제**:

**파일**: `core/v4_trading_engine.py`
**메서드**: `_on_order_completed` (Lines 1253-1366)

**문제 지점 1** (Lines 1277-1279):
```python
# 완료되지 않은 주문은 무시
if state not in ['done', 'cancel', 'prevented']:
    logger.debug(f"   ⏳ 주문 {order_uuid[:8]}... 아직 진행 중 (state={state})")
    return  # ← state='trade' 여기서 무시됨!
```

**문제 지점 2** (Lines 1282-1290):
```python
# 취소/방지된 주문 처리
if state in ['cancel', 'prevented']:
    logger.warning(f"   ⚠️ 주문 {order_uuid[:8]}... 취소됨 (state={state})")
    # pending_order 필드 정리만 하고 return
    position = self.position_manager.get_position(symbol)
    if position and position.get('pending_order', {}).get('order_id') == order_uuid:
        self.position_manager.update_position(symbol, {
            'pending_order': None
        })
    return  # ← DCA add_dca() 호출 안 함!
```

**결과**:
- `state=trade` → 무시 (1279줄 return)
- `state=cancel` → pending_order만 제거하고 return (1290줄)
- `position_manager.add_dca()` 호출 안 됨
- `dca_count` 증가 안 됨
- `total_invested_krw` 업데이트 안 됨
- `profit_pct` 재계산 안 됨

**악순환**:
```
DCA 체크 → dca_count=0 → 항상 레벨 0 (첫 번째) 체크
         → -2.2% < -1.0% → 조건 만족
         → DCA1 실행 → state=trade → 무시
         → dca_count=0 유지 (업데이트 안 됨)
         → 다시 DCA 체크 → dca_count=0 → 무한 반복...
```

---

## 🔧 내일 작업할 내용

### 목표
DCA 순차 실행 문제 해결 (state=trade 처리 로직 추가)

### 수정할 파일
**1개 파일만 수정**: `core/v4_trading_engine.py`

### 수정할 메서드
`_on_order_completed` (Lines 1253-1366)

### 수정 방법

#### 현재 코드 구조
```python
def _on_order_completed(self, order_data: Dict):
    order_uuid = order_data.get('uuid')
    symbol = order_data.get('code')
    state = order_data.get('state')
    ask_bid = order_data.get('ask_bid')
    executed_volume = order_data.get('executed_volume', 0)
    avg_price = order_data.get('avg_price', 0)

    logger.info(f"📬 주문 체결 이벤트 수신: {symbol} {order_uuid[:8]}... state={state}")

    # 문제 1: state='trade' 무시
    if state not in ['done', 'cancel', 'prevented']:
        return  # ← 여기서 state='trade' 무시됨!

    # 문제 2: state='cancel' 처리 시 DCA 업데이트 안 함
    if state in ['cancel', 'prevented']:
        logger.warning(f"   ⚠️ 주문 {order_uuid[:8]}... 취소됨")
        # pending_order만 정리하고 return
        return  # ← DCA add_dca() 호출 안 됨!

    # state='done'만 여기 도달
    position = self.position_manager.get_position(symbol)
    pending_order = position.get('pending_order')
    order_type = pending_order.get('type')  # 'profit', 'loss', 'dca'
    level_index = pending_order.get('level')

    if order_type == 'dca':
        # DCA 추가 처리
        self.position_manager.add_dca(...)  # ← 여기 도달 안 함!
```

#### 수정 후 코드 구조
```python
def _on_order_completed(self, order_data: Dict):
    order_uuid = order_data.get('uuid')
    symbol = order_data.get('code')
    state = order_data.get('state')
    ask_bid = order_data.get('ask_bid')
    executed_volume = order_data.get('executed_volume', 0)
    avg_price = order_data.get('avg_price', 0)

    logger.info(f"📬 주문 체결 이벤트 수신: {symbol} {order_uuid[:8]}... state={state}")

    # 수정 1: state='wait'만 무시
    if state == 'wait':
        logger.debug(f"   ⏳ 주문 {order_uuid[:8]}... 아직 대기 중")
        return

    # 수정 2: state='trade' 처리 (부분 체결)
    if state == 'trade':
        logger.info(f"   💰 주문 {order_uuid[:8]}... 부분 체결 (수량: {executed_volume:.8f})")

        # executed_volume > 0이면 DCA 처리
        if executed_volume > 0:
            position = self.position_manager.get_position(symbol)
            if not position:
                return

            pending_order = position.get('pending_order')
            if not pending_order or pending_order.get('order_id') != order_uuid:
                return

            order_type = pending_order.get('type')

            # DCA 주문이면 add_dca() 호출
            if order_type == 'dca':
                dca_price = pending_order.get('dca_price', avg_price)
                dca_amount = executed_volume  # 실제 체결 수량
                dca_value_krw = pending_order.get('dca_value_krw', 0)
                level_index = pending_order.get('level', 0)
                group_id = pending_order.get('group_id', 'unknown')
                group_name = pending_order.get('group_name', 'Unknown')

                # 포지션 DCA 추가
                self.position_manager.add_dca(
                    symbol=symbol,
                    dca_price=dca_price,
                    dca_amount=dca_amount,
                    dca_value_krw=dca_value_krw
                )

                logger.info(f"   ✅ {symbol} DCA 레벨 {level_index+1} 부분 체결 완료 → add_dca() 호출")

                # 거래 기록 추가
                updated_position = self.position_manager.get_position(symbol)
                self.trade_history.add_trade(
                    group_id=group_id,
                    group_name=group_name,
                    symbol=symbol,
                    action="buy",
                    trade_type="dca",
                    price=updated_position.get("avg_buy_price"),
                    amount=updated_position.get("total_amount"),
                    total_krw=dca_value_krw,
                    dry_run=False,
                    dca_level=level_index + 1
                )

                # pending_order 제거
                self.position_manager.update_position(symbol, {'pending_order': None})

        return  # state='trade' 처리 완료

    # 수정 3: state='cancel' 처리 (이미 trade에서 처리했으면 무시)
    if state in ['cancel', 'prevented']:
        logger.warning(f"   ⚠️ 주문 {order_uuid[:8]}... 취소/방지됨 (state={state})")

        # pending_order 정리 (trade에서 이미 제거했으면 없음)
        position = self.position_manager.get_position(symbol)
        if position and position.get('pending_order', {}).get('order_id') == order_uuid:
            self.position_manager.update_position(symbol, {'pending_order': None})
            logger.info(f"   🗑️ {symbol} pending_order 정리 완료")

        return

    # state='done' 처리 (전체 체결 완료 - 기존 로직 유지)
    position = self.position_manager.get_position(symbol)
    if not position:
        logger.warning(f"   ⚠️ {symbol} 포지션 없음")
        return

    pending_order = position.get('pending_order')
    if not pending_order or pending_order.get('order_id') != order_uuid:
        logger.debug(f"   ⏭️ {symbol} pending_order와 불일치 (무시)")
        return

    order_type = pending_order.get('type')
    level_index = pending_order.get('level')

    logger.info(f"   ✅ {symbol} {order_type} 레벨 {level_index} 전체 체결 완료")

    # 기존 done 처리 로직...
    # (profit, loss, dca 타입별 처리)
```

### 핵심 변경 사항

1. **state='trade' 처리 추가**:
   - 부분 체결 시점에 DCA 업데이트
   - `add_dca()` 호출로 `dca_count` 증가
   - `total_invested_krw` 업데이트
   - 거래 기록 추가

2. **state='cancel' 처리 개선**:
   - trade에서 이미 처리했으면 pending_order 없음
   - 없으면 정리만 하고 종료

3. **state='done' 기존 로직 유지**:
   - 전체 체결 완료 시 기존 방식대로 처리

### 기대 효과

**수정 전**:
```
DCA1 실행 → state=trade (무시) → state=cancel (무시)
          → dca_count=0 유지 → DCA1 반복 실행...
```

**수정 후**:
```
DCA1 실행 → state=trade → add_dca() 호출 → dca_count=1, total_invested 업데이트
          → profit_pct 재계산 (-2.2% → -1.1%)
          → state=cancel → pending_order 정리만 (DCA는 이미 처리됨)

가격 추가 하락 → -1.5% 도달
  → DCA 체크 → dca_count=1 → i=1 체크 (2번째 레벨)
  → 조건 만족 → DCA2 실행 ✅
```

---

## 📁 관련 파일 위치

### 수정 대상
- `core/v4_trading_engine.py` (Line 1253-1366: `_on_order_completed` 메서드)

### 참고 파일
- `core/upbit_websocket.py` (Line 839-977: `MyOrderWebSocket` 클래스)
- `core/position_manager.py` (Line 356-421: `add_dca` 메서드)

### 데이터 파일
- `data/positions_live.json` - Live 모드 포지션 (DCA 카운트 저장)
- `data/positions_dryrun.json` - Dry-run 모드 포지션

---

## 🧪 테스트 시나리오

### 준비
1. Dry-run 모드 활성화
2. 작은 금액 코인 수동 매수 (예: 6,000원)
3. DCA 설정:
   - 레벨 1: -1.0% / 100%
   - 레벨 2: -1.5% / 50%

### 테스트 1: DCA 레벨 1 실행
- 가격 하락으로 -1.0% 도달
- 예상: DCA1 실행 → 6,000원 추가 → 총 12,000원
- 확인:
  - `dca_count` = 1
  - `total_invested_krw` = 12,000
  - `profit_pct` 개선 확인

### 테스트 2: DCA 레벨 2 실행
- 가격 추가 하락으로 -1.5% 도달
- 예상: DCA2 실행 → 6,000원 추가 (50% of 12,000) → 총 18,000원
- 확인:
  - `dca_count` = 2
  - `total_invested_krw` = 18,000
  - DCA1 반복 실행 안 됨

### 테스트 3: DCA 최대 횟수 제한
- 모든 레벨 실행 후 추가 DCA 안 나가는지 확인

---

## 💾 Git 상태

### 현재 브랜치
```
claude/copy-rate-limit-backup-011CV2yYQtVQngS6AJ5Yxmjy
```

### 최근 커밋
```
53069b5 fix: Change DCA calculation to use current total investment instead of initial amount
4001d21 fix: Correct DCA field names to match level settings configuration
f4b1ef4 fix: Display decimal places in level settings dialog
ee55a10 fix: Standardize field name to avg_buy_price across all modules
e703323 fix: Resolve GUI freeze and enable profit-taking by fixing thread blocking
```

### 작업 상태
- Working directory: Clean
- Uncommitted changes: None
- Ready for new branch/commits

---

## 📝 내일 작업 체크리스트

- [ ] `core/v4_trading_engine.py` 파일 열기
- [ ] `_on_order_completed` 메서드 찾기 (Line 1253)
- [ ] state='trade' 처리 로직 추가
- [ ] state='cancel' 처리 로직 개선
- [ ] 코드 커밋 (메시지: "fix: Process DCA updates on state=trade for sequential execution")
- [ ] Dry-run 모드로 테스트
- [ ] DCA 레벨 1 → 레벨 2 순차 실행 확인
- [ ] 로그 확인:
  - `dca_count` 증가 확인
  - `total_invested_krw` 업데이트 확인
  - `profit_pct` 재계산 확인
- [ ] 문제 없으면 Live 모드 소액 테스트
- [ ] 최종 커밋 및 푸시

---

## 🔗 관련 문서
- `/home/user/upbit-auto-trader/CLAUDE.md` - 프로젝트 전체 가이드
- `/home/user/upbit-auto-trader/core/v4_trading_engine.py` - 트레이딩 엔진
- `/home/user/upbit-auto-trader/core/position_manager.py` - 포지션 관리
- `/home/user/upbit-auto-trader/core/upbit_websocket.py` - WebSocket 관리

---

## 🎯 최종 목표

**DCA 순차 실행 완벽히 동작**:
- ✅ 레벨 1 (-1%) → 실행
- ✅ 평균 단가 개선
- ✅ 레벨 2 (-1.5%) → 실행
- ✅ 레벨 1 중복 실행 안 됨
- ✅ 유저가 설정한 시나리오대로 정확히 동작

**성공 기준**:
1. `dca_count`가 순차적으로 증가 (0 → 1 → 2)
2. `total_invested_krw`가 DCA마다 정확히 업데이트
3. `profit_pct`가 DCA 후 재계산됨
4. 같은 레벨이 중복 실행 안 됨
5. 로그에 명확한 진행 상황 표시

---

**작성 일시**: 2025-11-12
**작성자**: Claude (AI Assistant)
**다음 세션에서 이 문서를 참고하여 작업 진행하세요.**
