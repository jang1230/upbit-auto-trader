# Phase 4 완료 보고서 - Semi-Auto Trading System

## 📋 개요

**Phase 4: 반자동 트레이딩 시스템 (Semi-Auto Mode)**

사용자가 Upbit에서 수동으로 매수한 포지션을 자동으로 감지하고, DCA 및 익절/손절을 자동으로 관리하는 시스템 구현 완료.

**구현 기간**: 2024-10-23  
**상태**: ✅ 완료 및 테스트 검증 완료

---

## 🎯 핵심 기능

### 1. PositionDetector (포지션 감지기)

**파일**: `/core/position_detector.py`

**주요 클래스**:
- `Position`: 포지션 정보를 담는 데이터 클래스
- `PositionDetector`: 수동 매수 감지 및 포지션 관리

**핵심 기능**:
```python
# 1. 포지션 스캔
result = detector.scan_positions()
# Returns: {
#   'managed': [관리 중인 포지션],
#   'manual': [수동 매수 포지션],
#   'new_manual': [새로 감지된 수동 매수]
# }

# 2. 관리 포지션 등록
detector.register_managed_position(symbol, position)

# 3. 관리 포지션 해제
detector.unregister_managed_position(symbol)

# 4. 포지션 조회
position = detector.get_position('KRW-BTC')

# 5. 관리 여부 확인
is_managed = detector.is_managed('KRW-BTC')
```

**테스트 결과**: ✅ 5개 테스트 모두 통과
- ✓ 초기 포지션 스캔
- ✓ 관리 포지션 등록
- ✓ 새로운 수동 매수 감지
- ✓ 포지션 청산 처리
- ✓ 관리 포지션 수량 업데이트

---

### 2. SemiAutoManager (반자동 관리자)

**파일**: `/core/semi_auto_manager.py`

**주요 클래스**:
- `ManagedPosition`: 관리 중인 포지션 상태 추적
- `SemiAutoManager`: 전체 반자동 트레이딩 관리

**핵심 워크플로우**:

```
1. 포지션 스캔 (주기적, 기본 10초)
   ↓
2. 새로운 수동 매수 감지
   → 감지 시 ManagedPosition 생성
   → PositionDetector에 관리 포지션 등록
   ↓
3. 관리 중인 포지션에 대해:
   ├─ DCA 체크 (가격 하락 시 자동 추가 매수)
   ├─ 익절 체크 (목표 수익률 도달 시 자동 매도)
   └─ 손절 체크 (손실 한도 도달 시 자동 매도)
```

**주요 기능**:

#### (1) 수동 매수 감지
```python
async def _on_new_manual_buy(self, position: Position):
    """
    사용자가 Upbit에서 수동 매수 시:
    1. 현재 가격 조회
    2. ManagedPosition 생성 (감지 시점 가격 기록)
    3. PositionDetector에 등록
    4. 알림 전송
    """
```

#### (2) DCA 자동 실행
```python
async def _check_dca(self, managed: ManagedPosition, current_price: float):
    """
    가격이 기준점 대비 설정된 %만큼 하락 시:
    1. DCA 레벨 확인 (level_config.drop_pct)
    2. 설정된 금액만큼 자동 매수 (level_config.order_amount)
    3. executed_dca_levels에 기록하여 중복 방지
    """
```

**DCA 설정 예시**:
```python
dca_levels = [
    DcaLevelConfig(level=0, drop_pct=0.0, weight_pct=50.0, order_amount=500000),
    DcaLevelConfig(level=1, drop_pct=-10.0, weight_pct=25.0, order_amount=250000),
    DcaLevelConfig(level=2, drop_pct=-20.0, weight_pct=15.0, order_amount=150000),
]
```

#### (3) 익절 자동 실행
```python
async def _check_take_profit(self, managed: ManagedPosition, current_price: float):
    """
    수익률이 목표치 도달 시:
    1. 평균 단가 대비 수익률 계산
    2. take_profit_pct 이상이면 전량 매도
    3. 포지션 제거 및 알림
    """
```

