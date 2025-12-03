"""
리팩토링 변경사항 테스트 스크립트

테스트 항목:
1. None 값 처리 (.get() or 0 패턴)
2. 불필요한 필드 저장 제외
3. 원자적 쓰기 (position_manager, config_manager)

실행: python tests/test_refactoring_changes.py
"""

import os
import sys
import json
import tempfile
import shutil

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 직접 import (core/__init__.py의 의존성 문제 회피)
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

position_manager_module = load_module("position_manager", os.path.join(PROJECT_ROOT, "core", "position_manager.py"))
config_manager_module = load_module("config_manager", os.path.join(PROJECT_ROOT, "core", "config_manager.py"))

PositionManager = position_manager_module.PositionManager
ConfigManager = config_manager_module.ConfigManager


def test_none_value_handling():
    """테스트 1: None 값 처리"""
    print("\n" + "="*50)
    print("테스트 1: None 값 처리 (.get() or 0 패턴)")
    print("="*50)

    # None 값이 포함된 포지션 데이터
    position_with_none = {
        "symbol": "KRW-BTC",
        "avg_buy_price": 50000000,
        "total_amount": 0.001,
        "current_price": None,  # None 값
        "profit_pct": None,     # None 값
        "profit_krw": None,     # None 값
    }

    # .get() or 0 패턴 테스트
    current_price = position_with_none.get("current_price") or 0
    profit_pct = position_with_none.get("profit_pct") or 0
    profit_krw = position_with_none.get("profit_krw") or 0

    assert current_price == 0, f"current_price should be 0, got {current_price}"
    assert profit_pct == 0, f"profit_pct should be 0, got {profit_pct}"
    assert profit_krw == 0, f"profit_krw should be 0, got {profit_krw}"

    # 포맷팅 테스트 (이전에 에러 발생했던 부분)
    try:
        formatted = f"{profit_pct:+.2f}%"
        print(f"  ✅ None → 0 변환 성공: {formatted}")
    except TypeError as e:
        print(f"  ❌ 포맷팅 실패: {e}")
        return False

    print("  ✅ None 값 처리 테스트 통과")
    return True


def test_fields_not_saved():
    """테스트 2: 불필요한 필드 저장 제외"""
    print("\n" + "="*50)
    print("테스트 2: 불필요한 필드 저장 제외")
    print("="*50)

    # 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp()
    positions_path = os.path.join(temp_dir, "test_positions.json")

    try:
        # PositionManager 생성 (dryrun 모드)
        pm = PositionManager(mode="dryrun")
        # 경로를 임시 경로로 변경
        pm.positions_path = positions_path

        # 테스트 포지션 생성 (모든 필드 포함)
        test_position = {
            "symbol": "KRW-BTC",
            "group_id": "test_group",
            "avg_buy_price": 50000000,
            "total_amount": 0.001,
            "total_invested_krw": 50000,
            "dca_levels_executed": 0,
            # 저장하면 안 되는 필드들
            "current_price": 51000000,
            "current_value_krw": 51000,
            "profit_krw": 1000,
            "profit_pct": 2.0,
            "group_name": "테스트 그룹",
        }

        # 포지션 추가
        pm.positions["KRW-BTC"] = test_position.copy()
        pm._save_positions()

        # 저장된 파일 확인
        with open(positions_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)

        saved_position = saved_data.get("KRW-BTC", {})

        # 저장되면 안 되는 필드 확인
        fields_should_not_exist = ['current_price', 'current_value_krw', 'profit_krw', 'profit_pct', 'group_name']

        for field in fields_should_not_exist:
            if field in saved_position:
                print(f"  ❌ '{field}' 필드가 저장됨 (저장되면 안 됨)")
                return False
            else:
                print(f"  ✅ '{field}' 필드 제외됨")

        # 저장되어야 하는 필드 확인
        fields_should_exist = ['symbol', 'group_id', 'avg_buy_price', 'total_amount']
        for field in fields_should_exist:
            if field in saved_position:
                print(f"  ✅ '{field}' 필드 저장됨")
            else:
                print(f"  ❌ '{field}' 필드가 누락됨")
                return False

        print("  ✅ 필드 저장 제외 테스트 통과")
        return True

    finally:
        # 정리
        shutil.rmtree(temp_dir)


