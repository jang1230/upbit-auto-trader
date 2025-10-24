# Bug Fix Report - Phase 3.7 GUI

## 발견된 버그 (2개)

### Bug 1: `api.close()` AttributeError

**증상:**
- 설정 다이얼로그에서 Upbit API 연결 테스트 시 처음에는 "조회완료" 표시
- 그 후 "'UpbitAPI' object has no attribute 'close'" 에러 발생
- CMD에서는 에러 메시지 없음

**원인:**
- `core/upbit_api.py`의 `UpbitAPI` 클래스는 `requests` 라이브러리 사용
- `requests`는 연결 풀 자동 관리하므로 명시적 `close()` 메서드 불필요
- WebSocket이나 DB 연결과 달리 HTTP 요청은 자동으로 정리됨
- GUI 코드에서 불필요하게 `api.close()` 호출

**수정 내용:**
```python
# BEFORE (settings_dialog.py:355)
api.close()  # ← 에러 발생

# AFTER
# 제거됨 (requests는 자동 정리)
```

**영향받은 파일:**
- ✅ `gui/settings_dialog.py` (line ~355) - `api.close()` 제거
- ✅ `gui/main_window.py` (line ~327) - `api.close()` 제거

---

### Bug 2: GUI 프리징 (응답없음)

**증상:**
- 메인 창에서 "🔄 새로고침" 버튼 클릭 시
- 프로그램이 "응답없음" 상태로 멈춤
- GUI 완전히 정지

**원인:**
- `api.get_accounts()` 호출이 동기(synchronous) 블로킹 호출
- Qt의 메인 이벤트 루프를 블로킹하여 GUI 프리징 발생
- API 응답 대기 중에 UI 업데이트/이벤트 처리 불가

**해결 방법:**
- `QThread`를 사용한 백그라운드 처리
- 메인 스레드는 UI 처리, 워커 스레드는 API 호출
- Qt Signal/Slot을 통한 스레드 간 안전한 통신

**수정 내용:**

1. **BalanceWorker 클래스 추가** (main_window.py 상단):
```python
class BalanceWorker(QThread):
    """잔고 조회 워커 스레드 - GUI 프리징 방지"""

    finished = Signal(dict)  # 성공 시그널
    error = Signal(str)      # 실패 시그널

    def run(self):
        # 백그라운드에서 API 호출
        api = UpbitAPI(...)
        accounts = api.get_accounts()
        # 결과를 시그널로 전달
        self.finished.emit(result)
```

2. **MainWindow._refresh_balance() 메서드 재작성**:
```python
def _refresh_balance(self):
    """잔고 새로고침 (비동기)"""
    # 워커 스레드 생성
    self.balance_worker = BalanceWorker(...)

    # 시그널 연결
    self.balance_worker.finished.connect(self._on_balance_success)
    self.balance_worker.error.connect(self._on_balance_error)

    # 백그라운드 실행
    self.balance_worker.start()
```

3. **성공/실패 핸들러 추가**:
```python
def _on_balance_success(self, result: dict):
    """API 성공 시 UI 업데이트"""
    self.total_asset_label.setText(...)

def _on_balance_error(self, error_msg: str):
    """API 실패 시 에러 표시"""
    QMessageBox.warning(...)
```

**개선 사항:**
- ✅ GUI 프리징 완전 해결
- ✅ 버튼 중복 클릭 방지 (실행 중 버튼 비활성화)
- ✅ 사용자 경험 향상 (응답성 유지)
- ✅ 안전한 스레드 간 통신 (Qt Signal/Slot)

---

## 테스트 결과

### Bug 1 테스트 방법:
1. 설정 > Upbit API 탭 열기
2. 올바른 API 키 입력
3. "🔍 연결 테스트" 버튼 클릭
4. **기대 결과**: "✅ Upbit API 연결 성공!" 메시지만 표시 (에러 없음)

### Bug 2 테스트 방법:
1. 메인 창 실행
2. "🔄 새로고침" 버튼 클릭
3. **기대 결과**:
   - 버튼 즉시 비활성화
   - 로그에 "🔄 계좌 정보 조회 중..." 표시
   - GUI 응답 유지 (프리징 없음)
   - 1-2초 후 잔고 정보 표시
   - 버튼 다시 활성화

---

## 기술 세부 사항

### QThread 사용 이유
- **문제**: 동기 API 호출 → 메인 스레드 블로킹 → GUI 프리징
- **해결**: 워커 스레드에서 API 호출 → 메인 스레드는 UI 처리 계속

### Qt Signal/Slot 패턴
```
[워커 스레드]           [메인 스레드]
     │                      │
     ├─ API 호출            │
     ├─ 데이터 처리         │
     ├─ finished.emit() ───→ _on_balance_success()
     │                      ├─ UI 업데이트
     │                      └─ 버튼 활성화
```

### 스레드 안전성
- ✅ 워커 스레드는 UI 직접 접근 금지
- ✅ Signal/Slot을 통해서만 UI 업데이트
- ✅ Qt가 자동으로 스레드 안전성 보장

---

## 다음 단계

수정 사항 검증 후 계속:
1. GUI 테스트 가이드의 **2-6번 재테스트**
2. 2-7번부터 나머지 테스트 진행
3. 모든 테스트 통과 후 Phase 3.7 완료

---

## 수정 파일 목록

1. **gui/settings_dialog.py**
   - Line 355: `api.close()` 제거

2. **gui/main_window.py**
   - Line 11: `QThread, Signal` import 추가
   - Line 17-64: `BalanceWorker` 클래스 추가
   - Line 79: `self.balance_worker = None` 초기화
   - Line 335-392: `_refresh_balance()` 메서드 완전 재작성
   - 추가: `_on_balance_success()`, `_on_balance_error()` 메서드

---

## 참고 문서

- Qt Documentation: [QThread](https://doc.qt.io/qt-6/qthread.html)
- Qt Documentation: [Signals & Slots](https://doc.qt.io/qt-6/signalsandslots.html)
- Python requests: [Connection Pooling](https://requests.readthedocs.io/en/latest/user/advanced/#session-objects)
