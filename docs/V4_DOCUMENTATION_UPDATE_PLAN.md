# V4 문서 업데이트 계획

**작성일**: 2025-11-13
**대상 문서**: 10개 필수 사용자 가이드
**목표**: V3 기반 문서를 V4 시스템에 맞게 전면 개편

---

## 📋 V3 → V4 주요 변경사항

### 1. **그룹 기반 시스템** (V4 핵심 변화)

**V3 (기존)**:
- 2가지 모드: 반자동/완전자동
- 단일 설정 파일
- 모든 코인에 동일한 전략 적용
- 코인별 개별 관리 어려움

**V4 (신규)**:
- **무제한 그룹** 생성 가능
- 그룹별 독립적인 설정:
  - 매수 방식 (자동/수동/관찰)
  - DCA 레벨 (그룹마다 다름)
  - 익절/손절 레벨 (그룹마다 다름)
  - 자동매수 전략 (Conservative/Balanced/Aggressive)
- 코인은 하나의 그룹에만 소속
- 그룹별 성과 추적

### 2. **설정 파일 구조 변경**

**V3**:
```
config/settings.json           # 메인 설정
config/auto_trading_config.json  # 자동매매 설정
```

**V4**:
```
config/trading_config.json     # 통합 설정 파일
  ├─ version: "4.0"
  ├─ mode: "live" or "dryrun"
  ├─ groups: {...}             # 그룹별 설정
  └─ daily_loss_limit: {...}   # 일일 손실 제한
```

### 3. **포지션 파일 분리**

**V3**:
```
data/positions.json            # 단일 포지션 파일
```

**V4**:
```
data/positions_live.json       # Live 모드 포지션
data/positions_dryrun.json     # Dry-run 모드 포지션
data/trade_history.json        # 거래 기록
data/virtual_balances.json     # Dry-run 잔고
data/daily_snapshot.json       # 일일 손실 추적
```

### 4. **자동매수 전략 프리셋**

**V3**:
- 전략 선택: ScalpingStrategy, FilteredBBStrategy 등
- 수동으로 지표 설정

**V4**:
- 3가지 프리셋:
  - **Conservative**: 4시간봉, 안정적 진입
  - **Balanced**: 1시간봉, 균형잡힌 트레이딩
  - **Aggressive**: 15분봉, 빠른 진입
- 각 프리셋마다 RSI, MACD, Volume 자동 설정
- Custom 옵션으로 세부 조정 가능

### 5. **GUI 변경사항**

**V3 GUI**:
- 상단: 모드 선택 (반자동/완전자동)
- 설정: 단일 설정 대화창
- 코인 선택: 단순 리스트

**V4 GUI**:
- 상단: 그룹 관리 버튼
- 그룹 관리 대화창:
  - 그룹 생성/삭제/수정
  - 그룹별 코인 할당
  - 그룹별 설정 (매수/DCA/익절/손절)
- 레벨 상세 설정 대화창:
  - DCA 레벨 다단계 설정
  - 익절 레벨 다단계 설정
  - 손절 레벨 다단계 설정
- 자동매수 설정 대화창:
  - 프리셋 선택
  - 지표 커스터마이징

### 6. **일일 손실 제한 (신규 기능)**

**V4 전용**:
- 매일 09:00 자동 리셋
- 손실률 도달 시:
  - `alert`: 텔레그램 알림만
  - `liquidate`: 전량 청산
- 계산 방식:
  - `daily_only`: 09:00 기준 손실률
  - `total_account`: 초기 자본 대비 손실률

---

## 📚 문서별 업데이트 계획

### 1️⃣ **README.md** (메인 프로젝트 소개)

**현재 문제**:
- V3 기준 소개
- Phase 4 완료 언급 (V3 Phase)
- ScalpingStrategy, FilteredBBStrategy 강조 (V3 전략)

**V4 업데이트 내용**:

#### 1. 프로젝트 소개 섹션
- **Before**: "암호화폐 자동 매매 트레이딩 봇 - 단타/중장기 전략 + DCA"
- **After**: "암호화폐 자동 매매 트레이딩 봇 - 그룹 기반 멀티 전략 + DCA 리스크 관리"

#### 2. 핵심 특징 재작성
```markdown
## 🎯 핵심 특징

### V4 그룹 기반 시스템
- ✅ **무제한 그룹 생성** - 그룹별로 다른 전략/설정 적용
- ✅ **3가지 매수 방식**
  - 자동매수 (Conservative/Balanced/Aggressive 프리셋)
  - 수동매수 (외부 거래 감지 자동 포지션 생성)
  - 관찰 모드 (포지션 추적만, 거래 안 함)
- ✅ **그룹별 독립 설정**
  - DCA 레벨 (하락 시 분할 매수)
  - 익절 레벨 (수익 실현 자동화)
  - 손절 레벨 (손실 제한)
- ✅ **일일 손실 제한** (09:00 자동 리셋)
- ✅ **실시간 모니터링** - PySide6 GUI + Telegram 알림
- ✅ **Live/Dry-run 분리** - 테스트와 실거래 완전 분리
```

#### 3. 빠른 시작 가이드 수정
```markdown
## ⚡ 빠른 시작

1. **설치**
   ```bash
   pip install -r requirements.txt
   ```

2. **API 키 설정**
   - Upbit API 키 발급 (https://upbit.com/mypage/open_api_management)
   - GUI에서 API 키 입력

3. **첫 그룹 생성**
   - GUI 상단 "그룹 관리" 버튼 클릭
   - "그룹 추가" → 이름 입력 (예: "비트코인 단타")
   - 코인 선택 (예: BTC, ETH)
   - 매수 방식 선택:
     - 자동매수 → Balanced 프리셋 선택
     - 매수 금액: 50,000원
   - DCA/익절/손절 설정

4. **시작**
   - Dry-run 모드로 먼저 테스트 (최소 1주일)
   - 정상 동작 확인 후 Live 모드 전환
```

#### 4. 스크린샷 업데이트
- V4 GUI 스크린샷 추가:
  - 그룹 관리 대화창
  - 그룹 설정 대화창
  - 레벨 설정 대화창
  - 포지션 테이블 (그룹별 표시)

#### 5. 시스템 아키텍처 다이어그램 수정
```
V4 Architecture:
┌─────────────────┐
│   MainWindow    │ ← 사용자 GUI
└────────┬────────┘
         │
┌────────▼────────────────────────────┐
│   V4TradingEngine                   │
│  - GroupManager                     │
│  - ConfigManager (trading_config)   │
│  - PositionManager (live/dryrun)    │
│  - TradeHistoryManager              │
│  - DailyLossTracker                 │
└────────┬────────────────────────────┘
         │
┌────────▼───────┐  ┌─────────────┐  ┌──────────────┐
│ V4AutoBuy      │  │ WebSocket   │  │ Upbit API    │
│ Strategy       │  │ (Real-time) │  │ (REST)       │
└────────────────┘  └─────────────┘  └──────────────┘
```

