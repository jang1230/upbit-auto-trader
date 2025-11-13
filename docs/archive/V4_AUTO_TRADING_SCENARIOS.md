# V4 자동매매 시스템 작동 시나리오

**작성일**: 2025-11-10
**엔진**: `core/v4_trading_engine.py` (930 lines)
**전략**: `core/strategies/v4_auto_buy_strategy.py` (456 lines)

---

## 🎬 시나리오 1: 시스템 시작

### 사용자 액션
```
1. GUI 실행: python main.py
2. "📁 그룹 관리" 클릭
   → 그룹 생성: "비트코인 그룹"
   → 코인 추가: KRW-BTC
   → Buy Settings:
      - Mode: "auto" (자동 매수)
      - Investment Style: "balanced" (1시간봉)
      - Buy Amount: 50,000원
   → DCA Settings:
      - Level 1: -5% 하락 시 50,000원 추가 매수
      - Level 2: -10% 하락 시 100,000원 추가 매수
   → Profit Settings:
      - Level 1: +5% 상승 시 50% 익절
      - Level 2: +10% 상승 시 100% 익절
   → Loss Settings:
      - Level 1: -15% 하락 시 100% 손절

3. "⚙️ 전역 설정" 클릭
   → Dry-run Mode: 활성화 (테스트용)
   → Daily Loss Limit: 10% 손실 시 알림

4. "▶ 전체 DCA 시작" 클릭
```

### 시스템 내부 동작

```python
# v4_trading_engine.py:107-153
def start(self):
    # 1. Upbit 계좌와 포지션 동기화
    sync_result = self.position_manager.sync_with_upbit(self.config)
    # → 현재 보유 중인 코인들을 포지션으로 로드

    # 2. 일일 손실 추적 초기화
    self.daily_loss_tracker.check_and_reset()
    # → 09:00 기준 스냅샷 생성

    # 3. 그룹별 전략 초기화
    self._initialize_strategies()
    # → "비트코인 그룹"의 KRW-BTC에 대해 V4AutoBuyStrategy 생성

    # 4. 스케줄러 시작 (09:00 일일 리셋)
    self.scheduler_thread.start()

    # 5. 메인 거래 루프 시작 (60초마다 실행)
    self.main_thread.start()
```

**로그 출력**:
```
[2025-11-10 14:30:00] 🚀 V4 거래 엔진 시작
[2025-11-10 14:30:00] 🧪 Dry-run 모드 - 가상 거래
[2025-11-10 14:30:01] 🔄 Upbit 계좌와 포지션 동기화 중...
[2025-11-10 14:30:02] ✅ 동기화 완료: {'synced_positions': 0, 'krw_balance': 500000}
[2025-11-10 14:30:02] 📊 그룹별 전략 초기화 중...
[2025-11-10 14:30:02]   - 비트코인 그룹: KRW-BTC 전략 생성 완료
[2025-11-10 14:30:02] ✅ 총 1개 전략 초기화 완료
[2025-11-10 14:30:02] ⏰ 스케줄러 시작
[2025-11-10 14:30:02] 🔄 메인 거래 루프 시작
[2025-11-10 14:30:02] ✅ V4 거래 엔진 시작 완료
```

---

## 🎬 시나리오 2: 자동 매수 신호 발생

### 상황 설정
- 시간: 2025-11-10 14:31:00
- BTC 가격: 120,000,000원 → 115,000,000원 (급락)
- 포지션: 없음

### 60초 루프 실행

```python
# v4_trading_engine.py:209-243
def _run_trading_loop(self):
    while not self.stop_event.is_set():
        # 1. 일일 손실 한도 체크 (매 루프마다)
        if self.daily_loss_tracker:
            self.daily_loss_tracker.check_and_reset()

        # 2. 모든 그룹 순회
        for group_id, group in all_groups.items():
            # 3. 각 코인 처리
            for symbol in group.get("coins", []):
                self._process_symbol(symbol, group_id, group)

        # 4. 60초 대기
        self.stop_event.wait(60)
```

