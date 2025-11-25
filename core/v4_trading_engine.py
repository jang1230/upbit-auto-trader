"""
V4 거래 엔진

역할:
- 모든 V4 컴포넌트 통합
- 그룹별 독립 거래 루프
- 실시간 포지션 관리
- 전역 제약 확인
- 일일 스냅샷 및 리셋
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import threading
import schedule
import asyncio

from core.config_manager import ConfigManager
from core.group_manager import GroupManager
from core.position_manager import PositionManager
from core.trade_history_manager import TradeHistoryManager
from core.daily_loss_tracker import DailyLossTracker
from core.strategies.v4_auto_buy_strategy import V4AutoBuyStrategy
from core.strategies.expert_strategy import ExpertStrategy
from core.upbit_api import UpbitAPI, SymbolNotFoundError
from core.websocket_manager import WebSocketManager
from core.balance_polling_manager import BalancePollingManager

logger = logging.getLogger(__name__)


class V4TradingEngine:
    """
    V4 거래 엔진

    변경사항:
    - GroupManager 통합
    - 그룹별 독립 거래 루프
    - 전역 설정 적용 (관찰 모드, 최소 잔고, 일일 손실 한도)
    """

    def __init__(
        self,
        config_path: str = "config/trading_config.json",
        upbit_api: Optional[UpbitAPI] = None,
        position_manager: Optional['PositionManager'] = None
    ):
        """
        V4TradingEngine 초기화

        Args:
            config_path: 설정 파일 경로
            upbit_api: Upbit API 인스턴스 (None이면 dry-run 모드)
            position_manager: 외부 PositionManager (None이면 내부 생성)
        """
        logger.info("🚀 V4TradingEngine 초기화 시작")

        # 설정 로드
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()

        # 전역 설정
        self.global_settings = self.config.get("global_settings", {})
        self.observation_mode = self.global_settings.get("observation_mode", False)
        self.dry_run = self.global_settings.get("dry_run", False)

        # 모드 결정
        mode = "dryrun" if self.dry_run else "live"

        # 그룹 관리
        self.group_manager = GroupManager(config_path, mode=mode)

        # 포지션 관리 (외부 인스턴스 사용 또는 내부 생성)
        if position_manager:
            self.position_manager = position_manager
            logger.info("✅ 외부 PositionManager 사용 (recent_bot_sells 공유)")
        else:
            self.position_manager = PositionManager(mode=mode, upbit_api=upbit_api)

        # 거래 내역
        self.trade_history = TradeHistoryManager()

        # Upbit API
        self.upbit_api = upbit_api

        # 🔧 Pending Order Manager (재시작 시 주문 복구)
        self.pending_order_mgr = None
        if self.upbit_api and not self.dry_run:
            from core.pending_order_manager import PendingOrderManager
            self.pending_order_mgr = PendingOrderManager()
            logger.info("✅ PendingOrderManager 초기화 완료")

        # MyOrder WebSocket (주문 체결 실시간 감지)
        self.myorder_ws = None
        if self.upbit_api and not self.dry_run:
            try:
                from core.upbit_websocket import MyOrderWebSocket
                self.myorder_ws = MyOrderWebSocket(
                    access_key=self.upbit_api.access_key,
                    secret_key=self.upbit_api.secret_key
                )
                logger.info("✅ MyOrderWebSocket 인스턴스 생성 완료")
            except Exception as e:
                logger.warning(f"⚠️ MyOrderWebSocket 초기화 실패 (REST API 폴백): {e}")
                self.myorder_ws = None

        # 🆕 MyAsset WebSocket + Adaptive Polling (잔고 실시간 감지)
        self.myasset_ws = None
        self.balance_polling_manager = None
        if self.upbit_api and not self.dry_run:
            try:
                from core.upbit_websocket import MyAssetWebSocket

                # BalancePollingManager 초기화 (1초 폴링)
                self.balance_polling_manager = BalancePollingManager(
                    upbit_api=self.upbit_api,
                    position_manager=self.position_manager,
                    config=self.config,  # Bug #4 수정: config 전달
                    interval=1.0  # 1초 간격
                )
                logger.info("✅ BalancePollingManager 인스턴스 생성 완료")

                # MyAssetWebSocket 초기화
                self.myasset_ws = MyAssetWebSocket(
                    access_key=self.upbit_api.access_key,
                    secret_key=self.upbit_api.secret_key
                )
                logger.info("✅ MyAssetWebSocket 인스턴스 생성 완료")

            except Exception as e:
                logger.warning(f"⚠️ MyAssetWebSocket/Polling 초기화 실패 (동기화 제한): {e}")
                self.myasset_ws = None
                self.balance_polling_manager = None
        # 텔레그램 봇 초기화
        telegram_config = self.global_settings.get("telegram", {})
        if telegram_config.get("enabled", False):
            try:
                from core.telegram_bot import TelegramBot
                self.telegram_bot = TelegramBot(
                    token=telegram_config.get("token", ""),
                    chat_id=telegram_config.get("chat_id", "")
                )
                logger.info("✅ 텔레그램 봇 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ 텔레그램 봇 초기화 실패: {e}")
                self.telegram_bot = None
        else:
            logger.info("ℹ️ 텔레그램 알림 비활성화")
            self.telegram_bot = None

        # 일일 손실 추적 (deprecated - 포지션 손실 한도로 대체)
        daily_loss_config = self.global_settings.get("daily_loss_limit", {})
        if daily_loss_config.get("enabled", False):
            self.daily_loss_tracker = DailyLossTracker(
                config=daily_loss_config,
                get_valuation_fn=self._get_total_valuation,
                get_krw_balance_fn=self._get_krw_balance,
                send_alert_fn=self._send_telegram_alert,
                liquidate_fn=self._liquidate_all_positions
            )
        else:
            self.daily_loss_tracker = None

        # 포지션 손실 한도 (새로운 방식)
        self.position_loss_limit_config = self.global_settings.get("position_loss_limit", {})
        self.loss_limit_reached = False  # 손실 한도 도달 플래그
        self.loss_limit_reached_time = None  # 도달 시각

        # 그룹별 전략 캐시
        self.strategies: Dict[str, Dict[str, Any]] = {}  # {group_id: {symbol: strategy}} (V4AutoBuyStrategy or ExpertStrategy)

        # 초기 매수 주문 추적 (MyOrder WebSocket에서 포지션 생성용)
        self.pending_initial_buys: Dict[str, Dict[str, Any]] = {}  # {order_uuid: {symbol, group_id, buy_amount_krw, ...}}

        # 🆕 처리된 봇 주문 UUID 추적 (중복 수동 매수 감지 방지)
        self.processed_bot_order_uuids: set = set()

        # 🆕 Phase B-C: MyOrder 처리 완료 추적 (MyAsset 백업용)
        self._myorder_processed_symbols: Dict[str, datetime] = {}  # {symbol: timestamp}

        # 최대 포지션 경고 플래그 (로그 스팸 방지)
        self.max_position_warning_shown = False

        # 캔들 데이터 캐시
        self.candles_cache: Dict[str, Dict[str, Any]] = {}  # {symbol: {candle_unit: candles}}

        # 🔧 잔고 캐시 (Rate Limit 방지)
        # TTL 60초: 매수/매도 직전에만 호출되므로 긴 TTL 사용
        # (DailyLossTracker나 포지션 평가 시에도 사용)
        self.balance_cache: Dict[str, Any] = {
            "krw": 0.0,
            "last_updated": None,
            "ttl": 60.0  # 60초 TTL (최적화됨)
        }

        # 🔧 캔들 캐시 (봉 크기별 스마트 캐싱)
        # {symbol_interval: {"candles": DataFrame, "expire_time": datetime}}
        self.candle_cache: Dict[str, Dict[str, Any]] = {}

        # 🔧 스킵 리스트 (404 에러 발생한 코인)
        self.skipped_symbols: set = set()

        # 실행 상태
        self.is_running = False
        self.stop_event = threading.Event()

        # 🔧 GUI 콜백 (중복 알림 방지용)
        self.on_auto_sell_callback = None  # 자동 매도 실행 시 호출 (익절/손절/DCA 매도)
        self.on_position_created_callback = None  # 포지션 생성 시 호출 (GUI 새로고침용)

        # 스레드
        self.main_thread = None
        self.scheduler_thread = None

        # 🚀 WebSocket Manager (실시간 캔들 관리)
        self.websocket_manager = WebSocketManager(upbit_api=upbit_api)
        self.websocket_loop = None  # asyncio 이벤트 루프
        self.websocket_thread = None  # WebSocket 스레드

        logger.info(f"✅ V4TradingEngine 초기화 완료 (모드: {mode}, 관찰: {self.observation_mode})")

    def start(self):
        """거래 시작"""
        if self.is_running:
            logger.warning("⚠️ 이미 실행 중입니다")
            return

        self.is_running = True
        self.stop_event.clear()

        logger.info("=" * 60)
        logger.info("🚀 V4 거래 엔진 시작")
        logger.info("=" * 60)

        if self.observation_mode:
            logger.warning("⚠️ 관찰 전용 모드 - 실제 거래 없음")

        if self.dry_run:
            logger.info("🧪 Dry-run 모드 - 가상 거래")
        else:
            logger.info("💰 Live 모드 - 실거래")

        # 초기 동기화
        if self.upbit_api and not self.dry_run:
            logger.info("🔄 Upbit 계좌와 포지션 동기화 중...")
            try:
                # accounts 조회 후 캐싱하여 전달 (중복 API 호출 방지)
                accounts = self.upbit_api.get_accounts()

                # 디버깅: REST API 응답 (DEBUG 레벨)
                logger.debug(f"📊 REST API 응답: 총 {len(accounts)}개 자산")
                for acc in accounts:
                    currency = acc.get('currency')
                    balance = float(acc.get('balance', 0))
                    locked = float(acc.get('locked', 0))

                    if currency == 'KRW':
                        logger.debug(f"   💰 {currency}: balance={balance:,.0f}원, locked={locked:,.0f}원")
                    elif balance > 0 or locked > 0:
                        avg_buy_price = float(acc.get('avg_buy_price', 0))
                        logger.debug(f"   🪙 {currency}: balance={balance:.8f}, avg_price={avg_buy_price:,.0f}원 | {acc}")

                sync_result = self.position_manager.sync_with_upbit(
                    self.config,
                    accounts=accounts
                )
                logger.info(f"✅ 동기화 완료: {sync_result}")
            except Exception as e:
                logger.error(f"❌ 동기화 실패: {e}")

        # 🔧 Step 1: pending_order 복구 (재시작 시)
        if self.pending_order_mgr:
            logger.info("🔄 pending_order 복구 시작...")
            try:
                self._recover_pending_orders()
            except Exception as e:
                logger.error(f"❌ pending_order 복구 실패: {e}", exc_info=True)

        # 🔧 Step 2: 재시작 시 수동 매수 조용히 추가 (알림 없음)
        if self.upbit_api and not self.dry_run:
            logger.info("🔄 재시작 시 수동 매수 확인 중...")
            try:
                self._sync_external_positions_on_startup()
            except Exception as e:
                logger.error(f"❌ 재시작 시 수동 매수 동기화 실패: {e}", exc_info=True)

        # 🆕 Adaptive Polling 시작 (MyAsset WebSocket + REST API 폴링)
        if self.balance_polling_manager and self.myasset_ws:
            logger.info("🔄 Adaptive Polling 시스템 시작 중...")
            try:
                # 1. REST API Polling 시작 (초기 상태: NOT_RECEIVING)
                self.balance_polling_manager.start_polling()
                logger.info("🔴 상태: NOT_RECEIVING - REST API Polling 활성화 (1초 간격)")

                # 2. MyAsset WebSocket 연결 및 구독 (백그라운드 스레드로 실행, 메인 루프 블로킹 방지)
                def run_myasset_websocket():
                    try:
                        asyncio.run(self._start_myasset_websocket())
                    except Exception as e:
                        logger.error(f"❌ MyAsset WebSocket 실행 오류: {e}", exc_info=True)

                self.myasset_thread = threading.Thread(target=run_myasset_websocket, daemon=True)
                self.myasset_thread.start()
                logger.info("✅ MyAsset WebSocket 백그라운드 스레드 시작")

            except Exception as e:
                logger.error(f"❌ Adaptive Polling 시작 실패: {e}", exc_info=True)
                logger.warning("⚠️ REST API 폴링만 사용 (WebSocket 없이)")

        # 일일 손실 추적 초기화
        if self.daily_loss_tracker:
            self.daily_loss_tracker.check_and_reset()

        # 그룹별 전략 초기화
        self._initialize_strategies()

        # 🚀 WebSocket + CandleAggregator 초기화
        logger.info("🌐 WebSocket 시스템 초기화 중...")
        try:
            self._initialize_websockets()
            logger.info("✅ WebSocket 시스템 초기화 완료")
        except Exception as e:
            logger.error(f"❌ WebSocket 초기화 실패: {e}", exc_info=True)
            logger.warning("⚠️ REST API 폴백 모드로 계속 진행")

        # 스케줄러 스레드 시작 (09:00 리셋 등)
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()

        # 메인 거래 루프 스레드 시작
        self.main_thread = threading.Thread(target=self._run_trading_loop, daemon=True)
        self.main_thread.start()

        logger.info("✅ V4 거래 엔진 시작 완료")

        # 텔레그램 시작 알림
        mode_text = "Live (실거래)" if not self.dry_run else "Dry-run (가상)"

        self._send_telegram_alert(
            f"🚀 프로그램 시작\n"
            f"모드: {mode_text}\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def stop(self):
        """거래 중지"""
        if not self.is_running:
            logger.warning("⚠️ 이미 중지되어 있습니다")
            return

        logger.info("🛑 V4 거래 엔진 중지 중...")
        self.is_running = False
        self.stop_event.set()

        # 🆕 Adaptive Polling 종료
        if self.balance_polling_manager:
            logger.info("🛑 REST API Polling 중지 중...")
            try:
                self.balance_polling_manager.stop_polling()
                logger.info("✅ REST API Polling 중지 완료")
            except Exception as e:
                logger.error(f"❌ Polling 중지 실패: {e}")

        if self.myasset_ws:
            logger.info("🔌 MyAsset WebSocket 연결 종료 중...")
            try:
                asyncio.run(self.myasset_ws.disconnect())
                logger.info("✅ MyAsset WebSocket 연결 종료 완료")
            except Exception as e:
                logger.error(f"❌ MyAsset WebSocket 종료 실패: {e}")

        # 🚀 WebSocket 종료
        if self.websocket_manager and self.websocket_manager.is_running:
            logger.info("🌐 WebSocket 연결 종료 중...")
            try:
                # 기존 이벤트 루프가 있는지 확인
                try:
                    loop = asyncio.get_running_loop()
                    # 이미 실행 중인 루프가 있으면 태스크 생성
                    loop.create_task(self.websocket_manager.stop_all())
                    logger.info("✅ WebSocket 종료 태스크 생성 완료")
                except RuntimeError:
                    # 실행 중인 루프가 없으면 새로 실행
                    asyncio.run(self.websocket_manager.stop_all())
                    logger.info("✅ WebSocket 연결 종료 완료")
            except Exception as e:
                logger.error(f"❌ WebSocket 종료 실패: {e}")

        # 스레드 종료 대기
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5)

        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        logger.info("✅ V4 거래 엔진 중지 완료")

        # 텔레그램 종료 알림
        self._send_telegram_alert(
            f"🛑 프로그램 종료\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def reload_config_and_update_groups(self):
        """
        설정 변경 시 config 리로드 및 그룹 업데이트

        MainWindow의 groups_changed Signal에서 호출됨
        API 호출 없이 메모리 기반 업데이트만 수행
        Bug #5 수정: 재시작 없이 설정 변경 즉시 반영
        """
        logger.info("🔄 Config 리로드 중...")

        try:
            # 1. Config 파일 다시 로드
            self.config = self.config_manager.load_config()
            logger.info("   📄 Config 파일 로드 완료")

            # 1-1. GroupManager의 ConfigManager도 리로드 (Bug 수정: DCA 설정 실시간 반영)
            self.group_manager.config_manager.config = None  # 캐시 무효화
            self.group_manager.config = self.group_manager.config_manager.load_config()
            logger.info("   📄 GroupManager config 리로드 완료")

            # 2. 포지션 그룹 업데이트 (API 호출 없음)
            updated_count = self.position_manager.update_position_groups_from_config(self.config)
            logger.info(f"   📊 포지션 그룹 업데이트 완료 ({updated_count}개 변경)")

            # 3. BalancePollingManager 업데이트
            if hasattr(self, 'balance_polling_manager') and self.balance_polling_manager:
                self.balance_polling_manager.update_config(self.config)
                logger.info("   🔄 BalancePollingManager config 업데이트 완료")

            logger.info("✅ Config 리로드 완료 (재시작 불필요)")

            # 4. Telegram 알림
            if self.telegram_bot:
                self.telegram_bot.send_message(
                    "✅ 설정 변경 적용 완료\n"
                    f"그룹 설정이 즉시 반영되었습니다.\n"
                    f"업데이트: {updated_count}개 포지션"
                )

        except Exception as e:
            logger.error(f"❌ Config 리로드 실패: {e}", exc_info=True)
            if self.telegram_bot:
                self.telegram_bot.send_message(
                    f"⚠️ 설정 변경 적용 실패\n"
                    f"오류: {e}\n"
                    f"프로그램을 재시작해주세요."
                )

    def _initialize_strategies(self):
        """그룹별 전략 초기화"""
        logger.info("📊 그룹별 전략 초기화 중...")

        all_groups = self.group_manager.get_all_groups()

        for group_id, group in all_groups.items():
            # 그룹별 전략 딕셔너리 생성
            self.strategies[group_id] = {}

            # 자동 매수 모드가 아니면 스킵
            buy_settings = group.get("buy_settings", {})
            if buy_settings.get("mode") != "auto":
                logger.info(f"  - {group['name']}: 수동 모드, 전략 없음")
                continue

            auto_config = buy_settings.get("auto_config", {})
            strategy_type = auto_config.get("strategy", "v4_auto_buy")  # 기본값: v4_auto_buy (하위 호환성)

            # 그룹의 각 코인에 대한 전략 생성
            for symbol in group.get("coins", []):
                try:
                    if strategy_type == "expert":
                        # ExpertStrategy 사용
                        expert_profile = auto_config.get("expert_profile", "balanced_expert")
                        candle_unit = auto_config.get("candle_unit", "10")
                        custom_weights = auto_config.get("custom_weights")
                        custom_threshold = auto_config.get("custom_threshold")

                        strategy = ExpertStrategy(
                            symbol=symbol,
                            expert_profile=expert_profile,
                            candle_unit=candle_unit,
                            custom_weights=custom_weights,
                            custom_threshold=custom_threshold
                        )

                        profile_info = f"Profile: {expert_profile}"
                        if expert_profile == "custom":
                            profile_info = f"Custom (Threshold: {custom_threshold}%)"

                        logger.info(
                            f"  - {group['name']}: {symbol} ExpertStrategy 생성 완료 "
                            f"({profile_info}, Candle: {candle_unit}min)"
                        )

                    else:
                        # V4AutoBuyStrategy 사용 (기본값)
                        investment_style = auto_config.get("investment_style", "balanced")
                        candle_unit = auto_config.get("candle_unit", "60")
                        indicators_config = auto_config.get("indicators", {})
                        signal_mode = auto_config.get("signal_mode", "all")
                        min_signals_required = auto_config.get("min_signals_required", None)

                        strategy = V4AutoBuyStrategy(
                            symbol=symbol,
                            investment_style=investment_style,
                            candle_unit=candle_unit,
                            indicators_config=indicators_config,
                            signal_mode=signal_mode,
                            min_signals_required=min_signals_required
                        )

                        # 신호 모드 정보 추가
                        signal_info = f"신호: {signal_mode}"
                        if signal_mode == "partial" and min_signals_required:
                            signal_info += f" (최소 {min_signals_required}개)"

                        logger.info(
                            f"  - {group['name']}: {symbol} V4AutoBuyStrategy 생성 완료 "
                            f"(Style: {investment_style}, Candle: {candle_unit}min, {signal_info})"
                        )

                    self.strategies[group_id][symbol] = strategy

                except Exception as e:
                    logger.error(f"❌ {symbol} 전략 생성 실패: {e}", exc_info=True)

        logger.info(f"✅ 총 {sum(len(s) for s in self.strategies.values())}개 전략 초기화 완료")

    async def _initialize_websockets_async(self):
        """WebSocket 및 CandleAggregator 초기화 (asyncio)"""
        logger.info("🌐 WebSocket 및 CandleAggregator 초기화 중...")

        all_groups = self.group_manager.get_all_groups()
        total_added = 0

        for group_id, group in all_groups.items():
            buy_settings = group.get("buy_settings", {})
            buy_mode = buy_settings.get("mode", "auto")

            # disabled 모드는 스킵
            if buy_mode == "disabled":
                logger.info(f"  - {group['name']}: disabled 모드, WebSocket 스킵")
                continue

            # candle_unit 결정
            if buy_mode == "auto":
                # Auto 모드: auto_config에서 가져옴
                auto_config = buy_settings.get("auto_config", {})
                candle_unit = int(auto_config.get("candle_unit", "60"))
            else:
                # Manual 모드: 기본값 60분 (DCA/익절/손절 판단용)
                candle_unit = 60
                logger.info(f"  - {group['name']}: manual 모드, candle_unit=60 (DCA/익절/손절용)")

            # 그룹의 각 코인에 대한 WebSocket + CandleAggregator 생성
            for symbol in group.get("coins", []):
                try:
                    # WebSocket + CandleAggregator 추가
                    # (내부에서 REST API로 과거 캔들 199개 로드)
                    await self.websocket_manager.add_symbol(
                        symbol=symbol,
                        candle_unit=candle_unit,
                        completed_candles=None  # REST API로 자동 로드
                    )
                    total_added += 1
                    logger.info(f"  - {group['name']}: {symbol} WebSocket 추가 완료 (mode={buy_mode}, candle={candle_unit}min)")

                    # Rate Limit 준수: candle 그룹 초당 10회 제한
                    # 0.11초 대기 (초당 최대 9.09회 = 안전)
                    await asyncio.sleep(0.11)

                except Exception as e:
                    logger.error(f"❌ {symbol} WebSocket 추가 실패: {e}")

        logger.info(f"✅ 총 {total_added}개 코인 WebSocket 초기화 완료")

        # 모든 WebSocket 연결 시작
        logger.info("🚀 WebSocket 연결 시작 중...")
        await self.websocket_manager.start_all()

        # MyOrderWebSocket 연결 (Live 모드에서만)
        if self.myorder_ws:
            logger.info("📋 MyOrder WebSocket 연결 중...")
            try:
                connected = await self.myorder_ws.connect()
                if connected:
                    await self.myorder_ws.subscribe_myorder()  # 전체 마켓 구독

                    # 🆕 기본 콜백 설정 (수동 매수 감지용)
                    self.myorder_ws.set_default_callback(self._on_order_completed)

                    logger.info("✅ MyOrder WebSocket 연결 및 구독 완료 (수동 매수 감지 활성화)")
                else:
                    logger.warning("⚠️ MyOrder WebSocket 연결 실패 (REST API 폴백)")
                    self.myorder_ws = None
            except Exception as e:
                logger.error(f"❌ MyOrder WebSocket 초기화 실패: {e}")
                self.myorder_ws = None

    async def _start_myasset_websocket(self):
        """
        MyAsset WebSocket 연결 및 메시지 수신 시작

        Adaptive Polling 전략:
        - 첫 메시지 수신 시 REST API Polling 중지
        - 연결 끊김 시 REST API Polling 재시작
        """
        try:
            logger.info("🔌 MyAsset WebSocket 연결 시도...")
            await self.myasset_ws.connect()
            logger.info("✅ MyAsset WebSocket 연결 성공")

            # MyAsset 구독
            await self.myasset_ws.subscribe_myasset()
            logger.info("💰 MyAsset 구독 완료 - 잔고 변동 실시간 감지 시작")

            first_message_received = False

            # 메시지 수신 루프
            listener = self.myasset_ws.listen()
            try:
                async for data in listener:
                    if not self.is_running:
                        break

                    # 첫 메시지 수신 시 Polling 중지
                    if not first_message_received:
                        first_message_received = True
                        if self.balance_polling_manager:
                            self.balance_polling_manager.stop_polling()
                        logger.info("🟢 상태: RECEIVING - MyAsset WebSocket 정상 수신 확인, REST API Polling 비활성화")

                    # 메시지 처리
                    await self._process_myasset_data(data)

            finally:
                await listener.aclose()

        except Exception as e:
            logger.error(f"❌ MyAsset WebSocket 실행 오류: {e}", exc_info=True)

            # 연결 끊김 시 Polling 재시작
            if first_message_received and self.balance_polling_manager:
                self.balance_polling_manager.start_polling()
                logger.warning("🟠 상태: DISCONNECTED - 연결 끊김으로 인해 REST API Polling 재활성화")

        finally:
            if self.myasset_ws:
                await self.myasset_ws.disconnect()
            logger.info("🔌 MyAsset WebSocket 연결 종료")

    async def _process_myasset_data(self, data: dict):
        """
        MyAsset 데이터 처리 및 새 자산 감지

        Args:
            data: WebSocket에서 수신한 데이터
        """
        try:
            if data.get('type') != 'myAsset':
                return

            assets = data.get('assets', [])
            if not assets:
                return

            logger.debug(f"💰 MyAsset 메시지 수신: {len(assets)}개 자산")

            # 새 자산 감지 및 group_null 포지션 생성
            for asset in assets:
                currency = asset.get('currency')

                # KRW는 제외
                if currency == 'KRW':
                    continue

                balance = float(asset.get('balance', 0))
                locked = float(asset.get('locked', 0))
                total = balance + locked

                # 잔고가 0이면 스킵
                if total <= 0:
                    continue

                symbol = f"KRW-{currency}"

                # 포지션 확인
                position = self.position_manager.get_position_by_symbol(symbol)

                if not position:
                    # 🆕 봇 주문인지 확인 (pending_initial_buys)
                    is_bot_order = any(
                        pending_data.get('symbol') == symbol
                        for pending_data in self.pending_initial_buys.values()
                    )

                    if is_bot_order:
                        # 봇 주문 → MyOrder WebSocket이 처리할 예정
                        logger.debug(f"⏭️ {symbol} 봇 주문 진행 중 (MyOrder WebSocket에서 처리 예정, MyAsset 스킵)")
                        continue

                    # 🔧 Phase C: MyOrder가 이미 처리했는지 확인 (5초 윈도우)
                    if self._was_recently_processed_by_myorder(symbol):
                        logger.debug(f"   ⏭️ {symbol} MyOrder에서 최근 처리됨 (5초 이내), MyAsset 스킵")
                        continue

                    # MyOrder가 누락했을 가능성 → 백업 처리
                    logger.warning(f"   ⚠️ {symbol} MyOrder 누락 감지, MyAsset 백업 처리")

                    # 수동 매수 감지 (Upbit 앱/웹에서 직접 매수)
                    logger.info(f"🆕 수동 매수 감지 (Upbit 앱/웹): {symbol}")

                    # avg_buy_price 조회 (WebSocket에 없으므로 REST API 사용)
                    # 최대 6번 재시도 (0.5초 간격, 총 3초) - position_manager와 동일한 로직
                    avg_buy_price = 0.0
                    if self.upbit_api:
                        for retry in range(6):
                            try:
                                accounts = self.upbit_api.get_accounts()
                                for acc in accounts:
                                    if acc['currency'] == currency:
                                        avg_buy_price = float(acc.get('avg_buy_price', 0))
                                        if avg_buy_price > 0:
                                            logger.info(f"   - REST API 평균가 조회: {symbol} = {avg_buy_price:,.0f}원 (재시도 {retry+1}회)")
                                            break

                                if avg_buy_price > 0:
                                    break  # 성공하면 루프 종료

                                if retry < 5:  # 마지막 시도가 아니면
                                    time.sleep(0.5)  # 0.5초 대기 후 재시도
                                    logger.debug(f"   🔄 {symbol} 평균가 재조회 대기 중... ({retry+1}/6)")

                            except Exception as e:
                                if retry == 5:  # 마지막 시도에서만 에러 로그
                                    logger.error(f"❌ avg_buy_price 조회 실패 ({symbol}): {e}")

                    # avg_buy_price > 0인 경우에만 포지션 생성
                    if avg_buy_price > 0:
                        try:
                            self.position_manager.create_position(
                                group_id="group_null",
                                symbol=symbol,
                                buy_price=avg_buy_price,
                                quantity=total,
                                force_create_for_sync=True
                            )
                            # GUI 로그만 (텔레그램 알림 없음 - group_null은 DCA/익절/손절 미작동)
                            total_krw = avg_buy_price * total
                            logger.info(f"[수동매수] 신규: {symbol} | {total_krw:,.0f}원 | {total:.8f}개 | group_null")

                            # BalancePollingManager의 known_symbols에도 추가
                            if self.balance_polling_manager:
                                self.balance_polling_manager.add_known_symbol(symbol)

                        except Exception as e:
                            logger.error(f"❌ 포지션 생성 실패 ({symbol}): {e}", exc_info=True)
                    else:
                        logger.warning(f"⚠️ {symbol} avg_buy_price가 0이라 포지션 생성 생략")

        except Exception as e:
            logger.error(f"❌ MyAsset 데이터 처리 오류: {e}", exc_info=True)

    def _initialize_websockets(self):
        """WebSocket 초기화 (동기 래퍼)"""
        asyncio.run(self._initialize_websockets_async())

    def _run_trading_loop(self):
        """메인 거래 루프 (1초마다 실시간 체크)"""
        logger.info("🔄 메인 거래 루프 시작 (1초 간격 실시간 체크)")

        check_interval = 1  # 🚀 1초마다 실시간 체크 (기존: 60초)
        loop_count = 0  # 루프 카운터
        verbose_interval = 60  # 60회마다 상세 로그 출력 (60초마다)

        while not self.stop_event.is_set():
            try:
                loop_count += 1

                # 상세 로그는 60회(60초)마다만 출력
                verbose = (loop_count % verbose_interval == 1)

                if verbose:
                    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logger.info(f"🔄 [{loop_count}회차] 거래 체크 시작 (1초 간격)")
                    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                # 일일 손실 한도 체크 및 리셋 (1초마다)
                if self.daily_loss_tracker:
                    self.daily_loss_tracker.check_and_reset()

                # 모든 그룹 순회
                all_groups = self.group_manager.get_all_groups()

                if verbose:
                    logger.info(f"📊 전체 그룹 개수: {len(all_groups)}개")

                for group_id, group in all_groups.items():
                    group_name = group.get("name", group_id)
                    coins = group.get("coins", [])
                    observation_only = group.get("observation_only", False)
                    buy_mode = group.get("buy_settings", {}).get("mode", "manual")

                    if verbose:
                        logger.info(f"")
                        logger.info(f"📌 그룹: {group_name} (ID: {group_id})")
                        logger.info(f"   - 코인 개수: {len(coins)}개")
                        logger.info(f"   - 관찰 전용: {observation_only}")
                        logger.info(f"   - 매수 모드: {buy_mode}")
                        logger.info(f"   - 코인 목록: {coins}")

                    # 관찰 전용 그룹 스킵
                    if observation_only:
                        if verbose:
                            logger.info(f"   ⏭️ 관찰 전용 그룹 스킵")
                        continue

                    # 그룹의 각 코인 처리 (1초마다 체크)
                    for symbol in coins:
                        try:
                            # 상세 로그는 verbose 모드에서만
                            if verbose:
                                logger.info(f"   🔍 {symbol} 처리 시작...")
                            self._process_symbol(symbol, group_id, group, verbose=verbose)
                        except Exception as e:
                            logger.error(f"❌ {symbol} 처리 오류: {e}", exc_info=True)

                if verbose:
                    logger.info(f"")
                    logger.info(f"✅ [{loop_count}회차] 거래 체크 완료, {check_interval}초 대기...")
                    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                # 대기
                self.stop_event.wait(check_interval)

            except Exception as e:
                logger.error(f"❌ 거래 루프 오류: {e}", exc_info=True)
                self.stop_event.wait(10)  # 에러 시 10초 대기

        logger.info("🛑 메인 거래 루프 종료")

    def _process_symbol(self, symbol: str, group_id: str, group: Dict[str, Any], verbose: bool = False):
        """
        코인 처리 (매수 신호 확인, 포지션 관리)

        Args:
            symbol: 코인 심볼 (예: KRW-BTC)
            group_id: 그룹 ID
            group: 그룹 데이터
            verbose: 상세 로그 출력 여부
        """
        # 0. 스킵 리스트 체크 (404 에러 발생한 코인)
        if symbol in self.skipped_symbols:
            if verbose:
                logger.info(f"      ⏭️ {symbol}: 스킵됨 (상장폐지 또는 404 에러)")
            return

        # 1. 포지션 확인 (활성 포지션만 체크)
        position = self.position_manager.get_position(symbol)
        has_active_position = position and position.get('status') == 'active'
        if verbose:
            logger.info(f"      📊 {symbol}: 활성 포지션 존재 = {has_active_position}")

        # 1-A. pending 초기 매수 확인 (중복 매수 방지)
        has_pending_buy = any(
            pending['symbol'] == symbol
            for pending in self.pending_initial_buys.values()
        )
        if verbose:
            logger.info(f"      📊 {symbol}: pending 초기 매수 = {has_pending_buy}")

        # 2-A. 신규 매수 (활성 포지션이 없고 pending도 없는 경우) - 전역 제약 체크 필요
        if not has_active_position and not has_pending_buy and group.get("buy_settings", {}).get("mode") == "auto":
            # 전역 제약 확인 (신규 매수 시에만)
            constraints_ok = self._check_global_constraints(verbose=verbose)
            if verbose:
                logger.info(f"      🔧 {symbol}: 전역 제약 체크 = {constraints_ok}")
            if not constraints_ok:
                if verbose:
                    logger.info(f"      ⏭️ {symbol}: 전역 제약 실패로 신규 매수 스킵")
                return

            if verbose:
                logger.info(f"      🎯 {symbol}: 매수 신호 체크 시작")
            self._check_buy_signal(symbol, group_id, group, verbose=verbose)

        # 2-B. 포지션 관리 (DCA, 익절, 손절) - 전역 제약 무관
        elif has_active_position:
            if verbose:
                logger.info(f"      🎯 {symbol}: 포지션 관리 시작 (DCA/익절/손절)")
            self._manage_position(symbol, group_id, group)

        # 2-C. pending 초기 매수 대기 중 (중복 매수 방지)
        elif not has_active_position and has_pending_buy:
            if verbose:
                logger.info(f"      ⏭️ {symbol}: pending 초기 매수 대기 중 (중복 매수 방지)")

        else:
            if verbose:
                buy_mode = group.get("buy_settings", {}).get("mode", "unknown")
                logger.info(f"      ⏭️ {symbol}: 매수 신호 체크 스킵 (mode={buy_mode})")

    def _check_buy_signal(self, symbol: str, group_id: str, group: Dict[str, Any], verbose: bool = False):
        """
        매수 신호 확인

        Args:
            symbol: 코인 심볼
            group_id: 그룹 ID
            group: 그룹 데이터
            verbose: 상세 로그 출력 여부
        """
        # 🔴 그룹 관찰 모드 체크 (최우선)
        # 관찰 모드 그룹은 자동 매수를 하지 않음
        if group.get("observation_only", False):
            if verbose:
                logger.debug(f"   👁️ {symbol}: 그룹 관찰 모드 (매수 신호 체크 스킵)")
            return

        # 전략 가져오기
        if verbose:
            logger.info(f"         🔍 전략 검색: group_id={group_id}, symbol={symbol}")
            logger.info(f"         🔍 self.strategies.keys() = {list(self.strategies.keys())}")

        strategy = self.strategies.get(group_id, {}).get(symbol)
        if verbose:
            logger.info(f"         🔍 전략 찾기 결과: {strategy is not None}")

        if not strategy:
            if verbose:
                logger.info(f"         ❌ {symbol}: 전략 없음 (그룹: {group_id})")
            return

        # 캔들 데이터 가져오기
        auto_config = group.get("buy_settings", {}).get("auto_config", {})
        candle_unit = auto_config.get("candle_unit", "60")
        if verbose:
            logger.info(f"         🔍 캔들 단위: {candle_unit}분")

        if verbose:
            logger.info(f"         📊 {symbol}: 캔들 조회 시작 (단위: {candle_unit}분, 개수: 200개)")
        candles = self._get_recent_candles(symbol, candle_unit, count=200)
        candle_count = len(candles) if candles is not None else 0
        if verbose:
            logger.info(f"         📊 {symbol}: 캔들 조회 완료 (조회됨: {candle_count}개)")

        if candles is None or len(candles) < 50:
            logger.warning(f"⚠️ {symbol}: 캔들 데이터 부족 (필요: 50개, 현재: {candle_count}개)")
            return

        # 매수 신호 확인
        try:
            if verbose:
                logger.info(f"         🔍 {symbol}: should_buy() 호출 시작...")
            buy_signal = strategy.should_buy(candles)
            if verbose:
                logger.info(f"         🔍 {symbol}: should_buy() 결과 = {buy_signal}")

            if buy_signal:
                # 매수 신호는 항상 로깅 (중요 이벤트)
                logger.info(f"🔔 [자동매수] {symbol}: 매수 신호 발생!")

                # 지표 값 출력
                indicators = strategy.get_indicator_values(candles)
                logger.info(f"   지표 값: {indicators}")

                # 매수 실행
                self._execute_buy(symbol, group_id, group)
            else:
                if verbose:
                    logger.info(f"         ⏭️ {symbol}: 매수 조건 미충족 (신호 없음)")
        except Exception as e:
            logger.error(f"❌ {symbol} 매수 신호 확인 오류: {e}", exc_info=True)

    def _execute_buy(self, symbol: str, group_id: str, group: Dict[str, Any]):
        """
        매수 실행

        Args:
            symbol: 코인 심볼
            group_id: 그룹 ID
            group: 그룹 데이터
        """
        if self.observation_mode:
            logger.info(f"[관찰] {symbol} 매수 신호 (실행 안 함)")
            return

        auto_config = group.get("buy_settings", {}).get("auto_config", {})
        buy_amount = auto_config.get("buy_amount_krw", 50000)

        # 잔고 체크 (매수 직전에만 REST API 호출)
        if not self._check_min_balance(buy_amount):
            logger.warning(f"⚠️ {symbol} 매수 취소: 잔고 부족")
            return

        logger.info(f"💰 [자동매수] {symbol} 매수 실행 중... (금액: {buy_amount:,}원)")

        try:
            if self.dry_run or not self.upbit_api:
                # Dry-run 모드: 가상 주문
                current_price = self._get_current_price_safe(symbol)
                if not current_price:
                    logger.error(f"❌ {symbol} 현재가 조회 실패")
                    return

                buy_quantity = buy_amount / current_price

                # 포지션 생성
                position = self.position_manager.create_position(
                    group_id=group_id,
                    symbol=symbol,
                    buy_price=current_price,
                    quantity=buy_quantity,
                    buy_amount_krw=buy_amount
                )

                logger.info(f"✅ [Dry-run] {symbol} 매수 완료: {buy_quantity:.8f}개 @ {current_price:,}원")

            else:
                # Live 모드: 실제 주문
                order_result = self.upbit_api.buy_market_order(symbol, buy_amount)

                if not order_result or 'error' in order_result:
                    logger.error(f"❌ {symbol} 매수 실패: {order_result}")
                    return

                order_uuid = order_result.get('uuid')
                if not order_uuid:
                    logger.error(f"❌ {symbol} 주문 UUID 없음: {order_result}")
                    return

                # 초기 매수 주문 추적 (MyOrder WebSocket에서 체결 완료 시 포지션 생성)
                self.pending_initial_buys[order_uuid] = {
                    'symbol': symbol,
                    'group_id': group_id,
                    'group_name': group.get('name', 'Unknown'),
                    'buy_amount_krw': buy_amount
                }

                # 🔧 Phase D: MyOrder WebSocket 콜백 등록 (DCA/익절/손절과 동일)
                if self.myorder_ws:
                    self.myorder_ws.register_order_callback(order_uuid, self._on_order_completed)
                    logger.info(f"   📡 [자동매수] {symbol} 주문 {order_uuid[:8]}... MyOrder WebSocket 콜백 등록 완료")
                else:
                    logger.warning(f"   ⚠️ [자동매수] {symbol} MyOrderWebSocket 없음 (콜백 등록 불가)")

                logger.info(f"✅ [자동매수] {symbol} 매수 주문 접수 완료: {order_uuid[:8]}... (MyOrder WebSocket에서 체결 대기 중)")
                return  # 포지션은 MyOrder WebSocket에서 생성

            # Dry-run 모드에만 거래 기록 및 알림
            # Live 모드는 MyOrder WebSocket에서 처리
            self.trade_history.add_trade(
                group_id=group_id,
                group_name=group.get("name", "Unknown"),
                symbol=symbol,
                action="buy",
                trade_type="initial",
                price=position.get("avg_buy_price"),
                amount=position.get("total_amount"),
                total_krw=buy_amount,
                dry_run=True
            )

            # 텔레그램 알림
            self._send_telegram_alert(
                f"✅ [Dry-run] 매수 완료\n"
                f"그룹: {group.get('name')}\n"
                f"코인: {symbol}\n"
                f"금액: {buy_amount:,}원\n"
                f"수량: {position.get('total_amount'):.8f}개\n"
                f"가격: {position.get('avg_buy_price'):,}원"
            )

        except Exception as e:
            logger.error(f"❌ {symbol} 매수 실행 오류: {e}", exc_info=True)

    def _manage_position(self, symbol: str, group_id: str, group: Dict[str, Any]):
        """
        포지션 관리 (DCA, 익절, 손절)

        Args:
            symbol: 코인 심볼
            group_id: 그룹 ID
            group: 그룹 데이터
        """
        # 🔴 그룹 관찰 모드 체크 (최우선)
        # 관찰 모드 그룹은 프로그램에서 아무 동작도 하지 않음
        if group.get("observation_only", False):
            logger.debug(f"   👁️ {symbol}: 그룹 관찰 모드 (포지션 관리 스킵)")
            return

        position = self.position_manager.get_position(symbol)
        if not position or position.get("status") != "active":
            return

        # 현재가 조회
        current_price = self._get_current_price_safe(symbol)
        if not current_price:
            return

        # 수익률 계산
        avg_buy_price = position.get("avg_buy_price", 0)
        if avg_buy_price == 0:
            return

        profit_pct = ((current_price - avg_buy_price) / avg_buy_price) * 100

        # DCA 체크
        self._check_dca(symbol, group_id, group, position, current_price, profit_pct)

        # 익절 체크
        self._check_profit_target(symbol, group_id, group, position, current_price, profit_pct)

        # 손절 체크
        self._check_stop_loss(symbol, group_id, group, position, current_price, profit_pct)

    def _check_dca(
        self,
        symbol: str,
        group_id: str,
        group: Dict[str, Any],
        position: Dict[str, Any],
        current_price: float,
        profit_pct: float
    ):
        """DCA 체크 및 실행 (체결 확인)"""
        dca_settings = group.get("dca_settings", {})

        if dca_settings.get("mode") != "auto":
            return

        # pending_order 체크 및 Timeout 확인 (Bug #2 수정)
        pending_order = position.get("pending_order")
        if pending_order:
            timestamp_str = pending_order.get('timestamp')

            if timestamp_str:
                try:
                    from datetime import datetime
                    timestamp = datetime.fromisoformat(timestamp_str)
                    elapsed = (datetime.now() - timestamp).total_seconds()

                    # 5분(300초) 이상 대기 중이면 자동 제거
                    if elapsed > 300:
                        logger.warning(
                            f"⚠️ {symbol} pending_order timeout "
                            f"(경과: {elapsed:.0f}초, 타입: {pending_order.get('type')}, "
                            f"레벨: {pending_order.get('level')}) → 제거 및 재시도"
                        )
                        self.position_manager.update_position(symbol, {
                            "pending_order": None
                        })

                        # Telegram 알림
                        if self.telegram_bot:
                            self.telegram_bot.send_message(
                                f"⚠️ pending_order Timeout\n"
                                f"코인: {symbol}\n"
                                f"타입: {pending_order.get('type')}\n"
                                f"레벨: {pending_order.get('level')}\n"
                                f"경과 시간: {elapsed:.0f}초\n"
                                f"자동 제거 후 재시도합니다."
                            )

                        # Timeout 후 계속 진행 (재시도)
                    else:
                        # 정상 대기 중
                        logger.debug(
                            f"   ⏳ {symbol}: DCA 스킵 "
                            f"(진행 중인 주문: {pending_order.get('type')} 레벨 {pending_order.get('level')}, "
                            f"경과: {elapsed:.0f}초)"
                        )
                        return  # 스킵

                except (ValueError, TypeError) as e:
                    # timestamp parsing 실패
                    logger.error(f"⚠️ {symbol} pending_order timestamp 파싱 실패: {e}")
                    # timestamp가 잘못되었으면 제거
                    self.position_manager.update_position(symbol, {
                        "pending_order": None
                    })
                    # 계속 진행 (재시도)
            else:
                # timestamp 없음 (오래된 데이터)
                logger.warning(f"⚠️ {symbol} pending_order에 timestamp 없음 → 제거")
                self.position_manager.update_position(symbol, {
                    "pending_order": None
                })
                # 계속 진행 (재시도)

        dca_levels = dca_settings.get("levels", [])
        dca_count = position.get("dca_count", 0)
        dca_levels_executed = position.get("dca_levels_executed", [])

        # 모든 DCA 레벨 소진
        if dca_count >= len(dca_levels):
            return

        # 다음 DCA 레벨 확인
        for i, level in enumerate(dca_levels):
            # 🔧 Phase D: dca_levels_executed 배열 체크로 변경 (익절/손절과 동일 패턴)
            if i in dca_levels_executed:
                continue  # 이미 실행된 레벨

            price_ratio = level.get("price_ratio", -5.0)

            if profit_pct <= price_ratio:
                logger.info(f"🔔 {symbol}: DCA 레벨 {i+1} 트리거 (현재: {profit_pct:.2f}%, 기준: {price_ratio:.2f}%)")
                self._execute_dca(symbol, group_id, group, position, level, i)
                break  # 한 번에 하나의 DCA만 실행

    def _execute_dca(
        self,
        symbol: str,
        group_id: str,
        group: Dict[str, Any],
        position: Dict[str, Any],
        level: Dict[str, Any],
        dca_level_index: int  # 0-based index
    ):
        """DCA 매수 실행 (주문 체결 확인 포함)"""
        dca_level_num = dca_level_index + 1  # 1-based for display

        if self.observation_mode:
            logger.info(f"[관찰] {symbol} DCA 레벨 {dca_level_num} (실행 안 함)")
            return

        # DCA 금액 계산: 현재 총 투자 금액 대비 비율
        total_invested = position.get("total_invested_krw", 50000)
        quantity_ratio = level.get("quantity_ratio", 100) / 100.0  # 100 = 1.0배 (100%)
        quantity_ratio = min(quantity_ratio, 1.0)  # 최대 100% 제한
        dca_amount = int(total_invested * quantity_ratio)

        # 잔고 체크 (DCA 직전에만 REST API 호출)
        if not self._check_min_balance(dca_amount):
            logger.warning(f"⚠️ {symbol} DCA 레벨 {dca_level_num} 취소: 잔고 부족")

            # pending_order 설정 (5분간 재시도 방지)
            from datetime import datetime
            self.position_manager.update_position(symbol, {
                "pending_order": {
                    "type": "dca_failed",
                    "level": dca_level_index,
                    "timestamp": datetime.now().isoformat(),
                    "reason": "insufficient_balance"
                }
            })
            return

        logger.info(f"💰 {symbol} DCA 레벨 {dca_level_num} 실행 중... (금액: {dca_amount:,}원, 비율: {quantity_ratio * 100:.0f}% of {total_invested:,}원)")

        try:
            if self.dry_run or not self.upbit_api:
                # Dry-run 모드: 즉시 실행 (체결 확인 불필요)
                current_price = self._get_current_price_safe(symbol)
                if not current_price:
                    logger.error(f"❌ {symbol} 현재가 조회 실패")
                    return

                dca_quantity = dca_amount / current_price

                # 포지션 DCA 추가 (즉시)
                self.position_manager.add_dca(
                    symbol=symbol,
                    dca_price=current_price,
                    dca_amount=dca_quantity,
                    dca_krw=dca_amount,  # 파라미터명 수정 (dca_value_krw → dca_krw)
                    level=dca_level_index  # DCA 레벨 추가 (Bug #3 수정)
                )

                logger.info(f"✅ [Dry-run] {symbol} DCA 완료: {dca_quantity:.8f}개 @ {current_price:,}원")

                # 거래 기록 (Dry-run)
                position = self.position_manager.get_position(symbol)
                self.trade_history.add_trade(
                    group_id=group_id,
                    group_name=group.get("name", "Unknown"),
                    symbol=symbol,
                    action="buy",
                    trade_type="dca",
                    price=position.get("avg_buy_price"),
                    amount=position.get("total_amount"),
                    total_krw=dca_amount,
                    dry_run=self.dry_run,
                    dca_level=dca_level_num  # 추가 정보
                )

            else:
                # Live 모드: pending_order 먼저 저장 → 주문 → 콜백 등록
                from datetime import datetime

                # 0. 주문 전 현재가 조회 (시장가 주문 예상가)
                current_price = self._get_current_price_safe(symbol)
                if not current_price:
                    logger.error(f"❌ {symbol} 현재가 조회 실패")
                    return

                # 1. pending_order 먼저 저장 (주문 전) - Bug #1 수정
                self.position_manager.update_position(symbol, {
                    "pending_order": {
                        "type": "dca",
                        "level": dca_level_index,
                        "timestamp": datetime.now().isoformat(),
                        "status": "preparing",  # 주문 준비 중
                        "group_id": group_id,
                        "group_name": group.get("name", "Unknown"),
                        "expected_price": current_price  # 예상 체결가 저장
                    }
                })
                logger.info(f"   📝 {symbol} DCA 레벨 {dca_level_num} pending_order 사전 저장 완료 (예상가: {current_price:,.0f}원)")

                # 2. REST API 호출
                try:
                    order_result = self.upbit_api.buy_market_order(symbol, dca_amount)

                    if not order_result or 'error' in order_result:
                        logger.error(f"❌ {symbol} DCA 실패: {order_result}")
                        # 실패 시 pending_order 제거
                        self.position_manager.update_position(symbol, {
                            "pending_order": None
                        })
                        return

                    order_uuid = order_result.get('uuid')
                    if not order_uuid:
                        logger.error(f"❌ {symbol} 주문 UUID 없음: {order_result}")
                        # 실패 시 pending_order 제거
                        self.position_manager.update_position(symbol, {
                            "pending_order": None
                        })
                        return

                    executed_volume = float(order_result.get('executed_volume', 0))
                    avg_price = float(order_result.get('avg_price', 0))

                    logger.info(f"   📝 {symbol} DCA 주문 생성: {order_uuid[:8]}... (수량: {executed_volume:.8f})")

                    # 3. pending_order 업데이트 (order_id 추가)
                    self.position_manager.update_position(symbol, {
                        "pending_order": {
                            "order_id": order_uuid,
                            "type": "dca",
                            "level": dca_level_index,
                            "timestamp": datetime.now().isoformat(),
                            "status": "waiting",  # 체결 대기
                            # DCA 정보 저장 (체결 후 add_dca 호출용)
                            "dca_price": current_price if avg_price == 0 else avg_price,  # avg_price 0이면 현재가 사용
                            "dca_amount": executed_volume,
                            "dca_value_krw": dca_amount,
                            "group_id": group_id,
                            "group_name": group.get("name", "Unknown")
                        }
                    })

                    # 4. MyOrderWebSocket 콜백 등록 (Live 모드에서만)
                    if self.myorder_ws:
                        self.myorder_ws.register_order_callback(order_uuid, self._on_order_completed)
                        logger.info(f"   📡 {symbol} DCA 주문 {order_uuid[:8]}... 콜백 등록 완료")
                    else:
                        logger.warning(f"   ⚠️ {symbol} MyOrderWebSocket 없음 (콜백 등록 불가)")

                    logger.info(f"   ⏳ {symbol} DCA 레벨 {dca_level_num} 주문 대기 중...")

                except Exception as api_error:
                    logger.error(f"❌ {symbol} DCA REST API 호출 오류: {api_error}", exc_info=True)
                    # 예외 발생 시 pending_order 제거
                    self.position_manager.update_position(symbol, {
                        "pending_order": None
                    })
                    return

        except Exception as e:
            logger.error(f"❌ {symbol} DCA 실행 오류: {e}", exc_info=True)

    def _check_profit_target(
        self,
        symbol: str,
        group_id: str,
        group: Dict[str, Any],
        position: Dict[str, Any],
        current_price: float,
        profit_pct: float
    ):
        """익절 체크 및 실행 (순차적 단발성 실행)"""
        profit_settings = group.get("profit_settings", {})

        if profit_settings.get("mode") not in ["auto", "alert"]:
            return

        # pending_order 체크 및 Timeout 확인 (Bug #2 수정)
        pending_order = position.get("pending_order")
        if pending_order:
            timestamp_str = pending_order.get('timestamp')

            if timestamp_str:
                try:
                    from datetime import datetime
                    timestamp = datetime.fromisoformat(timestamp_str)
                    elapsed = (datetime.now() - timestamp).total_seconds()

                    # 5분(300초) 이상 대기 중이면 자동 제거
                    if elapsed > 300:
                        logger.warning(
                            f"⚠️ {symbol} pending_order timeout "
                            f"(경과: {elapsed:.0f}초, 타입: {pending_order.get('type')}, "
                            f"레벨: {pending_order.get('level')}) → 제거 및 재시도"
                        )
                        self.position_manager.update_position(symbol, {
                            "pending_order": None
                        })

                        # Telegram 알림
                        if self.telegram_bot:
                            self.telegram_bot.send_message(
                                f"⚠️ pending_order Timeout\n"
                                f"코인: {symbol}\n"
                                f"타입: {pending_order.get('type')}\n"
                                f"레벨: {pending_order.get('level')}\n"
                                f"경과 시간: {elapsed:.0f}초\n"
                                f"자동 제거 후 재시도합니다."
                            )

                        # Timeout 후 계속 진행 (재시도)
                    else:
                        # 정상 대기 중
                        logger.debug(
                            f"   ⏳ {symbol}: 익절 스킵 "
                            f"(진행 중인 주문: {pending_order.get('type')} 레벨 {pending_order.get('level')}, "
                            f"경과: {elapsed:.0f}초)"
                        )
                        return  # 스킵

                except (ValueError, TypeError) as e:
                    # timestamp parsing 실패
                    logger.error(f"⚠️ {symbol} pending_order timestamp 파싱 실패: {e}")
                    # timestamp가 잘못되었으면 제거
                    self.position_manager.update_position(symbol, {
                        "pending_order": None
                    })
                    # 계속 진행 (재시도)
            else:
                # timestamp 없음 (오래된 데이터)
                logger.warning(f"⚠️ {symbol} pending_order에 timestamp 없음 → 제거")
                self.position_manager.update_position(symbol, {
                    "pending_order": None
                })
                # 계속 진행 (재시도)

        profit_levels = profit_settings.get("levels", [])
        profit_levels_executed = position.get("profit_levels_executed", [])

        # 레벨을 순차적으로 확인 (인덱스 포함)
        for level_index, level in enumerate(profit_levels):
            # 이미 실행된 레벨은 스킵 (단발성 보장)
            if level_index in profit_levels_executed:
                continue

            target_pct = level.get("price_ratio", 5.0)
            quantity_ratio = level.get("quantity_ratio", 100) / 100.0

            if profit_pct >= target_pct:
                logger.info(f"[익절] {symbol} 레벨{level_index} 도달 (+{profit_pct:.2f}%) → 매도 주문")

                if profit_settings.get("mode") == "auto":
                    self._execute_sell(symbol, group_id, group, "profit", quantity_ratio, level_index, profit_pct)
                else:
                    self._send_telegram_alert(
                        f"🎯 익절 알림 (레벨 {level_index})\n"
                        f"그룹: {group.get('name')}\n"
                        f"코인: {symbol}\n"
                        f"수익률: {profit_pct:.2f}%\n"
                        f"목표: {target_pct:.2f}%"
                    )

                break  # 한 번에 하나의 레벨만 실행 (순차적 실행)

    def _check_stop_loss(
        self,
        symbol: str,
        group_id: str,
        group: Dict[str, Any],
        position: Dict[str, Any],
        current_price: float,
        profit_pct: float
    ):
        """손절 체크 및 실행 (순차적 단발성 실행)"""
        loss_settings = group.get("loss_settings", {})

        if loss_settings.get("mode") not in ["auto", "alert"]:
            return

        # pending_order 체크 및 Timeout 확인 (Bug #2 수정)
        pending_order = position.get("pending_order")
        if pending_order:
            timestamp_str = pending_order.get('timestamp')

            if timestamp_str:
                try:
                    from datetime import datetime
                    timestamp = datetime.fromisoformat(timestamp_str)
                    elapsed = (datetime.now() - timestamp).total_seconds()

                    # 5분(300초) 이상 대기 중이면 자동 제거
                    if elapsed > 300:
                        logger.warning(
                            f"⚠️ {symbol} pending_order timeout "
                            f"(경과: {elapsed:.0f}초, 타입: {pending_order.get('type')}, "
                            f"레벨: {pending_order.get('level')}) → 제거 및 재시도"
                        )
                        self.position_manager.update_position(symbol, {
                            "pending_order": None
                        })

                        # Telegram 알림
                        if self.telegram_bot:
                            self.telegram_bot.send_message(
                                f"⚠️ pending_order Timeout\n"
                                f"코인: {symbol}\n"
                                f"타입: {pending_order.get('type')}\n"
                                f"레벨: {pending_order.get('level')}\n"
                                f"경과 시간: {elapsed:.0f}초\n"
                                f"자동 제거 후 재시도합니다."
                            )

                        # Timeout 후 계속 진행 (재시도)
                    else:
                        # 정상 대기 중
                        logger.debug(
                            f"   ⏳ {symbol}: 손절 스킵 "
                            f"(진행 중인 주문: {pending_order.get('type')} 레벨 {pending_order.get('level')}, "
                            f"경과: {elapsed:.0f}초)"
                        )
                        return  # 스킵

                except (ValueError, TypeError) as e:
                    # timestamp parsing 실패
                    logger.error(f"⚠️ {symbol} pending_order timestamp 파싱 실패: {e}")
                    # timestamp가 잘못되었으면 제거
                    self.position_manager.update_position(symbol, {
                        "pending_order": None
                    })
                    # 계속 진행 (재시도)
            else:
                # timestamp 없음 (오래된 데이터)
                logger.warning(f"⚠️ {symbol} pending_order에 timestamp 없음 → 제거")
                self.position_manager.update_position(symbol, {
                    "pending_order": None
                })
                # 계속 진행 (재시도)

        loss_levels = loss_settings.get("levels", [])
        loss_levels_executed = position.get("loss_levels_executed", [])

        # 레벨을 순차적으로 확인 (인덱스 포함)
        for level_index, level in enumerate(loss_levels):
            # 이미 실행된 레벨은 스킵 (단발성 보장)
            if level_index in loss_levels_executed:
                continue

            stop_pct = level.get("price_ratio", -15.0)
            quantity_ratio = level.get("quantity_ratio", 100) / 100.0

            if profit_pct <= stop_pct:
                logger.info(f"[손절] {symbol} 레벨{level_index} 도달 ({profit_pct:.2f}%) → 매도 주문")

                if loss_settings.get("mode") == "auto":
                    self._execute_sell(symbol, group_id, group, "loss", quantity_ratio, level_index, profit_pct)
                else:
                    self._send_telegram_alert(
                        f"🛑 손절 알림 (레벨 {level_index})\n"
                        f"그룹: {group.get('name')}\n"
                        f"코인: {symbol}\n"
                        f"수익률: {profit_pct:.2f}%\n"
                        f"기준: {stop_pct:.2f}%"
                    )

                break  # 한 번에 하나의 레벨만 실행 (순차적 실행)

    def _execute_sell(
        self,
        symbol: str,
        group_id: str,
        group: Dict[str, Any],
        reason: str,  # "profit" or "loss"
        quantity_ratio: float = 1.0,  # 판매 비율 (1.0 = 전량)
        level_index: int = 0,  # 익절/손절 레벨 인덱스
        profit_pct: float = 0.0  # 수익률 (%)
    ):
        """매도 실행 (주문 체결 확인 포함)"""
        if self.observation_mode:
            logger.info(f"[관찰] {symbol} 매도 신호 (사유: {reason}, 레벨: {level_index}, 실행 안 함)")
            return

        position = self.position_manager.get_position(symbol)
        if not position:
            return

        # 현재가 조회 (최소 주문 금액 체크용)
        current_price = self._get_current_price_safe(symbol)
        if not current_price:
            logger.error(f"❌ {symbol} 현재가 조회 실패")
            return

        total_amount = position.get("total_amount", 0)
        sell_amount = total_amount * quantity_ratio
        sell_value_krw = sell_amount * current_price

        # Upbit 최소 주문 금액 체크 (5000원)
        MIN_ORDER_KRW = 5000

        if sell_value_krw < MIN_ORDER_KRW:
            if quantity_ratio >= 0.99:
                # 전량 매도인데도 5000원 미만 → 매도 불가
                logger.warning(
                    f"⚠️ {symbol} 매도 불가: 주문 금액 {sell_value_krw:,.0f}원 < 최소 {MIN_ORDER_KRW:,.0f}원 "
                    f"(전량 {total_amount:.8f}개 @ {current_price:,.2f}원)"
                )
                return
            else:
                # 부분 매도인데 5000원 미만 → 전량 매도로 변경
                original_ratio = quantity_ratio * 100
                logger.warning(
                    f"⚠️ {symbol} 부분 매도 금액 부족 ({sell_value_krw:,.0f}원 < {MIN_ORDER_KRW:,.0f}원) "
                    f"→ 전량 매도로 변경"
                )

                # 텔레그램 알림
                self._send_telegram_alert(
                    f"⚠️ 익절/손절 수량 자동 조정\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"코인: {symbol}\n"
                    f"사유: {reason} (레벨 {level_index})\n"
                    f"설정: {original_ratio:.0f}% 매도\n"
                    f"예정 금액: {sell_value_krw:,.0f}원\n"
                    f"최소 금액: {MIN_ORDER_KRW:,.0f}원\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"→ 전량 매도(100%)로 변경됩니다"
                )

                quantity_ratio = 1.0
                sell_amount = total_amount
                sell_value_krw = sell_amount * current_price

                # 전량 매도로 변경해도 5000원 미만이면 포기
                if sell_value_krw < MIN_ORDER_KRW:
                    logger.warning(
                        f"⚠️ {symbol} 매도 불가: 전량 매도해도 {sell_value_krw:,.0f}원 < {MIN_ORDER_KRW:,.0f}원"
                    )

                    # 텔레그램 알림
                    self._send_telegram_alert(
                        f"⚠️ 매도 불가 알림\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"코인: {symbol}\n"
                        f"사유: {reason} (레벨 {level_index})\n"
                        f"보유 수량: {total_amount:.8f}개\n"
                        f"전량 매도 금액: {sell_value_krw:,.0f}원\n"
                        f"최소 주문 금액: {MIN_ORDER_KRW:,.0f}원\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"→ 매도 스킵 (다음 기회 대기)"
                    )
                    return

        logger.debug(f"💰 {symbol} 매도 실행 중... (사유: {reason}, 레벨: {level_index}, 수량: {sell_amount:.8f}개, 금액: {sell_value_krw:,.0f}원)")

        try:
            if self.dry_run or not self.upbit_api:
                # Dry-run 모드: 즉시 실행 (체결 확인 불필요)
                sell_value = sell_value_krw
                profit = sell_value - (position.get("total_invested_krw", 0) * quantity_ratio)

                # 포지션 업데이트 (executed_levels 추가)
                if quantity_ratio >= 0.99:  # 거의 전량 매도
                    self.position_manager.close_position(symbol, close_price=current_price, close_reason=reason)
                    logger.info(f"✅ [Dry-run] {symbol} 전량 매도 완료: {sell_amount:.8f}개 @ {current_price:,}원 (수익: {profit:+,.0f}원)")
                else:
                    # 부분 매도: executed_levels 업데이트
                    if reason == "profit":
                        profit_levels_executed = position.get("profit_levels_executed", [])
                        if level_index not in profit_levels_executed:
                            profit_levels_executed.append(level_index)
                            self.position_manager.update_position(symbol, {
                                "profit_levels_executed": profit_levels_executed
                            })
                    elif reason == "loss":
                        loss_levels_executed = position.get("loss_levels_executed", [])
                        if level_index not in loss_levels_executed:
                            loss_levels_executed.append(level_index)
                            self.position_manager.update_position(symbol, {
                                "loss_levels_executed": loss_levels_executed
                            })
                    logger.info(f"✅ [Dry-run] {symbol} 부분 매도 완료: {sell_amount:.8f}개 @ {current_price:,}원")

            else:
                # Live 모드: pending_order 먼저 저장 → 주문 → 콜백 등록
                from datetime import datetime

                # 1. pending_order 먼저 저장 (주문 전) - Bug #1 수정
                self.position_manager.update_position(symbol, {
                    "pending_order": {
                        "type": reason,  # "profit" or "loss"
                        "level": level_index,
                        "timestamp": datetime.now().isoformat(),
                        "status": "preparing",  # 주문 준비 중
                        "quantity_ratio": quantity_ratio,
                        "group_id": group_id,
                        "group_name": group.get('name', 'Unknown'),
                        "sell_amount_krw": sell_value_krw,
                        "sell_amount": sell_amount,
                        "profit_pct": profit_pct  # 수익률 (%)
                    }
                })
                logger.debug(f"   📝 {symbol} {reason} 레벨 {level_index} pending_order 사전 저장 완료")

                # 2. REST API 호출
                try:
                    order_result = self.upbit_api.sell_market_order(symbol, sell_amount)

                    if not order_result or 'error' in order_result:
                        logger.error(f"❌ {symbol} 매도 실패: {order_result}")
                        # 실패 시 pending_order 제거
                        self.position_manager.update_position(symbol, {
                            "pending_order": None
                        })
                        return

                    order_uuid = order_result.get('uuid')
                    if not order_uuid:
                        logger.error(f"❌ {symbol} 주문 UUID 없음: {order_result}")
                        # 실패 시 pending_order 제거
                        self.position_manager.update_position(symbol, {
                            "pending_order": None
                        })
                        return

                    executed_volume = float(order_result.get('executed_volume', 0))
                    avg_price = float(order_result.get('avg_price', 0))

                    logger.debug(f"   📝 {symbol} 주문 생성: {order_uuid[:8]}... (수량: {executed_volume:.8f})")

                    # 3. pending_order 업데이트 (order_id 추가)
                    self.position_manager.update_position(symbol, {
                        "pending_order": {
                            "order_id": order_uuid,
                            "type": reason,  # "profit" or "loss"
                            "level": level_index,
                            "timestamp": datetime.now().isoformat(),
                            "status": "waiting",  # 체결 대기
                            "quantity_ratio": quantity_ratio,
                            "group_id": group_id,
                            "group_name": group.get('name', 'Unknown'),
                            "sell_amount_krw": sell_value_krw,
                            "sell_amount": sell_amount,
                            "profit_pct": profit_pct  # 수익률 (%)
                        }
                    })

                    # 4. MyOrderWebSocket 콜백 등록 (Live 모드에서만)
                    if self.myorder_ws:
                        self.myorder_ws.register_order_callback(order_uuid, self._on_order_completed)
                        logger.debug(f"   📡 {symbol} 주문 {order_uuid[:8]}... 콜백 등록 완료")
                    else:
                        logger.warning(f"   ⚠️ {symbol} MyOrderWebSocket 없음 (콜백 등록 불가)")

                    # 5. 포지션 종료 여부 로그
                    if quantity_ratio >= 0.99:
                        # 체결 확인 후 포지션 종료는 _on_order_completed에서 처리
                        logger.debug(f"   ⏳ {symbol} 전량 매도 주문 대기 중...")
                    else:
                        logger.debug(f"   ⏳ {symbol} 부분 매도 주문 대기 중...")

                except Exception as api_error:
                    logger.error(f"❌ {symbol} 매도 REST API 호출 오류: {api_error}", exc_info=True)
                    # 예외 발생 시 pending_order 제거
                    self.position_manager.update_position(symbol, {
                        "pending_order": None
                    })
                    return

            # 거래 기록 (Dry-run만 즉시 기록, Live는 체결 확인 후)
            if self.dry_run:
                self.trade_history.add_trade(
                    group_id=group_id,
                    group_name=group.get("name", "Unknown"),
                    symbol=symbol,
                    action="sell",
                    trade_type=reason,  # "profit" or "loss"
                    price=current_price,
                    amount=sell_amount,
                    total_krw=sell_value,
                    dry_run=self.dry_run,
                    profit_loss=profit  # 추가 정보
                )

                # 텔레그램 알림 (Dry-run)
                emoji = "🎉" if profit > 0 else "😢"
                self._send_telegram_alert(
                    f"{emoji} 매도 완료 ({reason}, 레벨 {level_index})\n"
                    f"그룹: {group.get('name')}\n"
                    f"코인: {symbol}\n"
                    f"수익: {profit:+,.0f}원\n"
                    f"수익률: {(profit / position.get('total_invested_krw', 1) * 100):+.2f}%"
                )

        except Exception as e:
            logger.error(f"❌ {symbol} 매도 실행 오류: {e}", exc_info=True)

    def _on_order_completed(self, order_data: Dict):
        """
        주문 체결 완료 콜백 (MyOrderWebSocket에서 호출됨)

        Args:
            order_data: MyOrder WebSocket에서 전달된 주문 데이터
                - uuid: 주문 고유 ID
                - code: 코인 심볼 (예: KRW-BTC)
                - state: 주문 상태 (done, cancel, prevented)
                - ask_bid: 매수/매도 (BID/ASK)
                - executed_volume: 체결된 수량
                - avg_price: 평균 체결 가격
        """
        try:
            order_uuid = order_data.get('uuid')
            symbol = order_data.get('code')
            state = order_data.get('state')
            ask_bid = order_data.get('ask_bid')
            executed_volume = order_data.get('executed_volume', 0)
            avg_price = order_data.get('avg_price', 0)
            trade_price = order_data.get('price', 0)  # ✅ 실제 체결가 (state='trade'일 때)

            logger.debug(f"📬 주문 체결 이벤트 수신: {symbol} {order_uuid[:8]}... state={state}")

            # 대기 중인 주문은 무시
            if state == 'wait':
                logger.debug(f"   ⏳ 주문 {order_uuid[:8]}... 아직 대기 중")
                return

            # 초기 매수 주문 체결 처리 (pending_initial_buys 확인)
            if order_uuid in self.pending_initial_buys:
                pending_buy = self.pending_initial_buys[order_uuid]

                # 🔧 Phase D: state='done' or 'cancel' 모두 처리 (DCA와 동일 패턴)
                if state in ['done', 'cancel']:
                    # ✅ 중복 체크: 이미 활성 포지션이 있으면 스킵
                    existing_position = self.position_manager.get_position(symbol)
                    if existing_position and existing_position.get('status') == 'active':
                        logger.warning(f"   ⚠️ [자동매수] {symbol} 초기 매수 중복 감지 (포지션 이미 존재) → 스킵")

                        # 텔레그램 알림 추가
                        self._send_telegram_alert(
                            f"⚠️ [자동매수] 초기 매수 중복 감지\n"
                            f"코인: {symbol}\n"
                            f"수량: {executed_volume:.8f}개\n"
                            f"가격: {avg_price:,}원\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"포지션이 이미 존재하여 스킵됨\n"
                            f"주문 ID: {order_uuid[:8]}..."
                        )

                        self.processed_bot_order_uuids.add(order_uuid)
                        del self.pending_initial_buys[order_uuid]
                        return

                    # state 구분 로그 (debug)
                    if state == 'done':
                        logger.debug(f"   ✅ [자동매수] {symbol} 초기 매수 체결 완료 (state=done, 완전 체결) (수량: {executed_volume:.8f}, MyOrder avg: {avg_price:,.0f}원)")
                    else:
                        logger.debug(f"   ✅ [자동매수] {symbol} 초기 매수 체결 완료 (state=cancel, 미세 잔량 반환) (수량: {executed_volume:.8f}, MyOrder avg: {avg_price:,.0f}원)")

                    # 🆕 REST API로 정확한 평균가 조회 (체결 반영 대기)
                    final_avg_price = avg_price  # fallback
                    final_balance = executed_volume  # fallback

                    if self.upbit_api:
                        try:
                            # 🔧 Upbit 시스템에 체결 반영될 때까지 대기
                            time.sleep(1.5)
                            accounts = self.upbit_api.get_accounts()
                            for acc in accounts:
                                currency = symbol.replace('KRW-', '')
                                if acc['currency'] == currency:
                                    final_avg_price = float(acc.get('avg_buy_price', 0))
                                    final_balance = float(acc.get('balance', 0))
                                    logger.debug(f"   📊 [최종] {symbol} REST API 평균가: {final_avg_price:,.0f}원 (수량: {final_balance:.8f}개)")
                                    break
                        except Exception as e:
                            logger.error(f"❌ {symbol} REST API 평균가 조회 실패 (fallback to MyOrder): {e}")

                    # 포지션 생성
                    position = self.position_manager.create_position(
                        group_id=pending_buy['group_id'],
                        symbol=symbol,
                        buy_price=final_avg_price,  # ✅ REST API 최종 평균가
                        quantity=final_balance,
                        buy_amount_krw=pending_buy['buy_amount_krw']
                    )

                    # 거래 기록
                    self.trade_history.add_trade(
                        group_id=pending_buy['group_id'],
                        group_name=pending_buy['group_name'],
                        symbol=symbol,
                        action="buy",
                        trade_type="initial",
                        price=final_avg_price,
                        amount=final_balance,
                        total_krw=pending_buy['buy_amount_krw'],
                        dry_run=False
                    )

                    # 🔧 GUI 완료 로그 (한 줄 요약)
                    logger.info(f"[자동매수완료] {symbol} | {pending_buy['buy_amount_krw']:,.0f}원 | {final_balance:.8f}개 | {final_avg_price:,.0f}원")

                    # 텔레그램 알림
                    self._send_telegram_alert(
                        f"✅ [자동매수] 매수 완료\n"
                        f"그룹: {pending_buy['group_name']}\n"
                        f"코인: {symbol}\n"
                        f"금액: {pending_buy['buy_amount_krw']:,}원\n"
                        f"수량: {final_balance:.8f}개\n"
                        f"가격: {final_avg_price:,}원"
                    )

                    # pending_initial_buys에서 제거
                    self.processed_bot_order_uuids.add(order_uuid)
                    del self.pending_initial_buys[order_uuid]
                    logger.debug(f"   🗑️ {symbol} pending_initial_buys 제거 완료")

                    # MyOrder 처리 완료 마킹 (MyAsset 백업 스킵용)
                    self._mark_processed_by_myorder(symbol)

                    # 🆕 GUI 새로고침 콜백 호출
                    if self.on_position_created_callback:
                        try:
                            self.on_position_created_callback(symbol)
                        except Exception as e:
                            logger.error(f"❌ 포지션 생성 콜백 오류: {e}")

                    logger.debug(f"   🎉 [자동매수] {symbol} 초기 매수 처리 완료")

                return  # 초기 매수는 여기서 종료

            # 🆕 Phase B: 수동 매수 처리 (state='done' or 'cancel' and side='bid')
            # 시장가 주문은 부분 체결 후 state=cancel로 완료될 수 있음
            if state in ['done', 'cancel'] and ask_bid == 'BID':
                # 🆕 이미 처리된 봇 주문이면 수동 매수 처리 스킵
                if order_uuid in self.processed_bot_order_uuids:
                    logger.debug(f"   ⏭️ {symbol} 이미 처리된 봇 주문 ({order_uuid[:8]}...), 수동 매수 처리 스킵")
                    return

                position = self.position_manager.get_position(symbol)
                has_active_position = position and position.get('status') == 'active'

                if not has_active_position:
                    # 🆕 Phase B-1: 외부 신규 매수 처리 (포지션 없거나 종료된 경우)
                    group_id = self._find_group_for_symbol(symbol)

                    if not group_id:
                        group_id = "group_null"

                    # 포지션 생성
                    position = self.position_manager.create_position(
                        group_id=group_id,
                        symbol=symbol,
                        buy_price=avg_price,
                        quantity=executed_volume,
                        force_create_for_sync=(group_id == "group_null")
                    )

                    # GUI 로그만 (텔레그램 알림 없음 - group_null은 DCA/익절/손절 미작동)
                    total_krw = avg_price * executed_volume
                    group_name = "그룹 없음" if group_id == "group_null" else group_id
                    logger.info(f"[수동매수] 신규: {symbol} | {total_krw:,.0f}원 | {executed_volume:.8f}개 | {group_name}")

                    # MyOrder 처리 완료 마킹 + 중복 방지
                    self._mark_processed_by_myorder(symbol)
                    self.processed_bot_order_uuids.add(order_uuid)

                    # 🆕 GUI 새로고침 콜백 호출
                    if self.on_position_created_callback:
                        try:
                            self.on_position_created_callback(symbol)
                        except Exception as e:
                            logger.error(f"❌ 포지션 생성 콜백 오류: {e}")
                    return

                # 🆕 Phase B-2: 외부 추가 매수 처리
                pending_order = position.get('pending_order')

                if not pending_order:
                    # REST API로 최신 평균가 조회
                    if self.upbit_api:
                        try:
                            accounts = self.upbit_api.get_accounts()
                            for acc in accounts:
                                currency = symbol.replace('KRW-', '')
                                if acc['currency'] == currency:
                                    new_avg_price = float(acc.get('avg_buy_price', 0))
                                    new_balance = float(acc.get('balance', 0))

                                    # 포지션 업데이트
                                    self.position_manager.update_position(symbol, {
                                        'total_amount': new_balance,
                                        'avg_buy_price': new_avg_price,
                                        'total_invested_krw': new_avg_price * new_balance
                                    })

                                    # GUI 한 줄 요약 로그 (텔레그램 알림 없음 - 신규 매수만 알림)
                                    additional_krw = avg_price * executed_volume
                                    logger.info(f"[수동매수] 추가: {symbol} | {additional_krw:,.0f}원 | 평균가 {new_avg_price:,.0f}원")
                                    break
                        except Exception as e:
                            logger.error(f"❌ [수동] {symbol} 평균가 조회 실패: {e}")

                    # MyOrder 처리 완료 마킹 + 중복 방지
                    self._mark_processed_by_myorder(symbol)
                    self.processed_bot_order_uuids.add(order_uuid)
                    return

            # 부분 체결 처리 (state='trade')
            if state == 'trade':
                # 🔧 익절/손절 부분체결 시 사용자 친화적 로그
                position = self.position_manager.get_position(symbol)
                pending_order = position.get('pending_order') if position else None
                order_type = pending_order.get('type') if pending_order else None

                if order_type == 'profit':
                    logger.info(f"[익절] {symbol} 부분체결: {executed_volume:.8f}개 @ {trade_price:,.0f}원")
                elif order_type == 'loss':
                    logger.info(f"[손절] {symbol} 부분체결: {executed_volume:.8f}개 @ {trade_price:,.0f}원")
                else:
                    logger.debug(f"   💰 주문 {order_uuid[:8]}... 부분 체결 (수량: {executed_volume:.8f}, 가격: {trade_price:,.0f}원)")

                # 🆕 실시간 평균가 업데이트 (REST API 조회)
                # 🔧 매도 주문(profit/loss)일 경우 total_amount 업데이트 건너뛰기
                if position and self.upbit_api:
                    # 매도 주문(profit/loss)이면 total_amount 업데이트 건너뛰기
                    if order_type in ['profit', 'loss']:
                        logger.debug(f"   ⏭️ [실시간] {symbol} 매도 주문 진행 중 → total_amount 업데이트 스킵")
                    else:
                        # 매수 주문(dca, buy 등)은 실시간 업데이트
                        try:
                            accounts = self.upbit_api.get_accounts()
                            for acc in accounts:
                                currency = symbol.replace('KRW-', '')
                                if acc['currency'] == currency:
                                    new_avg_price = float(acc.get('avg_buy_price', 0))
                                    new_balance = float(acc.get('balance', 0))

                                    # 포지션 업데이트 (실시간)
                                    self.position_manager.update_position(symbol, {
                                        'total_amount': new_balance,
                                        'avg_buy_price': new_avg_price,
                                        'total_invested_krw': new_avg_price * new_balance
                                    })

                                    logger.debug(f"   📊 [실시간] {symbol} 평균가 업데이트: {new_avg_price:,.0f}원 (수량: {new_balance:.8f}개)")
                                    break
                        except Exception as e:
                            logger.error(f"❌ [실시간] {symbol} 평균가 조회 실패: {e}")

                return  # 최종 처리는 state='done'에서

            # 체결 후 미세 잔량 발생 처리 (state=cancel)
            # Upbit: 체결 후 소수점 단위 등으로 미세 잔량 발생 시 계좌 반환 + state=cancel
            # (시장가/지정가 모두 발생 가능, done과 동일하게 처리)
            if state in ['cancel', 'prevented']:
                logger.warning(f"   ⚠️ 주문 {order_uuid[:8]}... 취소/방지됨 (state={state})")

                # pending_order 정리
                position = self.position_manager.get_position(symbol)
                if not position:
                    logger.warning(f"   ⚠️ {symbol} 포지션 없음")
                    return

                pending_order = position.get('pending_order')
                if not pending_order or pending_order.get('order_id') != order_uuid:
                    logger.debug(f"   ⏭️ {symbol} pending_order와 불일치 (무시)")
                    return

                order_type = pending_order.get('type')
                level_index = pending_order.get('level')

                # 🔧 Phase D 버그 수정: cancel/done 모두 동일하게 처리
                # state=cancel: 체결 후 미세 잔량 발생 (잔량은 계좌 반환, 정상 완료)
                # state=done: 완전 체결 (잔량 없음)

                if order_type == 'dca':
                    # 🔧 중복 처리 방지: 봇 주문 UUID 먼저 기록 (타이밍 이슈 방지)
                    self.processed_bot_order_uuids.add(order_uuid)

                    # ✅ 중복 체크: 이미 실행된 레벨이면 스킵
                    dca_levels_executed = position.get('dca_levels_executed', [])
                    if level_index in dca_levels_executed:
                        logger.warning(f"   ⚠️ {symbol} DCA 레벨 {level_index+1} 이미 실행됨 → 중복 스킵")
                        logger.warning(f"   🔍 중복 원인 디버그: order_uuid={order_uuid[:8]}..., "
                                     f"state={state}, dca_levels_executed={dca_levels_executed}")

                        # 텔레그램 알림 추가
                        group_id = pending_order.get('group_id', 'unknown')
                        group_name = pending_order.get('group_name', 'Unknown')
                        self._send_telegram_alert(
                            f"⚠️ DCA 중복 감지 (로직 오류)\n"
                            f"그룹: {group_name}\n"
                            f"코인: {symbol}\n"
                            f"레벨: {level_index + 1}\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"이미 실행된 레벨입니다\n"
                            f"state: {state}\n"
                            f"주문 ID: {order_uuid[:8]}...\n"
                            f"실행된 레벨: {dca_levels_executed}\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"이 알림이 반복되면 로그를 확인하세요"
                        )

                        self.position_manager.update_position(symbol, {'pending_order': None})
                        return

                    # DCA 처리 (done과 동일)
                    dca_value_krw = pending_order.get('dca_value_krw', 0)
                    group_id = pending_order.get('group_id', 'unknown')
                    group_name = pending_order.get('group_name', 'Unknown')

                    logger.debug(f"   ✅ {symbol} DCA 레벨 {level_index+1} 체결 완료 (state=cancel, MyOrder avg: {avg_price:,.0f}원, 수량: {executed_volume:.8f})")

                    # 🆕 REST API로 정확한 평균가 조회 (체결 반영 대기)
                    final_avg_price = avg_price  # fallback
                    final_balance = 0  # fallback

                    if self.upbit_api:
                        try:
                            # 🔧 Upbit 시스템에 체결 반영될 때까지 대기
                            time.sleep(1.5)
                            accounts = self.upbit_api.get_accounts()
                            for acc in accounts:
                                currency = symbol.replace('KRW-', '')
                                if acc['currency'] == currency:
                                    final_avg_price = float(acc.get('avg_buy_price', 0))
                                    final_balance = float(acc.get('balance', 0))
                                    logger.debug(f"   📊 [최종] {symbol} REST API 평균가: {final_avg_price:,.0f}원 (수량: {final_balance:.8f}개)")
                                    break
                        except Exception as e:
                            logger.error(f"❌ {symbol} REST API 평균가 조회 실패 (fallback to MyOrder): {e}")

                    # DCA 히스토리 기록
                    dca_history = position.get('dca_history', [])
                    dca_record = {
                        "level": level_index,
                        "price": avg_price,  # 체결가 기록
                        "amount": executed_volume,
                        "krw": dca_value_krw,
                        "timestamp": datetime.now().isoformat()
                    }
                    dca_history.append(dca_record)

                    # 🔧 DCA 레벨 기록 (중복 방지)
                    dca_levels_executed.append(level_index)

                    # 포지션 업데이트
                    self.position_manager.update_position(symbol, {
                        'total_amount': final_balance,
                        'avg_buy_price': final_avg_price,
                        'total_invested_krw': final_avg_price * final_balance,
                        'dca_count': position.get('dca_count', 0) + 1,
                        'dca_history': dca_history,
                        'dca_levels_executed': dca_levels_executed,
                        'pending_order': None
                    })

                    logger.debug(f"   📝 {symbol} DCA 레벨 {level_index+1} 완료 - dca_levels_executed: {dca_levels_executed}")

                    # 거래 기록
                    updated_position = self.position_manager.get_position(symbol)
                    self.trade_history.add_trade(
                        group_id=group_id,
                        group_name=group_name,
                        symbol=symbol,
                        action="buy",
                        trade_type="dca",
                        price=updated_position.get("avg_buy_price"),
                        amount=updated_position.get("total_amount"),
                        total_krw=dca_value_krw,
                        dry_run=False,
                        dca_level=level_index + 1
                    )

                    # 🔧 GUI 완료 로그 (한 줄 요약)
                    logger.info(f"[DCA완료] {symbol} L{level_index + 1} | {dca_value_krw:,.0f}원 | 평균가 {final_avg_price:,.0f}원 | 보유 {final_balance:.8f}개")

                    # 텔레그램 알림
                    self._send_telegram_alert(
                        f"🔄 DCA 추가 매수 완료\n"
                        f"그룹: {group_name}\n"
                        f"코인: {symbol}\n"
                        f"레벨: {level_index + 1}\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"추가 금액: {dca_value_krw:,.0f}원\n"
                        f"추가 수량: {executed_volume:.8f}개\n"
                        f"체결 가격: {avg_price:,.0f}원\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"평균 매수가: {final_avg_price:,.0f}원\n"
                        f"총 보유량: {final_balance:.8f}개"
                    )

                    # MyOrder 처리 완료 마킹 (MyAsset 백업 스킵용)
                    self._mark_processed_by_myorder(symbol)

                    # 🆕 GUI 새로고침 콜백 호출 (DCA로 포지션 변경됨)
                    if self.on_position_created_callback:
                        try:
                            self.on_position_created_callback(symbol)
                        except Exception as e:
                            logger.error(f"❌ DCA 완료 GUI 콜백 오류: {e}")

                    # 🔧 중복 처리 방지: 봇 주문 UUID 기록
                    self.processed_bot_order_uuids.add(order_uuid)

                    logger.debug(f"   🎉 {symbol} DCA 주문 {order_uuid[:8]}... 처리 완료")

                elif order_type in ['profit', 'loss']:
                    # 🔧 중복 처리 방지: 봇 주문 UUID 먼저 기록 (타이밍 이슈 방지)
                    self.processed_bot_order_uuids.add(order_uuid)

                    # ✅ 중복 체크
                    if order_type == 'profit':
                        levels_executed = position.get('profit_levels_executed', [])
                        key = 'profit_levels_executed'
                        action_type = "익절"
                    else:
                        levels_executed = position.get('loss_levels_executed', [])
                        key = 'loss_levels_executed'
                        action_type = "손절"

                    if level_index in levels_executed:
                        logger.warning(f"   ⚠️ {symbol} {order_type} 레벨 {level_index} 이미 실행됨 → 중복 스킵")
                        logger.warning(f"   🔍 중복 원인 디버그: order_uuid={order_uuid[:8]}..., "
                                     f"state={state}, {key}={levels_executed}")

                        # 텔레그램 알림 추가
                        group_id = pending_order.get('group_id', 'unknown')
                        group_name = pending_order.get('group_name', 'Unknown')
                        emoji = "✅" if order_type == 'profit' else "❌"
                        self._send_telegram_alert(
                            f"{emoji} {action_type} 중복 감지 (로직 오류)\n"
                            f"그룹: {group_name}\n"
                            f"코인: {symbol}\n"
                            f"레벨: {level_index}\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"이미 실행된 레벨입니다\n"
                            f"state: {state}\n"
                            f"주문 ID: {order_uuid[:8]}...\n"
                            f"실행된 레벨: {levels_executed}\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"이 알림이 반복되면 로그를 확인하세요"
                        )

                        self.position_manager.update_position(symbol, {'pending_order': None})
                        return

                    # 레벨 기록
                    levels_executed.append(level_index)
                    logger.debug(f"   📝 {symbol} {order_type} 레벨 {level_index} 체결 완료 (state=cancel, 미세 잔량 반환) → {key}에 기록")

                    # 🔧 Phase D 버그 수정: 포지션 수량 감소 처리 (state=done과 동일)
                    group_id = pending_order.get('group_id', 'unknown')
                    group_name = pending_order.get('group_name', 'Unknown')

                    # 남은 수량 계산
                    total_amount = position.get('total_amount', 0)
                    remaining_amount = total_amount - executed_volume

                    action_type = "익절" if order_type == 'profit' else "손절"
                    logger.debug(f"   📊 {symbol} {action_type} 매도 후 수량: {total_amount:.8f} → {remaining_amount:.8f} (매도: {executed_volume:.8f})")

                    # 현재가 조회 (최소 주문 금액 체크용)
                    current_price = self._get_current_price_safe(symbol)
                    if current_price:
                        remaining_value = remaining_amount * current_price
                        MIN_ORDER_KRW = 5000

                        if remaining_value < MIN_ORDER_KRW:
                            # 남은 금액이 최소 주문 금액 미만 → 포지션 종료
                            logger.debug(f"   💰 {symbol} 남은 금액 {remaining_value:,.0f}원 < 최소 {MIN_ORDER_KRW:,.0f}원 → 포지션 종료")
                            self.position_manager.close_position(symbol, close_price=avg_price, close_reason=order_type)

                            # 거래 기록
                            sell_amount_krw = avg_price * executed_volume  # 실제 체결 금액
                            trade_params = {
                                "group_id": group_id,
                                "group_name": group_name,
                                "symbol": symbol,
                                "action": "sell",
                                "trade_type": order_type,
                                "price": avg_price,
                                "amount": executed_volume,
                                "total_krw": sell_amount_krw,
                                "dry_run": False
                            }
                            if order_type == 'profit':
                                trade_params['profit_level'] = level_index + 1
                            else:
                                trade_params['loss_level'] = level_index + 1

                            self.trade_history.add_trade(**trade_params)

                            # 🔧 GUI 완료 로그 (한 줄 요약)
                            profit_pct = pending_order.get('profit_pct', 0)
                            avg_buy_price = position.get('avg_buy_price', 0)
                            profit_krw = sell_amount_krw - (avg_buy_price * executed_volume)
                            logger.info(f"[{action_type}완료] {symbol} | {sell_amount_krw:,.0f}원 | {profit_krw:+,.0f}원 ({profit_pct:+.2f}%)")

                            # 텔레그램 알림
                            emoji = "✅" if order_type == 'profit' else "❌"
                            self._send_telegram_alert(
                                f"{emoji} {action_type} 매도 완료 (포지션 종료)\n"
                                f"그룹: {group_name}\n"
                                f"코인: {symbol}\n"
                                f"레벨: {level_index + 1}\n"
                                f"━━━━━━━━━━━━━━\n"
                                f"매도 금액: {sell_amount_krw:,.0f}원\n"
                                f"매도 수량: {executed_volume:.8f}개\n"
                                f"체결 가격: {avg_price:,.0f}원\n"
                                f"━━━━━━━━━━━━━━\n"
                                f"포지션 전체 종료됨"
                            )
                        else:
                            # 남은 금액 충분 → 수량만 감소
                            logger.debug(f"   💰 {symbol} 남은 금액 {remaining_value:,.0f}원 → 포지션 유지")
                            self.position_manager.update_position(symbol, {
                                key: levels_executed,
                                'pending_order': None,
                                'total_amount': remaining_amount
                            })

                            # 거래 기록
                            sell_amount_krw = avg_price * executed_volume  # 실제 체결 금액
                            trade_params = {
                                "group_id": group_id,
                                "group_name": group_name,
                                "symbol": symbol,
                                "action": "sell",
                                "trade_type": order_type,
                                "price": avg_price,
                                "amount": executed_volume,
                                "total_krw": sell_amount_krw,
                                "dry_run": False
                            }
                            if order_type == 'profit':
                                trade_params['profit_level'] = level_index + 1
                            else:
                                trade_params['loss_level'] = level_index + 1

                            self.trade_history.add_trade(**trade_params)

                            # 🔧 GUI 완료 로그 (한 줄 요약)
                            profit_pct = pending_order.get('profit_pct', 0)
                            avg_buy_price = position.get('avg_buy_price', 0)
                            profit_krw = sell_amount_krw - (avg_buy_price * executed_volume)
                            logger.info(f"[{action_type}완료] {symbol} | {sell_amount_krw:,.0f}원 | {profit_krw:+,.0f}원 ({profit_pct:+.2f}%) | 잔여: {remaining_value:,.0f}원")

                            # 텔레그램 알림
                            emoji = "✅" if order_type == 'profit' else "❌"
                            self._send_telegram_alert(
                                f"{emoji} {action_type} 부분 매도 완료\n"
                                f"그룹: {group_name}\n"
                                f"코인: {symbol}\n"
                                f"레벨: {level_index + 1}\n"
                                f"━━━━━━━━━━━━━━\n"
                                f"매도 금액: {sell_amount_krw:,.0f}원\n"
                                f"매도 수량: {executed_volume:.8f}개\n"
                                f"체결 가격: {avg_price:,.0f}원\n"
                                f"━━━━━━━━━━━━━━\n"
                                f"남은 수량: {remaining_amount:.8f}개\n"
                                f"남은 금액: {remaining_value:,.0f}원"
                            )

                    # MyOrder 처리 완료 마킹
                    self._mark_processed_by_myorder(symbol)

                    # 🆕 GUI 새로고침 콜백 호출 (익절/손절로 포지션 변경됨)
                    if self.on_position_created_callback:
                        try:
                            self.on_position_created_callback(symbol)
                        except Exception as e:
                            logger.error(f"❌ 익절/손절 완료 GUI 콜백 오류: {e}")

                else:
                    # 기타 주문 타입
                    self.position_manager.update_position(symbol, {'pending_order': None})
                    logger.debug(f"   🗑️ {symbol} pending_order 정리 완료")

                return

            # 완전 체결 처리 (state=done, 잔량 없음)
            # Upbit: 주문 잔량 없이 완전히 체결된 경우 (시장가/지정가 모두 발생 가능)
            position = self.position_manager.get_position(symbol)
            if not position:
                logger.warning(f"   ⚠️ {symbol} 포지션 없음 (주문 {order_uuid[:8]}...)")
                return

            pending_order = position.get('pending_order')
            if not pending_order or pending_order.get('order_id') != order_uuid:
                logger.debug(f"   ⏭️ {symbol} pending_order와 불일치 (무시)")
                return

            # pending_order에서 주문 타입과 레벨 정보 가져오기
            order_type = pending_order.get('type')  # 'profit', 'loss', 'dca'
            level_index = pending_order.get('level')  # 0, 1, 2, ...

            logger.debug(f"   ✅ {symbol} {order_type} 레벨 {level_index} 체결 완료 "
                       f"(수량: {executed_volume:.8f}, 가격: {avg_price:,.0f}원)")

            # 🔧 중복 처리 방지: 봇 주문 UUID 먼저 기록 (타이밍 이슈 방지)
            self.processed_bot_order_uuids.add(order_uuid)

            # executed_levels 배열에 추가
            updates = {'pending_order': None}

            if order_type == 'profit':
                # 레벨 기록
                profit_levels_executed = position.get('profit_levels_executed', [])
                if level_index not in profit_levels_executed:
                    profit_levels_executed.append(level_index)
                    updates['profit_levels_executed'] = profit_levels_executed
                    logger.debug(f"   📝 {symbol} profit_levels_executed 업데이트: {profit_levels_executed}")

                # 🔧 Phase D 버그 수정: 포지션 수량 감소 처리
                group_id = pending_order.get('group_id', 'unknown')
                group_name = pending_order.get('group_name', 'Unknown')

                # 남은 수량 계산
                total_amount = position.get('total_amount', 0)
                remaining_amount = total_amount - executed_volume

                logger.debug(f"   📊 {symbol} 익절 매도 후 수량: {total_amount:.8f} → {remaining_amount:.8f} (매도: {executed_volume:.8f})")

                # 현재가 조회 (최소 주문 금액 체크용)
                current_price = self._get_current_price_safe(symbol)
                if current_price:
                    remaining_value = remaining_amount * current_price
                    MIN_ORDER_KRW = 5000

                    if remaining_value < MIN_ORDER_KRW:
                        # 남은 금액이 최소 주문 금액 미만 → 포지션 종료
                        logger.debug(f"   💰 {symbol} 남은 금액 {remaining_value:,.0f}원 < 최소 {MIN_ORDER_KRW:,.0f}원 → 포지션 종료")
                        self.position_manager.close_position(symbol, close_price=avg_price, close_reason="profit")

                        # 거래 기록
                        sell_amount_krw = avg_price * executed_volume  # 실제 체결 금액
                        self.trade_history.add_trade(
                            group_id=group_id,
                            group_name=group_name,
                            symbol=symbol,
                            action="sell",
                            trade_type="profit",
                            price=avg_price,
                            amount=executed_volume,
                            total_krw=sell_amount_krw,
                            dry_run=False,
                            profit_level=level_index + 1
                        )

                        # 🔧 GUI 완료 로그 (한 줄 요약)
                        profit_pct = pending_order.get('profit_pct', 0)
                        avg_buy_price = position.get('avg_buy_price', 0)
                        profit_krw = sell_amount_krw - (avg_buy_price * executed_volume)
                        logger.info(f"[익절완료] {symbol} | {sell_amount_krw:,.0f}원 | {profit_krw:+,.0f}원 ({profit_pct:+.2f}%)")

                        # 텔레그램 알림
                        self._send_telegram_alert(
                            f"✅ 익절 매도 완료 (포지션 종료)\n"
                            f"그룹: {group_name}\n"
                            f"코인: {symbol}\n"
                            f"레벨: {level_index + 1}\n"
                            f"수익률: +{profit_pct:.2f}%\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"매도 금액: {sell_amount_krw:,.0f}원\n"
                            f"매도 수량: {executed_volume:.8f}개\n"
                            f"체결 가격: {avg_price:,.0f}원\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"포지션 전체 종료됨"
                        )

                        # 🔧 GUI 콜백 호출 (중복 알림 방지)
                        if self.on_auto_sell_callback:
                            self.on_auto_sell_callback(symbol, executed_volume)
                    else:
                        # 남은 금액 충분 → 수량만 감소
                        logger.debug(f"   💰 {symbol} 남은 금액 {remaining_value:,.0f}원 → 포지션 유지")
                        updates['total_amount'] = remaining_amount

                        # 거래 기록
                        sell_amount_krw = avg_price * executed_volume  # 실제 체결 금액
                        self.trade_history.add_trade(
                            group_id=group_id,
                            group_name=group_name,
                            symbol=symbol,
                            action="sell",
                            trade_type="profit",
                            price=avg_price,
                            amount=executed_volume,
                            total_krw=sell_amount_krw,
                            dry_run=False,
                            profit_level=level_index + 1
                        )

                        # 🔧 GUI 완료 로그 (한 줄 요약)
                        profit_pct = pending_order.get('profit_pct', 0)
                        avg_buy_price = position.get('avg_buy_price', 0)
                        profit_krw = sell_amount_krw - (avg_buy_price * executed_volume)
                        logger.info(f"[익절완료] {symbol} | {sell_amount_krw:,.0f}원 | {profit_krw:+,.0f}원 ({profit_pct:+.2f}%) | 잔여: {remaining_value:,.0f}원")

                        # 텔레그램 알림
                        self._send_telegram_alert(
                            f"✅ 익절 부분 매도 완료\n"
                            f"그룹: {group_name}\n"
                            f"코인: {symbol}\n"
                            f"레벨: {level_index + 1}\n"
                            f"수익률: +{profit_pct:.2f}%\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"매도 금액: {sell_amount_krw:,.0f}원\n"
                            f"매도 수량: {executed_volume:.8f}개\n"
                            f"체결 가격: {avg_price:,.0f}원\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"남은 수량: {remaining_amount:.8f}개\n"
                            f"남은 금액: {remaining_value:,.0f}원"
                        )

                        # 🔧 GUI 콜백 호출 (중복 알림 방지)
                        if self.on_auto_sell_callback:
                            self.on_auto_sell_callback(symbol, executed_volume)

                # 🆕 Phase B-C: MyOrder 처리 완료 마킹 (MyAsset 백업 스킵용)
                self._mark_processed_by_myorder(symbol)

            elif order_type == 'loss':
                # 레벨 기록
                loss_levels_executed = position.get('loss_levels_executed', [])
                if level_index not in loss_levels_executed:
                    loss_levels_executed.append(level_index)
                    updates['loss_levels_executed'] = loss_levels_executed
                    logger.debug(f"   📝 {symbol} loss_levels_executed 업데이트: {loss_levels_executed}")

                # 🔧 Phase D 버그 수정: 포지션 수량 감소 처리
                group_id = pending_order.get('group_id', 'unknown')
                group_name = pending_order.get('group_name', 'Unknown')

                # 남은 수량 계산
                total_amount = position.get('total_amount', 0)
                remaining_amount = total_amount - executed_volume

                logger.debug(f"   📊 {symbol} 손절 매도 후 수량: {total_amount:.8f} → {remaining_amount:.8f} (매도: {executed_volume:.8f})")

                # 현재가 조회 (최소 주문 금액 체크용)
                current_price = self._get_current_price_safe(symbol)
                if current_price:
                    remaining_value = remaining_amount * current_price
                    MIN_ORDER_KRW = 5000

                    if remaining_value < MIN_ORDER_KRW:
                        # 남은 금액이 최소 주문 금액 미만 → 포지션 종료
                        logger.debug(f"   💰 {symbol} 남은 금액 {remaining_value:,.0f}원 < 최소 {MIN_ORDER_KRW:,.0f}원 → 포지션 종료")
                        self.position_manager.close_position(symbol, close_price=avg_price, close_reason="loss")

                        # 거래 기록
                        sell_amount_krw = avg_price * executed_volume  # 실제 체결 금액
                        self.trade_history.add_trade(
                            group_id=group_id,
                            group_name=group_name,
                            symbol=symbol,
                            action="sell",
                            trade_type="loss",
                            price=avg_price,
                            amount=executed_volume,
                            total_krw=sell_amount_krw,
                            dry_run=False,
                            loss_level=level_index + 1
                        )

                        # 🔧 GUI 완료 로그 (한 줄 요약)
                        loss_pct = pending_order.get('profit_pct', 0)
                        avg_buy_price = position.get('avg_buy_price', 0)
                        profit_krw = sell_amount_krw - (avg_buy_price * executed_volume)
                        logger.info(f"[손절완료] {symbol} | {sell_amount_krw:,.0f}원 | {profit_krw:+,.0f}원 ({loss_pct:+.2f}%)")

                        # 텔레그램 알림
                        self._send_telegram_alert(
                            f"❌ 손절 매도 완료 (포지션 종료)\n"
                            f"그룹: {group_name}\n"
                            f"코인: {symbol}\n"
                            f"레벨: {level_index + 1}\n"
                            f"수익률: {loss_pct:.2f}%\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"매도 금액: {sell_amount_krw:,.0f}원\n"
                            f"매도 수량: {executed_volume:.8f}개\n"
                            f"체결 가격: {avg_price:,.0f}원\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"포지션 전체 종료됨"
                        )

                        # 🔧 GUI 콜백 호출 (중복 알림 방지)
                        if self.on_auto_sell_callback:
                            self.on_auto_sell_callback(symbol, executed_volume)
                    else:
                        # 남은 금액 충분 → 수량만 감소
                        logger.debug(f"   💰 {symbol} 남은 금액 {remaining_value:,.0f}원 → 포지션 유지")
                        updates['total_amount'] = remaining_amount

                        # 거래 기록
                        sell_amount_krw = avg_price * executed_volume  # 실제 체결 금액
                        self.trade_history.add_trade(
                            group_id=group_id,
                            group_name=group_name,
                            symbol=symbol,
                            action="sell",
                            trade_type="loss",
                            price=avg_price,
                            amount=executed_volume,
                            total_krw=sell_amount_krw,
                            dry_run=False,
                            loss_level=level_index + 1
                        )

                        # 🔧 GUI 완료 로그 (한 줄 요약)
                        loss_pct = pending_order.get('profit_pct', 0)
                        avg_buy_price = position.get('avg_buy_price', 0)
                        profit_krw = sell_amount_krw - (avg_buy_price * executed_volume)
                        logger.info(f"[손절완료] {symbol} | {sell_amount_krw:,.0f}원 | {profit_krw:+,.0f}원 ({loss_pct:+.2f}%) | 잔여: {remaining_value:,.0f}원")

                        # 텔레그램 알림
                        self._send_telegram_alert(
                            f"❌ 손절 부분 매도 완료\n"
                            f"그룹: {group_name}\n"
                            f"코인: {symbol}\n"
                            f"레벨: {level_index + 1}\n"
                            f"수익률: {loss_pct:.2f}%\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"매도 금액: {sell_amount_krw:,.0f}원\n"
                            f"매도 수량: {executed_volume:.8f}개\n"
                            f"체결 가격: {avg_price:,.0f}원\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"남은 수량: {remaining_amount:.8f}개\n"
                            f"남은 금액: {remaining_value:,.0f}원"
                        )

                        # 🔧 GUI 콜백 호출 (중복 알림 방지)
                        if self.on_auto_sell_callback:
                            self.on_auto_sell_callback(symbol, executed_volume)

                # 🆕 Phase B-C: MyOrder 처리 완료 마킹 (MyAsset 백업 스킵용)
                self._mark_processed_by_myorder(symbol)

            elif order_type == 'dca':
                # 🔧 중복 처리 방지: 봇 주문 UUID 먼저 기록 (타이밍 이슈 방지)
                self.processed_bot_order_uuids.add(order_uuid)

                # ✅ 중복 체크: 이미 실행된 레벨이면 스킵
                dca_levels_executed = position.get('dca_levels_executed', [])
                if level_index in dca_levels_executed:
                    logger.warning(f"   ⚠️ {symbol} DCA 레벨 {level_index+1} 이미 실행됨 (state=done) → 중복 스킵")
                    self.position_manager.update_position(symbol, {'pending_order': None})
                    return

                # 🔧 Phase D 버그 수정: state=done에서 정확한 최종 평균가 사용
                # DCA 주문 체결 완료 → REST API 조회
                dca_value_krw = pending_order.get('dca_value_krw', 0)
                group_id = pending_order.get('group_id', 'unknown')
                group_name = pending_order.get('group_name', 'Unknown')

                logger.debug(f"   ✅ {symbol} DCA 레벨 {level_index+1} 체결 완료 (state=done, MyOrder avg: {avg_price:,.0f}원, 수량: {executed_volume:.8f})")

                # 🆕 REST API로 정확한 평균가 조회 (체결 반영 대기)
                final_avg_price = avg_price  # fallback
                final_balance = 0  # fallback

                if self.upbit_api:
                    try:
                        # 🔧 Upbit 시스템에 체결 반영될 때까지 대기
                        time.sleep(1.5)
                        accounts = self.upbit_api.get_accounts()
                        for acc in accounts:
                            currency = symbol.replace('KRW-', '')
                            if acc['currency'] == currency:
                                final_avg_price = float(acc.get('avg_buy_price', 0))
                                final_balance = float(acc.get('balance', 0))
                                logger.debug(f"   📊 [최종] {symbol} REST API 평균가: {final_avg_price:,.0f}원 (수량: {final_balance:.8f}개)")
                                break
                    except Exception as e:
                        logger.error(f"❌ {symbol} REST API 평균가 조회 실패 (fallback to MyOrder): {e}")

                # DCA 히스토리 기록
                dca_history = position.get('dca_history', [])
                dca_record = {
                    "level": level_index,
                    "price": avg_price,  # 체결가 기록
                    "amount": executed_volume,
                    "krw": dca_value_krw,
                    "timestamp": datetime.now().isoformat()
                }
                dca_history.append(dca_record)

                # 🔧 DCA 레벨 기록 (중복 방지)
                dca_levels_executed.append(level_index)

                # 포지션 업데이트
                updates['total_amount'] = final_balance
                updates['avg_buy_price'] = final_avg_price
                updates['total_invested_krw'] = final_avg_price * final_balance
                updates['dca_count'] = position.get('dca_count', 0) + 1
                updates['dca_history'] = dca_history
                updates['dca_levels_executed'] = dca_levels_executed

                logger.debug(f"   📝 {symbol} DCA 레벨 {level_index+1} 완료 - dca_levels_executed: {dca_levels_executed}")

                # 거래 기록 (Live 모드에서만, Dry-run은 _execute_dca에서 이미 기록)
                self.trade_history.add_trade(
                    group_id=group_id,
                    group_name=group_name,
                    symbol=symbol,
                    action="buy",
                    trade_type="dca",
                    price=final_avg_price,
                    amount=final_balance,
                    total_krw=dca_value_krw,
                    dry_run=False,  # Live 모드
                    dca_level=level_index + 1  # 1-based for display
                )

                # 🔧 GUI 완료 로그 (한 줄 요약)
                logger.info(f"[DCA완료] {symbol} L{level_index + 1} | {dca_value_krw:,.0f}원 | 평균가 {final_avg_price:,.0f}원 | 보유 {final_balance:.8f}개")

                # 텔레그램 알림
                self._send_telegram_alert(
                    f"🔄 DCA 추가 매수 완료\n"
                    f"그룹: {group_name}\n"
                    f"코인: {symbol}\n"
                    f"레벨: {level_index + 1}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"추가 금액: {dca_value_krw:,.0f}원\n"
                    f"추가 수량: {executed_volume:.8f}개\n"
                    f"체결 가격: {avg_price:,.0f}원\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"평균 매수가: {final_avg_price:,.0f}원\n"
                    f"총 보유량: {final_balance:.8f}개"
                )

                # 🆕 Phase B-C: MyOrder 처리 완료 마킹 (MyAsset 백업 스킵용)
                self._mark_processed_by_myorder(symbol)

                # 🔧 중복 처리 방지: 봇 주문 UUID 기록
                self.processed_bot_order_uuids.add(order_uuid)

            # 포지션 업데이트 (pending_order 제거)
            self.position_manager.update_position(symbol, updates)

            # 🆕 GUI 새로고침 콜백 호출 (포지션 변경됨)
            if self.on_position_created_callback:
                try:
                    self.on_position_created_callback(symbol)
                except Exception as e:
                    logger.error(f"❌ 포지션 변경 GUI 콜백 오류: {e}")

            logger.debug(f"   🎉 {symbol} 주문 {order_uuid[:8]}... 처리 완료")

        except Exception as e:
            logger.error(f"❌ 주문 체결 콜백 처리 오류: {e}", exc_info=True)

    def _find_group_for_symbol(self, symbol: str) -> Optional[str]:
        """
        config.groups를 검색하여 symbol이 속한 그룹 ID 반환

        Args:
            symbol: "KRW-BTC" 형식의 심볼

        Returns:
            그룹 ID (예: "group_1") 또는 None
        """
        config = self.config

        for group_id, group_data in config.get('groups', {}).items():
            coins = group_data.get('coins', [])
            if symbol in coins:
                logger.debug(f"   🔍 {symbol} → 그룹 매칭: {group_id}")
                return group_id

        logger.debug(f"   🔍 {symbol} → 그룹 없음")
        return None

    def _mark_processed_by_myorder(self, symbol: str):
        """
        MyOrder에서 symbol 처리했음을 기록

        Args:
            symbol: "KRW-BTC" 형식
        """
        self._myorder_processed_symbols[symbol] = datetime.now()
        logger.debug(f"   📝 {symbol} MyOrder 처리 기록")

    def _was_recently_processed_by_myorder(self, symbol: str, window_seconds: int = 5) -> bool:
        """
        최근 N초 이내 MyOrder에서 해당 symbol 처리했는지 확인

        Args:
            symbol: "KRW-BTC" 형식
            window_seconds: 윈도우 시간 (기본 5초)

        Returns:
            True if 최근 처리됨, False otherwise
        """
        last_time = self._myorder_processed_symbols.get(symbol)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < window_seconds:
                logger.debug(f"   ⏭️ {symbol} MyOrder에서 {elapsed:.1f}초 전 처리됨")
                return True

        return False

    def _check_global_constraints(self, verbose: bool = False) -> bool:
        """
        전역 제약 확인

        Args:
            verbose: 상세 로그 출력 여부

        Returns:
            거래 가능 여부
        """
        # 관찰 모드 체크
        if verbose:
            logger.info(f"         🔍 observation_mode = {self.observation_mode}")
        if self.observation_mode:
            if verbose:
                logger.info(f"         ❌ 관찰 모드로 인해 거래 불가")
            return False

        # ⚠️ 최소 잔고 체크는 _execute_buy()와 _execute_dca()에서 직접 수행
        # → 매수 직전에만 API 호출 (불필요한 매초 API 호출 방지)

        # 일일 손실 한도 체크
        daily_loss_enabled = self.daily_loss_tracker is not None
        if verbose:
            logger.info(f"         🔍 일일 손실 한도 체크 활성화 = {daily_loss_enabled}")

        if self.daily_loss_tracker and self.daily_loss_tracker.is_limit_reached():
            logger.warning(f"⚠️ 일일 손실 한도 도달로 인해 거래 불가")
            return False

        # 포지션 손실 한도 체크
        position_loss_enabled = self.position_loss_limit_config.get("enabled", False)
        if verbose:
            logger.info(f"         🔍 포지션 손실 한도 체크 활성화 = {position_loss_enabled}")

        if position_loss_enabled:
            # 한도 체크 (이미 도달한 경우 또는 새로 도달한 경우)
            if self._check_position_loss_limit():
                logger.warning(f"⚠️ 포지션 손실 한도 도달로 인해 거래 불가")
                return False

        # 최대 포지션 개수 체크
        max_positions_config = self.global_settings.get("max_positions", {})
        max_positions_enabled = max_positions_config.get("enabled", False)
        if verbose:
            logger.info(f"         🔍 최대 포지션 개수 체크 활성화 = {max_positions_enabled}")

        if max_positions_enabled:
            max_limit = max_positions_config.get("limit", 3)

            # 현재 활성 포지션 개수 계산 (observation_only 그룹 제외)
            all_positions = self.position_manager.get_active_positions()  # status='active'인 포지션만
            active_positions = 0

            # 1. 기존 포지션 카운트
            for symbol, position in all_positions.items():
                group_id = position.get("group_id")
                if group_id and group_id in self.config.get("groups", {}):
                    group = self.config["groups"][group_id]
                    # observation_only가 True인 그룹은 제외
                    if not group.get("observation_only", False):
                        active_positions += 1

            # 2. pending 초기 매수 주문도 카운트 (observation_only 그룹 제외)
            pending_count = 0
            for pending in self.pending_initial_buys.values():
                pending_group_id = pending.get('group_id')
                if pending_group_id and pending_group_id in self.config.get("groups", {}):
                    pending_group = self.config["groups"][pending_group_id]
                    if not pending_group.get("observation_only", False):
                        active_positions += 1
                        pending_count += 1

            if verbose:
                logger.info(f"         🔍 현재 포지션: {active_positions}개 (포지션: {len(all_positions)}개 + pending: {pending_count}개) / 최대: {max_limit}개")

            if active_positions >= max_limit:
                position_count = len(all_positions)

                # 최초 도달 시에만 경고 출력 (로그 스팸 방지)
                if not self.max_position_warning_shown:
                    logger.warning(f"⚠️ 최대 포지션 개수 도달로 인해 거래 불가 (포지션: {position_count}개 + pending: {pending_count}개 = 총 {active_positions}개 >= 최대: {max_limit}개)")
                    logger.info(f"ℹ️  이 경고는 포지션이 감소할 때까지 다시 표시되지 않습니다.")
                    self.max_position_warning_shown = True

                return False

            # 최대 포지션 미만이면 플래그 해제
            else:
                if self.max_position_warning_shown:
                    logger.info(f"✅ 최대 포지션 해제 (현재: {active_positions}개 < 최대: {max_limit}개) - 신규 매수 가능")
                    self.max_position_warning_shown = False

        if verbose:
            logger.info(f"         ✅ 전역 제약 모두 통과")
        return True

    def _get_current_price_safe(self, symbol: str) -> Optional[float]:
        """
        현재가 안전 조회 (WebSocket 우선, REST API fallback)

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')

        Returns:
            float: 현재가 (실패 시 None)
        """
        try:
            # 🚀 우선순위 1: WebSocketManager에서 실시간 현재가 가져오기
            if self.websocket_manager and self.websocket_manager.is_running:
                current_price = self.websocket_manager.get_current_price(symbol)

                if current_price is not None:
                    logger.debug(f"🌐 WebSocket 현재가 사용: {symbol} = {current_price:,.0f}")
                    return current_price
                else:
                    logger.debug(f"⚠️ WebSocket 현재가 없음: {symbol}, REST API로 fallback")

            # 📡 우선순위 2: REST API (fallback)
            if self.upbit_api:
                ticker = self.upbit_api.get_ticker(symbol)
                if ticker and 'trade_price' in ticker:
                    price = float(ticker['trade_price'])
                    logger.debug(f"📊 REST API 현재가 사용: {symbol} = {price:,.0f}")
                    return price
                else:
                    logger.error(f"❌ {symbol} 현재가 조회 실패: ticker 데이터 없음")
                    return None
            else:
                logger.error(f"❌ {symbol} 현재가 조회 실패: WebSocket 및 UpbitAPI 모두 없음")
                return None

        except SymbolNotFoundError as e:
            # 404 에러: 상장폐지된 코인 → 스킵 리스트에 추가
            logger.warning(f"⏭️ {symbol}: 스킵 리스트에 추가 (상장폐지)")
            self.skipped_symbols.add(symbol)
            return None

        except Exception as e:
            logger.error(f"❌ {symbol} 현재가 조회 오류: {e}")
            return None

    def _calculate_trading_groups_profit_loss(self) -> dict:
        """
        거래 그룹의 합산 손익 계산 (관찰 그룹 제외)

        Returns:
            dict: {
                "total_invested": 총 투자금,
                "total_profit_loss": 총 손익금,
                "total_profit_loss_pct": 합산 수익률 (%),
                "positions": [포지션 상세 리스트]
            }
        """
        total_invested = 0.0
        total_profit_loss = 0.0
        position_details = []

        # 모든 그룹 조회
        all_groups = self.group_manager.get_all_groups()

        for group_id, group in all_groups.items():
            # 관찰 전용 그룹 제외
            if group.get("observation_mode", False):
                logger.debug(f"⏭️ 손익 계산 제외 (관찰 그룹): {group.get('name', group_id)}")
                continue

            # 해당 그룹의 코인들
            group_coins = group.get("coins", [])

            for symbol in group_coins:
                # 포지션 존재 여부 확인 (활성 포지션만)
                active_positions = self.position_manager.get_active_positions()
                position = None

                for pos_id, pos in active_positions.items():
                    if pos.get("symbol") == symbol and pos.get("group_id") == group_id:
                        position = pos
                        break

                if not position:
                    continue

                # 현재가 조회
                current_price = self._get_current_price_safe(symbol)
                if not current_price:
                    logger.warning(f"⚠️ {symbol} 현재가 조회 실패, 손익 계산 스킵")
                    continue

                # 수익률 계산
                avg_price = position.get('avg_price', 0)
                amount = position.get('amount', 0)
                invested = position.get('total_invested', 0)

                if invested == 0:
                    continue

                current_value = amount * current_price
                profit_loss = current_value - invested
                profit_loss_pct = (profit_loss / invested) * 100

                total_invested += invested
                total_profit_loss += profit_loss

                position_details.append({
                    "symbol": symbol,
                    "group_id": group_id,
                    "invested": invested,
                    "current_value": current_value,
                    "profit_loss": profit_loss,
                    "profit_loss_pct": profit_loss_pct
                })

                logger.debug(f"   {symbol}: {profit_loss:+,.0f}원 ({profit_loss_pct:+.2f}%)")

        # 합산 수익률 계산
        if total_invested > 0:
            total_profit_loss_pct = (total_profit_loss / total_invested) * 100
        else:
            total_profit_loss_pct = 0.0

        return {
            "total_invested": total_invested,
            "total_profit_loss": total_profit_loss,
            "total_profit_loss_pct": total_profit_loss_pct,
            "positions": position_details
        }

    def _get_recent_candles(self, symbol: str, candle_unit: str, count: int = 200):
        """
        최근 캔들 데이터 가져오기 (WebSocket 우선, REST API fallback)

        Args:
            symbol: 코인 심볼
            candle_unit: 캔들 단위 (분, 예: "15", "60", "240")
            count: 캔들 개수

        Returns:
            DataFrame: 캔들 데이터 (과거 199개 + 현재 진행 중 1개)
        """
        try:
            # 🚀 우선순위 1: WebSocketManager에서 실시간 캔들 가져오기
            if self.websocket_manager and self.websocket_manager.is_running:
                candles = self.websocket_manager.get_candles(symbol, count)

                if candles is not None and not candles.empty:
                    logger.debug(f"🌐 WebSocket 캔들 사용: {symbol} ({candle_unit}분봉, {len(candles)}개)")
                    return candles
                else:
                    logger.debug(f"⚠️ WebSocket 캔들 없음: {symbol}, REST API로 fallback")

            # 📡 우선순위 2: REST API (fallback)
            if not self.upbit_api:
                logger.error(f"❌ {symbol} 캔들 조회 실패: UpbitAPI 및 WebSocket 모두 없음")
                return None

            # 캐시 키 생성
            cache_key = f"{symbol}_minute{candle_unit}"
            now = datetime.now()

            # 캐시 확인
            if cache_key in self.candle_cache:
                cached = self.candle_cache[cache_key]
                expire_time = cached.get("expire_time")

                if now < expire_time:
                    # 캐시 유효 → 사용
                    logger.debug(f"✅ 캐시 사용: {symbol} ({candle_unit}분봉)")
                    return cached["candles"]
                else:
                    logger.debug(f"⏰ 캐시 만료: {symbol} ({candle_unit}분봉)")

            # 캐시 없거나 만료 → API 조회
            logger.debug(f"📊 REST API 조회: {symbol} ({candle_unit}분봉)")
            interval = f"minute{candle_unit}"
            candles = self.upbit_api.get_candles(symbol, interval=interval, count=count)

            if candles is None or len(candles) == 0:
                return None

            # 다음 캔들 완성 시간 계산
            expire_time = self._calculate_next_candle_time(now, int(candle_unit))

            # 캐시 저장
            self.candle_cache[cache_key] = {
                "candles": candles,
                "last_update": now,
                "expire_time": expire_time
            }

            logger.debug(f"💾 캐시 저장: {symbol} ({candle_unit}분봉, 만료: {expire_time.strftime('%H:%M:%S')})")

            return candles

        except SymbolNotFoundError as e:
            # 404 에러: 상장폐지된 코인 → 스킵 리스트에 추가
            logger.warning(f"⏭️ {symbol}: 스킵 리스트에 추가 (상장폐지)")
            self.skipped_symbols.add(symbol)
            return None

        except Exception as e:
            logger.error(f"❌ {symbol} 캔들 데이터 조회 오류: {e}")
            return None

    def _calculate_next_candle_time(self, now: datetime, candle_minutes: int) -> datetime:
        """
        다음 캔들 완성 시간 계산

        Args:
            now: 현재 시간
            candle_minutes: 캔들 단위 (분)

        Returns:
            다음 캔들 완성 시간
        """
        if candle_minutes == 15:
            # 다음 15분 정각 (00, 15, 30, 45)
            next_minute = ((now.minute // 15) + 1) * 15
            if next_minute >= 60:
                return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            else:
                return now.replace(minute=next_minute, second=0, microsecond=0)

        elif candle_minutes == 60:
            # 다음 정각
            return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

        elif candle_minutes == 240:
            # 다음 4시간 정각 (00, 04, 08, 12, 16, 20)
            next_hour = ((now.hour // 4) + 1) * 4
            if next_hour >= 24:
                return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                return now.replace(hour=next_hour, minute=0, second=0, microsecond=0)

        else:
            # 기타 봉 크기는 기본적으로 봉 크기만큼 캐시
            return now + timedelta(minutes=candle_minutes)

    def _check_min_balance(self, required_amount: float) -> bool:
        """
        최소 잔고 체크 (매수/DCA 직전에만 호출)

        Args:
            required_amount: 필요한 KRW 금액

        Returns:
            bool: True면 잔고 충분, False면 잔고 부족
        """
        krw_balance = self._get_krw_balance()
        min_balance_config = self.global_settings.get("min_balance", {})
        min_balance_enabled = min_balance_config.get("enabled", False)

        if not min_balance_enabled:
            # 최소 잔고 체크 비활성화 시, 필요 금액만 확인
            if krw_balance < required_amount:
                logger.warning(f"⚠️ 잔고 부족: {krw_balance:,.0f}원 < {required_amount:,.0f}원")
                return False
            return True

        # 최소 잔고 활성화 시
        min_reserve = min_balance_config.get("amount", 50000)

        if krw_balance < (required_amount + min_reserve):
            logger.warning(
                f"⚠️ 잔고 부족: {krw_balance:,.0f}원 < "
                f"{required_amount:,.0f}원 (필요) + {min_reserve:,.0f}원 (예비) = "
                f"{required_amount + min_reserve:,.0f}원"
            )
            return False

        return True

    def _get_krw_balance(self) -> float:
        """
        KRW 잔고 조회 (캐시 적용)

        Rate Limit 방지를 위해 60초 TTL 캐시 사용
        매수/DCA 직전에만 호출되므로 긴 TTL 적용
        """
        try:
            # 캐시 유효성 확인
            now = time.time()
            last_updated = self.balance_cache.get("last_updated")
            ttl = self.balance_cache.get("ttl", 1.0)

            if last_updated and (now - last_updated) < ttl:
                # 캐시 사용
                logger.debug(f"💾 잔고 캐시 사용 (나이: {now - last_updated:.2f}초)")
                return self.balance_cache["krw"]

            # 캐시 만료 또는 없음 → API 호출
            logger.debug("📊 계좌 정보 조회 중...")

            if self.dry_run or not self.upbit_api:
                # Dry-run 모드: 가상 잔고
                balances = self.position_manager.get_virtual_balances()
                krw_balance = balances.get("KRW", 0.0)
            else:
                # Live 모드: 실제 잔고
                balance = self.upbit_api.get_balance("KRW")
                krw_balance = float(balance) if balance else 0.0

            # 캐시 업데이트
            self.balance_cache["krw"] = krw_balance
            self.balance_cache["last_updated"] = now

            logger.debug(f"💰 KRW 잔고: {krw_balance:,.2f}")
            return krw_balance

        except Exception as e:
            logger.error(f"❌ KRW 잔고 조회 오류: {e}")
            # 에러 시 캐시 있으면 캐시 반환
            if self.balance_cache.get("last_updated"):
                logger.warning(f"⚠️ 에러 발생, 이전 캐시 사용")
                return self.balance_cache["krw"]
            return 0.0

    def _get_total_valuation(self) -> float:
        """전체 자산 평가액 (KRW + 보유 코인 평가액)"""
        try:
            krw_balance = self._get_krw_balance()

            # 활성 포지션의 현재가 평가액
            active_positions = self.position_manager.get_active_positions()
            coin_value = 0.0

            for symbol, position in active_positions.items():
                current_price = self._get_current_price_safe(symbol)
                if current_price:
                    total_amount = position.get("total_amount", 0)
                    coin_value += current_price * total_amount

            return krw_balance + coin_value

        except Exception as e:
            logger.error(f"❌ 자산 평가액 계산 오류: {e}")
            return 0.0

    def _check_position_loss_limit(self) -> bool:
        """
        포지션 손실 한도 체크

        Returns:
            bool: True면 한도 도달 (거래 중단), False면 정상
        """
        # 설정 확인
        if not self.position_loss_limit_config.get("enabled", False):
            return False  # 비활성화 상태

        # 이미 한도 도달한 경우
        if self.loss_limit_reached:
            logger.debug("⚠️ 이미 포지션 손실 한도 도달 상태 (재시작 필요)")
            return True

        # 손익 계산
        result = self._calculate_trading_groups_profit_loss()

        total_pct = result["total_profit_loss_pct"]
        limit_pct = self.position_loss_limit_config.get("limit_pct", -10.0)

        logger.debug(f"💰 거래 그룹 합산 수익률: {total_pct:+.2f}% (한도: {limit_pct}%)")

        # 한도 체크
        if total_pct <= limit_pct:
            logger.error(f"🚨 포지션 손실 한도 도달!")
            logger.error(f"   합산 수익률: {total_pct:.2f}% ≤ 한도: {limit_pct}%")
            logger.error(f"   총 투자금: {result['total_invested']:,.0f}원")
            logger.error(f"   총 손익금: {result['total_profit_loss']:+,.0f}원")

            # 상세 내역 로그
            for pos in result["positions"]:
                logger.error(f"   - {pos['symbol']}: {pos['profit_loss']:+,.0f}원 "
                           f"({pos['profit_loss_pct']:+.2f}%)")

            # 플래그 설정
            self.loss_limit_reached = True
            self.loss_limit_reached_time = datetime.now()

            # 액션 실행
            action = self.position_loss_limit_config.get("action", "alert")

            if action == "liquidate":
                logger.error("🔴 전량 청산 시작...")
                self._liquidate_all_positions(reason="포지션 손실 한도 도달")
            elif action == "alert":
                logger.warning("⚠️ 텔레그램 알림 발송...")
                self._send_loss_limit_alert(result)

            return True

        return False

    def _send_loss_limit_alert(self, result: dict):
        """포지션 손실 한도 도달 알림"""
        message = f"""
