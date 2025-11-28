"""
Pending Order Manager

프로그램이 보낸 주문을 추적하고 재시작 시 복구하는 관리자

Author: Claude
Created: 2025-01-26
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PendingOrderManager:
    """
    pending_order CRUD 관리

    프로그램이 Upbit에 보낸 주문을 파일에 저장하고,
    재시작 시 복구하여 포지션을 정확하게 생성합니다.

    Attributes:
        file_path (Path): pending_orders.json 파일 경로
        orders (Dict): 메모리 상의 주문 목록 {order_id: order_data}

    Example:
        >>> manager = PendingOrderManager()
        >>> manager.add_order(
        ...     order_id="abc123",
        ...     symbol="KRW-BTC",
        ...     side="bid",
        ...     price=50000000,
        ...     amount=0.001,
        ...     group_id="group_1"
        ... )
        >>> orders = manager.get_all_orders()
        >>> manager.remove_order("abc123")
    """

    def __init__(self, file_path: str = "data/pending_orders.json"):
        """
        PendingOrderManager 초기화

        Args:
            file_path: pending_orders.json 파일 경로
        """
        self.file_path = Path(file_path)
        self.orders: Dict[str, Dict] = {}

        # 파일이 없으면 생성
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_to_file()
        else:
            self._load_from_file()

    def add_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        price: float,
        amount: float,
        group_id: str,
        order_type: str = "limit",
        created_by: str = "auto",
        **extra_fields
    ) -> None:
        """
        pending_order에 주문 추가

        Args:
            order_id: Upbit API가 반환한 주문 UUID
            symbol: 마켓 코드 (예: KRW-BTC)
            side: "bid" (매수) or "ask" (매도)
            price: 주문 가격
            amount: 주문 수량
            group_id: V4 그룹 ID
            order_type: "limit", "market" 등
            created_by: "auto" (프로그램) or "manual" (수동)
            **extra_fields: 추가 필드 (거래내역 업데이트용)
                - trade_type: "initial_buy", "dca", "profit", "loss"
                - dca_level: DCA 레벨 (0-based)
                - profit_level: 익절 레벨
                - loss_level: 손절 레벨
                - group_name: 그룹 이름
                - trigger_price: 트리거 가격
                - order_amount_krw: 주문 금액 (KRW)
                - quantity_ratio: 매도 비율 (익절/손절)
                - profit_pct: 수익률 (%)

        Example:
            >>> manager.add_order(
            ...     order_id="abc-123-uuid",
            ...     symbol="KRW-XRP",
            ...     side="bid",
            ...     price=1000.0,
            ...     amount=50.0,
            ...     group_id="scalping_group",
            ...     trade_type="dca",
            ...     dca_level=2,
            ...     group_name="스캘핑 그룹"
            ... )
        """
        order_data = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "price": price,
            "amount": amount,
            "group_id": group_id,
            "order_type": order_type,
            "created_by": created_by,
            "timestamp": datetime.now().isoformat()
        }

        # 추가 필드 병합 (거래내역 업데이트용)
        order_data.update(extra_fields)

        self.orders[order_id] = order_data
        self._save_to_file()

        # 로그 메시지 개선
        trade_type = extra_fields.get('trade_type', order_type)
        level_info = ""
        if 'dca_level' in extra_fields:
            level_info = f" L{extra_fields['dca_level'] + 1}"
        elif 'profit_level' in extra_fields:
            level_info = f" L{extra_fields['profit_level']}"
        elif 'loss_level' in extra_fields:
            level_info = f" L{extra_fields['loss_level']}"

        logger.info(
            f"📝 pending_order 추가: {symbol} {trade_type}{level_info} "
            f"(order_id: {order_id[:8]}...)"
        )

    def remove_order(self, order_id: str) -> bool:
        """
        pending_order에서 주문 제거 (체결 완료 시)

        Args:
            order_id: 제거할 주문 ID

        Returns:
            bool: 제거 성공 여부

        Example:
            >>> manager.remove_order("abc-123-uuid")
            True
        """
        if order_id in self.orders:
            order = self.orders.pop(order_id)
            self._save_to_file()

            logger.info(
                f"pending_order 제거: {order['symbol']} "
                f"(order_id: {order_id[:8]}...)"
            )
            return True
        else:
            logger.warning(f"pending_order 없음: {order_id[:8]}...")
            return False

    def get_order(self, order_id: str) -> Optional[Dict]:
        """
        특정 주문 조회

        Args:
            order_id: 조회할 주문 ID

        Returns:
            Optional[Dict]: 주문 데이터 또는 None

        Example:
            >>> order = manager.get_order("abc-123-uuid")
            >>> if order:
            ...     print(order['symbol'])
        """
        return self.orders.get(order_id)

    def get_all_orders(self) -> List[Dict]:
        """
        모든 pending_order 조회

        Returns:
            List[Dict]: 모든 주문 데이터 리스트

        Example:
            >>> orders = manager.get_all_orders()
            >>> for order in orders:
            ...     print(order['symbol'], order['order_id'])
        """
        return list(self.orders.values())

    def has_order(self, order_id: str) -> bool:
        """
        주문 존재 여부 확인

        Args:
            order_id: 확인할 주문 ID

        Returns:
            bool: 존재 여부

        Example:
            >>> if manager.has_order("abc-123-uuid"):
            ...     print("프로그램이 보낸 주문")
            ... else:
            ...     print("외부 주문")
        """
        return order_id in self.orders

    def clear_all(self) -> None:
        """
        모든 pending_order 삭제 (테스트용)

        Warning:
            운영 환경에서는 사용하지 마세요!
        """
        self.orders.clear()
        self._save_to_file()
        logger.warning("모든 pending_order 삭제됨!")

    def get_count(self) -> int:
        """
        pending_order 개수 조회

        Returns:
            int: 주문 개수
        """
        return len(self.orders)

    def _load_from_file(self) -> None:
        """파일에서 pending_orders 로드"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # orders 리스트를 딕셔너리로 변환
            orders_list = data.get('orders', [])
            self.orders = {
                order['order_id']: order
                for order in orders_list
            }

            logger.info(
                f"pending_orders 로드 완료: {len(self.orders)}개"
            )

        except json.JSONDecodeError as e:
            logger.error(f"pending_orders.json 파싱 실패: {e}")
            logger.warning("빈 파일로 초기화합니다.")
            self.orders = {}
            self._save_to_file()

        except Exception as e:
            logger.error(f"pending_orders 로드 실패: {e}")
            self.orders = {}

    def _save_to_file(self) -> None:
        """pending_orders를 파일에 저장"""
        try:
            data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "orders": list(self.orders.values())
            }

            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(
                f"pending_orders 저장 완료: {len(self.orders)}개"
            )

        except Exception as e:
            logger.error(f"pending_orders 저장 실패: {e}")

    def __repr__(self) -> str:
        return f"<PendingOrderManager orders={len(self.orders)}>"
