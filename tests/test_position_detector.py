"""
PositionDetector 테스트 스크립트

실제 Upbit API를 사용하지 않고 mock 데이터로 테스트합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.position_detector import Position, PositionDetector
from datetime import datetime


class MockUpbitAPI:
    """테스트용 Mock Upbit API"""
    
    def __init__(self):
        # 시뮬레이션용 계좌 데이터
        self.accounts = [
            {
                'currency': 'KRW',
                'balance': '1000000.0',
                'locked': '0.0',
                'avg_buy_price': '0'
            },
            {
                'currency': 'BTC',
                'balance': '0.05',
                'locked': '0.0',
                'avg_buy_price': '95000000'
            },
            {
                'currency': 'ETH',
                'balance': '1.5',
                'locked': '0.0',
                'avg_buy_price': '4500000'
            }
        ]
    
    def get_accounts(self):
        """Mock 계좌 조회"""
        return self.accounts
    
    def add_position(self, currency: str, balance: float, avg_buy_price: float):
        """테스트용: 새로운 포지션 추가"""
        self.accounts.append({
            'currency': currency,
            'balance': str(balance),
            'locked': '0.0',
            'avg_buy_price': str(avg_buy_price)
        })
    
    def remove_position(self, currency: str):
        """테스트용: 포지션 제거 (청산)"""
        self.accounts = [acc for acc in self.accounts if acc['currency'] != currency]


def test_initial_scan():
    """초기 스캔 테스트"""
    print("\n" + "="*80)
    print("TEST 1: 초기 포지션 스캔")
    print("="*80)
    
    mock_api = MockUpbitAPI()
    detector = PositionDetector(mock_api)
    
    result = detector.scan_positions()
    
    print(f"\n관리 포지션: {len(result['managed'])}개")
    print(f"수동 포지션: {len(result['manual'])}개")
    print(f"새 수동 매수: {len(result['new_manual'])}개")
    
    print("\n수동 포지션 목록:")
    for pos in result['manual']:
        print(f"  - {pos}")
    
    assert len(result['managed']) == 0, "초기에는 관리 포지션이 없어야 함"
    assert len(result['manual']) == 2, "BTC, ETH 2개의 수동 포지션이 있어야 함"
    assert len(result['new_manual']) == 2, "모두 새로운 수동 매수여야 함"
    
    print("\n✅ TEST 1 통과")
    return detector, mock_api


def test_register_managed():
    """관리 포지션 등록 테스트"""
    print("\n" + "="*80)
    print("TEST 2: 관리 포지션 등록")
    print("="*80)
    
    detector, mock_api = test_initial_scan()
    
    # BTC를 관리 포지션으로 등록
    btc_position = detector.get_position('KRW-BTC')
    detector.register_managed_position('KRW-BTC', btc_position)
    
    print(f"\nBTC를 관리 포지션으로 등록")
    
    # 다시 스캔
    result = detector.scan_positions()
    
    print(f"\n관리 포지션: {len(result['managed'])}개")
    print(f"수동 포지션: {len(result['manual'])}개")
    print(f"새 수동 매수: {len(result['new_manual'])}개")
    
    print("\n관리 포지션 목록:")
    for pos in result['managed']:
        print(f"  - {pos}")
    
    print("\n수동 포지션 목록:")
    for pos in result['manual']:
        print(f"  - {pos}")
    
    assert len(result['managed']) == 1, "BTC 1개가 관리 포지션이어야 함"
    assert len(result['manual']) == 1, "ETH 1개만 수동 포지션이어야 함"
    assert len(result['new_manual']) == 0, "새 매수는 없어야 함"
    assert detector.is_managed('KRW-BTC'), "BTC는 관리 중이어야 함"
    assert not detector.is_managed('KRW-ETH'), "ETH는 관리 중이 아니어야 함"
    
    print("\n✅ TEST 2 통과")
    return detector, mock_api


def test_new_manual_buy():
    """새로운 수동 매수 감지 테스트"""
    print("\n" + "="*80)
    print("TEST 3: 새로운 수동 매수 감지")
    print("="*80)
    
    detector, mock_api = test_register_managed()
    
    # 사용자가 XRP를 수동 매수했다고 가정
    print("\n사용자가 Upbit에서 XRP를 수동 매수...")
    mock_api.add_position('XRP', 1000.0, 650.0)
    
    # 스캔
    result = detector.scan_positions()
    
    print(f"\n관리 포지션: {len(result['managed'])}개")
    print(f"수동 포지션: {len(result['manual'])}개")
    print(f"새 수동 매수: {len(result['new_manual'])}개")
    
    print("\n새로 감지된 수동 매수:")
    for pos in result['new_manual']:
        print(f"  🔔 {pos}")
    
    assert len(result['new_manual']) == 1, "XRP 1개가 새 수동 매수여야 함"
    assert result['new_manual'][0].symbol == 'KRW-XRP', "XRP여야 함"
    
    print("\n✅ TEST 3 통과")
    return detector, mock_api


def test_position_cleanup():
    """포지션 청산 테스트"""
    print("\n" + "="*80)
    print("TEST 4: 포지션 청산 처리")
    print("="*80)
    
    detector, mock_api = test_new_manual_buy()
    
    # ETH를 수동 매도했다고 가정
    print("\n사용자가 ETH를 전량 매도...")
    mock_api.remove_position('ETH')
    
    # 스캔
    result = detector.scan_positions()
    
    print(f"\n관리 포지션: {len(result['managed'])}개")
    print(f"수동 포지션: {len(result['manual'])}개")
    
    print("\n현재 수동 포지션:")
    for pos in result['manual']:
        print(f"  - {pos}")
    
    assert len(result['manual']) == 1, "XRP만 남아야 함"
    assert detector.get_position('KRW-ETH') is None, "ETH는 제거되어야 함"
    
    print("\n✅ TEST 4 통과")
    return detector, mock_api


def test_managed_position_update():
    """관리 포지션 업데이트 테스트"""
    print("\n" + "="*80)
    print("TEST 5: 관리 포지션 수량 업데이트")
    print("="*80)
    
    detector, mock_api = test_position_cleanup()
    
    # BTC 추가 매수 (DCA)
    print("\n프로그램이 BTC 추가 매수 (DCA)...")
    for acc in mock_api.accounts:
        if acc['currency'] == 'BTC':
            old_balance = float(acc['balance'])
            new_balance = old_balance + 0.01
            acc['balance'] = str(new_balance)
            print(f"BTC 수량: {old_balance:.4f} → {new_balance:.4f}")
    
    # 스캔
    result = detector.scan_positions()
    
    btc_pos = detector.get_position('KRW-BTC')
    print(f"\n업데이트된 BTC 포지션:")
    print(f"  {btc_pos}")
    print(f"  실제 balance 값: {btc_pos.balance}")
    print(f"  예상 값: 0.06")
    print(f"  차이: {abs(btc_pos.balance - 0.06)}")
    
    # float 비교는 근사값으로
    assert abs(btc_pos.balance - 0.06) < 0.0001, f"BTC 수량이 업데이트되어야 함 (실제: {btc_pos.balance})"
    
    print("\n✅ TEST 5 통과")


def main():
    """전체 테스트 실행"""
    print("\n" + "="*80)
    print("PositionDetector 테스트 시작")
    print("="*80)
    
    try:
        test_initial_scan()
        test_register_managed()
        test_new_manual_buy()
        test_position_cleanup()
        test_managed_position_update()
        
        print("\n" + "="*80)
        print("✅ 모든 테스트 통과!")
        print("="*80)
        print("\nPositionDetector가 정상적으로 작동합니다:")
        print("  ✓ 초기 포지션 스캔")
        print("  ✓ 관리 포지션 등록")
        print("  ✓ 새로운 수동 매수 감지")
        print("  ✓ 포지션 청산 처리")
        print("  ✓ 관리 포지션 수량 업데이트")
        
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 예상치 못한 에러: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
