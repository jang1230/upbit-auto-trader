# ❓ 자주 묻는 질문 (FAQ)

Upbit DCA Trader 사용 중 자주 발생하는 질문과 답변 모음

---

## 📋 목차

1. [설치 및 설정](#설치-및-설정)
2. [API 키 관련](#api-키-관련)
3. [보안 관련](#보안-관련)
4. [실행 및 사용](#실행-및-사용)
5. [오류 해결](#오류-해결)
6. [Windows .exe 빌드](#windows-exe-빌드)
7. [거래 관련](#거래-관련)

---

## 설치 및 설정

### Q1. Python이 설치되어 있는지 어떻게 확인하나요?

**A**: 명령 프롬프트에서:
```bash
python --version
```

버전이 표시되면 설치됨.
오류가 나면 https://www.python.org/downloads/ 에서 설치.

---

### Q2. Python 설치 시 "Add Python to PATH"를 깜빡했어요!

**A**: Python을 재설치하거나, 다음 방법으로 수동 추가:

**방법 1: 재설치 (권장)**
1. Python 설치 파일 다시 실행
2. "Modify" 선택
3. "Add Python to PATH" 체크
4. "Modify" 클릭

**방법 2: 환경 변수 수동 추가**
1. 시작 메뉴 → "환경 변수" 검색
2. "시스템 환경 변수 편집" 클릭
3. "환경 변수" 버튼 클릭
4. "Path" 선택 → "편집"
5. Python 설치 경로 추가 (예: `C:\Users\사용자명\AppData\Local\Programs\Python\Python310`)

---

### Q3. 필수 패키지 설치 중 "권한이 없습니다" 오류가 나요.

**A**: 다음 명령 사용:
```bash
pip install --user -r requirements.txt
```

또는 명령 프롬프트를 **관리자 권한**으로 실행.

---

### Q4. 다른 프로젝트와 충돌을 피하고 싶어요.

**A**: 가상 환경 사용 (권장):

```bash
# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화 (Windows)
venv\Scripts\activate

# 가상 환경 활성화 (Mac/Linux)
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

가상 환경이 활성화되면 명령 프롬프트 앞에 `(venv)`가 표시됩니다.

---

## API 키 관련

### Q5. Upbit API 키는 어디서 발급받나요?

**A**:
1. https://upbit.com 로그인
2. 우측 상단 "내 정보" → "Open API 관리"
3. "Open API 키 발급" 버튼 클릭

또는 직접: https://upbit.com/mypage/open_api_management

---

### Q6. API 키 권한은 어떻게 설정하나요?

**A**:
**필수 권한**:
- ✅ 자산 조회
- ✅ 주문 조회

**선택 권한** (실거래 시):
- ✅ 주문하기

**절대 체크하지 말 것**:
- ❌ 출금하기 (보안상 위험)

---

### Q7. API 키를 잃어버렸어요!

**A**:
Secret Key는 발급 시 한 번만 보여줍니다.

**해결 방법**:
1. Upbit Open API 관리 페이지 접속
2. 기존 API 키 삭제
3. 새 API 키 발급
4. 프로그램에서 다시 저장:
```bash
python main.py --save-keys
```

---

### Q8. API 키를 변경하고 싶어요.

**A**:
```bash
# 1. 기존 API 키 삭제
python main.py --delete-keys

# 2. 새 API 키 저장
python main.py --save-keys
```

---

### Q9. IP 주소 제한을 설정해야 하나요?

**A**:
**보안 강화** (권장):
- 집/사무실 고정 IP만 허용
- 공용 Wi-Fi에서 접속 불가

**편의성 우선**:
- 모든 IP 허용
- 어디서든 접속 가능
- 단, API 키 유출 시 위험

---

## 보안 관련

### Q10. API 키는 어떻게 저장되나요?

**A**:
- **암호화**: AES-256 (Fernet) 암호화
- **키 유도**: PBKDF2-HMAC (480,000 iterations)
- **저장 위치**: `data/config/.credentials.enc`
- **마스터 키**: `data/config/.master.key`

**보안 수준**: 은행급 암호화 (매우 안전)

---

### Q11. 마스터 키 파일을 백업해야 하나요?

**A**:
**강력 권장!**

백업하지 않으면:
- ❌ 프로그램 재설치 시 API 키 복구 불가
- ❌ 다른 컴퓨터로 이동 시 API 키 재입력 필요

**백업 방법**:
1. `data/config/` 폴더 전체 복사
2. USB 드라이브 또는 안전한 클라우드에 저장
3. 암호화된 폴더에 보관

---

### Q12. 패스워드 보호를 추가하고 싶어요.

**A**:
API 키 저장 시:
```bash
python main.py --save-keys
```

"추가 패스워드를 설정하시겠습니까?" → `y` 입력

**장점**:
- 이중 보호 (마스터 키 + 패스워드)
- 타인의 무단 사용 방지

**단점**:
- 패스워드 분실 시 복구 불가
- 매번 입력 필요 (자동화에 불편)

---

### Q13. API 키 파일을 GitHub에 업로드했어요!

**A**:
⚠️ **즉시 조치 필요!**

1. **API 키 삭제** (Upbit 웹사이트에서)
2. **GitHub에서 파일 삭제** 및 커밋 이력 제거
3. **새 API 키 발급** 및 재설정

**파일 이력까지 삭제**:
```bash
# 주의: 이력 삭제는 신중하게!
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch data/config/.credentials.enc" \
  --prune-empty --tag-name-filter cat -- --all
```

---

## 실행 및 사용

### Q14. GUI 모드와 헤드리스 모드의 차이는?

**A**:

**GUI 모드** (Phase 6 구현 예정):
- 그래픽 인터페이스
- 마우스 클릭으로 조작
- 초보자 친화적

**헤드리스 모드** (현재 사용 가능):
- 명령줄 인터페이스
- 백그라운드 실행 가능
- 서버 환경에 적합

---

### Q15. 드라이런 모드는 뭔가요?

**A**:
**실제 주문 없이** 시뮬레이션만 하는 모드

```bash
python main.py --headless --dry-run
```

**특징**:
- ✅ API 연결 정상 작동
- ✅ 가격 조회 정상 작동
- ❌ 실제 주문은 실행 안 됨
- ✅ 전략 테스트 가능

**용도**: 실거래 전 테스트용

---

### Q16. 프로그램을 백그라운드에서 계속 실행하려면?

**A**:

**Windows**:
```bash
start /B python main.py --headless
```

**Linux/Mac**:
```bash
nohup python main.py --headless &
```

**더 좋은 방법** (Phase 4 구현 예정):
- Windows 서비스 등록
- Systemd 서비스 (Linux)
- 자동 시작 설정

---

### Q17. 로그는 어디서 확인하나요?

**A**:
**로그 파일 위치**: `logs/upbit_dca.log`

**확인 방법**:
```bash
# 전체 로그 보기
type logs\upbit_dca.log

# 최근 20줄만 보기 (Linux/Mac)
tail -20 logs/upbit_dca.log

# 실시간 로그 보기 (Linux/Mac)
tail -f logs/upbit_dca.log
```

---

## 오류 해결

### Q18. "ModuleNotFoundError: No module named 'X'" 오류

**A**:
해당 모듈이 설치되지 않음.

```bash
# 전체 재설치
pip install --upgrade -r requirements.txt

# 특정 모듈만 설치
pip install 모듈이름
```

---

### Q19. "Rate Limit 초과" 오류

**A**:
Upbit API 요청 한도 초과.

**대기 시간**:
- 주문 API: 1초당 8회 → 0.125초 대기
- 계좌 API: 1초당 30회 → 0.033초 대기
- 시세 API: 1분당 600회 → 0.1초 대기

**해결**: 1분 후 재시도

---

### Q20. "JWT token is invalid" 오류

**A**:
API 키가 잘못되었거나 만료됨.

**확인사항**:
1. Upbit에서 API 키 상태 확인 (활성화 여부)
2. API 키 권한 확인
3. IP 주소 제한 확인

**해결**:
```bash
# API 키 재저장
python main.py --delete-keys
python main.py --save-keys
```

---

### Q21. "Connection Error" 오류

**A**:
네트워크 연결 문제.

**확인사항**:
1. 인터넷 연결 상태
2. 방화벽 설정 (443 포트 허용)
3. Upbit 서버 상태: https://status.upbit.com

**해결**: 잠시 후 재시도 또는 재부팅

---

## Windows .exe 빌드

### Q22. .exe 파일로 만들 수 있나요?

**A**:
네! PyInstaller로 빌드 가능합니다.

**빌드 방법**:
```bash
pip install pyinstaller
pyinstaller build_exe.spec
```

**결과물**: `dist/UpbitDCATrader/UpbitDCATrader.exe`

자세한 내용: `BUILD_GUIDE.md` 참고

---

### Q23. 단일 파일 vs 디렉토리 모드?

**A**:

**단일 파일** (`ONE_FILE = True`):
- ✅ 배포 간편 (파일 하나)
- ❌ 시작 느림 (3~10초 압축 해제)
- ❌ 파일 크기 큼 (150~200MB)

**디렉토리 모드** (`ONE_FILE = False`, 권장):
- ✅ 시작 빠름 (즉시)
- ✅ 업데이트 쉬움 (특정 파일만 교체)
- ❌ 여러 파일로 구성

**권장**: 디렉토리 모드

---

### Q24. Windows Defender가 악성코드로 감지해요!

**A**:
PyInstaller로 만든 파일은 **오탐지**가 자주 발생합니다.

**해결 방법**:

**방법 1: Windows Defender 제외 목록 추가**
1. 시작 → "Windows 보안" 검색
2. "바이러스 및 위협 방지" 클릭
3. "바이러스 및 위협 방지 설정 관리"
4. "제외 추가" → "폴더"
5. `dist/UpbitDCATrader` 폴더 선택

**방법 2: 코드 서명** (유료)
- 디지털 서명 인증서 구매
- 실행 파일에 서명 적용

---

### Q25. .exe 파일 크기를 줄이고 싶어요.

**A**:

**방법 1: UPX 압축 활성화**
`build_exe.spec` 파일에서:
```python
upx=True,
```

**방법 2: 불필요한 모듈 제외**
```python
excludes=[
    'matplotlib',  # 그래프 라이브러리
    'scipy',       # 과학 계산
    'IPython',     # Jupyter
]
```

**예상 감소**: 30~50MB

---

## 거래 관련

### Q26. 실제 거래 전에 테스트할 수 있나요?

**A**:
네! 드라이런 모드 사용:

```bash
python main.py --headless --dry-run
```

**Phase 1.5 백테스팅** (구현 예정):
- 과거 데이터로 전략 검증
- 실제 주문 없이 성과 확인

---

### Q27. 어떤 거래 전략을 사용하나요?

**A**:
**Phase 2에서 구현 예정**:

1. **DCA + RSI**: RSI 과매도 구간에서 분할 매수
2. **DCA + MACD**: MACD 골든 크로스 시 매수
3. **DCA + Bollinger Bands**: 하단 밴드 돌파 시 매수

**현재**: API 연동만 완료 (Phase 1)

---

### Q28. 손실이 발생하면 누구 책임인가요?

**A**:
⚠️ **모든 투자 손실은 사용자 책임입니다.**

**이 프로그램은**:
- 교육 및 연구 목적
- 수익 보장 없음
- 투자 조언 아님

**거래 시 주의사항**:
- 소액으로 시작
- 손실 감당 가능한 금액만 투자
- 백테스팅 후 실거래

---

### Q29. 수수료는 얼마인가요?

**A**:
**Upbit 수수료** (2025년 1월 기준):
- 거래 수수료: 0.05% (일반)
- KRW 마켓: Maker 0.05%, Taker 0.05%

**이 프로그램**:
- 무료 오픈소스
- 수수료 없음

---

### Q30. 24시간 자동매매가 가능한가요?

**A**:
**Phase 4 구현 후 가능** (예정):

**현재** (Phase 1):
- API 연동만 완료
- 수동 실행 필요

**향후** (Phase 4):
- 24시간 자동 실행
- 전략 자동 적용
- 텔레그램 알림

---

## 추가 질문

### Q31. 다른 거래소도 지원하나요?

**A**:
현재: Upbit만 지원

향후: 바이낸스, 빗썸 등 추가 예정 (요청 시)

---

### Q32. Mac/Linux에서도 실행되나요?

**A**:
네! 모든 플랫폼 지원:
- ✅ Windows 10/11
- ✅ macOS 10.14 이상
- ✅ Linux (Ubuntu, CentOS 등)

Python이 설치되어 있으면 됩니다.

---

### Q33. 소스 코드를 수정해도 되나요?

**A**:
네! 오픈소스입니다.

**라이선스**: 교육 및 연구 목적
**자유**: 수정, 재배포 가능
**제한**: 상업적 이용 시 별도 협의

---

### Q34. 업데이트는 어떻게 하나요?

**A**:
**Git 사용 시**:
```bash
git pull origin main
pip install --upgrade -r requirements.txt
```

**수동 다운로드**:
1. 최신 버전 다운로드
2. 기존 `data/config/` 폴더 백업
3. 새 버전 압축 해제
4. 백업한 `data/config/` 폴더 복사

---

### Q35. 기여하고 싶어요!

**A**:
환영합니다! 🎉

**기여 방법**:
1. GitHub에서 Fork
2. 기능 개발 또는 버그 수정
3. Pull Request 제출

**기여 분야**:
- 버그 리포트
- 기능 제안
- 코드 개선
- 문서화
- 번역

---

## 📞 추가 도움

더 궁금한 점이 있으면:
- **GitHub Issues**: 버그 리포트 및 기능 요청
- **README.md**: 전체 사용 설명서
- **테스트_가이드.md**: 상세 테스트 가이드
- **BUILD_GUIDE.md**: Windows .exe 빌드 가이드

---

**최종 업데이트**: 2025-01-15
**버전**: FAQ v1.0
**Phase**: Phase 1 완료
