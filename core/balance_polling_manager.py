"""
Balance Polling Manager
계좌 잔고 Polling 관리자

MyAsset WebSocket 상태에 따라 자동으로 REST API polling 시작/중지:
- WebSocket 미수신 → Polling ON (1초 간격)
- WebSocket 정상 → Polling OFF
- WebSocket 끊김 → Polling ON (Fallback)

Example:
    >>> polling_mgr = BalancePollingManager(upbit_api, position_manager)
    >>> polling_mgr.start_polling()
    >>> # WebSocket 정상 수신 시
    >>> polling_mgr.stop_polling()
"""

import time
import logging
import threading
from typing import Set, Optional

logger = logging.getLogger(__name__)


class BalancePollingManager:
    """
    계좌 잔고 Polling 관리자

    MyAsset WebSocket 상태에 따라 자동으로 polling 시작/중지
    - WebSocket 미수신 → Polling ON (1초 간격)
    - WebSocket 정상 → Polling OFF
    - WebSocket 끊김 → Polling ON (Fallback)

    Features:
    - 1초 간격으로 계좌 잔고 조회 (REST API)
    - 새로운 보유 코인 자동 감지
    - group_null 포지션 자동 생성
    - 중복 방지 (known_symbols)
    - Thread-safe 구현
    """

    def __init__(
        self,
        upbit_api,  # UpbitAPI 인스턴스
        position_manager,  # PositionManager 인스턴스
        config: dict = None,  # Config 딕셔너리 (Bug #4 수정: 그룹 매핑용)
        interval: float = 1.0  # Polling 간격 (초)
    ):
        """
        BalancePollingManager 초기화

        Args:
            upbit_api: UpbitAPI 인스턴스 (계좌 조회용)
            position_manager: PositionManager 인스턴스 (포지션 생성용)
            config: Config 딕셔너리 (그룹 매핑용, Bug #4 수정)
            interval: Polling 간격 (초, 기본 1.0초)
        """
        self.upbit_api = upbit_api
        self.position_manager = position_manager
        self.config = config or {}  # Config 저장 (Bug #4 수정)
        self.interval = interval

        # Polling 상태
        self.is_running = False  # 전체 매니저 실행 상태
        self.is_polling_active = False  # Polling 활성화 상태

        # Thread
        self.polling_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 기존 보유 코인 추적 (중복 방지)
        self.known_symbols: Set[str] = set()  # {"KRW-BTC", "KRW-ETH", ...}

        logger.info("✅ BalancePollingManager 초기화 완료")

    def start_polling(self):
        """
        Polling 시작 (별도 스레드)

        이미 polling이 활성화되어 있으면 무시
        """
        if self.is_polling_active:
            logger.debug("💾 Polling이 이미 활성화되어 있음, 무시")
            return

        logger.info("🔴 REST API Polling 시작 (간격: {}초)".format(self.interval))

        self.is_polling_active = True
        self.stop_event.clear()

        # Polling 스레드 생성 및 시작
        self.polling_thread = threading.Thread(
            target=self._polling_loop,
            daemon=True,
            name="BalancePollingThread"
        )
        self.polling_thread.start()

    def stop_polling(self):
        """
        Polling 중지

        스레드를 안전하게 종료하고 자원 정리
        """
        if not self.is_polling_active:
            logger.debug("💾 Polling이 이미 비활성화되어 있음, 무시")
            return

        logger.info("🛑 REST API Polling 중지")

        self.is_polling_active = False
        self.stop_event.set()

        # 스레드 종료 대기 (최대 2초)
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=2.0)
            if self.polling_thread.is_alive():
                logger.warning("⚠️ Polling 스레드가 2초 내 종료되지 않음")

    def _polling_loop(self):
        """
        1초마다 계좌 잔고 조회

        새로운 보유 코인 발견 시:
          1. avg_buy_price, balance, locked 확인
          2. 필터링: avg_buy_price > 0 AND (balance + locked) > 0
          3. group_null 포지션 생성
          4. known_symbols에 추가
        """
        logger.info("📊 Polling 루프 시작")

        while not self.stop_event.is_set():
            try:
                # 1. 계좌 잔고 조회
                # NOTE: get_accounts()는 1초 TTL 캐시를 사용하므로
                #       1초 내 여러 번 호출되어도 실제 API는 1회만 호출됨
                accounts = self.upbit_api.get_accounts()

                # 2. 각 자산 검사
                logger.debug(f"📊 Polling 수신: {len(accounts)}개 자산")
                for account in accounts:
                    currency = account['currency']

                    # KRW는 제외 (코인이 아님)
                    if currency == 'KRW':
                        continue

                    # 필터링: 실제 보유 중인 코인만
                    balance = float(account['balance'])
                    locked = float(account['locked'])
                    avg_buy_price = float(account['avg_buy_price'])
                    total = balance + locked

                    # 디버깅: Polling 데이터 (DEBUG 레벨)
                    logger.debug(f"   🪙 {currency}: balance={balance:.8f}, avg_price={avg_buy_price:,.0f}원 | {account}")

                    # 조건: 평균가 > 0 AND 잔고 > 0
                    # (AQUQ 같은 평가금 0원 코인 제외)
                    if avg_buy_price <= 0 or total <= 0:
                        continue

                    symbol = f"KRW-{currency}"

                    # 이미 알고 있는 코인이면 스킵
                    if symbol in self.known_symbols:
                        logger.debug(f"   ⏭️  {currency}: 이미 known_symbols에 있음, 스킵")
                        continue

                    # 3. 새 코인 발견!
                    logger.info(f"   🆕 신규 보유 코인 감지 (REST API): {symbol}")
                    logger.info(f"      - 평균가: {avg_buy_price:,.0f}원")
                    logger.info(f"      - 수량: {total:.8f}")

                    # 4. 포지션 확인 (중복 방지)
                    position = self.position_manager.get_position_by_symbol(symbol)

                    if not position:
                        # 5. 그룹 찾기 (Bug #4 수정: 동적 그룹 매핑)
                        group_id = self.position_manager._find_group_for_coin(symbol, self.config)

                        if not group_id:
                            group_id = "group_null"
                            logger.info(f"   📝 {symbol} 그룹 없음 → group_null로 설정")
                        else:
                            logger.info(f"   📝 {symbol} 외부 매수 감지 → {group_id}로 포지션 생성")

                        # 6. 포지션 생성
                        try:
                            self.position_manager.create_position(
                                group_id=group_id,  # 동적으로 결정된 그룹 (Bug #4 수정)
                                symbol=symbol,
                                buy_price=avg_buy_price,
                                quantity=total,
                                force_create_for_sync=True
                            )
                            logger.info(f"✅ {group_id} 포지션 생성: {symbol}")
                        except Exception as e:
                            logger.error(f"❌ 포지션 생성 실패 ({symbol}): {e}", exc_info=True)
                            continue
                    else:
                        logger.debug(f"💾 {symbol} 포지션이 이미 존재함, 스킵")

                    # 6. known_symbols에 추가 (중복 방지)
                    self.known_symbols.add(symbol)

                # 1초 대기 (취소 가능하도록 0.1초씩 체크)
                for _ in range(10):
                    if self.stop_event.is_set():
                        break
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"❌ Polling 루프 오류: {e}", exc_info=True)

                # 에러 발생 시 1초 대기 후 재시도
                if not self.stop_event.is_set():
                    time.sleep(1.0)

        logger.info("📊 Polling 루프 종료")

    def reset_known_symbols(self):
        """
        known_symbols 초기화

        포지션 파일이 삭제되었거나 초기화가 필요한 경우 사용
        """
        logger.info("🔄 known_symbols 초기화")
        self.known_symbols.clear()

    def add_known_symbol(self, symbol: str):
        """
        known_symbols에 심볼 추가

        다른 곳에서 포지션을 생성한 경우 중복 방지를 위해 사용

        Args:
            symbol: 심볼 (예: "KRW-BTC")
        """
        self.known_symbols.add(symbol)
        logger.debug(f"💾 known_symbols에 추가: {symbol}")

    def shutdown(self):
        """
        완전 종료

        Polling 중지 및 모든 자원 정리
        """
        logger.info("🛑 BalancePollingManager 종료")

        self.stop_polling()
        self.is_running = False

        # 스레드 완전 종료 대기
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=3.0)

        logger.info("✅ BalancePollingManager 종료 완료")

    def update_config(self, config: dict):
        """
        Config 업데이트 (설정 변경 시 호출)

        Bug #4 수정: 설정 변경 시 그룹 매핑 정보 업데이트

        Args:
            config: 새로운 config dict
        """
        self.config = config
        logger.info("✅ BalancePollingManager config 업데이트 완료")
