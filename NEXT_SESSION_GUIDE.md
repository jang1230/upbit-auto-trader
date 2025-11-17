# 다음 세션 작업 가이드

**최종 업데이트**: 2025-11-17 07:00 (UTC)
**브랜치**: `claude/expert-strategy-backup-01KA4Aq841xqvr8BhrDAWDvf`
**최신 커밋**: `81c7334`

---

## 🎯 즉시 수행할 작업

### 1. 현재 상태 확인

```bash
# 1. 브랜치 확인
git status
git log --oneline -5

# 2. 실행 중인 프로그램 확인
# GUI가 실행 중인지 확인하고 현재 포지션 상태 확인

# 3. 로그 확인
tail -n 100 logs/trading_*.log
```

### 2. 테스트 필요 항목 (우선순위순)

#### 🔴 Priority 1: DCA 최대 포지션 제한 테스트

**커밋**: `1f65727`
**테스트 시나리오**:

```
상황: 포지션 10개 보유 중 (최대치)

✅ 예상 동작:
1. 신규 매수 → ❌ 차단됨
2. 기존 포지션 DCA → ✅ 정상 실행
3. 익절/손절 → ✅ 정상 실행

❌ 버그 가능성:
- DCA가 여전히 차단되는지 확인
- 로그에 "최대 포지션 개수 도달" 경고 확인
```

**테스트 방법**:
```python
# core/v4_trading_engine.py:709-766 로직 확인

# 1. 포지션 10개 만들기 (수동 또는 자동)
# 2. 기존 포지션 하나에 DCA 트리거 대기
# 3. 로그 확인:
#    - "⚠️ 최대 포지션 개수 도달..." → 신규 매수만 차단
#    - "💰 KRW-XXX DCA 레벨 X 실행 중..." → DCA 정상 실행
```

**예상 로그**:
```
15:00:00 - ⚠️ 최대 포지션 개수 도달 (10개 >= 10개) - 신규 매수 중지
15:00:05 - 🔔 KRW-BTC: DCA 레벨 1 트리거 (현재: -5.2%, 기준: -5.0%)
15:00:05 - 💰 KRW-BTC DCA 레벨 1 실행 중... (금액: 50,000원)
15:00:06 - ✅ KRW-BTC 매수 완료: 0.00123456개 @ 40,500,000원
```

#### 🔴 Priority 2: 익절/손절 5000원 미만 전량 매도 테스트

**커밋**: `81c7334`
**테스트 시나리오**:

```
상황 A: 부분 매도 금액 부족
포지션: 8,000원
익절 레벨 0: 50% @ +5% → 4,000원 (OK)

✅ 예상 동작:
1. 부분 매도(50%) 계산: 4,000원 < 5,000원
2. 자동으로 전량 매도로 변경
3. 로그: "⚠️ 부분 매도 금액 부족 → 전량 매도로 변경"

상황 B: 전량 매도도 부족
포지션: 3,000원
익절 레벨 0: 100% @ +5% → 3,000원 (X)

✅ 예상 동작:
1. 전량 매도해도 3,000원 < 5,000원
2. 매도 포기
3. 로그: "⚠️ 매도 불가: 전량 매도해도 3,000원 < 5,000원"
```

**테스트 방법**:
```bash
# 소액 포지션 의도적으로 생성 (예: 5,000원 이하)
# 익절 트리거 대기

# 로그 확인:
grep "매도 불가" logs/trading_*.log
grep "전량 매도로 변경" logs/trading_*.log
```

#### 🟡 Priority 3: DCA 잔고부족 쿨다운 테스트

**커밋**: `66b49bb`
**테스트 시나리오**:

```
상황: KRW 잔고 30,000원, DCA 금액 50,000원

✅ 예상 동작:
1. 첫 시도: "⚠️ KRW-XXX DCA 레벨 1 취소: 잔고 부족"
2. pending_order 설정 (5분 쿨다운)
3. 5분간 재시도 안함
4. 5분 후 자동 재시도 (잔고 충분하면 실행)

❌ 과거 동작:
- 매초 "잔고 부족" 경고 spam
```

