"""
GUI Logging Handler - 사용자 중심 로그 필터링
중요한 거래 정보(매수/매도/익절/손절/에러)만 GUI에 표시
"""

import logging
import re
from datetime import datetime
from PySide6.QtCore import QObject, Signal


class GuiLogHandler(logging.Handler, QObject):
    """
    GUI용 스마트 로깅 핸들러

    기능:
    - 중요한 로그만 GUI에 표시 (매수/매도/익절/손절/에러)
    - 반복적인 시스템 로그 필터링 (캔들 완성, 체크 완료 등)
    - 사용자 친화적인 포맷팅

    사용법:
        gui_handler = GuiLogHandler()
        gui_handler.log_signal.connect(main_window.on_backend_log)
        logging.getLogger("core").addHandler(gui_handler)
    """

    # Signal: (level: str, formatted_message: str)
    log_signal = Signal(str, str)

    # ═══════════════════════════════════════════════════════════
    # 🎯 GUI 표시 대상: 사용자가 관심 있는 거래 결과
    # ═══════════════════════════════════════════════════════════
    IMPORTANT_KEYWORDS = [
        # 💰 거래 체결
        "매수", "매도", "체결", "주문", "취소",

        # 📈 수익/손실
        "익절", "손절", "청산", "수익", "손실",

        # 📊 포지션 관리
        "포지션 생성", "포지션 종료", "DCA 트리거", "DCA 매수",

        # ⚠️ 중요 알림
        "일일 손실 한도", "한도 도달", "거래 중지", "거래 재개",

        # 🔴 에러
        "에러", "오류", "실패", "시간 초과", "API 오류",

        # 🟡 경고 (Rate limit 등)
        "경고", "Rate limit 근접", "재시도",

        # ✅ 시작/종료
        "엔진 시작", "엔진 중지", "거래 시작", "거래 중지"
    ]

    # ═══════════════════════════════════════════════════════════
    # ❌ GUI 제외 대상: 개발자용 디버깅 정보
    # ═══════════════════════════════════════════════════════════
    EXCLUDED_KEYWORDS = [
        # 🔄 반복 로그
        "캔들 완성", "거래 체크 완료", "체크 완료", "폴링 중", "대기 중",
        "모니터링 중", "확인 중", "조회 중",

        # 📡 WebSocket 상세
        "WebSocket 메시지", "WebSocket 연결 시작", "WebSocket 재연결",
        "ping", "pong", "heartbeat",

        # 🔧 Rate Limit 정상 범위
        "Remaining-Req: 3", "Remaining-Req: 4", "Remaining-Req: 5",
        "Rate limit: 3", "Rate limit: 4", "Rate limit: 5",
        "초 대기", "ms 대기",

        # 🧪 내부 처리
        "버퍼 업데이트", "캐시 갱신", "상태 동기화", "헬스체크",
        "데이터 수집", "지표 계산",

        # 🎯 매수 신호 체크 (매 분마다 반복되는 로그)
        "매수 조건 미충족", "매수 신호 체크 시작", "pending 초기 매수",
        "일일 손실 한도 체크 활성화", "포지션 손실 한도 체크 활성화",
        "매수 모드: auto", "매수 모드: manual",

        # 🔄 포지션 관리 (매 분마다 모든 코인에서 반복)
        "포지션 관리 시작",
    ]

    # ═══════════════════════════════════════════════════════════
    # 🚫 제외할 Logger (너무 verbose한 모듈)
    # ═══════════════════════════════════════════════════════════
    EXCLUDED_LOGGERS = [
        "core.candle_aggregator",      # 1분마다 캔들 완성 로그
        "core.upbit_websocket",         # WebSocket 상세 로그
        "core.websocket_manager",       # WebSocket 관리 로그
        "urllib3.connectionpool",       # HTTP 연결 로그
        "asyncio",                      # 비동기 이벤트 루프 로그
    ]

    # ═══════════════════════════════════════════════════════════
    # 🧹 INFO 레벨에서 제거할 이모지 (WARNING/ERROR는 유지)
    # ═══════════════════════════════════════════════════════════
    EMOJI_TO_REMOVE = [
        '🎯', '📬', '💰', '📡', '📝', '🎉', '⏭️', '🔖', '🗑️', '📊',
        '📱', '✅', '🔄', '🛒', '🔌', '🚀', '📌', '🔍', '💵', '🆕',
        '━', '─', '═',  # 구분선 문자도 정리
    ]

    def __init__(self):
        """핸들러 초기화"""
        logging.Handler.__init__(self)
        QObject.__init__(self)

        # 기본 레벨: INFO 이상만 처리
        self.setLevel(logging.INFO)

    def _clean_emoji(self, message: str) -> str:
        """
        INFO 레벨 로그에서 불필요한 이모지 제거

        WARNING/ERROR 레벨은 이모지 유지 (주의 환기 목적)
        """
        for emoji in self.EMOJI_TO_REMOVE:
            message = message.replace(emoji, '')

        # 연속 공백 정리
        while '  ' in message:
            message = message.replace('  ', ' ')

        return message.strip()

    def _format_multiline_message(self, message: str) -> str:
        """
        여러 줄 텔레그램 메시지를 한 줄로 요약

        Before: [Telegram] DCA 추가 매수 완료\n그룹: 3번 그룹\n코인: KRW-0G\n...
        After:  [DCA] KRW-0G Lv.1 | 6,000원 → 1,830원 | 평단 1,871원
        """
        # 여러 줄 메시지가 아니면 그대로 반환
        if '\n' not in message:
            return message

        # ─────────────────────────────────────────────────
        # DCA 추가 매수 완료
        # ─────────────────────────────────────────────────
        if "DCA 추가 매수 완료" in message:
            try:
                coin = re.search(r'코인:\s*(KRW-\w+)', message)
                level = re.search(r'레벨:\s*(\d+)', message)
                amount = re.search(r'추가 금액:\s*([\d,]+)원', message)
                price = re.search(r'체결 가격:\s*([\d,]+)원', message)
                avg_price = re.search(r'평균 매수가:\s*([\d,]+)원', message)

                if coin and level and amount and price:
                    result = f"[DCA] {coin.group(1)} Lv.{level.group(1)} | {amount.group(1)}원 → {price.group(1)}원"
                    if avg_price:
                        result += f" | 평단 {avg_price.group(1)}원"
                    return result
            except Exception:
                pass

        # ─────────────────────────────────────────────────
        # 익절 매도 완료
        # ─────────────────────────────────────────────────
        if "익절 매도 완료" in message:
            try:
                coin = re.search(r'코인:\s*(KRW-\w+)', message)
                level = re.search(r'레벨:\s*(\d+)', message)
                amount = re.search(r'매도 금액:\s*([\d,]+)원', message)
                price = re.search(r'체결 가격:\s*([\d,]+)원', message)

                if coin and level and amount and price:
                    return f"[익절] {coin.group(1)} Lv.{level.group(1)} | {amount.group(1)}원 | 체결 {price.group(1)}원"
            except Exception:
                pass

        # ─────────────────────────────────────────────────
        # 손절 매도 완료
        # ─────────────────────────────────────────────────
        if "손절 매도 완료" in message:
            try:
                coin = re.search(r'코인:\s*(KRW-\w+)', message)
                level = re.search(r'레벨:\s*(\d+)', message)
                amount = re.search(r'매도 금액:\s*([\d,]+)원', message)
                price = re.search(r'체결 가격:\s*([\d,]+)원', message)

                if coin and level and amount and price:
                    return f"[손절] {coin.group(1)} Lv.{level.group(1)} | {amount.group(1)}원 | 체결 {price.group(1)}원"
            except Exception:
                pass

        # ─────────────────────────────────────────────────
        # 기타 여러 줄 메시지: 첫 줄만 반환
        # ─────────────────────────────────────────────────
        first_line = message.split('\n')[0].strip()
        return first_line

    def emit(self, record: logging.LogRecord):
        """
        로그 레코드 처리 및 필터링

        필터링 순서:
        1. DEBUG 레벨 제외
        2. 제외 대상 Logger 필터링
        3. 제외 키워드 체크
        4. 중요 키워드 또는 WARNING 이상만 통과
        5. GUI로 전송
        """
        try:
            # ─────────────────────────────────────────────────
            # 1️⃣ 레벨 필터: DEBUG는 무조건 제외
            # ─────────────────────────────────────────────────
            if record.levelno < logging.INFO:
                return

            # ─────────────────────────────────────────────────
            # 2️⃣ Logger 필터: 특정 모듈 제외
            # ─────────────────────────────────────────────────
            if any(record.name.startswith(excluded) for excluded in self.EXCLUDED_LOGGERS):
                return

            # ─────────────────────────────────────────────────
            # 3️⃣ 메시지 추출
            # ─────────────────────────────────────────────────
            message = record.getMessage()

            # ─────────────────────────────────────────────────
            # 4️⃣ 제외 키워드 체크
            # ─────────────────────────────────────────────────
            if any(keyword in message for keyword in self.EXCLUDED_KEYWORDS):
                return

            # ─────────────────────────────────────────────────
            # 5️⃣ 중요도 체크
            # ─────────────────────────────────────────────────
            is_important = (
                record.levelno >= logging.WARNING or  # WARNING/ERROR는 무조건 표시
                any(keyword in message for keyword in self.IMPORTANT_KEYWORDS)
            )

            if not is_important:
                return  # 중요하지 않으면 GUI에 표시 안 함

            # ─────────────────────────────────────────────────
            # 6️⃣ 여러 줄 메시지 한 줄로 요약
            # ─────────────────────────────────────────────────
            message = self._format_multiline_message(message)

            # ─────────────────────────────────────────────────
            # 7️⃣ GUI 포맷팅 및 전송
            # ─────────────────────────────────────────────────
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

            # INFO 레벨: 이모지 제거 (깔끔한 로그)
            # WARNING/ERROR: 이모지 유지 (주의 환기)
            if record.levelno == logging.INFO:
                # INFO는 메시지 내 이모지 제거, 레벨 이모지도 제거
                clean_message = self._clean_emoji(message)
                formatted = f"[{timestamp}] {clean_message}"
            else:
                # WARNING/ERROR는 이모지 유지
                level_emoji = {
                    'WARNING': '⚠️',
                    'ERROR': '❌',
                    'CRITICAL': '🚨'
                }
                emoji = level_emoji.get(record.levelname, '')
                formatted = f"[{timestamp}] {emoji} {message}"

            # Qt Signal로 GUI 스레드에 전송
            self.log_signal.emit(record.levelname, formatted)

        except Exception as e:
            # 핸들러 내부 에러는 표준 에러 처리로 넘김
            self.handleError(record)

    def filter_example_logs(self):
        """
        예시 로그 필터링 테스트
        (개발자용 참고 자료)
        """
        test_logs = [
            ("INFO", "🔄 캔들 완성: KRW-BTC 1분봉"),  # ❌ 제외
            ("INFO", "거래 체크 완료 - 신호 없음"),     # ❌ 제외
            ("INFO", "💰 매수 주문 체결: KRW-BTC"),   # ✅ 표시
            ("INFO", "Rate limit: 380/400"),          # ❌ 제외
            ("WARNING", "⚠️ Rate limit 근접: 398/400"),  # ✅ 표시
            ("INFO", "💵 익절 매도 체결: +5.2%"),      # ✅ 표시
            ("ERROR", "❌ API 오류: HTTP 500"),        # ✅ 표시
            ("INFO", "WebSocket 메시지 수신"),         # ❌ 제외
            ("INFO", "📉 DCA 트리거: -3.2% 하락"),     # ✅ 표시
        ]

        results = []
        for level, message in test_logs:
            # 제외 키워드 체크
            is_excluded = any(kw in message for kw in self.EXCLUDED_KEYWORDS)

            # 중요 키워드 체크
            is_important = (
                level in ["WARNING", "ERROR", "CRITICAL"] or
                any(kw in message for kw in self.IMPORTANT_KEYWORDS)
            )

            display = "✅ 표시" if (not is_excluded and is_important) else "❌ 제외"
            results.append(f"{display} | {level:8s} | {message}")

        return "\n".join(results)


# ═══════════════════════════════════════════════════════════════
# 💡 사용 예시
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    """테스트 코드"""
    handler = GuiLogHandler()
    print("=" * 60)
    print("GuiLogHandler 필터링 예시")
    print("=" * 60)
    print(handler.filter_example_logs())
    print("=" * 60)
