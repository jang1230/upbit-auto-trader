"""
과거 데이터 순차 수집 스크립트
Sequential Historical Data Collection

2022-01-01 ~ 2024-10-19 과거 데이터를 코인별로 순차 수집
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backtest.safe_data_collector import SafeDataCollector

def main():
    """메인 실행 함수"""
    
    print("\n" + "="*80)
    print("📊 과거 데이터 순차 수집")
    print("="*80)
    print(f"기간: 2022-01-01 ~ 2024-10-19")
    print(f"코인: BTC, ETH, XRP")
    print(f"간격: 1분봉")
    print(f"예상 소요 시간: 약 12-15시간")
    print("="*80)
    
    # 사용자 확인
    response = input("\n계속 진행하시겠습니까? (y/n): ").strip().lower()
    if response != 'y':
        print("중단되었습니다.")
        return
    
    # 수집기 생성 (API 대기 시간 1초)
    collector = SafeDataCollector(delay_seconds=1)
    
    # 수집 설정
    start_date = '2022-01-01'
    end_date = '2024-10-19'
    coins = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
    
    total_start = time.time()
    
    # 코인별 순차 수집
    for i, symbol in enumerate(coins, 1):
        print(f"\n{'='*80}")
        print(f"📌 [{i}/3] {symbol} 수집 시작")
        print(f"{'='*80}\n")
        
        try:
            filepath = collector.collect_and_save(symbol, start_date, end_date)
            
            if filepath:
                print(f"\n✅ {symbol} 완료!")
                print(f"   저장 경로: {filepath}")
            else:
                print(f"\n❌ {symbol} 실패")
                
        except KeyboardInterrupt:
            print(f"\n\n⚠️ 사용자에 의해 중단됨")
            print(f"체크포인트가 저장되어 있어 나중에 이어서 수집할 수 있습니다.")
            return
        except Exception as e:
            print(f"\n❌ {symbol} 수집 중 오류: {e}")
            continue
        
        # 다음 코인 전 대기
        if i < len(coins):
            print(f"\n⏳ 다음 코인까지 5초 대기...")
            time.sleep(5)
    
    # 완료 통계
    total_time = time.time() - total_start
    
    print(f"\n{'='*80}")
    print("🎉 전체 수집 완료!")
    print(f"{'='*80}")
    print(f"총 소요 시간: {total_time/3600:.1f}시간 ({total_time/60:.0f}분)")
    print(f"완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
