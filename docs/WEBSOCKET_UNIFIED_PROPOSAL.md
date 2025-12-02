# WebSocket 통합 구조 개선 제안서

> 작성일: 2025-12-02
> 상태: 제안 (Proposal)
> 관련 브랜치: 별도 브랜치에서 작업 예정

---

## 1. 배경

### 현재 문제점
- **시작 시간이 오래 걸림**: 13개 코인 기준 약 16초 소요
- 코인당 1개의 WebSocket 연결 → 연결 시간 누적
- 코인 수가 늘어날수록 시작 시간 증가 (50개 코인 = 약 50초)

### 원인 분석 (로그 기반)
```
16:04:32 → V4 엔진 초기화
16:04:32-34 → 캔들 199개 로드 (13개 코인) (~2초) ✅ 빠름
16:04:34-46 → WebSocket 연결 (13개 코인) (~12초) ⭐ 병목!
16:04:47 → 텔레그램 알림
```

- WebSocket 연결당 약 1초 소요 (연결 0.5초 + Rate Limit 대기 0.5초)
- 13개 × 1초 = 13초

---

## 2. 현재 구조 vs 개선 구조

### 2.1 현재 구조: 코인별 개별 WebSocket

```
업비트 서버
    │
    ├── WebSocket 1 ──→ TickerWebSocket (BTC) ──→ CandleAggregator (BTC, 5분봉)
    │
    ├── WebSocket 2 ──→ TickerWebSocket (ETH) ──→ CandleAggregator (ETH, 5분봉)
    │
    ├── WebSocket 3 ──→ TickerWebSocket (XRP) ──→ CandleAggregator (XRP, 3분봉)
    │
    └── ... (코인 수만큼 WebSocket 연결)
```

**코드 위치**: `core/websocket_manager.py`
```python
# 현재: 코인마다 별도 WebSocket + 1:1 콜백
ws = TickerWebSocket(on_tick_callback=aggregator.on_tick)
self.websockets[symbol] = ws
```

### 2.2 개선 구조: 통합 WebSocket + 라우터

```
업비트 서버
    │
    └── WebSocket 1개 ──→ TickRouter ──┬──→ CandleAggregator (BTC, 5분봉)
        (모든 코인 구독)               │
                                      ├──→ CandleAggregator (ETH, 5분봉)
                                      │
                                      ├──→ CandleAggregator (XRP, 3분봉)
                                      │
                                      └──→ ... (코인별 Aggregator)
```

**개선 코드 (예시)**:
```python
# 개선: 통합 WebSocket + 라우터 콜백
def tick_router(tick_data):
    symbol = tick_data.get('code')  # 'KRW-BTC', 'KRW-ETH' 등
    if symbol in self.aggregators:
        self.aggregators[symbol].on_tick(tick_data)

ws = TickerWebSocket(on_tick_callback=tick_router)
await ws.subscribe_ticker(all_symbols)  # 모든 코인 한 번에 구독
```

---

## 3. 12세 이해 버전 데이터 흐름도

### 현재 구조: "코인마다 따로 전화"

```
업비트 서버 🏢
    │
    ├── 📞 전화선 1 ──→ 🤖 BTC 담당자 ──→ 📊 BTC 캔들 기계
    │
    ├── 📞 전화선 2 ──→ 🤖 ETH 담당자 ──→ 📊 ETH 캔들 기계
    │
    ├── 📞 전화선 3 ──→ 🤖 XRP 담당자 ──→ 📊 XRP 캔들 기계
    │
    └── ... (13개 전화선 = 13초)
```

**데이터 흐름**:
1. 업비트: "BTC 가격이 1억 3천이야!"
2. BTC 전화선으로만 감
3. BTC 담당자가 받음
4. BTC 캔들 기계에 전달
5. 캔들 업데이트 완료!

### 개선 구조: "한 전화선으로 다 받기"

```
업비트 서버 🏢
    │
    📞 전화선 1개 ──→ 🎯 교환원 ──┬──→ 📊 BTC 캔들 기계
    (모든 코인)                   │
                                 ├──→ 📊 ETH 캔들 기계
                                 │
                                 └──→ 📊 XRP 캔들 기계

    (1개 연결 = 1-2초)
```

**데이터 흐름**:
1. 업비트: "BTC 가격이 1억 3천이야!"
2. 전화선 1개로 옴
3. 교환원이 확인: "이건 BTC 정보네!"
4. BTC 캔들 기계로 연결
5. 캔들 업데이트 완료!

---

## 4. 장단점 비교

### 현재 구조 (코인별 개별 WebSocket)

| 장점 | 단점 |
|------|------|
| ✅ 코드가 단순함 | ❌ 시작 시간 오래 걸림 |
| ✅ 에러 격리 (한 코인 문제 = 그 코인만 영향) | ❌ 코인 수 증가 시 시간 선형 증가 |
| ✅ 디버깅 쉬움 | ❌ 리소스 낭비 (연결 N개 유지) |
| ✅ 콜백 1:1 매핑으로 라우팅 불필요 | |

