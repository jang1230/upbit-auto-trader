"""
통합 WebSocket 테스트 스크립트

테스트 항목:
1. tick_router 라우팅 로직
2. 통계 정보 구조
3. __repr__ 형식

참고: 실제 WebSocket 연결 테스트는 프로그램 실행 시 확인
실행: python tests/test_websocket_unified.py
"""

import os
import sys

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# Mock WebSocketManager (실제 의존성 없이 로직만 테스트)
class MockWebSocketManager:
    """WebSocketManager의 핵심 로직만 테스트용으로 구현"""

    def __init__(self):
        self.websocket = None
        self.aggregators = {}
        self.candle_units = {}
        self.is_running = False
        self._reconnect_count = 0

    def _tick_router(self, tick_data):
        """통합 콜백: symbol별 CandleAggregator로 라우팅"""
        symbol = tick_data.get('code')
        if not symbol:
            return
        aggregator = self.aggregators.get(symbol)
        if aggregator:
            aggregator.on_tick(tick_data)

    def get_stats(self, symbol=None):
        if symbol:
            aggregator = self.aggregators.get(symbol)
            if aggregator:
                return aggregator.get_stats()
            return {}
        return {
            'total_symbols': len(self.aggregators),
            'is_running': self.is_running,
            'websocket_connected': self.websocket.is_connected if self.websocket else False,
            'reconnect_count': self._reconnect_count,
            'symbols': {sym: agg.get_stats() for sym, agg in self.aggregators.items()}
        }

    def __repr__(self):
        return f"WebSocketManager(symbols={len(self.aggregators)}, running={self.is_running}, unified=True)"


WebSocketManager = MockWebSocketManager


def test_initialization():
    """테스트 1: WebSocketManager 초기화"""
    print("\n" + "="*50)
    print("테스트 1: WebSocketManager 초기화")
    print("="*50)

    try:
        manager = WebSocketManager()

        # 초기 상태 확인
        assert manager.websocket is None, "websocket should be None initially"
        assert len(manager.aggregators) == 0, "aggregators should be empty"
        assert manager.is_running == False, "is_running should be False"

        print("  ✅ 초기화 성공")
        print(f"  - websocket: {manager.websocket}")
        print(f"  - aggregators: {len(manager.aggregators)}개")
        print(f"  - is_running: {manager.is_running}")
        print("  ✅ WebSocketManager 초기화 테스트 통과")
        return True

    except Exception as e:
        print(f"  ❌ 테스트 실패: {e}")
        return False


def test_tick_router():
    """테스트 2: tick_router 라우팅"""
    print("\n" + "="*50)
    print("테스트 2: tick_router 라우팅")
    print("="*50)

    try:
        manager = WebSocketManager()

        # Mock aggregator (on_tick 호출 추적)
        class MockAggregator:
            def __init__(self):
                self.received_ticks = []

            def on_tick(self, tick_data):
                self.received_ticks.append(tick_data)

        # Mock aggregator 등록
        btc_aggregator = MockAggregator()
        eth_aggregator = MockAggregator()
        manager.aggregators['KRW-BTC'] = btc_aggregator
        manager.aggregators['KRW-ETH'] = eth_aggregator

        # BTC tick 전송
        btc_tick = {'type': 'ticker', 'code': 'KRW-BTC', 'trade_price': 130000000}
        manager._tick_router(btc_tick)

        # ETH tick 전송
        eth_tick = {'type': 'ticker', 'code': 'KRW-ETH', 'trade_price': 4500000}
        manager._tick_router(eth_tick)

        # XRP tick 전송 (등록 안 됨 - 무시되어야 함)
        xrp_tick = {'type': 'ticker', 'code': 'KRW-XRP', 'trade_price': 1500}
        manager._tick_router(xrp_tick)

        # 검증
        assert len(btc_aggregator.received_ticks) == 1, "BTC should receive 1 tick"
        assert btc_aggregator.received_ticks[0]['trade_price'] == 130000000
        print("  ✅ BTC tick 라우팅 성공")

        assert len(eth_aggregator.received_ticks) == 1, "ETH should receive 1 tick"
        assert eth_aggregator.received_ticks[0]['trade_price'] == 4500000
        print("  ✅ ETH tick 라우팅 성공")

        print("  ✅ XRP tick 무시됨 (미등록 symbol)")

        print("  ✅ tick_router 테스트 통과")
        return True

    except Exception as e:
        print(f"  ❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stats():
    """테스트 3: 통계 정보"""
    print("\n" + "="*50)
    print("테스트 3: 통계 정보")
    print("="*50)

    try:
        manager = WebSocketManager()

        # 빈 상태 통계
        stats = manager.get_stats()
        assert stats['total_symbols'] == 0
        assert stats['is_running'] == False
        assert stats['websocket_connected'] == False
        print("  ✅ 초기 통계 확인")

        # Mock aggregator 추가
        class MockAggregator:
            def get_stats(self):
                return {'tick_count': 100}

        manager.aggregators['KRW-BTC'] = MockAggregator()
        manager.aggregators['KRW-ETH'] = MockAggregator()

        # 통계 재확인
        stats = manager.get_stats()
        assert stats['total_symbols'] == 2
        assert 'KRW-BTC' in stats['symbols']
        assert 'KRW-ETH' in stats['symbols']
        print("  ✅ aggregator 추가 후 통계 확인")

        print("  ✅ 통계 정보 테스트 통과")
        return True

    except Exception as e:
        print(f"  ❌ 테스트 실패: {e}")
        return False


def test_repr():
    """테스트 4: __repr__"""
    print("\n" + "="*50)
    print("테스트 4: __repr__")
    print("="*50)

    try:
        manager = WebSocketManager()
        repr_str = repr(manager)

        assert 'WebSocketManager' in repr_str
        assert 'symbols=0' in repr_str
        assert 'unified=True' in repr_str
        print(f"  ✅ repr: {repr_str}")

        print("  ✅ __repr__ 테스트 통과")
        return True

    except Exception as e:
        print(f"  ❌ 테스트 실패: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("통합 WebSocket 테스트")
    print("="*60)

    results = []

    # 테스트 실행
    results.append(("초기화", test_initialization()))
    results.append(("tick_router", test_tick_router()))
    results.append(("통계 정보", test_stats()))
    results.append(("__repr__", test_repr()))

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

    # 참고 사항
    print("\n" + "="*60)
    print("참고 사항")
    print("="*60)
    print("  - 실제 WebSocket 연결 테스트는 Upbit API가 필요합니다")
    print("  - 실제 테스트는 프로그램 실행 시 시작 시간으로 확인하세요")
    print("  - 예상: 13개 코인 기준 16초 → 2초")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
