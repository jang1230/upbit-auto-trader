# Upbit Auto Trader V4 - 프로젝트 컨텍스트

> 499개 커밋 분석 기반 (2025-10-24 ~ 2025-12-01)

## 프로젝트 개요

업비트(Upbit) 거래소에서 암호화폐를 자동으로 매매하는 트레이딩 봇.
V3의 2가지 모드(반자동/완전자동) 한계를 극복하고, **무제한 그룹 기반**으로 전면 재설계됨.

## 개발 타임라인

| 기간 | 작업 내용 | 커밋 수 |
|------|----------|--------|
| 10/24 | Initial commit (Phase 4 features) | 1 |
| 10/27~10/31 | V3 semi_auto_manager, GUI 최적화, Live 트레이딩 | ~50 |
| 11/3~11/7 | V4 설계 문서 작성, 스키마 정의 | ~40 |
| 11/10~11/14 | V4 Phase 1-2 (데이터 구조, 백엔드) | ~80 |
| 11/17~11/21 | V4 Phase 3 (GUI), WebSocket 개선, Real-time | ~60 |
| 11/24~11/28 | 안정화, Race Condition, 중복 알림 수정 | ~80 |
| 12/1 | 최종 안정화 (Lock, 중복 제거) | ~9 |

## 기술 스택

- **Python**: 3.8+
- **GUI**: PySide6
- **API**: Upbit REST API + WebSocket (Private: MyOrder, MyAsset)
- **알림**: Telegram Bot
- **주요 라이브러리**: pyupbit, websockets, websocket-client, pandas, numpy, ta

## V3 → V4 주요 변경점

| 항목 | V3 | V4 |
|------|-----|-----|
| 트레이딩 모드 | 2개 (반자동/완전자동) | 무제한 그룹 |
| 코인 관리 | 전역 설정 | 그룹별 독립 관리 |
| 매수 전략 | 단일 전략 | 프리셋 3종 (Conservative/Balanced/Aggressive) |
| DCA/익절/손절 | 단일 레벨 | 다단계 레벨 |
| 일일 손실 한도 | 없음 | 09:00 자동 리셋 |
| 포지션 파일 | 1개 | 2개 (live/dryrun 분리) |
| WebSocket | 기본 | MyOrder + MyAsset Private 채널 |

## 아키텍처

```
┌─────────────────┐
│   MainWindow    │ ← 사용자 GUI (PySide6)
└────────┬────────┘
         │
┌────────▼────────────────────────────┐
│       V4TradingEngine               │
│  - GroupManager                     │
│  - ConfigManager (trading_config)   │
│  - PositionManager (live/dryrun)    │
│  - TradeHistoryManager              │
│  - DailyLossTracker                 │
│  - PendingOrderManager              │
└────────┬────────────────────────────┘
         │
┌────────▼───────┐ ┌─────────────────────┐ ┌──────────────┐
│ V4AutoBuy      │ │ WebSocket Workers   │ │  Upbit API   │
│ Strategy       │ │ - MyOrderWebSocket  │ │   (REST)     │
│                │ │ - MyAssetWebSocket  │ │              │
│                │ │ - PriceWebSocket    │ │              │
└────────────────┘ └─────────────────────┘ └──────────────┘
```

## GUI 컴포넌트 관계도

```
MainWindow (gui/main_window.py)
│
├── 설정 관리
│   ├── ConfigManager (gui/config_manager.py) ─────→ .env 파일
│   │   └── Upbit API Key, Selected Coins
│   └── V4ConfigManager (core/config_manager.py) ─→ config/trading_config.json
│       └── 그룹, 텔레그램, 손실한도 설정
│
├── 다이얼로그
│   ├── GlobalSettingsDialog (gui/global_settings_dialog.py)
│   │   ├── Upbit API 탭 → ConfigManager (.env)
│   │   ├── 거래 제한 탭 → V4ConfigManager
│   │   ├── 손실 한도 탭 → V4ConfigManager
│   │   └── 텔레그램 탭 → V4ConfigManager
│   │
│   ├── GroupManagementDialog (gui/group_management_dialog.py)
│   │   └── GroupUnifiedSettingsDialog (gui/group_unified_settings_dialog.py)
│   │       ├── AutoBuySettingsDialogV2 (gui/auto_buy_settings_dialog_v2.py)
│   │       └── LevelSettingsDialog (gui/level_settings_dialog.py)
│   │
│   └── DcaSimulatorDialog (gui/dca_simulator.py)
│
├── 워커 (백그라운드 스레드)
│   ├── SemiAutoWorker (gui/semi_auto_worker.py)
│   ├── PriceWebSocketWorker (gui/price_websocket_worker.py)
│   └── MyAssetWebSocketWorker (gui/myasset_websocket_worker.py)
│
└── 유틸리티
    ├── LoggingHandler (gui/logging_handler.py)
    └── TradeData (gui/trade_data.py)
```