### 코인 처리 (_process_symbol)

```python
# v4_trading_engine.py:245-267
def _process_symbol(self, symbol: str, group_id: str, group: Dict):
    # 1. 전역 제약 확인 (관찰 모드, 최소 잔고, 일일 손실 한도)
    if not self._check_global_constraints():
        return

    # 2. 포지션 확인
    position = self.position_manager.get_position("KRW-BTC")
    # → None (포지션 없음)

    # 3. 포지션 없음 + 자동 매수 모드 → 매수 신호 체크
    if not position and group.get("buy_settings", {}).get("mode") == "auto":
        self._check_buy_signal(symbol, group_id, group)
```

### 매수 신호 체크

```python
# v4_trading_engine.py:268-304
def _check_buy_signal(self, symbol: str, group_id: str, group: Dict):
    # 1. 전략 가져오기
    strategy = self.strategies["비트코인 그룹"]["KRW-BTC"]
    # → V4AutoBuyStrategy (balanced 프리셋)

    # 2. 캔들 데이터 가져오기 (1시간봉 200개)
    candles = self._get_recent_candles("KRW-BTC", "60", count=200)
    # → UpbitAPI.get_candles("KRW-BTC", interval="minute60", count=200)

    # 3. 매수 신호 확인
    if strategy.should_buy(candles):
        # ✅ 매수 신호 발생!
        logger.info(f"🔔 KRW-BTC: 매수 신호 발생!")

        # 4. 지표 값 출력
        indicators = strategy.get_indicator_values(candles)
        # → {'rsi': 28.5, 'macd_cross': True, 'volume_surge': True}
        logger.info(f"   지표 값: {indicators}")

        # 5. 매수 실행
        self._execute_buy(symbol, group_id, group)
```

### V4AutoBuyStrategy.should_buy() 로직

```python
# v4_auto_buy_strategy.py:144-192
def should_buy(self, candles: pd.DataFrame) -> bool:
    buy_signals = []

    # 조건 1: RSI ≤ 30 (과매도)
    rsi = self._calculate_rsi(candles)
    if rsi.iloc[-1] <= 30:
        buy_signals.append(True)  # ✅ RSI = 28.5
    else:
        buy_signals.append(False)

    # 조건 2: MACD 골든크로스
    if self._check_macd_golden_cross(candles):
        buy_signals.append(True)  # ✅ 골든크로스 발생
    else:
        buy_signals.append(False)

    # 조건 3: Volume ≥ 2.0x 평균
    if self._check_volume_surge(candles):
        buy_signals.append(True)  # ✅ 거래량 2.5배
    else:
        buy_signals.append(False)

    # 모든 조건 만족 시 매수
    return all(buy_signals)  # ✅ True (3개 조건 모두 True)
```

### 매수 실행

```python
# v4_trading_engine.py:305-394
def _execute_buy(self, symbol: str, group_id: str, group: Dict):
    # 1. 관찰 모드 체크
    if self.observation_mode:
        return  # 관찰 전용 모드면 실행 안 함

    # 2. 매수 금액 가져오기
    buy_amount = group["buy_settings"]["auto_config"]["buy_amount_krw"]
    # → 50,000원

    logger.info(f"💰 KRW-BTC 매수 실행 중... (금액: 50,000원)")

    # 3. Dry-run 모드
    if self.dry_run:
        # 현재가 조회
        current_price = self._get_current_price_safe("KRW-BTC")
        # → 115,000,000원

        # 매수 수량 계산
        buy_quantity = 50000 / 115000000
        # → 0.00043478 BTC

        # 포지션 생성
        position = self.position_manager.create_position(
            group_id="비트코인 그룹",
            symbol="KRW-BTC",
            buy_price=115000000,
            buy_amount=0.00043478,
            buy_value_krw=50000
        )

        logger.info(f"✅ [Dry-run] KRW-BTC 매수 완료: 0.00043478개 @ 115,000,000원")

    # 4. 거래 기록
    self.trade_history.add_trade(
        group_id="비트코인 그룹",
        symbol="KRW-BTC",
        action="buy",
        trade_type="initial",
        price=115000000,
        amount=0.00043478,
        total_krw=50000
    )

    # 5. 텔레그램 알림
    self._send_telegram_alert(
        "✅ 매수 완료\n"
        "그룹: 비트코인 그룹\n"
        "코인: KRW-BTC\n"
        "금액: 50,000원\n"
        "수량: 0.00043478개\n"
        "가격: 115,000,000원"
    )
```