🚨 포지션 손실 한도 도달!

📊 합산 수익률: {result['total_profit_loss_pct']:+.2f}%
💰 총 투자금: {result['total_invested']:,.0f}원
💸 총 손익금: {result['total_profit_loss']:+,.0f}원

📋 포지션 상세:
"""

        for pos in result["positions"]:
            message += f"- {pos['symbol']}: {pos['profit_loss']:+,.0f}원 ({pos['profit_loss_pct']:+.2f}%)\n"

        message += "\n⚠️ 매수가 중단됩니다. 프로그램 재시작 필요."

        self._send_telegram_alert(message)

    def _liquidate_all_positions(self, reason: str = "일일 손실 한도 도달"):
        """모든 포지션 청산"""
        logger.warning(f"🚨 모든 포지션 청산 시작 (사유: {reason})")

        all_positions = self.position_manager.get_all_positions()

        for symbol, position in all_positions.items():
            if position.get("status") != "active":
                continue

            # 그룹 찾기
            group_tuple = self.group_manager.get_group_by_symbol(symbol)
            if not group_tuple:
                continue

            group_id, group = group_tuple

            # 매도 실행
            self._execute_sell(symbol, group_id, group, "emergency", quantity_ratio=1.0)

        logger.warning(f"✅ 모든 포지션 청산 완료")

    def _send_telegram_alert(self, message: str):
        """텔레그램 알림 전송 (동기 방식) - GUI 로그 없이 텔레그램만 전송"""
        # 텔레그램 봇 전송
        if self.telegram_bot:
            def send_sync():
                """동기 메시지 전송 (requests 라이브러리 사용, async 회피)"""
                try:
                    import requests
                    url = f"https://api.telegram.org/bot{self.telegram_bot.token}/sendMessage"
                    payload = {
                        "chat_id": self.telegram_bot.chat_id,
                        "text": message
                    }
                    response = requests.post(url, json=payload, timeout=10)
                    response.raise_for_status()
                    logger.debug(f"📤 텔레그램 전송 완료")
                except Exception as e:
                    logger.error(f"❌ 텔레그램 메시지 전송 실패: {e}")

            # 별도 스레드에서 동기 전송 (메인 루프 블로킹 방지)
            thread = threading.Thread(target=send_sync, daemon=True)
            thread.start()

    def _run_scheduler(self):
        """스케줄러 실행 (09:00 리셋 등)"""
        logger.info("⏰ 스케줄러 시작")

        # 09:00 리셋 스케줄 등록
        if self.daily_loss_tracker:
            schedule.every().day.at("09:00").do(self._daily_reset_task)

        while not self.stop_event.is_set():
            try:
                schedule.run_pending()
                self.stop_event.wait(60)  # 1분마다 체크
            except Exception as e:
                logger.error(f"❌ 스케줄러 오류: {e}", exc_info=True)

        logger.info("🛑 스케줄러 종료")

    def _daily_reset_task(self):
        """일일 리셋 작업"""
        logger.info("🌅 09:00 일일 리셋 시작")

        if self.daily_loss_tracker:
            self.daily_loss_tracker.check_and_reset()

        logger.info("✅ 09:00 일일 리셋 완료")

    # ========================================
    # 🔧 Pending Order 복구 & 수동 매수 감지
    # ========================================

    def _recover_pending_orders(self):
        """
        재시작 시 pending_order 복구

        프로그램이 종료되기 전에 보낸 주문이 있으면
        Upbit API로 주문 상태를 확인하고 체결 완료된 주문은
        포지션으로 복구합니다.

        Note:
            - order_id로 정확히 "내 주문"인지 확인 가능
            - 복구된 주문은 텔레그램 알림 발송
            - 체결 완료 or 취소된 주문은 pending_order에서 제거
        """
        if not self.pending_order_mgr:
            return

        pending_orders = self.pending_order_mgr.get_all_orders()

        if not pending_orders:
            logger.info("ℹ️ 복구할 pending_order 없음")
            return

        logger.info(f"📋 pending_order {len(pending_orders)}개 발견, 복구 시작...")

        recovered_count = 0
        removed_count = 0

        for order in pending_orders:
            order_id = order['order_id']
            symbol = order['symbol']
            group_id = order.get('group_id', 'unknown')

            try:
                # Upbit API로 주문 상태 조회
                order_status = self.upbit_api.get_order(order_id)

                state = order_status.get('state')
                logger.info(f"  📝 {symbol}: order_id={order_id[:8]}... state={state}")

                if state == 'done':
                    # ✅ 체결 완료 → 포지션 생성
                    self._create_position_from_recovered_order(order, order_status, group_id)
                    self.pending_order_mgr.remove_order(order_id)
                    recovered_count += 1

                    # 텔레그램 알림
                    if self.telegram_bot:
                        trades = order_status.get('trades', [])
                        executed_volume = sum(float(t['volume']) for t in trades)
                        executed_funds = sum(float(t['funds']) for t in trades)
                        avg_price = executed_funds / executed_volume if executed_volume > 0 else 0

                        self.telegram_bot.send_message(
                            f"✅ [{symbol}] 매수 완료 (복구됨)\n"
                            f"평단가: {avg_price:,.0f}원\n"
                            f"수량: {executed_volume:.8f}개\n"
                            f"총액: {executed_funds:,.0f}원\n\n"
                            f"프로그램 재시작 시 복구된 주문입니다."
                        )

                elif state in ['wait', 'watch']:
                    # ⏳ 아직 대기 중 → 그대로 유지
                    logger.info(f"  ⏳ {symbol}: 주문 대기 중, pending_order 유지")

                else:
                    # ❌ 취소됨 or 기타 → 제거
                    logger.warning(f"  ❌ {symbol}: 주문 취소/실패 (state={state}), pending_order 제거")
                    self.pending_order_mgr.remove_order(order_id)
                    removed_count += 1

            except Exception as e:
                logger.error(f"  ❌ {symbol}: 주문 복구 실패 ({order_id[:8]}...) - {e}")
                # 에러 발생 시 pending_order는 유지 (다음 재시작 시 재시도)

        logger.info(
            f"✅ pending_order 복구 완료: "
            f"복구={recovered_count}, 제거={removed_count}, 대기={len(self.pending_order_mgr.get_all_orders())}"
        )

    def _create_position_from_recovered_order(self, order: dict, order_status: dict, group_id: str):
        """
        복구된 주문으로 포지션 생성

        Args:
            order: pending_order 데이터
            order_status: Upbit API에서 조회한 주문 상태
            group_id: V4 그룹 ID
        """
        symbol = order['symbol']
        trades = order_status.get('trades', [])

        if not trades:
            logger.warning(f"⚠️ {symbol}: trades 없음, 포지션 생성 불가")
            return

        # 체결 내역에서 평단가 계산
        executed_volume = sum(float(t['volume']) for t in trades)
        executed_funds = sum(float(t['funds']) for t in trades)
        avg_price = executed_funds / executed_volume if executed_volume > 0 else 0

        # 포지션 생성
        try:
            position = self.position_manager.create_position(
                group_id=group_id,
                symbol=symbol,
                buy_price=avg_price,
                amount=executed_volume,
                source="auto"  # 프로그램이 주문한 것
            )
            logger.info(
                f"  ✅ {symbol}: 포지션 생성 완료 "
                f"(평단가={avg_price:,.0f}원, 수량={executed_volume:.8f}개)"
            )

        except Exception as e:
            logger.error(f"  ❌ {symbol}: 포지션 생성 실패 - {e}")

    def _sync_external_positions_on_startup(self):
        """
        재시작 시 수동 매수 조용히 추가 (알림 없음)

        프로그램이 꺼져있는 동안 사용자가 Upbit 앱에서 수동 매수한 코인을
        포지션에 추가합니다.

        Note:
            - **알림을 보내지 않음** (재시작 시는 프로그램과 무관한 매수)
            - Upbit 잔고와 positions를 비교하여 차이 발견
            - source="external"로 포지션 생성
        """
        if not self.upbit_api:
            return

        try:
            # Upbit 잔고 조회
            accounts = self.upbit_api.get_accounts()
            current_positions = self.position_manager.get_all_positions()

            # 기존 포지션 심볼 목록
            existing_symbols = {pos['symbol'] for pos in current_positions.values()}

            external_count = 0

            for account in accounts:
                currency = account.get('currency')
                balance = float(account.get('balance', 0))

                if currency == 'KRW':
                    continue

                if balance <= 0:
                    continue

                symbol = f"KRW-{currency}"

                # 이미 포지션에 있으면 스킵
                if symbol in existing_symbols:
                    continue

                # 수동 매수 발견!
                avg_buy_price = float(account.get('avg_buy_price', 0))

                # 에어드랍 코인 스킵 (평단가 0원)
                if avg_buy_price <= 0:
                    logger.info(f"  ⏭️ {symbol}: 에어드랍 코인 (평단가 0원) - 스킵")
                    continue

                logger.info(
                    f"  ℹ️ {symbol}: 재시작 시 수동 매수 감지 "
                    f"(평단가={avg_buy_price:,.0f}원, 수량={balance:.8f}개)"
                )

                # 그룹 결정 (첫 번째 활성화된 그룹에 추가)
                groups = self.group_manager.get_all_groups()
                active_group_ids = [gid for gid, g in groups.items() if g.get('enabled', True)]

                if not active_group_ids:
                    logger.warning(f"  ⚠️ {symbol}: 활성화된 그룹 없음, 포지션 생성 불가")
                    continue

                group_id = active_group_ids[0]

                # 포지션 생성 (source=external)
                try:
                    self.position_manager.create_position(
                        group_id=group_id,
                        symbol=symbol,
                        buy_price=avg_buy_price,
                        entry_amount=balance,
                        source="external"
                    )
                    external_count += 1

                    # ⚠️ 알림 보내지 않음 (재시작 시)
                    logger.info(f"  ✅ {symbol}: 수동 매수 포지션 추가 (알림 없음)")

                except Exception as e:
                    logger.error(f"  ❌ {symbol}: 수동 매수 포지션 생성 실패 - {e}")

            if external_count > 0:
                logger.info(f"✅ 재시작 시 수동 매수 {external_count}개 추가 완료 (알림 없음)")
            else:
                logger.info("ℹ️ 재시작 시 수동 매수 없음")

        except Exception as e:
            logger.error(f"❌ 재시작 시 수동 매수 동기화 실패: {e}", exc_info=True)

    async def _handle_order_event(self, order_data: dict):
        """
        WebSocket myOrder 이벤트 처리 (실행 중 수동 매수 감지)

        Args:
            order_data: myOrder 데이터
                {
                    "type": "myOrder",
                    "code": "KRW-VIRTUAL",
                    "uuid": "xyz789",
                    "ask_bid": "BID",
                    "state": "done",
                    "executed_volume": 20.0,
                    "price": 5000.0
                }

        Note:
            - pending_order에 있으면: 프로그램 주문 (알림 없음, OrderManager가 처리)
            - pending_order에 없으면: 수동 매수 (즉시 알림!)
        """
        try:
            # 매수만 처리
            if order_data.get('ask_bid') != 'BID':
                return

            # 체결 완료만 처리
            if order_data.get('state') != 'done':
                return

            order_id = order_data.get('uuid')
            symbol = order_data.get('code')

            # pending_order에 있는지 확인
            pending_order = self.pending_order_mgr.get_order(order_id) if self.pending_order_mgr else None

            if pending_order:
                # ✅ 프로그램이 주문한 것
                logger.info(
                    f"📝 [{symbol}] 프로그램 주문 체결 감지 "
                    f"(order_id={order_id[:8]}..., OrderManager에서 처리)"
                )
                # OrderManager에서 이미 처리하므로 여기서는 아무것도 안 함

            else:
                # ✅ 수동 매수! (Upbit 앱에서 수동 주문)
                logger.info(
                    f"🔔 [{symbol}] 수동 매수 감지! (실시간) "
                    f"(order_id={order_id[:8]}...)"
                )
                await self._handle_external_buy_realtime(order_data)

        except Exception as e:
            logger.error(f"❌ myOrder 이벤트 처리 실패: {e}", exc_info=True)

    async def _handle_external_buy_realtime(self, order_data: dict):
        """
        실행 중 수동 매수 처리 (실시간 알림)

        Args:
            order_data: myOrder 데이터

        Note:
            - 프로그램 실행 중 수동 매수만 알림
            - 포지션 생성 + 텔레그램 즉시 알림
        """
        symbol = order_data.get('code')
        price = float(order_data.get('price', 0))
        executed_volume = float(order_data.get('executed_volume', 0))

        logger.info(
            f"🔔 [{symbol}] 수동 매수 처리: "
            f"평단가={price:,.0f}원, 수량={executed_volume:.8f}개"
        )

        # 그룹 결정 (첫 번째 활성화된 그룹)
        groups = self.group_manager.get_all_groups()
        active_groups = [g for g in groups.values() if g.get('enabled', True)]

        if not active_groups:
            logger.warning(f"⚠️ [{symbol}] 활성화된 그룹 없음, 포지션 생성 불가")
            return

        group_id = active_groups[0]['group_id']

        # 포지션 생성
        try:
            position = self.position_manager.create_position(
                group_id=group_id,
                symbol=symbol,
                buy_price=price,
                amount=executed_volume,
                source="external"
            )

            logger.info(f"✅ [{symbol}] 수동 매수 포지션 생성 완료")

            # 📱 텔레그램 즉시 알림! (실행 중 수동 매수)
            if self.telegram_bot:
                executed_funds = price * executed_volume

                self.telegram_bot.send_message(
                    f"ℹ️ [{symbol}] 수동 매수 감지! (실시간)\n\n"
                    f"평단가: {price:,.0f}원\n"
                    f"수량: {executed_volume:.8f}개\n"
                    f"총액: {executed_funds:,.0f}원\n\n"
                    f"⚠️ 이 포지션은 외부에서 매수되었습니다.\n"
                    f"그룹: {group_id}\n"
                    f"DCA/익절/손절이 적용됩니다."
                )

        except Exception as e:
            logger.error(f"❌ [{symbol}] 수동 매수 포지션 생성 실패: {e}", exc_info=True)


# 테스트 코드
if __name__ == "__main__":
    import sys

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    print("=" * 60)
    print("V4TradingEngine 테스트")
    print("=" * 60)

    try:
        # V4TradingEngine 생성 (Dry-run 모드)
        engine = V4TradingEngine(
            config_path="config/trading_config.json",
            upbit_api=None  # Dry-run
        )

        print("\n✅ V4TradingEngine 생성 완료")
        print(f"  - 모드: {'Dry-run' if engine.dry_run else 'Live'}")
        print(f"  - 관찰 모드: {engine.observation_mode}")
        print(f"  - 그룹 수: {len(engine.group_manager.get_all_groups())}")

        # 시작
        print("\n🚀 엔진 시작...")
        engine.start()

        print("\n✅ 엔진 실행 중 (10초 대기)...")
        time.sleep(10)

        # 중지
        print("\n🛑 엔진 중지...")
        engine.stop()

        print("\n✅ 테스트 완료")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
