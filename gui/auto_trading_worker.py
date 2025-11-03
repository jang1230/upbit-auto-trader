"""
AutoTradingWorker - 완전 자동 트레이딩 워커

AutoTradingManager + SemiAutoManager를 실행하는 QThread 워커
"""

import asyncio
import logging
from PySide6.QtCore import QThread, Signal
from typing import Dict, List, Optional

from core.upbit_api import UpbitAPI
from core.order_manager import OrderManager
from core.semi_auto_manager import SemiAutoManager
from core.auto_trading_manager import AutoTradingManager
from core.telegram_bot import TelegramBot
from gui.auto_trading_config import AutoTradingConfig
from gui.dca_config import AdvancedDcaConfig

logger = logging.getLogger(__name__)


class AutoTradingWorker(QThread):
    """
    완전 자동 트레이딩 워커
    
    - AutoTradingManager: 자동 매수 신호 감지 및 진입
    - SemiAutoManager: DCA/익절/손절 자동 관리
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
        auto_config: AutoTradingConfig,
        dca_config: AdvancedDcaConfig,
        dry_run: bool = True,
        balance_update_callback=None,  # 🔧 잔고 갱신 콜백
        telegram_token: Optional[str] = None,  # 🔧 텔레그램 봇 토큰
        telegram_chat_id: Optional[str] = None,  # 🔧 텔레그램 채팅 ID
        parent=None
    ):
        super().__init__(parent)

        self.access_key = access_key
        self.secret_key = secret_key
        self.auto_config = auto_config
        self.dca_config = dca_config
        self.dry_run = dry_run
        self.balance_update_callback = balance_update_callback  # 🔧 저장
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id

        self.api = None
        self.order_manager = None
        self.semi_auto_manager = None
        self.auto_trading_manager = None
        self.telegram_bot = None  # 🔧 텔레그램 봇 인스턴스

        self._running = False
        self._loop = None
    
    def run(self):
        """스레드 실행"""
        try:
            self.log_signal.emit("🚀 완전 자동 트레이딩 시작")
            
            # 새로운 이벤트 루프 생성
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # 비동기 메인 실행
            self._loop.run_until_complete(self._async_main())
            
        except Exception as e:
            logger.error(f"완전 자동 트레이딩 워커 오류: {e}", exc_info=True)
            self.error_signal.emit(f"오류 발생: {str(e)}")
        finally:
            if self._loop:
                self._loop.close()
            self.log_signal.emit("✅ 완전 자동 트레이딩 종료")
    
    async def _async_main(self):
        """비동기 메인 로직"""
        try:
            # 1. API 초기화
            self.api = UpbitAPI(self.access_key, self.secret_key)
            self.log_signal.emit("✅ Upbit API 연결")

            # 2. TelegramBot 초기화 및 시작
            if self.telegram_token and self.telegram_chat_id:
                try:
                    self.telegram_bot = TelegramBot(self.telegram_token, self.telegram_chat_id)
                    await self.telegram_bot.start_bot()
                    self.log_signal.emit("✅ 텔레그램 봇 연결")
                except Exception as e:
                    logger.warning(f"텔레그램 봇 시작 실패: {e}")
                    self.log_signal.emit(f"⚠️ 텔레그램 봇 연결 실패 (알림 비활성화)")
                    self.telegram_bot = None
            else:
                self.log_signal.emit("ℹ️ 텔레그램 미설정 (알림 비활성화)")

            # 3. OrderManager 초기화
            self.order_manager = OrderManager(
                upbit_api=self.api,
                min_order_amount=5000.0,
                balance_update_callback=self.balance_update_callback  # 🔧 잔고 갱신 콜백 전달
            )
            self.log_signal.emit("✅ OrderManager 초기화")

            # 4. SemiAutoManager 초기화
            self.semi_auto_manager = SemiAutoManager(
                upbit_api=self.api,
                order_manager=self.order_manager,
                dca_config=self.dca_config,
                scan_interval=10,
                notification_callback=self._notification_callback,
                balance_update_callback=self.balance_update_callback  # 🔧 잔고 갱신 콜백 전달
            )
            self.log_signal.emit("✅ SemiAutoManager 초기화")
            
            # 4. AutoTradingManager 초기화
            self.auto_trading_manager = AutoTradingManager(
                upbit_api=self.api,
                order_manager=self.order_manager,
                semi_auto_manager=self.semi_auto_manager,
                config=self.auto_config,
                notification_callback=self._notification_callback,
                dry_run=self.dry_run
            )
            self.log_signal.emit("✅ AutoTradingManager 초기화")
            
            # 5. 시작
            await self.semi_auto_manager.start()
            await self.auto_trading_manager.start()
            
            self._running = True
            self.log_signal.emit("🎯 모니터링 시작")
            
            # 6. 상태 모니터링 루프
            while self._running:
                await asyncio.sleep(30)  # 30초마다 상태 업데이트
                
                # 상태 정보 수집
                auto_status = self.auto_trading_manager.get_status()
                semi_status = self.semi_auto_manager.get_status()
                
                # 통합 상태 전송
                status = {
                    'monitoring_count': auto_status['monitoring_count'],
                    'managed_positions': semi_status['managed_count'],
                    'daily_trades': auto_status['daily_trades'],
                    'daily_pnl_pct': auto_status['daily_pnl_pct'],
                    'krw_balance': auto_status['krw_balance'],
                    'positions': semi_status.get('positions', [])
                }
                
                self.status_signal.emit(status)
        
        except asyncio.CancelledError:
            self.log_signal.emit("⏸️ 완전 자동 트레이딩 중지 요청")
        except Exception as e:
            logger.error(f"완전 자동 트레이딩 오류: {e}", exc_info=True)
            self.error_signal.emit(f"오류 발생: {str(e)}")
        finally:
            # 정리
            if self.auto_trading_manager:
                await self.auto_trading_manager.stop()
            if self.semi_auto_manager:
                await self.semi_auto_manager.stop()

            # TelegramBot 종료
            if self.telegram_bot:
                try:
                    await self.telegram_bot.stop_bot()
                    logger.info("✅ TelegramBot 정상 종료")
                except Exception as e:
                    logger.warning(f"TelegramBot 종료 중 오류: {e}")
    
    async def _notification_callback(self, message: str):
        """알림 콜백"""
        # GUI 로그 출력
        self.log_signal.emit(f"📢 {message}")

        # 텔레그램 메시지 전송
        if self.telegram_bot:
            try:
                await self.telegram_bot.send_message(message)
                logger.debug(f"텔레그램 알림 전송 완료: {message[:50]}...")
            except Exception as e:
                logger.error(f"텔레그램 메시지 전송 실패: {e}")
                # 텔레그램 실패 시 GUI 로그만 남기고 계속 진행
                pass
    
    def stop(self):
        """워커 중지"""
        self._running = False
        
        # 이벤트 루프에 중지 태스크 추가
        if self._loop and self._loop.is_running():
            # 루프가 실행 중이면 태스크 취소
            for task in asyncio.all_tasks(self._loop):
                task.cancel()