## 설정 파일 구분

| 설정 파일 | 관리 클래스 | 저장 내용 |
|----------|------------|----------|
| `.env` | `gui/config_manager.py` | Upbit API Key, 선택된 코인 |
| `config/trading_config.json` | `core/config_manager.py` | 그룹, 전략, 텔레그램, 손실한도 |
| `data/positions_*.json` | `core/position_manager.py` | 포지션 상태 |
| `data/trade_history.json` | `core/trade_history_manager.py` | 거래 기록 |

## 핵심 모듈 (파일별 수정 횟수)

| 순위 | 파일 | 수정 횟수 | 역할 |
|-----|------|----------|------|
| 1 | `core/v4_trading_engine.py` | 134 | 메인 오케스트레이터, 주문 처리 |
| 2 | `gui/main_window.py` | 102 | GUI 메인 윈도우 |
| 3 | `core/semi_auto_manager.py` | 45 | V3 반자동 매니저 (레거시) |
| 4 | `core/position_manager.py` | 39 | 포지션 CRUD, DCA 관리 |
| 5 | `core/upbit_websocket.py` | 27 | WebSocket 연결 (Price, MyOrder, MyAsset) |
| 6 | `gui/auto_buy_settings_dialog_v2.py` | 21 | 자동매수 설정 다이얼로그 |
| 7 | `gui/group_unified_settings_dialog.py` | 18 | 그룹 통합 설정 |
| 8 | `gui/group_management_dialog.py` | 15 | 그룹 관리 대화창 |
| 9 | `core/upbit_api.py` | 14 | REST API 클라이언트 |
| 10 | `gui/logging_handler.py` | 13 | GUI 로그 필터링 |

## 주요 파일 경로

```
upbit-auto-trader/
├── main.py                          # 진입점
├── config/
│   ├── trading_config.json          # V4 통합 설정
│   └── schemas/
│       └── trading_config_schema.json
├── data/
│   ├── positions_live.json          # Live 포지션
│   ├── positions_dryrun.json        # Dry-run 포지션
│   ├── trade_history.json           # 거래 기록
│   └── virtual_balances.json        # Dry-run 잔고
├── core/
│   ├── v4_trading_engine.py         # ⭐ 핵심 엔진 (930+ lines)
│   ├── group_manager.py             # 그룹 관리 (578 lines)
│   ├── config_manager.py            # 설정 관리 (512 lines)
│   ├── position_manager.py          # 포지션 관리 (656 lines)
│   ├── trade_history_manager.py     # 거래 기록 (479 lines)
│   ├── daily_loss_tracker.py        # 일일 손실 (329 lines)
│   ├── pending_order_manager.py     # 대기 주문 관리
│   ├── balance_polling_manager.py   # 잔고 폴링
│   ├── upbit_websocket.py           # WebSocket
│   ├── upbit_api.py                 # REST API
│   └── strategies/
│       └── v4_auto_buy_strategy.py  # 자동매수 전략 (456 lines)
├── gui/
│   ├── main_window.py               # ⭐ 메인 GUI
│   ├── group_management_dialog.py
│   ├── group_unified_settings_dialog.py
│   ├── group_settings_dialog.py
│   ├── level_settings_dialog.py
│   ├── auto_buy_settings_dialog_v2.py
│   ├── coin_selection_dialog.py
│   ├── logging_handler.py
│   ├── trade_data.py
│   ├── myasset_websocket_worker.py
│   ├── price_websocket_worker.py
│   └── semi_auto_worker.py          # V3 레거시
└── docs/
    ├── DESIGN_V4_COMPLETE.md        # V4 상세 설계 (172KB, 18개 섹션)
    ├── LIVE_TRADING_CHECKLIST.md
    ├── TROUBLESHOOTING.md
    └── archive/                     # V3 문서
```

