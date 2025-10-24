"""
페이퍼 트레이딩 테스트
Paper Trading Test

실전 배포 전 마지막 검증:
- 실시간 데이터 → 전략 → 리스크 관리 → 주문 → 알림
- 모든 컴포넌트 통합 테스트
- 최소 1주일 이상 실행 권장

사용법:
    python tests/test_paper_trading.py
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.trading_engine import TradingEngine
from dotenv import load_dotenv

# 로깅 설정 (UTF-8 인코딩으로 이모지 지원)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            f'paper_trading_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            encoding='utf-8'  # 🔧 UTF-8 인코딩
        ),
        logging.StreamHandler()
    ]
)

# StreamHandler도 UTF-8로 설정 (Windows CMD 이모지 지원)
import sys
if sys.platform == 'win32':
    # Windows에서 UTF-8 콘솔 출력 강제
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
logger = logging.getLogger(__name__)


async def paper_trading():
    """페이퍼 트레이딩 실행"""
    
    print("\n" + "="*100)
    print("📄 페이퍼 트레이딩 (Paper Trading)")
    print("="*100 + "\n")
    
    print("⚠️ 주의사항:")
    print("  1. Dry Run 모드로 실행 (실제 주문 없음)")
    print("  2. 실시간 시장 데이터 사용")
    print("  3. 최소 1주일 이상 실행 권장")
    print("  4. 성과를 모니터링하고 전략 검증")
    print("  5. Ctrl+C로 안전하게 중단 가능\n")
    
    # 환경 변수 로드
    load_dotenv()
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_token or not telegram_chat_id:
        print("⚠️ 텔레그램 설정이 없습니다. 알림 없이 진행합니다.")
        telegram_config = {}
    else:
        telegram_config = {
            'token': telegram_token,
            'chat_id': telegram_chat_id
        }
    
    # 트레이딩 엔진 설정
    config = {
        'symbol': 'KRW-BTC',
        
        # 전략: BB (20, 2.5) - Phase 2.5에서 검증된 최고 전략
        'strategy': {
            'period': 20,
            'std_dev': 2.5
        },
        
        # 리스크 관리: Phase 2.5 테스트에서 최적화된 설정
        'risk_manager': {
            'stop_loss_pct': 5.0,       # -5% 스톱로스
            'take_profit_pct': 10.0,    # +10% 타겟
            'max_daily_loss_pct': 10.0  # 일일 최대 손실 -10%
        },
        
        # 주문 금액 (Phase 2.5: 10,000원 단위)
        'order_amount': 10000,
        
        # Dry Run 모드 (실제 주문 없음)
        'dry_run': True,
        
        # 텔레그램 알림
        'telegram': telegram_config
    }
    
    print("\n📋 설정 정보:")
    print(f"  심볼: {config['symbol']}")
    print(f"  전략: BB ({config['strategy']['period']}, {config['strategy']['std_dev']})")
    print(f"  스톱로스: -{config['risk_manager']['stop_loss_pct']}%")
    print(f"  타겟: +{config['risk_manager']['take_profit_pct']}%")
    print(f"  주문 금액: {config['order_amount']:,}원")
    print(f"  모드: Dry Run (가상 매매)")
    print(f"  텔레그램: {'활성화' if telegram_config else '비활성화'}")
    print()
    
    # 트레이딩 엔진 시작
    engine = TradingEngine(config)
    
    print("="*100)
    print("🚀 페이퍼 트레이딩 시작")
    print("="*100)
    print()
    print("📊 실시간 데이터 수신 중...")
    print("🔔 신호 발생 시 자동으로 주문 실행 (Dry Run)")
    print("📱 텔레그램으로 알림 전송 (설정된 경우)")
    print()
    print("⏸️ 중단하려면 Ctrl+C를 누르세요")
    print("="*100)
    print()
    
    try:
        await engine.start()
    except KeyboardInterrupt:
        print("\n\n" + "="*100)
        print("⏸️ 페이퍼 트레이딩 중단")
        print("="*100 + "\n")
        
        await engine.stop()
        
        # 최종 상태 출력
        status = engine.get_status()
        
        print("\n" + "="*100)
        print("📊 최종 성과")
        print("="*100 + "\n")
        
        print(f"💰 자본:")
        print(f"  시작: {status['initial_capital']:,.0f}원")
        print(f"  최종: {status['current_capital']:,.0f}원")
        print(f"  수익: {status['net_profit']:+,.0f}원")
        print(f"  수익률: {status['return_pct']:+.2f}%")
        print()
        
        print(f"📈 거래 통계:")
        print(f"  총 거래: {status['total_trades']}회")
        print(f"  성공: {status['winning_trades']}회")
        print(f"  실패: {status['losing_trades']}회")
        print(f"  승률: {status['win_rate']:.1f}%")
        print()
        
        print(f"💸 손익:")
        print(f"  총 수익: +{status['total_profit']:,.0f}원")
        print(f"  총 손실: {status['total_loss']:,.0f}원")
        print(f"  순손익: {status['net_profit']:+,.0f}원")
        print()
        
        if status['position'] > 0:
            print(f"⚠️ 경고: 포지션이 남아있습니다!")
            print(f"  보유 수량: {status['position']:.8f}개")
            print(f"  진입 가격: {status['entry_price']:,.0f}원")
            print()
        
        print("="*100)
        print("✅ 페이퍼 트레이딩 완료")
        print("="*100)
        print()
        
        print("📝 다음 단계:")
        print("  1. 로그 파일 분석 (paper_trading_*.log)")
        print("  2. 성과 평가 (수익률, 승률, MDD 등)")
        print("  3. 최소 1주일 실행 후 실전 배포 결정")
        print("  4. 실전 배포 시 dry_run=False 설정")
        print()
    
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        await engine.stop()


if __name__ == "__main__":
    asyncio.run(paper_trading())