**테스트 방법**:
```bash
# 1. 잔고를 의도적으로 부족하게 만들기
# 2. DCA 트리거 대기
# 3. 로그 확인:
#    - 첫 경고 후 5분간 같은 경고 없어야 함
#    - 5분 후 "pending_order timeout" 로그 확인
```

#### 🟡 Priority 4: 포지션 테이블 그룹 색상 확인

**커밋**: `35e8ef2`
**테스트 방법**:

```
1. GUI 실행
2. 활성 포지션 탭 확인
3. 확인 사항:
   - 같은 그룹끼리 같은 배경색
   - 그룹 ID 순으로 정렬
   - 그룹명 볼드체
   - 실시간 가격 업데이트 시 색상 유지
```

#### 🟢 Priority 5: 레벨 mode 자동 업데이트 확인

**커밋**: `3ed5c27`
**테스트 방법**:

```
1. GUI에서 그룹 설정 열기
2. DCA 레벨 모두 삭제 → 저장
3. config/trading_config.json 확인:
   "dca_settings": {
     "mode": "disabled",  ← 자동으로 disabled
     "levels": []
   }

4. DCA 레벨 1개 추가 → 저장
5. config 확인:
   "dca_settings": {
     "mode": "auto",  ← 자동으로 auto
     "levels": [...]
   }
```

---

## 🐛 알려진 이슈 및 제한사항

### Issue #1: 소액 포지션 익절/손절 불가

**현상**:
- 포지션 5,000원 미만 시 전량 매도해도 Upbit API 거부
- 익절/손절 레벨에 도달해도 매도 안됨

**영향**:
- 소액 테스트 시 포지션이 영구히 남을 수 있음
- 예: 3,000원 포지션 → +10% 익절 도달해도 매도 안됨

**임시 해결책**:
1. 수동 매도 (GUI에서 직접 매도)
2. 포지션 최소 10,000원 이상 유지

**근본 해결책 (미구현)**:
- 마지막 레벨 금액 사전 계산
- 5,000원 미만 예상 시 이전 레벨에서 전량 매도
- 설계 완료, 구현 보류 중

**관련 파일**:
- `core/v4_trading_engine.py:1467-1509` (현재 구현)
- `WORK_SUMMARY_2025-11-17.md` (Phase 1 로직 설계)

### Issue #2: WebSocket 60초 폴링

**현상**:
- 현재 60초마다 REST API로 가격 조회
- WebSocket 실시간 스트림 미사용

**영향**:
- 가격 변동 반영 최대 60초 지연
- 익절/손절 타이밍 약간 지연 가능

**상태**:
- 동작은 정상
- 최적화 여지 있음

**개선 방향**:
- `core/upbit_websocket.py` WebSocket 통합
- Rate Limit 고려 필요

---

## 📁 핵심 파일 위치

### 트레이딩 엔진
```
core/v4_trading_engine.py
  - Line 709-766: _process_symbol() - 전역 제약 체크
  - Line 1002-1085: _check_dca() - DCA 체크 및 pending_order
  - Line 1086-1228: _execute_dca() - DCA 실행 (avg_price fallback)
  - Line 1467-1509: _execute_sell() - 매도 실행 (최소 금액 체크)
```

### GUI
```
gui/main_window.py
  - Line 2260-2366: _load_v4_positions() - 그룹 색상 및 정렬
  - Line 2486-2548: _on_price_updated() - 실시간 가격 업데이트

gui/level_settings_dialog.py
  - Line 300-330: _save_levels() - mode 자동 업데이트

gui/group_unified_settings_dialog.py
  - Line 500-550: _save_settings() - 설정 저장 및 mode 자동 업데이트
```

