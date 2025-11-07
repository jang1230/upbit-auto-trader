"""
V4Worker - V4 거래 엔진 QThread 래퍼

V4TradingEngine을 Qt GUI와 통합하기 위한 워커
- V4TradingEngine 실행 및 관리
- Qt 신호를 통한 GUI 업데이트
- 로그 캡처 및 전달
"""

import logging
import time
from PySide6.QtCore import QThread, Signal
from typing import Optional

from core.v4_trading_engine import V4TradingEngine
from core.upbit_api import UpbitAPI

logger = logging.getLogger(__name__)


class QtLogHandler(logging.Handler):
    """
    로깅 핸들러 - 로그 메시지를 Qt 신호로 전달
    """

    def __init__(self, log_signal: Signal):
        super().__init__()
        self.log_signal = log_signal

        # 로그 포맷 설정
        formatter = logging.Formatter('%(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        """로그 메시지를 신호로 전달"""
        try:
            msg = self.format(record)
            self.log_signal.emit(msg)
        except Exception:
            self.handleError(record)


class V4Worker(QThread):
    """
    V4 거래 엔진 워커

    V4TradingEngine을 QThread 안에서 실행하고
    Qt 신호를 통해 GUI와 통신
    """

    # 시그널 정의 (V3 워커와 호환)
    log_signal = Signal(str)
    status_signal = Signal(dict)
    error_signal = Signal(str)
    position_update_signal = Signal(dict)
    trade_signal = Signal(dict)

    def __init__(
        self,
        config_path: str = "config/trading_config.json",
        upbit_api: Optional[UpbitAPI] = None,
        parent=None
    ):
        """
        Args:
            config_path: 설정 파일 경로
            upbit_api: Upbit API 인스턴스 (None이면 dry-run)
            parent: 부모 위젯
        """
        super().__init__(parent)

        self.config_path = config_path
        self.upbit_api = upbit_api
        self.engine = None
        self._running = False

        # 로그 핸들러 설정
        self._setup_log_handler()

    def _setup_log_handler(self):
        """로그 핸들러 설정"""
        # V4TradingEngine의 로거에 핸들러 추가
        engine_logger = logging.getLogger('core.v4_trading_engine')

        # 기존 핸들러 제거 (중복 방지)
        for handler in engine_logger.handlers[:]:
            if isinstance(handler, QtLogHandler):
                engine_logger.removeHandler(handler)

        # 새 핸들러 추가
        qt_handler = QtLogHandler(self.log_signal)
        qt_handler.setLevel(logging.INFO)
        engine_logger.addHandler(qt_handler)

        # 다른 V4 컴포넌트 로거에도 추가
        for module_name in [
            'core.group_manager',
            'core.position_manager',
            'core.trade_history_manager',
            'core.daily_loss_tracker'
        ]:
            mod_logger = logging.getLogger(module_name)

            # 기존 핸들러 제거
            for handler in mod_logger.handlers[:]:
                if isinstance(handler, QtLogHandler):
                    mod_logger.removeHandler(handler)

            # 새 핸들러 추가
            mod_logger.addHandler(qt_handler)

    def run(self):
        """스레드 실행"""
        try:
            self.log_signal.emit("=" * 60)
            self.log_signal.emit("🚀 V4 거래 엔진 시작")
            self.log_signal.emit("=" * 60)

            # V4TradingEngine 생성
            self.engine = V4TradingEngine(
                config_path=self.config_path,
                upbit_api=self.upbit_api
            )

            # 초기 상태 전송
            self._emit_initial_status()

            # 엔진 시작
            self._running = True
            self.engine.start()

            # 엔진이 실행되는 동안 상태 모니터링
            self._monitor_engine()

        except Exception as e:
            logger.error(f"V4 워커 오류: {e}", exc_info=True)
            self.error_signal.emit(f"오류 발생: {str(e)}")
        finally:
            self._cleanup()

    def _emit_initial_status(self):
        """초기 상태 전송"""
        if not self.engine:
            return

        try:
            # 그룹 정보
            groups = self.engine.group_manager.get_all_groups()

            # 전역 설정
            global_settings = self.engine.global_settings

            status = {
                'groups_count': len(groups),
                'observation_mode': self.engine.observation_mode,
                'dry_run': self.engine.dry_run,
                'daily_loss_enabled': self.engine.daily_loss_tracker is not None
            }

            self.status_signal.emit(status)

            # 로그로도 출력
            self.log_signal.emit(f"📊 활성 그룹: {len(groups)}개")
            if self.engine.observation_mode:
                self.log_signal.emit("⚠️ 관찰 전용 모드")
            if self.engine.dry_run:
                self.log_signal.emit("🧪 Dry-run 모드")

        except Exception as e:
            logger.error(f"초기 상태 전송 오류: {e}")

    def _monitor_engine(self):
        """
        엔진 상태 모니터링

        주기적으로 포지션 정보와 거래내역을 업데이트하고 GUI로 전송
        """
        monitor_interval = 5  # 5초마다 체크

        # 🔍 디버그: 모니터링 루프 시작 확인
        logger.info(f"🔍 [DEBUG] V4Worker._monitor_engine 시작")
        logger.info(f"🔍 [DEBUG] _running: {self._running}")
        logger.info(f"🔍 [DEBUG] engine 존재: {self.engine is not None}")
        if self.engine:
            logger.info(f"🔍 [DEBUG] engine.is_running: {self.engine.is_running}")

        while self._running and self.engine and self.engine.is_running:
            try:
                # 🔍 디버그: 루프 반복 확인
                logger.info(f"🔍 [DEBUG] _monitor_engine 루프 실행 중...")

                # 포지션 정보 수집 및 전송
                self._emit_position_updates()

                # 거래내역 수집 및 전송
                self._emit_trade_history_updates()

                # 대기
                time.sleep(monitor_interval)

            except Exception as e:
                logger.error(f"모니터링 오류: {e}")
                time.sleep(monitor_interval)

        # 🔍 디버그: 모니터링 루프 종료
        logger.info(f"🔍 [DEBUG] _monitor_engine 루프 종료")
        logger.info(f"🔍 [DEBUG] 종료 이유 - _running: {self._running}, engine: {self.engine is not None}, is_running: {self.engine.is_running if self.engine else 'N/A'}")

    def _emit_position_updates(self):
        """포지션 업데이트 전송"""
        # 🔍 디버그: 메서드 호출 확인
        logger.info(f"🔍 [DEBUG] V4Worker._emit_position_updates 호출됨")
        logger.info(f"🔍 [DEBUG] engine 존재: {self.engine is not None}")

        if not self.engine:
            logger.info(f"🔍 [DEBUG] engine이 없어서 리턴")
            return

        try:
            # 모든 포지션 가져오기
            logger.info(f"🔍 [DEBUG] position_manager.get_all_positions() 호출 전")
            positions = self.engine.position_manager.get_all_positions()
            logger.info(f"🔍 [DEBUG] positions 타입: {type(positions)}")
            logger.info(f"🔍 [DEBUG] positions 길이: {len(positions) if positions else 0}")

            if positions:
                # 🔍 디버그: 포지션 샘플 출력
                sample_keys = list(positions.keys())[:3] if isinstance(positions, dict) else []
                logger.info(f"🔍 [DEBUG] positions 샘플 키 (최대 3개): {sample_keys}")

                position_data = {
                    'positions': positions,
                    'total_count': len(positions),
                    'timestamp': time.time()
                }

                logger.info(f"🔍 [DEBUG] position_update_signal.emit() 호출 직전")
                logger.info(f"🔍 [DEBUG] position_data keys: {position_data.keys()}")
                logger.info(f"🔍 [DEBUG] total_count: {position_data['total_count']}")

                self.position_update_signal.emit(position_data)

                logger.info(f"🔍 [DEBUG] position_update_signal.emit() 완료")
            else:
                logger.info(f"🔍 [DEBUG] positions가 비어있어서 emit 안함")

        except Exception as e:
            logger.error(f"포지션 업데이트 오류: {e}", exc_info=True)

    def _emit_trade_history_updates(self):
        """거래내역 업데이트 전송"""
        # 🔍 디버그: 메서드 호출 확인
        logger.info(f"🔍 [DEBUG] V4Worker._emit_trade_history_updates 호출됨")

        if not self.engine:
            logger.info(f"🔍 [DEBUG] engine이 없어서 리턴")
            return

        try:
            # 거래내역 가져오기 (최신 50건)
            logger.info(f"🔍 [DEBUG] trade_history_manager.get_all_trades() 호출 전")
            trades = self.engine.trade_history_manager.get_all_trades()[:50]
            logger.info(f"🔍 [DEBUG] trades 타입: {type(trades)}")
            logger.info(f"🔍 [DEBUG] trades 길이: {len(trades) if trades else 0}")

            if trades:
                trade_data = {
                    'trades': trades,
                    'total_count': len(trades),
                    'timestamp': time.time()
                }

                logger.info(f"🔍 [DEBUG] trade_signal.emit() 호출")
                self.trade_signal.emit(trade_data)
                logger.info(f"🔍 [DEBUG] trade_signal.emit() 완료")
            else:
                logger.info(f"🔍 [DEBUG] trades가 비어있어서 emit 안함")

        except Exception as e:
            logger.error(f"거래내역 업데이트 오류: {e}", exc_info=True)

    def stop(self):
        """엔진 중지"""
        self.log_signal.emit("🛑 V4 거래 엔진 중지 요청...")
        self._running = False

        if self.engine:
            try:
                self.engine.stop()
                self.log_signal.emit("✅ V4 거래 엔진 중지 완료")
            except Exception as e:
                logger.error(f"엔진 중지 오류: {e}")
                self.error_signal.emit(f"중지 오류: {str(e)}")

    def _cleanup(self):
        """리소스 정리"""
        self.log_signal.emit("🧹 리소스 정리 중...")

        # 엔진 중지
        if self.engine and self.engine.is_running:
            try:
                self.engine.stop()
            except Exception as e:
                logger.error(f"엔진 중지 오류: {e}")

        self._running = False
        self.log_signal.emit("✅ 정리 완료")


if __name__ == "__main__":
    """테스트 코드"""
    print("V4Worker 테스트")
    print("=" * 60)

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Upbit API 생성 (테스트용 - dry-run)
    api = None  # dry-run 모드

    # 워커 생성
    worker = V4Worker(
        config_path="config/trading_config.json",
        upbit_api=api
    )

    # 신호 연결 (테스트용)
    worker.log_signal.connect(lambda msg: print(f"[LOG] {msg}"))
    worker.error_signal.connect(lambda msg: print(f"[ERROR] {msg}"))
    worker.status_signal.connect(lambda data: print(f"[STATUS] {data}"))

    print("\n워커 시작...")
    worker.start()

    # 10초 대기
    import time
    time.sleep(10)

    print("\n워커 중지...")
    worker.stop()
    worker.wait()

    print("\n✅ 테스트 완료")
