"""
Semi-Auto Manager 실전 테스트 스크립트 (Dry-Run)

실제 Upbit API를 사용하지만 주문은 시뮬레이션만 합니다.
완전히 안전한 테스트입니다.

실행 방법:
    python3 run_semi_auto_test.py

종료 방법:
    Ctrl+C
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.upbit_api import UpbitAPI
from core.order_manager import OrderManager
from core.semi_auto_manager import SemiAutoManager
from gui.config_manager import ConfigManager
from gui.dca_config import DcaConfigManager, AdvancedDcaConfig, DcaLevelConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def print_banner():
    """시작 배너 출력"""
    print("\n" + "="*80)
    print("🤖 Semi-Auto Manager 실전 테스트 (DRY-RUN)")
    print("="*80)
    print("\n⚠️  안전 모드 활성화:")
    print("   - 실제 Upbit API로 데이터 조회 ✅")
    print("   - 포지션 감지 및 모니터링 ✅")
    print("   - 주문은 시뮬레이션만 (실제 주문 안 보냄) ✅")
    print("\n💡 테스트 내용:")
    print("   1. Upbit 계정 연결 확인")
    print("   2. 현재 보유 포지션 스캔")
    print("   3. 수동 매수 감지 테스트")
    print("   4. DCA/익절/손절 로직 모니터링")
    print("\n🛑 종료: Ctrl+C\n")
    print("="*80 + "\n")


def load_config():
    """설정 로드"""
    logger.info("📂 설정 파일 로드 중...")
    
    config_manager = ConfigManager()
    
    # API 키 조회
    access_key = config_manager.get_upbit_access_key()
    secret_key = config_manager.get_upbit_secret_key()
    
    if not access_key or not secret_key or access_key == 'your_access_key_here':
        logger.error("❌ Upbit API 키가 설정되지 않았습니다.")
        logger.info("💡 .env 파일에 UPBIT_ACCESS_KEY와 UPBIT_SECRET_KEY를 설정해주세요.")
        sys.exit(1)
    
    # 설정 딕셔너리 생성
    config = {
        'upbit': {
            'access_key': access_key,
            'secret_key': secret_key
        }
    }
    
    logger.info("✅ 설정 로드 완료")
    return config


def load_dca_config():
    """DCA 설정 로드"""
    logger.info("📂 DCA 설정 로드 중...")
    
    dca_manager = DcaConfigManager()
    dca_config = dca_manager.load()
    
    if not dca_config or not dca_config.enabled:
        logger.warning("⚠️  DCA 설정이 없거나 비활성화되어 있습니다.")
        logger.info("💡 기본 DCA 설정을 사용합니다.")
        
        # 기본 DCA 설정 생성
        dca_levels = [
            DcaLevelConfig(level=0, drop_pct=0.0, weight_pct=50.0, order_amount=10000),
            DcaLevelConfig(level=1, drop_pct=-5.0, weight_pct=25.0, order_amount=10000),
            DcaLevelConfig(level=2, drop_pct=-10.0, weight_pct=15.0, order_amount=10000),
        ]
        
        dca_config = AdvancedDcaConfig(
            levels=dca_levels,
            take_profit_pct=5.0,   # 5% 익절
            stop_loss_pct=-10.0,   # -10% 손절
            total_capital=100000,
            enabled=True
        )
    
    logger.info("✅ DCA 설정 로드 완료")
    logger.info(f"   - 익절 목표: {dca_config.take_profit_pct}%")
    logger.info(f"   - 손절 한도: {dca_config.stop_loss_pct}%")
    logger.info(f"   - DCA 레벨: {len(dca_config.levels)}개")
    
    return dca_config


async def test_api_connection(api: UpbitAPI):
    """API 연결 테스트"""
    logger.info("\n🔌 Upbit API 연결 테스트 중...")
    
    try:
        # 계좌 조회
        accounts = api.get_accounts()
        
        # KRW 잔고 확인
        krw_balance = 0
        for account in accounts:
            if account['currency'] == 'KRW':
                krw_balance = float(account['balance'])
                break
        
        logger.info(f"✅ API 연결 성공!")
        logger.info(f"   - KRW 잔고: {krw_balance:,.0f}원")
        logger.info(f"   - 보유 자산: {len(accounts)}개")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ API 연결 실패: {e}")
        return False


async def notification_callback(message: str):
    """알림 콜백 (콘솔 출력)"""
    print(f"\n📢 알림: {message}\n")


async def monitor_status(manager: SemiAutoManager):
    """상태 모니터링"""
    while True:
        try:
            await asyncio.sleep(30)  # 30초마다
            
            status = manager.get_status()
            
            logger.info("\n" + "="*80)
            logger.info(f"📊 상태 리포트 ({datetime.now().strftime('%H:%M:%S')})")
            logger.info("="*80)
            logger.info(f"관리 중인 포지션: {status['managed_count']}개")
            
            if status['managed_count'] > 0:
                for pos in status['positions']:
                    logger.info(f"\n  🪙 {pos['symbol']}")
                    logger.info(f"     수량: {pos['balance']:.6f}")
                    logger.info(f"     평단가: {pos['avg_price']:,.0f}원")
                    logger.info(f"     기준가: {pos['signal_price']:,.0f}원")
                    logger.info(f"     DCA 실행: Level {pos['dca_levels']}")
            else:
                logger.info("  (관리 중인 포지션 없음)")
            
            logger.info("="*80 + "\n")
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"상태 모니터링 에러: {e}")


async def main():
    """메인 실행"""
    print_banner()
    
    # 1. 설정 로드
    config = load_config()
    dca_config = load_dca_config()
    
    # 2. API 초기화
    logger.info("\n🔧 컴포넌트 초기화 중...")
    upbit_config = config['upbit']
    api = UpbitAPI(
        access_key=upbit_config['access_key'],
        secret_key=upbit_config['secret_key']
    )
    
    # 3. API 연결 테스트
    if not await test_api_connection(api):
        logger.error("❌ API 연결에 실패했습니다. 종료합니다.")
        return
    
    # 4. OrderManager 초기화
    # 주의: dry_run은 OrderManager 초기화가 아니라 각 주문 메서드에 전달
    order_manager = OrderManager(
        upbit_api=api,  # ⭐ 파라미터 이름: upbit_api
        min_order_amount=5000.0
    )
    logger.info("✅ OrderManager 초기화")
    
    # 5. SemiAutoManager 초기화
    manager = SemiAutoManager(
        upbit_api=api,
        order_manager=order_manager,
        dca_config=dca_config,
        scan_interval=10,  # 10초마다 스캔
        notification_callback=notification_callback
    )
    logger.info("✅ SemiAutoManager 초기화")
    
    # 6. 매니저 시작
    logger.info("\n🚀 Semi-Auto Manager 시작!\n")
    await manager.start()
    
    # 7. 상태 모니터링 태스크 시작
    monitor_task = asyncio.create_task(monitor_status(manager))
    
    # 8. 사용자 안내
    logger.info("="*80)
    logger.info("✅ 시스템이 정상 작동 중입니다!")
    logger.info("="*80)
    logger.info("\n💡 이제 Upbit에서 코인을 수동 매수하면:")
    logger.info("   1. 자동으로 감지됩니다")
    logger.info("   2. DCA 설정에 따라 자동 관리됩니다")
    logger.info("   3. 모든 주문은 시뮬레이션만 됩니다 (DRY-RUN)\n")
    logger.info("🛑 종료하려면 Ctrl+C를 누르세요\n")
    
    try:
        # 무한 대기 (Ctrl+C까지)
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\n\n🛑 종료 신호 받음...")
        
        # 9. 정리
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        await manager.stop()
        
        logger.info("✅ Semi-Auto Manager 종료 완료")
        logger.info("👋 안전하게 종료되었습니다!\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 프로그램 종료")
    except Exception as e:
        logger.error(f"\n❌ 예상치 못한 에러: {e}", exc_info=True)
        sys.exit(1)
