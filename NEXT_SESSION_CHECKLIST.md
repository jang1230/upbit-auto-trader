# 🚀 다음 세션 빠른 시작 체크리스트

## ✅ 세션 시작 전 확인

```bash
# 1. 브랜치 확인
git branch --show-current
# 예상: claude/backup-from-v5-copy-01CL6M1nRo9EjaMa9wH9Hw3D

# 2. 최신 커밋 확인
git log -1 --oneline
# 예상: 6fab2e2 fix: 자동 매도(익절/손절) 중복 텔레그램 알림 방지

# 3. 작업 트리 클린 확인
git status
# 예상: nothing to commit, working tree clean

# 4. 가상환경 활성화 (필요시)
# source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows
```

---

## 🎯 우선 작업: 테스트 (예상 2-3시간)

### Test 1: 즉시매도 중복 알림 차단 (30분)
**목표**: 텔레그램 알림 정확히 1회만 전송

```bash
# 실행 단계
1. python main.py
2. GUI에서 포지션 선택 → "즉시매도" 클릭
3. 텔레그램 확인
4. 10초 이내 동일 코인 재매도 시도 (알림 없어야 함)
5. 10초 후 다른 코인 매도 (알림 있어야 함)

# 체크 항목
- [ ] 첫 매도 시 텔레그램 알림 1회
- [ ] 10초 이내 재매도 시 알림 없음
- [ ] GUI 로그 "🟢 즉시매도 완료" 표시
- [ ] MyAsset WebSocket 감지 시 "🔴 수동매도 감지" 없음
```

**실패 시 디버깅**:
```python
# gui/main_window.py:2142-2238 확인
# _execute_immediate_sell() 메서드 내부

# 1. recent_immediate_sells 등록 확인
print(f"DEBUG: recent_immediate_sells = {self.recent_immediate_sells}")

# 2. _on_balance_updated()에서 차단 로직 확인
# L1952-1959
```

---

### Test 2: 즉시매도 실제 체결가 사용 (30분)
**목표**: 알림 매도가 = Upbit 실제 체결가

```bash
# 실행 단계
1. python main.py
2. 호가 스프레드 큰 코인 선택 (예: 저유동성 코인)
3. "즉시매도" 클릭
4. 텔레그램 알림 매도가 메모
5. Upbit 웹/앱에서 "거래 내역" 확인
6. 매도가 일치 여부 검증

# 체크 항목
- [ ] 텔레그램 알림 매도가 = Upbit 체결가
- [ ] 호가 스프레드 5% 이상 코인도 정확
- [ ] GUI 성공 메시지에 실제 체결가 표시
- [ ] 로그에 체결가 기록
```

**실패 시 디버깅**:
```python
# gui/main_window.py:2177-2195 확인
# get_order() API 응답 처리

# 1. trades 배열 존재 확인
order_info = self.upbit_api.get_order(order_id)
print(f"DEBUG: order_info = {order_info}")

# 2. 가중 평균 계산 확인
trades = order_info.get('trades', [])
print(f"DEBUG: trades = {trades}")
```

---

### Test 3: 자동 매도(익절/손절) 중복 알림 차단 (1시간)
**목표**: 자동 매도 시 텔레그램 알림 1회만

```bash
# 준비: config/trading_config.json 수정
{
  "profit_targets": [
    {"price_ratio": 1.01, "quantity_ratio": 1.0}  # 1% 익절 (테스트용)
  ],
  "stop_losses": [
    {"price_ratio": 0.99, "quantity_ratio": 1.0}  # 1% 손절 (테스트용)
  ]
}

# 실행 단계
1. python main.py
2. V4 엔진 시작 (GUI에서 "시작" 버튼)
3. 포지션 생성 (자동 매수 대기 or 수동 매수)
4. 가격 변동 대기 (익절/손절 조건 충족)
5. 텔레그램 확인

# 체크 항목
- [ ] 자동 익절 시 텔레그램 알림 1회
- [ ] 자동 손절 시 텔레그램 알림 1회
- [ ] MyAsset WebSocket 감지 시 추가 알림 없음
- [ ] GUI 로그에 "자동 익절/손절" 메시지
```

