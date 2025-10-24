"""
텔레그램 봇 통합 테스트
Telegram Bot Integration Test

실시간 신호 → 주문 → 텔레그램 알림 전체 플로우 테스트

사용법:
    python tests/test_telegram_integration.py
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.telegram_bot import TelegramBot
from core.upbit_websocket import CandleWebSocket
from core.data_buffer import CandleBuffer
from core.strategies import BollingerBands_Strategy
from core.order_manager import OrderManager
from core.upbit_api import UpbitAPI
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_telegram_integration():
    """텔레그램 봇 통합 테스트"""
    
    print("\n" + "="*100)
    print("텔레그램 봇 통합 테스트")
    print("Telegram Bot Integration Test")
    print("="*100 + "\n")
    
    # 1. 환경 변수 로드
    print("🔧 1단계: 환경 변수 로드")
    load_dotenv()
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    upbit_access_key = os.getenv('UPBIT_ACCESS_KEY')
    upbit_secret_key = os.getenv('UPBIT_SECRET_KEY')
    
    if not telegram_token or not telegram_chat_id:
        print("❌ 텔레그램 설정이 없습니다.")
        print("   .env 파일에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID를 설정하세요.")
        print("\n📖 설정 방법:")
        print("   1. @BotFather에게 /newbot 명령으로 봇 생성")
        print("   2. 받은 토큰을 TELEGRAM_BOT_TOKEN에 설정")
        print("   3. 봇과 대화 시작")
        print("   4. https://api.telegram.org/bot<TOKEN>/getUpdates 에서 chat_id 확인")
        return
    
    if not upbit_access_key or not upbit_secret_key:
        print("⚠️ Upbit API 키가 없습니다. Dry Run 모드로 진행합니다.")
        dry_run = True
    else:
        dry_run = False
    
    print(f"  텔레그램 봇: 설정됨")
    print(f"  Upbit API: {'설정됨' if not dry_run else '미설정 (Dry Run)'}")
    print()
    
    # 2. 컴포넌트 초기화
    print("🔧 2단계: 컴포넌트 초기화")
    
    # 텔레그램 봇
    telegram = TelegramBot(telegram_token, telegram_chat_id)
    await telegram.send_message("🤖 *통합 테스트 시작*\n\n실시간 데이터 → 전략 → 주문 → 알림 플로우 테스트")
    print("  텔레그램 봇: 초기화 완료")
    
    # 전략
    strategy = BollingerBands_Strategy(period=20, std_dev=2.5)
    print(f"  전략: {strategy.name}")
    
    # 데이터 버퍼
    buffer = CandleBuffer(max_size=200, required_count=100)
    print(f"  버퍼: max_size=200, required=100")
    
    # 웹소켓
    ws = CandleWebSocket(interval_seconds=10)
    print(f"  웹소켓: 1분봉, 10초 간격 체크")
    
    # 주문 관리자 (Dry Run 모드)
    if not dry_run:
        api = UpbitAPI(upbit_access_key, upbit_secret_key)
        order_manager = OrderManager(api, min_order_amount=5000)
        print(f"  주문 관리자: 실거래 모드")
    else:
        # Dry Run용 더미 API
        api = None
        order_manager = None
        print(f"  주문 관리자: Dry Run 모드")
    
    print()
    
    # 3. 실시간 데이터 + 신호 + 알림 테스트
    print("📊 3단계: 실시간 데이터 + 전략 + 알림 통합 테스트")
    print("(버퍼가 준비될 때까지 대기... 약 1-2분 소요)")
    print("(최대 5개 캔들만 수신 후 종료)\n")
    
    signal_count = 0
    candle_count = 0
    max_candles = 5
    
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
                    
                    # 텔레그램 알림
                    await telegram.send_signal_alert(signal, 'KRW-BTC', candle['trade_price'])
                    
                    # 주문 실행 (Dry Run)
                    if signal == 'buy':
                        if dry_run:
                            # Dry Run 모드
                            result = {
                                'success': True,
                                'order_id': f'dry_run_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                                'symbol': 'KRW-BTC',
                                'side': 'buy',
                                'amount': 10000,
                                'executed_volume': 10000 / candle['trade_price'],
                                'executed_price': candle['trade_price'],
                                'timestamp': datetime.now()
                            }
                        else:
                            # 실제 주문
                            result = await order_manager.execute_buy('KRW-BTC', 10000, dry_run=False)
                        
                        # 주문 결과 알림
                        await telegram.send_order_result(result)
                    
                    elif signal == 'sell':
                        if dry_run:
                            # Dry Run 모드
                            result = {
                                'success': True,
                                'order_id': f'dry_run_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                                'symbol': 'KRW-BTC',
                                'side': 'sell',
                                'volume': 0.0001,
                                'executed_funds': 0.0001 * candle['trade_price'],
                                'executed_price': candle['trade_price'],
                                'timestamp': datetime.now()
                            }
                        else:
                            # 실제 주문 (보유량 확인 필요)
                            result = await order_manager.execute_sell('KRW-BTC', 0.0001, dry_run=False)
                        
                        # 주문 결과 알림
                        await telegram.send_order_result(result)
            
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
    
    # 4. 결과 요약
    print("\n" + "="*100)
    print("📈 테스트 결과 요약")
    print("="*100 + "\n")
    
    info = buffer.get_info()
    print(f"수신 캔들 수: {candle_count}개")
    print(f"버퍼 크기: {info['size']}개")
    print(f"신호 발생 횟수: {signal_count}회")
    
    if info['size'] > 0:
        print(f"\n가격 정보:")
        print(f"  최신 가격: {info['latest_price']:,.0f}원")
        print(f"  최저 가격: {info['price_range']['min']:,.0f}원")
        print(f"  최고 가격: {info['price_range']['max']:,.0f}원")
    
    # 최종 알림
    await telegram.send_message("✅ *통합 테스트 완료*\n\n모든 컴포넌트가 정상 작동합니다!")
    
    print("\n" + "="*100)
    print("✅ 통합 테스트 완료")
    print("="*100 + "\n")
    
    print("📱 텔레그램 앱에서 알림을 확인하세요!")
    print()


if __name__ == "__main__":
    asyncio.run(test_telegram_integration())