### API
```
core/upbit_api.py
  - Line 410-441: buy_market_order() - 매수 주문 (에러 체크)
  - Line 443-472: sell_market_order() - 매도 주문 (에러 체크)
```

### 설정
```
config/trading_config.json
  - V4 전체 설정
  - 그룹별 buy/dca/profit/loss 설정

data/positions_live.json
  - 실제 포지션 데이터
  - pending_order 상태
```

---

## 🔬 디버깅 가이드

### 1. DCA 관련 문제

**증상**: DCA가 실행 안됨

**체크리스트**:
```bash
# 1. 설정 확인
cat config/trading_config.json | jq '.groups.GROUP_ID.dca_settings'

# 확인 사항:
# - mode: "auto" 여부
# - levels: 레벨이 있는지
# - enabled: true인지

# 2. 포지션 상태 확인
cat data/positions_live.json | jq '.SYMBOL'

# 확인 사항:
# - dca_count: 현재 DCA 횟수
# - pending_order: 대기 중인 주문 있는지
# - avg_buy_price: 평균가가 0이 아닌지

# 3. 로그 확인
grep "DCA" logs/trading_*.log | tail -50

# 찾아볼 내용:
# - "DCA 레벨 X 트리거" - 트리거 발생 여부
# - "잔고 부족" - 잔고 문제
# - "pending_order" - 대기 중인 주문 있는지
```

### 2. 익절/손절 관련 문제

**증상**: 익절/손절이 안됨

**체크리스트**:
```bash
# 1. 설정 확인
cat config/trading_config.json | jq '.groups.GROUP_ID.profit_settings'
cat config/trading_config.json | jq '.groups.GROUP_ID.loss_settings'

# 확인 사항:
# - mode: "auto" 또는 "alert"
# - levels: 레벨 설정 있는지

# 2. 포지션 수익률 확인
cat data/positions_live.json | jq '.SYMBOL.profit_pct'

# 3. 최소 금액 확인
# 포지션 금액 = total_amount * current_price
# 부분 매도 금액 = 포지션 금액 * quantity_ratio
# → 5,000원 이상이어야 함

# 4. 로그 확인
grep "익절\|손절" logs/trading_*.log | tail -50
```

### 3. 설정 반영 안되는 문제

**증상**: GUI에서 설정 변경했는데 적용 안됨

**해결**:
```bash
# 1. 설정 파일 확인
cat config/trading_config.json

# 2. 엔진 재시작
# GUI에서 "거래 중지" → "거래 시작"

# 3. 로그 확인
grep "config 리로드" logs/trading_*.log | tail -10

# "📄 GroupManager config 리로드 완료" 메시지 확인
```

### 4. 로그 레벨 조정

**상세 로그 필요 시**:
```python
# core/v4_trading_engine.py 최상단
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # DEBUG로 변경

# 또는 특정 함수에서만
def _check_dca(self, ...):
    logger.setLevel(logging.DEBUG)
    # ... 디버깅할 코드 ...
    logger.setLevel(logging.INFO)
```

---

## 🚀 미구현 기능 (우선순위순)

### 1. 5000원 미만 사전 체크 (High Priority)

**필요성**: 소액 포지션 익절/손절 불가 근본 해결

**구현 위치**: `core/v4_trading_engine.py`

**Phase 1 구현 가이드**:

