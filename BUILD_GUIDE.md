# Windows .exe 파일 빌드 가이드

Upbit DCA Trader를 Windows 실행 파일(.exe)로 패키징하는 가이드입니다.

## 📋 사전 요구사항

### 1. Python 설치
- Python 3.10 이상 권장
- https://www.python.org/downloads/

### 2. 필수 패키지 설치
```bash
pip install -r requirements.txt
pip install pyinstaller
```

## 🔨 빌드 방법

### 옵션 1: 디렉토리 형태 (권장)
**장점**: 빠른 시작 속도, 디버깅 용이
**단점**: 여러 파일로 구성

```bash
# build_exe.spec 파일 수정
# ONE_FILE = False (기본값)

# 빌드 실행
pyinstaller build_exe.spec

# 결과물 위치
dist/UpbitDCATrader/UpbitDCATrader.exe
```

### 옵션 2: 단일 실행 파일
**장점**: 배포 간편, 단일 파일
**단점**: 느린 시작 속도 (압축 해제 시간), 큰 파일 크기

```bash
# build_exe.spec 파일 수정
# ONE_FILE = True

# 빌드 실행
pyinstaller build_exe.spec

# 결과물 위치
dist/UpbitDCATrader.exe
```

## 📁 디렉토리 구조

### 디렉토리 모드 (권장)
```
dist/
└── UpbitDCATrader/
    ├── UpbitDCATrader.exe    # 실행 파일
    ├── data/                  # 설정 및 데이터 디렉토리
    ├── README.md
    ├── requirements.txt
    └── _internal/             # PyInstaller 내부 파일들
        ├── api/
        ├── core/
        ├── gui/
        ├── utils/
        └── ...
```

### 단일 파일 모드
```
dist/
└── UpbitDCATrader.exe    # 단일 실행 파일 (모든 것 포함)
```

## 🎯 빌드 옵션 설정

`build_exe.spec` 파일을 편집하여 빌드 옵션을 변경할 수 있습니다:

```python
# 빌드 옵션
ONE_FILE = False  # True: 단일 .exe, False: 디렉토리 형태
CONSOLE = False   # True: 콘솔 표시, False: GUI 전용
NAME = 'UpbitDCATrader'
```

### ONE_FILE (단일 파일 여부)
- `True`: 모든 것을 하나의 .exe 파일로 압축
  - 배포 편리
  - 시작 시 압축 해제 시간 소요 (3-10초)
  - 파일 크기: 약 150-200MB

- `False`: 디렉토리 형태로 배포 (권장)
  - 빠른 시작 (즉시 실행)
  - 업데이트 시 특정 파일만 교체 가능
  - 디버깅 용이

### CONSOLE (콘솔 창 표시)
- `True`: 프로그램 실행 시 콘솔 창 표시
  - 로그 메시지 확인 가능
  - 디버깅 용도

- `False`: GUI 전용 모드
  - 콘솔 창 없이 GUI만 표시
  - 일반 사용자용

## 🔍 빌드 후 테스트

### 1. 기본 실행 테스트
```bash
# 디렉토리 모드
cd dist/UpbitDCATrader
./UpbitDCATrader.exe

# 단일 파일 모드
cd dist
./UpbitDCATrader.exe
```

### 2. 헤드리스 모드 테스트
```bash
./UpbitDCATrader.exe --headless --dry-run
```

### 3. API 키 저장 테스트
```bash
./UpbitDCATrader.exe --save-keys
```

## 🐛 문제 해결

### ImportError: 모듈을 찾을 수 없음
**원인**: PyInstaller가 모듈을 자동 감지하지 못함

**해결**:
1. `build_exe.spec` 파일 열기
2. `hiddenimports` 리스트에 누락된 모듈 추가:
```python
hiddenimports=[
    'your_missing_module',
    ...
]
```
3. 재빌드

### 실행 시 "파일을 찾을 수 없습니다" 오류
**원인**: 리소스 파일 경로 문제

**해결**:
1. `build_exe.spec` 파일의 `datas` 섹션 확인:
```python
datas=[
    ('data', 'data'),        # 데이터 디렉토리
    ('README.md', '.'),       # 루트 파일
]
```
2. 코드에서 `sys._MEIPASS` 사용 확인

