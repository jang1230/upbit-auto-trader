#!/bin/bash

# 세션 상태 확인 스크립트
# 사용법: bash check_session_status.sh

echo "========================================="
echo "📊 작업 세션 상태 확인 (2025-11-24)"
echo "========================================="
echo ""

# 1. Git 브랜치 확인
echo "🌿 현재 브랜치:"
current_branch=$(git branch --show-current)
expected_branch="claude/backup-from-v5-copy-01CL6M1nRo9EjaMa9wH9Hw3D"

if [ "$current_branch" = "$expected_branch" ]; then
    echo "   ✅ $current_branch"
else
    echo "   ⚠️  $current_branch (예상: $expected_branch)"
fi
echo ""

# 2. 최신 커밋 확인
echo "📝 최신 커밋:"
latest_commit=$(git log -1 --oneline)
expected_commit="6fab2e2"

if [[ "$latest_commit" == *"$expected_commit"* ]]; then
    echo "   ✅ $latest_commit"
else
    echo "   ⚠️  $latest_commit (예상: $expected_commit로 시작)"
fi
echo ""

# 3. 작업 트리 상태
echo "📂 작업 트리 상태:"
git_status=$(git status --short)

if [ -z "$git_status" ]; then
    echo "   ✅ Clean (변경사항 없음)"
else
    echo "   ⚠️  변경사항 있음:"
    git status --short
fi
echo ""

# 4. 오늘 커밋 개수
echo "🔢 오늘(2025-11-24) 커밋 개수:"
commit_count=$(git log --oneline --since="2025-11-24" --until="2025-11-25" | wc -l)
echo "   총 $commit_count 개 커밋"
echo ""

# 5. 변경된 파일 목록
echo "📄 오늘 변경된 주요 파일:"
echo "   1. gui/main_window.py"
echo "   2. core/v4_trading_engine.py"
echo "   3. gui/logging_handler.py (신규)"
echo ""

# 6. 다음 작업 확인
echo "🎯 다음 작업 우선순위:"
echo "   1. [🔴 긴급] 즉시매도 중복 알림 차단 테스트 (30분)"
echo "   2. [🔴 긴급] 즉시매도 실제 체결가 테스트 (30분)"
echo "   3. [🔴 긴급] 자동 매도 중복 알림 차단 테스트 (1시간)"
echo "   4. [🟡 중요] GUI 로그 필터링 테스트 (30분)"
echo ""

# 7. 세션 문서 확인
echo "📚 세션 문서:"
if [ -f "WORK_SESSION_2025-11-24.md" ]; then
    echo "   ✅ WORK_SESSION_2025-11-24.md (상세 보고서)"
else
    echo "   ❌ WORK_SESSION_2025-11-24.md 없음"
fi

if [ -f "NEXT_SESSION_CHECKLIST.md" ]; then
    echo "   ✅ NEXT_SESSION_CHECKLIST.md (빠른 가이드)"
else
    echo "   ❌ NEXT_SESSION_CHECKLIST.md 없음"
fi

if [ -f "SESSION_DOCS_README.md" ]; then
    echo "   ✅ SESSION_DOCS_README.md (문서 가이드)"
else
    echo "   ❌ SESSION_DOCS_README.md 없음"
fi
echo ""

# 8. Python 환경 확인
echo "🐍 Python 환경:"
if command -v python &> /dev/null; then
    python_version=$(python --version 2>&1)
    echo "   ✅ $python_version"
else
    echo "   ❌ Python not found"
fi
echo ""

# 9. 필수 패키지 확인
echo "📦 필수 패키지:"
python -c "from PySide6 import QtCore; print('   ✅ PySide6 설치됨')" 2>/dev/null || echo "   ❌ PySide6 없음"
python -c "import time; print('   ✅ time 모듈 OK')" 2>/dev/null || echo "   ❌ time 모듈 없음"
echo ""

# 10. 빠른 시작 명령어
echo "🚀 빠른 시작 명령어:"
echo "   테스트 실행: python main.py"
echo "   로그 확인: tail -f logs/trading_*.log"
echo "   문서 열기: cat NEXT_SESSION_CHECKLIST.md"
echo ""

echo "========================================="
echo "✅ 상태 확인 완료"
echo "========================================="
echo ""
echo "💡 다음 단계:"
echo "   1. NEXT_SESSION_CHECKLIST.md 읽기 (5분)"
echo "   2. 테스트 시작 (python main.py)"
echo ""
