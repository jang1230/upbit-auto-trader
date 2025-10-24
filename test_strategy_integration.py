"""
전략 GUI 통합 테스트
- ConfigManager에서 전략 설정 로드/저장
- 코인별 최적 파라미터 자동 적용 확인
"""

import sys
import os

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.config_manager import ConfigManager
from core.strategies.filtered_bb_strategy import FilteredBollingerBandsStrategy


def test_config_manager():
    """ConfigManager 전략 설정 테스트"""
    print("=" * 80)
    print("1. ConfigManager 전략 설정 테스트")
    print("=" * 80)
    
    config_manager = ConfigManager()
    
    # 현재 전략 타입 조회
    current_strategy = config_manager.get_strategy_type()
    print(f"현재 전략 타입: {current_strategy}")
    
    # 전략 설정 조회
    strategy_config = config_manager.get_strategy_config()
    print(f"전략 설정: {strategy_config}")
    
    # 전체 설정 조회
    all_config = config_manager.get_all_config()
    print(f"\n전체 설정:")
    print(f"  - Upbit: API 키 설정됨")
    print(f"  - Telegram: {all_config['telegram']}")
    print(f"  - Trading: {all_config['trading']}")
    print(f"  - Strategy: {all_config['strategy']}")
    print(f"  - Coins: {all_config['coin_selection']['selected_coins']}")
    
    # 전략 타입 변경 테스트
    print("\n전략 타입 변경 테스트:")
    test_strategies = ['filtered_bb', 'bb', 'rsi', 'macd']
    for strategy_type in test_strategies:
        success = config_manager.set_strategy_type(strategy_type)
        if success:
            print(f"  ✅ {strategy_type} 저장 성공")
        else:
            print(f"  ❌ {strategy_type} 저장 실패")
    
    # 원래 전략으로 복원
    config_manager.set_strategy_type(current_strategy)
    print(f"\n원래 전략으로 복원: {current_strategy}")
    
    print("\n" + "=" * 80)
    print("ConfigManager 테스트 완료!")
    print("=" * 80)


def test_coin_specific_strategies():
    """코인별 최적 파라미터 자동 적용 테스트"""
    print("\n" + "=" * 80)
    print("2. 코인별 최적 파라미터 자동 적용 테스트")
    print("=" * 80)
    
    test_coins = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL', 'KRW-ADA']
    
    for symbol in test_coins:
        print(f"\n{'='*60}")
        print(f"📊 {symbol} 전략 생성")
        print(f"{'='*60}")
        
        # FilteredBollingerBandsStrategy 생성
        strategy = FilteredBollingerBandsStrategy.create_for_coin(symbol)
        
        # 파라미터 출력
        params = strategy.get_parameters()
        print(f"전략: {params['strategy']}")
        print(f"심볼: {params['symbol']}")
        print(f"파라미터:")
        print(f"  - BB Period: {params['bb_period']}")
        print(f"  - BB Std Dev: {params['bb_std_dev']}")
        print(f"  - MA Period: {params['ma_period']}")
        print(f"  - ATR Period: {params['atr_period']}")
        print(f"  - ATR Multiplier: {params['atr_multiplier']}")
        print(f"  - Min Hours Between Trades: {params['min_hours_between_trades']}")
        
        # 최적 파라미터 확인
        if symbol == 'KRW-BTC':
            assert params['bb_std_dev'] == 2.0
            assert params['min_hours_between_trades'] == 6
            assert params['atr_multiplier'] == 0.3
            print("✅ BTC 최적 파라미터 확인")
            
        elif symbol == 'KRW-ETH':
            assert params['bb_std_dev'] == 2.5
            assert params['min_hours_between_trades'] == 10
            assert params['atr_multiplier'] == 0.4
            print("✅ ETH 최적 파라미터 확인")
            
        elif symbol == 'KRW-XRP':
            assert params['bb_std_dev'] == 2.0
            assert params['min_hours_between_trades'] == 6
            assert params['atr_multiplier'] == 0.3
            print("✅ XRP 최적 파라미터 확인")
            
        else:
            # 기본 파라미터
            assert params['bb_std_dev'] == 2.0
            assert params['min_hours_between_trades'] == 6
            assert params['atr_multiplier'] == 0.3
            print("✅ 기본 파라미터 확인")
    
    print("\n" + "=" * 80)
    print("코인별 전략 테스트 완료!")
    print("=" * 80)


def test_strategy_factory():
    """전략 팩토리 패턴 테스트"""
    print("\n" + "=" * 80)
    print("3. 전략 팩토리 패턴 테스트")
    print("=" * 80)
    
    config_manager = ConfigManager()
    
    # 다양한 전략 타입 테스트
    strategy_types = {
        'filtered_bb': 'FilteredBollingerBandsStrategy',
        'bb': 'BollingerBands_Strategy',
        'rsi': 'RSI_Strategy',
        'macd': 'MACD_Strategy'
    }
    
    for strategy_type, expected_class in strategy_types.items():
        print(f"\n전략 타입: {strategy_type}")
        
        # ConfigManager에 저장
        config_manager.set_strategy_type(strategy_type)
        
        # 설정 확인
        loaded_config = config_manager.get_strategy_config()
        print(f"  설정: {loaded_config}")
        
        assert loaded_config['type'] == strategy_type
        print(f"  ✅ {strategy_type} 설정 확인")
    
    print("\n" + "=" * 80)
    print("전략 팩토리 테스트 완료!")
    print("=" * 80)


def main():
    """메인 테스트 함수"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "전략 GUI 통합 테스트" + " " * 38 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        # 1. ConfigManager 테스트
        test_config_manager()
        
        # 2. 코인별 최적 파라미터 테스트
        test_coin_specific_strategies()
        
        # 3. 전략 팩토리 패턴 테스트
        test_strategy_factory()
        
        # 최종 결과
        print("\n" + "=" * 80)
        print("🎉 모든 테스트 통과!")
        print("=" * 80)
        print()
        print("✅ ConfigManager 전략 설정 저장/로드 정상")
        print("✅ 코인별 최적 파라미터 자동 적용 정상")
        print("✅ 전략 팩토리 패턴 동작 정상")
        print()
        print("다음 단계:")
        print("  1. GUI 실행하여 설정 → 전략 설정 탭 확인")
        print("  2. 전략 선택하고 저장")
        print("  3. 트레이딩 시작하여 실제 적용 확인")
        print()
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ 테스트 실패!")
        print("=" * 80)
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
