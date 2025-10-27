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
        """평균 매수가"""
        return self.position.avg_buy_price
    
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
        scan_interval: int = 10,  # 스캔 주기 (초)
        notification_callback: Optional[Callable] = None,
        position_callback: Optional[Callable] = None,  # 🔧 포지션 업데이트 콜백
        balance_update_callback: Optional[Callable] = None  # 🔧 잔고 갱신 콜백
    ):
        """
        Args:
            upbit_api: Upbit API 클라이언트
            order_manager: 주문 관리자
            dca_config: DCA 설정
            scan_interval: 포지션 스캔 주기 (초)
            notification_callback: 알림 콜백 함수
            position_callback: 포지션 업데이트 콜백 함수 (새 포지션 감지, 업데이트 시 호출)
            balance_update_callback: 잔고 갱신 콜백 함수 (수동 매수 감지 시 호출)
        """
        self.api = upbit_api
        self.order_manager = order_manager
        self.dca_config = dca_config
        self.scan_interval = scan_interval
        self.notification_callback = notification_callback
        self.position_callback = position_callback  # 🔧 저장
        self.balance_update_callback = balance_update_callback  # 🔧 저장
        
        # PositionDetector 초기화
        self.detector = PositionDetector(upbit_api)
        
        # 관리 중인 포지션 (symbol -> ManagedPosition)
        self.managed_positions: Dict[str, ManagedPosition] = {}
        
        # 🔧 WebSocket 실시간 가격 수신
        self.websocket = UpbitWebSocket()
        self.last_prices: Dict[str, float] = {}  # {symbol: last_price}
        self.last_check_time: Dict[str, float] = {}  # {symbol: timestamp} DCA/익절/손절 체크
        self.last_gui_update: Dict[str, float] = {}  # {symbol: timestamp} GUI 업데이트
        
        # 실행 상태
        self.is_running = False
        self._scan_task = None  # PositionDetector 스캔 태스크
        self._websocket_task = None  # WebSocket 리스닝 태스크
        
        logger.info(f"SemiAutoManager 초기화 완료 (스캔 주기: {scan_interval}초)")
    
    async def start(self):
        """매니저 시작"""
        if self.is_running:
            logger.warning("SemiAutoManager가 이미 실행 중입니다")
            return
        
        self.is_running = True
        logger.info("🚀 SemiAutoManager 시작")
        
        # 🔧 1. WebSocket 연결
        connected = await self.websocket.connect()
        if not connected:
            logger.warning("⚠️ WebSocket 연결 실패, REST API fallback 사용")
        
        # 🔧 2. 초기 스캔 (수동 매수 감지)
        await self._scan_and_process()
        
        # 🔧 3. 관리 중인 포지션이 있으면 WebSocket 구독
        if self.managed_positions and connected:
            symbols = list(self.managed_positions.keys())
            await self.websocket.subscribe_ticker(symbols)
            logger.info(f"📊 WebSocket ticker 구독: {symbols}")
        
        # 🔧 4. PositionDetector 스캔 태스크 (10초마다 수동 매수 감지)
        self._scan_task = asyncio.create_task(self._run_scan_loop())
        
        # 🔧 5. WebSocket 리스닝 태스크 (실시간 가격 수신)
        if connected:
            self._websocket_task = asyncio.create_task(self._listen_websocket())
    
    async def stop(self):
        """매니저 종료"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 🔧 1. 스캔 태스크 취소
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        
        # 🔧 2. WebSocket 태스크 취소
        if self._websocket_task:
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                pass
        
        # 🔧 3. WebSocket 연결 종료
        await self.websocket.disconnect()
        
        logger.info("🛑 SemiAutoManager 종료")
    
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
                
                # 가격 캐시 업데이트
                self.last_prices[symbol] = price
                
                # 1. GUI 업데이트 (100ms throttling)
                await self._update_gui_if_needed(symbol, price)
                
                # 2. DCA/익절/손절 체크 (500ms throttling)
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
    
    async def _update_gui_if_needed(self, symbol: str, price: float):
        """🔧 GUI 업데이트 (1000ms throttling)"""
        if not self.position_callback:
            return

        now = time.time()
        last_update = self.last_gui_update.get(symbol, 0)

        # 1000ms = 1초마다 업데이트 (초당 1회) - GUI 과부하 방지
        if now - last_update < 1.0:
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
        await self.position_callback(position_data)
        
        # 마지막 업데이트 시간 기록
        self.last_gui_update[symbol] = now
    
    async def _check_trading_conditions(self, symbol: str, price: float):
        """🔧 DCA/익절/손절 체크 (300ms throttling)"""
        now = time.time()
        last_check = self.last_check_time.get(symbol, 0)

        # 300ms = 0.3초마다 체크 (초당 3.3회) - 실시간 대응
        # GUI 업데이트(1초)보다 빠르게 체크하여 급격한 가격 변동에 대응
        if now - last_check < 0.3:
            return
        
        # 관리 중인 포지션만 체크
        managed = self.managed_positions.get(symbol)
        if not managed:
            return
        
        try:
            # DCA 체크
            await self._check_dca(managed, price)
            
            # 익절 체크
            await self._check_take_profit(managed, price)
            
            # 손절 체크
            await self._check_stop_loss(managed, price)
            
        except Exception as e:
            logger.error(f"{symbol} DCA/익절/손절 체크 에러: {e}", exc_info=True)
        
        # 마지막 체크 시간 기록
        self.last_check_time[symbol] = now
    
    async def _scan_and_process(self):
        """포지션 스캔 및 처리"""
        try:
            # 1. 포지션 스캔
            result = self.detector.scan_positions()
            
            # 2. 새로운 수동 매수 처리
            for position in result['new_manual']:
                await self._on_new_manual_buy(position)
            
            # 3. 관리 중인 포지션 업데이트
            for position in result['managed']:
                await self._update_managed_position(position)
            
            # 4. 현재 가격 조회 및 DCA/익절/손절 체크
            await self._check_all_positions()
            
        except Exception as e:
            logger.error(f"포지션 스캔 중 에러: {e}", exc_info=True)
    
    async def _on_new_manual_buy(self, position: Position):
        """새로운 수동 매수 감지 시 처리"""
        symbol = position.symbol
        
        logger.info(
            f"🔔 새로운 수동 매수 감지: {symbol} "
            f"수량={position.balance:.6f} 평단가={position.avg_buy_price:,.0f}원"
        )
        
        # 평단가 0원인 포지션은 제외 (에어드랍 코인 등)
        if position.avg_buy_price == 0:
            logger.warning(f"⚠️ 평단가 0원 포지션 제외: {symbol} (에어드랍 또는 이벤트 지급)")
            return
        
        # 현재 가격 조회
        current_price = await self._get_current_price(symbol)
        
        if current_price is None:
            logger.warning(f"현재 가격 조회 실패: {symbol}")
            return
        
        # ManagedPosition 생성
        # ⭐ signal_price를 평단가로 설정 (사용자가 매수한 가격 기준)
        managed = ManagedPosition(
            position=position,
            dca_config=self.dca_config,
            initial_signal_price=position.avg_buy_price  # 평단가 기준
        )
        
        self.managed_positions[symbol] = managed
        
        # PositionDetector에 관리 포지션 등록
        self.detector.register_managed_position(symbol, position)
        
        # 알림
        if self.notification_callback:
            await self.notification_callback(
                f"🔔 수동 매수 감지\n"
                f"심볼: {symbol}\n"
                f"수량: {position.balance:.6f}\n"
                f"평단가: {position.avg_buy_price:,.0f}원\n"
                f"현재가: {current_price:,.0f}원\n"
                f"자동 관리 시작!"
            )
        
        # 🔧 포지션 업데이트 콜백 (GUI 업데이트용)
        if self.position_callback:
            position_data = {
                'symbol': symbol,
                'position': position.balance,
                'entry_price': position.avg_buy_price,
                'current_price': current_price,
                'profit_loss': (current_price - position.avg_buy_price) * position.balance,
                'return_pct': ((current_price - position.avg_buy_price) / position.avg_buy_price) * 100,
                'entry_time': managed.created_at.isoformat()
            }
            await self.position_callback(position_data)
        
        # 🔧 WebSocket에 모든 관리 심볼 재구독 (기존 구독 유지)
        if self.websocket.is_connected:
            try:
                all_symbols = list(self.managed_positions.keys())
                await self.websocket.subscribe_ticker(all_symbols)
                logger.info(f"📊 WebSocket ticker 재구독: {all_symbols}")
            except Exception as e:
                logger.warning(f"⚠️ WebSocket 구독 실패: {e}")

        # 🔧 잔고 갱신 콜백 호출 (반자동 수동 매수 감지 시)
        if self.balance_update_callback:
            try:
                if asyncio.iscoroutinefunction(self.balance_update_callback):
                    await self.balance_update_callback()
                else:
                    self.balance_update_callback()
                logger.debug("✅ 잔고 갱신 콜백 호출 완료 (수동 매수 감지)")
            except Exception as e:
                logger.error(f"❌ 잔고 갱신 콜백 실패: {e}")

        logger.info(f"✅ 관리 포지션 등록: {managed}")
    
    async def _update_managed_position(self, position: Position):
        """관리 중인 포지션 정보 업데이트"""
        symbol = position.symbol
        
        if symbol in self.managed_positions:
            self.managed_positions[symbol].update_position(position)
            
            # 🔧 포지션 업데이트 콜백 (GUI 실시간 업데이트용)
            if self.position_callback:
                current_price = await self._get_current_price(symbol)
                if current_price:
                    position_data = {
                        'symbol': symbol,
                        'position': position.balance,
                        'entry_price': position.avg_buy_price,
                        'current_price': current_price,
                        'profit_loss': (current_price - position.avg_buy_price) * position.balance,
                        'return_pct': ((current_price - position.avg_buy_price) / position.avg_buy_price) * 100,
                        'entry_time': self.managed_positions[symbol].created_at.isoformat()
                    }
                    await self.position_callback(position_data)
    
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
                # DCA 추가 매수 실행
                await self._execute_dca_buy(managed, level_config, current_price)
                managed.executed_dca_levels.add(level)
    
    async def _check_take_profit(self, managed: ManagedPosition, current_price: float):
        """익절 체크"""
        if not self.dca_config.enabled:
            return
        
        avg_price = managed.avg_entry_price
        
        # 평단가 0 방지
        if avg_price == 0:
            return
        
        profit_pct = ((current_price - avg_price) / avg_price) * 100
        
        # 익절 조건
        if profit_pct >= self.dca_config.take_profit_pct:
            await self._execute_take_profit(managed, current_price, profit_pct)
    
    async def _check_stop_loss(self, managed: ManagedPosition, current_price: float):
        """손절 체크"""
        if not self.dca_config.enabled:
            return
        
        avg_price = managed.avg_entry_price
        
        # 평단가 0 방지
        if avg_price == 0:
            return
        
        loss_pct = ((current_price - avg_price) / avg_price) * 100
        
        # 손절 조건 (설정값이 양수로 저장되어 있으므로 음수로 변환하여 비교)
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
            f"   현재가: {price:,.0f}원\n"
            f"   매수 금액: {buy_amount:,.0f}원\n"
            f"   하락률: {level_config.drop_pct}%"
        )
        
        # 주문 실행 (dry_run 모드)
        order_result = await self.order_manager.execute_buy(
            symbol=symbol,
            amount=buy_amount,
            dry_run=True  # ⭐ Dry-run 모드 (실제 주문 안 보냄)
        )
        
        if order_result and order_result.get('success'):
            # 알림
            if self.notification_callback:
                await self.notification_callback(
                    f"💰 DCA 추가 매수 (Level {level})\n"
                    f"심볼: {symbol}\n"
                    f"가격: {price:,.0f}원\n"
                    f"금액: {buy_amount:,.0f}원\n"
                    f"하락률: {level_config.drop_pct}%"
                )
            
            logger.info(f"✅ DCA 추가 매수 완료: {symbol} Level {level}")
        else:
            logger.error(f"❌ DCA 추가 매수 실패: {symbol} Level {level}")
    
    async def _execute_take_profit(self, managed: ManagedPosition, price: float, profit_pct: float):
        """익절 실행"""
        symbol = managed.position.symbol
        balance = managed.total_balance
        
        logger.info(
            f"🎯 익절 실행: {symbol}\n"
            f"   수익률: {profit_pct:.2f}%\n"
            f"   현재가: {price:,.0f}원\n"
            f"   수량: {balance:.6f}"
        )
        
        # 전량 매도 (dry_run 모드)
        order_result = await self.order_manager.execute_sell(
            symbol=symbol,
            volume=balance,  # ⭐ 파라미터 이름: volume (수량)
            dry_run=True  # ⭐ Dry-run 모드 (실제 주문 안 보냄)
        )
        
        if order_result and order_result.get('success'):
            # 포지션 제거
            del self.managed_positions[symbol]
            self.detector.unregister_managed_position(symbol)
            
            # 알림
            if self.notification_callback:
                await self.notification_callback(
                    f"🎯 익절 완료!\n"
                    f"심볼: {symbol}\n"
                    f"수익률: {profit_pct:.2f}%\n"
                    f"매도가: {price:,.0f}원"
                )
            
            logger.info(f"✅ 익절 완료: {symbol} (+{profit_pct:.2f}%)")
        else:
            logger.error(f"❌ 익절 실패: {symbol}")
    
    async def _execute_stop_loss(self, managed: ManagedPosition, price: float, loss_pct: float):
        """손절 실행"""
        symbol = managed.position.symbol
        balance = managed.total_balance
        
        logger.info(
            f"🚨 손절 실행: {symbol}\n"
            f"   손실률: {loss_pct:.2f}%\n"
            f"   현재가: {price:,.0f}원\n"
            f"   수량: {balance:.6f}"
        )
        
        # 전량 매도 (dry_run 모드)
        order_result = await self.order_manager.execute_sell(
            symbol=symbol,
            volume=balance,  # ⭐ 파라미터 이름: volume (수량)
            dry_run=True  # ⭐ Dry-run 모드 (실제 주문 안 보냄)
        )
        
        if order_result and order_result.get('success'):
            # 포지션 제거
            del self.managed_positions[symbol]
            self.detector.unregister_managed_position(symbol)
            
            # 알림
            if self.notification_callback:
                await self.notification_callback(
                    f"🚨 손절 완료\n"
                    f"심볼: {symbol}\n"
                    f"손실률: {loss_pct:.2f}%\n"
                    f"매도가: {price:,.0f}원"
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
        try:
            ticker = self.api.get_ticker(symbol)
            if ticker and 'trade_price' in ticker:
                price = float(ticker['trade_price'])
                # 캐시에 저장
                self.last_prices[symbol] = price
                return price
        except Exception as e:
            logger.error(f"가격 조회 실패 ({symbol}): {e}")
        
        return None
    
    def get_status(self) -> Dict:
        """현재 상태 조회"""
        return {
            'is_running': self.is_running,
            'managed_count': len(self.managed_positions),
            'positions': [
                {
                    'symbol': pos.position.symbol,
                    'balance': pos.total_balance,
                    'avg_price': pos.avg_entry_price,
                    'dca_levels': len(pos.executed_dca_levels),
                    'signal_price': pos.signal_price,
                }
                for pos in self.managed_positions.values()
            ]
        }
