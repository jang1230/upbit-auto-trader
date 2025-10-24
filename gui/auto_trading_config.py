"""
AutoTradingConfig - 완전 자동 트레이딩 설정 관리

자동매수 설정 및 리스크 관리 옵션을 관리합니다.
"""

import json
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AutoTradingConfig:
    """
    완전 자동 트레이딩 설정 클래스
    
    Features:
    - 매수 금액 설정
    - 모니터링 코인 선택 (상위 N개 또는 커스텀 리스트)
    - 선택적 리스크 관리 (4가지 옵션)
    """
    
    def __init__(self):
        """기본값으로 초기화"""
        # 기본 설정
        self.enabled: bool = True
        self.buy_amount: float = 10000.0
        
        # 모니터링 설정
        self.monitoring_mode: str = "top_marketcap"  # "top_marketcap" | "custom_list"
        self.top_n: int = 10
        self.custom_symbols: List[str] = []
        
        # 리스크 관리 - 최대 포지션 수
        self.max_positions_enabled: bool = True
        self.max_positions_limit: int = 3
        
        # 리스크 관리 - 일일 거래 횟수
        self.daily_trades_enabled: bool = True
        self.daily_trades_limit: int = 5
        
        # 리스크 관리 - 최소 잔고
        self.min_krw_balance_enabled: bool = True
        self.min_krw_balance_amount: float = 50000.0
        
        # 리스크 관리 - 일일 손실 한도
        self.stop_on_loss_enabled: bool = True
        self.stop_on_loss_daily_pct: float = 10.0
        
        # 전략 설정
        self.strategy_type: str = "scalping"
        self.scan_interval: int = 60  # 초
    
    @classmethod
    def from_file(cls, file_path: str) -> 'AutoTradingConfig':
        """
        JSON 파일에서 설정 로드
        
        Args:
            file_path: 설정 파일 경로
            
        Returns:
            AutoTradingConfig: 로드된 설정 객체
        """
        config = cls()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 기본 설정
            config.enabled = data.get('enabled', True)
            config.buy_amount = float(data.get('buy_amount', 10000.0))
            
            # 모니터링 설정
            monitoring = data.get('monitoring', {})
            config.monitoring_mode = monitoring.get('mode', 'top_marketcap')
            config.top_n = monitoring.get('top_n', 10)
            config.custom_symbols = monitoring.get('custom_symbols', [])
            
            # 리스크 관리 설정
            risk = data.get('risk_management', {})
            
            # 1. 최대 포지션 수
            max_pos = risk.get('max_positions', {})
            config.max_positions_enabled = max_pos.get('enabled', True)
            config.max_positions_limit = max_pos.get('limit', 3)
            
            # 2. 일일 거래 횟수
            daily_trades = risk.get('daily_trades', {})
            config.daily_trades_enabled = daily_trades.get('enabled', True)
            config.daily_trades_limit = daily_trades.get('limit', 5)
            
            # 3. 최소 잔고
            min_balance = risk.get('min_krw_balance', {})
            config.min_krw_balance_enabled = min_balance.get('enabled', True)
            config.min_krw_balance_amount = float(min_balance.get('amount', 50000.0))
            
            # 4. 일일 손실 한도
            stop_loss = risk.get('stop_on_loss', {})
            config.stop_on_loss_enabled = stop_loss.get('enabled', True)
            config.stop_on_loss_daily_pct = float(stop_loss.get('daily_loss_pct', 10.0))
            
            # 전략 설정
            strategy = data.get('strategy', {})
            config.strategy_type = strategy.get('type', 'scalping')
            config.scan_interval = strategy.get('scan_interval', 60)
            
            logger.info(f"✅ 자동매수 설정 로드 완료: {file_path}")
            logger.info(f"   - 매수 금액: {config.buy_amount:,.0f}원")
            logger.info(f"   - 모니터링 모드: {config.monitoring_mode} (상위 {config.top_n}개)")
            logger.info(f"   - 스캔 주기: {config.scan_interval}초")
            
            return config
            
        except FileNotFoundError:
            logger.warning(f"⚠️ 설정 파일 없음: {file_path} (기본값 사용)")
            return config
        except Exception as e:
            logger.error(f"❌ 설정 로드 실패: {e}")
            return config
    
    def to_file(self, file_path: str):
        """
        JSON 파일로 설정 저장
        
        Args:
            file_path: 저장할 파일 경로
        """
        try:
            data = {
                "enabled": self.enabled,
                "buy_amount": self.buy_amount,
                "monitoring": {
                    "mode": self.monitoring_mode,
                    "top_n": self.top_n,
                    "custom_symbols": self.custom_symbols
                },
                "risk_management": {
                    "max_positions": {
                        "enabled": self.max_positions_enabled,
                        "limit": self.max_positions_limit
                    },
                    "daily_trades": {
                        "enabled": self.daily_trades_enabled,
                        "limit": self.daily_trades_limit
                    },
                    "min_krw_balance": {
                        "enabled": self.min_krw_balance_enabled,
                        "amount": self.min_krw_balance_amount
                    },
                    "stop_on_loss": {
                        "enabled": self.stop_on_loss_enabled,
                        "daily_loss_pct": self.stop_on_loss_daily_pct
                    }
                },
                "strategy": {
                    "type": self.strategy_type,
                    "scan_interval": self.scan_interval
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 설정 저장 완료: {file_path}")
            
        except Exception as e:
            logger.error(f"❌ 설정 저장 실패: {e}")
    
    def get_monitoring_symbols(self) -> List[str]:
        """
        모니터링 대상 심볼 리스트 반환
        
        Returns:
            List[str]: 모니터링할 심볼 리스트
                      - top_marketcap 모드: 빈 리스트 (런타임에 조회)
                      - custom_list 모드: 설정된 심볼 리스트
        """
        if self.monitoring_mode == "custom_list":
            return self.custom_symbols
        else:
            # top_marketcap 모드는 런타임에 조회
            return []
    
    def validate(self) -> tuple[bool, str]:
        """
        설정 유효성 검증
        
        Returns:
            tuple[bool, str]: (유효 여부, 에러 메시지)
        """
        # 매수 금액 체크
        if self.buy_amount < 5000:
            return False, "매수 금액은 5,000원 이상이어야 합니다 (Upbit 최소 주문 금액)"
        
        # 모니터링 모드 체크
        if self.monitoring_mode not in ["top_marketcap", "custom_list"]:
            return False, f"잘못된 모니터링 모드: {self.monitoring_mode}"
        
        # 커스텀 리스트 모드인데 심볼이 없으면
        if self.monitoring_mode == "custom_list" and len(self.custom_symbols) == 0:
            return False, "커스텀 리스트 모드인데 모니터링할 심볼이 지정되지 않았습니다"
        
        # 리스크 관리 값 체크
        if self.max_positions_enabled and self.max_positions_limit < 1:
            return False, "최대 포지션 수는 1개 이상이어야 합니다"
        
        if self.daily_trades_enabled and self.daily_trades_limit < 1:
            return False, "일일 거래 횟수는 1회 이상이어야 합니다"
        
        if self.min_krw_balance_enabled and self.min_krw_balance_amount < 0:
            return False, "최소 잔고는 0원 이상이어야 합니다"
        
        if self.stop_on_loss_enabled and self.stop_on_loss_daily_pct <= 0:
            return False, "일일 손실 한도는 0보다 커야 합니다"
        
        # 스캔 주기 체크
        if self.scan_interval < 10:
            return False, "스캔 주기는 10초 이상이어야 합니다 (API 제한)"
        
        return True, "OK"
    
    def __repr__(self):
        return (
            f"AutoTradingConfig("
            f"enabled={self.enabled}, "
            f"buy_amount={self.buy_amount:,.0f}, "
            f"mode={self.monitoring_mode}, "
            f"scan_interval={self.scan_interval}s)"
        )
