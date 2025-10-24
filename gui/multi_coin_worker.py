"""
Multi-Coin Trading Worker
GUI에서 MultiCoinTrader를 백그라운드로 실행하는 워커 스레드
"""

import asyncio
import logging
from PySide6.QtCore import QThread, Signal
from typing import Dict, Optional, List
from core.multi_coin_trader import MultiCoinTrader

logger = logging.getLogger(__name__)


class MultiCoinTradingWorker(QThread):
    """
    Multi-Coin Trading Worker 스레드

    GUI 프리징을 방지하고 백그라운드에서 MultiCoinTrader를 실행합니다.
    여러 코인을 동시에 독립적으로 트레이딩합니다.
    """

    # 시그널 정의
    started = Signal()                     # 트레이더 시작됨
    stopped = Signal()                     # 트레이더 중지됨
    log_message = Signal(str)              # 로그 메시지
    portfolio_update = Signal(dict)        # 포트폴리오 통합 상태 업데이트
    coin_update = Signal(str, dict)        # 개별 코인 상태 업데이트 (symbol, status)
    trade_executed = Signal(dict)          # 거래 실행됨 (trade_data)
    error_occurred = Signal(str)           # 에러 발생

    def __init__(self, config: Dict):
        """
        초기화

        Args:
            config: Multi-Coin Trader 설정 딕셔너리
                - symbols: List[str] - 코인 심볼 리스트
                - total_capital: float - 총 투자 자본
                - strategy: Dict - 전략 설정
                - risk_management: Dict - 리스크 관리 설정
                - dca_config: DcaConfig - DCA 설정
                - order_amount: float - 주문 금액
                - dry_run: bool - 페이퍼 트레이딩 모드
                - access_key: str - 업비트 API 키
                - secret_key: str - 업비트 시크릿 키
                - telegram: Dict - 텔레그램 설정
        """
        super().__init__()
        self.config = config
        self.trader: Optional[MultiCoinTrader] = None
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

            # MultiCoinTrader 생성 (거래 콜백 전달)
            self.trader = MultiCoinTrader(
                symbols=self.config['symbols'],
                total_capital=self.config['total_capital'],
                strategy_config=self.config['strategy'],
                risk_config=self.config['risk_management'],
                dca_config=self.config['dca_config'],
                order_amount=self.config['order_amount'],
                dry_run=self.config['dry_run'],
                access_key=self.config.get('access_key', ''),
                secret_key=self.config.get('secret_key', ''),
                telegram_config=self.config.get('telegram'),
                trade_callback=self._on_trade_executed  # 🔧 거래 콜백
            )

            # 로그 핸들러 추가 (트레이더 로그를 GUI로 전달)
            self._setup_log_handler()

            # 시작 시그널
            self.started.emit()
            self.log_message.emit("🚀 다중 코인 트레이딩 시작")

            # 상태 업데이트 태스크 시작 (0.5초마다)
            self._status_update_task = self.loop.create_task(self._status_update_loop())

            # 트레이더 실행 (비동기)
            self.loop.run_until_complete(self.trader.start())

        except Exception as e:
            error_msg = f"트레이더 실행 중 오류: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)

        finally:
            # 1. 로그 핸들러 제거
            self._cleanup_log_handlers()

            # 2. 모든 pending tasks 정리
            if self.loop and not self.loop.is_closed():
                try:
                    pending = asyncio.all_tasks(self.loop)
                    for task in pending:
                        task.cancel()

                    if pending:
                        self.loop.run_until_complete(
                            asyncio.wait(pending, timeout=1.0)
                        )
                except Exception:
                    pass
                finally:
                    self.loop.close()

            # 3. Signal emit
            try:
                self.stopped.emit()
                self.log_message.emit("⏹️ 다중 코인 트레이딩 중지됨")
            except RuntimeError:
                pass

    def stop_trader(self):
        """트레이더 중지 요청 (비블로킹)"""
        if self.trader and self.trader.is_running:
            self.log_message.emit("⏸️ 다중 코인 트레이딩 중지 요청...")

            # asyncio 태스크로 중지
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.trader.stop(),
                    self.loop
                )

    def get_portfolio_status(self) -> Optional[Dict]:
        """전체 포트폴리오 상태 조회"""
        if self.trader:
            return self.trader.get_portfolio_status()
        return None

    def get_coin_status(self, symbol: str) -> Optional[Dict]:
        """특정 코인 상태 조회"""
        if self.trader:
            return self.trader.get_coin_status(symbol)
        return None
    
    def update_dca_config(self, dca_config):
        """
        실행 중 DCA 설정 업데이트 (비블로킹)
        
        Args:
            dca_config: 새로운 AdvancedDcaConfig 객체
        """
        if self.trader and self.trader.is_running:
            self.log_message.emit("🔄 DCA 설정 업데이트 중...")
            
            # asyncio 태스크로 업데이트
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.trader.update_dca_config(dca_config),
                    self.loop
                )
    
    def update_coins(self, new_symbols: list):
        """
        실행 중 코인 선택 변경 (비블로킹)
        
        Args:
            new_symbols: 새로운 코인 심볼 리스트
        """
        if self.trader and self.trader.is_running:
            self.log_message.emit(f"🔄 코인 선택 업데이트 중... ({len(new_symbols)}개)")
            
            # asyncio 태스크로 업데이트
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.trader.update_coins(new_symbols),
                    self.loop
                )
    
    def _on_trade_executed(self, trade_data: dict):
        """
        거래 실행 콜백 핸들러
        
        TradingEngine에서 매수/매도 실행 시 호출되며, GUI로 시그널 전송
        
        Args:
            trade_data: 거래 정보
                - timestamp: 거래 시각
                - symbol: 코인 심볼
                - trade_type: 'buy' or 'sell'
                - price: 거래 가격
                - quantity: 거래 수량
                - amount: 거래 금액
                - profit: 손익 (매도 시)
                - profit_pct: 손익률 (매도 시)
                - reason: 거래 사유
                - order_id: 주문 ID
        """
        try:
            # GUI로 거래 데이터 전송
            self.trade_executed.emit(trade_data)
        except Exception as e:
            logger.error(f"거래 콜백 오류: {e}")

    async def _status_update_loop(self):
        """
        상태 업데이트 루프 (0.5초마다 - 실시간 UI 반영)

        포트폴리오 전체 상태와 개별 코인 상태를 GUI로 전송합니다.
        """
        logger.info("🔄 포트폴리오 상태 업데이트 루프 시작 (0.5초 간격)")

        # 트레이더가 시작될 때까지 대기 (최대 5초)
        for _ in range(10):
            if self.trader and self.trader.is_running:
                break
            await asyncio.sleep(0.5)

        if not self.trader or not self.trader.is_running:
            logger.error("❌ 트레이더가 시작되지 않아 상태 업데이트 루프 종료")
            return

        logger.info("✅ 트레이더 시작 확인, 상태 업데이트 시작")

        # 이전 포지션 수 추적 (매수/매도 발생 시에만 로그)
        prev_position_count = 0

        while self.trader and self.trader.is_running:
            try:
                # 포트폴리오 전체 상태 조회
                portfolio_status = self.trader.get_portfolio_status()

                if portfolio_status:
                    total_asset = portfolio_status.get('total_current_asset', 0)
                    return_pct = portfolio_status.get('total_return_pct', 0)
                    position_count = portfolio_status.get('summary', {}).get('position_count', 0)

                    # 포지션 수 변경 시에만 로그 출력 (매수/매도/익절/손절)
                    if position_count != prev_position_count:
                        logger.info(
                            f"💼 포트폴리오: 총 자산={total_asset:,.0f}원, "
                            f"수익률={return_pct:+.2f}%, "
                            f"포지션={position_count}개"
                        )
                        prev_position_count = position_count

                    # GUI로 포트폴리오 상태 전송 (항상 전송 - UI 업데이트용)
                    self.portfolio_update.emit(portfolio_status)

                    # 개별 코인 상태도 전송
                    coins_status = portfolio_status.get('coins', {})
                    for symbol, coin_status in coins_status.items():
                        self.coin_update.emit(symbol, coin_status)

                # 0.5초 대기
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"상태 업데이트 오류: {e}")
                await asyncio.sleep(0.5)

    def _setup_log_handler(self):
        """
        로그 핸들러 설정

        MultiCoinTrader 및 모든 TradingEngine의 로그를 GUI로 전달합니다.
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
                    pass

        # 핸들러 추가
        gui_handler = GUILogHandler(self.log_message)
        gui_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        gui_handler.setFormatter(formatter)

        # 로거 리스트
        logger_names = [
            'gui.multi_coin_worker',
            'core.multi_coin_trader',
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
            logger_obj.setLevel(logging.INFO)
            logger_obj.addHandler(gui_handler)
            self._log_handlers.append((logger_obj, gui_handler))

    def _cleanup_log_handlers(self):
        """로그 핸들러 정리"""
        for logger_obj, handler in self._log_handlers:
            try:
                logger_obj.removeHandler(handler)
            except Exception:
                pass
        self._log_handlers.clear()
