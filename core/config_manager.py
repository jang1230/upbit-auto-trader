"""
V4 설정 관리자

역할:
- trading_config.json 로드/저장
- JSON 스키마 검증
- V3 → V4 마이그레이션
- 기본 설정 생성
"""

import json
import os
import shutil
import time
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigValidationError(Exception):
    """설정 검증 오류"""
    pass


class ConfigManager:
    """V4 통합 설정 관리자"""

    DEFAULT_CONFIG_PATH = "config/trading_config.json"
    TEMPLATE_PATH = "config/trading_config_template.json"
    SCHEMA_PATH = "config/schemas/trading_config_schema.json"

    # V3 설정 파일 경로
    V3_DCA_CONFIG = "config/dca_config.json"
    V3_AUTO_CONFIG = "config/auto_trading_config.json"
    V3_BACKUP_DIR = "config/backup_v3"

    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: 설정 파일 경로 (기본값: config/trading_config.json)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config: Optional[Dict[str, Any]] = None

    def load_config(self, auto_migrate: bool = True) -> Dict[str, Any]:
        """
        설정 파일 로드

        Args:
            auto_migrate: V3 설정 발견 시 자동 마이그레이션 여부

        Returns:
            설정 딕셔너리

        Raises:
            ConfigValidationError: 설정 검증 실패
            FileNotFoundError: 설정 파일 없음
        """
        # 설정 파일이 없으면 마이그레이션 시도 또는 기본 설정 생성
        if not os.path.exists(self.config_path):
            if auto_migrate and self._has_v3_config():
                print("📋 V3 설정 파일 발견 - 자동 마이그레이션 시작...")
                self.migrate_from_v3()
            else:
                print("⚠️ 설정 파일이 없습니다. 기본 설정을 생성합니다.")
                self.create_default_config()

        # 설정 파일 로드
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"JSON 파싱 오류: {e}")

        # 'strategy' 필드 자동 마이그레이션 (V4 내부 업데이트)
        migrated_strategy = self._migrate_strategy_field(self.config)
        if migrated_strategy:
            print("🔄 설정 업데이트: 'strategy' 필드 추가됨")

        # 'buy_amount_krw' 필드 자동 마이그레이션 (manual 모드 지원)
        migrated_buy_amount = self._migrate_buy_amount_field(self.config)
        if migrated_buy_amount:
            print("🔄 설정 업데이트: 'buy_amount_krw' 필드 추가됨")

        # 마이그레이션이 있었으면 저장
        if migrated_strategy or migrated_buy_amount:
            self.save_config(self.config)

        # 스키마 검증
        self.validate_config(self.config)

        print(f"✅ 설정 로드 완료: {self.config_path}")
        return self.config

    def save_config(self, config: Dict[str, Any] = None) -> None:
        """
        설정 파일 저장

        Args:
            config: 저장할 설정 (None이면 현재 self.config 사용)

        Raises:
            ConfigValidationError: 설정 검증 실패
        """
        if config is None:
            if self.config is None:
                raise ValueError("저장할 설정이 없습니다.")
            config = self.config
        else:
            self.config = config

        # 저장 전 검증
        self.validate_config(config)

        # 백업 생성 (기존 파일이 있으면)
        if os.path.exists(self.config_path):
            backup_path = f"{self.config_path}.backup"
            shutil.copy2(self.config_path, backup_path)

        # 저장
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"✅ 설정 저장 완료: {self.config_path}")

    def validate_config(self, config: Dict[str, Any]) -> None:
        """
        설정 검증

        Args:
            config: 검증할 설정

        Raises:
            ConfigValidationError: 검증 실패
        """
        # 기본 구조 검증
        required_keys = ['version', 'global_settings', 'groups']
        for key in required_keys:
            if key not in config:
                raise ConfigValidationError(f"필수 키 누락: {key}")

        # 버전 검증
        version = config.get('version', '')
        if not version.startswith('4.'):
            raise ConfigValidationError(f"잘못된 버전: {version} (4.x.x 필요)")

        # 그룹 검증 (딕셔너리 구조)
        groups = config.get('groups', {})
        if not isinstance(groups, dict):
            raise ConfigValidationError("groups는 딕셔너리여야 합니다.")

        # 코인 중복 할당 검사
        all_coins = []
        for group_id, group in groups.items():
            coins = group.get('coins', [])
            for coin in coins:
                if coin in all_coins:
                    raise ConfigValidationError(f"코인 {coin}이 여러 그룹에 할당되었습니다 (그룹: {group_id}).")
                all_coins.append(coin)

        # JSON 스키마 검증 (선택적 - jsonschema 패키지가 있으면)
        try:
            import jsonschema
            if os.path.exists(self.SCHEMA_PATH):
                with open(self.SCHEMA_PATH, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                jsonschema.validate(config, schema)
        except ImportError:
            # jsonschema 없으면 기본 검증만 수행
            pass
        except jsonschema.ValidationError as e:
            raise ConfigValidationError(f"스키마 검증 실패: {e.message}")

    def create_default_config(self) -> Dict[str, Any]:
        """
        기본 설정 생성

        Returns:
            생성된 기본 설정
        """
        # 템플릿에서 복사
        if os.path.exists(self.TEMPLATE_PATH):
            shutil.copy2(self.TEMPLATE_PATH, self.config_path)
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            # 템플릿이 없으면 최소 설정 생성
            config = {
                "version": "4.0.0",
                "global_settings": {
                    "trading_day_reset_hour": 9,
                    "max_positions": {
                        "enabled": False,
                        "limit": 3
                    },
                    "min_krw_balance": {
                        "enabled": True,
                        "amount": 50000
                    },
                    "daily_loss_limit": {
                        "enabled": False,
                        "loss_pct": 10.0,
                        "calculation_method": "daily_only",
                        "action": "alert"
                    },
                    "telegram": {
                        "enabled": False,
                        "token": "",
                        "chat_id": ""
                    },
                    "dry_run": True
                },
                "groups": {}
            }
            self.save_config(config)

        self.config = config
        print("✅ 기본 설정 생성 완료")
        return config

    def _has_v3_config(self) -> bool:
        """V3 설정 파일 존재 여부"""
        return (os.path.exists(self.V3_DCA_CONFIG) or
                os.path.exists(self.V3_AUTO_CONFIG))

    def migrate_from_v3(self) -> Dict[str, Any]:
        """
        V3 설정을 V4로 마이그레이션

        변환 규칙:
        - dca_config.json → 그룹 "반자동 모드 (V3)"
        - auto_trading_config.json → 그룹 "자동 모드 (V3)"

        Returns:
            마이그레이션된 V4 설정
        """
        print("🔄 V3 → V4 마이그레이션 시작...")

        # V4 기본 구조 생성
        v4_config = {
            "version": "4.0.0",
            "global_settings": {
                "trading_day_reset_hour": 9,
                "max_positions": {
                    "enabled": False,
                    "limit": 3
                },
                "min_krw_balance": {
                    "enabled": False,
                    "amount": 50000
                },
                "daily_loss_limit": {
                    "enabled": False,
                    "loss_pct": 10.0,
                    "calculation_method": "daily_only",
                    "action": "alert"
                },
                "telegram": {
                    "enabled": False,
                    "token": "",
                    "chat_id": ""
                },
                "dry_run": True  # 안전하게 dry-run으로 시작
            },
            "groups": {}
        }

        # V3 DCA 설정 마이그레이션 (반자동 모드)
        if os.path.exists(self.V3_DCA_CONFIG):
            try:
                with open(self.V3_DCA_CONFIG, 'r', encoding='utf-8') as f:
                    dca_config = json.load(f)

                group_id = "semi_auto_v3"
                semi_auto_group = {
                    "name": "반자동 모드 (V3 마이그레이션)",
                    "observation_only": False,
                    "coins": [],  # 사용자가 수동으로 추가
                    "buy_settings": {
                        "mode": "manual"
                    },
                    "dca_settings": {
                        "mode": "auto",
                        "levels": [
                            {"price_ratio": -3.0, "quantity_ratio": 100},
                            {"price_ratio": -7.0, "quantity_ratio": 100},
                            {"price_ratio": -12.0, "quantity_ratio": 100}
                        ]
                    },
                    "profit_settings": {
                        "mode": "auto",
                        "levels": [
                            {"price_ratio": dca_config.get('profit_target_pct', 5.0), "quantity_ratio": 100}
                        ]
                    },
                    "loss_settings": {
                        "mode": "auto",
                        "levels": [
                            {"price_ratio": dca_config.get('stop_loss_pct', -15.0), "quantity_ratio": 100}
                        ]
                    }
                }

                # 텔레그램 설정 가져오기
                if 'telegram' in dca_config:
                    v4_config['global_settings']['telegram'] = dca_config['telegram']

                v4_config['groups'][group_id] = semi_auto_group
                print(f"  ✅ 반자동 모드 그룹 생성: {semi_auto_group['name']}")

            except Exception as e:
                print(f"  ⚠️ DCA 설정 마이그레이션 실패: {e}")

        # V3 Auto 설정 마이그레이션 (자동 모드)
        if os.path.exists(self.V3_AUTO_CONFIG):
            try:
                with open(self.V3_AUTO_CONFIG, 'r', encoding='utf-8') as f:
                    auto_config = json.load(f)

                group_id = "auto_v3"
                auto_group = {
                    "name": "자동 모드 (V3 마이그레이션)",
                    "observation_only": False,
                    "coins": auto_config.get('symbols', []),
                    "buy_settings": {
                        "mode": "auto",
                        "auto_config": {
                            "enabled": True,
                            "strategy": "v4_auto_buy",  # 기본 전략
                            "investment_style": "balanced",  # 기본값
                            "candle_unit": "60",
                            "indicators": {
                                "rsi": {
                                    "enabled": True,
                                    "period": 14,
                                    "oversold": 30,
                                    "overbought": 70
                                },
                                "macd": {
                                    "enabled": True,
                                    "fast": 12,
                                    "slow": 26,
                                    "signal": 9
                                },
                                "volume": {
                                    "enabled": True,
                                    "period": 20,
                                    "threshold": 2.0
                                }
                            },
                            "buy_amount_krw": auto_config.get('buy_amount_krw', 50000)
                        }
                    },
                    "dca_settings": {
                        "mode": "auto",
                        "levels": [
                            {"price_ratio": -3.0, "quantity_ratio": 100},
                            {"price_ratio": -7.0, "quantity_ratio": 100},
                            {"price_ratio": -12.0, "quantity_ratio": 100}
                        ]
                    },
                    "profit_settings": {
                        "mode": "auto",
                        "levels": [
                            {"price_ratio": auto_config.get('profit_target_pct', 5.0), "quantity_ratio": 100}
                        ]
                    },
                    "loss_settings": {
                        "mode": "auto",
                        "levels": [
                            {"price_ratio": auto_config.get('stop_loss_pct', -15.0), "quantity_ratio": 100}
                        ]
                    }
                }

                # 텔레그램 설정 가져오기
                if 'telegram' in auto_config:
                    v4_config['global_settings']['telegram'] = auto_config['telegram']

                v4_config['groups'][group_id] = auto_group
                print(f"  ✅ 자동 모드 그룹 생성: {auto_group['name']}")

            except Exception as e:
                print(f"  ⚠️ Auto 설정 마이그레이션 실패: {e}")

        # V3 파일 백업
        self._backup_v3_files()

        # V4 설정 저장
        self.config = v4_config
        self.save_config(v4_config)

        print("✅ V3 → V4 마이그레이션 완료!")
        print(f"   - 생성된 그룹 수: {len(v4_config['groups'])}")
        print(f"   - V3 파일 백업 위치: {self.V3_BACKUP_DIR}")
        print(f"   ⚠️ Dry-run 모드로 설정됨 - 실거래 전 설정을 확인하세요!")

        return v4_config

    def _backup_v3_files(self) -> None:
        """V3 설정 파일 백업"""
        os.makedirs(self.V3_BACKUP_DIR, exist_ok=True)

        v3_files = [
            self.V3_DCA_CONFIG,
            self.V3_AUTO_CONFIG,
            "data/positions.json"
        ]

        for v3_file in v3_files:
            if os.path.exists(v3_file):
                backup_name = os.path.basename(v3_file)
                backup_path = os.path.join(self.V3_BACKUP_DIR, backup_name)
                shutil.copy2(v3_file, backup_path)
                print(f"  📦 백업 완료: {v3_file} → {backup_path}")

    def _migrate_strategy_field(self, config: Dict[str, Any]) -> bool:
        """
        'strategy' 필드 자동 마이그레이션 (V4 내부 업데이트)

        기존 V4 config에 'strategy' 필드가 없는 경우 자동으로 추가합니다.

        Args:
            config: 설정 딕셔너리

        Returns:
            bool: 마이그레이션 수행 여부
        """
        migrated_groups = []

        for group_id, group in config.get('groups', {}).items():
            # buy_settings가 없으면 skip
            if 'buy_settings' not in group:
                continue

            # auto_config가 없으면 skip (manual 모드)
            if 'auto_config' not in group['buy_settings']:
                continue

            auto_config = group['buy_settings']['auto_config']

            # 'strategy' 필드가 없거나 잘못된 값인 경우
            if 'strategy' not in auto_config:
                auto_config['strategy'] = 'v4_auto_buy'
                migrated_groups.append(group_id)
                print(f"  ✅ 그룹 '{group_id}': strategy → v4_auto_buy")
            elif auto_config['strategy'] not in ['v4_auto_buy', 'expert']:
                # 잘못된 값 수정
                old_value = auto_config['strategy']
                auto_config['strategy'] = 'v4_auto_buy'
                migrated_groups.append(group_id)
                print(f"  ⚠️ 그룹 '{group_id}': 잘못된 strategy '{old_value}' → v4_auto_buy")

        return len(migrated_groups) > 0

    def _migrate_buy_amount_field(self, config: Dict[str, Any]) -> bool:
        """
        'buy_amount_krw' 필드 자동 마이그레이션

        기존 V4 config에서 manual 모드를 위한 buy_amount_krw 필드를 추가합니다.
        - mode='manual' + buy_amount_krw 없음 → 기본값 50000 추가
        - mode='auto' + buy_amount_krw 없음 → auto_config.buy_amount_krw에서 복사

        Args:
            config: 설정 딕셔너리

        Returns:
            bool: 마이그레이션 수행 여부
        """
        migrated_groups = []

        for group_id, group in config.get('groups', {}).items():
            # buy_settings가 없으면 skip
            if 'buy_settings' not in group:
                continue

            buy_settings = group['buy_settings']

            # mode가 없으면 skip (잘못된 설정)
            if 'mode' not in buy_settings:
                continue

            mode = buy_settings['mode']

            # buy_amount_krw가 이미 있으면 skip
            if 'buy_amount_krw' in buy_settings:
                continue

            # mode별 마이그레이션
            if mode == 'manual':
                # manual 모드: 기본값 50000 추가
                buy_settings['buy_amount_krw'] = 50000
                migrated_groups.append(group_id)
                print(f"  ✅ 그룹 '{group_id}' (manual): buy_amount_krw → 50000")

            elif mode == 'auto':
                # auto 모드: auto_config.buy_amount_krw에서 복사
                if 'auto_config' in buy_settings and 'buy_amount_krw' in buy_settings['auto_config']:
                    buy_settings['buy_amount_krw'] = buy_settings['auto_config']['buy_amount_krw']
                    migrated_groups.append(group_id)
                    print(f"  ✅ 그룹 '{group_id}' (auto): buy_amount_krw → {buy_settings['buy_amount_krw']}")
                else:
                    # auto_config.buy_amount_krw도 없으면 기본값
                    buy_settings['buy_amount_krw'] = 50000
                    migrated_groups.append(group_id)
                    print(f"  ⚠️ 그룹 '{group_id}' (auto): buy_amount_krw → 50000 (기본값)")

        return len(migrated_groups) > 0

    def get_group_by_id(self, group_id: str) -> Optional[Dict[str, Any]]:
        """그룹 ID로 그룹 조회"""
        if self.config is None:
            self.load_config()

        return self.config.get('groups', {}).get(group_id)

    def get_group_by_symbol(self, symbol: str) -> Optional[tuple]:
        """
        코인 심볼로 그룹 조회

        Returns:
            (group_id, group_data) 또는 None
        """
        if self.config is None:
            self.load_config()

        for group_id, group in self.config.get('groups', {}).items():
            if symbol in group.get('coins', []):
                return (group_id, group)
        return None

    def get_all_groups(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 그룹 반환

        Returns:
            딕셔너리 {group_id: group_data}
        """
        if self.config is None:
            self.load_config()

        return self.config.get('groups', {})

    def update_group(self, group_id: str, updates: Dict[str, Any]) -> None:
        """
        그룹 정보 업데이트

        Args:
            group_id: 그룹 ID
            updates: 업데이트할 필드들
        """
        # ✅ 수정: 항상 최신 파일을 로드하여 다른 다이얼로그의 변경사항 덮어쓰기 방지
        self.load_config()

        if group_id not in self.config['groups']:
            raise ValueError(f"그룹을 찾을 수 없습니다: {group_id}")

        self.config['groups'][group_id].update(updates)
        self.save_config()

    def add_group(self, group_id: str, group: Dict[str, Any]) -> None:
        """
        새 그룹 추가

        Args:
            group_id: 그룹 ID (사용자 지정)
            group: 그룹 데이터
        """
        if self.config is None:
            self.load_config()

        if group_id in self.config['groups']:
            raise ValueError(f"그룹 ID가 이미 존재합니다: {group_id}")

        self.config['groups'][group_id] = group
        self.save_config()

    def remove_group(self, group_id: str) -> None:
        """그룹 제거"""
        if self.config is None:
            self.load_config()

        if group_id in self.config['groups']:
            del self.config['groups'][group_id]
            self.save_config()
        else:
            raise ValueError(f"그룹을 찾을 수 없습니다: {group_id}")


if __name__ == "__main__":
    # 테스트 코드
    print("=== ConfigManager 테스트 ===\n")

    manager = ConfigManager()

    # 1. 기본 설정 생성
    print("1. 기본 설정 생성")
    config = manager.create_default_config()
    print(f"   - 버전: {config['version']}")
    print(f"   - Dry-run: {config['global_settings']['dry_run']}")
    print(f"   - 그룹 수: {len(config['groups'])}")
    print()

    # 2. 설정 로드
    print("2. 설정 로드")
    loaded_config = manager.load_config()
    print(f"   - 로드 성공: {loaded_config['version']}")
    print()

    # 3. 그룹 조회
    print("3. 그룹 조회")
    groups = manager.get_all_groups()
    print(f"   - 전체 그룹 수: {len(groups)}")
    if groups:
        first_group_id = list(groups.keys())[0]
        print(f"   - 첫 번째 그룹 ID: {first_group_id}")
        print(f"   - 첫 번째 그룹명: {groups[first_group_id]['name']}")
    print()

    print("✅ 테스트 완료!")