### 안티바이러스 경고
**원인**: PyInstaller로 생성된 파일은 오탐지될 수 있음

**해결**:
1. Windows Defender 제외 목록에 추가
2. 프로그램 시작 전 안티바이러스 임시 비활성화
3. 또는 코드 서명 인증서 적용 (유료)

### 실행 속도가 느림 (단일 파일 모드)
**원인**: 프로그램 시작 시 압축 해제 시간

**해결**:
- 디렉토리 모드로 변경 (`ONE_FILE = False`)

## 📦 배포 준비

### 1. 테스트 완료 확인
- [ ] GUI 모드 정상 작동
- [ ] 헤드리스 모드 정상 작동
- [ ] API 연결 테스트 성공
- [ ] 모든 기능 정상 작동

### 2. 배포 파일 준비
```bash
# 디렉토리 전체를 ZIP으로 압축
cd dist
zip -r UpbitDCATrader_v1.0.0.zip UpbitDCATrader/

# 또는 단일 파일
zip UpbitDCATrader_v1.0.0.zip UpbitDCATrader.exe
```

### 3. README 포함
배포 시 다음 파일들 포함:
- `UpbitDCATrader.exe` (또는 디렉토리)
- `README.md` (사용 설명서)
- `LICENSE` (라이선스 정보)

## 📊 예상 파일 크기

### 디렉토리 모드
- 전체 크기: 약 150-200MB
- 주요 용량: PySide6 (약 100MB)

### 단일 파일 모드
- 파일 크기: 약 150-200MB
- 압축된 단일 실행 파일

## 🔒 보안 고려사항

### API 키 저장
- API 키는 `data/config/.credentials.enc` 파일에 암호화되어 저장
- 마스터 키는 `data/config/.master.key` 파일에 저장
- 이 파일들은 반드시 사용자가 보관해야 함
- 프로그램 재설치 시 백업 필요

### 배포 시 주의사항
- 절대 API 키를 포함하여 배포하지 마세요
- `data/config/` 디렉토리는 사용자별로 생성됩니다
- `.env` 파일은 배포에서 제외하세요

## 🎨 커스터마이징

### 아이콘 변경
1. `.ico` 파일 준비 (256x256 권장)
2. `build_exe.spec` 파일 수정:
```python
icon='path/to/your/icon.ico'
```
3. 재빌드

### 프로그램 이름 변경
```python
NAME = 'YourProgramName'
```

## 📝 빌드 체크리스트

빌드 전 확인 사항:
- [ ] 모든 테스트 통과
- [ ] requirements.txt 업데이트
- [ ] 버전 번호 확인
- [ ] README.md 업데이트
- [ ] 라이선스 정보 확인

빌드 후 확인 사항:
- [ ] 실행 파일 정상 작동
- [ ] 모든 기능 테스트
- [ ] 다른 PC에서 실행 테스트
- [ ] Windows Defender 오탐지 확인

---

## 📦 Pre-Build Checklist (V4)

**V4 시스템**을 빌드하기 전, 다음 항목들을 반드시 확인하세요:

### 1. V4 Configuration Files Included

V4 설정 파일들이 프로젝트에 포함되어 있는지 확인:

```bash
# Configuration template
ls -la config/trading_config_template.json

# JSON Schema validation file
ls -la config/schemas/trading_config_schema.json
```

**Expected Output**:
```
-rw-r--r-- 1 user user 1234 Jan 26 config/trading_config_template.json
-rw-r--r-- 1 user user 5678 Jan 26 config/schemas/trading_config_schema.json
```

### 2. Data Folder Structure

V4 런타임 데이터 폴더 구조 확인:

```bash
ls -la data/
```

**Expected Structure**:
```
data/
├── .gitkeep  (placeholder, 빌드 시 포함)
└── (runtime files will be auto-created on first run)
```

**Note**:
- `positions_live.json`, `positions_dryrun.json`, `trade_history.json`는 첫 실행 시 자동 생성됩니다
- 빌드에 포함할 필요 없음

### 3. V4 Dependencies Installed

V4 필수 패키지들이 설치되었는지 확인:

```bash
pip list | grep -E "PySide6|requests|websockets|jsonschema"
```

