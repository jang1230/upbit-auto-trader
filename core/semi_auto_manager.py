"""
Semi-Auto Manager - 반자동 트레이딩 관리자

사용자의 수동 매수를 감지하고 자동으로 DCA 및 익절/손절을 관리합니다.

주요 기능:
1. 수동 매수 감지 (PositionDetector)
2. DCA 자동 추가 매수
3. 익절/손절 자동 실행
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import asyncio
import time

from core.position_detector import PositionDetector, Position
from core.order_manager import OrderManager
from core.upbit_api import UpbitAPI
from core.upbit_websocket import UpbitWebSocket
from core.utils import format_price
from gui.dca_config import AdvancedDcaConfig

logger = logging.getLogger(__name__)


class ManagedPosition:
    """관리 중인 포지션 정보"""
    
    def __init__(
        self,
        position: Position,
        dca_config: AdvancedDcaConfig,
        initial_signal_price: float
    ):
        """
        Args:
            position: Position 객체
            dca_config: DCA 설정
            initial_signal_price: 최초 감지 시점의 가격 (DCA 기준점)
        """
        self.position = position
        self.dca_config = dca_config
        self.signal_price = initial_signal_price
        
        # DCA 상태 추적
        self.executed_dca_levels = set()  # 실행된 DCA 레벨
        self.total_invested = position.balance * position.avg_buy_price
        
        # 익절/손절 상태 추적
        self.executed_tp_levels = set()  # 실행된 익절 레벨
        self.executed_sl_levels = set()  # 실행된 손절 레벨
        
        self.created_at = datetime.now()
        self.last_checked = datetime.now()
    
    def update_position(self, position: Position):
        """포지션 정보 업데이트"""
        self.position = position
        self.last_checked = datetime.now()
    
    @property
    def avg_entry_price(self) -> float:
        """평균 매수가 (수동 매수 감지 시점의 시장가 기준)"""
        # 🔧 Upbit API의 avg_buy_price 대신 감지 시점의 signal_price 사용
        # - Upbit API는 이전 보유분을 포함한 평균가를 반환 (부정확)
        # - signal_price는 수동 매수 감지 시점의 실시간 시장가 (더 정확)
        return self.signal_price
    
    @property
    def total_balance(self) -> float:
        """총 보유량"""
        return self.position.total_balance
    
    def __repr__(self):
        return (
            f"ManagedPosition({self.position.symbol}, "
            f"balance={self.total_balance:.6f}, "
            f"avg_price={self.avg_entry_price:,.0f}, "
            f"dca_levels={len(self.executed_dca_levels)})"
        )


class SemiAutoManager:
    """
    반자동 트레이딩 관리자
    
    역할:
    1. Upbit에서 사용자의 수동 매수 감지
    2. 감지된 포지션에 DCA 자동 적용
    3. 익절/손절 자동 실행
    """
    
    def __init__(
        self,
        upbit_api: UpbitAPI,
        order_manager: OrderManager,
        dca_config: AdvancedDcaConfig,
        access_key: str,  # 🔧 MyAsset WebSocket 인증용
        secret_key: str,  # 🔧 MyAsset WebSocket 인증용
        scan_interval: int = 60,  # 🔧 fallback 스캔 주기 (초) - 10→60으로 변경
        notification_callback: Optional[Callable] = None,
        position_callback: Optional[Callable] = None,  # 🔧 포지션 업데이트 콜백
        balance_update_callback: Optional[Callable] = None  # 🔧 잔고 갱신 콜백
    ):
        """
        Args:
            upbit_api: Upbit API 클라이언트
            order_manager: 주문 관리자
            dca_config: DCA 설정
            access_key: Upbit Access Key (MyAsset WebSocket 인증용)
            secret_key: Upbit Secret Key (MyAsset WebSocket 인증용)
            scan_interval: Fallback 스캔 주기 (초, MyAsset WebSocket 실패 시 사용)
            notification_callback: 알림 콜백 함수
            position_callback: 포지션 업데이트 콜백 함수 (새 포지션 감지, 업데이트 시 호출)
            balance_update_callback: 잔고 갱신 콜백 함수 (수동 매수 감지 시 호출)
        """
        self.api = upbit_api
        self.order_manager = order_manager
        self.dca_config = dca_config
        self.access_key = access_key
        self.secret_key = secret_key
        self.scan_interval = scan_interval
        self.notification_callback = notification_callback
        self.position_callback = position_callback  # 🔧 저장
        self.balance_update_callback = balance_update_callback  # 🔧 저장

        # PositionDetector 초기화
        self.detector = PositionDetector(upbit_api)

        # 관리 중인 포지션 (symbol -> ManagedPosition)
        self.managed_positions: Dict[str, ManagedPosition] = {}

        # 🔧 WebSocket 실시간 가격 수신 (ticker)
        self.websocket = UpbitWebSocket()

        # 🔧 MyAsset WebSocket 실시간 자산 변동 감지
        from core.upbit_websocket import MyAssetWebSocket
        self.myasset_websocket = MyAssetWebSocket(access_key, secret_key)

        self.last_prices: Dict[str, float] = {}  # {symbol: last_price}
        self.last_check_time: Dict[str, float] = {}  # {symbol: timestamp} DCA/익절/손절 체크
        self.last_gui_update: Dict[str, float] = {}  # {symbol: timestamp} GUI 업데이트

        # 🔧 자동 매도 추적 (수동 매도 vs 자동 매도 구분용)
        # {symbol: {'quantity': 20.0, 'timestamp': 1234567890.123}}
        self._recent_auto_sells: Dict[str, Dict] = {}

        # 실행 상태
        self.is_running = False
        self._scan_task = None  # PositionDetector 스캔 태스크 (fallback)
        self._websocket_task = None  # Ticker WebSocket 리스닝 태스크
        self._myasset_task = None  # 🔧 MyAsset WebSocket 리스닝 태스크
        self._is_initial_scan = True  # 🔧 초기 스캔 플래그 (기존 보유 vs 신규 매수 구분)

        logger.info(f"SemiAutoManager 초기화 완료 (fallback 스캔: {scan_interval}초)")
    
    async def start(self):
        """매니저 시작"""
        if self.is_running:
            logger.warning("SemiAutoManager가 이미 실행 중입니다")
            return

        self.is_running = True
        logger.info("🚀 SemiAutoManager 시작")

        # 🔧 1. Ticker WebSocket 연결
        ticker_connected = await self.websocket.connect()
        if not ticker_connected:
            logger.warning("⚠️ Ticker WebSocket 연결 실패")

        # 🔧 2. MyAsset WebSocket 연결 (자산 변동 실시간 감지)
        myasset_connected = await self.myasset_websocket.connect()
        if myasset_connected:
            try:
                await self.myasset_websocket.subscribe_myasset()
                logger.info("✅ MyAsset WebSocket 활성화 - 실시간 자산 변동 감지")
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"⚠️ MyAsset WebSocket 구독 실패: {e} - fallback polling 사용")
                myasset_connected = False  # 구독 실패 시 연결 상태 False로 변경
        else:
            logger.warning("⚠️ MyAsset WebSocket 연결 실패 - fallback polling 사용")

        # 🔧 3. 초기 스캔 (수동 매수 감지)
        await self._scan_and_process()

        # 🔧 3-1. 초기 스캔 완료 - 이후 감지는 실시간 매수로 간주
        self._is_initial_scan = False
        logger.info("✅ 초기 스캔 완료 - 실시간 매수 감지 모드로 전환")

        # 🔧 4. 관리 중인 포지션이 있으면 Ticker WebSocket 구독
        if self.managed_positions and ticker_connected:
            symbols = list(self.managed_positions.keys())
            try:
                await self.websocket.subscribe_ticker(symbols)
                logger.info(f"📊 WebSocket ticker 구독 완료: {len(symbols)}개 종목")
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"⚠️ WebSocket 구독 실패: {e}")
                ticker_connected = False  # 구독 실패 시 연결 상태 False로 변경

        # 🔧 5. MyAsset WebSocket 리스닝 태스크 (실시간 자산 변동 감지)
        if myasset_connected:
            self._myasset_task = asyncio.create_task(self._listen_myasset())

        # 🔧 6. Fallback 스캔 태스크 (MyAsset 실패 시 또는 보조용)
        if not myasset_connected:
            logger.info(f"⏰ Fallback polling 시작 ({self.scan_interval}초)")
        else:
            logger.info(f"⏰ Fallback polling 활성 ({self.scan_interval}초, 보조용)")
        self._scan_task = asyncio.create_task(self._run_scan_loop())

        # 🔧 7. Ticker WebSocket 리스닝 태스크 (실시간 가격 수신)
        if ticker_connected:
            self._websocket_task = asyncio.create_task(self._listen_websocket())
    
    async def stop(self):
        """매니저 종료"""
        if not self.is_running:
            return

        logger.info("🛑 SemiAutoManager 종료 시작...")
        self.is_running = False

        # 🔧 1. 스캔 태스크 취소 (1초 타임아웃)
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._scan_task), timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.debug(f"스캔 태스크 종료 중 에러: {e}")

        # 🔧 2. MyAsset WebSocket 연결 종료
        try:
            await asyncio.wait_for(self.myasset_websocket.disconnect(), timeout=2.0)
        except asyncio.TimeoutError:
            logger.warning("⚠️ MyAsset WebSocket 종료 타임아웃")
        except Exception as e:
            logger.debug(f"MyAsset WebSocket 종료 중 에러: {e}")

        # 🔧 3. MyAsset WebSocket 태스크 취소
        if self._myasset_task and not self._myasset_task.done():
            self._myasset_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._myasset_task), timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.debug(f"MyAsset 태스크 종료 중 에러: {e}")

        # 🔧 4. Ticker WebSocket 연결 종료
        try:
            await asyncio.wait_for(self.websocket.disconnect(), timeout=2.0)
        except asyncio.TimeoutError:
            logger.warning("⚠️ Ticker WebSocket 종료 타임아웃")
        except Exception as e:
            logger.debug(f"Ticker WebSocket 종료 중 에러: {e}")

        # 🔧 5. Ticker WebSocket 태스크 취소
        if self._websocket_task and not self._websocket_task.done():
            self._websocket_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._websocket_task), timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.debug(f"Ticker WebSocket 태스크 종료 중 에러: {e}")

        logger.info("✅ SemiAutoManager 종료 완료")
    
    async def _run_scan_loop(self):
        """🔧 PositionDetector 스캔 루프 (수동 매수 감지 전용)"""
        try:
            while self.is_running:
                await asyncio.sleep(self.scan_interval)
                await self._scan_and_process()
        except asyncio.CancelledError:
            logger.info("PositionDetector 스캔 루프 종료")
        except Exception as e:
            logger.error(f"PositionDetector 스캔 루프 에러: {e}", exc_info=True)
    
    async def _listen_websocket(self):
        """🔧 WebSocket 실시간 ticker 수신 루프"""
        try:
            async for data in self.websocket.listen():
                if not self.is_running:
                    break
                
                # ticker 타입만 처리
                if data.get('type') != 'ticker':
                    continue
                
                symbol = data['code']  # "KRW-BTC"
                price = data['trade_price']

                # 🔍 디버깅: 가격 수신 로그 (심볼별 처음 3회만, logger.debug)
                if not hasattr(self, '_debug_price_count'):
                    self._debug_price_count = {}
                if symbol not in self._debug_price_count:
                    self._debug_price_count[symbol] = 0
                if self._debug_price_count[symbol] < 3:
                    logger.debug(f"🔍 WebSocket 가격 수신: {symbol} = {price:,.0f}원")
                    self._debug_price_count[symbol] += 1

                # 가격 캐시 업데이트
                self.last_prices[symbol] = price

                # 1. GUI 업데이트
                await self._update_gui_if_needed(symbol, price)

                # 2. DCA/익절/손절 체크
                await self._check_trading_conditions(symbol, price)
                
        except asyncio.CancelledError:
            logger.info("WebSocket 리스닝 종료")
        except Exception as e:
            logger.error(f"WebSocket 리스닝 에러: {e}", exc_info=True)
            # 에러 발생 시 재연결 시도
            if self.is_running:
                logger.info("WebSocket 재연결 시도 중...")
                await asyncio.sleep(5)
                if await self.websocket.connect():
                    symbols = list(self.managed_positions.keys())
                    if symbols:
                        await self.websocket.subscribe_ticker(symbols)
                        # 재귀 호출로 리스닝 재개
                        await self._listen_websocket()

    async def _listen_myasset(self):
        """🔧 MyAsset WebSocket 실시간 자산 변동 감지 루프"""
        try:
            logger.info("💰 MyAsset WebSocket 리스닝 시작 - 자산 변동 실시간 감지")

            async for data in self.myasset_websocket.listen():
                if not self.is_running:
                    break

                # myAsset 데이터 파싱 (공식 문서 구조)
                # {
                #   "type": "myAsset",
                #   "assets": [
                #     {"currency": "BTC", "balance": 0.00011834, "locked": 0}
                #   ]
                # }

                # 🔧 전체 메시지 로그 (디버깅용, logger.debug)
                logger.debug(f"📨 MyAsset 메시지 수신: {data}")

                assets = data.get('assets', [])

                # 각 자산의 변동 로그 및 수동 매도 감지
                asset_changes = []
                has_coin_change = False
                has_krw_change = False

                for asset in assets:
                    currency = asset.get('currency')  # 'KRW', 'BTC', 'XRP' 등
                    balance = asset.get('balance', 0)  # 보유 수량
                    locked = asset.get('locked', 0)  # 주문 중 수량

                    if currency == 'KRW':
                        logger.info(f"💰 자산 변동 감지: {currency} - 잔액: {balance:,.0f}원, 주문중: {locked:,.0f}원")
                        has_krw_change = True
                    else:
                        logger.info(f"💰 자산 변동 감지: {currency} - 잔액: {balance:.8f}, 주문중: {locked:.8f}")
                        if balance > 0:
                            has_coin_change = True

                        # 🔧 수동 매도 감지: 관리 중인 코인의 총 보유량 감소 확인
                        symbol = f"KRW-{currency}"
                        if symbol in self.managed_positions:
                            managed = self.managed_positions[symbol]

                            # ✅ 수정: balance만 확인하지 않고 total (balance + locked) 확인
                            # - DCA 추가매수: balance 감소하지만 locked 증가 → total 동일 또는 증가
                            # - 실제 매도: total (balance + locked) 감소
                            old_total = managed.position.balance + managed.position.locked
                            new_total = balance + locked

                            # 총 보유량 감소 감지 → 실제 매도로 판단
                            if new_total < old_total:
                                logger.info(f"🔍 총 보유량 감소 감지: {symbol} ({old_total:.8f} → {new_total:.8f})")
                                # Position 객체 생성하여 _update_managed_position 호출
                                from core.position_detector import Position
                                updated_position = Position(
                                    symbol=symbol,
                                    currency=currency,
                                    balance=balance,  # ✅ 수정: new_balance → balance
                                    avg_buy_price=managed.position.avg_buy_price,
                                    locked=locked
                                )
                                await self._update_managed_position(updated_position)

                    asset_changes.append(currency)

                # 🔧 개선: KRW 변동 또는 코인 변동 모두 스캔 트리거
                # - KRW 감소 = 매수 발생 가능
                # - KRW 증가 = 매도 발생 가능
                # - 코인 변동 = 매수/매도 발생
                if has_krw_change or has_coin_change:
                    logger.info(f"🔍 자산 변동 감지 ({', '.join(asset_changes)}) → 즉시 포지션 스캔")
                    await self._scan_and_process()

        except asyncio.CancelledError:
            logger.info("MyAsset WebSocket 리스닝 종료")
        except Exception as e:
            logger.error(f"MyAsset WebSocket 리스닝 에러: {e}", exc_info=True)
            # 에러 발생 시 재연결 시도
            if self.is_running:
                logger.info("MyAsset WebSocket 재연결 시도 중...")
                await asyncio.sleep(5)
                if await self.myasset_websocket.connect():
                    await self.myasset_websocket.subscribe_myasset()
                    # 재귀 호출로 리스닝 재개
                    await self._listen_myasset()

    async def _update_gui_if_needed(self, symbol: str, price: float):
        """🔧 GUI 업데이트 (500ms throttling)"""
        if not self.position_callback:
            return

        now = time.time()
        last_update = self.last_gui_update.get(symbol, 0)

        # 500ms = 0.5초마다 업데이트 (초당 2회) - GUI 과부하 방지하면서 더 빠른 업데이트
        if now - last_update < 0.5:
            return
        
        # 관리 중인 포지션만 업데이트
        managed = self.managed_positions.get(symbol)
        if not managed:
            return
        
        # 포지션 데이터 생성
        position = managed.position
        avg_price = managed.avg_entry_price
        
        position_data = {
            'symbol': symbol,
            'position': position.balance,
            'entry_price': avg_price,
            'current_price': price,
            'profit_loss': (price - avg_price) * position.balance,
            'return_pct': ((price - avg_price) / avg_price) * 100 if avg_price > 0 else 0,
            'entry_time': managed.created_at.isoformat()
        }
        
        # GUI 업데이트 콜백 호출
        try:
            await self.position_callback(position_data)
        except Exception as e:
            logger.error(f"❌ GUI 가격 업데이트 실패 ({symbol}): {e}", exc_info=True)

        # 마지막 업데이트 시간 기록
        self.last_gui_update[symbol] = now
    
    async def _check_trading_conditions(self, symbol: str, price: float):
        """
        🔧 DCA/익절/손절 체크 (NO throttling)

        WebSocket에서 가격이 업데이트될 때마다 즉각 체크하여
        급격한 가격 변동 시 익절/손절 타이밍을 놓치지 않습니다.

        체크 로직은 가벼운 산술 연산이므로 초당 수십 번 실행해도 무방합니다.
        """
        # 관리 중인 포지션만 체크
        managed = self.managed_positions.get(symbol)
        if not managed:
            return

        try:
            # ⚡ 즉각 체크 (throttling 없음)
            # DCA 체크
            await self._check_dca(managed, price)

            # 익절 체크 - 가격이 목표에 도달하면 즉시 매도
            await self._check_take_profit(managed, price)

            # 손절 체크 - 손실이 한계에 도달하면 즉시 매도
            await self._check_stop_loss(managed, price)

        except Exception as e:
            logger.error(f"{symbol} DCA/익절/손절 체크 에러: {e}", exc_info=True)
    
    async def _scan_and_process(self):
        """포지션 스캔 및 처리"""
        try:
            # 1. 포지션 스캔 (별도 스레드에서 실행하여 이벤트 루프 차단 방지)
            # scan_positions()는 동기 blocking 함수 (requests.get 사용)
            # asyncio.to_thread()로 별도 스레드에서 실행
            result = await asyncio.to_thread(self.detector.scan_positions)

            # 2. 새로운 수동 매수 처리
            new_manual_count = len(result['new_manual'])
            if new_manual_count > 0:
                logger.info(f"🔔 새로운 수동 매수 감지: {new_manual_count}개 종목 처리 중...")

                # 🔧 배치 GUI 업데이트를 위한 리스트
                batch_position_updates = []

                for position in result['new_manual']:
                    # WebSocket 재구독, 잔고 갱신, GUI 콜백 모두 건너뛰고 포지션만 등록
                    position_data = await self._on_new_manual_buy(
                        position,
                        skip_websocket_resubscribe=True,
                        skip_balance_update=True,
                        skip_position_callback=True  # GUI 콜백도 건너뛰기
                    )

                    # GUI 업데이트 데이터 수집 (None이 아니면)
                    if position_data:
                        batch_position_updates.append(position_data)

                # 🔧 모든 종목 처리 후 GUI 업데이트 (순차 호출)
                if batch_position_updates and self.position_callback:
                    for position_data in batch_position_updates:
                        try:
                            await self.position_callback(position_data)
                        except Exception as e:
                            logger.error(f"❌ GUI 포지션 업데이트 실패 ({position_data.get('symbol', 'UNKNOWN')}): {e}", exc_info=True)

                # 🔧 배치 처리 완료 알림 (GUI 로그)
                if batch_position_updates and self.notification_callback:
                    try:
                        coin_names = [data['symbol'].replace('KRW-', '') for data in batch_position_updates]
                        await self.notification_callback(
                            f"💰 수동 매수 감지: {new_manual_count}개 종목\n"
                            f"   종목: {', '.join(coin_names)}"
                        )
                    except Exception as e:
                        logger.error(f"배치 알림 실패: {e}")

                # 🔧 모든 종목 처리 후 WebSocket 재구독 (한 번만)
                if self.websocket.is_connected and self.managed_positions:
                    try:
                        all_symbols = list(self.managed_positions.keys())
                        await self.websocket.subscribe_ticker(all_symbols)
                        logger.info(f"📊 WebSocket ticker 구독 완료: {len(all_symbols)}개 종목")
                    except Exception as e:
                        logger.warning(f"⚠️ WebSocket 구독 실패: {e}")

                # 🔧 모든 종목 처리 후 잔고 갱신 (한 번만)
                if self.balance_update_callback:
                    try:
                        if asyncio.iscoroutinefunction(self.balance_update_callback):
                            await self.balance_update_callback()
                        else:
                            self.balance_update_callback()
                        logger.info(f"✅ {new_manual_count}개 종목 등록 완료, 잔고 갱신 완료")
                    except Exception as e:
                        logger.error(f"❌ 잔고 갱신 콜백 실패: {e}")

            # 3. 관리 중인 포지션 업데이트
            for position in result['managed']:
                await self._update_managed_position(position)

            # 4. 현재 가격 조회 및 DCA/익절/손절 체크
            await self._check_all_positions()

        except Exception as e:
            logger.error(f"포지션 스캔 중 에러: {e}", exc_info=True)
    
    async def _on_new_manual_buy(self, position: Position, skip_websocket_resubscribe: bool = False, skip_balance_update: bool = False, skip_position_callback: bool = False):
        """
        새로운 수동 매수 감지 시 처리

        Args:
            position: 포지션 정보
            skip_websocket_resubscribe: WebSocket 재구독 건너뛰기 (일괄 처리 시)
            skip_balance_update: 잔고 갱신 건너뛰기 (일괄 처리 시)
            skip_position_callback: GUI 콜백 건너뛰기 (배치 처리 시)

        Returns:
            position_data (dict): GUI 업데이트용 데이터 (skip_position_callback=True 시에만 반환)
        """
        symbol = position.symbol

        # 현재 가격 조회 (평단가 0원 시 대체값으로 사용)
        current_price = await self._get_current_price(symbol)

        if current_price is None:
            logger.warning(f"현재 가격 조회 실패: {symbol}")
            return None

        # 평단가 0원인 포지션 처리 (일부 코인은 Upbit API가 평단가 제공 안 함)
        if position.avg_buy_price == 0:
            # ✅ 현재 시장가를 평단가로 사용 (정확하지 않지만 실용적)
            position.avg_buy_price = current_price
            logger.warning(
                f"⚠️ 평단가 0원 감지 → 현재가로 대체: {symbol}\n"
                f"   현재가: {format_price(current_price)} (Upbit API 평단가 미제공)"
            )

        # 🔧 진입가 결정 로직 (초기 스캔 vs 실시간 매수 구분)
        # - 초기 스캔 (프로그램 시작 시): API 평단가 사용 (실제 매수가)
        # - 실시간 매수 감지: 현재 시장가 사용 (감지 시점 가격)
        if self._is_initial_scan:
            # 초기 스캔: 기존 보유 종목 → Upbit API 평단가 사용
            entry_price = position.avg_buy_price
            logger.info(
                f"  📊 {symbol}: 기존 보유 종목 감지\n"
                f"     진입가: {format_price(entry_price)} (API 평단가)\n"
                f"     현재가: {format_price(current_price)}\n"
                f"     수익률: {((current_price - entry_price) / entry_price * 100):+.2f}%"
            )
        else:
            # 실시간 감지: 신규 매수 → 현재 시장가 사용
            entry_price = current_price
            # API 평단가와 차이가 1% 이상 나면 로그 출력 (이전 보유분 있음)
            if abs(position.avg_buy_price - current_price) > current_price * 0.01:
                logger.info(
                    f"  💰 {symbol}: 신규 매수 감지 (이전 보유분 있음)\n"
                    f"     진입가: {format_price(entry_price)} (시장가 기준)\n"
                    f"     API평단가: {format_price(position.avg_buy_price)} (이전보유분 포함)"
                )

        # ManagedPosition 생성
        managed = ManagedPosition(
            position=position,
            dca_config=self.dca_config,
            initial_signal_price=entry_price
        )

        self.managed_positions[symbol] = managed

        # PositionDetector에 관리 포지션 등록
        self.detector.register_managed_position(symbol, position)

        # 🔧 포지션 등록 확인 로그
        profit_loss = (current_price - entry_price) * position.balance
        profit_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

        logger.info(
            f"  ✅ {symbol}: 수량={position.balance:.6f}, "
            f"진입가={format_price(entry_price)}, "
            f"수익률={profit_pct:+.2f}%"
        )

        # GUI 업데이트 데이터 생성
        position_data = {
            'symbol': symbol,
            'position': position.balance,
            'entry_price': entry_price,  # 🔧 초기 스캔: API 평단가 / 실시간: 시장가
            'current_price': current_price,
            'profit_loss': profit_loss,
            'return_pct': profit_pct,
            'entry_time': managed.created_at.isoformat()
        }

        # 🔧 포지션 업데이트 콜백 (GUI 업데이트용)
        if not skip_position_callback and self.position_callback:
            # 개별 처리 시 즉시 GUI 업데이트
            try:
                await self.position_callback(position_data)
            except Exception as e:
                logger.error(f"❌ GUI 포지션 업데이트 실패 ({symbol}): {e}", exc_info=True)

        # 🔧 GUI 로그 알림 (개별 처리 시)
        if not skip_position_callback and self.notification_callback:
            try:
                coin_name = symbol.replace('KRW-', '')
                await self.notification_callback(
                    f"💰 수동 매수 감지: {coin_name}\n"
                    f"   수량: {position.balance:.6f}개\n"
                    f"   진입가: {format_price(entry_price)}\n"
                    f"   수익률: {profit_pct:+.2f}%"
                )
            except Exception as e:
                logger.error(f"GUI 알림 실패: {e}")
        # skip_position_callback=True 시에는 데이터만 반환 (배치 처리용)

        # 🔧 WebSocket 재구독 (skip 플래그가 False일 때만 - 개별 감지 시)
        if not skip_websocket_resubscribe and self.websocket.is_connected:
            try:
                all_symbols = list(self.managed_positions.keys())
                await self.websocket.subscribe_ticker(all_symbols)
                logger.info(f"📊 WebSocket ticker 재구독: {all_symbols}")
            except Exception as e:
                logger.warning(f"⚠️ WebSocket 구독 실패: {e}")

        # 🔧 잔고 갱신 (skip 플래그가 False일 때만 - 개별 감지 시)
        if not skip_balance_update and self.balance_update_callback:
            try:
                if asyncio.iscoroutinefunction(self.balance_update_callback):
                    await self.balance_update_callback()
                else:
                    self.balance_update_callback()
                logger.debug("✅ 잔고 갱신 콜백 호출 완료 (수동 매수 감지)")
            except Exception as e:
                logger.error(f"❌ 잔고 갱신 콜백 실패: {e}")

        # 배치 처리용 데이터 반환
        return position_data if skip_position_callback else None
    
    async def _update_managed_position(self, position: Position):
        """관리 중인 포지션 정보 업데이트"""
        symbol = position.symbol

        if symbol in self.managed_positions:
            managed = self.managed_positions[symbol]
            old_balance = managed.position.balance
            new_balance = position.balance

            # 🔧 수량 감소 감지 (매도 발생)
            if new_balance < old_balance:
                sold_amount = old_balance - new_balance

                # 🔍 최근 5초 이내 자동 매도 확인
                is_auto_sell = False
                if symbol in self._recent_auto_sells:
                    recent = self._recent_auto_sells[symbol]
                    time_diff = time.time() - recent['timestamp']

                    if time_diff < 5.0:  # 5초 이내
                        # ✅ 자동 매도 (익절/손절/DCA)
                        is_auto_sell = True
                        logger.info(
                            f"✅ 자동 매도 확인: {symbol}\n"
                            f"   타입: {recent['type']}\n"
                            f"   수량: {sold_amount:.6f}개\n"
                            f"   경과: {time_diff:.1f}초"
                        )
                        # 사용 완료, 삭제
                        del self._recent_auto_sells[symbol]

                # ⚠️ 수동 매도 감지
                if not is_auto_sell:
                    current_price = await self._get_current_price(symbol)
                    entry_price = managed.avg_entry_price

                    # 손익 계산
                    profit_loss = (current_price - entry_price) * sold_amount if current_price else 0
                    profit_pct = ((current_price - entry_price) / entry_price * 100) if (current_price and entry_price > 0) else 0

                    logger.warning(
                        f"⚠️ 수동 매도 감지: {symbol}\n"
                        f"   매도 수량: {sold_amount:.6f}개 ({old_balance:.6f} → {new_balance:.6f})\n"
                        f"   매도가: {format_price(current_price)}\n"
                        f"   진입가: {format_price(entry_price)}\n"
                        f"   손익: {profit_loss:+,.0f}원 ({profit_pct:+.2f}%)"
                    )

                    # GUI 알림 (선택)
                    if self.notification_callback:
                        coin_name = symbol.replace('KRW-', '')
                        try:
                            await self.notification_callback(
                                f"⚠️ 수동 매도 감지: {coin_name}\n"
                                f"   수량: {sold_amount:.6f}개\n"
                                f"   손익: {profit_loss:+,.0f}원 ({profit_pct:+.2f}%)"
                            )
                        except Exception as e:
                            logger.error(f"수동 매도 알림 실패: {e}")

                # 🔧 전량 매도 시 포지션 제거
                if new_balance == 0:
                    # 🔧 GUI 업데이트 먼저 (포지션 삭제 전에 GUI에 position=0 전송)
                    if self.position_callback:
                        current_price = await self._get_current_price(symbol)
                        entry_price = managed.avg_entry_price

                        position_data = {
                            'symbol': symbol,
                            'position': 0,  # ✅ 전량 매도 → GUI에서 테이블 행 제거
                            'entry_price': entry_price,
                            'current_price': current_price or 0,
                            'profit_loss': 0,
                            'return_pct': 0,
                            'entry_time': managed.created_at.isoformat()
                        }
                        try:
                            await self.position_callback(position_data)
                        except Exception as e:
                            logger.error(f"GUI 콜백 실패: {e}")

                    # 🔧 안전한 삭제 (이미 삭제된 경우 방지)
                    if symbol in self.managed_positions:
                        del self.managed_positions[symbol]
                        self.detector.unregister_managed_position(symbol)
                        sell_type = "자동" if is_auto_sell else "수동"
                        logger.info(f"✅ 포지션 제거: {symbol} (전량 {sell_type} 매도)")
                    else:
                        logger.warning(f"⚠️ 포지션이 이미 제거됨: {symbol}")
                    return  # 포지션 제거 완료

            # 포지션 업데이트
            managed.update_position(position)

            # 🔧 포지션 업데이트 콜백 (GUI 실시간 업데이트용)
            if self.position_callback:
                current_price = await self._get_current_price(symbol)
                if current_price:
                    # 🔧 고정된 진입가 사용 (managed.avg_entry_price)
                    entry_price = managed.avg_entry_price

                    position_data = {
                        'symbol': symbol,
                        'position': position.balance,
                        'entry_price': entry_price,  # 🔧 초기 진입가 (고정)
                        'current_price': current_price,
                        'profit_loss': (current_price - entry_price) * position.balance,
                        'return_pct': ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0,
                        'entry_time': managed.created_at.isoformat()
                    }
                    asyncio.create_task(self.position_callback(position_data))
    
    async def _check_all_positions(self):
        """모든 관리 포지션에 대해 DCA/익절/손절 체크"""
        for symbol, managed in list(self.managed_positions.items()):
            try:
                # 현재 가격 조회
                current_price = await self._get_current_price(symbol)
                
                if current_price is None:
                    continue
                
                # DCA 체크
                await self._check_dca(managed, current_price)
                
                # 익절 체크
                await self._check_take_profit(managed, current_price)
                
                # 손절 체크
                await self._check_stop_loss(managed, current_price)
                
            except Exception as e:
                logger.error(f"{symbol} 처리 중 에러: {e}", exc_info=True)
    
    async def _check_dca(self, managed: ManagedPosition, current_price: float):
        """DCA 추가 매수 체크"""
        if not self.dca_config.enabled:
            return
        
        symbol = managed.position.symbol
        signal_price = managed.signal_price
        
        # 가격 하락률 계산
        drop_pct = ((current_price - signal_price) / signal_price) * 100
        
        # DCA 레벨 확인 (level 1은 초기 진입이므로 스킵)
        for level_config in self.dca_config.levels:
            level = level_config.level
            
            if level == 1:
                continue  # 초기 진입 레벨은 스킵 (이미 수동 매수함)
            
            if level in managed.executed_dca_levels:
                continue  # 이미 실행됨
            
            # DCA 조건: 가격이 기준점 대비 설정된 % 하락
            # 설정값이 양수로 저장되어 있으므로 음수로 변환하여 비교
            # 예: drop_pct = -3%, level_config.drop_pct = 5% → -3 <= -5 (실행 안 함)
            #     drop_pct = -6%, level_config.drop_pct = 5% → -6 <= -5 (실행)
            if drop_pct <= -level_config.drop_pct:
                # 🔧 중복 실행 방지: 실행 **전**에 레벨 기록
                managed.executed_dca_levels.add(level)

                # DCA 추가 매수 실행
                await self._execute_dca_buy(managed, level_config, current_price)
    
    async def _check_take_profit(self, managed: ManagedPosition, current_price: float):
        """익절 체크 (다단계 익절 지원)"""
        if not self.dca_config.enabled:
            return

        avg_price = managed.avg_entry_price

        # 평단가 0 방지
        if avg_price == 0:
            return

        profit_pct = ((current_price - avg_price) / avg_price) * 100

        # 🔍 디버깅: 익절 체크 로그 (심볼별 처음 1회만)
        symbol = managed.position.symbol
        if not hasattr(self, '_debug_profit_check'):
            self._debug_profit_check = set()
        if symbol not in self._debug_profit_check:
            logger.info(
                f"🔍 익절 체크 시작: {symbol}\n"
                f"   평단가: {format_price(avg_price)}\n"
                f"   현재가: {format_price(current_price)}\n"
                f"   수익률: {profit_pct:.2f}%\n"
                f"   다단계 익절 설정: {len(self.dca_config.take_profit_levels) if self.dca_config.take_profit_levels else 0}개"
            )
            self._debug_profit_check.add(symbol)

        # 다단계 익절 체크
        if self.dca_config.take_profit_levels and len(self.dca_config.take_profit_levels) > 0:
            # 다단계 익절: 각 레벨별로 체크
            for tp_level in self.dca_config.take_profit_levels:
                level = tp_level.level
                target_pct = tp_level.profit_pct
                sell_ratio = tp_level.sell_ratio

                # 🔧 executed_tp_levels 초기화 (없으면)
                if not hasattr(managed, 'executed_tp_levels'):
                    managed.executed_tp_levels = set()

                # 이미 실행된 레벨은 건너뜀
                if level in managed.executed_tp_levels:
                    continue

                # 익절 조건 충족 시
                if profit_pct >= target_pct:
                    # 🔧 중복 실행 방지: 실행 **전**에 레벨 기록
                    managed.executed_tp_levels.add(level)

                    # 익절 실행
                    await self._execute_take_profit_level(managed, current_price, profit_pct, tp_level)

                    # 🔧 한 번이라도 익절 실행 시 나머지 레벨 체크 중단
                    break
        else:
            # 단일 익절: 기존 로직
            if profit_pct >= self.dca_config.take_profit_pct:
                await self._execute_take_profit(managed, current_price, profit_pct)
    
    async def _check_stop_loss(self, managed: ManagedPosition, current_price: float):
        """손절 체크 (다단계 손절 지원)"""
        if not self.dca_config.enabled:
            return

        avg_price = managed.avg_entry_price

        # 평단가 0 방지
        if avg_price == 0:
            return

        loss_pct = ((current_price - avg_price) / avg_price) * 100

        # 다단계 손절 체크
        if self.dca_config.stop_loss_levels and len(self.dca_config.stop_loss_levels) > 0:
            # 다단계 손절: 각 레벨별로 체크
            for sl_level in self.dca_config.stop_loss_levels:
                level = sl_level.level
                target_pct = sl_level.loss_pct
                sell_ratio = sl_level.sell_ratio

                # 🔧 executed_sl_levels 초기화 (없으면)
                if not hasattr(managed, 'executed_sl_levels'):
                    managed.executed_sl_levels = set()

                # 이미 실행된 레벨은 건너뜀
                if level in managed.executed_sl_levels:
                    continue

                # 손절 조건 충족 시 (손실률이 음수이므로 -를 붙여서 비교)
                if loss_pct <= -target_pct:
                    # 🔧 중복 실행 방지: 실행 **전**에 레벨 기록
                    managed.executed_sl_levels.add(level)

                    # 손절 실행
                    await self._execute_stop_loss_level(managed, current_price, loss_pct, sl_level)

                    # 🔧 한 번이라도 손절 실행 시 나머지 레벨 체크 중단
                    break
        else:
            # 단일 손절: 기존 로직
            # 예: loss_pct = -10%, stop_loss_pct = 20% → -10 <= -20 (손절 안 함)
            #     loss_pct = -25%, stop_loss_pct = 20% → -25 <= -20 (손절 실행)
            if loss_pct <= -self.dca_config.stop_loss_pct:
                await self._execute_stop_loss(managed, current_price, loss_pct)
    
    async def _execute_dca_buy(self, managed: ManagedPosition, level_config, price: float):
        """DCA 추가 매수 실행"""
        symbol = managed.position.symbol
        level = level_config.level
        
        # DCA 매수 금액 (설정에서 가져옴)
        buy_amount = level_config.order_amount
        
        logger.info(
            f"💰 DCA 추가 매수 실행: {symbol} Level {level}\n"
            f"   현재가: {format_price(price)}\n"
            f"   매수 금액: {buy_amount:,.0f}원\n"
            f"   하락률: {level_config.drop_pct}%"
        )
        
        # 주문 실행 (실거래 모드)
        order_result = await self.order_manager.execute_buy(
            symbol=symbol,
            amount=buy_amount,
            dry_run=False  # ⚠️ 실거래 모드 (실제 주문 실행!)
        )
        
        if order_result and order_result.get('success'):
            # 알림
            if self.notification_callback:
                coin_name = symbol.replace('KRW-', '')
                await self.notification_callback(
                    f"💰 DCA 추가 매수 완료 (Level {level}): {coin_name}\n"
                    f"   가격: {format_price(price)} | 금액: {buy_amount:,.0f}원 | 하락률: -{level_config.drop_pct}%"
                )

            logger.info(f"✅ DCA 추가 매수 완료: {symbol} Level {level}")

            # 🔧 DCA 추가매수 후 즉시 포지션 스캔 → GUI 업데이트
            logger.info(f"🔍 DCA 추가매수 완료 후 즉시 포지션 스캔 트리거")
            await self._scan_and_process()
        else:
            logger.error(f"❌ DCA 추가 매수 실패: {symbol} Level {level}")
    
    async def _execute_take_profit_level(self, managed: ManagedPosition, price: float, profit_pct: float, tp_level):
        """다단계 익절 실행 (일부 매도)"""
        symbol = managed.position.symbol
        balance = managed.total_balance
        sell_ratio = tp_level.sell_ratio / 100.0  # 퍼센트를 비율로 변환
        sell_volume = balance * sell_ratio

        # ⚠️ 최소 주문 금액 체크 (Upbit: 5,000원)
        MIN_ORDER_AMOUNT = 5000
        estimated_amount = sell_volume * price

        adjusted = False
        if estimated_amount < MIN_ORDER_AMOUNT:
            # 5,100원(여유분 포함)이 되도록 수량 조정
            target_amount = MIN_ORDER_AMOUNT + 100
            adjusted_volume = target_amount / price

            # 보유 수량을 초과하지 않도록 체크
            if adjusted_volume <= balance:
                sell_volume = adjusted_volume
                estimated_amount = sell_volume * price
                adjusted = True
                logger.info(
                    f"⚙️ 최소 주문 금액 조정: {symbol}\n"
                    f"   원래 금액: {estimated_amount - (target_amount - estimated_amount):,.0f}원 → 조정 후: {estimated_amount:,.0f}원\n"
                    f"   조정 수량: {balance * sell_ratio:.6f}개 → {sell_volume:.6f}개"
                )
            else:
                # 전량 매도해도 5,000원 미만이면 건너뛰기
                logger.warning(
                    f"⚠️ 최소 주문 금액 미달로 익절 건너뜀: {symbol} Level {tp_level.level}\n"
                    f"   보유 전량: {balance:.6f}개 × {price:,.0f}원 = {balance * price:,.0f}원 < 5,000원"
                )
                return

        logger.info(
            f"🎯 익절 실행 (Level {tp_level.level}): {symbol}\n"
            f"   목표 수익률: {tp_level.profit_pct:.2f}%\n"
            f"   현재 수익률: {profit_pct:.2f}%\n"
            f"   현재가: {format_price(price)}\n"
            f"   매도 비율: {tp_level.sell_ratio:.0f}%{' (수량 조정됨)' if adjusted else ''}\n"
            f"   매도 수량: {sell_volume:.6f} / {balance:.6f}\n"
            f"   예상 금액: {estimated_amount:,.0f}원"
        )

        # 🔧 자동 매도 기록 (수동 매도와 구분용)
        self._recent_auto_sells[symbol] = {
            'quantity': sell_volume,
            'timestamp': time.time(),
            'type': f'익절 L{tp_level.level}'
        }

        # 일부 매도 (실거래 모드)
        order_result = await self.order_manager.execute_sell(
            symbol=symbol,
            volume=sell_volume,
            dry_run=False  # ⚠️ 실거래 모드 (실제 주문 실행!)
        )

        if order_result and order_result.get('success'):
            # 알림
            if self.notification_callback:
                coin_name = symbol.replace('KRW-', '')
                await self.notification_callback(
                    f"🎯 익절 완료 (Level {tp_level.level}): {coin_name}\n"
                    f"   수익률: +{profit_pct:.2f}% | 매도: {tp_level.sell_ratio:.0f}% | 가격: {format_price(price)}"
                )

            logger.info(f"✅ 익절 완료: {symbol} Level {tp_level.level}")

            # 100% 매도한 경우 포지션 제거
            if tp_level.sell_ratio >= 100.0:
                # 🔧 안전한 삭제 (이미 삭제된 경우 방지)
                if symbol in self.managed_positions:
                    del self.managed_positions[symbol]
                    self.detector.unregister_managed_position(symbol)
                    logger.info(f"✅ 포지션 제거: {symbol} (전량 익절)")
                else:
                    logger.warning(f"⚠️ 포지션이 이미 제거됨: {symbol}")
        else:
            logger.error(f"❌ 익절 실패: {symbol} Level {tp_level.level}")

    async def _execute_take_profit(self, managed: ManagedPosition, price: float, profit_pct: float):
        """익절 실행 (단일 익절, 전량 매도)"""
        symbol = managed.position.symbol
        balance = managed.total_balance
        
        logger.info(
            f"🎯 익절 실행: {symbol}\n"
            f"   수익률: {profit_pct:.2f}%\n"
            f"   현재가: {format_price(price)}\n"
            f"   수량: {balance:.6f}"
        )

        # 🔧 자동 매도 기록 (수동 매도와 구분용)
        self._recent_auto_sells[symbol] = {
            'quantity': balance,
            'timestamp': time.time(),
            'type': '익절 (단일)'
        }

        # 전량 매도 (실거래 모드)
        order_result = await self.order_manager.execute_sell(
            symbol=symbol,
            volume=balance,  # ⭐ 파라미터 이름: volume (수량)
            dry_run=False  # ⚠️ 실거래 모드 (실제 주문 실행!)
        )
        
        if order_result and order_result.get('success'):
            # 🔧 안전한 포지션 제거 (이미 삭제된 경우 방지)
            if symbol in self.managed_positions:
                del self.managed_positions[symbol]
                self.detector.unregister_managed_position(symbol)
            else:
                logger.warning(f"⚠️ 포지션이 이미 제거됨: {symbol}")

            # 알림
            if self.notification_callback:
                coin_name = symbol.replace('KRW-', '')
                await self.notification_callback(
                    f"🎯 익절 완료: {coin_name}\n"
                    f"   수익률: +{profit_pct:.2f}% | 매도가: {format_price(price)}"
                )
            
            logger.info(f"✅ 익절 완료: {symbol} (+{profit_pct:.2f}%)")
        else:
            logger.error(f"❌ 익절 실패: {symbol}")
    
    async def _execute_stop_loss_level(self, managed: ManagedPosition, price: float, loss_pct: float, sl_level):
        """다단계 손절 실행 (일부 매도)"""
        symbol = managed.position.symbol
        balance = managed.total_balance
        sell_ratio = sl_level.sell_ratio / 100.0  # 퍼센트를 비율로 변환
        sell_volume = balance * sell_ratio

        # ⚠️ 최소 주문 금액 체크 (Upbit: 5,000원)
        MIN_ORDER_AMOUNT = 5000
        estimated_amount = sell_volume * price

        adjusted = False
        if estimated_amount < MIN_ORDER_AMOUNT:
            # 5,100원(여유분 포함)이 되도록 수량 조정
            target_amount = MIN_ORDER_AMOUNT + 100
            adjusted_volume = target_amount / price

            # 보유 수량을 초과하지 않도록 체크
            if adjusted_volume <= balance:
                sell_volume = adjusted_volume
                estimated_amount = sell_volume * price
                adjusted = True
                logger.info(
                    f"⚙️ 최소 주문 금액 조정: {symbol}\n"
                    f"   원래 금액: {estimated_amount - (target_amount - estimated_amount):,.0f}원 → 조정 후: {estimated_amount:,.0f}원\n"
                    f"   조정 수량: {balance * sell_ratio:.6f}개 → {sell_volume:.6f}개"
                )
            else:
                # 전량 매도해도 5,000원 미만이면 건너뛰기
                logger.warning(
                    f"⚠️ 최소 주문 금액 미달로 손절 건너뜀: {symbol} Level {sl_level.level}\n"
                    f"   보유 전량: {balance:.6f}개 × {price:,.0f}원 = {balance * price:,.0f}원 < 5,000원"
                )
                return

        logger.info(
            f"🚨 손절 실행 (Level {sl_level.level}): {symbol}\n"
            f"   목표 손실률: -{sl_level.loss_pct:.2f}%\n"
            f"   현재 손실률: {loss_pct:.2f}%\n"
            f"   현재가: {format_price(price)}\n"
            f"   매도 비율: {sl_level.sell_ratio:.0f}%{' (수량 조정됨)' if adjusted else ''}\n"
            f"   매도 수량: {sell_volume:.6f} / {balance:.6f}\n"
            f"   예상 금액: {estimated_amount:,.0f}원"
        )

        # 🔧 자동 매도 기록 (수동 매도와 구분용)
        self._recent_auto_sells[symbol] = {
            'quantity': sell_volume,
            'timestamp': time.time(),
            'type': f'손절 L{sl_level.level}'
        }

        # 일부 매도 (실거래 모드)
        order_result = await self.order_manager.execute_sell(
            symbol=symbol,
            volume=sell_volume,
            dry_run=False  # ⚠️ 실거래 모드 (실제 주문 실행!)
        )

        if order_result and order_result.get('success'):
            # 알림
            if self.notification_callback:
                coin_name = symbol.replace('KRW-', '')
                await self.notification_callback(
                    f"🚨 손절 완료 (Level {sl_level.level}): {coin_name}\n"
                    f"   손실률: {loss_pct:.2f}% | 매도: {sl_level.sell_ratio:.0f}% | 가격: {format_price(price)}"
                )

            logger.info(f"✅ 손절 완료: {symbol} Level {sl_level.level}")

            # 100% 매도한 경우 포지션 제거
            if sl_level.sell_ratio >= 100.0:
                # 🔧 안전한 삭제 (이미 삭제된 경우 방지)
                if symbol in self.managed_positions:
                    del self.managed_positions[symbol]
                    self.detector.unregister_managed_position(symbol)
                    logger.info(f"✅ 포지션 제거: {symbol} (전량 손절)")
                else:
                    logger.warning(f"⚠️ 포지션이 이미 제거됨: {symbol}")
        else:
            logger.error(f"❌ 손절 실패: {symbol} Level {sl_level.level}")

    async def _execute_stop_loss(self, managed: ManagedPosition, price: float, loss_pct: float):
        """손절 실행 (단일 손절, 전량 매도)"""
        symbol = managed.position.symbol
        balance = managed.total_balance
        
        logger.info(
            f"🚨 손절 실행: {symbol}\n"
            f"   손실률: {loss_pct:.2f}%\n"
            f"   현재가: {format_price(price)}\n"
            f"   수량: {balance:.6f}"
        )

        # 🔧 자동 매도 기록 (수동 매도와 구분용)
        self._recent_auto_sells[symbol] = {
            'quantity': balance,
            'timestamp': time.time(),
            'type': '손절 (단일)'
        }

        # 전량 매도 (실거래 모드)
        order_result = await self.order_manager.execute_sell(
            symbol=symbol,
            volume=balance,  # ⭐ 파라미터 이름: volume (수량)
            dry_run=False  # ⚠️ 실거래 모드 (실제 주문 실행!)
        )
        
        if order_result and order_result.get('success'):
            # 🔧 안전한 포지션 제거 (이미 삭제된 경우 방지)
            if symbol in self.managed_positions:
                del self.managed_positions[symbol]
                self.detector.unregister_managed_position(symbol)
            else:
                logger.warning(f"⚠️ 포지션이 이미 제거됨: {symbol}")

            # 알림
            if self.notification_callback:
                coin_name = symbol.replace('KRW-', '')
                await self.notification_callback(
                    f"🚨 손절 완료: {coin_name}\n"
                    f"   손실률: {loss_pct:.2f}% | 매도가: {format_price(price)}"
                )
            
            logger.info(f"✅ 손절 완료: {symbol} ({loss_pct:.2f}%)")
        else:
            logger.error(f"❌ 손절 실패: {symbol}")
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """🔧 현재 가격 조회 (WebSocket 캐시 우선, REST API fallback)"""
        # 1. WebSocket 캐시에서 확인 (실시간)
        if symbol in self.last_prices:
            return self.last_prices[symbol]

        # 2. REST API fallback (WebSocket 연결 전 또는 실패 시)
        # get_ticker()는 동기 blocking 함수이므로 별도 스레드에서 실행
        try:
            ticker = await asyncio.to_thread(self.api.get_ticker, symbol)
            if ticker and 'trade_price' in ticker:
                price = float(ticker['trade_price'])
                # 캐시에 저장
                self.last_prices[symbol] = price
                return price
        except Exception as e:
            logger.error(f"가격 조회 실패 ({symbol}): {e}")

        return None
    
    def get_status(self) -> Dict:
        """
        현재 상태 조회 (포트폴리오 수익률 포함)

        Returns:
            dict:
                - is_running: 실행 중 여부
                - managed_count: 관리 중인 포지션 수
                - total_invested: 총 투자금액 (KRW)
                - total_value: 총 평가금액 (KRW)
                - total_profit: 총 수익금액 (KRW)
                - total_return_pct: 총 수익률 (%)
                - positions: 포지션 리스트
        """
        total_invested = 0.0  # 총 투자금액
        total_value = 0.0     # 총 평가금액

        positions_data = []

        # 🔧 순회 중 딕셔너리 변경 방지 (list로 복사)
        for symbol, pos in list(self.managed_positions.items()):
            # 투자금액 = 평균 진입가 × 보유량
            invested = pos.avg_entry_price * pos.total_balance
            total_invested += invested

            # 평가금액 = 현재가 × 보유량
            current_price = self.last_prices.get(symbol, pos.avg_entry_price)  # 가격 없으면 진입가 사용
            value = current_price * pos.total_balance
            total_value += value

            # 포지션 정보
            positions_data.append({
                'symbol': pos.position.symbol,
                'balance': pos.total_balance,
                'avg_price': pos.avg_entry_price,
                'current_price': current_price,
                'invested': invested,
                'value': value,
                'profit': value - invested,
                'return_pct': ((value - invested) / invested * 100) if invested > 0 else 0,
                'dca_levels': len(pos.executed_dca_levels),
                'signal_price': pos.signal_price,
            })

        # 전체 수익/손실 계산
        total_profit = total_value - total_invested
        total_return_pct = (total_profit / total_invested * 100) if total_invested > 0 else 0

        return {
            'is_running': self.is_running,
            'managed_count': len(self.managed_positions),
            'total_invested': total_invested,      # 총 투자금액
            'total_value': total_value,            # 총 평가금액
            'total_profit': total_profit,          # 총 수익금액
            'total_return_pct': total_return_pct,  # 총 수익률 (%)
            'positions': positions_data
        }

    async def update_dca_config(self, dca_config: AdvancedDcaConfig):
        """
        DCA 설정 실시간 업데이트

        설정 변경 시 모든 관리 중인 포지션에 새 설정을 적용하고,
        즉시 익절/손절 조건을 재체크하여 변경된 레벨에 도달한 포지션은 자동 매도합니다.

        Args:
            dca_config: 새로운 DCA 설정
        """
        logger.info("🔄 DCA 설정 업데이트 시작...")

        # 1. 매니저의 DCA 설정 업데이트
        old_config = self.dca_config
        self.dca_config = dca_config

        # 2. 모든 ManagedPosition의 DCA 설정 업데이트
        # 🔧 순회 중 딕셔너리 변경 방지 (list로 복사)
        for symbol, managed in list(self.managed_positions.items()):
            managed.dca_config = dca_config

        # 3. 설정 변경 로그
        logger.info(f"  📊 관리 중인 포지션: {len(self.managed_positions)}개")

        # 익절 설정 변경 로그
        if old_config.is_multi_level_tp_enabled() or dca_config.is_multi_level_tp_enabled():
            if dca_config.is_multi_level_tp_enabled():
                logger.info(f"  🎯 익절: 다단계 ({len(dca_config.take_profit_levels)}레벨)")
                for tp in dca_config.take_profit_levels:
                    logger.info(f"     Level {tp.level}: +{tp.profit_pct}% → {tp.sell_ratio}% 매도")
            else:
                logger.info(f"  🎯 익절: 단일 레벨 (+{dca_config.take_profit_pct}%)")
        else:
            logger.info(f"  🎯 익절: +{dca_config.take_profit_pct}%")

        # 손절 설정 변경 로그
        if old_config.is_multi_level_sl_enabled() or dca_config.is_multi_level_sl_enabled():
            if dca_config.is_multi_level_sl_enabled():
                logger.info(f"  🛑 손절: 다단계 ({len(dca_config.stop_loss_levels)}레벨)")
                for sl in dca_config.stop_loss_levels:
                    logger.info(f"     Level {sl.level}: -{sl.loss_pct}% → {sl.sell_ratio}% 매도")
            else:
                logger.info(f"  🛑 손절: 단일 레벨 (-{dca_config.stop_loss_pct}%)")
        else:
            logger.info(f"  🛑 손절: -{dca_config.stop_loss_pct}%")

        # 4. 즉시 모든 포지션 재체크 (익절/손절 레벨 변경 시 즉시 실행)
        if self.managed_positions:
            logger.info("🔍 변경된 설정으로 모든 포지션 재체크 중...")

            # 🔧 순회 중 딕셔너리 변경 방지 (익절/손절 시 포지션 삭제될 수 있음)
            for symbol, managed in list(self.managed_positions.items()):
                # 현재 가격 가져오기
                current_price = await self._get_current_price(symbol)

                if current_price is None:
                    logger.warning(f"  ⚠️ {symbol}: 현재 가격 조회 실패, 스킵")
                    continue

                # 수익률 계산
                avg_price = managed.avg_entry_price
                if avg_price == 0:
                    continue

                profit_pct = ((current_price - avg_price) / avg_price) * 100

                logger.info(
                    f"  📊 {symbol}: 현재 수익률 {profit_pct:+.2f}% "
                    f"(평단가 {format_price(avg_price)} → 현재가 {format_price(current_price)})"
                )

                # 익절/손절/DCA 체크 (변경된 설정으로)
                await self._check_trading_conditions(symbol, current_price)

        logger.info("✅ DCA 설정 업데이트 완료")