---

### 2️⃣ **CLAUDE.md** (Claude 작업 가이드)

**현재 문제**:
- V3 아키텍처 설명 (TradingEngine, MultiCoinTrader)
- V4 Phase 1-2만 언급 (최신 상태 아님)
- V4 GUI 설명 없음

**V4 업데이트 내용**:

#### 1. Project Overview 업데이트
```markdown
## Project Overview

**Upbit DCA Trader V4** - 그룹 기반 자동 매매 시스템

**Language**: Python 3.8+
**Primary Use**: Korean cryptocurrency market (KRW trading pairs)
**Architecture**: V4 (Group-based multi-strategy system)

**V4 Key Changes**:
- Group-based configuration (unlimited groups)
- Separate Live/Dry-run position files
- Preset-based auto-buy strategies (Conservative/Balanced/Aggressive)
- Daily loss limit with 09:00 auto-reset
- Independent settings per group
```

#### 2. Key Commands 섹션에 V4 추가
```markdown
### Running the Application (V4)

```bash
# Launch V4 GUI (main application)
python main.py

# Check current configuration
cat config/trading_config.json

# Check positions
cat data/positions_live.json      # Live mode
cat data/positions_dryrun.json    # Dry-run mode

# Check trade history
cat data/trade_history.json
```
```

#### 3. Architecture Overview 재작성
```markdown
## V4 Architecture Overview

### High-Level Data Flow

```
GUI → V4TradingEngine → GroupManager → PositionManager → Upbit API
                    ↓                                    ↓
              ConfigManager                         WebSocket
                    ↓                                    ↓
           trading_config.json              Real-time Price/Balance
```

### Core Components

**1. V4TradingEngine** (`core/v4_trading_engine.py`, 930 lines)
- Main orchestrator for V4 system
- Group-level trading loops
- Position monitoring (60-second polling)
- Auto-buy strategy execution
- DCA trigger logic
- Profit/loss trigger logic
- Daily loss tracker integration

**2. GroupManager** (`core/group_manager.py`, 578 lines)
- Group lifecycle: create, delete, update
- Coin management: add, remove, move between groups
- Cross-group validation (prevent coin duplication)

**3. ConfigManager** (`core/config_manager.py`, 512 lines)
- Unified configuration management
- JSON Schema validation
- V3→V4 automatic migration

**4. PositionManager** (`core/position_manager.py`, 656 lines)
- Separate files: positions_live.json, positions_dryrun.json
- CRUD operations: create, update, close positions
- DCA management: add_dca(), track dca_count
- Upbit synchronization: sync_with_upbit()

**5. TradeHistoryManager** (`core/trade_history_manager.py`, 479 lines)
- Records all trades to data/trade_history.json
- Group-level statistics calculation

**6. DailyLossTracker** (`core/daily_loss_tracker.py`, 329 lines)
- Daily loss limit enforcement
- 09:00 auto-reset
- Snapshot-based calculation
- Callback architecture (alert/liquidate)

**7. V4AutoBuyStrategy** (`core/strategies/v4_auto_buy_strategy.py`, 456 lines)
- Preset-based auto-buy: Conservative (4H), Balanced (1H), Aggressive (15min)
- Technical indicators: RSI, MACD, Volume
- Group-level strategy assignment
```

#### 4. V4 Configuration Structure 추가
```markdown
### V4 Configuration Structure

**File**: `config/trading_config.json`

```json
{
  "version": "4.0",
  "mode": "live",  // or "dryrun"
  "groups": {
    "group_1": {
      "name": "비트코인 단타",
      "coins": ["KRW-BTC", "KRW-ETH"],
      "buy_settings": {
        "mode": "auto",  // or "manual" or "observation"
        "auto_config": {
          "enabled": true,
          "investment_style": "balanced",  // or "conservative", "aggressive"
          "candle_unit": "60",  // 15, 60, 240
          "indicators": {...},
          "buy_amount_krw": 50000
        }
      },
      "dca_settings": {
        "mode": "auto",  // or "disabled"
        "levels": [
          {"price_ratio": -3.0, "quantity_ratio": 100},
          {"price_ratio": -5.0, "quantity_ratio": 100}
        ]
      },
      "profit_settings": {
        "mode": "auto",  // or "disabled"
        "levels": [
          {"price_ratio": 5.0, "quantity_ratio": 50},
          {"price_ratio": 10.0, "quantity_ratio": 50}
        ]
      },
      "loss_settings": {
        "mode": "auto",  // or "disabled"
        "levels": [
          {"price_ratio": -15.0, "quantity_ratio": 100}
        ]
      }
    }
  },
  "daily_loss_limit": {
    "enabled": true,
    "loss_pct": 10.0,
    "action": "alert",  // or "liquidate"
    "calculation_method": "daily_only"  // or "total_account"
  }
}
```
```

#### 5. Common Development Workflows 업데이트
```markdown
### Adding a New Group (V4)

1. Open GUI → "그룹 관리" button
2. "그룹 추가" → Enter name
3. Select coins
4. Configure settings:
   - Buy mode: auto/manual/observation
   - DCA levels
   - Profit/Loss levels
5. Save

### Modifying Group Settings

1. Open GUI → "그룹 관리"
2. Select group → "그룹 설정"
3. Modify:
   - "⚙️ 자동매수 설정" → Change preset
   - "⚙️ 레벨 상세 설정" → Adjust DCA/Profit/Loss levels
4. Save

### Testing in Dry-run Mode

1. Set mode to "dryrun" in trading_config.json
2. Start trading engine
3. Check positions: `data/positions_dryrun.json`
4. Check virtual balance: `data/virtual_balances.json`
5. Monitor for 1 week minimum
6. Switch to "live" mode after validation
```

---

### 3️⃣ **INSTALLATION.md** (설치 가이드)

**현재 문제**:
- 설치 가이드는 대체로 정확함
- V4 관련 설정 파일 언급 없음

**V4 업데이트 내용**:

#### 1. Prerequisites 섹션 - 변경 없음
(Python 3.8+, pip, git 등은 동일)

#### 2. Installation Steps - 마지막 단계 추가
```markdown
## Step 4: Verify Installation

### Check V4 Configuration Template

```bash
# Check if trading_config.json template exists
ls config/trading_config_template.json

