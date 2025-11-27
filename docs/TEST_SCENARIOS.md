# 🧪 GUI 포지션 표시 테스트 시나리오

GUI에서 Dry-run/Live 모드의 포지션 표시가 올바르게 작동하는지 검증하기 위한 테스트 시나리오입니다.

---

## 📋 사전 준비

### 1. 설정 파일 준비
```bash
# trading_config.json 생성 (없으면)
cp config/trading_config_template.json config/trading_config.json
```

### 2. 테스트용 그룹 생성
`config/trading_config.json` 편집:
```json
{
  "version": "4.0.0",
  "global_settings": {
    "dry_run": true  // 테스트 시작은 Dry-run
  },
  "groups": {
    "test_group_1": {
      "name": "테스트 그룹 1",
      "coins": ["KRW-BTC", "KRW-ETH"]
    },
    "test_group_2": {
      "name": "테스트 그룹 2",
      "coins": ["KRW-XRP"]
    }
  }
}
```

### 3. 초기 상태 확인
```bash
# 포지션 파일 초기화 (선택)
rm -f data/positions_live.json
rm -f data/positions_dryrun.json
```

---

## 🟢 시나리오 1: Dry-run 모드 기본 테스트

### 목적
Dry-run 모드에서 포지션이 정상적으로 로드되고 표시되는지 확인

### 사전 조건
- `config/trading_config.json`에서 `"dry_run": true` 설정
- `data/positions_dryrun.json` 파일 존재 또는 생성

### 테스트 데이터 준비
`data/positions_dryrun.json` 생성:
```json
{
  "KRW-BTC": {
    "group_id": "test_group_1",
    "symbol": "KRW-BTC",
    "status": "active",
    "entry_price": 90000000,
    "entry_amount": 0.001,
    "entry_krw": 90000,
    "current_price": 90000000,
    "current_value_krw": 90000,
    "profit_krw": 0,
    "profit_pct": 0,
    "dca_history": [],
    "dca_levels_executed": [],
    "total_invested_krw": 90000,
    "total_amount": 0.001,
    "average_price": 90000000,
    "created_at": "2025-01-26T10:00:00",
    "updated_at": "2025-01-26T10:00:00"
  }
}
```

### 실행 단계
1. GUI 실행: `python main.py`
2. 로그 확인:
   ```
   🟢 [Step 2] Dry-run 모드: 가상 포지션 로드
   📊 포지션 1개 로드됨
   ```
3. "활성 포지션" 탭 확인

### 예상 결과
- ✅ 테이블에 KRW-BTC 포지션 1개 표시
- ✅ 그룹명: "테스트 그룹 1"
- ✅ 평균가: 90,000,000원
- ✅ 수익률: 0.00%
- ✅ 실시간 가격 업데이트 시작

### 검증 체크리스트
- [ ] 포지션 테이블에 1개 행 표시됨
- [ ] 그룹명이 올바르게 표시됨
- [ ] 매수/DCA/익절/손절 상태 표시
- [ ] 평균가, 현재가, 수량 표시
- [ ] 평가손익, 수익률 표시
- [ ] 상태바에 "Dry-run 모드" 표시

---

## 🔴 시나리오 2: Live 모드 - Upbit 동기화 테스트

### 목적
Live 모드에서 Upbit 계좌와 동기화하여 실제 포지션을 로드하는지 확인

### 사전 조건
- `config/trading_config.json`에서 `"dry_run": false` 설정
- Upbit API 키 설정 완료
- **실제 Upbit 계좌에 테스트 코인 보유 필요**

### 실행 단계
1. Upbit 웹사이트에서 현재 보유 자산 확인
   - 예: BTC 0.001개 @ 95,000,000원
   - 예: ETH 0.05개 @ 3,000,000원

2. `config/trading_config.json` 수정:
   ```json
   {
     "global_settings": {
       "dry_run": false  // Live 모드로 변경
     },
     "groups": {
       "test_group_1": {
         "coins": ["KRW-BTC", "KRW-ETH"]  // 보유 중인 코인 포함
       }
     }
   }
   ```

3. GUI 실행: `python main.py`