## 주문 처리 흐름 (Phase A-B-C-D)

V4TradingEngine에서 주문은 4단계로 처리됩니다:

```
Phase A: 주문 요청
    ↓
Phase B: MyOrder WebSocket 수신 (state: wait → done)
    ↓
Phase C: 포지션 업데이트 (REST API fallback)
    ↓
Phase D: GUI 업데이트 + 텔레그램 알림
```

## 코드 컨벤션

### 커밋 메시지 접두사
- `fix:` 버그 수정
- `feat:` 새 기능
- `refactor:` 리팩토링
- `debug:` 디버그 로그 추가
- `docs:` 문서 수정
- `style:` UI/스타일 변경
- `perf:` 성능 개선
- `revert:` 롤백
- `WIP:` 작업 중 (검증 필요)

### 로깅 패턴
```python
logger.info(f"✅ 성공 메시지")
logger.info(f"🎯 중요 이벤트: {symbol}")
logger.info(f"📊 상태 정보")
logger.info(f"🔍 디버그 정보")
logger.info(f"⏭️ 스킵 메시지")
logger.warning(f"⚠️ 경고")
logger.error(f"❌ 에러")
```

### 중복 방지 패턴
```python
# 1. TTL 기반 메시지 중복 제거 (5초)
self._recent_messages = {}  # {(uuid, state, timestamp): received_time}
self._dedup_ttl_seconds = 5

# 2. threading.Lock 사용
with self._dedup_lock:
    if msg_key in self._recent_messages:
        return
    self._recent_messages[msg_key] = now

# 3. 봇 매도 추적 (10초)
self.recent_bot_sells: Dict[str, float] = {}
```

## 알려진 이슈 패턴 (해결됨)

| 이슈 | 원인 | 해결책 |
|------|------|--------|
| WebSocket 메시지 2회 수신 | Upbit이 동일 메시지 중복 전송 | `threading.Lock` + TTL 중복 제거 |
| `group_id=None` 시 포지션 삭제 | `sync_with_upbit()`에서 None 포지션 삭제 | `"group_null"` 문자열 사용 |
| 익절/손절 후 수동매도 중복 알림 | 봇 매도와 MyAsset 감지 동시 발생 | `recent_bot_sells` 10초 추적 |
| DCA Phase B 조기 return | 잘못된 조건 체크 | Phase C 도달 로직 수정 |
| GUI Race Condition | 멀티스레드 접근 | Signal 패턴, Lock, 콜백 동기화 |
| REST API Rate Limit | 과도한 API 호출 | Adaptive Polling, WebSocket 우선 |

## WebSocket 채널

1. **Price WebSocket** (Public)
   - 실시간 시세 (1초마다)
   - 캔들 데이터

2. **MyOrder WebSocket** (Private)
   - 주문 상태 변경 감지
   - `state: wait → done`
   - 봇/수동 주문 구분 (`identifier`)

3. **MyAsset WebSocket** (Private)
   - 잔고 변경 감지
   - 수동 매수/매도 감지

## 테스트 시나리오

1. **자동매수**: RSI + Volume 조건 충족 → 매수
2. **DCA 추가매수**: -3%, -5%, -7% 레벨
3. **익절**: +5% (50%), +10% (50%)
4. **손절**: -15% (100%)
5. **수동매수 감지**: Upbit 앱에서 매수 → 자동 포지션 생성
6. **수동매도 감지**: Upbit 앱에서 매도 → 포지션 종료

## 연락처

- GitHub: https://github.com/jang1230/upbit-auto-trader
- 현재 브랜치: `claude/duplicate-branch-history-0182BCX6kFJuNtc2y14sG1K9`
