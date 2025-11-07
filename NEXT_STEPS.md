# MyAsset WebSocket 통합 완료 - 다음 단계

**작업 완료일**: 2025-01-26
**브랜치**: claude/fix-rate-limit-bugs-011CUsYs6G9xGN3EPCMU7DAi
**완료 커밋**: 38c1c00 - fix(myasset): Fix average price not updating on additional buy

---

## 🔴 1. 중요: 평균매수가 변경 시 REST API 필수!

### ⚠️ 핵심 원칙

**MyAsset WebSocket에는 `avg_buy_price` 필드가 없습니다!**

공식 문서 (`upbit_docs/reference/websocket-myasset.md`) 확인 결과:
- ✅ 제공: `currency`, `balance`, `locked`
- ❌ 미제공: `avg_buy_price`, `avg_buy_price_modified`

### 언제 REST API를 호출해야 하나?

```
✅ REST API 필수: 평균가가 변하는 경우
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 추가 매수 (수량 증가)
   → 평균가 재계산 필요
   → MyAsset WebSocket에 avg_buy_price 없음
   → REST API get_accounts() 호출 필수

⚠️ REST API 선택적: 평균가가 안 바뀌는 경우
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. 부분 매도 (수량 감소)
   → 평균가 그대로 유지
   → 기존 average_price 재사용 가능
   → 현재는 안전을 위해 REST API 호출 중 (보수적 접근)
```

### 코드 위치

**core/position_manager.py:627-654**

```python
# 수량이 변경되었으면 평균가도 바뀌었을 가능성 → REST API 조회
if abs(balance - existing_amount) > 0.00000001:
    logger.warning(f"⚠️ {symbol} 수량 변동 감지, REST API로 평균가 조회")
    if self.upbit_api:
        accounts = self.upbit_api.get_accounts()
        for acc in accounts:
            if f"KRW-{acc['currency']}" == symbol:
                fetched_avg_price = float(acc.get('avg_buy_price', 0))
                updates['average_price'] = fetched_avg_price
                updates['total_invested_krw'] = fetched_avg_price * balance
                logger.info(f"📊 REST API 평균가 조회: {symbol} = {fetched_avg_price:.0f}원")
                break
```

### 시스템 아키텍처

```
Three-Stream System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Ticker WebSocket (가격 업데이트)
   - 주기: ~0.5초마다
   - 용도: 실시간 현재가
   - 데이터: trade_price, change_rate

2️⃣ MyAsset WebSocket (잔고 변동 감지 트리거)
   - 주기: 거래 발생 시에만
   - 용도: 잔고 변동 감지
   - 데이터: currency, balance, locked
   - ⚠️ avg_buy_price 없음!

3️⃣ REST API (상세 정보 조회)
   - 주기: 필요 시 (수량 변동 감지 시)
   - 용도: 평균매수가 조회
   - 데이터: avg_buy_price, avg_buy_price_modified
   - Rate Limit: 초당 30회

Flow:
MyAsset 변동 신호
  → 수량 변동 체크 (balance != existing_amount)
    → REST API 호출 (평균가 조회)
      → GUI 업데이트
```

---

## 📋 2. 다음 작업 단계

### Phase 1: 즉시 진행 (테스트 단계) ⚡

#### 1-1. 추가 매수 시나리오 재테스트 (최우선!)

```bash
실행 순서:
1. GUI 실행: python main.py
2. 모니터 탭에서 CLI 로그 확인
3. Upbit 앱에서 BTC 추가 매수 (5만원)
4. 5-10초 내 자동 동기화 대기
5. 로그 확인 포인트:
   ✓ "💰 잔고 변동: BTC - 잔액: X.XXXXXXXX"
   ✓ "⚠️ KRW-BTC 수량 변동 감지, REST API로 평균가 조회"
   ✓ "📊 REST API 평균가 조회: KRW-BTC = XXX원"
   ✓ "📊 수량 변동: KRW-BTC" (사용자 알림)
6. GUI 확인 포인트:
   ✓ 수량 증가
   ✓ 평균가 변경 (이전과 다름)
   ✓ 평가손익 재계산
   ✓ 수익률(%) 재계산
```

