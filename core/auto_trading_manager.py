"""
AutoTradingManager - 완전 자동 트레이딩 매니저

ScalpingStrategy 시그널 기반으로 자동 진입(매수)하고
SemiAutoManager로 자동 관리하는 완전 자동 트레이딩 시스템

주요 기능:
1. 시가총액 상위 N개 코인 모니터링
2. ScalpingStrategy 진입 시그널 감지
3. 리스크 관리 체크 (4가지 선택적 옵션)
4. 자동 매수 실행
5. SemiAutoManager 자동 연계
"""

import logging
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime, date
import asyncio
import pandas as pd

from core.upbit_api import UpbitAPI
from core.order_manager import OrderManager
from core.semi_auto_manager import SemiAutoManager
from core.strategies.scalping_strategy import ScalpingStrategy
from gui.auto_trading_config import AutoTradingConfig

logger = logging.getLogger(__name__)


# 글로벌 시가총액 상위 10개 (2025년 10월 기준, BNB→LINK 대체)
MARKETCAP_TOP_10 = [
    'KRW-BTC',   # 1위: 비트코인
    'KRW-ETH',   # 2위: 이더리움
    'KRW-USDT',  # 3위: 테더
    'KRW-SOL',   # 4위: 솔라나
    'KRW-LINK',  # 5위: 체인링크 (BNB 대체)
    'KRW-USDC',  # 6위: 유에스디코인
    'KRW-DOGE',  # 7위: 도지코인
    'KRW-ADA',   # 8위: 에이다
    'KRW-TRX',   # 9위: 트론
    'KRW-XRP',   # 10위: 엑스알피
]