```python
def _will_have_insufficient_amount(
    self,
    symbol: str,
    position: Dict,
    levels: List[Dict],
    current_level_index: int,
    current_price: float
) -> Tuple[bool, Optional[int], float]:
    """
    현재 레벨 이후 5000원 미만 레벨 발생 여부 체크

    Returns:
        (발생여부, 문제레벨인덱스, 예상금액)
    """
    MIN_ORDER_KRW = 5000
    SAFETY_MARGIN = 1.1  # 10% 안전 마진
    MIN_THRESHOLD = MIN_ORDER_KRW * SAFETY_MARGIN

    # 현재 포지션 실제 금액 (DCA 이후에도 정확)
    total_amount = position.get("total_amount", 0)
    total_value_krw = total_amount * current_price

    # 이미 실행된 레벨들
    executed_levels = position.get("profit_levels_executed", [])

    # 시뮬레이션: 현재 레벨까지 실행 후 남을 금액
    remaining_value_krw = total_value_krw

    for i in range(current_level_index + 1):
        if i in executed_levels:
            continue
        ratio = levels[i].get("quantity_ratio", 0) / 100.0
        sell_value = total_value_krw * ratio
        remaining_value_krw -= sell_value

    # 현재 레벨 이후의 모든 레벨 체크
    for i in range(current_level_index + 1, len(levels)):
        if i in executed_levels:
            continue

        ratio = levels[i].get("quantity_ratio", 0) / 100.0
        sell_value = total_value_krw * ratio

        if 0 < sell_value < MIN_THRESHOLD:
            logger.warning(
                f"⚠️ {symbol} 레벨 {i+1} 예상 금액 부족: "
                f"{sell_value:,.0f}원 < {MIN_THRESHOLD:,.0f}원"
            )
            return True, i, sell_value

    # 최종 잔여 금액 체크
    if 0 < remaining_value_krw < MIN_THRESHOLD:
        logger.warning(
            f"⚠️ {symbol} 최종 잔여 금액 부족: "
            f"{remaining_value_krw:,.0f}원 < {MIN_THRESHOLD:,.0f}원"
        )
        return True, None, remaining_value_krw

    return False, None, 0.0


def _check_profit_target(self, ...):
    """익절 체크 (수정 필요)"""
    # ... 기존 로직 ...

    for i, level in enumerate(profit_levels):
        if i in executed_levels:
            continue

        if profit_pct >= target:
            quantity_ratio = level.get("quantity_ratio", 100) / 100.0

            # ✅ 새 로직 추가
            has_problem, problem_level, problem_amount = self._will_have_insufficient_amount(
                symbol, position, profit_levels, i, current_price
            )

            if has_problem:
                logger.warning(
                    f"⚠️ {symbol} 레벨 {i}에서 전량 매도 결정\n"
                    f"   사유: {'레벨 ' + str(problem_level+1) if problem_level else '최종 잔여'} "
                    f"금액 {problem_amount:,.0f}원 < 5,500원"
                )
                quantity_ratio = 1.0  # 전량 매도

                # 텔레그램 알림
                self._send_telegram_alert(
                    f"⚠️ 자동 전량 매도\n"
                    f"코인: {symbol}\n"
                    f"레벨: {i}\n"
                    f"사유: 다음 레벨 금액 부족 ({problem_amount:,.0f}원)"
                )

            self._execute_sell(symbol, group_id, group, "profit", quantity_ratio, i)
            break
```

**테스트 시나리오**:
```
포지션: 10,000원
레벨 0: 40% @ +5% → 4,000원 (OK)
레벨 1: 30% @ +10% → 3,000원 (감지: 다음 2,000원)
레벨 2: 20% @ +15% → 2,000원 (X)

→ 레벨 1 도달 시:
   감지: 레벨 2가 2,000원 < 5,500원
   조치: 레벨 1에서 60% (전량) 매도
```

### 2. WebSocket 실시간 통합 (Medium Priority)

**필요성**: 익절/손절 타이밍 최적화

**현재**: 60초 REST API 폴링
**개선**: WebSocket 실시간 가격 스트림

**구현 위치**: `core/v4_trading_engine.py`

