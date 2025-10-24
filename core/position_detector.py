"""
Position Detector - 수동 매수 포지션 감지

사용자의 수동 매수를 감지하고 프로그램이 관리하는 포지션과 구분합니다.
"""

import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
from api.upbit_api import UpbitAPI

logger = logging.getLogger(__name__)


class Position:
    """포지션 정보"""

    def __init__(
        self,
        symbol: str,
        currency: str,
        balance: float,
        locked: float,
        avg_buy_price: float,
        is_managed: bool = False,
        detected_at: Optional[datetime] = None
    ):
        """
        Args:
            symbol: 거래 심볼 (예: 'KRW-BTC')
            currency: 통화 코드 (예: 'BTC')
            balance: 보유 수량
            locked: 거래 중인 수량
            avg_buy_price: 평균 매수가
            is_managed: 프로그램이 관리하는 포지션 여부
            detected_at: 감지 시각
        """
        self.symbol = symbol
        self.currency = currency
        self.balance = balance
        self.locked = locked
        self.avg_buy_price = avg_buy_price
        self.is_managed = is_managed
        self.detected_at = detected_at or datetime.now()

    @property
    def total_balance(self) -> float:
        """총 보유량 (거래 중 포함)"""
        return self.balance + self.locked

    @property
    def value_krw(self) -> float:
        """평가액 (KRW)"""
        return self.total_balance * self.avg_buy_price

    def __repr__(self):
        return (
            f"Position({self.symbol}, balance={self.balance:.6f}, "
            f"avg_price={self.avg_buy_price:,.0f}, managed={self.is_managed})"
        )


class PositionDetector:
    """
    수동 매수 포지션 감지기

    역할:
    1. Upbit API로 현재 보유 중인 코인 목록 조회
    2. 프로그램이 관리하는 포지션과 수동 매수 포지션 구분
    3. 새로운 수동 매수 감지 및 알림
    """

    def __init__(self, upbit_api: UpbitAPI, market_prefix: str = 'KRW'):
        """
        Args:
            upbit_api: Upbit API 클라이언트
            market_prefix: 마켓 접두사 (기본 'KRW')
        """
        self.api = upbit_api
        self.market_prefix = market_prefix

        # 프로그램이 관리하는 포지션 추적
        # key: symbol (예: 'KRW-BTC'), value: Position
        self._managed_positions: Dict[str, Position] = {}

        # 감지된 수동 매수 포지션
        # key: symbol, value: Position
        self._manual_positions: Dict[str, Position] = {}

        # 무시할 통화 (KRW 등)
        self._ignored_currencies: Set[str] = {market_prefix}

        logger.info(f"PositionDetector 초기화 완료 (마켓: {market_prefix})")

    def scan_positions(self) -> Dict[str, List[Position]]:
        """
        현재 보유 포지션 스캔

        Returns:
            {
                'managed': [관리 중인 포지션 리스트],
                'manual': [수동 매수 포지션 리스트],
                'new_manual': [새로 감지된 수동 매수 리스트]
            }
        """
        try:
            # Upbit API로 계좌 조회
            accounts = self.api.get_accounts()

            current_positions = {}
            new_manual_positions = []

            for account in accounts:
                currency = account['currency']

                # 무시할 통화 스킵 (KRW 등)
                if currency in self._ignored_currencies:
                    continue

                balance = float(account['balance'])
                locked = float(account['locked'])

                # 잔고가 0이면 스킵
                if balance + locked == 0:
                    continue

                avg_buy_price = float(account.get('avg_buy_price', 0))
                symbol = f"{self.market_prefix}-{currency}"

                # Position 객체 생성
                position = Position(
                    symbol=symbol,
                    currency=currency,
                    balance=balance,
                    locked=locked,
                    avg_buy_price=avg_buy_price,
                    is_managed=False,  # 일단 수동으로 간주
                    detected_at=datetime.now()
                )

                # 프로그램이 관리 중인 포지션인지 확인
                if symbol in self._managed_positions:
                    position.is_managed = True
                    self._managed_positions[symbol] = position
                else:
                    # 새로운 수동 매수인지 확인
                    if symbol not in self._manual_positions:
                        # 새로 발견된 수동 매수!
                        new_manual_positions.append(position)
                        logger.info(
                            f"🔔 새로운 수동 매수 감지: {symbol} "
                            f"수량={balance:.6f} 평단가={avg_buy_price:,.0f}원"
                        )

                    self._manual_positions[symbol] = position

                current_positions[symbol] = position

            # 청산된 포지션 정리
            self._cleanup_closed_positions(current_positions)

            return {
                'managed': list(self._managed_positions.values()),
                'manual': list(self._manual_positions.values()),
                'new_manual': new_manual_positions
            }

        except Exception as e:
            logger.error(f"포지션 스캔 중 에러: {e}")
            return {
                'managed': [],
                'manual': [],
                'new_manual': []
            }

    def register_managed_position(self, symbol: str, position: Position) -> None:
        """
        프로그램이 관리하는 포지션 등록

        Args:
            symbol: 거래 심볼 (예: 'KRW-BTC')
            position: Position 객체
        """
        position.is_managed = True
        self._managed_positions[symbol] = position

        # 수동 매수 목록에서 제거
        if symbol in self._manual_positions:
            del self._manual_positions[symbol]

        logger.info(f"✅ 관리 포지션 등록: {position}")

    def unregister_managed_position(self, symbol: str) -> None:
        """
        관리 포지션 해제 (청산 완료 시)

        Args:
            symbol: 거래 심볼
        """
        if symbol in self._managed_positions:
            del self._managed_positions[symbol]
            logger.info(f"✅ 관리 포지션 해제: {symbol}")

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        특정 심볼의 포지션 조회

        Args:
            symbol: 거래 심볼

        Returns:
            Position 객체 또는 None
        """
        # 관리 포지션에서 먼저 찾기
        if symbol in self._managed_positions:
            return self._managed_positions[symbol]

        # 수동 포지션에서 찾기
        if symbol in self._manual_positions:
            return self._manual_positions[symbol]

        return None

    def is_managed(self, symbol: str) -> bool:
        """
        프로그램이 관리하는 포지션인지 확인

        Args:
            symbol: 거래 심볼

        Returns:
            True if managed
        """
        return symbol in self._managed_positions

    def _cleanup_closed_positions(self, current_positions: Dict[str, Position]) -> None:
        """
        청산된 포지션 정리

        Args:
            current_positions: 현재 보유 중인 포지션 딕셔너리
        """
        # 관리 포지션 중 청산된 것 제거
        closed_managed = [
            symbol for symbol in self._managed_positions
            if symbol not in current_positions
        ]
        for symbol in closed_managed:
            del self._managed_positions[symbol]
            logger.info(f"✅ 청산 완료: {symbol} (관리 포지션)")

        # 수동 포지션 중 청산된 것 제거
        closed_manual = [
            symbol for symbol in self._manual_positions
            if symbol not in current_positions
        ]
        for symbol in closed_manual:
            del self._manual_positions[symbol]
            logger.info(f"✅ 청산 완료: {symbol} (수동 포지션)")

    def get_all_positions(self) -> List[Position]:
        """
        모든 포지션 반환 (관리 + 수동)

        Returns:
            Position 리스트
        """
        all_positions = list(self._managed_positions.values())
        all_positions.extend(self._manual_positions.values())
        return all_positions

    def get_managed_positions(self) -> List[Position]:
        """관리 중인 포지션만 반환"""
        return list(self._managed_positions.values())

    def get_manual_positions(self) -> List[Position]:
        """수동 매수 포지션만 반환"""
        return list(self._manual_positions.values())