**예상 로그 예시**:
```
[2025-01-26 15:30:45] 💰 잔고 변동: BTC - 잔액: 0.00012345, 주문중: 0.00000000, 평균가: 0원
[2025-01-26 15:30:45] ⚠️ KRW-BTC 수량 변동 감지 (기존: 0.00006975 → 신규: 0.00012345), REST API로 평균가 조회
[2025-01-26 15:30:46] 📊 REST API 평균가 조회: KRW-BTC = 95000000원
[2025-01-26 15:30:46] 📊 수량 변동: KRW-BTC
```

#### 1-2. 전체 거래 사이클 테스트

```
Step 1: BTC 초기 매수 (10만원)
  → 포지션 생성 확인

Step 2: BTC 추가 매수 (5만원)
  → 평균가 변경 확인
  → REST API 로그 확인

Step 3: BTC 부분 매도 (50%)
  → 평균가 유지 확인
  → GUI 수량/손익 업데이트 확인

Step 4: BTC 전체 매도 (100%)
  → 포지션 삭제 확인
  → 테이블에서 사라지는지 확인
```

#### 1-3. TEST_SCENARIOS.md 시나리오 6-9 진행

현재 1-5번 완료, 나머지 엣지 케이스 테스트 진행

---

### Phase 2: 중기 작업 (최적화) 🔧

#### 2-1. REST API 호출 최적화 검토

**현재 (보수적 접근)**:
```python
# 수량 변동 시 무조건 호출
if abs(balance - existing_amount) > 0.00000001:
    call_rest_api()  # 증가/감소 모두
```

**최적화 옵션 (공격적 접근)**:
```python
# 수량 증가 시만 호출
if balance > existing_amount + 0.00000001:
    call_rest_api()  # 증가만
else:
    reuse_existing_avg_price()  # 감소는 재사용
```

**Trade-off**:
- 장점: API 호출 50% 절감 (부분 매도 시 호출 안 함)
- 단점: 엣지 케이스에서 평균가 불일치 위험 (예: 동시 거래)

**권장 사항**:
- 현재는 안정성 우선으로 보수적 접근 유지
- 1주일 실거래 모니터링 후 최적화 검토

#### 2-2. 장기 모니터링

```
□ 실거래 환경에서 1주일 모니터링
□ REST API 호출 빈도 통계 수집
  - 추가 매수: N회
  - 부분 매도: M회
  - 전체 매도: K회
□ Rate Limit 위험 평가 (초당 30회 제한)
□ 평균가 불일치 사례 수집
```

---

### Phase 3: 장기 작업 (선택적) 🚀

#### 3-1. WebSocket 실시간 가격 업데이트 통합

```
현재: 60초 폴링 방식 (정상 동작 중)
개선: Ticker WebSocket으로 0.5초 실시간 업데이트

장점:
- GUI 반응성 향상
- 실시간 수익률 표시

단점:
- CPU 사용량 증가
- 복잡도 증가

우선순위: Low (현재 방식으로도 충분)
```

#### 3-2. Unit Test 추가

```python
tests/test_position_manager.py

test_sync_from_myasset_additional_buy()
  - 수량 증가 → REST API 호출 확인
  - 평균가 업데이트 확인

test_sync_from_myasset_partial_sell()
  - 수량 감소 → 평균가 유지 확인
  - total_invested_krw 재계산 확인

test_sync_from_myasset_full_sell()
  - balance+locked=0 → 포지션 삭제 확인

test_sync_from_myasset_incremental_update()
  - 일부 코인만 전송 → 다른 포지션 유지 확인
```

---

## 🧪 3. 현재 테스트해야 할 부분

### ✅ 이미 검증 완료

- [x] 중복 API 호출 제거
  - 로그: "✅ 캐시된 accounts 데이터 사용 (중복 API 호출 방지)"
  - Step1에서 가져온 데이터를 Step2에서 재사용

- [x] 부분 매도 시 GUI 업데이트
  - 테스트: SOL 50% 매도
  - 결과: 수량/손익 정상 업데이트, 다른 포지션 유지

- [x] 전체 매도 시 포지션 삭제
  - 테스트: ETH 100% 매도
  - 결과: GUI에서 정상 삭제