**로그 출력**:
```
[2025-11-10 14:31:00] 🔔 KRW-BTC: 매수 신호 발생!
[2025-11-10 14:31:00]    지표 값: {'rsi': 28.5, 'macd_cross': True, 'volume_surge': True}
[2025-11-10 14:31:00] 💰 KRW-BTC 매수 실행 중... (금액: 50,000원)
[2025-11-10 14:31:01] ✅ [Dry-run] KRW-BTC 매수 완료: 0.00043478개 @ 115,000,000원
[2025-11-10 14:31:01] 📱 [Telegram] ✅ 매수 완료
그룹: 비트코인 그룹
코인: KRW-BTC
금액: 50,000원
수량: 0.00043478개
가격: 115,000,000원
```

**GUI 포지션 테이블 업데이트**:
```
┌─────────────┬────────────┬──────────┬────────────┬─────────┬──────────┐
│ 코인        │ 평단가     │ 수량     │ 현재가     │ 수익률  │ 평가액   │
├─────────────┼────────────┼──────────┼────────────┼─────────┼──────────┤
│ KRW-BTC     │ 115,000,000│ 0.00043  │ 115,000,000│ +0.00%  │ 50,000원 │
└─────────────┴────────────┴──────────┴────────────┴─────────┴──────────┘
```

---

## 🎬 시나리오 3: DCA 트리거 (가격 하락)

### 상황 설정
- 시간: 2025-11-10 15:00:00 (매수 후 29분)
- BTC 가격: 115,000,000원 → 109,250,000원 (-5.0% 하락)
- 포지션: 있음 (평단가 115,000,000원, 수량 0.00043478 BTC)

### 60초 루프 실행 → 포지션 관리

```python
# v4_trading_engine.py:245-267
def _process_symbol(self, symbol: str, group_id: str, group: Dict):
    # 1. 전역 제약 확인
    if not self._check_global_constraints():
        return

    # 2. 포지션 확인
    position = self.position_manager.get_position("KRW-BTC")
    # → {'status': 'active', 'avg_buy_price': 115000000, ...}

    # 3. 포지션 있음 → 포지션 관리 (DCA, 익절, 손절)
    if position:
        self._manage_position(symbol, group_id, group)
```

### 포지션 관리

```python
# v4_trading_engine.py:395-428
def _manage_position(self, symbol: str, group_id: str, group: Dict):
    position = self.position_manager.get_position("KRW-BTC")

    # 1. 현재가 조회
    current_price = self._get_current_price_safe("KRW-BTC")
    # → 109,250,000원

    # 2. 수익률 계산
    avg_buy_price = position["avg_buy_price"]  # 115,000,000원
    profit_pct = ((current_price - avg_buy_price) / avg_buy_price) * 100
    # → ((109,250,000 - 115,000,000) / 115,000,000) * 100 = -5.0%

    # 3. DCA 체크
    self._check_dca(symbol, group_id, group, position, current_price, profit_pct)

    # 4. 익절 체크
    self._check_profit_target(...)  # profit_pct = -5.0% → 익절 조건 불만족

    # 5. 손절 체크
    self._check_stop_loss(...)  # profit_pct = -5.0% → 손절 조건 불만족 (-15%)
```

### DCA 트리거 체크

