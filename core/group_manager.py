"""
V4 그룹 관리자

역할:
- 그룹 생성/수정/삭제
- 코인 할당/이동
- 그룹별 설정 적용
- 그룹 제약사항 검증
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from core.config_manager import ConfigManager
from core.position_manager import PositionManager


class GroupValidationError(Exception):
    """그룹 검증 오류"""
    pass


class CoinAlreadyAssignedError(GroupValidationError):
    """코인이 이미 다른 그룹에 할당됨"""
    pass


class GroupNotFoundError(GroupValidationError):
    """그룹을 찾을 수 없음"""
    pass


class ActivePositionError(GroupValidationError):
    """활성 포지션이 존재하여 작업 불가"""
    pass


class GroupManager:
    """V4 그룹 관리 핵심 클래스"""

    def __init__(self, config_path: str = "config/trading_config.json", mode: str = "live"):
        """
        Args:
            config_path: 설정 파일 경로
            mode: "live" 또는 "dryrun"
        """
        self.config_manager = ConfigManager(config_path)
        self.position_manager = PositionManager(mode)

        # 설정 로드
        self.config = self.config_manager.load_config()

    def create_group(
        self,
        group_id: str,
        name: str,
        coins: List[str] = None,
        buy_settings: Dict[str, Any] = None,
        dca_settings: Dict[str, Any] = None,
        profit_settings: Dict[str, Any] = None,
        loss_settings: Dict[str, Any] = None,
        observation_only: bool = False
    ) -> Dict[str, Any]:
        """
        새 그룹 생성

        Args:
            group_id: 그룹 ID (사용자 지정, 예: "large_cap")
            name: 그룹명
            coins: 코인 리스트 (기본값: [])
            buy_settings: 매수 설정 (기본값: manual 모드)
            dca_settings: DCA 설정 (기본값: disabled)
            profit_settings: 익절 설정 (기본값: alert)
            loss_settings: 손절 설정 (기본값: alert)
            observation_only: 관찰 전용 모드

        Returns:
            생성된 그룹

        Raises:
            GroupValidationError: 그룹 ID 중복 또는 코인 중복 할당
        """
        # 그룹 ID 중복 확인
        if group_id in self.config['groups']:
            raise GroupValidationError(f"그룹 ID가 이미 존재합니다: {group_id}")

        # 코인 중복 할당 확인
        coins = coins or []
        for coin in coins:
            existing_group = self._find_group_by_coin(coin)
            if existing_group:
                raise CoinAlreadyAssignedError(
                    f"코인 {coin}이 이미 그룹 '{existing_group['name']}'에 할당되어 있습니다."
                )

        # 기본 설정 생성
        group = {
            "name": name,
            "observation_only": observation_only,
            "coins": coins,
            "buy_settings": buy_settings or {
                "mode": "manual"
            },
            "dca_settings": dca_settings or {
                "mode": "disabled",
                "levels": []
            },
            "profit_settings": profit_settings or {
                "mode": "alert",
                "levels": [{"price_ratio": 5.0, "quantity_ratio": 100}]
            },
            "loss_settings": loss_settings or {
                "mode": "alert",
                "levels": [{"price_ratio": -15.0, "quantity_ratio": 100}]
            }
        }

        # 그룹 추가
        self.config_manager.add_group(group_id, group)
        self.config = self.config_manager.load_config()  # 리로드

        print(f"✅ 그룹 생성: {name} (ID: {group_id}, 코인: {len(coins)}개)")
        return group

    def delete_group(self, group_id: str, force: bool = False) -> bool:
        """
        그룹 삭제

        Args:
            group_id: 그룹 ID
            force: 강제 삭제 (활성 포지션 무시)

        Returns:
            삭제 성공 여부

        Raises:
            GroupNotFoundError: 그룹을 찾을 수 없음
            ActivePositionError: 활성 포지션이 존재함 (force=False인 경우)
        """
        # 그룹 존재 확인
        group = self.config_manager.get_group_by_id(group_id)
        if not group:
            raise GroupNotFoundError(f"그룹을 찾을 수 없습니다: {group_id}")

        # 활성 포지션 확인
        if not force:
            active_positions = self.position_manager.get_positions_by_group(group_id)
            active_count = len([p for p in active_positions.values() if p.get('status') == 'active'])

            if active_count > 0:
                raise ActivePositionError(
                    f"그룹에 {active_count}개의 활성 포지션이 존재합니다. "
                    f"포지션을 먼저 정리하거나 force=True로 강제 삭제하세요."
                )

        # 그룹 삭제
        self.config_manager.remove_group(group_id)
        self.config = self.config_manager.load_config()  # 리로드

        print(f"✅ 그룹 삭제: {group['name']} (ID: {group_id})")
        return True

    def update_group_settings(
        self,
        group_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        그룹 설정 업데이트

        Args:
            group_id: 그룹 ID
            updates: 업데이트할 필드들 (name, buy_settings, dca_settings 등)

        Returns:
            업데이트된 그룹

        Raises:
            GroupNotFoundError: 그룹을 찾을 수 없음
        """
        # 그룹 존재 확인
        group = self.config_manager.get_group_by_id(group_id)
        if not group:
            raise GroupNotFoundError(f"그룹을 찾을 수 없습니다: {group_id}")

        # coins 변경 시 중복 확인
        if 'coins' in updates:
            new_coins = updates['coins']
            current_coins = group.get('coins', [])

            # 새로 추가되는 코인들만 중복 확인
            added_coins = set(new_coins) - set(current_coins)
            for coin in added_coins:
                existing_group = self._find_group_by_coin(coin)
                if existing_group:
                    raise CoinAlreadyAssignedError(
                        f"코인 {coin}이 이미 그룹 '{existing_group['name']}'에 할당되어 있습니다."
                    )

        # 업데이트
        self.config_manager.update_group(group_id, updates)
        self.config = self.config_manager.load_config()  # 리로드

        updated_group = self.config_manager.get_group_by_id(group_id)
        print(f"✅ 그룹 설정 업데이트: {updated_group['name']} (ID: {group_id})")
        return updated_group

    def add_coin_to_group(self, group_id: str, symbol: str) -> Dict[str, Any]:
        """
        그룹에 코인 추가

        Args:
            group_id: 그룹 ID
            symbol: 코인 심볼 (예: "KRW-BTC")

        Returns:
            업데이트된 그룹

        Raises:
            GroupNotFoundError: 그룹을 찾을 수 없음
            CoinAlreadyAssignedError: 코인이 이미 다른 그룹에 할당됨
        """
        # 그룹 존재 확인
        group = self.config_manager.get_group_by_id(group_id)
        if not group:
            raise GroupNotFoundError(f"그룹을 찾을 수 없습니다: {group_id}")

        # 코인 중복 확인
        existing_group = self._find_group_by_coin(symbol)
        if existing_group:
            raise CoinAlreadyAssignedError(
                f"코인 {symbol}이 이미 그룹 '{existing_group['name']}'에 할당되어 있습니다."
            )

        # 코인 추가
        coins = group.get('coins', [])
        if symbol not in coins:
            coins.append(symbol)
            return self.update_group_settings(group_id, {'coins': coins})

        return group

    def remove_coin_from_group(
        self,
        group_id: str,
        symbol: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        그룹에서 코인 제거

        Args:
            group_id: 그룹 ID
            symbol: 코인 심볼
            force: 강제 제거 (활성 포지션 무시)

        Returns:
            업데이트된 그룹

        Raises:
            GroupNotFoundError: 그룹을 찾을 수 없음
            ActivePositionError: 활성 포지션이 존재함 (force=False인 경우)
        """
        # 그룹 존재 확인
        group = self.config_manager.get_group_by_id(group_id)
        if not group:
            raise GroupNotFoundError(f"그룹을 찾을 수 없습니다: {group_id}")

        # 활성 포지션 확인
        if not force:
            position = self.position_manager.get_position(symbol)
            if position and position.get('status') == 'active':
                raise ActivePositionError(
                    f"코인 {symbol}에 활성 포지션이 존재합니다. "
                    f"포지션을 먼저 정리하거나 force=True로 강제 제거하세요."
                )

        # 코인 제거
        coins = group.get('coins', [])
        if symbol in coins:
            coins.remove(symbol)
            return self.update_group_settings(group_id, {'coins': coins})

        return group

    def move_coin(
        self,
        symbol: str,
        from_group_id: str,
        to_group_id: str,
        force: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        코인을 그룹 간 이동

        Args:
            symbol: 코인 심볼
            from_group_id: 원본 그룹 ID
            to_group_id: 대상 그룹 ID
            force: 강제 이동 (활성 포지션 무시)

        Returns:
            (원본 그룹, 대상 그룹)

        Raises:
            GroupNotFoundError: 그룹을 찾을 수 없음
            ActivePositionError: 활성 포지션이 존재함 (force=False인 경우)
        """
        # 두 그룹 모두 존재 확인
        from_group = self.config_manager.get_group_by_id(from_group_id)
        to_group = self.config_manager.get_group_by_id(to_group_id)

        if not from_group:
            raise GroupNotFoundError(f"원본 그룹을 찾을 수 없습니다: {from_group_id}")
        if not to_group:
            raise GroupNotFoundError(f"대상 그룹을 찾을 수 없습니다: {to_group_id}")

        # 활성 포지션 확인
        if not force:
            position = self.position_manager.get_position(symbol)
            if position and position.get('status') == 'active':
                raise ActivePositionError(
                    f"코인 {symbol}에 활성 포지션이 존재합니다. "
                    f"설정 변경은 위험할 수 있습니다. force=True로 강제 이동하세요."
                )

        # 원본 그룹에서 제거
        from_coins = from_group.get('coins', [])
        if symbol in from_coins:
            from_coins.remove(symbol)
            self.update_group_settings(from_group_id, {'coins': from_coins})

        # 대상 그룹에 추가
        to_coins = to_group.get('coins', [])
        if symbol not in to_coins:
            to_coins.append(symbol)
            self.update_group_settings(to_group_id, {'coins': to_coins})

        print(f"✅ 코인 이동: {symbol} | {from_group['name']} → {to_group['name']}")

        # 리로드
        self.config = self.config_manager.load_config()
        return (
            self.config_manager.get_group_by_id(from_group_id),
            self.config_manager.get_group_by_id(to_group_id)
        )

    def get_group_by_symbol(self, symbol: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        코인이 속한 그룹 조회

        Args:
            symbol: 코인 심볼

        Returns:
            (group_id, group) 또는 None
        """
        return self.config_manager.get_group_by_symbol(symbol)

    def get_all_groups(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 그룹 반환

        Returns:
            딕셔너리 {group_id: group_data}
        """
        return self.config_manager.get_all_groups()

    def get_group_statistics(self, group_id: str) -> Dict[str, Any]:
        """
        그룹 통계

        Args:
            group_id: 그룹 ID

        Returns:
            통계 딕셔너리
        """
        group = self.config_manager.get_group_by_id(group_id)
        if not group:
            raise GroupNotFoundError(f"그룹을 찾을 수 없습니다: {group_id}")

        # 그룹의 포지션들
        positions = self.position_manager.get_positions_by_group(group_id)
        active_positions = [p for p in positions.values() if p.get('status') == 'active']

        # 통계 계산
        total_invested = sum(p.get('total_invested_krw', 0) for p in active_positions)
        total_value = sum(p.get('current_value_krw', 0) for p in active_positions)
        total_profit = total_value - total_invested
        profit_pct = (total_profit / total_invested * 100) if total_invested > 0 else 0

        return {
            "group_name": group['name'],
            "total_coins": len(group.get('coins', [])),
            "active_positions": len(active_positions),
            "total_invested_krw": total_invested,
            "total_value_krw": total_value,
            "total_profit_krw": total_profit,
            "profit_pct": profit_pct
        }

    def validate_group_constraints(self, group_id: str) -> bool:
        """
        그룹 제약사항 검증

        Args:
            group_id: 그룹 ID

        Returns:
            검증 통과 여부
        """
        group = self.config_manager.get_group_by_id(group_id)
        if not group:
            return False

        # 1. 코인 중복 할당 확인
        all_coins = []
        for gid, g in self.get_all_groups().items():
            all_coins.extend(g.get('coins', []))

        if len(all_coins) != len(set(all_coins)):
            print(f"⚠️ 코인 중복 할당 감지")
            return False

        # 2. 필수 필드 확인
        required_fields = ['name', 'coins', 'buy_settings', 'dca_settings', 'profit_settings', 'loss_settings']
        for field in required_fields:
            if field not in group:
                print(f"⚠️ 필수 필드 누락: {field}")
                return False

        return True

    def _find_group_by_coin(self, symbol: str) -> Optional[Dict[str, Any]]:
        """코인이 속한 그룹 찾기 (내부용)"""
        result = self.config_manager.get_group_by_symbol(symbol)
        if result:
            group_id, group = result
            return group
        return None

    def get_coins_without_group(self, all_symbols: List[str]) -> List[str]:
        """
        그룹에 할당되지 않은 코인 조회

        Args:
            all_symbols: 전체 코인 리스트

        Returns:
            할당되지 않은 코인 리스트
        """
        assigned_coins = set()
        for group in self.get_all_groups().values():
            assigned_coins.update(group.get('coins', []))

        return [s for s in all_symbols if s not in assigned_coins]


if __name__ == "__main__":
    # 테스트 코드
    print("=== GroupManager 테스트 ===\n")

    manager = GroupManager(mode="dryrun")

    # 1. 그룹 생성
    print("1. 그룹 생성")
    try:
        group1 = manager.create_group(
            group_id="test_group_1",
            name="테스트 그룹 1",
            coins=["KRW-BTC", "KRW-ETH"],
            buy_settings={"mode": "auto", "auto_config": {"buy_amount_krw": 50000}}
        )
        print(f"   - 그룹명: {group1['name']}")
        print(f"   - 코인: {group1['coins']}")
    except Exception as e:
        print(f"   ⚠️ 오류: {e}")
    print()

    # 2. 그룹 조회
    print("2. 그룹 조회")
    all_groups = manager.get_all_groups()
    print(f"   - 전체 그룹 수: {len(all_groups)}")
    for gid, group in all_groups.items():
        print(f"   - {gid}: {group['name']} ({len(group.get('coins', []))}개 코인)")
    print()

    # 3. 코인으로 그룹 찾기
    print("3. 코인으로 그룹 찾기")
    result = manager.get_group_by_symbol("KRW-BTC")
    if result:
        group_id, group = result
        print(f"   - KRW-BTC → {group['name']} (ID: {group_id})")
    print()

    # 4. 코인 추가
    print("4. 코인 추가")
    try:
        manager.add_coin_to_group("test_group_1", "KRW-XRP")
        print(f"   - KRW-XRP 추가 완료")
    except Exception as e:
        print(f"   ⚠️ 오류: {e}")
    print()

    # 5. 그룹 통계
    print("5. 그룹 통계")
    try:
        stats = manager.get_group_statistics("test_group_1")
        print(f"   - 코인 수: {stats['total_coins']}")
        print(f"   - 활성 포지션: {stats['active_positions']}")
    except Exception as e:
        print(f"   ⚠️ 오류: {e}")
    print()

    # 6. 그룹 삭제
    print("6. 그룹 삭제")
    try:
        manager.delete_group("test_group_1", force=True)
        print(f"   - 삭제 완료")
    except Exception as e:
        print(f"   ⚠️ 오류: {e}")
    print()

    print("✅ 테스트 완료!")
