"""
V4 포지션 관리자

역할:
- Live/Dry-run 포지션 별도 관리
- 포지션 CRUD (생성/조회/업데이트/삭제)
- 그룹별 포지션 조회
- 가상 잔고 관리 (Dry-run용)
- Upbit API 동기화 (Live 모드)
"""

import json
import os
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from core.upbit_api import UpbitAPI

logger = logging.getLogger(__name__)


class PositionManager:
    """V4 포지션 관리자"""

    POSITIONS_LIVE_PATH = "data/positions_live.json"
    POSITIONS_DRYRUN_PATH = "data/positions_dryrun.json"
    VIRTUAL_BALANCES_PATH = "data/virtual_balances.json"

    def __init__(self, mode: str = "live", upbit_api: Optional['UpbitAPI'] = None):
        """
        Args:
            mode: "live" 또는 "dryrun"
            upbit_api: UpbitAPI 인스턴스 (Live 모드에서 Upbit 동기화에 필요)
        """
        if mode not in ["live", "dryrun"]:
            raise ValueError(f"잘못된 모드: {mode} (live 또는 dryrun만 가능)")

        self.mode = mode
        self.positions_path = (
            self.POSITIONS_LIVE_PATH if mode == "live"
            else self.POSITIONS_DRYRUN_PATH
        )

        # Upbit API (Live 모드에서만 사용)
        self.upbit_api = upbit_api

        # 포지션 캐시
        self.positions: Dict[str, Dict[str, Any]] = {}

        # Thread-safe file I/O lock
        self._lock = threading.Lock()

        # 로드
        self._load_positions()

    def _load_positions(self) -> None:
        """포지션 파일 로드"""
        if not os.path.exists(self.positions_path):
            self.positions = {}
            self._save_positions()
            return

        try:
            with open(self.positions_path, 'r', encoding='utf-8') as f:
                self.positions = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ 포지션 파일 파싱 오류: {self.positions_path}")
            self.positions = {}

    def _save_positions(self) -> None:
        """포지션 파일 저장 (Thread-safe)"""
        with self._lock:
            os.makedirs(os.path.dirname(self.positions_path), exist_ok=True)
            with open(self.positions_path, 'w', encoding='utf-8') as f:
                json.dump(self.positions, f, indent=2, ensure_ascii=False)

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        포지션 조회

        Args:
            symbol: 코인 심볼 (예: "KRW-BTC")

        Returns:
            포지션 정보 또는 None
        """
        return self.positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """모든 포지션 반환"""
        return self.positions.copy()

    def get_positions_by_group(self, group_id: str) -> Dict[str, Dict[str, Any]]:
        """
        특정 그룹의 포지션 조회

        Args:
            group_id: 그룹 ID

        Returns:
            해당 그룹의 포지션들
        """
        return {
            symbol: pos
            for symbol, pos in self.positions.items()
            if pos.get('group_id') == group_id
        }

    def get_active_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        활성 포지션만 조회 (status='active')

        Returns:
            활성 포지션들
        """
        return {
            symbol: pos
            for symbol, pos in self.positions.items()
            if pos.get('status') == 'active'
        }

    def create_position(
        self,
        symbol: str,
        group_id: str,
        entry_price: float,
        entry_amount: float,
        buy_amount_krw: float,
        **kwargs
    ) -> Dict[str, Any]:
        """
        새 포지션 생성

        Args:
            symbol: 코인 심볼
            group_id: 그룹 ID
            entry_price: 진입 가격
            entry_amount: 진입 수량
            buy_amount_krw: 매수 금액 (KRW)
            **kwargs: 추가 정보

        Returns:
            생성된 포지션
        """
        if symbol in self.positions:
            raise ValueError(f"포지션이 이미 존재합니다: {symbol}")

        position = {
            "group_id": group_id,
            "symbol": symbol,
            "status": "active",
            "entry_price": entry_price,
            "entry_amount": entry_amount,
            "entry_krw": buy_amount_krw,
            "current_price": entry_price,
            "current_value_krw": buy_amount_krw,
            "profit_krw": 0.0,
            "profit_pct": 0.0,
            "dca_count": 0,
            "dca_history": [],
            "total_invested_krw": buy_amount_krw,
            "total_amount": entry_amount,
            "average_price": entry_price,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            **kwargs
        }

        self.positions[symbol] = position
        self._save_positions()

        print(f"✅ 포지션 생성 ({self.mode}): {symbol} @ {entry_price:,.0f}원")
        return position

    def update_position(
        self,
        symbol: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        포지션 업데이트

        Args:
            symbol: 코인 심볼
            updates: 업데이트할 필드들

        Returns:
            업데이트된 포지션
        """
        if symbol not in self.positions:
            raise ValueError(f"포지션을 찾을 수 없습니다: {symbol}")

        # 업데이트 시간 자동 갱신
        updates['updated_at'] = datetime.now().isoformat()

        self.positions[symbol].update(updates)
        self._save_positions()

        return self.positions[symbol]

    def update_price(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """
        현재가 업데이트 및 수익률 계산

        Args:
            symbol: 코인 심볼
            current_price: 현재 가격

        Returns:
            업데이트된 포지션
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        # 현재 평가액 계산
        total_amount = position['total_amount']
        current_value_krw = current_price * total_amount

        # 수익 계산
        total_invested = position['total_invested_krw']
        profit_krw = current_value_krw - total_invested
        profit_pct = (profit_krw / total_invested) * 100 if total_invested > 0 else 0

        # 업데이트
        updates = {
            'current_price': current_price,
            'current_value_krw': current_value_krw,
            'profit_krw': profit_krw,
            'profit_pct': profit_pct
        }

        return self.update_position(symbol, updates)

    def add_dca(
        self,
        symbol: str,
        dca_price: float,
        dca_amount: float,
        dca_krw: float,
        level: int
    ) -> Dict[str, Any]:
        """
        DCA 추가 매수 기록

        Args:
            symbol: 코인 심볼
            dca_price: DCA 가격
            dca_amount: DCA 수량
            dca_krw: DCA 금액 (KRW)
            level: DCA 레벨

        Returns:
            업데이트된 포지션
        """
        if symbol not in self.positions:
            raise ValueError(f"포지션을 찾을 수 없습니다: {symbol}")

        position = self.positions[symbol]

        # DCA 기록 추가
        dca_record = {
            "level": level,
            "price": dca_price,
            "amount": dca_amount,
            "krw": dca_krw,
            "timestamp": datetime.now().isoformat()
        }
        position['dca_history'].append(dca_record)

        # 평균 단가 재계산
        total_amount = position['total_amount'] + dca_amount
        total_invested = position['total_invested_krw'] + dca_krw
        average_price = total_invested / total_amount if total_amount > 0 else 0

        # 업데이트
        updates = {
            'dca_count': position['dca_count'] + 1,
            'dca_history': position['dca_history'],
            'total_amount': total_amount,
            'total_invested_krw': total_invested,
            'average_price': average_price
        }

        print(f"✅ DCA 추가 ({self.mode}): {symbol} @ {dca_price:,.0f}원 (레벨 {level})")
        return self.update_position(symbol, updates)

    def close_position(
        self,
        symbol: str,
        close_price: float,
        close_reason: str = "manual"
    ) -> Dict[str, Any]:
        """
        포지션 종료

        Args:
            symbol: 코인 심볼
            close_price: 청산 가격
            close_reason: 청산 이유 (profit, loss, manual 등)

        Returns:
            종료된 포지션
        """
        if symbol not in self.positions:
            raise ValueError(f"포지션을 찾을 수 없습니다: {symbol}")

        position = self.positions[symbol]

        # 최종 수익 계산
        total_amount = position['total_amount']
        total_invested = position['total_invested_krw']
        final_value = close_price * total_amount
        final_profit = final_value - total_invested
        final_profit_pct = (final_profit / total_invested) * 100 if total_invested > 0 else 0

        # 업데이트
        updates = {
            'status': 'closed',
            'close_price': close_price,
            'close_reason': close_reason,
            'close_value_krw': final_value,
            'final_profit_krw': final_profit,
            'final_profit_pct': final_profit_pct,
            'closed_at': datetime.now().isoformat()
        }

        print(f"✅ 포지션 종료 ({self.mode}): {symbol} | {close_reason} | {final_profit_pct:+.2f}%")
        return self.update_position(symbol, updates)

    def delete_position(self, symbol: str) -> None:
        """
        포지션 삭제 (완전 제거)

        Args:
            symbol: 코인 심볼
        """
        if symbol not in self.positions:
            return

        del self.positions[symbol]
        self._save_positions()
        print(f"✅ 포지션 삭제 ({self.mode}): {symbol}")

    def has_position(self, symbol: str) -> bool:
        """포지션 존재 여부"""
        return symbol in self.positions

    def _find_group_for_coin(self, symbol: str, config: Dict[str, Any]) -> Optional[str]:
        """
        특정 코인이 어느 그룹에 속하는지 찾기

        Args:
            symbol: 코인 심볼 (예: "KRW-BTC")
            config: 전체 설정 딕셔너리

        Returns:
            그룹 ID 또는 None (어느 그룹에도 속하지 않음)
        """
        groups = config.get('groups', {})

        for group_id, group_data in groups.items():
            coins = group_data.get('coins', [])
            if symbol in coins:
                return group_id

        return None

    def get_total_valuation(self) -> float:
        """
        전체 포지션 평가액 합계

        Returns:
            총 평가액 (KRW)
        """
        return sum(
            pos.get('current_value_krw', 0)
            for pos in self.positions.values()
            if pos.get('status') == 'active'
        )

    def get_total_profit(self) -> tuple:
        """
        전체 포지션 수익 합계

        Returns:
            (총 수익 KRW, 총 수익률%)
        """
        active_positions = [
            pos for pos in self.positions.values()
            if pos.get('status') == 'active'
        ]

        if not active_positions:
            return 0.0, 0.0

        total_profit_krw = sum(pos.get('profit_krw', 0) for pos in active_positions)
        total_invested = sum(pos.get('total_invested_krw', 0) for pos in active_positions)

        profit_pct = (total_profit_krw / total_invested * 100) if total_invested > 0 else 0

        return total_profit_krw, profit_pct

    def sync_with_upbit(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upbit API와 동기화 (개선 버전)

        프로그램 시작 시 최초 1회 호출하여:
        1. Upbit에서 실제 보유 자산 조회
        2. 로컬 포지션 파일과 비교
        3. balance, avg_buy_price 등 Upbit 데이터로 업데이트 (Upbit = Source of Truth)
        4. Upbit에 없는 포지션 자동 삭제 (완전 매도된 경우)
        5. config 그룹에 속한 코인만 포지션 생성

        Args:
            config: 전체 설정 딕셔너리 (그룹 정보 포함)

        Returns:
            동기화 결과 딕셔너리
                {
                    'synced_positions': List[str],  # 동기화된 심볼들
                    'new_positions': List[str],     # 새로 생성된 포지션
                    'removed_positions': List[str], # 제거된 포지션
                    'skipped_positions': List[str], # 스킵된 포지션 (그룹 없음)
                    'krw_balance': float
                }

        Raises:
            RuntimeError: Live 모드가 아니거나 upbit_api가 없을 때
        """
        if self.mode != "live":
            raise RuntimeError("Upbit 동기화는 Live 모드에서만 가능합니다.")

        if self.upbit_api is None:
            raise RuntimeError("UpbitAPI 인스턴스가 설정되지 않았습니다.")

        print("🔄 Upbit 동기화 시작...")

        # Upbit 계좌 정보 조회
        accounts = self.upbit_api.get_accounts()

        synced_positions = []
        new_positions = []
        removed_positions = []
        skipped_positions = []
        krw_balance = 0.0

        # Upbit 보유 자산 처리
        for account in accounts:
            currency = account['currency']
            balance = float(account['balance'])
            locked = float(account['locked'])
            avg_buy_price = float(account['avg_buy_price'])

            # KRW 잔고는 별도 처리
            if currency == 'KRW':
                krw_balance = balance
                print(f"   💰 KRW 잔고: {krw_balance:,.0f}원")
                continue

            # 보유량이 거의 없으면 무시 (먼지)
            if balance < 0.00000001:
                continue

            # 심볼 생성 (예: BTC → KRW-BTC)
            symbol = f"KRW-{currency}"

            # 기존 포지션 확인
            position = self.get_position(symbol)

            if position:
                # 기존 포지션 업데이트 (Upbit = Source of Truth)
                updates = {
                    'total_amount': balance,
                    'average_price': avg_buy_price,
                    'locked_amount': locked,
                    'total_invested_krw': avg_buy_price * balance
                }
                self.update_position(symbol, updates)
                synced_positions.append(symbol)
                print(f"   ✅ 동기화: {symbol} | {balance:.8f} @ {avg_buy_price:,.0f}원")
            else:
                # 새 포지션 발견 (Upbit에는 있지만 로컬에 없음)
                # config 그룹에 속한 코인만 자동 생성
                group_id = self._find_group_for_coin(symbol, config)

                if group_id:
                    # 그룹에 속한 코인 → 자동 생성
                    try:
                        new_position = self.create_position(
                            symbol=symbol,
                            group_id=group_id,
                            entry_price=avg_buy_price,
                            entry_amount=balance,
                            buy_amount_krw=avg_buy_price * balance,
                            locked_amount=locked
                        )
                        new_positions.append(symbol)
                        print(f"   🆕 포지션 생성: {symbol} → {group_id} | {balance:.8f} @ {avg_buy_price:,.0f}원")
                    except Exception as e:
                        print(f"   ⚠️ 포지션 생성 실패: {symbol} - {e}")
                        skipped_positions.append(symbol)
                else:
                    # 그룹에 속하지 않은 코인 → 스킵
                    skipped_positions.append(symbol)
                    print(f"   ⏭️ 스킵: {symbol} (그룹 없음) | {balance:.8f} @ {avg_buy_price:,.0f}원")

        # 로컬 포지션 정리: Upbit에 없거나 그룹에서 제외된 포지션 삭제
        upbit_symbols = {f"KRW-{account['currency']}" for account in accounts if account['currency'] != 'KRW'}

        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]

            if position.get('status') != 'active':
                continue

            # 조건 1: Upbit에 없는 포지션 (완전 매도됨)
            if symbol not in upbit_symbols:
                self.delete_position(symbol)
                removed_positions.append(symbol)
                print(f"   🗑️ 자동 삭제: {symbol} (Upbit에 없음, 완전 매도된 것으로 간주)")
                continue

            # 조건 2: 어떤 그룹에도 속하지 않는 포지션 (그룹에서 제외됨)
            group_id = self._find_group_for_coin(symbol, config)
            if not group_id:
                self.delete_position(symbol)
                removed_positions.append(symbol)
                print(f"   🗑️ 자동 삭제: {symbol} (그룹에서 제외됨)")

        print(f"✅ Upbit 동기화 완료")
        print(f"   - 동기화된 포지션: {len(synced_positions)}개")
        print(f"   - 새로 생성된 포지션: {len(new_positions)}개")
        print(f"   - 삭제된 포지션: {len(removed_positions)}개")
        print(f"   - 스킵된 포지션: {len(skipped_positions)}개")

        return {
            'synced_positions': synced_positions,
            'new_positions': new_positions,
            'removed_positions': removed_positions,
            'skipped_positions': skipped_positions,
            'krw_balance': krw_balance
        }

    def sync_from_myasset(self, assets: list, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        MyAsset WebSocket 데이터로 포지션 동기화

        실시간 잔고 변동 데이터를 받아서 포지션을 업데이트/생성/삭제합니다.
        sync_with_upbit()와 동일한 로직이지만 WebSocket 데이터를 사용합니다.

        Args:
            assets: MyAsset WebSocket에서 받은 자산 리스트
                [{"currency": "BTC", "balance": "0.001", "locked": "0", "avg_buy_price": "95000000"}, ...]
            config: 거래 설정 (그룹 정보 포함)

        Returns:
            딕셔너리 {
                'synced_positions': [symbol, ...],  # 업데이트된 포지션
                'new_positions': [symbol, ...],     # 새로 생성된 포지션
                'removed_positions': [symbol, ...], # 삭제된 포지션
                'skipped_positions': [symbol, ...]  # 스킵된 포지션 (그룹 없음)
            }
        """
        synced_positions = []
        new_positions = []
        removed_positions = []
        skipped_positions = []
        krw_balance = 0.0

        # 자산 데이터 처리
        for asset in assets:
            currency = asset.get('currency')
            balance = float(asset.get('balance', 0))
            locked = float(asset.get('locked', 0))

            # avg_buy_price: MyAsset WebSocket에 포함 (Upbit 공식 문서 확인됨)
            avg_buy_price = float(asset.get('avg_buy_price', 0))
            avg_buy_price_modified = asset.get('avg_buy_price_modified', False)

            # 디버깅: avg_buy_price 확인
            logger.debug(f"   [MyAsset] {currency} | balance={balance:.8f}, locked={locked:.8f}, avg_buy_price={avg_buy_price:.0f}")

            # KRW 잔고는 별도 처리
            if currency == 'KRW':
                krw_balance = balance
                continue

            # 전체 보유량 계산 (balance + locked)
            total_balance = balance + locked

            # 심볼 생성
            symbol = f"KRW-{currency}"

            # ⚠️ MyAsset WebSocket은 "변동이 있는 자산만" 전송합니다!
            # 따라서 balance+locked=0인 경우만 "명시적 매도 완료"로 판단
            if total_balance < 0.00000001:
                # 명시적으로 0으로 업데이트된 경우 → 매도 완료
                position = self.get_position(symbol)
                if position:
                    self.delete_position(symbol)
                    removed_positions.append(symbol)
                    logger.info(f"   🗑️ 매도 감지: {symbol} (잔고 0)")
                continue

            # 기존 포지션 확인
            position = self.get_position(symbol)

            if position:
                # 기존 포지션 업데이트
                updates = {
                    'total_amount': balance,
                    'locked_amount': locked,
                }

                # avg_buy_price 처리: MyAsset → 기존 포지션 → REST API 순서로 사용
                if avg_buy_price > 0:
                    # MyAsset에서 제공한 평균가 사용
                    updates['average_price'] = avg_buy_price
                    updates['total_invested_krw'] = avg_buy_price * balance
                    logger.debug(f"   ✅ MyAsset 평균가 사용: {symbol} | avg_price={avg_buy_price:.0f}")
                else:
                    # MyAsset에 없으면 기존 포지션의 평균가 사용
                    existing_avg_price = position.get('average_price', 0)
                    if existing_avg_price > 0:
                        updates['total_invested_krw'] = existing_avg_price * balance
                        logger.debug(f"   ✅ 기존 평균가 사용: {symbol} | avg_price={existing_avg_price:.0f}, invested={existing_avg_price * balance:.0f}")
                    else:
                        # 둘 다 없으면 REST API로 조회
                        logger.warning(f"   ⚠️ {symbol} 평균가 없음, REST API 조회 필요")
                        if self.upbit_api:
                            accounts = self.upbit_api.get_accounts()
                            for acc in accounts:
                                if f"KRW-{acc['currency']}" == symbol:
                                    fetched_avg_price = float(acc.get('avg_buy_price', 0))
                                    updates['average_price'] = fetched_avg_price
                                    updates['total_invested_krw'] = fetched_avg_price * balance
                                    logger.info(f"   📊 REST API 평균가 조회: {symbol} = {fetched_avg_price:.0f}원")
                                    break

                self.update_position(symbol, updates)
                synced_positions.append(symbol)
                logger.debug(f"   ✅ MyAsset 동기화: {symbol} | balance={balance:.8f}, locked={locked:.8f}")
            else:
                # 새 포지션 발견 (외부 앱에서 매수한 경우)
                group_id = self._find_group_for_coin(symbol, config)

                if group_id:
                    # 그룹에 속한 코인 → 자동 생성
                    try:
                        # avg_buy_price 사용 (MyAsset에 포함됨)
                        entry_price = avg_buy_price if avg_buy_price > 0 else 0

                        if entry_price == 0:
                            # MyAsset에 avg_buy_price가 없으면 REST API로 조회
                            logger.warning(f"   ⚠️ {symbol} MyAsset에 평균가 없음, REST API 조회 필요")
                            if self.upbit_api:
                                accounts = self.upbit_api.get_accounts()
                                for acc in accounts:
                                    if f"KRW-{acc['currency']}" == symbol:
                                        entry_price = float(acc.get('avg_buy_price', 0))
                                        logger.info(f"   📊 REST API 평균가 조회: {symbol} = {entry_price:.0f}원")
                                        break

                        new_position = self.create_position(
                            symbol=symbol,
                            group_id=group_id,
                            entry_price=entry_price,
                            entry_amount=balance,
                            buy_amount_krw=entry_price * balance if entry_price > 0 else 0,
                            locked_amount=locked
                        )
                        new_positions.append(symbol)
                        logger.info(f"   🆕 MyAsset 포지션 생성: {symbol} → {group_id} | {balance:.8f} @ {entry_price:.0f}원")
                    except Exception as e:
                        logger.warning(f"   ⚠️ 포지션 생성 실패: {symbol} - {e}")
                        skipped_positions.append(symbol)
                else:
                    # 그룹에 속하지 않은 코인 → 스킵
                    skipped_positions.append(symbol)
                    logger.debug(f"   ⏭️ 스킵: {symbol} (그룹 없음) | {balance:.8f}")

        # ⚠️ 중요: MyAsset WebSocket은 변동이 있는 자산만 전송하므로,
        # "메시지에 없음" ≠ "매도됨"입니다. 따라서 이 섹션은 제거합니다.
        # 삭제는 위의 "total_balance < 0.00000001" 조건에서만 수행합니다.

        logger.debug(f"💰 MyAsset 동기화 완료: 업데이트 {len(synced_positions)}, "
                    f"신규 {len(new_positions)}, 삭제 {len(removed_positions)}")

        return {
            'synced_positions': synced_positions,
            'new_positions': new_positions,
            'removed_positions': removed_positions,
            'skipped_positions': skipped_positions,
            'krw_balance': krw_balance
        }

    def get_virtual_balances(self) -> Dict[str, float]:
        """
        가상 잔고 조회 (Dry-run 모드 전용)

        Returns:
            딕셔너리 {"KRW": float, "KRW-BTC": float, ...}

        Raises:
            RuntimeError: Dry-run 모드가 아닐 때
        """
        if self.mode != "dryrun":
            raise RuntimeError("가상 잔고는 Dry-run 모드에서만 조회 가능합니다.")

        # VirtualBalanceManager 인스턴스 생성하여 잔고 로드
        virtual_mgr = VirtualBalanceManager()
        return virtual_mgr.balances


class VirtualBalanceManager:
    """Dry-run 모드 가상 잔고 관리자"""

    VIRTUAL_BALANCES_PATH = "data/virtual_balances.json"

    def __init__(self):
        self.balances: Dict[str, float] = {}
        self._load_balances()

    def _load_balances(self) -> None:
        """가상 잔고 로드"""
        if not os.path.exists(self.VIRTUAL_BALANCES_PATH):
            self.balances = {"KRW": 0.0}
            self._save_balances()
            return

        try:
            with open(self.VIRTUAL_BALANCES_PATH, 'r', encoding='utf-8') as f:
                self.balances = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ 가상 잔고 파일 파싱 오류")
            self.balances = {"KRW": 0.0}

    def _save_balances(self) -> None:
        """가상 잔고 저장"""
        os.makedirs(os.path.dirname(self.VIRTUAL_BALANCES_PATH), exist_ok=True)
        with open(self.VIRTUAL_BALANCES_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.balances, f, indent=2, ensure_ascii=False)

    def init_balance(self, krw_amount: float) -> None:
        """
        초기 KRW 잔고 설정

        Args:
            krw_amount: 초기 KRW 금액
        """
        self.balances = {"KRW": krw_amount}
        self._save_balances()
        print(f"✅ 가상 잔고 초기화: {krw_amount:,.0f}원")

    def get_krw_balance(self) -> float:
        """KRW 잔고 조회"""
        return self.balances.get("KRW", 0.0)

    def update_krw_balance(self, delta: float) -> float:
        """
        KRW 잔고 업데이트

        Args:
            delta: 변화량 (양수=입금, 음수=출금)

        Returns:
            업데이트된 KRW 잔고
        """
        current = self.balances.get("KRW", 0.0)
        new_balance = current + delta

        if new_balance < 0:
            raise ValueError(f"잔고 부족: {current:,.0f}원 (필요: {-delta:,.0f}원)")

        self.balances["KRW"] = new_balance
        self._save_balances()

        return new_balance

    def get_coin_balance(self, symbol: str) -> float:
        """
        코인 잔고 조회

        Args:
            symbol: 코인 심볼 (예: "KRW-BTC")

        Returns:
            코인 수량
        """
        return self.balances.get(symbol, 0.0)

    def update_coin_balance(self, symbol: str, delta: float) -> float:
        """
        코인 잔고 업데이트

        Args:
            symbol: 코인 심볼
            delta: 변화량

        Returns:
            업데이트된 코인 잔고
        """
        current = self.balances.get(symbol, 0.0)
        new_balance = current + delta

        if new_balance < 0:
            raise ValueError(f"코인 잔고 부족: {symbol} {current} (필요: {-delta})")

        self.balances[symbol] = new_balance

        # 잔고가 0이면 제거
        if new_balance == 0:
            del self.balances[symbol]

        self._save_balances()
        return new_balance

    def get_all_balances(self) -> Dict[str, float]:
        """모든 잔고 반환"""
        return self.balances.copy()


if __name__ == "__main__":
    # 테스트 코드
    print("=== PositionManager 테스트 ===\n")

    # Dry-run 모드로 테스트
    manager = PositionManager(mode="dryrun")

    # 1. 포지션 생성
    print("1. 포지션 생성")
    position = manager.create_position(
        symbol="KRW-BTC",
        group_id="group_test",
        entry_price=95000000,
        entry_amount=0.001,
        buy_amount_krw=95000
    )
    print(f"   - 진입가: {position['entry_price']:,.0f}원")
    print(f"   - 평균가: {position['average_price']:,.0f}원")
    print()

    # 2. 가격 업데이트
    print("2. 가격 업데이트")
    updated = manager.update_price("KRW-BTC", 96000000)
    print(f"   - 현재가: {updated['current_price']:,.0f}원")
    print(f"   - 수익률: {updated['profit_pct']:.2f}%")
    print()

    # 3. DCA 추가
    print("3. DCA 추가")
    dca_pos = manager.add_dca(
        symbol="KRW-BTC",
        dca_price=92000000,
        dca_amount=0.0015,
        dca_krw=138000,
        level=1
    )
    print(f"   - DCA 횟수: {dca_pos['dca_count']}")
    print(f"   - 평균가: {dca_pos['average_price']:,.0f}원")
    print()

    # 4. 포지션 종료
    print("4. 포지션 종료")
    closed = manager.close_position("KRW-BTC", 97000000, "profit")
    print(f"   - 최종 수익: {closed['final_profit_krw']:,.0f}원 ({closed['final_profit_pct']:.2f}%)")
    print()

    # 5. 가상 잔고 테스트
    print("5. 가상 잔고 테스트")
    balance_mgr = VirtualBalanceManager()
    balance_mgr.init_balance(1000000)
    print(f"   - 초기 잔고: {balance_mgr.get_krw_balance():,.0f}원")

    balance_mgr.update_krw_balance(-95000)
    print(f"   - 매수 후 잔고: {balance_mgr.get_krw_balance():,.0f}원")

    balance_mgr.update_coin_balance("KRW-BTC", 0.001)
    print(f"   - BTC 잔고: {balance_mgr.get_coin_balance('KRW-BTC')}")
    print()

    print("✅ 테스트 완료!")