```python
# v4_trading_engine.py:429-461
def _check_dca(self, symbol, group_id, group, position, current_price, profit_pct):
    # 1. DCA 설정 가져오기
    dca_settings = group["dca_settings"]
    # → {"mode": "auto", "levels": [
    #      {"drop_pct": -5.0, "buy_ratio": 1.0},
    #      {"drop_pct": -10.0, "buy_ratio": 2.0}
    #    ]}

    # 2. DCA 모드 체크
    if dca_settings.get("mode") != "auto":
        return  # auto가 아니면 DCA 안 함

    # 3. DCA 레벨 확인
    dca_levels = dca_settings["levels"]
    dca_count = position.get("dca_count", 0)  # 0 (아직 DCA 안 함)

    # 4. 각 레벨 순회
    for i, level in enumerate(dca_levels):
        if i < dca_count:
            continue  # 이미 실행된 레벨 스킵

        drop_pct = level["drop_pct"]  # -5.0%

        # 5. 트리거 조건 확인
        if profit_pct <= drop_pct:
            # ✅ -5.0% <= -5.0% → DCA 레벨 1 트리거!
            logger.info(f"🔔 KRW-BTC: DCA 레벨 1 트리거 (현재: -5.00%, 기준: -5.00%)")
            self._execute_dca(symbol, group_id, group, level, i+1)
            break
```

### DCA 매수 실행

```python
# v4_trading_engine.py:463-542
def _execute_dca(self, symbol, group_id, group, level, dca_level_num):
    # 1. DCA 금액 계산
    base_amount = group["buy_settings"]["auto_config"]["buy_amount_krw"]  # 50,000원
    buy_ratio = level["buy_ratio"]  # 1.0
    dca_amount = int(base_amount * buy_ratio)  # 50,000원

    logger.info(f"💰 KRW-BTC DCA 레벨 1 실행 중... (금액: 50,000원, 비율: 1.0x)")

    # 2. Dry-run 모드
    if self.dry_run:
        current_price = self._get_current_price_safe("KRW-BTC")
        # → 109,250,000원

        dca_quantity = 50000 / 109250000
        # → 0.00045775 BTC

        # 포지션 DCA 추가
        self.position_manager.add_dca(
            symbol="KRW-BTC",
            dca_price=109250000,
            dca_amount=0.00045775,
            dca_value_krw=50000
        )
        # → 평단가 재계산:
        #    총 투자금: 100,000원
        #    총 수량: 0.00043478 + 0.00045775 = 0.00089253 BTC
        #    새 평단가: 100,000 / 0.00089253 = 112,047,619원

        logger.info(f"✅ [Dry-run] KRW-BTC DCA 완료: 0.00045775개 @ 109,250,000원")

    # 3. 거래 기록
    self.trade_history.add_trade(
        group_id="비트코인 그룹",
        symbol="KRW-BTC",
        action="buy",
        trade_type="dca",
        price=109250000,
        amount=0.00045775,
        total_krw=50000,
        dca_level=1
    )
```

**로그 출력**:
```
[2025-11-10 15:00:00] 🔔 KRW-BTC: DCA 레벨 1 트리거 (현재: -5.00%, 기준: -5.00%)
[2025-11-10 15:00:00] 💰 KRW-BTC DCA 레벨 1 실행 중... (금액: 50,000원, 비율: 1.0x)
[2025-11-10 15:00:01] ✅ [Dry-run] KRW-BTC DCA 완료: 0.00045775개 @ 109,250,000원
```

**GUI 포지션 테이블 업데이트**:
```
┌─────────────┬────────────┬──────────┬────────────┬─────────┬──────────┐
│ 코인        │ 평단가     │ 수량     │ 현재가     │ 수익률  │ 평가액   │
├─────────────┼────────────┼──────────┼────────────┼─────────┼──────────┤
│ KRW-BTC     │ 112,047,619│ 0.00089  │ 109,250,000│ -2.50%  │ 97,500원 │
└─────────────┴────────────┴──────────┴────────────┴─────────┴──────────┘
DCA: 1/2 레벨 사용
```

