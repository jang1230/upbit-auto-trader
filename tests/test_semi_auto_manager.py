"""
SemiAutoManager 테스트 스크립트

Mock 객체를 사용하여 Semi-Auto Manager의 동작을 검증합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from core.semi_auto_manager import SemiAutoManager, ManagedPosition
from core.position_detector import Position
from gui.dca_config import AdvancedDcaConfig, DcaLevelConfig
from datetime import datetime


class MockUpbitAPI:
    """테스트용 Mock Upbit API"""
    
    def __init__(self):
        self.accounts = [
            {
                'currency': 'KRW',
                'balance': '1000000.0',
                'locked': '0.0',
                'avg_buy_price': '0'
            }
        ]
        self.current_prices = {
            'KRW-BTC': 95000000.0,
            'KRW-ETH': 4500000.0,
            'KRW-XRP': 650.0
        }
    
    def get_accounts(self):
        return self.accounts
    
    def get_ticker(self, symbol: str):
        price = self.current_prices.get(symbol, 0)
        return {'trade_price': price}
    
    def add_manual_buy(self, currency: str, balance: float, avg_buy_price: float):
        """수동 매수 시뮬레이션"""
        self.accounts.append({
            'currency': currency,
            'balance': str(balance),
            'locked': '0.0',
            'avg_buy_price': str(avg_buy_price)
        })
    
    def update_balance(self, currency: str, new_balance: float):
        """잔고 업데이트"""
        for acc in self.accounts:
            if acc['currency'] == currency:
                acc['balance'] = str(new_balance)
    
    def remove_position(self, currency: str):
        """포지션 제거"""
        self.accounts = [acc for acc in self.accounts if acc['currency'] != currency]
    
    def set_price(self, symbol: str, price: float):
        """가격 설정"""
        self.current_prices[symbol] = price


class MockOrderManager:
    """테스트용 Mock Order Manager"""
    
    def __init__(self):
        self.orders = []
    
    async def place_market_buy(self, symbol: str, amount: float):
        """시장가 매수"""
        order = {
            'type': 'buy',
            'symbol': symbol,
            'amount': amount,
            'timestamp': datetime.now()
        }
        self.orders.append(order)
        print(f"  📝 주문 기록: 매수 {symbol} {amount:,.0f}원")
        return {'success': True, 'order': order}
    
    async def place_market_sell(self, symbol: str, quantity: float):
        """시장가 매도"""
        order = {
            'type': 'sell',
            'symbol': symbol,
            'quantity': quantity,
            'timestamp': datetime.now()
        }
        self.orders.append(order)
        print(f"  📝 주문 기록: 매도 {symbol} {quantity:.6f}")
        return {'success': True, 'order': order}


async def test_manual_buy_detection():
    """수동 매수 감지 테스트"""
    print("\n" + "="*80)
    print("TEST 1: 수동 매수 감지 및 관리 시작")
    print("="*80)
    
    # Mock 객체 생성
    mock_api = MockUpbitAPI()
    mock_order_manager = MockOrderManager()
    
    # DCA 설정
    dca_levels = [
        DcaLevelConfig(level=0, drop_pct=0.0, weight_pct=50.0, order_amount=500000),
        DcaLevelConfig(level=1, drop_pct=-10.0, weight_pct=25.0, order_amount=250000),
        DcaLevelConfig(level=2, drop_pct=-20.0, weight_pct=15.0, order_amount=150000),
        DcaLevelConfig(level=3, drop_pct=-30.0, weight_pct=10.0, order_amount=100000),
    ]
    
    dca_config = AdvancedDcaConfig(
        levels=dca_levels,
        take_profit_pct=10.0,
        stop_loss_pct=-15.0,
        total_capital=1000000,
        enabled=True
    )
    
    # SemiAutoManager 생성
    manager = SemiAutoManager(
        upbit_api=mock_api,
        order_manager=mock_order_manager,
        dca_config=dca_config,
        scan_interval=1
    )
    
    # 매니저 시작
    await manager.start()
    
    print("\n사용자가 BTC를 수동 매수...")
    mock_api.add_manual_buy('BTC', 0.01, 95000000.0)
    
    # 스캔 대기
    await asyncio.sleep(2)
    
    # 상태 확인
    status = manager.get_status()
    print(f"\n관리 포지션 수: {status['managed_count']}")
    for pos in status['positions']:
        print(f"  - {pos['symbol']}: {pos['balance']:.6f} @ {pos['avg_price']:,.0f}원")
    
    assert status['managed_count'] == 1, "BTC가 관리되어야 함"
    assert status['positions'][0]['symbol'] == 'KRW-BTC', "BTC여야 함"
    
    await manager.stop()
    print("\n✅ TEST 1 통과")
    
    return mock_api, mock_order_manager, manager


async def test_dca_trigger():
    """DCA 추가 매수 트리거 테스트"""
    print("\n" + "="*80)
    print("TEST 2: DCA 추가 매수 트리거")
    print("="*80)
    
    # Mock 객체 생성
    mock_api = MockUpbitAPI()
    mock_order_manager = MockOrderManager()
    
    # DCA 설정 (10% 하락마다 추가 매수)
    dca_levels = [
        DcaLevelConfig(level=0, drop_pct=0.0, weight_pct=50.0, order_amount=500000),
        DcaLevelConfig(level=1, drop_pct=-10.0, weight_pct=25.0, order_amount=250000),
        DcaLevelConfig(level=2, drop_pct=-20.0, weight_pct=15.0, order_amount=150000),
    ]
    
    dca_config = AdvancedDcaConfig(
        levels=dca_levels,
        take_profit_pct=10.0,
        stop_loss_pct=-15.0,
        total_capital=1000000,
        enabled=True
    )
    
    # SemiAutoManager 생성
    manager = SemiAutoManager(
        upbit_api=mock_api,
        order_manager=mock_order_manager,
        dca_config=dca_config,
        scan_interval=1
    )
    
    await manager.start()
    
    # 수동 매수
    print("\n사용자가 BTC를 95,000,000원에 수동 매수...")
    mock_api.add_manual_buy('BTC', 0.01, 95000000.0)
    mock_api.set_price('KRW-BTC', 95000000.0)
    
    await asyncio.sleep(2)
    
    # 가격 10% 하락 → DCA Level 1 트리거
    print("\n가격 10% 하락: 95,000,000 → 85,500,000원")
    mock_api.set_price('KRW-BTC', 85500000.0)
    
    await asyncio.sleep(2)
    
    # 주문 확인
    buy_orders = [o for o in mock_order_manager.orders if o['type'] == 'buy']
    print(f"\n실행된 매수 주문: {len(buy_orders)}개")
    
    assert len(buy_orders) >= 1, "DCA 추가 매수가 실행되어야 함"
    
    # 가격 20% 하락 → DCA Level 2 트리거
    print("\n가격 20% 하락: 95,000,000 → 76,000,000원")
    mock_api.set_price('KRW-BTC', 76000000.0)
    
    await asyncio.sleep(2)
    
    buy_orders = [o for o in mock_order_manager.orders if o['type'] == 'buy']
    print(f"\n실행된 매수 주문: {len(buy_orders)}개")
    
    assert len(buy_orders) >= 2, "DCA Level 2가 실행되어야 함"
    
    await manager.stop()
    print("\n✅ TEST 2 통과")


async def test_take_profit():
    """익절 트리거 테스트"""
    print("\n" + "="*80)
    print("TEST 3: 익절 트리거")
    print("="*80)
    
    # Mock 객체 생성
    mock_api = MockUpbitAPI()
    mock_order_manager = MockOrderManager()
    
    # DCA 설정 (10% 수익 시 익절)
    dca_levels = [
        DcaLevelConfig(level=0, drop_pct=0.0, weight_pct=50.0, order_amount=500000),
    ]
    
    dca_config = AdvancedDcaConfig(
        levels=dca_levels,
        take_profit_pct=10.0,
        stop_loss_pct=-15.0,
        total_capital=1000000,
        enabled=True
    )
    
    # SemiAutoManager 생성
    manager = SemiAutoManager(
        upbit_api=mock_api,
        order_manager=mock_order_manager,
        dca_config=dca_config,
        scan_interval=1
    )
    
    await manager.start()
    
    # 수동 매수
    print("\n사용자가 BTC를 95,000,000원에 수동 매수...")
    mock_api.add_manual_buy('BTC', 0.01, 95000000.0)
    mock_api.set_price('KRW-BTC', 95000000.0)
    
    await asyncio.sleep(2)
    
    # 가격 10% 상승 → 익절 트리거
    print("\n가격 10% 상승: 95,000,000 → 104,500,000원")
    mock_api.set_price('KRW-BTC', 104500000.0)
    
    await asyncio.sleep(2)
    
    # 매도 주문 확인
    sell_orders = [o for o in mock_order_manager.orders if o['type'] == 'sell']
    print(f"\n실행된 매도 주문: {len(sell_orders)}개")
    
    assert len(sell_orders) >= 1, "익절 매도가 실행되어야 함"
    
    # 포지션 제거 확인
    status = manager.get_status()
    print(f"\n관리 포지션 수: {status['managed_count']}")
    
    assert status['managed_count'] == 0, "익절 후 포지션이 제거되어야 함"
    
    await manager.stop()
    print("\n✅ TEST 3 통과")


async def test_stop_loss():
    """손절 트리거 테스트"""
    print("\n" + "="*80)
    print("TEST 4: 손절 트리거")
    print("="*80)
    
    # Mock 객체 생성
    mock_api = MockUpbitAPI()
    mock_order_manager = MockOrderManager()
    
    # DCA 설정 (-15% 손실 시 손절)
    dca_levels = [
        DcaLevelConfig(level=0, drop_pct=0.0, weight_pct=50.0, order_amount=500000),
    ]
    
    dca_config = AdvancedDcaConfig(
        levels=dca_levels,
        take_profit_pct=10.0,
        stop_loss_pct=-15.0,
        total_capital=1000000,
        enabled=True
    )
    
    # SemiAutoManager 생성
    manager = SemiAutoManager(
        upbit_api=mock_api,
        order_manager=mock_order_manager,
        dca_config=dca_config,
        scan_interval=1
    )
    
    await manager.start()
    
    # 수동 매수
    print("\n사용자가 BTC를 95,000,000원에 수동 매수...")
    mock_api.add_manual_buy('BTC', 0.01, 95000000.0)
    mock_api.set_price('KRW-BTC', 95000000.0)
    
    await asyncio.sleep(2)
    
    # 가격 15% 하락 → 손절 트리거
    print("\n가격 15% 하락: 95,000,000 → 80,750,000원")
    mock_api.set_price('KRW-BTC', 80750000.0)
    
    await asyncio.sleep(2)
    
    # 매도 주문 확인
    sell_orders = [o for o in mock_order_manager.orders if o['type'] == 'sell']
    print(f"\n실행된 매도 주문: {len(sell_orders)}개")
    
    assert len(sell_orders) >= 1, "손절 매도가 실행되어야 함"
    
    # 포지션 제거 확인
    status = manager.get_status()
    print(f"\n관리 포지션 수: {status['managed_count']}")
    
    assert status['managed_count'] == 0, "손절 후 포지션이 제거되어야 함"
    
    await manager.stop()
    print("\n✅ TEST 4 통과")


async def main():
    """전체 테스트 실행"""
    print("\n" + "="*80)
    print("SemiAutoManager 테스트 시작")
    print("="*80)
    
    try:
        await test_manual_buy_detection()
        await test_dca_trigger()
        await test_take_profit()
        await test_stop_loss()
        
        print("\n" + "="*80)
        print("✅ 모든 테스트 통과!")
        print("="*80)
        print("\nSemiAutoManager가 정상적으로 작동합니다:")
        print("  ✓ 수동 매수 감지 및 관리 시작")
        print("  ✓ DCA 추가 매수 자동 실행")
        print("  ✓ 익절 자동 실행")
        print("  ✓ 손절 자동 실행")
        
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
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
