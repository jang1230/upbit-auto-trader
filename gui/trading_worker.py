"""
Trading Engine Worker
GUI에서 Trading Engine을 백그라운드로 실행하는 워커 스레드
"""

import asyncio
import logging
from PySide6.QtCore import QThread, Signal
from typing import Dict, Optional
from core.trading_engine import TradingEngine

logger = logging.getLogger(__name__)


class TradingEngineWorker(QThread):
    """
    Trading Engine 워커 스레드

    GUI 프리징을 방지하고 백그라운드에서 Trading Engine을 실행합니다.
    """

    # 시그널 정의
    started = Signal()                     # 엔진 시작됨
    stopped = Signal()                     # 엔진 중지됨
    log_message = Signal(str)              # 로그 메시지
    status_update = Signal(dict)           # 상태 업데이트
    error_occurred = Signal(str)           # 에러 발생

    def __init__(self, config: Dict):
        """
        초기화

        Args:
            config: Trading Engine 설정 딕셔너리
        """
        super().__init__()
        self.config = config
        self.engine: Optional[TradingEngine] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_requested = False
        self._status_update_task = None
        self._log_handlers = []  # 로그 핸들러 추적용

    def run(self):
        """스레드 실행 (백그라운드)"""
        try:
            # 새로운 이벤트 루프 생성
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Trading Engine 생성
            self.engine = TradingEngine(self.config)

            # 로그 핸들러 추가 (엔진 로그를 GUI로 전달)
            self._setup_log_handler()

            # 시작 시그널
            self.started.emit()
            self.log_message.emit("🚀 트레이딩 엔진 시작")

            # 상태 업데이트 태스크 시작 (2초마다)
            self._status_update_task = self.loop.create_task(self._status_update_loop())

            # 엔진 실행 (비동기)
            self.loop.run_until_complete(self.engine.start())

        except Exception as e:
            error_msg = f"엔진 실행 중 오류: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)

        finally:
            # 1. 로그 핸들러 제거 (Signal source deleted 방지)
            self._cleanup_log_handlers()

            # 2. WebSocket 명시적 종료 (cleanup 속도 향상)
            if self.engine and hasattr(self.engine, 'websocket'):
                try:
                    if self.loop and not self.loop.is_closed():
                        self.loop.run_until_complete(self.engine.websocket.disconnect())
                except Exception:
                    pass

            # 3. 모든 pending tasks 한 번에 정리 (빠른 종료)
            if self.loop and not self.loop.is_closed():
                try:
                    # 모든 태스크 수집 및 취소
                    pending = asyncio.all_tasks(self.loop)
                    for task in pending:
                        task.cancel()

                    # 짧은 timeout으로 한 번에 정리 (최대 1초)
                    if pending:
                        self.loop.run_until_complete(
                            asyncio.wait(pending, timeout=1.0)
                        )
                except Exception:
                    pass
                finally:
                    # Loop 닫기
                    self.loop.close()

            # 4. Signal emit (마지막에 실행)
            try:
                self.stopped.emit()
                self.log_message.emit("⏹️ 트레이딩 엔진 중지됨")
            except RuntimeError:
                pass

    def stop_engine(self):
        """엔진 중지 요청 (비블로킹)"""
        if self.engine and self.engine.is_running:
            self.log_message.emit("⏸️ 트레이딩 중지 요청...")

            # asyncio 태스크로 중지 (블로킹 제거)
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.engine.stop(),
                    self.loop
                )
                # future.result() 제거 → 비블로킹
                # Worker 스레드가 자연스럽게 종료됨

    def get_status(self) -> Optional[Dict]:
        """현재 상태 조회"""
        if self.engine:
            return self.engine.get_status()
        return None

    async def _status_update_loop(self):
        """
        상태 업데이트 루프 (0.5초마다 - 실시간 UI 반영)

        Trading Engine의 현재 상태를 조회하여 GUI로 전송합니다.
        """
        logger.info("🔄 상태 업데이트 루프 시작 (0.5초 간격)")

        # 🔧 엔진이 시작될 때까지 대기 (최대 5초)
        for _ in range(10):
            if self.engine and self.engine.is_running:
                break
            await asyncio.sleep(0.5)

        if not self.engine or not self.engine.is_running:
            logger.error("❌ 엔진이 시작되지 않아 상태 업데이트 루프 종료")
            return

        logger.info("✅ 엔진 시작 확인, 상태 업데이트 시작")

        # 이전 포지션 추적 (변경 시에만 로그)
        prev_position = 0.0

        while self.engine and self.engine.is_running:
            try:
                # 현재 상태 조회
                status = self.engine.get_status()

                if status:
                    # 🔧 포지션 변경 시에만 로그 출력 (로그 스팸 방지)
                    position = status.get('position', 0)
                    if position != prev_position:
                        capital = status.get('current_capital', 0)
                        logger.info(f"📊 포지션 변경: {prev_position:.8f} → {position:.8f}, 자본={capital:,.0f}원")
                        prev_position = position

                    # GUI로 상태 전송 (매번 전송)
                    self.status_update.emit(status)

                # 0.5초 대기 (실시간 반영을 위해 단축)
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                # 태스크 취소 시 정상 종료
                break
            except Exception as e:
                logger.error(f"상태 업데이트 오류: {e}")
                await asyncio.sleep(0.5)

    def _setup_log_handler(self):
        """
        로그 핸들러 설정

        Trading Engine의 로그를 GUI로 전달합니다.
        """
        # 커스텀 핸들러
        class GUILogHandler(logging.Handler):
            def __init__(self, signal):
                super().__init__()
                self.signal = signal

            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.signal.emit(msg)
                except RuntimeError:
                    # Signal source deleted → 무시
                    pass

        # 핸들러 추가
        gui_handler = GUILogHandler(self.log_message)
        gui_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        gui_handler.setFormatter(formatter)

        # 로거 리스트
        logger_names = [
            'gui.trading_worker',  # 🔧 워커 자체 로거 추가 (디버그 로그용)
            'core.trading_engine',
            'core.upbit_websocket',
            'core.data_buffer',
            'core.strategies',
            'core.risk_manager',
            'core.order_manager',
            'core.telegram_bot'
        ]

        # 각 로거에 핸들러 추가 및 추적
        for logger_name in logger_names:
            logger_obj = logging.getLogger(logger_name)
            logger_obj.setLevel(logging.INFO)  # 🔧 로거 레벨을 INFO로 설정
            logger_obj.addHandler(gui_handler)
            self._log_handlers.append((logger_obj, gui_handler))

    def _cleanup_log_handlers(self):
        """로그 핸들러 정리 (재시작 시 Signal source deleted 방지)"""
        for logger_obj, handler in self._log_handlers:
            try:
                logger_obj.removeHandler(handler)
            except Exception:
                pass
        self._log_handlers.clear()