# If not exists, will be auto-created on first run
```

### First Run (V4)

```bash
python main.py
```

**On first run, V4 will**:
1. Create `config/trading_config.json` from template
2. Create empty position files:
   - `data/positions_live.json`
   - `data/positions_dryrun.json`
3. Create empty trade history: `data/trade_history.json`
4. Show group management dialog (no groups yet)

**Next Steps**:
- Configure Upbit API keys (see ENVIRONMENT_SETUP.md)
- Create your first group (GUI → "그룹 관리")
```

---

### 4️⃣ **ENVIRONMENT_SETUP.md** (환경 설정 가이드)

**현재 문제**:
- V3 settings.json 기준
- 그룹 설정 방법 없음

**V4 업데이트 내용**:

#### 1. Configuration Overview 재작성
```markdown
## Configuration Overview

V4 uses a unified configuration system:

**Main Configuration**:
- `config/trading_config.json` - All trading settings (groups, DCA, profit/loss)

**Runtime Data**:
- `data/positions_live.json` - Live mode positions
- `data/positions_dryrun.json` - Dry-run mode positions
- `data/trade_history.json` - Trade records
- `data/virtual_balances.json` - Dry-run balances
- `data/daily_snapshot.json` - Daily loss tracking

**Note**: Runtime data files are auto-created. DO NOT edit manually.
```

#### 2. Upbit API Keys - 변경 없음
(API 키 발급 방법은 동일)

#### 3. First Time Setup (V4 기준)
```markdown
## First Time Setup (V4)

### Step 1: Launch GUI

```bash
python main.py
```

### Step 2: Configure API Keys

1. GUI → Settings → API Configuration
2. Enter:
   - Access Key: `your_access_key`
   - Secret Key: `your_secret_key`
3. Save

### Step 3: Create First Group

1. Click "그룹 관리" button (top of GUI)
2. Click "그룹 추가"
3. Enter group name (e.g., "Bitcoin Trading")
4. Click "코인 선택" → Select coins (e.g., KRW-BTC, KRW-ETH)
5. Click "그룹 설정"

### Step 4: Configure Group Settings

**Buy Settings**:
- Mode: "자동매수" (Auto-buy)
- Click "⚙️ 자동매수 설정..."
- Select preset: "Balanced" (1-hour candles)
- Buy amount: 50,000 KRW
- Save

**DCA Settings**:
- Check "DCA 활성화"
- Click "⚙️ 레벨 상세 설정"
- DCA Tab:
  - Level 1: -3% / 100%
  - Level 2: -5% / 100%
  - Level 3: -7% / 100%

**Profit Settings**:
- Check "익절 활성화"
- Profit Tab:
  - Level 1: +5% / 50% (take 50% profit)
  - Level 2: +10% / 50% (take rest)

**Loss Settings**:
- Check "손절 활성화"
- Loss Tab:
  - Level 1: -15% / 100% (cut all loss)

- Save all settings

### Step 5: Set Daily Loss Limit

1. Edit `config/trading_config.json`:
```json
{
  "daily_loss_limit": {
    "enabled": true,
    "loss_pct": 10.0,
    "action": "alert",
    "calculation_method": "daily_only"
  }
}
```

### Step 6: Test in Dry-run Mode

1. Set mode to "dryrun":
```json
{
  "mode": "dryrun"
}
```

2. Restart application
3. Monitor for 1 week
4. Check results in `data/trade_history.json`

### Step 7: Switch to Live Mode

**ONLY after successful dry-run testing!**

1. Set mode to "live":
```json
{
  "mode": "live"
}
```

2. Restart application
3. Monitor carefully for first day
```

---

### 5️⃣ **TROUBLESHOOTING.md** (문제 해결 가이드)

**현재 문제**:
- V3 기준 트러블슈팅
- 그룹 관련 문제 없음
- V4 파일 구조 관련 문제 없음

**V4 업데이트 내용**:

#### 1. Common Issues 섹션에 V4 추가

```markdown
## V4 Specific Issues

### 그룹 관리 문제

#### 문제: "그룹을 찾을 수 없습니다" 오류
**증상**: 그룹 설정 저장 시 오류 발생

**원인**:
- trading_config.json이 손상됨
- 그룹이 삭제되었는데 포지션은 남아있음

**해결**:
1. 백업 확인:
```bash
# 최근 백업 확인
ls -lt config/trading_config.json*
```

2. 설정 파일 검증:
```bash
# JSON 문법 검증
python -m json.tool config/trading_config.json
```

3. 템플릿에서 재생성:
```bash
cp config/trading_config_template.json config/trading_config.json
python main.py
```

---

#### 문제: 코인이 중복으로 여러 그룹에 나타남
**증상**: 같은 코인이 2개 그룹에 동시 할당

**원인**: 수동으로 config 파일 편집 시 발생

**해결**:
1. GUI에서 "그룹 관리" 열기
2. 중복된 코인 확인
3. 한 그룹에서만 남기고 다른 그룹에서 제거
4. 저장

**예방**: GUI에서만 그룹 관리 (수동 편집 금지)

---

### 포지션 관리 문제

#### 문제: Live 모드인데 positions_dryrun.json에 포지션 생김
**증상**: 모드와 다른 파일에 포지션 저장됨

**원인**:
- 모드 전환 중 프로그램 재시작 안 함
- 여러 인스턴스 동시 실행

**해결**:
1. 현재 모드 확인:
```bash
grep "mode" config/trading_config.json
```

2. 프로그램 완전 종료
3. 올바른 모드 설정
4. 단일 인스턴스만 실행

---

#### 문제: 포지션 파일이 비어있거나 손상됨
**증상**: GUI에 포지션이 안 보임, 또는 오류 발생

**해결**:
1. Upbit 동기화:
```bash
# 프로그램 실행 시 자동으로 sync_with_upbit() 호출됨
# 수동 실행:
python -c "from core.position_manager import PositionManager; \
           from api.upbit_api import UpbitAPI; \
           api = UpbitAPI(); \
           pm = PositionManager(mode='live', upbit_api=api); \
           pm.sync_with_upbit()"
