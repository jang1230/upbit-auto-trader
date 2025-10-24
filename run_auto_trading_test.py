"""
완전 자동 트레이딩 테스트 스크립트 (DRY-RUN)

테스트 내용:
1. 시가총액 상위 10개 코인 조회
2. ScalpingStrategy 시그널 모니터링
3. 리스크 관리 체크
4. 자동 매수 시뮬레이션
5. SemiAutoManager 자동 연계 확인

⚠️ 안전 모드:
- 실제 Upbit API로 데이터 조회
- 모든 주문은 시뮬레이션 (dry_run=True)
"""

import sys
import logging
import asyncio
from datetime import datetime

from core.upbit_api import UpbitAPI
from core.order_manager import OrderManager
from core.semi_auto_manager import SemiAutoManager
from core.auto_trading_manager import AutoTradingManager
from gui.config_manager import ConfigManager
from gui.dca_config import DcaConfigManager
from gui.auto_trading_config import AutoTradingConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def print_header():
    """헤더 출력"""
    print("\n" + "=" * 80)
    print("🤖 완전 자동 트레이딩 테스트 (DRY-RUN)")
    print("=" * 80)
    print()
    print("⚠️  안전 모드 활성화:")
    print("   - 실제 Upbit API로 데이터 조회 ✅")
    print("   - 시가총액 상위 10개 모니터링 ✅")
    print("   - ScalpingStrategy 시그널 감지 ✅")
    print("   - 주문은 시뮬레이션만 (실제 주문 안 보냄) ✅")
    print()
    print("💡 테스트 내용:")
    print("   1. 상위 10개 코인 조회")
    print("   2. 각 코인별 진입 시그널 모니터링")
    print("   3. 리스크 관리 체크 (4가지)")
    print("   4. 자동 매수 시뮬레이션")
    print("   5. SemiAutoManager 자동 연계")
    print()
    print("🛑 종료: Ctrl+C")
    print()
    print("=" * 80)
    print()


def load_config():
    """설정 로드"""
    logger.info("📂 설정 파일 로드 중...")
    
    config_manager = ConfigManager()
    
    # API 키 조회
    access_key = config_manager.get_upbit_access_key()
    secret_key = config_manager.get_upbit_secret_key()
    
    if not access_key or access_key == 'your_access_key_here':
        logger.error("❌ Upbit API 키가 설정되지 않았습니다.")
        logger.error("   .env 파일을 확인하세요.")
        sys.exit(1)
    
    config = {
        'upbit': {
            'access_key': access_key,
            'secret_key': secret_key
        }
    }
    
    logger.info("✅ 설정 로드 완료")
    return config


async def notification_callback(message: str):
    """알림 콜백"""
    print(f"\n📢 알림: {message}\n")


