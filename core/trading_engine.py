"""
Trading Engine
트레이딩 엔진

모든 컴포넌트를 통합한 메인 트레이딩 엔진:
- 실시간 데이터 수신 (WebSocket)
- 전략 신호 생성 (Strategy)
- 리스크 관리 (RiskManager)
- 주문 실행 (OrderManager)
- 알림 전송 (TelegramBot)
- 상태 관리 및 모니터링

Example:
    >>> engine = TradingEngine(config)
    >>> await engine.start()
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

from core.upbit_websocket import CandleWebSocket, UpbitWebSocket
from core.data_buffer import CandleBuffer
from core.strategies import BollingerBands_Strategy, AggressiveTestStrategy
from core.risk_manager import RiskManager
from core.order_manager import OrderManager
from core.upbit_api import UpbitAPI
from core.telegram_bot import TelegramBot
from gui.dca_config import DcaConfigManager  # DCA 설정 로드

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    트레이딩 엔진
    
    모든 컴포넌트를 통합하여 자동 매매를 수행합니다.
    """
    
    def __init__(self, config: Dict, trade_callback=None):
        """
        트레이딩 엔진 초기화
        
        Args:
            config: 설정 딕셔너리
                {
                    'symbol': 'KRW-BTC',
                    'strategy': {...},
                    'risk_manager': {...},
                    'order_amount': 10000,
                    'dry_run': True,
                    'upbit': {'access_key': '...', 'secret_key': '...'},
                    'telegram': {'token': '...', 'chat_id': '...'}
                }
            trade_callback: 거래 발생 시 호출될 콜백 함수 (trade_data: dict)
        """
        self.config = config
        self.symbol = config.get('symbol', 'KRW-BTC')
        self.order_amount = config.get('order_amount', 10000)
        self.dry_run = config.get('dry_run', True)
        self.trade_callback = trade_callback  # 🔧 거래 콜백
        
        # 상태 변수
        self.is_running = False
        self.position = 0.0  # 보유 수량
        self.entry_price = None  # 진입 가격
        self.entry_time = None  # 진입 시각
        self.initial_capital = None  # 시작 자본
        self.current_capital = None  # 현재 자본 (KRW 잔액)
        self.last_price = None  # 최근 가격 (총 자산 계산용)

        # 🔧 다단계 익절/손절 상태
        self.avg_entry_price = None  # 평균 단가
        self.total_invested = 0.0  # 총 투자 금액
        self.executed_tp_levels = set()  # 실행된 익절 레벨 (1, 2, 3...)
        self.executed_sl_levels = set()  # 실행된 손절 레벨 (1, 2, 3...)
        self.executed_dca_levels = set()  # 🔧 실행된 DCA 추가매수 레벨 (1, 2, 3...)

        # 🔧 DCA 신호 가격 (매수 신호 발생 시점의 가격)
        self.signal_price = None  # DCA 기준점

        # 통계
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0

        # DCA 설정 로드
        from gui.dca_config import AdvancedDcaConfig  # 🔧 클래스 import

        self.dca_config_manager = DcaConfigManager()
        if 'dca_config' in self.config and self.config['dca_config']:
            # config에서 전달받은 DCA 설정 사용 (다중 코인 지원)
            self.dca_config = AdvancedDcaConfig.from_dict(self.config['dca_config'])
            logger.info(f"  DCA 설정: config에서 로드 ({'활성화' if self.dca_config.enabled else '비활성화'})")
        else:
            # 파일에서 로드 (단일 코인 모드)
            self.dca_config = self.dca_config_manager.load()
            logger.info(f"  DCA 설정: 파일에서 로드 ({'활성화' if self.dca_config.enabled else '비활성화'})")

        # 컴포넌트 초기화
        self._init_components()
        
        logger.info("✅ 트레이딩 엔진 초기화 완료")
    
    def _init_components(self):
        """컴포넌트 초기화"""

        # 1. 전략
        strategy_config = self.config.get('strategy', {})
        strategy_type = strategy_config.get('type', 'filtered_bb')
        
        # 전략 타입에 따라 인스턴스 생성
        if strategy_type == 'filtered_bb':
            from core.strategies.proximity_bb_strategy import ProximityBollingerBandsStrategy
            # DCA 최적화 전략 사용 (근접 모드, 빈번한 거래 기회)
            self.strategy = ProximityBollingerBandsStrategy(symbol=self.symbol)
            logger.info(f"  전략: {self.strategy.name} (DCA 최적화 - 근접 모드)")
            
        elif strategy_type == 'bb':
            self.strategy = BollingerBands_Strategy(
                period=strategy_config.get('period', 20),
                std_dev=strategy_config.get('std_dev', 2.0)
            )
            logger.info(f"  전략: {self.strategy.name}")
            
        elif strategy_type == 'rsi':
            from core.strategies import RSI_Strategy
            self.strategy = RSI_Strategy(
                period=strategy_config.get('period', 14),
                oversold=strategy_config.get('oversold', 30),
                overbought=strategy_config.get('overbought', 70)
            )
            logger.info(f"  전략: {self.strategy.name}")
            
        elif strategy_type == 'macd':
            from core.strategies import MACD_Strategy
            self.strategy = MACD_Strategy(
                fast_period=strategy_config.get('fast_period', 12),
                slow_period=strategy_config.get('slow_period', 26),
                signal_period=strategy_config.get('signal_period', 9)
            )
            logger.info(f"  전략: {self.strategy.name}")
            
        else:
            logger.warning(f"⚠️ 알 수 없는 전략 타입: {strategy_type}, 기본 BB 사용")
            self.strategy = BollingerBands_Strategy(period=20, std_dev=2.0)
            logger.info(f"  전략: {self.strategy.name}")
        
        # 2. 리스크 관리자
        risk_config = self.config.get('risk_manager', {})
        self.risk_manager = RiskManager(
            stop_loss_pct=risk_config.get('stop_loss_pct', 5.0),
            take_profit_pct=risk_config.get('take_profit_pct', 10.0),
            max_daily_loss_pct=risk_config.get('max_daily_loss_pct', 10.0),
            trailing_stop_pct=risk_config.get('trailing_stop_pct', None)
        )
        logger.info(f"  리스크 관리: SL={self.risk_manager.stop_loss_pct}%, TP={self.risk_manager.take_profit_pct}%")
        
        # 3. 데이터 버퍼
        # 과거 데이터 200개 로드 시 즉시 준비 (볼린저 밴드 계산 가능)
        self.buffer = CandleBuffer(max_size=200, required_count=20)
        logger.info(f"  데이터 버퍼: max=200, required=20 (과거 데이터 로드 시 즉시 준비)")
        
        # 4. 웹소켓
        self.websocket = CandleWebSocket(interval_seconds=10)
        logger.info(f"  웹소켓: 1분봉, 10초 간격")

        # 🔧 실시간 가격 추적용 Ticker WebSocket
        self.ticker_ws = UpbitWebSocket()
        logger.info(f"  Ticker WebSocket: 실시간 가격 추적 활성화")
        
        # 5. 주문 관리자
        if not self.dry_run:
            upbit_config = self.config.get('upbit', {})
            api = UpbitAPI(
                access_key=upbit_config.get('access_key'),
                secret_key=upbit_config.get('secret_key')
            )
            self.order_manager = OrderManager(api, min_order_amount=5000)
            logger.info(f"  주문 관리자: 실거래 모드")
        else:
            self.order_manager = None
            logger.info(f"  주문 관리자: Dry Run 모드")
        
        # 6. 텔레그램 봇 (선택적)
        telegram_config = self.config.get('telegram', {})
        if telegram_config.get('token') and telegram_config.get('chat_id'):
            self.telegram = TelegramBot(
                token=telegram_config['token'],
                chat_id=telegram_config['chat_id']
            )
            logger.info(f"  텔레그램: 활성화")
        else:
            self.telegram = None
            logger.info(f"  텔레그램: 비활성화")
    
    async def start(self):
        """트레이딩 시작"""
        if self.is_running:
            logger.warning("⚠️ 트레이딩 엔진이 이미 실행 중입니다")
            return
        
        self.is_running = True
        
        # 시작 알림
        if self.telegram:
            await self.telegram.send_message(
                f"🚀 *트레이딩 시작*\n\n"
                f"심볼: `{self.symbol}`\n"
                f"전략: `{self.strategy.name}`\n"
                f"모드: `{'Dry Run' if self.dry_run else '실거래'}`\n"
                f"시작 시각: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            )
        
        # 초기 자본 설정
        if not self.dry_run and self.order_manager:
            self.initial_capital = self.order_manager.api.get_balance('KRW')
            self.current_capital = self.initial_capital
        else:
            self.initial_capital = 1000000  # Dry Run: 100만원
            self.current_capital = self.initial_capital
        
        logger.info(f"💰 시작 자본: {self.initial_capital:,.0f}원")

        # 🔧 당일 9시부터 현재까지의 1분봉 데이터 로드
        await self._load_historical_candles()

        # Ticker WebSocket 연결 및 구독
        await self.ticker_ws.connect()
        await self.ticker_ws.subscribe_ticker([self.symbol])
        logger.info(f"📡 실시간 Ticker 구독 시작: {self.symbol}")

        # 🔧 Ticker 루프와 Trading 루프를 병렬로 실행
        ticker_task = asyncio.create_task(self._ticker_loop())
        trading_task = asyncio.create_task(self._trading_loop())

        # 둘 중 하나라도 종료되면 전체 중단
        try:
            await asyncio.gather(ticker_task, trading_task)
        except Exception as e:
            logger.error(f"❌ 루프 실행 오류: {e}")
            ticker_task.cancel()
            trading_task.cancel()
    
    async def stop(self):
        """트레이딩 중단"""
        if not self.is_running:
            return

        self.is_running = False

        # 🔧 WebSocket 명시적 종료 (즉시 루프 탈출)
        if self.websocket:
            await self.websocket.disconnect()
            logger.info("🔌 Candle WebSocket 연결 종료")

        if self.ticker_ws:
            await self.ticker_ws.disconnect()
            logger.info("🔌 Ticker WebSocket 연결 종료")

        # 중단 알림
        if self.telegram:
            await self.telegram.send_message(
                f"⏸️ *트레이딩 중단*\n\n"
                f"중단 시각: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
                f"최종 자본: `{self.current_capital:,.0f}원`\n"
                f"수익률: `{((self.current_capital - self.initial_capital) / self.initial_capital * 100):+.2f}%`"
            )

        logger.info("⏹️ 트레이딩 엔진 중단")

    def update_dca_config(self, dca_config):
        """
        실행 중 DCA 설정 업데이트 (동기 메서드)
        
        Args:
            dca_config: 새로운 AdvancedDcaConfig 객체
        """
        logger.info(f"🔄 {self.symbol}: DCA 설정 업데이트")
        
        # 기존 설정 정보 로깅
        old_tp = "다단계" if self.dca_config.is_multi_level_tp_enabled() else f"{self.dca_config.take_profit_pct}%"
        old_sl = "다단계" if self.dca_config.is_multi_level_sl_enabled() else f"{self.dca_config.stop_loss_pct}%"
        
        # 새 설정으로 교체
        self.dca_config = dca_config
        
        # 새 설정 정보 로깅
        new_tp = "다단계" if dca_config.is_multi_level_tp_enabled() else f"{dca_config.take_profit_pct}%"
        new_sl = "다단계" if dca_config.is_multi_level_sl_enabled() else f"{dca_config.stop_loss_pct}%"
        
        logger.info(f"  🎯 익절: {old_tp} → {new_tp}")
        logger.info(f"  🛑 손절: {old_sl} → {new_sl}")
        logger.info(f"  📊 DCA 레벨: {len(dca_config.levels)}단계")
        logger.info(f"  ⚙️ DCA 상태: {'활성화' if dca_config.enabled else '비활성화'}")
        
        # ⚠️ 주의: 이미 실행된 익절/손절 레벨은 초기화하지 않음
        # 기존 포지션의 executed_tp_levels, executed_sl_levels 유지
        # 새로운 레벨만 추가로 체크됨
        
        logger.info(f"✅ {self.symbol}: DCA 설정 업데이트 완료")

    async def _load_historical_candles(self):
        """
        당일 9시부터 현재까지의 1분봉 데이터 로드

        - REST API를 사용하여 과거 데이터 조회
        - CandleBuffer에 미리 채워서 차트가 바로 표시되도록 함
        """
        from datetime import datetime, timedelta
        import requests

        try:
            # 당일 9시 시각 계산
            now = datetime.now()
            today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)

            # 9시 이전이면 어제 9시부터 로드
            if now < today_9am:
                today_9am = today_9am - timedelta(days=1)

            # 🔧 전략에 필요한 캔들 수 계산
            # - 볼린저 밴드: 20개
            # - MA240: 240개 (4시간)
            # → 안전하게 최대 200개 로드 (Upbit API 제한)
            required_candles = 200  # 업비트 API 최대값

            logger.info(f"📊 과거 1분봉 데이터 로드 시작: 최근 {required_candles}개 (전략 계산용)")
            
            # 🔧 count를 고정값 200으로 변경 (9시 기준 제거)
            count = required_candles

            url = "https://api.upbit.com/v1/candles/minutes/1"
            params = {
                'market': self.symbol,
                'count': count
            }

            # 🔧 타임아웃 설정 (10초) - 무한 대기 방지
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            candles = response.json()

            # 시간순으로 정렬 (오래된 것부터)
            candles = sorted(candles, key=lambda x: x['candle_date_time_kst'])

            # CandleBuffer에 추가
            for candle_data in candles:
                # 🔧 타임스탬프 문자열 → datetime 변환 (pandas Timestamp와 타입 일치)
                timestamp_str = candle_data['candle_date_time_kst']
                # '2025-01-17T12:36:00+09:00' 형식을 datetime으로 변환
                timestamp_dt = datetime.fromisoformat(timestamp_str.replace('+09:00', ''))

                # Upbit API 응답을 CandleBuffer 형식으로 변환
                candle = {
                    'symbol': self.symbol,
                    'timestamp': timestamp_dt,  # datetime 객체로 변환
                    'open_price': candle_data['opening_price'],
                    'high_price': candle_data['high_price'],
                    'low_price': candle_data['low_price'],
                    'close_price': candle_data['trade_price'],
                    'candle_acc_trade_volume': candle_data['candle_acc_trade_volume'],
                    'trade_price': candle_data['trade_price']  # 현재가
                }

                self.buffer.add_candle(candle, is_realtime=False)  # 과거 데이터 표시

            # 🔧 과거 데이터 로드 완료 표시 (이제부터 실시간 캔들 대기)
            self.buffer.mark_historical_loaded()

            logger.info(f"✅ 과거 1분봉 데이터 로드 완료: {len(candles)}개 | 버퍼 상태: {len(self.buffer)}/{self.buffer.required_count}")

        except Exception as e:
            logger.error(f"❌ 과거 데이터 로드 실패: {e}")
            # 실패해도 계속 진행 (WebSocket으로 실시간 데이터 수집)

    async def _ticker_loop(self):
        """
        실시간 Ticker 가격 추적 및 TP/SL 체크 루프

        - 0.1~1초 간격으로 실시간 가격 업데이트
        - 포지션 보유 중이면 즉시 익절/손절 체크
        - 캔들 데이터와 독립적으로 동작
        """
        logger.info("📡 Ticker 루프 시작 (실시간 가격 추적)")

        try:
            async for ticker in self.ticker_ws.listen():
                if not self.is_running:
                    break

                # 실시간 가격 업데이트
                current_price = ticker['trade_price']
                self.last_price = current_price

                # 포지션 보유 중이면 실시간 TP/SL 체크
                if self.position > 0 and self.avg_entry_price and self.dca_config.enabled:
                    tp_sl_executed = await self._check_multi_level_tp_sl(current_price)

                    if tp_sl_executed:
                        logger.info(f"💹 실시간 TP/SL 실행 완료 (가격: {current_price:,.0f}원)")

        except asyncio.CancelledError:
            logger.info("⚠️ Ticker 루프 취소됨")
        except Exception as e:
            logger.error(f"❌ Ticker 루프 오류: {e}")
            import traceback
            traceback.print_exc()

    async def _trading_loop(self):
        """메인 트레이딩 루프"""
        logger.info("📊 트레이딩 루프 시작")
        
        try:
            async for candle in self.websocket.subscribe_candle([self.symbol], unit="1"):
                if not self.is_running:
                    break
                
                # 캔들 데이터 버퍼에 추가 (실시간 데이터)
                self.buffer.add_candle(candle, is_realtime=True)
                current_price = candle['trade_price']
                self.last_price = current_price  # 🔧 최근 가격 저장 (총 자산 계산용)

                # 버퍼 준비 확인 (과거 데이터 200개 로드 시 즉시 준비됨)
                if not self.buffer.is_ready():
                    continue  # 조용히 대기 (로그 불필요)
                
                # 리스크 관리 체크 (포지션 보유 중)
                if self.position > 0:
                    # 🔧 다단계 익절/손절 체크 (평균 단가 기준)
                    if self.avg_entry_price and self.dca_config.enabled:
                        tp_sl_executed = await self._check_multi_level_tp_sl(current_price)
                        if tp_sl_executed:
                            continue  # 다단계 익절/손절 실행됨, 다음 루프로

                    # 기존 리스크 관리 (하위 호환)
                    should_exit, exit_reason = self.risk_manager.should_exit_position(
                        current_price,
                        self.current_capital,
                        datetime.now()
                    )

                    if should_exit:
                        logger.warning(f"🚨 리스크 관리 청산: {exit_reason}")
                        await self._execute_sell(current_price, exit_reason)
                        continue
                
                # 🔧 DCA 분할 매수 체크
                if self.dca_config.enabled:
                    # 포지션 보유 중: 추가 매수 체크
                    if self.position > 0 and self.signal_price:
                        dca_executed = await self._check_dca_levels(current_price)
                        if dca_executed:
                            continue  # DCA 매수 실행됨, 다음 루프로
                    # 포지션 없음: 신호 대기 중
                    elif self.position == 0 and self.signal_price:
                        # 신호 가격 기준 DCA 레벨 체크
                        dca_executed = await self._check_dca_levels(current_price)
                        if dca_executed:
                            continue  # DCA 최초 매수 실행됨, 다음 루프로

                # 전략 신호 생성
                candles_df = self.buffer.get_candles(100)
                signal = self.strategy.generate_signal(candles_df)

                if signal:
                    logger.info(f"🚨 신호 발생: {signal.upper()}")

                    # 텔레그램 알림
                    if self.telegram:
                        await self.telegram.send_signal_alert(signal, self.symbol, current_price)

                    # 매수 신호만 사용 (매도는 DCA 익절/손절로만 처리)
                    if signal == 'buy' and self.position == 0:
                        # 🔧 신호 가격 기록 (DCA 기준점)
                        self.signal_price = current_price
                        logger.info(f"📍 매수 신호 가격 기록: {self.signal_price:,.0f}원 (DCA 기준점)")

                        # DCA 활성화 시: 즉시 DCA 레벨 체크 (0.0% 레벨 지원)
                        if self.dca_config.enabled:
                            logger.info(f"🔍 DCA 모드: 레벨 체크 중...")
                            # 🔧 즉시 DCA 체크 추가 (신호 발생 시점에 바로 실행)
                            dca_executed = await self._check_dca_levels(current_price)
                            if not dca_executed:
                                logger.info(f"⏳ DCA 레벨 대기 중... (하락 필요)")
                        else:
                            # DCA 비활성화 시: 즉시 매수
                            await self._execute_buy(current_price)
                    
                    # ⚠️ 전략의 매도 신호는 사용하지 않음
                    # 매도는 DCA 익절/손절 설정으로만 처리됨
                    # (고급 DCA 설정에서 익절률/손절률 조정 가능)
                    elif signal == 'sell':
                        logger.debug(f"ℹ️ 매도 신호 감지됨 (DCA 익절/손절로 처리되므로 무시)")
        
        except KeyboardInterrupt:
            logger.info("⚠️ 사용자에 의해 중단됨")
        except Exception as e:
            logger.error(f"❌ 트레이딩 루프 오류: {e}")
            import traceback
            traceback.print_exc()
    
    async def _execute_buy(self, price: float):
        """매수 실행"""
        logger.info(f"🛒 매수 실행: {self.order_amount:,.0f}원 @ {price:,.0f}원")
        
        if self.dry_run:
            # Dry Run 모드
            volume = self.order_amount / price
            result = {
                'success': True,
                'order_id': f'dry_run_buy_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'symbol': self.symbol,
                'side': 'buy',
                'amount': self.order_amount,
                'executed_volume': volume,
                'executed_price': price,
                'timestamp': datetime.now()
            }
            
            # 포지션 업데이트
            self.position = volume
            self.entry_price = price
            self.entry_time = datetime.now()
            self.current_capital -= self.order_amount

            # 🔧 평균 단가 계산 (누적 매수)
            self.total_invested += self.order_amount
            self.avg_entry_price = self.total_invested / self.position

            # 리스크 관리자 포지션 시작
            self.risk_manager.on_position_open(price, self.current_capital)
        else:
            # 실거래
            result = await self.order_manager.execute_buy(self.symbol, self.order_amount, dry_run=False)
            
            if result['success']:
                self.position = result['executed_volume']
                self.entry_price = result['executed_price']
                self.entry_time = datetime.now()
                self.current_capital = self.order_manager.api.get_balance('KRW')

                # 🔧 평균 단가 계산 (누적 매수)
                self.total_invested += self.order_amount
                self.avg_entry_price = self.total_invested / self.position

                # 리스크 관리자 포지션 시작
                self.risk_manager.on_position_open(result['executed_price'], self.current_capital)
        
        # 텔레그램 알림
        if self.telegram:
            await self.telegram.send_order_result(result)
        
        if result['success']:
            self.total_trades += 1
            logger.info(f"✅ 매수 완료: {self.position:.8f}개")
            
            # 🔧 거래 콜백 호출
            if self.trade_callback:
                trade_data = {
                    'timestamp': result['timestamp'],
                    'symbol': self.symbol,
                    'trade_type': 'buy',
                    'price': price,
                    'quantity': result['executed_volume'],
                    'amount': self.order_amount,
                    'profit': 0.0,
                    'profit_pct': 0.0,
                    'reason': '시그널 매수',
                    'order_id': result.get('order_id')
                }
                self.trade_callback(trade_data)
    
    async def _execute_sell(self, price: float, reason: str):
        """매도 실행"""
        logger.info(f"💵 매도 실행: {self.position:.8f}개 @ {price:,.0f}원 (이유: {reason})")
        
        if self.dry_run:
            # Dry Run 모드
            funds = self.position * price
            result = {
                'success': True,
                'order_id': f'dry_run_sell_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'symbol': self.symbol,
                'side': 'sell',
                'volume': self.position,
                'executed_funds': funds,
                'executed_price': price,
                'timestamp': datetime.now()
            }
            
            # 손익 계산
            profit = funds - self.order_amount
            profit_pct = (profit / self.order_amount) * 100
            
            # 통계 업데이트
            if profit > 0:
                self.winning_trades += 1
                self.total_profit += profit
            else:
                self.losing_trades += 1
                self.total_loss += abs(profit)
            
            # 포지션 정리
            self.current_capital += funds
            self.position = 0.0
            self.entry_price = None
            self.entry_time = None

            # 🔧 다단계 익절/손절 상태 초기화
            self.avg_entry_price = None
            self.total_invested = 0.0
            self.executed_tp_levels.clear()
            self.executed_sl_levels.clear()
            self.executed_dca_levels.clear()  # 🔧 DCA 레벨 초기화
            self.signal_price = None  # 🔧 신호 가격 초기화

            # 리스크 관리자 포지션 종료
            self.risk_manager.on_position_close()
        else:
            # 실거래
            result = await self.order_manager.execute_sell(self.symbol, self.position, dry_run=False)

            if result['success']:
                # 손익 계산
                profit = result['executed_funds'] - self.order_amount
                profit_pct = (profit / self.order_amount) * 100

                # 통계 업데이트
                if profit > 0:
                    self.winning_trades += 1
                    self.total_profit += profit
                else:
                    self.losing_trades += 1
                    self.total_loss += abs(profit)

                # 포지션 정리
                self.current_capital = self.order_manager.api.get_balance('KRW')
                self.position = 0.0
                self.entry_price = None
                self.entry_time = None

                # 🔧 다단계 익절/손절 상태 초기화
                self.avg_entry_price = None
                self.total_invested = 0.0
                self.executed_tp_levels.clear()
                self.executed_sl_levels.clear()
                self.executed_dca_levels.clear()  # 🔧 DCA 레벨 초기화
                self.signal_price = None  # 🔧 신호 가격 초기화

                # 리스크 관리자 포지션 종료
                self.risk_manager.on_position_close()
        
        # 텔레그램 알림
        if self.telegram:
            await self.telegram.send_order_result(result)
            
            # 리스크 이벤트 알림
            if reason != 'strategy_signal':
                await self.telegram.send_risk_event(reason, {
                    'symbol': self.symbol,
                    'price': price,
                    'pnl_pct': profit_pct
                })
        
        if result['success']:
            logger.info(f"✅ 매도 완료: {result['executed_funds']:,.0f}원, 손익: {profit:+,.0f}원 ({profit_pct:+.2f}%)")
            
            # 🔧 거래 콜백 호출
            if self.trade_callback:
                trade_data = {
                    'timestamp': result['timestamp'],
                    'symbol': self.symbol,
                    'trade_type': 'sell',
                    'price': price,
                    'quantity': result.get('volume', result.get('executed_volume', 0)),
                    'amount': result['executed_funds'],
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'reason': reason,
                    'order_id': result.get('order_id')
                }
                self.trade_callback(trade_data)

    async def _check_multi_level_tp_sl(self, current_price: float) -> bool:
        """
        다단계 익절/손절 체크 및 실행

        Args:
            current_price: 현재가

        Returns:
            bool: 익절/손절이 실행되었는지 여부
        """
        if not self.avg_entry_price or self.position == 0:
            return False

        executed = False

        # 1️⃣ 익절 레벨 체크
        tp_levels = self.dca_config.get_tp_levels_with_prices(self.avg_entry_price)
        for tp in tp_levels:
            level = tp['level']
            target_price = tp['price']
            sell_ratio = tp['sell_ratio']

            # 조건: 현재가 >= 목표가 AND 아직 실행 안 됨
            if current_price >= target_price and level not in self.executed_tp_levels:
                logger.info(f"🎯 익절 레벨 {level} 도달: {current_price:,.0f}원 >= {target_price:,.0f}원 (매도 {sell_ratio}%)")
                await self._execute_partial_sell(current_price, sell_ratio, level, f'take_profit_L{level}')
                self.executed_tp_levels.add(level)
                executed = True
                break  # 한 번에 하나씩 실행

        # 2️⃣ 손절 레벨 체크 (익절 미실행 시에만)
        if not executed:
            sl_levels = self.dca_config.get_sl_levels_with_prices(self.avg_entry_price)
            for sl in sl_levels:
                level = sl['level']
                target_price = sl['price']
                sell_ratio = sl['sell_ratio']

                # 조건: 현재가 <= 목표가 AND 아직 실행 안 됨
                if current_price <= target_price and level not in self.executed_sl_levels:
                    logger.warning(f"🛑 손절 레벨 {level} 도달: {current_price:,.0f}원 <= {target_price:,.0f}원 (매도 {sell_ratio}%)")
                    await self._execute_partial_sell(current_price, sell_ratio, level, f'stop_loss_L{level}')
                    self.executed_sl_levels.add(level)
                    executed = True
                    break  # 한 번에 하나씩 실행

        return executed
    
    async def _check_dca_levels(self, current_price: float) -> bool:
        """
        DCA 레벨 체크 및 실행 (신호 가격 기준)

        신호 발생 가격을 기준으로 하락률을 계산하여 DCA 레벨에 도달하면 매수
        - 레벨 1: 최초 진입 매수
        - 레벨 2, 3, ...: 추가 매수

        Args:
            current_price: 현재가

        Returns:
            bool: 매수가 실행되었는지 여부
        """
        if not self.signal_price or not self.dca_config.enabled:
            return False

        # 신호 가격 대비 하락률 계산
        drop_pct = ((current_price - self.signal_price) / self.signal_price) * 100

        # DCA 레벨 순회 (하락률이 작은 순서대로 정렬 - 레벨 1부터)
        sorted_levels = sorted(self.dca_config.levels, key=lambda x: x.drop_pct)

        for level_config in sorted_levels:
            level_num = level_config.level
            target_drop_pct = -level_config.drop_pct  # 음수로 변환 (-0.0, -0.5, -1.0 등)
            order_amount = level_config.order_amount

            # 이미 실행된 레벨인지 확인
            if level_num in self.executed_dca_levels:
                continue

            # 조건: 현재 하락률이 목표 하락률 이하 (예: -0.6% <= -0.5%)
            if drop_pct <= target_drop_pct:
                logger.info(
                    f"📊 DCA 레벨 {level_num} 도달: "
                    f"신호가격={self.signal_price:,.0f}원 → 현재가={current_price:,.0f}원 "
                    f"({drop_pct:.2f}% <= {target_drop_pct:.2f}%)"
                )

                # 매수 실행
                is_first_entry = (self.position == 0)
                await self._execute_dca_buy(current_price, level_num, order_amount, is_first_entry)

                # 레벨 실행 기록 (중복 매수 방지)
                self.executed_dca_levels.add(level_num)

                return True

        return False
    
    async def _execute_dca_buy(self, price: float, level: int, amount: float, is_first_entry: bool = False):
        """
        DCA 매수 실행

        Args:
            price: 매수 가격
            level: DCA 레벨 번호
            amount: 매수 금액
            is_first_entry: 최초 진입 매수 여부
        """
        if is_first_entry:
            logger.info(f"🛒 DCA 레벨 {level} 최초 진입: {amount:,.0f}원 @ {price:,.0f}원")
        else:
            logger.info(f"🔄 DCA 레벨 {level} 추가 매수: {amount:,.0f}원 @ {price:,.0f}원")
        
        if self.dry_run:
            # Dry Run 모드
            volume = amount / price
            result = {
                'success': True,
                'order_id': f'dry_run_dca_buy_L{level}_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'symbol': self.symbol,
                'side': 'buy',
                'amount': amount,
                'executed_volume': volume,
                'executed_price': price,
                'timestamp': datetime.now(),
                'dca_level': level
            }
            
            # 포지션 업데이트 (누적)
            prev_position = self.position
            prev_invested = self.total_invested

            self.position += volume
            self.total_invested += amount
            self.current_capital -= amount

            # 평균 단가 재계산
            self.avg_entry_price = self.total_invested / self.position

            # 🔧 최초 진입 시 entry_price와 entry_time 설정
            if is_first_entry:
                self.entry_price = price
                self.entry_time = datetime.now()

            # 로그 출력 (최초 진입 vs 추가 매수)
            if prev_position > 0:
                logger.info(
                    f"✅ DCA 추가 매수 완료: "
                    f"보유량 {prev_position:.8f} → {self.position:.8f} (+{volume:.8f}), "
                    f"평균단가 {prev_invested/prev_position:,.0f}원 → {self.avg_entry_price:,.0f}원"
                )
            else:
                logger.info(
                    f"✅ DCA 최초 진입 완료: "
                    f"보유량 {self.position:.8f}, "
                    f"평균단가 {self.avg_entry_price:,.0f}원"
                )
            
        else:
            # 실거래
            result = await self.order_manager.execute_buy(self.symbol, amount, dry_run=False)
            
            if result['success']:
                prev_position = self.position
                prev_avg = self.avg_entry_price

                self.position += result['executed_volume']
                self.total_invested += amount
                self.current_capital = self.order_manager.api.get_balance('KRW')

                # 평균 단가 재계산
                self.avg_entry_price = self.total_invested / self.position

                # 🔧 최초 진입 시 entry_price와 entry_time 설정
                if is_first_entry:
                    self.entry_price = price
                    self.entry_time = datetime.now()

                # 로그 출력 (최초 진입 vs 추가 매수)
                if prev_position > 0 and prev_avg:
                    logger.info(
                        f"✅ DCA 추가 매수 완료: "
                        f"보유량 {prev_position:.8f} → {self.position:.8f}, "
                        f"평균단가 {prev_avg:,.0f}원 → {self.avg_entry_price:,.0f}원"
                    )
                else:
                    logger.info(
                        f"✅ DCA 최초 진입 완료: "
                        f"보유량 {self.position:.8f}, "
                        f"평균단가 {self.avg_entry_price:,.0f}원"
                    )
        
        # 텔레그램 알림
        if self.telegram:
            await self.telegram.send_order_result(result)
        
        if result['success']:
            self.total_trades += 1
            
            # 🔧 거래 콜백 호출
            if self.trade_callback:
                # 최초 진입 vs 추가 매수 구분
                reason_text = f'DCA 레벨 {level} 최초 진입' if is_first_entry else f'DCA 레벨 {level} 추가매수'

                trade_data = {
                    'timestamp': result['timestamp'],
                    'symbol': self.symbol,
                    'trade_type': 'buy',
                    'price': price,
                    'quantity': result['executed_volume'],
                    'amount': amount,
                    'profit': 0.0,
                    'profit_pct': 0.0,
                    'reason': reason_text,
                    'order_id': result.get('order_id')
                }
                self.trade_callback(trade_data)

    async def _execute_partial_sell(self, price: float, sell_ratio: float, level: int, reason: str):
        """
        부분 매도 실행

        Args:
            price: 매도 가격
            sell_ratio: 매도 비율 (0~100%)
            level: 익절/손절 레벨 번호
            reason: 매도 이유 (예: 'take_profit_L1', 'stop_loss_L2')
        """
        # 매도 수량 계산
        partial_volume = self.position * (sell_ratio / 100.0)

        logger.info(f"💰 부분 매도 실행: {partial_volume:.8f}개 ({sell_ratio}%) @ {price:,.0f}원 (이유: {reason})")

        if self.dry_run:
            # Dry Run 모드
            funds = partial_volume * price
            result = {
                'success': True,
                'order_id': f'dry_run_partial_sell_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'symbol': self.symbol,
                'side': 'sell',
                'volume': partial_volume,
                'executed_funds': funds,
                'executed_price': price,
                'timestamp': datetime.now(),
                'partial': True,
                'sell_ratio': sell_ratio
            }

            # 손익 계산 (부분 매도분)
            partial_invested = self.avg_entry_price * partial_volume
            profit = funds - partial_invested
            profit_pct = (profit / partial_invested) * 100

            # 통계 업데이트 (부분 매도도 카운트)
            if profit > 0:
                self.total_profit += profit
            else:
                self.total_loss += abs(profit)

            # 포지션 업데이트 (평균 단가는 유지)
            self.current_capital += funds
            self.position -= partial_volume
            self.total_invested -= partial_invested

            # 전량 청산 시 상태 초기화
            if self.position < 0.00000001:  # 부동소수점 오차 고려
                self.position = 0.0
                self.entry_price = None
                self.entry_time = None
                self.avg_entry_price = None
                self.total_invested = 0.0
                self.executed_tp_levels.clear()
                self.executed_sl_levels.clear()
                self.executed_dca_levels.clear()  # 🔧 DCA 레벨 초기화
                self.signal_price = None  # 🔧 신호 가격 초기화
                self.risk_manager.on_position_close()
        else:
            # 실거래
            result = await self.order_manager.execute_sell(self.symbol, partial_volume, dry_run=False)

            if result['success']:
                # 손익 계산 (부분 매도분)
                partial_invested = self.avg_entry_price * partial_volume
                profit = result['executed_funds'] - partial_invested
                profit_pct = (profit / partial_invested) * 100

                # 통계 업데이트
                if profit > 0:
                    self.total_profit += profit
                else:
                    self.total_loss += abs(profit)

                # 포지션 업데이트
                self.current_capital = self.order_manager.api.get_balance('KRW')
                self.position -= partial_volume
                self.total_invested -= partial_invested

                # 전량 청산 시 상태 초기화
                if self.position < 0.00000001:  # 부동소수점 오차 고려
                    self.position = 0.0
                    self.entry_price = None
                    self.entry_time = None
                    self.avg_entry_price = None
                    self.total_invested = 0.0
                    self.executed_tp_levels.clear()
                    self.executed_sl_levels.clear()
                    self.executed_dca_levels.clear()  # 🔧 DCA 레벨 초기화
                    self.signal_price = None  # 🔧 신호 가격 초기화
                    self.risk_manager.on_position_close()

                result['partial'] = True
                result['sell_ratio'] = sell_ratio

        # 텔레그램 알림
        if self.telegram:
            await self.telegram.send_order_result(result)

            # 리스크 이벤트 알림 (부분 매도 정보 포함)
            await self.telegram.send_risk_event(reason, {
                'symbol': self.symbol,
                'price': price,
                'pnl_pct': profit_pct,
                'partial': True,
                'sell_ratio': sell_ratio,
                'remaining_position': self.position
            })

        if result['success']:
            logger.info(f"✅ 부분 매도 완료: {result['executed_funds']:,.0f}원, 손익: {profit:+,.0f}원 ({profit_pct:+.2f}%), 잔여: {self.position:.8f}개")

            # 🔧 거래 콜백 호출 (GUI에 매도 내역 전달)
            if self.trade_callback:
                # 익절/손절 레벨 표시
                reason_text = f'익절 레벨 {level}' if 'take_profit' in reason else f'손절 레벨 {level}'
                if self.position < 0.00000001:
                    reason_text += ' (전량 청산)'
                else:
                    reason_text += f' ({sell_ratio}% 매도)'

                trade_data = {
                    'timestamp': result['timestamp'],
                    'symbol': self.symbol,
                    'trade_type': 'sell',
                    'price': price,
                    'quantity': partial_volume,
                    'amount': result['executed_funds'],
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'reason': reason_text,
                    'order_id': result.get('order_id')
                }
                self.trade_callback(trade_data)

    def get_status(self) -> Dict:
        """현재 상태 조회"""
        # 🔧 총 자산 = 남은 현금 + 보유 BTC 평가금액
        btc_value = 0.0
        if self.position > 0 and self.last_price:
            btc_value = self.position * self.last_price

        total_asset = self.current_capital + btc_value if self.current_capital else 0

        # 수익률 계산 (총 자산 기준)
        return_pct = 0.0
        if self.initial_capital and total_asset:
            return_pct = ((total_asset - self.initial_capital) / self.initial_capital * 100)

        return {
            'is_running': self.is_running,
            'symbol': self.symbol,
            'position': self.position,
            'entry_price': self.entry_price,  # 최초 진입 가격
            'avg_entry_price': self.avg_entry_price,  # 🔧 DCA 평균 단가
            'total_invested': self.total_invested,  # 🔧 총 투자 금액
            'entry_time': self.entry_time,
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,  # KRW 잔액
            'btc_value': btc_value,  # BTC 평가금액
            'total_asset': total_asset,  # 총 자산 (KRW + BTC)
            'last_price': self.last_price,  # 최근 가격
            'return_pct': return_pct,  # 수익률 (총 자산 기준)
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'net_profit': self.total_profit - self.total_loss,
            'latest_candle': self.buffer.get_latest_candle() if self.buffer.is_ready() else None  # 최신 캔들
        }


