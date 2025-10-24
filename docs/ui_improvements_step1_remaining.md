# Step 1 활성 포지션 테이블 - 남은 개선사항

## ✅ 완료된 기능
- [x] 실시간 포지션 테이블 (8개 컬럼)
- [x] 동적 행 추가/제거 (매수/매도 시)
- [x] 색상 코딩 (빨강=수익, 파랑=손실, 검은색=중립)
- [x] 테이블 정렬 기능 (컬럼 헤더 클릭)
- [x] 포지션 요약 정보 (총 포지션 수, 전체 평가손익)

---

## 📋 남은 개선사항 (우선순위별)

### 3. 평균 단가 표시 (중간 우선순위)
**목적**: 물타기(추가 매수) 발생 시 평균 진입가 추적

**구현 방안**:
- 테이블에 "평균 단가" 컬럼 추가 (또는 "진입가" 컬럼과 통합)
- TradingEngine에서 물타기 로직 추가 필요
- 계산 공식: `(기존_진입가 * 기존_수량 + 추가_진입가 * 추가_수량) / 전체_수량`

**예상 작업량**: 30분

**참고 코드 위치**: 
- `core/trading_engine.py` - 물타기 로직 구현
- `gui/main_window.py:_on_coin_update()` - 평균 단가 표시

---

### 4. 빈 테이블 메시지 (낮은 우선순위)
**목적**: 포지션이 없을 때 사용자에게 안내 메시지 표시

**구현 방안**:
```python
if self.position_table.rowCount() == 0:
    # QLabel로 "현재 보유 중인 포지션이 없습니다" 메시지 표시
    # 또는 테이블 위에 반투명 오버레이로 표시
```

**예상 작업량**: 15분

**참고 코드 위치**: 
- `gui/main_window.py:_on_coin_update()` - 행 제거 후 확인
- `gui/main_window.py:_init_ui()` - 오버레이 위젯 추가

---

### 5. 컨텍스트 메뉴 (낮은 우선순위)
**목적**: 테이블 행 우클릭 시 추가 기능 제공

**구현 방안**:
- 테이블에 `customContextMenuRequested` 시그널 연결
- 메뉴 항목 예시:
  - "강제 매도" (수동 포지션 청산)
  - "상세 정보 보기" (다이얼로그로 거래 내역)
  - "차트 보기" (해당 코인 차트 팝업)

**예상 작업량**: 45분

**참고 코드**:
```python
self.position_table.setContextMenuPolicy(Qt.CustomContextMenu)
self.position_table.customContextMenuRequested.connect(self._show_position_menu)

def _show_position_menu(self, position):
    menu = QMenu(self)
    sell_action = menu.addAction("🔴 강제 매도")
    detail_action = menu.addAction("📊 상세 정보")
    # ...
    action = menu.exec_(self.position_table.viewport().mapToGlobal(position))
```

---

### 6. 색상 강도 조절 (낮은 우선순위)
**목적**: 수익/손실 크기에 따라 색상 강도 변화

**구현 방안**:
- 손익률 범위에 따라 색상 강도 조절
  - 0-2%: 연한 빨강/파랑
  - 2-5%: 중간 빨강/파랑
  - 5%+: 진한 빨강/파랑

**예상 작업량**: 20분

**참고 코드**:
```python
def _get_color_intensity(self, return_pct):
    if abs(return_pct) < 2:
        return QColor(255, 200, 200) if return_pct > 0 else QColor(200, 200, 255)
    elif abs(return_pct) < 5:
        return QColor(255, 100, 100) if return_pct > 0 else QColor(100, 100, 255)
    else:
        return Qt.red if return_pct > 0 else Qt.blue
```

---

## 💡 추가 아이디어 (미래 개선)

### 7. 포지션 알림 기능
- 특정 손익률 도달 시 알림 (예: +10%, -5%)
- 텔레그램 알림 연동

### 8. 포지션 히스토리
- 과거 청산된 포지션 기록 보기
- 거래 내역 CSV 내보내기

### 9. 차트 통합
- 테이블 행 더블클릭 시 미니 차트 팝업
- 진입가/현재가 표시

---

## 📌 구현 시 참고사항

### 핵심 파일 위치
- **GUI 메인**: `gui/main_window.py`
- **트레이딩 엔진**: `core/trading_engine.py`
- **멀티코인 워커**: `gui/multi_coin_worker.py`

### 데이터 흐름
```
TradingEngine (Ticker WebSocket 0.1-1s)
  ↓ last_price 업데이트
MultiCoinTrader.get_coin_status()
  ↓ 0.5초마다 폴링
MultiCoinWorker._status_update_loop()
  ↓ coin_update.emit(symbol, status)
MainWindow._on_coin_update()
  ↓ 테이블 업데이트
Position Table + Summary
```

### 색상 규칙 (한국 증시 규약)
- 🔴 **빨강**: 수익 (양수)
- 🔵 **파랑**: 손실 (음수)
- ⚫ **검은색**: 중립 (0 또는 상태)
- 배경색: `#ffe5e5` (수익), `#e5e5ff` (손실), `#f5f5f5` (중립)

---

**문서 작성일**: 2025-10-17
**작성자**: Claude Code
**프로젝트**: Upbit DCA Trader GUI Enhancement
