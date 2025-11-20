# Phase D: 통합 테스트 계획

**작성 일자**: 2025-11-20
**브랜치**: `claude/backup-copy-v4-01D6qnKRJSHFVEK1WJQRYzEH`
**완료 단계**: Phase A-C 완료, Phase D 준비
**테스트 대상**: MyOrder/MyAsset 재설계 (Phase B-C 구현)

---

## 📋 목차

1. [테스트 개요](#1-테스트-개요)
2. [테스트 환경 설정](#2-테스트-환경-설정)
3. [테스트 시나리오 (6개)](#3-테스트-시나리오-6개)
4. [검증 항목](#4-검증-항목)
5. [테스트 실행 순서](#5-테스트-실행-순서)
6. [로그 분석 가이드](#6-로그-분석-가이드)
7. [버그 발견 시 대응](#7-버그-발견-시-대응)

---

## 1. 테스트 개요

### 1.1 목적

Phase B-C 구현 검증:
- MyOrder가 **모든 매수**(봇 + 외부, 신규 + 추가)를 처리하는지 확인
- MyAsset이 백업 역할만 수행하는지 확인
- 레이스 컨디션 및 중복 처리가 없는지 확인

### 1.2 테스트 범위

| 컴포넌트 | 테스트 항목 |
|---------|----------|
| **MyOrder WebSocket** | 봇 신규/DCA, 외부 신규/추가 매수 처리 |
| **MyAsset WebSocket** | MyOrder 처리 확인 후 백업 스킵 |
| **PositionManager** | 포지션 생성/업데이트, 평균가 정확성 |
| **그룹 매칭** | 그룹 내/외 코인 구분, group_null 생성 |
| **처리 마킹** | _mark_processed_by_myorder, 5초 윈도우 |

### 1.3 성공 기준

✅ **6개 시나리오 모두 통과**
✅ **중복 처리 0건**
✅ **평균가 100% 정확**
✅ **MyAsset 백업만 동작** (MyOrder 우선)

---

## 2. 테스트 환경 설정

### 2.1 필수 조건

```json
// config/trading_config.json

{
  "global_settings": {
    "dry_run": false,  // Live 모드 (실거래)
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "chat_id": "YOUR_CHAT_ID"
    }
  },
  "groups": {
    "test_group_1": {
      "name": "테스트 그룹 1",
      "coins": ["KRW-BTC", "KRW-ETH"],
      "buy_settings": {
        "mode": "manual"  // 수동 모드 (테스트용)
      }
    }
  }
}
```

### 2.2 테스트 코인 준비

**그룹 내 코인**:
- KRW-BTC (테스트 그룹 1)
- KRW-ETH (테스트 그룹 1)

**그룹 외 코인**:
- KRW-XRP (group_null 테스트용)
- KRW-DOGE (group_null 테스트용)

### 2.3 로그 설정

```bash
# 로그 레벨: DEBUG로 설정
# 모든 처리 과정 확인 가능
```

### 2.4 Upbit 앱 준비

- Upbit 모바일 앱 or 웹 로그인
- 소액 테스트 (코인당 5,000-10,000원)
- 즉시 매수 가능 상태

---

## 3. 테스트 시나리오 (6개)

### 시나리오 1: 봇 신규 매수 ✅ (Phase 1-2에서 검증 완료)

**목적**: MyOrder가 봇 주문을 처리하는지 확인

**절차**:
1. 프로그램 시작 (V4TradingEngine)
2. GUI에서 "수동 매수" 버튼 클릭
3. 그룹: test_group_1, 코인: KRW-BTC, 금액: 5,000원

**예상 로그**:
```
💰 [봇] KRW-BTC 매수 실행 중...
✅ [봇] KRW-BTC 매수 주문 접수 완료: abc123... (MyOrder WebSocket에서 체결 대기 중)

[MyOrder WebSocket]
📬 주문 체결 이벤트 수신: KRW-BTC abc123... state=done
✅ [봇] KRW-BTC 초기 매수 체결 완료 (수량: 0.00005, 평균가: 100,000,000원)
📝 KRW-BTC MyOrder 처리 기록

[MyAsset WebSocket]
⏭️ KRW-BTC 봇 주문 진행 중 (MyOrder WebSocket에서 처리 예정, MyAsset 스킵)
```

**검증**:
- [ ] MyOrder가 포지션 생성
- [ ] pending_initial_buys 제거
- [ ] MyAsset이 봇 주문 스킵
- [ ] _mark_processed_by_myorder 호출 확인
- [ ] 포지션 파일: test_group_1, KRW-BTC 존재

---

### 시나리오 2: 봇 DCA ✅ (Phase 1 버그 수정 완료)

**목적**: MyOrder가 DCA 평균가를 정확히 계산하는지 확인

**절차**:
1. 시나리오 1 완료 (KRW-BTC 보유)
2. KRW-BTC 가격 -3% 하락 대기
3. DCA 자동 실행 확인

**예상 로그**:
```
📉 KRW-BTC DCA 레벨 1 트리거 (현재가: 97,000,000원)
💰 DCA 매수 주문 접수 완료

[MyOrder WebSocket]
💰 주문 def456... 부분 체결 (수량: 0.00005)
📊 KRW-BTC 체결가: 96,998,000원 (예상: 97,000,000원)
✅ KRW-BTC DCA 레벨 1 부분 체결 완료 → add_dca() 호출

[MyAsset WebSocket]
(수량 변동 감지)
⏭️ [봇] KRW-BTC 최근 DCA 발생 (10초 이내) → MyOrder에서 평균가 계산 완료, MyAsset skip
```

**검증**:
- [ ] MyOrder add_dca() 호출
- [ ] 평균가 정확 계산 (실제 체결가 반영)
- [ ] MyAsset이 DCA 히스토리 체크 후 스킵
- [ ] Upbit 앱 평균가 = GUI 평균가 (100% 일치)

---

### 시나리오 3: 외부 신규 매수 (그룹 내) 🆕 Phase B

**목적**: MyOrder가 외부 신규 매수를 그룹에 매칭하는지 확인

**절차**:
1. Upbit 앱에서 KRW-ETH 매수 (5,000원)
2. test_group_1에 KRW-ETH가 있음을 확인

**예상 로그**:
```
[MyOrder WebSocket]
📬 주문 체결 이벤트 수신: KRW-ETH xyz789... state=done
🔍 KRW-ETH → 그룹 매칭: test_group_1
🆕 [외부] KRW-ETH 신규 매수 감지 (그룹: test_group_1)
✅ [외부] test_group_1 포지션 생성: KRW-ETH
📝 KRW-ETH MyOrder 처리 기록

[MyAsset WebSocket]
⏭️ KRW-ETH MyOrder에서 최근 처리됨 (5초 이내), MyAsset 스킵
```

**검증**:
- [ ] MyOrder가 그룹 매칭 수행
- [ ] test_group_1에 포지션 생성 (group_null 아님)
- [ ] MyAsset이 5초 윈도우 체크 후 스킵
- [ ] 포지션 파일: test_group_1, KRW-ETH 존재

---

### 시나리오 4: 외부 신규 매수 (그룹 외) 🆕 Phase B

**목적**: MyOrder가 그룹 외 코인을 group_null에 생성하는지 확인

**절차**:
1. Upbit 앱에서 KRW-XRP 매수 (5,000원)
2. KRW-XRP는 어떤 그룹에도 없음

**예상 로그**:
```
[MyOrder WebSocket]
📬 주문 체결 이벤트 수신: KRW-XRP uvw123... state=done
🔍 KRW-XRP → 그룹 없음
🆕 [외부] KRW-XRP 신규 매수 감지 (그룹 없음 → group_null)
✅ [외부] group_null 포지션 생성: KRW-XRP
📝 KRW-XRP MyOrder 처리 기록

[MyAsset WebSocket]
⏭️ KRW-XRP MyOrder에서 최근 처리됨 (5초 이내), MyAsset 스킵
```

**검증**:
- [ ] MyOrder가 group_null에 포지션 생성
- [ ] MyAsset이 스킵
- [ ] 포지션 파일: group_null, KRW-XRP 존재

---

### 시나리오 5: 외부 추가 매수 🆕 Phase B

**목적**: MyOrder가 외부 추가 매수를 처리하는지 확인

**절차**:
1. 시나리오 3 완료 (KRW-ETH 보유, test_group_1)
2. Upbit 앱에서 KRW-ETH 추가 매수 (5,000원)

**예상 로그**:
```
[MyOrder WebSocket]
📬 주문 체결 이벤트 수신: KRW-ETH rst456... state=done
🆕 [외부] KRW-ETH 추가 매수 감지 (수량: 0.00142857)
✅ [외부] KRW-ETH 추가 매수 반영 (새 평균가: 3,500,000원)
📝 KRW-ETH MyOrder 처리 기록

[MyAsset WebSocket]
⏭️ KRW-ETH MyOrder에서 최근 처리됨 (5초 이내), MyAsset 스킵
```

**검증**:
- [ ] MyOrder가 REST API로 평균가 조회
- [ ] 포지션 업데이트 (평균가, 수량)
- [ ] Upbit 앱 평균가 = GUI 평균가
- [ ] MyAsset이 스킵

---

### 시나리오 6: MyOrder 누락 → MyAsset 백업 🆕 Phase C

**목적**: MyOrder 누락 시 MyAsset이 백업 처리하는지 확인

**절차**:
1. MyOrder WebSocket 일시 중단 (테스트용)
   - 또는: 5초 이상 대기 후 Upbit 앱 매수
2. Upbit 앱에서 KRW-DOGE 매수

**예상 로그**:
```
[MyOrder WebSocket]
(연결 끊김 or 5초 초과)

[MyAsset WebSocket]
🆕 외부 매수 감지 (Upbit 앱/웹): KRW-DOGE
(pending_initial_buys 체크 → 없음)
(MyOrder 최근 처리 체크 → 5초 초과)
⚠️ KRW-DOGE MyOrder 누락 감지, MyAsset 백업 처리
✅ [외부] group_null 포지션 생성: KRW-DOGE (Upbit 앱/웹 매수)
```

**검증**:
- [ ] MyAsset이 백업 경고 로그 출력
- [ ] group_null에 포지션 생성
- [ ] 정상 동작 (백업 메커니즘)

---

## 4. 검증 항목

### 4.1 포지션 파일 검증

**파일**: `data/positions_live.json`

```json
{
  "test_group_1": {
    "KRW-BTC": {
      "symbol": "KRW-BTC",
      "group_id": "test_group_1",
      "avg_buy_price": 100000000,
      "total_amount": 0.00005,
      "status": "active"
    },
    "KRW-ETH": {
      "symbol": "KRW-ETH",
      "group_id": "test_group_1",
      "avg_buy_price": 3500000,
      "total_amount": 0.00285714,
      "status": "active"
    }
  },
  "group_null": {
    "KRW-XRP": {
      "symbol": "KRW-XRP",
      "group_id": "group_null",
      "avg_buy_price": 1200,
      "total_amount": 4.16666667,
      "status": "active"
    },
    "KRW-DOGE": {
      "symbol": "KRW-DOGE",
      "group_id": "group_null",
      "avg_buy_price": 150,
      "total_amount": 33.33333333,
      "status": "active"
    }
  }
}
```

**체크 항목**:
- [ ] KRW-BTC: test_group_1 (시나리오 1)
- [ ] KRW-ETH: test_group_1 (시나리오 3, 5)
- [ ] KRW-XRP: group_null (시나리오 4)
- [ ] KRW-DOGE: group_null (시나리오 6)

### 4.2 평균가 검증

**방법**:
1. Upbit 앱/웹에서 각 코인 평균가 확인
2. GUI 활성 포지션 테이블 평균가 확인
3. 100% 일치 확인

**예시**:
```
Upbit 앱: KRW-ETH 평균가 3,500,000원
GUI:      KRW-ETH 평균가 3,500,000원
→ ✅ 일치
```

### 4.3 중복 처리 검증

**방법**:
- 로그에서 "포지션 생성" 또는 "update_position" 검색
- 같은 심볼에 대해 MyOrder + MyAsset 둘 다 처리했는지 확인

**성공 기준**:
- MyOrder 처리 → MyAsset 스킵 ✅
- MyOrder + MyAsset 동시 처리 ❌

---

## 5. 테스트 실행 순서

### 5.1 사전 준비 (10분)

```bash
# 1. 브랜치 확인
git status
git log -1 --oneline

# 2. 설정 파일 확인
cat config/trading_config.json | jq '.groups'

# 3. 기존 포지션 백업
cp data/positions_live.json data/positions_live.json.backup

# 4. 로그 디렉토리 정리
rm -f logs/trading_*.log

# 5. 프로그램 시작
python main.py
```

### 5.2 테스트 실행 (30-40분)

| # | 시나리오 | 예상 시간 | 순서 |
|---|---------|----------|-----|
| 1 | 봇 신규 매수 | 2분 | 1번 |
| 2 | 봇 DCA | 5-10분 (가격 대기) | 2번 |
| 3 | 외부 신규 (그룹 내) | 2분 | 3번 |
| 5 | 외부 추가 매수 | 2분 | 4번 |
| 4 | 외부 신규 (그룹 외) | 2분 | 5번 |
| 6 | MyAsset 백업 | 5분 | 6번 (선택) |

### 5.3 결과 분석 (10분)

```bash
# 1. 포지션 파일 확인
cat data/positions_live.json | jq '.'

# 2. 로그 분석
grep "MyOrder 처리 기록" logs/trading_*.log
grep "MyAsset 스킵" logs/trading_*.log
grep "백업 처리" logs/trading_*.log

# 3. 중복 처리 확인
grep "포지션 생성" logs/trading_*.log | grep "KRW-BTC"
grep "포지션 생성" logs/trading_*.log | grep "KRW-ETH"

# 4. 평균가 검증
# Upbit 앱과 비교
```

---

## 6. 로그 분석 가이드

### 6.1 필수 로그 패턴

#### MyOrder 처리 성공
```
🆕 [외부] KRW-XXX 신규 매수 감지 (그룹: test_group_1)
✅ [외부] test_group_1 포지션 생성: KRW-XXX
📝 KRW-XXX MyOrder 처리 기록
```

#### MyAsset 백업 스킵
```
⏭️ KRW-XXX MyOrder에서 최근 처리됨 (5초 이내), MyAsset 스킵
```

#### MyAsset 백업 처리
```
⚠️ KRW-XXX MyOrder 누락 감지, MyAsset 백업 처리
✅ [외부] group_null 포지션 생성: KRW-XXX (Upbit 앱/웹 매수)
```

### 6.2 문제 로그 패턴

#### 중복 처리 (버그)
```
[MyOrder] ✅ 포지션 생성: KRW-BTC
[MyAsset] ✅ 포지션 생성: KRW-BTC  ← ❌ 문제!
```

#### 평균가 덮어쓰기 (버그)
```
[MyOrder] add_dca() → 평균가: 3,500,000원
[MyAsset] REST API → 평균가: 3,520,000원 ← ❌ 문제!
```

---

## 7. 버그 발견 시 대응

### 7.1 중복 처리 발견

**증상**:
- 같은 심볼에 MyOrder + MyAsset 둘 다 포지션 생성

**원인 분석**:
1. _mark_processed_by_myorder 호출 누락?
2. _was_recently_processed_by_myorder 윈도우 너무 짧음?
3. MyOrder 처리 지연?

**수정 방법**:
- 윈도우 5초 → 10초 증가
- 마킹 위치 추가

### 7.2 평균가 불일치 발견

**증상**:
- Upbit 앱 평균가 ≠ GUI 평균가

**원인 분석**:
1. MyAsset이 DCA 평균가 덮어쓰기?
2. REST API 타이밍 이슈?

**수정 방법**:
- DCA 히스토리 체크 강화
- 10초 윈도우 유지

### 7.3 MyOrder 누락

**증상**:
- 외부 매수 시 MyOrder 로그 없음

**원인 분석**:
1. MyOrder WebSocket 연결 문제?
2. ask_bid 필드 확인?

**수정 방법**:
- WebSocket 재연결
- ask_bid == 'BID' 체크 확인

---

## 8. 테스트 체크리스트

### 사전 준비
- [ ] 브랜치: claude/backup-copy-v4-01D6qnKRJSHFVEK1WJQRYzEH
- [ ] Live 모드 설정 (dry_run: false)
- [ ] 텔레그램 알림 활성화
- [ ] 테스트 그룹 생성 (KRW-BTC, KRW-ETH)
- [ ] Upbit 앱 로그인
- [ ] 로그 파일 정리

### 시나리오 테스트
- [ ] 시나리오 1: 봇 신규 매수
- [ ] 시나리오 2: 봇 DCA
- [ ] 시나리오 3: 외부 신규 (그룹 내)
- [ ] 시나리오 4: 외부 신규 (그룹 외)
- [ ] 시나리오 5: 외부 추가 매수
- [ ] 시나리오 6: MyAsset 백업 (선택)

### 검증
- [ ] 포지션 파일 확인 (4개 코인)
- [ ] 평균가 100% 일치
- [ ] 중복 처리 0건
- [ ] MyAsset 백업만 동작

### 결과
- [ ] ✅ 모든 테스트 통과
- [ ] ⚠️ 일부 실패 (버그 기록)
- [ ] ❌ 심각한 버그 발견

---

## 9. 성공 시 다음 단계

Phase D 성공 시:
1. 테스트 결과 문서 작성
2. Phase E 문서화 진행
3. 커밋 및 푸시
4. 11/18-19 테스트 체크리스트 진행

---

**테스트 담당자**: _________
**테스트 일시**: _________
**소요 시간**: _________분
**결과**: [ ] 통과 [ ] 실패

