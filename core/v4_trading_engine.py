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
from core.upbit_api import UpbitAPI, SymbolNotFoundError
from core.websocket_manager import WebSocketManager

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
        upbit_api: Optional[UpbitAPI] = None
    ):
        """
        V4TradingEngine 초기화

        Args:
            config_path: 설정 파일 경로
            upbit_api: Upbit API 인스턴스 (None이면 dry-run 모드)
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

        # 포지션 관리
        self.position_manager = PositionManager(mode=mode, upbit_api=upbit_api)

        # 거래 내역
        self.trade_history = TradeHistoryManager()

        # Upbit API
        self.upbit_api = upbit_api

        # 일일 손실 추적
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

        # 그룹별 전략 캐시
        self.strategies: Dict[str, Dict[str, V4AutoBuyStrategy]] = {}  # {group_id: {symbol: strategy}}

        # 캔들 데이터 캐시
        self.candles_cache: Dict[str, Dict[str, Any]] = {}  # {symbol: {candle_unit: candles}}

        # 🔧 잔고 캐시 (Rate Limit 방지)
        self.balance_cache: Dict[str, Any] = {
            "krw": 0.0,
            "last_updated": None,
            "ttl": 1.0  # 1초 TTL
        }

        # 🔧 캔들 캐시 (봉 크기별 스마트 캐싱)
        # {symbol_interval: {"candles": DataFrame, "expire_time": datetime}}
        self.candle_cache: Dict[str, Dict[str, Any]] = {}

        # 🔧 스킵 리스트 (404 에러 발생한 코인)
        self.skipped_symbols: set = set()

        # 실행 상태
        self.is_running = False
        self.stop_event = threading.Event()

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
                sync_result = self.position_manager.sync_with_upbit(
                    self.config,
                    accounts=accounts
                )
                logger.info(f"✅ 동기화 완료: {sync_result}")
            except Exception as e:
                logger.error(f"❌ 동기화 실패: {e}")

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

    def stop(self):
        """거래 중지"""
        if not self.is_running:
            logger.warning("⚠️ 이미 중지되어 있습니다")
            return

        logger.info("🛑 V4 거래 엔진 중지 중...")
        self.is_running = False
        self.stop_event.set()

        # 🚀 WebSocket 종료
        if self.websocket_manager and self.websocket_manager.is_running:
            logger.info("🌐 WebSocket 연결 종료 중...")
            try:
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

            # 그룹의 각 코인에 대한 전략 생성
            for symbol in group.get("coins", []):
                try:
                    strategy = V4AutoBuyStrategy(
                        symbol=symbol,
                        investment_style=auto_config.get("investment_style", "balanced"),
                        candle_unit=auto_config.get("candle_unit", "60"),
                        indicators_config=auto_config.get("indicators", {})
                    )

                    self.strategies[group_id][symbol] = strategy
                    logger.info(f"  - {group['name']}: {symbol} 전략 생성 완료")

                except Exception as e:
                    logger.error(f"❌ {symbol} 전략 생성 실패: {e}")

        logger.info(f"✅ 총 {sum(len(s) for s in self.strategies.values())}개 전략 초기화 완료")

    async def _initialize_websockets_async(self):
        """WebSocket 및 CandleAggregator 초기화 (asyncio)"""
        logger.info("🌐 WebSocket 및 CandleAggregator 초기화 중...")

        all_groups = self.group_manager.get_all_groups()
        total_added = 0

        for group_id, group in all_groups.items():
            # 자동 매수 모드가 아니면 스킵
            buy_settings = group.get("buy_settings", {})
            if buy_settings.get("mode") != "auto":
                continue

            auto_config = buy_settings.get("auto_config", {})
            candle_unit = int(auto_config.get("candle_unit", "60"))

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
                    logger.info(f"  - {group['name']}: {symbol} WebSocket 추가 완료")

                except Exception as e:
                    logger.error(f"❌ {symbol} WebSocket 추가 실패: {e}")

        logger.info(f"✅ 총 {total_added}개 코인 WebSocket 초기화 완료")

        # 모든 WebSocket 연결 시작
        logger.info("🚀 WebSocket 연결 시작 중...")
        await self.websocket_manager.start_all()

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
                            self._process_symbol(symbol, group_id, group)
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

    def _process_symbol(self, symbol: str, group_id: str, group: Dict[str, Any]):
        """
        코인 처리 (매수 신호 확인, 포지션 관리)

        Args:
            symbol: 코인 심볼 (예: KRW-BTC)
            group_id: 그룹 ID
            group: 그룹 데이터
        """
        # 0. 스킵 리스트 체크 (404 에러 발생한 코인)
        if symbol in self.skipped_symbols:
            logger.info(f"      ⏭️ {symbol}: 스킵됨 (상장폐지 또는 404 에러)")
            return

        # 1. 전역 제약 확인
        constraints_ok = self._check_global_constraints()
        logger.info(f"      🔧 {symbol}: 전역 제약 체크 = {constraints_ok}")
        if not constraints_ok:
            logger.info(f"      ⏭️ {symbol}: 전역 제약 실패로 스킵")
            return

        # 2. 매수 신호 확인 (포지션이 없는 경우)
        position = self.position_manager.get_position(symbol)
        logger.info(f"      📊 {symbol}: 포지션 존재 = {position is not None}")

        if not position and group.get("buy_settings", {}).get("mode") == "auto":
            logger.info(f"      🎯 {symbol}: 매수 신호 체크 시작")
            self._check_buy_signal(symbol, group_id, group)
        elif position:
            logger.info(f"      🎯 {symbol}: 포지션 관리 시작")
            self._manage_position(symbol, group_id, group)
        else:
            buy_mode = group.get("buy_settings", {}).get("mode", "unknown")
            logger.info(f"      ⏭️ {symbol}: 매수 신호 체크 스킵 (mode={buy_mode})")

    def _check_buy_signal(self, symbol: str, group_id: str, group: Dict[str, Any]):
        """
        매수 신호 확인

        Args:
            symbol: 코인 심볼
            group_id: 그룹 ID
            group: 그룹 데이터
        """
        # 전략 가져오기
        logger.info(f"         🔍 전략 검색: group_id={group_id}, symbol={symbol}")
        logger.info(f"         🔍 self.strategies.keys() = {list(self.strategies.keys())}")

        strategy = self.strategies.get(group_id, {}).get(symbol)
        logger.info(f"         🔍 전략 찾기 결과: {strategy is not None}")

        if not strategy:
            logger.info(f"         ❌ {symbol}: 전략 없음 (그룹: {group_id})")
            return

        # 캔들 데이터 가져오기
        auto_config = group.get("buy_settings", {}).get("auto_config", {})
        candle_unit = auto_config.get("candle_unit", "60")
        logger.info(f"         🔍 캔들 단위: {candle_unit}분")

        logger.info(f"         📊 {symbol}: 캔들 조회 시작 (단위: {candle_unit}분, 개수: 200개)")
        candles = self._get_recent_candles(symbol, candle_unit, count=200)
        candle_count = len(candles) if candles is not None else 0
        logger.info(f"         📊 {symbol}: 캔들 조회 완료 (조회됨: {candle_count}개)")

        if candles is None or len(candles) < 50:
            logger.info(f"         ❌ {symbol}: 캔들 데이터 부족 (필요: 50개, 현재: {candle_count}개)")
            return

        # 매수 신호 확인
        try:
            logger.info(f"         🔍 {symbol}: should_buy() 호출 시작...")
            buy_signal = strategy.should_buy(candles)
            logger.info(f"         🔍 {symbol}: should_buy() 결과 = {buy_signal}")

            if buy_signal:
                logger.info(f"🔔 {symbol}: 매수 신호 발생!")

                # 지표 값 출력
                indicators = strategy.get_indicator_values(candles)
                logger.info(f"   지표 값: {indicators}")

                # 매수 실행
                self._execute_buy(symbol, group_id, group)
            else:
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

        logger.info(f"💰 {symbol} 매수 실행 중... (금액: {buy_amount:,}원)")

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
                    buy_amount=buy_quantity,
                    buy_value_krw=buy_amount
                )

                logger.info(f"✅ [Dry-run] {symbol} 매수 완료: {buy_quantity:.8f}개 @ {current_price:,}원")

            else:
                # Live 모드: 실제 주문
                order_result = self.upbit_api.buy_market_order(symbol, buy_amount)

                if not order_result or 'error' in order_result:
                    logger.error(f"❌ {symbol} 매수 실패: {order_result}")
                    return

                # 주문 정보 추출
                executed_volume = float(order_result.get('executed_volume', 0))
                avg_price = float(order_result.get('avg_price', 0))
                paid_fee = float(order_result.get('paid_fee', 0))
                total_paid = float(order_result.get('trades_sum', buy_amount))

                # 포지션 생성
                position = self.position_manager.create_position(
                    group_id=group_id,
                    symbol=symbol,
                    buy_price=avg_price,
                    buy_amount=executed_volume,
                    buy_value_krw=total_paid
                )

                logger.info(f"✅ {symbol} 매수 완료: {executed_volume:.8f}개 @ {avg_price:,}원 (수수료: {paid_fee:,}원)")

            # 거래 기록
            self.trade_history.add_trade(
                group_id=group_id,
                group_name=group.get("name", "Unknown"),
                symbol=symbol,
                action="buy",
                trade_type="initial",
                price=position.get("avg_buy_price"),
                amount=position.get("total_amount"),
                total_krw=buy_amount,
                dry_run=self.dry_run
            )

            # 텔레그램 알림
            self._send_telegram_alert(
                f"✅ 매수 완료\n"
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
        """DCA 체크 및 실행"""
        dca_settings = group.get("dca_settings", {})

        if dca_settings.get("mode") != "auto":
            return

        dca_levels = dca_settings.get("levels", [])
        dca_count = position.get("dca_count", 0)

        # 모든 DCA 레벨 소진
        if dca_count >= len(dca_levels):
            return

        # 다음 DCA 레벨 확인
        for i, level in enumerate(dca_levels):
            if i < dca_count:
                continue  # 이미 실행된 레벨

            drop_pct = level.get("drop_pct", -5.0)

            if profit_pct <= drop_pct:
                logger.info(f"🔔 {symbol}: DCA 레벨 {i+1} 트리거 (현재: {profit_pct:.2f}%, 기준: {drop_pct:.2f}%)")
                self._execute_dca(symbol, group_id, group, level, i+1)
                break  # 한 번에 하나의 DCA만 실행

    def _execute_dca(
        self,
        symbol: str,
        group_id: str,
        group: Dict[str, Any],
        level: Dict[str, Any],
        dca_level_num: int
    ):
        """DCA 매수 실행"""
        if self.observation_mode:
            logger.info(f"[관찰] {symbol} DCA 레벨 {dca_level_num} (실행 안 함)")
            return

        # DCA 금액 계산
        auto_config = group.get("buy_settings", {}).get("auto_config", {})
        base_amount = auto_config.get("buy_amount_krw", 50000)
        buy_ratio = level.get("buy_ratio", 1.0)
        dca_amount = int(base_amount * buy_ratio)

        logger.info(f"💰 {symbol} DCA 레벨 {dca_level_num} 실행 중... (금액: {dca_amount:,}원, 비율: {buy_ratio}x)")

        try:
            if self.dry_run or not self.upbit_api:
                # Dry-run 모드
                current_price = self._get_current_price_safe(symbol)
                if not current_price:
                    logger.error(f"❌ {symbol} 현재가 조회 실패")
                    return

                dca_quantity = dca_amount / current_price

                # 포지션 DCA 추가
                self.position_manager.add_dca(
                    symbol=symbol,
                    dca_price=current_price,
                    dca_amount=dca_quantity,
                    dca_value_krw=dca_amount
                )

                logger.info(f"✅ [Dry-run] {symbol} DCA 완료: {dca_quantity:.8f}개 @ {current_price:,}원")

            else:
                # Live 모드
                order_result = self.upbit_api.buy_market_order(symbol, dca_amount)

                if not order_result or 'error' in order_result:
                    logger.error(f"❌ {symbol} DCA 실패: {order_result}")
                    return

                executed_volume = float(order_result.get('executed_volume', 0))
                avg_price = float(order_result.get('avg_price', 0))

                # 포지션 DCA 추가
                self.position_manager.add_dca(
                    symbol=symbol,
                    dca_price=avg_price,
                    dca_amount=executed_volume,
                    dca_value_krw=dca_amount
                )

                logger.info(f"✅ {symbol} DCA 완료: {executed_volume:.8f}개 @ {avg_price:,}원")

            # 거래 기록
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
        """익절 체크 및 실행"""
        profit_settings = group.get("profit_settings", {})

        if profit_settings.get("mode") not in ["auto", "alert"]:
            return

        profit_levels = profit_settings.get("levels", [])

        for level in profit_levels:
            target_pct = level.get("price_ratio", 5.0)
            quantity_ratio = level.get("quantity_ratio", 100) / 100.0

            if profit_pct >= target_pct:
                logger.info(f"🎯 {symbol}: 익절 목표 도달 (현재: {profit_pct:.2f}%, 목표: {target_pct:.2f}%)")

                if profit_settings.get("mode") == "auto":
                    self._execute_sell(symbol, group_id, group, "profit", quantity_ratio)
                else:
                    self._send_telegram_alert(
                        f"🎯 익절 알림\n"
                        f"그룹: {group.get('name')}\n"
                        f"코인: {symbol}\n"
                        f"수익률: {profit_pct:.2f}%\n"
                        f"목표: {target_pct:.2f}%"
                    )

                break  # 첫 번째 달성한 레벨만 실행

    def _check_stop_loss(
        self,
        symbol: str,
        group_id: str,
        group: Dict[str, Any],
        position: Dict[str, Any],
        current_price: float,
        profit_pct: float
    ):
        """손절 체크 및 실행"""
        loss_settings = group.get("loss_settings", {})

        if loss_settings.get("mode") not in ["auto", "alert"]:
            return

        loss_levels = loss_settings.get("levels", [])

        for level in loss_levels:
            stop_pct = level.get("price_ratio", -15.0)
            quantity_ratio = level.get("quantity_ratio", 100) / 100.0

            if profit_pct <= stop_pct:
                logger.warning(f"🛑 {symbol}: 손절 기준 도달 (현재: {profit_pct:.2f}%, 기준: {stop_pct:.2f}%)")

                if loss_settings.get("mode") == "auto":
                    self._execute_sell(symbol, group_id, group, "loss", quantity_ratio)
                else:
                    self._send_telegram_alert(
                        f"🛑 손절 알림\n"
                        f"그룹: {group.get('name')}\n"
                        f"코인: {symbol}\n"
                        f"수익률: {profit_pct:.2f}%\n"
                        f"기준: {stop_pct:.2f}%"
                    )

                break  # 첫 번째 달성한 레벨만 실행

    def _execute_sell(
        self,
        symbol: str,
        group_id: str,
        group: Dict[str, Any],
        reason: str,  # "profit" or "loss"
        quantity_ratio: float = 1.0  # 판매 비율 (1.0 = 전량)
    ):
        """매도 실행"""
        if self.observation_mode:
            logger.info(f"[관찰] {symbol} 매도 신호 (사유: {reason}, 실행 안 함)")
            return

        position = self.position_manager.get_position(symbol)
        if not position:
            return

        total_amount = position.get("total_amount", 0)
        sell_amount = total_amount * quantity_ratio

        logger.info(f"💰 {symbol} 매도 실행 중... (사유: {reason}, 수량: {sell_amount:.8f}개)")

        try:
            if self.dry_run or not self.upbit_api:
                # Dry-run 모드
                current_price = self._get_current_price_safe(symbol)
                if not current_price:
                    logger.error(f"❌ {symbol} 현재가 조회 실패")
                    return

                sell_value = sell_amount * current_price
                profit = sell_value - (position.get("total_invested_krw", 0) * quantity_ratio)

                # 포지션 종료
                if quantity_ratio >= 0.99:  # 거의 전량 매도
                    self.position_manager.close_position(symbol)
                    logger.info(f"✅ [Dry-run] {symbol} 전량 매도 완료: {sell_amount:.8f}개 @ {current_price:,}원 (수익: {profit:+,.0f}원)")
                else:
                    # 부분 매도 (나중에 구현)
                    logger.warning(f"⚠️ 부분 매도는 아직 미구현")
                    return

            else:
                # Live 모드
                order_result = self.upbit_api.sell_market_order(symbol, sell_amount)

                if not order_result or 'error' in order_result:
                    logger.error(f"❌ {symbol} 매도 실패: {order_result}")
                    return

                executed_volume = float(order_result.get('executed_volume', 0))
                avg_price = float(order_result.get('avg_price', 0))
                sell_value = executed_volume * avg_price
                profit = sell_value - (position.get("total_invested_krw", 0) * quantity_ratio)

                # 포지션 종료
                if quantity_ratio >= 0.99:
                    self.position_manager.close_position(symbol)
                    logger.info(f"✅ {symbol} 전량 매도 완료: {executed_volume:.8f}개 @ {avg_price:,}원 (수익: {profit:+,.0f}원)")
                else:
                    logger.warning(f"⚠️ 부분 매도는 아직 미구현")
                    return

            # 거래 기록
            self.trade_history.add_trade(
                group_id=group_id,
                group_name=group.get("name", "Unknown"),
                symbol=symbol,
                action="sell",
                trade_type=reason,  # "profit" or "loss"
                price=current_price if self.dry_run else avg_price,
                amount=sell_amount,
                total_krw=sell_value,
                dry_run=self.dry_run,
                profit_loss=profit  # 추가 정보
            )

            # 텔레그램 알림
            emoji = "🎉" if profit > 0 else "😢"
            self._send_telegram_alert(
                f"{emoji} 매도 완료 ({reason})\n"
                f"그룹: {group.get('name')}\n"
                f"코인: {symbol}\n"
                f"수익: {profit:+,.0f}원\n"
                f"수익률: {(profit / position.get('total_invested_krw', 1) * 100):+.2f}%"
            )

        except Exception as e:
            logger.error(f"❌ {symbol} 매도 실행 오류: {e}", exc_info=True)

    def _check_global_constraints(self) -> bool:
        """
        전역 제약 확인

        Returns:
            거래 가능 여부
        """
        # 관찰 모드 체크
        logger.info(f"         🔍 observation_mode = {self.observation_mode}")
        if self.observation_mode:
            logger.info(f"         ❌ 관찰 모드로 인해 거래 불가")
            return False

        # 최소 잔고 체크
        min_balance_config = self.global_settings.get("min_krw_balance", {})
        min_balance_enabled = min_balance_config.get("enabled", False)
        logger.info(f"         🔍 최소 잔고 체크 활성화 = {min_balance_enabled}")

        if min_balance_enabled:
            current_balance = self._get_krw_balance()
            min_balance = min_balance_config.get("amount", 50000)
            logger.info(f"         🔍 현재 잔고: {current_balance:,.0f}원 / 최소: {min_balance:,.0f}원")

            if current_balance < min_balance:
                logger.info(f"         ❌ 최소 잔고 미달로 인해 거래 불가")
                return False

        # 일일 손실 한도 체크
        daily_loss_enabled = self.daily_loss_tracker is not None
        logger.info(f"         🔍 일일 손실 한도 체크 활성화 = {daily_loss_enabled}")

        if self.daily_loss_tracker and self.daily_loss_tracker.is_limit_reached():
            logger.info(f"         ❌ 일일 손실 한도 도달로 인해 거래 불가")
            return False

        logger.info(f"         ✅ 전역 제약 모두 통과")
        return True

    def _get_current_price_safe(self, symbol: str) -> Optional[float]:
        """
        현재가 안전 조회 (Dry-run/Live 모드 호환)

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')

        Returns:
            float: 현재가 (실패 시 None)
        """
        try:
            if self.upbit_api:
                # UpbitAPI 사용 (Live/Dry-run 모두 사용 가능)
                ticker = self.upbit_api.get_ticker(symbol)
                if ticker and 'trade_price' in ticker:
                    return float(ticker['trade_price'])
                else:
                    logger.error(f"❌ {symbol} 현재가 조회 실패: ticker 데이터 없음")
                    return None
            else:
                logger.error(f"❌ {symbol} 현재가 조회 실패: UpbitAPI 없음 (Dry-run 모드에서는 UpbitAPI 필요)")
                return None

        except SymbolNotFoundError as e:
            # 404 에러: 상장폐지된 코인 → 스킵 리스트에 추가
            logger.warning(f"⏭️ {symbol}: 스킵 리스트에 추가 (상장폐지)")
            self.skipped_symbols.add(symbol)
            return None

        except Exception as e:
            logger.error(f"❌ {symbol} 현재가 조회 오류: {e}")
            return None

    def _get_recent_candles(self, symbol: str, candle_unit: str, count: int = 200):
        """
        최근 캔들 데이터 가져오기 (스마트 캐싱 적용)

        Args:
            symbol: 코인 심볼
            candle_unit: 캔들 단위 (분, 예: "15", "60", "240")
            count: 캔들 개수

        Returns:
            DataFrame: 캔들 데이터
        """
        try:
            if not self.upbit_api:
                logger.error(f"❌ {symbol} 캔들 조회 실패: UpbitAPI 없음")
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
            logger.debug(f"📊 API 조회: {symbol} ({candle_unit}분봉)")
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

    def _get_krw_balance(self) -> float:
        """
        KRW 잔고 조회 (캐시 적용)

        Rate Limit 방지를 위해 1초 TTL 캐시 사용
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

            # 모든 포지션의 현재가 평가액
            all_positions = self.position_manager.get_all_positions()
            coin_value = 0.0

            for symbol, position in all_positions.items():
                if position.get("status") != "active":
                    continue

                current_price = self._get_current_price_safe(symbol)
                if current_price:
                    total_amount = position.get("total_amount", 0)
                    coin_value += current_price * total_amount

            return krw_balance + coin_value

        except Exception as e:
            logger.error(f"❌ 자산 평가액 계산 오류: {e}")
            return 0.0

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
        """텔레그램 알림 전송"""
        # TODO: 텔레그램 봇 통합
        logger.info(f"📱 [Telegram] {message}")

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