---

## 🎬 시나리오 4: 익절 트리거 (가격 상승)

### 상황 설정
- 시간: 2025-11-10 16:00:00 (DCA 후 1시간)
- BTC 가격: 109,250,000원 → 117,650,000원 (+5.0% 상승, 평단가 대비)
- 포지션: 평단가 112,047,619원, 수량 0.00089253 BTC

### 포지션 관리 → 익절 체크

```python
# v4_trading_engine.py:395-428
def _manage_position(self, symbol, group_id, group, position, current_price, profit_pct):
    # 현재가: 117,650,000원
    # 평단가: 112,047,619원
    # 수익률: +5.0%

    # 1. DCA 체크 → 불만족 (수익률 양수)
    # 2. 익절 체크
    self._check_profit_target(symbol, group_id, group, position, current_price, profit_pct)
```

### 익절 트리거 체크

```python
# v4_trading_engine.py:543-579
def _check_profit_target(self, symbol, group_id, group, position, current_price, profit_pct):
    # 1. 익절 설정 가져오기
    profit_settings = group["profit_settings"]
    # → {"mode": "auto", "levels": [
    #      {"price_ratio": 5.0, "quantity_ratio": 50},
    #      {"price_ratio": 10.0, "quantity_ratio": 100}
    #    ]}

    # 2. 익절 모드 체크
    if profit_settings.get("mode") not in ["auto", "alert"]:
        return

    # 3. 익절 레벨 순회
    for level in profit_settings["levels"]:
        target_pct = level["price_ratio"]  # 5.0%
        quantity_ratio = level["quantity_ratio"] / 100.0  # 0.5 (50%)

        # 4. 트리거 조건 확인
        if profit_pct >= target_pct:
            # ✅ +5.0% >= +5.0% → 익절 레벨 1 트리거!
            logger.info(f"🎯 KRW-BTC: 익절 목표 도달 (현재: +5.00%, 목표: +5.00%)")

            # 5. 자동 매도 실행
            if profit_settings["mode"] == "auto":
                self._execute_sell(symbol, group_id, group, "profit", quantity_ratio)
            break
```

### 익절 매도 실행

```python
# v4_trading_engine.py:617-706
def _execute_sell(self, symbol, group_id, group, reason, quantity_ratio):
    # 1. 매도 수량 계산
    total_amount = position["total_amount"]  # 0.00089253 BTC
    sell_amount = total_amount * quantity_ratio  # 0.00089253 * 0.5 = 0.00044627 BTC

    logger.info(f"💰 KRW-BTC 매도 실행 중... (사유: profit, 수량: 0.00044627개)")

    # 2. Dry-run 모드
    if self.dry_run:
        current_price = 117650000
        sell_value = 0.00044627 * 117650000  # 52,497원

        # 투자금 대비 수익 계산
        invested = position["total_invested_krw"] * quantity_ratio  # 100,000 * 0.5 = 50,000원
        profit = sell_value - invested  # 52,497 - 50,000 = +2,497원

        # 포지션 부분 매도 (50%)
        # ⚠️ 현재 구현: 부분 매도 미지원 (전량 매도만 가능)
        logger.warning(f"⚠️ 부분 매도는 아직 미구현")
        return
```

**주의**: 현재 V4 엔진은 **부분 매도 미구현** (line 656)
- 익절 레벨 1 (50% 매도) → 실행 안 됨
- 익절 레벨 2 (100% 매도) → 전량 매도 가능

**만약 quantity_ratio = 1.0 (100% 매도)이면**:
```python
# 전량 매도
if quantity_ratio >= 0.99:
    self.position_manager.close_position("KRW-BTC")
    logger.info(f"✅ [Dry-run] KRW-BTC 전량 매도 완료: 0.00089253개 @ 117,650,000원 (수익: +4,994원)")
```