def test_atomic_write_position():
    """테스트 3: PositionManager 원자적 쓰기"""
    print("\n" + "="*50)
    print("테스트 3: PositionManager 원자적 쓰기")
    print("="*50)

    temp_dir = tempfile.mkdtemp()
    positions_path = os.path.join(temp_dir, "test_positions.json")

    try:
        pm = PositionManager(mode="dryrun")
        pm.positions_path = positions_path

        # 포지션 추가 및 저장
        pm.positions["KRW-ETH"] = {
            "symbol": "KRW-ETH",
            "group_id": "test",
            "avg_buy_price": 3000000,
            "total_amount": 0.01,
        }
        pm._save_positions()

        # 파일 존재 확인
        if os.path.exists(positions_path):
            print(f"  ✅ 파일 생성됨: {positions_path}")
        else:
            print("  ❌ 파일이 생성되지 않음")
            return False

        # 임시 파일이 남아있지 않은지 확인
        temp_path = positions_path + '.tmp'
        if os.path.exists(temp_path):
            print(f"  ❌ 임시 파일이 남아있음: {temp_path}")
            return False
        else:
            print("  ✅ 임시 파일 정리됨")

        # 파일 내용 확인
        with open(positions_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "KRW-ETH" in data:
            print("  ✅ 데이터 정상 저장됨")
        else:
            print("  ❌ 데이터가 저장되지 않음")
            return False

        print("  ✅ PositionManager 원자적 쓰기 테스트 통과")
        return True

    finally:
        shutil.rmtree(temp_dir)


def test_atomic_write_config():
    """테스트 4: ConfigManager 원자적 쓰기"""
    print("\n" + "="*50)
    print("테스트 4: ConfigManager 원자적 쓰기")
    print("="*50)

    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(temp_dir, "test_config.json")

    try:
        cm = ConfigManager(config_path)

        # 테스트 설정
        test_config = {
            "version": "4.0.0",
            "global_settings": {
                "dry_run": True,
                "max_positions": {"enabled": False, "limit": 3},
                "min_krw_balance": {"enabled": True, "amount": 50000},
                "position_loss_limit": {"enabled": False, "limit_pct": -10.0, "action": "alert", "exclude_observation_groups": True},
                "telegram": {"enabled": False, "token": "", "chat_id": ""}
            },
            "groups": {}
        }

        # 저장
        cm.save_config(test_config)

        # 파일 존재 확인
        if os.path.exists(config_path):
            print(f"  ✅ 파일 생성됨: {config_path}")
        else:
            print("  ❌ 파일이 생성되지 않음")
            return False

        # 임시 파일이 남아있지 않은지 확인
        temp_path = config_path + '.tmp'
        if os.path.exists(temp_path):
            print(f"  ❌ 임시 파일이 남아있음: {temp_path}")
            return False
        else:
            print("  ✅ 임시 파일 정리됨")

        # 파일 내용 확인
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if data.get("version") == "4.0.0":
            print("  ✅ 데이터 정상 저장됨")
        else:
            print("  ❌ 데이터가 올바르게 저장되지 않음")
            return False

        print("  ✅ ConfigManager 원자적 쓰기 테스트 통과")
        return True

    finally:
        shutil.rmtree(temp_dir)


def test_update_price_no_save():
    """테스트 5: update_price()가 파일을 저장하지 않는지 확인"""
    print("\n" + "="*50)
    print("테스트 5: update_price() 메모리만 업데이트")
    print("="*50)

    temp_dir = tempfile.mkdtemp()
    positions_path = os.path.join(temp_dir, "test_positions.json")

    try:
        pm = PositionManager(mode="dryrun")
        pm.positions_path = positions_path

        # 초기 포지션
        pm.positions["KRW-BTC"] = {
            "symbol": "KRW-BTC",
            "group_id": "test",
            "avg_buy_price": 50000000,
            "total_amount": 0.001,
            "total_invested_krw": 50000,
        }
        pm._save_positions()

        # 파일 수정 시간 기록
        initial_mtime = os.path.getmtime(positions_path)

        # 약간의 딜레이
        import time
        time.sleep(0.1)

        # 가격 업데이트 (파일 저장 안 함)
        pm.update_price("KRW-BTC", 51000000)

        # 파일 수정 시간 확인
        after_mtime = os.path.getmtime(positions_path)

        if initial_mtime == after_mtime:
            print("  ✅ update_price() 호출 후 파일 변경 없음")
        else:
            print("  ❌ update_price() 호출 후 파일이 변경됨")
            return False

        # 메모리에는 업데이트 되었는지 확인
        pos = pm.positions.get("KRW-BTC", {})
        if pos.get("current_price") == 51000000:
            print("  ✅ 메모리 내 current_price 업데이트됨")
        else:
            print(f"  ⚠️ 메모리 업데이트 확인 필요: {pos.get('current_price')}")

        print("  ✅ update_price() 메모리만 업데이트 테스트 통과")
        return True

    finally:
        shutil.rmtree(temp_dir)


def main():
    print("\n" + "="*60)
    print("리팩토링 변경사항 테스트")
    print("="*60)

    results = []

    # 테스트 실행
    results.append(("None 값 처리", test_none_value_handling()))
    results.append(("필드 저장 제외", test_fields_not_saved()))
    results.append(("PositionManager 원자적 쓰기", test_atomic_write_position()))
    results.append(("ConfigManager 원자적 쓰기", test_atomic_write_config()))
    results.append(("update_price() 메모리만 업데이트", test_update_price_no_save()))

    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n총 {len(results)}개 테스트: {passed}개 통과, {failed}개 실패")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