- [x] 증분 업데이트 처리
  - 문제: SOL 매도 시 BTC/ETH/XRP 삭제됨
  - 해결: balance+locked=0인 경우만 삭제

---

### 🔄 추가 검증 필요 (Critical!)

#### ⭐ 시나리오 A: 추가 매수 (최우선!)

```
목적: 평균가 업데이트 로직 검증

준비:
  - 현재 보유: BTC 0.00006975개
  - 평균가: 약 95,000,000원

실행:
  1. Upbit 앱에서 BTC 5만원 추가 매수
  2. GUI 로그 모니터링

예상 로그:
  💰 잔고 변동: BTC - 잔액: 0.000XXXXX, 주문중: 0.00000000, 평균가: 0원
  ⚠️ KRW-BTC 수량 변동 감지 (기존: 0.00006975 → 신규: 0.000XXXXX), REST API로 평균가 조회
  📊 REST API 평균가 조회: KRW-BTC = XXXXXX원
  📊 수량 변동: KRW-BTC

예상 GUI 변화:
  - 수량: 0.00006975 → 0.000XXXXX (증가)
  - 평균가: 95,000,000원 → XXXXXX원 (변경됨!)
  - 평가손익: 재계산됨
  - 수익률(%): 재계산됨
  - 포지션 색상: 수익/손실에 따라 변경

확인 포인트:
  ✓ REST API 호출 로그 출력 (가장 중요!)
  ✓ 평균가가 이전과 달라짐 (혼합 평균)
  ✓ total_invested_krw = 신규평균가 × 신규수량
  ✓ profit_krw = current_value - total_invested
```

#### 시나리오 B: 연속 거래 사이클

```
1단계: BTC 초기 매수 (10만원)
  → 포지션 생성
  → 평균가1 기록

2단계: BTC 추가 매수 (5만원)
  → REST API 로그 확인
  → 평균가2 = (평균가1×수량1 + 현재가×수량2) / 총수량
  → 평균가1 ≠ 평균가2 확인

3단계: BTC 부분 매도 (50%)
  → 평균가2 유지 확인 (변경 없어야 함)
  → 수량만 감소
  → 손익 재계산

4단계: BTC 전체 매도 (100%)
  → 포지션 삭제
  → 테이블에서 사라짐
```

#### 시나리오 C: 동시 다중 코인

```
목적: MyAsset 증분 업데이트 처리 검증

1. BTC 추가 매수 실행
2. 즉시 (5초 내) ETH 부분 매도 실행
3. 확인:
   - BTC: 수량↑, 평균가 변경, REST API 호출
   - ETH: 수량↓, 평균가 유지
   - 다른 포지션(SOL, XRP 등): 변경 없음
```

---

### 테스트 실행 방법

```bash
# 1. GUI 실행
python main.py

# 2. 모니터 탭 → CLI 로그 영역 확인
#    (자동 스크롤 켜기)

# 3. Upbit 앱에서 실제 거래 실행

# 4. 5-10초 내 MyAsset WebSocket 신호 수신
#    → 자동 동기화 시작

# 5. 로그 확인 (아래 체크리스트)
```

---

### 로그 확인 체크리스트

**추가 매수 시 (예: BTC 5만원)**:
```
✓ [ ] 💰 잔고 변동: BTC - 잔액: X.XXXXXXXX, 주문중: 0.00000000, 평균가: 0원
✓ [ ] ⚠️ KRW-BTC 수량 변동 감지 (기존: Y.YYYYYYYY → 신규: X.XXXXXXXX), REST API로 평균가 조회
✓ [ ] 📊 REST API 평균가 조회: KRW-BTC = ZZZZZZ원
✓ [ ] 📊 수량 변동: KRW-BTC
```

**부분 매도 시 (예: ETH 50%)**:
```
✓ [ ] 💰 잔고 변동: ETH - 잔액: X.XXXXXXXX, 주문중: 0.00000000
✓ [ ] 📊 수량 변동: KRW-ETH
```

**전체 매도 시 (예: SOL 100%)**:
```
✓ [ ] 💰 잔고 변동: SOL - 잔액: 0.00000000, 주문중: 0.00000000
✓ [ ] 🗑️ 매도 감지: KRW-SOL
```

---

### GUI 확인 체크리스트