**로그 출력** (100% 익절 시):
```
[2025-11-10 16:00:00] 🎯 KRW-BTC: 익절 목표 도달 (현재: +5.00%, 목표: +5.00%)
[2025-11-10 16:00:00] 💰 KRW-BTC 매도 실행 중... (사유: profit, 수량: 0.00089253개)
[2025-11-10 16:00:01] ✅ [Dry-run] KRW-BTC 전량 매도 완료: 0.00089253개 @ 117,650,000원 (수익: +4,994원)
[2025-11-10 16:00:01] 📱 [Telegram] 🎉 매도 완료 (profit)
그룹: 비트코인 그룹
코인: KRW-BTC
수익: +4,994원
수익률: +4.99%
```

---

## 🎬 시나리오 5: 손절 트리거 (가격 추가 하락)

### 상황 설정
- 시간: 2025-11-10 17:00:00
- BTC 가격: 109,250,000원 → 95,240,000원 (-15.0% 하락, 평단가 대비)
- 포지션: 평단가 112,047,619원, 수량 0.00089253 BTC (DCA 1회 실행 후)

### 포지션 관리 → 손절 체크

```python
# v4_trading_engine.py:580-616
def _check_stop_loss(self, symbol, group_id, group, position, current_price, profit_pct):
    # 1. 손절 설정 가져오기
    loss_settings = group["loss_settings"]
    # → {"mode": "auto", "levels": [
    #      {"price_ratio": -15.0, "quantity_ratio": 100}
    #    ]}

    # 2. 손절 레벨 순회
    for level in loss_settings["levels"]:
        stop_pct = level["price_ratio"]  # -15.0%
        quantity_ratio = level["quantity_ratio"] / 100.0  # 1.0 (100%)

        # 3. 트리거 조건 확인
        if profit_pct <= stop_pct:
            # ✅ -15.0% <= -15.0% → 손절 트리거!
            logger.warning(f"🛑 KRW-BTC: 손절 기준 도달 (현재: -15.00%, 기준: -15.00%)")

            # 4. 자동 매도 실행
            if loss_settings["mode"] == "auto":
                self._execute_sell(symbol, group_id, group, "loss", quantity_ratio)
            break
```

### 손절 매도 실행

```python
# v4_trading_engine.py:617-706
def _execute_sell(self, symbol, group_id, group, reason="loss", quantity_ratio=1.0):
    # 1. 전량 매도 (quantity_ratio = 1.0)
    total_amount = 0.00089253 BTC
    sell_value = 0.00089253 * 95240000 = 84,995원
    profit = 84,995 - 100,000 = -15,005원

    # 2. 포지션 종료
    self.position_manager.close_position("KRW-BTC")

    logger.info(f"✅ [Dry-run] KRW-BTC 전량 매도 완료: 0.00089253개 @ 95,240,000원 (수익: -15,005원)")
```

**로그 출력**:
```
[2025-11-10 17:00:00] 🛑 KRW-BTC: 손절 기준 도달 (현재: -15.00%, 기준: -15.00%)
[2025-11-10 17:00:00] 💰 KRW-BTC 매도 실행 중... (사유: loss, 수량: 0.00089253개)
[2025-11-10 17:00:01] ✅ [Dry-run] KRW-BTC 전량 매도 완료: 0.00089253개 @ 95,240,000원 (수익: -15,005원)
[2025-11-10 17:00:01] 📱 [Telegram] 😢 매도 완료 (loss)
그룹: 비트코인 그룹
코인: KRW-BTC
수익: -15,005원
수익률: -15.00%
```

---

## 🎬 시나리오 6: 일일 손실 한도 도달

### 상황 설정
- 시간: 2025-11-10 18:00:00
- 오늘 시작 잔고: 500,000원 (09:00 스냅샷)
- 현재 평가액: 440,000원 (60,000원 손실)
- 손실률: -12.0% (일일 손실 한도 -10% 초과)

### 일일 손실 추적 체크