```

2. 또는 빈 파일로 재생성:
```bash
echo '{"positions": {}}' > data/positions_live.json
echo '{"positions": {}}' > data/positions_dryrun.json
```

3. 프로그램 재시작 → 자동 동기화

---

### 일일 손실 제한 문제

#### 문제: 09:00에 리셋이 안 됨
**증상**: 어제 손실이 계속 누적됨

**원인**:
- 프로그램이 09:00에 실행 중이 아님
- daily_snapshot.json이 손상됨

**해결**:
1. 프로그램이 09:00에 실행 중인지 확인
2. 스냅샷 파일 확인:
```bash
cat data/daily_snapshot.json
```

3. 수동 리셋:
```bash
rm data/daily_snapshot.json
# 프로그램 재시작 → 자동으로 새 스냅샷 생성
```

---

#### 문제: 손실 한도 도달했는데 거래가 계속됨
**증상**: daily_loss_limit 설정했는데 무시됨

**원인**:
- action이 "alert"로 설정됨 (거래 중지 안 함)
- enabled가 false

**해결**:
1. 설정 확인:
```bash
grep -A 5 "daily_loss_limit" config/trading_config.json
```

2. 설정 변경:
```json
{
  "daily_loss_limit": {
    "enabled": true,
    "loss_pct": 10.0,
    "action": "liquidate",  // ← 거래 중지하려면 "liquidate"
    "calculation_method": "daily_only"
  }
}
```

3. 프로그램 재시작

---

### DCA 순차 실행 문제

#### 문제: DCA 레벨 1이 반복 실행됨, 레벨 2는 실행 안 됨
**증상**: -5% 하락했는데 레벨 1만 10번 이상 실행

**원인**:
- ~~state='trade' 처리 누락~~ (2025-11-12 수정 완료)
- 오래된 버전 사용 중

**해결**:
1. 최신 버전 확인:
```bash
git log --oneline | head -n 5
# "fix: Process DCA updates on state=trade" 커밋 있는지 확인
```

2. 최신 버전으로 업데이트:
```bash
git pull origin main
```

3. 포지션 상태 확인:
```bash
# dca_count가 증가하는지 확인
cat data/positions_live.json | grep -A 10 "KRW-BTC"
```

---

### 자동매수 전략 문제

#### 문제: 자동매수 설정했는데 매수 안 됨
**증상**: Balanced 프리셋인데 매수 신호 없음

**원인**:
- 그룹 buy_settings.mode가 "manual"로 되어있음
- 자금 부족
- 지표 조건 불만족

**해결**:
1. 그룹 설정 확인:
```bash
cat config/trading_config.json | grep -A 20 "group_1"
```

2. mode가 "auto"인지 확인:
```json
{
  "buy_settings": {
    "mode": "auto",  // ← 이게 "auto"여야 함
    "auto_config": {...}
  }
}
```

3. 잔고 확인:
```bash
# GUI에서 "잔고 새로고침" 클릭
# 또는 로그 확인
tail -f logs/trading_*.log | grep "잔고 부족"
```

4. 지표 조건 확인:
```bash
# 로그에서 지표 값 확인
tail -f logs/trading_*.log | grep "RSI\|MACD\|Volume"
```
```

---

### 6️⃣ **FAQ.md** (자주 묻는 질문)

**현재 문제**:
- V3 기준 질문들
- 그룹 관련 질문 없음

**V4 업데이트 내용**:

#### 1. V4 관련 질문 추가