4. 로그 확인:
   ```
   🔴 [Step 2] Live 모드: Upbit 동기화 시작
   🔄 Upbit 동기화 시작...
   💰 KRW 잔고: 5,000,000원
   ✅ 동기화: KRW-BTC | 0.00100000 @ 95,000,000원
   🆕 포지션 생성: KRW-ETH → test_group_1 | 0.05000000 @ 3,000,000원
   ✅ Upbit 동기화 완료
   ✅ 동기화 완료: 1개 업데이트, 1개 신규, 0개 삭제
   ```

### 예상 결과
- ✅ Upbit 계좌의 실제 포지션이 테이블에 표시
- ✅ `data/positions_live.json` 파일 생성됨
- ✅ Upbit의 평균 매수가가 반영됨
- ✅ 실시간 가격 업데이트 시작

### 검증 체크리스트
- [ ] Upbit 보유 자산과 테이블 내용 일치
- [ ] 평균 매수가가 Upbit과 동일
- [ ] 수량이 Upbit과 동일
- [ ] 그룹에 속한 코인만 표시됨
- [ ] 상태바에 "Live 모드" 표시

---

## 🔄 시나리오 3: 모드 전환 테스트

### 목적
Dry-run ↔ Live 모드 전환 시 포지션이 올바르게 로드되는지 확인

### 3-1. Dry-run → Live 전환

#### 실행 단계
1. Dry-run 모드로 시작 (시나리오 1)
2. 메뉴: `설정 → 모드 전환 (Dry-run → Live)`
3. 확인 다이얼로그에서 "예" 클릭
4. 로그 확인:
   ```
   🔄 모드 전환: Dry-run → Live
   ✅ PositionManager 재생성 완료: live
   🔄 Upbit 동기화 시작...
   ```

#### 예상 결과
- ✅ Upbit 계좌와 동기화
- ✅ 실제 보유 자산이 표시됨
- ✅ Dry-run 포지션은 사라짐
- ✅ 상태바: "Live 모드" 표시

#### 검증 체크리스트
- [ ] 포지션 테이블이 새로 로드됨
- [ ] Upbit 보유 자산과 일치
- [ ] `data/positions_live.json` 사용됨
- [ ] 상태바 모드 표시 변경

### 3-2. Live → Dry-run 전환

#### 실행 단계
1. Live 모드로 시작 (시나리오 2)
2. 메뉴: `설정 → 모드 전환 (Live → Dry-run)`
3. 확인 다이얼로그에서 "예" 클릭

#### 예상 결과
- ✅ Dry-run 포지션 로드
- ✅ `data/positions_dryrun.json` 사용
- ✅ 상태바: "Dry-run 모드" 표시

#### 검증 체크리스트
- [ ] 포지션 테이블이 새로 로드됨
- [ ] Dry-run 포지션 표시
- [ ] Live 포지션은 보이지 않음
- [ ] 상태바 모드 표시 변경

---

## 🎯 시나리오 4: 그룹 필터링 테스트

### 목적
config 그룹에 속한 코인만 포지션으로 생성되는지 확인

### 사전 조건
- Live 모드
- Upbit 계좌에 다음 코인 보유:
  - BTC (그룹에 포함)
  - ETH (그룹에 포함)
  - SOL (그룹에 **미포함**)

### 설정 파일
```json
{
  "global_settings": {
    "dry_run": false
  },
  "groups": {
    "test_group": {
      "coins": ["KRW-BTC", "KRW-ETH"]
      // KRW-SOL은 의도적으로 제외
    }
  }
}
```

### 실행 단계
1. GUI 실행
2. 로그 확인:
   ```
   ✅ 동기화: KRW-BTC | ...
   🆕 포지션 생성: KRW-ETH → test_group | ...
   ⏭️ 스킵: KRW-SOL (그룹 없음) | ...
   ✅ Upbit 동기화 완료
      - 동기화된 포지션: 1개
      - 새로 생성된 포지션: 1개
      - 스킵된 포지션: 1개
   ```

### 예상 결과
- ✅ KRW-BTC, KRW-ETH만 테이블에 표시
- ✅ KRW-SOL은 스킵되어 표시 안 됨
- ✅ 로그에 "스킵" 메시지 출력

### 검증 체크리스트
- [ ] 그룹에 속한 코인만 표시
- [ ] 그룹에 없는 코인은 표시 안 됨
- [ ] 로그에 스킵 메시지 확인
- [ ] Upbit에서는 SOL 보유 중이지만 프로그램에서 관리 안 함