```python
# v4_trading_engine.py:215-220
def _run_trading_loop(self):
    while not self.stop_event.is_set():
        # 매 루프마다 일일 손실 한도 체크
        if self.daily_loss_tracker:
            self.daily_loss_tracker.check_and_reset()
```

### DailyLossTracker 동작

```python
# daily_loss_tracker.py (simplified)
def check_and_reset(self):
    # 1. 현재 시간 체크
    now = datetime.now().time()

    # 2. 09:00 리셋 확인
    if now >= time(9, 0) and self.last_reset_date != date.today():
        self._reset()  # 스냅샷 재생성

    # 3. 손실률 계산
    current_valuation = self.get_valuation_fn()  # 440,000원
    snapshot_valuation = self.snapshot["valuation"]  # 500,000원

    if self.config["calculation_method"] == "daily_only":
        loss_pct = ((current_valuation - snapshot_valuation) / snapshot_valuation) * 100
        # → ((440,000 - 500,000) / 500,000) * 100 = -12.0%

    # 4. 한도 초과 확인
    if loss_pct <= -self.config["loss_pct"]:  # -12.0 <= -10.0
        # ✅ 일일 손실 한도 도달!
        self._handle_limit_reached()
```

### 한도 도달 처리

```python
# daily_loss_tracker.py
def _handle_limit_reached(self):
    # 1. 알림 전송
    if self.send_alert_fn:
        self.send_alert_fn(
            "🚨 일일 손실 한도 도달!\n"
            f"손실률: -12.0%\n"
            f"한도: -10.0%\n"
            f"현재 평가액: 440,000원"
        )

    # 2. 액션 실행
    action = self.config["action"]  # "liquidate" or "alert"

    if action == "liquidate":
        # 전체 청산
        if self.liquidate_fn:
            self.liquidate_fn(reason="일일 손실 한도 도달")
    elif action == "alert":
        # 알림만 (거래 계속)
        pass
```

### 전체 청산 (action = "liquidate")

```python
# v4_trading_engine.py:831-851
def _liquidate_all_positions(self, reason: str = "일일 손실 한도 도달"):
    logger.warning(f"🚨 모든 포지션 청산 시작 (사유: {reason})")

    # 모든 포지션 순회
    all_positions = self.position_manager.get_all_positions()

    for symbol, position in all_positions.items():
        if position.get("status") != "active":
            continue

        # 그룹 찾기
        group_tuple = self.group_manager.get_group_by_symbol(symbol)
        group_id, group = group_tuple

        # 전량 매도 실행
        self._execute_sell(symbol, group_id, group, "emergency", quantity_ratio=1.0)

    logger.warning(f"✅ 모든 포지션 청산 완료")
```

**로그 출력**:
```
[2025-11-10 18:00:00] 🚨 일일 손실 한도 도달! (손실률: -12.0%, 한도: -10.0%)
[2025-11-10 18:00:00] 📱 [Telegram] 🚨 일일 손실 한도 도달!
손실률: -12.0%
한도: -10.0%
현재 평가액: 440,000원

[2025-11-10 18:00:00] 🚨 모든 포지션 청산 시작 (사유: 일일 손실 한도 도달)
[2025-11-10 18:00:01] 💰 KRW-BTC 매도 실행 중... (사유: emergency, 수량: 전량)
[2025-11-10 18:00:02] ✅ [Dry-run] KRW-BTC 전량 매도 완료
[2025-11-10 18:00:02] 💰 KRW-ETH 매도 실행 중... (사유: emergency, 수량: 전량)
[2025-11-10 18:00:03] ✅ [Dry-run] KRW-ETH 전량 매도 완료
[2025-11-10 18:00:03] ✅ 모든 포지션 청산 완료
```

---

## 📊 전체 타임라인 요약

