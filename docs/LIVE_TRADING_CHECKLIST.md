# 🚨 실계좌 거래 전 필수 체크리스트 (V4)

**주의**: 이 문서는 Dry-run에서 Live 모드로 전환하기 전에 **반드시** 확인해야 할 사항들을 정리한 것입니다.

---

## ⚠️ 사전 준비 사항

### 1. Dry-run 충분한 테스트 완료
- [ ] 최소 1주일 이상 Dry-run 모드로 안정적 운영 확인
- [ ] 모든 거래 시나리오가 예상대로 동작하는지 확인 (자동매수, DCA, 익절, 손절)
- [ ] 로그 파일에 에러가 없는지 확인
- [ ] 승률 ≥ 55% 달성
- [ ] 수익률 > 0% 달성

### 2. API 키 설정
- [ ] Upbit API 키 발급 완료
- [ ] **권한 확인**: 자산 조회, 주문 조회, 주문 등록/취소 ✅
- [ ] **권한 확인**: 출금 **제외** ❌ (보안상 필수)
- [ ] API 키가 GUI 설정에 올바르게 저장됨
- [ ] IP 화이트리스트 설정 (선택사항, 보안 강화)

### 3. V4 설정 파일 검증 ✅

#### ✅ Verify V4 Configuration File

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

### 4. 각 그룹 설정 검증 ⭐⭐⭐

**For each group, check**:

#### 1. **Buy Settings**:
   - [ ] `mode`: "auto", "manual", or "observation" 확인
   - [ ] If auto: preset 선택 확인 (conservative/balanced/aggressive)
   - [ ] `buy_amount_krw`: 합리적인 금액 (예: 50,000 KRW)
   - [ ] **첫 실행 시 소액 권장**: 10,000 ~ 50,000원

#### 2. **DCA Settings**:
   - [ ] Levels defined (예: -3%, -5%, -7%)
   - [ ] `quantity_ratio` 합리적 (예: 100%)
   - [ ] 너무 많은 레벨 없음 (권장 ≤ 5)
   - [ ] **같은 값 중복 없음** (DCA, 익절, 손절 간)

#### 3. **Profit Settings**:
   - [ ] Levels defined (예: +5%, +10%)
   - [ ] `quantity_ratio` 합계 100% 이하
   - [ ] 너무 공격적이지 않음 (첫 레벨 ≥ 3%)

#### 4. **Loss Settings**:
   - [ ] 최소 1 레벨 정의 (예: -15%)
   - [ ] `quantity_ratio` = 100% (전량 손절)
   - [ ] 너무 타이트하지 않음 (≥ -15% 권장)

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

### 5. Daily Loss Limit 검증 ⭐

```bash
grep -A 5 "daily_loss_limit" config/trading_config.json
```

**Recommended Settings for Live Trading**:
```json
{
  "daily_loss_limit": {
    "enabled": true,
    "loss_pct": 10.0,  // 10% daily loss limit
    "action": "liquidate",  // ⚠️ Force liquidate (not just alert!)
    "calculation_method": "daily_only"  // Reset at 09:00 daily
  }
}
```

**⚠️ CRITICAL**: Set `action` to "liquidate" for live trading!

- [ ] `enabled`: true
- [ ] `loss_pct`: 합리적 (5% ~ 15%)
- [ ] `action`: "liquidate" (실거래 시 필수)
- [ ] `calculation_method`: "daily_only" (권장)

---

### 6. Position Files 검증

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

- [ ] `positions_live.json` 존재
- [ ] `positions_dryrun.json` 존재
- [ ] 유효한 JSON 형식

---

## 🔍 필수 Dry-run 테스트 항목 (MANDATORY)

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

#### Scenario 1: Auto-buy Execution
- [ ] Buy signal detected (check logs)
- [ ] Position created in `positions_dryrun.json`
- [ ] Virtual balance decreased
- [ ] Telegram notification received

#### Scenario 2: DCA Execution
- [ ] Price drops to DCA level (e.g., -3%)
- [ ] Additional buy executed
- [ ] `dca_count` increased (0 → 1)
- [ ] `avg_buy_price` updated (lowered)
- [ ] `total_invested_krw` increased
- [ ] **No duplicate execution** (Level 1 only once)

#### Scenario 3: Profit-taking
- [ ] Price rises to profit level (e.g., +5%)
- [ ] Partial sell executed
- [ ] `profit_levels_executed` updated
- [ ] Position still active (if partial)
- [ ] Profit recorded in `trade_history`

