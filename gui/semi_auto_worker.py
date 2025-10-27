"""
SemiAutoWorker - 반자동 트레이딩 워커

SemiAutoManager를 실행하는 QThread 워커
- Upbit 앱에서 수동 매수
- 봇이 포지션 감지
- 자동 DCA/익절/손절 관리
"""

import asyncio
import logging
from PySide6.QtCore import QThread, Signal
from typing import Dict

from core.upbit_api import UpbitAPI
from core.order_manager import OrderManager
from core.semi_auto_manager import SemiAutoManager
from gui.dca_config import AdvancedDcaConfig

logger = logging.getLogger(__name__)


class SemiAutoWorker(QThread):
    """
    반자동 트레이딩 워커
    
    - SemiAutoManager: 수동 매수 감지 + DCA/익절/손절 자동 관리
    """
    
    # 시그널 정의
    log_signal = Signal(str)
    status_signal = Signal(dict)
    error_signal = Signal(str)
    position_update_signal = Signal(dict)
    trade_signal = Signal(dict)
    
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        dca_config: AdvancedDcaConfig,
        dry_run: bool = True,
        scan_interval: int = 10,
        balance_update_callback=None,  # 🔧 잔고 갱신 콜백
        parent=None
    ):
        super().__init__(parent)

        self.access_key = access_key
        self.secret_key = secret_key
        self.dca_config = dca_config
        self.dry_run = dry_run
        self.scan_interval = scan_interval
        self.balance_update_callback = balance_update_callback  # 🔧 저장

        self.api = None
        self.order_manager = None
        self.semi_auto_manager = None

        self._running = False
        self._loop = None
    
    def run(self):
        """스레드 실행"""
        try:
            self.log_signal.emit("🚀 반자동 트레이딩 시작")
            self.log_signal.emit("   - Upbit 앱에서 수동 매수 시 자동 감지")
            self.log_signal.emit("   - DCA/익절/손절 자동 관리")
            
            # 새로운 이벤트 루프 생성
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # 비동기 메인 실행
            self._loop.run_until_complete(self._async_main())
            
        except Exception as e:
            logger.error(f"반자동 트레이딩 워커 오류: {e}", exc_info=True)
            self.error_signal.emit(f"오류 발생: {str(e)}")
        finally:
            if self._loop:
                self._loop.close()
            self.log_signal.emit("✅ 반자동 트레이딩 종료")
    
    async def _async_main(self):
        """비동기 메인 로직"""
        try:
            # 1. API 초기화
            self.api = UpbitAPI(self.access_key, self.secret_key)
            self.log_signal.emit("✅ Upbit API 연결")
            
            # 2. OrderManager 초기화
            self.order_manager = OrderManager(
                upbit_api=self.api,
                min_order_amount=5000.0,
                dry_run=self.dry_run,
                balance_update_callback=self.balance_update_callback  # 🔧 잔고 갱신 콜백 전달
            )
            self.log_signal.emit(f"✅ OrderManager 초기화 (dry_run={self.dry_run})")

            # 3. SemiAutoManager 초기화
            self.semi_auto_manager = SemiAutoManager(
                upbit_api=self.api,
                order_manager=self.order_manager,
                dca_config=self.dca_config,
                scan_interval=self.scan_interval,
                notification_callback=self._notification_callback,
                position_callback=self._position_callback,  # 🔧 포지션 업데이트 콜백
                balance_update_callback=self.balance_update_callback  # 🔧 잔고 갱신 콜백 전달
            )
            self.log_signal.emit("✅ SemiAutoManager 초기화")
            
            # 4. 시작
            await self.semi_auto_manager.start()
            
            self._running = True
            self.log_signal.emit("🎯 포지션 모니터링 시작")
            self.log_signal.emit(f"   - 스캔 주기: {self.scan_interval}초")
            
            # 5. 상태 모니터링 루프 (30초마다)
            while self._running:
                await asyncio.sleep(30)
                
                # 상태 정보 수집
                status = self.semi_auto_manager.get_status()
                
                # 시그널 발송
                self.status_signal.emit(status)
                
                # 로그 (간단하게)
                managed_count = status.get('managed_positions', 0)
                if managed_count > 0:
                    self.log_signal.emit(f"📊 관리 중인 포지션: {managed_count}개")
        
        except Exception as e:
            logger.error(f"SemiAutoWorker 비동기 메인 오류: {e}", exc_info=True)
            self.error_signal.emit(f"오류: {str(e)}")
    
    def stop(self):
        """워커 중단"""
        self._running = False
        if self._loop and self.semi_auto_manager:
            # 비동기 stop 호출을 위한 태스크 생성
            future = asyncio.run_coroutine_threadsafe(
                self.semi_auto_manager.stop(),
                self._loop
            )
            try:
                # 최대 5초 대기 (SemiAutoManager.stop()은 최대 4초 소요)
                future.result(timeout=5)
                logger.info("✅ SemiAutoManager 정상 종료")
            except asyncio.TimeoutError:
                logger.warning("⚠️ SemiAutoManager 종료 타임아웃 (5초 초과)")
            except Exception as e:
                logger.error(f"SemiAutoManager 중단 오류: {e}")

    def update_dca_config(self, dca_config: AdvancedDcaConfig):
        """
        DCA 설정 실시간 업데이트

        Args:
            dca_config: 새로운 DCA 설정
        """
        self.dca_config = dca_config

        if self._loop and self.semi_auto_manager and self._running:
            # 비동기 업데이트 호출을 위한 태스크 생성
            future = asyncio.run_coroutine_threadsafe(
                self.semi_auto_manager.update_dca_config(dca_config),
                self._loop
            )
            try:
                future.result(timeout=3)
                self.log_signal.emit("✅ DCA 설정 실시간 반영 완료")
            except Exception as e:
                logger.error(f"DCA 설정 업데이트 오류: {e}")
                self.error_signal.emit(f"DCA 설정 업데이트 실패: {str(e)}")

    async def _notification_callback(self, message: str):
        """알림 콜백 (SemiAutoManager에서 호출)"""
        self.log_signal.emit(f"📢 {message}")

    async def _position_callback(self, position_data: dict):
        """포지션 업데이트 콜백 (SemiAutoManager에서 호출)"""
        # GUI 업데이트를 위해 position_update_signal emit
        self.position_update_signal.emit(position_data)
