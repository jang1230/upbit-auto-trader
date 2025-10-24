"""
Trade Data Structure
거래 내역 데이터 구조

매수/매도 거래를 기록하고 추적하는 데이터 클래스
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Trade:
    """
    거래 내역 데이터
    
    Attributes:
        timestamp: 거래 시각
        symbol: 코인 심볼 (예: 'KRW-BTC')
        trade_type: 거래 유형 ('buy', 'sell')
        price: 거래 가격 (원)
        quantity: 거래 수량
        amount: 거래 금액 (price * quantity)
        profit: 손익 (매도 시에만 유효, 매수 시 0)
        profit_pct: 손익률 (매도 시에만 유효, 매수 시 0)
        reason: 거래 사유 (예: '시그널 매수', '익절', '손절')
        order_id: 주문 ID (실제 거래 시)
    """
    timestamp: datetime
    symbol: str
    trade_type: str  # 'buy' or 'sell'
    price: float
    quantity: float
    amount: float
    profit: float = 0.0
    profit_pct: float = 0.0
    reason: str = ""
    order_id: Optional[str] = None
    
    def to_dict(self):
        """딕셔너리로 변환 (시그널 전송용)"""
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'trade_type': self.trade_type,
            'price': self.price,
            'quantity': self.quantity,
            'amount': self.amount,
            'profit': self.profit,
            'profit_pct': self.profit_pct,
            'reason': self.reason,
            'order_id': self.order_id
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """딕셔너리로부터 생성"""
        return cls(
            timestamp=data.get('timestamp', datetime.now()),
            symbol=data['symbol'],
            trade_type=data['trade_type'],
            price=data['price'],
            quantity=data['quantity'],
            amount=data['amount'],
            profit=data.get('profit', 0.0),
            profit_pct=data.get('profit_pct', 0.0),
            reason=data.get('reason', ''),
            order_id=data.get('order_id')
        )
    
    def get_symbol_short(self) -> str:
        """심볼에서 'KRW-' 제거"""
        return self.symbol.replace('KRW-', '')
    
    def get_type_emoji(self) -> str:
        """거래 유형 이모지"""
        return "🔴" if self.trade_type == 'buy' else "🔵"
    
    def get_type_text(self) -> str:
        """거래 유형 텍스트 (한글)"""
        return "매수" if self.trade_type == 'buy' else "매도"
    
    def get_time_str(self) -> str:
        """시각 문자열 (HH:MM:SS)"""
        return self.timestamp.strftime("%H:%M:%S")
    
    def __repr__(self) -> str:
        return (
            f"Trade({self.get_symbol_short()}, "
            f"{self.get_type_text()}, "
            f"{self.price:,.0f}원, "
            f"{self.quantity:.8f}, "
            f"손익: {self.profit:+,.0f}원)"
        )
