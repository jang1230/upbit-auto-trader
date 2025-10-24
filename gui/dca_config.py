"""
DCA Configuration Manager
고급 DCA 전략 설정 관리

5단계 DCA 레벨별 설정:
- 하락률 (Drop %)
- 매수 비중 (Weight %)
- 주문 금액 (Order Amount)

익절/손절 설정:
- Take Profit %
- Stop Loss %
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class DcaLevelConfig:
    """
    개별 DCA 레벨 설정

    Attributes:
        level: 레벨 번호 (1-5)
        drop_pct: 하락률 (%), 0 = 초기 진입
        weight_pct: 매수 비중 (%), 총합이 100% 초과 가능
        order_amount: 주문 금액 (원)
    """
    level: int
    drop_pct: float
    weight_pct: float
    order_amount: int

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DcaLevelConfig':
        """딕셔너리에서 생성"""
        return cls(**data)


@dataclass
class TakeProfitLevel:
    """
    익절 레벨 설정

    Attributes:
        level: 레벨 번호 (1, 2, 3...)
        profit_pct: 평균 단가 대비 수익률 (%)
        sell_ratio: 보유량 대비 매도 비율 (%), 0~100
    """
    level: int
    profit_pct: float
    sell_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TakeProfitLevel':
        """딕셔너리에서 생성"""
        return cls(**data)


@dataclass
class StopLossLevel:
    """
    손절 레벨 설정

    Attributes:
        level: 레벨 번호 (1, 2, 3...)
        loss_pct: 평균 단가 대비 손실률 (%)
        sell_ratio: 보유량 대비 매도 비율 (%), 0~100
    """
    level: int
    loss_pct: float
    sell_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StopLossLevel':
        """딕셔너리에서 생성"""
        return cls(**data)


@dataclass
class AdvancedDcaConfig:
    """
    고급 DCA 전략 설정

    Attributes:
        levels: DCA 레벨 설정 리스트
        take_profit_pct: 단일 익절 목표 (%), 평균 단가 대비 (하위 호환)
        stop_loss_pct: 단일 손절 목표 (%), 평균 단가 대비 (하위 호환)
        take_profit_levels: 다단계 익절 레벨 리스트 (비어있으면 단일 익절 사용)
        stop_loss_levels: 다단계 손절 레벨 리스트 (비어있으면 단일 손절 사용)
        total_capital: 총 투자 가능 자산 (원), 비중↔금액 계산 기준
        enabled: DCA 전략 활성화 여부
    """
    levels: List[DcaLevelConfig]
    take_profit_pct: float
    stop_loss_pct: float
    total_capital: int = 1000000  # 기본값: 100만원
    enabled: bool = True
    take_profit_levels: List[TakeProfitLevel] = None  # 다단계 익절
    stop_loss_levels: List[StopLossLevel] = None  # 다단계 손절

    def __post_init__(self):
        """초기화 후 처리"""
        # None을 빈 리스트로 변환
        if self.take_profit_levels is None:
            self.take_profit_levels = []
        if self.stop_loss_levels is None:
            self.stop_loss_levels = []
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'levels': [level.to_dict() for level in self.levels],
            'take_profit_pct': self.take_profit_pct,
            'stop_loss_pct': self.stop_loss_pct,
            'total_capital': self.total_capital,
            'enabled': self.enabled,
            'take_profit_levels': [tp.to_dict() for tp in self.take_profit_levels],
            'stop_loss_levels': [sl.to_dict() for sl in self.stop_loss_levels]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdvancedDcaConfig':
        """딕셔너리에서 생성"""
        levels = [DcaLevelConfig.from_dict(level) for level in data['levels']]

        # 다단계 익절/손절 (없으면 빈 리스트)
        take_profit_levels = [
            TakeProfitLevel.from_dict(tp)
            for tp in data.get('take_profit_levels', [])
        ]
        stop_loss_levels = [
            StopLossLevel.from_dict(sl)
            for sl in data.get('stop_loss_levels', [])
        ]

        return cls(
            levels=levels,
            take_profit_pct=data['take_profit_pct'],
            stop_loss_pct=data['stop_loss_pct'],
            total_capital=data.get('total_capital', 1000000),
            enabled=data.get('enabled', True),
            take_profit_levels=take_profit_levels,
            stop_loss_levels=stop_loss_levels
        )
    
    def get_level_config(self, level: int) -> Optional[DcaLevelConfig]:
        """특정 레벨 설정 조회"""
        for level_config in self.levels:
            if level_config.level == level:
                return level_config
        return None

    def calculate_amount_from_weight(self, weight_pct: float) -> int:
        """
        비중(%)에서 금액(원) 계산

        Args:
            weight_pct: 매수 비중 (%)

        Returns:
            계산된 금액 (원)
        """
        return int(self.total_capital * weight_pct / 100)

    def calculate_weight_from_amount(self, order_amount: int) -> float:
        """
        금액(원)에서 비중(%) 계산

        Args:
            order_amount: 주문 금액 (원)

        Returns:
            계산된 비중 (%)
        """
        if self.total_capital == 0:
            return 0.0
        return round(order_amount / self.total_capital * 100, 2)
    
    def calculate_average_price(self, current_price: float) -> tuple[float, float, float]:
        """
        평균 단가 계산
        
        Args:
            current_price: 현재가
            
        Returns:
            (총 투자금, 총 매수 수량, 평균 단가)
        """
        total_invested = 0.0
        total_quantity = 0.0
        
        for level_config in self.levels:
            # 진입가 계산
            entry_price = current_price * (1 - level_config.drop_pct / 100)
            
            # 매수 수량 계산
            quantity = level_config.order_amount / entry_price
            
            total_invested += level_config.order_amount
            total_quantity += quantity
        
        avg_price = total_invested / total_quantity if total_quantity > 0 else 0
        
        return total_invested, total_quantity, avg_price
    
    def calculate_targets(self, current_price: float) -> Dict[str, float]:
        """
        익절/손절가 계산

        Args:
            current_price: 현재가

        Returns:
            {'avg_price', 'take_profit_price', 'stop_loss_price', 'total_invested'}
        """
        total_invested, total_quantity, avg_price = self.calculate_average_price(current_price)

        take_profit_price = avg_price * (1 + self.take_profit_pct / 100)
        stop_loss_price = avg_price * (1 - self.stop_loss_pct / 100)

        return {
            'avg_price': avg_price,
            'take_profit_price': take_profit_price,
            'stop_loss_price': stop_loss_price,
            'total_invested': total_invested,
            'total_quantity': total_quantity
        }

    def is_multi_level_tp_enabled(self) -> bool:
        """다단계 익절 사용 여부"""
        return len(self.take_profit_levels) > 0

    def is_multi_level_sl_enabled(self) -> bool:
        """다단계 손절 사용 여부"""
        return len(self.stop_loss_levels) > 0

    def get_tp_levels_with_prices(self, avg_price: float) -> List[Dict[str, Any]]:
        """
        익절 레벨별 가격 계산

        Args:
            avg_price: 평균 단가

        Returns:
            [{'level': 1, 'profit_pct': 5.0, 'sell_ratio': 30.0, 'price': 105000}, ...]
        """
        if not self.is_multi_level_tp_enabled():
            # 단일 익절
            return [{
                'level': 1,
                'profit_pct': self.take_profit_pct,
                'sell_ratio': 100.0,
                'price': avg_price * (1 + self.take_profit_pct / 100)
            }]

        # 다단계 익절
        return [
            {
                'level': tp.level,
                'profit_pct': tp.profit_pct,
                'sell_ratio': tp.sell_ratio,
                'price': avg_price * (1 + tp.profit_pct / 100)
            }
            for tp in self.take_profit_levels
        ]

    def get_sl_levels_with_prices(self, avg_price: float) -> List[Dict[str, Any]]:
        """
        손절 레벨별 가격 계산

        Args:
            avg_price: 평균 단가

        Returns:
            [{'level': 1, 'loss_pct': 10.0, 'sell_ratio': 50.0, 'price': 90000}, ...]
        """
        if not self.is_multi_level_sl_enabled():
            # 단일 손절
            return [{
                'level': 1,
                'loss_pct': self.stop_loss_pct,
                'sell_ratio': 100.0,
                'price': avg_price * (1 - self.stop_loss_pct / 100)
            }]

        # 다단계 손절
        return [
            {
                'level': sl.level,
                'loss_pct': sl.loss_pct,
                'sell_ratio': sl.sell_ratio,
                'price': avg_price * (1 - sl.loss_pct / 100)
            }
            for sl in self.stop_loss_levels
        ]


class DcaConfigManager:
    """
    DCA 설정 파일 관리자
    
    JSON 파일로 설정 저장/로드
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        초기화
        
        Args:
            config_path: 설정 파일 경로 (None이면 프로젝트 루트)
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'dca_config.json'
        
        self.config_path = config_path
    
    def load(self) -> AdvancedDcaConfig:
        """
        설정 로드
        
        Returns:
            AdvancedDcaConfig 인스턴스
        """
        if not self.config_path.exists():
            return self.create_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return AdvancedDcaConfig.from_dict(data)
        
        except Exception as e:
            print(f"⚠️ 설정 로드 실패: {e}")
            return self.create_default_config()
    
    def save(self, config: AdvancedDcaConfig) -> bool:
        """
        설정 저장
        
        Args:
            config: AdvancedDcaConfig 인스턴스
            
        Returns:
            성공 여부
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            
            print(f"✅ DCA 설정 저장 완료: {self.config_path}")
            return True
        
        except Exception as e:
            print(f"❌ 설정 저장 실패: {e}")
            return False
    
    def create_default_config(self) -> AdvancedDcaConfig:
        """
        기본 설정 생성
        
        Returns:
            기본 AdvancedDcaConfig
        """
        # 기본 5단계 DCA 설정
        default_levels = [
            DcaLevelConfig(level=1, drop_pct=0.0, weight_pct=20.0, order_amount=10000),
            DcaLevelConfig(level=2, drop_pct=5.0, weight_pct=25.0, order_amount=12500),
            DcaLevelConfig(level=3, drop_pct=10.0, weight_pct=30.0, order_amount=15000),
            DcaLevelConfig(level=4, drop_pct=15.0, weight_pct=40.0, order_amount=20000),
            DcaLevelConfig(level=5, drop_pct=20.0, weight_pct=50.0, order_amount=25000),
        ]
        
        config = AdvancedDcaConfig(
            levels=default_levels,
            take_profit_pct=10.0,  # 평균 단가 대비 +10%
            stop_loss_pct=25.0,    # 평균 단가 대비 -25%
            enabled=True
        )
        
        # 기본 설정 저장
        self.save(config)
        
        return config


# 테스트 코드
if __name__ == "__main__":
    # 설정 관리자 생성
    manager = DcaConfigManager()
    
    # 기본 설정 로드
    config = manager.load()
    
    print("=" * 60)
    print("📊 DCA 설정")
    print("=" * 60)
    
    for level_config in config.levels:
        print(f"레벨 {level_config.level}: "
              f"하락 {level_config.drop_pct}%, "
              f"비중 {level_config.weight_pct}%, "
              f"금액 {level_config.order_amount:,}원")
    
    print()
    print(f"🎯 익절: +{config.take_profit_pct}%")
    print(f"🛑 손절: -{config.stop_loss_pct}%")
    print()
    
    # 현재가 1억원 기준 계산
    current_price = 100000000
    targets = config.calculate_targets(current_price)
    
    print("=" * 60)
    print(f"📈 시뮬레이션 (현재가: {current_price:,}원)")
    print("=" * 60)
    print(f"총 투자금: {targets['total_invested']:,.0f}원")
    print(f"평균 단가: {targets['avg_price']:,.0f}원")
    print(f"익절가: {targets['take_profit_price']:,.0f}원")
    print(f"손절가: {targets['stop_loss_price']:,.0f}원")
    print("=" * 60)