**가이드**:
```python
# core/upbit_websocket.py의 CandleWebSocket 활용

# 1. WebSocket 시작
self.candle_ws = CandleWebSocket(symbols=[...], candle_unit="1")
self.candle_ws.on_candle = self._on_candle_received

# 2. 콜백 처리
def _on_candle_received(self, candle_data):
    symbol = candle_data['market']
    close_price = candle_data['trade_price']

    # 포지션 가격 업데이트
    position = self.position_manager.update_price(symbol, close_price)

    # 익절/손절 체크
    # ...
```

**주의사항**:
- Rate Limit: 초당 5회, 분당 100회
- 이미 `core/upbit_websocket.py:CandleWebSocket` 구현되어 있음
- GUI의 `PriceWebSocketWorker`와 통합 고려

---

## 🎓 코드 컨벤션

### 1. 로그 레벨

```python
# 정상 동작
logger.info("✅ 매수 완료: ...")
logger.info("💰 매도 실행 중...")

# 경고 (동작은 하지만 주의)
logger.warning("⚠️ 부분 매도 금액 부족 → 전량 매도로 변경")
logger.warning("⚠️ 잔고 부족: ...")

# 에러 (동작 실패)
logger.error("❌ 매수 실패: ...")
logger.error("❌ API 에러: ...")

# 디버그 (verbose 모드)
if verbose:
    logger.info("         🔍 전략 찾기 결과: ...")
```

### 2. 주석

```python
# ✅ 핵심 로직 추가
has_problem = self._will_have_insufficient_amount(...)

# 🔧 Bug #1 수정: DCA 중복 실행 방지
self.position_manager.update_position(symbol, {
    "pending_order": {...}
})

# 🔴 그룹 관찰 모드 체크 (최우선)
if group.get("observation_only", False):
    return
```

### 3. 커밋 메시지

```bash
# Feature
feat: 포지션 테이블 그룹별 색상 구분

# Bug Fix
fix: DCA 중복 실행 방지 (pending_order 사전 저장)

# Refactor
refactor: Custom 모드 UI 단순화
```

---

## 📞 긴급 문제 해결

### 프로그램이 멈춤

```bash
# 1. 로그 확인
tail -f logs/trading_*.log

# 2. WebSocket 상태 확인
# 로그에서 "WebSocket 상태 체크" 검색

# 3. 강제 종료 후 재시작
# GUI: 거래 중지 → 프로그램 종료 → 재시작
```

### 포지션이 안 닫힘

```bash
# 1. pending_order 확인
cat data/positions_live.json | jq '.SYMBOL.pending_order'

# 2. pending_order가 있으면 수동 제거
# data/positions_live.json 직접 수정 또는
# GUI에서 수동 매도

# 3. 5분 대기 (timeout 후 자동 재시도)
```

### API 에러 반복

```bash
# 1. Rate Limit 확인
grep "Rate limit" logs/trading_*.log

# 2. 10초 대기 후 재시작

# 3. API 키 확인
# config/api_keys.json 확인
```

---

## 📚 참고 문서

- `README.md` - 프로젝트 전체 문서
- `CLAUDE.md` - Claude Code 가이드
- `WORK_SUMMARY_2025-11-17.md` - 오늘 작업 요약
- `docs/TELEGRAM_설정_가이드.md` - 텔레그램 설정
- `FAQ.md` - 자주 묻는 질문

---

## ✅ 세션 시작 체크리스트

다음 세션 시작 시 확인:

- [ ] 브랜치 확인: `claude/expert-strategy-backup-01KA4Aq841xqvr8BhrDAWDvf`
- [ ] 최신 커밋 pull: `git pull origin claude/expert-strategy-backup-01KA4Aq841xqvr8BhrDAWDvf`
- [ ] 실행 중인 프로그램 확인
- [ ] 로그 확인 (에러 없는지)
- [ ] 포지션 상태 확인
- [ ] 이 문서의 "즉시 수행할 작업" 섹션 확인

---

_다음 세션에서 바로 작업을 시작할 수 있도록 준비되었습니다._
_문제 발생 시 이 문서를 참고하세요._

**Happy Trading! 🚀**