**Expected Output**:
```
jsonschema         4.x.x
PySide6            6.6.x
requests           2.31.x
websockets         12.x
```

### 4. Test V4 Features Before Build

빌드하기 전, V4 기능들을 테스트하여 정상 작동 확인:

```bash
# Launch GUI
python main.py
```

**Test Checklist**:
- [ ] Create a group via GUI
- [ ] Add coins to the group
- [ ] Configure auto-buy preset (Conservative/Balanced/Aggressive)
- [ ] Configure DCA levels (e.g., -3%, -5%, -7%)
- [ ] Configure Profit levels (e.g., +5%, +10%)
- [ ] Configure Loss levels (e.g., -15%)
- [ ] Test dry-run mode (at least 5 minutes)
- [ ] Verify `config/trading_config.json` is created
- [ ] Verify position files are created

### 5. Verify build_exe.spec

`build_exe.spec` 파일을 열어 V4 파일들이 포함되어 있는지 확인:

```bash
cat build_exe.spec | grep -A 10 "datas="
```

**Expected in datas list**:
```python
datas=[
    ('config/trading_config_template.json', 'config'),
    ('config/schemas/trading_config_schema.json', 'config/schemas'),
    ('data', 'data'),  # Include data folder with .gitkeep
    ('README.md', '.'),
    ('requirements.txt', '.'),
    # ... other files
]
```

**Critical V4 Files**:
- ✅ `config/trading_config_template.json` - V4 configuration template
- ✅ `config/schemas/trading_config_schema.json` - JSON Schema validation
- ✅ `data/` folder structure - Runtime data location

**V4 Core Modules (automatically included)**:
- `core/config_manager.py`
- `core/position_manager.py`
- `core/trade_history_manager.py`
- `core/group_manager.py`
- `core/daily_loss_tracker.py`
- `core/strategies/v4_auto_buy_strategy.py`
- `core/v4_trading_engine.py`

### 6. Clean Previous Builds

이전 빌드 결과물을 삭제하여 깨끗한 빌드 환경 조성:

```bash
# Remove build artifacts
rm -rf build/ dist/

# Clear PyInstaller cache
rm -rf __pycache__/ *.spec.bak
```

### 7. V4 Build Command

모든 체크리스트 완료 후 빌드 실행:

```bash
# Directory mode (recommended for V4)
pyinstaller build_exe.spec

# Verify V4 files in output
ls -la dist/UpbitDCATrader/config/
ls -la dist/UpbitDCATrader/data/
```

**Post-Build Verification**:
```bash
cd dist/UpbitDCATrader/

# Check V4 config files exist
ls config/trading_config_template.json
ls config/schemas/trading_config_schema.json

# Run executable
./UpbitDCATrader.exe

# On first run, should auto-create:
# - config/trading_config.json
# - data/positions_live.json
# - data/positions_dryrun.json
# - data/trade_history.json
```

---

## 🚀 고급 빌드 옵션

### UPX 압축
파일 크기를 더 줄이려면 UPX 사용:

```python
upx=True,            # UPX 압축 활성화
upx_exclude=[],      # 제외할 파일
```

**주의**: UPX 압축은 안티바이러스 오탐지를 증가시킬 수 있습니다.

### 특정 모듈 제외
불필요한 모듈을 제외하여 크기 감소:

```python
excludes=[
    'matplotlib',   # 그래프 라이브러리 (불필요 시)
    'IPython',      # Jupyter 관련
    'scipy',        # 과학 계산 (불필요 시)
]
```

## 💡 팁

1. **개발 중**: `CONSOLE = True`로 설정하여 로그 확인
2. **배포 시**: `CONSOLE = False`, `ONE_FILE` 선택
3. **대량 배포**: 디렉토리 모드 권장 (업데이트 편리)
4. **개인 사용**: 단일 파일 모드 간편

## 📞 문제 발생 시

문제가 발생하면 다음을 확인하세요:
1. Python 버전: 3.10 이상
2. PyInstaller 버전: 최신 버전
3. 모든 dependencies 설치 확인
4. `build/` 및 `dist/` 폴더 삭제 후 재빌드

상세한 로그를 보려면:
```bash
pyinstaller --log-level DEBUG build_exe.spec
```