#### Scenario 4: Stop-loss
- [ ] Price drops to loss level (e.g., -15%)
- [ ] Full sell executed
- [ ] Position closed
- [ ] Loss recorded in `trade_history`

#### Scenario 5: Daily Loss Limit
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
- [ ] ✅ Win Rate ≥ 55%
- [ ] ✅ Total Profit > 0 (positive)
- [ ] ✅ No critical errors in logs
- [ ] ✅ All scenarios tested successfully
- [ ] ✅ No unexpected behavior

**If Dry-run Results Are Poor**:
- ❌ DO NOT switch to live mode
- Adjust group settings (DCA levels, profit targets, etc.)
- Test again for another week

### 1. 포지션 동기화 테스트 ⭐⭐⭐
**이유**: 기존 보유 자산과 프로그램이 올바르게 동기화되는지 확인

**테스트 방법**:
```bash
python test_position_sync.py
```

**확인 사항**:
- [ ] ✅ 모든 테스트 통과 확인
- [ ] `_find_group_for_coin()` 테스트 통과
- [ ] `sync_with_upbit()` 테스트 통과
- [ ] 기존 포지션 업데이트 정상
- [ ] 새 포지션 생성 정상
- [ ] 고아 포지션 삭제 정상
- [ ] 그룹 없는 코인 스킵 정상

**만약 테스트 실패 시**:
- 🚨 **절대 실계좌 전환하지 마세요**
- 개발자에게 문의하거나 로그 확인 필요

---

### 2. 실계좌 포지션 확인 (첫 실행 전)

**Upbit 웹사이트/앱에서 수동 확인**:
- [ ] 현재 보유 중인 코인 목록 확인
- [ ] 각 코인의 평균 매수가 확인
- [ ] 각 코인의 수량 확인
- [ ] 이 중 `trading_config.json`의 그룹에 속한 코인만 프로그램이 관리할 것임을 이해

**예시**:
```
Upbit 보유 자산:
- KRW-BTC: 0.001 BTC @ 95,000,000원
- KRW-ETH: 0.05 ETH @ 3,000,000원
- KRW-SOL: 1.5 SOL @ 150,000원

trading_config.json:
{
  "groups": {
    "group_1": {
      "coins": ["KRW-BTC", "KRW-ETH"]
    }
  }
}

→ KRW-BTC, KRW-ETH만 프로그램이 관리
→ KRW-SOL은 스킵됨 (수동으로만 관리)
```

---

### 3. sync_with_upbit() 동작 시나리오 이해 ⭐⭐⭐

**프로그램 시작 시 동작**:

#### 시나리오 1: 기존 포지션이 있고 Upbit에도 존재
```
로컬: KRW-BTC (0.001 @ 90M원)
Upbit: BTC (0.001 @ 95M원)
그룹: group_1에 KRW-BTC 포함

→ 결과: 로컬 포지션 업데이트 (95M원으로 변경)
→ ✅ Upbit 데이터가 진리의 원천
```

#### 시나리오 2: Upbit에만 존재, 그룹에 속함
```
로컬: 포지션 없음
Upbit: ETH (0.05 @ 3M원)
그룹: group_1에 KRW-ETH 포함

→ 결과: 자동 포지션 생성
→ ✅ 프로그램이 관리 시작
```

#### 시나리오 3: Upbit에만 존재, 그룹에 없음
```
로컬: 포지션 없음
Upbit: SOL (1.5 @ 150K원)
그룹: 어디에도 KRW-SOL 없음

→ 결과: 스킵 (포지션 생성 안 함)
→ ✅ 수동으로만 관리, 프로그램이 건드리지 않음
```

#### 시나리오 4: 로컬에만 존재, Upbit에 없음 ⚠️
```
로컬: KRW-ADA (100 @ 1,000원)
Upbit: ADA 보유량 0 (완전 매도됨)

→ 결과: 자동 삭제
→ ✅ 완전 매도된 것으로 간주하고 포지션 제거
```

**확인 사항**:
- [ ] 위 4가지 시나리오를 완전히 이해했는가?
- [ ] 프로그램이 관리할 코인과 수동 관리할 코인을 구분했는가?
- [ ] 자동 삭제 동작이 문제없음을 이해했는가?

---

### 4. 첫 실행 테스트 (소액)