---

## 🗑️ 시나리오 5: 자동 삭제 테스트

### 목적
Upbit에서 완전 매도한 포지션이 자동으로 삭제되는지 확인

### 사전 조건
- Live 모드
- `data/positions_live.json`에 KRW-ADA 포지션 존재
- Upbit 계좌에는 ADA 보유량 0 (완전 매도됨)

### 테스트 데이터 준비
`data/positions_live.json`:
```json
{
  "KRW-BTC": {
    "group_id": "test_group",
    "symbol": "KRW-BTC",
    "status": "active",
    ...
  },
  "KRW-ADA": {
    "group_id": "test_group",
    "symbol": "KRW-ADA",
    "status": "active",
    "average_price": 1000,
    "total_amount": 100,
    ...
  }
}
```

### 실행 단계
1. GUI 실행
2. 로그 확인:
   ```
   🗑️ 자동 삭제: KRW-ADA (Upbit에 없음, 완전 매도된 것으로 간주)
   ✅ Upbit 동기화 완료
      - 삭제된 포지션: 1개
   ```

### 예상 결과
- ✅ KRW-ADA가 테이블에서 사라짐
- ✅ `data/positions_live.json`에서 KRW-ADA 제거됨
- ✅ KRW-BTC는 여전히 표시됨

### 검증 체크리스트
- [ ] 매도된 포지션이 테이블에서 사라짐
- [ ] JSON 파일에서도 삭제됨
- [ ] 다른 포지션은 영향 없음
- [ ] 로그에 자동 삭제 메시지 확인

---

## 💰 시나리오 6: 가격 업데이트 테스트

### 목적
WebSocket을 통한 실시간 가격 업데이트가 정상 작동하는지 확인

### 사전 조건
- Live 또는 Dry-run 모드
- 포지션 최소 1개 이상

### 실행 단계
1. GUI 실행
2. 포지션 테이블의 초기 가격 기록
   - 예: BTC 현재가 95,000,000원
3. 1-2분 대기 (실제 시장 가격 변동)
4. 테이블 확인

### 예상 결과
- ✅ 현재가가 실시간으로 변경됨
- ✅ 평가손익이 자동 재계산됨
- ✅ 수익률(%)이 자동 업데이트됨
- ✅ 수익: 빨간색, 손실: 파란색 표시

### 검증 체크리스트
- [ ] 현재가가 업데이트됨 (1-5초마다)
- [ ] 평가손익이 재계산됨
- [ ] 수익률이 재계산됨
- [ ] 색상이 올바르게 적용됨
- [ ] 로그에 "✅ 실시간 가격 업데이트 연결됨" 확인

---

## 🔧 시나리오 7: 수동 새로고침 테스트

### 목적
포지션 테이블 새로고침이 정상 작동하는지 확인

### 실행 단계
1. GUI 실행 후 포지션 로드
2. 외부에서 `data/positions_live.json` 또는 `positions_dryrun.json` 수정
   - 예: 수량 변경, 새 포지션 추가
3. GUI 재시작 **없이** 새로고침 방법 확인
   - 방법 1: 모드 전환 2회 (Live→Dry→Live)
   - 방법 2: 그룹 설정 변경

### 예상 결과
- ✅ 변경된 포지션이 테이블에 반영됨
- ✅ sync_with_upbit() 재실행됨 (Live 모드)

### 검증 체크리스트
- [ ] 변경사항이 반영됨
- [ ] 기존 포지션 유지됨
- [ ] 오류 없이 정상 작동

---

## 🐛 시나리오 8: 에러 처리 테스트

### 8-1. API 키 없음

#### 실행 단계
1. API 키 파일 삭제 또는 비우기
2. Live 모드로 GUI 실행

#### 예상 결과
- ✅ "⚠️ API 키 미설정" 메시지
- ✅ 프로그램 크래시 없음
- ✅ Dry-run 모드로 fallback 제안

### 8-2. JSON 파일 손상

#### 실행 단계
1. `data/positions_live.json` 파일을 잘못된 JSON으로 수정
   ```json
   {
     "KRW-BTC": {
       "invalid":
   ```
2. GUI 실행

