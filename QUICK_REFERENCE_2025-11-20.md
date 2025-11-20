# Quick Reference - 2025년 11월 20일 작업

## 🔍 바로 확인할 것들

### 1. 최종 커밋 확인
```bash
git log --oneline -1
# 05f715a - fix: 초기 매수 MyOrder WebSocket 콜백 등록 누락 수정
```

### 2. 핵심 수정 내용

#### 초기 매수 (05f715a) ⭐ 가장 중요!
```python
# Line 976-981: 콜백 등록 추가
if self.myorder_ws:
    self.myorder_ws.register_order_callback(order_uuid, self._on_order_completed)
```
**결과**: 초기 매수도 MyOrder WebSocket으로 처리 + 텔레그램 발송

#### DCA 중복 방지 (dea6f7a, 7854d0c)
```python
# Line 1946-1947, 2360-2362: 레벨 기록 추가
dca_levels_executed.append(level_index)

# Line 1131: 트리거 시점 체크
if i in dca_levels_executed:
    continue
```
**결과**: DCA 중복 실행 100% 방지

#### 익절/손절 포지션 업데이트 (0cd5b28)
```python
# Line 2053-2099: 수량 감소 로직
remaining_amount = total_amount - executed_volume
if remaining_value < 5000:
    close_position()
else:
    updates['total_amount'] = remaining_amount
```
**결과**: 2차 익절 시 `insufficient_funds_ask` 에러 해결

#### DCA 텔레그램 (a90765c)
```python
# Line 1954-1967, 2101-2114: 알림 추가
self._send_telegram_alert("🔄 DCA 추가 매수 완료...")
```
**결과**: DCA 완료 시 텔레그램 발송

---

## 🎯 테스트 우선순위

### 1순위: 초기 매수 (Critical!)
**확인할 로그**:
```
📡 [봇] ... MyOrder WebSocket 콜백 등록 완료  ← 이 로그가 핵심!
📬 주문 체결 이벤트 수신: ... state=done
✅ [봇] ... 초기 매수 체결 완료
```
**텔레그램**: `✅ [봇] 매수 완료`

**실패 시**:
- "🆕 외부 매수 감지" → 콜백 미등록 (버그!)

### 2순위: DCA 평균가
**확인 사항**:
- GUI 평균가 = Upbit 앱 평균가 (100% 일치)
- 로그: `📊 ... DCA 최종 평균가: {price}원`

### 3순위: 익절/손절 수량
**확인 사항**:
- 로그: `📊 ... 익절 매도 후 수량: {A} → {B}`
- GUI 포지션 수량 = 실제 잔고
- 2차 익절 시 에러 없음

### 4순위: 중복 방지
**확인할 로그**:
```
⚠️ ... DCA 레벨 {N} 이미 실행됨 → 중복 스킵
```

---

## 📊 처리 경로 비교

### 수정 전 (버그)
```
초기 매수: MyAsset + REST API (메인)
          → 텔레그램 없음
          → 그룹 할당 오류 가능

DCA:      state=trade 처리 (부정확)
          → MyAsset 덮어쓰기
          → 평균가 부정확

익절/손절: 레벨만 기록
          → 수량 미감소
          → 2차 실행 시 에러
```

### 수정 후 (정상)
```
초기 매수: MyOrder WebSocket (메인) ← 콜백 등록 추가!
          → 텔레그램 발송
          → 정확한 그룹 할당

DCA:      state=done 처리 (가중 평균)
          → MyAsset 스킵
          → 평균가 100% 정확
          → dca_levels_executed 기록

익절/손절: 레벨 기록 + 수량 감소
          → 정확한 잔고 추적
          → 연속 실행 가능
```

---

## 🚨 긴급 상황 대응

### 초기 매수 MyOrder 경로 안 탐
**증상**: "🆕 외부 매수 감지" 로그

**원인**: 콜백 미등록

**확인**:
```bash
grep "MyOrder WebSocket 콜백 등록 완료" logs/trading_*.log
```
없으면 → 코드 수정 안 된 것

**해결**:
```bash
git log --oneline -1  # 05f715a 확인
git diff HEAD~1 core/v4_trading_engine.py | grep "register_order_callback"
```

### DCA 평균가 틀림
**증상**: GUI 평균가 ≠ Upbit 앱 평균가

**원인**: state=trade 처리 또는 REST API 덮어쓰기

**확인**:
```bash
grep "DCA 최종 평균가" logs/trading_*.log
```

**해결**: 커밋 fd71c56 확인

### 익절/손절 에러
**증상**: `insufficient_funds_ask`

**원인**: 포지션 수량 미감소

**확인**:
```bash
grep "익절 매도 후 수량" logs/trading_*.log
```

**해결**: 커밋 0cd5b28 확인

---

## 📝 커밋 히스토리 (오늘 작업)

```
05f715a - 초기 매수 콜백 등록 ⭐ 최종
7854d0c - DCA 트리거 중복 체크
dea6f7a - DCA 레벨 기록
0cd5b28 - 익절/손절 수량 업데이트
a90765c - DCA 텔레그램
7c40e76 - 초기 매수 state=cancel
8d690e6 - 문서 수정
3f1bda5 - DCA state=cancel 처리
baaab79 - DCA 중복 방지
fd71c56 - DCA 평균가 개선
```

---

## 🎓 핵심 개념

### MyOrder WebSocket (메인)
- 주문 체결 시 콜백 실행
- `avg_price`: 가중 평균가 (정확!)
- `executed_volume`: 실제 체결 수량
- state=done/cancel 모두 처리

### MyAsset WebSocket + REST API (백업)
- MyOrder 처리 실패 시만 동작
- 5초 윈도우 체크
- REST API 평균가는 부정확할 수 있음

### 중복 방지 이중 체크
1. **pending_order** (실시간, 5분)
2. **\*_levels_executed** (영구, 배열)

---

## 💡 Tip

### 로그 필터링
```bash
# 초기 매수만
grep "봇.*매수" logs/trading_*.log

# DCA만
grep "DCA" logs/trading_*.log

# 익절/손절만
grep -E "(익절|손절)" logs/trading_*.log

# 텔레그램만
grep "_send_telegram_alert" logs/trading_*.log

# 에러만
grep "ERROR\|❌" logs/trading_*.log
```

### GUI vs Upbit 앱 비교
- 평균 매수가
- 보유 수량
- 총 투자 금액

**반드시 100% 일치해야 함!**

---

**문서 작성일**: 2025년 11월 20일
**브랜치**: claude/backup-copy-v4-01D6qnKRJSHFVEK1WJQRYzEH
**최종 커밋**: 05f715a
