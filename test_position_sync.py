"""
포지션 동기화 테스트 스크립트

sync_with_upbit() 개선사항을 테스트합니다:
- Threading.Lock 동작
- _find_group_for_coin() 헬퍼 메서드
- 그룹 기반 필터링
- 자동 삭제
- Upbit를 진리의 원천으로 사용

사용법:
    python test_position_sync.py
"""

import json
import os
import sys
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# position_manager만 직접 import (core/__init__.py 우회)
import importlib.util
spec = importlib.util.spec_from_file_location("position_manager", "core/position_manager.py")
position_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(position_manager_module)
PositionManager = position_manager_module.PositionManager


class MockUpbitAPI:
    """테스트용 Mock Upbit API"""

    def __init__(self, accounts: List[Dict[str, Any]]):
        self.accounts = accounts

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Mock 계좌 정보 반환"""
        return self.accounts


def create_test_config() -> Dict[str, Any]:
    """테스트용 설정 생성"""
    return {
        "version": "4.0.0",
        "global_settings": {
            "dry_run": False
        },
        "groups": {
            "group_1": {
                "name": "테스트 그룹 1",
                "coins": ["KRW-BTC", "KRW-ETH"]
            },
            "group_2": {
                "name": "테스트 그룹 2",
                "coins": ["KRW-XRP"]
            }
        }
    }


def setup_test_positions(position_manager: PositionManager):
    """테스트용 기존 포지션 생성"""
    # KRW-BTC 포지션 (Upbit에도 존재 - 업데이트 테스트용)
    position_manager.create_position(
        symbol="KRW-BTC",
        group_id="group_1",
        entry_price=90000000,
        entry_amount=0.001,
        buy_amount_krw=90000
    )

    # KRW-ADA 포지션 (Upbit에는 없음 - 삭제 테스트용)
    position_manager.create_position(
        symbol="KRW-ADA",
        group_id="group_1",
        entry_price=1000,
        entry_amount=100,
        buy_amount_krw=100000
    )

    print("✅ 테스트 포지션 생성 완료")
    print(f"   - KRW-BTC: 0.001 @ 90,000,000원")
    print(f"   - KRW-ADA: 100 @ 1,000원 (삭제 대상)")
    print()


def create_mock_upbit_accounts() -> List[Dict[str, Any]]:
    """Mock Upbit 계좌 데이터 생성"""
    return [
        {
            "currency": "KRW",
            "balance": "5000000",
            "locked": "0",
            "avg_buy_price": "0"
        },
        {
            "currency": "BTC",
            "balance": "0.001",
            "locked": "0",
            "avg_buy_price": "95000000"  # 업데이트될 가격
        },
        {
            "currency": "ETH",
            "balance": "0.05",
            "locked": "0",
            "avg_buy_price": "3000000"  # 새로 생성될 포지션 (group_1에 속함)
        },
        {
            "currency": "SOL",
            "balance": "1.5",
            "locked": "0",
            "avg_buy_price": "150000"  # 스킵될 포지션 (그룹 없음)
        }
    ]


def test_find_group_for_coin():
    """_find_group_for_coin() 메서드 테스트"""
    print("=" * 60)
    print("테스트 1: _find_group_for_coin() 헬퍼 메서드")
    print("=" * 60)

    # Dry-run 모드로 생성 (API 필요 없음)
    pm = PositionManager(mode="dryrun")
    config = create_test_config()

    # 테스트 케이스
    test_cases = [
        ("KRW-BTC", "group_1", "✅"),
        ("KRW-ETH", "group_1", "✅"),
        ("KRW-XRP", "group_2", "✅"),
        ("KRW-SOL", None, "✅"),
        ("KRW-DOGE", None, "✅"),
    ]

    for symbol, expected_group, status in test_cases:
        result = pm._find_group_for_coin(symbol, config)
        match = "✅" if result == expected_group else "❌"
        print(f"   {match} {symbol:12} → {result or 'None':10} (예상: {expected_group or 'None'})")

    print()


def test_sync_with_upbit():
    """sync_with_upbit() 전체 시나리오 테스트"""
    print("=" * 60)
    print("테스트 2: sync_with_upbit() 전체 동작")
    print("=" * 60)

    # Mock Upbit API 생성
    mock_accounts = create_mock_upbit_accounts()
    mock_api = MockUpbitAPI(mock_accounts)

    # Live 모드 PositionManager 생성
    pm = PositionManager(mode="live", upbit_api=mock_api)

    # 테스트용 기존 포지션 생성
    setup_test_positions(pm)

    print("🔄 동기화 전 포지션 상태:")
    for symbol, pos in pm.positions.items():
        print(f"   - {symbol}: {pos['total_amount']:.8f} @ {pos['avg_buy_price']:,.0f}원")
    print()

    # 설정 생성
    config = create_test_config()

    # sync_with_upbit() 실행
    print("🚀 sync_with_upbit() 실행...")
    print()

    result = pm.sync_with_upbit(config)

    print()
    print("📊 동기화 결과:")
    print(f"   - KRW 잔고: {result['krw_balance']:,.0f}원")
    print(f"   - 동기화된 포지션: {result['synced_positions']}")
    print(f"   - 새로 생성된 포지션: {result['new_positions']}")
    print(f"   - 삭제된 포지션: {result['removed_positions']}")
    print(f"   - 스킵된 포지션: {result['skipped_positions']}")
    print()

    print("🔍 동기화 후 포지션 상태:")
    for symbol, pos in pm.positions.items():
        print(f"   - {symbol}: {pos['total_amount']:.8f} @ {pos['avg_buy_price']:,.0f}원 (그룹: {pos['group_id']})")
    print()

    # 검증
    print("=" * 60)
    print("검증 결과")
    print("=" * 60)

    checks = [
        ("KRW-BTC 업데이트", pm.has_position("KRW-BTC") and pm.get_position("KRW-BTC")["avg_buy_price"] == 95000000),
        ("KRW-ETH 생성", pm.has_position("KRW-ETH")),
        ("KRW-ADA 삭제", not pm.has_position("KRW-ADA")),
        ("KRW-SOL 스킵", not pm.has_position("KRW-SOL")),
    ]

    for check_name, passed in checks:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"   {status}: {check_name}")

    print()

    # 상세 검증
    if pm.has_position("KRW-BTC"):
        btc_pos = pm.get_position("KRW-BTC")
        print(f"📍 KRW-BTC 상세:")
        print(f"   - 평균가: {btc_pos['avg_buy_price']:,.0f}원 (예상: 95,000,000원)")
        print(f"   - 수량: {btc_pos['total_amount']:.8f}")
        print(f"   - 투자금: {btc_pos['total_invested_krw']:,.0f}원")
        print()

    if pm.has_position("KRW-ETH"):
        eth_pos = pm.get_position("KRW-ETH")
        print(f"📍 KRW-ETH 상세:")
        print(f"   - 그룹: {eth_pos['group_id']}")
        print(f"   - 평균가: {eth_pos['avg_buy_price']:,.0f}원")
        print(f"   - 수량: {eth_pos['total_amount']:.8f}")
        print()


def cleanup_test_files():
    """테스트 파일 정리"""
    test_files = [
        "data/positions_live.json",
        "data/positions_dryrun.json"
    ]

    for file_path in test_files:
        if os.path.exists(file_path):
            # 백업
            backup_path = file_path + ".backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(file_path, backup_path)
            print(f"✅ 백업 생성: {backup_path}")


def restore_test_files():
    """테스트 파일 복원"""
    test_files = [
        "data/positions_live.json",
        "data/positions_dryrun.json"
    ]

    for file_path in test_files:
        backup_path = file_path + ".backup"
        if os.path.exists(backup_path):
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(backup_path, file_path)
            print(f"✅ 복원 완료: {file_path}")


def main():
    """메인 테스트 실행"""
    print("\n")
    print("=" * 60)
    print("포지션 동기화 개선사항 테스트")
    print("=" * 60)
    print()

    # 기존 파일 백업
    cleanup_test_files()
    print()

    try:
        # 테스트 1: _find_group_for_coin()
        test_find_group_for_coin()

        # 테스트 2: sync_with_upbit() 전체
        test_sync_with_upbit()

        print("=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)
        print()

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 테스트 파일 복원
        print("\n테스트 파일 복원 중...")
        restore_test_files()
        print()


if __name__ == "__main__":
    main()
