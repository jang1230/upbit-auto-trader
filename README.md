# Upbit DCA Trader V4

> **암호화폐 자동 매매 트레이딩 봇**
> 그룹 기반 멀티 전략 + DCA 리스크 관리 + 실시간 알림

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![V4 Status](https://img.shields.io/badge/V4-Phase%202%20Complete%20(100%25)-success.svg)](docs/DESIGN_V4_COMPLETE.md)

---

## 🎯 핵심 특징

### ✨ V4 그룹 기반 시스템

- **무제한 그룹 생성** - 그룹별로 다른 전략/설정 적용
- **3가지 매수 방식**
  - 🤖 **자동매수**: Conservative/Balanced/Aggressive 프리셋
  - 👤 **수동매수**: 외부 거래 감지 → 자동 포지션 생성
  - 👁️ **관찰 모드**: 포지션 추적만, 거래 안 함

- **그룹별 독립 설정**
  - 📊 DCA 레벨 (하락 시 분할 매수)
  - 📈 익절 레벨 (수익 실현 자동화)
  - 📉 손절 레벨 (손실 제한)

- **포지션 손실 한도** - 24시간 암호화폐 시장에 적합한 손실 관리
- **실시간 모니터링** - PySide6 GUI + Telegram 알림
- **Live/Dry-run 분리** - 테스트와 실거래 완전 분리

---

## ⚡ 빠른 시작

### 1. 설치

```bash
git clone https://github.com/jang1230/upbit-auto-trader.git
cd upbit-auto-trader
pip install -r requirements.txt
```

### 2. API 키 설정

- Upbit API 키 발급 ([https://upbit.com/mypage/open_api_management](https://upbit.com/mypage/open_api_management))
- GUI 실행 후 설정에서 API 키 입력

### 3. 첫 그룹 생성

1. **GUI 실행**: `python main.py`
2. **그룹 관리 버튼** 클릭 (상단)
3. **그룹 추가** → 이름 입력 (예: "비트코인 단타")
4. **코인 선택** (예: KRW-BTC, KRW-ETH)
5. **매수 방식 설정**:
   - 자동매수 → **Balanced** 프리셋 선택
   - 매수 금액: 50,000원
6. **DCA/익절/손절 설정**:
   - DCA: -3%, -5%, -7% (각 100%)
   - 익절: +5% (50%), +10% (50%)
   - 손절: -15% (100%)

### 4. 시작

- **Dry-run 모드**로 먼저 테스트 (최소 1주일)
- 정상 동작 확인 후 **Live 모드** 전환

---

## 📋 목차

- [소개](#소개)
- [V4 새로운 기능](#v4-새로운-기능)
- [시스템 구조](#시스템-구조)
- [설치 및 설정](#설치-및-설정)
- [사용 방법](#사용-방법)
- [문서](#문서)
- [FAQ](#faq)
- [주의사항](#주의사항)

---

## 소개

**Upbit DCA Trader V4**는 업비트(Upbit) 거래소에서 암호화폐를 자동으로 매매하는 트레이딩 봇입니다.

### V4의 핵심 개선사항

V3의 2가지 모드(반자동/완전자동) 한계를 극복하고, **무제한 그룹** 기반으로 전면 재설계되었습니다.

| 기능 | V3 | V4 |
|------|----|----|
| 트레이딩 모드 | 2개 (반자동/완전자동) | **무제한 그룹** |
| 코인 관리 | 전역 설정 | **그룹별 독립 관리** |
| 매수 전략 | 단일 전략 | **그룹별 프리셋** (Conservative/Balanced/Aggressive) |
| DCA 설정 | 전역 설정 | **그룹별 독립 설정** |
| 익절/손절 | 단일 레벨 | **다단계 레벨 지원** |
| 포지션 손실 한도 | 없음 | **24시간 시장에 적합한 포지션 기반** |
| 포지션 파일 | 1개 | **2개 (live/dryrun 분리)** |

📖 **V4 상세 문서**: [DESIGN_V4_COMPLETE.md](docs/DESIGN_V4_COMPLETE.md) (172KB, 18개 섹션)

---

## V4 새로운 기능

### 1. 그룹 기반 트레이딩

**이제 원하는 만큼 그룹을 만들 수 있습니다!**

```
그룹 1: "비트코인 단타"
  - 코인: BTC, ETH
  - 매수: Aggressive (15분봉)
  - DCA: -2%, -4%, -6%
  - 익절: +3%, +7%

그룹 2: "알트코인 중장기"
  - 코인: XRP, ADA, DOT
  - 매수: Conservative (4시간봉)
  - DCA: -5%, -10%, -15%
  - 익절: +10%, +20%

그룹 3: "관찰 전용"
  - 코인: DOGE, SHIB
  - 매수: 관찰 모드 (거래 안 함)
```

### 2. 자동매수 프리셋

#### 🐢 Conservative (보수적)
- **캔들**: 4시간봉
- **RSI**: < 25 (강한 과매도)
- **Volume**: > 2.5x 평균
- **특징**: 안정적 진입, 장기 투자

#### ⚖️ Balanced (균형) - 권장
- **캔들**: 1시간봉
- **RSI**: < 30 (과매도)
- **Volume**: > 2.0x 평균
- **특징**: 균형잡힌 트레이딩

#### 🚀 Aggressive (공격적)
- **캔들**: 15분봉
- **RSI**: < 35 (약한 과매도)
- **Volume**: > 1.5x 평균
- **특징**: 빠른 진입, 단타용

### 3. 다단계 DCA/익절/손절

**각 그룹마다 독립적인 레벨 설정 가능**:

```json
{
  "dca_levels": [
    {"price_ratio": -3.0, "quantity_ratio": 100},
    {"price_ratio": -5.0, "quantity_ratio": 100},
    {"price_ratio": -7.0, "quantity_ratio": 100}
  ],
  "profit_levels": [
    {"price_ratio": 5.0, "quantity_ratio": 50},
    {"price_ratio": 10.0, "quantity_ratio": 50}
  ],
  "loss_levels": [
    {"price_ratio": -15.0, "quantity_ratio": 100}
  ]
}
```

### 4. 포지션 손실 한도

- **24시간 암호화폐 시장에 적합** (일일 리셋 없음)
- **손실률 도달 시**:
  - `alert`: 텔레그램 알림 + 매수 중단
  - `liquidate`: 전량 청산 + 매수 중단
- **관찰 그룹 제외**: 관찰 전용 그룹은 손실 계산에서 제외 가능

---

## 시스템 구조

### V4 아키텍처

```
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
│  - Position Loss Limit              │
└────────┬────────────────────────────┘
         │
┌────────▼───────┐  ┌─────────────┐  ┌──────────────┐
│ V4AutoBuy      │  │ WebSocket   │  │ Upbit API    │
│ Strategy       │  │ (Real-time) │  │ (REST)       │
└────────────────┘  └─────────────┘  └──────────────┘
```

### 핵심 컴포넌트 (V4)

**1. V4TradingEngine** (`core/v4_trading_engine.py`, 930 lines)
- Main orchestrator for V4 system
- Group-level trading loops
- Position monitoring (60-second polling)
- Auto-buy strategy execution
- DCA/Profit/Loss trigger logic
- Position loss limit enforcement

**2. GroupManager** (`core/group_manager.py`, 578 lines)
- Group lifecycle: create, delete, update
- Coin management: add, remove, move between groups
- Cross-group validation (prevent coin duplication)

**3. ConfigManager** (`core/config_manager.py`, 512 lines)
- Unified configuration management (`trading_config.json`)
- JSON Schema validation
- V3→V4 automatic migration

**4. PositionManager** (`core/position_manager.py`, 656 lines)
- Separate files: `positions_live.json`, `positions_dryrun.json`
- CRUD operations: create, update, close positions
- DCA management: `add_dca()`, track `dca_levels_executed`
- Upbit synchronization: `sync_with_upbit()`

**5. TradeHistoryManager** (`core/trade_history_manager.py`, 479 lines)
- Records all trades to `data/trade_history.json`
- Group-level statistics calculation

**6. V4AutoBuyStrategy** (`core/strategies/v4_auto_buy_strategy.py`, 456 lines)
- Preset-based auto-buy: Conservative (4H), Balanced (1H), Aggressive (15min)
- Technical indicators: RSI, MACD, Volume
- Group-level strategy assignment

---

## 설치 및 설정

### 사전 요구사항

- **Python**: 3.8 이상
- **운영체제**: Windows, Mac, Linux
- **텔레그램**: 알림 수신용 (선택)
- **업비트 API**: 실거래 시 필요

### 설치

```bash
# 1. 프로젝트 클론
git clone https://github.com/jang1230/upbit-auto-trader.git
cd upbit-auto-trader

# 2. 의존성 설치
pip install -r requirements.txt

# 3. GUI 실행
python main.py
```

**첫 실행 시 V4가 자동 생성하는 파일**:
- `config/trading_config.json` (통합 설정 파일)
- `data/positions_live.json` (Live 포지션)
- `data/positions_dryrun.json` (Dry-run 포지션)
- `data/trade_history.json` (거래 기록)
- `data/virtual_balances.json` (Dry-run 잔고)

### 첫 그룹 생성 (GUI)

#### Step 1: 그룹 관리 열기
- GUI 상단 **"📁 그룹 관리"** 버튼 클릭

#### Step 2: 그룹 추가
- **"그룹 추가"** 클릭
- 그룹 이름 입력 (예: "비트코인 단타")

#### Step 3: 코인 선택
- **"코인 선택"** 클릭
- 원하는 코인 체크 (예: KRW-BTC, KRW-ETH)
- 저장

#### Step 4: 그룹 설정

**매수 설정**:
1. **"⚙️ 그룹 설정"** 클릭
2. 매수 모드: **"자동매수"** 선택
3. **"⚙️ 자동매수 설정..."** 클릭
4. 프리셋 선택: **Balanced** (권장)
5. 매수 금액: 50,000원
6. 저장

**DCA/익절/손절 설정**:
1. **"⚙️ 레벨 상세 설정"** 클릭
2. **DCA 탭**:
   - Level 1: -3% / 100%
   - Level 2: -5% / 100%
   - Level 3: -7% / 100%
3. **익절 탭**:
   - Level 1: +5% / 50% (절반 익절)
   - Level 2: +10% / 50% (나머지 익절)
4. **손절 탭**:
   - Level 1: -15% / 100% (전량 손절)
5. 저장

#### Step 5: API 키 설정 (실거래 시)

**Upbit API 키**:
1. Upbit 웹사이트 → Open API 관리
2. 새 API 키 발급 (권한: 자산 조회, 주문 조회, 주문 등록/취소)
3. GUI → **⚙️ 설정** → **🔑 API 키** 탭
4. Access Key, Secret Key 입력 → 저장

**텔레그램 봇** (알림용):
1. @BotFather에게 `/newbot` 명령
2. 봇 토큰 복사
3. GUI → **⚙️ 설정** → **📱 텔레그램** 탭
4. 봇 토큰, Chat ID 입력 → 저장

📖 **상세 가이드**: [ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md)

---

## 사용 방법

### 1단계: Dry-run 테스트 (필수)

**최소 1주일 이상 Dry-run 모드로 테스트하세요!**

1. `config/trading_config.json` 열기
2. `"mode": "dryrun"` 설정
3. GUI에서 **"🚀 트레이딩 시작"** 클릭
4. 1주일 모니터링:
   - GUI에서 포지션 확인
   - 텔레그램 알림 확인
   - `data/trade_history.json` 성과 확인

**Dry-run 검증 기준**:
- ✅ 수익률 > 0%
- ✅ 승률 ≥ 55%
- ✅ 오류 없이 안정적 운영
- ✅ 모든 시나리오 테스트 (자동매수, DCA, 익절, 손절)

### 2단계: Live 모드 전환 (검증 후)

**⚠️ Dry-run 테스트 완료 후에만 진행하세요!**

1. `config/trading_config.json` 열기
2. `"mode": "live"` 변경
3. 프로그램 재시작
4. **소액**으로 시작 (예: 50,000원)
5. 첫 24시간 집중 모니터링

### 3단계: 모니터링

**텔레그램 명령어**:
```
/status        - 현재 포지션 및 그룹 상태
/group <id>    - 특정 그룹 상세 정보
/positions     - 전체 포지션 조회
/stop          - 트레이딩 중지
/help          - 도움말
```

**GUI**:
- 실시간 포지션 테이블
- 그룹별 수익률
- 로그 출력

---

## 문서

### 필수 문서 ⭐

1. **[INSTALLATION.md](docs/INSTALLATION.md)** - 설치 가이드
2. **[ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md)** - V4 환경 설정
3. **[LIVE_TRADING_CHECKLIST.md](docs/LIVE_TRADING_CHECKLIST.md)** - 실거래 체크리스트
4. **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - 문제 해결

### 참고 문서

5. **[FAQ.md](docs/FAQ.md)** - 자주 묻는 질문
6. **[TELEGRAM_설정_가이드.md](docs/TELEGRAM_설정_가이드.md)** - 텔레그램 설정
7. **[DESIGN_V4_COMPLETE.md](docs/DESIGN_V4_COMPLETE.md)** - V4 상세 설계
8. **[CLAUDE.md](CLAUDE.md)** - 개발자 가이드

### V3 관련 문서 (아카이브)

V3 Phase 문서는 `docs/archive/` 폴더로 이동되었습니다.

---

## FAQ

### Q1. V3과 V4의 차이점은 무엇인가요?

**A**: V3은 2가지 모드만 지원했지만, V4는 무제한 그룹을 만들 수 있습니다.

| 항목 | V3 | V4 |
|------|----|----|
| 모드 | 2가지 (반자동/완전자동) | 무제한 그룹 |
| 설정 파일 | 2개 분리 | 1개 통합 |
| 코인별 설정 | 불가능 (모두 동일) | 가능 (그룹별 독립) |
| 포지션 파일 | 1개 | 2개 (live/dryrun 분리) |
| 포지션 손실 한도 | 없음 | 있음 (24시간 시장 적합) |

### Q2. 그룹을 최대 몇 개까지 만들 수 있나요?

**A**: 제한이 없습니다. 시스템 성능이 허용하는 한 원하는 만큼 만들 수 있습니다.

**권장 사용 예시**:
- 전략별 분리 (단타, 중장기, 실험)
- 코인 유형별 분리 (메이저코인, 알트코인)
- 리스크 수준별 분리 (안전, 공격적)

### Q3. 한 코인을 여러 그룹에 동시에 넣을 수 있나요?

**A**: 아니요, 한 코인은 하나의 그룹에만 속할 수 있습니다.

**이유**: 중복 매수/매도 방지, 포지션 관리 명확화

### Q4. 자동매수 프리셋의 차이점은 무엇인가요?

**A**: 캔들 주기와 지표 민감도가 다릅니다.

| 프리셋 | 캔들 | RSI | Volume | 매수 빈도 |
|--------|------|-----|--------|-----------|
| Conservative | 4시간 | < 25 | > 2.5x | 낮음 (안정적) |
| Balanced | 1시간 | < 30 | > 2.0x | 중간 (권장) |
| Aggressive | 15분 | < 35 | > 1.5x | 높음 (빠른 진입) |

### Q5. 수동 매수 모드에서도 DCA/익절/손절이 작동하나요?

**A**: 네! 매수는 사용자가 Upbit 앱에서 직접 하고, 프로그램이 감지하여 자동으로 포지션 생성 후 DCA/익절/손절을 자동 실행합니다.

### Q6. Live 모드와 Dry-run 모드를 동시에 실행할 수 있나요?

**A**: 아니요, 동시 실행은 불가능합니다.

**권장 방식**:
1. Dry-run으로 1주일 테스트
2. 만족스러우면 Live로 전환

### Q7. 포지션 손실 한도는 어떻게 작동하나요?

**A**: 개별 포지션의 손익률을 실시간 모니터링합니다.

- 설정된 손실률(예: -10%)에 도달하면 `alert` 또는 `liquidate` 실행
- 24시간 암호화폐 시장에 적합한 리스크 관리 방식
- `exclude_observation_groups`: 관찰 전용 그룹 제외 옵션

### Q8. V3 설정을 V4로 자동 마이그레이션할 수 있나요?

**A**: 네, V4 첫 실행 시 V3 설정 파일을 감지하면 자동으로 마이그레이션됩니다.

- V3 파일을 `group_1`로 변환
- 백업 파일 생성 (`*.v3_backup`)

### Q9. 24시간 컴퓨터를 켜두어야 하나요?

**A**: 예, AWS/GCP 같은 클라우드 서버 사용을 권장합니다.

### Q10. 실전 배포 시 초기 자본은 얼마가 적당한가요?

**A**: 처음에는 최소 50,000원부터 시작하세요. 몇 주간 안정적 운영 확인 후 점진적으로 증액하세요.

---

## 주의사항

### ⚠️ 투자 위험 고지

**이 봇은 투자 손실 위험이 있습니다!**

- 과거 성과가 미래 성과를 보장하지 않습니다
- 암호화폐 시장은 변동성이 매우 큽니다
- **손실 가능한 금액만 투자하세요**
- 투자 결정은 본인의 책임입니다

### 🔒 보안 주의사항

1. **API 키 보안**
   - `.env` 파일을 절대 공유하지 마세요
   - GitHub에 업로드하지 마세요
   - 정기적으로 API 키 변경

2. **텔레그램 봇 토큰**
   - 봇 토큰을 타인과 공유하지 마세요
   - Chat ID를 공개하지 마세요

### 🐛 버그 제보

버그를 발견하시면:
1. GitHub Issues에 등록
2. 에러 메시지 전체 복사
3. 재현 방법 상세히 설명
4. 로그 파일 첨부 (민감한 정보 제거 후)

### 💡 기여하기

프로젝트 기여를 환영합니다!

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## 프로젝트 히스토리

### V4 (2025-01, 현재)
- ✅ **Phase 1 완료**: 데이터 구조 (ConfigManager, PositionManager, TradeHistoryManager)
- ✅ **Phase 2 완료**: 백엔드 핵심 (GroupManager, V4AutoBuyStrategy, V4TradingEngine)
- ⏳ **Phase 3 진행 중**: GUI 리팩토링
- ⏳ **Phase 4 대기 중**: 통합 테스트
- ⏳ **Phase 5 대기 중**: V3→V4 마이그레이션 및 배포

### V3 (2024-12, 완료)
- Phase 1-4 완료 (WebSocket, REST API, Telegram, GUI)
- ScalpingStrategy 운영
- 반자동/완전자동 2가지 모드

📖 **V3 히스토리**: [docs/archive/](docs/archive/) 폴더 참조

---

## 로드맵

### 단기 (1-2주)
- [ ] V4 Phase 3: GUI 완성 (그룹 관리 대화창)
- [ ] V4 Phase 4: 통합 테스트

### 중기 (1-2개월)
- [ ] V4 Phase 5: V3→V4 마이그레이션 가이드
- [ ] Dry-run 테스트 (1주일)
- [ ] 소액 Live 배포

### 장기 (3개월+)
- [ ] 통계 대시보드 (그룹별 성과 비교)
- [ ] 백테스팅 프레임워크 개선
- [ ] 머신러닝 통합

---

## 라이선스

MIT License

Copyright (c) 2025 Upbit DCA Trader

---

## 면책 조항

이 소프트웨어는 교육 및 연구 목적으로 제공됩니다.

- 투자 조언이 아닙니다
- 수익을 보장하지 않습니다
- 사용으로 인한 손실에 대해 책임지지 않습니다
- 투자 결정은 본인의 책임입니다

**투자에는 위험이 따르며, 원금 손실 가능성이 있습니다.**

---

## 연락처

- **GitHub**: https://github.com/jang1230/upbit-auto-trader
- **Issues**: https://github.com/jang1230/upbit-auto-trader/issues

---

**Happy Trading! 🚀📈**

*"The best investment you can make is in yourself."* - Warren Buffett