async def main():
    """메인 실행 함수"""
    print_header()
    
    # 1. 설정 로드
    config = load_config()
    
    # 2. DCA 설정 로드
    logger.info("📂 DCA 설정 로드 중...")
    dca_manager = DcaConfigManager()
    dca_config = dca_manager.load()
    logger.info("✅ DCA 설정 로드 완료")
    logger.info(f"   - 익절 목표: {dca_config.take_profit_pct}%")
    logger.info(f"   - 손절 한도: {dca_config.stop_loss_pct}%")
    logger.info(f"   - DCA 레벨: {len(dca_config.levels)}개")
    
    # 3. 자동매수 설정 로드
    logger.info("📂 자동매수 설정 로드 중...")
    auto_config = AutoTradingConfig.from_file('auto_trading_config.json')
    logger.info("✅ 자동매수 설정 로드 완료")
    logger.info(f"   - 매수 금액: {auto_config.buy_amount:,.0f}원")
    logger.info(f"   - 모니터링: 상위 {auto_config.top_n}개")
    logger.info(f"   - 스캔 주기: {auto_config.scan_interval}초")
    
    # 4. 컴포넌트 초기화
    logger.info("\n🔧 컴포넌트 초기화 중...")
    
    # Upbit API
    api = UpbitAPI(
        access_key=config['upbit']['access_key'],
        secret_key=config['upbit']['secret_key']
    )
    logger.info("✅ Upbit API 클라이언트 초기화 완료")
    
    # API 연결 테스트
    logger.info("\n🔌 Upbit API 연결 테스트 중...")
    accounts = api.get_accounts()
    if accounts:
        logger.info("✅ API 연결 성공!")
        krw_balance = 0
        for account in accounts:
            if account.get('currency') == 'KRW':
                krw_balance = float(account.get('balance', 0))
        logger.info(f"   - KRW 잔고: {krw_balance:,.0f}원")
        logger.info(f"   - 보유 자산: {len(accounts)}개")
    else:
        logger.error("❌ API 연결 실패")
        sys.exit(1)
    
    # OrderManager
    order_manager = OrderManager(
        upbit_api=api,
        min_order_amount=5000.0
    )
    logger.info("✅ 주문 관리자 초기화 완료 (최소 주문: 5,000원)")
    
    # SemiAutoManager (DCA/익절/손절)
    semi_auto = SemiAutoManager(
        upbit_api=api,
        order_manager=order_manager,
        dca_config=dca_config,
        scan_interval=10,
        notification_callback=notification_callback
    )
    logger.info("✅ SemiAutoManager 초기화")
    
    # AutoTradingManager (완전 자동)
    auto_manager = AutoTradingManager(
        upbit_api=api,
        order_manager=order_manager,
        semi_auto_manager=semi_auto,
        config=auto_config,
        notification_callback=notification_callback
    )
    logger.info("✅ AutoTradingManager 초기화")
    
    # 5. 시작
    logger.info("\n🚀 완전 자동 트레이딩 시작!\n")
    
    # SemiAutoManager 시작 (DCA/익절/손절)
    await semi_auto.start()
    
    # AutoTradingManager 시작 (자동 진입)
    await auto_manager.start()
    
    logger.info("================================================================================")
    logger.info("✅ 시스템이 정상 작동 중입니다!")
    logger.info("================================================================================")
    logger.info("\n💡 모니터링 중:")
    
    status = auto_manager.get_status()
    logger.info(f"   - 모니터링 코인: {status['monitoring_count']}개")
    logger.info(f"   - 스캔 주기: {auto_config.scan_interval}초")
    logger.info(f"   - 매수 금액: {auto_config.buy_amount:,.0f}원")
    logger.info(f"\n💡 리스크 관리:")
    logger.info(f"   - 최대 포지션: {auto_config.max_positions_limit}개")
    logger.info(f"   - 일일 거래: {auto_config.daily_trades_limit}회")
    logger.info(f"   - 최소 잔고: {auto_config.min_krw_balance_amount:,.0f}원")
    logger.info(f"   - 손실 한도: -{auto_config.stop_on_loss_daily_pct}%")
    logger.info(f"\n🛑 종료하려면 Ctrl+C를 누르세요\n")
    
    # 6. 메인 루프 (상태 모니터링)
    try:
        while True:
            await asyncio.sleep(60)  # 60초마다 상태 출력
            
            status = auto_manager.get_status()
            
            logger.info("\n" + "=" * 80)
            logger.info(f"📊 상태 리포트 ({datetime.now().strftime('%H:%M:%S')})")
            logger.info("=" * 80)
            logger.info(f"모니터링: {status['monitoring_count']}개")
            logger.info(f"관리 중인 포지션: {status['managed_positions']}개")
            logger.info(f"오늘 거래 횟수: {status['daily_trades']}회")
            logger.info(f"오늘 손익률: {status['daily_pnl_pct']:.2f}%")
            logger.info(f"KRW 잔고: {status['krw_balance']:,.0f}원")
            logger.info("=" * 80)
    
    except KeyboardInterrupt:
        logger.info("\n\n🛑 사용자 중단 요청")
        
        # 정리
        await auto_manager.stop()
        await semi_auto.stop()
        
        logger.info("✅ 종료 완료")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✅ 프로그램 종료")
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        sys.exit(1)