**추가 매수 후**:
```
컬럼별 확인:
✓ [ ] 심볼: 변경 없음
✓ [ ] 수량: 증가함 (이전보다 많음)
✓ [ ] 평균가: 변경됨 (이전과 다른 값)
✓ [ ] 현재가: 실시간 업데이트 중
✓ [ ] 평가손익: 재계산됨 (= 현재가치 - 투자금)
✓ [ ] 수익률(%): 재계산됨 (= 평가손익/투자금 × 100)
✓ [ ] 포지션 색상: 수익(초록)/손실(빨강) 상태 반영
```

**부분 매도 후**:
```
컬럼별 확인:
✓ [ ] 수량: 감소함
✓ [ ] 평균가: 변경 없음 (이전과 동일)
✓ [ ] 평가손익: 재계산됨 (수량 변화 반영)
✓ [ ] 수익률(%): 재계산됨
```

**전체 매도 후**:
```
✓ [ ] 포지션 테이블에서 해당 행 삭제됨
✓ [ ] 다른 포지션들은 그대로 유지됨
```

---

## 📝 완료된 버그 수정 요약

### 커밋 히스토리

1. **a9336b8** - fix: Add logger import and fix locked balance handling
   - NameError: 'logger' is not defined 수정
   - locked 잔고 포함 로직 추가 (balance + locked)

2. **2b55841** - fix(myasset): Fix critical bugs in MyAsset WebSocket sync logic
   - 증분 업데이트 처리 (다른 포지션 삭제 방지)
   - balance+locked=0인 경우만 포지션 삭제

3. **3ebc30a** - fix(myasset): Fix profit_krw calculation bug in partial sell scenarios
   - avg_buy_price 폴백 로직 추가
   - total_invested_krw 재계산 로직 수정

4. **f9c8e4e** - perf: Remove duplicate get_accounts() API call in initialization
   - Step1/Step2 중복 API 호출 제거
   - accounts 캐싱 메커니즘 구현

5. **b2334c0** - fix(gui): Fix additional buy not updating GUI in real-time
   - synced_positions를 GUI 리로드 조건에 추가
   - "📊 수량 변동" 사용자 알림 추가

6. **38c1c00** - fix(myasset): Fix average price not updating on additional buy
   - 수량 변동 감지 로직 추가
   - REST API 호출 트리거 구현

---

## 🎯 성공 기준

다음 조건들이 모두 만족되면 MyAsset WebSocket 통합이 완전히 성공한 것입니다:

### 기능 요구사항
- [x] 부분 매도 시 GUI 실시간 업데이트
- [x] 전체 매도 시 포지션 자동 삭제
- [x] 증분 업데이트 처리 (다른 포지션 유지)
- [ ] **추가 매수 시 평균가 업데이트** ← 최종 검증 필요!

### 성능 요구사항
- [x] 중복 API 호출 제거 (50% 절감)
- [x] 5-10초 내 실시간 동기화
- [x] Rate Limit 준수 (REST: 30회/초, WS: 5회/초)

### 안정성 요구사항
- [x] 예외 처리 (로거 누락 수정)
- [x] 엣지 케이스 처리 (locked 잔고, 0 평균가)
- [ ] 1주일 무중단 운영 검증

---

## 📚 참고 자료

### 코드 파일
- `core/position_manager.py` - 포지션 동기화 핵심 로직
- `gui/main_window.py` - GUI 초기화 및 리프레시
- `gui/myasset_websocket_worker.py` - WebSocket 워커

### 문서
- `upbit_docs/reference/websocket-myasset.md` - MyAsset 공식 스펙
- `CLAUDE.md` - 프로젝트 전체 구조
- `TEST_SCENARIOS.md` - 테스트 시나리오 (있다면)

### 관련 이슈
- MyAsset WebSocket 필드에 avg_buy_price 없음 (공식 확인)
- 증분 업데이트 방식 (변동 자산만 전송)
- Rate Limit: REST 30회/초, WebSocket 5회/초·100회/분

---

**마지막 업데이트**: 2025-01-26
**다음 체크포인트**: 추가 매수 시나리오 테스트 완료 후 업데이트
**담당자**: Claude (claude/fix-rate-limit-bugs-011CUsYs6G9xGN3EPCMU7DAi)