**실패 시 디버깅**:
```python
# 1. 콜백 등록 확인
# gui/main_window.py:1348
print(f"DEBUG: callback registered = {self.v4_trading_engine.on_auto_sell_callback}")

# 2. 콜백 호출 확인
# core/v4_trading_engine.py:775-780, 814-819, 1165-1170, 1204-1209
# 각 위치에 print 추가
if self.on_auto_sell_callback:
    print(f"DEBUG: Calling auto_sell callback for {symbol}, type={sell_type}")
    self.on_auto_sell_callback(symbol, sell_type)

# 3. recent_immediate_sells 등록 확인
# gui/main_window.py:1360-1378
print(f"DEBUG: Added to recent_immediate_sells: {symbol}")
```

---

### Test 4: GUI 로그 필터링 (30분)
**목표**: 중요 메시지만 GUI에 표시

```bash
# 실행 단계
1. python main.py
2. V4 엔진 시작
3. 5분간 동작 관찰
4. GUI 로그 창 메시지 개수 세기
5. logs/ 폴더 로그 파일과 비교

# 체크 항목
- [ ] GUI 로그: 매수/매도/익절/손절만 표시
- [ ] "캔들 완성" 메시지 없음
- [ ] "체크 완료" 메시지 없음
- [ ] "WebSocket" 메시지 없음
- [ ] 로그 파일: 모든 메시지 기록
- [ ] 로그 개수 90% 이상 감소 (이전 대비)
```

**실패 시 디버깅**:
```python
# gui/logging_handler.py:58-139 확인
# should_show_in_gui() 메서드

# 1. 필터링 로직 테스트
handler = GuiLogHandler()
test_messages = [
    "매수 완료: KRW-BTC",  # 표시 O
    "캔들 완성: KRW-BTC",  # 표시 X
    "ERROR: API 오류",     # 표시 O
]
for msg in test_messages:
    result = handler.should_show_in_gui(logging.INFO, msg)
    print(f"{msg}: {'표시' if result else '숨김'}")

# 2. 백엔드 로거 핸들러 등록 확인
# gui/main_window.py:1280-1344
print(f"DEBUG: Backend loggers = {logging.getLogger().handlers}")
```

---

## 🐛 알려진 이슈 대응 계획

### Issue 1: recent_immediate_sells 메모리 누수
**현재 상태**: 10초 후 자동 제거 (코드로 구현됨)

**모니터링 방법**:
```python
# gui/main_window.py에 추가 (옵션)
def _monitor_recent_sells(self):
    """디버깅용: recent_immediate_sells 크기 출력"""
    size = len(self.recent_immediate_sells)
    if size > 10:  # 정상 범위 초과 시 경고
        self.logger.warning(f"⚠️ recent_immediate_sells 크기: {size}")
```

**개선 구현** (필요 시):
```python
# gui/main_window.py:__init__()에 추가
self.cleanup_timer = QtCore.QTimer()
self.cleanup_timer.timeout.connect(self._cleanup_old_sells)
self.cleanup_timer.start(60000)  # 1분마다

def _cleanup_old_sells(self):
    """10초 이상 경과한 항목 제거"""
    now = time.time()
    to_remove = [
        symbol for symbol, ts in self.recent_immediate_sells.items()
        if now - ts > 10
    ]
    for symbol in to_remove:
        del self.recent_immediate_sells[symbol]
    if to_remove:
        self.logger.debug(f"🧹 Cleaned up old sells: {to_remove}")
```

---

### Issue 2: 자동 매도 콜백 재등록
**현재 상태**: V4 엔진 시작 시 1회 등록

**추가 체크 필요**:
```python
# gui/main_window.py:_on_stop_clicked() 확인
# V4 엔진 재시작 시 콜백 재등록 여부
```

**개선 구현** (필요 시):
```python
# gui/main_window.py:_on_start_clicked()
def _on_start_clicked(self):
    # ... 기존 코드 ...

    # 콜백 재등록 (재시작 대비)
    if self.v4_trading_engine:
        self.v4_trading_engine.on_auto_sell_callback = self._on_auto_sell_executed
        self.logger.info("✅ 자동 매도 콜백 재등록 완료")
```

