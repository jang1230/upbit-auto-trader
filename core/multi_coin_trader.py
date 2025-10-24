"""
Multi-Coin Trader - 다중 코인 동시 트레이딩 관리자

여러 코인을 동시에 독립적으로 트레이딩하는 시스템
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from core.trading_engine import TradingEngine
from gui.dca_config import AdvancedDcaConfig  # 🔧 gui 폴더에 위치

logger = logging.getLogger(__name__)


class MultiCoinTrader:
    """
    다중 코인 트레이딩 관리자

    각 코인별로 독립적인 TradingEngine 인스턴스를 생성하고 병렬로 실행
    포트폴리오 전체의 수익률과 상태를 통합 관리
    """

    def __init__(
        self,
        symbols: List[str],
        total_capital: float,
        strategy_config: Dict,
        risk_config: Dict,
        dca_config: AdvancedDcaConfig,
        order_amount: float = 100000,
        dry_run: bool = True,
        access_key: str = "",
        secret_key: str = "",
        telegram_config: Optional[Dict] = None,
        trade_callback=None
    ):
        """
        초기화

        Args:
            symbols: 거래할 코인 심볼 리스트 (예: ['KRW-BTC', 'KRW-ETH'])
            total_capital: 총 투자 자본
            strategy_config: 전략 설정
            risk_config: 리스크 관리 설정
            dca_config: DCA 설정
            order_amount: 코인당 주문 금액
            dry_run: 페이퍼 트레이딩 모드
            access_key: 업비트 API 키
            secret_key: 업비트 시크릿 키
            telegram_config: 텔레그램 설정
            trade_callback: 거래 발생 시 호출될 콜백 함수
        """
        self.symbols = symbols
        self.total_capital = total_capital
        self.capital_per_coin = total_capital / len(symbols)
        self.strategy_config = strategy_config
        self.risk_config = risk_config
        self.dca_config = dca_config
        self.order_amount = order_amount
        self.dry_run = dry_run
        self.access_key = access_key
        self.secret_key = secret_key
        self.telegram_config = telegram_config
        self.trade_callback = trade_callback  # 🔧 거래 콜백

        # 각 코인별 TradingEngine 인스턴스
        self.engines: Dict[str, TradingEngine] = {}

        # 실행 상태
        self.is_running = False
        self.start_time: Optional[datetime] = None

        logger.info(f"🎯 MultiCoinTrader 초기화")
        logger.info(f"  코인 수: {len(symbols)}개")
        logger.info(f"  총 자본: {total_capital:,.0f}원")
        logger.info(f"  코인당 자본: {self.capital_per_coin:,.0f}원")
        logger.info(f"  코인 목록: {', '.join(symbols)}")

    async def start(self):
        """모든 코인 트레이딩 시작"""
        if self.is_running:
            logger.warning("⚠️ 이미 실행 중입니다")
            return

        logger.info("=" * 60)
        logger.info("🚀 다중 코인 트레이딩 시작")
        logger.info("=" * 60)

        self.is_running = True
        self.start_time = datetime.now()

        # 각 코인별 TradingEngine 생성
        for symbol in self.symbols:
            try:
                logger.info(f"")
                logger.info(f"📊 {symbol} 엔진 생성 중...")

                # TradingEngine은 config Dict를 받음
                engine_config = {
                    'symbol': symbol,
                    'initial_capital': self.capital_per_coin,
                    'strategy': self.strategy_config,
                    'risk_manager': self.risk_config,
                    'order_amount': self.order_amount,
                    'dry_run': self.dry_run,
                    'upbit': {
                        'access_key': self.access_key,
                        'secret_key': self.secret_key
                    },
                    'telegram': self.telegram_config,
                    'dca_config': self.dca_config.to_dict()  # Dict로 변환
                }

                # 🔧 콜백 전달
                engine = TradingEngine(engine_config, trade_callback=self.trade_callback)
                self.engines[symbol] = engine
                logger.info(f"✅ {symbol} 엔진 생성 완료")
            except Exception as e:
                logger.error(f"❌ {symbol} 엔진 생성 실패: {e}")
                import traceback
                traceback.print_exc()
                raise  # 재발생시켜서 프로그램 중단

        logger.info("")
        logger.info("=" * 60)
        logger.info("🔄 모든 엔진 병렬 실행 시작 (연결 지연 포함)")
        logger.info("=" * 60)

        # 🔧 WebSocket 연결 지연 추가 (HTTP 429 방지)
        # 각 엔진을 순차적으로 시작하되, WebSocket 연결 간 1초 지연
        tasks = []
        for idx, (symbol, engine) in enumerate(self.engines.items()):
            if idx > 0:
                logger.info(f"⏳ WebSocket 연결 지연 1초... (Rate Limit 방지)")
                await asyncio.sleep(1.0)  # 1초 대기

            logger.info(f"🚀 {symbol} 엔진 시작 중...")
            task = asyncio.create_task(engine.start())
            tasks.append(task)

        # 모든 엔진을 병렬로 실행
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"❌ 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            logger.info("⏹️ 다중 코인 트레이딩 종료")

    async def stop(self):
        """모든 코인 트레이딩 중지"""
        if not self.is_running:
            logger.warning("⚠️ 실행 중이 아닙니다")
            return

        logger.info("=" * 60)
        logger.info("🛑 다중 코인 트레이딩 중지 시작")
        logger.info("=" * 60)

        # 모든 엔진을 병렬로 중지
        stop_tasks = []
        for symbol, engine in self.engines.items():
            logger.info(f"⏹️ {symbol} 중지 중...")
            stop_tasks.append(engine.stop())

        await asyncio.gather(*stop_tasks)

        self.is_running = False
        logger.info("✅ 모든 엔진 중지 완료")

    async def update_dca_config(self, dca_config):
        """
        실행 중 DCA 설정 업데이트
        
        Args:
            dca_config: 새로운 AdvancedDcaConfig 객체
        """
        if not self.is_running:
            logger.warning("⚠️ 트레이더가 실행 중이 아닙니다")
            return
        
        logger.info("🔄 DCA 설정 실시간 업데이트 시작")
        
        # 각 코인별 엔진에 DCA 설정 업데이트
        for symbol, engine in self.engines.items():
            logger.info(f"  📊 {symbol}: DCA 설정 업데이트 중...")
            engine.update_dca_config(dca_config)
        
        # MultiCoinTrader 자체 설정도 업데이트
        self.dca_config = dca_config
        
        logger.info("✅ 모든 엔진의 DCA 설정 업데이트 완료")

    async def update_coins(self, new_symbols: List[str]):
        """
        실행 중 코인 선택 변경 (추가/제거)
        
        Args:
            new_symbols: 새로운 코인 심볼 리스트
        """
        if not self.is_running:
            logger.warning("⚠️ 트레이더가 실행 중이 아닙니다")
            return
        
        logger.info("🔄 코인 선택 실시간 업데이트 시작")
        
        current_symbols = set(self.engines.keys())
        new_symbols_set = set(new_symbols)
        
        # 제거할 코인
        to_remove = current_symbols - new_symbols_set
        # 추가할 코인
        to_add = new_symbols_set - current_symbols
        
        # 1️⃣ 제거할 코인의 엔진 중지
        for symbol in to_remove:
            logger.info(f"❌ {symbol}: 제거 중...")
            engine = self.engines[symbol]
            await engine.stop()
            del self.engines[symbol]
            logger.info(f"✅ {symbol}: 제거 완료")
        
        # 2️⃣ 추가할 코인의 엔진 생성 및 시작
        for symbol in to_add:
            logger.info(f"➕ {symbol}: 추가 중...")
            
            # 엔진 설정 생성
            engine_config = {
                'symbol': symbol,
                'strategy': self.strategy_config,
                'risk_manager': self.risk_config,
                'order_amount': self.order_amount,
                'dry_run': self.dry_run,
                'upbit': {
                    'access_key': self.access_key,
                    'secret_key': self.secret_key
                },
                'telegram': self.telegram_config,
                'dca_config': self.dca_config.to_dict()  # DCA 설정 전달
            }
            
            # TradingEngine 생성
            from core.trading_engine import TradingEngine
            engine = TradingEngine(engine_config, trade_callback=self.trade_callback)
            
            # 엔진 저장
            self.engines[symbol] = engine
            
            # 엔진 시작 (백그라운드 태스크로)
            asyncio.create_task(engine.start())
            
            logger.info(f"✅ {symbol}: 추가 완료")
        
        # 3️⃣ symbols 리스트 업데이트
        self.symbols = new_symbols
        
        logger.info(f"✅ 코인 선택 업데이트 완료: {len(self.engines)}개 코인 실행 중")
        logger.info(f"   현재 코인: {', '.join([s.replace('KRW-', '') for s in self.symbols])}")

    def get_portfolio_status(self) -> Dict:
        """
        전체 포트폴리오 상태 조회

        Returns:
            Dict: 포트폴리오 통합 상태
        """
        if not self.engines:
            return {
                'is_running': self.is_running,
                'total_initial_capital': self.total_capital,
                'total_current_asset': 0,
                'total_return_pct': 0.0,
                'coins': {},
                'summary': {
                    'running_count': 0,
                    'position_count': 0,
                    'total_profit': 0
                }
            }

        # 각 코인 상태 수집
        coins_status = {}
        total_asset = 0
        position_count = 0

        for symbol, engine in self.engines.items():
            status = engine.get_status()
            coins_status[symbol] = status

            # 총 자산 합산
            total_asset += status.get('total_asset', 0)

            # 포지션 보유 중인 코인 수
            if status.get('position', 0) > 0:
                position_count += 1

        # 전체 수익률 계산
        total_return_pct = 0.0
        if self.total_capital > 0 and total_asset > 0:
            total_return_pct = ((total_asset - self.total_capital) / self.total_capital * 100)

        # 총 손익금
        total_profit = total_asset - self.total_capital if total_asset > 0 else 0

        # 실행 시간
        runtime = None
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            runtime = str(elapsed).split('.')[0]  # 초 단위까지만

        return {
            'is_running': self.is_running,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'runtime': runtime,
            'total_initial_capital': self.total_capital,
            'total_current_asset': total_asset,
            'total_return_pct': total_return_pct,
            'total_profit': total_profit,
            'coins': coins_status,
            'summary': {
                'coin_count': len(self.symbols),
                'running_count': len(self.engines),
                'position_count': position_count,
            }
        }

    def get_coin_status(self, symbol: str) -> Optional[Dict]:
        """
        특정 코인 상태 조회

        Args:
            symbol: 코인 심볼 (예: 'KRW-BTC')

        Returns:
            Dict: 코인 상태 또는 None
        """
        engine = self.engines.get(symbol)
        if not engine:
            return None

        return engine.get_status()