# 테스트 코드
if __name__ == "__main__":
    """테스트: Dry Run 모드로 트레이딩 엔진 실행"""
    import os
    from dotenv import load_dotenv
    
    print("=== Trading Engine 테스트 (Dry Run) ===\n")
    
    # .env 파일 로드
    load_dotenv()
    
    # 설정
    config = {
        'symbol': 'KRW-BTC',
        'strategy': {
            'period': 20,
            'std_dev': 2.5
        },
        'risk_manager': {
            'stop_loss_pct': 5.0,
            'take_profit_pct': 10.0,
            'max_daily_loss_pct': 10.0
        },
        'order_amount': 10000,
        'dry_run': True,
        'telegram': {
            'token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID')
        }
    }
    
    async def test_trading_engine():
        engine = TradingEngine(config)
        
        print("트레이딩 엔진 시작...")
        print("(Ctrl+C로 중단)\n")
        
        try:
            await engine.start()
        except KeyboardInterrupt:
            print("\n\n중단 요청...")
            await engine.stop()
            
            # 최종 상태
            status = engine.get_status()
            print("\n=== 최종 상태 ===")
            print(f"총 거래: {status['total_trades']}회")
            print(f"승률: {status['win_rate']:.1f}%")
            print(f"최종 자본: {status['current_capital']:,.0f}원")
            print(f"수익률: {status['return_pct']:+.2f}%")
    
    # 실행
    asyncio.run(test_trading_engine())
