# 텔레그램 봇 설정 가이드

> **초보자를 위한 단계별 텔레그램 봇 설정 가이드**  
> 텔레그램을 처음 사용하시는 분도 쉽게 따라할 수 있습니다!

---

## 📋 목차

1. [텔레그램이란?](#텔레그램이란)
2. [텔레그램 앱 설치](#텔레그램-앱-설치)
3. [봇 생성하기](#봇-생성하기)
4. [Chat ID 확인하기](#chat-id-확인하기)
5. [환경 변수 설정](#환경-변수-설정)
6. [테스트하기](#테스트하기)
7. [문제 해결](#문제-해결)

---

## 텔레그램이란?

텔레그램(Telegram)은 무료 메신저 앱입니다. 우리 트레이딩 봇은 텔레그램을 통해:
- 📊 매수/매도 신호 알림
- ✅ 주문 체결 결과 알림
- 🚨 리스크 관리 이벤트 알림
- 📈 일일 성과 요약

을 실시간으로 보내드립니다!

**장점**:
- ✅ 무료
- ✅ 빠른 알림
- ✅ 모바일/PC 모두 사용 가능
- ✅ 봇 API 무료 제공

---

## 텔레그램 앱 설치

### 스마트폰 (Android/iPhone)

1. **앱 스토어에서 다운로드**
   - Android: Google Play Store
   - iPhone: Apple App Store
   
2. **'Telegram' 검색**
   
   - 개발자: Telegram FZ-LLC
   - 파란색 종이비행기 아이콘

3. **설치 및 실행**
   - '설치' 버튼 클릭
   - 앱 실행

4. **회원가입**
   - 전화번호 입력
   - SMS 인증번호 입력
   - 이름 설정

✅ **완료!** 텔레그램 앱이 준비되었습니다.

### PC (Windows/Mac/Linux)

**방법 1: 웹 브라우저**
- https://web.telegram.org 접속
- 전화번호로 로그인

**방법 2: 데스크톱 앱**
- https://desktop.telegram.org 에서 다운로드
- 설치 후 실행
- 전화번호로 로그인

---

## 봇 생성하기

### 1단계: BotFather 찾기

BotFather는 텔레그램 봇을 만들어주는 **공식 봇**입니다.

**방법 1: 검색으로 찾기**

1. 텔레그램 앱 실행
2. 상단 검색창 클릭
3. `@BotFather` 입력
4. **BotFather** 선택 (파란색 체크 마크 확인!)

**방법 2: 링크로 바로 가기**

스마트폰에서 이 링크 클릭:
```
https://t.me/BotFather
```

⚠️ **주의**: 반드시 **파란색 체크 마크**가 있는 공식 BotFather를 선택하세요!

---

### 2단계: 봇 생성하기

1. **대화 시작**
   - BotFather 채팅방 진입
   - 화면 하단 `START` 버튼 클릭

2. **명령어 입력**
   ```
   /newbot
   ```
   - 채팅창에 입력 후 전송

3. **봇 이름 정하기**
   
   BotFather가 물어봅니다:
   ```
   Alright, a new bot. How are we going to call it?
   Please choose a name for your bot.
   ```
   
   **예시 답변**:
   ```
   Upbit DCA Trader
   ```
   또는
   ```
   내 비트코인 트레이딩봇
   ```
   
   💡 이름은 한글/영어 모두 가능하며, 자유롭게 지으시면 됩니다!

4. **봇 사용자명 정하기**
   
   BotFather가 물어봅니다:
   ```
   Good. Now let's choose a username for your bot.
   It must end in 'bot'. Like this, for example: TetrisBot or tetris_bot.
   ```
   
   **규칙**:
   - 반드시 `bot`으로 끝나야 함
   - 영어 소문자, 숫자, 언더스코어(_)만 사용
   - 최소 5자 이상
   
   **예시 답변**:
   ```
   upbit_dca_trader_bot
   ```
   또는
   ```
   my_btc_trading_bot
   ```
   
   ⚠️ **주의**: 이미 사용 중인 이름은 안 됩니다! 
   만약 "Sorry, this username is already taken" 메시지가 나오면 다른 이름을 시도하세요.

5. **토큰 받기**
   
   성공하면 BotFather가 다음과 같은 메시지를 보냅니다:
   
   ```
   Done! Congratulations on your new bot. You will find it at t.me/your_bot_name_bot.
   You can now add a description, about section and profile picture for your bot,
   see /help for a list of commands.
   
   Use this token to access the HTTP API:
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
   
   Keep your token secure and store it safely, it can be used by anyone to control your bot.
   ```
   
   **중요**: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890` 부분이 **봇 토큰**입니다!
   
   📝 **토큰을 복사해서 저장하세요**:
   - 메모장에 복사
   - 또는 스크린샷 저장
   
   ⚠️ **절대 다른 사람에게 공유하지 마세요!** 
   토큰을 가진 사람은 봇을 마음대로 조종할 수 있습니다.

✅ **완료!** 봇이 생성되었습니다!

---

## Chat ID 확인하기

Chat ID는 텔레그램에서 **당신을 식별하는 고유 번호**입니다.
봇이 알림을 보낼 대상을 지정하는 데 필요합니다.

### 1단계: 내 봇과 대화 시작

1. **봇 찾기**
   
   **방법 1: 검색**
   - 텔레그램 검색창에 `@your_bot_name_bot` 입력
   - (위에서 만든 봇 사용자명)
   
   **방법 2: BotFather 메시지에서 링크 클릭**
   - BotFather가 보낸 메시지에서 `t.me/your_bot_name_bot` 클릭

2. **대화 시작**
   - 봇 채팅방에서 `START` 버튼 클릭
   - 또는 `/start` 입력 후 전송

3. **아무 메시지 보내기**
   ```
   안녕
   ```
   또는
   ```
   hello
   ```
   
   💡 봇이 아직 프로그램과 연결되지 않아서 답장은 안 옵니다. 괜찮습니다!

---

### 2단계: Chat ID 확인하기

**방법 1: 웹 브라우저 사용 (권장)**

1. **웹 브라우저 열기** (Chrome, Edge, Safari 등)

2. **다음 주소 입력**
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
   
   **중요**: `<YOUR_BOT_TOKEN>` 부분을 **위에서 복사한 봇 토큰**으로 바꾸세요!
   
   **예시**:
   ```
   https://api.telegram.org/bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890/getUpdates
   ```

3. **엔터 누르기**

4. **결과 확인**
   
   다음과 같은 JSON 데이터가 나타납니다:
   
   ```json
   {
     "ok": true,
     "result": [
       {
         "update_id": 123456789,
         "message": {
           "message_id": 1,
           "from": {
             "id": 987654321,  <-- 이게 Chat ID입니다!
             "is_bot": false,
             "first_name": "홍길동"
           },
           "chat": {
             "id": 987654321,  <-- 이것도 Chat ID입니다!
             "first_name": "홍길동",
             "type": "private"
           },
           "date": 1705200000,
           "text": "안녕"
         }
       }
     ]
   }
   ```
   
   📝 **Chat ID 찾기**:
   - `"chat"` 섹션에서 `"id": 987654321` 부분
   - 또는 `"from"` 섹션의 `"id": 987654321` 부분
   - 이 숫자가 **Chat ID**입니다!
   
   **예시 Chat ID**:
   ```
   987654321
   ```
   또는 음수일 수도 있습니다:
   ```
   -987654321
   ```

5. **Chat ID 저장**
   - 메모장에 복사
   - 또는 스크린샷 저장

---

**방법 2: 봇 사용 (@userinfobot)**

만약 위 방법이 어려우시면 다른 봇을 사용할 수도 있습니다:

1. 텔레그램 검색창에 `@userinfobot` 입력
2. @userinfobot 선택
3. `START` 버튼 클릭
4. 봇이 자동으로 Chat ID를 보여줍니다:
   ```
   Id: 987654321
   First: 홍길동
   Username: @your_username
   ```

5. `Id:` 뒤의 숫자가 Chat ID입니다!

✅ **완료!** Chat ID를 확인했습니다!

---

## 환경 변수 설정

이제 봇 토큰과 Chat ID를 프로그램에 설정합니다.

### 1단계: .env 파일 생성

1. **프로젝트 폴더 열기**
   ```
   upbit_dca_trader/
   ```

2. **.env.example 파일 찾기**
   - 프로젝트 루트 폴더에 있습니다

3. **.env.example 복사해서 .env 만들기**
   
   **Windows (명령 프롬프트)**:
   ```cmd
   copy .env.example .env
   ```
   
   **Mac/Linux (터미널)**:
   ```bash
   cp .env.example .env
   ```
   
   **또는 파일 탐색기에서**:
   - `.env.example` 파일 우클릭
   - '복사' 선택
   - 같은 폴더에 붙여넣기
   - 이름을 `.env`로 변경

---

### 2단계: .env 파일 편집

1. **.env 파일 열기**
   
   **메모장 (Windows)**:
   - `.env` 파일 우클릭
   - '연결 프로그램' → '메모장'
   
   **텍스트 편집기 (Mac)**:
   - `.env` 파일 우클릭
   - '연결 프로그램' → 'TextEdit'
   
   **VS Code / 기타 편집기**:
   - 편집기에서 `.env` 파일 열기

2. **텔레그램 설정 수정**
   
   파일에서 다음 부분을 찾으세요:
   ```bash
   # Telegram Bot (Phase 3.3)
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TELEGRAM_CHAT_ID=your_telegram_chat_id_here
   ```
   
   **수정 전**:
   ```bash
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TELEGRAM_CHAT_ID=your_telegram_chat_id_here
   ```
   
   **수정 후** (예시):
   ```bash
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
   TELEGRAM_CHAT_ID=987654321
   ```
   
   ⚠️ **주의사항**:
   - `=` 앞뒤에 공백 없이 입력
   - 따옴표(`"` 또는 `'`) 사용하지 않기
   - 토큰과 Chat ID를 정확히 복사

3. **파일 저장**
   - `Ctrl + S` (Windows) 또는 `Cmd + S` (Mac)
   - 또는 '파일' → '저장'

✅ **완료!** 환경 변수 설정이 끝났습니다!

---

## 테스트하기

설정이 제대로 되었는지 테스트해봅시다!

### 방법 1: 텔레그램 봇 테스트 스크립트

1. **터미널/명령 프롬프트 열기**

2. **프로젝트 폴더로 이동**
   ```bash
   cd /mnt/d/claude-project12/upbit_dca_trader
   ```

3. **테스트 실행**
   ```bash
   python core/telegram_bot.py
   ```

4. **결과 확인**
   
   **성공 시**:
   ```
   === Telegram Bot 테스트 ===
   
   1. 시작 메시지 전송
      ✅ 전송 완료
   
   2. 매수 신호 알림 테스트
      ✅ 전송 완료
   
   3. 주문 체결 알림 테스트
      ✅ 전송 완료
   
   4. 스톱로스 알림 테스트
      ✅ 전송 완료
   
   5. 일일 성과 요약 테스트
      ✅ 전송 완료
   
   ✅ 모든 테스트 완료
   
   📱 텔레그램 앱에서 메시지를 확인하세요!
   ```
   
   **실패 시**:
   ```
   ❌ API 키가 설정되지 않았습니다.
      .env 파일에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID를 설정하세요.
   ```
   → [문제 해결](#문제-해결) 섹션 참고

5. **텔레그램 앱 확인**
   
   내 봇과의 채팅방에서 다음과 같은 메시지가 왔는지 확인:
   
   ```
   🤖 Upbit DCA Trader 테스트
   
   텔레그램 봇 연동 테스트입니다.
   ```
   
   ```
   🛒 매수 신호 발생!
   
   📊 마켓: KRW-BTC
   💰 가격: 100,000,000원
   ...
   ```

✅ **성공!** 텔레그램 봇이 정상 작동합니다!

---

### 방법 2: 통합 테스트

실제 트레이딩 시스템과 통합 테스트:

```bash
python tests/test_telegram_integration.py
```

이 테스트는:
- ✅ 실시간 데이터 수신
- ✅ 전략 신호 생성
- ✅ 텔레그램 알림 전송

을 모두 테스트합니다. (약 2-3분 소요)

---

## V4 Notification Examples

V4 시스템에서는 그룹 기반 알림을 보냅니다. 실제 운영 중 받게 될 메시지 예시입니다.

### 🤖 자동매수 신호 감지

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

**언제 오나요?**
- 자동매수 프리셋 조건이 모두 충족되었을 때
- 매수 주문 실행 직전

---

### 📈 DCA 레벨 실행

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

**언제 오나요?**
- 포지션이 설정한 DCA 레벨에 도달했을 때
- 예: -5% 도달 시 Level 2 추가 매수

---

### 🎉 익절 레벨 실행

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

**언제 오나요?**
- 포지션이 설정한 익절 레벨에 도달했을 때
- 예: +5% 도달 시 50% 물량 매도

---

### 🛑 손절 레벨 실행

```
🛑 손절 레벨 1 실행

그룹: 비트코인 단타
코인: KRW-BTC
손익률: -15.2%

손절 설정: -15.0% / 100%
매도 수량: 0.00222 BTC (100%)
매도 가격: 38,250,000원
실현 손실: -7,500원
```

**언제 오나요?**
- 포지션이 설정한 손절 레벨에 도달했을 때
- 손실을 제한하기 위한 자동 청산

---

### ⚠️ 일일 손실 한도 도달

```
⚠️ 일일 손실 한도 도달

그룹: 전체
현재 손실률: -10.2%
한도: -10.0%

액션: 알림
(liquidate로 설정 시 전량 청산됩니다)

09:00에 자동 리셋됩니다.
```

**언제 오나요?**
- 일일 손실이 설정한 한도를 초과했을 때
- 예: 하루 -10% 손실 발생 시

---

## Telegram Bot Commands (V4)

V4 시스템에서는 다음 명령어를 텔레그램 봇을 통해 사용할 수 있습니다.

### `/status` - 전체 상태 확인

봇 채팅방에서 `/status` 입력 시:

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

**활용 시나리오**:
- 외출 중 전체 시스템 상태 빠르게 확인
- 그룹별 수익률 한눈에 파악

---

### `/group <group_id>` - 그룹 상세 정보

봇 채팅방에서 `/group group_1` 입력 시:

```
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

**활용 시나리오**:
- 특정 그룹의 자세한 설정 확인
- 그룹별 성과 분석

---

### `/positions` - 전체 포지션 조회

봇 채팅방에서 `/positions` 입력 시:

```
📊 활성 포지션 (3개)

1. KRW-BTC [비트코인 단타]
   진입: 44,500,000원
   현재: 45,800,000원
   손익: +2.9% (+1,300원)
   DCA: 0/3 (아직 미실행)

2. KRW-ETH [비트코인 단타]
   진입: 3,150,000원 (평균)
   현재: 3,200,000원
   손익: +1.6% (+500원)
   DCA: 2/3 (Level 1, 2 실행됨)

3. KRW-XRP [알트코인 중장기]
   진입: 700원
   현재: 680원
   손익: -2.9% (-200원)
   DCA: 1/3 (Level 1 실행됨)

총 평가 손익: +1,600원 (+1.8%)
```

**활용 시나리오**:
- 모든 포지션의 실시간 손익 확인
- DCA 진행 상황 파악

---

### `/balance` - 잔고 확인

봇 채팅방에서 `/balance` 입력 시:

```
💰 계좌 잔고

KRW 잔고: 500,000원

포지션 평가액:
• BTC: 45,800원
• ETH: 100,500원
• XRP: 19,800원

총 평가액: 666,100원
일일 손익: +1,600원 (+0.24%)
```

**활용 시나리오**:
- 가용 자금 확인
- 전체 포트폴리오 가치 파악

---

### `/stop` / `/start` - 거래 정지/재개

```
/stop
⏸️ 트레이딩 일시 정지
새로운 매수 신호를 무시합니다.
기존 포지션은 유지됩니다.
```

```
/start
▶️ 트레이딩 재개
매수 신호를 다시 감지합니다.
```

**활용 시나리오**:
- 급격한 시장 변동 시 일시 정지
- 점검 후 거래 재개

---

### `/help` - 명령어 도움말

봇 채팅방에서 `/help` 입력 시:

```
📖 사용 가능한 명령어

/status - 시스템 전체 상태 확인
/group <id> - 특정 그룹 상세 정보
/positions - 활성 포지션 목록
/balance - 계좌 잔고 확인
/stop - 트레이딩 일시 정지
/start - 트레이딩 재개
/help - 이 도움말 표시

V4 시스템 (그룹 기반)
```

---

## 알림 주기 및 빈도

### 자동매수 신호
- **빈도**: 프리셋에 따라 다름
  - Conservative: 코인당 주 1-2회
  - Balanced: 코인당 주 3-5회
  - Aggressive: 코인당 주 10-20회

### DCA/익절/손절 알림
- **빈도**: 시장 상황에 따라 가변적
- 포지션이 설정 레벨에 도달할 때만

### 일일 손실 한도
- **빈도**: 한도 도달 시 1회
- 09:00 자동 리셋

---

## 문제 해결

### 문제 1: "API 키가 설정되지 않았습니다"

**증상**:
```
❌ API 키가 설정되지 않았습니다.
   .env 파일에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID를 설정하세요.
```

**해결 방법**:

1. **.env 파일이 존재하는지 확인**
   ```bash
   ls -la .env  # Mac/Linux
   dir .env     # Windows
   ```
   
   파일이 없으면:
   ```bash
   cp .env.example .env
   ```

2. **.env 파일 내용 확인**
   ```bash
   cat .env  # Mac/Linux
   type .env # Windows
   ```
   
   다음 줄이 있는지 확인:
   ```
   TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
   TELEGRAM_CHAT_ID=987654321
   ```

3. **설정 값이 올바른지 확인**
   - 봇 토큰: `:` 기호가 포함된 긴 문자열
   - Chat ID: 숫자만 (또는 `-`로 시작하는 숫자)
   - `=` 앞뒤에 공백 없음
   - 따옴표 없음

---

### 문제 2: "메시지 전송 실패"

**증상**:
```
❌ 메시지 전송 실패: Unauthorized
```

**원인**: 봇 토큰이 잘못되었습니다.

**해결 방법**:

1. **BotFather에서 토큰 다시 확인**
   - BotFather 채팅방 열기
   - `/mybots` 입력
   - 내 봇 선택
   - `API Token` 선택
   - 토큰 복사

2. **.env 파일에 정확히 입력**
   - 공백 없이
   - 전체 토큰 복사
   - `:` 기호 포함 여부 확인

---

### 문제 3: "Chat not found"

**증상**:
```
❌ 메시지 전송 실패: Bad Request: chat not found
```

**원인**: Chat ID가 잘못되었습니다.

**해결 방법**:

1. **봇과 대화 시작 확인**
   - 봇 채팅방에서 `/start` 버튼 클릭
   - 아무 메시지나 보내기 (예: "안녕")

2. **Chat ID 다시 확인**
   - 브라우저에서:
     ```
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
     ```
   - `"chat"` 섹션의 `"id"` 값 확인
   - 정확히 복사해서 `.env`에 입력

3. **음수 Chat ID 확인**
   - Chat ID가 `-`로 시작하면 반드시 포함:
     ```
     TELEGRAM_CHAT_ID=-987654321
     ```

---

### 문제 4: ".env 파일을 찾을 수 없음"

**증상**:
```
파일을 찾을 수 없습니다: .env
```

**원인**: 프로젝트 루트 폴더에 `.env` 파일이 없습니다.

**해결 방법**:

1. **현재 폴더 확인**
   ```bash
   pwd   # Mac/Linux
   cd    # Windows
   ```
   
   올바른 경로:
   ```
   /mnt/d/claude-project12/upbit_dca_trader
   ```

2. **.env.example에서 복사**
   ```bash
   cp .env.example .env
   ```

3. **숨김 파일 보기 설정** (Windows)
   - 파일 탐색기 열기
   - '보기' 탭
   - '숨김 항목' 체크

---

### 문제 5: "python을 찾을 수 없음"

**증상**:
```
'python'은(는) 내부 또는 외부 명령, 실행할 수 있는 프로그램, 또는 배치 파일이 아닙니다.
```

**원인**: Python이 설치되지 않았거나 경로 설정이 안 됨.

**해결 방법**:

1. **Python 설치 확인**
   ```bash
   python --version
   python3 --version
   ```

2. **Python 3 사용**
   - Windows: `python` 대신 `python3` 또는 `py` 사용
   - Mac/Linux: `python3` 사용

3. **Python 설치** (설치 안 된 경우)
   - https://www.python.org/downloads/
   - "Add Python to PATH" 옵션 체크!

---

### 문제 6: 봇이 메시지에 응답하지 않음

**증상**: 봇에게 메시지를 보내도 아무 답장이 없습니다.

**해결 방법**:

이것은 **정상입니다**!

- 봇은 알림만 보내는 역할입니다
- 명령어는 **페이퍼 트레이딩 실행 중**에만 작동합니다
- `/status`, `/balance` 등은 트레이딩 엔진이 실행 중일 때만 가능

**명령어 테스트 방법**:
```bash
# 페이퍼 트레이딩 시작
python tests/test_paper_trading.py

# 이제 봇에게 명령어 입력:
# /status
# /balance
# /help
```

---

## 추가 팁

### 봇 프로필 사진 설정

1. BotFather 채팅방에서 `/mybots` 입력
2. 내 봇 선택
3. `Edit Bot` → `Edit Botpic`
4. 사진 업로드

### 봇 설명 추가

1. BotFather 채팅방에서 `/mybots` 입력
2. 내 봇 선택
3. `Edit Bot` → `Edit Description`
4. 설명 입력:
   ```
   비트코인 자동 매매 트레이딩 봇
   
   - 실시간 매매 신호 알림
   - 주문 체결 알림
   - 리스크 관리 이벤트 알림
   - 일일 성과 요약
   ```

### 알림 설정

텔레그램 앱에서:
1. 봇 채팅방 열기
2. 상단 봇 이름 클릭
3. `Notifications` 설정:
   - 소리: ON
   - 진동: ON
   - 미리보기: ON

---

## 자주 묻는 질문 (FAQ)

### Q1: 텔레그램 계정이 없어도 되나요?
**A**: 아니요, 텔레그램 계정이 필수입니다. 하지만 무료이고 5분이면 만들 수 있습니다!

### Q2: 봇 토큰을 잃어버렸어요!
**A**: 
1. BotFather 채팅방 열기
2. `/mybots` 입력
3. 내 봇 선택
4. `API Token` 클릭
5. 토큰 다시 복사

### Q3: Chat ID를 잘못 입력했어요. 어떻게 수정하나요?
**A**: 
1. `.env` 파일 열기
2. `TELEGRAM_CHAT_ID=` 부분 수정
3. 저장
4. 프로그램 다시 실행

### Q4: 여러 명이 알림을 받을 수 있나요?
**A**: 현재 버전은 1명만 지원합니다. 여러 명이 받으려면:
- 각자 봇을 만들거나
- 텔레그램 그룹을 만들어 봇 추가 (고급)

### Q5: 봇 이름을 변경할 수 있나요?
**A**: 
1. BotFather 채팅방에서 `/mybots`
2. 내 봇 선택
3. `Edit Bot` → `Edit Name`
4. 새 이름 입력

### Q6: 알림이 너무 많이 와요. 줄일 수 있나요?
**A**: 
- 현재는 모든 신호와 체결 알림이 옵니다
- 향후 업데이트에서 알림 필터링 기능 추가 예정
- 임시 방법: 텔레그램에서 알림 끄기

### Q7: 봇을 삭제하고 싶어요.
**A**: 
1. BotFather 채팅방에서 `/mybots`
2. 내 봇 선택
3. `Delete Bot`
4. 확인

⚠️ **주의**: 삭제하면 토큰도 무효화됩니다!

---

## 다음 단계

✅ 텔레그램 봇 설정이 완료되었습니다!

**이제 무엇을 할까요?**

### 1. 빠른 테스트
```bash
python tests/test_telegram_integration.py
```

### 2. 페이퍼 트레이딩 시작
```bash
python tests/test_paper_trading.py
```

### 3. README 읽기
전체 프로젝트 사용법을 확인하세요:
```
README.md
```

---

## 도움이 필요하신가요?

위 단계를 따라했는데도 문제가 해결되지 않으면:

1. **에러 메시지 전체 복사**
2. **어떤 단계에서 문제가 발생했는지 설명**
3. **스크린샷 첨부** (민감한 정보는 가리고)

---

**작성일**: 2025-01-14 (V4 업데이트: 2025-01-26)
**버전**: 2.0 (V4 대응)
**대상**: 초보자
**소요 시간**: 약 10-15분
