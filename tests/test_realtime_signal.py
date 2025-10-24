"""
실시간 신호 생성 테스트
Real-time Signal Generation Test

웹소켓 → 데이터 버퍼 → 전략 신호 생성 → 출력

사용법:
    python tests/test_realtime_signal.py
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.upbit_websocket import CandleWebSocket
from core.data_buffer import CandleBuffer
from core.strategies import BollingerBands_Strategy

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_realtime_signal():
    """실시간 신호 생성 테스트"""

    print("\n" + "="*100)
    print("실시간 신호 생성 테스트")
    print("Real-time Signal Generation Test")
    print("="*100 + "\n")

    # 1. 컴포넌트 초기화
    print("🔧 1단계: 컴포넌트 초기화")

    # 전략: BB (20, 2.5) - Phase 2.5에서 검증된 최고 전략
    strategy = BollingerBands_Strategy(period=20, std_dev=2.5)
    print(f"  전략: {strategy.name}")

    # 데이터 버퍼: 200개 캔들 저장, 100개 필요
    buffer = CandleBuffer(max_size=200, required_count=100)
    print(f"  버퍼: max_size=200, required=100")

    # 웹소켓: 1분봉 (테스트용으로 10초마다 체크)
    ws = CandleWebSocket(interval_seconds=10)
    print(f"  웹소켓: 1분봉, 10초 간격 체크\n")

    # 2. 실시간 데이터 수신 및 신호 생성
    print("📊 2단계: 실시간 데이터 수신 및 신호 생성")
    print("(버퍼가 준비될 때까지 대기... 약 1-2분 소요)\n")

    signal_count = 0
    candle_count = 0
    max_candles = 120  # 최대 120개 캔들 (약 2시간) 수신 후 종료

    try:
        async for candle in ws.subscribe_candle(['KRW-BTC'], unit="1"):
            candle_count += 1

            # 버퍼에 추가
            buffer.add_candle(candle)

            # 현재 상태 출력
            print(f"[{candle_count}] {candle['timestamp']} | 가격: {candle['trade_price']:,.0f}원 | 버퍼: {len(buffer)}/100")

            # 버퍼 준비 확인
            if buffer.is_ready():
                # 전략 신호 생성
                candles_df = buffer.get_candles(100)
                signal = strategy.generate_signal(candles_df)

                if signal:
                    signal_count += 1
                    print(f"\n🚨 신호 발생! #{signal_count}")
                    print(f"  신호: {signal.upper()}")
                    print(f"  시각: {datetime.now()}")
                    print(f"  가격: {candle['trade_price']:,.0f}원\n")

            # 최대 캔들 수 도달 시 종료
            if candle_count >= max_candles:
                print(f"\n✅ 최대 캔들 수 ({max_candles}개) 도달. 테스트 종료.")
                break

    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    # 3. 결과 요약
    print("\n" + "="*100)
    print("📈 테스트 결과 요약")
    print("="*100 + "\n")

    info = buffer.get_info()
    print(f"수신 캔들 수: {candle_count}개")
    print(f"버퍼 크기: {info['size']}개")
    print(f"신호 발생 횟수: {signal_count}회")
    print(f"신호 발생률: {signal_count / max(candle_count, 1) * 100:.2f}%")

    if info['size'] > 0:
        print(f"\n가격 정보:")
        print(f"  최신 가격: {info['latest_price']:,.0f}원")
        print(f"  최저 가격: {info['price_range']['min']:,.0f}원")
        print(f"  최고 가격: {info['price_range']['max']:,.0f}원")
        print(f"  평균 가격: {info['price_range']['avg']:,.0f}원")

    print("\n" + "="*100)
    print("✅ 테스트 완료")
    print("="*100 + "\n")

    print("다음 단계:")
    print("  1. 자동 주문 시스템 구현")
    print("  2. Telegram 알림 연동")
    print("  3. Trading Engine 통합")
    print()


async def quick_test():
    """빠른 테스트 (5개 캔들만)"""
    print("\n" + "="*100)
    print("빠른 실시간 연동 테스트 (5개 캔들)")
    print("="*100 + "\n")

    ws = CandleWebSocket(interval_seconds=5)
    buffer = CandleBuffer(max_size=10, required_count=5)

    print("📊 BTC 1분봉 수신 중...\n")

    count = 0
    async for candle in ws.subscribe_candle(['KRW-BTC'], unit="1"):
        count += 1
        buffer.add_candle(candle)

        print(f"[{count}] {candle['timestamp']} | 가격: {candle['trade_price']:,.0f}원 | 버퍼: {len(buffer)}")

        if count >= 5:
            break

    print(f"\n✅ {count}개 캔들 수신 완료")
    print(f"버퍼 준비 상태: {buffer.is_ready()}")
    print(f"최신 가격: {buffer.get_latest_price():,.0f}원\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # 빠른 테스트
        asyncio.run(quick_test())
    else:
        # 전체 테스트
        asyncio.run(test_realtime_signal())