#### (4) 손절 자동 실행
```python
async def _check_stop_loss(self, managed: ManagedPosition, current_price: float):
    """
    손실률이 한도 도달 시:
    1. 평균 단가 대비 손실률 계산
    2. stop_loss_pct 이하이면 전량 매도
    3. 포지션 제거 및 알림
    """
```

**테스트 결과**: ✅ 4개 테스트 모두 통과
- ✓ 수동 매수 감지 및 관리 시작
- ✓ DCA 추가 매수 자동 실행
- ✓ 익절 자동 실행
- ✓ 손절 자동 실행

---

## 📊 시스템 구조

```
사용자 Upbit 수동 매수
         ↓
    Upbit API
         ↓
PositionDetector.scan_positions()
         ↓
    새 포지션 감지?
         ↓ Yes
SemiAutoManager._on_new_manual_buy()
         ↓
   ManagedPosition 생성
   (signal_price 기록)
         ↓
    주기적 체크 (10초)
         ↓
    현재 가격 조회
         ↓
  ┌──────┴──────┐
  ↓             ↓
DCA 체크    익절/손절 체크
  ↓             ↓
조건 만족?    조건 만족?
  ↓ Yes        ↓ Yes
자동 매수    자동 매도
  ↓             ↓
포지션 업데이트  포지션 제거
```

---

## 🔧 설정 구조

### AdvancedDcaConfig

```python
@dataclass
class AdvancedDcaConfig:
    levels: List[DcaLevelConfig]       # DCA 레벨별 설정
    take_profit_pct: float             # 익절 목표 (%)
    stop_loss_pct: float               # 손절 한도 (%)
    total_capital: int                 # 총 투자 가능 자산
    enabled: bool                      # DCA 활성화 여부
```

### DcaLevelConfig

```python
@dataclass
class DcaLevelConfig:
    level: int          # 레벨 번호 (0=초기, 1,2,3...=추가 매수)
    drop_pct: float     # 하락률 (%, 0=초기 진입)
    weight_pct: float   # 매수 비중 (%)
    order_amount: int   # 주문 금액 (원)
```

---

## 💡 사용 예시

### 기본 사용법

```python
from core.semi_auto_manager import SemiAutoManager
from core.upbit_api import UpbitAPI
from core.order_manager import OrderManager
from gui.dca_config import AdvancedDcaConfig, DcaLevelConfig

# 1. API 및 주문 관리자 준비
upbit_api = UpbitAPI(access_key, secret_key)
order_manager = OrderManager(upbit_api, dry_run=False)

# 2. DCA 설정
dca_levels = [
    DcaLevelConfig(level=0, drop_pct=0.0, weight_pct=50.0, order_amount=500000),
    DcaLevelConfig(level=1, drop_pct=-10.0, weight_pct=25.0, order_amount=250000),
    DcaLevelConfig(level=2, drop_pct=-20.0, weight_pct=15.0, order_amount=150000),
]

dca_config = AdvancedDcaConfig(
    levels=dca_levels,
    take_profit_pct=10.0,   # 10% 수익 시 익절
    stop_loss_pct=-15.0,    # -15% 손실 시 손절
    total_capital=1000000,
    enabled=True
)

# 3. SemiAutoManager 생성 및 시작
manager = SemiAutoManager(
    upbit_api=upbit_api,
    order_manager=order_manager,
    dca_config=dca_config,
    scan_interval=10,  # 10초마다 스캔
    notification_callback=send_telegram_notification
)

await manager.start()

# 4. 상태 조회
status = manager.get_status()
print(f"관리 중인 포지션: {status['managed_count']}개")
for pos in status['positions']:
    print(f"  - {pos['symbol']}: {pos['balance']:.6f} @ {pos['avg_price']:,.0f}원")

# 5. 종료
await manager.stop()
```

---

## 🧪 테스트 커버리지

### PositionDetector 테스트
- **파일**: `/tests/test_position_detector.py`
- **결과**: ✅ 5/5 통과

### SemiAutoManager 테스트
- **파일**: `/tests/test_semi_auto_manager.py`
- **결과**: ✅ 4/4 통과

**테스트 시나리오**:
1. 수동 매수 감지 → 관리 포지션 등록 확인
2. 가격 10% 하락 → DCA Level 1 자동 매수 확인
3. 가격 20% 하락 → DCA Level 2 자동 매수 확인
4. 가격 10% 상승 → 익절 자동 매도 확인
5. 가격 15% 하락 → 손절 자동 매도 확인