**첫 실행 시 권장사항**:
- [ ] **소액**으로 시작 (예: 각 코인당 10,000원)
- [ ] 관찰 전용 모드 활성화 고려 (`observation_only: true`)
- [ ] Telegram 알림 설정 완료
- [ ] 로그 실시간 모니터링 준비

**첫 실행 시 확인**:
```bash
# 프로그램 시작
python main.py

# 로그 확인 (별도 터미널)
tail -f logs/trading_*.log
```

**첫 실행 로그에서 확인할 것**:
- [ ] `🔄 Upbit 동기화 시작...` 로그 출력
- [ ] `💰 KRW 잔고: XXX원` 정상 출력
- [ ] `✅ 동기화: KRW-BTC | ...` 각 코인별 로그 정상
- [ ] `🆕 포지션 생성` 또는 `⏭️ 스킵` 로그 예상대로 출력
- [ ] `🗑️ 자동 삭제` 로그 확인 (있다면)
- [ ] `✅ Upbit 동기화 완료` 최종 완료 메시지

---

## 🛡️ 안전 장치 확인

### 1. 일일 손실 한도
```json
"daily_loss_limit": {
  "enabled": true,
  "loss_pct": 10.0,
  "action": "alert"  // 또는 "liquidate"
}
```
- [ ] 손실 한도 설정 확인
- [ ] `action: "liquidate"`로 설정 시 자동 전량 매도됨을 이해

### 2. 최소 KRW 잔고
```json
"min_krw_balance": {
  "enabled": true,
  "amount": 50000
}
```
- [ ] 최소 잔고 설정 확인
- [ ] 이 금액 이하로는 매수하지 않음

### 3. 최대 포지션 수
```json
"max_positions": {
  "enabled": true,
  "limit": 3
}
```
- [ ] 최대 포지션 수 설정 확인

---

## ⚠️ 긴급 상황 대응

### 프로그램 긴급 정지
```bash
# 방법 1: Telegram 봇 명령어
/stop

# 방법 2: 프로그램 강제 종료
Ctrl + C
```

### 긴급 전량 매도 (수동)
1. Upbit 웹사이트/앱 접속
2. 각 코인 수동 매도
3. 프로그램 종료
4. `data/positions_live.json` 백업 후 삭제

---

## 📋 실행 전 최종 체크리스트

**문서 확인**:
- [ ] 이 체크리스트를 처음부터 끝까지 읽고 이해함
- [ ] 모든 시나리오를 이해함
- [ ] 긴급 상황 대응 방법을 숙지함

**테스트 완료**:
- [ ] `python test_position_sync.py` 테스트 통과
- [ ] Dry-run 모드 1주일 이상 안정적 운영

**설정 확인**:
- [ ] API 키 설정 완료
- [ ] `trading_config.json` 검증 완료
- [ ] `dry_run: false` 확인
- [ ] 그룹 및 코인 리스트 최종 확인

**모니터링 준비**:
- [ ] Telegram 봇 연동 완료
- [ ] 로그 모니터링 준비 완료
- [ ] 첫 1시간은 실시간으로 로그 확인할 것

**최종 확인**:
- [ ] **소액**으로 시작
- [ ] 모든 항목 체크 완료
- [ ] 긴급 정지 방법 숙지
- [ ] 심리적 준비 완료 (실거래는 감정 관리가 중요)

---

## 🚀 실행

모든 체크리스트를 완료했다면:

```bash
# 설정 파일 최종 확인
cat config/trading_config.json | grep "dry_run"

# 실행
python main.py

# 별도 터미널에서 로그 모니터링
tail -f logs/trading_*.log
```

---

## 📞 문제 발생 시

1. **즉시 프로그램 정지** (Ctrl+C 또는 `/stop`)
2. **로그 파일 백업** (`logs/` 폴더 전체)
3. **포지션 파일 백업** (`data/positions_live.json`)
4. **문제 상황 기록**
5. **필요시 개발자/커뮤니티에 문의**

---

## 📚 관련 문서

- [INSTALLATION.md](../INSTALLATION.md) - 설치 가이드
- [ENVIRONMENT_SETUP.md](../ENVIRONMENT_SETUP.md) - 환경 설정
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - 문제 해결
- [README.md](../README.md) - 전체 프로젝트 문서

---

**마지막 경고**: 실거래는 실제 자산 손실이 발생할 수 있습니다. 충분한 테스트 없이 큰 금액으로 시작하지 마세요.

**Created**: 2025-01-26
**Last Updated**: 2025-01-26