class AutoTradingManager:
    """
    완전 자동 트레이딩 매니저
    
    역할:
    - 시가총액 상위 N개 코인 모니터링
    - ScalpingStrategy로 진입 시그널 감지
    - 리스크 관리 및 자동 매수 실행
    - SemiAutoManager와 자동 연계
    """
    
    def __init__(
        self,
        upbit_api: UpbitAPI,
        order_manager: OrderManager,
        semi_auto_manager: SemiAutoManager,
        config: AutoTradingConfig,
        notification_callback: Optional[Callable] = None,
        dry_run: bool = True
    ):
        """
        Args:
            upbit_api: Upbit API 클라이언트
            order_manager: 주문 관리자
            semi_auto_manager: 반자동 매니저 (DCA/익절/손절)
            config: 자동매수 설정
            notification_callback: 알림 콜백 함수
            dry_run: 페이퍼 트레이딩 모드 (True: 테스트, False: 실거래)
        """
        self.api = upbit_api
        self.order_manager = order_manager
        self.semi_auto = semi_auto_manager
        self.config = config
        self.notification_callback = notification_callback
        self.dry_run = dry_run  # 🔧 dry_run 모드 저장
        
        # ScalpingStrategy 인스턴스들 (코인별)
        self.strategies: Dict[str, ScalpingStrategy] = {}
        
        # 모니터링 대상 코인 목록
        self.monitoring_symbols: List[str] = []
        
        # 일일 통계 (자정에 초기화)
        self.daily_trades = 0  # 오늘 거래 횟수
        self.daily_start_balance = 0.0  # 오늘 시작 잔고
        self.last_reset_date = date.today()
        
        # 실행 상태
        self.is_running = False
        self._task = None
        
        logger.info(f"AutoTradingManager 초기화 완료 (스캔 주기: {config.scan_interval}초)")
    
    async def start(self):
        """자동 매매 시작"""
        if self.is_running:
            logger.warning("AutoTradingManager가 이미 실행 중입니다")
            return
        
        # 설정 유효성 검증
        is_valid, error_msg = self.config.validate()
        if not is_valid:
            logger.error(f"❌ 설정 오류: {error_msg}")
            return
        
        self.is_running = True
        logger.info("🚀 AutoTradingManager 시작")
        
        # 일일 통계 초기화
        self._reset_daily_stats_if_needed()
        await self._initialize_daily_balance()
        
        # 모니터링 대상 코인 설정
        await self._setup_monitoring_symbols()
        
        # ScalpingStrategy 인스턴스 생성
        await self._setup_strategies()
        
        # 주기적 스캔 태스크 시작
        self._task = asyncio.create_task(self._run_loop())
        
        logger.info("✅ 자동 매매 시작 완료")
    
    async def stop(self):
        """자동 매매 중지"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 AutoTradingManager 종료")
    
    async def _run_loop(self):
        """메인 실행 루프"""
        try:
            logger.info(f"🔄 스캔 시작 ({self.config.scan_interval}초 간격)")
            
            while self.is_running:
                # 일일 통계 초기화 체크
                self._reset_daily_stats_if_needed()
                
                # 스캔 및 트레이딩
                await self._scan_and_trade()
                
                # 대기
                await asyncio.sleep(self.config.scan_interval)
                
        except asyncio.CancelledError:
            logger.info("AutoTradingManager 루프 종료")
        except Exception as e:
            logger.error(f"AutoTradingManager 루프 에러: {e}", exc_info=True)
    
    async def _setup_monitoring_symbols(self):
        """모니터링 대상 코인 설정"""
        if self.config.monitoring_mode == "top_marketcap":
            # 시가총액 상위 N개 조회
            symbols = await self._get_top_marketcap_symbols(self.config.top_n)
            self.monitoring_symbols = symbols
            
            logger.info(f"📊 시가총액 상위 {self.config.top_n}개 조회 완료")
            for i, symbol in enumerate(symbols, 1):
                logger.info(f"   {i}. {symbol}")
        
        elif self.config.monitoring_mode == "custom_list":
            # 사용자 지정 리스트
            self.monitoring_symbols = self.config.custom_symbols
            logger.info(f"📊 커스텀 리스트: {len(self.monitoring_symbols)}개")
    
    async def _setup_strategies(self):
        """코인별 ScalpingStrategy 인스턴스 생성"""
        logger.info("🔧 ScalpingStrategy 인스턴스 생성 중...")
        
        for symbol in self.monitoring_symbols:
            try:
                # ScalpingStrategy 생성
                strategy = ScalpingStrategy(
                    upbit_api=self.api,
                    symbol=symbol,
                    timeframe='1h',
                    rsi_period=14,
                    rsi_oversold=30,
                    rsi_overbought=70
                )
                
                self.strategies[symbol] = strategy
                
            except Exception as e:
                logger.error(f"Strategy 생성 실패 ({symbol}): {e}")
        
        logger.info(f"✅ {len(self.strategies)}개 Strategy 생성 완료")
    
    async def _get_top_marketcap_symbols(self, n: int) -> List[str]:
        """
        시가총액 상위 N개 코인 조회 (고정 리스트)
        
        글로벌 시가총액 기준 상위 10개 코인 반환
        - BNB는 업비트 미상장으로 LINK(12위)로 대체
        - 안정적이고 검증된 코인 위주
        
        Args:
            n: 상위 N개 (최대 10개)
            
        Returns:
            List[str]: 시가총액 상위 심볼 리스트
        """
        # 글로벌 시가총액 상위 10개 고정 리스트 사용
        return MARKETCAP_TOP_10[:n]
    
    async def _scan_and_trade(self):
        """스캔 및 트레이딩 실행"""
        try:
            logger.info("📊 스캔 중...")
            
            for symbol in self.monitoring_symbols:
                try:
                    # 이미 관리 중인 포지션이면 스킵
                    if symbol in self.semi_auto.managed_positions:
                        continue
                    
                    # 진입 시그널 체크
                    has_signal = await self._check_entry_signal(symbol)
                    
                    if has_signal:
                        logger.info(f"🎯 진입 시그널 발견: {symbol}")
                        
                        # 리스크 관리 체크
                        can_trade, reason = self._check_risk_limits()
                        
                        if can_trade:
                            # 자동 매수 실행
                            await self._execute_auto_buy(symbol)
                        else:
                            logger.warning(f"⚠️ 리스크 제한: {reason}")
                            
                            # 알림
                            if self.notification_callback:
                                await self.notification_callback(
                                    f"⚠️ 자동매수 제한\n"
                                    f"심볼: {symbol}\n"
                                    f"사유: {reason}"
                                )
                
                except Exception as e:
                    logger.error(f"{symbol} 처리 중 에러: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"스캔 중 에러: {e}", exc_info=True)
    
    async def _check_entry_signal(self, symbol: str) -> bool:
        """
        진입 시그널 체크
        
        Args:
            symbol: 심볼
            
        Returns:
            bool: 진입 시그널 여부
        """
        try:
            strategy = self.strategies.get(symbol)
            if not strategy:
                return False
            
            # Candles 데이터 조회 (최근 200개)
            candles = await self._fetch_candles(symbol, count=200)
            
            if candles is None or len(candles) < 50:
                logger.warning(f"Candles 데이터 부족: {symbol} (len={len(candles) if candles is not None else 0})")
                return False
            
            # ScalpingStrategy의 should_buy() 호출
            signal = strategy.should_buy(candles)
            
            return signal
            
        except Exception as e:
            logger.error(f"시그널 체크 실패 ({symbol}): {e}")
            return False
    
    async def _fetch_candles(self, symbol: str, count: int = 200) -> pd.DataFrame:
        """
        Candles 데이터 조회
        
        Args:
            symbol: 심볼
            count: 조회할 캔들 개수
            
        Returns:
            pd.DataFrame: Candles 데이터
        """
        try:
            import requests
            
            url = "https://api.upbit.com/v1/candles/minutes/15"  # 15분봉 (단타 전략)
            params = {
                'market': symbol,
                'count': count
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # DataFrame 변환
            df = pd.DataFrame(data)
            
            # 필요한 컬럼만 선택 (원본 컬럼명으로)
            df = df[[
                'candle_date_time_kst',
                'opening_price',
                'high_price',
                'low_price',
                'trade_price',
                'candle_acc_trade_volume'
            ]]
            
            # 컬럼명 변경 (중복 방지)
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            
            # 시간순 정렬 (오래된 것부터)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Candles 조회 실패 ({symbol}): {e}")
            return None
    
    def _check_risk_limits(self) -> Tuple[bool, str]:
        """
        리스크 관리 체크 (4가지 선택적 옵션)
        
        Returns:
            Tuple[bool, str]: (거래 가능 여부, 사유)
        """
        # 1. 최대 포지션 수 체크
        if self.config.max_positions_enabled:
            current_positions = len(self.semi_auto.managed_positions)
            if current_positions >= self.config.max_positions_limit:
                return False, f"최대 포지션 수 초과 ({current_positions}/{self.config.max_positions_limit})"
        
        # 2. 일일 거래 횟수 체크
        if self.config.daily_trades_enabled:
            if self.daily_trades >= self.config.daily_trades_limit:
                return False, f"일일 거래 횟수 초과 ({self.daily_trades}/{self.config.daily_trades_limit})"
        
        # 3. 최소 잔고 체크
        if self.config.min_krw_balance_enabled:
            krw_balance = self._get_krw_balance()
            required = self.config.min_krw_balance_amount + self.config.buy_amount
            
            if krw_balance < required:
                return False, f"잔고 부족 ({krw_balance:,.0f}원 < {required:,.0f}원)"
        
        # 4. 일일 손실 한도 체크
        if self.config.stop_on_loss_enabled:
            daily_pnl_pct = self._calculate_daily_pnl_pct()
            
            if daily_pnl_pct <= -self.config.stop_on_loss_daily_pct:
                return False, f"일일 손실 한도 초과 ({daily_pnl_pct:.1f}% <= -{self.config.stop_on_loss_daily_pct}%)"
        
        return True, "OK"
    
    async def _execute_auto_buy(self, symbol: str):
        """
        자동 매수 실행
        
        Args:
            symbol: 심볼
        """
        try:
            buy_amount = self.config.buy_amount
            
            logger.info(
                f"💰 자동 매수 실행: {symbol}\n"
                f"   매수 금액: {buy_amount:,.0f}원"
            )
            
            # 주문 실행 (dry_run 모드)
            order_result = await self.order_manager.execute_buy(
                symbol=symbol,
                amount=buy_amount,
                dry_run=self.dry_run  # 🔧 설정된 dry_run 모드 사용
            )
            
            if order_result and order_result.get('success'):
                # 통계 업데이트
                self.daily_trades += 1
                
                # 알림
                if self.notification_callback:
                    await self.notification_callback(
                        f"💰 자동 매수 완료!\n"
                        f"심볼: {symbol}\n"
                        f"금액: {buy_amount:,.0f}원\n"
                        f"오늘 거래: {self.daily_trades}회"
                    )
                
                logger.info(f"✅ 자동 매수 완료: {symbol}")
                logger.info(f"   → SemiAutoManager가 자동으로 관리 시작")
                
            else:
                logger.error(f"❌ 자동 매수 실패: {symbol}")
                
        except Exception as e:
            logger.error(f"자동 매수 실패 ({symbol}): {e}", exc_info=True)
    
    def _get_krw_balance(self) -> float:
        """
        KRW 잔고 조회
        
        Returns:
            float: KRW 잔고
        """
        try:
            accounts = self.api.get_accounts()
            
            for account in accounts:
                if account.get('currency') == 'KRW':
                    return float(account.get('balance', 0))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return 0.0
    
    def _calculate_daily_pnl_pct(self) -> float:
        """
        일일 손익률 계산
        
        Returns:
            float: 손익률 (%)
        """
        try:
            if self.daily_start_balance == 0:
                return 0.0
            
            # 현재 총 자산 평가
            current_balance = self._get_krw_balance()
            
            # 보유 포지션 평가액 합산
            for managed in self.semi_auto.managed_positions.values():
                position_value = managed.total_balance * managed.avg_entry_price
                current_balance += position_value
            
            # 손익률 계산
            pnl_pct = ((current_balance - self.daily_start_balance) / self.daily_start_balance) * 100
            
            return pnl_pct
            
        except Exception as e:
            logger.error(f"손익률 계산 실패: {e}")
            return 0.0
    
    async def _initialize_daily_balance(self):
        """일일 시작 잔고 초기화"""
        try:
            # 현재 총 자산 평가
            krw_balance = self._get_krw_balance()
            
            # 보유 포지션 평가액 합산
            total_value = krw_balance
            for managed in self.semi_auto.managed_positions.values():
                position_value = managed.total_balance * managed.avg_entry_price
                total_value += position_value
            
            self.daily_start_balance = total_value
            
            logger.info(f"📊 일일 시작 잔고: {self.daily_start_balance:,.0f}원")
            
        except Exception as e:
            logger.error(f"시작 잔고 초기화 실패: {e}")
            self.daily_start_balance = 0.0
    
    def _reset_daily_stats_if_needed(self):
        """일일 통계 초기화 (자정 기준)"""
        today = date.today()
        
        if today != self.last_reset_date:
            logger.info("🔄 일일 통계 초기화 (자정)")
            
            self.daily_trades = 0
            self.daily_start_balance = 0.0
            self.last_reset_date = today
            
            # 비동기 초기화는 다음 루프에서 수행됨
    
    def get_status(self) -> Dict:
        """
        현재 상태 조회
        
        Returns:
            Dict: 상태 정보
        """
        daily_pnl_pct = self._calculate_daily_pnl_pct()
        
        return {
            'is_running': self.is_running,
            'monitoring_count': len(self.monitoring_symbols),
            'monitoring_symbols': self.monitoring_symbols,
            'daily_trades': self.daily_trades,
            'daily_trades_limit': self.config.daily_trades_limit if self.config.daily_trades_enabled else None,
            'daily_pnl_pct': daily_pnl_pct,
            'daily_start_balance': self.daily_start_balance,
            'managed_positions': len(self.semi_auto.managed_positions),
            'max_positions': self.config.max_positions_limit if self.config.max_positions_enabled else None,
            'krw_balance': self._get_krw_balance(),
            'config': {
                'buy_amount': self.config.buy_amount,
                'scan_interval': self.config.scan_interval,
                'monitoring_mode': self.config.monitoring_mode
            }
        }