```
14:30:00 - 시스템 시작
         ↓
14:31:00 - 자동 매수 신호 발생 (RSI 28.5, MACD 골든크로스, Volume 2.5배)
         ↓ 매수: 0.00043478 BTC @ 115,000,000원 (50,000원)
         ↓
15:00:00 - DCA 레벨 1 트리거 (-5.0% 하락)
         ↓ 추가 매수: 0.00045775 BTC @ 109,250,000원 (50,000원)
         ↓ 평단가: 112,047,619원, 총 수량: 0.00089253 BTC
         ↓
16:00:00 - 익절 레벨 1 트리거 (+5.0% 상승)
         ↓ ⚠️ 부분 매도 미구현 → 스킵
         ↓
17:00:00 - 손절 트리거 (-15.0% 하락)
         ↓ 전량 매도: 0.00089253 BTC @ 95,240,000원 (손실 -15,005원)
         ↓
18:00:00 - 일일 손실 한도 도달 (-12.0%)
         ↓ 모든 포지션 청산 (emergency)
         ↓
09:00:00 (다음날) - 일일 리셋
         ↓ 스냅샷 재생성, 거래 재개
```

---

## ⚙️ 시스템 설정 파일 위치

### 설정 파일
```json
// config/trading_config.json
{
  "version": "4.0",
  "mode": "dryrun",
  "groups": {
    "비트코인 그룹": {
      "name": "비트코인 그룹",
      "coins": ["KRW-BTC"],
      "buy_settings": {
        "mode": "auto",
        "auto_config": {
          "investment_style": "balanced",
          "candle_unit": "60",
          "buy_amount_krw": 50000
        }
      },
      "dca_settings": {
        "mode": "auto",
        "levels": [
          {"drop_pct": -5.0, "buy_ratio": 1.0},
          {"drop_pct": -10.0, "buy_ratio": 2.0}
        ]
      },
      "profit_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": 5.0, "quantity_ratio": 50},
          {"price_ratio": 10.0, "quantity_ratio": 100}
        ]
      },
      "loss_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": -15.0, "quantity_ratio": 100}
        ]
      }
    }
  },
  "global_settings": {
    "dry_run": true,
    "observation_mode": false,
    "daily_loss_limit": {
      "enabled": true,
      "loss_pct": 10.0,
      "action": "liquidate",
      "calculation_method": "daily_only"
    }
  }
}
```

### 포지션 파일
```json
// data/positions_dryrun.json
{
  "KRW-BTC": {
    "group_id": "비트코인 그룹",
    "symbol": "KRW-BTC",
    "status": "active",
    "avg_buy_price": 112047619,
    "total_amount": 0.00089253,
    "total_invested_krw": 100000,
    "dca_count": 1,
    "dca_history": [
      {
        "timestamp": "2025-11-10 14:31:00",
        "price": 115000000,
        "amount": 0.00043478,
        "value_krw": 50000
      },
      {
        "timestamp": "2025-11-10 15:00:00",
        "price": 109250000,
        "amount": 0.00045775,
        "value_krw": 50000
      }
    ],
    "created_at": "2025-11-10 14:31:00",
    "updated_at": "2025-11-10 15:00:00"
  }
}
```

---

## ✅ 핵심 포인트

### 1. 완전 자동화
- ✅ 자동 매수 (60초마다 신호 체크)
- ✅ 자동 DCA (가격 하락 시)
- ✅ 자동 익절 (목표 수익률 도달 시)
- ✅ 자동 손절 (손실 한도 도달 시)
- ✅ 일일 손실 한도 (전체 청산)

### 2. 60초 폴링 방식
- WebSocket 실시간 통합 없음
- REST API로 캔들 데이터 조회
- 60초마다 루프 실행

### 3. Dry-run 모드 지원
- 가상 주문 실행
- 실제 API 호출 없음
- 안전한 테스트 환경

### 4. 미구현 기능
- ⚠️ 부분 매도 (quantity_ratio < 1.0)
- ⚠️ WebSocket 실시간 통합 (현재는 60초 폴링)

---

**마지막 업데이트**: 2025-11-10
**작성자**: Claude (Sonnet 4.5)
**상태**: 시나리오 문서 완성