```markdown
## V4 시스템 관련

### Q1. V3과 V4의 차이점은 무엇인가요?

**A**: V3은 2가지 모드(반자동/완전자동)만 지원했지만, V4는 무제한 그룹을 만들 수 있습니다.

| 항목 | V3 | V4 |
|------|----|----|
| 모드 | 2가지 (반자동/완전자동) | 무제한 그룹 |
| 설정 파일 | 2개 분리 | 1개 통합 (trading_config.json) |
| 코인별 설정 | 불가능 (모두 동일) | 가능 (그룹별 독립) |
| 포지션 파일 | 1개 (positions.json) | 2개 (live/dryrun 분리) |
| 자동매수 전략 | 수동 지표 설정 | 프리셋 (Conservative/Balanced/Aggressive) |
| 일일 손실 제한 | 없음 | 있음 (09:00 리셋) |

---

### Q2. 그룹을 최대 몇 개까지 만들 수 있나요?

**A**: 제한이 없습니다. 시스템 성능이 허용하는 한 원하는 만큼 만들 수 있습니다.

**권장 사항**:
- 전략별로 그룹 분리 (예: "단타", "중장기", "실험")
- 코인 유형별로 분리 (예: "메이저코인", "알트코인")
- 리스크 수준별로 분리 (예: "안전", "공격적")

**예시**:
- 그룹 1: "비트코인 단타" (BTC, ETH) - Aggressive
- 그룹 2: "알트코인 중장기" (XRP, ADA, DOT) - Conservative
- 그룹 3: "실험 전략" (DOGE, SHIB) - Balanced

---

### Q3. 한 코인을 여러 그룹에 동시에 넣을 수 있나요?

**A**: 아니요, 한 코인은 하나의 그룹에만 속할 수 있습니다.

**이유**:
- 중복 매수/매도 방지
- 포지션 관리 명확화
- 수익률 계산 정확성

**해결 방법**:
- 전략을 바꾸고 싶으면 코인을 다른 그룹으로 이동
- GUI → "그룹 관리" → 코인 선택 → "다른 그룹으로 이동"

---

### Q4. 그룹마다 다른 DCA 설정을 할 수 있나요?

**A**: 네, 각 그룹마다 독립적인 DCA 레벨을 설정할 수 있습니다.

**예시**:
- **보수적 그룹**: -5%, -10%, -15% (큰 하락에만 추가 매수)
- **공격적 그룹**: -2%, -4%, -6% (작은 하락에도 추가 매수)

**설정 방법**:
1. "그룹 관리" → 그룹 선택 → "그룹 설정"
2. "⚙️ 레벨 상세 설정" 클릭
3. DCA 탭에서 레벨 추가/수정

---

### Q5. 자동매수 프리셋의 차이점은 무엇인가요?

**A**: 3가지 프리셋은 캔들 주기와 지표 민감도가 다릅니다.

| 프리셋 | 캔들 주기 | 매수 빈도 | 특징 |
|--------|-----------|-----------|------|
| **Conservative** | 4시간 | 낮음 | 안정적 진입, 장기 투자용 |
| **Balanced** | 1시간 | 중간 | 균형잡힌 트레이딩 (권장) |
| **Aggressive** | 15분 | 높음 | 빠른 진입, 단타용 |

**지표 차이**:
- Conservative: RSI < 25 (과매도 강함), Volume > 2.5x
- Balanced: RSI < 30 (과매도), Volume > 2.0x
- Aggressive: RSI < 35 (과매도 약함), Volume > 1.5x

**권장**:
- 초보자: Balanced 또는 Conservative
- 숙련자: Aggressive (하지만 리스크 높음)

---

### Q6. 수동 매수 모드에서도 DCA/익절/손절이 작동하나요?

**A**: 네, 작동합니다!

**수동 매수 모드**:
- 매수는 사용자가 Upbit 앱에서 직접
- 프로그램이 감지하여 자동으로 포지션 생성
- DCA/익절/손절은 자동 실행

**사용 사례**:
- "매수는 내가 타이밍 보고 직접 하고 싶어요"
- "자동 매수는 믿음이 안 가요"
- "특정 뉴스 나올 때만 수동으로 매수하고 싶어요"

---

### Q7. 관찰 모드는 언제 사용하나요?

**A**: 거래는 하지 않고 포지션만 추적할 때 사용합니다.

**사용 사례**:
- "이미 보유 중인 코인 수익률만 보고 싶어요"
- "프로그램 테스트 중이라 거래는 안 하고 싶어요"
- "DCA/익절/손절 없이 그냥 홀딩만 할 거예요"

**설정**:
- GUI → "그룹 관리" → 그룹 설정 → "관찰 모드"

---

### Q8. 일일 손실 제한은 어떻게 계산되나요?

**A**: 2가지 방식이 있습니다.

**1. daily_only** (권장):
- 매일 09:00 시점의 총 자산을 기준으로 계산
- 하루 단위 손실만 추적
- 예: 09:00에 1,000만원 → 10% 손실 = 100만원까지 허용

**2. total_account**:
- 초기 자본 대비 총 손실률 계산
- 프로그램 시작 후 누적 손실 추적
- 예: 초기 1,000만원 → 현재 900만원 = -10%

**설정**:
```json
{
  "daily_loss_limit": {
    "enabled": true,
    "loss_pct": 10.0,
    "action": "alert",  // 알림만: "alert", 청산: "liquidate"
    "calculation_method": "daily_only"  // 또는 "total_account"
  }
}
```

---

### Q9. Live 모드와 Dry-run 모드를 동시에 실행할 수 있나요?

**A**: 아니요, 동시 실행은 불가능합니다.

**이유**:
- 포지션 파일이 충돌할 수 있음
- WebSocket 연결이 중복됨
- 시스템 리소스 낭비

**권장 방식**:
1. Dry-run으로 1주일 테스트
2. 만족스러우면 Live로 전환
3. Live 실행 중 추가 테스트 필요하면:
   - Live 종료
   - Dry-run으로 전환
   - 테스트 완료 후 다시 Live로

---

### Q10. V3 설정을 V4로 자동 마이그레이션할 수 있나요?

**A**: 네, 자동으로 마이그레이션됩니다.

**마이그레이션 과정**:
1. V3 설정 파일 감지:
   - `config/settings.json`
   - `config/auto_trading_config.json`

2. V4 형식으로 변환:
   - 기본 그룹 "group_1" 생성
   - V3 설정을 group_1에 복사
   - V3 코인 리스트를 group_1에 할당

3. 백업 생성:
   - `config/settings.json.v3_backup`
   - `config/auto_trading_config.json.v3_backup`

**주의사항**:
- 마이그레이션 후 설정 확인 필수
- 필요시 그룹 재구성 권장

---

## 기타 V4 관련

### Q11. 거래 기록은 어디서 확인하나요?

**A**: `data/trade_history.json` 파일 또는 GUI에서 확인할 수 있습니다.

**파일 확인**:
```bash
cat data/trade_history.json | python -m json.tool
```

**GUI 확인**:
- (향후 구현 예정: 거래 기록 탭)

**그룹별 통계**:
```python
from core.trade_history_manager import TradeHistoryManager
history = TradeHistoryManager()
stats = history.calculate_statistics("group_1")
print(stats)
```

---

### Q12. 포지션을 수동으로 닫을 수 있나요?

**A**: 네, 2가지 방법이 있습니다.

**방법 1: Upbit 앱에서 직접 매도**
- Upbit 앱에서 직접 매도
- 프로그램이 자동으로 감지하여 포지션 닫기

**방법 2: GUI에서 강제 종료**
- (향후 구현 예정: 포지션 우클릭 → "강제 종료")

**주의**:
- 데이터 파일을 수동으로 편집하지 마세요
- 프로그램이 자동으로 동기화합니다

---

### Q13. 그룹 성과를 비교할 수 있나요?

**A**: 네, `trade_history.json`에서 그룹별 통계를 볼 수 있습니다.

**확인 방법**:
```python
from core.trade_history_manager import TradeHistoryManager
history = TradeHistoryManager()

# 그룹 1 성과
stats1 = history.calculate_statistics("group_1")
print(f"그룹 1 승률: {stats1['win_rate']}%")
print(f"그룹 1 총 수익: {stats1['total_profit']}원")

# 그룹 2 성과
stats2 = history.calculate_statistics("group_2")
print(f"그룹 2 승률: {stats2['win_rate']}%")
print(f"그룹 2 총 수익: {stats2['total_profit']}원")
```

**향후 GUI 개선 예정**:
- 그룹별 성과 대시보드
- 그룹 간 비교 차트
```

---

### 7️⃣ **BUILD_GUIDE.md** (빌드 가이드)

**현재 상태**:
- 빌드 프로세스는 V3/V4 동일 (변경 없음)
- Python 코드를 .exe로 패키징하는 방법

**V4 업데이트 내용**:

#### 1. 빌드 전 체크리스트 추가
```markdown
## Pre-Build Checklist (V4)

Before building, ensure:

1. **Configuration Files Included**:
   - `config/trading_config_template.json` ✓
   - `config/schemas/trading_config_schema.json` ✓

2. **Data Folder Structure**:
   ```
   data/
   ├── .gitkeep  (placeholder)
   └── (runtime files will be auto-created)
   ```

3. **V4 Dependencies**:
   ```bash
   pip list | grep -E "PySide6|requests|websocket|jsonschema"
   ```

4. **Test V4 Features**:
   - Create a group
   - Configure DCA/Profit/Loss levels
   - Test dry-run mode
```

#### 2. build_exe.spec 파일에 V4 파일 추가 확인
```markdown
## Verify build_exe.spec

Ensure V4 files are included:

```python
datas=[
    ('config/trading_config_template.json', 'config'),
    ('config/schemas/trading_config_schema.json', 'config/schemas'),
    # ... other files
]
```
```

---

### 8️⃣ **docs/LIVE_TRADING_CHECKLIST.md** (실거래 체크리스트)

**현재 문제**:
- V3 기준 체크리스트
- 그룹 설정 확인 없음

**V4 업데이트 내용**:

#### 1. Configuration Validation 섹션 재작성
```markdown
## 1. Configuration Validation

### ✅ Verify V4 Configuration File

```bash
# Check config exists and is valid JSON
python -m json.tool config/trading_config.json
```

**Expected Structure**:
```json
{
  "version": "4.0",
  "mode": "dryrun",  // ← 먼저 dry-run으로!
  "groups": {
    "group_1": {...}  // ← 최소 1개 그룹
  },
  "daily_loss_limit": {
    "enabled": true,
    "loss_pct": 10.0
  }
}
```

---

### ✅ Verify Each Group Configuration

**For each group, check**:

1. **Buy Settings**:
   - [ ] mode: "auto", "manual", or "observation"
   - [ ] If auto: preset selected (conservative/balanced/aggressive)
   - [ ] buy_amount_krw: reasonable amount (e.g., 50,000 KRW)

2. **DCA Settings**:
   - [ ] Levels defined (e.g., -3%, -5%, -7%)
   - [ ] quantity_ratio reasonable (e.g., 100%)
   - [ ] Not too many levels (recommend ≤ 5)

3. **Profit Settings**:
   - [ ] Levels defined (e.g., +5%, +10%)
   - [ ] quantity_ratio adds up to 100% or less
   - [ ] Not too aggressive (first level ≥ 3%)

4. **Loss Settings**:
   - [ ] At least 1 level defined (e.g., -15%)
   - [ ] quantity_ratio = 100% (cut all losses)
   - [ ] Not too tight (≥ -15% recommended)

**Example Good Configuration**:
```json
{
  "groups": {
    "conservative_trading": {
      "name": "Conservative BTC/ETH",
      "coins": ["KRW-BTC", "KRW-ETH"],
      "buy_settings": {
        "mode": "auto",
        "auto_config": {
          "investment_style": "conservative",
          "buy_amount_krw": 50000
        }
      },
      "dca_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": -5.0, "quantity_ratio": 100},
          {"price_ratio": -10.0, "quantity_ratio": 100}
        ]
      },
      "profit_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": 5.0, "quantity_ratio": 50},
          {"price_ratio": 10.0, "quantity_ratio": 50}
        ]
      },
      "loss_settings": {
        "mode": "auto",
        "levels": [
          {"price_ratio": -15.0, "quantity_ratio": 100}
        ]
      }
    }
  }
}
```

---

### ✅ Verify Daily Loss Limit

```bash
grep -A 5 "daily_loss_limit" config/trading_config.json
```

**Recommended Settings for Live Trading**:
```json
{
  "daily_loss_limit": {
    "enabled": true,
    "loss_pct": 10.0,  // 10% daily loss limit
    "action": "liquidate",  // Force liquidate (not just alert!)
    "calculation_method": "daily_only"  // Reset at 09:00 daily
  }
}
```

**⚠️ CRITICAL**: Set action to "liquidate" for live trading!

---

### ✅ Verify Position Files Exist

```bash
# Check position files
ls -lh data/positions_live.json data/positions_dryrun.json

# Verify they're valid JSON
python -m json.tool data/positions_live.json
python -m json.tool data/positions_dryrun.json
```

**Expected Content** (empty at first):
```json
{
  "positions": {}
}
```
```

#### 2. Dry-run Testing 섹션 확장
```markdown
## 2. Dry-run Testing (MANDATORY)

### ✅ Run Dry-run Mode for Minimum 1 Week

1. Set mode to "dryrun":
```json
{
  "mode": "dryrun"
}
```

2. Start application:
```bash
python main.py
```

3. Monitor for 1 week (7 days minimum)

4. Check results:
```bash
# Check trade history
cat data/trade_history.json | python -m json.tool

# Check positions
cat data/positions_dryrun.json | python -m json.tool

# Check virtual balance
cat data/virtual_balances.json | python -m json.tool
```

---

### ✅ Verify Key Scenarios

**Scenario 1: Auto-buy Execution**
- [ ] Buy signal detected (check logs)
- [ ] Position created in positions_dryrun.json
- [ ] Virtual balance decreased
- [ ] Telegram notification received

**Scenario 2: DCA Execution**
- [ ] Price drops to DCA level (e.g., -3%)
- [ ] Additional buy executed
- [ ] dca_count increased (0 → 1)
- [ ] avg_buy_price updated (lowered)
- [ ] total_invested_krw increased

**Scenario 3: Profit-taking**
- [ ] Price rises to profit level (e.g., +5%)
- [ ] Partial sell executed
- [ ] profit_levels_executed updated
- [ ] Position still active (if partial)
- [ ] Profit recorded in trade_history

**Scenario 4: Stop-loss**
- [ ] Price drops to loss level (e.g., -15%)
- [ ] Full sell executed
- [ ] Position closed
- [ ] Loss recorded in trade_history

**Scenario 5: Daily Loss Limit**
- [ ] Accumulate 10% daily loss
- [ ] Alert/liquidate triggered
- [ ] Next day (09:00) resets correctly

---

### ✅ Calculate Dry-run Performance

```python
from core.trade_history_manager import TradeHistoryManager

history = TradeHistoryManager()

for group_id in ["group_1", "group_2"]:  # Your group IDs
    stats = history.calculate_statistics(group_id)

    print(f"\n=== {group_id} ===")
    print(f"Total Trades: {stats['total_trades']}")
    print(f"Win Rate: {stats['win_rate']:.1f}%")
    print(f"Total Profit: {stats['total_profit']:,} KRW")
    print(f"Avg Profit per Trade: {stats['avg_profit_per_trade']:,.0f} KRW")
```

**Acceptable Results** (for live trading):
- ✅ Win Rate ≥ 55%
- ✅ Total Profit > 0 (positive)
- ✅ No critical errors in logs
- ✅ All scenarios tested successfully
- ✅ No unexpected behavior

**If Dry-run Results Are Poor**:
- ❌ DO NOT switch to live mode
- Adjust group settings (DCA levels, profit targets, etc.)
- Test again for another week
```

