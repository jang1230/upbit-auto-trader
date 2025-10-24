"""
Risk Management Module
리스크 관리 모듈

스톱로스, 타겟 프라이스, 최대 손실 제한 등의 리스크 관리 기능을 제공합니다.

Example:
    >>> risk_manager = RiskManager(stop_loss_pct=5.0, take_profit_pct=10.0)
    >>> risk_manager.set_entry_price(100000000)  # 1억원 진입
    >>>
    >>> # 가격이 95,000,000원으로 하락
    >>> if risk_manager.check_stop_loss(95000000):
    >>>     print("스톱로스 발동!")
    >>>
    >>> # 가격이 110,000,000원으로 상승
    >>> if risk_manager.check_take_profit(110000000):
    >>>     print("타겟 달성!")
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskManager:
    """
    리스크 관리 클래스

    스톱로스, 타겟 프라이스, 최대 손실 제한 등의 기능을 제공합니다.

    Attributes:
        stop_loss_pct: 스톱로스 퍼센트 (기본값: 5.0%)
        take_profit_pct: 타겟 프라이스 퍼센트 (기본값: 10.0%)
        max_daily_loss_pct: 일일 최대 손실 퍼센트 (기본값: 10.0%)
        trailing_stop_pct: 트레일링 스톱 퍼센트 (기본값: None, 비활성화)
    """

    def __init__(
        self,
        stop_loss_pct: float = 5.0,
        take_profit_pct: float = 10.0,
        max_daily_loss_pct: float = 10.0,
        trailing_stop_pct: Optional[float] = None
    ):
        """
        리스크 관리자 초기화

        Args:
            stop_loss_pct: 스톱로스 퍼센트 (예: 5.0 = -5% 손실에서 청산)
            take_profit_pct: 타겟 프라이스 퍼센트 (예: 10.0 = +10% 수익에서 청산)
            max_daily_loss_pct: 일일 최대 손실 퍼센트 (예: 10.0 = -10% 손실 시 거래 중단)
            trailing_stop_pct: 트레일링 스톱 퍼센트 (None이면 비활성화)
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.trailing_stop_pct = trailing_stop_pct

        # 상태 변수
        self.entry_price: Optional[float] = None
        self.highest_price: Optional[float] = None  # 트레일링 스톱용
        self.daily_start_capital: Optional[float] = None
        self.daily_losses: float = 0.0
        self.current_date: Optional[datetime] = None

        logger.info(f"리스크 관리자 초기화:")
        logger.info(f"  스톱로스: -{stop_loss_pct}%")
        logger.info(f"  타겟 프라이스: +{take_profit_pct}%")
        logger.info(f"  일일 최대 손실: -{max_daily_loss_pct}%")
        if trailing_stop_pct:
            logger.info(f"  트레일링 스톱: -{trailing_stop_pct}%")

    def set_entry_price(self, price: float):
        """
        진입 가격 설정

        Args:
            price: 진입 가격
        """
        self.entry_price = price
        self.highest_price = price
        logger.info(f"진입 가격 설정: {price:,.0f}원")

    def on_position_open(self, entry_price: float, current_capital: float):
        """
        포지션 진입 시 호출

        Args:
            entry_price: 진입 가격
            current_capital: 현재 자본
        """
        self.entry_price = entry_price
        self.highest_price = entry_price

        # 일일 상태 초기화 (첫 포지션인 경우)
        if self.daily_start_capital is None:
            self.daily_start_capital = current_capital
            self.current_date = datetime.now()

        logger.info(f"✅ 포지션 진입: {entry_price:,.0f}원")

    def on_position_close(self):
        """포지션 청산 시 호출"""
        self.entry_price = None
        self.highest_price = None
        logger.info("✅ 포지션 청산")

    def reset_position(self):
        """포지션 정보 초기화 (Deprecated: on_position_close 사용)"""
        self.on_position_close()

    def check_stop_loss(self, current_price: float) -> bool:
        """
        스톱로스 확인

        Args:
            current_price: 현재 가격

        Returns:
            bool: 스톱로스 발동 여부
        """
        if self.entry_price is None:
            return False

        loss_pct = ((current_price - self.entry_price) / self.entry_price) * 100

        if loss_pct <= -self.stop_loss_pct:
            logger.warning(f"🚨 스톱로스 발동: {loss_pct:.2f}% 손실 (진입: {self.entry_price:,.0f}원 → 현재: {current_price:,.0f}원)")
            return True

        return False

    def check_take_profit(self, current_price: float) -> bool:
        """
        타겟 프라이스 확인

        Args:
            current_price: 현재 가격

        Returns:
            bool: 타겟 달성 여부
        """
        if self.entry_price is None:
            return False

        profit_pct = ((current_price - self.entry_price) / self.entry_price) * 100

        if profit_pct >= self.take_profit_pct:
            logger.info(f"🎯 타겟 달성: {profit_pct:.2f}% 수익 (진입: {self.entry_price:,.0f}원 → 현재: {current_price:,.0f}원)")
            return True

        return False

    def check_trailing_stop(self, current_price: float) -> bool:
        """
        트레일링 스톱 확인

        Args:
            current_price: 현재 가격

        Returns:
            bool: 트레일링 스톱 발동 여부
        """
        if self.trailing_stop_pct is None or self.entry_price is None:
            return False

        # 최고가 갱신
        if self.highest_price is None or current_price > self.highest_price:
            self.highest_price = current_price

        # 최고가 대비 하락률 계산
        drop_from_high = ((current_price - self.highest_price) / self.highest_price) * 100

        if drop_from_high <= -self.trailing_stop_pct:
            logger.warning(f"📉 트레일링 스톱 발동: 최고가 대비 {drop_from_high:.2f}% 하락 (최고가: {self.highest_price:,.0f}원 → 현재: {current_price:,.0f}원)")
            return True

        return False

    def update_daily_status(self, current_date: datetime, current_capital: float):
        """
        일일 상태 업데이트

        Args:
            current_date: 현재 날짜
            current_capital: 현재 자본
        """
        # 날짜가 바뀌면 일일 손실 초기화
        if self.current_date is None or current_date.date() != self.current_date.date():
            self.current_date = current_date
            self.daily_start_capital = current_capital
            self.daily_losses = 0.0
            logger.debug(f"일일 상태 초기화: {current_date.date()}, 시작 자본: {current_capital:,.0f}원")

    def check_daily_loss_limit(self, current_capital: float) -> bool:
        """
        일일 최대 손실 제한 확인

        Args:
            current_capital: 현재 자본

        Returns:
            bool: 일일 손실 한도 초과 여부
        """
        if self.daily_start_capital is None:
            return False

        daily_loss_pct = ((current_capital - self.daily_start_capital) / self.daily_start_capital) * 100

        if daily_loss_pct <= -self.max_daily_loss_pct:
            logger.error(f"⛔ 일일 최대 손실 한도 초과: {daily_loss_pct:.2f}% 손실 (시작: {self.daily_start_capital:,.0f}원 → 현재: {current_capital:,.0f}원)")
            logger.error(f"   오늘의 거래를 중단합니다.")
            return True

        return False

    def should_exit_position(self, current_price: float, current_capital: float, current_date: datetime) -> tuple[bool, str]:
        """
        포지션 청산 여부 종합 판단

        Args:
            current_price: 현재 가격
            current_capital: 현재 자본
            current_date: 현재 날짜

        Returns:
            tuple[bool, str]: (청산 여부, 청산 사유)
        """
        # 일일 상태 업데이트
        self.update_daily_status(current_date, current_capital)

        # 일일 손실 한도 체크 (최우선)
        if self.check_daily_loss_limit(current_capital):
            return True, "daily_loss_limit"

        # 스톱로스 체크
        if self.check_stop_loss(current_price):
            return True, "stop_loss"

        # 타겟 프라이스 체크
        if self.check_take_profit(current_price):
            return True, "take_profit"

        # 트레일링 스톱 체크
        if self.check_trailing_stop(current_price):
            return True, "trailing_stop"

        return False, ""

    def get_risk_metrics(self) -> Dict[str, Any]:
        """
        현재 리스크 지표 반환

        Returns:
            dict: 리스크 관련 지표
        """
        metrics = {
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'max_daily_loss_pct': self.max_daily_loss_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'entry_price': self.entry_price,
            'highest_price': self.highest_price,
        }

        if self.entry_price and self.highest_price:
            metrics['unrealized_profit_pct'] = ((self.highest_price - self.entry_price) / self.entry_price) * 100

        return metrics

    def __repr__(self) -> str:
        return (
            f"RiskManager(stop_loss={self.stop_loss_pct}%, "
            f"take_profit={self.take_profit_pct}%, "
            f"max_daily_loss={self.max_daily_loss_pct}%)"
        )
