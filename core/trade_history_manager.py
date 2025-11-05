"""
V4 거래 내역 관리자

역할:
- 거래 기록 저장/조회
- 그룹별/코인별 거래 내역 조회
- 통계 계산 (승률, 평균 수익, 거래 횟수 등)
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path


class TradeHistoryManager:
    """V4 거래 내역 관리자"""

    TRADE_HISTORY_PATH = "data/trade_history.json"

    def __init__(self):
        self.trades: List[Dict[str, Any]] = []
        self._load_history()

    def _load_history(self) -> None:
        """거래 내역 로드"""
        if not os.path.exists(self.TRADE_HISTORY_PATH):
            self.trades = []
            self._save_history()
            return

        try:
            with open(self.TRADE_HISTORY_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.trades = data.get('trades', [])
        except json.JSONDecodeError:
            print(f"⚠️ 거래 내역 파일 파싱 오류")
            self.trades = []

    def _save_history(self) -> None:
        """거래 내역 저장"""
        os.makedirs(os.path.dirname(self.TRADE_HISTORY_PATH), exist_ok=True)

        data = {
            "trades": self.trades,
            "last_updated": datetime.now().isoformat()
        }

        with open(self.TRADE_HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_trade(
        self,
        group_id: str,
        group_name: str,
        symbol: str,
        action: str,
        trade_type: str,
        price: float,
        amount: float,
        total_krw: float,
        dry_run: bool = False,
        **kwargs
    ) -> str:
        """
        거래 기록 추가

        Args:
            group_id: 그룹 ID
            group_name: 그룹명
            symbol: 코인 심볼
            action: "buy" 또는 "sell"
            trade_type: "initial", "dca", "profit", "loss", "manual"
            price: 거래 가격
            amount: 거래 수량
            total_krw: 거래 금액 (KRW)
            dry_run: Dry-run 여부
            **kwargs: 추가 정보 (strategy_signal, notes 등)

        Returns:
            거래 ID
        """
        trade_id = f"trade_{int(datetime.now().timestamp() * 1000)}"

        trade = {
            "id": trade_id,
            "group_id": group_id,
            "group_name": group_name,
            "symbol": symbol,
            "action": action,
            "type": trade_type,
            "price": price,
            "amount": amount,
            "total_krw": total_krw,
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            **kwargs
        }

        self.trades.append(trade)
        self._save_history()

        return trade_id

    def get_all_trades(self) -> List[Dict[str, Any]]:
        """모든 거래 내역 반환 (최신순)"""
        return sorted(self.trades, key=lambda x: x['timestamp'], reverse=True)

    def get_trades_by_symbol(
        self,
        symbol: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        특정 코인의 거래 내역 조회

        Args:
            symbol: 코인 심볼
            limit: 최대 개수 (None이면 전체)

        Returns:
            거래 내역 리스트 (최신순)
        """
        trades = [t for t in self.trades if t['symbol'] == symbol]
        trades = sorted(trades, key=lambda x: x['timestamp'], reverse=True)

        if limit:
            trades = trades[:limit]

        return trades

    def get_trades_by_group(
        self,
        group_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        특정 그룹의 거래 내역 조회

        Args:
            group_id: 그룹 ID
            limit: 최대 개수

        Returns:
            거래 내역 리스트 (최신순)
        """
        trades = [t for t in self.trades if t['group_id'] == group_id]
        trades = sorted(trades, key=lambda x: x['timestamp'], reverse=True)

        if limit:
            trades = trades[:limit]

        return trades

    def get_trades_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        날짜 범위로 거래 내역 조회

        Args:
            start_date: 시작일 (ISO format)
            end_date: 종료일 (ISO format)

        Returns:
            거래 내역 리스트
        """
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        trades = [
            t for t in self.trades
            if start <= datetime.fromisoformat(t['timestamp']) <= end
        ]

        return sorted(trades, key=lambda x: x['timestamp'], reverse=True)

    def get_trades_by_action(
        self,
        action: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        액션별 거래 내역 조회 (buy/sell)

        Args:
            action: "buy" 또는 "sell"
            limit: 최대 개수

        Returns:
            거래 내역 리스트
        """
        trades = [t for t in self.trades if t['action'] == action]
        trades = sorted(trades, key=lambda x: x['timestamp'], reverse=True)

        if limit:
            trades = trades[:limit]

        return trades

    def calculate_statistics(
        self,
        group_id: Optional[str] = None,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        통계 계산

        Args:
            group_id: 특정 그룹 (None이면 전체)
            days: 최근 N일 (None이면 전체)

        Returns:
            통계 딕셔너리
        """
        # 거래 필터링
        trades = self.trades

        if group_id:
            trades = [t for t in trades if t['group_id'] == group_id]

        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            trades = [
                t for t in trades
                if datetime.fromisoformat(t['timestamp']) >= cutoff_date
            ]

        if not trades:
            return {
                "total_trades": 0,
                "buy_count": 0,
                "sell_count": 0,
                "total_buy_krw": 0,
                "total_sell_krw": 0,
                "profit_trades": 0,
                "loss_trades": 0,
                "win_rate": 0,
                "total_profit_krw": 0,
                "average_profit_krw": 0
            }

        # 매수/매도 분리
        buy_trades = [t for t in trades if t['action'] == 'buy']
        sell_trades = [t for t in trades if t['action'] == 'sell']

        # 수익/손실 거래 (매도만)
        profit_trades = [
            t for t in sell_trades
            if t.get('type') == 'profit'
        ]
        loss_trades = [
            t for t in sell_trades
            if t.get('type') == 'loss'
        ]

        # 총 거래 금액
        total_buy_krw = sum(t['total_krw'] for t in buy_trades)
        total_sell_krw = sum(t['total_krw'] for t in sell_trades)

        # 수익 계산 (매도 - 원금)
        # 주의: 정확한 수익 계산은 포지션 단위로 해야 하지만,
        # 간단히 매도 금액 - 매수 금액으로 계산
        total_profit_krw = total_sell_krw - total_buy_krw

        # 승률 (수익 거래 / 전체 매도 거래)
        total_sells = len(sell_trades)
        win_rate = (len(profit_trades) / total_sells * 100) if total_sells > 0 else 0

        # 평균 수익
        avg_profit = total_profit_krw / total_sells if total_sells > 0 else 0

        return {
            "total_trades": len(trades),
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "total_buy_krw": total_buy_krw,
            "total_sell_krw": total_sell_krw,
            "profit_trades": len(profit_trades),
            "loss_trades": len(loss_trades),
            "win_rate": win_rate,
            "total_profit_krw": total_profit_krw,
            "average_profit_krw": avg_profit
        }

    def calculate_group_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        그룹별 통계 계산

        Returns:
            {group_id: 통계, ...}
        """
        # 모든 그룹 ID 수집
        group_ids = list(set(t['group_id'] for t in self.trades))

        group_stats = {}
        for group_id in group_ids:
            group_stats[group_id] = self.calculate_statistics(group_id=group_id)

        return group_stats

    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        최근 거래 내역 조회

        Args:
            limit: 최대 개수

        Returns:
            최근 거래 리스트
        """
        trades = sorted(self.trades, key=lambda x: x['timestamp'], reverse=True)
        return trades[:limit]

    def get_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        일일 거래 요약

        Args:
            date: 날짜 (ISO format, None이면 오늘)

        Returns:
            일일 요약
        """
        if date is None:
            target_date = datetime.now().date()
        else:
            target_date = datetime.fromisoformat(date).date()

        # 해당 날짜의 거래만 필터링
        daily_trades = [
            t for t in self.trades
            if datetime.fromisoformat(t['timestamp']).date() == target_date
        ]

        if not daily_trades:
            return {
                "date": target_date.isoformat(),
                "total_trades": 0,
                "buy_count": 0,
                "sell_count": 0,
                "symbols_traded": []
            }

        buy_count = len([t for t in daily_trades if t['action'] == 'buy'])
        sell_count = len([t for t in daily_trades if t['action'] == 'sell'])
        symbols = list(set(t['symbol'] for t in daily_trades))

        return {
            "date": target_date.isoformat(),
            "total_trades": len(daily_trades),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "symbols_traded": symbols
        }

    def clear_old_trades(self, days: int = 90) -> int:
        """
        오래된 거래 내역 정리

        Args:
            days: 보관 기간 (기본값 90일)

        Returns:
            삭제된 거래 수
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        old_count = len(self.trades)
        self.trades = [
            t for t in self.trades
            if datetime.fromisoformat(t['timestamp']) >= cutoff_date
        ]

        deleted_count = old_count - len(self.trades)

        if deleted_count > 0:
            self._save_history()
            print(f"✅ {deleted_count}개의 오래된 거래 내역 정리 완료")

        return deleted_count


if __name__ == "__main__":
    # 테스트 코드
    print("=== TradeHistoryManager 테스트 ===\n")

    manager = TradeHistoryManager()

    # 1. 거래 기록 추가
    print("1. 거래 기록 추가")
    trade_id1 = manager.add_trade(
        group_id="group_test",
        group_name="테스트 그룹",
        symbol="KRW-BTC",
        action="buy",
        trade_type="initial",
        price=95000000,
        amount=0.001,
        total_krw=95000,
        dry_run=True,
        strategy_signal="RSI+MACD",
        notes="1시간봉 골든크로스"
    )
    print(f"   - 거래 ID: {trade_id1}")
    print()

    # 2. DCA 매수 기록
    print("2. DCA 매수 기록")
    trade_id2 = manager.add_trade(
        group_id="group_test",
        group_name="테스트 그룹",
        symbol="KRW-BTC",
        action="buy",
        trade_type="dca",
        price=92000000,
        amount=0.0015,
        total_krw=138000,
        dry_run=True,
        notes="DCA 레벨 1"
    )
    print(f"   - 거래 ID: {trade_id2}")
    print()

    # 3. 익절 매도 기록
    print("3. 익절 매도 기록")
    trade_id3 = manager.add_trade(
        group_id="group_test",
        group_name="테스트 그룹",
        symbol="KRW-BTC",
        action="sell",
        trade_type="profit",
        price=97000000,
        amount=0.0025,
        total_krw=242500,
        dry_run=True,
        notes="목표 익절 달성"
    )
    print(f"   - 거래 ID: {trade_id3}")
    print()

    # 4. 통계 계산
    print("4. 통계 계산")
    stats = manager.calculate_statistics()
    print(f"   - 총 거래: {stats['total_trades']}회")
    print(f"   - 매수: {stats['buy_count']}회, 매도: {stats['sell_count']}회")
    print(f"   - 총 매수액: {stats['total_buy_krw']:,.0f}원")
    print(f"   - 총 매도액: {stats['total_sell_krw']:,.0f}원")
    print(f"   - 총 수익: {stats['total_profit_krw']:,.0f}원")
    print(f"   - 승률: {stats['win_rate']:.1f}%")
    print()

    # 5. 코인별 조회
    print("5. 코인별 조회")
    btc_trades = manager.get_trades_by_symbol("KRW-BTC")
    print(f"   - BTC 거래 내역: {len(btc_trades)}건")
    print()

    # 6. 최근 거래 조회
    print("6. 최근 거래 조회")
    recent = manager.get_recent_trades(limit=5)
    print(f"   - 최근 거래: {len(recent)}건")
    if recent:
        last_trade = recent[0]
        print(f"   - 마지막 거래: {last_trade['action']} {last_trade['symbol']} @ {last_trade['price']:,.0f}원")
    print()

    # 7. 일일 요약
    print("7. 일일 요약")
    today_summary = manager.get_daily_summary()
    print(f"   - 날짜: {today_summary['date']}")
    print(f"   - 오늘 거래: {today_summary['total_trades']}건")
    print(f"   - 거래 코인: {', '.join(today_summary['symbols_traded'])}")
    print()

    print("✅ 테스트 완료!")
