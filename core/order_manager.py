"""
Order Manager
주문 관리자

주문 실행, 검증, 재시도 로직:
- 주문 실행 전 검증 (잔고, 최소 주문 금액)
- 주문 완료 대기 (타임아웃)
- 실패 시 자동 재시도 (지수 백오프)
- 주문 상태 추적

Example:
    >>> api = UpbitAPI(access_key, secret_key)
    >>> manager = OrderManager(api)
    >>> result = await manager.execute_buy('KRW-BTC', 10000)
"""

import asyncio
import logging
from typing import Dict, Optional, Callable
from datetime import datetime

from core.upbit_api import UpbitAPI

logger = logging.getLogger(__name__)


class OrderManager:
    """
    주문 관리자
    
    주문 실행, 검증, 완료 대기를 담당합니다.
    """
    
    def __init__(
        self,
        upbit_api: UpbitAPI,
        min_order_amount: float = 5000.0,
        order_timeout: int = 30,
        dry_run: bool = False,
        balance_update_callback: Optional[Callable] = None,  # 🔧 잔고 갱신 콜백
        trade_callback: Optional[Callable] = None  # 🔧 거래 내역 기록 콜백
    ):
        """
        주문 관리자 초기화

        Args:
            upbit_api: Upbit API 클라이언트
            min_order_amount: 최소 주문 금액 (원)
            order_timeout: 주문 완료 대기 시간 (초)
            dry_run: True이면 실제 주문 없이 시뮬레이션 (기본값)
            balance_update_callback: 주문 완료 시 호출할 잔고 갱신 콜백
            trade_callback: 거래 완료 시 호출할 거래 내역 기록 콜백
        """
        self.api = upbit_api
        self.min_order_amount = min_order_amount
        self.order_timeout = order_timeout
        self.dry_run = dry_run
        self.balance_update_callback = balance_update_callback  # 🔧 저장
        self.trade_callback = trade_callback  # 🔧 저장

        # 주문 기록
        self.order_history = []

        mode = "DRY-RUN" if dry_run else "실거래"
        logger.info(f"✅ 주문 관리자 초기화 완료 (최소 주문: {min_order_amount:,.0f}원, 모드: {mode})")
    
    async def execute_buy(
        self,
        symbol: str,
        amount: float,
        dry_run: Optional[bool] = None
    ) -> Dict:
        """
        매수 주문 실행
        
        Args:
            symbol: 마켓 코드 (예: 'KRW-BTC')
            amount: 매수 금액 (KRW)
            dry_run: True이면 실제 주문 없이 시뮬레이션만 (None이면 초기화 시 설정값 사용)
            
        Returns:
            Dict: 주문 결과
                {
                    'success': True/False,
                    'order_id': '주문 UUID',
                    'symbol': 'KRW-BTC',
                    'side': 'buy',
                    'amount': 10000.0,
                    'executed_volume': 0.001,
                    'executed_price': 100000000.0,
                    'timestamp': datetime,
                    'error': 'error message' (if failed)
                }
        """
        # dry_run 파라미터가 명시되지 않으면 초기화 시 설정값 사용
        if dry_run is None:
            dry_run = self.dry_run
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}🛒 매수 주문 요청: {symbol}, {amount:,.0f}원")
        
        # 1. 검증: 최소 주문 금액
        if amount < self.min_order_amount:
            error_msg = f"최소 주문 금액 미달: {amount:,.0f}원 < {self.min_order_amount:,.0f}원"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'symbol': symbol,
                'side': 'buy',
                'amount': amount,
                'timestamp': datetime.now(),
                'error': error_msg
            }
        
        # 2. 검증: KRW 잔고
        # get_balance()는 동기 blocking 함수이므로 별도 스레드에서 실행
        krw_balance = await asyncio.to_thread(self.api.get_balance, 'KRW')
        if krw_balance < amount:
            error_msg = f"잔고 부족: {krw_balance:,.0f}원 < {amount:,.0f}원"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'symbol': symbol,
                'side': 'buy',
                'amount': amount,
                'timestamp': datetime.now(),
                'error': error_msg
            }
        
        # 3. Dry Run 모드
        if dry_run:
            logger.info("✅ [DRY RUN] 매수 주문 시뮬레이션 완료")
            return {
                'success': True,
                'order_id': 'dry_run_order_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                'symbol': symbol,
                'side': 'buy',
                'amount': amount,
                'executed_volume': amount / 100000000.0,  # 가상의 체결량
                'executed_price': 100000000.0,  # 가상의 체결가
                'timestamp': datetime.now(),
                'dry_run': True
            }
        
        # 4. 실제 주문 실행
        try:
            # buy_market_order()는 동기 blocking 함수이므로 별도 스레드에서 실행
            order = await asyncio.to_thread(self.api.buy_market_order, symbol, amount)
            order_id = order['uuid']
            
            # 5. 주문 완료 대기
            final_order = await self.wait_for_order(order_id)
            
            # 6. 결과 반환
            if final_order['state'] == 'done':
                # 체결 정보 계산
                executed_volume = sum(float(trade['volume']) for trade in final_order.get('trades', []))
                executed_funds = sum(float(trade['funds']) for trade in final_order.get('trades', []))
                avg_price = executed_funds / executed_volume if executed_volume > 0 else 0
                
                result = {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': 'buy',
                    'amount': amount,
                    'executed_volume': executed_volume,
                    'executed_price': avg_price,
                    'timestamp': datetime.now()
                }
                
                logger.info(f"✅ 매수 완료: {executed_volume:.8f}개 @ {avg_price:,.0f}원")

                # 주문 기록 저장
                self.order_history.append(result)

                # 🔧 잔고 갱신 콜백 호출 (매수 완료 시)
                if self.balance_update_callback:
                    try:
                        if asyncio.iscoroutinefunction(self.balance_update_callback):
                            await self.balance_update_callback()
                        else:
                            self.balance_update_callback()
                        logger.debug("✅ 잔고 갱신 콜백 호출 완료 (매수)")
                    except Exception as e:
                        logger.error(f"❌ 잔고 갱신 콜백 실패: {e}")

                # 🔧 거래 내역 기록 콜백 호출 (매수 완료 시)
                if self.trade_callback:
                    try:
                        trade_data = {
                            'symbol': symbol,
                            'trade_type': 'buy',
                            'price': avg_price,
                            'quantity': executed_volume,
                            'amount': executed_funds,
                            'timestamp': datetime.now(),
                            'reason': '수동 매수' if not dry_run else 'DRY RUN 매수'
                        }
                        if asyncio.iscoroutinefunction(self.trade_callback):
                            await self.trade_callback(trade_data)
                        else:
                            self.trade_callback(trade_data)
                        logger.debug("✅ 거래 내역 콜백 호출 완료 (매수)")
                    except Exception as e:
                        logger.error(f"❌ 거래 내역 콜백 실패: {e}")

                return result
            else:
                error_msg = f"주문 미체결: state={final_order['state']}"
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': 'buy',
                    'amount': amount,
                    'timestamp': datetime.now(),
                    'error': error_msg
                }
        
        except Exception as e:
            error_msg = f"매수 주문 실패: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'symbol': symbol,
                'side': 'buy',
                'amount': amount,
                'timestamp': datetime.now(),
                'error': error_msg
            }
    
    async def execute_sell(
        self,
        symbol: str,
        volume: float,
        dry_run: Optional[bool] = None
    ) -> Dict:
        """
        매도 주문 실행
        
        Args:
            symbol: 마켓 코드
            volume: 매도 수량 (코인 수량)
            dry_run: True이면 실제 주문 없이 시뮬레이션만 (None이면 초기화 시 설정값 사용)
            
        Returns:
            Dict: 주문 결과
        """
        # dry_run 파라미터가 명시되지 않으면 초기화 시 설정값 사용
        if dry_run is None:
            dry_run = self.dry_run
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}💵 매도 주문 요청: {symbol}, {volume:.8f}개")
        
        # 1. 검증: 보유 수량
        currency = symbol.split('-')[1]  # 'KRW-BTC' -> 'BTC'
        # get_balance()는 동기 blocking 함수이므로 별도 스레드에서 실행
        balance = await asyncio.to_thread(self.api.get_balance, currency)

        if balance < volume:
            error_msg = f"보유 수량 부족: {balance:.8f}개 < {volume:.8f}개"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'symbol': symbol,
                'side': 'sell',
                'volume': volume,
                'timestamp': datetime.now(),
                'error': error_msg
            }
        
        # 2. Dry Run 모드
        if dry_run:
            logger.info("✅ [DRY RUN] 매도 주문 시뮬레이션 완료")
            return {
                'success': True,
                'order_id': 'dry_run_order_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                'symbol': symbol,
                'side': 'sell',
                'volume': volume,
                'executed_funds': volume * 100000000.0,  # 가상의 체결금액
                'executed_price': 100000000.0,  # 가상의 체결가
                'timestamp': datetime.now(),
                'dry_run': True
            }
        
        # 3. 실제 주문 실행
        try:
            # sell_market_order()는 동기 blocking 함수이므로 별도 스레드에서 실행
            order = await asyncio.to_thread(self.api.sell_market_order, symbol, volume)
            order_id = order['uuid']
            
            # 4. 주문 완료 대기
            final_order = await self.wait_for_order(order_id)
            
            # 5. 결과 반환
            if final_order['state'] == 'done':
                # 체결 정보 계산
                executed_funds = sum(float(trade['funds']) for trade in final_order.get('trades', []))
                executed_volume = sum(float(trade['volume']) for trade in final_order.get('trades', []))
                avg_price = executed_funds / executed_volume if executed_volume > 0 else 0
                
                result = {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': 'sell',
                    'volume': volume,
                    'executed_funds': executed_funds,
                    'executed_price': avg_price,
                    'timestamp': datetime.now()
                }
                
                logger.info(f"✅ 매도 완료: {executed_volume:.8f}개 @ {avg_price:,.0f}원, 총 {executed_funds:,.0f}원")

                # 주문 기록 저장
                self.order_history.append(result)

                # 🔧 잔고 갱신 콜백 호출 (매도 완료 시)
                if self.balance_update_callback:
                    try:
                        if asyncio.iscoroutinefunction(self.balance_update_callback):
                            await self.balance_update_callback()
                        else:
                            self.balance_update_callback()
                        logger.debug("✅ 잔고 갱신 콜백 호출 완료 (매도)")
                    except Exception as e:
                        logger.error(f"❌ 잔고 갱신 콜백 실패: {e}")

                # 🔧 거래 내역 기록 콜백 호출 (매도 완료 시)
                if self.trade_callback:
                    try:
                        trade_data = {
                            'symbol': symbol,
                            'trade_type': 'sell',
                            'price': avg_price,
                            'quantity': executed_volume,
                            'amount': executed_funds,
                            'timestamp': datetime.now(),
                            'reason': '수동 매도' if not dry_run else 'DRY RUN 매도'
                        }
                        if asyncio.iscoroutinefunction(self.trade_callback):
                            await self.trade_callback(trade_data)
                        else:
                            self.trade_callback(trade_data)
                        logger.debug("✅ 거래 내역 콜백 호출 완료 (매도)")
                    except Exception as e:
                        logger.error(f"❌ 거래 내역 콜백 실패: {e}")

                return result
            else:
                error_msg = f"주문 미체결: state={final_order['state']}"
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': 'sell',
                    'volume': volume,
                    'timestamp': datetime.now(),
                    'error': error_msg
                }
        
        except Exception as e:
            error_msg = f"매도 주문 실패: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'symbol': symbol,
                'side': 'sell',
                'volume': volume,
                'timestamp': datetime.now(),
                'error': error_msg
            }
    
    async def wait_for_order(self, order_id: str) -> Dict:
        """
        주문 완료 대기
        
        Args:
            order_id: 주문 UUID
            
        Returns:
            Dict: 최종 주문 상태
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 타임아웃 체크
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.order_timeout:
                logger.warning(f"⚠️ 주문 대기 타임아웃: {order_id}")
                break
            
            # 주문 상태 조회
            # get_order()는 동기 blocking 함수이므로 별도 스레드에서 실행
            order = await asyncio.to_thread(self.api.get_order, order_id)

            # 완료 또는 취소 상태면 반환
            if order['state'] in ['done', 'cancel']:
                return order

            # 0.5초 대기 후 재시도
            await asyncio.sleep(0.5)

        # 타임아웃 시 최종 상태 반환
        return await asyncio.to_thread(self.api.get_order, order_id)
    
    def get_order_history(self, limit: Optional[int] = None) -> list:
        """
        주문 기록 조회
        
        Args:
            limit: 조회할 최대 개수
            
        Returns:
            list: 주문 기록
        """
        if limit:
            return self.order_history[-limit:]
        return self.order_history


class OrderRetryHandler:
    """
    주문 재시도 핸들러
    
    실패한 주문을 자동으로 재시도합니다.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0
    ):
        """
        재시도 핸들러 초기화
        
        Args:
            max_retries: 최대 재시도 횟수
            base_delay: 기본 대기 시간 (초)
            max_delay: 최대 대기 시간 (초)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        logger.info(f"✅ 재시도 핸들러 초기화: 최대 {max_retries}회")
    
    async def execute_with_retry(self, order_func, *args, **kwargs) -> Dict:
        """
        재시도 로직을 포함한 주문 실행
        
        Args:
            order_func: 주문 함수 (execute_buy 또는 execute_sell)
            *args, **kwargs: 주문 함수에 전달할 인자
            
        Returns:
            Dict: 주문 결과
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔄 주문 시도 {attempt + 1}/{self.max_retries}")
                
                # 주문 실행
                result = await order_func(*args, **kwargs)
                
                # 성공 시 반환
                if result['success']:
                    if attempt > 0:
                        logger.info(f"✅ 재시도 성공 (시도 횟수: {attempt + 1})")
                    return result
                
                # 실패 시 에러 저장
                last_error = result.get('error', 'Unknown error')
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ 주문 시도 실패: {last_error}")
            
            # 마지막 시도가 아니면 대기 후 재시도
            if attempt < self.max_retries - 1:
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.info(f"⏳ {delay:.1f}초 대기 후 재시도...")
                await asyncio.sleep(delay)
        
        # 모든 시도 실패
        logger.error(f"❌ 모든 재시도 실패: {last_error}")
        return {
            'success': False,
            'error': f"Max retries exceeded: {last_error}",
            'timestamp': datetime.now()
        }


