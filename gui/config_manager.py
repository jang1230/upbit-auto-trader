"""
GUI Configuration Manager
.env 파일 및 설정 관리
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv, set_key, unset_key


class ConfigManager:
    """
    설정 관리 클래스

    .env 파일을 읽고 쓰는 기능 제공
    GUI에서 설정을 쉽게 변경할 수 있도록 지원
    """

    def __init__(self, env_path: Optional[Path] = None):
        """
        초기화

        Args:
            env_path: .env 파일 경로 (None이면 프로젝트 루트)
        """
        if env_path is None:
            # 프로젝트 루트 디렉토리
            project_root = Path(__file__).parent.parent
            env_path = project_root / '.env'

        self.env_path = env_path

        # .env 파일이 없으면 생성
        if not self.env_path.exists():
            self._create_default_env()

        # 환경 변수 로드
        load_dotenv(self.env_path)

    def _create_default_env(self):
        """기본 .env 파일 생성"""
        default_content = """# Upbit API Keys
UPBIT_ACCESS_KEY=your_access_key_here
UPBIT_SECRET_KEY=your_secret_key_here

# Trading Settings
MIN_ORDER_AMOUNT=5000
ORDER_TIMEOUT=30

# Coin Selection (거래할 코인 선택)
SELECTED_COINS=KRW-BTC,KRW-ETH,KRW-XRP