---

### Issue 3: get_order() API Rate Limit
**현재 상태**: 즉시매도당 1회 호출

**모니터링 방법**:
```python
# api/upbit_api.py에서 Rate Limit 로깅 확인
# UpbitAPI.get_order() 호출 시 _check_rate_limit() 자동 실행
```

**개선 구현** (필요 시):
```python
# gui/main_window.py:_execute_immediate_sell()
# API 호출 전 Rate Limit 체크 추가
if not self.upbit_api._can_make_request("order"):
    self.logger.warning("⚠️ Rate Limit 도달, 1초 대기")
    time.sleep(1)
```

---

## 📊 테스트 결과 기록 템플릿

```markdown
# 테스트 결과 - 2025-11-XX

## Test 1: 즉시매도 중복 알림 차단
- [ ] PASS / [ ] FAIL
- 테스트 시간:
- 텔레그램 알림 횟수:
- 비고:

## Test 2: 즉시매도 실제 체결가 사용
- [ ] PASS / [ ] FAIL
- 알림 매도가:
- Upbit 체결가:
- 오차:
- 비고:

## Test 3: 자동 매도 중복 알림 차단
- [ ] PASS / [ ] FAIL
- 익절 알림 횟수:
- 손절 알림 횟수:
- 비고:

## Test 4: GUI 로그 필터링
- [ ] PASS / [ ] FAIL
- GUI 로그 개수:
- 파일 로그 개수:
- 감소율:
- 비고:

## 발견된 버그
1.
2.

## 개선 사항
1.
2.
```

---

## 🔧 버그 수정 시 워크플로우

```bash
# 1. 버그 재현
python main.py
# → 버그 발생 조건 기록

# 2. 디버깅 로그 추가
# 해당 파일에 print() 또는 self.logger.debug() 추가

# 3. 수정 후 테스트
python main.py
# → 버그 해결 확인

# 4. 커밋
git add <수정된_파일>
git commit -m "fix: <버그_설명>"

# 5. 푸시
git push -u origin claude/backup-from-v5-copy-01CL6M1nRo9EjaMa9wH9Hw3D
```

---

## 📚 빠른 코드 참조

### 즉시매도 관련
```python
# gui/main_window.py

# L2142-2238: _execute_immediate_sell()
# - L2177-2195: get_order() 체결가 조회
# - L2200-2202: recent_immediate_sells 등록
```

### 자동 매도 관련
```python
# core/v4_trading_engine.py
# L775-780: 익절 매도 콜백 (모니터링 루프)
# L814-819: 손절 매도 콜백 (모니터링 루프)
# L1165-1170: 익절 매도 콜백 (DCA 루프)
# L1204-1209: 손절 매도 콜백 (DCA 루프)

# gui/main_window.py
# L1360-1378: _on_auto_sell_executed() 콜백 핸들러
# L1348: 콜백 등록 (V4 엔진 시작 시)
```

### 로그 필터링 관련
```python
# gui/logging_handler.py
# L58-139: should_show_in_gui() 필터링 로직

# gui/main_window.py
# L1280-1344: _setup_backend_logging() 핸들러 등록
# L1346-1358: _on_backend_log() Signal 핸들러
```

---

## 🎯 세션 종료 시 체크리스트

```bash
# 1. 변경 사항 커밋
git add .
git commit -m "test: <테스트_내용> 또는 fix: <버그_수정>"

# 2. 푸시
git push -u origin claude/backup-from-v5-copy-01CL6M1nRo9EjaMa9wH9Hw3D

# 3. 테스트 결과 기록 (위 템플릿 사용)

# 4. 다음 세션 계획 업데이트
# → 이 파일(NEXT_SESSION_CHECKLIST.md) 수정
```

---

**작성일**: 2025-11-24
**예상 테스트 소요시간**: 2-3시간
**예상 버그 수정 소요시간**: 1-2시간 (버그 발견 시)

**다음 세션 목표**: 모든 테스트 PASS → 안정화 완료