---

## 📈 실제 동작 시나리오

### 시나리오 1: 수동 매수 → DCA → 익절

```
1. [사용자] Upbit에서 BTC 0.01개를 95,000,000원에 수동 매수
   
2. [시스템] 
   - PositionDetector가 새 포지션 감지
   - SemiAutoManager가 ManagedPosition 생성
   - 🔔 알림: "수동 매수 감지! 자동 관리 시작"

3. [가격 하락] BTC 가격이 85,500,000원으로 10% 하락
   
4. [시스템]
   - DCA Level 1 조건 충족 감지
   - 자동으로 250,000원 추가 매수 실행
   - 💰 알림: "DCA 추가 매수 (Level 1)"

5. [가격 상승] BTC 평균 단가 대비 10% 상승
   
6. [시스템]
   - 익절 조건 충족 감지
   - 전량 자동 매도 실행
   - 포지션 제거
   - 🎯 알림: "익절 완료! 수익률: +10.5%"
```

### 시나리오 2: 수동 매수 → 손절

```
1. [사용자] Upbit에서 ETH 1.5개를 4,500,000원에 수동 매수
   
2. [시스템] 자동 관리 시작

3. [가격 급락] ETH 가격이 3,825,000원으로 15% 급락
   
4. [시스템]
   - 손절 조건 충족 감지
   - 전량 자동 매도 실행
   - 포지션 제거
   - 🚨 알림: "손절 완료. 손실률: -15.0%"
```

---

## 🔐 안전 장치

1. **중복 실행 방지**
   - `executed_dca_levels`: DCA 레벨별 실행 여부 추적
   - 동일 레벨 중복 매수 방지

2. **예외 처리**
   - 모든 비동기 작업에 try-except 적용
   - 에러 발생 시 로깅 후 계속 실행

3. **포지션 동기화**
   - 주기적으로 Upbit API에서 실제 잔고 확인
   - 청산된 포지션 자동 제거

4. **알림 시스템**
   - 주요 이벤트마다 사용자에게 알림
   - 매수/매도 실행 결과 즉시 통보

---

## 📝 다음 단계 (Phase 5)

1. **GUI 통합**
   - Semi-Auto 모드 활성화/비활성화 토글
   - 관리 중인 포지션 실시간 모니터링
   - DCA 설정 GUI에서 편집

2. **알림 강화**
   - Telegram Bot 통합
   - 주요 이벤트 푸시 알림

3. **Paper Trading 검증**
   - Dry-run 모드에서 충분한 검증
   - 실제 자금 투입 전 안정성 확인

---

## ✅ 완료 체크리스트

- [x] PositionDetector 구현
- [x] PositionDetector 테스트 작성 및 검증
- [x] SemiAutoManager 구현
- [x] SemiAutoManager 테스트 작성 및 검증
- [x] DCA 자동 실행 로직
- [x] 익절 자동 실행 로직
- [x] 손절 자동 실행 로직
- [x] 중복 실행 방지 메커니즘
- [x] 예외 처리 및 안전 장치
- [x] 문서화

---

## 📚 관련 파일

**핵심 구현**:
- `/core/position_detector.py` - 포지션 감지 시스템
- `/core/semi_auto_manager.py` - 반자동 관리 시스템

**테스트**:
- `/tests/test_position_detector.py` - PositionDetector 테스트
- `/tests/test_semi_auto_manager.py` - SemiAutoManager 테스트

**문서**:
- `/docs/PHASE_4_완료_보고서.md` - 본 문서

**관련 설정**:
- `/gui/dca_config.py` - DCA 설정 데이터 클래스

---

## 🎉 Phase 4 완료!

**Semi-Auto Trading System** 구현 완료 및 테스트 검증 완료!

모든 핵심 기능이 정상 작동하며, 사용자가 Upbit에서 수동으로 매수한 코인을
자동으로 감지하여 DCA와 익절/손절을 완전 자동으로 관리할 수 있습니다.

**다음**: Phase 5 (GUI 통합) 진행 예정