# Strategy Settings
# 전략 타입: filtered_bb (권장), bb, rsi, macd
STRATEGY_TYPE=filtered_bb
"""
        self.env_path.write_text(default_content, encoding='utf-8')

    # ========================================
    # Upbit API 설정
    # ========================================

    def get_upbit_access_key(self) -> str:
        """Upbit Access Key 조회"""
        return os.getenv('UPBIT_ACCESS_KEY', '')

    def get_upbit_secret_key(self) -> str:
        """Upbit Secret Key 조회"""
        return os.getenv('UPBIT_SECRET_KEY', '')

    def set_upbit_keys(self, access_key: str, secret_key: str) -> bool:
        """
        Upbit API 키 저장

        Args:
            access_key: Access Key
            secret_key: Secret Key

        Returns:
            성공 여부
        """
        try:
            set_key(str(self.env_path), 'UPBIT_ACCESS_KEY', access_key)
            set_key(str(self.env_path), 'UPBIT_SECRET_KEY', secret_key)

            # 환경 변수도 업데이트
            os.environ['UPBIT_ACCESS_KEY'] = access_key
            os.environ['UPBIT_SECRET_KEY'] = secret_key

            return True
        except Exception as e:
            print(f"API 키 저장 실패: {e}")
            return False

    # ========================================
    # Coin Selection 설정
    # ========================================

    def get_selected_coins(self) -> List[str]:
        """
        선택된 코인 리스트 조회

        Returns:
            List[str]: 선택된 코인 심볼 리스트 (예: ['KRW-BTC', 'KRW-ETH'])
        """
        coins_str = os.getenv('SELECTED_COINS', 'KRW-XRP,KRW-BTC,KRW-ETH')

        # 쉼표로 분리하여 리스트로 변환
        coins = [coin.strip() for coin in coins_str.split(',') if coin.strip()]

        # 빈 리스트면 기본값 반환
        if not coins:
            return ['KRW-XRP', 'KRW-BTC', 'KRW-ETH']

        return coins

    def set_selected_coins(self, coins: List[str]) -> bool:
        """
        선택된 코인 리스트 저장

        Args:
            coins: 코인 심볼 리스트 (예: ['KRW-BTC', 'KRW-ETH'])

        Returns:
            성공 여부
        """
        try:
            # 검증: 빈 리스트가 아니어야 함
            if not coins or not isinstance(coins, list):
                print("⚠️ 유효하지 않은 코인 리스트")
                return False

            # 리스트를 쉼표로 구분된 문자열로 변환
            coins_str = ','.join(coins)

            # .env 파일에 저장
            set_key(str(self.env_path), 'SELECTED_COINS', coins_str)

            # 환경 변수도 업데이트
            os.environ['SELECTED_COINS'] = coins_str

            return True
        except Exception as e:
            print(f"선택된 코인 저장 실패: {e}")
            return False

    # ========================================
    # Trading 설정
    # ========================================

    def get_min_order_amount(self) -> int:
        """최소 주문 금액 조회"""
        return int(os.getenv('MIN_ORDER_AMOUNT', '5000'))

    def get_order_timeout(self) -> int:
        """주문 타임아웃 조회"""
        return int(os.getenv('ORDER_TIMEOUT', '30'))

    def set_trading_config(self, min_order_amount: int, order_timeout: int) -> bool:
        """
        거래 설정 저장

        Args:
            min_order_amount: 최소 주문 금액
            order_timeout: 주문 타임아웃

        Returns:
            성공 여부
        """
        try:
            set_key(str(self.env_path), 'MIN_ORDER_AMOUNT', str(min_order_amount))
            set_key(str(self.env_path), 'ORDER_TIMEOUT', str(order_timeout))

            # 환경 변수도 업데이트
            os.environ['MIN_ORDER_AMOUNT'] = str(min_order_amount)
            os.environ['ORDER_TIMEOUT'] = str(order_timeout)

            return True
        except Exception as e:
            print(f"거래 설정 저장 실패: {e}")
            return False

    # ========================================
    # Strategy 설정
    # ========================================

    def get_strategy_type(self) -> str:
        """
        전략 타입 조회
        
        Returns:
            전략 타입 문자열
            - 'filtered_bb': 필터링된 볼린저 밴드 (권장)
            - 'bb': 기본 볼린저 밴드
            - 'rsi': RSI 전략
            - 'macd': MACD 전략
        """
        return os.getenv('STRATEGY_TYPE', 'filtered_bb')
    
    def set_strategy_type(self, strategy_type: str) -> bool:
        """
        전략 타입 저장
        
        Args:
            strategy_type: 전략 타입
        
        Returns:
            성공 여부
        """
        try:
            valid_strategies = ['filtered_bb', 'bb', 'rsi', 'macd']
            if strategy_type not in valid_strategies:
                print(f"⚠️ 유효하지 않은 전략 타입: {strategy_type}")
                return False
            
            set_key(str(self.env_path), 'STRATEGY_TYPE', strategy_type)
            os.environ['STRATEGY_TYPE'] = strategy_type
            
            return True
        except Exception as e:
            print(f"전략 타입 저장 실패: {e}")
            return False
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """
        전략 설정 조회 (코인별 자동 파라미터 적용)
        
        Returns:
            전략 설정 딕셔너리
        """
        strategy_type = self.get_strategy_type()
        
        config = {
            'type': strategy_type,
            'auto_optimize': True,  # 코인별 자동 최적화
        }
        
        # 전략별 기본 파라미터
        if strategy_type == 'filtered_bb':
            config.update({
                'bb_period': 20,
                'ma_period': 240,
                'atr_period': 14,
                # 코인별 파라미터는 FilteredBollingerBandsStrategy.create_for_coin()에서 자동 적용
            })
        elif strategy_type == 'bb':
            config.update({
                'period': 20,
                'std_dev': 2.0
            })
        elif strategy_type == 'rsi':
            config.update({
                'period': 14,
                'oversold': 30,
                'overbought': 70
            })
        elif strategy_type == 'macd':
            config.update({
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9
            })
        
        return config

    # ========================================
    # 전체 설정
    # ========================================

    def get_all_config(self) -> Dict[str, Any]:
        """
        전체 설정 조회

        Returns:
            설정 딕셔너리
        """
        return {
            'upbit': {
                'access_key': self.get_upbit_access_key(),
                'secret_key': self.get_upbit_secret_key()
            },
            'trading': {
                'min_order_amount': self.get_min_order_amount(),
                'order_timeout': self.get_order_timeout()
            },
            'coin_selection': {
                'selected_coins': self.get_selected_coins()
            },
            'strategy': self.get_strategy_config()
        }

    def validate_upbit_keys(self) -> bool:
        """
        Upbit API 키 유효성 검사 (실제 API 연결 테스트)

        Returns:
            유효 여부
        """
        access_key = self.get_upbit_access_key()
        secret_key = self.get_upbit_secret_key()

        # 1. 기본값이 아닌지 확인
        if access_key == 'your_access_key_here' or not access_key:
            return False

        if secret_key == 'your_secret_key_here' or not secret_key:
            return False

        # 2. 길이 확인 (Upbit API 키 형식)
        if len(access_key) < 20 or len(secret_key) < 20:
            return False

        # 3. 🔧 실제 API 연결 테스트 (가장 중요!)
        try:
            from core.upbit_api import UpbitAPI

            api = UpbitAPI(access_key, secret_key)
            accounts = api.get_accounts()  # 실제 API 호출

            # 계좌 조회 성공 → 유효한 키
            if accounts and isinstance(accounts, list):
                return True
            else:
                return False

        except Exception as e:
            # API 호출 실패 → 잘못된 키
            print(f"⚠️ API 키 검증 실패: {e}")
            return False

    def reload(self):
        """환경 변수 다시 로드"""
        load_dotenv(self.env_path, override=True)