#### 3. Live Mode Transition 섹션 확장
```markdown
## 3. Live Mode Transition

### ✅ Final Pre-Live Checklist

**Before switching to live mode, ensure**:

1. **Dry-run Testing Complete**:
   - [ ] Ran for ≥ 7 days
   - [ ] Win rate ≥ 55%
   - [ ] All scenarios tested
   - [ ] No critical errors

2. **Configuration Finalized**:
   - [ ] Groups configured correctly
   - [ ] DCA/Profit/Loss levels validated
   - [ ] Daily loss limit enabled
   - [ ] Telegram notifications working

3. **API Keys Valid**:
   - [ ] Upbit API keys entered
   - [ ] Permissions: "View" + "Trade" (NOT "Withdraw"!)
   - [ ] Test balance query works

4. **Emergency Plan**:
   - [ ] Know how to stop program immediately
   - [ ] Telegram bot commands memorized (/stop, /status)
   - [ ] Phone accessible for manual intervention

5. **Capital Allocation**:
   - [ ] Only trade with money you can afford to lose
   - [ ] Start with small amounts (e.g., 100,000 KRW)
   - [ ] Don't use full exchange balance

---

### ✅ Switch to Live Mode

1. **Backup Current Configuration**:
```bash
cp config/trading_config.json config/trading_config_backup_$(date +%Y%m%d).json
```

2. **Set Mode to "live"**:
```json
{
  "mode": "live"
}
```

3. **Clear Dry-run Positions** (optional):
```bash
# Keep history but clear positions
echo '{"positions": {}}' > data/positions_dryrun.json
```

4. **Restart Application**:
```bash
python main.py
```

5. **Verify Live Mode Active**:
```bash
# Check logs for "Live 모드" message
tail -f logs/trading_*.log | grep "모드"
```

---

### ✅ First Day Monitoring (CRITICAL)

**Monitor closely for first 24 hours**:

1. **Check Every 1-2 Hours**:
   - GUI position table
   - Telegram notifications
   - Upbit exchange balance
   - Position files (data/positions_live.json)

2. **Verify First Trade**:
   - [ ] Buy signal detected correctly
   - [ ] Order executed on exchange
   - [ ] Position created in positions_live.json
   - [ ] Balance updated correctly
   - [ ] Telegram notification received

3. **Verify Position Sync**:
```bash
# Check positions match Upbit exchange
cat data/positions_live.json
```
Compare with Upbit app holdings.

4. **Watch for Errors**:
```bash
# Monitor logs for errors
tail -f logs/trading_*.log | grep -E "ERROR|CRITICAL|❌"
```

**If Any Issues Occur**:
- STOP immediately (/stop in Telegram or close GUI)
- Check logs: `logs/trading_*.log`
- Review recent actions
- Fix issues before restarting
```

---

### 9️⃣ **docs/TECHNICAL_INDICATORS_STANDARD.md** (기술 지표 가이드)

**현재 상태**:
- 단타 전략용 지표 가이드 (V3 기준)
- V4 프리셋과 연결 필요

**V4 업데이트 내용**:

#### 1. V4 Preset Mapping 추가
```markdown
## V4 Preset Indicator Settings

V4의 3가지 프리셋은 아래 지표 조합을 사용합니다:

### Conservative Preset (4-hour candles)

**Target**: Long-term investment, stable entry

**Indicator Settings**:
```json
{
  "candle_unit": "240",  // 4 hours
  "indicators": {
    "rsi": {
      "enabled": true,
      "period": 14,
      "oversold": 25,  // Strong oversold
      "overbought": 75
    },
    "macd": {
      "enabled": true,
      "fast": 12,
      "slow": 26,
      "signal": 9
    },
    "volume": {
      "enabled": true,
      "period": 20,
      "threshold": 2.5  // 250% of average
    }
  }
}
```

**Buy Conditions** (ALL must be true):
1. RSI < 25 (strong oversold)
2. MACD golden cross (MACD line > Signal line)
3. Volume > 2.5x average (high volume surge)

**Characteristics**:
- Fewer buy signals (1-2 per week per coin)
- Higher confidence entries
- Suitable for conservative traders

---

### Balanced Preset (1-hour candles)

**Target**: Balanced trading, recommended for most users

**Indicator Settings**:
```json
{
  "candle_unit": "60",  // 1 hour
  "indicators": {
    "rsi": {
      "enabled": true,
      "period": 14,
      "oversold": 30,  // Standard oversold
      "overbought": 70
    },
    "macd": {
      "enabled": true,
      "fast": 12,
      "slow": 26,
      "signal": 9
    },
    "volume": {
      "enabled": true,
      "period": 20,
      "threshold": 2.0  // 200% of average
    }
  }
}
```

**Buy Conditions** (ALL must be true):
1. RSI < 30 (oversold)
2. MACD golden cross
3. Volume > 2.0x average

**Characteristics**:
- Moderate buy signals (3-5 per week per coin)
- Good balance between frequency and quality
- **Recommended for beginners**

---

### Aggressive Preset (15-minute candles)

**Target**: Scalping, fast entries

**Indicator Settings**:
```json
{
  "candle_unit": "15",  // 15 minutes
  "indicators": {
    "rsi": {
      "enabled": true,
      "period": 14,
      "oversold": 35,  // Mild oversold
      "overbought": 65
    },
    "macd": {
      "enabled": true,
      "fast": 12,
      "slow": 26,
      "signal": 9
    },
    "volume": {
      "enabled": true,
      "period": 20,
      "threshold": 1.5  // 150% of average
    }
  }
}
```

**Buy Conditions** (ALL must be true):
1. RSI < 35 (mild oversold)
2. MACD golden cross
3. Volume > 1.5x average

**Characteristics**:
- Frequent buy signals (10-20 per week per coin)
- Lower confidence but more opportunities
- **Higher risk, requires close monitoring**

---

## Choosing the Right Preset

| Situation | Recommended Preset |
|-----------|-------------------|
| New to crypto trading | **Balanced** |
| Conservative, long-term investor | **Conservative** |
| Experienced trader, active monitoring | **Aggressive** |
| Testing new strategy | **Balanced** (dry-run) |
| High-volatility market | **Conservative** |
| Stable market conditions | **Balanced** or **Aggressive** |
| Limited time to monitor | **Conservative** |
| Full-time trader | **Aggressive** |

---

## Custom Preset

If none of the presets fit, use Custom mode:

**How to Configure**:
1. GUI → 그룹 설정 → 자동매수 설정
2. Select "Custom" radio button
3. Adjust indicators manually:
   - RSI oversold level (20-40)
   - Volume threshold (1.0-3.0x)
   - MACD parameters (advanced)

**Example Custom Settings**:
```json
{
  "candle_unit": "30",  // 30 minutes (between Balanced and Aggressive)
  "indicators": {
    "rsi": {
      "oversold": 32
    },
    "volume": {
      "threshold": 1.8
    }
  }
}
```

**⚠️ Warning**: Custom settings require backtesting!
```

---

### 🔟 **docs/TELEGRAM_설정_가이드.md** (텔레그램 가이드)

**현재 상태**:
- 텔레그램 봇 설정 방법 (V3/V4 동일)
- 명령어 리스트

**V4 업데이트 내용**:

#### 1. V4 알림 메시지 예시 추가
```markdown
## V4 Notification Examples

### Auto-buy Signal (V4)

```
🤖 자동매수 신호 감지

그룹: 비트코인 단타
코인: KRW-BTC
프리셋: Balanced (1H)

현재가: 45,000,000원
RSI: 28.5 (< 30 ✓)
MACD: Golden Cross ✓
Volume: 2.3x (> 2.0x ✓)

매수 예정 금액: 50,000원
```

---

### DCA Execution (V4)

```
📈 DCA 레벨 2 실행