# 테스트 코드
if __name__ == "__main__":
    """테스트: Dry Run 모드로 주문 실행"""
    import os
    from dotenv import load_dotenv
    
    print("=== Order Manager 테스트 (Dry Run) ===\n")
    
    # .env 파일에서 API 키 로드
    load_dotenv()
    access_key = os.getenv('UPBIT_ACCESS_KEY')
    secret_key = os.getenv('UPBIT_SECRET_KEY')
    
    if not access_key or not secret_key:
        print("❌ API 키가 설정되지 않았습니다.")
        print("   .env 파일에 UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY를 설정하세요.")
        exit(1)
    
    async def test_order_manager():
        # API 클라이언트 초기화
        api = UpbitAPI(access_key, secret_key)
        
        # 주문 관리자 초기화
        manager = OrderManager(api, min_order_amount=5000)
        retry_handler = OrderRetryHandler(max_retries=3)
        
        # 1. Dry Run 매수 테스트
        print("1. Dry Run 매수 테스트")
        result = await manager.execute_buy('KRW-BTC', 10000, dry_run=True)
        print(f"   성공: {result['success']}")
        print(f"   주문 ID: {result['order_id']}")
        print(f"   체결량: {result['executed_volume']:.8f}개")
        print()
        
        # 2. Dry Run 매도 테스트
        print("2. Dry Run 매도 테스트")
        result = await manager.execute_sell('KRW-BTC', 0.001, dry_run=True)
        print(f"   성공: {result['success']}")
        print(f"   주문 ID: {result['order_id']}")
        print(f"   체결금액: {result['executed_funds']:,.0f}원")
        print()
        
        # 3. 검증 실패 테스트 (최소 주문 금액 미달)
        print("3. 검증 실패 테스트 (최소 주문 금액)")
        result = await manager.execute_buy('KRW-BTC', 1000, dry_run=True)
        print(f"   성공: {result['success']}")
        print(f"   에러: {result.get('error', 'N/A')}")
        print()
        
        # 4. 재시도 핸들러 테스트
        print("4. 재시도 핸들러 테스트 (Dry Run)")
        result = await retry_handler.execute_with_retry(
            manager.execute_buy,
            'KRW-BTC',
            10000,
            dry_run=True
        )
        print(f"   최종 성공: {result['success']}")
        print()
        
        print("✅ 모든 테스트 완료")
        print("\n⚠️ 주의: 실제 주문은 Phase 3.5 페이퍼 트레이딩에서 테스트합니다.")
    
    # 비동기 테스트 실행
    asyncio.run(test_order_manager())
