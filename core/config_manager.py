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

        # 그룹 검증
        groups = config.get('groups', [])
        if not isinstance(groups, list):
            raise ConfigValidationError("groups는 배열이어야 합니다.")

        # 그룹 ID 중복 검사
        group_ids = [g['id'] for g in groups if 'id' in g]
        if len(group_ids) != len(set(group_ids)):
            raise ConfigValidationError("그룹 ID가 중복되었습니다.")

        # 코인 중복 할당 검사
        all_coins = []
        for group in groups:
            coins = group.get('coins', [])
            for coin in coins:
                if coin in all_coins:
                    raise ConfigValidationError(f"코인 {coin}이 여러 그룹에 할당되었습니다.")
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
                    "observation_mode": False,
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
                "groups": []
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
                "observation_mode": False,
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
            "groups": []
        }

        # V3 DCA 설정 마이그레이션 (반자동 모드)
        if os.path.exists(self.V3_DCA_CONFIG):
            try:
                with open(self.V3_DCA_CONFIG, 'r', encoding='utf-8') as f:
                    dca_config = json.load(f)

                semi_auto_group = {
                    "id": f"group_{int(time.time() * 1000)}",
                    "name": "반자동 모드 (V3 마이그레이션)",
                    "coins": [],  # 사용자가 수동으로 추가
                    "buy_settings": {
                        "mode": "manual"
                    },
                    "dca_settings": {
                        "mode": "auto",
                        "levels": dca_config.get('dca_levels', [
                            {"drop_pct": -3.0, "buy_ratio": 1.5},
                            {"drop_pct": -7.0, "buy_ratio": 2.0},
                            {"drop_pct": -12.0, "buy_ratio": 3.0}
                        ])
                    },
                    "profit_settings": {
                        "mode": "auto",
                        "target_pct": dca_config.get('profit_target_pct', 5.0)
                    },
                    "loss_settings": {
                        "mode": "auto",
                        "stop_loss_pct": dca_config.get('stop_loss_pct', -15.0)
                    }
                }

                # 텔레그램 설정 가져오기
                if 'telegram' in dca_config:
                    v4_config['global_settings']['telegram'] = dca_config['telegram']

                v4_config['groups'].append(semi_auto_group)
                print(f"  ✅ 반자동 모드 그룹 생성: {semi_auto_group['name']}")

            except Exception as e:
                print(f"  ⚠️ DCA 설정 마이그레이션 실패: {e}")

        # V3 Auto 설정 마이그레이션 (자동 모드)
        if os.path.exists(self.V3_AUTO_CONFIG):
            try:
                with open(self.V3_AUTO_CONFIG, 'r', encoding='utf-8') as f:
                    auto_config = json.load(f)

                auto_group = {
                    "id": f"group_{int(time.time() * 1000) + 1}",
                    "name": "자동 모드 (V3 마이그레이션)",
                    "coins": auto_config.get('symbols', []),
                    "buy_settings": {
                        "mode": "auto",
                        "auto_config": {
                            "enabled": True,
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
                        "levels": auto_config.get('dca_levels', [
                            {"drop_pct": -3.0, "buy_ratio": 1.5},
                            {"drop_pct": -7.0, "buy_ratio": 2.0},
                            {"drop_pct": -12.0, "buy_ratio": 3.0}
                        ])
                    },
                    "profit_settings": {
                        "mode": "auto",
                        "target_pct": auto_config.get('profit_target_pct', 5.0)
                    },
                    "loss_settings": {
                        "mode": "auto",
                        "stop_loss_pct": auto_config.get('stop_loss_pct', -15.0)
                    }
                }

                # 텔레그램 설정 가져오기
                if 'telegram' in auto_config:
                    v4_config['global_settings']['telegram'] = auto_config['telegram']

                v4_config['groups'].append(auto_group)
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

    def get_group_by_id(self, group_id: str) -> Optional[Dict[str, Any]]:
        """그룹 ID로 그룹 조회"""
        if self.config is None:
            self.load_config()

        for group in self.config.get('groups', []):
            if group['id'] == group_id:
                return group
        return None

    def get_group_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """코인 심볼로 그룹 조회"""
        if self.config is None:
            self.load_config()

        for group in self.config.get('groups', []):
            if symbol in group.get('coins', []):
                return group
        return None

    def get_all_groups(self) -> list:
        """모든 그룹 반환"""
        if self.config is None:
            self.load_config()

        return self.config.get('groups', [])

    def update_group(self, group_id: str, updates: Dict[str, Any]) -> None:
        """
        그룹 정보 업데이트

        Args:
            group_id: 그룹 ID
            updates: 업데이트할 필드들
        """
        if self.config is None:
            self.load_config()

        for i, group in enumerate(self.config['groups']):
            if group['id'] == group_id:
                self.config['groups'][i].update(updates)
                self.save_config()
                return

        raise ValueError(f"그룹을 찾을 수 없습니다: {group_id}")

    def add_group(self, group: Dict[str, Any]) -> None:
        """새 그룹 추가"""
        if self.config is None:
            self.load_config()

        # ID 자동 생성
        if 'id' not in group:
            group['id'] = f"group_{int(time.time() * 1000)}"

        self.config['groups'].append(group)
        self.save_config()

    def remove_group(self, group_id: str) -> None:
        """그룹 제거"""
        if self.config is None:
            self.load_config()

        self.config['groups'] = [
            g for g in self.config['groups'] if g['id'] != group_id
        ]
        self.save_config()


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
        print(f"   - 첫 번째 그룹: {groups[0]['name']}")
    print()

    print("✅ 테스트 완료!")