그룹: 알트코인 중장기
코인: KRW-ETH
현재 손익률: -5.2%

DCA 설정: -5.0% / 100%
추가 매수: 50,000원
평균 단가: 3,200,000원 → 3,100,000원
총 투자: 50,000원 → 100,000원
```

---

### Profit-taking (V4)

```
🎉 익절 레벨 1 실행

그룹: 비트코인 단타
코인: KRW-BTC
수익률: +5.3%

익절 설정: +5.0% / 50%
매도 수량: 0.00111 BTC (50%)
매도 가격: 47,500,000원
실현 수익: +2,500원
```

---

### Daily Loss Limit (V4)

```
⚠️ 일일 손실 한도 도달

그룹: 전체
현재 손실률: -10.2%
한도: -10.0%

액션: 알림
(liquidate로 설정 시 전량 청산됩니다)

09:00에 자동 리셋됩니다.
```
```

#### 2. V4 Commands 추가
```markdown
## Telegram Bot Commands (V4)

### /status - 현재 상태 확인

```
📊 V4 시스템 상태

모드: Live
활성 그룹: 3개

--- 그룹 1: 비트코인 단타 ---
코인: BTC, ETH (2개)
매수 방식: 자동 (Balanced)
활성 포지션: 2개
그룹 수익률: +3.2%

--- 그룹 2: 알트코인 중장기 ---
코인: XRP, ADA, DOT (3개)
매수 방식: 자동 (Conservative)
활성 포지션: 1개
그룹 수익률: -1.5%

--- 그룹 3: 관찰 전용 ---
코인: DOGE, SHIB (2개)
매수 방식: 관찰 모드
활성 포지션: 0개

일일 손실 한도: -10.0% (현재: -2.3%)
KRW 잔고: 500,000원
```

---

### /group <group_id> - 그룹 상세 정보

```
/group group_1

📋 그룹 상세 정보

그룹 ID: group_1
그룹 이름: 비트코인 단타

코인 (2개):
• KRW-BTC (활성)
• KRW-ETH (활성)

설정:
• 매수: 자동 (Balanced, 1H)
• DCA: 3레벨 (-3%, -5%, -7%)
• 익절: 2레벨 (+5%, +10%)
• 손절: 1레벨 (-15%)

성과:
• 총 거래: 15회
• 승률: 66.7%
• 총 수익: +45,000원
• 평균 수익/거래: +3,000원
```

---

### /positions - 전체 포지션 조회

```
📊 활성 포지션 (3개)

--- 그룹: 비트코인 단타 ---
BTC: 0.00222 (45,000,000원)
  진입가: 44,500,000원
  현재가: 45,000,000원
  손익: +1.1% (+24,750원)
  DCA: 0/3

ETH: 0.0156 (3,200,000원)
  진입가: 3,150,000원
  현재가: 3,200,000원
  손익: +1.6% (+2,560원)
  DCA: 1/3 (평단가 개선됨)

--- 그룹: 알트코인 중장기 ---
XRP: 50 (1,000원)
  진입가: 1,050원
  현재가: 1,000원
  손익: -4.8% (-2,500원)
  DCA: 0/3
```

---

### /stop_group <group_id> - 그룹 중지

```
/stop_group group_1

⏸️ 그룹 중지 완료

그룹: 비트코인 단타
상태: 중지됨

영향:
• 자동매수 중지
• DCA 중지
• 익절/손절 계속 작동 (포지션 보호)

재시작: /start_group group_1
```

---

### /daily_reset - 일일 손실 리셋 (수동)

```
/daily_reset

🔄 일일 손실 한도 수동 리셋

이전 스냅샷: 1,000,000원
현재 자산: 950,000원
오늘 손실: -50,000원 (-5.0%)

새 스냅샷 생성: 950,000원
손실률 리셋: 0.0%

⚠️ 주의: 정상적으로는 09:00에 자동 리셋됩니다.
수동 리셋은 긴급 상황에만 사용하세요.
```
```

---

## 📝 요약

총 **10개 필수 문서**에 대한 V4 업데이트 계획:

| # | 문서 | 주요 업데이트 내용 | 우선순위 |
|---|------|-------------------|----------|
| 1 | README.md | 프로젝트 소개, 그룹 시스템 강조, 빠른 시작 가이드 | ⭐⭐⭐ 최우선 |
| 2 | CLAUDE.md | V4 아키텍처, 핵심 컴포넌트, 개발 워크플로우 | ⭐⭐⭐ 최우선 |
| 3 | INSTALLATION.md | V4 첫 실행, 파일 생성 확인 | ⭐⭐ 중간 |
| 4 | ENVIRONMENT_SETUP.md | V4 그룹 설정, 첫 그룹 생성 가이드 | ⭐⭐⭐ 최우선 |
| 5 | TROUBLESHOOTING.md | V4 특화 문제 (그룹, 포지션, DCA 순차 실행) | ⭐⭐⭐ 최우선 |
| 6 | FAQ.md | V4 그룹 시스템 질문 (13개 질문 추가) | ⭐⭐⭐ 최우선 |
| 7 | BUILD_GUIDE.md | V4 파일 포함 확인 | ⭐ 낮음 |
| 8 | LIVE_TRADING_CHECKLIST.md | V4 설정 검증, 그룹별 체크리스트 | ⭐⭐⭐ 최우선 |
| 9 | TECHNICAL_INDICATORS_STANDARD.md | V4 프리셋 매핑, 지표 설정 | ⭐⭐ 중간 |
| 10 | TELEGRAM_설정_가이드.md | V4 알림 메시지, 그룹 명령어 | ⭐⭐ 중간 |

---

## 🚀 실행 계획

### Phase 1: 최우선 문서 (1-2일)
1. README.md
2. CLAUDE.md
3. ENVIRONMENT_SETUP.md
4. TROUBLESHOOTING.md
5. FAQ.md
6. LIVE_TRADING_CHECKLIST.md

### Phase 2: 중간 우선순위 (1일)
7. INSTALLATION.md
8. TECHNICAL_INDICATORS_STANDARD.md
9. TELEGRAM_설정_가이드.md

### Phase 3: 낮은 우선순위 (필요 시)
10. BUILD_GUIDE.md

---

## ✅ 검증 방법

각 문서 업데이트 후:
1. ✅ V3 언급 제거 확인
2. ✅ 그룹 시스템 설명 포함 확인
3. ✅ 실제 코드/설정과 일치 확인
4. ✅ 사용자 관점에서 이해 가능한지 확인
5. ✅ 스크린샷 필요 시 추가

---

**작성 완료**: 2025-11-13
**다음 단계**: Phase 1 문서부터 순차 업데이트 시작