#### 예상 결과
- ✅ "⚠️ 포지션 파일 파싱 오류" 메시지
- ✅ 빈 테이블 표시
- ✅ 프로그램 크래시 없음

### 8-3. Upbit API 오류

#### 실행 단계
1. 네트워크 연결 끊기
2. Live 모드로 GUI 실행

#### 예상 결과
- ✅ "⚠️ Upbit 동기화 실패" 메시지
- ✅ 기존 로컬 포지션 유지
- ✅ 프로그램 크래시 없음

---

## 📊 시나리오 9: 대량 포지션 테스트

### 목적
다수의 포지션을 한 번에 표시할 수 있는지 확인

### 테스트 데이터
`data/positions_dryrun.json`에 10개 포지션 생성:
```json
{
  "KRW-BTC": {...},
  "KRW-ETH": {...},
  "KRW-XRP": {...},
  "KRW-SOL": {...},
  "KRW-ADA": {...},
  "KRW-DOGE": {...},
  "KRW-DOT": {...},
  "KRW-LINK": {...},
  "KRW-MATIC": {...},
  "KRW-AVAX": {...}
}
```

### 실행 단계
1. GUI 실행
2. 테이블 스크롤 확인
3. 정렬 기능 테스트 (컬럼 헤더 클릭)

### 예상 결과
- ✅ 모든 포지션 표시됨
- ✅ 스크롤 정상 작동
- ✅ 정렬 기능 작동
- ✅ UI 렉 없음

### 검증 체크리스트
- [ ] 10개 포지션 모두 표시
- [ ] 스크롤바 작동
- [ ] 컬럼 정렬 기능 작동
- [ ] 성능 이슈 없음

---

## ✅ 종합 체크리스트

### Dry-run 모드
- [ ] 시나리오 1: 기본 테스트 통과
- [ ] 시나리오 6: 가격 업데이트 통과
- [ ] 시나리오 9: 대량 포지션 통과

### Live 모드
- [ ] 시나리오 2: Upbit 동기화 통과
- [ ] 시나리오 4: 그룹 필터링 통과
- [ ] 시나리오 5: 자동 삭제 통과
- [ ] 시나리오 6: 가격 업데이트 통과

### 모드 전환
- [ ] 시나리오 3-1: Dry-run → Live 통과
- [ ] 시나리오 3-2: Live → Dry-run 통과

### 에러 처리
- [ ] 시나리오 8-1: API 키 없음 통과
- [ ] 시나리오 8-2: JSON 손상 통과
- [ ] 시나리오 8-3: API 오류 통과

---

## 🚨 문제 발생 시 확인 사항

### 1. 포지션이 표시되지 않을 때
```bash
# 로그 파일 확인
tail -f logs/trading_*.log

# 포지션 파일 확인
cat data/positions_live.json
cat data/positions_dryrun.json

# 설정 파일 확인
cat config/trading_config.json | grep dry_run
```

### 2. 동기화 실패 시
```bash
# API 키 확인
cat config/api_keys.json

# Upbit API 테스트
python -c "from core.upbit_api import UpbitAPI; api = UpbitAPI('access', 'secret'); print(api.get_accounts())"
```

### 3. 모드 전환 안 될 때
```bash
# PositionManager 초기화 확인
grep "PositionManager 재생성" logs/trading_*.log
```

---

## 📝 테스트 결과 기록

각 시나리오 테스트 후 결과를 기록하세요:

| 시나리오 | 날짜 | 결과 | 비고 |
|---------|------|------|------|
| 1. Dry-run 기본 | | ⬜ | |
| 2. Live 동기화 | | ⬜ | |
| 3-1. Dry→Live | | ⬜ | |
| 3-2. Live→Dry | | ⬜ | |
| 4. 그룹 필터링 | | ⬜ | |
| 5. 자동 삭제 | | ⬜ | |
| 6. 가격 업데이트 | | ⬜ | |
| 7. 수동 새로고침 | | ⬜ | |
| 8-1. API 키 없음 | | ⬜ | |
| 8-2. JSON 손상 | | ⬜ | |
| 8-3. API 오류 | | ⬜ | |
| 9. 대량 포지션 | | ⬜ | |

범례: ✅ 통과 | ❌ 실패 | ⬜ 미실시

---

**작성일**: 2025-01-26
**최종 업데이트**: 2025-01-26