### 개선 구조 (통합 WebSocket + 라우터)

| 장점 | 단점 |
|------|------|
| ✅ 시작 빠름 (1-2초) | ❌ 코드 복잡도 증가 (라우터 필요) |
| ✅ 코인 수 무관하게 일정한 시작 시간 | ❌ 에러 전파 위험 (연결 끊기면 전부 영향) |
| ✅ 리소스 효율적 (연결 1개) | ❌ 디버깅 시 symbol 확인 필요 |
| ✅ Upbit 공식 문서 권장 방식 | |

---

## 5. Upbit 공식 문서 근거

### 출처: `upbit_docs/reference/websocket-guide.md`

> "만약 **여러 페어의 정보를 동시에 수신**하고 싶은 경우 **codes 필드에 페어 코드들을 쉼표(,)로 구분**하여 명시합니다."

**공식 예시**:
```json
// 여러 코인을 하나의 WebSocket에서 구독
[{"ticket":"test"},{"type":"ticker","codes":["KRW-BTC","KRW-ETH","KRW-XRP"]}]

// 체결 + 호가 동시 구독
[{"ticket":"test"},{"type":"trade","codes":["KRW-BTC"]},{"type":"orderbook","codes":["KRW-ETH"]}]
```

---

## 6. 구현 계획

### 6.1 변경 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `core/websocket_manager.py` | 통합 WebSocket 구조로 리팩토링 |
| `core/upbit_websocket.py` | (선택) TickerWebSocket 라우터 콜백 지원 |

### 6.2 구현 단계

1. **새 브랜치 생성**: `claude/websocket-unified-...`
2. **WebSocketManager 리팩토링**:
   - 단일 TickerWebSocket 인스턴스 사용
   - tick_router 콜백 함수 구현
   - 모든 코인 한 번에 구독
3. **테스트**:
   - 시작 시간 측정
   - 캔들 생성 정상 동작 확인
   - 에러 상황 테스트 (연결 끊김 등)
4. **비교 및 선택**:
   - 기존 구조 vs 개선 구조 비교
   - 문제 없으면 main에 merge

### 6.3 예상 코드 변경 (WebSocketManager)

```python
class WebSocketManager:
    def __init__(self, upbit_api=None):
        self.upbit_api = upbit_api
        self.websocket: TickerWebSocket = None  # 단일 WebSocket
        self.aggregators: Dict[str, CandleAggregator] = {}  # symbol -> aggregator
        self.candle_units: Dict[str, int] = {}
        self.is_running = False

    def _tick_router(self, tick_data: Dict):
        """통합 콜백: symbol별로 해당 aggregator에 전달"""
        symbol = tick_data.get('code')
        if symbol and symbol in self.aggregators:
            self.aggregators[symbol].on_tick(tick_data)

    async def start_all(self):
        """모든 코인 한 번에 구독"""
        all_symbols = list(self.aggregators.keys())

        # 단일 WebSocket 생성
        self.websocket = TickerWebSocket(on_tick_callback=self._tick_router)
        await self.websocket.connect()
        await self.websocket.subscribe_ticker(all_symbols)  # 한 번에 구독!

        self.is_running = True
        logger.info(f"✅ WebSocket 연결 완료 ({len(all_symbols)}개 코인, 1개 연결)")
```

---

## 7. 예상 효과

| 지표 | 현재 | 개선 후 |
|------|------|---------|
| 13개 코인 시작 시간 | ~16초 | ~2초 |
| 50개 코인 시작 시간 | ~50초 | ~2초 |
| WebSocket 연결 수 | N개 | 1개 |
| 코드 복잡도 | 낮음 | 중간 |

---

## 8. 리스크 및 대응

| 리스크 | 대응 방안 |
|--------|----------|
| WebSocket 연결 끊김 시 전체 영향 | 자동 재연결 로직 강화 |
| 라우터 버그 시 특정 코인 누락 | 로깅 강화, 모니터링 |
| 기존 코드와 호환성 | 새 브랜치에서 충분한 테스트 |

---

## 9. 결론

- **현재 구조**: 안정적이지만 시작 시간이 오래 걸림
- **개선 구조**: Upbit 공식 권장 방식, 시작 시간 대폭 단축
- **권장**: 새 브랜치에서 구현 후 테스트, 문제 없으면 적용

---

## 10. 참고 자료

- Upbit WebSocket 가이드: `upbit_docs/reference/websocket-guide.md`
- 현재 WebSocket 구현: `core/websocket_manager.py`
- GUI WebSocket (참고): `gui/price_websocket_worker.py` (이미 통합 방식 사용)
